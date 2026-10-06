#include <vulkan/vulkan.h>

#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

static std::string json_escape(const char *value) {
    std::string out;
    for (const unsigned char c : std::string(value ? value : "")) {
        if (c == '"' || c == '\\') { out.push_back('\\'); out.push_back(static_cast<char>(c)); }
        else if (c < 0x20) { out += "?"; }
        else { out.push_back(static_cast<char>(c)); }
    }
    return out;
}

static std::string hex_bytes(const uint8_t *bytes, size_t count) {
    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (size_t i = 0; i < count; ++i) out << std::setw(2) << static_cast<unsigned>(bytes[i]);
    return out.str();
}

static bool has_extension(const std::vector<VkExtensionProperties> &extensions, const char *name) {
    for (const auto &extension : extensions) {
        if (std::string(extension.extensionName) == name) return true;
    }
    return false;
}

static const char *vendor_name(uint32_t id) {
    switch (id) {
        case 0x10DE: return "NVIDIA";
        case 0x1002: return "AMD";
        case 0x8086: return "Intel";
        default: return "OTHER";
    }
}

static const char *device_type_name(VkPhysicalDeviceType type) {
    switch (type) {
        case VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU: return "INTEGRATED_GPU";
        case VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU: return "DISCRETE_GPU";
        case VK_PHYSICAL_DEVICE_TYPE_VIRTUAL_GPU: return "VIRTUAL_GPU";
        case VK_PHYSICAL_DEVICE_TYPE_CPU: return "CPU";
        default: return "OTHER";
    }
}

static void print_buffer_query(VkPhysicalDevice physical,
                               VkExternalMemoryHandleTypeFlagBits handle_type,
                               VkBufferUsageFlags usage,
                               const char *handle_name,
                               const char *usage_name,
                               bool first) {
    VkPhysicalDeviceExternalBufferInfo info{};
    info.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTERNAL_BUFFER_INFO;
    info.flags = 0;
    info.usage = usage;
    info.handleType = handle_type;

    VkExternalBufferProperties properties{};
    properties.sType = VK_STRUCTURE_TYPE_EXTERNAL_BUFFER_PROPERTIES;
    vkGetPhysicalDeviceExternalBufferProperties(physical, &info, &properties);
    const auto features = properties.externalMemoryProperties.externalMemoryFeatures;
    if (!first) std::cout << ',';
    std::cout << "{\"handle\":\"" << handle_name
              << "\",\"usage\":\"" << usage_name
              << "\",\"flags\":0,\"external_memory_features_hex\":\"0x"
              << std::hex << features << std::dec
              << "\",\"importable\":" << ((features & VK_EXTERNAL_MEMORY_FEATURE_IMPORTABLE_BIT) ? "true" : "false")
              << ",\"exportable\":" << ((features & VK_EXTERNAL_MEMORY_FEATURE_EXPORTABLE_BIT) ? "true" : "false")
              << ",\"dedicated_only\":" << ((features & VK_EXTERNAL_MEMORY_FEATURE_DEDICATED_ONLY_BIT) ? "true" : "false")
              << ",\"compatible_handle_types_hex\":\"0x" << std::hex
              << properties.externalMemoryProperties.compatibleHandleTypes << "\",\"export_from_imported_handle_types_hex\":\"0x"
              << properties.externalMemoryProperties.exportFromImportedHandleTypes << std::dec << "\"}";
}

int main() {
    uint32_t loader_version = VK_API_VERSION_1_0;
    if (vkEnumerateInstanceVersion(&loader_version) != VK_SUCCESS) {
        std::cerr << "vkEnumerateInstanceVersion failed\n";
        return 2;
    }
    if (loader_version < VK_API_VERSION_1_1) {
        std::cerr << "Vulkan 1.1 is unavailable; this build uses core 1.1 property-query entry points\n";
        return 2;
    }

    VkApplicationInfo app{};
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName = "bounded_external_memory_capability_query";
    app.applicationVersion = 1;
    app.pEngineName = "none";
    app.engineVersion = 1;
    app.apiVersion = loader_version < VK_API_VERSION_1_1 ? loader_version : VK_API_VERSION_1_1;

    VkInstanceCreateInfo create{};
    create.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    create.pApplicationInfo = &app;
    VkInstance instance = VK_NULL_HANDLE;
    VkResult result = vkCreateInstance(&create, nullptr, &instance);
    if (result != VK_SUCCESS || instance == VK_NULL_HANDLE) {
        std::cerr << "vkCreateInstance failed: " << static_cast<int>(result) << "\n";
        return 2;
    }

    uint32_t physical_count = 0;
    result = vkEnumeratePhysicalDevices(instance, &physical_count, nullptr);
    if (result != VK_SUCCESS) {
        std::cerr << "vkEnumeratePhysicalDevices(count) failed: " << static_cast<int>(result) << "\n";
        vkDestroyInstance(instance, nullptr);
        return 2;
    }
    std::vector<VkPhysicalDevice> physical_devices(physical_count);
    if (physical_count != 0) {
        result = vkEnumeratePhysicalDevices(instance, &physical_count, physical_devices.data());
        if (result != VK_SUCCESS) {
            std::cerr << "vkEnumeratePhysicalDevices(list) failed: " << static_cast<int>(result) << "\n";
            vkDestroyInstance(instance, nullptr);
            return 2;
        }
        physical_devices.resize(physical_count);
    }

    size_t intel_count = 0;
    std::cout << "{\"query\":\"physical-device external host buffer capabilities only\",\"vk_instance_api\":\""
              << VK_VERSION_MAJOR(app.apiVersion) << '.' << VK_VERSION_MINOR(app.apiVersion)
              << "\",\"physical_device_count\":" << physical_devices.size() << ",\"devices\":[";

    for (size_t index = 0; index < physical_devices.size(); ++index) {
        VkPhysicalDevice physical = physical_devices[index];
        uint32_t extension_count = 0;
        result = vkEnumerateDeviceExtensionProperties(physical, nullptr, &extension_count, nullptr);
        if (result != VK_SUCCESS) {
            std::cerr << "vkEnumerateDeviceExtensionProperties(count) failed at index " << index << ": " << static_cast<int>(result) << "\n";
            vkDestroyInstance(instance, nullptr);
            return 2;
        }
        std::vector<VkExtensionProperties> extensions(extension_count);
        if (extension_count != 0) {
            result = vkEnumerateDeviceExtensionProperties(physical, nullptr, &extension_count, extensions.data());
            if (result != VK_SUCCESS) {
                std::cerr << "vkEnumerateDeviceExtensionProperties(list) failed at index " << index << ": " << static_cast<int>(result) << "\n";
                vkDestroyInstance(instance, nullptr);
                return 2;
            }
            extensions.resize(extension_count);
        }
        const bool host_ext = has_extension(extensions, VK_EXT_EXTERNAL_MEMORY_HOST_EXTENSION_NAME);

        VkPhysicalDeviceIDProperties id{};
        id.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES;
        VkPhysicalDeviceExternalMemoryHostPropertiesEXT host{};
        host.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTERNAL_MEMORY_HOST_PROPERTIES_EXT;
        id.pNext = host_ext ? &host : nullptr;
        VkPhysicalDeviceProperties2 props{};
        props.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2;
        props.pNext = &id;
        vkGetPhysicalDeviceProperties2(physical, &props);
        const auto &base = props.properties;
        if (base.vendorID == 0x8086) ++intel_count;

        if (index != 0) std::cout << ',';
        std::cout << "{\"index\":" << index
                  << ",\"name\":\"" << json_escape(base.deviceName)
                  << "\",\"vendor_id_hex\":\"0x" << std::hex << base.vendorID
                  << "\",\"device_id_hex\":\"0x" << base.deviceID << std::dec
                  << "\",\"vendor\":\"" << vendor_name(base.vendorID)
                  << "\",\"device_type\":\"" << device_type_name(base.deviceType)
                  << "\",\"api_version\":\"" << VK_VERSION_MAJOR(base.apiVersion) << '.' << VK_VERSION_MINOR(base.apiVersion)
                  << "\",\"device_uuid\":\"" << hex_bytes(id.deviceUUID, VK_UUID_SIZE)
                  << "\",\"driver_uuid\":\"" << hex_bytes(id.driverUUID, VK_UUID_SIZE)
                  << "\",\"vk_ext_external_memory_host\":" << (host_ext ? "true" : "false")
                  << ",\"min_imported_host_pointer_alignment\":";
        if (host_ext) std::cout << host.minImportedHostPointerAlignment;
        else std::cout << "null";
        std::cout << ",\"host_memory_queries\":[";

        if (host_ext && base.apiVersion >= VK_API_VERSION_1_1) {
            const VkBufferUsageFlags transfer = VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
            const VkBufferUsageFlags storage_transfer = transfer | VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
            bool first = true;
            print_buffer_query(physical, VK_EXTERNAL_MEMORY_HANDLE_TYPE_HOST_ALLOCATION_BIT_EXT, transfer,
                               "HOST_ALLOCATION", "TRANSFER_SRC|TRANSFER_DST", first); first = false;
            print_buffer_query(physical, VK_EXTERNAL_MEMORY_HANDLE_TYPE_HOST_ALLOCATION_BIT_EXT, storage_transfer,
                               "HOST_ALLOCATION", "STORAGE_BUFFER|TRANSFER_SRC|TRANSFER_DST", first); first = false;
            print_buffer_query(physical, VK_EXTERNAL_MEMORY_HANDLE_TYPE_HOST_MAPPED_FOREIGN_MEMORY_BIT_EXT, transfer,
                               "HOST_MAPPED_FOREIGN_MEMORY", "TRANSFER_SRC|TRANSFER_DST", first); first = false;
            print_buffer_query(physical, VK_EXTERNAL_MEMORY_HANDLE_TYPE_HOST_MAPPED_FOREIGN_MEMORY_BIT_EXT, storage_transfer,
                               "HOST_MAPPED_FOREIGN_MEMORY", "STORAGE_BUFFER|TRANSFER_SRC|TRANSFER_DST", first);
        } else {
            std::cout << "{\"status\":\"UNAVAILABLE\",\"reason\":\""
                      << (host_ext ? "PHYSICAL_DEVICE_API_BELOW_1_1" : "VK_EXT_external_memory_host_not_advertised")
                      << "\"}";
        }
        std::cout << "]}";
    }

    std::cout << "],\"intel_vendor_id_0x8086_devices_enumerated\":" << intel_count
              << ",\"intel_status\":\"" << (intel_count == 0 ? "NOT_ENUMERATED_BY_THIS_VULKAN_INSTANCE" : "ENUMERATED")
              << "\",\"safety_scope\":\"No VkDevice, buffer, memory allocation, import, semaphore, or GPU work was created. Capability bits do not establish cross-vendor direct GPU memory access, P2P, or VRAM residency.\"}\n";
    vkDestroyInstance(instance, nullptr);
    return 0;
}

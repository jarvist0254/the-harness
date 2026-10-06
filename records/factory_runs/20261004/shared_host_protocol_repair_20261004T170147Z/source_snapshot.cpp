// DESIGN-ONLY prototype. Do not compile or run before independent root review.
// The inter-instance alias/FOREIGN ownership correspondence is an explicit
// review gate; see contract.md.
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <vulkan/vulkan.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <functional>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr VkDeviceSize kPayloadBytes = 256u * 1024u;
constexpr VkDeviceSize kChunkBytes = 4096u;
constexpr uint32_t kChunkCount = static_cast<uint32_t>(kPayloadBytes / kChunkBytes);
constexpr uint64_t kFenceTimeoutNs = 5'000'000'000ull;
constexpr VkExternalMemoryHandleTypeFlagBits kHostHandle =
    VK_EXTERNAL_MEMORY_HANDLE_TYPE_HOST_ALLOCATION_BIT_EXT;
constexpr VkDeviceSize kReadbackBudget = 2u * 1024u * 1024u;

struct Failure : std::runtime_error {
    using std::runtime_error::runtime_error;
};

void check(VkResult result, const char* what) {
    if (result != VK_SUCCESS) {
        std::ostringstream message;
        message << what << " returned VkResult " << static_cast<int>(result);
        throw Failure(message.str());
    }
}

[[noreturn]] void terminateWithPendingWork(const char* why) {
    std::cerr << "{\"status\":\"FAIL\",\"reason\":\"" << why
              << "\",\"cleanup\":\"PROCESS_EXIT_WITHOUT_VULKAN_DESTRUCTORS\"}\n";
    // A submitted command may still refer to the imported host address. Avoid
    // C++ stack unwinding / VirtualFree while that work could still be active.
    ::ExitProcess(3);
}

std::string hexBytes(const uint8_t* bytes, size_t count) {
    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (size_t i = 0; i < count; ++i) out << std::setw(2) << unsigned(bytes[i]);
    return out.str();
}

bool hasExtension(VkPhysicalDevice physical, const char* wanted) {
    uint32_t count = 0;
    check(vkEnumerateDeviceExtensionProperties(physical, nullptr, &count, nullptr),
          "vkEnumerateDeviceExtensionProperties(count)");
    std::vector<VkExtensionProperties> props(count);
    check(vkEnumerateDeviceExtensionProperties(physical, nullptr, &count, props.data()),
          "vkEnumerateDeviceExtensionProperties(list)");
    return std::any_of(props.begin(), props.end(), [&](const auto& p) {
        return std::strcmp(p.extensionName, wanted) == 0;
    });
}

struct HostBlock {
    void* pointer = nullptr;
    HostBlock() {
        pointer = ::VirtualAlloc(nullptr, static_cast<SIZE_T>(kPayloadBytes),
                                 MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
        if (!pointer) throw Failure("VirtualAlloc(256 KiB) failed");
        std::memset(pointer, 0, static_cast<size_t>(kPayloadBytes));
    }
    ~HostBlock() {
        if (pointer) ::VirtualFree(pointer, 0, MEM_RELEASE);
    }
    HostBlock(const HostBlock&) = delete;
    HostBlock& operator=(const HostBlock&) = delete;
};

struct Context {
    const char* label = "";
    uint32_t requiredVendor = 0;
    VkInstance instance = VK_NULL_HANDLE;
    VkPhysicalDevice physical = VK_NULL_HANDLE;
    VkPhysicalDeviceProperties properties{};
    VkDevice device = VK_NULL_HANDLE;
    VkQueue queue = VK_NULL_HANDLE;
    uint32_t queueFamily = UINT32_MAX;
    VkCommandPool commandPool = VK_NULL_HANDLE;
    VkBuffer sharedBuffer = VK_NULL_HANDLE;
    VkDeviceMemory sharedMemory = VK_NULL_HANDLE;
    VkBuffer readbackBuffer = VK_NULL_HANDLE;
    VkDeviceMemory readbackMemory = VK_NULL_HANDLE;
    void* readbackMapped = nullptr;
    VkDeviceSize sharedRequirementBytes = 0;
    VkDeviceSize sharedRequirementAlignment = 0;
    VkDeviceSize readbackAllocationBytes = 0;
    VkDeviceSize minHostPointerAlignment = 0;
    uint32_t pointerMemoryTypeBits = 0;
    uint32_t bufferRequirementMemoryTypeBits = 0;
    uint32_t importedMemoryTypeIndex = UINT32_MAX;
    VkExternalMemoryFeatureFlags externalMemoryFeatures = 0;
    VkExternalMemoryHandleTypeFlags compatibleHandleTypes = 0;
    VkMemoryPropertyFlags importedTypeFlags = 0;
    VkMemoryPropertyFlags importedHeapFlags = 0;
    VkPhysicalDeviceIDProperties id{};
    PFN_vkGetMemoryHostPointerPropertiesEXT getHostPointerProperties = nullptr;
    bool hasUsedAlias = false;
    bool inForeignOwnership = false;

    ~Context() { destroyNormal(); }
    Context() = default;
    Context(const Context&) = delete;
    Context& operator=(const Context&) = delete;

    void destroyNormal() noexcept {
        if (device) {
            if (readbackMapped && readbackMemory) vkUnmapMemory(device, readbackMemory);
            if (readbackBuffer) vkDestroyBuffer(device, readbackBuffer, nullptr);
            if (sharedBuffer) vkDestroyBuffer(device, sharedBuffer, nullptr);
            if (readbackMemory) vkFreeMemory(device, readbackMemory, nullptr);
            if (sharedMemory) vkFreeMemory(device, sharedMemory, nullptr);
            if (commandPool) vkDestroyCommandPool(device, commandPool, nullptr);
            vkDestroyDevice(device, nullptr);
        }
        if (instance) vkDestroyInstance(instance, nullptr);
        readbackMapped = nullptr;
        readbackBuffer = sharedBuffer = VK_NULL_HANDLE;
        readbackMemory = sharedMemory = VK_NULL_HANDLE;
        commandPool = VK_NULL_HANDLE;
        device = VK_NULL_HANDLE;
        instance = VK_NULL_HANDLE;
    }

    void initialize(const char* name, uint32_t vendor, void* sharedHostPointer) {
        label = name;
        requiredVendor = vendor;

        VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
        app.pApplicationName = "bounded_shared_host_import_fixture";
        app.applicationVersion = 1;
        app.pEngineName = "none";
        app.engineVersion = 1;
        app.apiVersion = VK_API_VERSION_1_1;
        VkInstanceCreateInfo ici{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
        ici.pApplicationInfo = &app;
        check(vkCreateInstance(&ici, nullptr, &instance), "vkCreateInstance");

        uint32_t physicalCount = 0;
        check(vkEnumeratePhysicalDevices(instance, &physicalCount, nullptr),
              "vkEnumeratePhysicalDevices(count)");
        if (!physicalCount) throw Failure("no Vulkan physical devices enumerated");
        std::vector<VkPhysicalDevice> devices(physicalCount);
        check(vkEnumeratePhysicalDevices(instance, &physicalCount, devices.data()),
              "vkEnumeratePhysicalDevices(list)");
        std::vector<VkPhysicalDevice> vendorMatches;
        for (VkPhysicalDevice candidate : devices) {
            VkPhysicalDeviceProperties candidateProperties{};
            vkGetPhysicalDeviceProperties(candidate, &candidateProperties);
            if (candidateProperties.vendorID == requiredVendor) vendorMatches.push_back(candidate);
        }
        if (vendorMatches.size() != 1) {
            throw Failure(std::string(label) + " must enumerate exactly one requested vendor device");
        }
        physical = vendorMatches.front();
        vkGetPhysicalDeviceProperties(physical, &properties);

        if (!hasExtension(physical, VK_EXT_EXTERNAL_MEMORY_HOST_EXTENSION_NAME))
            throw Failure(std::string(label) + " lacks VK_EXT_external_memory_host");
        if (!hasExtension(physical, VK_EXT_QUEUE_FAMILY_FOREIGN_EXTENSION_NAME))
            throw Failure(std::string(label) + " lacks VK_EXT_queue_family_foreign");

        VkPhysicalDeviceExternalMemoryHostPropertiesEXT hostProperties{
            VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTERNAL_MEMORY_HOST_PROPERTIES_EXT};
        id = {VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES};
        hostProperties.pNext = nullptr;
        id.pNext = &hostProperties;
        VkPhysicalDeviceProperties2 properties2{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};
        properties2.pNext = &id;
        vkGetPhysicalDeviceProperties2(physical, &properties2);
        minHostPointerAlignment = hostProperties.minImportedHostPointerAlignment;
        if (!minHostPointerAlignment) throw Failure("zero minImportedHostPointerAlignment");

        VkPhysicalDeviceExternalBufferInfo extInfo{
            VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTERNAL_BUFFER_INFO};
        extInfo.flags = 0;
        extInfo.usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
        extInfo.handleType = kHostHandle;
        VkExternalBufferProperties extProps{VK_STRUCTURE_TYPE_EXTERNAL_BUFFER_PROPERTIES};
        vkGetPhysicalDeviceExternalBufferProperties(physical, &extInfo, &extProps);
        const auto& mp = extProps.externalMemoryProperties;
        externalMemoryFeatures = mp.externalMemoryFeatures;
        compatibleHandleTypes = mp.compatibleHandleTypes;
        if (!(mp.externalMemoryFeatures & VK_EXTERNAL_MEMORY_FEATURE_IMPORTABLE_BIT) ||
            !(mp.compatibleHandleTypes & kHostHandle)) {
            throw Failure(std::string(label) + " HOST_ALLOCATION transfer buffer is not importable");
        }
        if (mp.externalMemoryFeatures & VK_EXTERNAL_MEMORY_FEATURE_DEDICATED_ONLY_BIT) {
            throw Failure(std::string(label) + " HOST_ALLOCATION unexpectedly requires dedicated allocation");
        }

        uint32_t familyCount = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(physical, &familyCount, nullptr);
        std::vector<VkQueueFamilyProperties> families(familyCount);
        vkGetPhysicalDeviceQueueFamilyProperties(physical, &familyCount, families.data());
        for (uint32_t i = 0; i < familyCount; ++i) {
            if (families[i].queueCount && (families[i].queueFlags & VK_QUEUE_TRANSFER_BIT)) {
                queueFamily = i;
                break;
            }
        }
        if (queueFamily == UINT32_MAX) throw Failure(std::string(label) + " has no transfer queue");

        const float priority = 1.0f;
        VkDeviceQueueCreateInfo qci{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
        qci.queueFamilyIndex = queueFamily;
        qci.queueCount = 1;
        qci.pQueuePriorities = &priority;
        const std::array<const char*, 2> enabledExtensions = {
            VK_EXT_EXTERNAL_MEMORY_HOST_EXTENSION_NAME,
            VK_EXT_QUEUE_FAMILY_FOREIGN_EXTENSION_NAME};
        VkDeviceCreateInfo dci{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
        dci.queueCreateInfoCount = 1;
        dci.pQueueCreateInfos = &qci;
        dci.enabledExtensionCount = static_cast<uint32_t>(enabledExtensions.size());
        dci.ppEnabledExtensionNames = enabledExtensions.data();
        check(vkCreateDevice(physical, &dci, nullptr, &device), "vkCreateDevice");
        vkGetDeviceQueue(device, queueFamily, 0, &queue);
        if (!queue) throw Failure(std::string(label) + " returned a null transfer queue");
        getHostPointerProperties = reinterpret_cast<PFN_vkGetMemoryHostPointerPropertiesEXT>(
            vkGetDeviceProcAddr(device, "vkGetMemoryHostPointerPropertiesEXT"));
        if (!getHostPointerProperties) throw Failure("host pointer properties entry point absent");

        VkCommandPoolCreateInfo cpci{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
        cpci.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
        cpci.queueFamilyIndex = queueFamily;
        check(vkCreateCommandPool(device, &cpci, nullptr, &commandPool), "vkCreateCommandPool");

        VkExternalMemoryBufferCreateInfo externalBuffer{
            VK_STRUCTURE_TYPE_EXTERNAL_MEMORY_BUFFER_CREATE_INFO};
        externalBuffer.handleTypes = kHostHandle;
        VkBufferCreateInfo sharedInfo{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        sharedInfo.pNext = &externalBuffer;
        sharedInfo.size = kPayloadBytes;
        sharedInfo.usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
        sharedInfo.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
        check(vkCreateBuffer(device, &sharedInfo, nullptr, &sharedBuffer), "vkCreateBuffer(shared)");

        VkMemoryRequirements sharedReq{};
        vkGetBufferMemoryRequirements(device, sharedBuffer, &sharedReq);
        sharedRequirementBytes = sharedReq.size;
        sharedRequirementAlignment = sharedReq.alignment;
        bufferRequirementMemoryTypeBits = sharedReq.memoryTypeBits;
        if (!sharedReq.alignment) throw Failure("zero shared-buffer memory alignment");
        if (sharedReq.size > kPayloadBytes) throw Failure("shared buffer requirements exceed 256 KiB");
        const uintptr_t hostAddress = reinterpret_cast<uintptr_t>(sharedHostPointer);
        if ((hostAddress % minHostPointerAlignment) != 0 ||
            (hostAddress % sharedReq.alignment) != 0) {
            throw Failure(std::string(label) + " VirtualAlloc pointer fails host/resource alignment");
        }

        VkMemoryHostPointerPropertiesEXT pointerProps{
            VK_STRUCTURE_TYPE_MEMORY_HOST_POINTER_PROPERTIES_EXT};
        check(getHostPointerProperties(device, kHostHandle, sharedHostPointer, &pointerProps),
              "vkGetMemoryHostPointerPropertiesEXT");
        pointerMemoryTypeBits = pointerProps.memoryTypeBits;
        VkPhysicalDeviceMemoryProperties memoryProps{};
        vkGetPhysicalDeviceMemoryProperties(physical, &memoryProps);
        const uint32_t typeBits = sharedReq.memoryTypeBits & pointerProps.memoryTypeBits;
        uint32_t importType = UINT32_MAX;
        for (uint32_t i = 0; i < memoryProps.memoryTypeCount; ++i) {
            if ((typeBits & (1u << i)) &&
                (memoryProps.memoryTypes[i].propertyFlags &
                 (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) ==
                    (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) {
                importType = i;
                break;
            }
        }
        if (importType == UINT32_MAX) throw Failure(std::string(label) + " has no coherent host import type intersection");
        importedMemoryTypeIndex = importType;
        importedTypeFlags = memoryProps.memoryTypes[importType].propertyFlags;
        importedHeapFlags = memoryProps.memoryHeaps[memoryProps.memoryTypes[importType].heapIndex].flags;

        VkImportMemoryHostPointerInfoEXT hostImport{
            VK_STRUCTURE_TYPE_IMPORT_MEMORY_HOST_POINTER_INFO_EXT};
        hostImport.handleType = kHostHandle;
        hostImport.pHostPointer = sharedHostPointer;
        VkMemoryAllocateInfo mai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        mai.pNext = &hostImport;
        mai.allocationSize = kPayloadBytes;
        mai.memoryTypeIndex = importType;
        check(vkAllocateMemory(device, &mai, nullptr, &sharedMemory), "vkAllocateMemory(host import)");
        check(vkBindBufferMemory(device, sharedBuffer, sharedMemory, 0), "vkBindBufferMemory(shared)");

        VkBufferCreateInfo readInfo{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        readInfo.size = kPayloadBytes;
        readInfo.usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT;
        readInfo.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
        check(vkCreateBuffer(device, &readInfo, nullptr, &readbackBuffer), "vkCreateBuffer(readback)");
        VkMemoryRequirements readReq{};
        vkGetBufferMemoryRequirements(device, readbackBuffer, &readReq);
        uint32_t readType = UINT32_MAX;
        for (uint32_t i = 0; i < memoryProps.memoryTypeCount; ++i) {
            if ((readReq.memoryTypeBits & (1u << i)) &&
                (memoryProps.memoryTypes[i].propertyFlags &
                 (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) ==
                    (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) {
                readType = i;
                break;
            }
        }
        if (readType == UINT32_MAX) throw Failure(std::string(label) + " has no coherent private readback type");
        readbackAllocationBytes = readReq.size;
        VkMemoryAllocateInfo readAlloc{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        readAlloc.allocationSize = readReq.size;
        readAlloc.memoryTypeIndex = readType;
        check(vkAllocateMemory(device, &readAlloc, nullptr, &readbackMemory),
              "vkAllocateMemory(readback)");
        check(vkBindBufferMemory(device, readbackBuffer, readbackMemory, 0),
              "vkBindBufferMemory(readback)");
        check(vkMapMemory(device, readbackMemory, 0, VK_WHOLE_SIZE, 0, &readbackMapped),
              "vkMapMemory(readback)");
    }
};

void bufferBarrier(Context& c, VkCommandBuffer cmd, VkBuffer buffer,
                   uint32_t srcFamily, uint32_t dstFamily,
                   VkAccessFlags srcAccess, VkAccessFlags dstAccess,
                   VkPipelineStageFlags srcStage, VkPipelineStageFlags dstStage) {
    VkBufferMemoryBarrier barrier{VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER};
    barrier.srcAccessMask = srcAccess;
    barrier.dstAccessMask = dstAccess;
    barrier.srcQueueFamilyIndex = srcFamily;
    barrier.dstQueueFamilyIndex = dstFamily;
    barrier.buffer = buffer;
    barrier.offset = 0;
    barrier.size = kPayloadBytes;
    vkCmdPipelineBarrier(cmd, srcStage, dstStage, 0, 0, nullptr, 1, &barrier, 0, nullptr);
}

void submitAndWait(Context& c, const std::function<void(VkCommandBuffer)>& record,
                   const char* label) {
    VkCommandBufferAllocateInfo cai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
    cai.commandPool = c.commandPool;
    cai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    cai.commandBufferCount = 1;
    VkCommandBuffer cmd = VK_NULL_HANDLE;
    check(vkAllocateCommandBuffers(c.device, &cai, &cmd), "vkAllocateCommandBuffers");
    VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    check(vkBeginCommandBuffer(cmd, &begin), "vkBeginCommandBuffer");
    record(cmd);
    check(vkEndCommandBuffer(cmd), "vkEndCommandBuffer");

    VkFenceCreateInfo fci{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
    VkFence fence = VK_NULL_HANDLE;
    check(vkCreateFence(c.device, &fci, nullptr, &fence), "vkCreateFence");
    VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &cmd;
    const VkResult queued = vkQueueSubmit(c.queue, 1, &submit, fence);
    if (queued != VK_SUCCESS) terminateWithPendingWork("vkQueueSubmit failed; process teardown required");
    const VkResult waited = vkWaitForFences(c.device, 1, &fence, VK_TRUE, kFenceTimeoutNs);
    if (waited != VK_SUCCESS) terminateWithPendingWork("5-second CPU fence wait failed or timed out");
    vkDestroyFence(c.device, fence, nullptr);
    vkFreeCommandBuffers(c.device, c.commandPool, 1, &cmd);
    (void)label;
}

std::vector<uint8_t> expectedPattern(uint8_t seed) {
    std::vector<uint8_t> expected(static_cast<size_t>(kPayloadBytes));
    for (uint32_t chunk = 0; chunk < kChunkCount; ++chunk) {
        const uint8_t value = static_cast<uint8_t>(seed + chunk * 37u + (chunk >> 1));
        std::fill(expected.begin() + chunk * static_cast<size_t>(kChunkBytes),
                  expected.begin() + (chunk + 1) * static_cast<size_t>(kChunkBytes), value);
    }
    return expected;
}

struct RoundResult {
    std::string name;
    size_t bytesChecked = 0;
    size_t mismatchCount = 0;
    size_t firstMismatch = SIZE_MAX;
    uint8_t expectedAtMismatch = 0;
    uint8_t actualAtMismatch = 0;
    bool pass = false;
};

RoundResult runRound(Context& producer, Context& consumer, void* sharedHostPointer, uint8_t seed,
                     bool injectSingleByteCorruption, const char* name) {
    std::vector<uint8_t> expected = expectedPattern(seed);
    submitAndWait(producer, [&](VkCommandBuffer cmd) {
        if (producer.inForeignOwnership) {
            bufferBarrier(producer, cmd, producer.sharedBuffer, VK_QUEUE_FAMILY_FOREIGN_EXT,
                          producer.queueFamily, 0, VK_ACCESS_TRANSFER_WRITE_BIT,
                          VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);
            producer.inForeignOwnership = false;
        }
        for (uint32_t chunk = 0; chunk < kChunkCount; ++chunk) {
            const uint8_t byte = expected[chunk * static_cast<size_t>(kChunkBytes)];
            const uint32_t fill = uint32_t(byte) * 0x01010101u;
            vkCmdFillBuffer(cmd, producer.sharedBuffer,
                            VkDeviceSize(chunk) * kChunkBytes, kChunkBytes, fill);
        }
        bufferBarrier(producer, cmd, producer.sharedBuffer, producer.queueFamily,
                      VK_QUEUE_FAMILY_FOREIGN_EXT, VK_ACCESS_TRANSFER_WRITE_BIT, 0,
                      VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT);
    }, "producer");
    producer.hasUsedAlias = true;
    producer.inForeignOwnership = true;

    if (injectSingleByteCorruption) {
        auto* bytes = static_cast<uint8_t*>(sharedHostPointer);
        bytes[12345] ^= 0x01;
    }

    submitAndWait(consumer, [&](VkCommandBuffer cmd) {
        bufferBarrier(consumer, cmd, consumer.sharedBuffer, VK_QUEUE_FAMILY_FOREIGN_EXT,
                      consumer.queueFamily, 0, VK_ACCESS_TRANSFER_READ_BIT,
                      VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);
        VkBufferCopy copy{};
        copy.srcOffset = 0;
        copy.dstOffset = 0;
        copy.size = kPayloadBytes;
        vkCmdCopyBuffer(cmd, consumer.sharedBuffer, consumer.readbackBuffer, 1, &copy);
        bufferBarrier(consumer, cmd, consumer.readbackBuffer, consumer.queueFamily,
                      consumer.queueFamily, VK_ACCESS_TRANSFER_WRITE_BIT, VK_ACCESS_HOST_READ_BIT,
                      VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_HOST_BIT);
        bufferBarrier(consumer, cmd, consumer.sharedBuffer, consumer.queueFamily,
                      VK_QUEUE_FAMILY_FOREIGN_EXT, VK_ACCESS_TRANSFER_READ_BIT, 0,
                      VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT);
    }, "consumer");
    consumer.hasUsedAlias = true;
    consumer.inForeignOwnership = true;

    RoundResult result;
    result.name = name;
    result.bytesChecked = static_cast<size_t>(kPayloadBytes);
    const auto* actual = static_cast<const uint8_t*>(consumer.readbackMapped);
    for (size_t i = 0; i < expected.size(); ++i) {
        if (actual[i] != expected[i]) {
            if (result.mismatchCount == 0) {
                result.firstMismatch = i;
                result.expectedAtMismatch = expected[i];
                result.actualAtMismatch = actual[i];
            }
            ++result.mismatchCount;
        }
    }
    result.pass = injectSingleByteCorruption
        ? (result.mismatchCount == 1 && result.firstMismatch == 12345 &&
           result.actualAtMismatch == static_cast<uint8_t>(result.expectedAtMismatch ^ 0x01))
        : (result.mismatchCount == 0);
    return result;
}

void printRound(const RoundResult& r) {
    std::cout << "{\"round\":\"" << r.name << "\",\"bytes_checked\":" << r.bytesChecked
              << ",\"mismatch_count\":" << r.mismatchCount << ",\"first_mismatch_offset\":";
    if (r.firstMismatch == SIZE_MAX) std::cout << "null";
    else std::cout << r.firstMismatch;
    std::cout << ",\"expected_byte_hex\":\"" << std::hex << std::setw(2) << std::setfill('0')
              << unsigned(r.expectedAtMismatch) << "\",\"actual_byte_hex\":\""
              << std::setw(2) << unsigned(r.actualAtMismatch) << std::dec
              << "\",\"pass\":" << (r.pass ? "true" : "false") << "}\n";
}

void printDevice(const Context& c) {
    std::cout << "{\"device\":\"" << c.label << "\",\"name\":\"" << c.properties.deviceName
              << "\",\"vendor_id_hex\":\"0x" << std::hex << c.properties.vendorID
              << "\",\"device_id_hex\":\"0x" << c.properties.deviceID
              << "\",\"device_uuid\":\"" << hexBytes(c.id.deviceUUID, VK_UUID_SIZE)
              << "\",\"driver_uuid\":\"" << hexBytes(c.id.driverUUID, VK_UUID_SIZE)
              << "\",\"queue_family\":" << std::dec << c.queueFamily
              << ",\"foreign_extension_enabled\":true,\"host_import_extension_enabled\":true"
              << ",\"external_memory_features_hex\":\"0x" << std::hex << c.externalMemoryFeatures
              << "\",\"compatible_handle_types_hex\":\"0x" << c.compatibleHandleTypes
              << "\",\"min_host_pointer_alignment\":" << std::dec << c.minHostPointerAlignment
              << ",\"buffer_requirement_alignment\":" << c.sharedRequirementAlignment
              << ",\"buffer_requirement_size\":" << c.sharedRequirementBytes
              << ",\"buffer_requirement_type_bits_hex\":\"0x" << std::hex
              << c.bufferRequirementMemoryTypeBits << "\",\"pointer_type_bits_hex\":\"0x"
              << c.pointerMemoryTypeBits << "\",\"selected_type_index\":" << std::dec
              << c.importedMemoryTypeIndex << ",\"selected_type_flags_hex\":\"0x" << std::hex
              << c.importedTypeFlags << "\",\"selected_heap_flags_hex\":\"0x"
              << c.importedHeapFlags << "\"}\n";
}

}  // namespace

int main() {
    try {
        HostBlock host;
        Context nvidia;
        Context amd;
        nvidia.initialize("NVIDIA", 0x10de, host.pointer);
        amd.initialize("AMD", 0x1002, host.pointer);
        if (std::memcmp(nvidia.id.deviceUUID, amd.id.deviceUUID, VK_UUID_SIZE) == 0)
            throw Failure("selected NVIDIA and AMD deviceUUID values are not distinct");
        const VkDeviceSize readbackTotal = nvidia.readbackAllocationBytes + amd.readbackAllocationBytes;
        if (readbackTotal > kReadbackBudget) throw Failure("private readback allocation budget exceeded");
        printDevice(nvidia);
        printDevice(amd);

        RoundResult nvToAmd = runRound(nvidia, amd, host.pointer, 0x19, false, "NVIDIA_TO_AMD");
        printRound(nvToAmd);
        RoundResult amdToNv = runRound(amd, nvidia, host.pointer, 0x53, false, "AMD_TO_NVIDIA");
        printRound(amdToNv);
        RoundResult corrupt = runRound(nvidia, amd, host.pointer, 0x87, true,
                                       "NVIDIA_TO_AMD_CORRUPTION_CONTROL");
        printRound(corrupt);

        const bool pass = nvToAmd.pass && amdToNv.pass && corrupt.pass;
        std::cout << "{\"status\":\"" << (pass ? "PASS" : "FAIL")
                  << "\",\"transport\":\"SHARED_HOST_BACKING_NOT_VRAM_P2P\"
                  << ",\"sync\":\"CPU_FENCE_CONTROL_NO_CPU_PAYLOAD_TRANSFER\"
                  << ",\"payload_bytes\":" << kPayloadBytes
                  << ",\"private_readback_allocation_bytes\":" << readbackTotal
                  << ",\"p2p_claim\":false,\"vram_residency_claim\":false}\n";
        return pass ? 0 : 1;
    } catch (const std::exception& e) {
        std::cerr << "{\"status\":\"NOT_CHECKED\",\"reason\":\"" << e.what()
                  << "\",\"transport\":\"SHARED_HOST_BACKING_NOT_VRAM_P2P\"}\n";
        return 2;
    }
}

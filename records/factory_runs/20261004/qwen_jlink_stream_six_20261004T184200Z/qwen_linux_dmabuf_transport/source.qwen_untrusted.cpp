#include <vulkan/vulkan.h>
#include <iostream>
#include <vector>
#include <cstring>
#include <cstdint>
#define STR(x) #x
void print_escaped(const char* s) {
  if (!s) return;
  const unsigned char* p = reinterpret_cast<const unsigned char*>(s);
  while (*p) {
    unsigned char c = *p++;
    if (c == 34 || c == 92) {
      std::cout << char(92) << char(c);
    } else if (c < 32) {
      std::cout << char(32);
    } else {
      std::cout << char(c);
    }
  }
}
void sep(bool& first) {
  if (!first) std::cout << ',';
  first = false;
}
void key(bool& first, const char* s) {
  sep(first);
  std::cout << char(34) << s << char(34) << ':';
  first = false;
}
void str_val(const char* s) {
  std::cout << char(34);
  print_escaped(s);
  std::cout << char(34);
}
void bool_val(bool b) {
  std::cout << (b ? STR(true) : STR(false));
}
void num_val(uint64_t v) {
  std::cout << v;
}
bool has_ext(const std::vector<VkExtensionProperties>& exts, const char* name) {
  for (size_t i = 0; i < exts.size(); ++i) {
    if (std::strcmp(exts[i].extensionName, name) == 0) return true;
  }
  return false;
}
#if defined(VK_VERSION_1_1)
void external_buffer_caps(VkPhysicalDevice pd, VkExternalMemoryHandleTypeFlagBits ht, const char* ht_name) {
  VkPhysicalDeviceExternalBufferInfo info{};
  info.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTERNAL_BUFFER_INFO;
  info.handleType = ht;
  VkExternalBufferProperties props{};
  props.sType = VK_STRUCTURE_TYPE_EXTERNAL_BUFFER_PROPERTIES;
  vkGetPhysicalDeviceExternalBufferProperties(pd, &info, &props);
  bool dedicated_only = (props.externalMemoryFeatures & VK_EXTERNAL_MEMORY_FEATURE_DEDICATED_ONLY_BIT) != 0;
  bool exportable = (props.externalMemoryFeatures & VK_EXTERNAL_MEMORY_FEATURE_EXPORTABLE_BIT) != 0;
  bool importable = (props.externalMemoryFeatures & VK_EXTERNAL_MEMORY_FEATURE_IMPORTABLE_BIT) != 0;
  bool first = true;
  key(first, STR(handle_type)); str_val(ht_name);
  key(first, STR(external_memory_features)); num_val(static_cast<uint64_t>(props.externalMemoryFeatures));
  key(first, STR(dedicated_only)); bool_val(dedicated_only);
  key(first, STR(exportable)); bool_val(exportable);
  key(first, STR(importable)); bool_val(importable);
  key(first, STR(export_from_imported_handle_types)); num_val(static_cast<uint64_t>(props.exportFromImportedHandleTypes));
  key(first, STR(compatible_handle_types)); num_val(static_cast<uint64_t>(props.compatibleHandleTypes));
}
void external_semaphore_caps(VkPhysicalDevice pd, VkExternalSemaphoreHandleTypeFlagBits ht, const char* ht_name) {
  VkPhysicalDeviceExternalSemaphoreInfo info{};
  info.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTERNAL_SEMAPHORE_INFO;
  info.handleType = ht;
  VkExternalSemaphoreProperties props{};
  props.sType = VK_STRUCTURE_TYPE_EXTERNAL_SEMAPHORE_PROPERTIES;
  vkGetPhysicalDeviceExternalSemaphoreProperties(pd, &info, &props);
  bool exportable = (props.externalSemaphoreFeatures & VK_EXTERNAL_SEMAPHORE_FEATURE_EXPORTABLE_BIT) != 0;
  bool importable = (props.externalSemaphoreFeatures & VK_EXTERNAL_SEMAPHORE_FEATURE_IMPORTABLE_BIT) != 0;
  bool first = true;
  key(first, STR(handle_type)); str_val(ht_name);
  key(first, STR(external_semaphore_features)); num_val(static_cast<uint64_t>(props.externalSemaphoreFeatures));
  key(first, STR(exportable)); bool_val(exportable);
  key(first, STR(importable)); bool_val(importable);
  key(first, STR(export_from_imported_handle_types)); num_val(static_cast<uint64_t>(props.exportFromImportedHandleTypes));
  key(first, STR(compatible_handle_types)); num_val(static_cast<uint64_t>(props.compatibleHandleTypes));
}
void external_fence_caps(VkPhysicalDevice pd, VkExternalFenceHandleTypeFlagBits ht, const char* ht_name) {
  VkPhysicalDeviceExternalFenceInfo info{};
  info.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTERNAL_FENCE_INFO;
  info.handleType = ht;
  VkExternalFenceProperties props{};
  props.sType = VK_STRUCTURE_TYPE_EXTERNAL_FENCE_PROPERTIES;
  vkGetPhysicalDeviceExternalFenceProperties(pd, &info, &props);
  bool exportable = (props.externalFenceFeatures & VK_EXTERNAL_FENCE_FEATURE_EXPORTABLE_BIT) != 0;
  bool importable = (props.externalFenceFeatures & VK_EXTERNAL_FENCE_FEATURE_IMPORTABLE_BIT) != 0;
  bool first = true;
  key(first, STR(handle_type)); str_val(ht_name);
  key(first, STR(external_fence_features)); num_val(static_cast<uint64_t>(props.externalFenceFeatures));
  key(first, STR(exportable)); bool_val(exportable);
  key(first, STR(importable)); bool_val(importable);
  key(first, STR(export_from_imported_handle_types)); num_val(static_cast<uint64_t>(props.exportFromImportedHandleTypes));
  key(first, STR(compatible_handle_types)); num_val(static_cast<uint64_t>(props.compatibleHandleTypes));
}
#endif
int main() {
  VkApplicationInfo app{};
  app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
  app.pApplicationName = nullptr;
  app.pEngineName = nullptr;
  app.apiVersion = VK_API_VERSION_1_1;
  VkInstanceCreateInfo ici{};
  ici.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
  ici.pApplicationInfo = &app;
  VkInstance instance = VK_NULL_HANDLE;
  VkResult res = vkCreateInstance(&ici, nullptr, &instance);
  bool root_first = true;
  std::cout << '{';
  key(root_first, STR(schema_version)); num_val(1);
  key(root_first, STR(status)); str_val(STR(UNPROVEN));
  key(root_first, STR(actual_gpu_qualification)); bool_val(false);
  key(root_first, STR(mock_contract_validator_pass)); bool_val(false);
  key(root_first, STR(import_copy_path_disabled)); bool_val(true);
  key(root_first, STR(legal_cross_vendor_dma_buf_p2p)); str_val(STR(UNPROVEN));
  key(root_first, STR(host_memory_as_vram_p2p)); str_val(STR(REFUSED));
  key(root_first, STR(benchmark_claims)); str_val(STR(NONE));
  key(root_first, STR(price_claims)); str_val(STR(NONE));
  key(root_first, STR(generated_by)); str_val(STR(vulkan_capability_query));
  if (res != VK_SUCCESS) {
    key(root_first, STR(vulkan_status)); str_val(STR(INSTANCE_UNAVAILABLE));
    key(root_first, STR(devices)); std::cout << '[' << ']';
    std::cout << '}' << char(10);
    return 0;
  }
  key(root_first, STR(vulkan_status)); str_val(STR(OK));
  uint32_t gpu_count = 0;
  res = vkEnumeratePhysicalDevices(instance, &gpu_count, nullptr);
  if (res != VK_SUCCESS) {
    key(root_first, STR(device_enumeration)); str_val(STR(FAILED));
    key(root_first, STR(devices)); std::cout << '[' << ']';
    std::cout << '}' << char(10);
    vkDestroyInstance(instance, nullptr);
    return 0;
  }
  std::vector<VkPhysicalDevice> gpus(gpu_count);
  if (gpu_count > 0) {
    res = vkEnumeratePhysicalDevices(instance, &gpu_count, gpus.data());
    if (res != VK_SUCCESS) gpu_count = 0;
  }
  key(root_first, STR(devices)); std::cout << '[';
  for (uint32_t gi = 0; gi < gpu_count; ++gi) {
    if (gi) std::cout << ',';
    VkPhysicalDevice pd = gpus[gi];
    std::vector<VkExtensionProperties> exts;
    uint32_t ext_count = 0;
    if (vkEnumerateDeviceExtensionProperties(pd, nullptr, &ext_count, nullptr) == VK_SUCCESS && ext_count > 0) {
      exts.resize(ext_count);
      if (vkEnumerateDeviceExtensionProperties(pd, nullptr, &ext_count, exts.data()) != VK_SUCCESS) exts.clear();
    }
    VkPhysicalDeviceProperties prop;
    vkGetPhysicalDeviceProperties(pd, &prop);
    bool dfirst = true;
    std::cout << '{';
    key(dfirst, STR(index)); num_val(gi);
    key(dfirst, STR(device_name)); str_val(prop.deviceName);
    key(dfirst, STR(api_version)); num_val(prop.apiVersion);
    key(dfirst, STR(driver_version)); num_val(prop.driverVersion);
    key(dfirst, STR(vendor_id)); num_val(prop.vendorID);
    key(dfirst, STR(device_id)); num_val(prop.deviceID);
    key(dfirst, STR(device_type)); num_val(prop.deviceType);
    key(dfirst, STR(device_type_name));
    switch (prop.deviceType) {
      case VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU: str_val(STR(INTEGRATED_GPU)); break;
      case VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU: str_val(STR(DISCRETE_GPU)); break;
      case VK_PHYSICAL_DEVICE_TYPE_VIRTUAL_GPU: str_val(STR(VIRTUAL_GPU)); break;
      case VK_PHYSICAL_DEVICE_TYPE_CPU: str_val(STR(CPU)); break;
      default: str_val(STR(OTHER)); break;
    }
#if defined(VK_VERSION_1_1)
    VkPhysicalDeviceIDProperties id_props{};
    id_props.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES;
    VkPhysicalDeviceProperties2 prop2{};
    prop2.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2;
#if defined(VK_EXT_pci_bus_info)
    VkPhysicalDevicePCIBusInfoPropertiesEXT pci_props{};
    bool have_pci = has_ext(exts, VK_EXT_PCI_BUS_INFO_EXTENSION_NAME);
    if (have_pci) {
      pci_props.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PCI_BUS_INFO_PROPERTIES_EXT;
      id_props.pNext = &pci_props;
    }
#endif
    prop2.pNext = &id_props;
    vkGetPhysicalDeviceProperties2(pd, &prop2);
    key(dfirst, STR(device_uuid)); std::cout << '[';
    for (uint32_t u = 0; u < VK_UUID_SIZE; ++u) {
      if (u) std::cout << ',';
      num_val(id_props.deviceUUID[u]);
    }
    std::cout << ']';
    key(dfirst, STR(device_luid)); std::cout << '[';
    for (uint32_t u = 0; u < VK_LUID_SIZE; ++u) {
      if (u) std::cout << ',';
      num_val(id_props.deviceLUID[u]);
    }
    std::cout << ']';
    key(dfirst, STR(luid_valid)); bool_val(id_props.luidValid != 0);
    key(dfirst, STR(device_node_mask)); num_val(id_props.deviceNodeMask);
#if defined(VK_EXT_pci_bus_info)
    if (have_pci) {
      key(dfirst, STR(pci_domain)); num_val(pci_props.pciDomain);
      key(dfirst, STR(pci_bus)); num_val(pci_props.pciBus);
      key(dfirst, STR(pci_device)); num_val(pci_props.pciDevice);
      key(dfirst, STR(pci_function)); num_val(pci_props.pciFunction);
    }
#endif
#endif
    key(dfirst, STR(device_extensions)); std::cout << '[';
    for (size_t ei = 0; ei < exts.size(); ++ei) {
      if (ei) std::cout << ',';
      std::cout << '{';
      bool efirst = true;
      key(efirst, STR(name)); str_val(exts[ei].extensionName);
      key(efirst, STR(spec_version)); num_val(exts[ei].specVersion);
      std::cout << '}';
    }
    std::cout << ']';
    VkPhysicalDeviceMemoryProperties mem_props;
    vkGetPhysicalDeviceMemoryProperties(pd, &mem_props);
    key(dfirst, STR(memory_heaps)); std::cout << '[';
    for (uint32_t hi = 0; hi < mem_props.memoryHeapCount; ++hi) {
      if (hi) std::cout << ',';
      std::cout << '{';
      bool hfirst = true;
      key(hfirst, STR(index)); num_val(hi);
      key(hfirst, STR(size)); num_val(mem_props.memoryHeaps[hi].size);
      key(hfirst, STR(flags)); num_val(mem_props.memoryHeaps[hi].flags);
      key(hfirst, STR(device_local)); bool_val((mem_props.memoryHeaps[hi].flags & VK_MEMORY_HEAP_DEVICE_LOCAL_BIT) != 0);
      std::cout << '}';
    }
    std::cout << ']';
    key(dfirst, STR(memory_types)); std::cout << '[';
    for (uint32_t ti = 0; ti < mem_props.memoryTypeCount; ++ti) {
      if (ti) std::cout << ',';
      std::cout << '{';
      bool tfirst = true;
      VkMemoryPropertyFlags f = mem_props.memoryTypes[ti].propertyFlags;
      key(tfirst, STR(index)); num_val(ti);
      key(tfirst, STR(heap_index)); num_val(mem_props.memoryTypes[ti].heapIndex);
      key(tfirst, STR(flags)); num_val(f);
      key(tfirst, STR(device_local)); bool_val((f & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT) != 0);
      key(tfirst, STR(host_visible)); bool_val((f & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) != 0);
      key(tfirst, STR(host_coherent)); bool_val((f & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) != 0);
      key(tfirst, STR(host_cached)); bool_val((f & VK_MEMORY_PROPERTY_HOST_CACHED_BIT) != 0);
      key(tfirst, STR(lazily_allocated)); bool_val((f & VK_MEMORY_PROPERTY_LAZILY_ALLOCATED_BIT) != 0);
      key(tfirst, STR(protected_memory)); bool_val((f & VK_MEMORY_PROPERTY_PROTECTED_BIT) != 0);
      std::cout << '}';
    }
    std::cout << ']';
#if defined(VK_VERSION_1_1)
    key(dfirst, STR(external_buffer_capabilities)); std::cout << '[';
    bool bfirst = true;
    sep(bfirst); std::cout << '{'; external_buffer_caps(pd, VK_EXTERNAL_MEMORY_HANDLE_TYPE_OPAQUE_FD_BIT, STR(OPAQUE_FD)); std::cout << '}';
#if defined(VK_EXT_external_memory_dma_buf)
    if (has_ext(exts, VK_EXT_EXTERNAL_MEMORY_DMA_BUF_EXTENSION_NAME)) {
      sep(bfirst); std::cout << '{'; external_buffer_caps(pd, VK_EXTERNAL_MEMORY_HANDLE_TYPE_DMA_BUF_BIT_EXT, STR(DMA_BUF_EXT)); std::cout << '}';
    }
#endif
    std::cout << ']';
    key(dfirst, STR(external_semaphore_capabilities)); std::cout << '[';
    bool sfirst = true;
    sep(sfirst); std::cout << '{'; external_semaphore_caps(pd, VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_OPAQUE_FD_BIT, STR(OPAQUE_FD)); std::cout << '}';
    sep(sfirst); std::cout << '{'; external_semaphore_caps(pd, VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT, STR(SYNC_FD)); std::cout << '}';
    std::cout << ']';
    key(dfirst, STR(external_fence_capabilities)); std::cout << '[';
    bool ffirst = true;
    sep(ffirst); std::cout << '{'; external_fence_caps(pd, VK_EXTERNAL_FENCE_HANDLE_TYPE_OPAQUE_FD_BIT, STR(OPAQUE_FD)); std::cout << '}';
    sep(ffirst); std::cout << '{'; external_fence_caps(pd, VK_EXTERNAL_FENCE_HANDLE_TYPE_SYNC_FD_BIT, STR(SYNC_FD)); std::cout << '}';
    std::cout << ']';
#endif
    key(dfirst, STR(import_copy_path_disabled)); bool_val(true);
    key(dfirst, STR(claims)); std::cout << '{';
    bool cfirst = true;
    key(cfirst, STR(dedicated_vram_p2p)); str_val(STR(UNPROVEN));
    key(cfirst, STR(cross_vendor_dma_buf_import)); str_val(STR(UNPROVEN));
    key(cfirst, STR(host_staged_activation)); str_val(STR(UNPROVEN));
    key(cfirst, STR(same_vendor_peer)); str_val(STR(UNPROVEN));
    key(cfirst, STR(rpc_loopback)); str_val(STR(UNPROVEN));
    key(cfirst, STR(d3d_cross_adapter_system_memory)); str_val(STR(NOT_APPLICABLE_LINUX));
    key(cfirst, STR(external_host_unresolved_views)); str_val(STR(UNPROVEN));
    std::cout << '}';
    std::cout << '}';
  }
  std::cout << ']';
  std::cout << '}' << char(10);
  vkDestroyInstance(instance, nullptr);
  return 0;
}

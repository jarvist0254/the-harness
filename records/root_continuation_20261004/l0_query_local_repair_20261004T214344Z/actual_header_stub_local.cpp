// SOURCE ONLY. Not compiled, linked or executed. Await Root admission.
// The official header's supported ZE_APIEXPORT override only suppresses DLL
// export decoration; all enum values, structs, types and signatures are real.
#define ZE_APIEXPORT
#define LZQ_TEST_NO_MAIN 1
#include "source.local_derivative.cpp"

static int scenario = 0; // 0 two roots; 1 init failure; 2 duplicate root handle
static unsigned external_queries = 0;
static unsigned peer_queries = 0;
static unsigned property_queries = 0;
static ze_driver_handle_t driver() { return reinterpret_cast<ze_driver_handle_t>(uintptr_t(0x100)); }
static ze_device_handle_t device(unsigned i) { return reinterpret_cast<ze_device_handle_t>(uintptr_t(0x200 + i)); }
static bool known(ze_device_handle_t h) { return h == device(0) || h == device(1); }

extern "C" ze_result_t ZE_APICALL zeInit(ze_init_flags_t flags) {
    if (flags != ZE_INIT_FLAG_GPU_ONLY) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    return scenario == 1 ? ZE_RESULT_ERROR_DEVICE_LOST : ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDriverGet(uint32_t* count, ze_driver_handle_t* handles) {
    if (!count) return ZE_RESULT_ERROR_INVALID_NULL_POINTER;
    if (!handles) { *count = 1; return ZE_RESULT_SUCCESS; }
    if (*count) { handles[0] = driver(); *count = 1; }
    return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGet(ze_driver_handle_t h, uint32_t* count, ze_device_handle_t* handles) {
    if (h != driver()) return ZE_RESULT_ERROR_INVALID_NULL_HANDLE;
    if (!count) return ZE_RESULT_ERROR_INVALID_NULL_POINTER;
    const uint32_t available = scenario == 2 ? 3 : 2;
    if (!handles) { *count = available; return ZE_RESULT_SUCCESS; }
    const uint32_t take = *count < available ? *count : available;
    for (uint32_t i = 0; i < take; ++i) handles[i] = scenario == 2 && i < 2 ? device(0) : device(i ? 1 : 0);
    *count = take; return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGetSubDevices(ze_device_handle_t h, uint32_t* count, ze_device_handle_t*) {
    if (!known(h)) return ZE_RESULT_ERROR_INVALID_NULL_HANDLE;
    if (!count) return ZE_RESULT_ERROR_INVALID_NULL_POINTER;
    *count = 0; return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGetProperties(ze_device_handle_t h, ze_device_properties_t* p) {
    if (!known(h)) return ZE_RESULT_ERROR_INVALID_NULL_HANDLE;
    if (!p || p->stype != ZE_STRUCTURE_TYPE_DEVICE_PROPERTIES || p->pNext) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    const unsigned i = h == device(0) ? 0 : 1;
    p->type = ZE_DEVICE_TYPE_GPU; p->vendorId = 0x8086; p->deviceId = 0x1234 + i;
    p->subdeviceId = 0;
    for (unsigned j = 0; j < 16; ++j) p->uuid.id[j] = uint8_t(16*i+j);
    std::strcpy(p->name, i ? "SYNTHETIC Intel root1" : "SYNTHETIC Intel root0");
    ++property_queries; return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGetCommandQueueGroupProperties(ze_device_handle_t h, uint32_t* count, ze_command_queue_group_properties_t* p) {
    if (!known(h)) return ZE_RESULT_ERROR_INVALID_NULL_HANDLE;
    if (!count) return ZE_RESULT_ERROR_INVALID_NULL_POINTER;
    if (!p) { *count = 1; return ZE_RESULT_SUCCESS; }
    if (*count) {
        if (p[0].stype != ZE_STRUCTURE_TYPE_COMMAND_QUEUE_GROUP_PROPERTIES || p[0].pNext) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
        p[0].flags = ZE_COMMAND_QUEUE_GROUP_PROPERTY_FLAG_COMPUTE; p[0].numQueues = 1; *count = 1;
    }
    return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGetExternalMemoryProperties(ze_device_handle_t h, ze_device_external_memory_properties_t* p) {
    ++external_queries;
    if (!known(h)) return ZE_RESULT_ERROR_INVALID_NULL_HANDLE;
    if (!p || p->stype != ZE_STRUCTURE_TYPE_DEVICE_EXTERNAL_MEMORY_PROPERTIES || p->pNext) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    p->memoryAllocationImportTypes = ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF;
    p->memoryAllocationExportTypes = ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF;
    return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceCanAccessPeer(ze_device_handle_t src, ze_device_handle_t dst, ze_bool_t* out) {
    if (!known(src) || !known(dst)) return ZE_RESULT_ERROR_INVALID_NULL_HANDLE;
    if (!out) return ZE_RESULT_ERROR_INVALID_NULL_POINTER;
    *out = src == device(0) && dst == device(1); ++peer_queries; return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGetP2PProperties(ze_device_handle_t src, ze_device_handle_t dst, ze_device_p2p_properties_t* p) {
    if (!known(src) || !known(dst)) return ZE_RESULT_ERROR_INVALID_NULL_HANDLE;
    if (!p || p->stype != ZE_STRUCTURE_TYPE_DEVICE_P2P_PROPERTIES || p->pNext) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    p->flags = src == device(0) && dst == device(1) ? ZE_DEVICE_P2P_PROPERTY_FLAG_ACCESS : 0;
    return ZE_RESULT_SUCCESS;
}
int main(int argc, char** argv) {
    if (argc == 2 && std::strcmp(argv[1], "init_error") == 0) scenario = 1;
    else if (argc == 2 && std::strcmp(argv[1], "duplicate_root") == 0) scenario = 2;
    else if (argc != 1) return 2;
    static char output[LZQ_OUT_BYTES];
    const size_t bytes = lzq_collect(output, sizeof(output));
    std::fwrite(output, 1, bytes, stdout); std::fputc('\n', stdout);
    std::fprintf(stderr, "{\"scope\":\"ACTUAL_HEADER_LOCAL_CPU_STUB_NOT_HARDWARE\",\"external_queries\":%u,\"peer_queries\":%u,\"property_queries\":%u,\"candidate_exit\":%d}\n", external_queries, peer_queries, property_queries, lzq_exit);
    return lzq_exit;
}

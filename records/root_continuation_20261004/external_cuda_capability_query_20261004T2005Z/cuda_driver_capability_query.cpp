// Source-only CUDA Driver capability inventory.
// Deliberately does not create a CUDA context, allocate memory, export/import
// handles, enqueue work, or claim that queried features prove P2P transport.
#include <cuda.h>
#include <cudaTypedefs.h>
#include <dlfcn.h>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace {
constexpr int kDeviceLimit = 32;
constexpr const char *kLibrary = "/usr/lib/wsl/lib/libcuda.so.1";
struct Error { std::string api; int code; };

std::string json_string(const std::string &s) {
    std::ostringstream o;
    o << '"';
    for (unsigned char c : s) {
        switch (c) {
        case '"': o << "\\\""; break;
        case '\\': o << "\\\\"; break;
        case '\b': o << "\\b"; break;
        case '\f': o << "\\f"; break;
        case '\n': o << "\\n"; break;
        case '\r': o << "\\r"; break;
        case '\t': o << "\\t"; break;
        default:
            if (c < 0x20 || c >= 0x80) {
                o << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                  << static_cast<unsigned int>(c) << std::dec;
            } else {
                o << static_cast<char>(c);
            }
        }
    }
    o << '"';
    return o.str();
}

template <typename T>
T resolve(void *library, const char *name) {
    void *raw = dlsym(library, name);
    T fn = nullptr;
    static_assert(sizeof(fn) == sizeof(raw), "POSIX function/data pointer size mismatch");
    std::memcpy(&fn, &raw, sizeof(fn));
    return fn;
}

struct IntCall { int result; int value; };
IntCall query_attribute(PFN_cuDeviceGetAttribute_v2000 fn, CUdevice dev,
                        CUdevice_attribute attribute, const char *api,
                        std::vector<Error> &errors) {
    int value = 0;
    const CUresult rc = fn(&value, attribute, dev);
    if (rc != CUDA_SUCCESS) errors.push_back({api, static_cast<int>(rc)});
    return {static_cast<int>(rc), value};
}

void print_errors(const std::vector<Error> &errors) {
    std::printf("\"errors\":[");
    for (size_t i = 0; i < errors.size(); ++i) {
        if (i) std::printf(",");
        std::printf("{\"api\":%s,\"result\":%d}",
                    json_string(errors[i].api).c_str(), errors[i].code);
    }
    std::printf("]");
}

void print_not_checked(const char *reason, const char *symbol = nullptr) {
    std::printf("{\"schema\":\"cuda-driver-capability-query-v1\","
                "\"scope\":\"CUDA_DRIVER_DEVICE_ATTRIBUTE_QUERY_ONLY\","
                "\"status\":\"NOT_CHECKED\",\"p2p_claim\":\"UNPROVEN\","
                "\"reason\":%s,\"missing_symbol\":",
                json_string(reason).c_str());
    if (symbol) std::printf("%s", json_string(symbol).c_str());
    else std::printf("null");
    std::printf("}\n");
}
} // namespace

int main() {
    void *library = dlopen(kLibrary, RTLD_NOW | RTLD_LOCAL);
    if (!library) {
        print_not_checked("PINNED_DRIVER_LIBRARY_UNAVAILABLE");
        return 2;
    }

    const auto init = resolve<PFN_cuInit_v2000>(library, "cuInit");
    const auto get_driver_version = resolve<PFN_cuDriverGetVersion_v2020>(library, "cuDriverGetVersion");
    const auto get_count = resolve<PFN_cuDeviceGetCount_v2000>(library, "cuDeviceGetCount");
    const auto get_device = resolve<PFN_cuDeviceGet_v2000>(library, "cuDeviceGet");
    const auto get_name = resolve<PFN_cuDeviceGetName_v2000>(library, "cuDeviceGetName");
    const auto get_uuid = resolve<PFN_cuDeviceGetUuid_v11040>(library, "cuDeviceGetUuid_v2");
    const auto get_attribute = resolve<PFN_cuDeviceGetAttribute_v2000>(library, "cuDeviceGetAttribute");
    const char *required_names[] = {"cuInit", "cuDriverGetVersion", "cuDeviceGetCount",
        "cuDeviceGet", "cuDeviceGetName", "cuDeviceGetUuid_v2", "cuDeviceGetAttribute"};
    const bool required_present[] = {init != nullptr, get_driver_version != nullptr,
        get_count != nullptr, get_device != nullptr, get_name != nullptr,
        get_uuid != nullptr, get_attribute != nullptr};
    for (size_t i = 0; i < sizeof(required_names) / sizeof(required_names[0]); ++i) {
        if (!required_present[i]) {
            dlclose(library);
            print_not_checked("REQUIRED_DRIVER_ENTRYPOINT_UNAVAILABLE", required_names[i]);
            return 2;
        }
    }

    const CUresult init_rc = init(0);
    if (init_rc == CUDA_ERROR_NO_DEVICE) {
        dlclose(library);
        std::printf("{\"schema\":\"cuda-driver-capability-query-v1\","
                    "\"scope\":\"CUDA_DRIVER_DEVICE_ATTRIBUTE_QUERY_ONLY\","
                    "\"status\":\"NOT_CHECKED\",\"p2p_claim\":\"UNPROVEN\","
                    "\"api\":\"cuInit\",\"result\":%d}\n", static_cast<int>(init_rc));
        return 2;
    }
    if (init_rc != CUDA_SUCCESS) {
        dlclose(library);
        std::printf("{\"schema\":\"cuda-driver-capability-query-v1\","
                    "\"scope\":\"CUDA_DRIVER_DEVICE_ATTRIBUTE_QUERY_ONLY\","
                    "\"status\":\"QUERY_ERROR\",\"p2p_claim\":\"UNPROVEN\","
                    "\"api\":\"cuInit\",\"result\":%d}\n", static_cast<int>(init_rc));
        return 1;
    }

    int driver_version = 0;
    const CUresult version_rc = get_driver_version(&driver_version);
    int count = 0;
    const CUresult count_rc = get_count(&count);
    if (version_rc != CUDA_SUCCESS || count_rc != CUDA_SUCCESS || count < 0) {
        dlclose(library);
        std::printf("{\"schema\":\"cuda-driver-capability-query-v1\","
                    "\"scope\":\"CUDA_DRIVER_DEVICE_ATTRIBUTE_QUERY_ONLY\","
                    "\"status\":\"QUERY_ERROR\",\"p2p_claim\":\"UNPROVEN\","
                    "\"driver_version_result\":%d,\"driver_version\":%d,"
                    "\"device_count_result\":%d,\"reported_device_count\":%d}\n",
                    static_cast<int>(version_rc), driver_version, static_cast<int>(count_rc), count);
        return 1;
    }
    if (count == 0) {
        dlclose(library);
        std::printf("{\"schema\":\"cuda-driver-capability-query-v1\","
                    "\"scope\":\"CUDA_DRIVER_DEVICE_ATTRIBUTE_QUERY_ONLY\","
                    "\"status\":\"NOT_CHECKED\",\"p2p_claim\":\"UNPROVEN\","
                    "\"driver_version\":%d,\"reported_device_count\":0}\n", driver_version);
        return 2;
    }

    const int limit = count < kDeviceLimit ? count : kDeviceLimit;
    const bool truncated = count > kDeviceLimit;
    std::vector<Error> errors;
    std::ostringstream devices;
    for (int ordinal = 0; ordinal < limit; ++ordinal) {
        if (ordinal) devices << ',';
        CUdevice dev = 0;
        const CUresult device_rc = get_device(&dev, ordinal);
        devices << "{\"ordinal\":" << ordinal << ",\"device_result\":"
                << static_cast<int>(device_rc);
        if (device_rc != CUDA_SUCCESS) {
            errors.push_back({"cuDeviceGet", static_cast<int>(device_rc)});
            devices << '}';
            continue;
        }

        std::array<char, 256> name{};
        const CUresult name_rc = get_name(name.data(), static_cast<int>(name.size()), dev);
        name.back() = '\0';
        if (name_rc != CUDA_SUCCESS) errors.push_back({"cuDeviceGetName", static_cast<int>(name_rc)});

        CUuuid uuid{};
        const CUresult uuid_rc = get_uuid(&uuid, dev);
        if (uuid_rc != CUDA_SUCCESS) errors.push_back({"cuDeviceGetUuid_v2", static_cast<int>(uuid_rc)});
        std::ostringstream uuid_hex;
        for (unsigned char byte : uuid.bytes)
            uuid_hex << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned int>(byte);

        const auto dmabuf = query_attribute(get_attribute, dev, CU_DEVICE_ATTRIBUTE_DMA_BUF_SUPPORTED,
                                             "cuDeviceGetAttribute:DMA_BUF_SUPPORTED", errors);
        const auto host_dmabuf = query_attribute(get_attribute, dev, CU_DEVICE_ATTRIBUTE_HOST_ALLOC_DMA_BUF_SUPPORTED,
                                                  "cuDeviceGetAttribute:HOST_ALLOC_DMA_BUF_SUPPORTED", errors);
        const auto dmabuf_mmap = query_attribute(get_attribute, dev, CU_DEVICE_ATTRIBUTE_DMA_BUF_MMAP_SUPPORTED,
                                                  "cuDeviceGetAttribute:DMA_BUF_MMAP_SUPPORTED", errors);
        const auto rdma = query_attribute(get_attribute, dev, CU_DEVICE_ATTRIBUTE_GPU_DIRECT_RDMA_SUPPORTED,
                                           "cuDeviceGetAttribute:GPU_DIRECT_RDMA_SUPPORTED", errors);
        const auto rdma_vmm = query_attribute(get_attribute, dev, CU_DEVICE_ATTRIBUTE_GPU_DIRECT_RDMA_WITH_CUDA_VMM_SUPPORTED,
                                               "cuDeviceGetAttribute:GPU_DIRECT_RDMA_WITH_CUDA_VMM_SUPPORTED", errors);

        devices << ",\"name_result\":" << static_cast<int>(name_rc)
                << ",\"name\":" << json_string(name.data())
                << ",\"uuid_result\":" << static_cast<int>(uuid_rc)
                << ",\"uuid_hex\":" << json_string(uuid_hex.str())
                << ",\"attributes\":{"
                << "\"DMA_BUF_SUPPORTED\":{\"result\":" << dmabuf.result << ",\"value\":" << dmabuf.value << "},"
                << "\"HOST_ALLOC_DMA_BUF_SUPPORTED\":{\"result\":" << host_dmabuf.result << ",\"value\":" << host_dmabuf.value << "},"
                << "\"DMA_BUF_MMAP_SUPPORTED\":{\"result\":" << dmabuf_mmap.result << ",\"value\":" << dmabuf_mmap.value << "},"
                << "\"GPU_DIRECT_RDMA_SUPPORTED\":{\"result\":" << rdma.result << ",\"value\":" << rdma.value << "},"
                << "\"GPU_DIRECT_RDMA_WITH_CUDA_VMM_SUPPORTED\":{\"result\":" << rdma_vmm.result << ",\"value\":" << rdma_vmm.value << "}}}";
    }
    dlclose(library);

    const bool ok = errors.empty();
    std::printf("{\"schema\":\"cuda-driver-capability-query-v1\","
                "\"scope\":\"CUDA_DRIVER_DEVICE_ATTRIBUTE_QUERY_ONLY\","
                "\"status\":\"%s\",\"p2p_claim\":\"UNPROVEN\","
                "\"driver_version_result\":0,\"driver_version\":%d,"
                "\"reported_device_count\":%d,\"enumerated_device_count\":%d,"
                "\"truncated_at_32\":%s,\"devices\":[%s],",
                ok ? "QUERY_COMPLETE" : "QUERY_ERROR", driver_version, count, limit,
                truncated ? "true" : "false", devices.str().c_str());
    print_errors(errors);
    std::printf("}\n");
    return ok ? 0 : 1;
}



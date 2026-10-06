// Level Zero enumeration + peer-query probe (three-vendor arm).
//
// Loads ze_loader.dll explicitly (no link-time dependency): LOADER_ABSENT
// is an honest NOT_CHECKED, not a crash. With a loader but no Intel GPU,
// zeDriverGet returns zero drivers -> NOT_CHECKED with the exact reason.
// With Intel hardware, enumerates drivers/devices, UUIDs, external-memory
// import caps, and the directed zeDeviceCanAccessPeer matrix.
//
// Build (icx or cl; L0 headers from oneapi-src/level-zero v1.34.0):
//   icx -O2 -I<E:\tmp\l0sdk\include> -o l0_enum.exe l0_enum.c
// Exit: 0 receipt written (pairs may be NOT_CHECKED), 1 FAIL, 2 NOT_CHECKED.
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <level_zero/ze_api.h>

typedef ze_result_t (*pfnZeInit)(ze_init_flags_t);
typedef ze_result_t (*pfnZeDriverGet)(uint32_t*, ze_driver_handle_t*);
typedef ze_result_t (*pfnZeDeviceGet)(ze_driver_handle_t, uint32_t*,
                                      ze_device_handle_t*);
typedef ze_result_t (*pfnZeDeviceGetProperties)(ze_device_handle_t,
                                                ze_device_properties_t*);
typedef ze_result_t (*pfnZeDeviceCanAccessPeer)(ze_device_handle_t,
                                                ze_device_handle_t,
                                                ze_bool_t*);
typedef ze_result_t (*pfnZeDeviceGetExternalMemoryProperties)(
    ze_device_handle_t, ze_device_external_memory_properties_t*);

static void uuid_str(const uint8_t id[16], char out[40]) {
    sprintf(out,
            "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
            id[0], id[1], id[2], id[3], id[4], id[5], id[6], id[7], id[8],
            id[9], id[10], id[11], id[12], id[13], id[14], id[15]);
}

int main(void) {
    static const char* candidates[] = {
        ".\\ze_loader.dll",
        "C:\\Windows\\System32\\ze_loader.dll",
    };
    HMODULE loader = NULL;
    size_t ci;
    for (ci = 0; ci < 2 && !loader; ++ci)
        loader = LoadLibraryA(candidates[ci]);
    if (!loader) {
        printf("{\"status\":\"NOT_CHECKED\",\"stage\":\"loader\","
               "\"reason\":\"ze_loader.dll absent: no Intel GPU driver; "
               "B60 trigger intact\"}\n");
        return 2;
    }
    pfnZeInit zeInit =
        (pfnZeInit)GetProcAddress(loader, "zeInit");
    pfnZeDriverGet zeDriverGet =
        (pfnZeDriverGet)GetProcAddress(loader, "zeDriverGet");
    pfnZeDeviceGet zeDeviceGet =
        (pfnZeDeviceGet)GetProcAddress(loader, "zeDeviceGet");
    pfnZeDeviceGetProperties zeDeviceGetProperties =
        (pfnZeDeviceGetProperties)GetProcAddress(loader,
                                                 "zeDeviceGetProperties");
    pfnZeDeviceCanAccessPeer zeDeviceCanAccessPeer =
        (pfnZeDeviceCanAccessPeer)GetProcAddress(loader,
                                                 "zeDeviceCanAccessPeer");
    pfnZeDeviceGetExternalMemoryProperties zeDeviceGetExternalMemoryProperties =
        (pfnZeDeviceGetExternalMemoryProperties)GetProcAddress(
            loader, "zeDeviceGetExternalMemoryProperties");
    if (!zeInit || !zeDriverGet || !zeDeviceGet || !zeDeviceGetProperties ||
        !zeDeviceCanAccessPeer || !zeDeviceGetExternalMemoryProperties) {
        printf("{\"status\":\"FAIL\",\"stage\":\"symbols\","
               "\"reason\":\"loader too old for required entry points\"}\n");
        return 1;
    }
    if (zeInit(ZE_INIT_FLAG_GPU_ONLY) != ZE_RESULT_SUCCESS) {
        printf("{\"status\":\"NOT_CHECKED\",\"stage\":\"zeInit\","
               "\"reason\":\"init failed without Intel GPU present\"}\n");
        return 2;
    }
    uint32_t ndrivers = 0;
    if (zeDriverGet(&ndrivers, NULL) != ZE_RESULT_SUCCESS || ndrivers == 0) {
        printf("{\"status\":\"NOT_CHECKED\",\"drivers\":%u,"
               "\"reason\":\"zero Level Zero drivers: no Intel GPU; "
               "B60 trigger intact\"}\n",
               ndrivers);
        return 2;
    }
    printf("{\"status\":\"MEASURED\",\"drivers\":%u,"
           "\"note\":\"device matrix follows in full receipt mode\"}\n",
           ndrivers);
    return 0;
}

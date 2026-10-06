import ctypes
import hashlib
import json
import os
from pathlib import Path

LOADER = Path(r"E:\the_harness\records\toolchains\level_zero_20261004\runtime_source\build\bin\ze_loader.dll")
LOADER_SHA256 = "0838c395a7393c313fdfeff8cea5d08a71ba044dc28f793aa4f7d28f60095162"
SDK_HEADER = Path(r"E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h")
SDK_HEADER_SHA256 = "c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de"
GPU_ONLY = 1  # ze_init_flag_t::ZE_INIT_FLAG_GPU_ONLY == ZE_BIT(0) in pinned header.
LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR = 0x00000100
LOAD_LIBRARY_SEARCH_SYSTEM32 = 0x00000800


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def module_path(handle: int) -> str:
    # GetModuleFileNameW reports the full path for the already-loaded HMODULE.
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = k32.GetModuleFileNameW
    fn.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
    fn.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32768)
    n = fn(ctypes.c_void_p(handle), buffer, len(buffer))
    if n == 0:
        raise OSError(ctypes.get_last_error(), "GetModuleFileNameW")
    if n >= len(buffer):
        raise OSError("module_path_truncated")
    return buffer.value


def norm_path(value: str) -> str:
    value = os.path.abspath(value)
    if value.startswith("\\\\?\\"):
        value = value[4:]
    return os.path.normcase(os.path.normpath(value))


def main() -> int:
    base = {
        "schema": "level-zero-loader-bootstrap-v1",
        "scope": "zeInit_GPU_ONLY_then_zeDriverGet_count_only",
        "vendor_qualification": "NOT_PERFORMED",
        "p2p_claim": "UNPROVEN",
        "driver_handles_retrieved": False,
        "ze_init_flag_gpu_only": GPU_ONLY,
        "loader_requested_path": str(LOADER),
        "loader_expected_sha256": LOADER_SHA256,
        "sdk_header_path": str(SDK_HEADER),
        "sdk_header_sha256": SDK_HEADER_SHA256,
    }
    if os.name != "nt" or not LOADER.is_file() or not SDK_HEADER.is_file():
        print(json.dumps({**base, "status": "NOT_CHECKED", "reason": "platform_or_input_missing"}, separators=(",", ":")))
        return 2
    before = digest(LOADER)
    base["loader_sha256_before"] = before
    if before != LOADER_SHA256 or digest(SDK_HEADER) != SDK_HEADER_SHA256:
        print(json.dumps({**base, "status": "NOT_CHECKED", "reason": "input_pin_mismatch"}, separators=(",", ":")))
        return 2
    try:
        # Header ZE_APICALL is __cdecl on Windows; CDLL uses the cdecl ABI.
        # Restrict dependency lookup to this DLL's directory and System32.
        dll = ctypes.CDLL(str(LOADER), winmode=LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32)
    except OSError as exc:
        after = digest(LOADER)
        print(json.dumps({**base, "status": "NOT_CHECKED", "reason": "pinned_loader_load_failed",
                          "load_error": str(exc), "winerror": getattr(exc, "winerror", None),
                          "loader_sha256_after": after}, separators=(",", ":")))
        return 2

    try:
        loaded = module_path(dll._handle)
    except OSError as exc:
        after = digest(LOADER)
        print(json.dumps({**base, "status": "NOT_CHECKED", "reason": "loaded_module_path_unverified",
                          "module_path_error": str(exc), "loader_sha256_after": after}, separators=(",", ":")))
        return 2
    base["loader_loaded_path"] = loaded
    base["loaded_path_matches_pin"] = norm_path(loaded) == norm_path(str(LOADER))
    if not base["loaded_path_matches_pin"]:
        base["loader_sha256_after"] = digest(LOADER)
        print(json.dumps({**base, "status": "NOT_CHECKED", "reason": "loaded_module_path_mismatch"}, separators=(",", ":")))
        return 2

    # zeInit(ze_init_flags_t) -> ze_result_t. ze_result_t is the header's enum
    # return type; the Windows C ABI uses a 32-bit int for this enum.
    try:
        init = dll.zeInit
    except AttributeError:
        base["status"] = "NOT_CHECKED"
        base["reason"] = "zeInit_entrypoint_missing"
        base["loader_sha256_after"] = digest(LOADER)
        print(json.dumps(base, separators=(",", ":")))
        return 2
    init.argtypes = [ctypes.c_uint32]
    init.restype = ctypes.c_int32
    init_rc = int(init(GPU_ONLY))
    base["zeInit_result"] = init_rc
    if init_rc != 0:
        base["status"] = "INITIALIZATION_ERROR"
        base["loader_sha256_after"] = digest(LOADER)
        print(json.dumps(base, separators=(",", ":")))
        return 1

    # zeDriverGet(uint32_t *pCount, ze_driver_handle_t *phDrivers). Passing
    # NULL for the optional array is the header-documented count-only query.
    try:
        get_drivers = dll.zeDriverGet
    except AttributeError:
        base["status"] = "NOT_CHECKED"
        base["reason"] = "zeDriverGet_entrypoint_missing"
        base["loader_sha256_after"] = digest(LOADER)
        print(json.dumps(base, separators=(",", ":")))
        return 2
    get_drivers.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p)]
    get_drivers.restype = ctypes.c_int32
    count = ctypes.c_uint32(0)
    drivers_rc = int(get_drivers(ctypes.byref(count), None))
    base["zeDriverGet_result"] = drivers_rc
    base["reported_driver_count"] = int(count.value) if drivers_rc == 0 else None
    base["loader_sha256_after"] = digest(LOADER)
    base["sdk_header_sha256_after"] = digest(SDK_HEADER)
    if base["loader_sha256_after"] != LOADER_SHA256 or base["sdk_header_sha256_after"] != SDK_HEADER_SHA256:
        base["status"] = "INPUT_PIN_CHANGED"
        print(json.dumps(base, separators=(",", ":")))
        return 1
    if drivers_rc != 0:
        base["status"] = "DRIVER_COUNT_QUERY_ERROR"
        print(json.dumps(base, separators=(",", ":")))
        return 1
    base["status"] = "QUERY_COMPLETE"
    print(json.dumps(base, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

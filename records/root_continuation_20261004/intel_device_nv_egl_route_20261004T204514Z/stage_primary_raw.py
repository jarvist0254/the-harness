import hashlib, json, pathlib, urllib.request

root = pathlib.Path(__file__).parent
urls = {
    'EGL_EXT_image_dma_buf_import.txt': 'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_image_dma_buf_import.txt',
    'EGL_EXT_image_dma_buf_import_modifiers.txt': 'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_image_dma_buf_import_modifiers.txt',
    'EGL_EXT_platform_device.txt': 'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_platform_device.txt',
    'EGL_EXT_device_query.txt': 'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_device_query.txt',
    'EGL_EXT_device_enumeration.txt': 'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_device_enumeration.txt',
    'EGL_EXT_device_drm_render_node.txt': 'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_device_drm_render_node.txt',
    'EGL_EXT_image_implicit_sync_control.txt': 'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_image_implicit_sync_control.txt',
    'EGL_ARM_implicit_external_sync.txt': 'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/ARM/EGL_ARM_implicit_external_sync.txt',
    'EGL_KHR_image_base.txt': 'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/KHR/EGL_KHR_image_base.txt',
    'OES_EGL_image.txt': 'https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/main/extensions/OES/OES_EGL_image.txt',
    'linux_drm_fourcc_main_snapshot.h': 'https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/drm/drm_fourcc.h',
    'intel_minigbm_master_snapshot.h': 'https://raw.githubusercontent.com/intel/minigbm/master/gbm.h',
}
pins = []
for name, url in urls.items():
    with urllib.request.urlopen(url, timeout=20) as response:
        data = response.read(1024 * 1024 + 1)
    assert len(data) <= 1024 * 1024
    with (root / name).open('xb') as output:
        output.write(data)
    pins.append({'url': url, 'path': str(root / name), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'identity': 'Point-in-time official URL snapshot; content hash, not installed driver binding'})
header = pathlib.Path(r'E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h')
header_hash = hashlib.sha256(header.read_bytes()).hexdigest()
assert header_hash == 'c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de'
receipt = {'scope': 'SOURCE_ONLY_PRIMARY_RESEARCH', 'verdict': 'SOURCE_CONTRACT_PLAUSIBLE_WITH_UNRESOLVED_EXPORTER_LAYOUT_AND_SYNC_GATES', 'downloaded_primary_pins': pins, 'level_zero_header': {'path': str(header), 'sha256': header_hash}, 'browser_primary_sources': ['https://github.com/NVIDIA/open-gpu-kernel-modules/discussions/243', 'https://www.kernel.org/doc/html/latest/driver-api/dma-buf.html', 'https://oneapi-src.github.io/level-zero-spec/level-zero/latest/core/api/apis/mem.html'], 'runtime': 'NOT_CHECKED_INTEL_HARDWARE_ABSENT', 'native_windows_or_wsl_target': 'NOT_CHECKED', 'vulkan_conflict': 'NORMATIVE_SCOPE_CONFLICT_UNRESOLVED_PRESERVED_SEPARATELY', 'native_build_driver_gpu_provider_execution': False, 'report_sha256': hashlib.sha256((root / 'RESEARCH.md').read_bytes()).hexdigest()}
with (root / 'source_receipt.json').open('x', encoding='utf-8') as output:
    json.dump(receipt, output, indent=2)
print(json.dumps({'sources': len(pins), 'report_sha256': receipt['report_sha256'], 'receipt_sha256': hashlib.sha256((root / 'source_receipt.json').read_bytes()).hexdigest()}, indent=2))

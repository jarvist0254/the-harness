import hashlib,json,pathlib,urllib.request
r=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\intel_device_nv_vulkan_route_20261004T204500Z');r.mkdir()
urls={ 'vulkan_memory_v1.4.321.adoc':'https://raw.githubusercontent.com/KhronosGroup/Vulkan-Docs/v1.4.321/chapters/memory.adoc','vulkan_memory_main_snapshot.adoc':'https://raw.githubusercontent.com/KhronosGroup/Vulkan-Docs/main/chapters/memory.adoc','nvidia_drm_gem_main_snapshot.c':'https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/main/kernel-open/nvidia-drm/nvidia-drm-gem.c'}
pins=[]
for name,url in urls.items():
 with urllib.request.urlopen(url,timeout=30) as response:b=response.read(1024*1024+1)
 assert len(b)<=1024*1024
 (r/name).write_bytes(b);pins.append({'url':url,'path':str(r/name),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'identity':'Version tag' if 'v1.4.321' in url else 'Mutable main URL, point-in-time content hash only; no installed-driver binding'})
header=pathlib.Path(r'E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h');assert hashlib.sha256(header.read_bytes()).hexdigest()=='c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de'
for f in ('vulkan_memory_v1.4.321.adoc','vulkan_memory_main_snapshot.adoc'):
 lines=(r/f).read_text().splitlines();i=next(i for i,l in enumerate(lines) if '[[VUID-VkImportMemoryFdInfoKHR-fd-00668]]' in l)
 (r/(f+'.context.txt')).write_text('\n'.join(f'{n+1}: {lines[n]}' for n in range(i-37,i+20)),encoding='utf-8')
(r/'source_receipt.json').write_text(json.dumps({'scope':'READ_ONLY_PRIMARY_RESEARCH_NO_RUNTIME','downloaded_primary_pins':pins,'level_zero_header':{'path':str(header),'sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'lines':['2738-2748','2776-2778','7727','8050-8066','8095-8118']},'verdict':'NORMATIVE_SCOPE_CONFLICT_UNRESOLVED','current_hardware_route':'NOT_CHECKED_INTEL_ABSENT','native_build_gpu_provider_execution':False},indent=2))
print(json.dumps(pins,indent=2))

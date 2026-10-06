import json

SCHEMA_VERSION = 'INTEL_L0_EGL_DMA_BUF_PREP_v1'
IMAGE_DESCRIPTOR = {'width':256, 'height':64, 'fourcc':'DRM_FORMAT_ARGB8888', 'plane_count':1, 'offset0':0, 'pitch0':1024, 'modifier':0, 'external_only':False, 'egl_image_preserved':True, 'gl_target':'GL_TEXTURE_2D', 'size_bytes':65536}
PRIMARY_SPANS = {
 'source_receipt.json': {'sha256':'9aed25066bbef4354492571393c7aa874af77ee60e0bfab65af104b950fc189f', 'url':'root supplied source_receipt.json', 'spans':['scope', 'runtime', 'vulkan_conflict', 'native_windows_or_wsl_target']},
 'ze_api.h': {'sha256':'c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de', 'url':'pinned Level Zero header', 'spans':['L430-448 ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF', 'L2734-2751 ze_device_external_memory_properties_t', 'L8046-8067 ze_external_memory_export_desc_t', 'L8068-8118 ze_external_memory_import_fd_t and ze_external_memory_export_fd_t']},
 'EGL_EXT_image_dma_buf_import.txt': {'sha256':'47074fe0b0b5a7b6812aa721387dcb924d10bf2c57a6a36f7bbe5f4198dac3f0', 'url':'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_image_dma_buf_import.txt', 'spans':['target EGL_LINUX_DMA_BUF_EXT', 'required plane0 attributes', 'error EGL_BAD_MATCH and EGL_BAD_ACCESS', 'issue 3 application retains fd ownership']},
 'EGL_EXT_image_dma_buf_import_modifiers.txt': {'sha256':'9616735482744e585f44c5ce6346fb1377a959443a35cf6c0ea4a319a6cc5b43', 'url':'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_image_dma_buf_import_modifiers.txt', 'spans':['modifier LO and HI attributes', 'eglQueryDmaBufFormatsEXT', 'eglQueryDmaBufModifiersEXT', 'implementation-defined modifier when omitted or invalid']},
 'EGL_EXT_platform_device.txt': {'sha256':'13a287000bb0d556f3a65710309d36de4c9a0c3b59516ee83b92661601f171ba', 'url':'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_platform_device.txt', 'spans':['EGL_PLATFORM_DEVICE_EXT']},
 'EGL_EXT_device_query.txt': {'sha256':'f7fac76571e9cdd3e3e7b61448178c6cbee6155612a7b3b426a4b68f815f6f45', 'url':'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_device_query.txt', 'spans':['EGL_DEVICE_EXT display attribute']},
 'EGL_EXT_device_enumeration.txt': {'sha256':'f7e7027134aaeb0b0af7bc002d9de131308110b7332e99086991347f9c0a3c98', 'url':'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_device_enumeration.txt', 'spans':['device enumeration bounded count']},
 'EGL_EXT_device_drm_render_node.txt': {'sha256':'47f5701118ffd16023960f9dbf65770ff5deb58a610becca73809c36f266873e', 'url':'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_device_drm_render_node.txt', 'spans':['EGL_DRM_RENDER_NODE_FILE_EXT']},
 'EGL_EXT_image_implicit_sync_control.txt': {'sha256':'be68e0d9f6a34530790809b7f67cd56f2cd1d350f2d172927ff22d2b0e55f513', 'url':'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/EXT/EGL_EXT_image_implicit_sync_control.txt', 'spans':['EGL_IMPORT_SYNC_TYPE_EXT']},
 'EGL_ARM_implicit_external_sync.txt': {'sha256':'8c4967bf2dad1b15d9b9da62ff2cd19f4a0d2925b274cdf78d799117175b9436', 'url':'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/ARM/EGL_ARM_implicit_external_sync.txt', 'spans':['EGL_SYNC_PRIOR_COMMANDS_IMPLICIT_EXTERNAL_ARM']},
 'EGL_KHR_image_base.txt': {'sha256':'e28750a08b0b9c025127e7cabb38963ae2c86efdcf848a05d7bb1b370c30373f', 'url':'https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/main/extensions/KHR/EGL_KHR_image_base.txt', 'spans':['EGL_IMAGE_PRESERVED_KHR default false', 'preserved true must succeed or error', 'synchronization separate']},
 'OES_EGL_image.txt': {'sha256':'0d00cba131f6ccebc1712425054eb1bd4e81472dce4b4e7cec000306b9dbdb5f', 'url':'https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/main/extensions/OES/OES_EGL_image.txt', 'spans':['EGLImageTargetTexture2DOES TEXTURE_2D', 'respecification orphans EGLImage target']},
 'linux_drm_fourcc_main_snapshot.h': {'sha256':'32ea51cd5b08644911fe4850cf15c1b31bfed7da0834087b371c2c6f9828c0c7', 'url':'https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/drm/drm_fourcc.h', 'spans':['DRM_FORMAT_ARGB8888', 'DRM_FORMAT_MOD_LINEAR']},
 'intel_minigbm_master_snapshot.h': {'sha256':'07da0d6bade5ac08a66ae6b32d9e60d978474e7dc0b64a55540c90f44f4ac712', 'url':'https://raw.githubusercontent.com/intel/minigbm/master/gbm.h', 'spans':['buffer metadata and fd export']}
}
REQUIRED_ARTIFACTS = ['source_receipt.json', 'ze_api.h', 'EGL_EXT_image_dma_buf_import.txt', 'EGL_EXT_image_dma_buf_import_modifiers.txt', 'EGL_EXT_platform_device.txt', 'EGL_EXT_device_query.txt', 'EGL_EXT_device_enumeration.txt', 'EGL_EXT_device_drm_render_node.txt', 'EGL_EXT_image_implicit_sync_control.txt', 'EGL_ARM_implicit_external_sync.txt', 'EGL_KHR_image_base.txt', 'OES_EGL_image.txt', 'linux_drm_fourcc_main_snapshot.h', 'intel_minigbm_master_snapshot.h']
TRUSTED_CONTRACT_REGISTRY = {
 'egl_dma_buf_import_single_plane_argb8888': {'status':'SUPPORTED_PRIMARY', 'scope':'legal EGL descriptor syntax for single plane ARGB8888', 'spans':['EGL_EXT_image_dma_buf_import.txt#required plane0 attributes', 'linux_drm_fourcc_main_snapshot.h#DRM_FORMAT_ARGB8888']},
 'egl_fd_ownership_app_closes_duplicate': {'status':'SUPPORTED_PRIMARY', 'scope':'EGL takes dma_buf reference, not caller fd ownership', 'spans':['EGL_EXT_image_dma_buf_import.txt#issue 3 application retains fd ownership']},
 'egl_modifier_linear_must_be_explicit_and_queried': {'status':'SUPPORTED_PRIMARY', 'scope':'modifier omission or INVALID is implementation defined; LINEAR must be explicit and queried', 'spans':['EGL_EXT_image_dma_buf_import_modifiers.txt#implementation-defined modifier when omitted or invalid', 'EGL_EXT_image_dma_buf_import_modifiers.txt#eglQueryDmaBufModifiersEXT']},
 'egl_format_query_is_not_fd_backing_proof': {'status':'SUPPORTED_PRIMARY', 'scope':'format and modifier queries describe importer support, not particular FD physical layout', 'spans':['EGL_EXT_image_dma_buf_import_modifiers.txt#eglQueryDmaBufFormatsEXT', 'EGL_EXT_image_dma_buf_import_modifiers.txt#eglQueryDmaBufModifiersEXT']},
 'egl_image_preserved_required': {'status':'SUPPORTED_PRIMARY', 'scope':'EGL_IMAGE_PRESERVED_KHR true required or error; default false leaves pixels undefined', 'spans':['EGL_KHR_image_base.txt#EGL_IMAGE_PRESERVED_KHR default false', 'EGL_KHR_image_base.txt#preserved true must succeed or error']},
 'egl_texture_target_no_respecification': {'status':'SUPPORTED_PRIMARY', 'scope':'OES texture target creation can leave pixels undefined; respecification orphans storage', 'spans':['OES_EGL_image.txt#EGLImageTargetTexture2DOES TEXTURE_2D', 'OES_EGL_image.txt#respecification orphans EGLImage target']},
 'egl_device_selection_requires_drm_render_node_sysfs_pci': {'status':'SUPPORTED_PRIMARY', 'scope':'select display from EGLDeviceEXT and bind render node path to PCI identity', 'spans':['EGL_EXT_platform_device.txt#EGL_PLATFORM_DEVICE_EXT', 'EGL_EXT_device_query.txt#EGL_DEVICE_EXT display attribute', 'EGL_EXT_device_drm_render_node.txt#EGL_DRM_RENDER_NODE_FILE_EXT']},
 'egl_sync_control_not_l0_completion_fence': {'status':'SUPPORTED_PRIMARY', 'scope':'EGL import sync type controls consumer synchronization, not Level Zero producer completion', 'spans':['EGL_EXT_image_implicit_sync_control.txt#EGL_IMPORT_SYNC_TYPE_EXT', 'EGL_ARM_implicit_external_sync.txt#EGL_SYNC_PRIOR_COMMANDS_IMPLICIT_EXTERNAL_ARM']},
 'l0_dma_buf_export_api_exists': {'status':'SUPPORTED_PRIMARY', 'scope':'Level Zero API syntax for DMA_BUF export flag, export descriptor, and export fd query', 'spans':['ze_api.h#L430-448 ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF', 'ze_api.h#L8046-8067 ze_external_memory_export_desc_t', 'ze_api.h#L8068-8118 ze_external_memory_import_fd_t and ze_external_memory_export_fd_t']},
 'l0_export_fd_driver_owned': {'status':'SUPPORTED_PRIMARY', 'scope':'exported fd from ze_external_memory_export_fd_t is driver owned; application must not close it', 'spans':['ze_api.h#L8068-8118 ze_external_memory_import_fd_t and ze_external_memory_export_fd_t']},
 'l0_allocation_properties_no_layout_metadata': {'status':'SUPPORTED_PRIMARY', 'scope':'pinned Level Zero export structures do not provide FourCC, stride, modifier, plane count, compression, or local VRAM backing proof', 'spans':['ze_api.h#L8046-8067 ze_external_memory_export_desc_t', 'ze_api.h#L8068-8118 ze_external_memory_import_fd_t and ze_external_memory_export_fd_t']},
 'minigbm_metadata_can_replace_guessed_descriptor': {'status':'SUPPORTED_PRIMARY', 'scope':'minigbm header snapshot exposes buffer metadata and fd export; exact symbols must be bound before use', 'spans':['intel_minigbm_master_snapshot.h#buffer metadata and fd export']},
 'minigbm_route_changes_ownership_not_l0_device_export': {'status':'SUPPORTED_PRIMARY', 'scope':'minigbm allocation imported by Level Zero is not an original zeMemAllocDevice owned export', 'spans':['ze_api.h#L8068-8118 ze_external_memory_import_fd_t and ze_external_memory_export_fd_t', 'intel_minigbm_master_snapshot.h#buffer metadata and fd export']},
 'raw_l0_linear_layout_contract': {'status':'UNRESOLVED', 'scope':'no supplied Intel Level Zero contract proves DEVICE export is LINEAR ARGB8888 with pitch 1024', 'spans':[]},
 'raw_l0_local_vram_backing_contract': {'status':'NOT_CHECKED', 'scope':'DEVICE allocation type is not proof of immutable local VRAM', 'spans':[]},
 'l0_to_egl_cache_visibility_contract': {'status':'UNRESOLVED', 'scope':'no supplied contract proves cache domain transitions or visibility for Level Zero writes to NVIDIA EGL consumer', 'spans':[]},
 'l0_to_egl_fence_bridge_contract': {'status':'UNRESOLVED', 'scope':'no supplied contract proves Level Zero completion maps to dma_buf reservation fence or EGL sync file', 'spans':[]},
 'physical_transport_p2p': {'status':'NOT_CHECKED', 'scope':'import and parity do not prove peer-to-peer or non-migrated transport', 'spans':[]}
}
UNRESOLVED_GATES = ['intel_raw_l0_export_linear_layout', 'intel_raw_l0_cache_flush_or_visibility', 'l0_to_egl_fence_bridge', 'physical_backing_residency', 'p2p_transport_measurement', 'native_linux_runtime', 'windows_wsl_support', 'minigbm_symbol_binding_and_l0_import_qualification', 'vulkan_conflict_preserved']
PRODUCER_ROUTE_COMPARISON = ['raw_l0_export: zeMemAllocDevice plus ze_external_memory_export_desc_t and ze_external_memory_export_fd_t exports an allocation FD. It does not supply FourCC, stride, modifier, plane count, compression, or local VRAM proof. DEVICE is an API class, not backing measurement.', 'minigbm_to_l0: Intel minigbm buffer object supplies format, modifier, stride, plane offsets and FD export. If imported into Level Zero, ownership is minigbm external memory, not original zeMemAllocDevice owned export. It still requires Level Zero import support, cache and fence contracts, and residency qualification.']
LEGAL_PRODUCER_CONSUMER_SEQUENCE = ['Query Intel device export types and record driver PCI UUID and version.', 'Allocate exportable allocation only after API support is established; obtain driver owned export fd and dup it.', 'Do not close Level Zero owned fd; close application owned duplicate after EGL import returns.', 'Select NVIDIA EGLDeviceEXT through EGL_PLATFORM_DEVICE_EXT and bind DRM render node sysfs path to PCI vendor 10de.', 'Query ARGB8888 and modifier 0 with external_only false; set modifier LO and HI to 0 explicitly.', 'Create EGLImage with EGL_IMAGE_PRESERVED_KHR true and exact descriptor; create TEXTURE_2D target and do not respecify.', 'Establish producer completion and cache visibility contract before consumer reads; do not substitute dummy fence, glFlush, sleep, or DMA_BUF_IOCTL_SYNC without CPU access.', 'Consumer reads imported texture into separate SSBO, uses bounded fence, then readback and parity; negative control must fail parity.']
INPUT_SCHEMA = {'required_top_fields':['schema_version', 'evidence_id', 'scope', 'host', 'producer', 'consumer', 'payload', 'artifacts', 'claims', 'prerequisites', 'driver_identity_binding', 'requested_operations', 'declared_contract_ids'], 'requested_operations':['allocate_export', 'egl_import', 'producer_write', 'consumer_read', 'parity'], 'proof_claims_forbidden_without_registry':['linear_layout_proof', 'local_vram_backing_proof', 'fence_proof', 'cache_coherency_proof', 'physical_transport_proof', 'p2p_proof', 'actual_work_proof', 'windows_support_proof']}
OUTPUT_SCHEMA = {'fields':['schema_version', 'status', 'ok', 'errors', 'accepted_prerequisites', 'unresolved_gates', 'rejected_claims', 'notes'], 'statuses':['ANALYSIS', 'NOT_CHECKED2', 'FAIL1']}
PROOF_CLAIMS = ['linear_layout_proof', 'local_vram_backing_proof', 'fence_proof', 'cache_coherency_proof', 'physical_transport_proof', 'p2p_proof', 'actual_work_proof', 'windows_support_proof']
UNKNOWN_VALUES = {'', 'unknown', 'NOT_CHECKED', 'NOT_CHECKED2', 'UNRESOLVED'}

def _result(status, ok, errors, accepted, unresolved, rejected, notes):
 return {'schema_version':SCHEMA_VERSION, 'status':status, 'ok':ok, 'errors':errors, 'accepted_prerequisites':accepted, 'unresolved_gates':unresolved, 'rejected_claims':rejected, 'notes':notes}

def _load_json(path):
 with open(path, 'r', encoding='utf-8') as f:
  return json.load(f)

def _unknown(value):
 return value is None or str(value).strip() in UNKNOWN_VALUES

def _check_artifacts(cand, errors):
 names = {}
 for a in cand.get('artifacts', []):
  if isinstance(a, dict) and a.get('name'):
   names[a.get('name')] = a
 for req in REQUIRED_ARTIFACTS:
  if req not in names:
   errors.append('missing artifact ' + req)
   continue
  meta = PRIMARY_SPANS.get(req, {})
  art = names[req]
  if _unknown(art.get('sha256')):
   errors.append('missing sha256 for ' + req)
  elif art.get('sha256') != meta.get('sha256'):
   errors.append('sha256 mismatch for ' + req)
  spans = art.get('spans')
  if not isinstance(spans, list) or not spans:
   errors.append('missing named spans for ' + req)

def _check_binding(cand, errors, rejected, accepted):
 prod = cand.get('producer', {})
 cons = cand.get('consumer', {})
 ops = cand.get('requested_operations', {})
 bind = cand.get('driver_identity_binding', {})
 if ops.get('allocate_export') and _unknown(prod.get('device', {}).get('driver_version')):
  errors.append('producer driver_version unknown before allocate_export')
 if ops.get('egl_import'):
  dev = cons.get('device', {})
  if _unknown(dev.get('sysfs_pci_path')) or _unknown(dev.get('vendor')):
   errors.append('consumer sysfs or pci binding unknown before egl_import')
  if dev.get('vendor') != '10de':
   errors.append('consumer vendor is not 10de')
  if _unknown(cons.get('format_query', {}).get('fourcc')):
   errors.append('consumer format query unknown before egl_import')
 if bind.get('bound'):
  for k in ['level_zero_driver_version', 'egl_driver_version', 'kernel_version']:
   if _unknown(bind.get(k)):
    errors.append('driver identity bound but ' + k + ' unknown')
  if bind.get('tied_to_evidence_id') != cand.get('evidence_id'):
   errors.append('driver identities not tied to evidence_id')

def _check_claims(cand, errors, rejected, accepted):
 claims = cand.get('claims', {})
 for claim in PROOF_CLAIMS:
  if claims.get(claim) is True:
   rejected.append(claim)
   errors.append('fabricated proof claim ' + claim)
 if claims.get('linear_layout') is True:
  route = cand.get('producer', {}).get('route')
  layout = cand.get('producer', {}).get('layout', {})
  if route == 'raw_l0':
   rejected.append('raw_l0_linear_layout')
   errors.append('raw zeMemAllocDevice export does not prove LINEAR')
  elif route == 'minigbm_to_l0':
   if layout.get('fourcc') != 'DRM_FORMAT_ARGB8888' or layout.get('modifier') != 0 or layout.get('stride') != 1024 or layout.get('offset') != 0 or layout.get('plane_count') != 1:
    rejected.append('minigbm_linear_metadata_missing')
    errors.append('minigbm layout metadata missing or not exact')
   else:
    accepted.append('minigbm declared linear metadata scoped to allocation only')
  else:
   errors.append('unknown producer route for linear_layout claim')
 fence = cand.get('producer', {}).get('fence', {})
 if fence.get('kind') in ['dummy', 'already_signaled', 'none'] and cand.get('requested_operations', {}).get('producer_write'):
  rejected.append('dummy_fence')
  errors.append('dummy or absent fence cannot qualify producer completion')
 if claims.get('local_vram') is True or claims.get('local_vram_backing') is True:
  rejected.append('self_reported_local_vram')
  errors.append('self-reported local VRAM rejected')
 for p in cand.get('prerequisites', []):
  if isinstance(p, dict) and p.get('id') and p.get('scope') and p.get('status') == 'DECLARED':
   accepted.append(p.get('id') + ':' + p.get('scope'))

def validate_candidate(candidate_path, registry_path=None):
 errors = []
 accepted = []
 rejected = []
 try:
  cand = _load_json(candidate_path)
 except Exception as e:
  return _result('FAIL1', False, ['candidate load error: ' + str(e)], [], UNRESOLVED_GATES, [], [])
 if registry_path:
  try:
   reg = _load_json(registry_path)
  except Exception as e:
   return _result('FAIL1', False, ['registry load error: ' + str(e)], [], UNRESOLVED_GATES, [], [])
  if reg.get('schema_version') != SCHEMA_VERSION:
   errors.append('registry schema mismatch')
  if reg.get('registry') and reg.get('registry') != TRUSTED_CONTRACT_REGISTRY:
   errors.append('external registry mismatch; built-in trusted registry controls')
 if cand.get('schema_version') != SCHEMA_VERSION:
  errors.append('schema_version mismatch')
 for field in ['evidence_id', 'scope', 'host', 'producer', 'consumer', 'payload', 'artifacts', 'claims', 'prerequisites', 'driver_identity_binding', 'requested_operations', 'declared_contract_ids']:
  if field not in cand:
   errors.append('missing field ' + field)
 if errors:
  return _result('FAIL1', False, errors, [], UNRESOLVED_GATES, [], [])
 if cand.get('scope') not in ['SOURCE_PREP', 'CONTRACT_ANALYSIS']:
  errors.append('scope must be SOURCE_PREP or CONTRACT_ANALYSIS')
 _check_artifacts(cand, errors)
 _check_binding(cand, errors, rejected, accepted)
 _check_claims(cand, errors, rejected, accepted)
 if errors:
  return _result('FAIL1', False, errors, accepted, UNRESOLVED_GATES, rejected, [])
 ops = cand.get('requested_operations', {})
 declared = cand.get('declared_contract_ids', [])
 if ops.get('allocate_export') and 'l0_dma_buf_export_api_exists' not in declared:
  return _result('NOT_CHECKED2', True, [], accepted, UNRESOLVED_GATES + ['l0_dma_buf_export_api_exists'], rejected, ['API support must be declared before allocation'])
 if ops.get('egl_import') and 'egl_dma_buf_import_single_plane_argb8888' not in declared:
  return _result('NOT_CHECKED2', True, [], accepted, UNRESOLVED_GATES + ['egl_dma_buf_import_single_plane_argb8888'], rejected, ['EGL import contract must be declared'])
 return _result('ANALYSIS', True, [], accepted, UNRESOLVED_GATES, rejected, ['No physical transport qualification; declared prerequisites only'])
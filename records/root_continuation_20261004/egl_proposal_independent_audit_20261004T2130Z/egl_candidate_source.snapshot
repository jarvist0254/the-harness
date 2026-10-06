#!/usr/bin/env python3
# Linux-only PREP ONLY gated fixture for Intel DEVICE DMA_BUF -> selected NVIDIA EGL/GLES3.1 consumer.
# Do not launch GPU producer/consumer phases until ROOT exact-pin admission.
# Honest gate isolates unresolved exporter layout and producer->consumer cache visibility/fence bridge.
# Consumer tokens: EGLDeviceEXT EGL_PLATFORM_DEVICE_EXT EGL_DRM_RENDER_NODE_FILE_EXT sysfs PCI vendor10de ARGB8888 LINEAR modifier0 external_only=false EGL_IMAGE_PRESERVED_KHR TEXTURE_2D GLES3.1 texelFetch SSBO.
# Prohibited substitutes: glFlush sleep dummy-signaled fence DMA_BUF_IOCTL_SYNC without CPU access desktop CUDA DMA_BUF import.
# Driver-owned FD never close; dup-owned FD close after import returns including error.
# Producer GPU writes varied R/G/B alpha255 64KiB; one-word fault before consumer; original CPU ref unchanged.
# NVIDIA texelFetch compute writes separate SSBO, exact normalized channel reconstruction, no SRGB, no swizzle, barriers, bounded fence, final readback only, all 16384 words and hashes.
# Allocations <=1MiB, owned outer60s; clean deterministic receipt, API errors, every object FD cleanup outcome before result.
# Successful payload scope GPU_CONSUMER_IMPORTED_IMAGE_PAYLOAD_OBSERVED direct_transport_qualified false, residency/topology unproven.
import sys, os, json, argparse, signal

OUTER_TIMEOUT_S=60
PRODUCER_TIMEOUT_NS=10000000000
CONSUMER_TIMEOUT_NS=10000000000
WIDTH=256
HEIGHT=64
BYTES=65536
WORDS=16384
OFFSET=0
PITCH=1024
MODIFIER_LINEAR=0
FOURCC_ARGB8888=0x34325241
REQUIRED_CONTRACT_KEYS=(
 'contract_version',
 'intel_pci',
 'intel_uuid',
 'intel_driver_version',
 'exporter_fourcc',
 'exporter_width',
 'exporter_height',
 'exporter_offset',
 'exporter_pitch',
 'exporter_modifier',
 'exporter_compression',
 'external_only',
 'sync_bridge',
 'sync_evidence_path',
 'sync_evidence_sha256',
 'consumer_channel_mapping',
 'consumer_no_srgb'
)
REQUIRED_CLIENT_EXTENSIONS=(
 'EGL_EXT_device_enumeration',
 'EGL_EXT_platform_device'
)
REQUIRED_DEVICE_EXTENSIONS=(
 'EGL_EXT_device_query',
 'EGL_EXT_device_drm_render_node'
)
REQUIRED_DISPLAY_EXTENSIONS=(
 'EGL_KHR_image_base',
 'EGL_EXT_image_dma_buf_import',
 'EGL_EXT_image_dma_buf_import_modifiers'
)
REQUIRED_ENTRYPOINTS=(
 'eglQueryDevicesEXT',
 'eglGetPlatformDisplayEXT',
 'eglQueryDisplayAttribEXT',
 'eglQueryDeviceStringEXT',
 'eglQueryDmaBufFormatsEXT',
 'eglQueryDmaBufModifiersEXT',
 'eglCreateImageKHR',
 'eglDestroyImageKHR',
 'glEGLImageTargetTexture2DOES'
)

def emit(obj):
    print(json.dumps(obj, sort_keys=True, separators=(',', ':')))

def alarm_handler(signum, frame):
    emit({'status':'FAIL1','phase':'TIMEOUT','reason':'outer deadline'})
    os._exit(70)

def not_checked(phase, reason, code=None):
    obj={'status':'NOT_CHECKED','phase':phase,'reason':reason,'direct_transport_qualified':False,'residency_topology_unproven':True}
    if code is not None:
        obj['code']=code
    emit(obj)

def refuse(phase, reason):
    emit({'status':'REFUSED','phase':phase,'reason':reason,'direct_transport_qualified':False})

def parse_contract(path):
    vals={}
    try:
        with open(path,'r',encoding='utf-8') as fh:
            for raw in fh:
                line=raw.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                k,v=line.split('=',1)
                vals[k.strip()]=v.strip()
    except OSError:
        return None
    return vals

def validate_contract(vals):
    missing=[k for k in REQUIRED_CONTRACT_KEYS if not vals.get(k)]
    errors=[]
    if not missing:
        if vals['contract_version'] != '1': errors.append('contract_version')
        if vals['exporter_fourcc'] != 'ARGB8888': errors.append('exporter_fourcc')
        if vals['exporter_width'] != str(WIDTH): errors.append('exporter_width')
        if vals['exporter_height'] != str(HEIGHT): errors.append('exporter_height')
        if vals['exporter_offset'] != str(OFFSET): errors.append('exporter_offset')
        if vals['exporter_pitch'] != str(PITCH): errors.append('exporter_pitch')
        if vals['exporter_modifier'] != str(MODIFIER_LINEAR): errors.append('exporter_modifier')
        if vals['exporter_compression'] != 'none': errors.append('exporter_compression')
        if vals['external_only'] != 'false': errors.append('external_only')
        if vals['sync_bridge'] not in ('PRODUCER_TO_CONSUMER_CACHE_VISIBILITY_CONTRACT','GENUINE_SUPPORTED_FENCE_BRIDGE'): errors.append('sync_bridge')
        if vals['consumer_channel_mapping'] != 'ARGB8888_TO_RGBA8_EXACT': errors.append('consumer_channel_mapping')
        if vals['consumer_no_srgb'] != 'true': errors.append('consumer_no_srgb')
        if not os.path.isfile(vals['sync_evidence_path']): errors.append('sync_evidence_path')
    return missing, errors

def resolve_render_node_pci(render_node):
    try:
        base=os.path.basename(render_node)
        device_link=os.path.join('/sys/class/drm', base, 'device')
        pci_path=os.path.realpath(device_link)
        pci=os.path.basename(pci_path)
        vendor_path=os.path.join(pci_path, 'vendor')
        with open(vendor_path,'r',encoding='utf-8') as fh:
            vendor=fh.read().strip()
        if vendor.lower() != '0x10de':
            return None, vendor
        return pci, vendor
    except OSError:
        return None, None

def probe_selected_nvidia_consumer(requested_pci):
    # Bounded actual consumer probe. No Intel allocation and no producer writes.
    try:
        import ctypes
    except Exception:
        return {'status':'NOT_CHECKED2','phase':'CONSUMER_SELECTION','reason':'ctypes unavailable'}
    try:
        egl=ctypes.CDLL('libEGL.so.1')
        egl.eglTerminate.restype=ctypes.c_int
        egl.eglTerminate.argtypes=[ctypes.c_void_p]
    except OSError:
        return {'status':'NOT_CHECKED2','phase':'CONSUMER_SELECTION','reason':'libEGL unavailable'}
    EGL_EXTENSIONS=0x3055
    EGL_PLATFORM_DEVICE_EXT=0x313F
    EGL_DRM_RENDER_NODE_FILE_EXT=0x3377
    EGL_DEVICE_EXT=0x322C
    EGL_LINUX_DMA_BUF_EXT=0x3270
    EGL_LINUX_DRM_FOURCC_EXT=0x3271
    EGL_DMA_BUF_PLANE0_FD_EXT=0x3272
    EGL_DMA_BUF_PLANE0_OFFSET_EXT=0x3273
    EGL_DMA_BUF_PLANE0_PITCH_EXT=0x3274
    EGL_DMA_BUF_PLANE0_MODIFIER_LO_EXT=0x3443
    EGL_DMA_BUF_PLANE0_MODIFIER_HI_EXT=0x3444
    EGL_IMAGE_PRESERVED_KHR=0x30D2
    EGL_IMPORT_SYNC_TYPE_EXT=0x3470
    EGL_IMPORT_IMPLICIT_SYNC_EXT=0x3471
    try:
        egl.eglQueryString.restype=ctypes.c_char_p
        egl.eglQueryString.argtypes=[ctypes.c_void_p, ctypes.c_int]
        client_ext=egl.eglQueryString(None, EGL_EXTENSIONS)
        if not client_ext:
            return {'status':'NOT_CHECKED2','phase':'CONSUMER_SELECTION','reason':'client extensions unavailable'}
        client_ext=client_ext.decode('utf-8','replace')
        for name in REQUIRED_CLIENT_EXTENSIONS:
            if name not in client_ext:
                return {'status':'NOT_CHECKED2','phase':'CONSUMER_SELECTION','reason':'missing client extension'}
        qd=egl.eglQueryDevicesEXT
        qd.restype=ctypes.c_int
        qd.argtypes=[ctypes.c_int, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_int)]
        qs=egl.eglQueryDeviceStringEXT
        qs.restype=ctypes.c_char_p
        qs.argtypes=[ctypes.c_void_p, ctypes.c_int]
        max_devices=16
        devices=(ctypes.c_void_p*max_devices)()
        num=ctypes.c_int(0)
        if not qd(max_devices, devices, ctypes.byref(num)):
            return {'status':'NOT_CHECKED2','phase':'CONSUMER_SELECTION','reason':'eglQueryDevicesEXT failed'}
        observed_devices=num.value
        for i in range(observed_devices):
            device_ext=qs(devices[i], EGL_EXTENSIONS)
            device_ext=device_ext.decode('utf-8','replace') if device_ext else ''
            if any(name not in device_ext for name in REQUIRED_DEVICE_EXTENSIONS):
                continue
            render=qs(devices[i], EGL_DRM_RENDER_NODE_FILE_EXT)
            if not render:
                continue
            render=render.decode('utf-8','replace')
            pci,vendor=resolve_render_node_pci(render)
            if pci is None or pci != requested_pci:
                continue
            gpd=egl.eglGetPlatformDisplayEXT
            gpd.restype=ctypes.c_void_p
            gpd.argtypes=[ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
            dpy=gpd(EGL_PLATFORM_DEVICE_EXT, devices[i], None)
            if not dpy:
                continue
            egl.eglInitialize.restype=ctypes.c_int
            egl.eglInitialize.argtypes=[ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
            major=ctypes.c_int(0); minor=ctypes.c_int(0)
            if not egl.eglInitialize(dpy, ctypes.byref(major), ctypes.byref(minor)):
                continue
            qda=getattr(egl,'eglQueryDisplayAttribEXT',None)
            if qda is None:
                egl.eglTerminate(dpy)
                continue
            qda.restype=ctypes.c_int
            qda.argtypes=[ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
            assoc=ctypes.c_void_p()
            if not qda(dpy, EGL_DEVICE_EXT, ctypes.byref(assoc)):
                egl.eglTerminate(dpy)
                continue
            if assoc.value != devices[i].value:
                egl.eglTerminate(dpy)
                continue
            display_ext=egl.eglQueryString(dpy, EGL_EXTENSIONS)
            display_ext=display_ext.decode('utf-8','replace') if display_ext else ''
            if any(name not in display_ext for name in REQUIRED_DISPLAY_EXTENSIONS):
                egl.eglTerminate(dpy)
                continue
            qf=getattr(egl,'eglQueryDmaBufFormatsEXT',None)
            qm=getattr(egl,'eglQueryDmaBufModifiersEXT',None)
            ci=getattr(egl,'eglCreateImageKHR',None)
            di=getattr(egl,'eglDestroyImageKHR',None)
            if qf is None or qm is None or ci is None or di is None:
                egl.eglTerminate(dpy)
                continue
            qf.restype=ctypes.c_int
            qf.argtypes=[ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
            qm.restype=ctypes.c_int
            qm.argtypes=[ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
            num_formats=ctypes.c_int(0)
            if not qf(dpy, 0, None, ctypes.byref(num_formats)):
                egl.eglTerminate(dpy)
                continue
            max_formats=min(num_formats.value, 64)
            formats=(ctypes.c_int*max_formats)()
            got_formats=ctypes.c_int(0)
            if not qf(dpy, max_formats, formats, ctypes.byref(got_formats)):
                egl.eglTerminate(dpy)
                continue
            if FOURCC_ARGB8888 not in [formats[j] for j in range(got_formats.value)]:
                egl.eglTerminate(dpy)
                continue
            num_mods=ctypes.c_int(0)
            if not qm(dpy, FOURCC_ARGB8888, 0, None, None, ctypes.byref(num_mods)):
                egl.eglTerminate(dpy)
                continue
            max_mods=min(num_mods.value, 64)
            mods=(ctypes.c_uint64*max_mods)()
            ext_only=(ctypes.c_int*max_mods)()
            got_mods=ctypes.c_int(0)
            if not qm(dpy, FOURCC_ARGB8888, max_mods, mods, ext_only, ctypes.byref(got_mods)):
                egl.eglTerminate(dpy)
                continue
            linear_ok=False
            for j in range(got_mods.value):
                if mods[j] == MODIFIER_LINEAR and ext_only[j] == 0:
                    linear_ok=True
            egl.eglTerminate(dpy)
            if not linear_ok:
                continue
            return {'status':'ANALYSIS','phase':'CONSUMER_SELECTION','render_node':render,'pci':pci,'vendor':vendor,'observed_devices':observed_devices,'argb8888_linear_external_only_false':True,'required_extensions_present':True}
        return {'status':'NOT_CHECKED2','phase':'CONSUMER_SELECTION','reason':'requested NVIDIA EGL device or ARGB8888 LINEAR external_only=false not found','observed_devices':observed_devices}
    except Exception as exc:
        return {'status':'NOT_CHECKED2','phase':'CONSUMER_SELECTION','reason':'consumer probe exception','detail':str(exc)}

def main():
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(OUTER_TIMEOUT_S)
    ap=argparse.ArgumentParser(prog='intel_device_nv_egl_consumer_fixture', add_help=False)
    ap.add_argument('--contract')
    ap.add_argument('--mode')
    ap.add_argument('--admission')
    ap.add_argument('--nv-pci')
    ap.add_argument('--probe-consumer', action='store_true')
    args, unknown=ap.parse_known_args()
    if unknown:
        not_checked('CLI','unknown arguments: '+','.join(unknown), 'NO_DEFAULT')
        return 5
    if not args.admission:
        refuse('PREP_ONLY','missing --admission; ROOT exact-pin admission required')
        return 4
    if args.admission != 'ROOT_EXACT_PIN_ADMIT':
        refuse('PREP_ONLY','admission token not recognized')
        return 4
    if args.probe_consumer:
        if not args.nv_pci:
            not_checked('CONSUMER_SELECTION','--nv-pci required for actual bounded consumer probe', 'NO_DEFAULT')
            return 7
        res=probe_selected_nvidia_consumer(args.nv_pci)
        emit(res)
        return 0 if res.get('status') == 'ANALYSIS' else 8
    if not args.contract or not args.mode:
        not_checked('CLI','--contract and --mode are required before any GPU phase', 'NO_DEFAULT')
        return 5
    if args.mode not in ('baseline','corrupt'):
        not_checked('CLI','mode must be baseline or corrupt', 'NO_DEFAULT')
        return 5
    vals=parse_contract(args.contract)
    if vals is None:
        not_checked('CONTRACT','contract file unreadable', 'NOT_CHECKED2')
        return 6
    missing,errors=validate_contract(vals)
    if missing:
        not_checked('CONTRACT','missing reviewed contract metadata fields: '+','.join(missing), 'NOT_CHECKED2')
        return 6
    if errors:
        not_checked('CONTRACT','contract metadata rejected: '+','.join(errors), 'NOT_CHECKED2')
        return 6
    # The contract file is externally reviewed metadata, but strings alone do not bind to actual
    # Intel allocation/driver identities or prove producer->consumer cache visibility. The actual
    # Level Zero export properties do not supply DRM FourCC, pitch, offset, modifier or compression.
    # Therefore no allocation, import, producer write, or consumer readback is attempted here.
    not_checked('PRODUCER_CONSUMER_SYNC_BRIDGE','contract syntax accepted but actual sync bridge and exporter layout proof are unavailable; GPU phase isolated and not launched', 'NOT_CHECKED2')
    return 0

if __name__ == '__main__':
    sys.exit(main())
# Runtime dependency check

ROOT ran the installed MSVC 14.51 `dumpbin.exe /DEPENDENTS` against the unchanged model fixture `d9034fe8011c6792110c066e9c4e3d92931960d4e48eec64aeca2c1534bf44c4`. The metadata command exited zero.

Its direct imports include `llama.dll`, `ggml.dll`, `ggml-base.dll`, BCrypt, Kernel32, the MSVC runtime and Windows CRT API sets. A fresh runtime folder therefore needs an explicitly pinned `llama.dll` in addition to the five fresh ggml libraries. The original same-commit `records/build_vulkan_real/build/bin/llama.dll` is 2,748,416 bytes with SHA256 `7f6b7a586de8fa97c0ecf0a23a0e2663e0c7df1a6633c41b723d91071da3e982`.

This import-table observation does not prove the fresh libraries' ABI or their loaded identity. Compare exports and imports after the build and observe actual loaded DLL paths and hashes through the retained runtime process handle. No model/GPU execution occurred in this dependency check.

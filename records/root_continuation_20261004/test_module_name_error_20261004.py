"""Pure regression for Win32 module enumeration; no WinDLL calls or processes."""
import importlib.util
import os
import types
import unittest

path = os.environ["JLINK_RUNTIME_HELPER_TEST_PATH"]
spec = importlib.util.spec_from_file_location("runtime_probe_under_test", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ModuleNameTests(unittest.TestCase):
    def probe(self, returned):
        p = m.Modules.__new__(m.Modules)
        def enum(handle, entries, size, needed):
            entries[0] = 4
            needed._obj.value = m.ctypes.sizeof(m.wintypes.HMODULE)
            return 1
        p.enum = enum
        p.name = lambda handle, entry, buffer, length: returned
        return p

    def test_zero_api_result_is_oserror(self):
        with self.assertRaises(OSError):
            self.probe(0).paths(types.SimpleNamespace(_handle=123))

    def test_truncated_path_remains_refused(self):
        with self.assertRaises(ValueError):
            self.probe(32768).paths(types.SimpleNamespace(_handle=123))

if __name__ == "__main__":
    unittest.main(verbosity=2)

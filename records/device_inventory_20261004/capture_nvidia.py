import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone
root = Path(__file__).resolve().parent
command = [r'C:\Windows\System32\nvidia-smi.exe', '--query-gpu=pci.bus_id,name,memory.total,memory.free,memory.used,uuid', '--format=csv,nounits']
start = datetime.now(timezone.utc)
p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
try:
    out, err = p.communicate(timeout=60)
except subprocess.TimeoutExpired:
    p.kill()
    out, err = p.communicate(timeout=10)
end = datetime.now(timezone.utc)
(root / 'nvidia_actual.csv').write_bytes(out)
(root / 'nvidia.stderr.log').write_bytes(err)
sample = {'vendor': 'nvidia', 'tool': 'nvidia-smi', 'tool_version': 'driver 591.86 from prior independent inventory', 'sampled_at_utc': start.isoformat(), 'capture_completed_utc': end.isoformat(), 'exit_code': p.returncode, 'format': 'csv', 'stdout': out.decode(), 'memory_kind': 'DEDICATED', 'classification_basis': 'Independent Windows PNP and OpenCL inventory identify actual discrete RTX5070Ti; not inferred from parser', 'command': command, 'pid': p.pid, 'binary_sha256': hashlib.sha256(Path(command[0]).read_bytes()).hexdigest()}
(root / 'nvidia_capture.json').write_text(json.dumps(sample, indent=2) + '\n')
print(json.dumps(sample))

"""Stage a separately attributed narrow repair; never alter provider artifacts."""
import ast
import datetime
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'records/factory_runs/20261004/layer_diagnostic_20261004T144323Z/grok_capture_edit/capture_comparator.grok_corrected.py'
EXPECTED = '2786a0213039cdeb1654dd1de7688e9f628672a963355fcfef6ebe94cba87495'
TARGET = Path(__file__).parent / 'capture_comparator_root_repair'


def main():
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED
    text = raw.decode('utf-8')
    substitutions = [
        (
            'if suffix.isdigit() and str(int(suffix)) == suffix and 0 <= int(suffix) <= 27:',
            'if suffix in {str(layer) for layer in range(28)}:',
        ),
        (
            '    if len(set(devices)) != len(devices):\r\n        raise CaptureError("Bad expected devices")\r\n    for device in devices:\r\n        if type(device) is not str or device not in ("Vulkan0", "Vulkan1"):\r\n            raise CaptureError("Bad expected devices")',
            '    for device in devices:\r\n        if type(device) is not str or device not in ("Vulkan0", "Vulkan1"):\r\n            raise CaptureError("Bad expected devices")\r\n    if len(set(devices)) != len(devices):\r\n        raise CaptureError("Bad expected devices")',
        ),
    ]
    for before, after in substitutions:
        assert text.count(before) == 1, 'Expected unique source edit'
        text = text.replace(before, after, 1)
    ast.parse(text)
    TARGET.mkdir(exist_ok=False)
    output = TARGET / 'capture_comparator.py'
    output.write_bytes(text.encode('utf-8'))
    diff = ''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True), text.splitlines(True),
                                        fromfile='grok_2786_preserved', tofile='root_repair'))
    (TARGET / 'root_repair.diff').write_text(diff, encoding='utf-8', newline='')
    provenance = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'provider_source': str(SOURCE.relative_to(ROOT)), 'provider_sha256': EXPECTED,
                  'root_source': str(output.relative_to(ROOT)),
                  'root_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                  'attribution': 'ROOT narrow repair derived from actual Grok edit; no new provider job',
                  'changes': ['Validate device item types before set() so malformed nested objects raise CaptureError.',
                              'Use exact 28 canonical suffix strings without unbounded integer conversion.'],
                  'admission': 'AST_ONLY_PENDING_INDEPENDENT_SYNTHETIC_CONTROLS',
                  'limitations': ['No opened-handle fstat identity check; bounded reads and static component checks do not certify dynamic filesystem races.',
                                  'No complete C++ capture candidate, native tensor capture or GPU/model qualification.']}
    with (TARGET / 'provenance.json').open('x', encoding='utf-8') as out:
        json.dump(provenance, out, indent=2)
        out.write('\n')
    print(json.dumps({'source': str(output), 'sha256': provenance['root_sha256'], 'scope': provenance['admission']}))


if __name__ == '__main__':
    main()

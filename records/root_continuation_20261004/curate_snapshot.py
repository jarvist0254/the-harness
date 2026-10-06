"""Create a new bounded integrity snapshot; never rewrite either frozen manifest.

This script hashes evidence, including refused candidates. It does not admit code,
authenticate provider receipts, run hardware, or certify the full project goal.
"""
import datetime
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'records/ADAPTATION_SHA256_20261004_FULL_CONTINUATION.json'
TEXT_SUFFIXES = {'.json', '.jsonl', '.journal', '.md', '.py', '.cpp', '.h', '.diff', '.log', '.txt', '.cmd', '.ps1', '.svg', '.png', '.fcstd', '.step'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    if TARGET.exists():
        raise FileExistsError('Frozen continuation snapshot already exists; choose a new dated snapshot.')
    earlier = json.loads((ROOT / 'records/ADAPTATION_SHA256_20261004.json').read_text(encoding='utf-8-sig'))
    paths = {ROOT / entry['path'] for entry in earlier['files']}
    for relative in ['README.md', 'docs/08_VENDOR_DEVELOPER_TOOLS.md', 'docs/09_FULL_GOAL_GATE_REGISTER.md',
                     'cad/README.md', 'cad/integrated_core.py', 'cad/tests/test_integrated_layout.py', 'cad/tests/test_gap_posts.py',
                     'j_link/device_inventory.py', 'j_link/tests/test_device_inventory.py',
                     'records/PACKAGE_SHA256.json', 'records/ADAPTATION_SHA256_20261004.json']:
        paths.add(ROOT / relative)
    for relative in [
        'records/root_continuation_20261004', 'records/provider_quality_review',
        'records/device_inventory_20261004', 'records/cad_draft_20261004',
        'records/vulkan_llm_qualification_20261004',
        'records/vendor_cli_qualification_20261004/native_hip',
        'records/factory_runs/20261004/full_fabric_continuation_20261004T113400Z',
        'records/factory_runs/20261004/supervision_qualification_20261004T121303Z',
        'records/factory_runs/20261004/coherent_repair_kv_20261004T130000Z',
        'records/factory_runs/20261004/bool_cleanup_repair_20261004T135000Z',
        'records/factory_runs/20261004/layer_diagnostic_20261004T144323Z',
        'records/factory_runs/20261004/fp32_staging_repair_20261004T153127Z',
    ]:
        for path in (ROOT / relative).rglob('*'):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and '__pycache__' not in path.parts:
                # Public provider prompts/code are covered by credential audits;
                # credential configuration, executables, model weights and toolchains
                # are outside this text/draft snapshot's scope.
                paths.add(path)
    for relative in ['records/compute_benchmarks_opencl_20261004/acceptance.json',
                     'records/compute_benchmarks_opencl_20261004/dirty_baseline.json']:
        paths.add(ROOT / relative)
    entries = []
    for path in sorted(paths, key=lambda p: str(p).lower()):
        path = path.resolve()
        relative = path.relative_to(ROOT).as_posix()
        if not path.is_file():
            raise FileNotFoundError(relative)
        entries.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': digest(path)})
    manifest = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Curated continuation code/docs, draft CAD and text/provider/test evidence. Includes rejected candidates and failures; hash validity is not acceptance. Excludes model weights, executables, toolchains, credential configuration, caches and external projects. Separate import-content audit identifies authorized changes and Git-index metadata variance. Earlier manifests are frozen and included by hash.',
        'files': entries,
    }
    with TARGET.open('x', encoding='utf-8') as destination:
        json.dump(manifest, destination, indent=2)
        destination.write('\n')
    print(json.dumps({'manifest': str(TARGET), 'files': len(entries)}, indent=2))


if __name__ == '__main__':
    main()

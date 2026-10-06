"""Re-measure immutable import inventory against explicitly declared changes."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREVIOUS = Path(__file__).parent / 'import_content_audit_20261004T132200Z.json'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    baseline = ROOT / 'records/PACKAGE_SHA256.json'
    manifest = json.loads(baseline.read_text(encoding='utf-8-sig'))
    previous = json.loads(PREVIOUS.read_text(encoding='utf-8-sig'))
    declared = {row['path']: row['classification'] for row in previous['changes']}
    changes, missing, unexpected = [], [], []
    unchanged = 0
    for entry in manifest['files']:
        relative = entry['path']
        path = ROOT / relative
        if not path.is_file():
            missing.append(relative)
            continue
        current = sha(path)
        if current == entry['sha256']:
            unchanged += 1
        else:
            classification = declared.get(relative, 'UNEXPECTED_CONTENT_CHANGE')
            row = {'path': relative, 'classification': classification,
                   'import_sha256': entry['sha256'], 'current_sha256': current}
            changes.append(row)
            if classification == 'UNEXPECTED_CONTENT_CHANGE':
                unexpected.append(row)
    passed = not missing and not unexpected and sha(baseline) == previous['import_manifest_sha256']
    receipt = {
        'created_utc': now.isoformat(), 'import_manifest_sha256': sha(baseline),
        'declared_changes_source': str(PREVIOUS.relative_to(ROOT)),
        'checked': len(manifest['files']), 'unchanged': unchanged,
        'missing': missing, 'changes': changes, 'unexpected_content_changes': unexpected,
        'status': 'CONTENT_PRESERVED_WITH_DECLARED_ADAPTATION_AND_GIT_METADATA_VARIANCE' if passed else 'FAIL',
        'limitations': [
            'Three declared Git index files may differ; cause is not independently established. No Git index restoration or mutation is performed.',
            'Extra derived local artifacts are outside the import inventory and require their own curated snapshot.',
            'Integrity is not hardware/model/CAD or full-goal qualification.',
        ],
    }
    target = Path(__file__).parent / ('import_content_audit_' + now.strftime('%Y%m%dT%H%M%SZ') + '.json')
    with target.open('x', encoding='utf-8') as out:
        json.dump(receipt, out, indent=2)
        out.write('\n')
    print(json.dumps({'receipt': str(target), 'checked': receipt['checked'],
                      'unchanged': unchanged, 'changes': len(changes), 'missing': len(missing),
                      'unexpected': len(unexpected), 'status': receipt['status']}, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())

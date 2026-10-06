import hashlib
import json
from pathlib import Path
import time
import urllib.request

destination = Path(r'E:\the_harness\records\toolchains\intel_sycl')
destination.mkdir(parents=True, exist_ok=True)
meta_path = Path(__file__).resolve().parent / 'intel_llvm_recent_releases.json'
releases = json.loads(meta_path.read_text(encoding='utf-8-sig'))
release = next(r for r in releases if r['tag_name'] == 'nightly-2026-10-04')
asset = next(a for a in release['assets'] if a['name'] == 'sycl_windows.tar.gz')
signature = next(a for a in release['assets'] if a['name'].endswith('.sigstore.json'))
provenance = {'release_url': release['html_url'], 'tag': release['tag_name'],
              'archive_url': asset['browser_download_url'], 'advertised_bytes': asset['size'],
              'api_digest': asset.get('digest'), 'signature_url': signature['browser_download_url'],
              'signature_verification': 'NOT_CHECKED_NO_SIGSTORE_VERIFIER',
              'status': 'DOWNLOADING'}
(destination / 'provenance.json').write_text(json.dumps(provenance, indent=2))
for entry in [asset, signature]:
    target = destination / entry['name']
    if target.exists():
        raise RuntimeError('Refusing to overwrite existing download')
    partial = target.with_suffix(target.suffix + '.partial')
    start = time.monotonic()
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(entry['browser_download_url'], timeout=30) as response, partial.open('xb') as stream:
        while True:
            if time.monotonic() - start > 60:
                raise TimeoutError('Download exceeded 60 second bound')
            block = response.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > entry['size']:
                raise ValueError('Downloaded bytes exceed official metadata size')
            digest.update(block)
            stream.write(block)
    if total != entry['size']:
        raise ValueError('Download size mismatch')
    expected = entry.get('digest')
    if expected and expected != 'sha256:' + digest.hexdigest():
        raise ValueError('GitHub API digest mismatch')
    partial.rename(target)
    provenance[entry['name']] = {'bytes': total, 'sha256': digest.hexdigest(), 'api_digest_matches': bool(expected), 'seconds': time.monotonic() - start}
    print(json.dumps(provenance[entry['name']]), flush=True)
provenance['status'] = 'DOWNLOADED_HASHED_NOT_EXTRACTED'
(destination / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')

"""Read-only root check of the five recorded native cases; launches no processes."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / 'supervisor_native_fixture_revision2'
RUN = FIXTURE / 'native_runs/native_20261004T144031Z'
SOURCE_HASH = '3cb1e44e35ea6c2ef9c01e0d329fb0df98c7785056d65e33ced52ec04706e51c'
RECEIPT_HASH = '462f36fc76e44f2ba037f31209c8abfac51107fc10ab95b5c194a95ab4aac85e'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    receipt_path = RUN / 'suite_receipt.json'
    suite = read(receipt_path)
    admission = read(FIXTURE / 'fixture_admission.json')
    assert sha(receipt_path) == RECEIPT_HASH
    assert suite['source_sha256'] == SOURCE_HASH == sha(Path(suite['source']))
    assert sha(Path(suite['interpreter'])) == admission['runtime']['sha256']
    for filename, expected in admission['fixture_hashes_sha256'].items():
        assert sha(FIXTURE / filename) == expected, filename
    assert suite['overall'] == 'FIXTURE_EXPECTATIONS_MET'
    expectations = [('natural', 'PROCESS_COMPLETED', '', 4), ('nonzero', 'FAILED', 'nonzero_exit', 1),
                    ('timeout', 'TIMEOUT', 'deadline', 1), ('cancel', 'CANCELLED', 'cancelled', 1),
                    ('overflow', 'FAILED', 'LOG_LIMIT', 1)]
    assert [case['case_id'] for case in suite['cases']] == [item[0] for item in expectations]
    results = []
    for case, (name, status, reason, count) in zip(suite['cases'], expectations):
        supervisor = case['supervisor']
        assert case['controller_exit_code'] == 0 and case['controller_timeout'] is False
        assert case['controller_pid_absent_after_wait'] is True
        assert case['worker_pids_absent_after_cleanup'] is True
        assert case['capture_limit_ok'] is True and 'outer_failure' not in case
        assert 0 < case['controller_elapsed_seconds'] < 30
        assert case['source_and_runtime_hashes_unchanged'] is True
        assert case['source_and_runtime_hashes_before'] == case['source_and_runtime_hashes_after']
        assert supervisor['status'] == status and supervisor['failure_reason'] == reason
        assert supervisor['run_id'] == 'native_' + name
        assert supervisor['job_active_count'] == 0 and supervisor['drain_proof'] == 'CLEANUP'
        assert supervisor['whole_tree_certificate'] is False
        assert supervisor['reattach'] is False and supervisor['replay'] is False
        workers = supervisor['workers']
        assert len(workers) == count
        assert all(worker['assigned'] is True and worker['resumed'] is True for worker in workers)
        assert [worker['pid'] for worker in workers] == case['worker_pids']
        assert len(set(case['worker_pids'])) == count
        assert case['restart_matches'] is True and case['restart_commit_verified'] is True
        assert case['restart_receipt'] == supervisor
        output = RUN / name / 'supervisor_output'
        assert read(output / ('native_' + name + '_receipt.json')) == supervisor
        for worker in workers:
            logged = supervisor['logs'][worker['worker_id']]
            for stream in ('stdout', 'stderr'):
                raw = (output / logged[stream + '_path']).read_bytes()
                assert len(raw) == logged[stream + '_bytes'] <= 1024
                assert raw.decode('utf-8') == logged[stream]
            if name == 'natural':
                assert worker['exit_code'] == 0
                assert logged['stdout'].strip() == worker['worker_id'] + ':stdout'
                assert logged['stderr'].strip() == worker['worker_id'] + ':stderr'
            elif name == 'nonzero':
                assert worker['exit_code'] == 3
            elif name in ('timeout', 'cancel'):
                assert logged['stdout'].strip() == worker['worker_id'] + ':sleeping'
            else:
                assert logged['stdout_overflow'] is True and logged['stdout_bytes'] == 1024
                assert logged['stdout'] == 'X' * 1024
        results.append({'case_id': name, 'accepted': True, 'status': status, 'failure_reason': reason,
                        'elapsed_seconds': case['controller_elapsed_seconds'], 'workers': count,
                        'raw_accepted_type': type(case['accepted']).__name__})
    now = datetime.datetime.now(datetime.timezone.utc)
    target = HERE / ('native_revision2_root_adjudication_' + now.strftime('%Y%m%dT%H%M%SZ') + '.json')
    result = {'utc': now.isoformat(), 'source_sha256': SOURCE_HASH,
              'raw_receipt': str(receipt_path), 'raw_receipt_sha256': RECEIPT_HASH,
              'scope': 'ROOT_RECHECKED_FIVE_RECORDED_NATIVE_CPU_FIXTURES_ONLY',
              'cases': results, 'production_admission': False, 'native_calls_by_adjudicator': 0,
              'limitations': ['PID absence is the recorded point-in-time check, not a new live query.',
                              'The driver returned lists instead of bool for timeout/cancel; all gates were recomputed from raw fields without using their truthiness.',
                              'Descendant escape, controller loss, high-water resource use and production recovery remain unqualified.']}
    with target.open('x', encoding='utf-8') as out:
        json.dump(result, out, indent=2)
        out.write('\n')
    print(json.dumps({'receipt': str(target), 'cases': len(results), 'status': 'FIXTURE_GATES_RECOMPUTED_PASS'}))


if __name__ == '__main__':
    main()

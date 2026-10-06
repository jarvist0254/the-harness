from __future__ import annotations
import enum
import time
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, List
RESULT_NOT_CHECKED='NOT_CHECKED'
RESULT_FAIL='FAIL'
RESULT_READY='DECLARED_PROTOCOL_READY'
DIRECT_TRANSPORT_QUALIFIED=False
UNKNOWN_DRAIN='UNKNOWN_DRAIN'
CURRENT_SNAPSHOT_RESULT='NOT_CHECKED'
class FdKind(enum.Enum):
    MEMORY_DMA_BUF='MEMORY_DMA_BUF'
    SEMAPHORE_SYNCOBJ='SEMAPHORE_SYNCOBJ'
    SYNC_FILE='SYNC_FILE'
    UNKNOWN='UNKNOWN'
class FdState(enum.Enum):
    ORIGINAL_BORROWED='ORIGINAL_BORROWED'
    CONSUMED_BEFORE_STATUS='CONSUMED_BEFORE_STATUS'
    CONSUMED_ON_SUCCESS='CONSUMED_ON_SUCCESS'
    RETAINED_ON_FAILURE='RETAINED_ON_FAILURE'
    RETAINED_FD0='RETAINED_FD0'
    DUPLICATE='DUPLICATE'
@dataclass(frozen=True)
class NativeOutcome:
    ok: bool
    error_code: int = 0
    message: str = ''
    timed_out: bool = False
    unknown_inflight: bool = False
    observed_fd_consumed: Optional[bool] = None
    payload_visible: Optional[bool] = None
@dataclass(frozen=True)
class FdToken:
    fd: int
    kind: FdKind
    owner: str
    duplicate: bool = False
    original_fd: Optional[int] = None
    state: FdState = FdState.ORIGINAL_BORROWED
@dataclass(frozen=True)
class Binding:
    physical_id: str
    driver_build: str
    source_commit: str
    operation_id: str
    payload_id: str
    controller_id: str
    producer_fault_control: str
    original_cpu_reference: str
@dataclass
class Prerequisites:
    root_admission: bool = False
    pinned_source_receipt: bool = False
    independent_native_admission: bool = False
    kernel_syncobj_to_sync_file_abi: Optional[str] = None
    nvidia_egl_native_fence_import: Optional[str] = None
    cache_visibility_contract: Optional[str] = None
    producer_completion_receipt: Optional[str] = None
    consumer_completion_proof: Optional[str] = None
    outer_worker_owned: bool = False
    def missing(self) -> List[str]:
        miss: List[str] = []
        if not self.root_admission:
            miss.append('root_admission')
        if not self.pinned_source_receipt:
            miss.append('pinned_source_receipt')
        if not self.independent_native_admission:
            miss.append('independent_native_admission')
        if not self.kernel_syncobj_to_sync_file_abi:
            miss.append('kernel_syncobj_to_sync_file_abi')
        if not self.nvidia_egl_native_fence_import:
            miss.append('nvidia_egl_native_fence_import')
        if not self.cache_visibility_contract:
            miss.append('cache_visibility_contract')
        if not self.producer_completion_receipt:
            miss.append('producer_completion_receipt')
        if not self.consumer_completion_proof:
            miss.append('consumer_completion_proof')
        if not self.outer_worker_owned:
            miss.append('outer_worker_owned')
        return miss
@dataclass
class Callbacks:
    memory_import: Callable[[FdToken, float], NativeOutcome]
    semaphore_import: Callable[[FdToken, float], NativeOutcome]
    producer_completion_wait: Callable[[float], NativeOutcome]
    syncobj_host_signal: Callable[[float], NativeOutcome]
    syncobj_export_sync_file: Callable[[float], NativeOutcome]
    egl_import_sync_file: Callable[[FdToken, float], NativeOutcome]
    consumer_completion_wait: Callable[[float], NativeOutcome]
    readback: Callable[[float], NativeOutcome]
    cleanup_drain: Callable[[float], NativeOutcome]
def _clean(s: str) -> bool:
    return isinstance(s, str) and len(s) > 0 and not any(ch.isspace() for ch in s)
class ProtocolAdapter:
    def __init__(self, binding: Binding, prereqs: Prerequisites, callbacks: Callbacks, clock: Optional[Callable[[], float]] = None) -> None:
        self.binding = binding
        self.prereqs = prereqs
        self.callbacks = callbacks
        self.clock = clock or time.monotonic
        self.events: List[Dict[str, Any]] = []
        self.fd_states: Dict[int, FdToken] = {}
        self.producer_completion_proven = False
        self.consumer_completion_proven = False
        self.sync_file_token: Optional[FdToken] = None
        self.result = RESULT_NOT_CHECKED
        self.cleanup_state = 'NOT_ATTEMPTED'
        self.failures: List[str] = []
        self.missing = prereqs.missing()
        self.original_cpu_reference = binding.original_cpu_reference
    def _record(self, event: str, **data: Any) -> None:
        item: Dict[str, Any] = {'event': event}
        item.update(data)
        self.events.append(item)
    def _fail(self, reason: str) -> None:
        self.result = RESULT_FAIL
        self.failures.append(reason)
        self._record('FAIL', reason=reason)
    def _not_checked(self, reason: str) -> None:
        if self.result != RESULT_FAIL:
            self.result = RESULT_NOT_CHECKED
        self._record('NOT_CHECKED', reason=reason)
    def _remaining(self, deadline: float) -> float:
        return deadline - self.clock()
    def _deadline_exceeded(self, deadline: float) -> bool:
        return self.clock() > deadline
    def _validate_binding(self) -> bool:
        b = self.binding
        fields = [b.physical_id, b.driver_build, b.source_commit, b.operation_id, b.payload_id, b.controller_id, b.producer_fault_control, b.original_cpu_reference]
        if not all(_clean(x) for x in fields):
            self._fail('binding_fields_not_clean')
            return False
        if b.original_cpu_reference != self.original_cpu_reference:
            self._fail('original_cpu_reference_changed')
            return False
        return True
    def register_fd(self, token: FdToken) -> None:
        self.fd_states[token.fd] = token
        self._record('FD_REGISTERED', fd=token.fd, kind=token.kind.value, owner=token.owner, duplicate=token.duplicate, state=token.state.value)
    def observe_memory_import(self, token: FdToken, outcome: NativeOutcome) -> FdToken:
        if token.kind != FdKind.MEMORY_DMA_BUF:
            self._fail('wrong_fd_flavor_for_memory_import')
            return token
        if outcome.ok:
            new_state = FdState.CONSUMED_ON_SUCCESS
        else:
            new_state = FdState.RETAINED_ON_FAILURE
        if outcome.observed_fd_consumed is True and not outcome.ok:
            self._fail('memory_failure_unexpected_fd_consumed')
        if outcome.observed_fd_consumed is False and outcome.ok:
            self._fail('memory_success_unexpected_fd_retained')
        token = FdToken(token.fd, token.kind, token.owner, token.duplicate, token.original_fd, new_state)
        self.fd_states[token.fd] = token
        self._record('MEMORY_IMPORT_OBSERVED', fd=token.fd, ok=outcome.ok, state=token.state.value)
        return token
    def observe_semaphore_import(self, token: FdToken, outcome: NativeOutcome) -> FdToken:
        if token.kind != FdKind.SEMAPHORE_SYNCOBJ:
            self._fail('wrong_fd_flavor_for_semaphore_import')
            return token
        if token.fd > 0:
            new_state = FdState.CONSUMED_BEFORE_STATUS
        elif token.fd == 0:
            new_state = FdState.RETAINED_FD0
        else:
            self._fail('semaphore_fd_negative')
            return token
        if outcome.observed_fd_consumed is True and token.fd == 0:
            self._fail('fd0_unexpectedly_consumed')
        if outcome.observed_fd_consumed is False and token.fd > 0:
            self._fail('semaphore_fd_positive_not_consumed')
        token = FdToken(token.fd, token.kind, token.owner, token.duplicate, token.original_fd, new_state)
        self.fd_states[token.fd] = token
        self._record('SEMAPHORE_IMPORT_OBSERVED', fd=token.fd, ok=outcome.ok, state=token.state.value)
        return token
    def observe_completion(self, stage: str) -> bool:
        if stage == 'producer':
            if self.consumer_completion_proven:
                self._fail('reordered_completion')
                return False
            self.producer_completion_proven = True
            self._record('PRODUCER_COMPLETION_PROVEN')
            return True
        if stage == 'consumer':
            if not self.producer_completion_proven:
                self._fail('reordered_completion')
                return False
            self.consumer_completion_proven = True
            self._record('CONSUMER_COMPLETION_PROVEN')
            return True
        self._fail('unknown_completion_stage')
        return False
    def _cleanup(self, deadline: float, unknown: bool = False) -> None:
        if self.cleanup_state != 'NOT_ATTEMPTED':
            return
        rem = self._remaining(deadline)
        if rem <= 0:
            self.cleanup_state = UNKNOWN_DRAIN
            self._record('CLEANUP', state=UNKNOWN_DRAIN, reason='no_remaining_deadline')
            return
        outcome = self.callbacks.cleanup_drain(rem)
        if unknown or outcome.unknown_inflight or outcome.timed_out or not outcome.ok:
            self.cleanup_state = UNKNOWN_DRAIN
            if outcome.ok is False and not outcome.timed_out and not outcome.unknown_inflight:
                self._fail('cleanup_error:' + str(outcome.error_code))
        else:
            self.cleanup_state = 'DRAINED'
        self._record('CLEANUP', state=self.cleanup_state)
    def _call(self, name: str, fn: Callable[..., NativeOutcome], deadline: float, *args: Any, fail_on_error: bool = True) -> Optional[NativeOutcome]:
        rem = self._remaining(deadline)
        if rem <= 0:
            self._not_checked('deadline_before_' + name)
            self._cleanup(deadline, unknown=True)
            return None
        outcome = fn(*args, rem)
        if self._deadline_exceeded(deadline) or outcome.timed_out or outcome.unknown_inflight:
            self._record('TIMEOUT_UNKNOWN', op=name)
            self._cleanup(deadline, unknown=True)
            if self.result != RESULT_FAIL:
                self.result = RESULT_NOT_CHECKED
            return None
        if not outcome.ok:
            if fail_on_error:
                self._fail(name + '_error:' + str(outcome.error_code))
                return None
            return outcome
        return outcome
    def signal_syncobj(self, deadline: float) -> Optional[NativeOutcome]:
        if not self.producer_completion_proven:
            self._fail('premature_host_signal_before_producer_completion')
            return None
        return self._call('syncobj_host_signal', self.callbacks.syncobj_host_signal, deadline)
    def run(self, deadline: float, memory_fd: FdToken, semaphore_fd: FdToken) -> Dict[str, Any]:
        self.result = RESULT_NOT_CHECKED
        if deadline <= self.clock():
            self._fail('deadline_not_finite')
            return self.report()
        if not self._validate_binding():
            return self.report()
        if self.missing:
            self._not_checked('missing_prerequisites:' + ','.join(self.missing))
            return self.report()
        self.register_fd(memory_fd)
        self.register_fd(semaphore_fd)
        outcome = self._call('memory_import', self.callbacks.memory_import, deadline, memory_fd, fail_on_error=False)
        if outcome is None:
            return self.report()
        memory_fd = self.observe_memory_import(memory_fd, outcome)
        if not outcome.ok and self.result != RESULT_FAIL:
            self._fail('memory_import_error:' + str(outcome.error_code))
        if self.result == RESULT_FAIL:
            return self.report()
        outcome = self._call('semaphore_import', self.callbacks.semaphore_import, deadline, semaphore_fd, fail_on_error=False)
        if outcome is None:
            return self.report()
        semaphore_fd = self.observe_semaphore_import(semaphore_fd, outcome)
        if not outcome.ok and self.result != RESULT_FAIL:
            self._fail('semaphore_import_error:' + str(outcome.error_code))
        if self.result == RESULT_FAIL:
            return self.report()
        outcome = self._call('producer_completion_wait', self.callbacks.producer_completion_wait, deadline)
        if outcome is None:
            return self.report()
        if not outcome.payload_visible:
            self._not_checked('producer_completion_receipt_not_visible')
            return self.report()
        if not self.observe_completion('producer'):
            return self.report()
        outcome = self.signal_syncobj(deadline)
        if outcome is None:
            return self.report()
        outcome = self._call('syncobj_export_sync_file', self.callbacks.syncobj_export_sync_file, deadline)
        if outcome is None:
            return self.report()
        self.sync_file_token = FdToken(fd=-1, kind=FdKind.SYNC_FILE, owner='nvidia_egl_consumer', duplicate=False, original_fd=semaphore_fd.fd, state=FdState.DUPLICATE)
        self.register_fd(self.sync_file_token)
        outcome = self._call('egl_import_sync_file', self.callbacks.egl_import_sync_file, deadline, self.sync_file_token)
        if outcome is None:
            return self.report()
        outcome = self._call('consumer_completion_wait', self.callbacks.consumer_completion_wait, deadline)
        if outcome is None:
            return self.report()
        if not outcome.payload_visible:
            self._not_checked('consumer_completion_proof_not_visible')
            return self.report()
        if not self.observe_completion('consumer'):
            return self.report()
        outcome = self._call('readback', self.callbacks.readback, deadline)
        if outcome is None:
            return self.report()
        if not outcome.payload_visible:
            self._not_checked('readback_payload_not_visible')
            return self.report()
        self.result = RESULT_READY
        self._record('PROTOCOL_READY')
        return self.report()
    def report(self) -> Dict[str, Any]:
        return {'result': self.result, 'direct_transport_qualified': DIRECT_TRANSPORT_QUALIFIED, 'cleanup_state': self.cleanup_state, 'missing_prerequisites': self.missing, 'failures': list(self.failures), 'producer_completion_proven': self.producer_completion_proven, 'consumer_completion_proven': self.consumer_completion_proven, 'fd_states': {fd: token.state.value for fd, token in self.fd_states.items()}, 'original_cpu_reference': self.original_cpu_reference, 'binding': {'physical_id': self.binding.physical_id, 'driver_build': self.binding.driver_build, 'source_commit': self.binding.source_commit, 'operation_id': self.binding.operation_id, 'payload_id': self.binding.payload_id, 'controller_id': self.binding.controller_id, 'producer_fault_control': self.binding.producer_fault_control, 'original_cpu_reference': self.binding.original_cpu_reference}, 'events': list(self.events)}

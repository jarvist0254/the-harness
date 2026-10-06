#!/usr/bin/env python3
"""Pure capacity planning for contiguous, indivisible model blocks. No GPU I/O."""
import argparse
import json
from pathlib import Path


class PlanError(ValueError):
    pass


def number(value, label, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, int) or value < (1 if positive else 0):
        raise PlanError(f'{label} must be an integer MiB count >= {1 if positive else 0}')
    return value


def plan(spec):
    devices = spec.get('devices', [])
    blocks = spec.get('blocks', [])
    if not isinstance(devices, list) or not 1 <= len(devices) <= 64:
        raise PlanError('Supply 1–64 ordered devices')
    if not isinstance(blocks, list) or not 1 <= len(blocks) <= 1024:
        raise PlanError('Supply 1–1024 ordered indivisible blocks')
    seen = set()
    seen_aliases = set()
    budgets = []
    details = []
    for d in devices:
        physical = d.get('physical_id')
        alias = d.get('id')
        if not isinstance(physical, str) or not physical or not isinstance(alias, str) or not alias:
            raise PlanError('Each device needs nonempty id and physical_id')
        if physical in seen or alias in seen_aliases:
            raise PlanError('Duplicate physical device or backend alias; deduplicate before planning')
        seen.add(physical)
        seen_aliases.add(alias)
        free = number(d.get('free_mib'), f'{alias}.free_mib')
        reserve = number(d.get('reserve_mib', 0), f'{alias}.reserve_mib')
        workspace = number(d.get('workspace_mib', 0), f'{alias}.workspace_mib')
        budget = max(0, free - reserve - workspace)
        budgets.append(budget)
        details.append({'id': alias, 'physical_id': physical,
                        'vendor': d.get('vendor', 'unknown'), 'free_mib': free,
                        'reserve_mib': reserve, 'workspace_mib': workspace,
                        'budget_mib': budget})
    names = set()
    prefix = [0]
    for i, block in enumerate(blocks):
        name = block.get('id')
        if not isinstance(name, str) or not name or name in names:
            raise PlanError('Each block needs a unique nonempty id')
        names.add(name)
        size = number(block.get('memory_mib'), f'block[{i}].memory_mib', positive=True)
        if size > max(budgets):
            raise PlanError(f'Indivisible block {name} cannot fit any device budget')
        prefix.append(prefix[-1] + size)
    if prefix[-1] > sum(budgets):
        raise PlanError('Total block memory exceeds usable aggregate budget')

    # Dynamic programming allows empty devices and searches every contiguous split.
    # Minimize sum of squared device utilization; this is not a speed optimizer.
    states = {0: (0.0, [])}
    for budget in budgets:
        next_states = {}
        for start, (score, cuts) in states.items():
            for end in range(start, len(blocks) + 1):
                used = prefix[end] - prefix[start]
                if used > budget:
                    break
                penalty = (used / budget) ** 2 if budget else 0.0
                candidate = (score + penalty, cuts + [(start, end)])
                if end not in next_states or candidate[0] < next_states[end][0]:
                    next_states[end] = candidate
        states = next_states
    if len(blocks) not in states:
        raise PlanError('No contiguous partition fits this ordered topology despite aggregate capacity')
    _, cuts = states[len(blocks)]
    for detail, (start, end) in zip(details, cuts):
        used = prefix[end] - prefix[start]
        detail.update(blocks=[b['id'] for b in blocks[start:end]], block_memory_mib=used,
                      remaining_budget_mib=detail['budget_mib'] - used)
    return {'status': 'PLANNED_NOT_ALLOCATED', 'hypothetical': spec.get('hypothetical', True),
            'unit': 'MiB', 'objective': 'capacity balance, not execution speed',
            'block_memory_mib': prefix[-1], 'aggregate_free_mib': sum(d['free_mib'] for d in details),
            'aggregate_budget_mib': sum(budgets), 'devices': details,
            'limitations': ['No discovery, driver probe, allocator, leases or execution',
                            'memory_mib must include block weights and block-local KV/activation requirements',
                            'Extra embeddings/output/workspace must be represented explicitly',
                            'Free samples precede modeled reserves; do not double-subtract resident leases',
                            'Topology ordering is caller supplied; no transfer-time optimization']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec', type=Path)
    args = parser.parse_args()
    try:
        result = plan(json.loads(args.spec.read_text(encoding='utf-8-sig')))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(json.dumps({'status': 'REJECTED', 'reason': str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

# Repository Guidelines

## Project Structure & Module Organization

The installable package is under `src/pyre`. `cli.py` performs
side-effect-free source inspection and writes launch plans; `runner.py`
supervises exactly one target and records receipts. `hardware.py`,
`allocation.py`, and `topology.py` discover and budget resources;
`target_bootstrap.py` applies supported framework ceilings before Python user
code. `checkpoint.py`, `resume.py`, `durable_jsonl.py`, and `io_policy.py`
provide recovery and placement contracts. `rpc.py`, `service.py`, and
`gpu_context.py` implement the authenticated loopback warm-state service.
Runtime paths and interpreter selection belong in `settings.py`; never embed
a drive letter, username, CUDA version, model path, or token elsewhere.

Architecture and protocol rationale live in `docs/`. Examples must remain
small and synthetic. Generated runs, models, environments, logs, profiles,
receipts, and tokens are ignored and must not enter source control.

## Build, Test, and Development Commands

Install an editable development checkout with
`python -m pip install -e ".[dev]"`. Run `ruff check .` for linting, `pytest`
for the CPU-only suite, `python tools/check_patch_series.py` for staged patch
series, and `python -m build` for both wheel and source
distribution. A single test is
`pytest tests/test_resume.py::test_arbitrary_nesting_indexes_completed_tasks`.
Public CI also runs `python tools/sync_from_canonical.py --public-only`.

## Coding Style & Naming Conventions

Python requires 3.10 or newer. Ruff enforces pycodestyle, Pyflakes, import
sorting, pyupgrade, bugbear, and simplify rules from `pyproject.toml`; the line
length is 88. Use explicit protocol/schema version strings in durable JSON.
Errors that are meant for automation use stable uppercase codes.

## Testing Guidelines

The default test suite must not import Torch, allocate CUDA, start a persistent
service, or depend on NVIDIA hardware. GPU tests are opt-in and must
distinguish CUDA-required failure from CPU fallback. Routing tests must prove
that inspection never executes a target. Resume tests cover identity mismatch,
unexpected IDs, malformed journals, wrong-unit rows, and duplicate conflicts.

## Commit & Pull Request Guidelines

This extraction starts with no inherited Git history, so no prior commit
convention exists. Use concise imperative subjects. Pull requests must state
failure semantics and list exact verification commands. Accelerator claims
require transfer-inclusive end-to-end measurements, parity evidence, and the
input/hardware/package context needed to reproduce them.

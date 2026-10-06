# J-Link — JE Horizon Multi-GPU Software Fabric

## Definition

J-Link is the project name for the software layer that makes the physically separate CUDA devices behave like one managed local compute fabric. It is not NVIDIA NVLink and not a hardware interconnect product.

## Required device inventory

For every GPU, record at startup:

- CUDA device index and persistent UUID
- model name
- VRAM total/free
- compute capability
- measured host-to-device bandwidth
- measured device-to-host bandwidth
- peer-access matrix where supported
- temperature/power/utilization telemetry
- physical link assignment: E1 branch A/B/C/D or E4
- worker health and resident model state

Do not depend on Windows device-index order remaining stable after hardware changes. Key scheduling identity to PCI bus ID / UUID and maintain an explicit physical map.

## Scheduler policy

Primary policy is task parallelism:

- keep frequently used models resident
- route a job to a GPU with enough free VRAM before considering sharding
- prefer the 5070 Ti for compute-heavy jobs that benefit most from its faster cores, subject to its measured PCI_E4 x4 transfer behavior
- use 3060s for resident agent workers, evaluation, embeddings, auxiliary inference and independent training runs
- overlap CPU preparation and PCIe transfer with CUDA work

## Multi-GPU training

Supported as an experiment, not an assumption:

- PyTorch DDP for replicated-model training
- DeepSpeed/FSDP for memory-distributed experiments
- explicit gradient accumulation to reduce synchronization frequency when useful
- benchmark communication overhead through the real x4 topology

Do not assume GeForce peer-to-peer behavior. Detect it. If direct P2P is unavailable or slower, use pinned host memory and pipeline/gradient strategies that tolerate host staging.

## Unified API

Target J-Link abstractions:

- `devices()`
- `capabilities(device)`
- `reserve(device, vram_mb, purpose)`
- `launch(worker_spec)`
- `route(job_spec)`
- `benchmark_link(src, dst)`
- `health()`
- `drain(device)`
- `stop_all()`

## Benchmarks to persist

Per device:

- H2D GB/s
- D2H GB/s
- small-transfer latency
- sustained model-load time
- tokens/s for selected local models
- training step time on a fixed microbenchmark
- VRAM high-water mark
- thermal/power steady state

Per multi-GPU mode:

- DDP scaling efficiency
- all-reduce time
- pipeline bubble percentage
- host-staging overhead
- failure/recovery behavior when one worker is drained

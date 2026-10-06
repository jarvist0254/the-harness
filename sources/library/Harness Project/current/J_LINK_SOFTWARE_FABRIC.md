# J-Link — JE Horizon Multi-GPU Software Fabric

J-Link is the software/orchestration layer for one or more GPU pods. It is **not** NVLink and not a JTAG/J-Link debug probe.

## Physical naming

Each GPU receives a stable topology label:

- `POD1-A`
- `POD1-B`
- `POD1-C`

Future pod:

- `POD2-A`
- `POD2-B`
- `POD2-C`

The software maps these physical bay labels to GPU UUID/PCI bus ID at boot and warns if topology changes.

## Inventory record per GPU

Store:

- pod_id / bay_id
- PCI bus ID
- GPU UUID
- vendor/model
- VRAM total/free
- CUDA/runtime support
- negotiated PCIe generation/width
- measured H2D and D2H bandwidth
- temperature
- power
- utilization
- supported precision/memory modes

## Scheduling priorities

1. Keep models resident when practical.
2. Prefer independent tasks/agents over unnecessary synchronized multi-GPU jobs.
3. Place transfer-sensitive work on the best measured host link.
4. Keep training/evaluation/inference workers separately pinnable.
5. Treat every additional pod as another topology object, not as an assumed shared-memory extension.

## First-host topology

Pod 1 uses three CPU-root x4 branches from PCI_E1 bifurcation. The existing RTX 5070 Ti uses the separate chipset PCI_E4 x4 path. The scheduler should benchmark rather than assume equal effective bandwidth/latency.

## Multi-GPU training

Allowed after electrical/link validation:

- DDP
- DeepSpeed
- FSDP
- explicit model/pipeline sharding

Aggregate VRAM is a capacity inventory, not automatically one address space.

## Pod expansion

A second pod may later connect through:

- additional host PCIe lanes,
- an active PCIe switch/fabric,
- a second host joined over high-speed Ethernet,
- another qualified transport.

J-Link should abstract worker placement so the mechanical pod design does not hard-code the future transport.

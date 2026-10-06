# CPU fake contract plan for the measured Level Zero query

This independently authored C++ stub source is pending root review and has not been compiled or executed. It includes the pinned candidate through `LZQ_ACTUAL_SOURCE_PATH` and implements only synthetic Level Zero entry points; it does not load a Level Zero runtime or touch a device.

Planned discriminating cases cover: baseline query output parses as full JSON while transport qualification remains false; init, driver-enumeration, property, and peer-query errors preserve an explicit failure stage and exit code; unsupported external-memory, queue-group, and peer queries remain unknown/null rather than becoming positive; count growth between count and fill is refused; root and subdevice clamps are disclosed; duplicate driver rows are recorded as aliases; quote/backslash/control bytes in device names keep serialized JSON valid; and a small writer capacity cannot yield incomplete JSON paired with success.

The source-boundary concern is concrete: when the fixed output writer reaches capacity, later writes including truncation markers are suppressed, but the normal path may already have set exit code 0 and selected `PASS`. The test demands that partial output never be accepted as complete success. This control is intended to expose that mismatch if the fake run confirms it; no result is claimed yet.

This contract is synthetic API/serialization evidence only. It cannot prove hardware behavior, runtime support, external-memory import, or peer transfer. Root admission is required before compiling or executing this fake harness.

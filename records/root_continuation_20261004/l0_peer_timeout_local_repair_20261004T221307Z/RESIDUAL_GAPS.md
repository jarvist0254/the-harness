# Unqualified behavior outside the regression

This derivative corrects finite-wait explicit teardown and surplus/duplicate CLI handling only. It does not qualify the following pre-existing behavior: unbounded driver/device/group allocation counts; count mutation between query/list calls; skipped device/property/group query errors; actual root/subdevice identity (subdeviceId alone is not the official subdevice flag gate); constant payload and stale producer discrimination; real queue ownership, driver behavior or peer transport. These require separate source contracts and measured controls. They were not silently repaired.

Terminal quarantine avoids explicit Level Zero destruction and destructor callbacks after unconfirmed submission. Process exit/outer reaping is not proof of safe OS/driver GPU reclamation. CPU fake hostmalloc parity is not Intel device transfer or P2P.

The phase controller requires retained process reaping, readers joined, both EOF drains and no read/close errors. A single failure refuses capture. Phase-specific root-pinned admission binds helper/source/stub/object; run-only admission additionally binds final fake object/executable. Build-only compiles/link-inspects without executing the fake binary. WSLclient observation is not a general tree-containment certificate.

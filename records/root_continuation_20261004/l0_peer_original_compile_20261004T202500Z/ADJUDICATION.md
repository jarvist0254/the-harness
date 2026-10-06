# Original Intel peer candidate: compiler-only adjudication

**COMPILE_REFUSED_WITH_CLEANUP**. Exact source string extracted from strict duplicate-key-rejecting JSON with no trimming or source edits:9,995 UTF8 bytes, SHA f0e4d363396c2ac1744e3e7d9458120929f311d92cb8e31ba112b7c818f9bd22. Original over-budget intake REFUSED remains unchanged. Provider tests were not run. Nothing was linked or executed as candidate code.

Actual MSVC14.51 /c compile against official ze_api.h SHA c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de exited2. First primary diagnostic: source.original_untrusted.cpp:41 C2660 zeCommandQueueCreate: function does not take5 arguments. Header:3588–3593 declares context,device,descriptor,out_handle (4 arguments). Calls at41,47,50 incorrectly add queue ordinal as a separate third argument despite already setting descriptor.ordinal. All3 errors are the same independent API misuse, not downstream cascade types. Compiler produced no accepted object/executable.

Static safety defects in the exact extracted source:

* source16 serializes only uuid.id[0..3], each with8hex digits. Official header1979/1986 defines16 uint8_t UUID bytes. This creates a32-character string encoding only4bytes, losing96bits of identity and allowing distinct devices to collide. Must serialize all16 bytes with twohex digits each and compare actual full IDs; no current physical-device assertion is qualified.
* source15 destructor ignores every command-list/queue/memory/context cleanup API result. FenceDestroy at45/46/49/52 is also unchecked. Success JSON is printed at66 before State destructor executes, so cleanup failures cannot change printed success or exit0. Explicit checked cleanup before terminal receipt is necessary; no runtime was attempted here.
* source46 corruption fills entireB=65536bytes with DEADBEEF rather than perturbing one word. It is a broad negative control rather than the requested localized discriminator.
* source53 exits comparison at the first mismatch. A clean run traverses all16384 words, but failed runs cannot report a full mismatch count/full-array results; the report must avoid representing failed comparison as full counting.
* source24 treats any zeInit error as NOT_CHECKED, and enumeration source27 silently skips device API errors; these classifications would need documented unavailable-vs-real-runtime distinction before execution.

Owned compile evidence: pinned FA907 supervisor with exact0e529 adapter; one CMD root PID60788, assigned/resumed true, root exit2, supervisor FAILED/nonzero_exit, final Job active0/CLEANUP, no whole-tree certificate. Outer Python PID46652 exit0 (evidence-controller completed), reaped/handle signaled2.25s, no timeout/overflow/reader errors. Compiler failure is not obscured by outer-controller exit0. Source/header/tool/controller pins match before/after in attempt2_command_correction/compile_receipt.json. Raw actual diagnostics: attempt2_command_correction/contained_compile/compile.stdout.log.

First command-launch attempt is preserved separately: prequoted /c argument was escaped by subprocess.list2cmdline; CMD failed before compiler launch, exit1 with Job0/CLEANUP. This was an independently authored controller quoting defect, not candidate compiler evidence. attempt2 changes only confined command argument and output object location; source remains byte identical. ROOT independently already repaired the loader controller to343b...b167; old a809 preparation is historical and not current live code.

No SDK/driver/global PATH changes, DLL loading, GPU execution or runtime peer claims. The observed compile refusal and static defects justify one focused repair, not promotion of this proposal.

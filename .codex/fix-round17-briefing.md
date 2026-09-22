Goal and acceptance:
Round 17 for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade: cut the latency the player feels. The mod is functionally clean in game (a full session produced zero errors or warnings from our scripts) but its effects land late. Report in Traditional Chinese (code, identifiers, paths verbatim).

Evidence (.codex/smoke5-Papyrus.0.log, a real session on the current build, new save, CACO removed so the VM is far quieter than before):
  - The engine hit its suspended-stack warning threshold 9 times and dumped 3007 stacks. About 290 of them are ours.
  - In one dump: `Event: essbguard.OnHitEx, Frequency: 175` (another dump: 135), `Event: essbcontroller.OnWeaponHit, Frequency: 48` (another: 18), `ESSBFormPowerEffect.OnEffectStart, Frequency: 9`. Those are OUR events queued and not yet run.
  - 262 of our suspended stacks sit on exactly one line: `ESSBGuard.psc:89  Ctl.RefreshDivineProtection()` — a cross-script call made on EVERY incoming hit, before anything has been decided. 42 more sit at ESSBGuard.psc:75.
  - The rest of the queue belongs to other mods (SOS, Mus3BAddon, _EDQuest all hooking OnCrosshairRefChange, 84% of the total) — we cannot fix those, so our own path must be cheap enough to survive a busy queue.

Required outcome, in priority order:
  1. Incoming hits (ESSBGuard.OnHitEx) must cost nothing when nothing can happen. Decide with local, already-cached state before any cross-instance call: if no relevant node is owned and no window is active, return immediately. `RefreshDivineProtection` must not be called per hit — drive it from state changes (form open/close, sync stage change, node purchase, load, tick) and keep a Guard-local mirror of anything Guard needs to test.
  2. Outgoing hits (ESSBController.OnWeaponHit) must reach the damage application with as few yields as possible. In Papyrus a call into another script instance releases the caller's lock and can be queued, so what matters for felt latency is the number of CROSS-INSTANCE calls before the proc lands, not the total instruction count. Count them today for the review's representative hit (ESSBNodes / ESSBTrees / ESSBElem* lookups, Guard, Status host) and cut them: mirror what the hit path reads into controller-local cached values refreshed on change (rounds 12 and 16 already cache derived values — extend that to whatever still crosses), and move bookkeeping that does not affect this hit's damage to the per-second tick.
  3. Do not change gameplay behaviour, numbers, or the fixes from rounds 9-16. Damage, marks, reactions, kill attribution, real-time deadlines and the deferred-kill safety must all behave exactly as they do now.
  4. Measure with build/papyrus_harness.py and report a table: per hit (outgoing) and per incoming hit, the number of cross-instance calls, global reads, native calls and total scripted calls, before and after, plus the number of cross-instance calls that occur BEFORE the damage spell is applied. The representative outgoing hit is currently 165 scripted+native calls; report the new figure. State plainly if a reduction is not achievable somewhere and why.

Passing = `python build_v03.py` exits 0 with every existing check line ok (READBACK masters ['Skyrim.esm'], records == manifest, CSF 13/13, DELIVERY ok, LAYOUT ok, DOT ok, MCM ok, MCM DEFAULTS ok, SCHEMA ok, FIX10-FIX16 ok, PLAN COVERAGE 0 unmapped, all scripts 0 errors) plus a new check line proving the latency work (the call-count table asserted, and a regression that fails on .codex/pre-fix17-snapshot sources); versus .codex/pre-fix17-snapshot/v03-formids.json no existing FormID changes (ESSB_DebugLevel 0x000811) unless a member-variable change forces a state_schema_version bump — avoid one if you can, and if you cannot, bump per the round-9 rule and say why. You run the build yourself.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\*.esm and D:\Game\Other\SKSE\MO2\mods\** as the build needs; executing the PapyrusCompiler.exe that build_v03.py invokes is allowed.
  - Write set (exact): src/*.psc, build_v03.py, settings.json, state-schema.lock.json, build/*.py verification helpers, 實作紀錄.md (append only), build/** and package/Elements Spellblade/** (generated), .codex/impl-fix-round17.html (progress ledger; create first, update per item).
  - MUST NOT: write anything under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE (the game may be running); edit 元素魔戰士規劃-v0.3.md (record deviations instead), any review-*.md, .codex/pre-fix*-snapshot/** or .codex/post-fix*-snapshot/**, fx_extract.py, .strategic-advance/** (append-only commander ledger — never assert on its hash); add masters; introduce Utility.Wait loops, non-single RegisterForUpdate or per-frame polling; weaken any guard that rounds 9-16 added (stale instance, StateBroken, dead-target, once-only settlement); access the network.
  - MUST: keep file encodings and line endings as they are (build_v03.py is CRLF).

Background (MAY):
  - The user's VM is shared with mods that spam OnCrosshairRefChange; our events sit in the same queue, so every avoided yield shortens the felt delay.
  - review-fable-2026-09-19-r15.md section 2 item 5 already listed some avoidable per-hit work; round 16 fixed part of it.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

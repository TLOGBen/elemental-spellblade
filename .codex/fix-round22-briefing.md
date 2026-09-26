Goal and acceptance:
Round 22 = slice N3 for the Skyrim SE 1.5.97 mod 元素魔戰士 at D:\Game\Other\SKSE\.codex\elemental-spellblade (git clean at commit 175734c; N1, N2 and the v0.4 tree rebuild are committed and deployed). N3 moves the target status layer out of Papyrus into engine effects applied by the DLL. After this round every v0.4 row tagged "DLL N3" works as v0.4 says, and every node the tree rebuild left as LATER-N3 or PARTIAL-N3 is implemented (or explicitly reported with the reason it cannot be done in N3). Report in Traditional Chinese (台灣); code, identifiers and paths verbatim.

Read first:
- `元素魔戰士規劃-v0.4.md` (design truth; rows tagged DLL N3; section 2.7 formulas; section 9 staging rules; section 10.3).
- `design-latency-2026-09-20.md` section 6, row N3 and the "分期斷裂總檢" rule below the table (line ~399 and ~408).
- `build/native-verification-3.md` (engine capabilities for N3–N6, all verified offline; items 1–5, 9, 10, 14, 15 matter here; section 18 has the in-game probes N3-1, N3-2, N3-3, X1 to put on the probe card).
- `build/plan-coverage.json` and the node status table in `.codex/impl-fix-round21.html` (LATER-N3 / PARTIAL-N3 nodes and their stated gaps).
- Previous contracts and ledgers still in force: `.codex/fix-round20-briefing.md`, `.codex/fix-round21-briefing.md`, `.codex/impl-fix-round20.html`, `.codex/impl-fix-round21.html`, and `.strategic-advance/essb-standalone-build/CHECKPOINT.md`.

Context on quality: earlier implementers forced checks to pass, padded tests, left work half-done and recorded changes they never made. The last round recorded two fixes that were not in the files. Every claim in the ledger must be true in the files; re-grep before recording. What you cannot finish is reported, not papered over.

Commander rulings (binding):
  R1. No save migration; one state_schema_version bump this round is fine.
  R2. v0.4 text is the truth for numbers and effects; G(L) only where v0.4's formula says so. KEPT means equal to v0.4 text; approximations are PARTIAL with the gap stated.
  R3. Engine rules from native-verification-3: always Dispel(true) the old instance before re-applying the same spell (duration restarts — accepted); read stacks from `ActiveEffect::magnitude`, not GetMagnitude(); target effect lists only on the main thread; script stubs only on low-frequency effects that need an end-of-life settlement (marks, 白熱引信, 星痕, 死咒, 浮空) — per-hit reapplied effects use tick polling; tell expiry / dispel / death apart by elapsedSeconds ≥ duration and IsDead(), not kDispelled.
  R4. Staging (分期斷裂): a Papyrus path is deleted only in the slice whose DLL/engine representation goes live. N3 deletes the status container (ESSBStatus, registry, pending, swap), the difference patch ApplyProc and target-side Papyrus multipliers (now the DLL reads target effects), ESSBPoison/ESSBSpread where replaced, and the known ghost bug (poison 180 / astral 60 / wetlock 30 appearing on fresh NPCs, FormID-keyed, ignoring the master switch) must be gone with it. Self counters stay until N4; mark reactions (融斷 etc.) are triggered by ModEvent into the existing ESSBReactions Papyrus until N5; lightning N stays 1 until N4.
  R5. 浸濕 full-stack wash (v0.4, decided 2026-09-23): when soak newly reaches full stacks, dispel buffs on the target that were hand-cast (left/right hand caster), have a duration and are beneficial; exclude race powers, quest scripts, abilities, diseases, potions and this mod's own effects (native-verification-3 item 14 gives the test).
  R6. Domains (領域) are N6 (decided: Spawn Hazard for enemy effects + DLL tick for self effects). Do not rebuild them now; keep their current Papyrus behaviour working.
  R7. Anything that would change the design itself: collect in a list for the commander, keep going.

Required outcome:
  1. DLL applies and reads the status layer per the N3 row: open/refresh marks, ladders (rise / refresh / top tier incl. freeze and shatter true damage), poison read–stack–reapply via magnitude override without changing shared spells, 瘴氣 cloak, fire heat and 聖佑 self ladders, target-side multipliers read from target effects (difference patch removed), open-mark ×1.5, same-target 3-hit 聖裁 count if v0.4 assigns it to N3, discharge crit (N2 deferred it to N3), soak wash (R5). Expiry/death via the effect-removed event sink.
  2. Papyrus: status container and ApplyProc removed per R4; ESSBReactions still reached via ModEvent; nothing left reading removed state. The identity guard (`build/fix21_identity.py`) and history seal (`build/fix21_history.py` or a round-22 successor with the same sha256 binding) cover every change; do not weaken them.
  3. Node statuses updated in plan_coverage.py: each LATER-N3 / PARTIAL-N3 node becomes DONE, or stays with an explicit reason.
  4. Tests: native tests (reference model independent of the C++, engine-read wiring through the fake engine, injected faults) for the new status logic; Papyrus/offline checks for the removals; `python -B native/build.py` and `python build_v03.py` exit 0 with every check line ok and meaningful; zero entry-51 entries of ours.
  5. Probe card `build/fix22-probes.md` (style of build/fix21-probes.md: no log, short console commands, expected on-screen result, pass/fail, ~15 min) including native-verification-3 probes X1, N3-1, N3-2, N3-3 and one check per element's ladder/mark, plus "fresh NPC has no ghost statuses".
  6. `build/native-verification.md` round-22 section; 實作紀錄.md append with player-visible changes.

Permission boundary:
  - Read scope: everything under the repo; read-only D:\Game\Other\SKSE\SkyrimSE\** and D:\Game\Other\SKSE\MO2\mods\**. You may run python, the build, MSVC/CMake from the installed Visual Studio 2022, and read-only disassembly tools.
  - Write set: native/** (ours; dependencies stay pinned), src/*.psc, build_v03.py and the root generator modules (*.py), settings.json, state-schema.lock.json, build/*.py, build/** generated outputs, build/fix22-probes.md, build/native-verification.md (append), package/Elements Spellblade/** (generated), 實作紀錄.md (append only), .codex/pre-fix22-snapshot/** (take it FIRST: src, build_v03.py, root *.py, settings.json, state-schema.lock.json, build/v03-formids.json, build/plan-tree-nodes.json, build/plan-coverage.json, native/src, native/include, native/tests), .codex/impl-fix-round22.html.
  - MUST NOT: write under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE; edit 元素魔戰士規劃-v0.3*.md, 元素魔戰士規劃-v0.4.md, design-*.md, README.md, art-book/**, .strategic-advance/**, CLAUDE.md, build/tree-v04-inventory.md, build/native-verification-3.md; use git to commit, reset, checkout or stash; hook, trampoline, vtable-patch or write game memory; add ESP masters beyond Skyrim.esm; store design state in the DLL or add save serialization (state lives in engine effects).
  - MUST: keep encodings and line endings (build_v03.py CRLF; docs UTF-8 no BOM); crash guards (SEH + C++ catch) on every sink and task; take ledger times from the system clock; if v0.4 is ambiguous, pick the reading closest to intent, record it, keep going.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

When done, report (Traditional Chinese): VERDICT, per outcome 1–6 and ruling R1–R7 what you did, test counts and what they prove, node status counts before/after, what stays for N4/N5/N6, design questions for the commander, player-visible changes, files to review first.

Supervision (supervised long task):
  - Ledger: D:\Game\Other\SKSE\.codex\elemental-spellblade\.codex\impl-fix-round22.html (skeleton created by the commander; in your write set). Update after reading (short plan), after each milestone, after each build/test run (exit code), on blockers.
  - Milestones: (1) snapshot + plan (list every N3 row and LATER/PARTIAL-N3 node you will handle); (2) DLL status layer: effects/records, apply/read, removal sink, tests; (3) target-side multipliers in DLL, difference patch and status container removed from Papyrus, ModEvent reactions; (4) node-by-node N3 items incl. heat/聖佑 ladders, poison/瘴氣, discharge crit, soak wash; (5) tests, probe card, docs; (6) full build and report. If resumed, read the ledger and continue from the last completed milestone.

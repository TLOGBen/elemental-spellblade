Goal and acceptance:
Round 25 = slice N6, the last slice before "initial completeness", for the Skyrim SE 1.5.97 mod 元素魔戰士 at D:\Game\Other\SKSE\.codex\elemental-spellblade (git clean at commit e53f280; N1–N5 and the tree rebuild committed and deployed). N6 = the per-second timers, the hotkey input sink, and the domains (領域). After this round every v0.4 row tagged "DLL N6" works as v0.4 says, the remaining nodes (神聖領域 PARTIAL-N6, 毒霧 KEPT-待決) are resolved, and no gameplay logic that v0.4 assigns to the DLL is still running in a Papyrus per-second loop. Report in Traditional Chinese (台灣); code, identifiers and paths verbatim.

Read first:
- `元素魔戰士規劃-v0.4.md` (rows tagged DLL N6; §2.7; §2.9 domain table ~line 507: domains 3 m, 5 s, max 3 — the max-3 limit is lifted by the ruling below; §5 tree rows for 火域、冰原、地裂、泥沼、血池、聖域／神聖領域、毒霧、潮池、死域、星域; §10.3 incl. the hazard row ~line 1636 and the TrueHUD row).
- `design-latency-2026-09-20.md` §6 row N6 (~line 402).
- `build/native-verification-3.md` items 11 (background timer thread + one AddTask per tick), 12 (input event sink: main thread, before SKSE tasks in a frame), 13 (Spawn Hazard archetype MGEF cast via CastSpellImmediate: owner = caster, magnitude ours, engine handles lifetime and limit; hits only actors hostile to the caster; placed at an actor's feet; PlaceObjectAtMe hazards never expire — do not use), §18 probes N6-1, N6-2, N6-3.
- Contracts and ledgers in force: `.codex/fix-round20..24-briefing.md`, `.codex/impl-fix-round20..24.html`, `.strategic-advance/essb-standalone-build/CHECKPOINT.md`.

Context on quality: earlier implementers forced checks to pass, padded tests, left work half-done and recorded changes they never made; first builds of N3/N4/N5 each had a serious bug found only in review (DLL self-disable on first bleed; blood form unkillable; fusion 3× too strong). Hand-compute expected values including edge cases (pause/menu/load, zero, huge values, death, bosses). Every ledger claim must be true in the files — re-grep before recording.

Commander rulings (binding):
  R1. No save migration; one state_schema_version bump this round.
  R2. v0.4 text is the truth; G(L) only where v0.4's formula says so. KEPT = equal to v0.4; approximations PARTIAL with the gap.
  R3. Engine rules: timer thread only posts one AddTask per tick (never self-rescheduling tasks — that froze the game in an earlier round); all effect/process-list reads and all casts on the main thread; timers stop during pause, menus and loading (N6-1); crash guards on every sink/task; the DLL keeps no design state across frames and adds no save serialization.
  R4. Domains (decided by the user 2026-09-25): enemy effects via a Spawn Hazard archetype MGEF cast with CastSpellImmediate at the fused target's feet (engine owns lifetime and count; the old limit of 3 is lifted); player-self effects (火域 heat rank-up without waiting and the 白熱 fuse +5 s on entry, 冰原 slow immunity, 血池 / 聖域 / 潮池 regeneration, 潮池 cleanse) are applied by the DLL tick checking whether the player stands inside a live domain's radius. Remove Papyrus TickDomain once the DLL version is live. If a domain's enemy effect cannot be expressed through a hazard, say why and use the DLL tick for it.
  R5. 毒霧 dose merge (v0.4 open item): treat like plague and 瘴氣 — each second, enemies inside get "spread one dose" merged into their own poison (duration d' = max(d − t, 12)); mark DONE and list the decision for the doc.
  R6. Hotkeys: an input event sink replaces the Papyrus key polling for the mod's hotkeys (form switch, powers, etc. as in ESSBInput); must not fire in the console, text input, or menus (N6-2).
  R7. Anything that would change the design itself: collect for the commander and keep going.

Required outcome:
  1. Per-second DLL work: upkeep (維持費), fire source cost, water magicka regen, environment, and every other Papyrus per-second job v0.4 assigns to the DLL, in the existing timer (one task per tick).
  2. Domains per R4 for all ten domains, incl. 神聖領域 and 毒霧 (R5).
  3. Hotkey input sink per R6; ESSBInput reduced to what must stay Papyrus (if anything), with the reason.
  4. Papyrus removals; nothing reads removed state; identity guard, Papyrus seal and native seal (incl. verifiers) extended to this round — never weakened.
  5. Node statuses: no -N6 or 待決 left, or each with an explicit reason; before/after table.
  6. Tests: hand anchors incl. edge cases, independent reference, fake-engine wiring (fake timer/pause state, fake input events, fake hazard casts), ≥ 5 new real C++ mutations, injected faults; both builds exit 0 with every check ok; zero entry-51 of ours; every DLL-cast spell/hazard resolves against the ESP.
  7. Probe card `build/fix25-probes.md` (style of fix24, ~25 min) incl. X1, N6-1, N6-2, N6-3, each domain once (enemy effect, player-self effect, lifetime, no effect on followers/neutrals), upkeep drain, hotkeys.
  8. `build/native-verification.md` round-25 section; 實作紀錄.md append with player-visible changes; owner-column deviations from v0.4 listed in the ledger for the doc fix.

Permission boundary:
  - Read scope: everything under the repo; read-only D:\Game\Other\SKSE\SkyrimSE\** and D:\Game\Other\SKSE\MO2\mods\**. You may run python, the build, MSVC/CMake from the installed Visual Studio 2022, and read-only disassembly tools.
  - Write set: native/** (ours; dependencies stay pinned), src/*.psc, build_v03.py and the root generator modules (*.py), settings.json, state-schema.lock.json, build/*.py, build/** generated outputs, build/fix25-probes.md, build/native-verification.md (append), package/Elements Spellblade/** (generated), 實作紀錄.md (append only), .codex/pre-fix25-snapshot/** (take it FIRST: same file set as pre-fix24 plus every verifier and seal file), .codex/impl-fix-round25.html.
  - MUST NOT: write under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE; edit 元素魔戰士規劃-v0.3*.md, 元素魔戰士規劃-v0.4.md, design-*.md, README.md, art-book/**, .strategic-advance/**, CLAUDE.md, build/tree-v04-inventory.md, build/native-verification-3.md; use git to commit, reset, checkout, stash, or rm; hook, trampoline, vtable-patch or write game memory; add ESP masters beyond Skyrim.esm; store design state in the DLL or add save serialization.
  - MUST: keep encodings and line endings; crash guards on every sink and task; ledger times from the system clock; if v0.4 is ambiguous, pick the reading closest to intent, record it, keep going.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

When done, report (Traditional Chinese): VERDICT, per outcome 1–8 and ruling R1–R7 what you did, test counts and what they prove, node status counts before/after, anything still not in the DLL and why, design questions for the commander, player-visible changes, files to review first.

Supervision (supervised long task):
  - Ledger: D:\Game\Other\SKSE\.codex\elemental-spellblade\.codex\impl-fix-round25.html (skeleton by the commander; in your write set). Update after reading (short plan), after each milestone, after each build/test run (exit code), on blockers.
  - Milestones: (1) snapshot + plan; (2) per-second DLL work with tests; (3) domains (hazard records, enemy effects, player-self tick) with tests; (4) hotkey input sink; (5) Papyrus removals, seals, node statuses; (6) tests, probe card, docs, full build and report. If resumed, read the ledger and continue from the last completed milestone.

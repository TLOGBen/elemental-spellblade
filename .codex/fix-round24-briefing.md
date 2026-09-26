Goal and acceptance:
Round 24 = slice N5 for the Skyrim SE 1.5.97 mod 元素魔戰士 at D:\Game\Other\SKSE\.codex\elemental-spellblade (git clean at commit d78cb85; N1, N2, tree rebuild, N3, N4 committed and deployed). N5 = fusion (融斷) range scans and settlement, death handling, and the reaction bodies moving out of Papyrus. After this round every v0.4 row tagged "DLL N5" works as v0.4 says, and every node marked LATER-N5 / PARTIAL-N5 / KEPT-N5 is implemented in the DLL or explicitly reported with the reason. This includes redoing the four effects removed early in round 21 (commander ruling C3): 火浴 heal, 不死 stamina refill, 毒 death spread (蔓延), 亡者歸來. Report in Traditional Chinese (台灣); code, identifiers and paths verbatim.

Read first:
- `元素魔戰士規劃-v0.4.md` (design truth; rows tagged DLL N5; §2.7 formulas; §9 staging; §10.3).
- `design-latency-2026-09-20.md` §6 row N5 (~line 401) and the 分期斷裂 rule (~line 408).
- `build/native-verification-3.md` (items 9 death event and killer, 10 process-list scan main-thread-only collect-then-act, 13 hazards are N6; §18 probes N5-1, N5-2).
- `build/plan-coverage.json` and node tables in `.codex/impl-fix-round22.html` / `.codex/impl-fix-round23.html` (the 52+ reaction bodies labelled KEPT-N5, the scan-N5 PARTIAL nodes such as 霜爆、牽引、濃毒、夢魘、群魔、明星、血約、星落、寒潮、毒濺、暗染、傳導、震波、風襲、血濺、聖輝、廣佈、星散, 化身 active effects, 天誅, 墜星, 地臨強化, 冷寂 → 寂 stacks for 寂滅, 斷界, 聚星 / 共鳴回聲, per-element fusion bonuses on the DLL side, death snapshot `ESSB_Death`).
- Contracts and ledgers in force: `.codex/fix-round20..23-briefing.md`, `.codex/impl-fix-round20..23.html`, `.strategic-advance/essb-standalone-build/CHECKPOINT.md`.

Context on quality: earlier implementers forced checks to pass, padded tests, left work half-done and recorded changes they never made; the N3 first build had a bug that would disable the DLL on the first bleed, and the N4 first build made blood form nearly unkillable because a cost path kept 1 health. Hand-compute expected values for every new formula and include edge cases (huge numbers, zero, death, bosses). Every ledger claim must be true in the files — re-grep before recording.

Commander rulings (binding):
  R1. No save migration; one state_schema_version bump this round.
  R2. v0.4 text is the truth; G(L) only where v0.4's formula says so. KEPT = equal to v0.4 text; approximations PARTIAL with the gap.
  R3. Engine rules from native-verification-3: process-list scans and effect lists on the main thread only, collect first then act; Dispel(true) before re-apply; crash guards on every sink/task; the DLL keeps no design state across frames and adds no save serialization.
  R4. Staging: this slice deletes ESSBGuard.psc entirely (OnActorKilled moves to a DLL death sink), the damage/status parts of ESSBReactions (table-driven in the DLL), OnFormClosed scanning and OnKillEvent judging. Push/knockback, fear AI, reanimation AI and summon caps stay Papyrus via ModEvent unless a native API is verified safe (then say so with evidence). 神佑 stays Papyrus.
  R5. Domains (領域) remain N6 (decided: Spawn Hazard for enemy effects + DLL tick for player-self effects); keep their current behaviour working, do not rebuild them now.
  R6. Scans: respect v0.4 radii and target limits; exclude the player, allies/followers and non-hostiles per v0.4; bound the cost (one scan per event, not per target per tick).
  R7. Anything that would change the design itself: collect for the commander and keep going.

Required outcome:
  1. Fusion: range scans, settlement, per-element fusion bonuses and every fusion-attached node, in the DLL.
  2. Death: DLL death sink (killer attribution, the death snapshot replaced or confirmed, 印記化灰, 亡者歸來 judgement, poison death spread, kill streaks incl. ESSB_LastHitSneak), and the four C3 early removals redone per v0.4.
  3. Reaction bodies: every KEPT-N5 / PARTIAL-N5 / LATER-N5 node done in the DLL (damage and status parts), Papyrus keeping only what R4 allows.
  4. Papyrus removals per R4; nothing reads removed state; identity guard, Papyrus seal and native seal (incl. verifiers) extended to this round — never weakened.
  5. Node statuses: every -N5 node becomes DONE or stays with an explicit reason; report the before/after table.
  6. Tests: hand anchors for every new formula, independent reference, fake-engine wiring incl. a fake process list and fake death events, ≥ 5 new real C++ mutations, injected faults; both builds exit 0 with every check ok; zero entry-51 of ours; every DLL-cast spell resolves against the ESP.
  7. Probe card `build/fix24-probes.md` (style of fix23; ~25 min) incl. N5-1, N5-2, one fusion per element, each death feature, the four redone effects, scan exclusions (follower and neutral NPC untouched).
  8. `build/native-verification.md` round-24 section; 實作紀錄.md append with player-visible changes; owner-column deviations from v0.4 listed in the ledger for a later doc fix.

Permission boundary:
  - Read scope: everything under the repo; read-only D:\Game\Other\SKSE\SkyrimSE\** and D:\Game\Other\SKSE\MO2\mods\**. You may run python, the build, MSVC/CMake from the installed Visual Studio 2022, and read-only disassembly tools.
  - Write set: native/** (ours; dependencies stay pinned), src/*.psc, build_v03.py and the root generator modules (*.py), settings.json, state-schema.lock.json, build/*.py, build/** generated outputs, build/fix24-probes.md, build/native-verification.md (append), package/Elements Spellblade/** (generated), 實作紀錄.md (append only), .codex/pre-fix24-snapshot/** (take it FIRST: same file set as pre-fix23 plus every verifier and seal file), .codex/impl-fix-round24.html.
  - MUST NOT: write under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE; edit 元素魔戰士規劃-v0.3*.md, 元素魔戰士規劃-v0.4.md, design-*.md, README.md, art-book/**, .strategic-advance/**, CLAUDE.md, build/tree-v04-inventory.md, build/native-verification-3.md; use git to commit, reset, checkout, stash, or rm; hook, trampoline, vtable-patch or write game memory; add ESP masters beyond Skyrim.esm; store design state in the DLL or add save serialization.
  - MUST: keep encodings and line endings; crash guards on every sink and task; ledger times from the system clock; if v0.4 is ambiguous, pick the reading closest to intent, record it, keep going.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

When done, report (Traditional Chinese): VERDICT, per outcome 1–8 and ruling R1–R7 what you did, test counts and what they prove, node status counts before/after, what stays for N6, design questions for the commander, player-visible changes, files to review first.

Supervision (supervised long task):
  - Ledger: D:\Game\Other\SKSE\.codex\elemental-spellblade\.codex\impl-fix-round24.html (skeleton by the commander; in your write set). Update after reading (short plan), after each milestone, after each build/test run (exit code), on blockers.
  - Milestones: (1) snapshot + plan (every N5 row and -N5 node); (2) scan + fusion in the DLL with tests; (3) death sink and the C3 redos; (4) reaction bodies table-driven; (5) Papyrus removals, seals, node statuses; (6) tests, probe card, docs, full build and report. If resumed, read the ledger and continue from the last completed milestone.

Goal and acceptance:
Round 23 = slice N4 for the Skyrim SE 1.5.97 mod 元素魔戰士 at D:\Game\Other\SKSE\.codex\elemental-spellblade (git clean at commit 20f754d; N1, N2, the v0.4 tree rebuild and N3 are committed and deployed). N4 = hits where the player is the target, and the player's own resources. After this round every v0.4 row tagged "DLL N4" works as v0.4 says, and every node the node table marks LATER-N4 / PARTIAL-N4 / KEPT-N4 is implemented in the DLL (or explicitly reported with the reason it cannot be done in N4). Report in Traditional Chinese (台灣); code, identifiers and paths verbatim.

Read first:
- `元素魔戰士規劃-v0.4.md` (design truth; rows tagged DLL N4; §1.1, §2.3, §2.7, §5.6, §5.8 resource pools; §9 staging; §10.3 incl. the TrueHUD display decision at ~line 1637).
- `design-latency-2026-09-20.md` §6 row N4 (~line 400) and the 分期斷裂 rule (~line 408).
- `build/native-verification-3.md` (items 6, 7, 8, 12, 15; §18 probes N4-1, N4-2), `build/native-verification-2.md`, `build/truehud-verification.md` (custom widget API; Valhalla Combat owns TrueHUD's special resource bar).
- `build/plan-coverage.json` and the node table in `.codex/impl-fix-round22.html`.
- Contracts and ledgers still in force: `.codex/fix-round20..22-briefing.md`, `.codex/impl-fix-round20..22.html`, `.strategic-advance/essb-standalone-build/CHECKPOINT.md`. Known N4 carry-overs recorded there: blood-guard pool same-frame double hit; 協奏／三重奏／過載終焉 multipliers on DLL-settled end damage; 懲戒 hit accumulation and 誓約; lightning N fixed at 1 (kChargesUntilN4); 反擊 block detection; 過載終焉 charges carried across forms; 疾風 dash refund (PARTIAL-基礎).

Context on quality: earlier implementers forced checks to pass, padded tests, left work half-done and recorded changes they never made; the last round's first build also contained a bug that would have disabled the DLL the first time any target bled. Every claim in the ledger must be true in the files — re-grep before recording. What you cannot finish is reported, not papered over.

Commander rulings (binding):
  R1. No save migration; one state_schema_version bump this round.
  R2. v0.4 text is the truth for numbers and effects; G(L) only where v0.4's formula says so. KEPT = equal to v0.4 text; approximations are PARTIAL with the gap stated.
  R3. Engine rules from native-verification-3 (Dispel(true) before re-apply; stacks from ActiveEffect::magnitude; effect lists and writes on the main thread; crash guards on every sink/task; collect-then-dispel). Self counters (charge, rock armour, wind, resolve/戰意, sync/同調, ice shield, water mirror, heat is already N3) live in the player's own effects; the DLL stores no design state and adds no save serialization.
  R4. Engine never lets current health/magicka/stamina exceed max: the three own resource pools 超載 (無元素), 護血 (血), 蓄勁 (土) are stored as magnitudes of the player's own effects (as N2 did for 護血). Water's magicka-based damage sharing (水盾／法盾分擔／止水, v0.4) belongs here.
  R5. Display of the pools (and the 同調 bar if v0.4 says so): TrueHUD custom widget API (RequestPluginAPI → LoadCustomWidgets/RegisterNewWidgetType/AddWidget); first version colour-only bars borrowing TrueHUD's ResourceBar, no own swf yet; must degrade silently when TrueHUD is absent or older. Do not touch TrueHUD's special resource bar.
  R6. Staging: delete ESSBGuard.OnHitEx and the Papyrus self-counter paths in this slice (their DLL version goes live now); ESSBGuard.OnActorKilled stays until N5; reactions stay Papyrus (ModEvent) until N5; knockback/push stays Papyrus via ModEvent unless a native API is verified safe. Lightning N = charge tier from now on.
  R7. Decided features in scope (v0.4 / 2026-09-23): 聖佑 damage reduction by tier (physical −5/−10/−15%, magic resist +10/20/35% native, 85% cap); lightning full-charge spell paralysis (hit on a casting enemy, 30% interrupt); 反咒 via the spell-cast event (caster carrying 破魔印, true damage from that cast's cost); 斷咒 via reading the target's cast state at hit and interrupting.
  R8. Anything that would change the design itself: collect for the commander and keep going.

Required outcome:
  1. A DLL sink for hits whose target is the player covering everything in the N4 row (armour/shield/mirror tier drop, 反震, 灼身, 寒反, 靜電, 毒皮, 殘影／影身, 反擊／反噬／破護, block detection for 反擊), and the self-resource ladders (charge, rock armour, wind, 戰意, 同調, ice shield, water mirror) incl. wind multi-trigger N loop and ESSB_LastHitSneak for kill streaks.
  2. The three resource pools and water magicka sharing per R4, the pool widgets per R5, the carry-overs listed above resolved.
  3. R7 features.
  4. Papyrus removals per R6; nothing reads removed state; identity guard, Papyrus history seal and native history seal extended to this round with the same sha256 binding — do not weaken any.
  5. Node statuses updated: every -N4 node becomes DONE or stays with an explicit reason.
  6. Tests: independent reference for new logic (hand-computed anchors for every new formula, not copied from the model), engine wiring through the fake engine, real C++ mutation tests (≥ 5 new), injected faults; `python -B native/build.py` and `python build_v03.py` exit 0 with every check ok and meaningful; zero entry-51 entries of ours; every spell/effect the DLL casts is resolved at load and checked against the ESP (the round-22 BleedTick class of bug must be impossible).
  7. Probe card `build/fix23-probes.md` (style of fix22: no log where possible, short console commands, expected on-screen result, pass/fail, ~20 min) incl. native-verification-3 probes N4-1, N4-2, the pool bars with and without TrueHUD, each self ladder, each on-hurt reaction, 聖佑 reduction, paralysis, 反咒 and 斷咒.
  8. `build/native-verification.md` round-23 section; 實作紀錄.md append with player-visible changes.

Permission boundary:
  - Read scope: everything under the repo; read-only D:\Game\Other\SKSE\SkyrimSE\** and D:\Game\Other\SKSE\MO2\mods\** (TrueHUD headers/API may be read from there). You may run python, the build, MSVC/CMake from the installed Visual Studio 2022, and read-only disassembly tools.
  - Write set: native/** (ours; dependencies stay pinned — a TrueHUD API header may be vendored under native/ with its licence), src/*.psc, build_v03.py and the root generator modules (*.py), settings.json, state-schema.lock.json, build/*.py, build/** generated outputs, build/fix23-probes.md, build/native-verification.md (append), package/Elements Spellblade/** (generated), 實作紀錄.md (append only), .codex/pre-fix23-snapshot/** (take it FIRST: same file set as pre-fix22 plus native/tests and build/plan-coverage.json), .codex/impl-fix-round23.html.
  - MUST NOT: write under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE; edit 元素魔戰士規劃-v0.3*.md, 元素魔戰士規劃-v0.4.md, design-*.md, README.md, art-book/**, .strategic-advance/**, CLAUDE.md, build/tree-v04-inventory.md, build/native-verification-3.md; use git to commit, reset, checkout, stash, or rm; hook, trampoline, vtable-patch or write game memory; add ESP masters beyond Skyrim.esm (TrueHUD must stay an optional runtime dependency); store design state in the DLL or add save serialization.
  - MUST: keep encodings and line endings; crash guards on every sink and task; ledger times from the system clock; if v0.4 is ambiguous, pick the reading closest to intent, record it, keep going.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

When done, report (Traditional Chinese): VERDICT, per outcome 1–8 and ruling R1–R8 what you did, test counts and what they prove, node status counts before/after, what stays for N5/N6, design questions for the commander, player-visible changes, files to review first.

Supervision (supervised long task):
  - Ledger: D:\Game\Other\SKSE\.codex\elemental-spellblade\.codex\impl-fix-round23.html (skeleton by the commander; in your write set). Update after reading (short plan), after each milestone, after each build/test run (exit code), on blockers.
  - Milestones: (1) snapshot + plan (every N4 row and -N4 node); (2) player-hit sink and self ladders in the DLL with tests; (3) resource pools, water sharing, TrueHUD widgets; (4) R7 features and carry-overs; (5) Papyrus removals, seals, node statuses; (6) tests, probe card, docs, full build and report. If resumed, read the ledger and continue from the last completed milestone.

Goal and acceptance:
Add a third early probe and harden the probe setup powers, for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade. Report in Traditional Chinese.

In-game results so far (.codex/smoke8-probe-results-Papyrus.0.log, `[ESSB-PROBE]` lines, 2026-09-21 22:39-23:00; main mod disabled; calibration k=0.95 accepted):
  - Probe 2: 0x1D doubled the entry-point spell (normalized 20) -> tier_multiplier_mode = entry. DONE.
  - Probe 1: perk ESSB_ProbeAB has two Apply Combat Hit Spell (51) entries, A (priority 200, spell ESSB_ProbeA, 5) and B (priority 199, ESSB_ProbeB, 7), both conditions true. Result: ONLY B applied (B_count=1, A_count=0, normalized delta 7.0). So within one perk, entry 51 yields a single winner and it is the LOWEST-priority (last processed) entry. The meter reported "unexpected" because its verdict table only knew 12 (additive) and 5 (first wins).
  - The release package's only entry-51 perk is ESSB_P_HitProc (74 entries, exactly-one-true by the HITPROC truth table), so the mod is internally safe.

Required outcome:
  1. Probe 1 verdict table: recognise the observed outcome as its own verdict, "single winner = last processed / lowest priority (7)", mapped to a named setting value (e.g. `lightning_roll_mode = exclusive`), alongside the existing additive (12) and first-wins (5) cases.
  2. NEW probe 3 — cross-perk behaviour, the question that decides whether the whole native proc path can coexist with other mods' combat hit spells (the player runs Ordinator, which has ~129 entry-51 entries): two SEPARATE perks, each with exactly one entry 51 whose condition is true on the same hit, applying distinguishable spells (e.g. 5 and 7, same attribution scheme as probe 1). Verdicts: both applied (12) -> "cross-perk additive: coexistence OK"; one applied -> which one (5 or 7) and state what property decided it as far as the data allows (perk FormID order, perk rank/priority, entry priority — design the two perks so the result discriminates between those explanations as much as one run can, or add a second trial variant); anything else -> unexpected, report. Add a fourth power 「探針：第三題」 that switches the perk set to probe 3 exactly like 「探針：第二題」 does, and make 清理 remove it too.
  3. Harden the setup powers against what happened in game:
     - The spawned bandit could not be hit until the player toggled AI twice with `tai`. Prepare the actor only after its 3D is loaded and it is fully initialised, and use a way of freezing it that keeps it hittable; verify hittability as far as can be done offline and explain the choice.
     - FireResist was forced to 0 but became 33 within a second (some other mod adds abilities to spawned NPCs), later -33 after the player's manual forceav. MaxHealth also shifted (+50). Neutralise the AVs in a way that survives such late additions (e.g. wait/settle then set, and re-assert with a modifier that nets to 0 rather than a force that can go negative), and re-check immediately before attaching the meter. The meter's own ENV/Clean checks stay strict.
     - Extra OnHit events from another mod's non-weapon form (e.g. 63000E76, FE38982D) accompanying a real dagger hit invalidated controls. Keep counting them, but if the hit set is exactly one hit from the test weapon plus hits whose source is not a weapon/spell of ours AND the health delta equals the physical control expectation, allow it and log that the extra events were ignored and why. Do not relax anything that could change a verdict.
  4. Update build/fix18-probes.md for probe 3 and the fourth power. Offline harness: probe-1 new verdict, probe-3 all verdicts, the hardened setup and hit-filter rules.
  5. Release package byte-identical to D:\Game\Other\SKSE\MO2\mods\Elements Spellblade (read-only compare). Probe plugin keeps master Skyrim.esm only.

Passing = `python build_v03.py` exit 0 with every check line ok (full build), release hashes unchanged, new offline checks pass.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\** and D:\Game\Other\SKSE\MO2\mods\**; executing PapyrusCompiler.exe allowed.
  - Write set (exact): build_v03.py (probe-package section only), src/ESSBProbe*.psc, build/*.py helpers, build/fix18-probes.md, build/fix18-probe-package/**, build/** generated outputs, package/Elements Spellblade/** (regenerated, must come out byte-identical), 實作紀錄.md (append), .codex/impl-fix-round18f.html.
  - MUST NOT: write under D:\Game\Other\SKSE\MO2 or SkyrimSE; edit design/plan documents or .strategic-advance/**; add masters to the probe plugin; access the network. Keep encodings/line endings (build_v03.py is CRLF).

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

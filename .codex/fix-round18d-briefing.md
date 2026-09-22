Goal and acceptance:
Fix the round-18 probe meter so it can reach a verdict on the player's real setup. Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade. Report in Traditional Chinese.

In-game evidence (.codex/smoke7-probe-Papyrus.0.log, lines with `[ESSB-PROBE]`, 2026-09-21 22:00-22:04; main mod disabled, probe plugin only, target env all zero):
  - Physical control passed (health_delta 0).
  - Native fire reference (nominal 10): health_delta 4.75 on Master difficulty, 9.50 on Adept. So a difficulty multiplier AND an extra x0.95 from some other mod in the player's load order scale player-caused spell damage. The meter requires exactly 10 +/- 0.15 and therefore STOPs every time. The player's load order is large (about 250 plugins) and hunting the x0.95 source is not an option.
  - `reported_magnitude` from inside the effect is 0 for the reference: health_delta was the right basis.
  - When the control is invalidated by an extra hit event (another mod's form FE38982D produced extra OnHit events on an unarmed punch; also a real double swing), the log says "CONTROL is not zero", which is false — delta was 0; the cause was the hit count.

Required outcome:
  1. Calibrate instead of requiring 10: the reference measures k = reference_delta / 10. Accept the reference when it is stable and k is within a sane band (say 0.2..2.0; pick and justify), log k explicitly (`CALIBRATE k=...`), and judge each probe on delta / k with the existing tolerances (5 / 12 / 10 / 20). Keep the reference, control, stability and hit-count rules otherwise. Both scale factors (difficulty, other mods) apply identically to the reference and the probe spells because they are the same kind of player-caused native fire spell on the same target — say so in 實作紀錄.md, and state any case where that equivalence would NOT hold.
  2. Refusal/invalid messages must name the real cause: extra hit events (with count and sources), non-zero physical delta, unstable health, perk change, etc. No message may claim a cause the numbers contradict.
  3. The offline harness covers k = 0.475, 0.95, 1.0 and a rejected out-of-band k, for both probes' verdicts, plus the new messages.
  4. Update build/fix18-probes.md: difficulty no longer needs to be exact (Adept still recommended), note the calibration line, note that unarmed punches can trigger extra hit events from other mods so use the dagger.
  5. Release package byte-identical (hash check against the currently deployed package in D:\Game\Other\SKSE\MO2\mods\Elements Spellblade, read-only).

Passing = `python build_v03.py` exit 0 with every check line ok (full build — you now have the read scope it needs), release hashes unchanged, harness cases above pass.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\** and D:\Game\Other\SKSE\MO2\mods\** (the full build reads FX source plugins and powerofthree PSC/PDB there); executing PapyrusCompiler.exe allowed.
  - Write set (exact): build_v03.py (probe-package section only), src/ESSBProbe*.psc, build/*.py helpers, build/fix18-probes.md, build/fix18-probe-package/**, build/** generated outputs of the full build, package/Elements Spellblade/** (regenerated, must come out byte-identical), 實作紀錄.md (append), .codex/impl-fix-round18d.html.
  - MUST NOT: write under D:\Game\Other\SKSE\MO2 or SkyrimSE; edit design/plan documents or .strategic-advance/**; change gameplay in the release package; access the network. Keep encodings/line endings (build_v03.py is CRLF).

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

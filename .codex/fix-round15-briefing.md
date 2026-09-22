Goal and acceptance:
Round 15 for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade: fix the mechanics that silently never (or almost never) fire in real play, as found by an independent reviewer. Report in Traditional Chinese (code, identifiers, paths verbatim).

The authoritative work list is review-fable-2026-09-19.md in the campaign root — read it in full first. It reviewed a snapshot taken BEFORE round 14. Round 14 (installed, see the newest entries of 實作紀錄.md) already changed kill attribution to "latest element damage within kill_attribution_seconds → real mark → 0" and applied it to 化灰, 亡者歸來 and 連殺. For each finding, first say whether round 14 already covered it, partly covered it, or not at all, then fix what remains. The commander spot-checked findings 1, 3, 4 and 8 against the current source and the log and confirmed them.

Findings, in the reviewer's order (details, file:line, log evidence and minimal fixes are in the report):
  1. 死咒 never resolves (5 darkness 終焉 set a curse, 0 "[ESSB][deathcurse]" lines): the countdown runs on status-host ticks, the host stops when the victim dies, and ClearSlot discards the pending curse. 饕餮 / 處刑 / 亡魂 ride on it.
  2. 連殺 / 奇襲 / sneak ×3 wind proc / 風勢直接滿 read LastHitSneak or run inside ApplyProc, both after the IsDead() early return in OnWeaponHit, so a killing sneak attack — the normal case — never counts. Record the hit's attack facts (sneak, power, weapon) BEFORE the dead-target rejection so kill-side effects can see them; do not apply damage to a dead target.
  3. 反擊 never applies: RiposteLeft is set and decremented but no damage path reads it; 實作紀錄 claims ApplyProc ×1.3, which is absent. Implement it per the design and the log's recorded decision, reachable from the path where the design says it applies.
  4. 神佑 cannot trigger: ESSBGuard requires Health <= 1.0 on a hit event that arrives after the damage, and a lethal hit has already killed the player. Implement it so a lethal hit is actually prevented (the standard approach is an essential-style protection or a health-threshold intercept before death — pick one that works on 1.5.97 with the installed PO3/SKSE, explain why, and keep the "once per combat" rule).
  5. Switching element zeroes lightning charge (OnFormSwitched → ClearSelfAll) before the old mark's 終焉 runs, so the switch-route 放電 always discharges 0. The design sections 2.3 and 2.6 appear to conflict; resolve it in favour of the 終焉 using the charge it had at the moment of the switch (snapshot it), and record the decision.
  6. Two clocks: windows counted in ticks (death curse, airborne, astral ring, catalyze, all TickTimers) stretch 5-8× under the measured load (controller tick gaps of 11-34 s, status-host ticks ~8 s apart, 融斷 settling 13-23 s after Z), while real-time expiries (heat, freeze, curse, marks) vanish in bulk on the late tick. Make every gameplay window a real-time deadline (Utility.GetCurrentRealTime based, rebased on load as round 12 already does) evaluated whenever the tick runs, so a late tick settles what is due instead of stretching or dropping it. Keep one tick per second as the scheduling target; do not add polling.
  7. On-kill stack readers: CaptureDeath omits curse (收割 / 亡者強化 read it live after death); all kill effects depend on the status host surviving death. Snapshot every stack a kill effect reads at the moment of death.
  8. 熔斷 branch is dead code (KeepHeatOnBurst is never called). Wire it where the design says.
  9. 火葬 / 亡魂 check Health <= 0 after applying — see the report.
 10. 斷咒 checks IsCasting at processing time, seconds after the hit. Decide from the state captured at hit time.

Passing = `python build_v03.py` exits 0 with every existing check line ok (READBACK masters ['Skyrim.esm'], records == manifest, CSF 13/13, DELIVERY ok, LAYOUT ok, DOT ok, MCM ok, MCM DEFAULTS ok, SCHEMA ok, FIX10-FIX14 ok, PLAN COVERAGE 0 unmapped, all scripts 0 errors) plus a new check line with one offline regression per finding that fails on .codex/pre-fix15-snapshot sources and passes after; versus .codex/pre-fix15-snapshot/v03-formids.json no existing FormID changes (ESSB_DebugLevel 0x000811) unless a member-variable change forces a state_schema_version bump — if it does, bump per the round-9 rule and say why; the representative hit stays at or below 166 calls. You run the build yourself.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\*.esm and D:\Game\Other\SKSE\MO2\mods\** as the build needs; executing the PapyrusCompiler.exe that build_v03.py invokes is allowed.
  - Write set (exact): src/*.psc, build_v03.py, settings.json, state-schema.lock.json, build/*.py verification helpers, 實作紀錄.md (append only), build/** and package/Elements Spellblade/** (generated), .codex/impl-fix-round15.html (progress ledger; create first, update per item).
  - MUST NOT: write anything under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE (the game may be running); edit 元素魔戰士規劃-v0.3.md (record deviations instead), any review-*.md, .codex/pre-fix*-snapshot/**, fx_extract.py, .strategic-advance/** (append-only commander ledger — never assert on its hash); add masters; introduce Utility.Wait loops, non-single RegisterForUpdate or per-frame polling; undo round 12's per-hit cost reductions or round 14's attribution rule; access the network.
  - MUST: keep file encodings and line endings as they are (build_v03.py is CRLF).

Background (MAY):
  - Real session evidence: .codex/smoke4-Papyrus.0.log. The user's load includes another mod that floods the Papyrus log with ~25,000 FloraHarvestScript binding errors per session, which is why ticks run 11-34 s late; the fix must be robust to that, not assume a quiet VM.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

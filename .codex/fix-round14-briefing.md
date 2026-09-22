Goal and acceptance:
Round 14 for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade: kill-triggered mechanics keyed on "the element that killed the victim" almost never fire in real play, because the killing blow is nearly always the weapon's physical damage. Report in Traditional Chinese (code, identifiers, paths verbatim).

Evidence (.codex/smoke4-Papyrus.0.log, a real session on the current build):
  - 15 kills in 黑暗 form (element=10), the player owns 亡者歸來 (bought 2026-09-18 22:26), and there were 0 reanimations. At the design's 25% chance, P(0 of 15) is about 1.3%.
  - 227 "[ESSB][hit-reject] reason=invalid-actor" lines in the same session: our proc arrives after the weapon has already killed the target and is correctly rejected — but then nothing records that this victim was being fought with darkness.
  - ESSBController.OnKillEvent passes `killingElement = LastDamageFor(akVictim)` to ESSBElem2.OnKill and ESSBElem3.OnKill; ESSBElem3 only calls Reanimate when `aiKillingElement == 10`, and ESSBElem2.ShouldAsh keys 化灰 on 7. Both exit silently when the rule fails.

User-approved rule change (record it in 實作紀錄.md as a user-approved deviation from the strict wording "因黑暗傷害死亡" in design 5.12 / "神聖致死" in 5.9 and 8):
  A kill is attributed to element X when the victim, at the moment of death, either carries a real mark of element X, or took damage of element X from this mod within the last 3 seconds (a new settings.json key `kill_attribution_seconds`, default 3.0). When both a mark and recent damage exist with different elements, the most recent of this mod's damage wins; when there is no recent damage, the mark decides; when neither exists the kill has no element (0) — never guess from the player's current form. Apply this one rule everywhere a kill effect depends on the killing element: at minimum 化灰 (7) and 亡者歸來 (10); find every other consumer of the killing element or of LastDamageFor/LastDamageWasElement and list them.
  Keep 化灰 and 亡者歸來 mutually exclusive exactly as the design says (化灰 decided first).

Also required:
  1. Diagnostics: every early exit in the reanimation decision and in the ash decision logs one throttled line at level 2 with the reason (no element / element mismatch / branch not owned / roll failed with the rolled value and chance / CanReanimate refused and why / tier refused / servant cap full / apply failed). Same for any other kill effect you touch. Use the round-12 cached-level guard so nothing is built at level 0.
  2. Offline regressions: the 1-hit weapon kill with a darkness mark (must reanimate on a forced roll), weapon kill with recent darkness damage but no mark, weapon kill after switching from divine to darkness (must not ash), kill with no mod damage and no mark (element 0, nothing fires), and the divine equivalents for 化灰.

Passing = `python build_v03.py` exits 0 with every existing check line ok (READBACK masters ['Skyrim.esm'], records == manifest, CSF 13/13, DELIVERY ok, LAYOUT ok, DOT ok, MCM ok, MCM DEFAULTS ok, SCHEMA ok, FIX10/FIX11/FIX12/FIX13 ok, PLAN COVERAGE 0 unmapped, all scripts 0 errors) plus a new check line for the attribution cases; versus .codex/pre-fix14-snapshot/v03-formids.json no existing FormID changes (ESSB_DebugLevel 0x000811) unless a member-variable change forces a state_schema_version bump — avoid one if you can (per-slot/per-actor arrays that already exist may carry a timestamp), and if you cannot, bump per the round-9 rule and say why. The representative hit must stay at or below round 13's 166 calls. You run the build yourself.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\*.esm and D:\Game\Other\SKSE\MO2\mods\** as the build needs; executing the PapyrusCompiler.exe that build_v03.py invokes is allowed.
  - Write set (exact): src/*.psc, build_v03.py, settings.json, state-schema.lock.json, build/*.py verification helpers, 實作紀錄.md (append only), build/** and package/Elements Spellblade/** (generated), .codex/impl-fix-round14.html (progress ledger; create first, update per item).
  - MUST NOT: write anything under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE (the game may be running); edit 元素魔戰士規劃-v0.3.md (record deviations instead), any review-*.md (a separate reviewer is writing one), .codex/pre-fix14-snapshot/**, fx_extract.py, .strategic-advance/** (append-only commander ledger — never assert on its hash); add masters; introduce Utility.Wait loops, non-single RegisterForUpdate or per-frame polling; undo round 12's per-hit cost reductions; access the network.
  - MUST: keep file encodings and line endings as they are (build_v03.py is CRLF).

Background (MAY):
  - Rounds 1-13 are accepted and installed. Round 10 introduced per-target damage-element tracking (RegLastDamage[8] plus DamageActor[128]/DamageElement[128]); round 12 threaded resolved slots through internal calls.
  - A separate read-only reviewer is looking for OTHER mechanics with the same class of problem; do not wait for it and do not try to fix beyond the kill-attribution scope.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

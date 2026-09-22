Goal and acceptance:
Independent code review of the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade after eleven fix rounds in one day. Hunt for defects that COMPILE and pass the offline checks but behave wrongly in game. Report in Traditional Chinese (keep code, identifiers, file paths and line numbers verbatim).

Passing = a findings list where every item has: file + line(s), the concrete trigger/reproduction, why it is wrong (cite the design text, the implementation log, or the engine/Papyrus rule), the minimal fix, and a confidence level (high/medium/low). Plus a section naming the areas you examined and found clean, and a section naming what you did NOT examine. Rank by impact. No style remarks. Do not pad: a short list of real defects beats a long list of guesses. Write it to review-2026-09-18.md in the campaign root and return the same list in your final report.

What today actually broke, so you know the shape of the bugs that survive our checks — look for MORE OF THESE, do not just re-verify that these are fixed:
  1. `arrayVar == None` is invalid for Papyrus arrays and logged a cast error on every evaluation (round 4 introduced 63 of them; round 9 fixed them). Scan for any remaining type-invalid comparison or operation of this class, on arrays or otherwise.
  2. Member variables added to a persisted script cannot be created in instances that already exist in a save; the mod now bumps `state_schema_version` (settings.json + state-schema.lock.json) to re-allocate the script-carrying quests. Check the lock actually covers every persisted script and that nothing else in the plugin holds script state across a bump.
  3. Old and new quest instances coexisted after a bump and BOTH dispatched events: every kill and every skill-increase ran twice, and the old instance's stale copy of a global made 化灰 fire on non-divine kills. Round 10 added identity checks. Audit every remaining entry point reachable from an engine event, a mod event, a menu, a magic effect or an alias for the same exposure — list any that can still run on a stale instance.
  4. Cross-target state kept in one variable with no owner (the 化灰 case). Look for other state that should be per-target or per-slot but is not.
  5. Borrowed FX records carrying behaviour we did not intend (a looping SNDR played with `Sound.Play`, whose instance handle was discarded, looped forever). Audit the rest of the copied FX (EFSH/ARTO/IPDS/EXPL/HAZD/LIGH) for persistence, sound or hazard behaviour that outlives its trigger.
  6. Whole weapon classes silently dropped by a hit gate (bow/crossbow produced zero procs all session; round 11 addresses it). Check every other eligibility gate — target eligibility (design 2.9), VIP/boss exclusions, ally exclusion, the engaged-marker path — for classes of actor or attack that fall through silently.

Also required — read the real logs, do not rely on the code alone:
  F. Mine the in-game evidence for anything the commander has NOT already filed. Sources: .codex/smoke3-essb-events.log (a full session of [ESSB] events plus error context) and .codex/smoke1-Papyrus.0.log (the earlier broken session). Already filed and out of scope: the array/None flood, the save-upgrade failure, double kill + double skill point, 化灰 on non-divine kills, the looping form sound, the no-form gating, and zero bow/crossbow hits. Look for the rest: event counts that do not match what the design predicts (e.g. a reaction that should fire per mark but fires once, a status that never appears, a throttle that hides a hot path), values that look wrong for the tree levels in that session, sequences that violate the design's ordering (開印 before 印記, 終焉 without a mark, kill effects after the slot was cleared), anything logged at a level that will spam in normal play, and any Papyrus error or warning whose stack touches our scripts that nobody has filed. For each, quote the log lines with timestamps and say what they prove. If the log is silent where the design says something should have happened, that absence is a finding too — say what should have appeared.

  G. Latency and per-hit cost. The user reports damage arriving in bursts: a few normal hits land, then the target's health drops all at once. The commander measured it from .codex/smoke3-essb-events.log by pairing each [ESSB][Hit] with the next proc/damage line for the same target: 25 landed in the same second, 34 one second later, 6 two seconds later, one at four and one at seven; up to 8 damage events landed in a single second. Establish what the hit path actually costs and where the latency comes from, then propose concrete reductions that do not change behaviour: count the script calls, property reads, GlobalVariable.GetValue calls, array scans and cross-script calls per hit (a call into another script object releases the caller's lock and can queue), and say which are avoidable (cache on form switch or on node purchase rather than per hit; collapse repeated GetValue of the same GLOB within one hit; avoid scans in the common case). Report the per-hit call count before and after your proposal. Note separately how much of the observed latency was the double dispatch fixed in round 10 and how much the level-3 debug logging costs per hit. Do not implement anything — this review is read-only.

Coverage required (say which you reached):
  A. src/ESSBController.psc — hit path, registry of 8 marked targets, status host swap, cooldowns, pushes, domains, the per-target damage-element tracking added in round 10, the schema/identity guards added in rounds 9-10.
  B. src/ESSBStatus.psc, src/ESSBReactions.psc, src/ESSBMark.psc — ring buckets (poison 12 s / bleed 10 s), export/import symmetry, 開印/終焉, mark eviction and expiry.
  C. src/ESSBElem*.psc, src/ESSBNodes.psc, src/ESSBNoForm.psc — node effects versus build/plan-tree-nodes.json, the round-6/7 scaling (ESSB_NodeScale, the six ESSB_Mult* sliders, G(L) applied once per path), the round-8 upkeep and no-form baseline, the round-10 no-form gating.
  D. src/ESSBTrees.psc, src/ESSBGuard.psc, src/ESSBMCM.psc, src/ESSBState.psc, src/ESSBFormRules.psc — point reconciliation, respec, menu events, MCM bindings, upkeep ticking and the magicka-empty auto-close.
  E. build_v03.py — are the generated records plausible for the intent (MGEF flags/archetype/AV/resist, SPEL type/cast/delivery, PERK entry points and CTDA, QUST aliases and VMAD, the MCM config refs, the SNDR normalisation)? Use vendor/wbDefinitionsTES5.pas as the format reference and build/v03-formids.json as the manifest.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\*.esm and D:\Game\Other\SKSE\MO2\mods\**.
  - Write set (exact): review-2026-09-18.md only.
  - MUST NOT: modify, create, move or delete any other file anywhere; run build_v03.py or any compile or install step; write under MO2 or SkyrimSE; access the network.
  - MUST: treat 元素魔戰士規劃-v0.3.md as the design truth and 實作紀錄.md as the record of deliberate deviations — a behaviour recorded there as a deviation is not a defect unless it is internally inconsistent or contradicts a later user decision recorded in the same file.

Background (MAY):
  - Tree ids 0..10 = fire, frost, lightning, earth, wind, blood, divine, poison, water, darkness, astral; 11 = no-form; 12 = common. Element ids 1..11 in the same order. Routes 0/1/2 = 持續/開啟/關閉. Tiers 0..4. Mainline rank 0..15, branches 0-based.
  - Damage is applied by setting magnitude on the mod's own spells then Actor.DoCombatSpellApply; never Spell.Cast, never DamageActorValue on enemy health.
  - .codex/smoke1-Papyrus.0.log and .codex/smoke3-essb-events.log are real in-game evidence from today.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

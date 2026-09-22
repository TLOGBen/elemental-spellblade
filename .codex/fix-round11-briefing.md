Goal and acceptance:
Round 11 for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade: bow and crossbow hits never trigger anything. Report in Traditional Chinese (code, identifiers, paths verbatim).

The defect:
  The user reports arrows produce no proc, no mark, no reaction. Evidence: in .codex/smoke3-essb-events.log (a full session, 1423 [ESSB] events) every single [ESSB][Hit] line is weapon=0, 1 or 5 — there is not one weapon=7 (bow) or weapon=9 (crossbow) hit, although the user shoots. So ranged hits are being dropped before the proc, silently.
  Design 2.1 explicitly supports weapon types 0-7 and 9 (fists, melee, bow, crossbow; staves excluded), and gives a sneak shot the power-attack multiplier.
  The current gate is in ESSBController.OnWeaponHit: it casts `akSource as Weapon`, reads GetWeaponType(), and then requires `akProjectile != None` for types 7/9 while requiring `akProjectile == None` for everything else. Commander's hypothesis, verify or refute it rather than assuming: for an arrow hit PO3's OnWeaponHit may pass the AMMO (or the projectile's source form) as akSource rather than the bow, so the cast yields None, weaponType falls back to 0, the "melee" branch then sees a non-None projectile and returns — every arrow is dropped. Another candidate: the RE::HitData flag mask 1097731 may match on arrow hits.
  Required outcome:
    1. Ranged hits register and go through the same proc/mark/reaction path as melee, with the design's rules: sneak shot counts as a power attack, bows have no power attack otherwise, staves (type 8) stay excluded, and a hit must still be a real weapon hit (not an explosion, bash or blocked hit).
    2. Do not weaken the existing melee gate: a melee swing must still never be counted twice, and non-weapon damage must still be rejected. Prove with offline cases for: one-hand melee, two-hand melee, unarmed, bow, crossbow, staff, spell, explosion, bash, blocked.
    3. Work whichever form akSource takes. Determine what is actually available at runtime instead of guessing: read vendor/imports/PO3_Events_Alias.psc and any PO3 source or docs reachable under D:\Game\Other\SKSE\MO2\mods (the installed "powerofthree's Papyrus Extender" ships Source/scripts), and if the answer is still not provable from files, handle Weapon, Ammo and None-with-projectile by falling back to the player's equipped weapon type, and say so.
    4. Add a debug line at level 3 for every REJECTED hit: the reason, the akSource record type and FormID, the resolved weapon type, whether a projectile was present, and the flag mask. Throttled per the 6.1 rules. This is how the next in-game session will confirm the fix or show what is still dropped.
    5. While you are in this path, check that the same drop does not affect ESSBGuard.OnHitEx (player as victim) for incoming arrows.

Passing = `python build_v03.py` exits 0 with every existing check line ok (READBACK masters ['Skyrim.esm'], records == manifest, CSF 13/13, DELIVERY ok, LAYOUT ok, DOT ok, MCM ok, SCHEMA ok, FIX9/FIX10 ok, PLAN COVERAGE 0 unmapped, all scripts 0 errors) plus a new check line for the ranged-hit cases; versus .codex/pre-fix11-snapshot/v03-formids.json no existing FormID changes (ESSB_DebugLevel 0x000811) unless a member-variable change forces a state_schema_version bump — avoid one if you can, and if you cannot, say why and bump per the round-9 rule. You run the build yourself.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\*.esm and D:\Game\Other\SKSE\MO2\mods\** (including the Papyrus Extender's shipped Source/scripts); executing the PapyrusCompiler.exe that build_v03.py invokes is allowed.
  - Write set (exact): src/*.psc, build_v03.py, settings.json, state-schema.lock.json, build/*.py verification helpers, 實作紀錄.md (append only), build/** and package/Elements Spellblade/** (generated), .codex/impl-fix-round11.html (progress ledger; create first, update per item).
  - MUST NOT: write anything under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE (the game is running); edit 元素魔戰士規劃-v0.3.md (record deviations instead), review-*.md, fx_extract.py, .strategic-advance/** (the commander's campaign ledger is append-only and changes between rounds — never assert on its hash); add masters; introduce Utility.Wait loops or non-single RegisterForUpdate; access the network.
  - MUST: keep file encodings and line endings as they are (build_v03.py is CRLF).

Background (MAY):
  - Rounds 1-10 are accepted; round 10 (per-victim kill element, old-instance double dispatch, one-shot sounds, no-form gating) is built but not yet installed. Do not undo any of them.
  - The hit path continues into ApplyProc / InstallMark / reactions; 潛行射擊 already has power-attack handling further down, keep it.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

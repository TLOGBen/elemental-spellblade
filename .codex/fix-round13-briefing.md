Goal and acceptance:
Round 13 for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade: the remaining review findings plus the user's MCM restore-defaults button. Report in Traditional Chinese (code, identifiers, paths verbatim).

Work items:
  1. Fix review findings 6 to 13 of review-2026-09-18.md (all P2). Read that report first — each finding carries its file:line, reproduction, design citation, minimal fix and confidence. In short:
      6. Lightning's ordinary proc is missing the design's 50% magicka drain (design 2.1 line 69). Cover normal hits, power attacks and extra procs; no magicka returned to the player, no conversion to true damage.
      7. When a ninth target evicts a slot whose victim carries two real marks, the secondary mark is abandoned instead of ending (design 2.2 line 107: eviction must trigger the expiry 終焉, nothing may vanish silently).
      8. 反震 can never pass its full-stack gate because ESSBGuard subtracts a rock-armour layer before the check. Judge from the pre-hit snapshot.
      9. Rock armour's armour buff expires on its own while the layers still stand, and the "only cast on change" early-out then refuses to restore it.
     10. Six elements' 開印 stack counts (fire, lightning, earth, blood, divine, darkness) do not apply the approved overall multiplier, although frost, wind and poison do; the earth open's player stamina restore needs it too. Use the existing RoundStochastic and keep the existing caps.
     11. 斷咒 and 冰心 consume their cooldown before checking whether the trigger condition holds, so a wasted attempt blocks the real one. Test the condition first.
     12. ESSBCounter can register or handle animation events after its active magic effect has ended — the live log shows `Unable to call RegisterForAnimationEvent - no native object bound` from OnEffectStart line 35, 48 deduplicated occurrences. Give the listener a stable native lifetime and gate late events.
     13. 斷咒's casting test reads animation graph variables (`IsCastingRight/Left/Dual`) that do not exist on every actor, producing `cannot fetch variable named ... returning false` and a wrong answer. Use `PO3_SKSEFunctions.IsCasting` with the actor's equipped magic item instead.
     For each, say whether you confirmed the review's diagnosis or found it wrong.
  2. MCM restore-defaults, user-requested and deferred from round 12. Add to the 平衡 page a confirm-then-reset control that writes every tunable back to its build-time default: the six ESSB_Mult* sliders, ESSB_BaseDamageMult, ESSB_NodeScale, ESSB_MultUpkeep, and the two DoT coefficient sliders on the 一般 page. Round 12 already added each slider's default to its MCM text and a build check that the MCM defaults equal the GLOB defaults — reuse that generated source of truth, never a second hardcoded copy. Confirm before applying, notify afterwards.
  3. 實作紀錄.md entry "fix round 13（審查 P2 與 MCM 預設）": FIXED / NOT FIXED table, and for each finding whether the review's diagnosis held.

Passing = `python build_v03.py` exits 0 with every existing check line ok (READBACK masters ['Skyrim.esm'], records == manifest, CSF 13/13, DELIVERY ok, LAYOUT ok, DOT ok, MCM ok, MCM DEFAULTS ok, SCHEMA ok, FIX10/FIX11/FIX12 ok, PLAN COVERAGE 0 unmapped, all scripts 0 errors); versus .codex/pre-fix13-snapshot/v03-formids.json no existing FormID changes (ESSB_DebugLevel 0x000811) unless a member-variable change forces a state_schema_version bump — avoid one if you can, and if you cannot, bump per the round-9 rule and say why; an offline regression per finding that fails on the pre-fix sources and passes after. You run the build yourself.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\*.esm and D:\Game\Other\SKSE\MO2\mods\** as the build needs; executing the PapyrusCompiler.exe that build_v03.py invokes is allowed.
  - Write set (exact): src/*.psc, build_v03.py, settings.json, state-schema.lock.json, build/*.py verification helpers, 實作紀錄.md (append only), build/** and package/Elements Spellblade/** (generated), .codex/impl-fix-round13.html (progress ledger; create first, update per item).
  - MUST NOT: write anything under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE (the game may be running); edit 元素魔戰士規劃-v0.3.md (record deviations instead), review-2026-09-18.md or any other review-*.md, fx_extract.py, .strategic-advance/** (the commander's campaign ledger is append-only — never assert on its hash); add masters; introduce Utility.Wait loops, non-single RegisterForUpdate or per-frame polling; undo round 12's per-hit cost reductions; access the network.
  - MUST: keep file encodings and line endings as they are (build_v03.py is CRLF).

Background (MAY):
  - Rounds 1-12 are accepted and installed; round 12 cut the representative hit from 920 calls to 163 and moved the tree menu to open 0.2 s after MessageBoxMenu closes. Keep both.
  - The review's own "已檢查且在該範圍未發現新問題" and "未檢查" sections tell you where it did and did not look.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

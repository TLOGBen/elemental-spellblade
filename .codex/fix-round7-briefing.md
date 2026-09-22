Goal and acceptance:
Seventh round (flat-value rebalance + balance sliders) for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade. The user's direction: tune the flat values UP first ("高了再說"), make them scale with tree level, and expose category balance sliders in the MCM. Numbers, scaling and sliders only — no mechanic changes. Report in Traditional Chinese (code, identifiers, paths verbatim).

Work items (user-approved):
  1. Apply the suggested values of build/flat-values-audit.md (60 rows, produced last round) with these commander rulings:
     - Rows whose suggestion is 保留／暫留 stay unchanged (05, 43, 55, 57, 58, 59, 60). Row 04 (斷咒 silence 1 s) stays.
     - Row 25 裁決 heal: 25 × environment per target, but cap the total heal of one 裁決 at 100 before environment multiplier. Row 30 shares row 29's values (same domain). Row 37 收割: 15 per layer as suggested.
     - Every other row: take the audit's suggested value verbatim. List each row id -> old -> new -> code site in the report; if a suggestion is ambiguous, pick the conservative reading and say so.
  2. Tree-level scaling: every flat amount the audit lists as "隨樹等級／G(L)？= 否" now scales with G(L) = 1 + 0.05 × level of the tree the node belongs to (base reactions use their element's tree; common-tree nodes use the current element's tree; no-form nodes use the no-form tree). Apply G exactly once per path — several of these values feed ApplyUtil, which does not multiply G today; do not route them through ApplyDamage. Prove per path (grep-level table) that no value now gets G twice. Exempt: row 60 神佑 (1 HP), durations/windows (rows 03, 04, 05, 59), slow/armour percentages that are already percentages of something (row 53's armour points DO scale; a percentage does not), and anything the audit already marks as level-scaled.
  3. Balance sliders. Six float GLOBs (appended IDs, default 1.0), bound as script properties and applied exactly once at the narrowest choke point of each category:
     - ESSB_MultDamage — reuse the existing ESSB_BaseDamageMult (rename only the MCM label to 傷害倍率; keep the EDID and FormID).
     - ESSB_MultDot — poison/bleed ticks and every other per-second damage (domains, catalyze, 血潮 remaining-bleed).
     - ESSB_MultCooldown — every cooldown and "每 N 秒一次" window (multiplies the seconds; 0.5 = twice as often). Not applied to the 8 s / 10 s mark durations or the DoT layer lives.
     - ESSB_MultRecovery — every heal, stamina/magicka restore and shield the mod gives the player or companions (including 長流, 聖域, 血池, 潮池).
     - ESSB_MultDrain — every stamina/magicka/armour drain applied to enemies (破魔 drain, 感電, 裂痕, 深寒, 地震削耐, 蝕魔…). Not the resist-shred percentages.
     - ESSB_MultDuration — durations of statuses the mod applies (marks 8/10 s, slows, 冰封, 沉默, 破魔印, 失衡, domains) and the DoT layer lives (12/10 s: the ring buckets are fixed-size, so implement duration scaling for DoT only if it can be done without resizing arrays — otherwise exempt DoT layer life, say so, and keep marks/slows/domains scaled). Clamp so no duration goes below 1 s.
     Add a new MCM page 平衡 with: 傷害倍率 (existing), 節點倍率 (move ESSB_NodeScale here), 持續傷害, 冷卻, 回復, 削減, 持續時間 — sliders 0.25–3.0 step 0.05 (cooldown 0.25–2.0). Keep the 一般 page for toggle / debug and the two DoT coefficient sliders.
  4. 實作紀錄.md entry "fix round 7（固定數值與平衡桿）": FIXED / NOT FIXED table, the 60-row before/after table, the G(L) once-only proof table, and the category -> call sites table for the six sliders.

Passing = `python build_v03.py` exits 0 with every existing check line ok (READBACK masters ['Skyrim.esm'], records == manifest, CSF 13/13, DELIVERY ok, LAYOUT ok, DOT ok, MCM ok with the new refs, PLAN COVERAGE 0 unmapped, all scripts 0 errors); no existing FormID changes versus .codex/pre-fix7-snapshot/v03-formids.json (ESSB_DebugLevel 0x000811; new GLOBs appended only). You run the build yourself.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\*.esm and D:\Game\Other\SKSE\MO2\mods\** as the build needs; executing the PapyrusCompiler.exe that build_v03.py invokes is allowed.
  - Write set (exact): src/*.psc, build_v03.py, settings.json, plan_coverage.py (only if coverage text must follow), 實作紀錄.md (append only), build/** and package/Elements Spellblade/** (generated), .codex/impl-fix-round7.html (progress ledger; create first, update per item).
  - MUST NOT: write anything under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE (the game may be running); edit 元素魔戰士規劃-v0.3.md (record deviations instead), review-*.md, fx_extract.py, .strategic-advance/**; add masters; renumber records; resize the DoT ring buckets or the export layout; change any mechanic, cap or branch semantics; access the network.
  - MUST: keep file encodings and line endings as they are.

Background (MAY):
  - Rounds 1-6 landed. Round 6 added ESSB_NodeScale and the 破魔/water/frost constants; round 4 added ESSB_BaseDamageMult / ESSB_PoisonDotK / ESSB_BleedDotK; round 5 added the MCM (MCM/Config/Elements Spellblade/config.json generated by build_v03.py). Do not undo them.
  - ApplyUtil is the common path for heals/drains/buffs (utility spells with SetNthEffectMagnitude then DoCombatSpellApply); the audit's code sites are accurate as of round 6.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

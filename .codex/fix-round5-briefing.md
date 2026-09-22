Goal and acceptance:
Fifth round (settings UI) for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade: move settings and debug controls from the MessageBox lesser power into an MCM page built with MCM Helper, keep tree opening on the power. Report in Traditional Chinese (code, identifiers, paths verbatim).

Work items (user-approved layout):
  0. (Do this first, build, then continue.) Longer DoT layers, user-approved: poison layer life 6 s -> 12 s, bleed layer life 5 s -> 10 s. Per-layer-per-second damage stays as round 4 set it (the user wants longer, not weaker), so total damage per layer rises accordingly. The layers live in ESSBStatus ring buckets (one bucket per second of life), mirrored by the controller's pending/backup arrays and by ExportInts/ImportState during the ~25 s host swap: resize every one of them consistently (bucket counts, slot offsets, the 27-int export layout and the backup arrays sized from it, 血潮 remaining-bleed maths that multiplies by seconds left, any node text that quotes "6 秒"/"5 秒" in code comments or notifications). Make the two lifetimes named constants in one place. Prove symmetry offline: an export -> import round trip preserves every bucket, and a layer added at t expires exactly at t+12 / t+10. Papyrus arrays cap at 128 elements — check every resized array against it.
  1. MCM mod entry "元素魔戰士" via MCM Helper (installed: D:\Game\Other\SKSE\MO2\mods\必须模组-MCM Helper-MCM助手, SkyUI present). Ship `MCM/Config/Elements Spellblade/config.json` (+ settings.ini only if ModSettings are used) in the package; other installed mods' MCM/Config folders are valid format references. Pages:
     - 一般: 附傷開關 (toggle -> ESSB_Enabled); 附傷基礎倍率 (slider 0.5-5.0 step 0.1 -> ESSB_BaseDamageMult); 毒層係數 / 流血係數 (sliders -> ESSB_PoisonDotK / ESSB_BleedDotK, sane ranges around the round-4 defaults).
     - 技能樹: read-only list of the 13 trees with level and unspent points (whatever MCM Helper can bind read-only to the existing level / perk-point GLOBs); 洗點：目前元素樹 and 洗點：全部 as buttons with a confirmation prompt, calling the existing ESSBTrees.Respec / RespecAll.
     - 除錯: 除錯等級 0-3 (enum/stepper -> ESSB_DebugLevel 0x000811), 印出目標表 (button -> ESSBController.DumpRegistry).
     Prefer GlobalValue bindings and CallFunction actions so the MCM quest script is as small as possible. UI text: write Traditional Chinese literals directly in config.json (UTF-8). Do NOT ship an Interface/Translations file unless unavoidable; if unavoidable it must be UTF-16 LE with BOM and named for sLanguage=ENGLISH (this install runs ENGLISH with Chinese content) — state why.
  2. The settings lesser power keeps only tree opening: MessageBox buttons 元素樹 / 通用樹 / 關閉 (update ESSBSettingsEffect choice indices and the box text; remove the moved functions from the box, not from the scripts).
  3. Dependency discipline: ESP masters stay ['Skyrim.esm'] (the MCM quest + script live in our plugin; SkyUI / MCM Helper are runtime-only soft dependencies). Without them the mod must still work (no hard references from gameplay scripts into the MCM script). Compile against import stubs if the real MCM_ConfigBase / SKI_ConfigBase sources are not available loose (they may be inside MCMHelper.bsa / SkyUI_SE.bsa — reading those archives is allowed); stubs go in vendor/imports, ASCII only, signatures must match the real scripts exactly and must NOT be shipped in the package.
  4. 實作紀錄.md entry "fix round 5（MCM）": FIXED / NOT FIXED table, the file list added to the package, every GLOB the MCM binds (EDID + FormID), and an in-game checklist (what the user should see, what to do if the MCM entry does not appear — e.g. new-game vs existing save registration delay).

Passing = `python build_v03.py` exits 0 with every existing check line ok (READBACK masters ['Skyrim.esm'], records == manifest, CSF 13/13, DELIVERY ok, LAYOUT ok, PLAN COVERAGE 0 unmapped, FX ok, all shipped scripts compile 0 errors); config.json parses and every form reference in it ("Elements Spellblade.esp|HEX") resolves to a record of the expected type in build/v03-formids.json — add that as a build-time check line "MCM ok"; no existing FormID changes versus .codex/pre-fix5-snapshot/v03-formids.json (ESSB_DebugLevel 0x000811; new records appended only). You run the build yourself.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\*.esm and D:\Game\Other\SKSE\MO2\mods\** ; executing the PapyrusCompiler.exe that build_v03.py invokes, and a BSA reader of your choice in read-only mode, is allowed.
  - Write set (exact): src/*.psc, build_v03.py, settings.json, vendor/imports/*.psc (compile stubs only), 實作紀錄.md (append only), build/** and package/Elements Spellblade/** (generated), .codex/impl-fix-round5.html (progress ledger; create first, update per item).
  - MUST NOT: write anything under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE; edit 元素魔戰士規劃-v0.3.md, review-*.md, fx_extract.py, .strategic-advance/**; add masters; renumber records; ship any file whose name could collide with another mod (everything stays under names starting with ESSB or inside "Elements Spellblade" folders); access the network.
  - MUST: keep file encodings and line endings as they are.

Background (MAY):
  - Rounds 1-4 landed today; round 4 created ESSB_BaseDamageMult / ESSB_PoisonDotK / ESSB_BleedDotK and moved B ranges into settings.json. Do not undo earlier rounds.
  - Opening a CSF tree from inside the MCM is deliberately not offered (the MCM lives inside the journal menu).

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

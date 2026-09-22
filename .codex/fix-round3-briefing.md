Goal and acceptance:
Third fix round (visual feedback from the user's first in-game session) for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade. Report in Traditional Chinese (code, identifiers, paths verbatim).

Work items:
  1. Form aura: the user dislikes the borrowed auras (the frost one, Icebloom `_IP_FrostIceFormFXShader02`, looks like the player is frozen solid) and decided: all 11 element form auras use the original Phenderix Elements form shader `ZZShader_<Element>Form` (already copied into the 0x003000 FX segment as ESSBFX_ZZShader_<Element>Form where present; copy any missing one with the existing fx_extract export path, new IDs only after the current highest FX id). Keep the currently bound non-Phenderix shaders in the plugin as spares. Make the aura choice data-driven: a `fx_aura` map in settings.json (element name -> selector "Plugin|EDID"), defaulting to the Phenderix form shaders, validated at build time, reflected in build/fx-bindings.json. Weapon glow and hit shaders stay as they are.
  2. Mark visibility: in game the user cannot tell which enemies carry a mark. Marks (ESSB_MarkEffect_<Element>, 8 s / water 10 s, FX Persist) currently reuse the hit shader via fxe('mark', ix). Make a marked enemy clearly identifiable for the WHOLE mark duration, in the element's colour. Decide from data, not guesses: parse the EFSH DATA of the candidate shaders (format reference vendor/wbDefinitionsTES5.pas) and report for each element the fields that govern persistence/visibility (fill and edge persistent alpha ratios, full-alpha times, edge colour, particle flags); pick per element the shader that stays visible while persisting (strong edge glow preferred over full-body fill so enemies remain readable). If a copied ARTO suits as a persistent attached marker, you may add it as Hit Effect Art only if it does not loop sound. Same data-driven treatment: `fx_mark` map in settings.json. Apply the same visibility check to the main status hosts that the player needs to read at a glance (frozen, 破魔印, 沉默) and fix any that are effectively invisible.
  3. Record in 實作紀錄.md a table per element: aura before/after, mark shader before/after with the EFSH numbers that justify it; plus how the user swaps a shader via settings.json and rebuilds.

Passing = `python build_v03.py` exits 0 with every existing check line ok (READBACK masters ['Skyrim.esm'], records == manifest, CSF 13/13, DELIVERY ok, LAYOUT ok, PLAN COVERAGE 0 unmapped, FX ok with masters still only Skyrim.esm, 17 scripts compile 0 errors); no existing FormID changes versus .codex/pre-fix3-snapshot/v03-formids.json (ESSB_DebugLevel 0x000811; new records only appended); FIXED / NOT FIXED table appended to 實作紀錄.md as "fix round 3（特效回饋）" and returned in the final report. You run the build yourself this round.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only access to D:\Game\Other\SKSE\SkyrimSE\Data\Skyrim.esm and the DLC masters, and to D:\Game\Other\SKSE\MO2\mods\** (source FX plugins, Papyrus compiler and import sources that build_v03.py already uses). Executing the PapyrusCompiler.exe that build_v03.py invokes is allowed.
  - Write set (exact): build_v03.py, settings.json, src/*.psc (only if a visual needs script support), 實作紀錄.md (append only), build/** and package/Elements Spellblade/** (generated), .codex/impl-fix-round3.html (progress ledger; create before the first product edit, update per item).
  - MUST NOT: write anything under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE (the game may be running); edit fx_extract.py beyond what item 1 strictly needs (prefer none), 元素魔戰士規劃-v0.3.md, review-*.md, .strategic-advance/**; add masters; renumber records; copy nif/dds/wav assets; introduce Utility.Wait loops, non-single RegisterForUpdate, Spell.Cast for damage, or DamageActorValue on enemy health; access the network.
  - MUST: keep file encodings and line endings as they are.

Background (MAY):
  - build/fx-catalog.json and build/fx-bindings.json describe every copied FX record and what it is bound to; `unbound_spares` lists shaders already in the plugin but unused.
  - Two rounds already landed today (review fixes; log-noise guards + tree layout + short menu labels + ShowMenu default 0). Do not undo them.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

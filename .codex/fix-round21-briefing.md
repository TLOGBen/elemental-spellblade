Goal and acceptance:
Round 21 = rebuild every skill tree to v0.4 for the Skyrim SE 1.5.97 mod 元素魔戰士 at D:\Game\Other\SKSE\.codex\elemental-spellblade (git repo, clean at commit f5edfc4; round 20 / N2 is committed and deployed). The ESP generator still builds the v0.3 trees; v0.4 (`元素魔戰士規劃-v0.4.md`, the design truth) changed about a third of the nodes. After this round the in-game trees (perk records, names, descriptions, ranks, layout, MCM) are exactly v0.4, and every node whose mechanic is owned by Papyrus or by an already-live DLL slice (N1/N2) works as v0.4 says. Report in Traditional Chinese (台灣); code, identifiers and paths verbatim.

Read first: `build/tree-v04-inventory.md` (node-by-node v0.3→v0.4 comparison, wiring notes, risks, recommended 8-step breakdown, appendix A slot/FormID proposal — produced read-only before N2 finished, so re-check wiring against the committed N2 code), `元素魔戰士規劃-v0.4.md` section 5 (the trees; the skeleton table at its start is a pattern only — where a tree's own table differs, the tree's table wins), `.codex/fix-round20-briefing.md` and `.codex/impl-fix-round20.html` (the previous round's contract and decisions, still in force), `.strategic-advance/essb-standalone-build/CHECKPOINT.md`.

Context on quality (user's experience with earlier implementers): half-done work, hard-to-read code, checks forced to pass. Don't. Every check tests what the spec requires; what you cannot finish is reported, not papered over.

Commander rulings (binding):
  R1. No save migration. The user will start a new game only after the full version is done and keeps no old saves. Do not write respec/migration code. A state_schema_version bump is fine (fold everything into one bump this round).
  R2. Per-tree tables override the skeleton table (the v0.4 doc now says so). Known consequence: `ESSBElem.psc` (~line 617) applies the skeleton's 關閉專精「終焉後接管附傷」 to every tree — wrong for 火、土、風、血、暗; fix it.
  R3. The MCM 節點倍率 slider range is 1～5 (v0.4), default per v0.4.
  R4. Nodes whose mechanic belongs to a later slice (tagged DLL N3/N4/N5/N6 in v0.4): create the real perk record (v0.4 name, description, ranks, slot) so the tree is complete, but do not implement the mechanic; list them in the ledger per slice. They are real design nodes, not placeholders — do not invent effects for them.
  R5. Nodes tagged DLL N2 that N2 skipped because the node did not exist (element-less 吸魔 +5%, 滅法倍率, 燒魔倍數, and the N2 half of 寂滅) are now implemented in the DLL. The element-less slots whose points currently do nothing ((11,1,0), (11,1,1)) and the slots still running v0.3 effects ((11,0,0)–(11,0,4), (11,2,3)) end up with their v0.4 meaning, old effects removed.
  R6. Water 浸濕 +0.3 s per point (N2 could not change duration through CastSpellImmediate): use the same technique as silence — a small set of fixed-duration spells the DLL picks from.
  R7. FormIDs: keep the append-only policy (new records get new FormIDs; removed perks are retired, not reused) and update the validators with an explicit, reviewed allow-list rather than removing checks. Separate the FormID slot from the display order if the inventory's risk 4 requires it.

Required outcome:
  1. Trees, perk records, descriptions (Traditional Chinese, v0.4 wording and numbers), rank counts, layout and MCM tree UI match v0.4 for all 13 trees; `plan_trees.py` reads the v0.4 table format.
  2. A single name-to-position identity table that Papyrus, the DLL (`native/include/NodeIds.h`, `NODE_IDENTITY` in build/fix19_native.py) and the ESP generator are all checked against, by v0.4 name — so "buying A activates B" cannot pass the build. Every position-based read in Papyrus (~400 sites) and in the DLL must be covered.
  3. The two functions that write perk values directly (`ESSBController.RefreshRecovery`, `ESSBNodes.RefreshWeaponPercent`) are updated or removed in the same round as the ESP change for the slots they touch.
  4. Every node owned by Papyrus or by N1/N2 works per v0.4; the rest per R4. Ledger table: every node of every tree → status (done / later slice N3–N6 / unchanged) with evidence.
  5. Tests and build: `python -B native/build.py` and `python build_v03.py` exit 0 with every check line ok and meaningful; add offline checks for the identity table and for R2/R5/R6; the release ESP has zero entry-51 entries of ours; injected-fault spot checks as in round 20.
  6. Probe card `build/fix21-probes.md` (same style as build/fix20-probes.md: no log, short console commands, expected on-screen result, pass/fail, about ten minutes): opening each tree's menu and checking a few changed nodes' names/descriptions, and in-game checks for R2, R5, R6 and one changed Papyrus-owned node per element group.
  7. Append a changelog to 實作紀錄.md; list the player-visible changes.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\** and D:\Game\Other\SKSE\MO2\mods\**. You may run python, the build, MSVC/CMake from the installed Visual Studio 2022, and read-only disassembly tools.
  - Write set: native/** (ours; dependencies stay pinned), src/*.psc, build_v03.py, plan_trees.py and other generator modules in the repo root that build the ESP, settings.json, state-schema.lock.json, build/*.py, build/** generated outputs, build/plan-tree-nodes.json, build/v03-formids.json, build/fix21-probes.md, build/native-verification.md (append a section if the DLL changes), package/Elements Spellblade/** (generated), 實作紀錄.md (append only), .codex/pre-fix21-snapshot/** (take it FIRST: src, build_v03.py, root *.py, settings.json, build/v03-formids.json, build/plan-tree-nodes.json, native/src, native/include, native/tests), .codex/impl-fix-round21.html.
  - Network: not needed.
  - MUST NOT: write under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE; edit 元素魔戰士規劃-v0.3.md, 元素魔戰士規劃-v0.3_alter.md, 元素魔戰士規劃-v0.4.md, design-*.md, README.md, art-book/**, .strategic-advance/**, CLAUDE.md, build/tree-v04-inventory.md, build/native-verification-3.md; use git to commit, reset, checkout or stash (the commander commits); hook, trampoline, vtable-patch or write game memory; add ESP masters beyond Skyrim.esm; store design state in the DLL or add save serialization.
  - MUST: keep file encodings and line endings as they are (build_v03.py is CRLF; docs UTF-8 no BOM). Take ledger times from the system clock. If v0.4 is ambiguous for a node, pick the reading closest to the design's intent, record it in the ledger, keep going; stop only for something that would change the design itself (collect those in a list for the commander instead of stopping, unless it blocks the build).

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

When done, report (Traditional Chinese): VERDICT, what you did per outcome 1–7 and ruling R1–R7, test counts and what they prove, the per-slice list of nodes left for N3–N6, design ambiguities you resolved, player-visible changes, and the files to review first.

Supervision (supervised long task):
  - Ledger: D:\Game\Other\SKSE\.codex\elemental-spellblade\.codex\impl-fix-round21.html (skeleton created by the commander; in your write set). Update after reading (short plan), after each milestone, after each build/test run (exit code), on blockers. The commander patrols every 5 minutes.
  - Milestones: (1) snapshot + plan; (2) v0.4 parser and the identity table with its checks (failing checks expected at this point are fine — record them); (3) ESP records + MCM/tree UI; (4) Papyrus and DLL rewiring incl. R2, R3, R5, R6 and outcome 3; (5) tests, probe card, changelog; (6) full build and report. If resumed, read the ledger and continue from the last completed milestone.

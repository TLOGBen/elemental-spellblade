Goal and acceptance:
Two jobs for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade. Report in Traditional Chinese.

Background — engine facts measured in game this week (evidence .codex/smoke8-probe-results-Papyrus.0.log, .codex/smoke9-probe3-Papyrus.0.log):
  - Perk entry point 51 "Apply Combat Hit Spell": across ALL perks the actor holds, one hit applies exactly ONE spell; the winner is the entry with the numerically LOWEST priority (perk order / FormID irrelevant). Equal-priority ties: untested.
  - Our release plugin's only entry-51 perk is ESSB_P_HitProc, priorities 127..200 (so today any competing entry below 127 beats us). Priority is a byte; 0 is the floor.
  - A raw scan of the player's active load order found 55 plugins / 382 entry-51 perks: .codex/entry51-loadorder-scan.txt (produced by build/scan_entry51.py; it uses the MO2 profile D:\Game\Other\SKSE\MO2\profiles\normal and does not resolve overrides or localized names perfectly).

JOB 1 — compatibility audit (read-only analysis, the main deliverable).
Produce build/entry51-compat-audit.md (Traditional Chinese, plain language for the player, with an evidence appendix) answering, for every entry-51 perk that can end up ON THE PLAYER in this load order:
  a. Who ends up with it: player skill tree / perk tree mod (CSF, custom trees), quest or script AddPerk, SPID or other distributor (search the MO2 mods for *_DISTR.ini, KID, and scripts calling AddPerk), ability/spell that adds it, or NPC-only (then say why you are sure). Use the winning override record (last loaded) for each perk.
  b. When its entry fires: decode the perk conditions and the entry-point condition tabs (perk owner / target / attacker weapon etc.) into plain words, and classify: ALWAYS on every player weapon hit / on a common subset (e.g. every one-handed hit, every sneak hit, every power attack) / only with a specific weapon or buff / effectively never.
  c. Its priority, and whether it beats ESSB_P_HitProc today (127..200) and whether it would tie or beat us at priority 0.
  d. What the player loses when we win that hit (what that perk's spell does, in one line) and what they lose when it wins (our element proc that hit).
Put special focus on these, which look like always-on combat systems: EldenSkyrim.esp and EldenSkyrim_RimSkills.esp (衝擊力／韌性／標記), MaxsuPoiseForEldenRim.esp, For Honor in Skyrim.esp (硬直命中／命中時), StealthKillDetectionFix.esp, Colorful_Magic_SE.esp, Natura.esp, the Darenii spell packs (Abyss, Bloodmoon, Vulcano, Stellaris, Arcane, Lunaris, Arclight, Flames of Coldharbour, Necrom), Thunderchild, Apocalypse, Lost Grimoire, Madmen, Phenderix Elements. Also the vanilla/USSEP/WACCF versions of Hack and Slash, Limbsplitter, Bullseye, Warmaster, Paralyzing Strike, TrickShot, and Ordinator's player perks (not the 非玩家角色 NPC ones).
Finish with a short ranked list: the perks that realistically collide with our proc on a normal hit, most frequent first. Do not recommend a design option — the design organ does that. State plainly anything you could not determine from files.

JOB 2 — tie probe (small build).
Add to the probe plugin (build/fix18-probe-package/, isolated, master Skyrim.esm only) a fourth early probe: two SEPARATE perks, each with one entry 51 at priority 0, conditions true on the same hit, distinguishable spells (5 / 7 as before), in two variants that swap perk order / FormID (and, if you can, a third variant separating "added to the player first/last" from "lower/higher FormID"), so the result shows what decides an equal-priority tie. Add power 「探針：第四題」 (cast repeatedly to step through variants, each logging which variant is active), include it in 清理, verdict lines naming the deciding property, offline harness cases, and a section in build/fix18-probes.md.

Passing = the audit file exists and covers every player-reachable entry-51 perk in the scan with a/b/c/d filled or explicitly marked unknown with the reason; `python build_v03.py` exit 0 with every check line ok; release package byte-identical to D:\Game\Other\SKSE\MO2\mods\Elements Spellblade (read-only compare); probe plugin keeps master Skyrim.esm only.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\**, D:\Game\Other\SKSE\MO2\mods\** and D:\Game\Other\SKSE\MO2\profiles\normal\**; executing PapyrusCompiler.exe and any local decompiler/parsing you write yourself is allowed.
  - Write set (exact): build/entry51-compat-audit.md, build/entry51-*.json|txt (evidence), build/scan_entry51.py and other build/*.py helpers, build_v03.py (probe-package section only), src/ESSBProbe*.psc, build/fix18-probes.md, build/fix18-probe-package/**, build/** generated outputs, package/Elements Spellblade/** (regenerated, must come out byte-identical), 實作紀錄.md (append), .codex/impl-fix-round18g.html.
  - MUST NOT: write under D:\Game\Other\SKSE\MO2 or SkyrimSE; edit design/plan documents or .strategic-advance/**; access the network. Keep encodings/line endings (build_v03.py is CRLF).

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

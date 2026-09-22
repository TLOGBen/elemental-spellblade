Goal and acceptance:
Make the round-18 probe runnable without typing console commands. Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade. Report in Traditional Chinese.

Context: the player runs the probe card in build/fix18-probes.md by hand. The game console does not allow paste, so every command (coc, help lookup of the load-order prefix, equipping the dagger, forceav on the player, placeatme, clicking the bandit, tai, six forceav/restoreav on the bandit, addperk, addspell) is typed each attempt; the player has repeatedly lost the console selection and put the meter on themselves. The probe plugin (build/fix18-probe-package/, isolated, master Skyrim.esm only) currently has no quest and grants nothing automatically. That isolation rule was about not contaminating real saves; this plugin is only ever enabled for probe runs in throwaway saves, so granting things on load is now acceptable.

Required outcome:
  1. When the probe plugin is loaded, the player automatically receives three lesser powers (favoritable, castable with the power key), with Traditional Chinese names:
     - 「探針：準備＋第一題」: equip the vanilla iron dagger (add one if missing), set the player's AttackDamageMult to 0 (remember the old value), spawn one fresh test bandit a short distance in front of the player (vanilla EncBandit01Melee1HKhajiitM or a better-justified choice), put it in the exact state build/fix18-probes.md requires (AI stopped / non-hostile-acting so it does not fight back, health forced and restored to 10000, FireResist/MagicResist/AbsorbChance/HealRate/HealRateMult forced to 0, unequip its gear), give the player probe-1 perk (ESSB_ProbeAB) and not the probe-2 perks, and attach the meter to THAT bandit. It must be impossible for the meter to land on the player.
     - 「探針：第二題」: remove probe-1 perk, add both probe-2 perks, and re-attach a fresh meter to the same test bandit (spawn a new one if the old is gone or dead, prepared the same way).
     - 「探針：清理」: remove all probe perks and meters, restore the player's AttackDamageMult, delete the test bandit(s).
     Each power logs one `[ESSB-PROBE] SETUP ...` line saying what it did (bandit reference, perks now held), and a clear message on screen (Debug.Notification) telling the player the next action ("用匕首砍一刀，然後等").
  2. Moving to qasmoke is optional; if you add it, do it without console (e.g. MoveTo a marker from Skyrim.esm), and justify. Difficulty cannot be set by script — the meter already calibrates k, so just note it.
  3. Nothing about measurement, calibration, controls or verdict logic changes. Existing offline checks stay green; add checks for the setup powers' logic (bandit prepared state, perk sets per power, meter never on player, cleanup restores AttackDamageMult).
  4. Update build/fix18-probes.md: the early probes now read "favorite the three powers → cast 準備＋第一題 → hit once → read log → cast 第二題 → hit once → read log → cast 清理". Keep the old console route as an appendix.
  5. The release package is byte-identical (compare against D:\Game\Other\SKSE\MO2\mods\Elements Spellblade, read-only). The probe plugin keeps master Skyrim.esm only.

Passing = `python build_v03.py` exit 0 with every check line ok (full build), release hashes unchanged, new offline checks pass.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\** and D:\Game\Other\SKSE\MO2\mods\**; executing PapyrusCompiler.exe allowed.
  - Write set (exact): build_v03.py (probe-package section only), src/ESSBProbe*.psc, build/*.py helpers, build/fix18-probes.md, build/fix18-probe-package/**, build/** generated outputs of the full build, package/Elements Spellblade/** (regenerated, must come out byte-identical), 實作紀錄.md (append), .codex/impl-fix-round18e.html.
  - MUST NOT: write under D:\Game\Other\SKSE\MO2 or SkyrimSE; edit design/plan documents or .strategic-advance/**; add masters to the probe plugin; access the network. Keep encodings/line endings (build_v03.py is CRLF).

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

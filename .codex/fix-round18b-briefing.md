Goal and acceptance:
Small addendum to round 18 for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade. Scope: the optional probe plugin only (build/fix18-probe-package/Elements Spellblade Round18 Probes.esp, described in build/fix18-probes.md section 「提前探針」). Report in Traditional Chinese (code, identifiers, paths verbatim).

The player will run the two early probes (perks xx000820, and xx000821 + xx000822) in a throwaway save, but reading damage off a health bar and subtracting a physical baseline by hand is unreliable. Make the probes answer themselves in the Papyrus log (Documents\My Games\Skyrim Special Edition\Logs\Script\Papyrus.0.log; logging is already enabled on this machine).

Required outcome:
  1. Every probe hit writes log lines with one fixed, greppable prefix (e.g. `[ESSB-PROBE]`) that record what fired and how much, measured by the plugin itself — no manual baseline needed.
  2. After each hit the log also states the VERDICT in plain words, mapped to the switch it decides:
     - probe 1: both segments fired (5+7) → `lightning_roll_mode = additive`; only the first (5) → `chain`; anything else → print the observed values and say "unexpected, report".
     - probe 2: 0x1D doubled the entry-point spell (20) → `tier_multiplier_mode = entry`; unchanged (10) → `spell_variant`; anything else → observed values + "unexpected, report".
  3. The measurement must not lie. Decide from evidence which quantity actually reflects the engine behaviour being tested — for probe 2 in particular, whether `ActiveMagicEffect.GetMagnitude()` inside the effect already includes a "Mod Spell Magnitude" perk adjustment is itself uncertain. If you cannot establish that from files, measure BOTH the reported magnitude and the target's health change attributable to the probe spell, log both, and base the verdict on the one that is trustworthy (say which, and why, in 實作紀錄.md). Fire resistance of the target must not be able to flip a verdict — handle it (e.g. log the target's fire resist and normalise, or instruct a zero-resist target) and state how.
  4. The probe plugin stays isolated and opt-in: master Skyrim.esm only (plus Elements Spellblade.esp only if truly required — prefer not), no quest, no auto AddPerk, nothing that runs unless the player adds the probe perk. The release package must be byte-identical to the current round-18 release build (prove it: rebuild and compare hashes against .codex/pre-fix18b-snapshot or the current package).
  5. Update build/fix18-probes.md so the two early probes read: exact console steps → which log lines to look for → what each verdict line means. Keep it runnable by a player who does not read code.

Passing = `python build_v03.py` exits 0 with every check line ok, release package hashes unchanged, the probe plugin and its compiled script(s) produced, and a harness/offline check that exercises the probe script's verdict logic for the 5 / 12 / 10 / 20 / unexpected cases.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\*.esm and D:\Game\Other\SKSE\MO2\mods\**; executing PapyrusCompiler.exe is allowed.
  - Write set (exact): build_v03.py (probe-package section only), src/ESSBProbe*.psc (new, probe-only scripts), build/*.py verification helpers, build/fix18-probes.md, build/fix18-probe-package/**, 實作紀錄.md (append only), .codex/pre-fix18b-snapshot/** (take first), .codex/impl-fix-round18b.html (ledger).
  - MUST NOT: change anything that ends up in package/Elements Spellblade/**; write under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE (the commander deploys); edit the design/plan documents, .codex/pre-fix18-snapshot/** or .strategic-advance/**; access the network.
  - MUST: keep encodings and line endings as they are (build_v03.py is CRLF).

Standing authority as in round 18: acceptance wording that proves unsatisfiable is yours to resolve and record; anything the player can feel is not.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

Goal and acceptance:
Round 16 for the Skyrim SE 1.5.97 mod at D:\Game\Other\SKSE\.codex\elemental-spellblade: fix what an independent review of round 15 found. Report in Traditional Chinese (code, identifiers, paths verbatim).

The authoritative work list is review-fable-2026-09-19-r15.md in the campaign root — read it in full first; it carries file:line in the round-15 code, the trigger, the reasoning and a minimal fix for each item. It reviewed .codex/post-fix15-snapshot, which is identical to the current src/.

Fix, in this order:
  A. New defects (section 2 of the report):
     1. Z 融斷 settles marks on corpses 13-23 s after the kills (No Death Dispel keeps the mark effects alive until the controller tick clears the slot): XP, 反哺 mana, EndWater sync and 回流 mana are granted from corpses, and EndDark puts a death curse on a corpse host that is never resolved. Dead slots in the burst loop must be settled as deaths (CaptureDeath + ClearSlot), and FinishMark / ESSBReactions.End must not run on dead targets.
     2. 神佑 / deferred kill residual paths: add an IsCurrentController() gate to RefreshDivineProtection; stop old-generation ESSBTrees from calling RefreshAbilities ungated; add an MCM action "解除神佑保護" (confirm, then EndDeferredKill + disarm, notify) so a player can always release it, including before uninstalling. Keep the round-15 unconditional EndDeferredKill at the start of every Setup.
     3. Pending-path 冰封 lasts ~6 s instead of 3: FlushPendingState calls SetFrozen(0.0, deadline) → FreezeSeconds 0 and FreezeTime = deadline, then Tick applies the default 3 s from the deadline; the future FreezeTime also falsely trips RebaseImportedClock on host swap.
     4. 領域 bulk settlement: `ticks` is per domain and applied to every actor currently inside, so a very late tick gives a target that entered one second ago the whole backlog. Settle per target from the later of (domain start, that target's entry) — or cap the backlog per target at the time it was actually inside.
     5. Per-hit cost added by round 15: IsCasting (up to 10 natives) runs on every no-form hit regardless of whether 斷咒 is owned — compute it only when the node is owned; every GetStack calls Holder.IsDead() before the cheap `elapsed < 1` check — reorder; AddSync at sync stage 3 calls RefreshDivineProtection on every hit even without the 神佑 node — gate it on ownership. Re-measure the representative hit with build/papyrus_harness.py; it must not exceed round 13's 166 and should drop.
  B. Partly-fixed findings (section 1 of the report):
     1.2 連殺: gate it on the form that was active at the moment of the killing hit (the hit facts are already recorded before the dead-target rejection) instead of on the killing element, so a one-hit sneak kill in wind form counts. Record this as a deviation from round 14's "never guess from the current form" — it is not a guess, it is the recorded hit-time form, and 連殺 is a wind-form branch.
     1.6 The PERK-mirrored 2-second guard windows (GGuardDivine and siblings) still last until the next tick (11-34 s). End them by deadline at the moment they are read, or clear the mirror when the deadline passes at any read.
     1.9 火葬／亡魂: replace the 3-s KillProc window with the report's suggestion (predict lethality from the health before the damage), so it neither over-fires on unrelated kills nor misses tick-path captures.
     1.10 斷咒: keep the casting check at hit time only when the node is owned (see A5); accept event-processing latency and record it.

Passing = `python build_v03.py` exits 0 with every existing check line ok (READBACK masters ['Skyrim.esm'], records == manifest, CSF 13/13, DELIVERY ok, LAYOUT ok, DOT ok, MCM ok, MCM DEFAULTS ok, SCHEMA ok, FIX10-FIX15 ok, PLAN COVERAGE 0 unmapped, all scripts 0 errors) plus a new check line with one offline regression per item that fails on .codex/pre-fix16-snapshot sources and passes after; versus .codex/pre-fix16-snapshot/v03-formids.json no existing FormID changes (ESSB_DebugLevel 0x000811) unless a member-variable change forces a state_schema_version bump — avoid one if you can; if you cannot, bump per the round-9 rule and say why. You run the build yourself.

Permission boundary:
  - Read scope: everything under D:\Game\Other\SKSE\.codex\elemental-spellblade; read-only D:\Game\Other\SKSE\SkyrimSE\Data\*.esm and D:\Game\Other\SKSE\MO2\mods\** as the build needs; executing the PapyrusCompiler.exe that build_v03.py invokes is allowed.
  - Write set (exact): src/*.psc, build_v03.py, settings.json, state-schema.lock.json, build/*.py verification helpers, 實作紀錄.md (append only), build/** and package/Elements Spellblade/** (generated), .codex/impl-fix-round16.html (progress ledger; create first, update per item).
  - MUST NOT: write anything under D:\Game\Other\SKSE\MO2 or D:\Game\Other\SKSE\SkyrimSE (the game may be running); edit 元素魔戰士規劃-v0.3.md (record deviations instead), any review-*.md, .codex/pre-fix*-snapshot/** or .codex/post-fix*-snapshot/**, fx_extract.py, .strategic-advance/** (append-only commander ledger — never assert on its hash); add masters; introduce Utility.Wait loops, non-single RegisterForUpdate or per-frame polling; undo rounds 12-15 (per-hit cost reductions, kill attribution, real-time deadlines, deferred-kill safety); access the network.
  - MUST: keep file encodings and line endings as they are (build_v03.py is CRLF).

Background (MAY):
  - Real session evidence: .codex/smoke4-Papyrus.0.log. The user's VM is heavily loaded by another mod (~25,000 FloraHarvestScript binding errors per session), so the controller tick runs 11-34 s apart and events arrive 0-7 s late; every fix must hold under that.

You may change tools, commands, and technical approaches at will,
within the granted permissions and write set.
A single tool or approach being unavailable means only that this
strategy failed — switch approaches and retry. Report blocked only
when the acceptance goal is genuinely unreachable, or when you need
permissions or scope beyond what was granted.

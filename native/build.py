"""Pinned, offline MSVC build of ElementsSpellblade.dll and its tests; never deploys to the game.

The receipt (native/out/build-receipt.json) records what was actually used, read back from the
build itself: CMake version, the compiler CMake detected, the Windows SDK, and the CTest result.
"""
from pathlib import Path
import os, sys, subprocess, json, re, shutil
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'build')]
import build_v03 as b
import fix19_native as n

LOCK = json.loads((n.NATIVE / 'toolchain.lock.json').read_text(encoding='utf8'))
CMAKE = n.NATIVE / 'deps' / f"cmake-{LOCK['cmake']}-windows-x86_64" / 'bin' / 'cmake.exe'
if not CMAKE.is_file():
    raise RuntimeError(f'CMake {LOCK["cmake"]} missing at {CMAKE}; run python -B native/fetch_cmake.py once')
OUT = n.NATIVE / 'out'
LOG = ROOT / 'build/fix20-msvc.log'


def run(cmd, log):
    print(' '.join(map(str, cmd)), flush=True)
    log.write(f'$ {" ".join(map(str, cmd))}\n')
    log.flush()
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf8', errors='replace')
    log.write(result.stdout)
    log.flush()
    if result.returncode:
        raise RuntimeError(f'Native build step failed ({result.returncode}); see build/fix20-msvc.log')
    return result.stdout


def compiler():
    """(version, path) of the C++ compiler CMake detected for this build tree."""
    files = list((OUT / 'CMakeFiles').glob('*/CMakeCXXCompiler.cmake'))
    assert len(files) == 1, files
    text = files[0].read_text(encoding='utf8')
    version = re.search(r'set\(CMAKE_CXX_COMPILER_VERSION "([^"]+)"\)', text)[1]
    path = re.search(r'set\(CMAKE_CXX_COMPILER "([^"]+)"\)', text)[1]
    return version, path


def windows_sdk():
    text = (OUT / 'ElementsSpellblade.vcxproj').read_text(encoding='utf8')
    return re.search(r'<WindowsTargetPlatformVersion>([^<]+)</WindowsTargetPlatformVersion>', text)[1]


# Review fix 6: mutations of the status-layer sources themselves (not of the expectation tables). Each replaces one exact
# text once in a copy of the header; the copy is compiled into its own test binary (its folder comes first on the
# include path) and that binary must FAIL. (name, header, test, original, mutant)
MUTANTS = [
    ('miasma rate 0.5 -> 0.6', 'Status.h', 'status',
     'inline constexpr float kMiasmaRate = 0.5f;', 'inline constexpr float kMiasmaRate = 0.6f;'),
    ('growth in multiplied doses (the halving bug of review fix 1)', 'Status.h', 'status',
     """    const float base = now.magnitude / factor;
    Poison next;
    next.magnitude = std::min(base + doses * perDose, static_cast<float>(n3::kDoseCap) * perDose) * factor;
    next.remaining = now.magnitude <= 0.0f ? openSeconds : std::min(now.remaining + add, maximum);""",
     """    const float base = now.magnitude;
    Poison next;
    next.magnitude = std::min(base + doses * perDose, static_cast<float>(n3::kDoseCap) * perDose);
    next.remaining = now.magnitude <= 0.0f ? openSeconds : std::min(now.remaining + add, maximum);"""),
    ('spread keeps min(d - t, 12)', 'Status.h', 'status',
     'next.remaining = std::max(now.remaining, floor);', 'next.remaining = std::min(now.remaining, floor);'),
    ('crystals end with the frozen effect', 'Status.h', 'status',
     'inline constexpr float kCrystalMargin = 1.0f;', 'inline constexpr float kCrystalMargin = 0.0f;'),
    ('御風 back behind sync stage 3', 'Status.h', 'status',
     """    if (nodes.Has(node::kWindRideWind) && target.Has(StatusKind::kUnbalance)) {   // 御風：不看同調（只有免疫減速看）
        term.mult *= n3::kRideWind;""",
     """    if (nodes.Has(node::kWindRideWind) && t.syncStage >= 3 && target.Has(StatusKind::kUnbalance)) {
        term.mult *= n3::kRideWind;"""),
    ('聖佑 lasts 9 s', 'Status.h', 'status',
     'inline constexpr float kHolyDecay = 8.0f;', 'inline constexpr float kHolyDecay = 9.0f;'),
    ('the wash takes our own effects', 'StatusEngine.h', 'engine',
     'return v.hasSpell && handCast && hand && timed && buff && !v.ours && !v.company;',
     'return v.hasSpell && handCast && hand && timed && buff && !v.company;'),
    ('damage cast on a dead target', 'StatusEngine.h', 'engine',
     'if (l.spell && !corpse && !engine.Dead(on)) {', 'if (l.spell && !corpse) {'),
    # Round 27h (review 1-8): nor a mark or a status on an actor already dead.
    ('27h: a status cast on a dead target', 'StatusEngine.h', 'engine',
     'if (l.spell && !corpse && !engine.Dead(on)) {', 'if (l.spell && !corpse && !(op.op == Op::kDamage && engine.Dead(on))) {'),
    # Round 27h (verification): a task that overlapped another returns (Runtime.h Scope).
    ('27h: an overlapping body not told', 'Runtime.h', 'runtime',
     '            overlapped_ = true;   // round 27h: the body must not run (our containers are not built for two at once)',
     '            // overlapped_ = true;'),
    # Round 27h (review 1-2): a load clears only a session fault.
    ('27h: a load clears a hard fault', 'Runtime.h', 'runtime',
     '    return now.hard ? now : FaultLatch{};', '    return FaultLatch{};'),
    # Round 27h (review 1-6): the domain ledger drops what ended.
    ('27h: a domain past its end kept', 'Runtime.h', 'runtime',
     'std::erase_if(records_, [&](Record& r) { return r.untilMs <= nowMs || !alive(r); });',
     'std::erase_if(records_, [&](Record& r) { return !alive(r); });'),
    # Round 27h (review 1-5): the sink decides a weapon-source hit without the hands.
    ('27h: every hit waits for the hands', 'HitPipeline.h', 'runtime',
     '    return f.source != SourceKind::kWeapon && f.source != SourceKind::kOther;', '    return true;'),
    # Round 28 (D4 / D5): the switch's bounce and the burn-out lockout.
    ('28 D4: no debounce', 'Timer.h', 'runtime',
     'if (f.lastSwitchMs != 0 && f.nowMs >= f.lastSwitchMs && f.nowMs - f.lastSwitchMs < kSwitchDebounceMs) {',
     'if (f.lastSwitchMs != 0 && f.nowMs >= f.lastSwitchMs && f.nowMs - f.lastSwitchMs < 1) {'),
    ('28 D5: no burn-out lockout', 'Timer.h', 'runtime',
     '    if (!f.active && f.nowMs < f.burnoutUntilMs) {', '    if (!f.active && f.nowMs < 1) {'),
    # Round 28b (F1): ESSBNative.CastWith never scales a magnitude spell's magnitude; the copy is the asked seconds.
    ('28b F1: a magnitude spell takes the seconds as effectiveness', 'Runtime.h', 'runtime',
     '    if (f.noMagnitude) {\n        c.spell = f.spell;', '    if (true) {\n        c.spell = f.spell;'),
    ('28b F1: the copy one second off', 'Runtime.h', 'runtime',
     'c.spell = family.first + static_cast<std::uint32_t>(c.copySeconds - 1);',
     'c.spell = family.first + static_cast<std::uint32_t>(c.copySeconds);'),
    ('28b F1: a magnitude spell without copies scaled instead of refused', 'Runtime.h', 'runtime',
     '    c.spell = 0;   // refused: a duration asked of a magnitude spell without copies',
     '    c.spell = f.spell;\n    c.effectiveness = f.seconds / f.recordSeconds;'),
    # Round 28b (F5): 印潮 marks only the unmarked, at most 2.
    ('28b F5: 印潮 takes the marked too', 'Reactions.h', 'anchor',
     '    return x.board.MarkCount() == 0 && x.body.health > 0.0f;', '    return x.body.health > 0.0f;'),
    ('28b F5: 印潮 marks 3', 'Reactions.h', 'anchor',
     'inline constexpr int kSurgeTargets = 2;', 'inline constexpr int kSurgeTargets = 3;'),
    ('28b F5: 印潮 reaches 20 m', 'Reactions.h', 'anchor',
     'const Picked p = Around(crowd, 0, n5::kNear, n5::kSurgeTargets,', 'const Picked p = Around(crowd, 0, n5::kNear * 1.4f, n5::kSurgeTargets,'),
    # Round 28b (F7): 水臨強化's 10 s cooldown.
    ('28b F7: 水臨強化 without its cooldown', 'Reactions.h', 'anchor',
     '        if (bin.waterAdventReady) {\n            plan.Push(MakeEvent(Event::kCleanse, 1));',
     '        if (true) {\n            plan.Push(MakeEvent(Event::kCleanse, 1));'),
    ('28b F7: 水臨強化 soaks while cooling', 'Reactions.h', 'anchor',
     '            if (waterPlus && bin.waterAdventReady) {', '            if (waterPlus) {'),
    ('28b F7: the cooldown 1 s', 'Reactions.h', 'anchor',
     'inline constexpr std::uint64_t kWaterAdventCooldownMs = 10000;', 'inline constexpr std::uint64_t kWaterAdventCooldownMs = 1000;'),
    ('28b F7: the cooldown never ends', 'Reactions.h', 'anchor',
     '[[nodiscard]] constexpr bool Ready(std::uint64_t nowMs) const noexcept { return nowMs >= untilMs; }',
     '[[nodiscard]] constexpr bool Ready(std::uint64_t nowMs) const noexcept { return untilMs == 0 && nowMs >= untilMs; }'),
    # Round 27h (review 1-4): the sync a burst leaves.
    ('27h: 連斷 keeps nothing', 'Runtime.h', 'runtime',
     '        s.keep = s.keep > f.syncBefore / 2 ? s.keep : f.syncBefore / 2;', '        s.keep = s.keep;'),
    ('the removal forgets the crystals', 'StatusEngine.h', 'engine',
     'out.crystals = board.Layers(StatusKind::kCrystal);', 'out.crystals = 0;'),
    ('the bleed tick is not resolved', 'StatusEngine.h', 'engine',
     'spell::kRestoreStamina, spell::kBleedTick,\n', 'spell::kRestoreStamina,\n'),
    # Round 23 (N4): mutations of your resources and the hits you take (SelfLayer.h, Hurt.h, the N4 part of Status.h),
    # each must fail self_test against build/fix23-self-table.json.
    ('pools: blocked = the share of what reached you (not h x s / (1 - s))', 'Hurt.h', 'self',
     'blocked = lost * share.share / (1.0f - share.share);', 'blocked = lost * share.share;'),
    ('法盾 does not spend the overload first', 'Hurt.h', 'self',
     'const float fromPool = std::min(pool, owed);', 'const float fromPool = 0.0f;'),
    ('寒反 only on melee', 'Hurt.h', 'self',
     'if (retort && form == kFrost && nodes.Has(node::kFrostColdRetort)) {',
     'if (retort && f.melee && form == kFrost && nodes.Has(node::kFrostColdRetort)) {'),
    ('護血 overflow is not paid from health', 'Hurt.h', 'self',
     '            if (left < 0.0f) {\n                hurtYou(-left);',
     '            if (left < -1.0e9f) {\n                hurtYou(-left);'),
    # Round 23 review: the unpaid magicka and the DoT add-back.
    ('法盾／水幕 out of magicka: the unpaid part is not dealt', 'Hurt.h', 'self',
     'hurtYou((owed - paid) / share.cost);', '(void)paid;'),
    ('a DoT keeps the pools\' cut (not dealt back)', 'Hurt.h', 'self',
     'hurtYou(f.dotDamage * share.share / (1.0f - share.share));', '(void)share;'),
    ('the full power discharge is not a sure crit', 'SelfLayer.h', 'self',
     'plan.Push(res::Discharge(before, 1.0f, n4::kPower, n4::kPowerCrit));',
     'plan.Push(res::Discharge(before, 1.0f, n4::kPower, 1.5f));'),
    ('a sneak attack does not fill the wind gauge', 'SelfLayer.h', 'self',
     'res::SetWind(plan, me, threshold, in, nodes);   // 1.1',
     'res::SetWind(plan, me, me.Layers(StatusKind::kWindGauge) + 1, in, nodes);   // 1.1'),
    ('協奏 pending after a burst instead of a switch', 'SelfLayer.h', 'self',
     '    if (!burst) {\n        pw.Set(StatusKind::kConcert, 1.0f, 3600.0f);',
     '    if (burst) {\n        pw.Set(StatusKind::kConcert, 1.0f, 3600.0f);'),
    ('碎岩 stamina without G(L)', 'SelfLayer.h', 'self',
     'n4::kCrushStamina * TreeG(t, TreeOf(kEarth)) * t.multDrain;', 'n4::kCrushStamina * t.multDrain;'),
    ('三重奏 needs four elements', 'Status.h', 'self',
     '        if (kinds >= 3) {\n            mult *= 3.0f;', '        if (kinds >= 4) {\n            mult *= 3.0f;'),
    # Round 24 (N5): mutations of the reaction bodies, the burst, the death handling and the range scans (Reactions.h,
    # the crowd selection of StatusEngine.h); each must fail reaction_test against build/fix24-body-table.json (or
    # engine_test for the process-list selection).
    ('the poison death spread gives 60% (not 50%)', 'Reactions.h', 'reaction',
     'inline constexpr float kDeathShare = 0.5f;', 'inline constexpr float kDeathShare = 0.6f;'),
    ('K_sync at stage 3 is x2.5 (not x3)', 'Reactions.h', 'reaction',
     'inline constexpr std::array<float, 4> kSync{ 1.0f, 1.5f, 2.0f, 3.0f };',
     'inline constexpr std::array<float, 4> kSync{ 1.0f, 1.5f, 2.0f, 2.5f };'),
    ('a range body picks an ally', 'Reactions.h', 'reaction',
     'if (k == centre || !x.has || x.ally || !keep(x)) {', 'if (k == centre || !x.has || !keep(x)) {'),
    ('the burst ignores the end cooldown', 'Reactions.h', 'reaction',
     'const bool allowed = !target.Has(StatusKind::kEndCooldown);', 'const bool allowed = true;'),
    ('不死 ignores its 30 s cooldown', 'Reactions.h', 'reaction',
     'if (bleeding && nodes.Has(node::kBloodUndying) && t.syncStage >= 3 && !self.Has(StatusKind::kUndyingCooldown)) {',
     'if (bleeding && nodes.Has(node::kBloodUndying) && t.syncStage >= 3) {'),
    ('寂 burns without 寂每層燒魔', 'Reactions.h', 'reaction',
     'const float burn = n5::kHushBurn + n5::kHushBurnPerPoint * static_cast<float>(nodes.Rank(node::kNoFormHushBurn));',
     'const float burn = n5::kHushBurn;'),
    ('the echo is not x1.5 at night', 'Reactions.h', 'reaction',
     '        ratio *= n5::kEchoNight;', '        ratio *= 1.0f;'),
    ('濺血 clears the bleed', 'Reactions.h', 'reaction',
     'SurgeOn(p.k[i], 0.5f, false, 0.5f);', 'SurgeOn(p.k[i], 0.5f, true, 0.5f);'),
    ('a neutral you did not attack joins the crowd', 'StatusEngine.h', 'engine',
     'if (!a.hostile && !a.engaged) {', 'if (false) {'),
    # Round 24 review: the fusion hit (v0.4 2.7 D_burst), 冰封融斷's shatter switch, the essential exemption.
    ('a fusion deals the end move of the element again', 'Reactions.h', 'reaction',
     'const bool fused = reason == EndReason::kBurst && !chain;', 'const bool fused = false;'),
    ('a fusion shatters without 冰封融斷', 'Status.h', 'reaction',
     'if (target.Has(StatusKind::kFrozen) && (reason != EndReason::kBurst || nodes.Has(node::kFrostBurstShatter))) {',
     'if (target.Has(StatusKind::kFrozen)) {'),
    ('a named (not essential) enemy is exempt from rising again', 'Reactions.h', 'reaction',
     'if ((!marked && !summon) || corpse.essential || corpse.dragon || f.servant) {',
     'if ((!marked && !summon) || corpse.essential || corpse.body.vip || corpse.dragon || f.servant) {'),
    # Round 25 (N6): mutations of the per-second work, the domains' DLL halves and the hotkey decisions (Timer.h, the
    # domain cast of StatusEngine.h); each must fail timer_test against build/fix25-timer-table.json.
    ('長流 gives back 90% of the upkeep (not 80%)', 'Timer.h', 'timer',
     'inline constexpr float kFlowMagickaShare = 0.8f;', 'inline constexpr float kFlowMagickaShare = 0.9f;'),
    # 審查修正 (round 25 review): 雷雨 / 暴風雪 per 2.10, the domain scan's node gate, the blood maximum.
    ('any rain counts as 雷雨 (lightning ignored)', 'Timer.h', 'timer',
     'e.thunder = outdoors && f.weather == 2 && f.lightning != n6::kNoLightning;', 'e.thunder = outdoors && f.weather == 2;'),
    ('any snow counts as 暴風雪 (wind ignored)', 'Timer.h', 'timer',
     'e.stormy = outdoors && f.weather == 3 && f.wind >= n6::kBlizzardWind;', 'e.stormy = outdoors && f.weather == 3;'),
    ('the domain scan runs without a domain node', 'Timer.h', 'timer',
     '            return true;\n        }\n    }\n    return false;\n}', '            return true;\n        }\n    }\n    return true;\n}'),
    ('blood upkeep amount on the current maximum', 'Timer.h', 'timer',
     'out.bled = f.healthPermanent * BloodUpkeepFraction(fraction) * tt.multUpkeep;',
     'out.bled = f.healthMax * BloodUpkeepFraction(fraction) * tt.multUpkeep;'),
    ('魔力歸零 closes after 1 s (not 2 s)', 'Timer.h', 'timer',
     'inline constexpr float kManaEmptySlack = 0.5f;', 'inline constexpr float kManaEmptySlack = 1.5f;'),
    ('the clock counts paused time', 'Timer.h', 'timer',
     '    if (stopped) {\n        return b;\n    }\n    c.active += dt;', '    c.active += dt;'),
    ('blood upkeep at 70% health is 0.5% (not 0.6%)', 'Timer.h', 'timer',
     'pct = 0.6f + (f - 0.7f) * (0.4f / 0.3f);', 'pct = 0.5f + (f - 0.7f) * (0.5f / 0.3f);'),
    ('opening the blood form needs 10% magicka', 'Timer.h', 'timer',
     'if (wanted != kBlood && !f.freePass', 'if (!f.freePass'),
    ('定神 makes you slow-immune below sync stage 3', 'Timer.h', 'timer',
     '(t.syncStage >= 3 && (nodes.Has(node::kCommonComposure)', '(t.syncStage >= 0 && (nodes.Has(node::kCommonComposure)'),
    ('a domain reaches 4 m (not 3 m)', 'Timer.h', 'timer',
     'inline constexpr float kDomainRadius = 210.0f;', 'inline constexpr float kDomainRadius = 280.0f;'),
    ('潮池 washes every buff a second (not one)', 'Timer.h', 'timer',
     '        wash.element = 1;\n        plan.Push(wash);', '        plan.Push(wash);'),
    ('the storm charges without its 3 s clock', 'Timer.h', 'timer',
     'if (f.form == kLightning && f.thunder && !me.Has(K::kStormCooldown)) {', 'if (f.form == kLightning && f.thunder) {'),
    ('the domain spell overrides the hazard magnitude', 'StatusEngine.h', 'timer',
     'engine.Cast(Who::kTarget, spawn, 0.0f, 1.0f);', 'engine.Cast(Who::kTarget, spawn, 1.0f, 1.0f);'),
    # Round 25 hotfix: mutations of the data-load resolution (Load.h). load_test needs the ESP build_v03.py writes, so
    # these are only BUILT here; build/fix25_verify.py runs each on the written ESP and requires it to fail (LOAD_DEFERRED).
    ('the 0.25.0 registration: the 護血 pool and 寂 not in the status effect table', 'Load.h', 'load',
     '''    effect(essb::effect::kBloodGuard, "blood guard pool");
    effect(essb::effect::kHush, "hush");
''', ''),
    ('the loader skips the spells CastSpells names', 'Load.h', 'load',
     '''        if (!have(s.spells, id)) {
            spell(id, "cast spell", 0.0f);
        }''', '''        (void)id;'''),
    ('the status effect table left unsorted (EffectById is a binary search)', 'Load.h', 'load',
     '    std::sort(s.effects.begin(), s.effects.end());\n', ''),
    # Round 26 (the probe log): mutations of Trace.h and the probe-log hooks of StatusEngine.h; each must fail trace_test
    # (against build/fix26-trace-format.json). The log may never change a roll, lose a line's cut marker, write op-done after
    # an op that changes no value, or mislabel a scan verdict.
    ('the tape changes the roll it records', 'Trace.h', 'trace',
     'const bool v = rng_.Chance(probability);', 'const bool v = rng_.Chance(probability * 0.5f);'),
    ('a cut line does not end in ~', 'Trace.h', 'trace', "text_ += '~';", "text_ += '+';"),
    ('op-done after every apply', 'StatusEngine.h', 'trace',
     'return op == Op::kDamage || op == Op::kHeal', 'return op == Op::kApply || op == Op::kDamage || op == Op::kHeal'),
    ('a far actor reported as a neutral', 'StatusEngine.h', 'trace', 'why(i, Pick::kFar);', 'why(i, Pick::kNeutral);'),
    # Round 26b: the sinks read only their own event (Sinks.h).
    ('the death sink reads the killer', 'Sinks.h', 'trace',
     '    s.servant = world.Servant(corpse);', '    s.servant = world.Servant(corpse) || (killer && world.Servant(static_cast<Ref>(const_cast<void*>(killer))));'),
    # Round 26c: the tape's bound, the dispel re-find, the nested-hit drop.
    ('the tape writes past its end', 'Trace.h', 'trace', 'if (i >= 0 && i < kTape) {', 'if (i >= 0) {'),
    ('a dispel by a stale handle (no re-find by identity)', 'StatusEngine.h', 'trace',
     'if (!done && v.uid == id.uid && v.effect == id.effect && v.spell == id.spell) {', 'if (!done) {'),
    ('a hit raised in our own hit task is queued again', 'Sinks.h', 'trace',
     '    if (insideHitTask) {\n        return HitRoute::kNested;', '    if (false) {\n        return HitRoute::kNested;'),
    ('a blocked hotkey is still run', 'Sinks.h', 'trace',
     'out.push_back(Action{ ActionKind::kSwitch, element, 0, code, open });', 'out.push_back(Action{ ActionKind::kSwitch, element, 0, code, true });'),
    # Round 27 (T): Plugin.cpp's rules moved into Runtime.h; runtime_test.
    ('T: a dispel by a position kept across dispels (no re-find)', 'Runtime.h', 'runtime',
     '            if (!done && u == uid && b == base) {', '            if (!done && b == base) {'),
    ('T: read-only natives stop with the master switch', 'Runtime.h', 'runtime',
     '    return readOnly ? active : enabled;', '    return enabled;'),
    ('T: the timer task skips the clock\'s bars when switched off', 'Runtime.h', 'runtime',
     '    p.hudOff = !enabled;', '    p.hudOff = false;'),
    ('T: the crowd walks a follower\'s effect list', 'Runtime.h', 'runtime',
     '    return !hostile && !teammate && !dead &&', '    return !hostile && !dead &&'),
    # Round 27c (0.27.2): the planner's context and the executor's hard guard.
    ('27c: a copied context points at the dead local\'s tuning', 'Runtime.h', 'runtime',
     '    Context(const Context& other) : tuning(other.tuning), player(other.player), in(other.in) { in.tuning = &tuning; }',
     '    Context(const Context& other) : tuning(other.tuning), player(other.player), in(other.in) {}'),
    ('27c: a non-finite magnitude reaches the engine', 'StatusEngine.h', 'engine',
     '    return x == x && x <= kMaxMagnitude && x >= -kMaxMagnitude;', '    return true;'),
    # Round 27b: review B.
    ('B-N1: a chained end multiplies the modded body by its line again', 'Reactions.h', 'anchor',
     '        const ModScope scope(*this, chain ? CarriedMod() : mod);', '        const ModScope scope(*this, mod);'),
    ('B-N2: the open\'s passed doses take 節點倍率 again', 'Reactions.h', 'anchor',
     '            const int doses = RoundStochastic(stacks, rng_);', '            const int doses = RoundStochastic(mult, rng_);'),
    ('B-N3: the source burns with no fire form', 'Status.h', 'anchor',
     '    return fireForm || self.Has(StatusKind::kSourceLinger);', '    return true;'),
    ('B-N5: 催毒\'s line multiplies on top again', 'Status.h', 'anchor',
     '    return (1.0f + dose + Pct(t, nodes.Rank(node::kSignature[kPoison]), 0.03f)) / (1.0f + dose);',
     '    return 1.0f + Pct(t, nodes.Rank(node::kSignature[kPoison]), 0.03f);'),
    ('B-N6: a killing blow spends your overload', 'SelfLayer.h', 'anchor', '    p.overloadAfter = -1.0f;\n', ''),
    ('B-N7: a non-sneak hit keeps the old sneak row', 'Runtime.h', 'runtime',
     '    std::erase_if(rows, [&](const auto& row) { return std::get<0>(row) == target || now - std::get<2>(row) > 5000; });\n    if (sneak) {',
     '    if (sneak) {\n        std::erase_if(rows, [&](const auto& row) { return std::get<0>(row) == target || now - std::get<2>(row) > 5000; });'),
    ('B-N9: an expiry end\'s mark is not noted', 'Registry.h', 'runtime',
     'return r.tag.kind == TagKind::kMark && r.reason == engine::Removal::kExpired && IsElement(r.tag.index) ? r.tag.index : 0;',
     'return 0;'),
    # Round 27b: review A.
    ('A-N2: the registry answers by FormID alone (a new reference reads a deleted one\'s snapshot)', 'Registry.h', 'runtime',
     '        if (it == map_.end() || it->second.handle != actor.handle) {\n            return std::nullopt;',
     '        if (it == map_.end()) {\n            return std::nullopt;'),
    ('A-N4: an access violation swallowed with a lock held', 'Runtime.h', 'runtime',
     'code == kAccessViolation && locksHeld == 0 && base != 0', 'code == kAccessViolation && base != 0'),
    ('A-N3: the world clock counts a stall', 'Runtime.h', 'runtime', 'seconds > 0.0f && seconds <= 1.0f', 'seconds > 0.0f'),
    ('A-N10: a whole health change counted as ours', 'Runtime.h', 'runtime', 'return d > b ? b : d < -b ? -b : d;', 'return d;'),
    # Round 28 (the user's fixes 2026-09-28): 死咒's boss factor, 三重奏's rest, the guide, 長流's refund.
    ('28: 死咒 lost-health part without the boss factor', 'Status.h', 'anchor',
     '(in.body.vip ? n3::kDeathCurseVip : 1.0f);', '(in.body.vip ? 1.0f : 1.0f);'),
    ('28: 三重奏 without its rest', 'Status.h', 'anchor',
     'if (nodes.Has(node::kCommonTrio) && IsElement(element) && !me.Has(StatusKind::kTrioCooldown)) {',
     'if (nodes.Has(node::kCommonTrio) && IsElement(element)) {'),
    ('28: the guide × the end again', 'Status.h', 'anchor',
     'tw.Set(StatusKind::kGuided, guide, Scaled(t, 30.0f));', 'tw.Set(StatusKind::kGuided, guide * mult, Scaled(t, 30.0f));'),
    ('28 F11: 長流 refunds the fee', 'Timer.h', 'timer',
     'plan.Push(Amount(Op::kRestoreMagicka, out.spent * n6::kFlowMagickaShare));', 'plan.Push(Amount(Op::kRestoreMagicka, fee * n6::kFlowMagickaShare));'),
    # Round 28 (the user's decisions 2026-09-28): anchor_test RotationAnchors / WaterAdventAnchors / SourcedBurstAnchors.
    ('28 D1: a forced open cuts a mark again', 'Status.h', 'anchor',
     '    if (!hitWork && target.MarkCount() > 0) {', '    if (!hitWork && target.MarkCount() > 99) {'),
    ('28 D2: every forced open gives your gains', 'Reactions.h', 'anchor',
     '                PlanSelfOpen(plan, element, target, self, in, nodes, rng, !gained);\n                gained = true;\n            }\n        });\n    };',
     '                PlanSelfOpen(plan, element, target, self, in, nodes, rng, true);\n                gained = true;\n            }\n        });\n    };'),
    ('28 D3: 水臨強化 without a hostile in range', 'Reactions.h', 'anchor',
     '    if (waterPlus && ring.n > 0) {', '    if (waterPlus) {'),   # round 28b: the test reads waterPlus
    ('28 D6: the source mark bursts whole', 'Reactions.h', 'anchor',
     'settle(e, sourced ? n3::kSourcedBurst : 1.0f);', 'settle(e, 1.0f);'),
    # Round 27g (0.27.6): 傷害倍率 covers every damage of ours (anchor_test DamageMultAnchors).
    ('27g: 死咒 lost-health part without the damage multiplier', 'Status.h', 'anchor',
     'lost * ratio * vulnerability * t.baseDamageMult * (in.body.vip', 'lost * ratio * vulnerability * (in.body.vip'),
    ('27g: 火源 cost part without the damage multiplier', 'Status.h', 'anchor',
     'source.perEnemy = (base + source.cost * n) * NodeSum(kFire, false, t, nodes) * t.baseDamageMult;',
     'source.perEnemy = (base * t.baseDamageMult + source.cost * n) * NodeSum(kFire, false, t, nodes);'),
    ('27g: 放血 without the damage multiplier', 'Status.h', 'anchor',
     'return static_cast<float>(layers) * rate * health * t.multDot * t.baseDamageMult;',
     'return static_cast<float>(layers) * rate * health * t.multDot;'),
    ('27g: 血刃 flat part without the damage multiplier', 'HitMath.h', 'anchor',
     'proc.magnitude += terms.flat[element] * t.baseDamageMult;', 'proc.magnitude += terms.flat[element];'),
    ('27g: 小滅法 without the damage multiplier', 'HitMath.h', 'anchor',
     '(plan.overloaded ? kOverloadDispel : 0.0f)) * trueMult * t.baseDamageMult;', '(plan.overloaded ? kOverloadDispel : 0.0f)) * trueMult;'),
    ('27g: 滅法 without the damage multiplier', 'HitMath.h', 'anchor',
     'const float damage = (spend + y) * multiplier * trueMult * t.baseDamageMult;', 'const float damage = (spend + y) * multiplier * trueMult;'),
    # Round 27g (0.27.6): a branch bought in the skill menu (5 points: the framework's 1 + 4 at the close).
    ('27g: exactly 4 points left after the framework is not enough for a branch', 'Runtime.h', 'runtime',
     '    if (available >= rest) {', '    if (available > rest) {'),
    ('27g: a refunded branch keeps the framework point', 'Runtime.h', 'runtime',
     '    return { false, available, available + kBranchFrameworkCost, available + kBranchFrameworkCost };',
     '    return { false, available, available, available + kBranchFrameworkCost };'),
    ('A-N7: a corpse event of the death task sent by the hit task', 'StatusEngine.h', 'runtime',
     '    return e == Event::kEnd;', '    return e == Event::kEnd || e == Event::kAsh;'),
    ('G15: a step key bound to a form is also the step marker', 'Sinks.h', 'trace',
     'if (!hotkey && f.active && f.trace', 'if (f.active && f.trace'),
    # Round 26d (0.26.3): Rng() calling itself again (the 0.26.2 freeze); trace_test's watchdog must end it with a failure.
    ('Rng() calls itself (the 0.26.2 freeze)', 'Trace.h', 'trace',
     '    return *rng;\n}', '    return TaskRng(rng, inTask, outsideReported, onOutside);\n}'),
    # Round 27: the engine glue without the engine (Runtime.h, Registry.h) and your own health (Hurt.h); runtime_test.
    ('E1: the removal sink does not erase the row that left (a stale snapshot settles twice)', 'Registry.h', 'runtime',
     'rows.erase(rows.begin() + static_cast<std::ptrdiff_t>(i));', '(void)i;'),
    ('E1: an expiry told from a dispel without the slack (the timer clock is 100 ms coarse)', 'Registry.h', 'runtime',
     'out.elapsed >= out.duration - kExpirySlack', 'out.elapsed >= out.duration'),
    ('E3: a new game keeps the old session (its queued tasks act in the new game)', 'Runtime.h', 'runtime',
     '// a new game from the main menu (no PreLoadGame before it): a new session all the same\n        s.epoch.fetch_add(1);',
     '// a new game from the main menu (no PreLoadGame before it): a new session all the same\n'),
    ('E3: the main menu does not end the session', 'Runtime.h', 'runtime',
     '    case Msg::kPreLoadGame:\n    case Msg::kMainMenu:\n', '    case Msg::kMainMenu:\n        break;\n    case Msg::kPreLoadGame:\n'),
    ('E4: a hit of this frame is taken before its damage is applied', 'Runtime.h', 'runtime',
     '(q_[n].frame < frame || nowMs', '(q_[n].frame <= frame || nowMs'),
    ('G7: our own health payments counted as the enemy damage', 'Hurt.h', 'runtime',
     'f.healthBefore - f.healthAfter + f.ownDelta', 'f.healthBefore - f.healthAfter'),
    ('G12: a failing log escapes SKSEPlugin_Query (the DLL is refused)', 'Runtime.h', 'runtime',
     '    try {\n        openLog();\n    } catch (...) {\n    }', '    openLog();'),
    ('E2: an access violation in the engine swallowed', 'Runtime.h', 'runtime',
     'locksHeld == 0 && base != 0 && at >= base && at < end', 'locksHeld == 0'),
    ('G6: the killing blow casts on the corpse', 'StatusEngine.h', 'runtime',
     'if (l.spell && !corpse && !engine.Dead(on)) {', 'if (l.spell) {'),   # 27h: the dead check covers the corpse too
    ('G6: the killing blow dispels from the corpse', 'StatusEngine.h', 'runtime',
     'if (l.dispelEffect && !corpse) {', 'if (l.dispelEffect) {'),
    ('G9: a mark the killing end took is not counted at the death', 'Registry.h', 'runtime',
     'if ((mask & (1u << e)) && !board.mark[e].has) {', 'if (false) {'),
    # Round 27 (M4): the hand anchors at level 100 / 節點倍率 5 / every line (anchor_test).
    ('G1: the closing lines multiplied again (common × the tree)', 'Status.h', 'anchor',
     'return 1.0f + lines + Pct(t, nodes.Rank(node::kEndMain[element]), 0.02f);',
     'return (1.0f + lines) * (1.0f + Pct(t, nodes.Rank(node::kEndMain[element]), 0.02f));'),
    ('G1: the end move\'s legend line multiplied on the sum', 'Reactions.h', 'anchor',
     'return (mod_ + SignaturePct(element, T(), nodes_) + extra) / mod_;', 'return (1.0f + SignaturePct(element, T(), nodes_) + extra);'),
    ('G1: 碎冰 at the end takes the end lines and the guide', 'Status.h', 'anchor',
     'rule::Shatter(plan, target, in, nodes, 2);   // round 27 (G1)', 'rule::Shatter(plan, target, in, nodes, 2, settle);   // round 27 (G1)'),
    ('G1: 催毒 compounds', 'Status.h', 'anchor',
     'const float whole = std::max(rule::PoisonFactor(target), factor);', 'const float whole = rule::PoisonFactor(target) * factor;'),
    ('G1: 死咒\'s lost-health part takes the fuse', 'Status.h', 'anchor',
     'lost * ratio * vulnerability * t.baseDamageMult * (in.body.vip', 'lost * ratio * fuseMult * t.baseDamageMult * (in.body.vip'),   # 27g/28: the line grew
    ('G1: 血潮\'s current-health part takes the end\'s K and sum', 'Reactions.h', 'anchor',
     'const float amount = (bleed * surge * Signature(kBlood) + health) * ReactionVulnerability(m.board, self_, T(), nodes_);',
     'const float amount = (bleed * surge * Signature(kBlood) + health * surge) * ReactionVulnerability(m.board, self_, T(), nodes_);'),
    ('G1: 聖裁 III takes 聖佑各階', 'Status.h', 'anchor',
     'damage = in.body.healthMax * (in.body.vip ? n3::kJudgeTopVip : n3::kJudgeTop) * t.baseDamageMult * tierT * (1.0f + judgeLine);',
     'damage = in.body.healthMax * (in.body.vip ? n3::kJudgeTopVip : n3::kJudgeTop) * t.baseDamageMult * tierT * (1.0f + judgeLine + Pct(t, nodes.Rank(node::kDivineHolyBonus), 0.01f) * 3.0f);'),
    ('G3: the open\'s counts take 節點倍率', 'Status.h', 'anchor',
     'float openStacks = 1.0f + static_cast<float>(nodes.Rank(node::kOpenEffect[element])) * 0.03f;', 'float openStacks = openMult;'),
    ('G4: 熔斷\'s fuse overheats with no form', 'Status.h', 'anchor',
     'if (in.n4 && in.formElement != kFire) {', 'if (false) {'),
    ('B-small: the burst\'s ops in the old 512 slots', 'Status.h', 'anchor',
     'inline constexpr int kMaxStatusOps = 8192;', 'inline constexpr int kMaxStatusOps = 512;'),
    ('B-small: the death curse kills without 冥召\'s marker', 'Status.h', 'anchor',
     '    Writer{ plan, target, Who::kTarget }.Set(StatusKind::kCurseKill, 1.0f, 1.0f);', '    (void)0;'),
    # Round 29 (灌注, .codex/design-infuse-2026-09-28.md): anchor_test InfuseAnchors / timer_test InfuseTimerChecks.
    ('29: K_infuse left out of the element proc', 'HitMath.h', 'anchor',
     'proc.magnitude *= kInfuseK;       // round 29', '(void)0;       // round 29'),
    ('29: lightning doubled on top of its forced crit (x5)', 'HitMath.h', 'anchor',
     'proc.magnitude *= kInfuseCrit;', 'proc.magnitude *= kInfuseCrit * kInfuseK;'),
    ('29: the floor ignored (cost alone is enough)', 'HitMath.h', 'anchor',
     'if (magicka < out.cost + out.floor || magicka - out.cost < kInfuseKeep) {', 'if (magicka < out.cost || magicka - out.cost < kInfuseKeep) {'),
    ('29: a wind repeat pays again (not one charge per event)', 'SelfLayer.h', 'anchor',
     '    again.cost = 0.0f;', '    (void)again.cost;'),
    ('29: 長流 refunds the infusion as upkeep', 'Timer.h', 'timer',
     'plan.Push(Amount(Op::kRestoreMagicka, out.spent * n6::kFlowMagickaShare));',
     'plan.Push(Amount(Op::kRestoreMagicka, (out.spent + f.infused) * n6::kFlowMagickaShare));'),
]
LOAD_DEFERRED = 'load'   # the mutants of this test run in build/fix25_verify.py (check_load), on the written ESP


def run_mutants(log):
    """Builds one test binary per mutant (a separate CMake tree under native/out/mutants) and requires each to fail."""
    root = OUT / 'mutants'
    # A fresh tree every time: MSBuild tracks the headers a compile read, not the folder a mutant header appears in,
    # so a stale object would hide a mutant (round 23 saw one survive that way).
    if root.exists():
        shutil.rmtree(root)
    lines = ['cmake_minimum_required(VERSION 3.24)', 'project(ESSBMutants LANGUAGES CXX)', 'set(CMAKE_CXX_STANDARD 23)',
             'set(CMAKE_CXX_STANDARD_REQUIRED ON)', 'set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")']
    inc = n.NATIVE / 'include'
    js = n.NATIVE / 'deps/json/single_include'
    for i, (name, header, test, old, new) in enumerate(MUTANTS):
        text = (inc / header).read_text(encoding='utf-8')
        assert text.count(old) == 1, ('mutant text not found exactly once', name)
        folder = root / f'm{i}'
        folder.mkdir(parents=True, exist_ok=True)
        # Every header is copied next to the mutant: a quoted include resolves in the including header's own folder
        # first, so a mutant reached through another header (SelfLayer.h through Hurt.h) needs its includer beside it.
        for other in inc.glob('*.h'):
            if other.name != header:
                (folder / other.name).write_bytes(other.read_bytes())
        (folder / header).write_text(text.replace(old, new), encoding='utf-8', newline='\n')
        source = n.NATIVE / 'tests' / {'status': 'status_test.cpp', 'engine': 'engine_test.cpp', 'self': 'self_test.cpp',
                                       'reaction': 'reaction_test.cpp', 'timer': 'timer_test.cpp', 'load': 'load_test.cpp',
                                       'trace': 'trace_test.cpp', 'runtime': 'runtime_test.cpp',
                                       'anchor': 'anchor_test.cpp'}[test]
        lines += [f'add_executable(m{i} "{source.as_posix()}")',
                  f'target_include_directories(m{i} PRIVATE "{folder.as_posix()}" "{inc.as_posix()}" "{js.as_posix()}")',
                  f'target_compile_options(m{i} PRIVATE /EHsc /utf-8 /bigobj)']
    (root / 'CMakeLists.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    run([CMAKE, '-S', root, '-B', root / 'build', '-G', 'Visual Studio 17 2022', '-A', 'x64'], log)
    run([CMAKE, '--build', root / 'build', '--config', 'Release', '--parallel', '8'], log)
    results = []
    for i, (name, header, test, *_rest) in enumerate(MUTANTS):
        exe = root / 'build' / 'Release' / f'm{i}.exe'
        if test == LOAD_DEFERRED:
            assert exe.is_file(), ('load mutant not built', name)
            results.append(dict(name=name, header=header, test=test, exit=None, exe=exe.relative_to(ROOT).as_posix(),
                                first_line='built here; run by build/fix25_verify.py on the written ESP (must fail)'))
            continue
        tables = {'status': ['build/fix22-status-table.json', 'build/fix22-wiring.json'],
                  'self': ['build/fix23-self-table.json', 'build/fix23-wiring.json'],
                  'reaction': ['build/fix24-body-table.json', 'build/fix24-wiring.json'],
                  'timer': ['build/fix25-timer-table.json', 'build/fix25-wiring.json'],
                  'trace': ['build/fix26-trace-format.json']}.get(test, [])
        args = [exe] + [ROOT / t for t in tables]
        r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf8', errors='replace')
        log.write(f'$ mutant {i} ({name}): exit {r.returncode}\n{r.stdout}\n')
        if r.returncode == 0:
            raise RuntimeError(f'NATIVE MUTANT survived: {name} ({header}) -- the {test} test does not see it')
        results.append(dict(name=name, header=header, test=test, exit=r.returncode, first_line=(r.stdout.strip().splitlines() or [f'no output: the process died (exit {r.returncode:#x})'])[-1][:200]))
    return results


# Round 27d (0.27.3): the lifetime net. Two lifetime bugs in a row (0.27.1's self-pointing Context copy, 0.27.2's node
# view bound to a temporary) were invisible to the MSVC build and the tests. When clang-cl is installed (LLVM), the DLL
# source and every test are compiled once more, syntax only, with clang's lifetime warnings as errors; a negative control
# (tests/lifetime_net.cpp) must fail, or the net is not armed. tests/asan_harness.cpp then runs under AddressSanitizer
# (clang-cl's ASan on this toolchain aborts on any throw, so the throwing tests stay on MSVC). Without clang-cl the receipt says "skipped" (the MSVC build still decides).
CLANG = Path(r'C:\Program Files\LLVM\bin\clang-cl.exe')
VCVARS = Path(r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat')
LIFETIME_FLAGS = ['/nologo', '/std:c++latest', '/EHsc', '/utf-8', '-fdelayed-template-parsing', '-Wno-everything',
                  '-Werror=dangling', '-Werror=dangling-gsl', '-Werror=return-stack-address', '-Werror=dangling-field',
                  '-Werror=dangling-initializer-list', '/DWIN32', '/D_WINDOWS', '/DWINVER=0x0601', '/D_WIN32_WINNT=0x0601',
                  '/DENABLE_SKYRIM_SE=1', '/DHAS_SKYRIM_MULTI_TARGETING=1', '/DSPDLOG_COMPILED_LIB']
ASAN_TESTS = ['asan_harness']   # the runtime / engine tests throw to check; clang-cl's ASan here cannot run a throw


def in_vcvars(args, log):
    line = 'call "' + str(VCVARS) + '" >nul 2>nul && ' + subprocess.list2cmdline([str(a) for a in args])
    # one string: cmd.exe does not understand the backslash-escaped quotes a list argument would get
    result = subprocess.run('cmd /d /s /c "' + line + '"', capture_output=True, text=True, encoding='utf-8', errors='replace')
    log.write(f'$ {line}\n{result.stdout}{result.stderr}\n')
    return result


def lifetime_net(log):
    if not CLANG.is_file() or not VCVARS.is_file():
        return {'status': 'skipped', 'reason': 'clang-cl or vcvars64.bat not installed'}
    native = n.NATIVE
    includes = []
    for d in ['include', 'deps/json/single_include', 'deps/CommonLibSSE-NG/include', 'deps/spdlog/include']:
        includes += ['/I', str(native / d)]
    checked = []
    control = in_vcvars([CLANG, *LIFETIME_FLAGS, '/Zs', *includes, native / 'tests/lifetime_net.cpp'], log)
    if control.returncode == 0 or 'dangling' not in (control.stdout + control.stderr):
        raise RuntimeError('LIFETIME NET not armed: tests/lifetime_net.cpp (a view on a temporary) compiled cleanly')
    sources = [native / 'src/Plugin.cpp'] + sorted(p for p in (native / 'tests').glob('*_test.cpp')) + [native / 'tests/asan_harness.cpp']
    for src in sources:
        r = in_vcvars([CLANG, *LIFETIME_FLAGS, '/Zs', *includes, src], log)
        if r.returncode != 0:
            raise RuntimeError(f'LIFETIME NET: {src.name} has a dangling reference / pointer (clang-cl); see build/fix20-msvc.log')
        checked.append(src.name)
    asan_dir = OUT / 'asan'
    asan_dir.mkdir(exist_ok=True)
    runtime_lib = next(iter(sorted((CLANG.parent.parent / 'lib/clang').glob('*/lib/windows'))), None)
    ran = []
    for test in ASAN_TESTS:
        exe = asan_dir / f'{test}.exe'
        r = in_vcvars([CLANG, '/nologo', '/std:c++latest', '/EHsc', '/utf-8', '/O1', '/Zi', '/MD', '-fsanitize=address',
                       '/D_DISABLE_STL_ANNOTATION', *includes, native / f'tests/{test}.cpp', f'/Fe:{exe}', f'/Fo:{asan_dir}\\',
                       '/link', '/NODEFAULTLIB:stl_asan.lib', f'/LIBPATH:{runtime_lib}'], log)
        if r.returncode != 0:
            raise RuntimeError(f'ASAN build of {test} failed; see build/fix20-msvc.log')
        env = dict(os.environ, PATH=f'{runtime_lib};' + os.environ.get('PATH', ''))
        run_r = subprocess.run([str(exe)], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, cwd=str(asan_dir))
        log.write(f'$ {exe}\n{run_r.stdout}{run_r.stderr}\n')
        if run_r.returncode != 0 or 'AddressSanitizer' in run_r.stderr:
            raise RuntimeError(f'ASAN: {test} failed under AddressSanitizer; see build/fix20-msvc.log')
        ran.append(test)
    return {'status': 'ok', 'clang': str(CLANG), 'checked': checked, 'control': 'caught', 'asan': ran}


# Round 27d (0.27.3): the DLL's PDB, kept for symbolizing crash logs (build/pdb/, never in package/), and proved to be the
# PDB of the DLL: the DLL's CodeView (RSDS) GUID and age equal the PDB info stream's.
import shutil as _shutil
import struct as _struct


from fix27_pdb import dll_codeview, pdb_info   # build/fix27_pdb.py (fix27_verify reads the same)


def keep_pdb():
    dll = OUT / 'Release/ElementsSpellblade.dll'
    pdb = OUT / 'Release/ElementsSpellblade.pdb'
    if not pdb.is_file():
        raise RuntimeError('the release build wrote no ElementsSpellblade.pdb (CMakeLists /Zi /DEBUG:FULL)')
    guid, age, _name = dll_codeview(dll)
    pguid, page = pdb_info(pdb)
    if (guid, age) != (pguid, page):
        raise RuntimeError(f'PDB mismatch: DLL {guid.hex()} age {age} vs PDB {pguid.hex()} age {page}')
    target = ROOT / f'build/pdb/ElementsSpellblade-{n.NATIVE_VERSION}.pdb'
    target.parent.mkdir(parents=True, exist_ok=True)
    _shutil.copy2(pdb, target)
    kept_guid, kept_age = pdb_info(target)
    if (kept_guid, kept_age) != (guid, age):
        raise RuntimeError('the kept PDB copy does not match the DLL')
    return {'path': str(target.relative_to(ROOT)).replace('\\', '/'), 'guid': guid.hex(), 'age': age, 'sha256': n.sha(target)}


def main():
    n.check_deps()
    n.generate_header(b)
    cases = n.fixture(b)
    import fix26_format   # round 26: the probe log's line formats (trace_test and build/probe-judge.py read the same file)
    fix26_format.FIXTURE()
    OUT.mkdir(exist_ok=True)
    receipt = OUT / 'build-receipt.json'
    if receipt.exists():
        receipt.unlink()
    before = n.inputs()
    with LOG.open('w', encoding='utf8') as log:
        cmake_version = run([CMAKE, '--version'], log).split()[2]
        run([CMAKE, '-S', n.NATIVE, '-B', OUT, '-G', 'Visual Studio 17 2022', '-A', 'x64'], log)
        run([CMAKE, '--build', OUT, '--config', 'Release', '--parallel', '8'], log)
        ctest = run([CMAKE.with_name('ctest.exe'), '--test-dir', OUT, '-C', 'Release', '--output-on-failure', '-V'], log)
        mutants = run_mutants(log)
        lifetime = lifetime_net(log)
    assert n.inputs() == before, 'Sources changed during compile; rebuild'
    pdb = keep_pdb()
    cl_version, cl_path = compiler()
    sdk = windows_sdk()
    drift = (cl_version, cmake_version, sdk) != (LOCK['cl_version'], LOCK['cmake'], LOCK['windows_sdk'])
    if drift or f"/MSVC/{LOCK['toolset_directory']}/" not in cl_path:
        raise RuntimeError(f'Toolchain drift: cl {cl_version} ({cl_path}) / cmake {cmake_version} / SDK {sdk} vs toolchain.lock.json')
    summary = re.search(r'(\d+)% tests passed, (\d+) tests failed out of (\d+)', ctest)
    assert summary and summary[2] == '0', 'CTest did not report a clean run'
    totals = re.findall(r'^\d+: (NATIVE [A-Z ]+ ok: .*)$', ctest, re.M)
    receipt.write_text(json.dumps({
        'inputs': before,
        'dll_sha256': n.sha(OUT / 'Release/ElementsSpellblade.dll'),
        'native_version': n.NATIVE_VERSION,
        'generator': 'Visual Studio 17 2022',
        'cmake': cmake_version,
        'cl_version': cl_version,
        'cxx_compiler': cl_path,
        'windows_sdk': sdk,
        'ctest': {'passed_percent': int(summary[1]), 'failed': int(summary[2]), 'tests': int(summary[3]), 'lines': totals},
        'magnitude_scenarios': cases,
        'mutants': mutants,
        'lifetime_net': lifetime,
        'pdb': pdb,
    }, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    by = {}
    for m in mutants:
        by[m['header']] = by.get(m['header'], 0) + 1
    ran = [m for m in mutants if m['exit'] is not None]
    print(f'NATIVE MUTANTS ok: {len(ran)}/{len(ran)} source mutations make the tests fail '
          f'(+{len(mutants) - len(ran)} Load.h mutants built for build/fix25_verify.py) '
          f'({", ".join(f"{h} {k}" for h, k in by.items())})')
    if lifetime['status'] == 'ok':
        print(f"LIFETIME NET ok: clang-cl dangling checks clean on {len(lifetime['checked'])} sources (the negative control caught); "
              f"AddressSanitizer clean on {', '.join(lifetime['asan'])}")
    else:
        print(f"LIFETIME NET skipped: {lifetime['reason']}")
    print(f"PDB ok: {pdb['path']} matches the DLL (CodeView GUID {pdb['guid']} age {pdb['age']}); not shipped")
    print(f'Native build ok: cl {cl_version}, cmake {cmake_version}, SDK {sdk}; ctest {summary[3]} test(s), 0 failed; receipt written.')


if __name__ == '__main__':
    main()

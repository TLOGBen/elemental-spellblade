"""Pinned, offline MSVC build of ElementsSpellblade.dll and its tests; never deploys to the game.

The receipt (native/out/build-receipt.json) records what was actually used, read back from the
build itself: CMake version, the compiler CMake detected, the Windows SDK, and the CTest result.
"""
from pathlib import Path
import sys, subprocess, json, re, shutil
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
     'if (l.spell && !(op.op == Op::kDamage && engine.Dead(on))) {', 'if (l.spell) {'),
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
     'SurgeOn(p.k[i], 0.5f, false);', 'SurgeOn(p.k[i], 0.5f, true);'),
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
]


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
                                       'reaction': 'reaction_test.cpp', 'timer': 'timer_test.cpp'}[test]
        lines += [f'add_executable(m{i} "{source.as_posix()}")',
                  f'target_include_directories(m{i} PRIVATE "{folder.as_posix()}" "{inc.as_posix()}" "{js.as_posix()}")',
                  f'target_compile_options(m{i} PRIVATE /EHsc /utf-8 /bigobj)']
    (root / 'CMakeLists.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    run([CMAKE, '-S', root, '-B', root / 'build', '-G', 'Visual Studio 17 2022', '-A', 'x64'], log)
    run([CMAKE, '--build', root / 'build', '--config', 'Release', '--parallel', '8'], log)
    results = []
    for i, (name, header, test, *_rest) in enumerate(MUTANTS):
        exe = root / 'build' / 'Release' / f'm{i}.exe'
        tables = {'status': ['build/fix22-status-table.json', 'build/fix22-wiring.json'],
                  'self': ['build/fix23-self-table.json', 'build/fix23-wiring.json'],
                  'reaction': ['build/fix24-body-table.json', 'build/fix24-wiring.json'],
                  'timer': ['build/fix25-timer-table.json', 'build/fix25-wiring.json']}.get(test, [])
        args = [exe] + [ROOT / t for t in tables]
        r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf8', errors='replace')
        log.write(f'$ mutant {i} ({name}): exit {r.returncode}\n{r.stdout}\n')
        if r.returncode == 0:
            raise RuntimeError(f'NATIVE MUTANT survived: {name} ({header}) -- the {test} test does not see it')
        results.append(dict(name=name, header=header, test=test, exit=r.returncode, first_line=r.stdout.strip().splitlines()[-1][:200]))
    return results


def main():
    n.check_deps()
    n.generate_header(b)
    cases = n.fixture(b)
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
    assert n.inputs() == before, 'Sources changed during compile; rebuild'
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
    }, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    by = {}
    for m in mutants:
        by[m['header']] = by.get(m['header'], 0) + 1
    print(f'NATIVE MUTANTS ok: {len(mutants)}/{len(mutants)} source mutations make the tests fail '
          f'({", ".join(f"{h} {k}" for h, k in by.items())})')
    print(f'Native build ok: cl {cl_version}, cmake {cmake_version}, SDK {sdk}; ctest {summary[3]} test(s), 0 failed; receipt written.')


if __name__ == '__main__':
    main()

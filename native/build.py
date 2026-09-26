"""Pinned, offline MSVC build of ElementsSpellblade.dll and its tests; never deploys to the game.

The receipt (native/out/build-receipt.json) records what was actually used, read back from the
build itself: CMake version, the compiler CMake detected, the Windows SDK, and the CTest result.
"""
from pathlib import Path
import sys, subprocess, json, re
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
     'spell::kRestoreStamina, spell::kBleedTick }) {', 'spell::kRestoreStamina }) {'),
]


def run_mutants(log):
    """Builds one test binary per mutant (a separate CMake tree under native/out/mutants) and requires each to fail."""
    root = OUT / 'mutants'
    lines = ['cmake_minimum_required(VERSION 3.24)', 'project(ESSBMutants LANGUAGES CXX)', 'set(CMAKE_CXX_STANDARD 23)',
             'set(CMAKE_CXX_STANDARD_REQUIRED ON)', 'set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")']
    inc = n.NATIVE / 'include'
    js = n.NATIVE / 'deps/json/single_include'
    for i, (name, header, test, old, new) in enumerate(MUTANTS):
        text = (inc / header).read_text(encoding='utf-8')
        assert text.count(old) == 1, ('mutant text not found exactly once', name)
        folder = root / f'm{i}'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / header).write_text(text.replace(old, new), encoding='utf-8', newline='\n')
        source = n.NATIVE / 'tests' / ('status_test.cpp' if test == 'status' else 'engine_test.cpp')
        lines += [f'add_executable(m{i} "{source.as_posix()}")',
                  f'target_include_directories(m{i} PRIVATE "{folder.as_posix()}" "{inc.as_posix()}" "{js.as_posix()}")',
                  f'target_compile_options(m{i} PRIVATE /EHsc /utf-8)']
    (root / 'CMakeLists.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    run([CMAKE, '-S', root, '-B', root / 'build', '-G', 'Visual Studio 17 2022', '-A', 'x64'], log)
    run([CMAKE, '--build', root / 'build', '--config', 'Release', '--parallel', '8'], log)
    results = []
    for i, (name, header, test, *_rest) in enumerate(MUTANTS):
        exe = root / 'build' / 'Release' / f'm{i}.exe'
        args = [exe] + ([ROOT / 'build/fix22-status-table.json', ROOT / 'build/fix22-wiring.json'] if test == 'status' else [])
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
    by = {h: sum(1 for m in mutants if m['header'] == h) for h in ('Status.h', 'StatusEngine.h')}
    print(f'NATIVE MUTANTS ok: {len(mutants)}/{len(mutants)} source mutations make the tests fail '
          f'(Status.h {by["Status.h"]}, StatusEngine.h {by["StatusEngine.h"]})')
    print(f'Native build ok: cl {cl_version}, cmake {cmake_version}, SDK {sdk}; ctest {summary[3]} test(s), 0 failed; receipt written.')


if __name__ == '__main__':
    main()

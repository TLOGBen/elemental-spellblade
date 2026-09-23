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
LOG = ROOT / 'build/fix19-msvc.log'


def run(cmd, log):
    print(' '.join(map(str, cmd)), flush=True)
    log.write(f'$ {" ".join(map(str, cmd))}\n')
    log.flush()
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf8', errors='replace')
    log.write(result.stdout)
    log.flush()
    if result.returncode:
        raise RuntimeError(f'Native build step failed ({result.returncode}); see build/fix19-msvc.log')
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
        'truth_table_rows': cases,
    }, indent=2) + '\n', encoding='utf8')
    print(f'Native build ok: cl {cl_version}, cmake {cmake_version}, SDK {sdk}; ctest {summary[3]} test(s), 0 failed; receipt written.')


if __name__ == '__main__':
    main()

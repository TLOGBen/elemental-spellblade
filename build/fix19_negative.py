"""Exercise missing/stale native build gates and prove release is untouched."""
from pathlib import Path
import hashlib, json, subprocess, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'build')]
import build_v03 as b
import fix19_native as n

def package_hashes():
    return {p.relative_to(ROOT).as_posix(): n.sha(p)
            for p in (ROOT / 'package/Elements Spellblade').rglob('*') if p.is_file()}

def rejected(label, marker):
    result = subprocess.run([sys.executable, '-B', 'build_v03.py'], cwd=ROOT,
                            capture_output=True, text=True, encoding='utf8', errors='replace')
    output = result.stdout + result.stderr
    (ROOT / f'build/fix19-negative-{label}.log').write_text(output, encoding='utf8')
    assert result.returncode != 0 and marker in output, (label, result.returncode, output)
    assert package_hashes() == baseline, f'{label} changed release files'
    return {'exit_code': result.returncode, 'expected_error': marker, 'package_unchanged': True}

n.require_fresh(b)
baseline = package_hashes()
dll = ROOT / 'native/out/Release/ElementsSpellblade.dll'
hold = dll.with_suffix('.dll.fix19-negative-hold')
assert not hold.exists()
assert dll.resolve().is_relative_to((ROOT / 'native').resolve())
assert hold.resolve().is_relative_to((ROOT / 'native').resolve())
report = {}
try:
    dll.rename(hold)
    report['missing'] = rejected('missing', 'NATIVE DLL missing')
finally:
    if hold.exists():
        hold.rename(dll)

source = ROOT / 'native/include/Selection.h'
original = source.read_bytes()
try:
    source.write_bytes(original + b'\n// deliberate stale-source gate test\n')
    report['stale'] = rejected('stale', 'NATIVE DLL stale')
finally:
    source.write_bytes(original)
n.require_fresh(b)
assert package_hashes() == baseline
report['restored_fresh'] = True
report['package_files'] = len(baseline)
(ROOT / 'build/fix19-negative.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('NATIVE NEGATIVE ok: missing/stale rejected before package writes; source and DLL restored; fresh receipt valid')

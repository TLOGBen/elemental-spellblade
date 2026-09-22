"""Run python build_v03.py using round18b isolation inside the round18c write set.

The inherited builder also reads MO2 FX plugins and PO3 evidence. Those reads
require explicit authorization beyond the initial round18c read scope.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
WORK = Path(__file__).resolve().parents[1]
VALIDATION = WORK/'build/fix18-probe-package/round18c-validation'


def install():
    import runpy
    # Reuse the already audited 18b byte-hash / decoded-PEX checker unchanged.
    # Only its staging root changes to this round's authorized write subtree.
    original = (WORK/'build/fix18b_isolated.py').read_text(encoding='utf8')
    old = '.codex/pre-fix18b-snapshot'
    assert original.count(old) == 2
    code = original.replace(old, 'build/fix18-probe-package/round18c-validation')
    namespace = {'__name__': 'fix18c_isolated', '__file__': str(WORK/'build/fix18b_isolated.py')}
    exec(compile(code, namespace['__file__'], 'exec'), namespace)

    # Bound source reads as well as writes; compiler execution is explicitly allowed.
    extra_reads = os.environ.get('ESSB18C_ALLOW_BUILD_INPUTS') == '1'
    data = WORK.parents[1]/'SkyrimSE/Data'
    mods = WORK.parents[1]/'MO2/mods'
    import fx_extract
    inputs = {mods/spec for spec in fx_extract.SOURCES}
    inputs.update(mods/"powerofthree's Papyrus Extender"/name for name in
                  ('Source/scripts/PO3_Events_Alias.psc', 'SKSE/Plugins/po3_PapyrusExtender.pdb'))
    python_roots = {Path(sys.base_prefix).resolve(), Path(sys.prefix).resolve()}
    def audit(event, args):
        if event.startswith('socket.'): raise PermissionError('Round18c: network forbidden')
        if event != 'open' or not isinstance(args[0], (str, bytes, os.PathLike)): return
        path = Path(os.fsdecode(args[0])).resolve()
        mode, flags = args[1], args[2]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing:
            if not path.is_relative_to(VALIDATION) and not path.is_relative_to(WORK/'build/fix18-probe-package'):
                raise PermissionError('Round18c write outside isolation: '+str(path))
        elif not (path.is_relative_to(WORK) or
                  (path.parent == data and path.suffix.lower() == '.esm') or
                  any(path.is_relative_to(root) for root in python_roots) or
                  (extra_reads and path in inputs)):
            raise PermissionError('Round18c read requires scope extension: '+str(path))
    sys.addaudithook(audit)
    namespace['install'](str(WORK))


def main():
    import hashlib
    release = WORK/'package/Elements Spellblade'
    baseline = json.loads((VALIDATION/'release-before.json').read_text(encoding='utf8'))
    actual = {p.relative_to(release).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(release.rglob('*')) if p.is_file()}
    assert actual == baseline
    (VALIDATION/'release-sha256.json').write_text(json.dumps(baseline, indent=2), encoding='utf8')
    if not (VALIDATION/'package/Elements Spellblade').exists():
        shutil.copytree(release, VALIDATION/'package/Elements Spellblade')
    bootstrap = VALIDATION/'bootstrap'
    bootstrap.mkdir(exist_ok=True)
    hook = ('import runpy,os,traceback\ntry:\n    runpy.run_path(' +
            repr(str(Path(__file__).resolve())) + ')["install"]()\n'
            'except BaseException:\n    traceback.print_exc()\n    os._exit(1)\n')
    (bootstrap/'sitecustomize.py').write_text(hook, encoding='utf8')
    env = os.environ.copy()
    env.update(PYTHONPATH=str(bootstrap)+os.pathsep+str(WORK),
               PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    print('Running python build_v03.py; writes isolated to round18c-validation', flush=True)
    result = subprocess.run([sys.executable, 'build_v03.py'], cwd=WORK, env=env)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()

"""Execute python build_v03.py in a write-isolated full build; never deploy."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
WORK = Path(__file__).resolve().parents[1]
STAGE = WORK/'build/round18f'


def install():
    # Redirect the unchanged release recipe, including its generated source,
    # into build/. Native compiler input/output/cwd are redirected as well.
    runpy.run_path(str(WORK/'build/fix18f_isolated.py'))['install'](str(WORK))
    allowed = (WORK/'build', WORK/'package/Elements Spellblade')
    def audit(event, args):
        if event.startswith('socket.'):
            raise PermissionError('Round18f: network forbidden')
        if event != 'open' or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        mode, flags = args[1:3]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing:
            path = Path(os.fsdecode(args[0])).absolute()
            if not any(path.is_relative_to(root) for root in allowed):
                raise PermissionError('Round18f: write outside granted output trees: '+str(path))
    sys.addaudithook(audit)


def main():
    deployed = WORK.parents[1]/'MO2/mods/Elements Spellblade'
    baseline = json.loads((STAGE/'baseline.json').read_text(encoding='utf8'))
    digest = runpy.run_path(str(WORK/'build/fix18f_isolated.py'))['digest_tree']
    assert digest(deployed) == baseline['deployed']
    assert digest(WORK/'package/Elements Spellblade') in (baseline['release'], baseline['deployed'])
    (STAGE/'release-sha256.json').write_text(json.dumps(baseline['deployed'], indent=2), encoding='utf8')
    shutil.copytree(deployed, STAGE/'package/Elements Spellblade', dirs_exist_ok=True)
    bootstrap = STAGE/'bootstrap'
    bootstrap.mkdir(exist_ok=True)
    hook = ('import runpy,os,traceback\ntry:\n    runpy.run_path(' + repr(str(Path(__file__).resolve())) + ')["install"]()\n'
            'except BaseException:\n    traceback.print_exc()\n    os._exit(1)\n')
    (bootstrap/'sitecustomize.py').write_text(hook, encoding='utf8')
    env = os.environ.copy()
    env.update(PYTHONPATH=str(bootstrap)+os.pathsep+str(WORK), PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    print('Running python build_v03.py; full build, staged writes, deployed package read-only', flush=True)
    result = subprocess.run([sys.executable, 'build_v03.py'], cwd=WORK, env=env)
    assert result.returncode == 0, f'full build exit={result.returncode}'
    assert digest(deployed) == baseline['deployed'] == digest(WORK/'package/Elements Spellblade')
    print('DEPLOYED-HASHES ok: all 56 release files byte-identical; deployed tree unchanged')


if __name__ == '__main__':
    main()

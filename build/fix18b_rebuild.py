"""Launch the unchanged full builder inside the round18b write-isolation hook."""
from pathlib import Path
import json,os,subprocess,sys
sys.dont_write_bytecode=True
work=Path(__file__).resolve().parents[1]
bootstrap=work/'.codex/pre-fix18b-snapshot/bootstrap'
bootstrap.mkdir(exist_ok=True)
hook="import runpy,os,traceback\ntry:\n    runpy.run_path("+repr(str(work/'build/fix18b_isolated.py'))+")[\"install\"]("+repr(str(work))+ ")\nexcept BaseException:\n    traceback.print_exc()\n    os._exit(1)\n"
(bootstrap/'sitecustomize.py').write_text(hook,encoding='utf8')
env=os.environ.copy()
env['PYTHONPATH']=str(bootstrap)
env['PYTHONDONTWRITEBYTECODE']='1'
env['PYTHONUNBUFFERED']='1'
command=[sys.executable,'build_v03.py']
print('Running python build_v03.py with snapshot-only writes',flush=True)
result=subprocess.run(command,cwd=work,env=env)
raise SystemExit(result.returncode)

import sys,json,runpy
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'build')]
import build_v03 as b
records,meta=b.read_plugin(b.OUT/b.PLUGIN)
written=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf8'))
b.validate_fix4(records,written)
b.validate_mcm(records,written)
for i in range(6,17):
 print('RUN',i,flush=True)
 runpy.run_path(str(ROOT/f'build/fix{i}_verify.py'))['run']()

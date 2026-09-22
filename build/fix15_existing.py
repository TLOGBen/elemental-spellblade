import runpy,sys
from pathlib import Path
sys.dont_write_bytecode=True
r=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(r),str(r/'build')]
for n in range(6,15):
 print('CHECK',n,flush=True)
 runpy.run_path(str(r/f'build/fix{n}_verify.py'))['run']()

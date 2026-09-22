import sys,json
from pathlib import Path
sys.dont_write_bytecode=True
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'build')]
import build_v03 as b
rr,_=b.read_plugin(b.OUT/b.PLUGIN);written=json.loads((b.WORK/'build/v03-formids.json').read_text(encoding='utf8'))
b.state_schema.verify(rr,written['records'],b)
b.validate_fix3(rr,written,json.loads((b.WORK/'build/fx-bindings.json').read_text(encoding='utf8')))
b.validate_fix4(rr,written)
b.validate_mcm(rr,written)
for i in range(6,17):
 print('RUN',i,flush=True)
 __import__('fix'+str(i)+'_verify').run()

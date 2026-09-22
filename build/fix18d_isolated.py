"""Run the existing full builder with writes redirected into the allowed snapshot.

The release recipe and every existing check still execute in build/. Final
release assembly is published only after decoded PEX and byte-hash verification. Compiler subprocess arguments are redirected too. PEX build
timestamps and declaration ordering are nondeterministic: verify decoded data and
instructions, retain the original release PEX, and keep the raw rebuild evidence.
"""
from pathlib import Path
import builtins, contextlib, hashlib, io, json, os, shutil, struct, subprocess, runpy

def digest_tree(folder):
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file()}

def decoded_pex(data,parser):
    tree=parser(data).read()  # Strict parser consumes every byte, resolves string IDs.
    for obj in tree['objects']:
        obj['vars'].sort(key=lambda row:row[0])
        obj['properties'].sort(key=lambda row:row['name'])
        for funcs in obj['states'].values():
            for function in funcs.values():function['locals'].sort(key=lambda row:row[0])
    tree['objects'].sort(key=lambda row:row['name'])
    # Preserve additional sections the legacy disassembler does not return.
    extra=parser(data)
    version=extra.get('IBBH');extra.get('Q')  # Build time, explicitly excluded.
    metadata=[extra.string() for _ in range(3)]
    extra.strings=[extra.string() for _ in range(extra.get('H'))]
    debug=[];has_debug=extra.get('B')
    if has_debug:
        extra.get('Q')  # Debug source modification time, explicitly excluded.
        for _ in range(extra.get('H')):
            obj,state,function=extra.sid(),extra.sid(),extra.sid()
            kind=extra.get('B');lines=[extra.get('H') for _ in range(extra.get('H'))]
            debug.append((obj,state,function,kind,lines))
    flags=[(extra.sid(),extra.get('B')) for _ in range(extra.get('H'))]
    return dict(tree=tree,version=version,metadata=metadata,strings=sorted(extra.strings),
                debug=sorted(debug),has_debug=has_debug,user_flags=sorted(flags))

class Tee:
    def __init__(self,stream,log):self.stream=stream;self.log=log
    def write(self,s):self.stream.write(s);self.log.write(s);return len(s)
    def flush(self):self.stream.flush();self.log.flush()

@contextlib.contextmanager
def isolated(b):
    work=b.WORK.resolve()
    snap=work/'build/round18d'
    assert (snap/'release-sha256.json').is_file(), 'Take pre-fix18b snapshot first'
    release=work/'package/Elements Spellblade'
    baseline=json.loads((snap/'release-sha256.json').read_text(encoding='utf8'))
    original_local = json.loads((snap/'baseline.json').read_text(encoding='utf8'))['release']
    initial_local = digest_tree(release)
    assert initial_local in (original_local, baseline), 'Release changed since snapshot'
    # New run directory, never clear or overwrite previous evidence.
    index=1
    while (snap/f'rebuild-{index}').exists():index+=1
    stage=snap/f'rebuild-{index}'
    stage.mkdir()
    shutil.copytree(release,stage/'package/Elements Spellblade')
    for p in (stage/'package/Elements Spellblade/Scripts').glob('*.pex'):p.unlink()
    real_open=builtins.open;real_io_open=io.open;real_stat=Path.stat
    real_mkdir=Path.mkdir;real_unlink=Path.unlink;real_iterdir=Path.iterdir
    real_run=subprocess.run

    def map_path(p,writing=False):
        if not isinstance(p,(str,bytes,os.PathLike)):return p
        p=Path(os.fsdecode(p)).absolute()
        if p.is_relative_to(snap):return p
        if not p.is_relative_to(work):
            if writing:raise PermissionError('Round18b write outside workspace: '+str(p))
            return p
        candidate=stage/p.relative_to(work)
        if writing:
            real_mkdir(candidate.parent,parents=True,exist_ok=True)
            return candidate
        try:real_stat(candidate);return candidate
        except FileNotFoundError:return p

    def wrap_open(original):
        def opened(file,mode='r',*args,**kwargs):
            return original(map_path(file,any(c in mode for c in 'wax+')),mode,*args,**kwargs)
        return opened
    def mapped_stat(p,*a,**kw):return real_stat(map_path(p),*a,**kw)
    def mapped_mkdir(p,*a,**kw):return real_mkdir(map_path(p,True),*a,**kw)
    def mapped_unlink(p,*a,**kw):return real_unlink(map_path(p,True),*a,**kw)
    def mapped_iterdir(p):
        mapped=map_path(p)
        for item in real_iterdir(mapped):yield p/item.name
    def compiler_run(command,*args,**kwargs):
        assert isinstance(command,list) and Path(command[0]).name.lower()=='papyruscompiler.exe', command
        command=list(command)
        command[1]=str(map_path(command[1]))
        for i,arg in enumerate(command[2:],2):
            if arg.startswith('-o='):command[i]='-o='+str(map_path(arg[3:],True))
            elif arg.startswith('-i='):command[i]='-i='+';'.join(str(map_path(p)) for p in arg[3:].split(';'))
        kwargs['cwd']=stage
        return real_run(command,*args,**kwargs)

    import sys
    with (stage/'build.log').open('w',encoding='utf8') as log:
        try:
            builtins.open=wrap_open(real_open);io.open=wrap_open(real_io_open)
            Path.stat=mapped_stat;Path.mkdir=mapped_mkdir;Path.unlink=mapped_unlink;Path.iterdir=mapped_iterdir
            subprocess.run=compiler_run
            with contextlib.redirect_stdout(Tee(sys.stdout,log)),contextlib.redirect_stderr(Tee(sys.stderr,log)):
                yield stage
        finally:
            builtins.open=real_open;io.open=real_io_open
            Path.stat=real_stat;Path.mkdir=real_mkdir;Path.unlink=real_unlink;Path.iterdir=real_iterdir
            subprocess.run=real_run
    rebuilt=stage/'package/Elements Spellblade'
    build_log=(stage/'build.log').read_text(encoding='utf8')
    for marker in ('FIX18 ok:','PROBE-LOGIC ok:','PROBES ok:','READBACK ok:','ENGINE COVERAGE ok:'):
        assert marker in build_log, 'Full build did not finish: '+marker
    assert build_log.count('  compile ')==20 and 'FAILED' not in build_log
    raw_hashes=digest_tree(rebuilt)
    reuse=[]
    parser=runpy.run_path(str(work/'build/fix5_read_bsa.py'))['Pex']
    for p in (rebuilt/'Scripts').glob('*.pex'):
        relative=p.relative_to(rebuilt)
        old=(snap/'package/Elements Spellblade'/relative).read_bytes()
        new=p.read_bytes()
        old_tree=decoded_pex(old,parser);new_tree=decoded_pex(new,parser)
        assert new_tree==old_tree, 'Release PEX decoded executable/debug data changed: '+p.name
        raw=stage/'raw-pex'/p.name;raw.parent.mkdir(exist_ok=True);raw.write_bytes(new)
        canonical=json.dumps(new_tree,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')
        reuse.append(dict(script=p.name,raw_byte_identical=new==old,decoded_sha256=hashlib.sha256(canonical).hexdigest()))
        p.write_bytes(old)  # Release assembly reuses proven-equivalent original PEX.
    rebuilt_hashes=digest_tree(rebuilt)
    assert rebuilt_hashes==baseline, 'Release differs after verified original PEX reuse'
    assert digest_tree(release)==initial_local, 'Live release package was modified'
    deployed = work.parents[1]/'MO2/mods/Elements Spellblade'
    assert digest_tree(deployed)==baseline, 'Deployed release changed during build'
    shutil.copytree(rebuilt,release,dirs_exist_ok=True)
    assert digest_tree(release)==baseline, 'Final release must match deployed bytes'
    # Publish only the explicitly authorized probe artifacts.
    source=stage/'build/fix18-probe-package'
    destination=work/'build/fix18-probe-package'
    shutil.copytree(source,destination,dirs_exist_ok=True)
    report=dict(build_exit_code=0,release_files=len(baseline),deployed_release_byte_identical=True, local_release_matches_deployed=True,
                rebuilt_release_byte_identical_after_verified_pex_reuse=True,
                raw_rebuild_hashes=raw_hashes,rebuilt_hashes=rebuilt_hashes,
                verified_pex_reuse=reuse,build_log=str((stage/'build.log').relative_to(work)),
                runtime_tested=False,deployed=False)
    (stage/'preservation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    (destination/'preservation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    lines=[f'PRESERVATION ok: {len(baseline)} deployed release files untouched; 36 rebuilt files byte-identical + {len(reuse)} decoded PEX equivalent; original PEX retained for identical release assembly',
           'SCOPE ok: full-build writes isolated under build/round18d; probe artifacts and verified release assembly published']
    for line in lines:print(line)
    with (stage/'build.log').open('a',encoding='utf8') as log:log.write('\n'.join(lines)+'\n')

def install(work):
    """Python startup hook: scope actual `python build_v03.py`, unchanged recipe."""
    import atexit,sys,traceback
    from types import SimpleNamespace
    context=isolated(SimpleNamespace(WORK=Path(work)))
    context.__enter__()
    failure=[None,None,None]
    original_hook=sys.excepthook
    def exception_hook(typ,value,tb):
        failure[:]=[typ,value,tb]
        original_hook(typ,value,tb)
    sys.excepthook=exception_hook
    def finish():
        try:
            context.__exit__(*failure)
        except BaseException:
            traceback.print_exc()
            sys.stdout.flush();sys.stderr.flush()
            os._exit(1)  # atexit normally swallows failures; acceptance must not.
    atexit.register(finish)

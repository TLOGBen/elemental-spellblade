"""Offline read-only MO2 record / distribution / Papyrus audit. Outputs only build/."""
import sys, os, re, json, struct, pickle, hashlib, collections
from pathlib import Path
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(W))
from tes import read_plugin, u32, text
ROOT=W.parents[1]; MODS=ROOT/'MO2/mods'; DATA=ROOT/'SkyrimSE/Data'; PROFILE=ROOT/'MO2/profiles/normal'
def dump(name,obj): (W/'build'/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def environment():
    enabled=[s[1:] for s in (PROFILE/'modlist.txt').read_text(encoding='utf-8-sig').splitlines() if s.startswith('+')]
    roots=[DATA]+[MODS/s for s in reversed(enabled)]
    paths={}
    for root in roots:
        if root.is_dir():
            for p in root.iterdir():
                if p.suffix.lower() in ('.esp','.esm','.esl'): paths[p.name.lower()]=p
    active={s[1:].lower() for s in (PROFILE/'plugins.txt').read_text(encoding='utf-8-sig').splitlines() if s.startswith('*')}
    active.update(['skyrim.esm','update.esm','dawnguard.esm','hearthfires.esm','dragonborn.esm'])
    order=[s for s in (PROFILE/'loadorder.txt').read_text(encoding='utf-8-sig').splitlines() if s.lower() in active]
    return enabled,roots,paths,order
def entries(r):
    out=[];cur=None;tab=None;top=[]
    for k,v in r.ss:
        if k=='PRKE':
            cur={'kind':v[0],'rank':v[1],'priority':v[2],'conditions':[]};out.append(cur);tab=None
        elif cur is not None:
            if k=='DATA':cur['data']=list(v)
            elif k=='PRKC':tab=v[0]
            elif k=='CTDA':cur['conditions'].append((tab,v.hex()))
            elif k in ('EPFT','EPFD'):cur[k]=v.hex()
            elif k=='PRKF':cur=None
        elif k=='CTDA':top.append((None,v.hex()))
    return top,[e for e in out if e['kind']==2 and e.get('data',[None])[0]==51]
def collect():
    enabled,roots,paths,order=environment(); records={};history=collections.defaultdict(list);meta={};errors=[]
    types={'PERK','SPEL','MGEF','ENCH','NPC_','RACE','QUST','AVIF','FLST','WEAP','ARMO','BOOK','KYWD','GLOB','SHOU','SCRL','INGR','ALCH'}
    for i,name in enumerate(order):
        if name.lower() not in paths:errors.append('missing plugin: '+name);continue
        try: rr,mm=read_plugin(paths[name.lower()],types)
        except ValueError as exc:
            errors.append(str(exc)); print(str(exc),flush=True); continue
        meta[name]=mm
        for r in rr:
            if r.sig=='PERK':history[r.key].append({'source':r.source,'edid':r.edid,'entries':entries(r)[1],'deleted':bool(r.flags&32)})
            if r.flags&32:records.pop(r.key,None)
            else:records[r.key]=r
        if i%250==0:print('records',i,len(order),len(records),flush=True)
    with (W/'build/entry51-records.pickle').open('wb') as f:pickle.dump((records,dict(history),meta),f)
    inventory=[];loose={};configs=[];sourcehits=[]
    enabledset=set(enabled)
    for parent in [DATA,MODS]:
        for base,dirs,files in os.walk(parent):
            for name in files:
                suffix=Path(name).suffix.lower()
                if suffix not in ('.ini','.json','.toml','.txt','.pex','.psc','.bsa','.strings','.dlstrings','.ilstrings'):continue
                p=Path(base)/name
                mod=p.relative_to(MODS).parts[0] if p.is_relative_to(MODS) else '<Data>'
                active=mod=='<Data>' or mod in enabledset
                row={'path':str(p),'mod':mod,'enabled':active,'suffix':suffix}
                inventory.append(row)
                if suffix=='.pex' and active:
                    rank=0 if mod=='<Data>' else len(enabled)-enabled.index(mod)
                    if name.lower() not in loose or rank>loose[name.lower()][0]:loose[name.lower()]=(rank,str(p))
                if suffix=='.psc':
                    raw=p.read_bytes()
                    if b'addperk' in raw.lower():
                        s=raw.decode('utf-8-sig',errors='replace');row=dict(row,text=s);sourcehits.append(row)
                elif suffix in ('.ini','.json','.toml','.txt'):
                    # All distributor files, CSF trees and other explicit perk references.
                    try:
                        if p.stat().st_size>8_000_000:continue
                        raw=p.read_bytes()
                    except OSError:continue
                    if any(x in name.lower() for x in ('_distr','_kid','customskill')) or b'perk' in raw.lower():
                        configs.append(dict(row,text=raw.decode('utf-8-sig',errors='replace')))
    dump('entry51-inventory.json',inventory);dump('entry51-configs.json',configs);dump('entry51-addperk-sources.json',sourcehits)
    dump('entry51-inputs.json',{'order':order,'plugins':meta,'enabled_mods':enabled,'errors':errors,'loose_scripts':loose,'profile_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [PROFILE/'plugins.txt',PROFILE/'loadorder.txt',PROFILE/'modlist.txt']}})
    print('collected',len(records),'records',len(history),'perks',len(inventory),'files',len(configs),'configs',len(sourcehits),'AddPerk sources',flush=True)
if __name__=='__main__':collect()

"""Round 11: execute actual Papyrus hit/proc/mark bodies, with explicit native mocks.
No Skyrim scheduling simulation or claim of live runtime verification.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import ast, collections, hashlib, json, re, struct, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'build'), str(ROOT)]
import papyrus_harness as h
from fix10_verify import controller, Actor as BaseActor, Spell as BaseSpell, Glob

class Form:
    record_type = 0
    def GetType(self): return self.record_type
    def GetFormID(self): return 0x123456
class Weapon(Form):
    record_type = 41
    def __init__(self, kind): self.kind = kind
    def GetWeaponType(self): return self.kind
class Ammo(Form): record_type = 42
class Projectile(Form): record_type = 50
class Explosion(Form): record_type = 87
class Spell(BaseSpell, Form): record_type = 22
class Actor(BaseActor):
    def __init__(self, right=None, left=None, magic=False):
        super().__init__(1000); self.right=right; self.left=left; self.magic=magic
    def GetEquippedWeapon(self, left=False): return self.left if left else self.right
    def GetEquippedItemType(self, hand):
        w=self.left if hand==0 else self.right
        return w.kind if w else (9 if self.magic else 0)

def native_cast(v,t):
    types={'Weapon':Weapon,'Ammo':Ammo,'Projectile':Projectile,'Spell':BaseSpell,'Actor':BaseActor}
    if t in types: return v if isinstance(v,types[t]) else None
    return h.cast(v,t)

def add(a,b):
    if isinstance(a,str) or isinstance(b,str): return str(a)+str(b)
    return a+b
class PapyrusAdd(ast.NodeTransformer):
    def visit_BinOp(self,node):
        self.generic_visit(node)
        if isinstance(node.op,ast.Add):
            return ast.copy_location(ast.Call(func=ast.Name(id='padd',ctx=ast.Load()),args=[node.left,node.right],keywords=[]),node)
        return node
class HitScript(h.Script):
    def evaluate(self,text,scope):
        tree=ast.fix_missing_locations(PapyrusAdd().visit(ast.parse(h.expression(text),mode='eval')))
        return eval(compile(tree,'<actual-papyrus>','eval'),{'__builtins__':{}},scope)

def native_generation(c):
    # Round 18-19 (baked native base, ApplyBakedProc) and round 20 (DLL computes the magnitude, NativeProcUnit)
    # both deliver the element proc outside Papyrus; the script only records attribution and adds differences.
    return 'ApplyBakedProc' in c.functions or 'NativeProcUnit' in c.functions

def make(folder=ROOT/'src', right=None, left=None, magic=False):
    c,_=controller(folder); c.__class__=HitScript
    p=Actor(right,left,magic); t=Actor(); calls=collections.Counter(); logs=[]; clock=[10.0]
    c.fields.update(PlayerRef=p,Enabled=Glob(1),DebugLevel=Glob(3),CachedDebugLevel=3,CurrentElement=Glob(10),Sync=Glob(0),
                    MarkSpells=h.Array([Spell() for _ in range(11)]),Trees=NS(OnValidHitXP=lambda *a:calls.update(['xp']),AwardInternal=lambda *a:calls.update(['xp']),OnOpenXP=lambda *a:calls.update(['open-xp'])))
    c.env.update(cast=native_cast,padd=add,__execute_logs__=True,Math=NS(LogicalAnd=lambda a,b:a&b),
                 Utility=NS(GetCurrentRealTime=lambda:clock[0]),Debug=NS(Trace=logs.append))
    c.env['ESSBNodes']=NS(TreeOf=lambda e:e-1,Br=lambda *a:False,HasExtreme=lambda *a:False,
        OpenStrikeMult=lambda *a:1,HasDualMark=lambda *a:False,MarkDurationBonus=lambda *a:0)
    c.env['ESSBElem']=NS(OpenStrikeMult=lambda *a:1,MarkDurationBonus=lambda *a:0)
    c.env['ESSBReactions']=NS(RollBase=lambda *a:10,Open=lambda *a:calls.update(['reaction']))
    c.overrides.update(AfterOpen=lambda *a:None,HitStacks=lambda *a:calls.update(['stacks']),
        ElementHitHook=lambda *a:None,AddSync=lambda *a:calls.update(['sync']),ScheduleTick=lambda *a:None,ScheduleTickInternal=lambda *a:None,
        CooldownSeconds=lambda x:x,DurationInt=lambda x:x)
    if native_generation(c):
        p.IsSneaking=lambda:False
        c.env['PO3_SKSEFunctions']=NS(IsPowerAttacking=lambda a:False)
        def note(*args):
            calls.update(['native-base-attribution'])
            c.overrides.pop('NoteDamageElement')
            try:return c.NoteDamageElement(*args)
            finally:c.overrides['NoteDamageElement']=note
        c.overrides['NoteDamageElement']=note
    return c,p,t,calls,logs,clock

def hit_case(name,source,projectile,equipped,flags,accept,power=False,left=None,magic=False,folder=ROOT/'src'):
    c,p,t,calls,logs,_=make(folder,equipped,left,magic)
    c.OnWeaponHit(t,source,projectile,flags)
    damage=[spell for spell in t.hits if spell in c.HitNormalSpells or spell in c.HitPowerSpells]
    if native_generation(c):
        assert calls['native-base-attribution']==int(accept) and not damage,(name,calls,damage)
    else:assert len(damage)==int(accept),(name,'proc',len(damage),logs)
    assert calls['reaction']==int(accept) and calls['xp']==int(accept),(name,calls)
    assert calls['sync']==int(accept)
    slot=c.FindSlot(t)
    assert (slot>=0 and c.RegElem[slot]==10)==accept,(name,'mark',slot)
    if accept:
        if not native_generation(c):
            assert damage[0].mag==(15 if power else 10),(name,'multiplier',damage[0].mag)
        # Round18 native magnitude and selection are independently read back in HITPROC.
        assert c.LastHitPower==power
        assert not any('[hit-reject]' in s for s in logs)
    else:
        assert len(logs)==1 and '[hit-reject][L3]' in logs[0],(name,logs)
        for field in ('reason=','sourceType=','sourceFormID=','weapon=','projectile=','flags=','rejectedMask='):
            assert field in logs[0],(name,field)
    return dict(name=name,accepted=accept,power=power,log=logs)

def outgoing():
    arrow=Projectile(); rows=[]
    for kind in range(7):
        for flags in (0,65536):
            rows.append(hit_case('melee-type-'+str(kind)+'-flags-'+str(flags),Weapon(kind),None,Weapon(kind),flags,True,bool(flags)))
    rows.append(hit_case('unarmed-none',None,None,None,0,True))
    for kind in (7,9):
        for label,source in [('weapon',Weapon(kind)),('ammo',Ammo()),('none',None),('projectile',arrow)]:
            for flags in (0,2048,65536,67584):
                rows.append(hit_case(f'ranged-{kind}-{label}-{flags}',source,arrow,Weapon(kind),flags,True,bool(flags&2048)))
        rows.append(hit_case(f'ranged-{kind}-left-fallback',Ammo(),arrow,None,0,True,left=Weapon(kind)))
        # PO3 does not guarantee a Projectile on arrow hits (observed None in the live log), so a bow/crossbow
        # hit is accepted with or without one. Phenderix's equivalent handler ignores akProjectile entirely.
        rows.append(hit_case(f'ranged-{kind}-no-projectile',Weapon(kind),None,Weapon(kind),0,True))
        for flag in (1,2,16384,32768,1048576,1097731):
            rows.append(hit_case(f'ranged-{kind}-blocked-bash-explosion-{flag}',Ammo(),arrow,Weapon(kind),flag,False))
    for label,source,proj,eq,magic in [
        ('staff',Weapon(8),None,Weapon(8),False),('staff-projectile',Weapon(8),arrow,Weapon(8),False),
        ('spell',Spell(),None,None,False),('spell-projectile-while-bow',Spell(),arrow,Weapon(7),False),
        ('explosion-form',Explosion(),None,None,False),('explosion-form-while-bow',Explosion(),arrow,Weapon(7),False),
        ('unknown-form',Form(),None,None,False),('unknown-form-while-bow',Form(),arrow,Weapon(7),False),
        ('melee-duplicate-projectile',Weapon(1),arrow,Weapon(1),False),
        ('twohand-duplicate-projectile',Weapon(5),arrow,Weapon(5),False),
        ('ammo-no-projectile',Ammo(),None,Weapon(7),True),('ammo-equipped-melee',Ammo(),arrow,Weapon(1),False),
        ('none-projectile-no-weapon',None,arrow,None,False),('none-projectile-staff',None,arrow,Weapon(8),False),
        ('none-no-projectile-spell',None,None,None,True),('none-no-projectile-bow',None,None,Weapon(7),True),
        ('other-projectile-source',Projectile(),arrow,Weapon(7),False),('invalid-weapon-type',Weapon(10),None,None,False)]:
        rows.append(hit_case(label,source,proj,eq,0,False,magic=magic))
    for flag in (1,2,16384,32768,1048576):
        rows.append(hit_case(f'melee-blocked-bash-explosion-{flag}',Weapon(1),None,Weapon(1),flag,False))
    # One swing's primary hit plus projectile duplicate plus magic side-effect: exactly one proc/XP.
    for kind in (0,1,5):
        c,p,t,calls,logs,_=make(right=Weapon(kind)); w=Weapon(kind)
        for source,proj in [(w,None),(w,arrow),(Spell(),arrow)]: c.OnWeaponHit(t,source,proj,0)
        assert calls['xp']==1 and calls['reaction']==1 and calls['sync']==1
        assert (calls['native-base-attribution'] if native_generation(c) else len([s for s in t.hits if s in c.HitNormalSpells]))==1
    # No-form accepted shots follow the existing no-form path once; resolved weapon is forwarded.
    for kind in (7,9):
        c,p,t,calls,logs,_=make(right=Weapon(kind)); c.FormActive.v=0; received=[]
        c.overrides['OnNoFormHit']=lambda *a:received.append(a)
        c.OnWeaponHit(t,Ammo(),arrow,2048)
        assert received==[(t,p.right,True)] and calls['xp']==1 and not t.hits
    # Show the immutable pre-fix11 event fails the same ammo/None regression.
    negatives=[]
    for source in (Ammo(),None):
        c,p,t,calls,logs,_=make(ROOT/'.codex/pre-fix11-snapshot/src',Weapon(7))
        c.OnWeaponHit(t,source,arrow,0)
        assert not t.hits and not calls and not logs
        negatives.append(type(source).__name__)
    return rows,negatives

def incoming():
    rows=[]; arrow=Projectile()
    for kind in (7,9):
        for source in (Weapon(kind),Ammo(),None,arrow):
            c,p,t,calls,logs,_=make(); c.CurrentElement.v=4
            c.overrides.update(GetSelf=lambda *a:1,GetIceShield=lambda:1,GetWaterMirror=lambda:1,
                ConsumeRockArmor=lambda:calls.update(['rock']),ConsumeIceShield=lambda:calls.update(['ice']),
                ConsumeWaterMirror=lambda:calls.update(['water']),GetGuardWindLeft=lambda:0)
            g=HitScript(ROOT/'src/ESSBGuard.psc',dict(cast=native_cast,padd=add,ESSBNodes=c.env['ESSBNodes'],
                ESSBElem2=NS(OnEarthRetaliate=lambda *a:calls.update(['melee-retaliation']))))
            g.fields['Ctl']=c
            if 'NodeBits' in g.fields:
                g.fields.update(Ready=True,Enabled=Glob(1),DivineArmed=Glob(0),RockArmor=Glob(1),IceShield=Glob(1),WaterMirror=Glob(1),GuardWind=Glob(0),NodeBits=False)
                g.overrides['GetActorReference']=c.ThePlayer
            g.OnHitEx(Actor(Weapon(kind)),source,arrow,False,False,False,False)
            assert dict(calls)==dict(rock=1,ice=1,water=1),dict(calls)
            rows.append(f'{kind}/{type(source).__name__}: rock/ice/water once; no melee retaliation')
    return rows

def diagnostics():
    c,p,t,calls,logs,clock=make(right=Weapon(7)); a=Ammo(); arrow=Projectile()
    for state,reason in [('not-operational','not-operational'),('disabled','disabled'),('invalid-element','invalid-element'),('dead','invalid-actor')]:
        c,p,t,calls,logs,clock=make(right=Weapon(7))
        if state=='not-operational': c.fields['Ready']=False
        if state=='disabled': c.Enabled.v=0
        if state=='invalid-element': c.CurrentElement.v=0
        if state=='dead': t.hp=0
        c.OnWeaponHit(t,a,arrow,0)
        assert len(logs)==1 and 'reason='+reason in logs[0],(state,logs)
    c,p,t,calls,logs,clock=make(right=Weapon(7))
    for _ in range(4): c.LogRejectedHit('same',t,a,arrow,1,7)
    assert len(logs)==1
    clock[0]+=0.5; c.LogRejectedHit('same',t,a,arrow,1,7); assert len(logs)==2
    for i in range(30): c.LogRejectedHit(str(i),t,a,arrow,1,7)
    assert len(logs)==20 and c.LogDropped==12
    clock[0]+=1; c.LogRejectedHit('next',t,a,arrow,1,7)
    assert 'dropped=12' in logs[-2] and 'reason=next' in logs[-1]
    class NoProbe:
        def __getattr__(self,n): raise AssertionError('disabled logging probed '+n)
    for level in (0,1,2):
        c.DebugLevel.v=level; c.fields['CachedDebugLevel']=level; n=len(logs); c.LogRejectedHit('off',NoProbe(),NoProbe(),NoProbe(),1)
        assert len(logs)==n
    return 'every rejection reason/fields; level 0-2 no probing; 0.5s dedup; 20/s cap; dropped count'

def local_evidence():
    po3=ROOT.parents[1]/'MO2/mods'/"powerofthree's Papyrus Extender"
    vendor=(ROOT/'vendor/imports/PO3_Events_Alias.psc').read_bytes()
    shipped=(po3/'Source/scripts/PO3_Events_Alias.psc').read_bytes()
    assert vendor==shipped
    pdb=(po3/'SKSE/Plugins/po3_PapyrusExtender.pdb').read_bytes()
    start=pdb.index(b'kBlocked\0'); end=pdb.index(b'RE::HitData::Flag\0',start)
    block=pdb[start-10:end]
    flags={}
    for m in re.finditer(b'\x02\x15\x03\x00',block): # CodeView LF_ENUMERATE, public attr
        pos=m.end(); leaf=struct.unpack_from('<H',block,pos)[0]; pos+=2
        if leaf<0x8000: value=leaf
        elif leaf==0x8002: value=struct.unpack_from('<H',block,pos)[0];pos+=2
        elif leaf==0x8004: value=struct.unpack_from('<I',block,pos)[0];pos+=4
        else: continue
        name=block[pos:block.index(b'\0',pos)].decode('ascii')
        flags[name]=value
    expected=dict(kBlocked=1,kBlockWithWeapon=2,kSneakAttack=2048,kBash=16384,kTimedBash=32768,kPowerAttack=65536,kExplosion=1048576)
    assert all(flags[k]==v for k,v in expected.items()),flags
    assert sum(expected[k] for k in ('kBlocked','kBlockWithWeapon','kBash','kTimedBash','kExplosion'))==1097731
    assert 1097731 & (2048|65536|flags['kRicochet'])==0
    lines=(ROOT/'.codex/smoke3-essb-events.log').read_text(encoding='utf-8-sig').splitlines()
    boundary=next(i for i,l in enumerate(lines) if l.startswith('\t'))
    stream=[l for l in lines[:boundary] if '[ESSB]' in l]
    hits=[l for l in stream if '[hit]' in l.lower()]
    return dict(po3_alias_identical=True,pdb_sha256=hashlib.sha256(pdb).hexdigest(),hitdata_flags=flags,
        source_contract='Form only; shipped PSC lacks source assignment; Weapon/Ammo/None/same Projectile fallback; actual runtime source unproven',
        smoke_events=len(stream),smoke_hit_count=len(hits),weapons=dict(collections.Counter(re.search(r'weapon=(\d+)',l)[1] for l in hits)))

def run():
    rows,negatives=outgoing(); guard=incoming(); logging=diagnostics(); evidence=local_evidence()
    before=json.loads((ROOT/'.codex/pre-fix11-snapshot/v03-formids.json').read_text(encoding='utf8'))['records']
    after=json.loads((ROOT/'build/v03-formids.json').read_text(encoding='utf8'))['records']
    import state_schema
    assert all(state_schema.stable_identity(k,after.get(k),v) for k,v in before.items())
    assert after['ESSB_DebugLevel']['id']=='000811'
    state_schema.preflight()
    # Round 12 changes members and load handling. Schema/identity gate replaces round-11 no-change scope.
    assert json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']==json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']
    for old in (ROOT/'build/fix11-before').rglob('*'):
        if not old.is_file(): continue
        p=ROOT/old.relative_to(ROOT/'build/fix11-before');a=old.read_bytes();b=p.read_bytes()
        if p.name=='實作紀錄.md':
            prior=a
            a=(ROOT/'.codex/pre-fix18b-snapshot/實作紀錄.md').read_bytes()
            assert a.replace(b'\r\n',b'\n').startswith(prior.replace(b'\r\n',b'\n'))
        assert a.startswith(b'\xef\xbb\xbf')==b.startswith(b'\xef\xbb\xbf'),str(p)
        if a.count(b'\r\n')==a.count(b'\n'): assert b.count(b'\r\n')==b.count(b'\n'),str(p)
        if not a.count(b'\r\n'): assert not b.count(b'\r\n'),str(p)
        if p.name=='實作紀錄.md': assert b.startswith(a)
    for name,digest in json.loads((ROOT/'build/fix11-protected.json').read_text()).items():
        if name == 'state-schema.lock.json':
            state_schema.preflight()
            continue
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    src=(ROOT/'src/ESSBController.psc').read_text(encoding='utf8')
    old=(ROOT/'.codex/pre-fix11-snapshot/src/ESSBController.psc').read_text(encoding='utf8')
    for token in ('RegisterForWeaponHit(Self)','Utility.Wait','RegisterForUpdate('):
        assert src.count(token)==old.count(token),token
    assert 'Event OnProjectileHit(' not in src and 'Event OnHit(' not in src
    report=dict(outgoing=rows,pre_fix_reproductions=negatives,incoming=guard,diagnostics=logging,evidence=evidence,
        formids_unchanged=len(after),debug_id='000811',schema_version=4,runtime_tested=False,
        limitations=['Native form casts/equipment/event delivery mocked; no live game or scheduler test.',
                     'Fallback uses impact-time equipment; an in-flight shot after unequipping its bow may be rejected and logged.',
                     'None/projectile relies on PO3 weapon event provenance plus equipped ranged type, not a general magic hit subscription.'])
    (ROOT/'build/fix11-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'FIX11 RANGED ok: {len(rows)} outgoing cases; 8 incoming arrows; proc/mark/reaction; melee duplicate gate; rejected-hit throttle; non-quest FormIDs unchanged; current schema')
    return report
if __name__=='__main__': run()

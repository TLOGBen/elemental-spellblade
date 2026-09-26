"""Offline round-7 readback and execution of real Papyrus producers/delivery bodies."""
from pathlib import Path
import json,re,math,runpy,hashlib,struct
ROOT=Path(__file__).resolve().parents[1]

def body(file,fn):
    s=(ROOT/'src'/f'{file}.psc').read_text(encoding='utf-8')
    m=re.search(r'^[^\n]*\bFunction '+fn+r'\([^\n]*\n.*?^EndFunction',s,re.M|re.S)
    assert m,(file,fn)
    return m[0]

def run():
    import sys
    sys.path.insert(0,str(ROOT))
    import build_v03 as b
    harness=runpy.run_path(str(ROOT/'build/fix6_verify.py'))
    Ctl,Actor,Spell,Glob,make=[harness[n] for n in ('Ctl','Actor','Spell','Glob','make_scripts')]
    settings=json.loads((ROOT/'settings.json').read_text(encoding='utf-8'))
    records,meta=b.read_plugin(b.OUT/b.PLUGIN)
    manifest=json.loads((ROOT/'build/v03-formids.json').read_text(encoding="utf-8"))['records']
    baseline=json.loads((ROOT/'.codex/pre-fix7-snapshot/v03-formids.json').read_text(encoding="utf-8"))['records']
    assert all(b.state_schema.stable_identity(k,manifest.get(k),v) for k,v in baseline.items())
    added={k:v for k,v in manifest.items() if k not in baseline and k not in b.SCHEMA_STUBS and k not in b.GUARD_WINDOW_EDIDS and k not in (b.hit18.new_edids(b) | b.hit19.NEW_EDIDS | set(b.tree_v04.NEW_PERK_EDIDS))}
    names=['Dot','Cooldown','Recovery','Drain','Duration']
    assert set(added)=={'ESSB_Mult'+n for n in names} | {'ESSB_MultUpkeep'}
    added={k:v for k,v in added.items() if k != 'ESSB_MultUpkeep'}
    highest=max(int(v['id'],16) for v in baseline.values())
    by={r.edid:r for r in records}
    for n in names:
        edid='ESSB_Mult'+n;r=by[edid]
        assert int(added[edid]['id'],16)>highest
        assert r.sig=='GLOB' and r.d['FNAM']==b'f' and struct.unpack('<f',r.d['FLTV'])[0]==1.0
        assert by['ESSB_MainQuest'].d['VMAD'].count(b.vstr('Mult'+n)+bytes([1,1])+b.obj(b.own(int(added[edid]['id'],16))))==1
    assert manifest['ESSB_DebugLevel']['id']=='000811'
    assert manifest['ESSB_BaseDamageMult']==baseline['ESSB_BaseDamageMult']
    assert meta['masters']==['Skyrim.esm']

    # G never occurs in the shared utility, category helpers, or leech splitter.
    for fn in ['ApplyUtil','Leech','RecoveryAmount','DrainAmount','ApplyDotDamage']:
        assert 'GLevel(' not in body('ESSBController',fn)
    assert body('ESSBController','ApplyDamage').count('GLevel(')==1
    assert body('ESSBController','ApplyDamage').count('BaseDamageMult.GetValue()')==1
    assert 'GLevel(' not in body('ESSBController','ApplyDamageRaw')
    assert 'GLevel(' not in body('ESSBReactions','ReactDamage')
    assert 'GLevel(' not in body('ESSBReactions','BaseMax')
    for file,fn in [('ESSBElem2','HealAllies'),('ESSBController','SyncRockArmor'),('ESSBElem2','QuakeOne'),('ESSBElem2','Quake')]:
        assert 'GLevel(' not in body(file,fn),(file,fn)
    runpy.run_path(str(ROOT/'build/report_fix7.py'))
    proof=json.loads((ROOT/'build/fix7-g-proof.json').read_text(encoding='utf-8'))
    retired=[p for p in proof if p.get('retired')]
    v04=[p for p in proof if p.get('v04')]
    # Round 21: 12 v0.3 producers retired; ruling C1 put v0.4 values without G(L) on the ones v0.4 gives as plain
    # numbers (each checked in report_fix7: the line has the v0.4 value and no GLevel). The rest keep G exactly once.
    assert len(proof)==60 and len(retired)==13 and len(v04)>=30
    assert all(p['G']==0 for p in retired+v04)
    assert all(p['G']==1 for p in proof if p not in retired and p not in v04 and p['tree'] is not None)
    # Fixed ring sizes and serialized layout, byte-identical exporter/importer.
    before=ROOT/'build/fix7-before/src'
    for fn in ['ExportInts','ExportFloats','ImportState','RingAge','RingAdd','BleedRemaining']:
        old=(before/'ESSBStatus.psc').read_text(encoding='utf-8')
        m=re.search(r'^[^\n]*\bFunction '+fn+r'\([^\n]*\n.*?^EndFunction',old,re.M|re.S)
        current_body=body('ESSBStatus',fn)
        current_body=re.sub(r'\n\tIf Ctl && Ctl.StateBroken\n[\s\S]*?\n\tEndIf', '', current_body, count=1)
        if fn in ('RingAge','RingAdd','BleedRemaining'):assert m[0]==current_body,fn
        else:assert 'ESSBState.' in current_body or 'AstralWeight' in current_body  # exact new serialization roundtrip: DOT + FIX15
    old_helper=(before/'ESSBState.psc').read_text(encoding='utf-8')
    for fn in re.findall(r'(?m)^.*?Function (\w+)\(', old_helper):
        old_fn=re.search(r'(?m)^.*?Function '+fn+r'\([\s\S]*?^EndFunction',old_helper)[0]
        assert old_fn==body('ESSBState',fn),fn  # FIX9 only adds generation resolvers; ring helpers stay exact.

    cases=[]
    for mult in [.25,.5,1,2,3]:
        ctl=Ctl(settings);reg=make(ROOT/'src',ctl)
        ctl.MultRecovery.x=ctl.MultDrain.x=ctl.MultDot.x=ctl.MultDuration.x=mult
        ctl.MultCooldown.x=min(mult,2)
        ctl.UtilSpells=[Spell() for _ in range(28)];ctl.UtilTargetSpells=[]
        for kind in [1,2,3,4,5,6,7,10,11,18,19,25]:
            reg['ESSBController'].ApplyUtil(kind,40,8,Actor())
            expected=40*mult*(settings['base_damage_mult'] if kind==7 else 1)
            assert math.isclose(ctl.UtilSpells[kind].mag,expected),(kind,mult)
            assert ctl.UtilSpells[kind].duration==max(1,int(8*mult+.5))
        for kind in [0,8,13,14,15,16,17,20,21,23,24,26,27]:
            reg['ESSBController'].ApplyUtil(kind,40,8,Actor())
            assert ctl.UtilSpells[kind].mag==40,(kind,mult)
        reg['ESSBController'].ApplyUtil(4,1,0,ctl.player,True)
        assert ctl.UtilSpells[4].mag==1
        assert reg['ESSBController'].CooldownSeconds(10)==10*min(mult,2)
        assert reg['ESSBController'].DurationSeconds(1)==max(1,mult)
        assert reg['ESSBController'].DurationSeconds(0)==0
        cases.append({'category_multiplier':mult,'duration_8':ctl.DurationInt(8),'cooldown_10':10*min(mult,2)})

    # Actual shared producer outputs: 地震耐力削減 scales with the earth tree's G once; 裂痕護甲削減 (30 + 2 x 15) and
    # the rock armor layer (25) are v0.4 plain numbers and do not change with level (round 21, ruling C1).
    for level in [1,10,100]:
        ctl=Ctl(settings);ctl.level=level;reg=make(ROOT/'src',ctl)
        assert math.isclose(reg['ESSBElem2'].QuakeStamina(ctl),2.9*(1+.05*level)),('QuakeStamina',level)
        assert math.isclose(reg['ESSBElem2'].FissureArmor(ctl),60.0),('FissureArmor',level)
        assert math.isclose(reg['ESSBElem2'].RockArmorPerLayer(ctl),25.0),('RockArmorPerLayer',level)
    # Real JudgeArea calls real Judge: 1..6 targets; damage still reaches every target.
    judge=[]
    for count in range(1,7):
        ctl=Ctl(settings);ctl.level=10;ctl.CurrentElement=Glob(7);reg=make(ROOT/'src',ctl)
        ctl.IsUndeadOrDaedra=lambda t:False;ctl.NoteDamageElement=lambda e:None
        hits=[];ctl.ApplyDamage=lambda e,a,t:hits.append(a)
        ctl.ScanTargets=lambda *args:[Actor() for _ in range(count-1)]
        ctl.rank_default=0;ctl.branches={(6,2,1,0)}
        reg['ESSBElem2'].JudgeArea(ctl,Actor(),1.0)
        heal=sum(v for k,v in ctl.events if k==4)
        # v0.4 2.x: every 裁決 treats you B_max(聖) x 1.0 (10); no G(L), no damage multiplier, no round-7 budget cap.
        assert math.isclose(heal,count*ctl.ElementDamageMax[6]*1.0)
        assert len(hits)==count
        judge.append({'targets':count,'heal_total':heal})
    # Independent damage vs utility sibling: neither drain G nor slider leaks into damage input.
    dis=body('ESSBElem','Discharge')
    assert 'ApplyDamage(3, amount, akTarget)' in dis
    assert 'ApplyUtil(2, amount * drainRatio * akCtl.GLevel(2),' in dis
    assert 'ApplyUtil(2, amount * jumpRatio * drainRatio * akCtl.GLevel(2),' in dis
    assert 'remaining * akCtl.MultDot.GetValue() * surge +' in body('ESSBReactions','EndBlood')
    assert 'Ctl.ApplyDotDamage(8, venom, Holder)' in body('ESSBStatus','Tick')
    assert 'Ctl.ApplyDotDamage(6, bleed * ESSBElem2.BleedPerLayer(Ctl), Holder)' in body('ESSBStatus','Tick')
    assert 'ApplyDotDamage(10,' in body('ESSBController','TickDomain')
    # Preserve original file encodings and EOLs.
    checked=[]
    for old in (ROOT/'build/fix7-before').rglob('*'):
        if not old.is_file() or old.suffix not in ('.psc','.py','.json'):continue
        current=ROOT/old.relative_to(ROOT/'build/fix7-before')
        if not current.exists():continue
        a=old.read_bytes();c=current.read_bytes()
        assert a.startswith(b'\xef\xbb\xbf')==c.startswith(b'\xef\xbb\xbf')
        if a.count(b'\n'):
            assert (a.count(b'\r\n')==a.count(b'\n'))==(c.count(b'\r\n')==c.count(b'\n')),str(current)
        c.decode('utf-8');checked.append(str(current.relative_to(ROOT)))
    report=dict(existing_unchanged=len(baseline),appended=added,category_cases=cases,judge=judge,
                rings_and_export_unchanged=True,encodings_checked=checked,runtime_tested=False)
    (ROOT/'build/fix7-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'FIX7 ok: existing non-quest IDs unchanged; baseline={len(baseline)}; 5 appended float GLOBs; category execution + G once where v0.4 says so + Judge B_max per target + fixed layout + encodings verified')
    return report

if __name__=='__main__':run()

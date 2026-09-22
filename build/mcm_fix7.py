from pathlib import Path
import re, json

sources = {}
endings = {}
def read(p):
    p = str(p)
    if p not in sources:
        b = Path(p).read_bytes()
        endings[p] = '\r\n' if b.count(b'\r\n') == b.count(b'\n') else '\n'
        sources[p] = b.decode('utf-8').replace('\r\n', '\n')
    return sources[p]
def change(file, old, new, fn=None, count=1):
    p = 'src/'+file+'.psc' if not file.endswith(('.py','.json')) else file
    s = read(p)
    start,end = 0,len(s)
    if fn:
        m=re.search(r'^[^\n]*\bFunction '+fn+r'\([^\n]*\n.*?^EndFunction',s,re.M|re.S)
        assert m, (file,fn)
        start,end=m.span()
    block=s[start:end]
    assert block.count(old)==count,(file,fn,old,block.count(old),count)
    sources[p]=s[:start]+block.replace(old,new)+s[end:]

c=change
p='build_v03.py';s=read(p)
a=s.index('    general = [',s.index('def write_mcm('));b=s.index('    trees = [',a)
sources[p]=s[:a]+'''    general = [
        control('ESSB_Enabled', '附傷開關', 'toggle', defaultValue=int(settings['enabled'])),
        control('ESSB_PoisonDotK', '毒層係數', 'slider', min=0.0, max=1.0, step=0.001,
                formatString='{3}', defaultValue=settings['poison_dot_k']),
        control('ESSB_BleedDotK', '流血係數', 'slider', min=0.0, max=1.0, step=0.001,
                formatString='{3}', defaultValue=settings['bleed_dot_k']),
    ]
    general[1]['help'] = f'每層獨立維持 {POISON_LAYER_SECONDS} 秒；固定桶壽命不受持續時間倍率影響。'
    general[2]['help'] = f'每層維持 {BLEED_LAYER_SECONDS} 秒，命中刷新血痕；固定桶壽命不受持續時間倍率影響。'
    balance = []
    for edid, label, help_text in [
        ('ESSB_BaseDamageMult', '傷害倍率', '所有傷害；持續傷害另乘持續傷害倍率。'),
        ('ESSB_NodeScale', '節點倍率', '調整核准的百分比增傷主線；節點文字顯示建置預設倍率。'),
        ('ESSB_MultDot', '持續傷害', '毒、血、催毒、死域與血潮剩餘流血傷害。'),
        ('ESSB_MultCooldown', '冷卻', '乘上冷卻秒數；0.5 為一半冷卻。每秒輪詢的效果仍受 tick 精度限制。'),
        ('ESSB_MultRecovery', '回復', '生命、魔力、耐力與護盾；神佑固定 1 HP。'),
        ('ESSB_MultDrain', '削減', '敵方魔力、耐力、護甲削減；不改抗性削減與沉默鎖零。'),
        ('ESSB_MultDuration', '持續時間', '印記、狀態與領域，最短 1 秒；毒血桶壽命與星痕引爆延遲固定。'),
    ]:
        knob = control(edid, label, 'slider', min=0.25,
                       max=2.0 if edid == 'ESSB_MultCooldown' else 3.0, step=0.05,
                       formatString='{2} 倍', defaultValue=settings[ID_BALANCE_GLOB[edid][1]])
        knob['help'] = help_text
        balance.append(knob)
''' + s[b:]
c(p,"'content': general},","'content': general + debug},\n                        {'pageDisplayName': '平衡', 'cursorFillMode': 'topToBottom', 'content': balance},")
c(p,"'content': trees},\n                        {'pageDisplayName': '除錯', 'cursorFillMode': 'topToBottom', 'content': debug}","'content': trees}")
c(p,"    assert glob_edids == expected_globals and len(glob_edids) == 32","    expected_globals |= {'ESSB_Mult' + n for n in ('Dot', 'Cooldown', 'Recovery', 'Drain', 'Duration')}\n    assert glob_edids == expected_globals and len(glob_edids) == 37")
c(p,"rows = config['pages'][1]['content']","rows = config['pages'][2]['content']")
c(p,"general = {r['id']: r for r in config['pages'][0]['content']}","general = {r['id']: r for page in config['pages'][:2] for r in page['content']}\n    assert [p['pageDisplayName'] for p in config['pages']] == ['一般', '平衡', '技能樹']\n    assert [r['text'] for r in config['pages'][1]['content']] == ['傷害倍率', '節點倍率', '持續傷害', '冷卻', '回復', '削減', '持續時間']\n    for row in config['pages'][1]['content']:\n        v = row['valueOptions']\n        assert (v['min'], v['max'], v['step']) == (0.25, 2.0 if row['id'] == 'ESSB_MultCooldown' else 3.0, 0.05)\n        assert v['min'] <= v['defaultValue'] <= v['max']")
c(p,"(node['min'], node['max'], node['step']) == (1.0, 5.0, 0.5)","(node['min'], node['max'], node['step']) == (0.25, 3.0, 0.05)")
c(p,"(base['min'], base['max'], base['step']) == (0.5, 5.0, 0.1)","(base['min'], base['max'], base['step']) == (0.25, 3.0, 0.05)")
c(p,'(32 GLOB + 3 QUST)','(37 GLOB + 3 QUST)')
c(p,'(3 fix4 + 12 fix6)','(3 fix4 + 12 fix6 + 5 fix7)')
c(p,"runpy.run_path(str(WORK / 'build/fix6_verify.py'))['run']()","runpy.run_path(str(WORK / 'build/fix6_verify.py'))['run']()\n    runpy.run_path(str(WORK / 'build/fix7_verify.py'))['run']()")
c('ESSBController','\tLastNodeScale = -1.0','\tLastNodeScale = -1.0\n\tLastRecoveryScale = -1.0',count=1)
# Extend the existing round-6 harness with real round-7 helper calls, preserving all assertions.
p='build/fix6_verify.py';s=read(p)
s=s.replace('self.BaseDamageMult=Glob',"\n        for n in ['Dot','Cooldown','Recovery','Drain','Duration']:setattr(self,'Mult'+n,Glob(settings['mult_'+n.lower()]))\n        self.BaseDamageMult=Glob")
s=s.replace('def ApplyUtil(self,kind,value,duration,target):','def ApplyUtil(self,kind,value,duration,target,balanced=False):')
s=s.replace('    def ApplyTrueDamage(self,*args):',"    def DrainAmount(self,value):return self.scripts['ESSBController'].DrainAmount(value)\n    def RecoveryAmount(self,value):return self.scripts['ESSBController'].RecoveryAmount(value)\n    def DurationSeconds(self,value):return self.scripts['ESSBController'].DurationSeconds(value)\n    def DurationInt(self,value):return int(self.DurationSeconds(value)+.5)\n    def ApplyTrueDamage(self,*args):")
s=s.replace("added={k:v for k,v in written['records'].items() if k not in baseline}","added={k:v for k,v in written['records'].items() if k not in baseline and not k.startswith('ESSB_Mult')}")
sources[p]=s
for p,s in sources.items(): Path(p).write_bytes(s.replace('\n',endings[p]).encode('utf-8'))
print('MCM + existing verification integrated')


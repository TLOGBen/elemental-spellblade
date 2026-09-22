"""Generate full per-origin audit plus exact old-scan reconciliation, offline only."""
from entry51_audit import *
R,H,M=pickle.loads((W/'build/entry51-records.pickle').read_bytes())
REF=json.loads((W/'build/entry51-links.json').read_text(encoding='utf8'))
VM=json.loads((W/'build/entry51-vmad.json').read_text(encoding='utf8'))
CONFIG=json.loads((W/'build/entry51-configs.json').read_text(encoding='utf8'))
CALL=json.loads((W/'build/entry51-addperk-bytecode.json').read_text(encoding='utf8'))
SCRIPTS,STRINGS=pickle.loads((W/'build/entry51-scripts.pickle').read_bytes())
I=json.loads((W/'build/entry51-inputs.json').read_text(encoding='utf8'))
FUN={}
for m in re.finditer(r"Index:\s*(\d+); Name: '([^']+)'([^\n]*)",(W/'vendor/wbDefinitionsTES5.pas').read_text(encoding='utf8')):
 FUN[int(m[1])]={'name':m[2],'types':re.findall(r'ParamType\d: (\w+)',m[3])}
ZH={'GetIsID':'是指定對象','GetIsRace':'種族是','GetInFaction':'屬於派系','GetIsSex':'性別','GetDead':'已死亡','GetIsReference':'是指定參照','GetGlobalValue':'全域狀態值','GetRandomPercent':'隨機百分比','GetEquipped':'裝備指定物品','IsWeaponOut':'已拔出武器','IsSneaking':'正在潛行','IsInCombat':'正在戰鬥','IsPowerAttacking':'正在重擊','IsAttackType':'攻擊類型','IsAttacking':'正在攻擊','IsBlocking':'正在格擋','IsBashing':'正在盾擊','IsSprinting':'正在衝刺','GetEquippedItemType':'手上裝備類型','GetEquippedItemType2':'裝備類型','GetWeaponAnimType':'武器動畫類型','GetIsUsedItemType':'使用物品類型','HasKeyword':'帶有關鍵字','HasMagicEffect':'有指定魔法效果','HasMagicEffectKeyword':'有帶指定關鍵字的效果','HasPerk':'持有天賦','HasSpell':'持有法術','GetActorValue':'屬性數值','GetActorValuePercentage':'屬性剩餘比例','GetBaseActorValue':'基礎屬性數值','GetPermanentActorValue':'永久屬性數值','GetAVPercentage':'屬性剩餘比例','GetHealthPercentage':'生命剩餘比例','GetItemCount':'持有物品數量','GetDistance':'距離','GetLineOfSight':'看得到','GetDetected':'被指定角色偵測','GetDetectionLevel':'偵測程度','IsPlayerTeammate':'是玩家隊友','IsCommandedActor':'是受控制／召喚角色','IsHostileToActor':'敵對於','GetRelationshipRank':'關係等級','IsUndead':'是不死生物','IsBleedingOut':'正在瀕死倒地','IsStaggered':'正在失衡','IsRecoiling':'正在反彈硬直','GetKnockedState':'倒地狀態','GetIsCreature':'是生物','GetLevel':'等級','GetMovementDirection':'移動方向','GetAttackState':'攻擊狀態','GetIsUsedItem':'使用指定物品','GetIsUsedItemEquipType':'使用裝備位置','GetIsUsedItemType':'使用物品類型','IsDualCasting':'正在雙手施法','IsCasting':'正在施法','IsWeaponMagicOut':'武器／魔法已備妥','GetGraphVariableFloat':'動畫圖浮點狀態','GetGraphVariableInt':'動畫圖整數狀態','IsInKillMove':'正在處決動畫','GetIsGhost':'是幽靈／不可命中','GetIsObjectType':'物件類型','GetIsVoiceType':'聲音類型','IsSneakAttacking':'本次是潛行攻擊'}
AV={6:'單手',7:'雙手',8:'弓術',9:'格擋',24:'生命',25:'魔力',26:'耐力',30:'攻擊倍率',39:'火抗',40:'電抗',41:'火抗',42:'冰抗'}
strcache={}
def strings(stem,ext):
 key=stem+'_'+ext
 if key in strcache:return strcache[key]
 out={}
 for lang in ('english','chinese','traditionalchinese'):
  item=STRINGS.get(stem+'_'+lang+'.'+ext)
  if not item:continue
  data=item[1];n,size=struct.unpack_from('<II',data);base=8+8*n
  for i in range(n):
   fid,off=struct.unpack_from('<II',data,8+8*i);p=base+off
   if ext!='strings':ln=u32(data,p);raw=data[p+4:p+4+ln]
   else:raw=data[p:data.find(b'\0',p)]
   out[fid]=raw.rstrip(b'\0').decode('utf8',errors='replace')
 strcache[key]=out;return out
def field(r,key):
 v=r.d.get(key,b'')
 if not v:return ''
 if not r.localized:return text(v)
 if len(v)!=4:return '[本地化格式未知]'
 sid=u32(v);ext='dlstrings' if key in ('DESC','DNAM') else 'strings'
 return strings(Path(r.source).stem.lower(),ext).get(sid,f'[字串ID {sid:08X} 未解析]')
def label(key):
 if key is None:return '無'
 r=R.get(key)
 if not r:return key
 name=field(r,'FULL');return (name+'／' if name and name!=r.edid else '')+(r.edid or key)
def identity_ref(r,n):
 try:return r.ref(n)
 except ValueError:return 'INVALID:'+hex(n)
def cond(r,tab,h):
 d=bytes.fromhex(h);flags=d[0];val=struct.unpack_from('<f',d,4)[0];fn=u32(d,8)&65535;p1,p2,run,ref=struct.unpack_from('<4I',d,12)
 f=FUN.get(fn,{'name':'UNKNOWN_'+str(fn),'types':[]});params=[]
 for n,t in zip((p1,p2),f['types']):
  if flags&2:params.append('任務 alias '+str(n))
  elif t in ('ptInteger','ptFloat','ptAxis','ptSex','ptActorValue','ptCastingSource','ptFormType','ptQuestStage','ptMiscStat','ptEquipType','ptCriticalStage','ptVATSValueFunction','ptVATSValueParam'):
   params.append(AV.get(n,str(n)) if t=='ptActorValue' else str(n))
  elif t in ('ptVariableName','ptString'):params.append('字串參數（見 CIS1/CIS2）')
  else:params.append(label(identity_ref(r,n)))
 scope={None:'天賦本體（取得條件）',0:'持有人',1:'攻擊武器',2:'命中目標'}.get(tab,'分頁'+str(tab))
 if run!=0:scope+='／RunOn='+{1:'Target',2:label(identity_ref(r,ref)),3:'CombatTarget',4:'LinkedRef',5:'QuestAlias',6:'PackageData',7:'EventData'}.get(run,str(run))
 if flags&16:scope+='（交換 subject/target）'
 op=['＝','≠','＞','≥','＜','≤','未知','未知'][flags>>5]
 value=label(identity_ref(r,u32(d,4))) if flags&4 else f'{val:g}'
 desc=scope+'：'+ZH.get(f['name'],f['name'])+('（'+'；'.join(params)+'）' if params else '')+op+value
 return {'tab':tab,'fn':fn,'function':f['name'],'flags':flags,'run_on':run,'ref':identity_ref(r,ref),'p1':p1,'p1_ref':identity_ref(r,p1) if f['types'] and f['types'][0] not in ('ptInteger','ptActorValue','ptCastingSource','ptAxis','ptFormType') else None,'p2':p2,'value':val,'text':desc,'raw':h}
def condition_text(cs):
 if not cs:return '無條件限制'
 groups=[];group=[]
 for c in cs:
  group.append(c['text'])
  if not c['flags']&1:groups.append('（'+' 或 '.join(group)+'）' if len(group)>1 else group[0]);group=[]
 if group:groups.append('（'+' 或 '.join(group)+'）')
 return ' 且 '.join(groups)
DIST=collections.defaultdict(list);TREES=collections.defaultdict(list)
edids={r.edid.lower():k for k,r in R.items() if r.edid}
# MO2 loose file winner by relative path; configs are data, never instructions.
rank={n:len(I['enabled_mods'])-i for i,n in enumerate(I['enabled_mods'])};winning={}
for row in CONFIG:
 if not row['enabled']:continue
 p=Path(row['path']);relative=p.relative_to(MODS/row['mod']).as_posix().lower() if row['mod']!='<Data>' else p.relative_to(DATA).as_posix().lower()
 if relative not in winning or rank.get(row['mod'],0)>rank.get(winning[relative]['mod'],0):winning[relative]=row
for relative,row in winning.items():
 if relative.endswith('meta.ini') or 'manifest' in relative:continue
 for ln,line in enumerate(row['text'].splitlines(),1):
  line=line.strip()
  if not line or line.startswith((';','#','//')):continue
  m=re.match(r'(Perk|Spell|Keyword)\s*=\s*(0x[0-9a-f]+)~([^|]+)',line,re.I)
  if m:
   key=m[3].strip().lower()+f'|{int(m[2],16):06X}';DIST[key].append({'kind':m[1],'path':row['path'],'line':ln,'text':line})
  else:
   m=re.match(r'(Perk|Spell)\s*=\s*([^|]+)',line,re.I)
   if m and m[2].strip().lower() in edids:DIST[edids[m[2].strip().lower()]].append({'kind':m[1],'path':row['path'],'line':ln,'text':line})
 # CSF v1 INI plugin/form IDs are on separate lines; capture node sections.
 if 'customskill' in relative:
  for section in re.split(r'(?m)(?=^\[)',row['text']):
   plugin=re.search(r'(?im)^\s*PerkFile\s*=\s*"?([^"\r\n]+)',section);fid=re.search(r'(?im)^\s*PerkId\s*=\s*(0x[0-9a-f]+|[0-9]+)',section)
   if plugin and fid:
    key=plugin[1].strip().lower()+f'|{int(fid[1],0):06X}';TREES[key].append({'path':row['path'],'section':section.splitlines()[0]})
  try:obj=json.loads(row['text'])
  except Exception:continue
  def walk(v):
   if isinstance(v,dict):
    for k,x in v.items():
     if k.lower()=='perk' and isinstance(x,str):
      parts=re.split('[|~]',x)
      if len(parts)==2:
       try:
        plug,fid=(parts[0],parts[1]) if parts[0].lower().endswith(('.esp','.esm','.esl')) else (parts[1],parts[0])
        key=plug.lower()+f'|{int(fid,16):06X}';TREES[key].append({'path':row['path'],'json':x})
       except ValueError:pass
     walk(x)
   elif isinstance(v,list):
    for x in v:walk(x)
  walk(obj)
def routes(key,depth=0,seen=None):
 seen=set() if seen is None else seen
 if key in seen or depth>5:return []
 seen=seen|{key};out=[]
 for x in DIST.get(key,[]):out.append('分發 '+Path(x['path']).name+':'+str(x['line'])+' `'+x['text']+'`')
 for x in TREES.get(key,[]):out.append('玩家自訂技能樹 '+x['path'].split('mods\\')[-1])
 for x in REF.get(key,[]):
  host=R.get(x['from'])
  if not host:continue
  f=x['field'];prefix=host.sig+' '+label(host.key)+' ['+host.key+'] → '+f
  if host.sig=='AVIF' and f=='PNAM':out.append('玩家原生技能樹：'+prefix)
  elif host.sig=='NPC_' and f=='NPC perk':out.append('NPC 固有天賦：'+prefix)
  elif host.sig=='RACE':out.append('種族來源：'+prefix)
  elif f.startswith('VMAD'):
   script,prop=f[5:].rsplit('.',1);calls=[c for c in CALL if c['script']==script.lower()+'.pex' and ('::'+prop+'_var').lower() in str(c['instruction']).lower()]
   if calls:out.append(prefix+'；AddPerk 位元碼 '+', '.join(c['function']+'→'+str(c['instruction'][1]) for c in calls))
   else:out.append(prefix+'；只是屬性引用，未證實此屬性被 AddPerk')
  else:
   ancestors=routes(host.key,depth+1,seen)
   if ancestors:out.extend(prefix+' ← '+a for a in ancestors)
   else:out.append(prefix+'；上游取得來源未知')
 return list(dict.fromkeys(out))
ARCH={0:'改變屬性',1:'腳本效果',2:'驅散',3:'治療疾病',4:'吸收屬性',5:'雙屬性效果',6:'平靜',7:'恐懼',8:'狂暴',9:'繳械',10:'命令召喚物',11:'隱形',12:'光源',13:'開鎖',14:'召喚綁定武器',15:'召喚生物',16:'偵測生命',17:'心靈傳動',18:'麻痺',19:'復活',20:'靈魂陷阱',21:'迴避',22:'導引',23:'狼人餵食',24:'治療麻痺',25:'治療成癮',26:'治療中毒',27:'腦震盪',28:'屬性與部位',29:'蓄力',30:'變形',31:'累積幅度',32:'失衡',33:'價值修正',34:'減速時間',35:'吸血鬼領主',36:'附魔',37:'危害區',38:'乙太化',39:'放逐',40:'生成腳本效果',41:'偽裝',42:'抓取'}
def spell_summary(key):
 r=R.get(key)
 if not r:return '未知：命中法術紀錄未解析 '+str(key),{}
 effects=[];cur=None
 for k,v in r.ss:
  if k=='EFID':cur={'id':identity_ref(r,u32(v)),'conditions':[]};effects.append(cur)
  elif k=='EFIT' and cur is not None:cur.update(zip(('magnitude','area','duration'),struct.unpack('<fII',v)))
  elif k=='CTDA' and cur is not None:cur['conditions'].append(cond(r,2,v.hex()))
 desc=[]
 for e in effects:
  m=R.get(e['id'])
  if not m:desc.append('未知效果 '+e['id']);continue
  d=m.d.get('DATA',b'');ar=u32(d,64) if len(d)>=72 else -1;av=struct.unpack_from('<i',d,68)[0] if len(d)>=72 else -1
  e.update(edid=m.edid,name=field(m,'FULL'),description=field(m,'DNAM'),archetype=ar,actor_value=av,scripts=VM.get(m.key,[]))
  textpart=field(m,'DNAM') or field(m,'FULL') or m.edid
  textpart=re.sub('<[^>]*>','',textpart).replace('\n',' ')
  native=ARCH.get(ar,'未知 archetype '+str(ar))
  if ar in (0,4,5):native+=' '+AV.get(av,str(av))
  extra='；腳本 '+','.join(v.get('name','?') for v in VM.get(m.key,[])) if VM.get(m.key) else ''
  desc.append(f'{textpart}（{native}；幅度 {e.get("magnitude",0):g}／{e.get("duration",0)} 秒{extra}）')
 return '；'.join(desc) or ('未知：法術無 EFID '+label(key)),{'key':key,'edid':r.edid,'effects':effects}
def priority(p):
 now='壓過正式包全部 127～200' if p<127 else '正式包壓過它' if p>200 else f'與正式包 {p} 平手；壓過 >{p}，輸給 <{p} 的啟用項'
 return f'{p}：{now}；我方改 0 時'+('平手，winner 未測定' if p==0 else '我方勝出')
def classification(cs,rt):
 funcs={c['function'] for c in cs}
 if not cs:return '每次武器命中（取得天賦後；法術內仍可能另有條件）'
 if funcs & {'HasMagicEffect','HasMagicEffectKeyword','GetEquipped','GetIsUsedItem','GetGlobalValue'} or any('MGEF perk to apply' in x or 'OnEquipped' in x for x in rt):return '特定武器／增益／狀態期間'
 return '常見子集（詳列武器、動作、目標與機率限制如下）'
def main():
 raw=[];p=None
 for ln,s in enumerate((W/'.codex/entry51-loadorder-scan.txt').read_text(encoding='utf8').splitlines(),1):
  if s.startswith('== '):p=s[3:].split('  (')[0]
  elif ' | prio' in s:
   ed=s.strip().split(' | ')[0];keys=[k for k,hh in H.items() if any(x['source'].lower()==p and x['edid']==ed for x in hh)]
   raw.append({'line':ln,'plugin':p,'edid':ed,'keys':keys})
 keys=sorted({k for row in raw for k in row['keys']})
 rows=[]
 for key in keys:
  r=R.get(key)
  if not r:rows.append({'key':key,'missing':'最終紀錄刪除／未讀得'});continue
  top,ee=entries(r);rt=routes(key)
  row={'key':key,'winner_plugin':r.source,'edid':r.edid,'name':field(r,'FULL'),'description':field(r,'DESC'),'history':H[key],'routes':rt,'perk_conditions':[cond(r,t,h) for t,h in top],'entries':[],'distribution':DIST.get(key,[]),'trees':TREES.get(key,[])}
  for e in ee:
   cs=[cond(r,t,h) for t,h in e['conditions']];spell=identity_ref(r,int.from_bytes(bytes.fromhex(e.get('EPFD','00000000'))[:4],'little'));effect,detail=spell_summary(spell)
   row['entries'].append({'priority':e['priority'],'rank':e['rank'],'conditions':cs,'frequency':classification(cs,rt),'priority_text':priority(e['priority']),'spell':detail,'loss_when_essb_wins':effect,'loss_when_other_wins':'本次命中的 ESSB 元素 proc（只有本次應觸發時才有損失）'})
  rows.append(row)
 dump('entry51-audit-data.json',rows);dump('entry51-reconciliation.json',raw);dump('entry51-distribution.json',dict(DIST));dump('entry51-trees.json',dict(TREES))
 funcs=collections.Counter(c['function'] for r in rows for e in r.get('entries',[]) for c in e['conditions']);dump('entry51-functions.json',dict(funcs))
 print('rows',len(raw),'origins',len(keys),'final entry51',sum(bool(r.get('entries')) for r in rows),'unmatched',sum(not r['keys'] for r in raw),'trees',len(TREES),'distributions',len(DIST))
 if '--data-only' in sys.argv:return
 lines=['# Entry 51 相容性稽核（normal 設定檔，離線檔案證據）','', '本報告以原始掃描逐列對帳，再以載入序最後一筆同源 FormID 覆寫為準。取得途徑不明的天賦也全部保留；不以名稱含 NPC 或 Test 就刪掉。實際存檔持有哪些天賦、SKSE DLL 動態賦予、玩家選過哪些樹與 buff，未從遊戲執行狀態驗證。','', '## 閱讀規則','', '同一刀只會有一個 entry 51 法術，數字越小越優先。表內只比較這個天賦與 ESSB；第三個模組仍可能同時搶走該刀。127～200 是正式包不同條目的優先序，不能把 150 一律寫成勝或敗。priority 0 已是下限，與另一個 0 只會平手，沒有比 0 更小的值。','', '「天賦本體」CTDA 列為取得／顯示門檻，不冒充每刀條件；每刀使用各 entry 的分頁條件。分頁 0=持有人、1=攻擊武器、2=命中目標；括號內「或」與組間「且」保留原 OR 邏輯。法術效果層 CTDA 在 JSON 的 spell.effects.conditions，效果層不生效不等於 entry 不會占用 winner。','', '## 全項清單（a／b／c／d）','']
 for row in rows:
  lines += ['### '+row['key'].replace('|',' / ')+' — '+row.get('name','')+' '+row.get('edid',''),'']
  if 'missing' in row:lines+=['a／b／c／d：未知；'+row['missing'],''];continue
  lines+=['最終覆寫：`'+row['winner_plugin']+'`。舊紀錄：'+' → '.join(x['source']+' / '+x['edid'] for x in row['history'])+'。','']
  rt=row['routes'];lines+=['**a. 誰會取得**：'+('；'.join(rt) if rt else '未知：未找到靜態技能樹、NPC PRKR、MGEF Perk to Apply、VMAD、已解析分發或自訂樹引用。未證明不可取得，DLL／動態查表仍可能賦予。'),'']
  if row['description']:lines+=['天賦說明：'+row['description'].replace('\n',' '),'']
  lines+=['天賦本體條件：'+condition_text(row['perk_conditions'])+'。','']
  if not row['entries']:lines+=['**b. 實際不參與 entry 51**：最後覆寫已移除。**c.** 舊 priority 不適用，與正式包／0 均不競爭。**d.** 此紀錄沒有命中法術可被搶，也不會搶走我方元素 proc。',''];continue
  for i,e in enumerate(row['entries'],1):
   lines+=['- **b'+str(i)+'. '+e['frequency']+'**：'+condition_text(e['conditions'])+'。', '  **c.** '+e['priority_text']+'。', '  **d. 我方贏時少掉**：'+e['loss_when_essb_wins']+'。**對方贏時少掉**：'+e['loss_when_other_wins']+'。']
  lines+=['']
 lines+=['## 證據附錄','',f'- 原掃描實際 {len(raw)} 列、{len({r["plugin"] for r in raw})} 個插件標題；同源去重 {len(keys)} 筆；{sum(bool(r.get("entries")) for r in rows)} 筆最後仍有 entry 51。背景的 382 與此指定檔案不一致，未提供的 53 列無法凭空補列。','- `entry51-reconciliation.json`：每一原始行號、舊 EDID 與同源 FormID；全部原始行都必須有對應。','- `entry51-audit-data.json`：每 entry 的 32-byte CTDA 原文、函式編號／分頁／比較值、最終法術與效果／效果 CTDA、覆寫鏈及取得引用。','- `entry51-inputs.json`：插件實際供檔路徑、SHA-256、master、載入序、MO2 啟用清單與設定檔雜湊；未讀取權限外的 overwrite 或 Skyrim.ccc。','- `entry51-links.json`、`entry51-vmad.json`：最後覆寫紀錄的 typed refs 與屬性。MGEF DATA+136 為 Perk to Apply；AVIF PNAM 為樹節點；NPC PRKR 為固有 perk。','- `entry51-configs.json`、`entry51-distribution.json`、`entry51-trees.json`：包括停用模組的搜尋原文；判讀只用已啟用且相對路徑獲勝檔。SPID／KID 設定與動畫條件引用分開，不把 HasPerk 動畫條件当賦予。','- `entry51-addperk-sources.json`、`entry51-addperk-bytecode.json`：MO2 全部來源碼 AddPerk 搜尋；341 個相關 BSA 與啟用 loose PEX 索引，7475 支 PEX 完整離線解析，510 個 AddPerk 指令。保留接收者、函式、完整指令序列；屬性存在本身不代表呼叫。','- `entry51-script-errors.json`／`entry51-link-errors.json`：未找到腳本、解析限制；原生 DLL 沒有當成已反編譯。','- 本機 `vendor/wbDefinitionsTES5.pas`：CTDA 函式與參數型別、PERK／MGEF 欄位定義。英文本地化名稱可由載入 BSA 的 STRINGS 解析；未解析者顯示字串 ID，不捏造翻譯。DSD 執行時覆蓋字串未完整合併，EDID／FormID 為穩定識別。','- `.codex/smoke8-probe-results-Papyrus.0.log`／`.codex/smoke9-probe3-Papyrus.0.log`：使用者指定的引擎實測證據。相等 priority 的新探針未入遊戲測試。','']
 (W/'build/entry51-compat-audit.md').write_text('\n'.join(lines),encoding='utf8')
if __name__=='__main__':main()

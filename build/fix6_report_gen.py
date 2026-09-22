from pathlib import Path
import json,collections,math
ROOT=Path.cwd();data=json.loads((ROOT/'build/fix6-check.json').read_text(encoding='utf-8'));rows=json.loads((ROOT/'build/fix6-classification.json').read_text(encoding='utf-8'))
labels={'SCALED':'×3','UNCHANGED':'不改','DECISION':'不改—需決策','SPECIFIC':'第2／2b項指定'}
def table(selected):
 lines=['| 樹 | 路線（index） | 階（index） | 分類／原因 | 原文 | 新數值／顯示文字 | 實際程式位置 |','|---|---|---|---|---|---|---|']
 for r in selected:
  site='；'.join(f'{a[0]}:{a[1]}' for a in r.get('code_sites',[])) or r['site']
  if r['tree']=='noform' and (r['route'],r['tier']) in [(0,0),(0,3),(2,3)]:site+='；build_v03.py:main_entries（預設 EPFD）'
  vals=[r['tree'],f"{r['route_name']}（{r['route']}）",f"{r['tier_name']}（{r['tier']}）",labels[r['status']]+'：'+r['reason'],r['old'],r['new'],site]
  lines.append('| '+' | '.join(str(x).replace('|','／').replace('\n',' ') for x in vals)+' |')
 return '\n'.join(lines)
(ROOT/'build/fix6-classification.md').write_text('# 195 主線完整分類\n\n'+table(rows)+'\n',encoding='utf-8')
(ROOT/'build/fix6-scaled-nodes.md').write_text('# 明確納入 ×3 的 105 主線\n\n'+table([r for r in rows if r['status']=='SCALED'])+'\n',encoding='utf-8')
notfixed=table([r for r in rows if r['status']=='DECISION'])
mult=['| 元素 | 元素樹單獨：舊 → 新 | M_mod 主線條件值：舊 → 新 | 新 G(100) × M_mod | 全分支條件上界：舊 → 新 |', '|---|---:|---:|---:|---:|']
for m,e in zip(data['multipliers'],data['branch_envelopes']):
 mult.append(f"| {m['element']} | {m['old']['element_mult']:.4f} → {m['new']['element_mult']:.4f} | {m['old']['M_mod']:.4f} → {m['new']['M_mod']:.4f} | {m['new']['G_times_M']:.4f} | {e['old']:.4f} → {e['new']:.4f} |")
oldburst=1.45*1.75*1.3*1.3*1.6;newburst=2.35*3.25*1.9*1.9*2.8
report=f'''\n\n## fix round 6（節點數值）

本輪產物：`package/Elements Spellblade/Elements Spellblade.esp` 與同資料夾內的 Scripts、Source、SKSE/Plugins/CustomSkills、MCM/Config；只生成工作區套件，沒有安裝到 MO2 或 SkyrimSE。原規劃文件維持原樣，本節記錄數值偏離。

### FIXED / NOT FIXED

| 狀態 | 工作 | 結果／邊界 |
|---|---|---|
| FIXED | 純百分比增傷 | 從 195 主線資料分類，105 節點 ×3；settings `node_percent_scale=3.0` → float GLOB `ESSB_NodeScale=0x00515C` → Controller.NodeScale → ESSBNodes.Pct；每個納入節點均有程式位置驗證。 |
| NOT FIXED — needs a decision | 題述的 56 與資料不一致 | 實際原文含 `+N%／點` 的節點共131；明確純增傷105，分布為 {data['scaled_distribution']}。不以刪節點或任意挑56來湊數。14 個混合／語義有疑義的節點保留原值，見下表。 |
| FIXED | 顯示與調整 | 同一份生成資料產出全部 2925 主線 rank PERK DESC；CSF 節點引用這些 PERK 顯示文字，沒有另外一套數字。火每層 8%→17%、死咒15%→37.5%、落地×0.5→×2.75等範圍也重算。MCM「一般」增加1.0–5.0、step0.5滑桿。 |
| FIXED | 破魔 | (20+4×rank)×G，蝕魔10%、枯竭20%，實際削量封頂與等量回魔保留；比例0.5→0.95、施法者 +5%／點、沉默／反咒時長保留。 |
| FIXED | 水／霜 | 長流2.0%基礎、熟練+0.2%／點、浸濕15%、霜結25%、清流30、回流80；大師／傳奇長流各0.05%規則與水牢20%不變。 |
| FIXED | 共用減速上限 | ESSBController.ApplyUtil 的 aiIndex=0 在 SetNthEffectMagnitude 前夾到 SlowCapPct，且硬上界70；所有本模組移動減速共用原有 ESSB_UtilEffect_Slow（AV30、Peak Value Modifier 34），同款效果取最強，不是不同來源相加。沒有新增定身／麻痺。 |
| FIXED | 固定數值盤點 | `build/flat-values-audit.md` 共60列、13/13樹；來源交叉表 `build/flat-values-audit-source.json`，建議一律未套用。 |
| NOT FIXED（照要求保留） | 水治療超過神聖 | 常態單體持續戰鬥已反超原設計5.11的預期；未偷偷設治療上限，也未改神聖。多目標裁決可讓神聖瞬間治療更高，詳見比較。 |
| FIXED | 編譯、原有檢查與 FormID | `python build_v03.py` exit0；19腳本全數0 errors；既有3895筆 identity與 pre-fix6 快照一致；新增12筆float GLOB 0x00515C–0x005167；DebugLevel仍0x000811。 |
| NOT FIXED（原有） | 穩步與遊戲內實測 | PLAN COVERAGE原有穩步DEFERRED仍保留；本輪沒有改動或宣稱修復。未啟動遊戲，動作排程、引擎效果與MCM互動仍需實機驗證。 |

### 指定數值前後與 G(L) 證明

settings 中 `_pct` 的單位為百分點（例如10.0表示10%），腳本需要比例時乘0.01。所有12個新常數均有float GLOB與QUST VMAD屬性綁定；`node_percent_scale` 之外11個常數沒有新增MCM項目。

| 設定／路徑 | 原值 | 新值 | 位置 |
|---|---|---|---|
| node_percent_scale | 無（等同1） | 3.0 | ESSBNodes.psc:Pct |
| manabreak_base / manabreak_per_rank | 5 + rank，沒有G | (20 +4×rank)×G(noform) | ESSBNoForm.psc:OnManaBreak |
| manabreak_maxmag_pct | 最大魔力2% | 10%，仍與已乘G的固定削量取高者 | ESSBNoForm.psc:OnManaBreak |
| manabreak_dry_pct | 玩家當前魔力5% | 20% | ESSBNoForm.psc:OnManaBreak |
| 破魔真傷比例 | 0.5 +0.03×rank，cap0.95 | 不變 | ESSBNoForm.psc:OnManaBreak |
| 施法者削魔加成 | 1+0.05×rank | 不變，滿點×1.75 | ESSBNoForm.psc:OnManaBreak |
| water_flow_base_pct | 0.3%／秒 | 2.0%／秒 | ESSBElem3.psc:FlowPercent |
| water_flow_per_rank_pct | +0.02%／點 | +0.2%／點，熟練滿點5.0% | ESSBElem3.psc:FlowPercent |
| water_wet_slow_pct | 10% | 15%，原主線+1%／點仍在，滿點30% | ESSBElem3.psc:WetSlow |
| frost_open_slow_pct | 15%／3秒 | 25%／3秒 | ESSBReactions.psc:Open |
| slow_cap_pct | 無共用上限，部分路徑80／90 | 70% | ESSBController.psc:ApplyUtil |
| water_clear_stamina | 5／命中 | 30／命中 | ESSBElem3.psc:OnWaterHit |
| water_open_stamina | 15／開印 | 80／開印 | ESSBElem3.psc:OpenWater |

破魔順序：`fixed=(20+4r)G` → 蝕魔時 `max(fixed, MaxMagicka×0.10)` → 施法者 `×(1+0.05×pierce)` → `actual=min(requested,currentMagicka)` → 扣除actual、回玩家actual → `trueAmount=actual×ratio`。`ApplyTrueDamage(..., abLevelScaled=True)`跳過自己的G乘法；原本的TrueMult（低魔力傳奇）與靜寂加成仍照常套用。百分比蝕魔分支若勝出，其10%本來就是獨立下限，也不再額外乘G。以下驗證關掉TrueMult／靜寂，避免把額外節點誤算成G：

| 樹等級／rank／目標當前魔力 | actual | ratio | 真傷（含G一次） | 回玩家魔力 |
|---|---:|---:|---:|---:|
| L10／r1／1000 | 36 | 0.95 | 34.2 | 36 |
| L100／r15／1000 | 480 | 0.95 | 456 | 480 |
| L100／r15／100 | 100 | 0.95 | 95 | 100 |
| L100／r15／10000，蝕魔＋施法者主線滿點 | 1750 | 0.95 | 1662.5 | 1750 |

L100、r15的普通施法者固定削量是480×1.75=840，再由當前魔力封頂。r1、L10且比例未投點的真傷=36×0.5=18。滿點低魔力傳奇現為+9%／點，另乘2.35；不能把此合法節點倍率誤認為重複乘G。

枯竭沒有actual drain，所以保留原路徑的一次G：玩家當前魔力300、L100時，300×20%×6=360（其他傷害節點另計），不是72也不是2160。離線測試直接執行上述兩個Papyrus函式內容，並核對回魔、比例封頂與兩個G分支；沒有用另一套抄寫公式冒充遊戲驗證。

### 長流與神聖比較

長流滿點、同調3：2.0 +15×0.2 +15×0.05×3 +15×0.05 = **8.0%／秒**；原為3.6%。這是每次WaterFormTick的上限，NodeScale=1、3、5均不影響。未投點基礎：300HP角色由0.9HP/s變6HP/s；滿點300–500HP角色為24–40HP/s，200–400耐力為16–32/s。玩家與原有範圍同伴的套用條件、對象都不變。

神聖B_max=10，治療走ApplyUtil，**不吃G(L)**：持續專精滿點僅3HP／擊；白天開印基礎6×1.45=8.7，再加開啟新手滿點7.5，合計16.2／開印；裁決每名受影響目標12HP（最多主目標＋5人=72／次）；聖斷每個融斷目標再12HP；聖域站內10HP/s；聖引10、聖臨20是額外事件，不是常駐每秒。

可稽核的持續模型（白天、不算外部回復）：`神聖HP/s = 3×每秒命中 +16.2×每秒開印 +12×每秒被裁決目標數 +12×每秒聖斷目標數 +10×聖域覆蓋率 +10×每秒聖引 +20×每秒聖臨`；通用回饋等一次性事件另加。無開印／終焉事件的1擊/s單體戰鬥，神聖為3，假設聖域100%覆蓋也只有13；遠低於水的24–40。即便單體每10秒額外開印、裁決、聖斷各一次，也只再加4.02/s。

另外，原有通用「化身」滿點每15秒能額外呼叫一次WaterFormTick，所以計入此額外事件，長流平均為8×(1+1/15)=8.5333%/s（300–500HP為25.6–42.6667），再加潮池站內7/s，為32.6–49.6667。神聖化身單體相當於12/15=0.8HP/s、六目標最多4.8HP/s；群體反覆裁決才可能超越水。水斷本身仍按融斷倍率回血／回耐，未在本輪另調基準。

**設計偏離：新水在常態單體與同伴持續治療已明顯超越神聖；8%不是包含所有分支事件的「全樹總治療」上限。** 保留使用者指定數值，不設新治療cap。大量敵人的神聖範圍裁決仍可能出現更高的瞬間回血，不能宣稱水在所有情境都更高。

### 倍率最壞情境檢查（樹等級100、同調3）

數字直接執行修改前備份／目前腳本的`GetHitMult`、各樹`HitMult`及共用helper取得，明細在`build/fix6-check.json`。舊「約×1.7」只接近一般元素樹自己的1+15%+45%+15%=1.75，**不是完整M_mod上界**；新值為1+45%+135%+45%=3.25，通用樹重擊倍率亦由1.75→3.25，兩者相乘已由3.0625→10.5625。

為呈現上界，表中所有主線（含未調的層數上限）都投滿、開印增益有效、重擊；熱度取無添薪時觸發自燃前12層、冰封5、聖印8、水壓8（僅開必要的水壓分支）、詛咒13；目標滿詛咒，接管增益有效（舊1.15→新1.45），滿血血位1.3；聖取白天、暗取夜晚各1.2。其餘分支關閉；這欄未放入火過熱等分支／狀態加成。M_mod不含G、B、重擊R=1.5、抗性或外部模組。

最右欄是更保守的**全分支條件上界**：所有分支、嗜血1.2、萬象1.25、風失衡／浮空1.3×1.5、星鎖1.1、星域1.2、暗低魔施法者1.5、火17熱度＋過熱／熔身／火域等全部條件各取最大，星痕9層。用來暴露既有乘算的風險，不代表所有互斥或短視窗必能在同一擊同時出現；實際可達峰值需遊戲事件順序驗證。

{chr(10).join(mult)}

元素樹內火／聖／水本来就有逐層項，不能把整欄都稱作舊×1.7。M_mod以外的原有開印擊分支最多再×1.5×1.5，風潛行／連殺最多×5×2，反擊再×1.3，皆未改值；G(100)=6與重擊R=1.5仍各乘一次。表內不是所有反應、DoT與無上限毒層的全系統單一上限。

終焉／融斷亦不能只看附傷：不含分支的共用融斷節點乘積 `CommonBurst×NoFormBurst×CommonEnd×ElementEnd×ElementBurst` 原={oldburst:.6f}、新={newburst:.6f}；同調3的K_sync=3另乘，單獨招式Signature對常見+3%主線則1.45→2.35。完整含K_sync與Signature的共同部分原={oldburst*3*1.45:.6f}、新={newburst*3*2.35:.6f}，尚未乘該招式K、G、狀態層數、環境、目標增傷或分支。水斷不乘Signature、其基準14在此無分支條件下已是14×3×{newburst:.6f}={14*3*newburst:.3f}回復／印記；因此盤點建議對水斷暫留，不再盲目提高基準。

無形態武器進入點維持原本結構：一般主線滿點1.15→1.45；每層戰意1.075→1.225，五層實作仍乘五次；淬火1.15→1.45。因此三者同時有效的武器倍率由{1.15**2*1.075**5:.6f}→{1.45**2*1.225**5:.6f}，不是五層戰意加法。既有條件與PRKE數目不變，僅EPFD預設值與SKSE SetNthEntryValue寫入值改動。

### 固定數值盤點摘要（未修改）

`build/flat-values-audit.md`的60列含所有13樹與基礎反應，依單次資源占比與觸發成本排序。最弱的一批：血命中基礎吸血約0.65–3／擊（有主線仍多為2.6–3.9）、神聖滿點3HP／擊、追風3耐／次、汲力滿點3.75耐／擊、毒血4.5HP／次、順風5耐／擊與深寒5削耐／秒。B_max型回血／回魔多數沒有G，不能因為傷害有G就推定它們也成長。雷神滿層150–350回魔、磐石滿層325護甲其實已可感受，表中明確建議保留。血盾是最大生命百分比，神佑1HP是保命語義，不當作可直接乘大的普通補血。表內建議沒有寫回settings或腳本。

### 未改 — 需要決策（14個）

{notfixed}

### 全195主線分類表（含原文、新數值、程式位置）

分類函式為`plan_trees.py:classify_main`：先排除指定不動的比例／施法者加成、機率、治療、減抗、移速／控制／防禦，再標記混合效果待決，最後以原文`+N%／點`與傷害語義分類。每個SCALED節點必須能映射到實際Pct呼叫，否則建置失敗；共享函式按樹展開比對，不能把函式個數當成節點數。完整資料版`build/fix6-classification.json`；105個改值節點另列`build/fix6-scaled-nodes.md`。其餘72個不改；4個SPECIFIC是破魔、長流熟練、浸濕、霜結說明。

{table(rows)}

### 驗證與保留界線

- 最終建置：`python build_v03.py` exit0。`build/fix6-build.log`包含DOT ok（12秒毒／10秒血、38 ints）、LAYOUT 13/13、19 compile OK、FIX3／FIX4／FIX6／MCM ok、READBACK masters=['Skyrim.esm'] records=3907 manifest=3907、CSF13/13、DELIVERY ok、PLAN COVERAGE unmapped=0。
- pre-fix6的3895筆FormID完全一致，僅附加12個GLOB；無新masters；ESSB_DebugLevel仍000811。VMAD每個常數僅綁一次，float回讀對照settings。MCM32個GLOB來源＋3個QUST動作參照均可解析。
- 全2925主線rank描述及300分支描述逐筆ESP回讀；僅四個明確核准分支描述變更。CSF節點直接引用同一PERK文字；MCM滑桿不會在遊戲內重寫ESP描述，描述顯示建置預設3.0；改settings重建會一起更新。
- 腳本數值透過讀取實際函式內容離線執行：Pct的rank0／1／15、scale1／1.5／3／5；全部45個武器rank PERK的105個entry更新；破魔固定削量／蝕魔／施法者／魔力不足／枯竭；長流不吃NodeScale；15–999的減速輸入均夾住。此工具只執行公式與mock delivery，沒有偽稱代替Skyrim引擎測試。
- 已核對24個原檔的BOM與LF／CRLF型態；既有來源編碼與換行保留。本紀錄以bytes append保留原有混合換行與全部舊內容。`build/fix6-before/`保留修改前來源，生成的`build/fix6-encoding-check.json`列出結果。
- 沒有修改設計原稿、review檔、fx_extract.py、.strategic-advance/**，沒有寫入MO2或SkyrimSE。第三輪FX、第四輪B／DoT／BaseDamageMult、第五輪狀態序列化與MCM既有功能均通過原檢查。
- 動態weapon百分比僅在既有Tick偵測NodeScale變更或讀檔後刷新全部rank entries；不改條件、觸發次數、buff時長、支線、傷害投遞方式。原有OnEnd對其他樹亦建立EndBoost的路徑保留舊0.01×rank，只有資料明定的冰／雷／聖／毒／水五個主線放大，避免共用函式越界改到非百分比節點。
'''
(ROOT/'build/fix6-report.md').write_text(report,encoding='utf-8')
print('Report prepared',len(report),'characters; classification',len(rows),'changed',sum(r['status']=='SCALED' for r in rows))

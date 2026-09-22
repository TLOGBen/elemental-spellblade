from pathlib import Path
import json,hashlib,html
root=Path('.')
old=json.loads((root/'build/fix3-before/fx-bindings.json').read_text(encoding='utf-8'))
new=json.loads((root/'build/fx-bindings.json').read_text(encoding='utf-8'))
audit=json.loads((root/'build/fx-visibility.json').read_text(encoding='utf-8'))
old_rows={r['element']:r for r in old['elements']}
candidates={r['edid']:r for r in audit['candidates']}
derived={r['selector'].split('|')[1]:r for r in audit['derived']}
f=lambda v:format(v,'.3g')
def nums(r):
 return (' / '.join(f(r[k]) for k in ('fill_persistent_alpha','edge_persistent_alpha'))+'; '+
         ' / '.join(f(r[k]) for k in ('fill_full_time','edge_full_time'))+'; '+
         ' / '.join(f(r[k]) for k in ('fill_full_alpha','edge_full_alpha')))
def rgb(r):return ','.join(str(c) for c in r['edge_color'])
lines=['','## fix round 3（特效回饋）','',
'本輪已自行執行 `python build_v03.py`，exit 0；產物在 `package/Elements Spellblade/`。依首次實機回饋將 11 個形態光環改回 Phenderix 原始 form shader；印記與命中特效拆開。建置、EFSH 數值及腳本生命週期檢查已通過，尚未宣稱遊戲內觀感已驗收。','',
'### 形態光環逐元素對照','',
'下表是本插件內 EDID；每筆「後」的來源 selector 都是 `Phenderix Elements.esp|ZZShader_<Element>Form`。11 筆原本已齊全，沒有補匯入或改寫其 EFSH DATA。退下來的借用光環仍保留原 FormID，實際未綁定者列在 `build/fx-bindings.json` 的 `unbound_spares`（依 MGEF 實際引用計算）。','',
'| 元素 | Aura 前 | Aura 後 |','|---|---|---|']
for r in new['elements']:
 o=old_rows[r['element']];lines.append(f"| {r['zh']} `{r['element']}` | `{o['aura_shader']}` | `{r['aura_shader']}` |")
lines+=['','### 印記：資料解析、選擇與可讀性','',
'依 `vendor/wbDefinitionsTES5.pas:7043–7182` 逐欄解析 66 個已複製 EFSH。DATA 位移：fill full time=24、fill persistent alpha=32、edge RGB=56、edge full time=64、edge persistent alpha=72、fill/edge full alpha=84/88、粒子 full time=116、持續粒子數=128、Ambient Sound=308、Flags=384。schema 回歸測試獨立從 Pascal 欄位順序算出相同位移。312-byte 舊記錄沒有 offset 384 的 Flags，報告為 null，不能擅自當成 0；這些記錄只作色彩來源，不作持續邊緣的證據。','',
'火、血、暗、星的舊命中霧效 flags 含 `0x1 No Membrane Shader`；風亦停用膜層。它們可有粒子持續，但無法提供可靠的目標輪廓。神聖舊命中效果 persistent fill/edge 均為 0；大地 persistent edge=0。冰霜的舊效果持續 fill=0.75，外觀偏全身覆蓋；水的舊效果 fill=1 且 RGB 偏暗。雷原效果已具合格持續邊緣（fill=0.01、edge=0.75），故用它作所有新印記的幾何／混合模板，保留原件不動。','',
'新增 11 個 `Elements Spellblade.esp|ESSBFX_Mark_<Element>`：模板選 `StormCalling.esl|_SC_ShockStormFXShader`，元素 RGB 則逐一取下表的實際來源，再等比例放大至最大通道 255，保持色相比較容易辨認。這是明確新增的本模組衍生 shader，並非宣稱來源原件本來就有這些數值。所有印記固定 fill persistent/full alpha=0，edge persistent/full alpha=1；初始 full-alpha time=0.05 秒，之後 persistent alpha 仍為 1；fade-in/out=0、pulse=0，沒有週期性淡出；edge falloff=1。','',
'新記錄 flags=`0x00000408`（No Particle Shader + No Weapons），不設 No Membrane、Affect Skin Only 或 Edge Inverse；持續粒子數=0、Addon Models=0、Ambient Sound=0。印記仍由既有 MGEF `FX Persist` 綁住 8 秒，Water 沿用控制器原本的 10 秒設定；自然到期、切換、終焉與 dispel 的遊戲流程完全不變。不新增 ARTO，原本開印閃現與 Charge 音效保留。','',
'數值欄格式：**Fp/Ep；Ft/Et；Ffull/Efull**，分別是 fill/edge 的持續 alpha、full-alpha 秒數、full-alpha ratio。Flags 是 EFSH DATA 的完整 flags，含粒子旗標；新記錄一律 `0x408`，舊表 `0x10000`/`0x20000` 分別表示粒子 grayscale color/alpha，`0x8` 表示無粒子。完整粒子時間、數量、壽命、旗標與來源在 `build/fx-visibility.json`。','',
'| 元素 | Mark 前（本插件 EDID） | 前：Fp/Ep；Ft/Et；Ffull/Efull | 前 edge RGB／flags | Mark 後（本插件 EDID） | 後：Fp/Ep；Ft/Et；Ffull/Efull | 後 edge RGB／flags |',
'|---|---|---|---|---|---|---|']
for r in new['elements']:
 o=old_rows[r['element']];a=candidates[o['hit_shader']];z=derived[r['mark_shader']]
 lines.append(f"| {r['zh']} `{r['element']}` | `{o['hit_shader']}` | {nums(a)} | {rgb(a)} / `{a['flags_hex']}` | `{r['mark_shader']}` | {nums(z)} | {rgb(z)} / `{z['flags_hex']}` |")
lines+=['','| 元素 | 新印記色彩取自（selector） | 原 RGB → 新 RGB | 新 FormID |','|---|---|---|---|']
# Use the same audited explicit mapping as the product.
import sys
sys.path.insert(0,str(root.resolve()))
import build_v03 as b
for r in new['elements']:
 d=derived[r['mark_shader']]
 lines.append(f"| {r['zh']} `{r['element']}` | `{b.FX_EDGE_COLORS[r['element']].replace('|','&#124;')}` | {','.join(map(str,d['colour_source_rgb']))} → {rgb(d)} | `0x{d['id']}` |")
lines+=['','### 冰封、破魔印、沉默','',
'| 狀態／宿主 | 前 | 後 | 持續性與清除 |','|---|---|---|---|',
'| 冰封／`ESSB_StatusHostEffect` + `ESSBStatus` | 只有凍結量表及減速，沒有專屬 shader，無 EFSH 數值可檢查 | `ESSBFX_Status_Frozen` `0x0030FA`；Fp/Ep=0.18/1、Ft/Et=0.05/0.05、Ffull/Efull=0.18/1；RGB=255,255,255；flags=0x408；ambient=0 | `Freeze >= 5` 開啟淡白膜＋白邊；與僅青藍邊的 Frost 印記區分。AddStack／SetStack／SetFrozen／ClearStack／ImportState 與既有 Tick 同步；不新增 timer。到期、清除、死亡、Dispel、OnEffectFinish、換宿都 Stop；舊宿主延遲結束不會 Stop 新宿主的 shader。 |']
w=candidates['ESSBFX__BL_EffectShaderWhiteShockGlow'];a=derived['ESSBFX_Status_White']
for label,host in [('破魔印','ESSB_ManaBreakEffect'),('沉默','ESSB_SilenceEffect')]:
 lines.append(f"| {label}／`{host}` | `ESSBFX__BL_EffectShaderWhiteShockGlow`；{nums(w)}；RGB={rgb(w)}；flags={w['flags_hex']}。原件不是零 alpha，但 fill=5 明顯高於 edge=0.45，改成較易讀輪廓 | `ESSBFX_Status_White` `0x0030F9`；{nums(a)}；RGB={rgb(a)}；flags={a['flags_hex']}；ambient=0 | 保留原 MGEF FX Persist 與法術時長；真實傷害仍用原白光，不連帶修改。 |")
lines+=['','冰封使用一個 `EffectShader` property 與 Play/Stop 狀態轉換，沒有 `Utility.Wait`、新增更新迴圈、`Spell.Cast` 或敵人 health `DamageActorValue`。原有 AME 結束／換宿防護保留。既有存檔中已存活的舊宿主不保證即時取得新增 property；新宿主或既有 30 秒換宿後會使用新綁定，這部分仍需實機確認。','',
'### 如何換 shader 與重建','',
'`settings.json` 的 `fx_aura` 與 `fx_mark` 都是英文元素名 → `Plugin|EDID` 的 map；省略 map 或其中某個元素會使用預設。插件名指來源 plugin，EDID 用來源原名；本模組新增 shader 則使用 `Elements Spellblade.esp|ESSBFX_Mark_<Element>`。','',
'例如只將雷電印記改用原來源 shader，修改既有 map 中這一項（其餘項目保留）：','',
'```json','"fx_mark": {','  "Lightning": "StormCalling.esl|_SC_ShockStormFXShader"','}','```','',
'形態例：`"Frost": "Phenderix Elements.esp|ZZShader_FrostForm"` 放在 `fx_aura`。候選來源可查 `build/fx-catalog.json`；已匯出 shader 的 persistence 數值查 `build/fx-visibility.json`。支持 `fx_extract.SOURCES` 清單內的來源插件，不接受缺失來源或任意裸 EDID。','',
'在 `D:\\Game\\Other\\SKSE\\.codex\\elemental-spellblade` 執行：','',
'```powershell','python build_v03.py','```','',
'建置會拒絕未知元素、非 map／非字串、缺失或模糊選擇器、非 EFSH 記錄；`fx_mark` 另外要求 DATA Flags 明確、膜層啟用、非 skin-only／inverse edge、edge persistent 減 pulse 至少 0.35、full edge alpha > 0、RGB 最大通道至少 80。這是保守資料門檻，不是遊戲畫面保證。未通過的霧效不能直接當 `fx_mark`；需要時可繼續作命中特效。自訂選擇器直接綁定來源複製件，**不會自動正規化其顏色或 alpha**；只有預設 `ESSBFX_Mark_*` 是本輪衍生版。','',
'成功後檢查 `build/fx-bindings.json` 的 `aura_source`、`mark_source`、`mark_shader`、`mark_visibility`。新來源由既有 `fx_extract.export` 路徑匯入，ID 固定沿用 snapshot／既有 manifest，新增一律超過目前最高 FX ID；已匯入但改選後不用的 FX 仍保留。不要刪除 `build/v03-formids.json` 與既有快照，否則未來新增的自訂 FX 無法保留其歷史配置。重建只產生 package，不自動部署到 MO2 或遊戲；退出遊戲後由使用者更新原 MO2 模組。','',
'### 完整驗收與保留邊界','',
'- `python build_v03.py`：exit 0，完整輸出 `build/fix3-build.log`。17 scripts 均 `0 error(s), 0 warning(s)`；總記錄 3891，READBACK records == manifest。','- masters 僅 `[\'Skyrim.esm\']`；來源 closure 中的 Dawnguard／Dragonborn 參照仍沿用原本 drop/null 處理，並未新增 masters。','- CSF 13/13；LAYOUT 13/13、最小間距 0.95；DELIVERY ok；PLAN COVERAGE 541 rows、0 unmapped；FX ok（原 238 + 衍生 13 = 251；EFSH 79）。','- `.codex/pre-fix3-snapshot/v03-formids.json` 的 3878 筆全部保留，`ESSB_DebugLevel=0x000811`；只追加 `0x0030EE–0x0030FA` 共 13 筆 EFSH。`build/fix3-readback.json` 記錄完整比對。','- `build/fix3_regression.py` 7/7：獨立 EFSH offset、ESP 位元組保留、冰封門檻／時長／換宿／死亡／消除／結束、自訂 FX 追加與錯誤設定拒絕；前輪 `fix2_regression.py` 11/11、`fix2_prior_regression.py` 23/23 亦通過。Papyrus 行為測試是實際函式內容搭配 native mocks，並非 Skyrim runtime。','- 3878 個既有記錄中只有 24 筆 payload 有改變：10 aura MGEF（水原本即 Phenderix）、11 mark MGEF、2 白光狀態 MGEF、1 status host VMAD。238 個既有 FX、全部武器光／命中／反應效果、其餘遊戲資料位元組相同。','- settings、build_v03.py 與 ESSBStatus.psc 保留原 UTF-8／行尾；本文件以原檔位元組為前綴僅追加。`fx_extract.py`、規劃、review、`.strategic-advance/**` 未改。未複製 nif/dds/wav、未使用網路、未寫 MO2／SkyrimSE。','- 原有唯一 PLAN COVERAGE DEFERRED「穩步」CK entry-point 實機確認保持原狀，與本輪特效變更無關。','',
'| 狀態 | 項目 | 結果 |','|---|---|---|',
'| FIXED | 11 元素形態光環 | 全部改回 Phenderix 原始 form shader；`fx_aura` 可設定；借用 FX 保留。 |',
'| FIXED | 11 元素印記 | 獨立持續元素色邊緣；`fx_mark` 可設定；8 秒／水 10 秒及命中特效保留。 |',
'| FIXED | 冰封、破魔印、沉默 | 冰封依狀態啟停；破魔印／沉默改持續白邊；數值與生命週期檢查通過。 |',
'| FIXED | FormID／前兩輪成果 | 舊 3878 筆零變動；追加 13 筆；原 FX 與武器／命中不變；前輪回歸全通過。 |',
'| FIXED | 完整建置與文件 | exit 0；17 scripts 0 errors；全部既有檢查 ok；逐元素 EFSH 表、設定方法、進度紀錄已完成。 |',
'| NOT FIXED | 修正後遊戲內視覺驗收 | 尚未實機重測；不同光線／ENB、雙印記與其他 shader 同時顯示、舊存檔宿主更新仍待確認。未安裝至 MO2。 |','']
path=root/'實作紀錄.md';before=path.read_bytes()
assert b'fix round 3\xef\xbc\x88' not in before
with path.open('ab') as fp:fp.write('\r\n'.join(lines).encode('utf-8'))
assert path.read_bytes().startswith((root/'build/fix3-before/實作紀錄.md').read_bytes())
# Replace the exploratory report with authoritative, correctly decoded source fields.
(root/'build/fix3-efsh-initial.json').write_text(json.dumps(audit['candidates'],ensure_ascii=False,indent=2),encoding='utf-8')
ledger='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>fix round 3（特效回饋）</title><style>body{font:16px system-ui;background:#f4f2eb;color:#27332f;max-width:1100px;margin:40px auto;padding:24px}table{border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #bbb;text-align:left}code{font-size:13px}</style><h1>fix round 3（特效回饋）</h1><p>完成建置與資料／腳本檢查。未部署，未進入遊戲實測。</p><table><tr><th>項目</th><th>狀態</th><th>證據</th></tr><tr><td>形態</td><td>FIXED 11/11</td><td>Phenderix 原始 form shader；fx_aura map；238 舊 FX byte-identical</td></tr><tr><td>印記／狀態</td><td>FIXED</td><td>66 來源 EFSH 審核；13 衍生 shader（0030EE–0030FA）；fx_mark map；冰封生命週期測試</td></tr><tr><td>建置</td><td>FIXED exit 0</td><td>17 scripts 0 errors；3891 records；CSF 13/13；DELIVERY、LAYOUT、COVERAGE、FX 全 ok</td></tr><tr><td>FormID／回歸</td><td>FIXED</td><td>3878 existing unchanged；本輪 7/7 + 前輪 11/11 + 23/23</td></tr><tr><td>實機視覺</td><td>NOT FIXED／待驗收</td><td>未寫 MO2／SkyrimSE，未操作遊戲</td></tr></table><p><a href="../實作紀錄.md">逐元素表與更換 shader 方法</a> · <a href="../build/fx-visibility.json">EFSH 數值</a> · <a href="../build/fix3-build.log">完整建置 log</a> · <a href="../build/fix3-readback.json">FormID 與 readback</a></p></html>'''
(root/'.codex/impl-fix-round3.html').write_bytes(ledger.encode('utf-8'))
print('Appended implementation record; original bytes preserved. Ledger complete.')

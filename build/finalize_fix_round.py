"""Append the authorized implementation entry and finalize the progress signal."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
items_path = root / 'build/fix-round-items.json'
items = json.loads(items_path.read_text(encoding='utf8'))
for row in items:
    row['change'] = row['change'].replace('總伤', '總傷').replace('替换', '替換')
    if row['id'] == 'P2：經驗曲線手感':
        row['file'] = 'settings.json；src/ESSBTrees.psc；build_v03.py'
        row['function'] = 'Award / XPBudget；csf_config'
assert len(items) == 45 and sum(r['status'] == 'FIXED' for r in items) == 40
assert len({r['id'] for r in items}) == 45
items_path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
audit = json.loads((root / 'build/fix-round-audit.json').read_text(encoding='utf8'))
delivery = json.loads((root / 'build/fix-round-delivery.json').read_text(encoding='utf8'))
baseline = json.loads((root / 'build/fix-round-baseline.json').read_text(encoding='utf8'))
log_path = root / '實作紀錄.md'
original = log_path.read_bytes()
assert hashlib.sha256(original).hexdigest() == baseline['files']['實作紀錄.md']['sha256'], 'Append once, to the unchanged original log only'
entry = '''

## 2026-09-17 22:13 Asia/Taipei — fix round（審查修正）

本輪依三個實體檔案中的四份審查修正：review-2026-09-17.md（commander 與 builder review）、review-astra-A.md、review-astra-B.md。先讀完整審查，再以未修改的 元素魔戰士規劃-v0.3.md 與 build/plan-tree-nodes.json 核對節點。A7/B4、A10/B8 各合併一次；B 的 P1-4 歸屬補充併入該項。40 個不重複修正項目均已完成；另將審查列出的五個 P2 實機／既有風險明列為 NOT FIXED，不把編譯成功當作遊戲驗證。

產品修改：src/ESSBController.psc、src/ESSBElem.psc、src/ESSBElem2.psc、src/ESSBElem3.psc、src/ESSBGuard.psc、src/ESSBNoForm.psc、src/ESSBReactions.psc、src/ESSBStatus.psc、src/ESSBTrees.psc、build_v03.py。所有 .psc 保持 UTF-8；未新增 import stub。settings.json、plan_coverage.py、plan_trees.py 未修改；本檔只追加。計畫、審查、fx_extract.py 保持原始 SHA-256；未寫入 .strategic-advance/、MO2 或 SkyrimSE，未存取網路。

### 建置與驗證

- campaign root 執行 `python build_v03.py`：最後一輪 exit 0；17 支出貨腳本全部編譯，0 errors、0 warnings。完整輸出：build/fix-round-build-final.log、build/v03-compile-results.json。
- ESP 回讀 masters == ['Skyrim.esm']；record_count == manifest == 3878；重複 FormID 0；未 ESL-flag。原有 3870 筆 EDID/FormID 配對全部保留，ESSB_DebugLevel 固定 0x000811，PERK EDID 集合不變。
- CSF 13/13 valid；495 nodes。plan coverage 541 列：540 IMPLEMENTED、1 原有 DEFERRED、0 unmapped、0 PENDING。既有 DEFERRED 是 ESSB_P_noform_0_0_B1「穩步」的原版格擋耐力進入點待實機確認，本輪未改設計或把它改標完成。
- SPEL SPIT 與每個引用 MGEF DATA 的 delivery 回讀全部相符：Contact (1) 71 支、Self (0) 49 支。敵方法術與同伴目標法術為 Contact；玩家法術為 Self。逐筆結果：build/fix-round-delivery.json。
- build/fix_round_regression.py：23 組測試通過，執行實際 Papyrus 函式／事件內容並替代原生與外部呼叫；涵蓋順序、快照、插層、世代交錯、去重、冷卻、重入、宿主緩衝、領域五跳及推拉。此為離線邏輯驗證，未執行 Skyrim 引擎。
- build/fix_round_audit.py：99 項檢查通過；包含保護檔案雜湊、FX 關鍵函式不變、既有 public function 名稱、禁用 API、UTF-8、陣列上限、FormID、產物與覆蓋率。報告：build/fix-round-audit.json。
- 建置自帶 420 處 Rank/Br 呼叫索引核對，0 out of range。FX 238 筆複製仍在，effect shader／impact／sound／explosion 與 StartDomain、PushSyncStage 等既有 FX 邏輯保留；沒有增加 master。
- 測試工具初跑出現兩個 fixture 缺陷（切片失去 Length、缺 TreeOf 替身），修正後全數重跑通過；稽核曾誤納未出貨歷史 ESSBPlayerAlias.psc，已改核對出貨白名單並確認歷史檔完全未變。產品每輪完整建置均通過。

### 逐項修正表

| 項目 | 狀態 | 檔案 | 函式／位置 | 修改或未修正原因 |
|---|---|---|---|---|
'''
for row in items:
    entry += '| ' + ' | '.join(row[k].replace('|', '\\|') for k in ('id', 'status', 'file', 'function', 'change')) + ' |\n'
entry += '''
### 實作邊界與相容性

PushActorAway 的 force 使用正值吹走、以中心 reference 負值拉近；沿用原冷卻與免疫判定。吹上天先進入 ragdoll，單次更新延遲後確認 knock state 才施加一次向上 ApplyHavokImpulse；未進入 ragdoll 就不施加。未新增 Utility.Wait 迴圈、持續 RegisterForUpdate 或每幀輪詢。推力的引擎實際距離仍需實機量測。

傷害仍走自有法術 DoCombatSpellApply；處決直接走原 TrueSpell，不發 Spell.Cast 傷害事件、不直接扣敵人 Health。玩家過熱另分 Self 法術；同伴回復／強化另分 Contact 法術，避免共用同一 SPEL 的互斥投遞設定。

八槽登記表架構保留；新增逐槽換宿備份與 Actor／世代核對，超時可重試，不把資料備份隨交易解鎖刪除。宿主浮點匯出由 12 欄增至 17 欄，匯入保留舊 12 欄格式預設值；外部 public function 名称保持，新增參數提供預設或更新全部呼叫端。

### 新增記錄（原記錄不重編）

| 本地 FormID | EDID | 類型 |
|---|---|---|
'''
entry = entry.replace('名称', '名稱')
for edid, value in sorted(audit['new_records'].items(), key=lambda pair: pair[1]['id']):
    entry += f"| 0x{value['id']} | {edid} | {value['type']} |\n"
entry += '''
### P0-2 完整 SPEL／MGEF EDID 清單

以下列出所有已回讀法術，包含原已正確而保留的 Self 法術，避免只列簡稱而漏掉效果。Contact 的 71 支為本輪改為 Contact 或新增 Contact；Self 中 ESSB_Util_*、ESSB_InheritSpell 為投遞修正，ESSB_OverheatSelfSpell 為新增，其餘保留 Self。每列所有 MGEF 與 SPEL 的 delivery 都相同。

| SPEL EDID | delivery（SPIT／DATA） | MGEF EDID |
|---|---|---|
'''
for row in sorted(delivery['spells'], key=lambda r: (r['delivery'], r['spell'])):
    value = 'Contact (1)' if row['delivery'] == 1 else 'Self (0)'
    entry += f"| {row['spell']} | {value} | {'、'.join(row['effects'])} |\n"
entry += '\n產物位於 package/Elements Spellblade/。本輪未安裝至 MO2、未啟動遊戲；P2 表列的五项界限保留。進度訊號位於 .codex/impl-fix-round.html。\n'.replace('五项', '五項')
with log_path.open('ab') as handle:
    handle.write(entry.encode('utf8'))
assert log_path.read_bytes()[:len(original)] == original

ledger = root / '.codex/impl-fix-round.html'
page = ledger.read_text(encoding='utf8')
import re
page = re.sub(r'<p id="stage">.*?</p>', '<p id="stage">目前階段：完成。40 項 FIXED；五項 P2 依技術原因保留 NOT FIXED。末輪建置 exit 0，17 支腳本 0 errors／0 warnings，23 組回歸與 99 項稽核通過；實作紀錄已 append-only 追加。</p>', page)
page = page.replace('五项', '五項')
page = page.replace('進行中；產品尚未編輯', '完成；產品編輯前已保存基準')
page = page.replace('待保存 FormID、FX、受保護檔案雜湊及原始檔基準。', 'build/fix-round-baseline.json 保存 3870 筆原記錄、產品原文與受保護檔案雜湊。')
page = page.replace('待最終建置、FormID／保護檔案／FX 稽核及 append-only 紀錄；未進遊戲。', '末輪建置 exit 0；3878/3878 records、0 重複、masters 僅 Skyrim.esm、CSF 13/13、0 unmapped／PENDING；既有 FormID／FX／保護檔案通過稽核，實作紀錄只追加。未進遊戲。')
page = page.replace('</html>', '<p>最終檔案：9 支 src/*.psc、build_v03.py、實作紀錄.md（只追加），以及授權的 build/**、package/Elements Spellblade/** 與此 ledger。剩餘產品修正：0；剩餘實機／保留風險：5，詳見實作紀錄。</p></html>')
ledger.write_text(page, encoding='utf8')
print(f'APPENDED {len(entry.encode("utf8"))} bytes; original {len(original)} bytes preserved exactly; 40 FIXED + 5 NOT FIXED; delivery {len(delivery["spells"])} rows')

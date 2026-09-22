from pathlib import Path
import json,hashlib,zipfile,html,re
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'build/fix16-check.json').read_text(encoding='utf8'))
log=(ROOT/'build/fix16-build-final.log').read_text(encoding='utf8')
required=['READBACK ok:',"masters=['Skyrim.esm'] records=3941 manifest=3941",'CSF ok: files=13 valid=13',
          'DELIVERY ok:','LAYOUT ok:','DOT ok:','MCM ok:','MCM DEFAULTS ok:','SCHEMA ok:',
          'FIX10 ok:','FIX11 RANGED ok:','FIX12 ok:','FIX13 ok:','FIX14 ATTRIBUTION ok:',
          'FIX15 ok:','FIX16 ok:','PLAN COVERAGE ok: rows=542 unmapped=0']
for line in required:assert line in log,line
compiler=json.loads((ROOT/'build/v03-compile-results.json').read_text(encoding='utf8'))['results']
assert len(compiler)==19 and all(r['exit_code']==0 for r in compiler)
assert len(report['negative_controls'])==len(report['cases'])==9
notes='''

## 2026-09-19 09:37 Asia/Taipei — fix round 16：修正 round 15 獨立審查

工作清單：完整讀取 `review-fable-2026-09-19-r15.md`，依使用者指定 A1–A5、B1.2、B1.6、B1.9、B1.10 次序完成。沒有修改規劃、審查報告、任何 pre/post snapshot 或 `.strategic-advance/`；不對指揮官 ledger 的 hash 作斷言。沒有連網，沒有写入 MO2 或 SkyrimSE。

| 項目 | 實作與離線證據 |
|---|---|
| A1 屍體融斷 | `OnFormClosed` 遇死者先 `CaptureDeath`、`ClearSlot`，不計入 burst。`FinishMark` 在解除印記前捕獲死亡，死者只 detach／dispel；`ESSBReactions.End` 入口亦拒絕死者。測試確認沒有終焉 XP、End、FX 或回流計數，死亡快照仍存在。|
| A2 神佑殘留 | `RefreshDivineProtection`、`RefreshAbilities` 加 `IsCurrentController()` 守衛；三個 ESSBTrees 呼叫點也要求 `Controller.IsOperational()`。保留每次 `Setup` 的無條件 `EndDeferredKill()`。MCM 平衡頁新增「解除神佑保護」：先確認，解析目前世代，停用模組、清保護、disarm、`EndDeferredKill`、通知；不要求 Ready／IsOperational，因此 StateBroken 亦可解除。停用是防止下一次 tick／戰鬥／Setup 重新武裝；一般頁手動重新啟用可恢復功能。取消完全不動狀態。|
| A3 pending 冰封 | `SetFrozen(0.0, deadline)` 儲存綁定時刻及剩餘秒數，已過期時保留原到期點；不再把未來 deadline 當起點，不再重複套用 MultDuration。測試綁定 101、期限 103，以及 110 才綁定；換宿不會把死咒／浮空改成 now+1。|
| A4 領域 | 三格領域各保留最多六個居民（沿用最近五敵＋玩家），保存首次觀測與已結算時間。每目標從自己進入紀錄結算，首見者不追領舊帳；觀測到離開／掉出最近五名後清除，重入重新起算。34 秒晚 tick 測試：原居民 34 秒，新居民 0 秒，下一秒各 1；毒層與玩家回血／回耐同樣隔離。領域重開與讀檔會清居民紀錄。|
| A5 命中成本 | 無形態命中只有持有斷咒才呼叫 `IsCasting`／`RecentCast`；三段同調只有持有神佑才呼叫 `RefreshDivineProtection`。GetStack／AddStack／SetStack／AddAstral 先判斷未滿一秒再呼叫 Holder.IsDead；已到結算秒仍跑 Tick。OpenBoost／EndBoost 為零時先回傳，省下無效 SecondsLeft 呼叫。|
| B1.2 連殺 | 新增 `HitForm`，在有效武器命中入口與 sneak／power／weapon 一起保存；連殺使用這份形態，而非 killingElement 或擊殺結算當下的形態。纯物理無印一刀、風形態潛行致死也成立；切成黑暗後才收到擊殺仍成立，反方向不成立。非潛行舊命中不先消耗 `HitKillDone`，因此 kill→fatal hit 逆序仍可兌現。|
| B1.6 防護視窗 | 九種短期防護改由 PERK 的 HasMagicEffect 條件讀取獨立原生限時 MGEF（順轉、安全閥、冰晶、殘影、神佑、破護、影身、預知、星光）。過期由引擎處理，不等待 AME／控制器腳本 tick；不新增更新事件或 polling。鏡射保留供其他腳本／診斷使用，GetGuardWindLeft／GetGuardDarkLeft 讀取時也更新鏡射。ESP 回讀核對九個 PERK 條件、MGEF 無 VMAD、有限 duration、Self delivery。|
| B1.9 火葬／亡魂 | 不再為所有爆燃／死咒開三秒窗口。`ApplyDamage` 算出實際交付的 level／base／target-scaled magnitude 後，在 native 傷害前以 HP 預測致死；只有預期致死才保存 -1 claim。獎勵保留原基準 amount，不重複放大。未致死 20/100 不會兌現兩秒後的無關武器擊殺；預期致死 20/20 即使 7／34 秒後 CaptureDeath→ClearSlot→OnKillEvent 仍只兌現一次。一般元素歸屬的 `kill_attribution_seconds` 保持原用途與值。|
| B1.10 斷咒 | 持有節點時，在命中回呼入口先保存施法狀態，再處理傷害；後續不重新讀動畫。未持有節點不支付施法查詢成本；事件晚七秒且施法已結束時，結果明確為 false。|

### 指定偏離、時間語意與實機界線

1. 連殺明示偏離 round 14 的「never guess from the current form」：連殺是風形態分支，使用已記錄的命中處理時形態 `HitForm`，不是在擊殺结算時猜形態，也不改寫其他擊殺效果的元素歸屬。PO3 未提供原生碰撞時的形態／施法時間戳，仍接受命中事件處理本身 0–7 秒的延遲；沒有宣稱重建 VM 尚未收到的事實。
2. 領域採保守的首次觀測時間。無額外 polling／原生進出事件，不能還原兩次觀測間完整移動軌跡；首見與已觀測到離開後重入的目標不會吃歷史整批傷害，未觀測到的離開再返回仍無法辨識。最近五名名額更換也重新起算，可能少給，但不把新選入者當成全程在場。
3. 防護效果的開始仍可能因 VM 排程晚發生；一旦 native 成功套用，有限 active-effect duration 由引擎到期，PERK 不讀過期的腳本 mirror。遊戲暫停／選單等引擎 active-effect 時鐘行為與效能、HasMagicEffect 實際到期行為尚未進遊戲確認，離線 native mock 只證明接線與期限模型。
4. 火葬／亡魂採使用者指定的「傷害前 HP 預測致死」，並納入本模組實際交付倍率。這不等於可觀測原生最後傷害封包；外部抗性、傷害替代／必要角色、其他模組干預可能讓預測與引擎結果不同。離線證明已消除普遍的非致死三秒窗口，與晚捕獲造成的窗口漏兌現；不宣稱外部模組下的引擎歸因已驗證。
5. 神佑的 ≤0 HP 等待回呼、StartDeferredKill 是否旗標／計數、是否持久化到 actor save change、和其他死亡替代模組互動，仍須 Skyrim SE 1.5.97 實機確認。卸載前請以 MCM「解除神佑保護」解除並存檔；不能在移除腳本後保證補救舊的 actor 狀態。

### Schema、建置與交付

- `state_schema_version` **5 → 6**：需要保存三領域各目標的 `DomainResident: Actor[18]`、`DomainResidentAt: Float[18]`，以及 `HitForm: Int[8]`。這三個持久 member 無法僅用區域變數跨 tick／事件保存；沒有借用仍在使用中的其他狀態陣列，依 round-9 規則新世代，沒有手改同版本 signature。新陣列纳入配置失敗檢查。
- 唯一既有 FormID 變動：`ESSB_MainQuest` **0x006006 → 0x006008**、`ESSB_MCMQuest` **0x006007 → 0x006009**；舊 ID 保留為 schema 5 inert stubs。其餘既有記錄身份全部與 `.codex/pre-fix16-snapshot/v03-formids.json` 相同，`ESSB_DebugLevel` **0x000811**。另新增九對防護 MGEF／SPEL，使用未占用的 **0x005170–0x005181**；masters 仍僅 `Skyrim.esm`。
- 親自執行 **`python build_v03.py`，exit 0**，完整輸出 `build/fix16-build-final.log`。19 支腳本全部 0 errors；READBACK **3941 == manifest 3941**；CSF **13/13**；DELIVERY、LAYOUT、DOT、MCM、MCM DEFAULTS、SCHEMA、FIX10–FIX15 全 ok；PLAN COVERAGE **542 rows、0 unmapped**。既有 optional deferred「穩步」不變。
- 新 **FIX16 ok**：九項實際原始碼離線回歸，每項皆在唯讀 pre-fix16 失敗、修正後通過。報告 `build/fix16-check.json`；source diff `build/fix16.patch`。既有 verifier 只為新增記錄、schema、MCM action、命中形態事實及被本輪明確替換的錯誤預期調整；沒有略過既有完整檢查，沒有寫舊進度帳。
- 相同代表命中：**116 scripted + 50 native = 166 → 115 scripted + 50 native = 165**，2 次 identity，L0 零 logging／字串拼接。另在實際 IsCasting body 的無節點分支，施法 native **10 → 0**；十次同秒 GetStack：**50 scripted + 40 native → 10 scripted + 10 native**，Holder.IsDead **10 → 0**。這些是明示 native mocks 的呼叫數，不是遊戲耗時。
- 原始編碼、BOM、換行保留；`build_v03.py` CRLF，`state-schema.lock.json` 升版時亦保留 CRLF；本紀錄只追加。未新增 Utility.Wait loops、非 single RegisterForUpdate 或 per-frame polling。

交付：`package/Elements Spellblade/`；`build/Elements-Spellblade-fix16.zip`。**未部署至 MO2，未進遊戲驗證。**
'''
p=ROOT/'實作紀錄.md';raw=p.read_bytes();nl='\r\n' if b'\r\n' in raw else '\n'
assert b'fix round 16' not in raw[-500:]  # deliberate one-shot delivery step
with p.open('ab') as f:f.write(notes.replace('\n',nl).encode('utf8'))
labels=['A1 屍體融斷','A2 神佑解除與世代守衛','A3 pending 冰封','A4 領域每目標結算','A5 命中成本','B1.2 連殺命中形態','B1.6 PERK 視窗','B1.9 預測致死','B1.10 斷咒延遲']
rows=''.join('<tr><td>'+label+'</td><td>修正完成；pre-fix16 失敗 → 修正版通過</td><td><code>'+html.escape(str(report['cases'][key]))+'</code></td></tr>' for label,key in zip(labels,report['cases']))
page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Round 16 完成</title><style>body{font:16px system-ui;margin:3rem auto;max-width:1150px;color:#192b34;background:#faf8f2}td,th{padding:12px;text-align:left;border-bottom:1px solid #c8d6d8}code{font-size:13px}a{color:#075f78}</style><h1>Round 16：修正與驗證完成</h1><p>依 review-fable-2026-09-19-r15.md 全文與指定 A/B 順序實作。未連網，未部署，未進遊戲。</p><p>完整 python build_v03.py exit 0；19 腳本成功；3941 records == manifest；九項負向對照與修正後回歸全部通過；代表命中 166 → 165 calls。</p><table><tr><th>項目</th><th>狀態</th><th>測試證據</th></tr>'''+rows+'''</table><p>Schema 5 → 6：新增逐目標領域時間、命中形態三個持久陣列。僅兩個任務既有 FormID 遷移；DebugLevel 0x000811。新增九對原生期限防護 MGEF/SPEL。</p><p>連殺採已記錄的命中處理時形態；斷咒接受 VM 事件延遲。領域無法重建未觀測的往返移動；預測致死仍受引擎抗性／外部模組影響。原生效果到期與 deferred-kill 存檔行為尚須實機驗證。</p><p><a href="../build/Elements-Spellblade-fix16.zip">完整封裝</a> · <a href="../build/fix16-build-final.log">建置輸出</a> · <a href="../build/fix16-check.json">回歸報告</a> · <a href="../實作紀錄.md">實作紀錄與取捨</a></p></html>'''
(ROOT/'.codex/impl-fix-round16.html').write_text(page,encoding='utf8',newline='\n')
pkg=ROOT/'package/Elements Spellblade';archive=ROOT/'build/Elements-Spellblade-fix16.zip'
files=sorted(p for p in pkg.rglob('*') if p.is_file())
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in files:z.write(p,p.relative_to(pkg).as_posix())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for p in files:assert z.read(p.relative_to(pkg).as_posix())==p.read_bytes()
before=json.loads((ROOT/'build/fix16-before.json').read_text(encoding='utf8'))
prefix=before['實作紀錄.md'];raw=(ROOT/'實作紀錄.md').read_bytes()
assert hashlib.sha256(raw[:prefix['length']]).hexdigest()==prefix['sha256']
delivery=dict(build_command='python build_v03.py',build_exit=0,check_lines=required,compiled=19,
 records=report['records'],runtime_tested=False,installed=False,files=len(files),archive=str(archive),
 archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
 package_sha256={p.relative_to(pkg).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
 regression='9 pre-fix failures -> 9 pass',hit_calls_before=166,hit_calls_after=165,log_append_only=True)
(ROOT/'build/fix16-delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in delivery.items() if k not in ('package_sha256','check_lines','records')},ensure_ascii=False,indent=2))

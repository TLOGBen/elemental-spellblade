"""Append the round15 record and package already verified local outputs only."""
from pathlib import Path
import json,hashlib,zipfile,difflib
R=Path(__file__).resolve().parents[1]
note='''

## fix round 15（review-fable：實戰靜默不觸發機制）

權威清單 `review-fable-2026-09-19.md` 已完整讀取；其來源為 pre-fix14。以下先核對已安裝 round 14，再列本輪修正。原規劃、review、pre-fix 快照及 `.strategic-advance/**` 未改寫。進度頁 `.codex/impl-fix-round15.html` 先建立，再逐項更新。

| 項目 | round 14 涵蓋 | 本輪結果與接線 |
|---|---|---|
| 1 死咒／饕餮／處刑／亡魂 | 未涵蓋。只有死亡歸屬快照，沒有保留死咒結算。 | FIXED：`ESSBStatus.ResolveDeathCurse` 先清除一次性狀態，再處理結果。活目標依真實期限结算；死亡的宿主／控制器死亡捕獲／清格前結算固定項與玩家收益。pending 死咒也在清格前處理。屍體不補傷害、不處刑；亡魂只由實際擊殺事件的死咒來源觸發。 |
| 2 致命潛行、連殺、奇襲、風勢 | 部分涵蓋。round 14 統一連殺的元素歸屬，但 `LastHitSneak` 仍在死者拒絕後。 | FIXED：有效武器、隊友等過濾後，先保存每目標的 sneak／power／weapon，再拒絕死者傷害流程。擊殺讀目標自己的事實；`SettledElement` 保留已凍結歸屬，支援 kill callback 先於 weapon callback。致命潛行補滿風勢、消耗上一輪連殺與處理附近活敵奇襲；不向屍體施加 proc、開印或吹飛。活目標風附傷 ×3／暗風 ×5 及連殺 ×2 原路保留。 |
| 3 反擊 | 未涵蓋。實作紀錄舊稱 ApplyProc ×1.3，來源沒有對應實作。 | FIXED：純武藝所在的 `OnNoFormHit` 消耗 3 秒期限，將該次 baseline 與 `OnMartialHit` 的真傷乘 1.3；不再假設無形態分支能走元素 ApplyProc。第二擊或超時均無加成。 |
| 4 神佑 | 未涵蓋。傷害後 Health <=1 判斷救不到致命傷。 | FIXED：`RefreshDivineProtection` 在神聖分支、同調三段、Enabled、形態與未使用條件成立時，事前 `StartDeferredKill()`。致命傷後先鎖本場已用、開短暫神佑、清負面、以 `RestoreActorValue` 恢復到實際 1 HP，最後 `EndDeferredKill()`。不合資格／停用／失敗關閉會解除自己持有的保護；脫戰沿原 tick 規則重置。 |
| 5 切換雷終焉 0 電荷 | 未涵蓋。 | FIXED：離開雷形態前保存 `SwitchCharge`，自身資源仍依 2.3 歸零；reason 0 終焉一次取走此快照。放電、過載終焉、雷殛與餘電使用同份電荷值。`PendingDischarge` 現在保存實際電荷，後續開印不再讀已歸零的 SelfCharge。 |
| 6 tick 秒數與真實時間混用 | 未涵蓋。round 12 修正排程與跨程序時鐘，仍保留 tick 計數。 | FIXED：所有 `TickTimers`、OpenBoost／EndBoost、浮空、死咒、催毒、星鎖、領域、化身、雷雨充電改成真實時間期限；電荷衰減按已流逝秒數補算。血毒與星痕仍使用固定小型桶，但 `RingClock` 按真實經過秒數推进；一個晚 tick 有界掃過到期桶，先累計應結算的 layer-seconds／星痕再移除。催毒倍率按每段是否在期限內積分。熔身及領域依期限內經過時間結算，不再每個 callback 當一秒。讀取／加入狀態前可結算已到期工作，既有排程仍為一秒 single update；沒有新增輪詢或 Wait。 |
| 7 擊殺層數與宿主消失 | 部分涵蓋。round 14 凍結元素並保護 mark-finish 的歸屬，但未保存 curse。 | FIXED：凍結 freeze／bleed／poison／curse／heat／holy，`ESSBElem3.OnKill` 使用傳入 curse，不再死後現讀。`OnStatusFinish` 在解除註冊前捕獲死亡；StatusHost 與 11 個 MarkEffect 加 No Death Dispel，死亡移除不再冒充自然終焉。其他 MGEF 不擴大套用此旗標。 |
| 8 熔斷 | 未涵蓋。 | FIXED：`EndFire` 接收 aiReason，只有 reason 1 且 `KeepHeatOnBurst` 才保留熱度；切換與過期保持原消耗規則，猛爆的例外也保留。 |
| 9 火葬／亡魂依即時 HP 判殺 | 部分涵蓋。round 14 改善一般傷害歸屬，但這兩個效果仍在施法返回後立刻讀 HP。 | FIXED：爆燃／死咒傷害前記錄目標、原因、量與期限；`OnKillEvent` 兌現一次火葬／亡魂。沒有以 ApplyDamage 返回後 HP <=0 判殺。來源過期不兌現，同目標新的來源取代舊來源，死亡快照捕獲有效來源後保留到延遲的 kill callback。一般 `ApplyTrackedDamage` 的 round-14「最近有效元素傷害 → 實印 → 0」仍保留，未改為目前形態歸屬。 |
| 10 斷咒判斷過晚 | 未涵蓋。round 13 修正 IsCasting API，但仍在破魔傷害處理後查詢。 | FIXED：`OnNoFormHit` 入口、任何傷害／開印之前保存施法狀態，再以參數傳入 `OnManaBreak`；同時使用穩定 alias 的左右手 SpellFire 動畫事件保存最近 1.5 秒施法事實。效果處理不再重新讀易失的 IsCasting。未施法不消耗冷卻的 round-13 規則保留。 |

### 明示的實作取捨與原生界線

1. 神佑使用本地 `vendor/imports/Actor.psc` 已宣告的原生 `StartDeferredKill`／`EndDeferredKill`（原生註解要求成對結束，否則角色不死）。這是先阻止死亡轉換，再讓既有 OnHit／tick 兌現的一次救命；不依赖「致命傷扣完後還能搶在死亡前補血」或 15% 血量閾值。實際 1.5.97 玩家死亡畫面、其他死亡替代模組是否共用 deferred-kill 狀態，未做實機測試；離線只證明資格、預先武裝、負 HP、一次／戰鬥及解除呼叫順序，沒有聲稱 native mock 等於引擎驗證。
2. 2.3／2.6 的衝突採使用者指定：雷的自身電荷立即清空，舊雷終焉取得「切換瞬間的電荷」一次性快照。其後不借用新形態累積的電荷。原規劃未修改。
3. 致命物理攻擊在 callback 抵達時已經死去，不能再以元素 proc 改寫那一刀傷害。本輪只補回仍有意義的玩家／附近活敵效果；連殺仍必須通過 round-14 元素歸屬。完全沒有近期元素傷害、也沒有實印的純物理一刀，歸屬仍為 0，不用目前風形態偽造擊殺元素。
4. 時限統一不會使堵塞的 Papyrus VM 準時醒來：工作仍可能晚執行，但一次醒來會結算到期內容，不把 34 秒當一秒。DoT 過期前應有的傷害以單次合計交付；領域使用結算時的幾何位置，沒有試圖重建卡頓期間的移動軌跡。固定血毒桶壽命與星痕的秒級桶精度保留，不新增逐層計時器。
5. 沿用 round-12 讀檔政策：重置控制器短期戰鬥視窗，清除相關 PERK mirror／連殺偵測保護；保留的宿主桶以新 uptime 起算，未結算的宿主／pending 有限動作改在載入後一秒到期。pending 死咒、催毒、浮空、冰封、星鎖保留请求時期限；同程序宿主搬移以 24 個 floats 保存精確 deadline，兩個 backup bank 各 96 floats，未超過 Papyrus 的 128 上限。
6. 火葬／亡魂原因視窗沿用 `kill_attribution_seconds=3.0`，不另藏一個硬編碼一秒門檻。它是近時來源證據，不是原生最後傷害封包證明；若回呼與最早死亡觀察本身都晚於視窗，仍可能無法還原引擎確切致死時間。斷咒的 snapshot 是腳本收到命中處理時的最早可用狀態，SpellFire 是補充證據；PO3 OnWeaponHit 沒有提供原生命中時的施法旗標／時間戳，故不聲稱能還原 VM 尚未收到事件前的瞬間。

### Schema、身份、驗證與交付

- `state_schema_version` **4 → 5**：新增目標命中事實／死亡來源陣列、神佑 latch、切換電荷；將剩餘整秒成員改成 Float deadline，並擴充宿主序列化 floats。這些是持久 member layout 變動，依 round-9 必須新世代。`state_schema.preflight()` 生成 lock，歷史 schema 4 的 signature 與快照來源交叉核對，沒有繞過同版 hash gate。
- `ESSB_MainQuest` **0x006004 → 0x006006**；`ESSB_MCMQuest` **0x006005 → 0x006007**。舊 schema 4 ID 保留為兩筆 inert stubs；全部舊非 Quest identity 不變，`ESSB_DebugLevel=0x000811`，masters 僅 `Skyrim.esm`。
- 親自執行完整 `python -B build_v03.py`，**exit 0**；`build/fix15-build-final.log` 保存輸出。19 支腳本全部成功、0 errors；READBACK **3921 records == 3921 manifest**；CSF **13/13**；DELIVERY、LAYOUT、DOT、MCM、MCM DEFAULTS、SCHEMA、FIX10–FIX14 全 ok；PLAN COVERAGE **542 rows，0 unmapped**。原「穩步」optional deferred 維持既有狀態。
- 新增 `FIX15 ok`：`build/fix15_verify.py` 實際執行 source bodies，**10 個案例在 `.codex/pre-fix15-snapshot/src` 失敗，在新來源全部通過**。包含死亡／清格／pending、致命 hit 與逆序 kill→hit、反擊消耗／超時、神佑一次性、切換快照／餘電、34 秒晚 tick 與 DoT／星痕／落地／死咒單次结算、swap／load deadline、死亡 curse 快照、熔斷、非同步傷害後擊殺、施法狀態在中途改變。ESP 回讀另外驗證 12 個 No Death Dispel 旗標及 Engaged 未擴大變動。細節在 `build/fix15-check.json`。
- 相同代表命中仍為 **116 scripted + 50 native = 166 calls**；2 次 identity、L0 零 logging／字串拼接。未撤銷 round 12 成本改善。沒有新增 Utility.Wait、RegisterForUpdate 或 per-frame polling。
- 舊 verifier 僅更新失效的固定 schema／FormID 範圍、序列化 layout、deadline clock fixture，以及神佑改接線的來源位置；原效果、失敗注入、數值、歸屬、MCM、native 邊界檢查仍執行。新增陣列也納入 FIX9 的配置失敗鎖定測試（105 項）。
- 原檔 BOM／換行保留，`build_v03.py` 保持 CRLF；本檔 append-only。沒有寫入 MO2、SkyrimSE，沒有網路操作或遊戲執行。

交付：`package/Elements Spellblade/`；封裝 `build/Elements-Spellblade-fix15.zip`。**未安裝，未進遊戲驗證。**
'''
p=R/'實作紀錄.md';raw=p.read_bytes();before=json.loads((R/'build/fix15-before.json').read_text(encoding='utf8'))['實作紀錄.md']
assert hashlib.sha256(raw[:before['length']]).hexdigest()==before['sha256']
assert b'## fix round 15' not in raw,'append must run only once'
nl='\r\n' if raw.count(b'\r\n')==raw.count(b'\n') else '\n'
with p.open('ab') as f:f.write(note.replace('\n',nl).encode('utf8'))
out=R/'package/Elements Spellblade';archive=R/'build/Elements-Spellblade-fix15.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for f in sorted(out.rglob('*')):
  if f.is_file():z.write(f,f.relative_to(out).as_posix())
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
proof=json.loads((R/'build/fix15-check.json').read_text(encoding='utf8'))
delivery=dict(package=str(out),archive=str(archive),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),esp_sha256=hashlib.sha256((out/'Elements Spellblade.esp').read_bytes()).hexdigest(),build_exit=0,records=3921,scripts=19,regressions=10,hit_calls=proof['cost']['total'],schema=5,runtime_tested=False,installed=False)
(R/'build/fix15-delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
patch=[]
for old in sorted((R/'.codex/pre-fix15-snapshot/src').glob('*.psc')):
 new=R/'src'/old.name
 patch.extend(difflib.unified_diff(old.read_text(encoding='utf8').splitlines(True),new.read_text(encoding='utf8').splitlines(True),fromfile='pre-fix15/src/'+old.name,tofile='src/'+old.name))
for n in ['build_v03.py','settings.json']:
 patch.extend(difflib.unified_diff((R/'.codex/pre-fix15-snapshot'/n).read_text(encoding='utf8').splitlines(True),(R/n).read_text(encoding='utf8').splitlines(True),fromfile='pre-fix15/'+n,tofile=n))
(R/'build/fix15.patch').write_text(''.join(patch),encoding='utf8')
p=R/'.codex/impl-fix-round15.html';s=p.read_text(encoding='utf8');s+='<p><strong>完整建置 exit 0</strong> · scripts 19/19 · FIX15 10/10 · records=manifest=3921 · CSF 13/13 · 0 unmapped · 166 calls · schema 5</p><p>詳細決策與限制：實作紀錄.md。交付：build/Elements-Spellblade-fix15.zip。未安裝／未實機測試。</p>';p.write_text(s,encoding='utf8')
print(json.dumps(delivery,ensure_ascii=False,indent=2))

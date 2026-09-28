# CHECKPOINT ｜ 2026-09-24

> 恢復入口。先讀這份，再讀 `元素魔戰士規劃-v0.4.md`。**所有給使用者的回覆一律繁體中文白話**（專案 CLAUDE.md 有寫）。

## 一句話
設計已完全定案（v0.4）；N1（DLL 命中附傷）已上線且實機探針全過；DLL 能力與 TrueHUD 都查證完成。**下一步：開 N2。**

## 真相來源
| 什麼 | 檔案 |
|---|---|
| 設計真相 | `元素魔戰士規劃-v0.4.md`（v0.3 原檔永不改；v0.3_alter 只當變更歷史） |
| 本輪玩法變更清單 | `design-v0.4-changes-2026-09-23.md` |
| 觸發分類 | `design-triggers-2026-09-23.md` |
| 玩法審查 | `design-fun-audit-2026-09-23.md` |
| 實作計畫（丙架構、N1～N6 切片） | `design-latency-2026-09-20.md`（4.11、第 6 節） |
| DLL 查證 | `build/native-verification.md`（N1）、`build/native-verification-2.md`（18 項） |
| TrueHUD 查證 | `build/truehud-verification.md` |
| N1 探針卡與實測結果 | `build/fix19-probes.md` |
| repo | https://github.com/TLOGBen/elemental-spellblade（main） |

## 目前部署在 MO2
- `MO2/mods/Elements Spellblade` = round 19b（N1）。使用者已勾主模組；探針包 `Elements Spellblade Round18 Probes` 應取消勾選。
- 回退：`.codex/mo2-installed-backup-20260923-204857`（round 18 entry-51 版）。

## 派工規則（使用者定）
- 實作與獨立審查：**Opus 5.5**（Agent 工具 model=opus）；純寫檔：Sonnet；Fable 額度幾乎用完，只在真正需要設計判斷時用；**不派 Astra**（快、極度防禦性，但做一半、程式難看、硬湊驗收）。
- 長任務走監督路徑：進度紀錄 `.codex/impl-<round>.html`、每 5 分鐘巡邏（Monitor）、做完派**另一個** Opus 做獨立審查，審過才部署。
- 部署只放檔案進 MO2/mods，不改 profile；遊戲開著不部署。
- 每輪驗收後提交並推送 GitHub；commit 結尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## 設計重點（v0.4 已寫入，這裡只列提示）
- 原則：機制有趣、數值看著辦、每個元素玩法不同。
- 三個自有資源池：超載（無元素）、護血（血）、蓄勁（土）；存在玩家身上自有效果的強度，不碰引擎 AV、不抬上限（引擎當前值不能超過上限）。顯示走 TrueHUD 自訂小工具，第一版純顏色。
- 無元素＝法殺；雷唯一暴擊；聖＝坦＋光傷＋聖裁（同目標第三擊）；星＝共鳴／闇星；暗＝幻覺＋死亡；水刻意平淡、最持久；防禦排序 物理 土＞冰＞聖、魔抗 聖＞冰、魔力分擔 無元素＞水。

## N2 開工要點（寫 briefing 時用）
- 內容（見 v0.4 第 9 節與 design-latency 第 6 節）：DLL 在命中當下算附傷強度（取代 Papyrus 事先寫強度＋十幾個重寫觸發點）；每刀隨機基礎傷害；雷真擲 1～25 取 N＝1＋電荷數次最大、暴擊（5%＋每格電荷 2%，×1.5／重擊 ×2.5）、形態內滿格重擊直接放電必暴；血位線性；命中吸血；（聖裁同目標三擊計數屬 N3，v0.4 為準）；無元素普攻吸魔＋小滅法（魔力 0 不觸發）、重擊滅法。
- **必避坑**：`CastSpellImmediate` 的強度覆寫會套到法術的每一個效果 → 需要不同強度的效果要拆成單效果法術各自施放（查證 NO 項）。
- 先清兩件小事：B 組測試的參數寫死成 1（右手）與 24（生命）而不是跟程式比；清掉 09-22 的舊證據檔、`native-verification.md:85` 改指 `build/fix19b-build.log`。
- 每秒執行點若 N2 用到：只能「背景計時執行緒每 tick AddTask 一次」，task 內自我重排會卡死遊戲。
- 舊狀態層（毒／星痕幽靈 bug）仍在，N3 才根除；N2 不碰狀態層。

## 完整版路線（2026-09-25 使用者定：等完整版才開新檔，N6、技能樹、HUD 都做）
1. N2（round 20）✅ 2026-09-25 f5edfc4 提交、已部署 MO2（備份 `.codex/mo2-installed-backup-20260925-204250`）；探針卡 `build/fix20-probes.md` 待使用者實測；吸血量約剩舊版 1/6，實測後可能要調倍率
1b. 準備報告：`build/native-verification-3.md`（N3～N6 介面，全部可行）、`build/tree-v04-inventory.md`（樹差異）
1c. 已定（2026-09-25 使用者 OK）：N6 領域＝對敵效果走 Spawn Hazard 原型 MGEF 經 CastSpellImmediate（放在目標腳下、只打敵對、引擎管壽命與上限，不再限 3 個）；對玩家自己的效果（火域熱度、冰原免減速、血池／聖域／潮池回復）由 DLL 每秒計時檢查玩家是否在領域範圍內補上。寫 N6 合約時納入，並同步改 v0.4 §10.3 領域列
2. T＝round 21 ✅ 2026-09-26 3d22562 提交、已部署 MO2（備份 `.codex/mo2-installed-backup-20260926-080245`）；兩輪審查後 PASS；狀態 DONE 74／KEPT 273／PARTIAL 42／LATER 104（清單在 build/plan-coverage.json）；探針卡 `build/fix21-probes.md` 待實測；提前移除火浴回血、不死、蔓延、亡者歸來（C3，於對應切片重做）。下一步 N3。
2b. N3＝round 22 ✅ 2026-09-26 20f754d 提交、已部署 MO2（備份 `.codex/mo2-installed-backup-20260926-124537`）；審查 PASS WITH FIXES 已修；探針卡 `build/fix22-probes.md`（約 20 分）。
2c. N4＝round 23 ✅ 2026-09-26 d78cb85 提交、已部署（備份 `.codex/mo2-installed-backup-20260926-152433`）；審查抓到護血不死（已修：分擔 50%、溢出可致死）；探針卡 `build/fix23-probes.md`（約 25 分）。裁定：雷神回魔 B_max×電荷×0.5、蓄能 ≥1 即轉、同調門檻讀 GLOB。
2d. N5＝round 24 ✅ 2026-09-26 e53f280 提交、已部署（備份 `.codex/mo2-installed-backup-20260926-185123`）；裁定：融斷傷害照 v0.4 2.7（B_max×K_sync×G×M_mod），各元素終焉只取非傷害部分，碎冰只在「冰封融斷」；附近＝15 m／5 人（v0.4 2.9 明文）；斷界弱化＝對應抗性 −10% 3 秒（待寫回文件）。探針卡 `build/fix24-probes.md`（約 30 分，第一步 X1）。
2q. 2026-09-28 10:40（壓縮前）：0.28.0 已完成但**未提交、未部署**（工作樹 58 檔改動；實作者交件：兩建置 exit 0、突變 122/122、FIX28 ok、PDB build/pdb/ElementsSpellblade-0.28.0.pdb；熱鍵輪轉錨點證明首次後無傷害、同調 1 人＝5 人）。**Fable 驗收進行中**（背景代理，唯讀，結論 SHIP / SHIP AFTER FIXES / DO NOT SHIP）。
- 使用者裁定（待併入下一個修正輪，與 Fable 必修項一起交實作者）：**印潮改為**「切換後第一刀開印，同時替 15 m 內**沒有任何印記**的其他敵人（最多 2 人）開新元素印」，不切印（D1 的副作用：原版挑帶舊印者→失效）。
- 實作者待辦：刪 `src/ESSBPlayerAlias.psc`、`build/compiler-results.json`（它不刪檔，需指揮官授權或自行處理並修 build_v03/fix12_verify 的引用）。
- 已知時序差：洗點前關形態→融斷在稍後 task，用洗點後節點（影響小）；CastWith 改為排 task 非同步施放。
- 流程：Fable 報告 → 必修項＋印潮交實作者（SendMessage 同一個實作代理，若不可用則新派 Opus 讀 `.codex/impl-fix-round27.html` 最新段）→ 指揮官建置驗收 → 提交 → 確認 SkyrimSE 沒在跑才部署 → Sonnet 回寫 v0.4（D1–D7、印潮、四項修正）並立即提交。
- 使用者仍待決：通用樹後期「消耗魔力換優勢」（A 超頻／B 灌注重擊（推薦）／C 魔力共鳴）。
2r. 2026-09-28 11:40：**0.28.1 已提交（55ea48e）並部署 MO2**（DLL sha256 c15d6c73…；備份 .codex/mo2-installed-backup-20260928-112737）。Fable 驗收 SHIP AFTER FIXES → round 28b 修完：CastWith 整秒複本（恐懼／瘋狂／狂刃／ApplyUtil）、讀檔清就緒旗標、domains 讀檔清、故障關閉清護血池、新印潮（15 m 內無印記最近 2 人）、水臨強化 10 秒冷卻（使用者 1b）；印記過期照常結算終焉（使用者 2a）。指揮官自跑兩建置 exit 0、ctest 9/9、突變 132/132。v0.4 已回寫 D1–D7／印潮／四修正／水冷卻（導引語意由指揮官更正：導引只存自身倍率，下一次終焉照常算自身倍率再乘導引）。**使用者待辦**：手動刪 src/ESSBPlayerAlias.psc、build/compiler-results.json（代理刪檔被權限擋）。**待使用者決定**：通用樹後期消耗魔力換優勢三案（A/B 推薦/C）。**下一步**：使用者實測 0.28.1（恐懼秒數、印潮、水冷卻＋原待測清單）。
2s. 2026-09-28 12:28：round 28c 提交 b3d298a 並重新部署（DLL 不變 c15d6c73；ESP 只改 6 筆技能說明；備份 mo2-installed-backup-20260928-122736）。已刪 ESSBPlayerAlias.psc、compiler-results.json（使用者授權）。技能說明覆寫改以節點為 key、原文變動即建置失敗，玩家文字禁 markdown。**教訓**：package/ 被 .gitignore，改 v0.4 後要拿 package 跟 MO2 逐檔比對，不能看 git status。待使用者決定：「（自有）」註記要不要從說明清掉；通用樹魔力方案 A/B/C。
2p. 2026-09-28：0.27.6（88c6565）已部署；v0.4 回寫 2aa4138。Fable 整體審查＋兩份子審查（玩法、Papyrus/ESP）回來；進行中 0.28.0（同一實作代理）＝技術修正（時鐘統一、fault 分級、換形態不空等、領域不掃格、升級不重建快取、讀檔能力同步、扣點漏洞、hazard 條件、監測）＋**使用者裁定玩法 D1–D7**：強制開印不切印、開印自身所得每事件一次、水臨強化改回 25% 魔力且需有敵人、熱鍵防連按 0.25 s、燃盡後 5 s 不能重開、火源自動印記融斷半額、維持費 5%／暗 7.5%＋長流照實扣退 80%；另修導引重複、死咒首領減半、風潛行秒殺算連殺、三重奏 10 s 內冷卻。0.28.0 交件後：驗收、部署、派 Sonnet 回寫 v0.4（D1–D7）。
**待使用者決定**：通用樹後期「消耗魔力換優勢」——A 超頻（每秒多付魔力換附傷）、B 灌注重擊（重擊耗 10% 魔力必暴／×2，指揮官推薦）、C 魔力共鳴（高魔力比例時附傷加成）；放通用樹傳奇階新分支。
2o. 2026-09-27 22:20 收工狀態：
- 已部署 0.27.5（fa1ade0）。實機另驗：雷電滿格重擊放電（7 次、清空電荷）、碎冰、聖裁、白熱火焰斗篷看得到、火源光環燒旁人、Custom Skill Menu 列出 13 棵樹。
- 22:00 卡死（hang2.dmp）：傾印裡本 DLL 無執行緒在跑，主執行緒卡在 Faster HDT-SMP（hdtsmp64.dll+0x3E2420）自身等待 → 判定 HDT-SMP 問題；白熱關聯弱（同局前 3 次白熱無事），不改火焰斗篷。待使用者提供 HDT-SMP 版本。
- PCEF（Project Combat Event Fixes 2.0）13:00 閃退＝其全域 unordered_map 無鎖、平行 Actor update 寫入；建議使用者停用、可回報 Nexus 158459。
- 進行中 0.27.6（實作者 Opus，同一個代理）：Custom Skill Menu 排序（無元素、通用、11 元素照熱鍵順序，已完成）、分支退回訊息寫明需要／剩餘點數＋分支說明標「需 5 點」＋reconcile trace 與測試；**使用者平衡決定**：傷害倍率預設 0.8（新檔；舊檔請自調 MCM）、維持費 一般 2.5%／黑暗 3.5%（原 1%／2%）。
- 22:25 使用者要求關掉背景任務 → 0.27.6 實作者已停止（停在「維持費改動」之前；排序完成、退回訊息與傷害 0.8 進度不明，工作樹有未提交改動，勿 reset）。恢復時：SendMessage 同一代理（若仍可用）或新派 Opus 讀 `.codex/impl-fix-round27.html` 最新段續做 0.27.6。
- 0.27.6 交件後：指揮官自己建置驗收 → 提交 → 部署（遊戲關著才部署）；再派 Sonnet 把三個平衡數字寫回 v0.4（寫完立刻提交，fix8 要求 spec＝HEAD）。
- 使用者待測清單：技能樹／MCM 是否還卡、分支買賣、A 站 6/7/10/11/15/16、風形態、毒、血吸血、暗瘋狂、星引爆、無元素、C 被打、D 群戰（隨從路人排除、領域、多印融斷）、要加點的站另開測試檔。
2n. 2026-09-27 21:45：0.27.5（fa1ade0）部署。實機已驗：白熱火焰斗篷看得到、火源光環對旁邊敵人每秒 4.85 火傷、雷電 N＝1＋電荷與暴擊、11 元素基本附傷、光圈。PCEF 閃退判定為該模組自身 map 無鎖（建議使用者停用）。待測清單見本次對話整理：🆕 技能樹／MCM 卡頓、Custom Skill Menu 13 棵樹；A 站 6/7/10/11/15/16；雷滿格重擊放電、風形態、碎冰、毒、血吸血、暗瘋狂、星引爆、無元素；C 被打；D 群戰（隨從路人排除、領域、多印融斷、毒死亡擴散）；要加點的站留到專用測試檔。
2m. 2026-09-27 20:10：0.27.3（2c83bd2）實機通過：融斷數值正常（8.05）、Z 力量開關不閃退、無 OVERLAP/BADMAG/crash；形態光圈使用者確認看得到（原版地面符文素材）。中間修掉的：0.27.2 Context 自指複製（融斷 inf）、0.27.2 SwitchWork 懸空節點檢視（Z 開形態閃退）；加了 clang 生命週期網、ASan harness、每版 PDB（build/pdb）。下一步：使用者照 `build/probes-all.md` 從站 2 起跑（每站按數字鍵區 +）。
2l. 2026-09-27 18:10：round 27＋27b（0.27.1，7720600）三份複審後修完、已部署。形態光圈取代武器光（原版蓄力光圈，四段外觀相同＝已知限制；顏色待實測）。v0.4 回寫 35986e5。下一步：使用者照 `build/probes-all.md`（0.27.1）先跑站 1，再視情況往下；探針 log 用除錯等級 4。
2k. 2026-09-27 晚：0.26.3（481b8d6，Rng 自呼叫修正）已部署。三份整體審查收齊，濃縮在 `.codex/review-2026-09-27.md`；round 27 合約 `.codex/fix-round27-briefing.md`（指揮官裁定 G1–G15：節點加成改回 1+Σ、百分比效果只吃自己主線、催毒不連乘；臨只在從無形態開啟時觸發、水臨強化需主線＋敵人；層數不吃節點倍率；熔斷白熱關形態不再計火源；魔力歸零關形態不融斷；致命一擊走屍體模式；受擊扣掉自己的付血；換形態由 DLL 同步處理；開新檔失效＝log 檔被鎖導致 Query 失敗；特效修復；法術加不可吸收）。使用者 2026-09-27 回覆：G1、G4 照辦；**G2 改為「切換也觸發臨系列、不設冷卻」（維持現行）**；**G5 改為「魔力歸零自動關形態仍融斷（燃盡）」**，瘴氣倍率那半照辦。已轉告 round 27 實作者。
2j. 2026-09-27 下午：實機證實 heap 損毀是我們（停用本模組就不閃）；原因＝Precision/TDM 讓命中在視窗執行緒送出，與我們 Post process task 並行 → 0.26.2（6bef455）所有引擎寫入改在 SKSE task、TrueHUD 呼叫改 UI task、MCM 加資源條開關。0.26.2 卡死＝Plugin.cpp `Rng()` 自呼叫（dump 證實）→ 0.26.3 單獨修（進行中）。開新檔時 Papyrus 原生函式像沒綁上（讀檔正常）、特效全失 → round 27（合約在紀錄 `.codex/impl-fix-round27.html`）。使用者睡覺前要求整體審查：派 3 個 Opus 唯讀審 6bef455（A 引擎接線、B 玩法對 v0.4、C ESP／Papyrus／MCM）。醒來前：部署 0.26.3、收三份審查、排修正輪。
2i. 執行緒定案（Fable 反組譯驗證，2026-09-27；Fable 授權已用掉）：遊戲中沒有「主執行緒做遊戲邏輯」；引擎把命中／傷害／死亡延後到 BSJobs「Post process」job，SKSE AddTask 緊接其後＝最安全的無 hook 位置，且該 phase 不與 Havok step 重疊。命中 sink 同步做事＝與原版同 context，保留。只改：死亡 sink 不在 sink 內讀兇手／玩家；輸入 sink 的 RequestSwitch 改 AddTask。否決自有佇列＋AddUITask（UI task 在表 4 UI job，更差）。11:17 閃退判定非本模組（他模組生物布娃娃約束懸空）。round 26b（0.26.1）實作中。round 26（00b8956）探針 log 已提交未部署。
2h. 2026-09-27 使用者授權：必要時派 Fable 處理最複雜的探測，**僅限 1 次**（已於 2i 使用）。計畫用在：Opus 交出執行緒查證與修法後，由 Fable 獨立反向驗證再動工。第三次實機：輸入 sink＝Papyrus native＝6300（真主執行緒），SKSE AddTask 的工作、命中、死亡事件都在其他執行緒；11:17 再閃退（crash-2026-09-27-03-17-19.log，堆疊無本 DLL）。使用者已暫停實測，等修好再叫。
2g. 2026-09-27：0.25.1 熱修（f03c42d）已部署，DLL 實機正常載入（F9）。閃退是 DynamicGrip 新版（使用者已停用）。**執行緒疑點**：實機 X1 顯示 kDataLoaded、timer task、TESHitEvent 三個不同執行緒 → round 26（探針 log 化，合約 `.codex/fix-round26-briefing.md`）優先查證並提修法，指揮官確認後才改。熱鍵：使用者 2026-09-27 決定維持數字鍵區（Numpad，預設鍵碼 79,80,81,75,76,77,71,72,73,82,83），不改 Shift+數字（原版最愛 1～8 不看修飾鍵、不 hook 就擋不掉）；同一熱鍵再按一次＝關形態；探針盡量寫 log、使用者只做動作。
2f. 初步完整 ✅ 2026-09-26 21:26 a1c1c29（N6）部署（備份 `.codex/mo2-installed-backup-20260926-212612`）。總探針卡 `build/probes-all.md`（102 步，Opus 逐步對程式核對完，20 步標離線無法核對；臨界＝15 m／5 人照 v0.4 2.9，程式對、round 24 紀錄說法錯）。待修小項（實測後一併處理）：`Plugin.cpp` 的 `Probe::kHurt` 被 TESHitEvent 與 hurt task 兩行共用，log 只印先到的那行；`TakePush` 每目標冷卻用真實時間（暫停時照走、讀檔不歸零）；死亡／倒地／騎馬時熱鍵行為待探針記錄後決定。
2e. N6＝round 25（✅ 見 2f；原註：合約 `.codex/fix-round25-briefing.md`、紀錄 `.codex/impl-fix-round25.html`）；毒霧劑數併入裁定照瘟疫。做完＝初步完整 → 整理全部探針卡成一張總表給使用者；v0.4 文件待修清單（負責欄偏離、52 列反應本體、斷界弱化、毒霧）交 Sonnet。使用者 2026-09-26：先做完 N3～N6 初步完整，再一次跑全部探針卡；切片之間不停。
（舊註記：2026-09-25 21:40 額度 99%，可能中斷。恢復：讀 `.codex/impl-fix-round21.html` 最後完成的里程碑，重派 Opus 照合約「If resumed」續做；快照 `.codex/pre-fix21-snapshot/` 不可覆寫；工作樹未提交的改動都是 round 21 的，勿 reset。合約 `.codex/fix-round21-briefing.md`、紀錄 `.codex/impl-fix-round21.html`）：技能樹照 v0.4 重建（ESP perk、Papyrus 樹／MCM、DLL 節點讀取對照）；補上 N2 因節點不存在沒做的無元素四列
3. N3：目標狀態層（根除舊狀態層幽靈 bug）
4. N4：受擊與自身資源（超載、蓄勁、護血扣減、電荷→雷 N）
5. N5 與 H 並行：N5 融斷與死亡；H＝TrueHUD 資源條（git worktree 隔離，新檔為主，指揮官合併）
6. N6：每秒計時（背景計時執行緒＋每 tick 一次 AddTask）、熱鍵 input sink、領域 Hazard
7. 總驗收：整合探針、效能量測、殘留清理、README → 使用者開新檔
- 每片開頭先實機查證該片用到的 PARTIAL／待查證 API（native-verification-2）；10.3 的 P3／P4／P8／P12 在相關切片定案。
- 審過就部署、接著派下一片，不等使用者實測；實測抓到的問題插小修正輪。

## 使用者環境備忘
- Claude 每週額度接近上限，9/26（週六）重置。
- 遊戲 1.5.97 永不升級；有 Ordinator、For Honor、Valhalla Combat（佔用 TrueHUD 特殊資源條）、MaxsuPoise、TrueHUD 1.1.10。

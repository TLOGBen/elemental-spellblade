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
2f. 初步完整 ✅ 2026-09-26 21:26 a1c1c29（N6）部署（備份 `.codex/mo2-installed-backup-20260926-212612`）。總探針卡 `build/probes-all.md`（Opus 核對中）。待修小項（實測後一併處理）：`Plugin.cpp` 的 `Probe::kHurt` 被 TESHitEvent 與 hurt task 兩行共用，log 只印先到的那行；`TakePush` 每目標冷卻用真實時間（暫停時照走、讀檔不歸零）；死亡／倒地／騎馬時熱鍵行為待探針記錄後決定。
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

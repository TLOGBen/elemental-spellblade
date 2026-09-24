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
- 內容（見 v0.4 第 9 節與 design-latency 第 6 節）：DLL 在命中當下算附傷強度（取代 Papyrus 事先寫強度＋十幾個重寫觸發點）；每刀隨機基礎傷害；雷真擲 1～25 取 N＝1＋電荷數次最大、暴擊（5%＋每格電荷 2%，×1.5／重擊 ×2.5）、形態內滿格重擊直接放電必暴；血位線性；命中吸血；聖裁同目標三擊計數；無元素普攻吸魔＋小滅法（魔力 0 不觸發）、重擊滅法。
- **必避坑**：`CastSpellImmediate` 的強度覆寫會套到法術的每一個效果 → 需要不同強度的效果要拆成單效果法術各自施放（查證 NO 項）。
- 先清兩件小事：B 組測試的參數寫死成 1（右手）與 24（生命）而不是跟程式比；清掉 09-22 的舊證據檔、`native-verification.md:85` 改指 `build/fix19b-build.log`。
- 每秒執行點若 N2 用到：只能「背景計時執行緒每 tick AddTask 一次」，task 內自我重排會卡死遊戲。
- 舊狀態層（毒／星痕幽靈 bug）仍在，N3 才根除；N2 不碰狀態層。

## 使用者環境備忘
- Claude 每週額度接近上限，9/26（週六）重置。
- 遊戲 1.5.97 永不升級；有 Ordinator、For Honor、Valhalla Combat（佔用 TrueHUD 特殊資源條）、MaxsuPoise、TrueHUD 1.1.10。

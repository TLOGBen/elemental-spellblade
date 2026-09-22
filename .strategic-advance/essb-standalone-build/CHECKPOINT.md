# CHECKPOINT ｜ 2026-09-22 23:00 +0800

## 一句話
附傷路徑定案為 SKSE 原生 DLL（只走丙、無 entry 51 退路）；第十九輪（DLL 第一片 N1）Astra 背景施工中；被引擎限制逼出的設計妥協已由使用者裁決全部還原成 v0.3；版控已上 GitHub。

## 真相來源
- 設計：`元素魔戰士規劃-v0.3_alter.md`（v0.3 原檔永不改，mtime 2026-09-16 07:31）
- 實作計畫：`design-latency-2026-09-20.md`（4.11 丙的架構；第 6 節 DLL 六片 N1～N6）
- 妥協盤點與使用者勾選：`design-compromises-2026-09-22.md`
- 相容性清查：`build/entry51-compat-audit.md`
- repo：https://github.com/TLOGBen/elemental-spellblade（公開；main；vendor/、package/、大型建置暫存不進 repo；core.autocrlf false、`* -text`）

## 使用者定案（2026-09-22）
- 只走 SKSE 原生插件，無 entry 51 退路；DLL 停用＝沒有元素附傷（已接受）。
- 遊戲永遠停在 1.5.97，DLL 只做單一執行期。
- 給 Astra 網路權限：只限下載 CommonLibSSE(-NG)、spdlog、fmt、binary_io 等建置相依與查其文件原始碼。
- 分工原則：狀態放引擎（效果強度／時長、GLOB、perk）、判斷放 DLL、介面留 Papyrus；DLL 不存狀態、不序列化。
- 妥協全部照建議：血痕回 v0.3 疊層（開印 2、+1、上限 8／12／15）、凍結 0～5、詛咒與水壓層數、電荷／岩甲／風勢／戰意計數、〔取代〕節點回原文、重擊潛行用命中旗標；**同調回砍刀計數 5／15／30**；**放血**若 DLL 能每秒執行就回「依目標當下生命每秒扣」，否則命中時重算。維持：毒單一成長效果、印記無上限、聖印單一。雷已還原為真擲 1～25 best-of-N、每刀隨機 B、血位線性。
- 派工分級：設計判斷→Fable（**額度只剩約 3%，省著用**）；純寫檔→Sonnet；實作建置→Codex astra。

## 探針結論（證據 .codex/smoke8、smoke9、smoke10 log）
- entry 51：全部 perk 合計一刀只套一個法術；優先度數字最小者贏；同優先度時先加到角色身上的 perk 贏。
- 0x1D Mod Spell Magnitude 對進入點法術有效。
- 使用者環境對玩家法術傷害 ×0.95（量測以參考火傷校正）。

## 進行中（下次接手第一件事）
1. **Astra round 19（N1）**：briefing `.codex/fix-round19-briefing.md`；runner `scratchpad/astra-fix19`（2026-09-22 22:36 開工）。看 `runner-state.txt` 有沒有 EXIT、`codex-final.txt` 的回報；產物在 `native/`、`build/native-verification.md`、`build/fix19-probes.md`、`.codex/impl-fix-round19.html`。驗收：自己跑 `python build_v03.py`、比對正式包、確認 ESP 沒有我們的 entry 51 段、選擇表單元測試通過；遊戲關著時才部署 MO2。然後請使用者跑 fix19 探針卡。
2. **Sonnet 文件同步**：把使用者勾選寫進 alter／latency／compromises；完成後提交推送（若本檔寫成時尚未完成，檢查三份文件的一致性再提交）。
3. `build/native-verification.md` 出來後，把實際 API 併回 4.11 待查證表（小事可給 Sonnet；若有設計取捨才動用 Fable）。
4. 之後依序派 N2～N5。

## 已部署在 MO2
- 正式包：round 18（entry 51 版，仍帶舊狀態層毒／星污染 bug）。探針包 `Elements Spellblade Round18 Probes` 仍在 mods，**使用者應取消勾選探針、勾回主模組**。
- 備份：`.codex/mo2-installed-backup-20260921-202224`（round 16）。

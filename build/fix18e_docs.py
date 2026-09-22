"""Produce the console-free card, retaining the original route as an appendix."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
old = (ROOT/'build/round18e/before/build/fix18-probes.md').read_text(encoding='utf8')
prefix = old[:old.index('## 提前探針：')].replace('round18d 校準版', 'round18e 免主控台版')
common = old[old.index('### 共同準備：'):old.index('### 探針 1：')]
appendix = common[:common.index('3. 日誌位置')]
logs = common[common.index('3. 日誌位置'):common.index('新增的 `START meter`')].replace('3. 日誌位置', '日誌位置')
probe1 = old[old.index('關閉主控台。看到 `READY CONTROL`'):old.index('完成後仍選取目標，輸入：')]
probe1 = probe1.replace('關閉主控台。看到', '施放「探針：準備＋第一題」後，看到')
probe2 = old[old.index('關閉主控台；同樣先等'):old.index('完成後清理：')]
probe2 = probe2.replace('關閉主控台；同樣先等', '施放「探針：第二題」後，同樣先等')
tail = old[old.index('退出且丟棄本測試檔；'):]
tail = tail.replace('再對目標 `removespell xx000831`／`addspell xx000831`，重跑控制', '再施放對應題目的能力，重跑控制；要換全新目標則施放「準備＋第一題」')
tail = tail.replace('能力只監測手動指定的目標，不要同時安裝到多個目標；換目標前先移除舊目標能力。', '能力只監測腳本保存的測試強盜；第一題會刪除舊目標並換新，第二題會沿用仍存活的目標。不要與附錄的手動掛載方式混用。')
tail = tail.replace('本次 round18d 已完成編譯及離線驗證', '本次 round18e 已完成編譯及離線驗證')
text = prefix + '''## 提前探針：引擎多段與倍率（免主控台）

安裝完整 `build/fix18-probe-package/` 的 ESP、`Scripts/` 與 `SEQ/`，或使用 `build/fix18e-probes-install.zip`。以 **SKSE 啟動 Skyrim SE 1.5.97**；只需 `Skyrim.esm` master，不需要正式 `Elements Spellblade.esp`。探針任務會在新檔初始化／讀檔時自動補發三個可收藏、可用能力鍵施放的次級能力。僅限獨立測試設定檔與可丟棄存檔，關閉正式 Elements Spellblade。

### 最短操作順序

**收藏三個能力 → 施放「探針：準備＋第一題」→ 砍一刀 → 讀 log → 施放「探針：第二題」→ 砍一刀 → 讀 log → 施放「探針：清理」。**

**每題保留原有控制與校準，因此每題實際要分兩次砍：** `READY CONTROL` 後的第一刀只確認物理扣血為零；等自動參考法術校準完成、出現 `READY PROBE`，再砍一刀才會得到該題結果。不得以控制刀或參考法術當作最終 verdict。

1. 載入測試檔，看到「探針能力已加入」，打開魔法 → 能力，收藏「探針：準備＋第一題」、「探針：第二題」、「探針：清理」。用收藏選單選取，再按能力鍵（預設 Z）施放。無須查載入序、選主控台目標或輸入指令。
2. 到平坦空曠處，面向前方留一個身位；施放「探針：準備＋第一題」。自動卸下玩家裝備、補足並裝備原版鐵匕首、保存原攻擊倍率後設為 0。強盜生成於前方 128 遊戲單位，先停 AI、停止戰鬥／警報並清空裝備，再設 Health=10000 並補滿，FireResist／MagicResist／AbsorbChance／HealRate／HealRateMult=0；只有第一題 perk。量測器直接加到此強盜，不受主控台選取影響，拒絕玩家參照。
3. 看 `[ESSB-PROBE] SETUP PROBE=1`：列強盜參照、三個 perk 是否持有與攻擊倍率。等 `READY CONTROL`，用匕首普通砍一刀，停至少 10 秒，等 `CONTROL physical-only hit = 0`、`CALIBRATE k=...`、`REFERENCE ... accepted`、`READY PROBE`。然後再普通砍一刀，等至少 6 秒及完整 `MEASURE`／`VERDICT`，記錄第一題結果。
4. 施放「探針：第二題」：自動移除第一題 perk、加入第二題兩個 perk，清掉舊量測器並重掛新的。沿用同一活強盜；若死亡、停用、已刪除或參照消失則換新，同樣完整準備。依上一步再做控制刀、等待校準、正式測試刀，讀第二題的 `MEASURE`／`VERDICT`。
5. 施放「探針：清理」：關閉探針 gate、失效化舊 session、移除三個 probe perk、玩家誤掛與腳本目標上的量測器、刪除測試強盜，還原第一次準備前記住的 AttackDamageMult。看到 `SETUP CLEANUP` 與畫面通知後離開並丟棄測試檔。三個操作能力保留，方便再測；匕首保留、已卸下的裝備不會自動重穿。

重複施放第一題會刪除前一隻再生一隻；重複施放或讀檔不會以 0 覆蓋保存的原攻擊倍率。也可直接施放第二題開始。正在準備／清理時重複施放會顯示忙碌，請稍候再施放。每次施放各有一行 `SETUP`，包含目標參照與 perk 現況；失敗會明確提示清理重試。

**測試條件：**請用自動裝備的原版鐵匕首（Skyrim.esm `0001397E`），不要徒手、塗毒、附魔、換武器或讓同伴參與。保持站立，普通單擊，不潛行、不重擊、不盾擊，不開無敵／幽靈／一擊必殺。強盜沿用本機 master 確認的 `EncBandit01Melee1HKhajiitM`（`000C3CA0`），與舊操作卡一致；不換種族以免另引入環境差異。

不自動傳送 qasmoke，避免載入畫面及將目標放在不熟悉的位置；在空曠安全處即可完成。Papyrus 不能設定難度；不必固定 Adept，量測器照原有邏輯校準 k，整個 session 中不得改難度或其他傷害倍率。保留其他模組時仍可能出現額外 OnHit 或附傷，請以拒絕訊息判讀，不強行解讀結果。

### 看日誌

''' + logs + '''`START meter`／`START segment` 仍是原量測腳本的入口日誌。`SETUP` 表示準備動作已執行，**`READY CONTROL` 才代表量測器接受環境**；`fresh_meter=True` 也不能取代 READY。若只看到 SETUP，請確認完整 ESP＋四支 PEX＋SEQ 已安裝並以 SKSE 啟動。若有 REFUSED／STOP，修正所列條件後重施放對應能力，無須照舊診斷文字手動輸入指令。

### 探針 1：全部套用或首段即停

''' + probe1 + '''第一題完整結果記下後，直接施放「探針：第二題」，不需任何移除／加入 perk 或 spell 的指令。

### 探針 2：0x1D 是否放大 entry point 法術

''' + probe2 + '''完成後施放「探針：清理」，再退出測試檔。

''' + tail + '''
## 附錄：舊主控台路線（備用）

以下保留原本人工操作方式；**正常測試請用上面的三個能力即可**。不要與自動能力混用：人工 `placeatme` 的強盜不屬於能力保存的參照，須人工清理。開始前另行記錄玩家原有 AttackDamageMult，最後用原值還原。

''' + appendix.replace('### 共同準備：照次序輸入', '### 人工共同準備').replace('restoreav health 10000\n', 'restoreav health 10000\nunequipall\n') + '''
### 人工第一題

仍選取強盜，輸入：

```text
player.addperk xx000820
addspell xx000831
```

關閉主控台，照正文先控制刀、等校準、再正式測試刀並讀 verdict。完成後重新選取同一強盜，輸入：

```text
removespell xx000831
player.removeperk xx000820
```

### 人工第二題

仍選取同一強盜，輸入：

```text
player.addperk xx000821
player.addperk xx000822
addspell xx000831
```

關閉主控台，同樣先做控制／校準再正式測試。完成後仍選取強盜，輸入：

```text
removespell xx000831
player.removeperk xx000820
player.removeperk xx000821
player.removeperk xx000822
disable
markfordelete
```

再以 `player.forceav attackdamagemult 原值` 還原先前記錄的攻擊倍率。若量測器誤掛玩家，另輸入 `player.removespell xx000831`。不要把 `原值` 或 `xx` 原樣輸入。關閉並丟棄測試檔。
'''
(ROOT/'build/fix18-probes.md').write_bytes(text.replace('\n','\r\n').encode('utf8'))

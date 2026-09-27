# 元素魔戰士（Elements Spellblade）整合測試卷 —— 探針 log 版（Round 26b，DLL 0.26.1）

這一版的原則：**你只負責動手，不用看畫面、不用抄數字**。每個可以觀察的事件，DLL 都會寫一行進 log（MCM「除錯等級」**4：探針 log**）；你跑完把 log 交給指揮官，指揮官用 `build/probe-judge.py` 逐步判定。只有 log 真的看不到的東西（特效、NPC 逃跑、音效、UI 條、技能樹畫面、FPS）才留一句「目視」，請你回答「是／否」。

全卷 102 步（ID 跟舊卷相同，SETUP-1、A-01～A-18、B-01～B-37、C-01～C-09、D-01～D-24、E-01～E-13），照「換一次場景、做到底」合併成 **91 站**。每一站開始前按一次「下一站」鍵（見下面），log 就會切成一站一段。E 段原本是「重做一次看 log」，現在大多直接用 B／C／D 那一站的 log 判定，不用再做一次。

預估時間：約 3.5 小時（比舊卷少了抄數字、開主控台看 getav 的時間）。

---

## 0. 開始之前（不計時）

1. **存檔**：用一個全新或可以丟的測試存檔。
2. **MO2**：右側外掛清單勾 `Elements Spellblade.esp`，記下它的 **Mod Index**（兩位十六進位，下面寫 `XX` 的地方換成它）；舊的探針包（`*-probe-pack*.esp`、round 18b 之類）一律取消勾選。部署完**整個重開遊戲**（DLL 只在啟動時載入）。
3. **MCM → 元素魔戰士 →「一般」頁 →「除錯等級」設 `4：探針 log`**，整份測試都維持 4（等級 4 也會照舊寫 L1～L3 的舊行，不影響判定）。「平衡」頁：節點倍率 **3**、傷害倍率 **1**、持續時間 **1**。「熱鍵」頁：「直接切換熱鍵」開著（預設數字鍵區 1＝火焰、2＝冰霜…9＝水、0＝黑暗、`.`＝星界）。
4. **Log 檔案位置**：`C:\Users\powde\OneDrive\Documents\My Games\Skyrim Special Edition\SKSE\ElementsSpellblade.log`（注意是 **OneDrive 底下的「文件」**）。
   - 這個檔**每次開遊戲都會整個覆寫**。DLL 每秒寫檔一次（存檔、讀檔時也會馬上寫），所以**關遊戲前先存一次檔、等 2 秒，再把 log 複製到別的地方**，然後才關遊戲。
   - 中途當機：先把 log 複製出來再重開，重開後從當機的那一站繼續（站號存在存檔裡，讀檔後接著按 + 就好）。
5. **站標記（每一站都要做）**：
   - **數字鍵區 `+`**：前進到下一站。畫面會跳一行「探針站 N」，**N 應該等於這一站的號碼**；不一樣就用下面的主控台指令改正。
   - **數字鍵區 `-`**：退回上一站（也會寫一個標記）。
   - **主控台 `set ESSB_ProbeStep to N`**：直接跳到第 N 站（例如 `set ESSB_ProbeStep to 25`）。
   - **某一站做錯要重做**：按一次 `-` 再按一次 `+`（重新標記這一站），然後重做。判定器只看**每一站最後一次**標記之後的內容。
   - 這兩個鍵只在除錯等級 4、遊戲畫面（不在選單、主控台）時有作用；round 26b 起熱鍵與站標記在下一個 task 執行（最多晚一幀）。
6. **基準**：本卷數字都假設**技能樹等級 1（G＝1.05）、傷害倍率 1、節點倍率 3、持續時間 1、白天、戶外、目標沒有抗性**。測試檔不要有「順轉」「免門檻」類節點。
7. **主控台小提醒**：`setav` 改的是基礎值（上限跟著變）；想改「當下的值」用 `damageav`／`restoreav`。`player.addperk XX……` 加的節點，DLL 每秒會記一行 `[ESSB][T][node] change=+ id=……`，不用另外確認。
8. **跑完之後**：把 log 交給指揮官。指揮官執行 `python -B build/probe-judge.py <log 路徑>`，每一步印出 PASS／FAIL／EYES（要你回答目視那一句）／RECORD（只記錄）／NO-DATA（那一站沒標記或沒做到），並附上證據行（`#序號`）。

### log 的樣子（給指揮官）

每一行探針 log：`[ESSB][T][種類] #序號 g=遊戲在跑的毫秒 r=實際毫秒 欄位=值 …`。演員一律寫成 `名字(0xFormID)[h=目前/上限 m=目前/上限 s=目前/上限]`。站標記：`[ESSB][STEP] 站號 #序號 g=… r=… via=key|key-back|console`。格式表在 `build/fix26-trace-format.json`（`native/tests/trace_test.cpp` 用同一份檢查 DLL 的輸出）。主要的種類：

| 種類 | 內容 |
|---|---|
| `proc` | 一次附傷：`src=hit/repeat/extra/cast`、目標與你（命中前）、元素、法術、`power`、`sneak`、強度、`crit`、雷的 `N`／`charges`／`critChance`、吸魔／燒魔、這一擊的施放清單 `steps=`、擲骰 `rolls=R(下,上)=值 …` |
| `hit-end` | 這一擊全部做完之後的目標與你 |
| `op` | 每一個狀態操作：`ctx=`（hit、hurt、burst、death、settle、tick、form-second、enter、leave、domain-enemy、spread、native:… 等）、`op=`（Apply、Remove、Mark、Unmark、Damage、Heal、Event…）、`kind=`（狀態記錄名，如 `N3_Heat1`、`N4_Charge`）、`el=`、`mag=`、`sec=`、事件的 `ev=`／`args=`／`reason=`（終焉：cut／burst／expire）、作用對象 `on=`、被取代的舊實例 `was=… left=… n=…` |
| `op-done` | 會改數值的 op（傷害、回復、付出）做完後，那個演員的數值 |
| `remove`／`apply` | 我們的效果離開演員（理由 expired／dispel／death、剩幾秒）；引擎替我們掛上的效果（領域標記、Papyrus 施放的法術） |
| `hurt` | 你被打：扣血前後、`lost`、近戰／法術／格擋、護血池、超載、魔力、持續傷 `dot`、當下的冷卻 `cd_you`／`cd_att` |
| `second` | 開著形態時每一秒：維持費 `spent`、血形態扣血 `bled`、長流 `flow`、`close`、雷雨電荷 `storm`，以及這一秒你的生命／魔力／耐力變化 `dH dM dS` |
| `env`／`tick`／`menu` | 每 5 秒的環境判定（含天氣 FormID）；計時器停住／恢復；每個選單的開關 |
| `switch`／`key`／`mcm`／`node` | 形態切換（via=hotkey／power）；熱鍵（accepted／blocked 與理由）；每個全域變數（MCM、主控台 set）的變動；節點的增減 |
| `scan`／`scan-c` | 範圍效果的一次掃描與每個演員的判定（picked、ally、neutral、far、dead…） |
| `death`／`death-event`／`burst`／`settle`／`native`／`cast` | 死亡處理、兩次死亡事件、融斷、到期結算、Papyrus 呼叫的原生函式、敵人施法 |
| `domain`／`domain-new`／`domain-gone`／`domain-in`／`domain-you`／`domain-enemy` | 領域：每秒每個領域、出現／消失、誰站在裡面、你在哪些領域裡、敵人在哪些領域裡 |
| `pap` | Papyrus 那一半：推力、跌倒、復生、恐懼／瘋狂／幻視、神佑、換形態、魔力耗盡關閉、以毒攻毒、化灰、「印出目標狀態」（`dump-nearest` 就是訊息框那一行）、MCM 按鈕 |
| `[ESSB][X1]` | 每個事件 sink／task 遇到的每一條執行緒，對照輸入 sink（主迴圈）、最近一次 SKSE task、遊戲視窗的執行緒 |

---

## SETUP：第一道關卡

### 站 1：SETUP-1（DLL 版本與執行緒 X1）

- **操作**：戶外晴天（`fw 81a`）。MCM →「查看 DLL 版本與狀態」按一次；按數字鍵區 1 開火焰、砍 NPC 一刀，用 Z（力量欄裝「【魔戰士】火焰形態」）關掉；讓 NPC 打你一下；讓一名會施法的 NPC 對你施一次法術；殺死一名 NPC；存檔再讀檔一次。
- **log 判定**：`[ESSB][load] ElementsSpellblade 0.26.1`；`[T][pap] kind=mcm-button … version=0.26.1 active=True`；`[ESSB][X1]` 十種都在：`Papyrus native`、`queued native task`、`TESHitEvent`、`TESHitEvent (you are the target)`、`hurt task`（round 26 修好：它以前跟上一行共用旗標）、`TESActiveEffectApplyRemoveEvent`、`TESDeathEvent`、`timer task`、`TESSpellCastEvent`、`input sink`；缺任何一種＝FAIL，**整份停下**。
  **X2（round 26b，指揮官的執行緒裁定）**：每個 sink／task 每一條不同的呼叫鏈一行 `[ESSB][X2] <名稱> thread= window= same|DIFFERENT paused= havok= keys= frames=SkyrimSE.exe+0x…`。判定：**遊戲中（paused=0）** 命中 sink（`keys` 有 `post-process`、`hit-task` 或 `hit-frame`）與所有 task（timer／queued native／hurt／settle／death／spell-cast／input task：`post-process`）都在 BSJobs 的 Post process；輸入 sink＝`poll-controls`、UI task＝`ui-job`（或 `main-ui`）、Papyrus native＝`vm-job`；**暫停時（paused=1）** 都在視窗執行緒（`same`）或 `paused-*` 路徑。對不上＝FAIL；12 層內沒有認得的呼叫鏈＝EYES（判定器列出 frames 給指揮官）。X1 的 same／DIFFERENT 不再判定。
  另外：除錯等級 3 時，本模組造成的每一次擊殺、推力、跌倒、hazard 各記一行 `[ESSB][AB][L3] kind=kill|push|knock|hazard ref= tick= via= thread=`（給崩潰對照用，不判定）。
- 目視：無（版本按鈕沒寫進 log 時才要看畫面）。

---

## A 段：幾乎不戰鬥（約 35 分）

站在戶外晴天。開始前：`player.setav health 1000`、`player.setav stamina 200`、`player.setav magicka 300`。**站 10 起到站 15**先把自然回復關掉：`player.setav magickarate 0`、`player.setav healrate 0`、`player.setav staminarate 0`（站 15 做完改回原值，一般是 3、0.7、5）。

### 站 2：A-01（節點倍率滑桿範圍）
- **操作**：MCM → 平衡 →「節點倍率」拉到最右、再拉到最左、最後放回 3。
- **log 判定**：`[T][mcm] global=ESSB_NodeScale` 的 `new=` 最大 5.000、最小 1.000、最後 3.000。

### 站 3：A-02（13 棵樹的代表節點）
- **操作**：開技能選單逐一進 13 棵樹，找：火焰 關閉·新手「餘壓」；冰霜 持續·大師「冰鎧」；雷電 持續·大師「逆電」；大地 關閉·專精「蓄能」；風 持續·新手主線說明寫「風刃傷害 +6%／點」；鮮血 持續·新手「血刃」；神聖 持續·大師「破邪斬」；毒素 關閉·熟練「疫染」；水 持續·熟練「水盾」；黑暗 持續·新手「咒延」；星界 持續·新手「星鏈」；無元素 第一條路線「大師」、新手分支「逼近」；通用 開啟·新手「跳印」；火焰 持續·新手只剩「添薪」。
- **log 判定**：無（技能樹畫面不經過 DLL）。
- **目視**：13 個都在、都是 v0.4 名稱，火焰關閉·新手看不到「洩壓」？

### 站 4：A-03（退役節點）
- **操作**：`player.addperk XX002029`，開火焰技能樹；主控台 `help 洩壓 4`。
- **log 判定**：`[T][node] change=+ id=002029 name=…已退役…`。
- **目視**：樹上沒有「洩壓」、`help` 顯示「洩壓（已退役）」？

### 站 5：A-04（新 NPC 沒有殘留）
- **操作**：`help 強盜 4` 找強盜 base ID，`player.placeatme <ID>`，先不要打，MCM →「印出目標狀態」。
- **log 判定**：`[T][pap] kind=dump-nearest who=<那名強盜> marks=0 s2=0 … s19=0`（全 0）。

### 站 6：A-05（熱鍵與 Z 的開關、魔力門檻）
- **操作**：數字鍵區 2 開冰霜、再按 2 關；`player.setav magicka 300`、`player.damageav magicka 280`；按 1（不開）；按 6（鮮血照開）、再按 6 關；力量欄裝「【魔戰士】火焰形態」按 Z（不開）；`player.restoreav magicka 300` 後按 Z（開）、再按 Z（關）。
- **log 判定**：`[T][switch]` 依序出現 `via=hotkey wanted=frost kind=open`、`kind=close`、`wanted=fire kind=refuse`、`wanted=blood kind=open`、`kind=close`、`via=power wanted=fire kind=refuse`、`kind=open`、`kind=close`；refuse 那兩行的你 `m=` 低於 `gate=`。

### 站 7：A-06＋E-10（選單裡按熱鍵）
- **操作**：先在遊戲畫面按一次數字鍵區 1（開火焰）；再分別在主控台、背包、MCM 的一個文字欄、Esc 選單裡各按一次 1。
- **log 判定**：A-06：`[T][key] … verdict=blocked` 至少有 `console=1`、`menu=1`、`text=1` 三種，而且 blocked 之後沒有 `switch via=hotkey`。E-10：遊戲畫面那一下 `verdict=accepted`，`thread=` 等於 `[ESSB][X1] input sink thread=` 的 id，接著一行 `switch via=hotkey`；每個 blocked 至少一個旗標是 1。

### 站 8：A-07（按住熱鍵、手把熱鍵）
- **操作**：按住數字鍵區 1 三秒再放開。（有手把的話）MCM 熱鍵頁把火焰改綁到手把一個鍵，按一次；再改回數字鍵區 1。
- **log 判定**：改綁之前只有一行 `switch via=hotkey`；改綁的 `[T][mcm] global=ESSB_Hotkey_Fire new=<手把代碼 ≥266>` 之後，那個代碼 `accepted` 一次、切換一次。沒改綁就只判前半（手把未測）。

### 站 9：A-08（死亡／倒地／騎馬時按熱鍵，只記錄）
- **操作**：`player.kill` 後（死亡鏡頭中）按 1；讀檔回來。讓 NPC 打倒你（或 `player.pushactoraway player 5`）倒地時按 1。騎上馬按 1。
- **log 判定**：只記錄每一次的 `key`／`switch` 行（`dead=` 等）；崩潰（log 突然中斷）才算 FAIL。

### 站 10：A-09（維持費）
- **操作**：（自然回復已關）`player.restoreav magicka 300`，開火焰形態站 10 秒；換黑暗形態站 10 秒。
- **log 判定**：`[T][second] form=fire spent=` 的中位數約 **最大魔力 ×1% ×0.993**（300 → 2.98），`form=dark` 約 **×2%**（5.96），差 20% 以內（用 `build/fix25_reference.py` 的 upkeep 算）；`dM` 約等於 −spent（回魔沒關時會提醒）。

### 站 11：A-10＋E-09（暫停時計時器停住）
- **操作**：火焰形態下按 Esc 停 30 秒再回來；打開背包 30 秒；（遊戲會在背景暫停的話）Alt+Tab 30 秒；存檔再讀檔。
- **log 判定**：每次停住一組 `[T][tick] state=stopped active=…`／`state=running active=…`，兩個 active 相差 < 1000；A-10：停住前後的 `second` 行，你的魔力差不超過兩秒份維持費；E-09：讀檔（`[T][trace] game-ready`）之後照常有 `second` 行。

### 站 12：A-11（魔力歸零 2 秒關形態）
- **操作**：開火焰形態，`player.setav magicka 0`；等形態自己關掉後 `player.setav magicka 300`。
- **log 判定**：第一行你 `m=0` 的 `second` 到 `second … close=1` 相隔 1～4 秒（g），之後 `[T][pap] kind=form-close reason=magicka-empty`。

### 站 13：A-12（血形態扣血）
- **操作**：（自然回復已關）`player.setav health 1000`，開鮮血等 5 秒；`player.restoreav health 1000`、`player.damageav health 300`，等 5 秒；`player.damageav health 600`，等 5 秒。
- **log 判定**：每一行 `second form=blood` 的 `bled` 照 v0.4 血位表（1.1：100% 1.0%、70% 0.6%、30% 0.2%、10% 以下 0，線性；用扣之前的生命÷永久生命算），誤差 15%；`spent=0`（不扣魔力）。滿血、約 70%、約 10% 三段都要有。

### 站 14：A-13（水形態長流）
- **操作**：（自然回復已關）`player.setav health 1000`、`player.setav stamina 200`、`player.setav magicka 300`；開水形態，`player.damageav health 500`、`player.damageav stamina 150`，站 10 秒。（長河部分有做就判：加「長河」、同調三段、隨從在 6 公尺內且受傷。）
- **log 判定**：`second form=water`：生命沒滿時 `dH` 約 +最大生命 2%（1000 → +20）、耐力沒滿時 `dS` 約 +最大耐力 2%（+4）；`dM` 在「−一半維持費～0」之間（付 3.0、長流回 2.4，淨約 −0.6）；長河：`op=HealTarget ctx=form-second`。

### 站 15：A-14（等待／睡覺／快速旅行／對話）
- **操作**：火焰形態、魔力 300：① 按 T 等待 1 小時；② 床上睡 1 小時；③ 地圖快速旅行；④ 跟一名 NPC 對話 30 秒（不選選項）。做完把三個 rate setav 回原值。
- **log 判定**：①②③ 各有一組 `tick stopped／running`，遊戲時鐘走不到 1.5 秒；④ `[T][menu] name=Dialogue Menu` 開著的期間 `second` 照扣（對話不暫停遊戲，只記錄秒數）。

### 站 16：A-15（天氣與雷雨）
- **操作**：`fw c8220`（雷雨）開雷電形態不攻擊，站 10 秒；走進室內站 10 秒；走回戶外；依序 `fw 81a`、`fw c821f`、`fw c8220`、`fw 4d7fb`、`fw c8221`、`fw 81a`，每種站 10 秒。
- **log 判定**：`[T][env]` 依天氣 FormID（`weather=`）：`0x000C8220` 雷雨 wet=1 stormy=0 thunder=1；室內 `interior=1` 三個都 0；`0x0000081A` 全 0；`0x000C821F` 一般雨 wet=1 thunder=0；`0x0004D7FB` 一般雪 wet=1 stormy=0；`0x000C8221` 暴風雪 wet=1 stormy=1 thunder=0。`second … storm=1`（雷雨加電荷）只出現在 thunder=1 的時候，間隔約 3 秒。

### 站 17：A-16（雨中浸濕減速）
- **操作**：`fw c821f` 關主控台等 6 秒；火焰砍 NPC 一刀；`fw 81a`，等 12 秒。
- **log 判定**：那一刀的 `proc … steps=` 裡有 `SoakSlow:15.00/10s`（speedmult 85、10 秒）；約 10 秒後 `[T][remove] … tag=Slow reason=expired`（沒有 remove 行時改看畫面 speedmult）。

### 站 18：A-18（浸濕時長四捨五入與 30 秒上限）
- **操作**：開大地形態。① `player.addperk XX004708`，`fw c821f` 等 6 秒，砍 NPC 一刀，`fw 81a`，等 12 秒。② `player.addperk XX004709`～`XX004716`，MCM「持續時間」拉到 **3**，重做 ①（這次等 32 秒）。做完「持續時間」放回 1。
- **log 判定**：① 那一刀 `SoakSlow:15.00/10s`（10.3 → 10）；② `SoakSlow:15.00/30s`（15×3＝45 夾到 30）；過期時間約 10 秒與 30 秒。

---

## B 段：單體戰鬥逐元素（約 60 分）

前置：戶外晴天中午（`fw 81a`、`set gamehour to 12`），單手武器（先不拿盾）。一個**不是隨從、不是亡靈或魔族**的強盜，`setav health 5000`、`setav aggression 0`。**不要用 `tcai`**。需要 NPC 主動打你的站會寫「點 NPC `setav aggression 1`」，做完改回 0。

### 站 19：B-01（無元素：吸魔、燒魔、滅法）
- **操作**：按 Z 關形態。`player.restoreav magicka 1000`、`player.damageav magicka 50`；NPC `setav magicka 200`。① 普通攻擊一刀。② 重擊一刀。③ `player.restoreav magicka 1000`；NPC `setav magicka 5`；重擊一刀，等 2 秒。
- **log 判定**：① `proc el=none power=0`：`mag=10.50`（有扣魔力時；`overloaded=1` 時是 13.13）、`siphon=10.50`、`burned=5.25`，`hit-end` 的 NPC 魔力比 `proc` 的少 15.75（±0.6）。② `power=1 dispel=1 siphon≈15.75`。③ 那一刀後 NPC `m=0`、之後的 `[T][silence] on=NPC` 行魔力一直是 0、`op=Apply kind=N4_Resolve`（戰意 +1）；你的魔力（`hit-end` 的 you）約 M×85%＋5（±3）。

### 站 20：B-02（無元素重擊不打到自己）
- **操作**：（沒開形態）連續重擊 3 刀，注意你自己。
- **log 判定**：三刀 `steps=` 都有 `SpendMagicka` ≈ 最大魔力 15%。
- **目視**：你自己沒有受擊硬直、音效、血花或「法術命中」特效？

### 站 21：B-03（吸魔量 +1 點）
- **操作**：`player.addperk XX0049AB`，NPC `setav magicka 200`，普通攻擊一刀。
- **log 判定**：`node change=+ id=0049AB` 之後的無元素普攻 `siphon` 10.9～11.1。

### 站 22：B-04（滅法倍率 +1 點）
- **操作**：`player.addperk XX0049F6`，`player.damageav magicka 50`，NPC `setav magicka 200`，普通攻擊一刀。
- **log 判定**：之後 `overloaded=0` 的無元素普攻 `mag` 10.55～10.66（5.25＋5.25×1.02）。

### 站 23：B-05（燒魔倍數）
- **操作**：`player.restoreav magicka 1000`；NPC `setav magicka 2000`；重擊一刀。`player.addperk XX004A05`，補滿兩邊魔力，再重擊一刀。
- **log 判定**：`burned ÷ 你的最大魔力`：加點前 0.150、加點後 0.1605（各 ±0.004）。

### 站 24：B-06＋E-04（反咒與斷咒）
- **操作**：按 Z 關形態，`player.addperk XX0022AE`（反咒）、`player.addperk XX0022AC`（斷咒）。找一名強盜法師 `setav magicka 500`，重擊一刀掛破魔印，8 秒內讓牠施放一次火球、一次專注火焰；接著在牠詠唱時普通攻擊打斷牠，5 秒內牠再詠唱時再打一刀。
- **log 判定**：B-06：`[T][cast] … marked=1 cost=X` 之後 `op=Damage ctx=enemy-cast el=none on=<那名法師>`，強度 ≈ X×1.02（±6%），同一個 ctx 有 `kind=N4_Resolve`；斷咒：`op=Interrupt ctx=hit` 一次（`[T][interrupt] who=法師`），5 秒內沒有第二次。E-04：每次施法只有一行 `cast`（專注法術不是每秒一行），`cost` 與法師前一行 `casting` 的魔力減掉 `cast` 行的魔力相差 < 1。

### 站 25：B-07（火焰附傷強度）
- **操作**：開火焰形態。普通攻擊 5 刀、重擊 3 刀，**每刀之間等 7 秒以上**。
- **log 判定**：`proc el=fire`：用 `rolls=R(10,12)=b` 算 `mag÷(b×1.05)`＝1（普通）或 1.5（重擊）的刀（沒有熱度）：普通 10.5～12.6、5 刀至少 3 種值；重擊 15.7～18.9。

### 站 26：B-08（熱度階梯、白熱、過熱）
- **操作**：生命滿，`player.setav healrate 0`。每隔 3 秒打 NPC 一刀共 3 刀，之後不再打，站在 NPC 2 公尺內等 12 秒。做完 healrate 改回。
- **log 判定**：你身上 `op=Apply kind=N3_Heat1` → `N3_Heat2` → `N3_Heat3`，一次只有一階（每次 Apply 前舊的已 Remove）；白熱中 `ctx=fire-source` 每秒打 NPC；`[T][settle] tag=N3_Heat3` 之後 `op=PayHealth` ≈ 最大生命 10%（過熱）；白熱開始到結束後，你的生命共少約 14%（10%～18%）。

### 站 27：B-10（冰封後重擊碎冰）
- **操作**：冰霜形態連續普通攻擊到冰封，馬上重擊一刀。
- **log 判定**：`N3_Frozen` 之後的冰霜重擊帶 `ev=Shatter`；那一擊 NPC 生命（`proc` 的 tgt → `hit-end` 的 tgt）少 ≥ 最大生命 16%；之後 `Remove kind=N3_Frozen`。

### 站 28：B-11（冰甲與霜膚的寒氣）
- **操作**：先 6 秒以上不用冰砍這個 NPC。`player.addperk XX002055`（冰甲），冰霜形態關再開，站 NPC 2 公尺內 5 秒，退到 6 公尺外 5 秒；`player.addperk XX002041`（霜膚），關再開冰霜，站約 4 公尺 5 秒。
- **log 判定**：`[T][apply]` 寒氣法術 `ESSB_IceArmorChill` 的 `mag=20.00`、霜膚 `ESSB_IceArmorChillWide` 的 `mag=30.00`（speedmult 80／70）。
- **目視**：6 公尺外 speedmult 100、關冰霜後不再減速？

### 站 29：B-12（冰盾）
- **操作**：冰霜形態砍 3 刀，停手 9 秒。
- **log 判定**：`kind=N4_IceShield mag=3`，同時 `N4_IceShieldArmorAV mag=60`、`N4_IceShieldMagicAV mag=12`；約 8 秒後 `remove tag=N4_IceShield reason=expired`。

### 站 30：B-13（電荷、雷的 N 與暴擊、滿格重擊放電）
- **操作**：開雷電形態。普通攻擊 5 刀（每刀隔 1 秒以上、10 秒內接著打），然後重擊一刀。
- **log 判定**：`kind=N4_Charge` 依序 2→3→4→5→6；每刀普攻 `N`＝`charges`＋1；沒暴擊的普攻 ≤ 26.3；滿格重擊之後 `ev=Discharge`、`Remove kind=N4_Charge`，那一擊 NPC 比附傷多掉 150 以上（約 177）。

### 站 31：B-14＋E-05（法術麻痺）
- **操作**：點 NPC `setav aggression 1`（或找會施法的敵人法師）。雷電形態砍到電荷 6，在牠舉手詠唱時用普通攻擊打牠，做 10 次。做完改回 0。
- **log 判定**：B-14：牠詠唱時的滿格普攻，`[T][rng] ctx=hit` 有 `C(0.3)=`；打斷（`op=Interrupt ctx=hit`）次數不是 0 也不是全部。E-05：`[T][casting]` 的 state 有 1～3 與 4～6；中斷後下一行 state 0 或 9。

### 站 32：B-15（反擊）
- **操作**：`player.addperk XX002298`，開一次任一形態再按 Z 關掉。NPC `setav magicka 200`、`setav aggression 1`；格擋擋下一刀，3 秒內普通攻擊一刀，再普通攻擊一刀。做完 `setav aggression 0`。
- **log 判定**：`hurt blocked=1` 之後 `op=Riposte`；下一刀無元素普攻 `riposte=1 siphon` 21.5～22.6；再下一刀 `riposte=0`、吸魔回到約 11。

### 站 33：B-16（岩甲、蓄勁、碎岩）
- **操作**：點 NPC `setav aggression 1`。大地形態：① 砍一刀；② 讓 NPC 打你一下；③ 拿盾格擋一下；④ 砍到岩甲滿層後重擊一刀。做完 `setav aggression 0`。
- **log 判定**：① `N4_RockArmor mag=2`、`N4_RockArmorAV mag=50`；② 被打後 `RockArmor mag=1`；③ `hurt blocked=1` 後 `N4_StoredForce mag=2`；④ 滿層重擊之後 `ev=Knock`（碎岩：範圍那一半由本體處理，log 看到的是倒地）、`Remove kind=N4_RockArmor`、`StoredForce mag=5`。

### 站 34：B-17（地臨強化）
- **操作**：關形態。`player.addperk XX0020D0`，站 NPC 2 公尺內開大地形態；再站 4 公尺外關、開一次。
- **log 判定**：`op=DrainStamina ctx=enter` 打在 2 公尺內的 NPC，強度 ≈ 牠最大耐力一半（±12%）；4 公尺外那次沒有。

### 站 35：B-18（疾風潛行 ×3）
- **操作**：切疾風形態。`tdetect`，蹲下普通攻擊 1 刀；再 `tdetect`，站 NPC 面前讓牠看到，蹲著一刀、站起一刀。
- **log 判定**：`proc el=wind sneak=1` 那刀 25.2～28.4；`sneak=0` 的都 ≤ 9.5。

### 站 36：B-19（風勢與風刃）
- **操作**：換一個沒被風打過的 NPC（或等 15 秒）。疾風形態普通攻擊 3 刀；`tdetect`，蹲下偷襲一刀，`tdetect` 還原。
- **log 判定**：`N4_WindGauge` 2→3，第三刀 `ev=Blade args=1|…` 並歸零；偷襲那刀立刻一個 `ev=Blade`。

### 站 37：B-20（被切的印記多觸發）
- **操作**：先 `player.removeperk XX002055`、`player.removeperk XX002041`。新 NPC：疾風砍一刀、冰霜砍一刀、MCM「印出目標狀態」；再換新 NPC：火焰一刀、冰霜一刀、再印一次。
- **log 判定**：兩行 `pap kind=dump-nearest` 的 `s2` 依序 4、3。

### 站 38：B-21（鮮血吸血）
- **操作**：卸下加生命的裝備。`player.setav health 200`、`player.damageav health 100`；鮮血形態普通攻擊兩刀。
- **log 判定**：第二刀 `proc el=blood power=0 mag` 8.0～10.0，`steps=` 的 `Heal` ≈ 強度 25%（±8%）；那一刀前後你的生命變化寫在證據裡。

### 站 39：B-22（護血池）
- **操作**：`player.addperk XX002131`、`XX002134`，每刀前開主控台 `player.restoreav health 1000`、關掉立刻砍，共 5 刀。做完 `player.setav health 1000`。
- **log 判定**：鮮血 `proc steps=` 的 `BloodGuard:池` 隨刀數增加（每刀約 +2.5～3.2），不超過最大生命 20%。

### 站 40：B-23（同調與升段）
- **操作**：按 Z 關形態，開鮮血形態，連打 30 刀。
- **log 判定**：`kind=N4_Sync` 1、2、…、30（每刀 +1）；`ev=SyncUp` 剛好三次，在第 5、15、30 刀。
- **目視**：升段音效各響一次、第 30 刀起三段光暈？

### 站 41：B-35＋E-02（血痕層數）
- **操作**：換一個沒被血打過的 NPC。鮮血形態連砍到不再增加，停手 12 秒。
- **log 判定**：B-35：`kind=N3_Bleed` 依序 2、3、…、上限 8；停手約 10 秒後 `remove tag=N3_Bleed reason=expired`。E-02（本站＋站 46）：每次 `op=BleedDot`／`PoisonDot` 的 `n=` ≤ 1（一次重套只趕走一個舊的）。

### 站 42：B-24（神聖日夜）
- **操作**：切神聖形態（身上沒有聖佑）。對 3 個沒被神聖打過的 NPC 各砍一刀；`set gamehour to 22`，等 6 秒，再對 3 個新 NPC 各砍一刀。做完 `set gamehour to 12`。
- **log 判定**：「目標沒有聖印記、你沒有聖佑」的第一刀：`env night=0` 時 ≥ 10.08；`night=1` 時 ≤ 10.5。

### 站 43：B-25（神聖對亡靈、聖痕）
- **操作**：（沒有聖佑）屍鬼第一刀；`player.addperk XX002188`，換一個沒被神聖打過的強盜，砍兩刀（2 秒內）。
- **log 判定**：屍鬼第一刀 15.1～18.9；聖痕之後同一名強盜的第二刀 21.6～27.0。

### 站 44：B-26（聖佑階梯）
- **操作**：關形態，等 30 秒。開神聖形態，每隔 3 秒砍同一 NPC 共 4 刀。
- **log 判定**：你身上 `N3_Holy1` → `N3_Holy2` → `N3_Holy3`，一次只有一階。
- **目視**：（可省）getav attackdamagemult／damageresist 的變化，由記錄帶，log 不重讀。

### 站 45：B-27（聖佑減傷）
- **操作**：點 NPC `setav aggression 1`。疾風形態讓牠打你 3 下、讓法師用火球打你一下；切神聖形態砍一刀（聖佑 I），3 秒內再讓牠打 3 下、火球一下。做完改回 0。
- **log 判定**：`hurt form=7 melee=1` 的平均 `lost` ÷ `form=5` 的平均 ＝ 0.88～0.99（約 0.95）；火球的比例（約 0.9）只記錄。

### 站 46：B-28（中毒劑數）
- **操作**：毒素形態：普攻一刀、印；再普攻、印；重擊、印；連續重擊到不再增加、印；停手 16 秒、印（「印」＝MCM「印出目標狀態」）。
- **log 判定**：五行 `dump-nearest` 的 `s7` 依序 3、4、6、10、0。

### 站 47：B-29（水臨強化）
- **操作**：`player.addperk XX0021FC`，`player.damageav magicka 50`，開水形態。
- **log 判定**：`op=RestoreMagicka ctx=enter`，做完（`op-done`）你的魔力＝最大魔力（±1）。

### 站 48：B-30＋E-03（水壓沖刷）
- **操作**：`player.addperk XX0021E4`。找會施放骨甲／石膚的敵人，牠施放後，你先喝一瓶力量藥水，水形態連砍 5 刀；之後主控台點牠 `cast <另一顆增益法術 ID> <牠>`，再砍 5 刀。
- **log 判定**：第 5 刀 `op=Wash`；`[T][wash]` 每個效果一行：只有「手施（castingSource 0／1、type 0／12／13）、有時長、非敵意、非我們的、非召喚」的是 `washed`，其他 `kept`，沒有你自己的效果。E-03：主控台施放的（castingSource=3）是 kept。
- **目視**：護甲術外觀消失、你的藥水還在？

### 站 49：B-31（恐懼、瘋狂、幻視）
- **操作**：有兩個以上強盜的營地。黑暗形態：砍其中一個到詛咒 3 層、再到 5 層；找一隻屍鬼砍到 3 層。
- **log 判定**：`ev=Hallucinate` 有 1（恐懼）與 2（瘋狂）；屍鬼那次 `pap kind=hallucinate … charm=False`（幻視）。
- **目視**：3 層逃跑約 2 秒、5 層攻擊同伴約 3 秒、屍鬼不逃？

### 站 50：B-36（幻影）
- **操作**：`player.addperk XX002235`，點 NPC `setav aggression 1`，`player.setav health 3000`。每次開印（切別的形態砍一刀、切回黑暗砍一刀）後 3 秒內讓牠連打，做 4 次（約 20 擊）。做完改回 0。
- **log 判定**：`N3_Phantom` 之後 3 秒內的 `hurt melee=1`：有落空（`lost` 0）也有扣血（約三成落空，不是全部也不是沒有）；3 秒外沒有落空。

### 站 51：B-32（星痕引爆）
- **操作**：星界形態砍一刀、再一刀，停手 3 秒。
- **log 判定**：`N3_Star mag=2`；約 2 秒後 `settle tag=N3_StarFuse`，接著 `op=Damage el=astral` 約 21（15～22.5，抗性前）與 `Remove kind=N3_Star`。

### 站 52：B-33（印記上身與過期）
- **操作**：換乾淨 NPC，火焰、風、水、星界形態各普通攻擊一刀，每刀後等 15 秒再換下一個。
- **log 判定**：四個元素各一行 `op=Mark el=…`，之後 `remove tag=Mark_<元素> reason=expired`：火／風／星 7～9.5 秒，水 9～11.5 秒。

### 站 53：B-34（終焉後接管）
- **操作**：先 `player.removeperk XX0021E4`。① `player.addperk XX004195`～`XX004199`，冰霜砍 NPC 開冰印，8 秒內切水砍同一名（切掉冰印），5 秒內再用水普攻 3～4 刀（每刀隔 1 秒）。② 換新 NPC，`player.addperk XX0040B4`～`XX0040B8`，火焰開印、8 秒內切水切掉火印、5 秒內水再砍 3～4 刀。
- **log 判定**：冰被切（`ev=End … reason=cut args=2|…`）後 5 秒內的水普攻至少一刀 > 7.35；火被切（`args=1|…`）後的都 ≤ 7.4。

### 站 54：B-37（關形態＝融斷）
- **操作**：換乾淨 NPC，火焰形態砍一刀，站在旁邊按 Z，MCM「印出目標狀態」。
- **log 判定**：`[T][burst]` 之後 `op=Damage ctx=burst el=fire` 12.3～12.9（同調 0 段：12×1×1.05）；之後 `dump-nearest marks=0`。

---

## C 段：玩家被打（約 30 分）

前置：不是隨從的強盜 `setav health 5000`、`setav aggression 1`。你 `player.setav health 1000`、`player.setav magicka 300`，**不要開 `tgm`**。

### 站 55：C-01＋E-06（法盾）
- **操作**：沒開形態，讓 NPC 砍你一下；`player.damageav magicka` 把魔力壓到剩 3，再讓牠砍一下。
- **log 判定**：C-01：`hurt form=0` 那一下 `op=SpendMagicka` ≈ `lost`×0.3÷0.7（±15%）；魔力 ≤ 5 那一下有 `op=HurtHealth`（付不出的部分照扣）。E-06（本站到站 57）：每一下一行 `hurt`，同一下沒有兩行。

### 站 56：C-02（水幕）
- **操作**：開水形態讓牠砍一下。
- **log 判定**：`hurt form=9` 那一下 `SpendMagicka` ≈ `lost`×0.2÷0.8×1.5（±15%）。

### 站 57：C-03（護血致死）
- **操作**：開鮮血形態，生命滿時砍 NPC 讓護血池約 20；NPC `setav attackdamagemult 50`，**先存檔**，讓牠砍你一下。做完讀檔、`setav attackdamagemult 1`。
- **log 判定**：`hurt guardBefore≈20` 之後 `op=GuardPool` 扣光、`op=HurtHealth` > 0；結果是你死亡（`death-event corpse=你`）或神佑救起（`pap kind=divine saved=1`），**不是**停在 1 點生命。

### 站 58：C-04（化法為力 → 超載）
- **操作**：沒開形態，`player.addperk XX00229D`，`player.restoreav magicka 1000`，讓法師用毀滅法術打你一下，等 8 秒。
- **log 判定**：`hurt spell=1` 之後 `op=Apply kind=N4_Overload ctx=hurt`，強度 ≈ 原本傷害（`lost`÷0.7）×0.3（±25%）；2.5 秒以後才出現 `ctx=tick` 的衰減。

### 站 59：C-05（十一項受擊反應與冷卻）
- **操作**：每項加對應節點，讓 NPC 在冷卻內連打你 2 下：反震（大地、岩甲滿）、殘影（疾風、風勢滿）、逆電（雷電）、毒皮（毒素）、靜電（雷電）、怨縛（黑暗、NPC 身上有詛咒）、咒返（未開形態、法師法術）、不屈（未開形態）、冰心（冰霜、生命 < 30%、附近有凍結的敵人）、庇護（神聖、生命 < 30%）、懲戒（神聖、聖佑 II 以上；加「誓約」並用神聖開印牠）。
- **log 判定**：每種反應的冷卻（`kind=N4_RetaliateCooldown`、`N4_ReverseCooldown`、`N4_RetortCooldown`、`N4_GrudgeCooldown`、`N4_SpellReturnCooldown`、`N4_UnyieldCooldown`、`N4_IceHeartCooldown`、`N4_SanctuaryCooldown`）在同一個對象上，冷卻時間（`sec`）內沒有再掛一次；同一下 `hurt` 之後同一個冷卻不出現兩次；懲戒（`N3_Punish`）的層數照列；沒做到的項目列為未測。

### 站 60：C-06（灼身）
- **操作**：火焰形態，`player.addperk XX00200C`，讓身上沒有別的印記的 NPC 近戰砍你一下，3 秒內再砍一下。
- **log 判定**：第一下 `ctx=hurt` 對攻擊者 `op=Mark el=fire` 與 `op=Damage el=fire`（11～13.5）；3 秒內第二下沒有。

### 站 61：C-07（持續傷不分擔）
- **操作**：沒開形態、魔力滿，讓法師用帶持續傷的毀滅法術打你（找不到原版就跳過，這一站會是 NO-DATA）。
- **log 判定**：`hurt dot>0`，同一下 `op=HurtHealth` ≈ dot×0.3÷0.7（±30%）。

### 站 62：C-08（TrueHUD 資源條）
- **操作**：有 TrueHUD：照站 58 做一次化法為力、血溢、蓄勁；打開再關掉 TrueHUD 的選單，讀一次檔。停用 TrueHUD 重開遊戲後重做化法為力（這一步可以留到全卷最後）。
- **log 判定**：`[ESSB][load] TrueHUD found`／`not found` 與超載的 op 列給指揮官。
- **目視**：紫／暗紅／金／淡藍條出現、空的隱藏、關選單與讀檔後條自己回來、停用 TrueHUD 時不出錯？

### 站 63：C-09（切換與 Z 清資源）
- **操作**：雷電形態砍到電荷 4，切到火焰形態；火焰砍同一名 NPC 一刀；按 Z。
- **log 判定**：`switch kind=switch wanted=fire` 之後 `Remove kind=N4_Charge`；火焰那一刀 `ev=End … reason=cut args=3|…` 接著 `ev=Discharge args=4|…`；Z 之後 `N4_Sync` 清掉。

---

## D 段：多目標（約 50 分）

前置：戶外晴天白天。叫出 5 名強盜，站成彼此 2～3 公尺，每名 `setav health 3000`、`setav aggression 0`、五種抗性 `setav … 0`。附近一名隨從、一名中立路人（沒被你打過）。你 `player.setav health 1000`、`player.setav magicka 300`。

### 站 64：D-01（融斷：火冰雷土）
- **操作**：各換一名 NPC：火焰開印按 Z；冰霜開印（不冰封）按 Z；雷電開印按 Z；大地開印按 Z（都只砍一刀）。
- **log 判定**：`ctx=burst` 的 `op=Damage`：火 12.6、冰 10.5、雷 26.25、土 10.5（±3%）；掃描裡的隨從、路人（`scan-c verdict=ally／neutral`）沒被任何 op 打到；沒有 `N3_Downed`。

### 站 65：D-02（融斷：風血聖毒水暗星）
- **操作**：各換一名 NPC，風、血、聖、毒、水、暗、星各開印按 Z（聖那名開印前 `player.damageav health 100`）。
- **log 判定**：`ctx=burst` 傷害約 B_max×1.05（風 9.45、毒 9.45、水 7.35、暗 10.5、星 10.5；血 ×血位倍率最多 ×1.3；聖戶外白天 ×1.2）；沒有 `op=Heal ctx=burst`、沒有 `N3_Guided`；有 `op=Hush`（寂）、風的 `ev=Push`、暗的 `N3_DeathCurse`、毒的 `N3_Catalyzed`。
- **目視**：風那名被吹上天？

### 站 66：D-03（冰封融斷）
- **操作**：冰霜同調 30 刀冰封目標（冰封後別再砍）按 Z；換新 NPC、加 `player.addperk XX002069` 重做；對一名首領（unique／protected）重做。
- **log 判定**：沒節點：冰融斷 31.5（10×3×1.05），沒有 `ev=Shatter`；有節點：`ev=Shatter` 之後的冰傷 ≈ 最大生命 20%（首領 10%），不乘 3。

### 站 67：D-04（三段同調的聖、星）
- **操作**：同調 30 後，聖印記 NPC 按 Z；另一名帶 2 層星痕的星印記 NPC 按 Z。
- **log 判定**：聖 37.8（不是 75.6）；星 31.5，另一筆引爆 15～22.5（不乘 3）。

### 站 68：D-05（融斷距離）
- **操作**：一名帶印記 NPC 站 17 公尺外（點 NPC `getdistance player` 約 1190）按 Z；加 `player.addperk XX0022C0`（收束）重做；拿掉收束、加 `XX004A5F`～`XX004A63`，NPC 站 16 公尺重做。
- **log 判定**：三次 `scan ctx=burst` 裡那名 NPC 的 `scan-c verdict`：無節點 `far`、收束 `picked`、冷寂 5 點 `picked`。

### 站 69：D-06（寂與萬寂）
- **操作**：① 加 `XX0022EC`（雙印）、`XX004A50`～`XX004A54`，讓法師同時帶火＋冰印記，按 Z。② 加 `XX0022CD`（萬寂），換法師：先讓牠中毒並帶詛咒、帶毒＋暗兩個印記，按 Z；10 秒內開雷電砍牠一刀，再按 Z。
- **log 判定**：① `op=DrainMagicka ctx=burst` ≈ 最大魔力 15%（±8%）；② 萬寂：清掉中毒（`PoisonDot mag=0`）與詛咒（`Remove kind=N3_Curse`），各一次 `el=none` 真傷。

### 站 70：D-07（範圍不碰隨從路人）
- **操作**：隨從與路人站 NPC 2 公尺內。雷電加 `XX0020A0`、`XX0020AC`，砍到電荷滿，切換形態後再砍同一名一刀；毒素把另一名毒到 5 劑、殺死它。
- **log 判定**：掃描判為 `ally`／`neutral` 的演員，沒有任何傷害類 op（Damage、Mark、PoisonDot、Slow…）。

### 站 71：D-08（聖灰）
- **操作**：加 `XX002171`，`player.damageav magicka 100`。神聖形態殺一名一般 NPC；殺一名有名字（unique）的敵人；對 essential 角色打到 0。
- **log 判定**：兩名死者各有 `ev=Ash ctx=death` 與 `op=RestoreMagicka` 20；`essential=1` 的死亡行沒有化灰。
- **目視**：化灰外觀、essential 倒下不死？

### 站 72：D-09（亡者歸來）
- **操作**：黑暗形態對一名 20 級以下、有名字的敵人砍到詛咒 5 層殺死；等牠復生結束倒下，點屍體 `resurrect`，再砍到 5 層殺一次。
- **log 判定**：`ev=Raise` 的秒數：13 級以下 240、14～20 級 360（依 `death level=`）；攻擊加成兩次都是 0.5（不是 1.0）。
- **目視**：站起來、結束後回 1.0？

### 站 73：D-10（中毒死亡擴散）
- **操作**：毒到 5 劑的 NPC，旁邊 15 公尺內 2 名、外 1 名，殺死它；加 `XX0021B0`（蔓延）重做。
- **log 判定**：`op=PoisonDot ctx=death` 每秒約 20（±20%）、約 22 秒（19～25）；蔓延後約 34 秒（30～38）；15 公尺外的沒被選中。

### 站 74：D-11（連鎖冰封、火葬、亡魂）
- **操作**：加 `XX002045`、`XX002035`、`XX00224C`，每名目標旁各站 2 名 NPC：① 冰封中用普攻打死；② 用被切或過期的爆燃打死；③ 等死咒爆炸時打死。
- **log 判定**：`ctx=death` 有 `N3_Freeze`（連鎖冰封）、火傷（火葬）、`ev=Hallucinate`（亡魂）。

### 站 75：D-12（不死、飲血、血承）
- **操作**：鮮血同調三段，加 `XX002130`、`XX002135`、`XX00213C`。最大生命 1000，`player.damageav health 850`，殺死流血的 NPC；30 秒內再殺一名。
- **log 判定**：`N5_UndyingCooldown` 只出現一次（30 秒內第二次沒有）；之後第一行 `second` 你的生命約 501（440～520）；`N3_Bloodthirst`。

### 站 76：D-13（焰起強化）
- **操作**：加 `XX00201C`，6 名 NPC 在目標 15 公尺內、1 名在 16 公尺外；對目標開火印。
- **log 判定**：`ctx=hit` 打在旁人（`at≠0`）的火傷剛好 5 人，每人 10.4～12.7。

### 站 77：D-14（印潮、雙斷、臨界）
- **操作**：① 加 `XX0022F2`：3 名 NPC 都帶火印記，水切掉其中一名。② 加 `XX0022CC`：帶印記按 Z，3 秒內開冰霜。③ 加 `XX0022F1`，開疾風。
- **log 判定**：① 另 2 名 `Mark el=water`（ctx=hit、at≠0）；② `ctx=enter` 的 `Mark el=frost`；③ `ctx=enter` 的 `Slow mag=30` 最多 5 人；都沒碰到隨從。

### 站 78：D-15＋E-07（同時死亡與死亡事件）
- **操作**：5 名 NPC 都 `setav health 20` 並掛印記，同調三段按 Z。再給一名 NPC 掛火印記＋中毒，分三次殺三名：武器、中毒持續傷、主控台 `kill`。
- **log 判定**：D-15：每名死者只有一行 `[T][death]`。E-07：`death-event dead=0` 的 `ours=` ≥ 1、`killer=` 正確；主控台 kill 可能只有 `dead=1`（只記錄）。
- **目視**：5 名同時死亡時畫面不卡？

### 站 79：D-16（連殺、無魔）
- **操作**：加 `XX002129`，疾風潛行偷襲殺死帶風印記的 NPC，5 秒內再潛行攻擊一名；加 `XX0022A6`，沒開形態殺死一名法師。
- **log 判定**：`ev=Sneak ctx=death`、`N3_KillStreak` 掛上，下一次潛行攻擊把它用掉；無魔：`ctx=death` 的 `RestoreMagicka`／`RestoreStamina`，多的進 `N4_Overload`。
- **目視**：5 秒內沒被發現？

### 站 80：B-09（火浴）
- **操作**：`player.addperk XX00200D`、`player.damageav health 100`。火焰形態，3 名敵對 NPC 站你 2 公尺內，打到白熱；2 秒後走開。
- **log 判定**：白熱第一秒 `[T][fire-source] hostiles=N bath=1`；之後每秒 `op=Heal ctx=tick` 固定 12×0.1×N（N＝3 時 3.6），走開（hostiles=0）後照回。

### 站 81：D-17＋A-17（火域、冰原、減速上限）
- **操作**：加「火域」「冰原」，MCM「持續時間」拉到 3。火焰融斷 NPC1 留下火域；立刻重開火焰、在火域裡打到白熱，走出去 3 秒、再走回去。冰霜融斷 NPC2 留下冰原，站進去，讓 NPC3 用冰霜法術打你。然後主控台 `set ESSB_SlowCapPct to 30`，再對 NPC2 做一次冰原；做完 `set ESSB_SlowCapPct to 70`、持續時間改回 1。
- **log 判定**：D-17：`domain-new el=fire`／`el=frost`；白熱中的火域引信延長（`ctx=tick` 的 `N3_Heat3`）次數不超過走進去的次數；你在冰原 `N6_FrostDomainPlayer`；冰原裡的敵人 `op=Slow ctx=domain-enemy mag=50`；領域壽命照 `domain-new`→`domain-gone` 列出（持續時間 3 時約 15 秒）。A-17：`mcm global=ESSB_SlowCapPct new=30` 之後的減速 `cast_mag` 都 ≤ 30。

### 站 82：D-18（血池、聖域、神聖領域、潮池）
- **操作**：各加節點：血池、潮池各融斷一次；只加「聖域」，讓聖印記自然到期或被切，留下聖域；再加「神聖領域」融斷一次。每個都站進去，`player.damageav health 500`。
- **log 判定**：你在領域裡（`domain-you inside=`）的每一秒：血池 `op=Heal` 20；聖域 `Heal` 25＋`RestoreMagicka` 20；潮池 `Heal` 15＋`RestoreStamina` 15（與 `ev=Cleanse`）；聖域壽命約 5 秒或 8 秒。

### 站 83：D-19（聖域減敵人傷害）
- **操作**：持續時間拉到 3。強盜在聖域外打你 5 下；聖終焉放聖域，強盜與你都站進去再打 5 下；法師外面、裡面各 3 發火球。做完改回 1。
- **log 判定**：強盜在聖域裡（同一秒 `domain-in el=divine who=牠`）時的 `lost` 平均 ÷ 外面的 ＝ 0.7～0.9。火球只記錄。

### 站 84：D-20＋E-11（地裂、毒霧、死域、星域）
- **操作**：持續時間拉到 3。各加節點：地裂、毒霧、死域、星域，各對一名 NPC 融斷，另一名站 3 公尺內（地裂那名 `setav stamina 0`）；死域那次旁邊站一名路人與隨從，連做 3 次（3 名不同的 A）。做完改回 1。
- **log 判定**：D-20：地裂標記、跌倒（同一目標 8 秒內最多一次）、毒霧 `PoisonDot ctx=domain-enemy`、死域暗傷每秒 4.9～6.7、星域標記。E-11：`domain el=dark` 每秒一行（3 個同時存在），`domain-in` 裡非敵對的演員生命沒少。

### 站 85：D-21＋E-12（領域不碰隨從、5 個同時）
- **操作**：隨從與路人站進死域與冰原；5 名帶火印記的 NPC 站你 15 公尺內，按一次 Z 全部融斷（持續時間 3）；5 個都還在時存檔、讀檔。做完改回 1。
- **log 判定**：D-21：`domain-in` 裡的隨從路人生命沒少、沒有 Slow；同一秒最多 5 個火域。E-12：讀檔前 5 個、讀檔後同一秒不超過 5 個。

### 站 86：D-22（死域裡存讀檔）
- **操作**：在死域裡存檔、讀檔。
- **log 判定**：讀檔（`trace game-ready`）之後照常有 `second`／`domain` 行、沒有 `[ESSB][fault]`。

### 站 87：D-23（瘴氣）
- **操作**：毒素把敵人 A 疊到 5 劑以上，另外 2 名敵人站 A 的 3 公尺內（一名有中毒、一名沒有），隨從也站到 A 旁邊，等 5 秒。
- **log 判定**：`[T][spread] kind=miasma` 每秒 0.5 劑（催毒時 1 劑，瘴氣主線每點 +0.05），`d` ≤ 3 公尺，`to=` 從來不是你；沒有 `ctx=spread` 打在你身上。

### 站 88：D-24（總開關）
- **操作**：火焰砍 NPC 一刀；MCM 關掉「元素魔戰士總開關」，關 MCM 等 10 秒；按熱鍵與 Z；讓 NPC 砍你兩下；殺一名帶印記的 NPC；按 MCM 的狀態按鈕與「印出目標狀態」。最後打開總開關、砍一刀。
- **log 判定**：`mcm global=ESSB_Enabled new=0` 到 `new=1` 之間沒有任何 `op`／`proc`／`hurt`／`death`／`settle`／`second`／`switch`／`burst` 行；MCM 的「印出目標狀態」照常（`pap kind=dump-status`／`dump-nearest`）；打開後的那一刀有 `proc`。

---

## E 段：只剩這三站要另外做（約 15 分）

（E-02～E-07、E-09～E-12 已經在 B／C／D 的站裡判定。）

### 站 89：E-01（星痕引信的三種移除）
- **操作**：星界形態：(a) 砍兩刀，等引信到期；(b) 再砍兩刀，1 秒內主控台點 NPC `dispelallspells`；(c) 換一個 NPC 砍兩刀，1 秒內點它 `kill`。
- **log 判定**：`remove tag=N3_StarFuse` 三種理由都有：(a) `expired`（elapsed ≥ duration）、(b) `dispel`、(c) `death`。

### 站 90：E-08（雪漫城門口的掃描）
- **操作**：到雪漫城門口（5 名以上 NPC），攻擊一名敵人並按 Z；戰鬥中連按 10 次開／關形態；重做一次雷殛與中毒死亡擴散。
- **log 判定**：每一組 `scan` 的 `scan-c`：`picked` 的都是 `hostile=1` 或 `engaged=1`，名單裡沒有你；路人與守衛是 `neutral`；不崩潰。

### 站 91：E-13（FPS）
- **操作**：戶外開 FPS 顯示。① 站在 5 個火域中間 30 秒，記最低與平均 FPS。② 把 10 個領域節點都 `player.removeperk` 拿掉，同地點站 30 秒再記。
- **log 判定**：FPS 不經過 DLL；只列出這一站的 `domain` 行（拿掉領域節點後應該沒有）供參考。
- **目視**：兩組 FPS 差不到 5%？（把兩組數字寫下來）

---

## 結果表（判定器產生，這裡只列目視題）

跑完後你只需要回答這些「目視」題（是／否，必要時一句話）：

| 站 | ID | 目視題 | 是／否 |
|---|---|---|---|
| 3 | A-02 | 13 棵樹的代表節點都在、都是 v0.4 名稱 | |
| 4 | A-03 | 火焰樹上沒有「洩壓」、help 顯示已退役 | |
| 20 | B-02 | 無元素重擊時你自己沒有受擊反應 | |
| 28 | B-11 | 6 公尺外 speedmult 100、關冰霜後不再減速 | |
| 40 | B-23 | 升段音效各一次、三段光暈 | |
| 44 | B-26 | （可省）getav 數值 | |
| 45 | B-27 | （可省）magicresist +10 | |
| 48 | B-30 | 護甲術外觀消失、你的藥水還在 | |
| 49 | B-31 | 逃跑、互打、屍鬼不逃 | |
| 62 | C-08 | TrueHUD 條的外觀、選單與讀檔後回來、停用不出錯 | |
| 65 | D-02 | 風被吹上天 | |
| 71 | D-08 | 化灰外觀、essential 不死 | |
| 72 | D-09 | 站起來、結束後回 1.0 | |
| 78 | D-15 | 5 名同時死亡時不卡 | |
| 79 | D-16 | 5 秒內沒被發現 | |
| 91 | E-13 | FPS 差不到 5%（兩組數字） | |

## 回報方式

1. 存檔、等 2 秒，把 `C:\Users\powde\OneDrive\Documents\My Games\Skyrim Special Edition\SKSE\ElementsSpellblade.log` 複製出來（不用截斷）。
2. 上面「目視題」的答案。
3. 中途當機或重做過哪些站，說一聲。

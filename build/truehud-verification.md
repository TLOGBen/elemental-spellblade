# TrueHUD 顯示三條自訂資源條（超載／護血／蓄勁）可行性驗證

查核時間：2026-09-24 21:29 (+08:00)
範圍：只讀 MO2 profile `normal`、MO2 mods 資料夾、SKSE log；網路只讀 github.com/ersh1/TrueHUD 與 github.com/schlangster/skyui。沒有改任何其他檔案。

## 一句話結論

- **TrueHUD 的「special resource bar」只有一條，而且這個檔案環境裡已經被 Valhalla Combat 占走了**（log 寫 `...Success`）。我們搶不到，就算搶到也只能顯示一條，還會弄壞 Valhalla 的敵人硬直條。**不要走這條路。**
- **三條都要顯示，可以用 TrueHUD 的「custom widget」API**（`LoadCustomWidgets` → `RegisterNewWidgetType` → `AddWidget`）。這組 API 沒有「只能一個 plugin 用」的限制，數量也不設上限；TrueHUD 每一幀會主動呼叫我們 widget 的 `Update()`（輪詢式）。同一個 load order 裡的 True Directional Movement 就在用這組 API（它 DLL 裡有 `TRUEHUD_API::WidgetBase` 的 RTTI，還會載入 `TrueDirectionalMovement/TDM_Widgets.swf`），代表它在這套環境裡能動。
- 代價：**要準備一個 Scaleform（AS2）的 .swf** 來畫條。最省事的做法是借用 TrueHUD 自己的 `TrueHUD_Widgets.swf` 裡匯出的 `ResourceBar` 圖形（但不是公開 API，而且沒有文字標籤）；比較正規的做法是自己做一個小 swf。

---

## 0. 安裝狀態（證據）

| 項目 | 結果 | 證據 |
|---|---|---|
| 啟用中的 TrueHUD | `TrueHUD`（modlist 第 1706 行 `+TrueHUD`） | `profiles\normal\modlist.txt` |
| 中文版資料夾 | 實際名稱是 `界面模组-TrueHUD-真实HUD`（簡體），**已停用**（第 1707 行 `-`），裡面是舊版 DLL 1.1.8.0 | 同上；DLL 的 FileVersion |
| 啟用中的 DLL 版本 | `TrueHUD.dll` FileVersion/ProductVersion **1.1.10.0**，檔案日期 2026-08-30；MO2 安裝檔 `TrueHUD 62775 1.1.10 2026-08-31...7z` | 版本資源；`mods\TrueHUD\meta.ini` |
| 對到的原始碼 | GitHub `ersh1/TrueHUD` master，最新 commit「Version 1.1.10」（2026-08-31）。repo 沒有 tag，所以直接以 master = 1.1.10 為準 | GitHub API commits |
| 執行時 log | `TrueHUD v1-1-10-0`（2026-09-23 21:16 那次啟動） | `OneDrive\Documents\My Games\Skyrim Special Edition\SKSE\TrueHUD.log` |
| 外掛 | `*TrueHUD.esl` 已啟用 | `plugins.txt` |

## 1. TrueHUD 公開 API（`src/TrueHUDAPI.h`，1.1.10）

### 1.1 怎麼取得 API
- **不是透過 SKSE messaging。** TrueHUD.dll 直接 export 一個 C 函式 `RequestPluginAPI`。已確認安裝的 DLL export 表有：`RequestPluginAPI`, `SKSEPlugin_Load`, `SKSEPlugin_Query`, `SKSEPlugin_Version`。
- 標頭檔提供的 inline 包裝：`TRUEHUD_API::RequestPluginAPI(InterfaceVersion)`，裡面做 `GetModuleHandle("TrueHUD.dll")` + `GetProcAddress(..., "RequestPluginAPI")`。官方建議「在 `kMessage_PostLoad` 當下或之後」呼叫（也就是 CommonLib 的 `SKSE::MessagingInterface::kPostLoad`；我們的 `Plugin.cpp` 目前只處理 `kDataLoaded` / `kPostLoadGame`，要加 `kPostLoad`，或直接在 `kDataLoaded` 呼叫也可以）。
- 版本：`enum class InterfaceVersion : uint8_t { V1, V2, V3, V4 }`，DLL 端 V1 到 V4 都回傳同一個 singleton。**請要 `V4`（數值 3），轉型成 `IVTrueHUD4*`。**
  - 附帶觀察：TrueHUD.log 有一行 `RequestPluginAPI called, InterfaceVersion 4` → `requested the wrong interface version`。這是某個已安裝的 mod 要了不存在的 V5（數值 4）；跟我們無關，但也證明 1.1.10 最多只到 V4。
- 移植成本：標頭檔用到的型別 `SKSE::PluginHandle`、`SKSE::kInvalidPluginHandle`、`RE::ActorHandle`、`RE::GPtr<RE::GFxMovieView>` 在我們固定版本的 `native/deps/CommonLibSSE-NG` 裡都有（`include/SKSE/Impl/Stubs.h`）；`Plugin.cpp` 已經 `#include <Windows.h>`。直接把 `TrueHUDAPI.h` 複製進專案就能用（標頭檔自己也寫明要這樣做）。自己的 handle 用 `SKSE::GetPluginHandle()` 取得。

### 1.2 Special resource bar（「特殊資源條」）
相關函式：`RequestSpecialResourceBarsControl`、`RegisterSpecialResourceFunctions`、`FlashActorSpecialBar`、`GetSpecialResourceBarControlOwner`、`ReleaseSpecialResourceBarControl`，外加 V2 的 `OverrideSpecialBarColor` / `RevertSpecialBarColor`。

原始碼（`src/ModAPI.cpp`、`src/HUDHandler.h`、`src/Widgets/PlayerWidget.cpp`）顯示：
- **同一時間只有一個擁有者。** `RequestSpecialResourceBarsControl` 用 `compare_exchange_strong` 搶一個 atomic 的 owner：有人先拿走的話，回傳 **`AlreadyTaken`**（自己已經拿到則回 `AlreadyGiven`）。**先搶到的贏，後來的不會蓋掉前面的。** 只有擁有者自己呼叫 `Release...` 才會釋放。
- **全域只有一條，而且只有一組 callback。** `HUDHandler` 只存一對 `GetCurrentSpecial` / `GetMaxSpecial`（型別 `std::function<float(RE::Actor*)>`）、一個 `bSpecialMode`、一個 `bDisplaySpecialForPlayer`。玩家條、敵人資訊條、Boss 條全部共用這一對 callback。**不可能做出三條。**
- 更新方式：**TrueHUD 輪詢**。`PlayerWidget::Update` 每一幀在 UI 執行緒呼叫 `GetMaxSpecial(player)` / `GetCurrentSpecial(player)`，再 `Invoke("updateSpecial")`。
- 顏色：可以用 `OverrideSpecialBarColor(actorHandle, BarColorType, 0xRRGGBB)` 依角色改色（BarColor／PhantomColor／BackgroundColor／PenaltyColor／FlashColor）。**沒有任何可以設定文字標籤的 API。**
- 位置：玩家區是 TrueHUD 的 Player Widget 上方一條小條（`fPlayerWidgetSpecialBarWidth`，預設寬 70）；敵人資訊條／Boss 條也各有一條 special。
- 玩家這條要真的顯示出來，需要：`bEnablePlayerWidget = 1`，而且 `uPlayerWidgetSpecialMode ≠ 0`（0=Never、1=Dynamic、2=InCombat、3=WhenBarDisplayed、4=Always，見 `src/Settings.h` 的 `PlayerWidgetDisplayMode`）。

### 1.3 Actor info bar（角色資訊條）
- `AddActorInfoBar` / `RemoveActorInfoBar` / `AddBoss` / `RemoveBoss` / `FlashActorValue` / `OverrideBarColor` 只能在「某個角色頭上或 Boss 位置」開出 TrueHUD **既有格式**的條：HP／MP／SP，加上那條共用的 special。**不能新增自訂的資源種類**，所以放不下超載／護血／蓄勁。

### 1.4 Custom widget（自訂 widget）——這是唯一能做出三條的 API
- 流程：
  1. `LoadCustomWidgets(handle, "路徑.swf"(相對 Data/Interface), callback)`
  2. `RegisterNewWidgetType(handle, typeId)`
  3. `AddWidget(handle, typeId, widgetId, "AS2 linkage 名稱", std::shared_ptr<WidgetBase>)`
  4. 需要時呼叫 `RemoveWidget`
- **沒有擁有者限制**：每個 plugin 的 widget 各自存在 `_customWidgets[pluginHandle][type][id]`，同一個 type 底下可以放很多個 id，**三條沒問題**。
- 更新方式：**TrueHUD 輪詢**。`TrueHUDMenu::Update` 每一幀對每個 custom widget 先跑 `ProcessDelegates()` 再跑 `Update(deltaTime)`，而且是在 UI 執行緒（`AdvanceMovie`）上。我們在 `Update` 裡用 `_object.Invoke(...)` 把數值推給 swf 就行。顏色、標籤、位置全部由我們自己的 swf 跟 C++ 決定。
- 生命週期的坑（原始碼證據）：
  - `LoadCustomWidgets` 在 AS 端是 `mcLoader.loadClip(...)`，**是非同步的**。callback 回 OK 只表示「開始載入了」，同一幀馬上 `AddWidget` 可能 attach 不到 symbol。要等一幀以上，或 attach 失敗就重試。
  - `TrueHUDMenu::OnClose()` 會呼叫 `RemoveAllWidgets()`，把**所有 custom widget 清空**；TrueHUD menu 會跟著 HUDMenu 一起開關。所以要監聽 `MenuOpenCloseEvent`（menuName `"TrueHUD"` 開啟時），重新做一次 Load → Register → Add。讀檔（`kPostLoadGame`）、新遊戲（`kNewGame`）之後也要確認 widget 在。
  - 這幾個 API 呼叫最後都會變成 HUD task 排進佇列（`AddHUDTask`），不用自己擔心執行緒；但 **`Update()` 在 UI 執行緒跑**，不要在裡面直接改遊戲狀態。建議遊戲執行緒把三個池的值寫進 `std::atomic<float>`，`Update()` 只負責讀。

## 2. 安裝 DLL 暴露的 API 版本
- DLL 1.1.10.0，對應 master「Version 1.1.10」；`main.cpp` 的 `RequestPluginAPI` 接受 V1 到 V4。**最高 `IVTrueHUD4`。**
- 這次啟動時各 mod 實際要求的版本（TrueHUD.log）：2、2、2、3，還有一個要 4 失敗（見 1.1）。

## 3. 衝突：誰在用 TrueHUD

掃描方式：對 modlist 中所有啟用（`+`）mod 的 `SKSE\Plugins\*.dll` 做字串搜尋，再對照 SKSE log。

| 啟用中的 mod | DLL | 跟 TrueHUD 的關係 |
|---|---|---|
| **Valhalla Combat**（1.3.3，`ValhallaCombat.esp` 已啟用） | `valhallaCombat.dll` | **持有 special bar**。DLL 字串有 `requestTrueHudSpecialBarControl` / `releaseTrueHudSpecialBarControl`；`ValhallaCombat.log`：`Requesting trueHUD API special bar control...` → **`...Success`**。由 `[Stun] bStunMeterToggle = 1` 控制（MCM 預設值是 1，overwrite 的 `MCM\Settings\ValhallaCombat.ini` 沒有改這一項） |
| True Directional Movement 2.3.1 | `TrueDirectionalMovement.dll` | 取得 TrueHUD API（`Obtained TrueHUD API`），用的是 target control + **custom widget**（`TDM_Widgets.swf`）。這是 custom widget 在本環境能用的先例 |
| Precision 2.0.6 | `Precision.dll` | 沒找到 TrueHUD 字串（大概只是透過 TDM／Valhalla 間接配合）；不碰 special bar |
| Better Third Person Selection | `BetterThirdPersonSelection.dll` | 有參考 `TrueHUDInterface`（用來選目標／資訊條），不碰 special bar |
| SCAR、Dynamic Collision Adjustment、Open Animation Replacer | 各自的 DLL | 只有 `TrueHUD.dll` 字串（偵測 TrueHUD 是否存在），不碰 special bar |
| MaxsuPoise 0.3.1、EldenParry、EldenCounter、Elden Rim 系列 | — | 沒找到 TrueHUD 參考 |

**TrueHUD 的設定覆蓋：**
- `界面模组-Untarnished UI-无光UI大修`（modlist 第 1700 行，優先權高於 TrueHUD 本體）提供了 `MCM\Settings\TrueHUD.ini`，裡面寫 **`uPlayerWidgetSpecialMode = 0`（Never）**、`bPlayerWidgetCombined = 1`。所以就算拿到 special bar，**玩家那條目前也被設定成不顯示**。
- 同一個 mod 還蓋掉了 `TrueHUD_Widgets.swf` 跟 `TrueHUD_Assets0~2.swf`（2022 年版本）。
- `Dear Diary Dark Mode`（第 1701 行）也有一份 `TrueHUD.ini`，但同一路徑被 Untarnished UI 蓋過去了。

**如果我們也去要 special bar，會怎樣：**
- Valhalla 在 `kDataLoaded` 設定階段就已經先要走了，我們會拿到 **`AlreadyTaken`**，後面的 `RegisterSpecialResourceFunctions` 只會回 `NotOwner`。**不會「後來的贏」。**
- 假如我們比它早拿到：Valhalla 會記錄 `Failure: TrueHUD API already taken by another plugin`，敵人的硬直條就消失了。而且 callback 只有一組，我們接管之後敵人條也會顯示我們的值。結論是**兩邊都不好**。

**備案比較：**

| 方案 | 能不能三條 | 標籤／顏色 | 工作量與風險 |
|---|---|---|---|
| A. TrueHUD custom widget ＋ 自己做 swf | 可以 | 完全自訂（中文標籤要確認字型，見第 4 節） | 要做一個 AS2 swf（需要 Flash／Animate 或 JPEXS 之類的工具）。C++ 大約一百多行。不受 Valhalla 影響 |
| A'. custom widget，但 swf 借用 TrueHUD 自己的 `TrueHUD_Widgets.swf`，attach 它匯出的 `ResourceBar` | 可以 | 顏色可以（它的 AS 類別有 `init(...)`、`setColor(...)`、`updatePercent(pct, instant)`、`playFlash(long)`）；**沒有文字標籤** | 不用做 swf，但依賴 TrueHUD 內部 symbol 名稱（非公開 API）。目前生效的是 Untarnished UI 版的 swf，匯出清單裡一樣有 `ResourceBar` / `LargeBar`，已確認。同一個 swf 載入兩次的行為沒驗證過 |
| B. SkyUI widget framework | 可以 | 自訂 | SkyUI BSA 裡只有 `SKI_WidgetBase` / `SKI_WidgetManager` / `widgetloader.swf`，**沒有做好的 meter swf**（SkyUI repo 只有 `src/HUDWidgets/meter.fla` 原始檔）。一樣得做 swf，還要多一層 Papyrus 輪詢把 DLL 的值送過去。比 A 更繞 |
| C. 只用畫面通知（`RE::DebugNotification`） | 看不到持續的量表 | — | 最簡單，只適合「滿了」「破盾」這類事件提示 |

## 4. 建議

**最簡單又穩的做法：方案 A'（先驗證）→ 正式版改用 A。一定不要去搶 special bar。**

1. 在 `kPostLoad`（或 `kDataLoaded`）呼叫 `TRUEHUD_API::RequestPluginAPI(InterfaceVersion::V4)`；拿到 nullptr 就改用方案 C 的通知，然後結束。
2. 寫一個 `class EssbPoolBar : public TRUEHUD_API::WidgetBase`，建三個實例（id 0／1／2 對應 超載／護血／蓄勁）。`Initialize()` 呼叫 swf 端的初始化，設好顏色跟位置；`Update()` 讀 atomic 值後 `Invoke("updatePercent", pct)`（A'），或我們自己 swf 的 `setValues(cur, max)`（A）。池子是空的就把 `_object` 的 `_alpha` 設成 0 或 `_visible=false`，不佔畫面。
3. 監聽 `MenuOpenCloseEvent` 裡 `"TrueHUD"` 的開啟事件 → 重新 Load／Register／Add（因為 `OnClose` 會清光）。AddWidget 失敗時下一幀重試。
4. 遊戲邏輯執行緒（我們已有的 hook／task）負責把 GLOB 或效果 magnitude 寫進 `std::atomic<float>`；UI 的 `Update()` 只讀。
5. 標籤：A' 沒有標籤，可以用三種不同顏色（例如 超載＝紫、護血＝暗紅、蓄勁＝土黃）來區分，再用 `DebugNotification` 在第一次出現時提示名稱。正式版（A）在 swf 裡放 TextField 顯示「超載／護血／蓄勁」。

### 要進遊戲驗證的項目
1. `ESSB.log` 印出 `RequestPluginAPI(V4)` 不是 null；TrueHUD.log 出現 `InterfaceVersion 3` / `returned the API singleton`。
2. `LoadCustomWidgets` 的 callback 拿到 `OK`；延後一幀 `AddWidget` 之後，`_object.IsDisplayObject()` 為 true（寫進 log）。
3. 三條都出現在畫面上，位置不跟 Untarnished UI 的 combined player widget（`fPlayerWidgetX=0.04, Y=0.915`, scale 0.6）重疊；分別在 16:9 與使用者實際解析度下看。
4. 數值變化會即時反映（施法／受擊／蓄勁），而且 0 值時會隱藏。
5. 讀檔、快速旅行（有載入畫面）、開關選單、進出 main menu 之後，widget 會自動回來（驗證 `OnClose` 清空後有重新加回）。
6. Valhalla 的敵人硬直條照常顯示（證明我們沒動到 special bar）；`ValhallaCombat.log` 依舊是 `...Success`。
7. （只限方案 A'）借用的 `ResourceBar` 在 Untarnished UI 版 swf 底下的 `init/setColor/updatePercent` 確實存在而且有效；如果畫面空白或 log 報錯，就改做自己的 swf（方案 A）。
8. （方案 A）中文標籤能正常顯示：TextField 要用遊戲字型對應裡有 CJK 字形的字型（例如 `$EverywhereFont`，實際以本環境 `fontconfig.txt` 為準），否則會變方塊。

## 證據檔案（本機）
- `D:\Game\Other\SKSE\MO2\profiles\normal\modlist.txt`、`plugins.txt`
- `D:\Game\Other\SKSE\MO2\mods\TrueHUD\SKSE\Plugins\TrueHUD.dll`（1.1.10.0；exports 如上）
- `D:\Game\Other\SKSE\MO2\mods\界面模组-Untarnished UI-无光UI大修\MCM\Settings\TrueHUD.ini`
- `D:\Game\Other\SKSE\MO2\mods\Valhalla Combat\SKSE\Plugins\valhallaCombat.dll`、`...\MCM\Config\ValhallaCombat\settings.ini`
- `C:\Users\powde\OneDrive\Documents\My Games\Skyrim Special Edition\SKSE\TrueHUD.log`、`ValhallaCombat.log`、`TrueDirectionalMovement.log`
- 原始碼：github.com/ersh1/TrueHUD master（`src/TrueHUDAPI.h`、`src/ModAPI.cpp`、`src/main.cpp`、`src/HUDHandler.*`、`src/Widgets/PlayerWidget.cpp`、`src/Scaleform/TrueHUDMenu.*`、`src/Settings.h`、`swf/HUD/TrueHUD.as`、`swf/Widgets/TrueHUD_Bar.as`）

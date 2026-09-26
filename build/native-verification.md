# Round 19 / 19b native API 核實（先核實、後實作）

## 選擇與固定來源

選 CommonLibSSE-NG，僅 `ENABLE_SKYRIM_SE=ON`、AE/VR/Xbyak/tests OFF。其 QueryInterface 明確支援舊 SKSE Query/Load，SE-only 可在呼叫 REL 初始化前拒絕非 1.5.97；不需要新版 AE 的版本資料匯出。MSVC 19.44（Visual Studio 2022 17.14）支援所需 C++23。對照過 powerof3 分支；本切片不需要該分支多出的 API。

- **NG**: https://github.com/CharmedBaryon/CommonLibSSE-NG commit `b93280e832f263dbef44e44cbe2936622a02f91a`（CMake project 3.6.0 / vcpkg 3.7.0 不一致，以 commit 為準）。下列 NG 路徑均相對該 commit；本機副本 `native/deps/CommonLibSSE-NG/`。
- 對照 PO3: https://github.com/powerof3/CommonLibSSE commit `3181a08602c77ba26775e5c4925c2612a89ed8c6`。
- SKSE 原始碼查證: https://github.com/ianpatt/skse64 commit `25b72352adb6543fa6d0bd3795780672b2e238e0`。不是 2.0.20 SDK 的替代品；舊 loader ABI 由 NG QueryInterface / 本機 2.0.20 版本交叉核實。
- spdlog 1.14.1 `27cb4c76708608465c413f6d0e6b8d99a4d84302`，使用其 bundled fmt（不另抓浮動 fmt）；rapidcsv 8.84 `a98b85e663114b8fdc9c0dc03abf22c296f38241`（NG find_path，SE-only 不編進 VR CSV）；nlohmann/json 3.11.3 `9cca280a4d0ccf0c08f47a99aa71d1b0e52f8d03`（manifest JSON，header-only）。不需要 binary_io、vcpkg 或其他傳遞下載。

## 4.11 查證表逐項

| 原表項目 | 核實結果／實際採用 API | 來源（上述 repo + commit） |
|---|---|---|
| CommonLib 分支、入口 | NG SE-only；`extern "C" __declspec(dllexport) bool SKSEPlugin_Query(const SKSE::QueryInterface*, SKSE::PluginInfo*)`、`bool SKSEPlugin_Load(const SKSE::LoadInterface*)`；`QueryInterface::RuntimeVersion() const -> REL::Version`、`SKSEVersion() const -> uint32_t`、`IsEditor() const -> bool`；`PluginInfo::{infoVersion,name,version}`。不匯出 AE `SKSEPlugin_Version`。 | `CMakeLists.txt`; `include/SKSE/Interfaces.h`; `include/SKSE/Impl/Stubs.h`; `src/SKSE/Interfaces.cpp` |
| 命中事件 | `TESHitEvent::{NiPointer<TESObjectREFR> target,cause; FormID source,projectile; stl::enumeration<Flag,uint8_t> flags}`；Power=1、Sneak=2、Bash=4、Blocked=8。`BSTEventSink<T>::ProcessEvent(const T*, BSTEventSource<T>*) -> BSEventNotifyControl`；`ScriptEventSourceHolder::GetSingleton()`；`AddEventSink<T>(BSTEventSink<T>*)`。**不是 PO3 HitData 的位元值**。 | `include/RE/T/TESHitEvent.h`; `include/RE/B/BSTEvent.h`; `include/RE/S/ScriptEventSourceHolder.h`; `src/RE/S/ScriptEventSourceHolder.cpp` |
| 即時施放 | `Actor::GetMagicCaster(MagicSystem::CastingSource) -> MagicCaster*` virtual 0x5C；`kInstant=3`；`virtual void MagicCaster::CastSpellImmediate(MagicItem*,bool,TESObjectREFR*,float,bool,float,Actor*)` virtual 1。採 `(spell,false,target,1.0f,false,0.0f,player)`（effectiveness 1.0 = 不縮放；見下方更正），不覆寫 magnitude。**原文「SKSE DoCombatSpellApply 就是這支」不成立**，詳見下方 binary 證據與限度。 | `include/RE/A/Actor.h`; `include/RE/M/MagicSystem.h`; `include/RE/M/MagicCaster.h`; `include/RE/A/ActorMagicCaster.h`; 本機 executable 下述追蹤 |
| 目標效果查詢 | `bool MagicTarget::HasMagicEffect(EffectSetting*)`; `bool HasMagicEffectWithKeyword(BGSKeyword*, uint64_t)`，第二參數原文漏寫。**本切片不呼叫兩者**，狀態層仍由 Papyrus 負責，不能憑推測填第二參數。 | `include/RE/M/MagicTarget.h`; `src/RE/M/MagicTarget.cpp` |
| GLOB／記錄 | `TESGlobal::value` float；`TESDataHandler::GetSingleton()`；`template<class T> T* LookupForm(FormID,std::string_view)`；`TESForm::LookupByID(FormID)`；`TESForm::As<T>()`。manifest 只存 local ID，data-loaded 一次解析，命中不查 EditorID。 | `include/RE/T/TESGlobal.h`; `include/RE/T/TESDataHandler.h`; `src/RE/T/TESDataHandler.cpp`; `include/RE/T/TESForm.h` |
| Papyrus 註冊 | `SKSE::GetPapyrusInterface() -> const PapyrusInterface*`; `PapyrusInterface::Register(...) const -> bool`，接受 `bool(RE::BSScript::IVirtualMachine*)`；`IVirtualMachine::RegisterFunction(string_view,string_view,F,bool=false)`；global callback 第一參數 `RE::StaticFunctionTag*`。三個函式均用預設非 tasklet 註冊。 | `include/SKSE/API.h`; `include/SKSE/Interfaces.h`; `include/RE/I/IVirtualMachine.h`; `include/RE/N/NativeFunction.h` |
| Address Library | **並非全部不依賴位址**。（round 19 用過的 Actor IsBlocking，SE ID 36927，19b 已不再呼叫。）條件執行 `TESConditionItem::IsTrue(ConditionCheckParams&) const -> bool` 用 SE ID 29090；singleton 與 LookupByID 等也經 REL。先驗 runtime + VFS `Data/SKSE/Plugins/version-1-5-97-0.bin`，才 `SKSE::Init`。缺檔拒絕且不進 REL。 | `src/RE/A/Actor.cpp`; `src/RE/T/TESCondition.cpp`; `include/REL/ID.h`; `src/REL/ID.cpp`; `src/SKSE/API.cpp`; `include/RE/Offsets.h` |
| SKSE／loader | 本機唯讀 FileVersion：`SkyrimSE.exe`=1.5.97.0，`skse64_1_5_97.dll`=0,2,0,20。檢查 QueryInterface 的 runtime 與 packed SKSE version（2.0.20=0x02000140）。不需要網路讀其他網站。 | 本機 `D:/Game/Other/SKSE/SkyrimSE/`; NG `src/SKSE/Interfaces.cpp`; SKSE `skse64/PluginAPI.h`, `skse64_common/skse_version.h` |

## 額外會用的已核實 API

`Actor::{IsDead(bool a_notEssential=true) const,IsPlayerTeammate() const,IsCommandedActor() const,GetEquippedObject(bool) const}`、`TESForm::Is(FormType)`（`FormType::Ammo`、`FormType::Projectile`）、`PlayerCharacter::GetSingleton()`、`TESObjectWEAP::GetWeaponType() const -> WEAPON_TYPE`。來源：NG `include/RE/{A/Actor,P/PlayerCharacter,T/TESObjectWEAP}.h` 與對應 src。武器 enum 弩=9；CTDA 597 弩=12，兩套值分開處理。

選擇狀態使用原條件 API：`TESConditionItem`、`CONDITION_ITEM_DATA::{functionData,comparisonValue,flags}`、`FUNCTION_DATA::FunctionID`、`ConditionCheckParams(TESObjectREFR*,TESObjectREFR*)`（`include/RE/T/TESCondition.h`）。現場 `IsPowerAttacking`、`IsSneaking`、右手 `GetEquippedItemType`、血量門檻、`GetRandomPercent` 由與舊 CTDA 相同的引擎條件函式讀取。**雷電仍用引擎逐段 GetRandomPercent，不換自製 RNG**；纯選擇器接受四段抽樣比較結果，首成功選 R5→R2，否則 R1。離線分佈測試區分 round-18 整數模型與連續模型，未假稱測到遊戲 RNG。

## 畫面通知（round 19b，F1）

- API：`void RE::DebugNotification(const char* a_notification, const char* a_soundToPlay = 0, bool a_cancelIfAlreadyQueued = true)`，NG `include/RE/M/Misc.h:18`；實作 `src/RE/M/Misc.cpp:44` 以 `REL::Relocation` 呼叫 `Offset::DebugNotification`＝`RELOCATION_ID(52050, 52933)`（`include/RE/Offsets.h:581`），SE 用 ID 52050。這就是 Papyrus `Debug.Notification` 的引擎函式。字串以 UTF-8 傳入（`/utf-8` 編譯），與本模組 Papyrus 既有的中文通知相同編碼。
- 執行緒：一律經 `SKSE::GetTaskInterface()->AddTask(std::function<void()>)`（NG `include/SKSE/Interfaces.h` `TaskInterface::AddTask(TaskFn)`、`src/SKSE/Interfaces.cpp:166`）排到主執行緒，不在事件或 Papyrus 執行緒直接碰 HUD。
- 資料載入（主選單）時 HUD 還不存在：此時的通知（例如 manifest 缺檔造成的故障）先存起來，讀檔／新遊戲（`kPostLoadGame` 成功、`kNewGame`）後顯示。
- 何時顯示：故障（附原因，只一次）；讀檔／新遊戲時 MCM 已關「DLL 命中附傷」，或 debug ≥ 1 時「運作中」；MCM 切換開關時；debug ≥ 2 每次附傷一行（元素＋法術 EditorID），同類通知 1 秒最多一行。log 行全部保留。
- 版本（遊戲／SKSE）與 Address Library 拒絕：發生在 `SKSE::Init` 之前，DLL 不可呼叫無法定位的遊戲函式，因此不能自己顯示。`ESSBController.Setup`（讀檔後約 2 秒）在 `ESSB_Enabled==1`、`ESSB_NativeWanted==1` 且 `ESSB_NativeHit!=1` 時顯示通用通知「DLL 命中附傷未運作（未安裝、遊戲／SKSE 版本或 Address Library 不符，或已故障）」；細分原因只在 log 的 `[ESSB][refuse]` 行。

`SKSE::GetMessagingInterface()->RegisterListener(EventCallback*) const -> bool`，消息 `kDataLoaded/kPreLoadGame/kPostLoadGame/kNewGame`（`include/SKSE/Interfaces.h`）。`SKSE::log::log_directory() -> optional<filesystem::path>`（`include/SKSE/Logger.h`, `src/SKSE/Logger.cpp`）。MSVC `__try/__except` 是編譯器功能，不是 CommonLib 的包裝；以無 C++ 解構物件的外層 SEH 呼叫內層 C++ catch，fault latch 禁止本 process 重啟處理。19b 起 log 不再用 mutex：每行一次 `WriteFile` 寫到 `FILE_APPEND_DATA` handle，SEH 中斷不會留下被持有的鎖（round 19 的 `logMutex` 若在 `fputs` 內發生存取違規會自鎖）。

## CastSpellImmediate 與 DoCombatSpellApply：不等價（round 19b 更正）

round 19 本節寫「兩條路等價、都到同一個 0x14054CD10」，**這個結論錯了**，已撤回。兩條路最後確實都到 0x14054CD10，但前面的關卡不同。證據全文：`build/fix19-binary-evidence.txt`，由 `python -B build/fix19_binary_evidence.py` 從本機 `SkyrimSE.exe`（1.5.97，sha256 寫在檔頭）以 llvm-objdump 重新產生；下列每個位址的完整反組譯都在該檔。

| 位址 | 角色 |
|---|---|
| 0x1409582C0 | Papyrus `DoCombatSpellApply` 註冊的 native thunk（字串 RIP-relative 引用可追到） |
| 0x1406282E0 | DoCombat 本體：疾病（SpellType 1）抗性擲骰；`GetMagicCaster(3)`（vfunc 0x2E0）；呼叫 0x14054CBE0（magnitude 0、hostile-only false） |
| 0x14054CBE0 | DoCombat 用的施法包裝：設定 spell／target 後呼叫 0x1401007F0 決定走哪條路 |
| 0x1401007F0 | `GetSpellType()`（vfunc 0x298 = MagicItem 虛擬函式 0x53）落在遮罩 0x412 = {1 Disease、4 Ability、10 Addiction} 時為真 |
| 0x140552E80 | 「目標身上已有此法術的 active effect」檢查（MagicTarget vfunc 0x38 = GetActiveEffectList 逐一比對）。**只有遮罩 0x412 的類型才會走到**；為真時跳過施放 |
| 0x14054C950 | 其他 SpellType 的路：先 `CheckCast`（MagicCaster vfunc 0x50 = 索引 0x0A；成本、條件），通過才呼叫 0x14054CD10 |
| 0x14054C5F0 | `ActorMagicCaster` vtable（0x141637490，Address Library ID 257613）slot 1 = `CastSpellImmediate`：沒有 CheckCast，沒有同法術關卡，直接呼叫 0x14054CD10 |
| 0x14054CD10 | 兩條路共用的找目標／套用核心 |

結論：

1. **同法術關卡（0x140552E80）存在，但只對 Disease／Ability／Addiction 生效。** 審查指出「DoCombat 在目標已有同一法術的效果時不施放」——對這三類法術成立；我們釋出的 53 筆 `ESSB_Hit_*` 全是 SpellType 0（證據檔末段由 ESP 讀出），DoCombat 對它們會走 0x14054C950，不經過這個關卡。
2. **兩條路仍不等價。** DoCombat 對 SpellType 0 多一道 `CheckCast`（成本與施法條件）與施法狀態機（state 5、雙持查詢、失敗時的聲音／提示）；`CastSpellImmediate` 沒有這些，直接進 0x14054CD10。DoCombat 對疾病另有抗性擲骰，並在目標是玩家時送疾病通知；我們只施放 SpellType 0、目標從不是玩家，這兩個分支不適用。
3. **DLL 用 CastSpellImmediate 是刻意的。** 舊 entry 51（Apply Combat Hit Spell）每一刀都施放，不看目標身上是否已有同法術效果；每個附傷法術都帶 30 秒的 `ESSB_EngagedEffect`，所以「同一元素 30 秒內連砍兩刀，兩刀都要有附傷」。CSI 每刀都套用，行為與 entry 51 一致；就算將來有人把附傷法術改成 Ability 類型，CSI 也不會被 0x140552E80 擋掉。探針卡第 5 步實測這件事。
4. **effectiveness 必須是 1.0，round 19 的 0.0 是錯的（本輪新發現並修正）。** 0x14054CD10 把 effectiveness 存進套用 visitor（0x140551980），逐一效果呼叫 `AdjustActiveEffect(effect, effectiveness)`（vtable slot 0x1C → 0x140550CD0 → 0x14053DEB0 → 0x140540360）。0x140540360：effectiveness 等於 1.0（常數 0x1415232D8）或小於 0 時不動；否則 magnitude = max(|magnitude| × effectiveness, 1.0)。所以 round 19 傳的 **0.0 會把每一刀附傷壓成 1 點**。DoCombat 對 SpellType 0 走 0x14054C950，傳的正是 1.0 常數，SPEL magnitude 原封不動；round 19 文件說「DoCombat 傳 0」只看到疾病那條路（0x14054CBE0 的 `xorps xmm1`）。本輪改為 `CastSpellImmediate(spell, false, target, 1.0f, false, 0.0f, player)`：effectiveness 1.0 = 不調整；magnitude override 0.0 = 不覆寫（0x140551980 只有非 0 才覆寫），倍率與抗性全交給引擎。`blameActor` 在 0x14054C5F0 不被讀取，歸屬由玩家 caster 決定。本切片沒有任何 raw address 呼叫，這些 VA 只作證據。

血量 Papyrus `GetActorValuePercentage` 的本機追蹤 0x14094ABB0→0x1405D6500：current/permanent，分母零回 1.0。但本切片直接沿用 CTDA 640 門檻比較，避免不同 getter 語意猜測。

## 有意限縮／不能宣稱的事

- 無 hook、trampoline、patch、engine code 寫入；依賴庫的 REL 呼叫是已核實 library API。GLOB value 寫入是規格要求的遊戲資料狀態更新，不是引擎程式碼 patch。
- 無 entry-51 fallback；DLL 缺少或關閉不補送 base 或差額附傷。既有狀態層保留，不把第二切片的印記／升階搬進 DLL。
- `ESSB_NativeHit` 是不存檔的可用狀態（GLOB Constant flag 避免上次 save 殘留 1）；偏好另存 `ESSB_NativeWanted`，狀態由 DLL data/new/postload 重算。
- SEH 無法保證任意引擎內部損壞都能恢復；僅攔截可處理例外，停止再次施放。Address Library 損毀可能觸發 CommonLib 的 fail-fast，因此初始化前驗證本機已核實的資料檔 SHA-256，以拒絕未知/損毀檔案而非進入 fail-fast。

## 最終建置與證據範圍

- 實際工具：Visual Studio 2022 Community 17.14、MSVC `19.44.35229.0`（toolset 目錄 `14.44.35207`）、Windows SDK `10.0.26100.0`，x64 `/MD`、`/EHsc`。`native/toolchain.lock.json` 保存版本與雜湊；`native/build.py` 從建置樹讀回 cl 版本與路徑、SDK、cmake 版本寫進 receipt，與 lock 不符即失敗。
- 執行階段：`/MD` 動態連結 VC++ 執行階段。VS 17.10 起 `std::mutex` 的 constexpr 建構子需要 msvcp140.dll ≥ 14.40，舊版執行階段會當機；Microsoft 也只保證執行階段不舊於建置工具組（14.44）。玩家需裝 VC++ 2015–2022 可轉散發套件 ≥ 14.44（本機 System32 為 14.51）。
- 本機 VS 路徑沒有可執行 CMake，改用官方 GitHub 的 CMake `3.31.8` Windows x64 portable；archive SHA-256 `81aa9964dbabd71fe02e7ec50472fd3ad56138c49944515ece9001efbff8d719`。位於 `native/deps/`，不安裝到系統，也不進 package。
- spdlog bundled fmt 的 `FMT_VERSION=100201`，即 `10.2.1`。所有建置依賴 HEAD 與 tracked 工作樹由生成器檢查；沒有浮動版本下載。
- `build/fix19-native-test.log`（round 19b，取代 round 19 的 39,888 組，其中約 34,320 組是正式路徑不會交給 select() 的 veto／血量浮點組合）：
  - A 228 組＝`BuildInput` 能產生的全部輸入（11 元素 × 右手 弓／弩／其他 × power × sneak；血形態 4 檔＋無檔；雷電 5 檔）對照 round-19 快照 ESP 74 段 CTDA oracle；38 個可選法術全部可達。Python 產生 fixture 時另外對舊 ESP 證明三個化約（非血形態結果與血量無關、非雷形態與 RNG 無關、首成功之後的 RNG 值無關）以及四個 veto 在舊 ESP 也不給法術。
  - B 1,376 組 mock 引擎狀態：`BuildInput` 發出的每個 CTDA 查詢（函式、參數、比較）與舊 ESP 相同，RNG 惰性抽取、血量只在血形態讀，產生的 Input 正確（含 85／50／20／0% 邊界兩側）。
  - C 4,368 組命中事實：`Filter`／`ResolveWeaponType` 與 Papyrus `OnWeaponHit`／`ResolveHitWeaponType` 的逐行轉寫一致（來源 14 種 × 投射物 × 兩手各 12 種狀態，加上其餘每個閘門）。
  - D 2,000,000 次雷電抽樣經 `BuildInput`：整數與連續兩種 RNG 模型的分佈。遊戲的實際 RNG 分佈沒有被離線測試取代。
  - 5 個刻意注入的錯誤（移除 blocked 過濾、改血量門檻、弓改用 power、雷電不 break、允許法杖）各自讓測試失敗。
- `build/fix19-audit.json`：除清空 `ESSB_P_HitProc` 外，4,066 筆既有 records 的 flags/subrecords 完全相同；既有 FormID 無變動或刪除。只新增 GLOB `ESSB_NativeHit=0052D1`、`ESSB_NativeWanted=0052D2`。Papyrus 差額算式與狀態腳本逐位元組保留。
- `build/fix19b-build.log` 保留 round 19b 的完整生成回歸（round 19 的 09-22 舊證據 `fix19-build.log`、`fix19-audit.log`、`fix19-pe.txt`、`fix19-dll-pe.txt`、`fix19-fix8.log`、`fix19-papyrus.log`、`fix19-address-map.json` 描述的是被退回的 round-19 DLL，round 20 起移到 `build/retired/2026-09-22-round19/`，不再當證據）；`build/fix19-negative.json` 及對應 logs 驗證 DLL 缺失／來源過期皆在寫入 package 前失敗。`native/out/build-receipt.json` 綁定 DLL 的生成來源（native/src、include 含生成的 ManifestData.h、tests、cmake、CMakeLists、兩個 lock、native/build.py、build/fix19_native.py、truth CSV）與 DLL SHA-256；19b 起不再包含整個 build_v03.py／settings.json（改 MCM 字串不必重建 DLL），`require_fresh` 另外重新產生 ManifestData.h 文字與磁碟比對，FormID 或 Address Library 設定改變仍會判定過期。Address Library 路徑改為 settings.json 的 `address_library_bin`。

### 雷電規格衝突的處理

snapshot 的 74 段中，R5→R1 priority 遞減；按 smoke 證實的最低 priority 規則，舊 release 會由 R1 勝出。舊 HITPROC 僅以 random=99 檢查，未揭露這個問題。本輪選擇遵守 acceptance 明列的「lightning five-band random at N=1」，以 R5→R1 首成功執行原來各段的 RNG 門檻，**不把原 ESP 的反向 priority 行為宣稱為等價**。原真值表全部案例仍相同。這是可感知的已知差異，五分鐘卡與交付摘要均需保留。

### 執行期尚未證實

尚未部署或啟動遊戲。DLL 實際載入、事件時序、各外部 mod 的 0x1D／抗性倍率、Vancian 次數、MCM 互動與關閉／缺檔行為須依 `fix19-probes.md` 驗收；本地反組譯與 mock 回歸不能替代這些結果。

## Round 20（N2）：命中時算強度

2026-09-25。依然是 CommonLibSSE-NG commit `b93280e832f263dbef44e44cbe2936622a02f91a`（`native/deps/CommonLibSSE-NG/`，下列路徑相對它），SE 1.5.97 單一執行期，沒有 hook、trampoline 或寫遊戲記憶體；新增的全部是程式庫 API 與既有引擎路徑。程式分層：`HitPipeline.h`（濾網）→ `EngineFacts.h`（引擎答案 → 輸入，純函式）→ `HitMath.h`（施放計畫，純函式）→ `Selection.h`（計畫步驟 → 法術記錄）→ `Plugin.cpp`（讀引擎、施放、通知）。

| 用途 | API（NG 路徑:行） | 查證結論 |
|---|---|---|
| 以覆寫強度施放 | `MagicCaster::CastSpellImmediate(MagicItem*, bool, TESObjectREFR*, float effectiveness, bool, float magnitudeOverride, Actor*)` virtual 1（`include/RE/M/MagicCaster.h:46`） | 沿用 19b：effectiveness 1.0（不縮放）；覆寫值由套用 visitor 0x140551980 寫進**每一個**效果（`native-verification-2.md` 第 10 節，判定 NO），0 代表不覆寫。所以每個需要自己數值的東西都是單效果法術：雷的削魔（`ESSB_Util_DrainMagicka`，覆寫＝傷害 × 0.5 × 削減倍率）、吸血（`ESSB_Util_RestoreHealth`）、護血池、耗魔、削耐回耐、真傷；附傷法術本身只剩傷害效果＋無強度的已交戰標記（建置時 `fix19_native.verify` 讀 ESP 確認）。滅法印與沉默用 0（保留記錄上的強度：沉默的 MagickaRateMult −100）。 |
| 施放對象是玩家自己 | 同上，`a_target` = 玩家 | 自身耗魔用新的「有害但不敵對」效果（`ESSB_Native_SpendMagickaEffect`，旗標 0x8A14，無 hit event），避免自己打自己觸發受擊路徑。**未實測**，探針卡無元素步驟看數字。 |
| 覆寫值不能改時長 | 同上（參數只有 magnitude） | 沉默 1～8 秒各做一顆固定時長法術（`ESSB_Native_Silence_1..8`），DLL 依節點、首領減半、持續時間倍率挑一顆；浸濕減速固定 10 秒；護血池 86400 秒（Papyrus 在離開形態時清掉）。 |
| 重擊、潛行攻擊 | `TESHitEvent::Flag::kPowerAttack = 1 << 0`、`kSneakAttack = 1 << 1`（`include/RE/T/TESHitEvent.h:15-16`） | 取代 N1 的 CTDA `IsPowerAttacking`／`IsSneaking`；弓弩以潛行攻擊旗標當重擊。旗標在引擎何時設（是否等於「未被發現」）：**未實測**，探針卡風潛行與弓潛行射擊看強度。 |
| 節點點數 | `Actor::HasPerk(BGSPerk*) const`（`include/RE/A/Actor.h:573`，`src/RE/A/Actor.cpp:699`，`Offset::Actor::HasPerk`） | 與 `ESSBTrees.GetMainRank` 同一個 4 次二分搜尋、同一組 FormID（主線 0x4000 + 節點 × 15 + 點 − 1、分支 0x2000 + 節點 × 4 + 序號）；perk 指標在資料載入時以 `TESDataHandler::LookupForm<BGSPerk>`（`include/RE/T/TESDataHandler.h:49`）一次解析（主線 2925 筆缺一即故障；分支空格為 null＝沒有）。無形態樹路線 0／1 在形態開啟時讀作 0（同 `ESSBController.Rank/Br`）。每擊最多約 20 條主線 × 4 次 ＋ 十幾個分支的 HasPerk，每次掃玩家 perk 陣列。 |
| 生命、魔力 | `ActorValueOwner::GetActorValue`／`GetPermanentActorValue`（`include/RE/A/ActorValueOwner.h:15-16`）；`Actor::GetActorValueModifier(ACTOR_VALUE_MODIFIER::kTemporary, av)`（`include/RE/A/Actor.h:526`，`src/RE/A/Actor.cpp:268`，ID 37524） | 血位比例＝目前 ÷ 永久（與 Papyrus `GetActorValuePercentage` 相同，分母 0 時 1.0，`native-verification-2.md` 18.1）；「還差多少滿血」與護血上限用最大值＝永久 ＋ 暫時（Papyrus `GetActorValueMax` 同式）。 |
| 室內 | `TESObjectREFR::GetParentCell()`（`include/RE/T/TESObjectREFR.h:413`）、`TESObjectCELL::IsInteriorCell()`（`src/RE/T/TESObjectCELL.cpp:140`，讀 cellFlags） | v0.4 2.10「室內、地城沒有環境加成」；日夜與天氣仍讀 Papyrus 每 5 秒寫的 `ESSB_EnvNight`／`ESSB_EnvWet`。 |
| 目標與玩家身上的效果 | `MagicTarget::GetActiveEffectList()`（`include/RE/M/MagicTarget.h:84`）、`ActiveEffect::{flags, magnitude, GetBaseObject()}`（`include/RE/A/ActiveEffect.h:44-52, 110-111`，`src/RE/A/ActiveEffect.cpp:15`） | 唯讀走訪、跳過 `kInactive`／`kDispelled`：血印記（N2 以它代表「流血中」）、沉默、護血池強度、餘響與雙生標記、魔法護甲／披風關鍵字。`HasMagicEffectWithKeyword` 的第二參數語意未查清（19 版已註記），所以不用它，改逐一比 `BGSKeywordForm::HasKeyword`（`include/RE/B/BGSKeywordForm.h:24`）。 |
| 餘響標記用完移除 | `ActiveEffect::Dispel(bool)`（`src/RE/A/ActiveEffect.cpp:8`，ID 33286）經 `SKSE::GetTaskInterface()->AddTask` 在主執行緒執行 | 依 `native-verification-2.md` 第 1 節「寫入遊戲狀態丟 AddTask」。任務只跑一次、不重排自己（每秒點的禁忌不適用：本輪沒有每秒點）。排隊到執行前的那一瞬間 DLL 忽略這顆標記，避免同一幀兩刀各算一次餘響。 |
| 亡靈魔族、死靈施法者、首領 | `TESObjectREFR::HasKeyword`（`src/RE/T/TESObjectREFR.cpp:554`）、`Actor::IsInFaction`（`src/RE/A/Actor.cpp:1743`）、`TESNPC::npcClass`（`include/RE/T/TESNPC.h:268`）、`MiddleHighProcessData::commandedActors`（`include/RE/M/MiddleHighProcessData.h:147`）、`Actor::IsEssential()`（`src/RE/A/Actor.cpp:805`）、`TESActorBaseData::IsEssential/IsProtected/IsUnique`（`include/RE/T/TESActorBaseData.h:101-108`） | 與 Papyrus `IsUndeadOrDaedra`、`IsNecromancer`（職業／陣營／有受命者）、`IsVIPTarget` 同一組判斷；Skyrim.esm 的關鍵字、職業、陣營 FormID 與 ESSBController 屬性用的是同一批（manifest 逐一核對）。 |
| 施法者判定 | `Actor::GetEquippedObject(bool)`（`include/RE/A/Actor.h:541`）+ `As<SpellItem>()` | 同 `ESSBNoForm.IsSpellUser`：任一手拿法術，或身上有魔法護甲／披風效果。 |
| 亂數 | 無 API：`HitMath.h` 的 SplitMix64，資料載入時以 `QueryPerformanceCounter` 與 `GetTickCount64` 播種 | 只由命中 sink 使用（sink 本身有重入保護，同一時間只有一個處理者）；雷用整數 1～25（v0.4 的期望 13.0／22.35／23.38 只有整數模型成立），其他元素在區間內連續均勻。不存檔、不影響設計狀態。原生 D 組以 10 萬次抽樣檢查分布。 |

### 仍未實測（探針卡 `build/fix20-probes.md`）

- 同一顆法術以新強度重套，會取代舊效果還是並存（護血池依賴「取代」）；探針卡看作用中效果只有一個「護血」且數字累加。
- `kSneakAttack` 旗標的實際語意、自身耗魔法術是否安靜、`AddTask` 驅散餘響的時序、天氣分類在雨天回 2。
- 覆寫後外部天賦（0x1D、Ordinator）仍在 `AdjustForPerks` 放大（`native-verification-2.md` 16），通知上的數字是放大前的值。
- 命中 sink 在哪個執行緒（沿用 19b 的未知，P1）。

## Round 21（技能樹照 v0.4 重建）：DLL 的改動（0.21.0）

本輪 DLL 沒有新增任何 hook、trampoline、vtable patch 或記憶體寫入，也沒有新的引擎 API；只多讀三個自有效果、多施放兩類自有法術，全部沿用上面已查證的呼叫。

| 項目 | 用到的 API（已在上方查證） | 本輪做法 |
|---|---|---|
| 讀「反擊」視窗、「寂」層數、「寂滅已用」標記 | `ForEachRunningEffect` 走 `ActiveEffect` 清單；`ActiveEffect::magnitude`（`include/RE/A/ActiveEffect.h:110`） | 玩家身上的 `ESSB_RiposteWindowEffect` 有就算反擊視窗；目標身上的 `ESSB_HushEffect` 取最大 magnitude 當寂的層數；`ESSB_HushSpentEffect` 有就算已用。三個 FormID 由 `ManifestData.h`（產生器）給，載入時解析，缺任何一個就判 DLL 故障、不命中（跟既有效果一樣）。 |
| 用掉反擊視窗 | `ActiveEffect::Dispel(bool)`（`include/RE/A/ActiveEffect.h:90`）；`SKSE::GetTaskInterface()->AddTask` | 跟餘響標記同一條路：命中當下只排一個主執行緒 task，task 先收集再驅散，外包 C++ 與 SEH 兩層防護；排隊期間 `ReadPlayer` 把視窗當成不存在，所以同一個視窗不會用兩次。兩種標記共用 `QueueMarkerDispel(Marker)`。 |
| 寂滅標記、浸濕時長 | `MagicCaster::CastSpellImmediate`（`include/RE/M/MagicCaster.h:46`） | 覆寫值只能改強度、不能改時長（上方已查證），所以：寂滅打完施放固定 10 秒的 `ESSB_HushSpent`（不覆寫）；浸濕減速依「10 + 0.3 × 浸濕持續點數」四捨五入成整秒、再乘持續時間倍率，夾在 1～30，挑 `ESSB_Native_Soak_<秒>`（10 秒沿用 round 20 的 `ESSB_Native_SoakSlow`），強度覆寫＝減速百分比（裁決 R6）。 |
| 吸魔量、滅法倍率、燒魔倍數、寂滅 | 無新 API（`HitMath.h` 純計算） | 吸魔 ×(1 + 0.05 × 點)、反擊視窗內再 ×2；滅法倍率 1 + 0.02 × 點（小滅法同倍率）；燒魔倍數 1 + 0.07 × 點；寂滅：寂 ≥3 層且沒有已用標記，這一發滅法倍率 +0.5（裁決 R5）。都不吃節點倍率（v0.4 表格明寫）。 |
| 節點位置 | 無 | `node::` 常數改由 `build/fix19_native.NODE_IDENTITY`（v0.4 名稱）經身分表查格位產生；`build/fix21_identity.py` 禁止 C++ 自己寫 `NodeId`／`BranchId` 字面值。 |

測試：原生 A0 錨點 6 → 10（新增吸魔量＋滅法倍率、反擊、寂滅、浸濕時長四個手算值），A 組情境 694 → 814（新增 A7：吸魔量×反擊視窗×擁有與否×重擊、滅法倍率×燒魔倍數、寂的層數×已用×擁有、浸濕點數×持續時間倍率），跟 `build/fix20_reference.py` 逐一相同。

### 仍未實測（探針卡 `build/fix21-probes.md`）

- 反擊視窗的驅散時序（同一幀兩刀時，第二刀是否還看得到視窗；設計上 `riposteDispelQueued` 讓它看不到）。
- 冰甲斗篷（原型 35，magnitude＝半徑呎）在 1.5.97 的實際半徑與只對敵對者生效（沿用原版斗篷的 hostile 條件）。
- 寂在 N5 之前遊戲內不會出現，寂滅的遊戲內效果要等 N5；本輪只有離線測試。

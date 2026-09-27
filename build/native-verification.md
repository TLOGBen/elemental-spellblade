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

## Round 22（N3）：目標狀態層搬進 DLL（0.22.0）

這一輪沒有新的逆向；用到的引擎行為都出自 `build/native-verification-3.md`（第 2、4、5、6、10、12、15、16 節）與 round 19／`native-verification-2.md` 已查證的施放路徑。下面只寫「怎麼用」與本輪額外反組譯確認的一點。

| 項目 | 依據 | 本輪做法 |
|---|---|---|
| 狀態存在哪 | nv3 §4（`ActiveEffect::magnitude`、`duration`、`elapsedSeconds` 可讀） | 每種目標狀態與你身上的階（熱度、聖佑、懲戒……）各一顆自有 MGEF（`build/fix22_records.py`，0x005400 起），層數＝`ActiveEffect::magnitude`、剩餘時間＝`duration − elapsedSeconds`。DLL 不存任何設計狀態、不做存檔序列化。 |
| 時長要連續值 | 本輪反組譯（08:28）：套用 visitor 0x140551980 先寫強度覆寫，再經 0x14053DEB0 → 0x140540360；後者在 effectiveness ≠ 1 且 MGEF 帶 NoMagnitude（0x400）時只把 duration 乘 effectiveness | 狀態 MGEF 全部 Script 原型＋NoMagnitude；DLL 以「強度覆寫＝層數、effectiveness＝想要秒數 ÷ 記錄秒數」施放。記錄秒數＝v0.4 預設，實機若不是這樣會退化成預設時長。**未實測**（探針卡 A 段的印記 15 秒消失間接看得到）。 |
| 重套 | nv3 §5、§6 | 一律先 `Dispel(true)` 舊的一顆再 `CastSpellImmediate`（R3）；驅散期間移除 sink 以 `selfDispel` 略過自己造成的移除。 |
| 強度覆寫會寫進每個效果 | nv2（visitor 0x140551980） | 聖佑三階的法術同時帶武器傷害（AV 154 `AttackDamageMult`，round 21 誤用 34 `MeleeDamage`）與護甲效果，所以以覆寫 0（不覆寫）施放，記錄值照用。 |
| 到期／驅散／死亡 | nv3 §2 | 只有要結算的效果（印記、白熱引信、熔燒、星痕引信、死咒、浮空、冰封、恐懼／瘋狂）掛空的 `ESSBStub` 腳本讓移除事件出現。sink 只讀：`elapsed ≥ duration` 且沒死＝到期，丟 `AddTask` 結算；其他（驅散、死亡）不結算。除錯等級 3 時寫 `[ESSB][N3-1]`。 |
| 死亡快照 | nv3 §10（`dead=false` 時效果還在） | `TESDeathEvent dead=false` 讀屍體的印記與層數，送 `ESSB_Death`（8 個值，含是否玩家擊殺）給 Papyrus 的擊殺掛勾（N5 前）。 |
| 反應本體 | SKSE `ModCallbackEvent`；Papyrus `StringUtil.Split`（本機 skse64 2.0.20 有） | DLL 送 `ESSB_Open／End／Frozen／Hallucinate／Judgment／Splash／Shatter／Landing／Rise`，strArg＝8 個值以 `|` 串接、定點 `%.5f`（Papyrus 字串轉 Float 不認指數）。 |
| 每秒點 | nv3 §12 | 既有 100 ms 計時執行緒每 tick 一個主執行緒 task：熱度／聖佑退階、白熱火源、放血與瘟疫的每秒傷害（`TargetSecond`）。 |
| 沖刷（R5） | nv3 §15 | `Executor::Wash`：法術類型為 spell／scroll／staff、`castingSource` 為左右手、有剩餘時間、非 hostile 非 detrimental、不是本模組、不是召喚／綁定武器／復活。除錯等級 3 寫 `[ESSB][N3-3]`。 |
| 執行緒（X1） | nv3 §16、§18 | 命中、效果移除、死亡、計時 task、Papyrus 原生函式各第一次觸發時寫 `[ESSB][X1] … same／DIFFERENT`。輸入與施法事件 sink 本輪不存在（N4／N6）。 |
| 防護 | — | 每個 sink 與 task 都是 SEH 外框＋C++ catch；本輪起每個 `ESSBNative` 原生函式也經 `Guard`（C++ catch＋`SehInvoke` 的 SEH 外框，C++ 例外 0xE06D7363 放行給 catch 保留訊息）。 |

測試：原生 A0 10、A 814、B 939、C 8442、D 1,140,000 照過；新增 `native/tests/status_test.cpp`：S 組 78 個情境（133 個預期操作，每一列後比對兩邊 board，對 `build/fix22_reference.py` 另寫的 Python 模型）、W 組 489 筆記錄對照（TagOf、Settles、Read、Lower 對 `build/fix22_records.py`）；`build/fix22_verify.py` 對測試注入 7 個錯誤全部失敗。參考模型與 C++ 是同一個實作者寫的，可能有同一個理解錯誤；手算核對了 5 個情境。

### 仍未實測（探針卡 `build/fix22-probes.md`）

- effectiveness 縮放時長（上面第二列）與 NoMagnitude 的組合。
- X1、N3-1、N3-2（本模組沒有 DLL 測試熱鍵，改看鮮血持續傷的掉血速度）、N3-3。
- 聖佑的 `AttackDamageMult` 數字、冰甲寒氣的第二顆互斥效果（條件讀 DLL 的凍結效果）。

### Round 22 審查修正：引擎端可測、總開關、放血法術

| 項目 | 做法 |
|---|---|
| 引擎端抽出 | `native/include/StatusEngine.h`：ReadBoard、DispelWhere（先收集再驅散、self-dispel 旗標）、RunPlan（Lower → 先驅散舊的再施放；死掉的目標不施放傷害）、Washes／Wash（裁定 R5）、OnRemoved（到期／驅散／死亡＋同一幀的冰晶）、PlanSettle、CastSpells／TaggedEffects。`Plugin.cpp` 只剩轉接：`EffectLists`（ForEach 跑中的效果、ForEachIncludingEnding 含正在結束的那一顆）與 `RealEngine`（Dispel(true)、CastSpellImmediate、付血、ModEvent）。沖刷用到的 SpellType／CastingSource 數字以 `static_assert` 釘在 CommonLib 的列舉上。 |
| 放血法術 | `ResolveStatus` 改成解析 `CastSpells()` 整份清單；`engine_test` 把每一種 op 降階後的法術都對這份清單（原本漏了 `ESSB_Util_BleedTick`，第一次放血 tick 會讓 `SpellById` 丟例外、DLL 故障停用）。 |
| 總開關 | `Enabled()`＝`Active()` 且 `ESSB_Enabled == 1`：結算 task、效果移除 sink、死亡 sink、每秒 task、每個原生函式（`Guard`）。命中路徑本來就由 `HitPipeline.h Filter` 擋。 |
| 探針 log | 除錯等級 3：`[ESSB][N3-1][L3]`（加 `crystals=`）、`[ESSB][N3-2][L3] dot=… dispelled=N`（每次重套 DoT 先驅散了幾顆）、`[ESSB][N3-3][L3]`（沖刷逐效果）。 |
| 瘴氣／瘟疫 | 披風記錄與 `Op::kMiasma` 拿掉；`TargetSecond` 每秒讀每個中毒敵人（`MiasmaDoses`／`PlagueChance`），對 3 公尺內的敵人 `SpreadDoses`（讀—長—先驅散再重套，同 R3）。 |

測試：E 組（假引擎）與 C++ 突變 10 個見 `native/out/build-receipt.json` 的 `mutants`。仍未實測：上面全部的遊戲內行為（探針卡 `build/fix22-probes.md`）。

## Round 23（N4：你的資源與受擊，2026-09-26）

本輪的 DLL 做法，每一項標出依據（`nv2`＝native-verification-2、`nv3`＝native-verification-3、`thud`＝truehud-verification、「推論」＝沒有直接查證）。實作者沒有進遊戲；「待實測」的項目寫在探針卡 `build/fix23-probes.md`。

| 項目 | 依據 | 做法 |
|---|---|---|
| 你被打（受擊） | nv2 §15（TESHitEvent 在扣血之前送出，近戰／投射物／法術三條路都是）；nv3 §18 P8 | 命中 sink 分兩支：攻擊者是你（原本）與**目標是你**（新）。目標是你的那支只讀事實（攻擊者、法術或武器、有沒有投射物、格擋旗標、你當下的生命／魔力／超載／護血／殘影與餘魔視窗），排一個 task；task 讀扣血後的生命，`lost = before − after`。同一幀多下依序接起來（下一下的 before 當上一下的 after）。純邏輯在 `native/include/Hurt.h`。 |
| 分擔池（法盾、水幕、護血） | v0.4 5.1／5.8／5.11「PERK 先減、DLL 反推」；nv2 §15 | PERK（`ESSB_P_BaseRules` 與分支）在扣血前把傷害乘 (1 − s)，法術那一半 Spell 分頁條件是 MagicDamageFire／Frost／Shock 三個關鍵字 OR；DLL 用 `h × s ÷ (1 − s)` 反推擋下的量並扣魔力（法盾先花超載）／耐力（餘魔）／護血池（不夠的部分立刻從生命補）。DLL 的 `hurt::ShareOf` 用跟 PERK 同一組條件判斷 s。v0.4 接受這是估計值。總開關關著時 PERK 也不切（條件加 `ESSB_Enabled == 1`）。 |
| 你的資源是效果 | R3；round 22 的效果層（Dispel(true) → 重套、強度＝計數、時長用 effectiveness） | 62 個新狀態種類（`build/fix23_records.py`，0x005500 起）接在 round 22 的 `StatusKind` 後面，同一套 Read／Lower／先驅散再施放。AV 類（岩甲護甲、冰盾護甲與魔抗、逼近移速）是 Peak Value Modifier，強度＝值、時長用記錄的秒數。 |
| 鏡射全域變數 | v0.4 2.3「PERK 條件要讀的門檻由 DLL 鏡射」；先例 `ESSB_NativeHit` | DLL 在每個會改你資源的計畫之後、以及每個計時器 tick，把 ESSB_Sync、ESSB_SyncStage、ESSB_Charge、ESSB_Resolve、ESSB_IceShield、ESSB_RockArmor、ESSB_Wind、ESSB_Bracing 寫成效果的值（`TESGlobal::value`，不是 hook）。Papyrus 不再寫它們（只有新 schema 的歸零）。 |
| 目標正在詠唱（法術麻痺、斷咒） | nv3 §8 | 讀目標 `magicCasters[0..3]`：state 1–4，或 state 6 且法術是專注型，算「正在詠唱」。打斷用 nv3 §9 的 `InterruptCast(false)`，排 task 做。探針 N4-2 在除錯等級 3 逐次記錄狀態變化。 |
| 反咒 | nv2 §6、nv3 §18 N4-1；R7 | `TESSpellCastEvent`（施法已扣魔之後送出）：施法者帶你的破魔印（`ESSB_ManaBreakEffect`）時，`CalculateMagickaCost(caster)`（雙手施放再乘 GMST `fMagicDualCastingCostMult`）× (1 + 2%／無元素樹等級) × 真傷倍率的真實傷害，戰意 +1。未開形態才生效。舊的 Papyrus 施法動畫事件路徑刪除。 |
| 逼近 | nv2 §6 | 同一個施法事件：15 公尺內敵對的施法者 → 2 秒移速 +30%（AV 效果）與化法為力 ×2，每 6 秒一次。 |
| 共鳴層 | v0.4 2.3、5.13；推論（掃描用 round 22 的 `HostilesAround`） | 星痕引爆送 `Op::kResonance`，引擎端數 15 公尺內身上有星痕的敵人（加上被引爆的那個，最多 8），加成共鳴層；到門檻（10，天穹 7）1：1 換成闇宙（上限 15）。 |
| 碎岩的 3 公尺環、冰心 | 推論（同 `HostilesAround`） | 引擎端掃描、對每個目標各施放傷害／削耐或把凍結量表補滿。 |
| 超載每秒衰減、風形態衝刺回補 | round 22 的 100 ms 計時器（每次一個 AddTask） | 計時器 task 每秒一次：超載在等待效果（3 秒，蓄流 6 秒）消失後每秒扣最大魔力 5%（不竭 −0.2%／點，最低 2%）。衝刺中（`IsSprinting`）每 100 ms 依 GMST 的衝刺耗耐算回補（20%，疾風 50%）。 |
| TrueHUD 資源條 | thud；本機 `MO2/mods/TrueHUD/SKSE/Plugins/TrueHUD.pdb`（1.1.10）以 llvm-pdbutil 讀出 `IVTrueHUD1` 的 21 個虛擬函式與位移、`WidgetBase` 的成員位移與大小 176 | 自寫宣告（`native/include/TrueHud.h`，`static_assert` 釘住版面；TrueHUD 是 GPL-3.0-or-later，不 vendor 它的標頭）。`RequestPluginAPI(0)`，沒有 TrueHUD 就整段不做（不報錯）。載入 `TrueHUD_Widgets.swf`、借它的 `ResourceBar`，四條（超載紫、護血暗紅、蓄勁金、同調淡藍）只有顏色、沒有文字；空池隱藏；TrueHUD 選單重開（讀檔、換場景）時重新載入。不動特殊資源條（Valhalla 在用）。**待實測**：位置不重疊、即時更新、讀檔後恢復。 |
| 化身 | v0.4 5.2；推論 | 10 秒視窗內，DLL 的節點讀取把當前形態元素的持續傳奇主線讀成滿點（被動數值、機率型的立即生效）。主動型的持續傳奇效果（範圍本體）沒有強制觸發一次 → 節點 PARTIAL-N5。 |
| 多段觸發 | v0.4 2.6、5.7 | 切掉風印記的那一擊：同一個 task 裡把這一擊的附傷再跑 N−1 次（第 2 次起 ×0.5、各自擲骰）、狀態與你的資源的 +1 照算（聖佑逐次升階，不等成熟）。 |
| 死亡快照 | round 22 的 `TESDeathEvent dead=false`（nv3 §10） | 加第 9 個值：屍體上的最後一擊潛行標記（`ESSB_N4_LastHitSneak`，1 秒，值＝形態元素）；Papyrus 的連殺讀它。 |
| 防護 | — | 新 sink（受擊支線、施法、選單）與新 task（受擊、施法、打斷、碎岩、冰心）都是 SEH 外框＋C++ catch；新原生函式 `FormEnter`、`SetSync` 經 `Guard`。 |

測試：原生 A0／A／B／C／D、S（round 22）、E 照過；新增 `native/tests/self_test.cpp`：S 組 115 個情境（198 個預期操作，每一列後比對你與目標兩邊的 board，對 `build/fix23_reference.py` 另寫的模型；三種擲骰模式）、W 組 84 筆（鏡射全域變數、新 op 的施放、護血池、N4 記錄）、X 組 10 筆直接檢查；手算錨點 14 個（`build/fix23_fixture.py HAND`）。C++ 原始碼突變共 19 個（round 23 新增 9 個：SelfLayer.h 4、Hurt.h 4、Status.h 的三重奏 1）全部讓測試失敗。參考模型與 C++ 是同一個實作者寫的，可能有同一個理解錯誤；手算錨點與突變是對這一點的補強。

### 仍未實測（探針卡 `build/fix23-probes.md`）

- 受擊反推的估計（`lost` 與畫面上的扣血一致）、分擔比例在遊戲裡的實際扣魔。
- N4-1（`CalculateMagickaCost` 與 NPC 實際少的魔力）、N4-2（詠唱狀態序列、中斷時魔力不退）。
- TrueHUD 資源條的位置與恢復；沒有 TrueHUD 時不壞。
- X1：受擊 sink、受擊 task、施法 sink 的執行緒。

### Round 23 審查修正（2026-09-26）

| 項目 | 依據 | 做法 |
|---|---|---|
| 分擔池付不出來的部分 | 指揮官裁定；推論（與主控台 `damageav health`／Papyrus DamageActorValue 同一條 actor value 路徑） | 新 `Op::kHurtHealth`：`RestoreActorValue(kDamage, Health, −x)`，**不留 1 點**。護血池不夠（護血改 50%）、法盾／水幕魔力不夠（付不出的魔力 ÷ 每點成本＝傷害），都照實扣血；扣到 0 以下時 `ESSB_Lethal` 照常送出（神佑照常處理）。這條路在 0 生命時會不會觸發引擎的死亡處理**沒有直接查證**，探針卡「護血致死」一格驗證。 |
| 持續傷（DoT）不分擔 | 指揮官裁定；`vendor/wbDefinitionsTES5.pas` 的條件函式清單 | PERK 的條件函式裡**沒有能讀效果持續時間的**（有 HasMagicEffectKeyword、EPMagic_SpellHasKeyword、GetCurrentCastingType 等，沒有 duration），所以法術那一半的條件做不到「排除有持續時間的效果」。改在 DLL：受擊 task 讀剛打中你的那個法術在你身上、帶持續時間的扣血效果（ValueModifier／DualValueModifier、主數值生命、有害），Σ 強度 ×剩餘秒數＝PERK 切過之後的持續傷；把 PERK 切掉的那一份（× s ÷ (1 − s)）**當下一次扣回來**，不向池收費。**剩下的差距**：時間點被提前（持續傷原本分幾秒扣，切掉的那份一次扣完）；持續傷中途被解除（藥水、法術）時，已提前扣的不會退；只看「同一個法術」的效果，法術以外的來源（附魔、毒）本來就不在毀滅關鍵字條件內。 |
| TrueHUD 版本 | thud；本機 1.1.10 的 PDB | `GetFileVersionInfoW` 讀 TrueHUD.dll 的檔案版本，低於 1.1.10 就不啟用小工具（不報錯）；`LoadCustomWidgets` 送出後 10 秒（100 個計時器 tick）沒有回呼就放棄這次、再送一次。 |
| 同調門檻 | 指揮官裁定 | DLL 讀 `ESSB_SyncT1..3`（預設 5／15／30），與 Papyrus 永續用的是同一份。 |

測試：SELF S 123 個情境／215 個預期操作（新增：巨大一擊穿過小池致死、池部分擋住、法盾／水幕魔力不夠、DoT 扣回、蓄能 ≥1、SyncT 3／8／12），手算錨點 23 個；C++ 突變 21 個（Hurt.h 新增 2 個：付不出的魔力、DoT 扣回）全部讓測試失敗。仍未實測：上面四項的遊戲內行為（`build/fix23-probes.md`）。

## Round 24（N5：融斷、死亡處理、反應本體，2026-09-26）

本輪的 DLL 做法（0.24.0），每一項標出依據（`nv3`＝native-verification-3、「推論」＝沒有直接查證）。實作者沒有進遊戲；遊戲內要看的列在 `build/fix24-probes.md`。

| 項目 | 依據 | 做法 |
|---|---|---|
| 範圍掃描 | nv3 §10（`ProcessLists::highActorHandles` 只能在主執行緒；先收集 handle 再動手）；v0.4 2.9 | 每個事件（命中、受擊、過期、融斷、死亡、開形態、原生函式）在主執行緒 task 裡**只掃一次**：`BuildCrowd` 逐一 `handle.get()` 收集 `NiPointer`（保住生命期）、讀位置與敵意，`StatusEngine.h SelectCrowd` 依 2.9 篩（敵意或敵對陣營、或帶 30 秒「已交戰」自有標記；不是你、不是隨從（隨從另列為盟友，只給聖光治療，最多 4 人）、不是受命者、活著、已載入），依距離排序、上限 24；之後才讀每個人的效果（Board、身體、抗性），純函式（`native/include/Reactions.h`）算出整份計畫，最後才施放。sink 裡不掃描。 |
| 群體計畫 | round 22 的效果層（Dispel(true) → 重套） | `StatusOp::at`／`StatusPlan::at`：每個 op 記它作用在群體第幾人（0＝事件本身的演員）；`RunOp` 先 `Select(at)` 再照舊 Lower／Dispel／Cast。計畫上限 96 → 512（放堆積，不壓引擎的堆疊）。 |
| 本體事件 | 裁定 R4 | 冰封、聖裁、濺血、越線、碎冰、落地、放電、風刃、過熱九種事件由 DLL 的本體流程（`RunBodies`）當場消耗，`SendEvent` 拒送（`BodyOnly`）；開印、終焉、幻覺照送（經驗、特效、恐懼／瘋狂 AI）。本體推出的新事件（連鎖終焉、強制開印）同一輪走完，最多 160 個。 |
| 留給 Papyrus 的一半 | 裁定 R4（推力、恐懼 AI、復生 AI 與召喚上限、化灰崩解、不解除潛行留 Papyrus；神佑、領域照舊） | 新 ModEvent：`ESSB_Push`（種類、公尺、落地傷害、中心的 FormID、推不動時減速）、`ESSB_Ash`、`ESSB_Raise`（階、等級上限、秒數、攻擊加成、永久）、`ESSB_Sneak`、`ESSB_Domain`。推力中心在計畫裡是群體成員編號（浮點數裝不下 FormID），送事件時換成那個演員的 FormID。 |
| 死亡處理 | nv3 §9（`dead=false` 在 `KillImpl` 裡同步送出，效果還在；兇手已寫好） | 死亡 sink 只處理 `dead=false`、不是你、而且屍體上有本模組的東西或是你殺的／你的僕從（`DeathCounts`）；sink 裡只讀屍體（Board、身體、抗性、等級）與兇手（你、你的瘋狂 NPC＝狂宴、你的僕從＝亡衛），交給 task；task 掃一次群體、`PlanDeath`、施放。Papyrus 的 `ESSB_Death` 快照與擊殺掛勾（`ESSBGuard.OnActorKilled`）刪除。爆燃與死咒結算在傷害**之前**先在目標掛 1 秒標記（火葬、亡魂、冥召讀它），同一幀的死亡看得到。 |
| 融斷 | v0.4 2.5、5.1、5.2 | 原生函式 `Burst(元素)` 取代 `BurstMarks(半徑, K)`：一次掃描（15 公尺、收束 20 公尺，+0.3 公尺／點），範圍內每個帶印記（或疊印殘印）的目標，每個印記照自己的終焉本體 × K_sync（1／1.5／2／3）× 通用與冷寂融斷主線 × 該樹「X印記的融斷」主線（雷斷另加電荷）；每目標一次終焉冷卻判定；寂（每清一種 +1，上限 5，寂上限 +1／每 5 點）與燒魔、萬寂、斷界、地斷、颶風、墜星的融斷那一半、回流（溢出進超載）、雙斷與安全閥的視窗都在同一份計畫。 |
| 有時限的數值效果 | 反組譯 0x140540360（非雙持施放時 effectiveness 只縮放強度，不縮放時長）；round 21 減速的先例 | 碎甲、攻擊削弱、各抗性削減、治療削減、耐力凝滯、移速、毒抗、魔抗增益：每種 20 個整秒法術（`build/fix24_records.py`，共用原本的 Util 效果），時長照持續時間倍率取整秒。 |
| 新狀態種類 | round 22 的效果層 | 14 個（0x005600 起）：火葬／死咒擊殺的 1 秒標記、不死冷卻、雙斷、安全閥、光耀、星鏈冷卻、血承 7 個 AV（Peak Value Modifier，只保留最新一個）。安全閥的 PERK 改讀 `ESSB_N5_SafetyValve`。 |
| 火浴 | v0.4 5.3（C3 重做） | 計算從計時器裡抽成純函式 `PlanFireBath`（首秒定人數、之後每秒 B_max × 0.1 × 人數），可以離線測。 |
| 原生函式的執行緒 | nv3 §10；round 22 的原生函式同一做法 | `Burst`、`FormEnter` 註冊時沒標 callable-from-tasklets，VM 在主執行緒執行，所以它們裡面的一次掃描也在主執行緒（R3）。 |
| 防護 | — | 死亡 sink（SEH＋C++ catch）→ task（`DeathGuarded`：SEH → `DeathCpp`：C++ catch）；所有新增的掃描都在既有 task 內；新原生函式 `Burst` 經 `Guard`；刪掉 7 個 Papyrus 本體用的原生函式（BurstMarks、SetGuided、DotRemaining、ForceOpen、EndMark、Shatter、Detonate）與註冊。沒有 hook、trampoline、vtable 修補，也不寫遊戲記憶體；DLL 不存任何設計狀態、沒有存檔序列化。 |

測試：原有的 A0／A／B／C／D、S（status）、E、SELF 照過；新增 `native/tests/reaction_test.cpp`：R 組 85 個情境（460 個預期操作，每個群體成員與你的 board 都比對；對 `build/fix24_reference.py` 另寫的 v0.4 模型，三種擲骰模式；25 個手算錨點由 `build/fix24_fixture.py` 逐一核對）、W 組 328 個接線檢查、X 組 13 個直接檢查（距離、Around、at 蓋章、本體專用事件、融斷範圍與 K_sync、火浴）；`engine_test.cpp` 加假 process list（2.9 資格、最近優先、上限、盟友）與假死亡事件（`DeathCounts`、一次完整死亡：隨從與中立 NPC 沒被施放）；9 個新原始碼突變（Reactions.h 8、StatusEngine.h 1），30/30 突變全被抓；`build/fix24_verify.py` 的來源錯誤與反應表錯誤注入全被抓。

### 仍未實測（探針卡 `build/fix24-probes.md`）

- N5-1：`TESDeathEvent` 兩次（dead=0／1）時屍體上本模組效果的數量、兇手；主控台 `kill` 是否只送 dead=1（那樣就沒有死亡處理）。
- N5-2：`highActorHandles` 的名單（只有敵人與身邊隨從、沒有你與路人）、戰鬥中連續掃描不崩潰；一個事件只掃一次。
- 推力中心換成 FormID 後 `Game.GetForm` 取得的參照（風渦）。
- 復生僕從的攻擊加成（`ModActorValue("AttackDamageMult")` 加在被復生的那具屍體上）。

### Round 24 審查修正（2026-09-26）

| 項目 | 依據 | 做法 |
|---|---|---|
| 融斷的傷害 | 指揮官裁定；v0.4 2.7 D_burst | 每個被融斷的印記打一次 **B_max × K_sync × G × M_mod**（M_mod 含融斷主線、終焉主線、導引；雷斷加電荷），沒有 K_react；元素自己的終焉招式（爆燃、碎冰 ×1.0、放電、地震、風刃、血潮、裁決、星落）不再打出。終焉的非傷害部分照 2.6：狀態部分（消耗、催毒〔毒斷 ×4〕、導引、死咒引信與不能治療、星痕引爆）以 ×1 跑（K_sync 只進融斷那一擊）、2.5 的吹上天、各分支。血潮的「當前生命 10%」與裁決／星落的 K_react 不乘 K_sync。水斷＝治療＋耐力 B_max × K × G；星斷＝真實傷害 ×0.6；血斷＝治療融斷傷害 50%。 |
| 冰封融斷 | 指揮官裁定；v0.4 5.4 | 融斷時冰封的目標**只有持有冰封融斷**才碎冰（一般碎冰：最大生命 20%、首領 10%、冰晶照加，不乘 K_sync）；沒有就只受融斷那一擊、維持冰封。`Status.h PlanEndBody` 讀 `node::kFrostBurstShatter`。 |
| 原生函式的執行緒 | 審查修正 1；nv3 §10 | 會掃描或施放的原生函式（Burst、FormEnter、FormLeave、SetSync、AddStatus、SetStatus、ClearStatus、SetWindow、ApplyMark、ExtendFuse、WashBuffs、CastProc、DumpTargets）在 Guard 裡只把工作包成 `NativeJob` 交給 SKSE `AddTask` 就回來；task 在主執行緒（SEH `NativeJobGuarded` → C++ catch `NativeJobCpp`，再檢查一次總開關）。佇列先進先出，所以 Burst → FormLeave → SetSync 的順序不變；代價是 Papyrus 在這些呼叫之後立刻 GetStatus 會讀到執行前的值（目前沒有這種寫法；三重奏的「保留全部同調」若是這次融斷才掛上，要到下一次融斷才讀到）。`MarkedNear`（在 VM 呼叫緒掃描、回傳陣列）刪除，MCM 狀態按鈕改用排隊的 `DumpTargets` 寫 log；`WashBuffs`、`Burst` 沒有回傳值了。新增 X1 探針行 `queued native task`。 |
| 必要角色 | 審查修正 2；v0.4 2.9、5.12 | 跌倒、復生、化灰只排除 **essential**（參照或本體）或正在填任務物件別名（`ExtraAliasInstanceArray` 裡 `BGSBaseAlias::IsQuestObject()`）的角色；有名字的（unique／protected）敵人不再豁免。首領的碎冰 10%、血潮 3%、沉默減半照舊讀 `vip`。Papyrus `CanReanimate`、`ApplyAsh` 改讀新的 `IsEssentialTarget`（任務別名 Papyrus 讀不到，DLL 那邊先擋）；推力的免疫名單（`CanRagdoll`）沒動。 |
| 僕從攻擊加成 | 審查修正 3；v0.4 5.12 | 不再 `ModActorValue`：`ESSB_ReanimateSpell` 多一個效果 `ESSB_N5_ServantAttackEffect`（AttackDamageMult 的 Peak Value Modifier、No Death Dispel，因為落地時屍體還是死的），強度與時長在施放前設定；跟復生一起結束，再復生是重新套用、不疊加。 |
| 已知邊界（裁定：記錄） | 指揮官裁定 | 主控台 `kill` 若只送 `dead=true`，那次死亡**沒有**死亡處理；火葬／亡魂／冥召靠 1 秒標記判斷「被爆燃／死咒殺死」：標記後 1 秒內被別的東西殺死也算。斷界＝對應抗性 −10% 3 秒（火／冰／電／毒自己的抗性，其餘魔抗），列為文件缺口。 |

測試：reaction_test R 組 92 個情境（467 個預期操作），手算錨點 33 個（新增：三段融斷打冰封目標有／沒有冰封融斷與首領、三段聖與星、有名字的敵人復生與化灰、essential 不復生不化灰）；3 個新原始碼突變（融斷又打出終焉招式、沒有冰封融斷也碎冰、有名字的敵人被豁免），全部 33/33 被抓；`build/fix24_verify.py` 加：13 個原生函式必須經 `QueueNative`（注入錯誤：Burst 在 VM 緒直接施放）、復生法術的第二個效果、今天腳本上的行為檢查（GetDamageMult 不再有 Papyrus 嗜血 ×1.2、晝夜 ×1.2、BaseMax、ReactDamage、ApplyUtil 的減速上限）；fix6 的 Pct／FlowPercent／ApplyUtil 改在今天的腳本上跑（只剩被刪的 WetSlow 在 round 23 的腳本上）。

## Round 25（N6：每秒計時、熱鍵、領域，2026-09-26）

本輪的 DLL 做法（0.25.0），每一項標出依據（`nv3`＝native-verification-3、「推論」＝沒有直接查證）。實作者沒有進遊戲；遊戲內要看的列在 `build/fix25-probes.md`。

| 項目 | 依據 | 做法 |
|---|---|---|
| 計時器 | 裁定 R3；nv3 §10 | 背景執行緒每 100 ms 只排**一個** `AddTask`（`tickQueued` 原子旗標：上一個還沒跑完就不排），task 不會再排自己。時間用 `Timer.h Cadence` 算：只累加「遊戲在跑」的毫秒（`GameStopped`＝`UI::GameIsPaused()` 或 Loading Menu 開著；每步上限 250 ms，秒數不補跑），每滿 1 秒一個 beat，每 5 秒環境檢查；讀檔（`kPostLoadGame`／新遊戲）重設。停住與恢復寫 `[N6-1][L3]`。對話等不暫停的選單照走（跟以前 Papyrus 的 `RegisterForSingleUpdate` 一樣）。 |
| 每秒工作 | 成果 1；v0.4 1.1、5.8、5.10 | 純函式 `PlanFormSecond`：維持費（`ESSB_MultUpkeep`×基礎％×最大魔力，等級減免）、魔力歸零（魔力 < 0.1 掛 3 秒標記 `ESSB_N6_ManaEmpty`，連續第 3 秒送 `ESSB_Close`）、血形態扣血（走代價路徑、留 1 點，血位曲線 `BloodUpkeepFraction`）、長流與長河（每秒回復×回復倍率；另回維持費 80% 的魔力；長河給 6 公尺（420 單位）內最多 5 名同伴生命與耐力，新 `Op::kStaminaTarget`）、雷雨電荷（第一個雷雨秒就給，之後 3 秒冷卻 `ESSB_N6_StormCooldown`）。環境（天氣分類順序同 Papyrus 的 `GetClassification`、室內、水中 `TESObjectREFR::IsPointSubmergedMoreThan(0.875)`、20–6 點算夜）寫 `ESSB_EnvWet／EnvStormy／EnvNight`。沉默的扣魔：施放當下 `RunOp`（`DrainMagickaAll`），之後每秒 `SilenceSecond`。 |
| 熱鍵 | 裁定 R6；nv3（BSInputDeviceManager 的 sink 在主執行緒，推論：跟 kDataLoaded 同一緒，探針 X1 看） | `BSTEventSink<InputEvent*>` 登記在 `BSInputDeviceManager`，永遠回 `kContinue`（不吃按鍵）。只看 `ButtonEvent::IsDown()`；鍵碼：鍵盤 DX scan、滑鼠 256+、手把對應到 266 起（LT 280／RT 281）。門檻 `InputOpen`：遊戲暫停、主控台、`ControlMap::textEntryCount > 0`、選單堆疊有 kPausesGame／kUsesCursor／kUsesMenuContext／kModal、讀檔，任何一個成立就擋（`[N6-2][L3]` 寫 blocked 或 accepted）。`PlanSwitch`：總開關、`ESSB_HotkeysEnabled`、魔力 10% 門檻（血形態免）、順轉、`ESSB_FreeOpen` 一次免門檻；結果寫全域變數後送 `ESSB_Switch`／`ESSB_Close`，Papyrus 只換形態。Z 路線（`ESSBFormPowerEffect`）呼叫同一個 `ESSBNative.RequestSwitch`（排進主執行緒 task）。 |
| 領域：敵人那一半 | 裁定 R4；推論（HAZD 半徑單位、limit 0＝不限，探針 N6-3 看） | 每個有領域的元素一個 HAZD（半徑 9.84＝210 單位若單位是呎；Inherit Duration + Drop to Ground；limit 0；目標間隔 0.3 秒；模型 `FXEmptyObject.nif`）、一個 hazard 法術（標記、地裂的耐力停回、死域的治療削減）、一個 Spawn Hazard（archetype 40）效果、24 個整秒放置法術（持續時間倍率取整秒）。`ESSB_Domain` 事件在融斷目標腳下 `CastSpellImmediate` 施放，強度 0（不覆寫）。引擎管壽命與數量（拿掉 3 格上限）；hazard 只打對施放者敵對的角色，所以隨從與路人不受影響。 |
| 領域：找 hazard | 推論（`Hazard::GetHazardRuntimeData` 的 owner／age／lifetime；`SpawnHazardEffect::hazard` handle） | 每秒一次：`TES::ForEachReferenceInRange` 找玩家 60 公尺（4200 單位）內的 PlacedHazard（owner 是你、hazard 是本模組的），加上身上效果的 `SpawnHazardEffect` handle，兩邊去重；寫 `[N6-3][L3]`。DLL 不存領域：每秒重找。 |
| 領域：DLL 每秒效果 | 裁定 R4、R5；v0.4 5.x | 敵人在 3 公尺（210 單位）內（幾何判定，`InsideOf`）：冰原減速 50% 2 秒（MCM 減速上限 hazard 讀不到）、毒霧擴散一劑（d' = max(d − t, 12)，同瘟疫／瘴氣）、潮池每秒沖刷一個增益、死域每秒 B_max × 0.5 × 反應倍率 × 易傷 × DoT 倍率（hazard 的強度覆寫會蓋掉治療削減，所以不走 hazard）、地裂耐力 ≤ 0 時推倒（推力留 Papyrus，力道 2.0）。你在裡面：火域第一次進入熱度 3 加 5 秒、2 秒視窗內不重複；冰原免疫減速；血池／聖域／潮池回復；潮池淨化送 `Cleanse` 事件；聖域寫 `ESSB_DomainDivine` 給 Papyrus 的「你在裡面受到傷害 −20%」。 |
| 免疫減速 | v0.4（定神、御風、冰原） | 每 tick `SlowImmunity`：`SlowImmune`（冰原視窗、或同調 ≥ 3 且有定神或御風）時把你身上本模組以外的減速驅散。以前的 Papyrus 守衛沒有呼叫者（假 DONE）。 |
| 刪除 | 成果 3、4 | 原生函式 `ExtendFuse`、`WashBuffs`、`SetWindow` 32–35 刪除；新增 `RequestSwitch`。Papyrus `ESSBFormRules`、`ESSBInput`、`ESSBSilence` 整檔刪除（VMAD 一起拿掉，別名腳本 3 → 2），控制器的三格領域、環境、雷雨計時、9 個領域鏡射屬性刪除。 |
| 防護 | — | 輸入 sink：SEH → C++ catch（`InputCpp`）；計時 task：`TickGuarded`（SEH）→ `TickCpp`（C++ catch）；`RequestSwitch` 經 `Guard` → `QueueNative`。沒有 hook、trampoline、vtable 修補，也不寫遊戲記憶體；DLL 不存設計狀態（領域每秒重找、計時只有時鐘）、沒有存檔序列化。 |

測試：原有各組照過；新增 `native/tests/timer_test.cpp`：T 組 118 個情境（581 個預期項目，對 `build/fix25_reference.py` 另寫的 v0.4 模型；14 個手算錨點由 `build/fix25_fixture.py` 核對，含邊界：等級 150 夾到 100、魔力不夠扣時只扣剩下的並開始 2 秒計時、歸零 2 秒關閉、血 70% 的損血）、W 組 457 個接線檢查（round 25 狀態種類、每個領域的 HAZD／Spawn Hazard／放置法術、CastSpells、全域變數、熱鍵、維持費設定）、X 組 15 個假引擎檢查（融斷時的領域施放、沉默扣魔、潮池沖刷上限、帶暫停與讀檔的假計時器、假輸入事件）；10 個新原始碼突變（Timer.h 9、StatusEngine.h 1），43/43 突變全被抓；`build/fix25_verify.py` 的 7 個來源錯誤與 7 個 timer_test 錯誤注入全被抓；每個 DLL 施放的法術與 hazard 由 `ResolveDomains` 對 ESP 核對（archetype 與 associated form）；0 個 entry-point 51。

### 仍未實測（探針卡 `build/fix25-probes.md`）

- N6-1：暫停、背包、Alt+Tab、讀檔時計時停住（`[N6-1]` 的 active 不增加）。
- N6-2：輸入 sink 的執行緒（X1）、主控台／背包／文字欄裡不觸發。
- N6-3：DLL 找得到 hazard（`cells` 或 `effects` > 0）、HAZD 半徑單位、limit 0 是否真的不限、hazard 只打敵人。
- 水中判定（`IsPointSubmergedMoreThan` 0.875）與天氣分類。

### Round 25 審查修正（2026-09-26）

| 項目 | 依據 | 做法 |
|---|---|---|
| 聖域「其中敵人傷害 −20%」 | 指揮官裁定；推論（NPC 的毀滅法術是否吃 DestructionPowerModifier 沒查證，探針 C4） | 聖域 hazard 法術 `ESSB_N6_HazardSpell_Divine` 多兩個有害的 Peak Value Modifier 效果：`ESSB_N6_DivineAttackEffect`（AV 154 AttackDamageMult −0.2）、`ESSB_N6_DivineMagicEffect`（AV 149 DestructionPowerModifier −20），各 2 秒，跟聖域標記一起由 hazard 重新套用（0x005905、0x005906）。「你在聖域裡受傷 −20%」的 PERK 進入點（聖域、神聖領域兩個節點）與 DLL 每秒寫的 `ESSB_DomainDivine` 鏡射拿掉；那個 GLOB 留著不回收，沒有人讀寫。 |
| 領域掃描 | 審查修正 2 | `Timer.h HasDomainNode`：你沒有任何一個會留下領域的節點（火域、冰原、地裂、血池、聖域、神聖領域、毒霧、潮池、死域、星域）時，每秒不跑 `ForEachReferenceInRange(4200)` 與效果掃描；每秒從你的 perk 讀，不快取。 |
| 雷雨與暴風雪 | v0.4 2.10；Skyrim.esm WTHR DATA（本機掃描：沒有雷電的天氣 thunderLightningFrequency 都是 255，SkyrimStormRain 系列 246；風速 SkyrimStormSnow 178、SkyrimOvercastSnow 76） | 雷雨＝天氣分類是雨、且雷電頻率 ≠ 255 → 新 GLOB `ESSB_EnvThunder`（0x005907），雷形態電荷只讀它。暴風雪＝天氣分類是雪、且風速 ≥ 128／255 → `ESSB_EnvStormy`（round 22 的命中路徑本來就把它當暴風雪：凍結累積 ×2）。下雨或下雪照舊給浸濕。`[env][L1]` 多寫 `thunder=`、`lightning=`、`wind=`。 |
| Papyrus 的秒計時器 | 審查修正 4 | 新原生函式 `ESSBNative.RunningSeconds`：DLL 計時器每步把「遊戲在跑的毫秒」加進一個 atomic（這次開遊戲以來，不重設、不存檔），函式只讀它，登記為 callable-from-tasklets（不等主執行緒），有自己的 SEH 與 C++ catch、不經 Guard（總開關關著時也要回答，否則計時器永遠不到期；也不讓 X1 的 native 執行緒探針被 tasklet 緒弄亂）。`ESSBController.Now()` 包它；TickTimers、TimersActive、SecondsLeft、各 Set 視窗函式、同調保留、雙生改用它。讀檔時 ResetLoadClock 照舊全部歸零。沒有讀者的連段 `ComboHits`／`ComboTime`／`GCombo` 刪除（`ESSB_Combo` GLOB 留著）。 |
| 血形態扣血 | 審查修正 5 | 比例（血位）與扣血量都用永久生命（`GetPermanentActorValue`，其他血位規則的分母）；以前扣血量用目前上限。錨點改為 70／100 → 0.6。 |
| 存檔結構 | 裁定 R1 | 控制器成員變了（連段刪除），round 25 的 schema 14 還沒出貨：`state-schema.lock.json` 從 pre-fix25 快照（13）還原，讓建置重新做這一輪唯一的 13 → 14。 |

測試：timer_test T 126 個情境（589 個預期項目；新增 8 個天氣情境，數字取自 Skyrim.esm）、W 457、X 18（新增領域節點閘門）；4 個新突變（任何雨算雷雨、任何雪算暴風雪、沒有節點也掃描、血形態扣血用目前上限），47/47 全被抓；`build/fix25_verify.py` 加：聖域 hazard 法術的兩個效果（AV、強度、2 秒、有害）、沒有 PERK 讀 `ESSB_DomainDivine`、`ESSB_EnvThunder` 存在、秒計時器函式不用真實時間（新注入錯誤：SecondsLeft 改回真實時間，被抓）、領域節點閘門、RunningSeconds 的登記；`build/fix22_verify.py` 的原生函式比對認得帶 callable-from-tasklets 的登記，防護檢查多認「函式自己有 SEH＋C++ catch」。

#### 仍未實測（探針卡 C 段）

- NPC 的毀滅法術（火球）在聖域裡是否 ×0.8（DestructionPowerModifier）；不吃的話替代做法由指揮官決定。
- 等待、睡覺、快速旅行時計時器是否停住（選單暫停遊戲、快速旅行是讀檔）；對話照走。
- 按住熱鍵是否只切換一次（只看 IsDown）、手把鍵；死亡、倒地、騎馬時按熱鍵的行為（沒有擋，記錄）。
- 同一元素 5 個領域與讀檔後 `domains=` 不重複；冰原減速吃 MCM 上限 30；五種天氣的 `[env]`；FPS。

## Round 25 hotfix（0.25.1，2026-09-27）：資料載入時 DLL 自我停用

實機 log：`[ESSB][fault] manifest identity mismatch: tagged effect resolved; native hit OFF until the game restarts`。

| 項目 | 內容 |
|---|---|
| 根因 | `StatusEngine.h TaggedEffects()` 列了 `effect::kBloodGuard`（0x005303 `ESSB_BloodGuardEffect`，round 23 加入，TagKind::kGuardPool）與 `effect::kHush`（0x005340 `ESSB_HushEffect`，round 24 加入，TagKind::kHush）。兩個 MGEF 都在 ESP 裡（`build/fix21_records.py` 建的），也在 `ResolveEffects` 解析成 `Forms::bloodGuard／hush`，但 `ResolveStatus` 從沒用 `effect(...)` 把它們登記進狀態效果表 `s.effects`，所以載入尾端的檢查必然失敗。從 round 23 起的每一版 DLL 在遊戲裡都會在 kDataLoaded 故障。 |
| 為什麼離線沒抓到 | engine_test／reaction_test 只檢查「id 在 TaggedEffects() 清單上」，沒有任何測試跑載入函式本身（它寫死在 Plugin.cpp、綁 CommonLib）。清單和解析器是兩份東西，沒人比對。 |
| 修正 | 載入解析整段（ResolveGlobals／Spells／Effects／Perks／Status／Domains 與版本檢查）搬到 `native/include/Load.h`，對抽象表單來源寫成樣板；Plugin.cpp 只剩 `GameForms` 轉接（TESDataHandler）並呼叫 `essb::load::LoadForms`。ResolveStatus 補登記 `ESSB_BloodGuardEffect`、`ESSB_HushEffect`；TaggedEffects 檢查原樣保留。 |
| 失敗訊息 | 每個失敗記一行 `[ESSB][load] FAILED ...`：哪一項檢查、本地 FormID、執行期 FormID（依外掛實際載入序號，ESL 也算）、EditorID（manifest 新增 `records`：本地 id → [EditorID, 類型]）、預期記錄類型，以及實際情況（沒有這筆／那裡是別的類型／解析得到但沒登記／秒數不同）。會繼續檢查到底，一次列完，最後才故障（行為不變：native OFF 到重開遊戲）。成功時記一行摘要：外掛前綴、globals、proc／命中路徑法術、具名效果、狀態效果表、狀態法術表、領域 hazard／放置效果、主線／分支天賦、Skyrim.esm 表單的數量。 |
| 離線檢查 | 新 `native/tests/load_test.cpp`：用假 TESDataHandler 跑 **同一份** `Load.h`。輸入是 `build/fix25_verify.py` 從剛寫出的 ESP 讀回的事實（每筆記錄的本地 id 與類型、SPEL 第一個效果秒數、MGEF archetype 與 associated item）加 Skyrim.esm 的 KYWD／CLAS／FACT（`build/fix25-load-forms.json`），以及打包的 manifest.json。之後再照 Plugin.cpp 的查法（排序表二分搜尋）查每個 TaggedEffects、CastSpells、命中路徑施放與領域。fix25_verify 另注入 8 個錯誤（ESP 少一筆、類型錯、秒數錯、spawn 效果不指向 hazard、manifest 來自別的建置、Skyrim.esm 少關鍵字、TaggedEffects 記錄不見、CastSpells 法術不見），每個都要失敗且訊息要含 FormID／EditorID／類型。 |
| 舊碼證明 | `native/build.py` 新增 3 個 Load.h 突變（只建置，由 fix25_verify 在寫出的 ESP 上跑，必須失敗）：第一個就是 0.25.0 的登記（拿掉兩行）。在已部署的 0.25.0 ESP 上它輸出 `tagged effect resolved: 0x005303 (runtime 0x01005303) ... expected MGEF, the record resolves, but ResolveStatus never put it in the status effect table` 與 0x005340 同樣一行，和實機 log 同一個檢查；修正版在同一份 ESP 上通過。另兩個（跳過 CastSpells 登記、狀態效果表不排序）也失敗。 |
| 其他載入檢查 | 盤點 LoadManifest 裡全部 CheckIdentity／Resolve：manifest 對編譯常數、每筆記錄的類型、狀態法術秒數、領域 Spawn Hazard archetype 與 associated item、proc／施放覆蓋、tuning／timer globals、天賦版面、Skyrim.esm 關鍵字／職業／派系、外掛檔。以前離線只比對 manifest 與 ESP 的 EditorID，這些在 Load.h 裡現在全部離線跑過；目前全部通過，沒有第二個會在遊戲裡炸的點。唯一無法離線的是 CommonLib 本身的行為（LookupForm 的類型判斷、TESFile 載入序號），轉接層只做一對一轉呼叫。 |
| 版本 | DLL 0.25.1（manifest 的 native_version 跟著變；log 開頭的版本可確認換上的是熱修版）。state schema 不變（14，控制器成員沒動）。 |

建置：`python -B native/build.py` exit 0（ctest 6/6，突變 47/47＋3 個 Load.h 突變）；`python build_v03.py` exit 0（`FIX25 LOAD ok`：8/8 注入錯誤、3/3 突變）。


## Round 26（探針 log，DLL 0.26.0）

合約 `.codex/fix-round26-briefing.md`，紀錄 `.codex/impl-fix-round26.html`。這一輪只加 log 與修探針旗標，玩法不變。

| 項目 | 內容 |
|---|---|
| 探針 log | MCM「除錯等級」新增 **4：探針 log**（預設 0）。每個可觀察事件一行 `[ESSB][T][種類] #序號 g=遊戲在跑的毫秒 r=實際毫秒 欄位=值…`，演員一律 `名字(0xFormID)[h=目前/上限 m=… s=…]`。行格式、緩衝、錄骰與各種行的產生函式在新純標頭 `native/include/Trace.h`；每種行的 regex 在 `build/fix26_format.py`（寫出 `build/fix26-trace-format.json`，trace_test 與判定器共用）。 |
| 涵蓋 | proc（元素、法術、強度、暴擊、擲骰 `rolls=`、雷的 N／電荷／暴擊率、吸魔／燒魔、施放清單）、hit-end、每一個狀態 op（`ctx=` 事件標籤、Apply／Remove／Mark／Damage／Event…、狀態記錄名、強度、秒數、被取代的舊實例 `was=/left=/n=`）與 op-done（做完後的數值）、remove（expired／dispel／death 與剩餘秒數）、apply（引擎替我們掛的效果：領域標記、Papyrus 法術）、hurt（含冷卻）、second（維持費／扣血／長流與 dH dM dS）、env（每 5 秒，含天氣 FormID）、tick（停住／恢復）、menu、switch、key、mcm（每個全域變數的變動）、node（節點增減，每秒比一次）、scan／scan-c（每次範圍掃描、每個演員的判定理由：picked／ally／neutral／far／dead…，`StatusEngine.h SelectCrowdWhy`）、death／death-event、burst、settle、native、cast、casting、interrupt、wash、spread、silence、fire-source、domain 系列、Papyrus 那一半的 pap（推力、跌倒、復生、恐懼／瘋狂／幻視、神佑、換形態、魔力耗盡關閉、以毒攻毒、化灰、印出目標狀態、MCM 按鈕，經新原生函式 `ESSBNative.Trace`）。 |
| 成本 | 等級不到 4 時：每個呼叫點一次浮點比較（RunOp 裡是引擎的 `Tracing()`）、TraceRng 每次擲骰多一個布林判斷；其他什麼都不做。等級 4：寫進記憶體緩衝（鎖內給序號），**計時執行緒每秒寫檔一次**，滿 1 MB、故障、讀檔前後、存檔時與 DLL 卸載時也立刻寫；單行上限 480 位元組（超過截斷、結尾 `~`）；緩衝超過 16 MB 會丟行並記一行數量。 |
| TraceRng | 包住原本的 SplitMix64：抽到的數字與順序完全一樣（trace_test 對 200 組 Int／Real／Chance 逐一比對，錄與不錄都一樣），只是把抽到的數字另外記下來寫進 `rolls=`／`[rng]`。 |
| 站標記 | 新記錄 `ESSB_ProbeStep`（GLOB 0x005C00，`build/fix26_records.py`，隨存檔保存）。等級 4 時數字鍵區 `+`（DIK 78）＝下一站、`-`（74）＝上一站，主控台 `set ESSB_ProbeStep to N` 直接跳；每次變動寫 `[ESSB][STEP] N #序號 g=… r=… via=key|key-back|console` 並在畫面顯示「探針站 N」。總開關關著時也有作用（D-24 要用）。 |
| X1 旗標修正 | `Probe::kHurtTask`：受擊 task 以前跟命中 sink 的「you are the target」共用 `Probe::kHurt`，只會寫先到的一行；現在各自一個旗標。 |
| 主執行緒查證（指揮官插單） | 見下一節。X1 改成每個 sink／task 遇到**每一條新執行緒**寫一行（最多 4 條），列原始 id、是否等於輸入 sink（主迴圈）、最近一次 SKSE task、遊戲視窗擁有者、kDataLoaded 的執行緒、當下是否暫停；新增 settle／death／spell-cast task 的探針。**執行緒模型沒有改。** |
| 判定器 | `build/probe-judge.py <log>`：依 `build/probes-all.md` 的 91 站判定 102 步（PASS／FAIL／EYES／RECORD／NO-DATA＋證據行）。`build/fix26_verify.py` 檢查卷與判定器一致，並用 trace_test 以真規劃器產生的樣本（B-07、B-35、B-33、A-15、A-05、A-09）與手寫樣本（SETUP-1、A-01、A-06、A-10、A-11、A-12、B-08、B-13、C-01、D-01、D-24、E-01）各跑一次 PASS、各注入一個錯誤要 FAIL。 |
| 版本 | DLL 0.26.0；state schema 不變（14：Papyrus 只加函式，沒動屬性／變數）。 |

### 主執行緒查證（2026-09-27，SE 1.5.97 + SKSE 2.0.20）

實測兩次：`kDataLoaded thread=42336`／`timer task 18188`（第一次）；`kDataLoaded 2744`、`timer task 22284`、`TESHitEvent 15464`（第二次，三個都不同）。靜態證據（`build/nv3-scratch/nv3.py` 唯讀反組譯 SkyrimSE.exe、SKSE 2.0.20 原始碼）：

1. **kDataLoaded 在 InitTESThread**：SKSE `Hooks_Data.cpp` 在 `0x5B0120+0x3E8`（ID 35554，原本呼叫 `DataHandler::LoadScripts` ID 13657）送 kDataLoaded；35554 唯一呼叫者 ID 35631 沒有直接呼叫者，是 vtable `0x14164D900` 第 1 格，RTTI `.?AVInitTESThread@@`。所以它不是主迴圈，不能當 X1 的參考。
2. **輸入 sink 在主迴圈**：`Main::Update`（ID 35565，呼叫鏈 35551 → 35545 → CRT `__scrt_common_main`＝WinMain）在 `0x1405B33B0` 呼叫 `PollInputDevices`（native-verification-3 §13）。
3. **task 佇列有兩個處理點**：SKSE 的 `ProcessTasks` 接在 `ProcessTaskQueue`（ID 35916）的兩個呼叫點：`Main::Update+0x6B8`（`0x1405B36A8`）與 ID 35582+0x1C。前者前面是 `test dil,dil; jne`，dil 在 `0x1405B30A5` 依 `UI+0x160`（暫停選單計數）設定：**遊戲在跑時跳過**、暫停時才在 WinMain 處理。後者的唯一呼叫者 ID 38136 是 BSJobs 工作表（.data `0x141DEE620`）裡名為「Post process」的工作；它先把目前執行緒登記進 TLS 位元遮罩 ID 517486（與 Main::Update 在 `0x1405B368A` 呼叫的 ID 38082 同一段）再處理佇列。**所以遊戲在跑時，引擎的 task 佇列與 SKSE task 在「Post process」工作裡，由任一條工作執行緒處理。**
4. **命中結算走同一個佇列**：送 TESHitEvent 的 ID 37650 只由 BSTaskPool 執行函式 ID 36016 呼叫；ID 35917 等約 60 個包裝函式在旗標 ID 509007（`0x141DEF8A0`，.data 初值 1；只有 ID 35552（關遊戲）與 ID 13646（暫存後還原）寫它）為真時把工作排進佇列。

5. **第三次實測**（0.25.1）：輸入 sink＝Papyrus native＝6300；timer task 41528、queued native task 38544、`TESHitEvent (you are the target)` 38544、`TESHitEvent` 26956、`TESDeathEvent` 46780。輸入 sink 的 `SendEvent`（ID 67355）每次 `PollInputDevices` 都呼叫 sink、不檢查有沒有事件（每幀一次）；PollInputDevices 暫停時由 Main::Update、遊戲中由「Poll controls」工作（ID 38135）呼叫。
6. **崩潰**（crash-2026-09-27-03-17-19）：76018＝bhkWorld vfunc 50 → 60562 hkpWorld 步進 → 60930／60931＝hkpSimulation vfunc 3／4 → 60941 → 61420 → 63800 約束求解，在 BSJobs::JobThread 上讀到壞指標（另一模組的 NPC「瘟疫狼」的 hkpConstraintInstance）。本 DLL 不在堆疊、不直接碰 Havok；在工作執行緒上做的施放／傷害（可能殺死而加入布娃娃約束）、Dispel、AV 寫入若與物理步進同時進行即可能破壞，但引擎自己的命中結算也在同一處，靜態上無法排除或坐實。

結論：遊戲進行中 SKSE task、命中與死亡事件都在工作執行緒（Post process 等），不是主迴圈；10:34 那一版「同一情境、不必改」作廢。提案（**等指揮官定案才改，本輪沒有改任何執行緒行為**）：自有 FIFO，所有 sink 只記快照再入列，在主執行緒點消化——首選 SKSE `AddUITask`（UI::ProcessMessages ID 79945，Main::Update `0x1405B35BA` 呼叫），備選輸入 sink 的每幀呼叫。為了讓下一次實機定案，X1 再加兩個見證：每秒一個 `SKSE UI task`、`input sink (every frame)`，都對照遊戲視窗擁有者（WinMain）與最近一次 SKSE task 的執行緒。

建置：見 `.codex/impl-fix-round26.html` 最後一段（`python -B native/build.py`、`python build_v03.py` 的 exit code 與檢查數）。


## Round 26b（指揮官的執行緒裁定，DLL 0.26.1）

裁定（獨立反組譯查證後）：遊戲進行中沒有「做遊戲邏輯的主執行緒」；引擎自己把命中結算、傷害、附魔施放、擊殺都延到 BSJobs 的「Post process」工作，SKSE `AddTask` 緊接在它後面消化——那是引擎自己的序列化點，也是不用 hook 最安全的情境。Post process 所在的工作清單與 Havok 步進（清單 4）之間有硬性屏障、不會重疊（Post process 在清單 6），而且登記 Havok 的 TLS 位元。遊戲中 `AddUITask` 在清單 4 的「UI」工作（更差）；輸入 sink 在「Poll controls」工作，與 Post process 並行；6300 只是工作執行緒。第三次崩潰判定不是本模組（別的模組生物的布娃娃約束缺第二個剛體；載入順序也顯示 DynamicGrip 的指標損壞）。我 11:22 的「改在 AddUITask 消化」提案被否決。

| 改動 | 內容 |
|---|---|
| 死亡 sink | 只讀屍體本身（我們的復生標記、我們的效果數、屍體的狀態與事實），兇手與你只比對身分（`native/include/Sinks.h DeathSink`）；兇手的狂宴判定、N5-1 與 death-event 行、屍體到你的距離、群體掃描與所有寫入都在死亡 task。 |
| 輸入 sink | 只讀事件的按鍵、全域變數與一次輸入閘門快照（`GateNow`），由純函式 `PlanInput` 對應成動作；`RequestSwitch` 與站標記改用 `AddTask` 執行（熱鍵最多晚一幀）。 |
| 不變 | 命中 sink 照舊同步；受擊／到期結算／施法／原生函式／計時器照舊走 `AddTask`；100 ms 計時執行緒只 AddTask；唯讀原生函式直接回答。每秒的 `AddUITask` 只當見證，不在那裡做任何事。 |
| X2 見證 | 每個 sink／task 每一條不同的呼叫鏈（`RtlCaptureStackBackTrace` 的雜湊）第一次出現時記一行：`[ESSB][X2] <名稱> thread= window= same|DIFFERENT paused= havok= keys= frames=SkyrimSE.exe+0x…`（12 層回傳位址減執行檔基址；本 DLL 的寫 `ESSB+0x…`）。`keys` 依 `Trace.h kChainKeys` 認：+0x640E67 Post process、+0x5B36AD 暫停路徑、+0x5C770C 命中 task 36016、+0x7211EF HitFrameHandler、+0x63FCC9 UI 工作、+0x5B35BF 主 ProcessMessages、+0x5B3F48 Poll controls、+0x5B33B5 暫停輸入、+0x640623 VM 更新工作、+0x5B3381 暫停 VM。task 另記 Havok TLS 字（`TLS[*ID 528600] + 0x688`，唯讀）。 |
| L3 對照 | 除錯等級 3 起，本模組造成的每一次擊殺、推力、跌倒、hazard 記一行 `[ESSB][AB][L3] kind= ref= tick=GetTickCount64 via= thread=`，給崩潰 A/B 對照。 |
| 判定 | `build/probe-judge.py` 的 SETUP-1：遊戲中命中 sink 與所有 task 要在 Post process（命中 sink 也接受命中 task／HitFrameHandler）、輸入／UI／VM 在各自的工作、暫停時在視窗執行緒；對不上 FAIL，12 層內沒有認得的鍵 EYES。 |
| 測試 | trace_test 的假世界：死亡 sink 只讀屍體（兇手、你從不被讀）、你的死亡什麼都不讀、`dead = true` 只記錄；`PlanInput` 被擋的熱鍵不執行、站標記要等級 4。2 個 Sinks.h 突變（死亡 sink 讀兇手、被擋的熱鍵照樣執行）都讓測試失敗。fix26_verify 另有 2 個 X2 錯誤樣本（遊戲中 task 在 UI 工作、暫停時 task 不在視窗執行緒）必須 FAIL。 |


## Round 26c（堆積損壞修正，DLL 0.26.2）

使用者 A/B：停用本模組不崩；0.26.1 幾分鐘內崩（`crash-2026-09-27-04-49-35`：EngineFixes 的 tbbmalloc free list 已損壞，崩在原版命中 task 35582→36016→37650→37673→37633 配置記憶體時）。唯讀稽核（堆積稽核筆記）：這個載入順序裡 TESHitEvent 在視窗執行緒送出（Precision／TDM 從 Main::Update hook 當場結算，X2 frame 0x5B373D；MagicTweaks 的法術路徑也是），而我們所有 SKSE task 同時在 Post process 工作執行緒上跑——命中 sink 同步做的 CastSpellImmediate、Dispel、RestoreActorValue、process list 掃描，跟我們自己的 task 在同一個玩家施法器、效果清單與數值上競爭。26b「命中 sink 維持同步」的前提（原版的送出情境）撤回。另一個 A/B：停用 TrueHUD（本 DLL 跳過資源條）玩 15～20 分鐘不崩，開著幾分鐘內崩。

| 項目 | 做法 |
|---|---|
| P1 命中 sink | 只讀事件、手上武器、全域變數與命中當下的旗標（`HitFacts`、`RawAttack`），在 sink 裡 `Filter`，接受的才排 `AddTask` 給命中 task；規劃、施放、驅散、數值寫入都在命中 task（晚一幀）。路由是 `Sinks.h RouteHit`（你的／打你的／我們命中 task 裡自己觸發的巢狀命中＝丟掉，取代舊的 `handling` 旗標）。受擊 sink 不再讀效果清單：你的池子由每個 task 的 `WriteMirrors` 寫進 atomic（最多晚一個 100 ms tick），披風檢查標記後在受擊 task 裡做。代價：這一刀直接打死目標時不附傷（`[hit-late]`）；因為死亡事件先到，死亡處理看不到這一刀的印記（例如第一刀就打死時聖灰不觸發）。 |
| P2 收集後驅散 | `StatusEngine.h DispelWhere`、`DispelMarkerCpp`、`SlowImmunity` 都改成先收集 id（usUniqueID＋基礎效果＋法術），每次 Dispel 前在即時清單裡重新找到它；找不到就跳過。 |
| P3 擲骰 | 只在 task 裡用（`Rng()`，task 以外第一次用會記 `[ESSB][RNG]`）；`TraceRng::Note` 先讀索引、就地檢查範圍再寫，不可能寫出 `tape_`。 |
| P4 共用狀態 | `selfDispel`、`traceCtx` 改成 thread_local（我們的 Dispel 的移除事件在同一條執行緒同步送回）；`handling` 移除；`deferredNotices` 加鎖；globalSeen／perksSeen／domainsSeen／stepSeen／secondSeen／traceWasOn、`cadence` 的重設、TrueHUD 的 `Link`（added／waitTicks／pendingTicks）都只在 task 裡改（讀檔時改由一個 game-ready task 重設，FIFO 排在第一個 tick 前）；`Fault()` 不再動別的執行緒的旗標。 |
| P5 重疊見證 | 每個 task 本體開一個 `TaskScope`（atomic 計數）；同時超過 1 個就記 `[ESSB][OVERLAP] <名稱> thread= with=<另一個>`，每對一次；release 也保留。 |
| P6 SEH 與鎖 | `EssentialOf` 的別名清單讀鎖改在只含 SEH 的函式裡手動上鎖、`__finally` 解鎖，外層 `__except` 攔到存取違規時也會解鎖（`BSReadLockGuard` 的解構在 /EHsc 的 SEH 展開裡會被跳過）。 |
| P7 計時執行緒 | 不再 detach；靜態的 `TimerStopper` 在 `state` 之前解構：設停止旗標、等待最多 1 秒、再 detach。 |
| T1 TrueHUD | 重新稽核見下。 |
| T2 開關 | 新 GLOB `ESSB_TrueHudBars`（0x005C01，預設 1），MCM「一般」頁「TrueHUD 資源條」；0＝不載入、不新增，已加的資源條移除。 |
| T3 生命週期 log | 除錯等級 3：`[ESSB][hud][L3] <呼叫> bar= thread= truehud=`（LoadCustomWidgets、loaded、RegisterNewWidgetType、AddWidget、RemoveWidget、Initialize、第一次 Update、Dispose）。 |

TrueHUD 資源條的稽核（T1）找到的具體問題：
1. **呼叫 TrueHUD 的執行緒錯了**：`RegisterNewWidgetType`／`AddWidget`（計時 tick 裡）與 `LoadCustomWidgets`（讀檔時在主執行緒的 `OnGameReady`、開 TrueHUD 選單時的 task）都是從我們的執行緒直接呼叫；遊戲中計時 task 在 Post process 工作執行緒上，跟 TrueHUD 自己在 UI 執行緒處理 widget 的工作並行。（推論）TrueHUD 的介面有 `GetTrueHUDThreadId`、`kBadThread`，表示它在意呼叫的執行緒；這些呼叫從別的執行緒進去就可能跟它的 HUD 佇列、widget 表同時被改——跟崩潰時 tbbmalloc 已損壞相符。改成全部經 SKSE `AddUITask`（UI 工作，TrueHUD 的選單在那裡跑）。
2. **`Link` 的非 atomic 欄位被兩條執行緒同時改**：`Reload()` 在主執行緒（OnGameReady）改 added／waitTicks／pendingTicks 的同時，工作執行緒上的 tick 在讀寫它們；可能在一次 reload 還沒完成時又 AddWidget 同樣的 id。改成只在我們的 task 裡改（讀檔的 Reload 也改成 task）。
3. **`PoolBar` 的 SEH 會吞掉 Scaleform 裡的存取違規**，讓堆積停在寫一半的狀態、之後在別處才崩；移除 SEH（只留 C++ catch）。
其餘沒問題：Update 只讀 atomics（Publish 只寫 atomics）；不保留 widget 的 shared_ptr（`make_shared` 直接交給 AddWidget），GFxValue 由 TrueHUD 在它的執行緒釋放；字串參數都是靜態常數。

測試：trace_test 加 tape 邊界（順序 100 次＋四條執行緒同時抽、第五條不停重設錄製，後方的保護值不變）、依 id 重找的驅散（假清單在 Dispel 時會位移）、`RouteHit`；3 個新突變（tape 寫出邊界、驅散用舊 handle、巢狀命中又排隊）都讓測試失敗（tape 那個會讓程式直接崩，build.py 已能記下沒有輸出的失敗）。fix26_verify 加靜態檢查：命中／受擊 sink 內沒有任何引擎工作或效果清單讀取、每個 task 本體有 TaskScope、thread_local、`__finally`、TimerStopper、`Rng()`；SETUP-1 出現 OVERLAP 必須 FAIL。

另一次崩潰（`crash-2026-09-27-05-12-16`，TrueHUD 已停用，長時間遊玩後開新遊戲時）：主迴圈 35565 → 34862／34872（SKSE 掛勾處）→ 34677 → 34735／34736 → 34745 → 13148／13147 → 13277／13278／13276 → 20026 → 20087 → 19000 → 18568 `call [rax+0x120]`，讀到 0xFFFFFFFFFFFFFFFF：對一個 vtable 已是垃圾的物件做虛擬呼叫＝物件已被釋放或覆寫。本 DLL 不在堆疊。這是「同一個 process 前面已經發生的堆積損壞，到清理／重建世界時才爆」的樣子，跟 TrueHUD 無關、跟 P1 的並行寫入一致；所以主修正仍是 P1～P7，TrueHUD（T1～T3）是另一個確認過的問題。

## Round 26d（DLL 0.26.3）：關形態＋融斷後凍結

- **現象**（使用者 0.26.2）：水 → 熱鍵冰（切換）→ 再按冰（關閉）→ `[T][pap] kind=Form who=- close 2` → `queued native task thread=39376` → `[T][burst-start] #230 …` 之後 log 完全停住，遊戲「沒有回應」（不是崩潰）。
- **傾印分析**（指揮官抓的 hang.dmp，自寫的 minidump 解析：ThreadList／ModuleList／Memory64List，堆疊掃回傳位址）：只有一條執行緒停在本 DLL 裡——39376（就是 log 最後那個 queued native task），`RIP = ElementsSpellblade.dll+0x59E46`。反組譯 0.26.2 的 DLL：
  `0x180059E43 cmpb $0x0,(%rbx)`（`t_inTask`）／`0x180059E46 jne 0x180059E43`；為假時 `xchgb` `rngOutsideLogged` 後 `jne` 也跳回 `0x180059E43`＝原地打轉。
- **根因**：Round 26c 把所有 `*state.rng` 換成 `Rng()` 時，連 `Rng()` 自己的本體也被換成 `return Rng();`——無限自我呼叫。MSVC 把尾端呼叫最佳化成跳回開頭，所以不是 stack overflow 崩潰，而是 100% CPU 的死迴圈。任何擲骰（命中附傷、融斷、化身、形態開啟的臨…）第一次呼叫就凍結；這次剛好第一次擲骰是融斷的 `Rng().Record(true)`（該 session 還沒有任何命中）。編譯器其實有發 C4717（「所有路徑都遞迴」），但 DLL 目標沒把警告當錯誤，沒人看到。
- **為什麼離線測試沒抓到**：`Rng()` 只存在 Plugin.cpp；Plugin.cpp 只編進 DLL，7 個測試程式都只編 `native/include/*.h`，沒有任何測試執行 Plugin.cpp 的程式碼。fix26_verify 的靜態檢查只查「沒有人繞過 Rng()」，沒查 Rng() 本體。
- **修法**：`Rng()` 的本體搬進 Trace.h `TaskRng(rng, inTask, outsideReported, onOutside)`（task 外的擲骰只報一次、未播種就播種、一律回傳來源）；Plugin.cpp 的 `Rng()` 只呼叫它。DLL 目標加 `/we4717`：任何「所有路徑都呼叫自己」的函式直接編譯失敗。
- **檢查**：① trace_test `TaskRngChecks`：task 內、task 外（只報一次）、先 Record 再擲、未播種，每次都在 3 秒看門狗下跑，卡住就以失敗結束（不會把 ctest 卡死）。② native/build.py 突變「Rng() calls itself (the 0.26.2 freeze)」：把 TaskRng 改回自我呼叫，trace_test 以 exit 3「never returned」失敗——離線重現了凍結。③ fix26_verify `check_26d`：Rng() 本體必須經 TaskRng、不能出現 `Rng()`、CMakeLists 有 `/we4717`；兩個注入錯誤（本體改回 `return Rng();`、繞過 TaskRng）都被抓到。新 DLL 反組譯：沒有原地打轉的迴圈。
- 版本 0.26.3（CMakeLists、ManifestData.h、fix19_native、manifest、probe-judge、測試卷）。玩法不變。

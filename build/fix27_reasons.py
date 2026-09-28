"""Round 27 (DLL 0.27.0): why each file the round-27 native seal covers changed (build/fix27_native_history_gen.py reads
NATIVE). One table, written as the work is done; the seal can only restate it."""

R = 'Round 27（DLL 0.27.0）：'
E = R + '引擎膠合（E1–E13）：'
G1 = R + 'G1（加法的 M_mod＝1＋Σ，K 類係數維持乘法）：'

NATIVE = {
    'build/fix21_identity.py': R + '27e：允許 NodeRank／NodeBranch／分支遮罩依座標讀（座標來自 ESSBNodes 依名稱的讀取）',
    'build/fix6_verify.py': R + '27e：perk 描述比對改用玩家文字（build/fix27_text.py，去掉規劃文件註記）',
    'native/tests/lifetime_net.cpp': R + '27d：生命週期網的負向對照（字串檢視綁在暫存物件上，clang-cl 必須報錯）',
    'native/tests/asan_harness.cpp': R + '27d：AddressSanitizer 用的不丟例外測試（Context 複製、具名節點檢視、24 目標融斷、登記表雙執行緒、受擊佇列）',
    'native/tests/self_test.cpp': R + '27d：static_assert WithAvatar 不收暫存物件',
    'native/tests/engine_test.cpp': R + '27c：inf／NaN／4e22／效力 0 的操作被丟掉',
    'native/include/Locks.h': R + '27b（審查 A N4）：新純標頭：lk::Mutex（自己計數的鎖）與 EnterEngineLock／LeaveEngineLock，SehFilter 在持鎖時不吞例外',
    'build/fix23_reference.py': R + 'G7：參考模型的護血跟著護血池走；27b：end_body 帶 carried（B N1）',
    'build/fix22_verify.py': R + 'T：Guard 的 try／catch 搬進 Runtime.h GuardRun，檢查跟著讀它',
    'build/probe-judge.py': R + 'SETUP-1 判 0.27.0（VERSION 常數）；[ESSB][OVERLAP-READ]（E1）與 [ESSB][crash]（E2）出現＝FAIL；27b：VERSION 0.27.1；27c：VERSION 0.27.2、BADMAG＝FAIL、SETUP-1 的 X1 改要 input task（G8 之後站 1 不再排 queued native task）；27d：VERSION 0.27.3；27e：VERSION 0.27.4；27f：VERSION 0.27.5；27g：VERSION 0.27.6',
    'build/fix26_verify.py': R + '檢查跟著新寫法：sink 經 QueueTask、重疊計數在 Runtime.h Scope、配接器的 Dispel 多了屍體與剛結算的記錄；版本改成「一個值、不早於 0.26.3」（0.27.0 由 fix27_verify 釘住）；27c：SETUP-1 樣本的 X1 用 input task',
    'build/fix25_verify.py': R + '檢查跟著新寫法：切換在 SwitchWork 送 ESSB_Switch（G8）、計時 task 經 QueueTask、GameStopped 讀 session；G13：火冰聖星領域的危險區模型；計時 task 的順序改由 PlanTick（tick.second）',
    'build/fix24_verify.py': R + '檢查跟著新寫法：task 經 QueueTask（帶 session 票的 AddTask）、死亡 sink 用 ReadMemberFrom、OnFormClosed 多了參數',
    'native/include/Reactions.h': G1 + '終結＝EndNodeMult（加法）＋BurstCommonLines（共通線加總）＋雷斷；簽名與聖裁用 EndMove（同一個加法池）；'
                                  'BurstMult 只剩 K_sync；湧動的百分比部分只吃自己的線、濺射與血祭之始 ×0.5；聖裁的階級 T 是乘法；27b：連鎖終焉帶主終焉的加總（B N1：CarriedMod、Current）、開印的劑數與拉近不吃節點倍率（B N2）、放電每格與風刃加入加總（B N4：EndMove、Joined）',
    'native/include/Sinks.h': R + 'G15：綁在元素熱鍵上的鍵只當熱鍵，不再同時當探針的步驟鍵',
    'native/include/Status.h': G1 + 'EndNodeMult 改加法、SignaturePct；碎冰不再自帶結算；催化不疊乘（base×最大係數）；暗蝕熔斷；死咒結束＝損失×比例×易傷，'
                                '擊殺旗標先設再扣；聖裁 III 只吃自己的線；G3：開印層數不乘 NodeScale；慈光用 PunishCap；G5：瘴氣速率不乘 NodeScale；'
                                'G4：熔斷的無形態融合算一次洩熱（VentHeat）；StatusPlan 改 vector（kMaxStatusOps 8192，爆量記 log 不丟例外）；27b：PlanEndBody 帶 carried（B N1，暗蝕熔斷）、開印事件帶未乘倍率的層數（B N2）、催毒 ×2 整、線加入每劑的加總（B N5 CatalysedLine）、FireSourceBurns／FireSourceCosts（B N3）',
    'native/tests/anchor_test.cpp': R + '新測試（ctest anchors）：G1 的手算錨點（碎冰 962.5／465、聖裁 III 135／67.5、死咒 540／1020、血 650／195、'
                                    '霜終結 420、催化 65、G3 詛咒 7、G4 洩熱、843 個 op 的爆發不溢位）；27b：催毒錨點改 38（B N5）；Review27bAnchors：焚天 ≤ 主終焉、開印劑數不隨節點倍率、火源、屍體模式',
    'native/tests/trace_test.cpp': R + 'G15：綁在熱鍵上的步驟鍵只切換形態',
    'build_v03.py': R + 'G13：武器光改 Enhance Weapon＋ENCH、武器光的條件改讀自己的 ESSB_SyncStage＋ESSB_WeaponGlow、印記效果拿掉命中特效與音效'
                        '（開印改由閃現法術放）、MCM 武器光開關；G14：DLL 施放的法術加 No Absorb/Reflect（標記加 Ignore Resistance）；'
                        'G15：冷卻滑桿 0.25～3.0；全域變數 56 個；開印閃現是接觸施放；27b：形態能力改掛四個光圈、MCM「形態光圈」、送給別人的法術加 No Absorb；27e：perk 名稱與描述去掉規劃文件的註記（build/fix27_text.py）、退役節點描述不再寫版本號、除錯等級說明不寫檔名；27g：Custom Skill Menu 的清單名稱加共同前綴與序號（元素魔戰士・01 無元素 … 13 星界），技能 id 不變',
    'build/fix22_records.py': R + 'G13：狀態的著色（凍結、冰晶閃、血痕、催毒、浸濕、水壓、詛咒、星痕、死咒閃），取自規劃 2.11 點名的紀錄；27f：白熱／熔燒／熔身的全身火焰改用原版火焰斗篷（著色＋火焰 art）；催毒著色改 Venomancy 毒霧（Rotflesh 的貼圖路徑在原模組就壞了）',
    'build/fix22_reference.py': G1 + 'Python 參考模型跟著 Status.h：加法終結、碎冰、催化、暗蝕、死咒、聖裁 T、開印層數、慈光、瘴氣、洩熱；27b：參考模型跟著 C++（B N1 carried、B N2 開印事件的層數、B N5 催毒）',
    'build/fix22_fixture.py': R + 'G5：瘴氣錨點改 1.5（不乘 NodeScale）',
    'build/fix24_reference.py': G1 + '參考模型跟著 Reactions.h：簽名加法、BurstLines、終結本體、BurstMult 只剩 K、湧動 pct_scale、聖裁；錨點：霜終結 17.43、爆發 31.248；27b：參考模型跟著 C++（B N1 連鎖帶加總、B N2、B N4）',
    'build/fix25_records.py': R + 'G13：火、冰、聖、星的領域用原版危險區模型（看得見範圍），其他維持空模型；27b：火領域換 FXFireOilHazard（較大）',
    'build/fix27_records.py': R + 'G13、G14 的新紀錄（新檔）：ESSB_WeaponGlow、武器光 ENCH 與它的效果、開印閃現；DLL 法術的 SPIT 旗標；27b：形態光圈 ESSB_FormRingEffect_<X>_0..3、切換號碼牌的兩個全域變數、送給別人的法術都加 No Absorb、ENCH 退役；27d：光圈改用我們自己的 ARTO（ESSB_FormRingArt_<X>，原版地面符文與恢復圈模型；0.27.1 的施法光圈看不到）',
    'native/include/Registry.h': E + '新純標頭：我們自己效果的登記表（task 的讀取發布快照；移除 sink、死亡 sink、唯讀 native 讀它；0.35 秒到期寬容；'
                                 '移除時 EraseUid）；G9 的 SettledMarks（1 秒內被結算掉的印記，死亡時算帶著）；27b：Key＝FormID＋handle（A N2）、lk::Mutex、ExpiredMarkOf（B N9）；27d：SnapshotView 拒收暫存的 Snapshot',
    'native/include/Runtime.h': E + '新純標頭：Scope／ResetScope（E9）、Session＋Ticket（E3：PreLoadGame／NewGame／主選單換 epoch）、'
                                'HealthLedger＋HurtQueue＋AssignAfter（E4 幀序＋G7 自己的生命帳）、OpenLogWith＋Query（G12）、SehVerdict（E2）、'
                                'GateFrom＋kInputMenus（E6）、EventText（E12）；T：DispelCollected、GuardOpen／GuardRun、PlanTick、ReadEngaged（Plugin.cpp 的規則移出來讓測試跑）；27b：SehVerdict 帶 locksHeld（A N4）、SehQuiet（N5）、WorldClock（N3）、OwnDelta（N10）、MenuEndsSession（N8）、NoteSneakHit（B N7）、lk::Mutex；27c（0.27.2）：rt::Context（每次複製都把 in.tuning 指回自己的 tuning；0.27.1 融斷與過期結算讀到已結束的區域變數，傷害 inf）；27d（0.27.3）：RingOf（形態光圈的效果編號）；27e：BranchBit／Gained、LethalDue',
    'native/include/Hurt.h': R + 'G7：HurtFacts.ownDelta，lost = before − after + ownDelta（我們自己的扣血、治療不算敵人的傷害）',
    'native/include/SelfLayer.h': R + 'G11：風的多段觸發的重複永遠不算滿格重擊放電；27b：CorpseHitPlan（B N6）；27d（0.27.3）：WithAvatar 拒收暫存的節點讀取器（0.27.2 崩潰：AvatarNodes 保留參考）',
    'native/include/StatusEngine.h': R + 'G6：RunOp 在引擎回報 IsCorpse 時不對屍體施放、驅散（事件、你身上的、其他人的照常）；27b：CorpseSends（A N7：屍體模式只送切掉的終焉事件）；27c：CheckOp／SaneValue——非有限、超過 ±1e7 或效力近 0 的操作整個丟掉',
    'native/include/Trace.h': E + 'E12：Utf8Fit（名字與被切斷的行不留半個字）；E7：Buffer::TryTake（結束時不等鎖）；27b：Buffer 用 lk::Mutex（A N4）',
    'native/include/TrueHud.h': E + 'E13：每次載入要求的 generation，舊的回呼作廢；關閉時舊要求的回答也作廢',
    'native/include/ManifestData.h': '由 build/fix19_native.py 產生：' + R + '版本 0.27.0；G8：kEchoPendingSpell、kTwinWindowSpell、kTwinWindowRecordSeconds、node::kCommonTwin；27b：版本 0.27.1；27c：版本 0.27.2；27d：版本 0.27.3、kRingEffectFirst、kRingStages、glob::kWeaponGlow；27e：版本 0.27.4；27f：版本 0.27.5；27g：版本 0.27.6',
    'native/src/Plugin.cpp': R + 'E1–E13、G6–G12（見 build/native-verification.md Round 27）：登記表與 OVERLAP-READ 見證；SehFilter；QueueTask 帶 epoch；'
                             '受擊按幀與自己的生命帳；GateNow 不走 menuStack；EventText；ScanDomains 先收再做；null cell；ESL 拒載；'
                             '計時先走時鐘、關閉或故障時移除 TrueHUD 條；OpenLog 不丟例外、Query 先填 info；主選單結束 session；'
                             '屍體模式（G6）、連殺讀命中 sink 的潛行旗標、剛結算的印記（G9）、施法中與命中前生命在 sink 讀（G10）；'
                             '形態切換由 DLL 在 task 裡做完（G8：SwitchWork、SwitchMarkers、CloseByMagicka、KeepSync）；T：DispelLive、Guard、TickCpp 的順序、BuildCrowd 的 engaged 讀取改用 Runtime.h；27b（DLL 0.27.1）：登記表的 handle 鍵、死亡第二事件與卸載 sink 的 Forget、世界時鐘、SEH 鎖深度與 stack overflow、遊戲就緒 task 的 sessionOnly、選單 sink 故障時仍結束 session、GetHandle 移到鎖外、自己的生命只記精確數值、屍體模式的事件過濾（A N2–N10）；火源條件（B N3）、屍體模式不花資源（B N6）、潛行紀錄（B N7）、過期終焉的剛結算印記（B N9）；27c（0.27.2）：Context 改用 Runtime.h 的版本；[ESSB][BADMAG]；27d（0.27.3）：RingWatch——除錯等級 ≥3 時光圈生效／失效各記一行 [ESSB][ring]；27d：SwitchWork 的節點讀取器改成具名變數（0.27.2 崩潰根因）、Executor 拒收暫存的 Tuning；27e（0.27.4）：NodeRank／NodeBranch／BranchesGained 原生函式（MCM 卡頓：技能樹階數不再靠 Papyrus 快取）、StatsMenu 開啟時記下分支、ESSB_Lethal 每秒最多一次',
    'native/tests/runtime_test.cpp': R + '新測試：task scope、session 與新遊戲、log 與 Query、SEH 判定、輸入閘門、事件文字與 UTF-8、登記表（兩條執行緒）、'
                                     '受擊佇列與自己的生命帳、屍體模式、剛結算的印記；T：驅散重找、原生守衛、計時順序、人群讀取；27b：Review27bChecks（A N2–N10、B N7、B N9）；27c：ContextChecks（回傳的複本讀自己的 tuning）；27d：RingChecks；27e：BranchChecks、LethalChecks',
    'native/CMakeLists.txt': R + '版本 0.27.0；runtime_test（ctest runtime）、anchor_test（ctest anchors）；C4717 當錯誤；27b：版本 0.27.1；27c：版本 0.27.2；27d：版本 0.27.3；27d：Release 加 /Zi、/DEBUG:FULL /OPT:REF /OPT:ICF；27e：版本 0.27.4；27f：版本 0.27.5；27g：版本 0.27.6',
    'native/build.py': R + 'runtime 與 anchors 測試的突變（E1、E2、E3、E4、G1、G3、G4、G6、G7、G9、G12、爆發溢位）、G15 的步驟鍵突變；'
                        '舊突變的原文跟著新寫法（對死者施放、濺射的 SurgeOn）；T 的 4 個突變（Runtime.h）；27b：A-N2／N3／N4／N7／N10、B-N1／N2／N3／N5／N6／N7／N9 突變；E2 突變原文跟著 locksHeld；27c：Context 與 SaneValue 的突變；27d：生命週期網（clang-cl -Werror=dangling* 檢查 Plugin.cpp 與所有測試、負向對照 lifetime_net.cpp 必須被抓到、asan_harness 在 AddressSanitizer 下跑）；27d：DLL 一律產生 PDB，GUID／age 對上 DLL 才複製到 build/pdb/（不出貨）',
    'build/fix19_native.py': R + 'NATIVE_VERSION 0.27.0；G8：manifest 的 spells 加 kEchoPendingSpell、kTwinWindowSpell，header 加 kTwinWindowRecordSeconds，'
                             'ROUND27_NODES（雙生）；27b：NATIVE_VERSION 0.27.1；27c：NATIVE_VERSION 0.27.2；27d：NATIVE_VERSION 0.27.3、光圈效果編號、ESSB_WeaponGlow 進 manifest globals；27e：NATIVE_VERSION 0.27.4；27f：NATIVE_VERSION 0.27.5；27g：NATIVE_VERSION 0.27.6',
    'build/fix26_format.py': R + 'G6：hit-late 行可帶 mode=corpse',
    'build/fix26_history.py': R + 'round 26 的 Papyrus 封印改讀 pre-fix27 快照（先過 round 27 的證明；由產生器重寫，表格不變）',
    'build/fix26_history_gen.py': R + '產生器讀 pre-fix27 快照的 src（round 26 出貨時的腳本）',
    'build/fix26_history_template.py': R + 'current_dir 改成 fix27_history.legacy_source()',
    'build/fix26_native_history.py': R + 'round 26 的原生封印改讀 pre-fix27 快照（先過 round 27 的證明；由產生器重寫，表格不變）',
    'build/fix26_native_history_gen.py': R + '產生器列出並雜湊 pre-fix27 快照（round 26 出貨時的位元組）',
    'build/fix26_native_history_template.py': R + 'base() 讀 pre-fix27 快照（同 round 26 對 round 25 的做法）',
    'build/fix27_history.py': R + 'round 27 的 Papyrus 封印（產生的）',
    'build/fix27_history_gen.py': R + 'round 27 Papyrus 封印產生器（新檔）',
    'build/fix27_history_template.py': R + 'round 27 Papyrus 封印樣板（新檔）',
    'build/fix27_native_history_gen.py': R + 'round 27 原生封印產生器（新檔）',
    'build/fix27_native_history_template.py': R + 'round 27 原生封印樣板（新檔）',
    'build/fix27_reasons.py': R + '這份理由表（新檔）',
    'build/fix27_verify.py': R + 'round 27 的驗證器（新檔）；27b：光圈的注入錯誤、版本 0.27.1、A-N2／B-N1／B-N2 突變必須存在；27c：版本 0.27.2、BADMAG 樣本、Context 與 BADMAG 的原始碼檢查；27d：版本 0.27.3；27d：包裡的 DLL 與 build/pdb 的 PDB 對得上、package/ 沒有 PDB；27e：版本 0.27.4、玩家文字不得含規劃文件的註記（perk 名稱／描述、CSF、MCM）；27f：版本 0.27.5；ASSETS：我們自己的視覺紀錄與身上的火要在原版封存檔裡、活效果用的複本要在已安裝的模組裡（兩個注入錯誤）；27g：版本 0.27.6',
    'build/fix27_visuals.py': R + 'G13：視覺提示的盤點與建置檢查（新檔）；27b：光圈檢查、送給別人的法術檢查、INVENTORY 依審查 C 重寫；27d：光圈的 ARTO／模型檢查、不准再用 *CastBodyFX；INVENTORY 更新；27f：INVENTORY 的全身火焰一列',
}

# Round 27g (DLL 0.27.6): appended to each file's reason (written as the work is done).
_27G = {
    'native/include/Runtime.h': 'rt::SettleBranch／SettleBranches（技能選單關閉時一個新分支的點數結算：夠 4 點就扣，不夠退回並加回 CSF 的 1 點）',
    'native/src/Plugin.cpp': 'ESSBNative.SettleBranch 原生函式（分支退回訊息：Papyrus 用它結算，規則有單元測試）',
    'native/tests/runtime_test.cpp': 'BranchChecks：分支點數夠／不夠、0.27.5 回報的情形（火焰 10 點：6 階主線＋4 分支全退）、點數守恆掃描',
    'native/build.py': '27g 突變：剛好 4 點不夠、退回不加回 CSF 的 1 點',
    'build/probe-judge.py': '傷害倍率從 log 的 mcm-state／mcm 行讀出（Line.dm、Line.d），傷害數字除以當下倍率再比（新遊戲預設 0.8）',
    'build_v03.py': '技能樹選單的列名依序排（MSM_ORDER）；分支描述開頭寫「分支：需 5 點。」（BRANCH_COST_TEXT）；round-4 設定檢查允許使用者決定的傷害倍率 0.8',
    'native/include/HitMath.h': '傷害倍率（ESSB_BaseDamageMult）補乘到小滅法、滅法的真傷與血刃的附加值',
    'native/include/Status.h': '傷害倍率補乘到死咒的已損生命段、火源的代價×N 段；放血改用 BleedDrainDamage（×傷害倍率）',
    'native/include/Reactions.h': '中毒死亡擴散的保底值 ×傷害倍率',
    'native/include/ManifestData.h': '維持費 2.5%（暗 3.5%），由 fix19_native 從 settings.json 產生',
    'native/tests/anchor_test.cpp': 'DamageMultAnchors：傷害倍率 0.8 讓死咒、火源、血刃、小滅法、滅法、放血都剛好 ×0.8',
    'build/fix20_reference.py': '參考模型：小滅法、滅法真傷 ×傷害倍率（跟 HitMath.h 一致）',
    'build/fix25_reference.py': '維持費 2.5%（暗 3.5%），手算錨點跟著改（使用者 2026-09-27 的平衡決定）',
    'build/fix13_verify.py': '舊版 ESSBState 的還原預設仍是 1.0（現行是 0.8）；round 14 設定比對允許傷害倍率 1.0→0.8',
    'build/fix27_verify.py': '判讀程式依 log 的傷害倍率換算的檢查（0.8／1.5 樣本）',
    'build/probes-all.md': '傷害倍率改由判讀程式從 log 讀；站 10、站 14 的維持費數字改 2.5%／3.5%',
    'build/fix26_verify.py': 'A-09 的注入錯誤不再寫死 2.98（維持費 2.5% 後原生樣本是 7.45）',
    'settings.json': '傷害倍率預設 0.8；維持費 2.5%、暗 3.5%（使用者的平衡決定）',
}
for _file, _why in _27G.items():
    NATIVE[_file] = NATIVE.get(_file, R.rstrip('：')) + '；27g（0.27.6）：' + _why

# Round 27h / 28 (DLL 0.28.0): the whole-project review, the Papyrus-layer review, the user's decisions of 2026-09-28.
_H = '27h／28（0.28.0）：'
_27H = {
    'native/include/Runtime.h': 'FaultGrade／Latch／ClearAtLoad（C++ 例外只停這次遊戲，本模組的存取違規才要重開）；Scope 記下重疊（Overlapped，task 直接返回）；'
                                'SyncKeep／OnBurstKeep／OnOpenKeep（承接、連斷、永續、三重奏的保留，從 Papyrus 搬進切換 task）；DomainLedger（施放時記下領域，每秒只查記下的）；'
                                'EventLedger（事件序號與 Papyrus 處理延遲）；PointsHold（技能樹點數檢查）',
    'native/include/Status.h': 'RunOp 以外：強制開印不碰任何已有印記（D1）；導引存自己的倍率（不乘這次終焉）；死咒已損生命段首領 ×0.5；三重奏觸發後 10 秒冷卻（kTrioCooldown）；'
                               '火源印記旗標 kMarkSourced、融斷只算一半（D6）',
    'native/include/StatusEngine.h': 'Select 可以回答 false（跳過這個 op，不丟例外）；死掉的角色（同一個計畫裡剛被打死的）不再施放任何法術',
    'native/include/Reactions.h': '臨／雙斷／印潮的自身所得每次事件只給一次（D2）；水臨強化要範圍內有敵人、回最大魔力 25%×回復倍率（D3）；大潮的導引不乘本體；'
                                  '連殺把風形態的潛行致命一擊當作有印記；融斷時火源印記 ×0.5（D6）',
    'native/include/SelfLayer.h': 'OpenGains／PlanSelfOpen 的 selfGains（D2：同一事件後面的目標只剩誓約）',
    'native/include/Timer.h': 'SwitchFacts 帶現在、上次切換、燃盡鎖定；PlanSwitch 的 kBlocked（D4 0.25 秒防抖、D5 燃盡 5 秒不能開）；長流退回實付魔力的 80%（F11）',
    'native/include/Trace.h': 'switch 行在 kind=blocked 時帶 reason=debounce／burnout-lockout',
    'native/include/HitPipeline.h': 'EarlyGate／NeedsHands：命中 sink 不讀手上的東西，需要時由 hit task 讀',
    'native/include/ManifestData.h': '由 build/fix19_native.py 產生：版本 0.28.0、kFormAbility、kTreePoints、kPapyrusReady／kHeatBodyFx、kTrioCooldown、承接／永續／連斷／免門檻的節點、維持費 5%／暗 7.5%',
    'native/src/Plugin.cpp': '1-1 世界時鐘統一（ReadMemberFrom、印記結算、潛行紀錄）與 death／settle／hit-late 行的 world= running=；1-2 故障分級（SessionFault、ClearSessionFault、'
                             '故障時關形態、RunningSeconds 不故障、Select 不丟例外）；1-3 白熱全身特效的 L3 記錄；1-4 形態能力與同調保留在切換 task、ESSBNative.CloseForm；'
                             '1-5 命中 sink 不讀背包；1-6 領域記錄（不再掃 60 公尺）、TargetSecond 只讀帶本模組效果的角色；1-7 讀檔重設各帳本；重疊的 task 直接返回（OverlapCount）；'
                             'Papyrus 審查：ESSB_PapyrusReady 與待切換、技能樹分支在選單關閉時由 DLL 結算、洗點原生、perk 快照、PoisonedNearby、CastWith、領域標記上身記錄；'
                             '探針：事件序號與延遲、每秒 rate、每 10 秒 [ESSB][vm]、[ESSB][form] 檢查、[ESSB][pts] 點數檢查、ForceFault 故障演練；'
                             '使用者決定：防抖、燃盡鎖定、火源印記旗標',
    'native/tests/runtime_test.cpp': 'FaultChecks、DomainLedgerChecks、HitGateChecks、ProbeLedgerChecks、SwitchRuleChecks（防抖、燃盡、同調保留）、OverlapHarness（兩條執行緒同時跑計畫與共用容器）、Scope 的 Overlapped',
    'native/tests/anchor_test.cpp': 'RotationAnchors（熱鍵輪轉：第一次之後不切印、不造成傷害、同調所得不隨目標數增加）、WaterAdventAnchors、SourcedBurstAnchors、FixAnchors（死咒首領、導引、三重奏冷卻）',
    'native/tests/engine_test.cpp': '死掉的目標不再被施放印記與狀態',
    'native/tests/status_test.cpp': '狀態紀錄接受 ESSB_N7_ 前綴（round 28 的三重奏冷卻）',
    'native/tests/self_test.cpp': '狀態紀錄接受 ESSB_N7_ 前綴',
    'native/tests/reaction_test.cpp': '狀態紀錄接受 ESSB_N7_ 前綴',
    'native/tests/timer_test.cpp': '狀態紀錄接受 ESSB_N7_ 前綴',
    'native/CMakeLists.txt': '版本 0.28.0',
    'native/build.py': '27h／28 的突變（故障分級、重疊、領域記錄、命中 sink、防抖、燃盡、連斷保留、死掉目標、D1、D2、D3、D6、死咒首領、三重奏冷卻、導引、長流退回）',
    'build/fix19_native.py': 'NATIVE_VERSION 0.28.0；manifest 的 spells 加 kFormAbility1..11、globals 加 ESSB_PapyrusReady／ESSB_HeatBodyFx／ESSB_Pts_*、狀態加 fix28 的 KINDS、ROUND27_NODES 加承接／永續／連斷／免門檻',
    'build/fix22_records.py': '白熱／熔燒／熔身的狀態效果不帶著色；身上的火是法術裡另一個效果（fix28 ESSB_HeatBodyFxEffect，條件 MCM 白熱全身特效）',
    'build/fix25_records.py': '領域危險區每個效果都帶條件：不是你、不是隊友、敵對（Papyrus 審查 5）',
    'build/fix28_records.py': '新檔：ESSB_PapyrusReady、ESSB_HeatBodyFx、ESSB_HeatBodyFxEffect、三重奏冷卻（KINDS）',
    'build/papyrus_budget.py': '新檔：Papyrus 處理器原生呼叫數的離線上限（fix28_verify 的預算）',
    'build/fix28_verify.py': '新檔：兩份審查的規則（切換在 DLL、Papyrus 就緒、技能樹、IsOperational、共用法術紀錄、掃描、故障分級、危險區條件、原生呼叫預算），每條都有注入錯誤',
    'build/fix22_reference.py': '參考模型：強制開印跳過有印記的目標（D1）、導引不乘本體、死咒已損生命段 ×傷害倍率 ×首領 0.5',
    'build/fix23_reference.py': '參考模型：三重奏冷卻、強制開印的自身所得一次（D2）',
    'build/fix24_reference.py': '參考模型：臨／印潮的自身所得一次（D2）、水臨強化（D3）、大潮導引、連殺',
    'build/fix22_fixture.py': '狀態種類接上 fix28 的 KINDS',
    'build/fix25_reference.py': '維持費 5%（暗 7.5%）、長流退回實付的 80%（F11）與它的手算錨點',
    'build/fix26_format.py': 'world= running=（death／settle／hit-late）、switch 的 reason=、rate 與 vm 兩種新行',
    'build/fix26_verify.py': 'settle 樣本帶 world= running=；命中 sink 的注入錯誤跟著 ReadAttack(ev)（手上的東西改在 task 讀）',
    'build/fix21_identity.py': 'perk 快照、選單關閉結算、洗點、點數檢查的座標讀取（取代 NodeRank／NodeBranch 直接讀 perk 的兩行）',
    'build/fix27_verify.py': 'AddTask 規則改成精確（QueueTask、Show、見證各一次，Show 只在 Notify 與讀檔補發）；身上的火改查 ESSB_HeatBodyFxEffect；版本 0.28.0',
    'build/fix13_verify.py': 'round 14 設定比對允許維持費 5%／7.5%',
    'build/fix25_verify.py': 'ESSB_Switch 交給 FormOpenedFx／FormClosedFx（形態在 DLL）；SetSyncKeep 刪了，不再列在秒數窗口',
    'build/fix24_verify.py': '關閉的融斷改查 SwitchWork 的 BurstWork（Papyrus 的 OnFormClosed 刪了，融斷在切換 task）；注入錯誤跟著改；ApplyUtil 的慢速上限檢查模擬 ESSBNative.CastWith',
    'build/fix22_verify.py': 'MCM 動作的檢查：ESSB_NativeHit 1 才算運作；0 時 IsOperational 為否、IsReadyUI 照舊；「沒有總開關」的注入錯誤跟著 IsOperational 的新寫法',
    'build/fix6_verify.py': 'ApplyUtil 改由 ESSBNative.CastWith 施放：模擬它把這次的強度交給法術（慢速上限的檢查照舊）',
    'build/probe-judge.py': 'VERSION 0.28.0；時鐘漂移警告；F-01 故障演練、F-02 HDT-SMP 站；每秒事件／原生呼叫摘要；Papyrus.0.log 掃描',
    'build/probes-all.md': '站 92 故障演練、站 93 HDT-SMP；站 10／14 的維持費改 5%／7.5%；A-05 目視題不再提號碼牌',
    'build_v03.py': 'fix28 紀錄與 MCM「白熱全身特效」；fix28_verify 接進建置；round-4 設定檢查不變',
    'settings.json': '維持費 5%、暗 7.5%（使用者 2026-09-28 的決定）',
}
for _file, _why in _27H.items():
    NATIVE[_file] = NATIVE.get(_file, R.rstrip('：')) + '；' + _H + _why

# Round 28b (DLL 0.28.1): Fable's acceptance review of 0.28.0 (F1-F6) and the user's ruling on 水臨強化 (F7).
_B = '28b（0.28.1）：'
_28B = {
    'native/src/Plugin.cpp': 'F1 CastWithWork 由 Runtime.h PlanCastWith 決定（有強度的法術用效力 1＋整秒複本，不再把秒數當效力）、執行器的 Cast 拒絕把效力用在有強度的法術；'
                             'F2 kPostLoadGame 成功分支在 OnGameReady 前清 ESSB_PapyrusReady；F3 GameReadyCpp 清領域登記；F4 故障關形態時驅散護血池與餘響待發；'
                             'F5 印潮改成切換後第一擊開印（surgeArmed，只有切換會設）；F7 水臨強化 10 秒冷卻（執行時鐘，讀檔歸零）與 L4 行',
    'native/include/Runtime.h': 'F1 CastWithFacts／CastWithCall／PlanCastWith（無強度：效力＝秒數比；有強度：效力 1、整秒複本、沒有複本就拒絕）',
    'native/include/Reactions.h': 'F5 新印潮（SurgeTarget：目標 15 公尺內沒有任何印記、活著的敵人，最近 2 人，kSurgeTargets）；'
                                  'F7 AdventCooldown／AdventOutcome、BodyInputs.waterAdventReady，PlanAdvent 回傳水臨強化發動或冷卻中',
    'native/include/StatusEngine.h': 'F1 CastSpells 列出 CastWith 的整秒複本（讀檔時解析）',
    'native/include/Load.h': 'F1 每個 CastWith 複本檢查它的秒數',
    'native/include/ManifestData.h': '由 build/fix19_native.py 產生：版本 0.28.1、status::kCastWith（8 族整秒複本）',
    'native/tests/anchor_test.cpp': 'F5 SurgeAnchors（0 個沒印記→0、範圍內 3 個→2、16 公尺→排除、已有印記→排除、沒有分支→沒有計畫）；'
                                    'F7 WaterAdventCooldownAnchors（0 秒發動、5 秒不發動且剩 5 秒、10.5 秒再發動；冰臨強化沒有冷卻）',
    'native/tests/runtime_test.cpp': 'F1 CastWithChecks（恐懼 4 秒、狂刃 1 秒、ApplyUtil 緩速 3 秒、超過上限、守勢窗口、化灰、ApplyUtil(4) 不變、沒有複本就拒絕）',
    'native/tests/reaction_test.cpp': 'F5 PlanSurge 不再帶舊元素',
    'native/CMakeLists.txt': '版本 0.28.1',
    'native/build.py': '28b 的突變：F1 三個（Runtime.h）、F5 三個、F7 四個（Reactions.h）；D3 突變跟著 waterPlus',
    'build/fix19_native.py': 'NATIVE_VERSION 0.28.1；ManifestData.h 的 status::kCastWith',
    'build/fix28_records.py': 'F1 CASTWITH：8 族（恐懼、瘋狂、狂刃、ApplyUtil 0／13／23／25／26）× 1..20 秒的複本，只改 EDID 與 EFIT 秒數',
    'build/fix24_reference.py': 'F5 參考模型的新印潮（沒有印記的人、最近 2 人）與兩個情境',
    'build/fix27_text.py': '水臨強化（25%、要有敵人、10 秒冷卻）與新印潮的節點說明',
    'build/fix27_verify.py': '版本 0.28.1',
    'build/fix28_verify.py': 'F2 三個讀檔點依位置檢查；GAMEREADY、FAULTCLOSE、CASTWITH（ESP 複本、DLL 表、每個 Papyrus 呼叫點）、SURGE、ADVENT 與它們的注入錯誤',
    'build/fix12_verify.py': 'F6：註明 src/ 不再需要原型腳本，但 NEW（pre-fix22 快照）裡還有 ESSBPlayerAlias.psc，所以照舊略過',
    'build/probe-judge.py': 'VERSION 0.28.1；B-29 水臨強化的 10 秒冷卻；D-14 新印潮',
    'build/probes-all.md': '站 47 加 ③④（冷卻）、站 77 新印潮的操作與判定',
    'build_v03.py': 'F1 記下每個 SPEL 的子紀錄、寫 CastWith 複本、複本的傳遞方式；F6 註解不再提原型腳本',
}
for _file, _why in _28B.items():
    NATIVE[_file] = NATIVE.get(_file, R.rstrip('：')) + '；' + _B + _why

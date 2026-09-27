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
    'build/probe-judge.py': R + 'SETUP-1 判 0.27.0（VERSION 常數）；[ESSB][OVERLAP-READ]（E1）與 [ESSB][crash]（E2）出現＝FAIL；27b：VERSION 0.27.1；27c：VERSION 0.27.2、BADMAG＝FAIL、SETUP-1 的 X1 改要 input task（G8 之後站 1 不再排 queued native task）；27d：VERSION 0.27.3；27e：VERSION 0.27.4',
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
                        'G15：冷卻滑桿 0.25～3.0；全域變數 56 個；開印閃現是接觸施放；27b：形態能力改掛四個光圈、MCM「形態光圈」、送給別人的法術加 No Absorb；27e：perk 名稱與描述去掉規劃文件的註記（build/fix27_text.py）、退役節點描述不再寫版本號、除錯等級說明不寫檔名',
    'build/fix22_records.py': R + 'G13：狀態的著色（凍結、冰晶閃、血痕、催毒、浸濕、水壓、詛咒、星痕、死咒閃），取自規劃 2.11 點名的紀錄',
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
    'native/include/ManifestData.h': '由 build/fix19_native.py 產生：' + R + '版本 0.27.0；G8：kEchoPendingSpell、kTwinWindowSpell、kTwinWindowRecordSeconds、node::kCommonTwin；27b：版本 0.27.1；27c：版本 0.27.2；27d：版本 0.27.3、kRingEffectFirst、kRingStages、glob::kWeaponGlow；27e：版本 0.27.4',
    'native/src/Plugin.cpp': R + 'E1–E13、G6–G12（見 build/native-verification.md Round 27）：登記表與 OVERLAP-READ 見證；SehFilter；QueueTask 帶 epoch；'
                             '受擊按幀與自己的生命帳；GateNow 不走 menuStack；EventText；ScanDomains 先收再做；null cell；ESL 拒載；'
                             '計時先走時鐘、關閉或故障時移除 TrueHUD 條；OpenLog 不丟例外、Query 先填 info；主選單結束 session；'
                             '屍體模式（G6）、連殺讀命中 sink 的潛行旗標、剛結算的印記（G9）、施法中與命中前生命在 sink 讀（G10）；'
                             '形態切換由 DLL 在 task 裡做完（G8：SwitchWork、SwitchMarkers、CloseByMagicka、KeepSync）；T：DispelLive、Guard、TickCpp 的順序、BuildCrowd 的 engaged 讀取改用 Runtime.h；27b（DLL 0.27.1）：登記表的 handle 鍵、死亡第二事件與卸載 sink 的 Forget、世界時鐘、SEH 鎖深度與 stack overflow、遊戲就緒 task 的 sessionOnly、選單 sink 故障時仍結束 session、GetHandle 移到鎖外、自己的生命只記精確數值、屍體模式的事件過濾（A N2–N10）；火源條件（B N3）、屍體模式不花資源（B N6）、潛行紀錄（B N7）、過期終焉的剛結算印記（B N9）；27c（0.27.2）：Context 改用 Runtime.h 的版本；[ESSB][BADMAG]；27d（0.27.3）：RingWatch——除錯等級 ≥3 時光圈生效／失效各記一行 [ESSB][ring]；27d：SwitchWork 的節點讀取器改成具名變數（0.27.2 崩潰根因）、Executor 拒收暫存的 Tuning；27e（0.27.4）：NodeRank／NodeBranch／BranchesGained 原生函式（MCM 卡頓：技能樹階數不再靠 Papyrus 快取）、StatsMenu 開啟時記下分支、ESSB_Lethal 每秒最多一次',
    'native/tests/runtime_test.cpp': R + '新測試：task scope、session 與新遊戲、log 與 Query、SEH 判定、輸入閘門、事件文字與 UTF-8、登記表（兩條執行緒）、'
                                     '受擊佇列與自己的生命帳、屍體模式、剛結算的印記；T：驅散重找、原生守衛、計時順序、人群讀取；27b：Review27bChecks（A N2–N10、B N7、B N9）；27c：ContextChecks（回傳的複本讀自己的 tuning）；27d：RingChecks；27e：BranchChecks、LethalChecks',
    'native/CMakeLists.txt': R + '版本 0.27.0；runtime_test（ctest runtime）、anchor_test（ctest anchors）；C4717 當錯誤；27b：版本 0.27.1；27c：版本 0.27.2；27d：版本 0.27.3；27d：Release 加 /Zi、/DEBUG:FULL /OPT:REF /OPT:ICF；27e：版本 0.27.4',
    'native/build.py': R + 'runtime 與 anchors 測試的突變（E1、E2、E3、E4、G1、G3、G4、G6、G7、G9、G12、爆發溢位）、G15 的步驟鍵突變；'
                        '舊突變的原文跟著新寫法（對死者施放、濺射的 SurgeOn）；T 的 4 個突變（Runtime.h）；27b：A-N2／N3／N4／N7／N10、B-N1／N2／N3／N5／N6／N7／N9 突變；E2 突變原文跟著 locksHeld；27c：Context 與 SaneValue 的突變；27d：生命週期網（clang-cl -Werror=dangling* 檢查 Plugin.cpp 與所有測試、負向對照 lifetime_net.cpp 必須被抓到、asan_harness 在 AddressSanitizer 下跑）；27d：DLL 一律產生 PDB，GUID／age 對上 DLL 才複製到 build/pdb/（不出貨）',
    'build/fix19_native.py': R + 'NATIVE_VERSION 0.27.0；G8：manifest 的 spells 加 kEchoPendingSpell、kTwinWindowSpell，header 加 kTwinWindowRecordSeconds，'
                             'ROUND27_NODES（雙生）；27b：NATIVE_VERSION 0.27.1；27c：NATIVE_VERSION 0.27.2；27d：NATIVE_VERSION 0.27.3、光圈效果編號、ESSB_WeaponGlow 進 manifest globals；27e：NATIVE_VERSION 0.27.4',
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
    'build/fix27_verify.py': R + 'round 27 的驗證器（新檔）；27b：光圈的注入錯誤、版本 0.27.1、A-N2／B-N1／B-N2 突變必須存在；27c：版本 0.27.2、BADMAG 樣本、Context 與 BADMAG 的原始碼檢查；27d：版本 0.27.3；27d：包裡的 DLL 與 build/pdb 的 PDB 對得上、package/ 沒有 PDB；27e：版本 0.27.4、玩家文字不得含規劃文件的註記（perk 名稱／描述、CSF、MCM）',
    'build/fix27_visuals.py': R + 'G13：視覺提示的盤點與建置檢查（新檔）；27b：光圈檢查、送給別人的法術檢查、INVENTORY 依審查 C 重寫；27d：光圈的 ARTO／模型檢查、不准再用 *CastBodyFX；INVENTORY 更新',
}

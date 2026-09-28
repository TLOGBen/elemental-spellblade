"""Round 27 seal of the DLL sources, the native tests, the generator modules, the verifiers and the probe judge. GENERATED
by build/fix27_native_history_gen.py from this template -- write reasons there, never edit the digests here.

FILES  path -> (state, sha256 now, why): 'unchanged' files equal the pre-fix27 snapshot (.codex/pre-fix27-snapshot, taken
       before any round-27 edit); 'changed' / 'added' ones carry the declared reason. verify() fails on any byte that
       differs, on a covered file that is missing and on a file in native/include, native/src or native/tests that is not
       listed. build/fix26_native_history.py checks the snapshot (round 26 as shipped) only after this proof.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / '.codex/pre-fix27-snapshot'

FILES = {
    'native/include/EngineFacts.h': ('unchanged', 'd87e73a6b435df0e4b63e29d3f59f9e77f8543dfe251530e55a3804add18ebe4', ''),
    'native/include/HitMath.h': ('changed', 'd877c3fa2c1980054d46efdf94480871d222a6ec67fa9d4aa691504c5f91deb1', 'Round 27（DLL 0.27.0）；27g（0.27.6）：傷害倍率（ESSB_BaseDamageMult）補乘到小滅法、滅法的真傷與血刃的附加值'),
    'native/include/HitPipeline.h': ('changed', '6a8e86676971290e3cd9b5b60d1be699353802a01ce1dbc45aba85f983132de4', 'Round 27（DLL 0.27.0）；27h／28（0.28.0）：EarlyGate／NeedsHands：命中 sink 不讀手上的東西，需要時由 hit task 讀'),
    'native/include/Hurt.h': ('changed', 'f3e5bc40bf4c9e80b4b2d5066357bf200dcb550dd69d20c3e562b5398d4298d4', 'Round 27（DLL 0.27.0）：G7：HurtFacts.ownDelta，lost = before − after + ownDelta（我們自己的扣血、治療不算敵人的傷害）'),
    'native/include/Load.h': ('changed', '59b34841259580233a01d8cc43419c87e70551624fb5c27fbaafd88879331932', 'Round 27（DLL 0.27.0）；28b（0.28.1）：F1 每個 CastWith 複本檢查它的秒數'),
    'native/include/Locks.h': ('added', '223802bd99e5e572e0e837c6d72ba52ecb8424fbf93b31f3d90ee34396630c0a', 'Round 27（DLL 0.27.0）：27b（審查 A N4）：新純標頭：lk::Mutex（自己計數的鎖）與 EnterEngineLock／LeaveEngineLock，SehFilter 在持鎖時不吞例外'),
    'native/include/ManifestData.h': ('changed', '83b3c2f6cc1e4a7afe60f86b18da6c2f408453a2f1747deac3b8f9f977d68f0b', '由 build/fix19_native.py 產生：Round 27（DLL 0.27.0）：版本 0.27.0；G8：kEchoPendingSpell、kTwinWindowSpell、kTwinWindowRecordSeconds、node::kCommonTwin；27b：版本 0.27.1；27c：版本 0.27.2；27d：版本 0.27.3、kRingEffectFirst、kRingStages、glob::kWeaponGlow；27e：版本 0.27.4；27f：版本 0.27.5；27g：版本 0.27.6；27g（0.27.6）：維持費 2.5%（暗 3.5%），由 fix19_native 從 settings.json 產生；27h／28（0.28.0）：由 build/fix19_native.py 產生：版本 0.28.0、kFormAbility、kTreePoints、kPapyrusReady／kHeatBodyFx、kTrioCooldown、承接／永續／連斷／免門檻的節點、維持費 5%／暗 7.5%；28b（0.28.1）：由 build/fix19_native.py 產生：版本 0.28.1、status::kCastWith（8 族整秒複本）'),
    'native/include/NodeIds.h': ('unchanged', 'fd843a2bded8e5bf423c87801bbbfe071a5189f8d5e05c15d0dee605ef8fe5f3', ''),
    'native/include/Reactions.h': ('changed', '1dcf5429f7ee416964a1d9cd0de1c61fa2b9e0bf3664c015e49a73a8ed36bf8b', 'Round 27（DLL 0.27.0）：G1（加法的 M_mod＝1＋Σ，K 類係數維持乘法）：終結＝EndNodeMult（加法）＋BurstCommonLines（共通線加總）＋雷斷；簽名與聖裁用 EndMove（同一個加法池）；BurstMult 只剩 K_sync；湧動的百分比部分只吃自己的線、濺射與血祭之始 ×0.5；聖裁的階級 T 是乘法；27b：連鎖終焉帶主終焉的加總（B N1：CarriedMod、Current）、開印的劑數與拉近不吃節點倍率（B N2）、放電每格與風刃加入加總（B N4：EndMove、Joined）；27g（0.27.6）：中毒死亡擴散的保底值 ×傷害倍率；27h／28（0.28.0）：臨／雙斷／印潮的自身所得每次事件只給一次（D2）；水臨強化要範圍內有敵人、回最大魔力 25%×回復倍率（D3）；大潮的導引不乘本體；連殺把風形態的潛行致命一擊當作有印記；融斷時火源印記 ×0.5（D6）；28b（0.28.1）：F5 新印潮（SurgeTarget：目標 15 公尺內沒有任何印記、活著的敵人，最近 2 人，kSurgeTargets）；F7 AdventCooldown／AdventOutcome、BodyInputs.waterAdventReady，PlanAdvent 回傳水臨強化發動或冷卻中'),
    'native/include/Registry.h': ('added', '5e09dea84e65804b1b9837f0f5688af46c12c931f15cfd565c3e8abd8e933973', 'Round 27（DLL 0.27.0）：引擎膠合（E1–E13）：新純標頭：我們自己效果的登記表（task 的讀取發布快照；移除 sink、死亡 sink、唯讀 native 讀它；0.35 秒到期寬容；移除時 EraseUid）；G9 的 SettledMarks（1 秒內被結算掉的印記，死亡時算帶著）；27b：Key＝FormID＋handle（A N2）、lk::Mutex、ExpiredMarkOf（B N9）；27d：SnapshotView 拒收暫存的 Snapshot'),
    'native/include/Runtime.h': ('added', 'b0284da85db19950ca5cb03060ad617cb5fbe8083202a7b33ac077792f8e9347', 'Round 27（DLL 0.27.0）：引擎膠合（E1–E13）：新純標頭：Scope／ResetScope（E9）、Session＋Ticket（E3：PreLoadGame／NewGame／主選單換 epoch）、HealthLedger＋HurtQueue＋AssignAfter（E4 幀序＋G7 自己的生命帳）、OpenLogWith＋Query（G12）、SehVerdict（E2）、GateFrom＋kInputMenus（E6）、EventText（E12）；T：DispelCollected、GuardOpen／GuardRun、PlanTick、ReadEngaged（Plugin.cpp 的規則移出來讓測試跑）；27b：SehVerdict 帶 locksHeld（A N4）、SehQuiet（N5）、WorldClock（N3）、OwnDelta（N10）、MenuEndsSession（N8）、NoteSneakHit（B N7）、lk::Mutex；27c（0.27.2）：rt::Context（每次複製都把 in.tuning 指回自己的 tuning；0.27.1 融斷與過期結算讀到已結束的區域變數，傷害 inf）；27d（0.27.3）：RingOf（形態光圈的效果編號）；27e：BranchBit／Gained、LethalDue；27g（0.27.6）：rt::SettleBranch／SettleBranches（技能選單關閉時一個新分支的點數結算：夠 4 點就扣，不夠退回並加回 CSF 的 1 點）；27h／28（0.28.0）：FaultGrade／Latch／ClearAtLoad（C++ 例外只停這次遊戲，本模組的存取違規才要重開）；Scope 記下重疊（Overlapped，task 直接返回）；SyncKeep／OnBurstKeep／OnOpenKeep（承接、連斷、永續、三重奏的保留，從 Papyrus 搬進切換 task）；DomainLedger（施放時記下領域，每秒只查記下的）；EventLedger（事件序號與 Papyrus 處理延遲）；PointsHold（技能樹點數檢查）；28b（0.28.1）：F1 CastWithFacts／CastWithCall／PlanCastWith（無強度：效力＝秒數比；有強度：效力 1、整秒複本、沒有複本就拒絕）'),
    'native/include/Selection.h': ('unchanged', '51574fa1fe6649c234dc774526898c876bae6bb7bce310d1958a092959bccf1e', ''),
    'native/include/SelfLayer.h': ('changed', '51fcf6145d61e525a1905984e6740451c809c915f4dbda01ecc700b5d7301bd9', 'Round 27（DLL 0.27.0）：G11：風的多段觸發的重複永遠不算滿格重擊放電；27b：CorpseHitPlan（B N6）；27d（0.27.3）：WithAvatar 拒收暫存的節點讀取器（0.27.2 崩潰：AvatarNodes 保留參考）；27h／28（0.28.0）：OpenGains／PlanSelfOpen 的 selfGains（D2：同一事件後面的目標只剩誓約）'),
    'native/include/Sinks.h': ('changed', 'aeedc700c117eeb21b6361bc7c9df31aaa44f6e1b4d49662bbc272263bff149e', 'Round 27（DLL 0.27.0）：G15：綁在元素熱鍵上的鍵只當熱鍵，不再同時當探針的步驟鍵'),
    'native/include/Status.h': ('changed', '8e6a910017647d1b36348a5fb8d0ab302a0083a5ebcaa752e52420902ba50740', 'Round 27（DLL 0.27.0）：G1（加法的 M_mod＝1＋Σ，K 類係數維持乘法）：EndNodeMult 改加法、SignaturePct；碎冰不再自帶結算；催化不疊乘（base×最大係數）；暗蝕熔斷；死咒結束＝損失×比例×易傷，擊殺旗標先設再扣；聖裁 III 只吃自己的線；G3：開印層數不乘 NodeScale；慈光用 PunishCap；G5：瘴氣速率不乘 NodeScale；G4：熔斷的無形態融合算一次洩熱（VentHeat）；StatusPlan 改 vector（kMaxStatusOps 8192，爆量記 log 不丟例外）；27b：PlanEndBody 帶 carried（B N1，暗蝕熔斷）、開印事件帶未乘倍率的層數（B N2）、催毒 ×2 整、線加入每劑的加總（B N5 CatalysedLine）、FireSourceBurns／FireSourceCosts（B N3）；27g（0.27.6）：傷害倍率補乘到死咒的已損生命段、火源的代價×N 段；放血改用 BleedDrainDamage（×傷害倍率）；27h／28（0.28.0）：RunOp 以外：強制開印不碰任何已有印記（D1）；導引存自己的倍率（不乘這次終焉）；死咒已損生命段首領 ×0.5；三重奏觸發後 10 秒冷卻（kTrioCooldown）；火源印記旗標 kMarkSourced、融斷只算一半（D6）'),
    'native/include/StatusEngine.h': ('changed', '472c32a1aa1eddd6ba40dd53a5f71b0296c2edda961f2ce069dde53972b90562', 'Round 27（DLL 0.27.0）：G6：RunOp 在引擎回報 IsCorpse 時不對屍體施放、驅散（事件、你身上的、其他人的照常）；27b：CorpseSends（A N7：屍體模式只送切掉的終焉事件）；27c：CheckOp／SaneValue——非有限、超過 ±1e7 或效力近 0 的操作整個丟掉；27h／28（0.28.0）：Select 可以回答 false（跳過這個 op，不丟例外）；死掉的角色（同一個計畫裡剛被打死的）不再施放任何法術；28b（0.28.1）：F1 CastSpells 列出 CastWith 的整秒複本（讀檔時解析）'),
    'native/include/Timer.h': ('changed', '7d1c6c85a57f20c7e6c301f3623aa9a5cfe160c0d60fc98aeb790ff412e2cde5', 'Round 27（DLL 0.27.0）；27h／28（0.28.0）：SwitchFacts 帶現在、上次切換、燃盡鎖定；PlanSwitch 的 kBlocked（D4 0.25 秒防抖、D5 燃盡 5 秒不能開）；長流退回實付魔力的 80%（F11）'),
    'native/include/Trace.h': ('changed', '799f6c10b9413941d77be5334148eb72d7daf38480b6a044bafad8c0e729875c', 'Round 27（DLL 0.27.0）：引擎膠合（E1–E13）：E12：Utf8Fit（名字與被切斷的行不留半個字）；E7：Buffer::TryTake（結束時不等鎖）；27b：Buffer 用 lk::Mutex（A N4）；27h／28（0.28.0）：switch 行在 kind=blocked 時帶 reason=debounce／burnout-lockout'),
    'native/include/TrueHud.h': ('changed', '42d2370e76b33e47e0683b6fbfdf6aa761837f15e42ef0e46c2d1e401d59e242', 'Round 27（DLL 0.27.0）：引擎膠合（E1–E13）：E13：每次載入要求的 generation，舊的回呼作廢；關閉時舊要求的回答也作廢'),
    'native/src/Plugin.cpp': ('changed', '61e52f7bbf55dbfc89e1a551046c9fc5b016663c5147a784a791a4bef0d447b9', 'Round 27（DLL 0.27.0）：E1–E13、G6–G12（見 build/native-verification.md Round 27）：登記表與 OVERLAP-READ 見證；SehFilter；QueueTask 帶 epoch；受擊按幀與自己的生命帳；GateNow 不走 menuStack；EventText；ScanDomains 先收再做；null cell；ESL 拒載；計時先走時鐘、關閉或故障時移除 TrueHUD 條；OpenLog 不丟例外、Query 先填 info；主選單結束 session；屍體模式（G6）、連殺讀命中 sink 的潛行旗標、剛結算的印記（G9）、施法中與命中前生命在 sink 讀（G10）；形態切換由 DLL 在 task 裡做完（G8：SwitchWork、SwitchMarkers、CloseByMagicka、KeepSync）；T：DispelLive、Guard、TickCpp 的順序、BuildCrowd 的 engaged 讀取改用 Runtime.h；27b（DLL 0.27.1）：登記表的 handle 鍵、死亡第二事件與卸載 sink 的 Forget、世界時鐘、SEH 鎖深度與 stack overflow、遊戲就緒 task 的 sessionOnly、選單 sink 故障時仍結束 session、GetHandle 移到鎖外、自己的生命只記精確數值、屍體模式的事件過濾（A N2–N10）；火源條件（B N3）、屍體模式不花資源（B N6）、潛行紀錄（B N7）、過期終焉的剛結算印記（B N9）；27c（0.27.2）：Context 改用 Runtime.h 的版本；[ESSB][BADMAG]；27d（0.27.3）：RingWatch——除錯等級 ≥3 時光圈生效／失效各記一行 [ESSB][ring]；27d：SwitchWork 的節點讀取器改成具名變數（0.27.2 崩潰根因）、Executor 拒收暫存的 Tuning；27e（0.27.4）：NodeRank／NodeBranch／BranchesGained 原生函式（MCM 卡頓：技能樹階數不再靠 Papyrus 快取）、StatsMenu 開啟時記下分支、ESSB_Lethal 每秒最多一次；27g（0.27.6）：ESSBNative.SettleBranch 原生函式（分支退回訊息：Papyrus 用它結算，規則有單元測試）；27h／28（0.28.0）：1-1 世界時鐘統一（ReadMemberFrom、印記結算、潛行紀錄）與 death／settle／hit-late 行的 world= running=；1-2 故障分級（SessionFault、ClearSessionFault、故障時關形態、RunningSeconds 不故障、Select 不丟例外）；1-3 白熱全身特效的 L3 記錄；1-4 形態能力與同調保留在切換 task、ESSBNative.CloseForm；1-5 命中 sink 不讀背包；1-6 領域記錄（不再掃 60 公尺）、TargetSecond 只讀帶本模組效果的角色；1-7 讀檔重設各帳本；重疊的 task 直接返回（OverlapCount）；Papyrus 審查：ESSB_PapyrusReady 與待切換、技能樹分支在選單關閉時由 DLL 結算、洗點原生、perk 快照、PoisonedNearby、CastWith、領域標記上身記錄；探針：事件序號與延遲、每秒 rate、每 10 秒 [ESSB][vm]、[ESSB][form] 檢查、[ESSB][pts] 點數檢查、ForceFault 故障演練；使用者決定：防抖、燃盡鎖定、火源印記旗標；28b（0.28.1）：F1 CastWithWork 由 Runtime.h PlanCastWith 決定（有強度的法術用效力 1＋整秒複本，不再把秒數當效力）、執行器的 Cast 拒絕把效力用在有強度的法術；F2 kPostLoadGame 成功分支在 OnGameReady 前清 ESSB_PapyrusReady；F3 GameReadyCpp 清領域登記；F4 故障關形態時驅散護血池與餘響待發；F5 印潮改成切換後第一擊開印（surgeArmed，只有切換會設）；F7 水臨強化 10 秒冷卻（執行時鐘，讀檔歸零）與 L4 行'),
    'native/tests/anchor_test.cpp': ('added', 'c56497a2a23662de00f57914c67a2918e31634cf6e67fa0f976623f72a4a5f50', 'Round 27（DLL 0.27.0）：新測試（ctest anchors）：G1 的手算錨點（碎冰 962.5／465、聖裁 III 135／67.5、死咒 540／1020、血 650／195、霜終結 420、催化 65、G3 詛咒 7、G4 洩熱、843 個 op 的爆發不溢位）；27b：催毒錨點改 38（B N5）；Review27bAnchors：焚天 ≤ 主終焉、開印劑數不隨節點倍率、火源、屍體模式；27g（0.27.6）：DamageMultAnchors：傷害倍率 0.8 讓死咒、火源、血刃、小滅法、滅法、放血都剛好 ×0.8；27h／28（0.28.0）：RotationAnchors（熱鍵輪轉：第一次之後不切印、不造成傷害、同調所得不隨目標數增加）、WaterAdventAnchors、SourcedBurstAnchors、FixAnchors（死咒首領、導引、三重奏冷卻）；28b（0.28.1）：F5 SurgeAnchors（0 個沒印記→0、範圍內 3 個→2、16 公尺→排除、已有印記→排除、沒有分支→沒有計畫）；F7 WaterAdventCooldownAnchors（0 秒發動、5 秒不發動且剩 5 秒、10.5 秒再發動；冰臨強化沒有冷卻）'),
    'native/tests/asan_harness.cpp': ('added', '36b48f01c684951ed1f141f893af3b5ecfd32419b41a49f770a047ebec14db00', 'Round 27（DLL 0.27.0）：27d：AddressSanitizer 用的不丟例外測試（Context 複製、具名節點檢視、24 目標融斷、登記表雙執行緒、受擊佇列）'),
    'native/tests/engine_test.cpp': ('changed', '6e05615537ece92ad30c4ad21a2cae83c1dd4feb9a00fcc3bf7d691cc468f534', 'Round 27（DLL 0.27.0）：27c：inf／NaN／4e22／效力 0 的操作被丟掉；27h／28（0.28.0）：死掉的目標不再被施放印記與狀態'),
    'native/tests/hit_pipeline_test.cpp': ('unchanged', 'a6acfdd1ec3b77e8b2e9baddceb7190f9551c1e5366252c8852200a65846b357', ''),
    'native/tests/lifetime_net.cpp': ('added', '808644c9fa785f0150d83278bdd05fe024044eed01c4010663e41ec990978a21', 'Round 27（DLL 0.27.0）：27d：生命週期網的負向對照（字串檢視綁在暫存物件上，clang-cl 必須報錯）'),
    'native/tests/load_test.cpp': ('unchanged', 'c1b5e69dc7e47d968f3afb2798bbbba4964bb7437d60e21c31598bdf8070148d', ''),
    'native/tests/reaction_test.cpp': ('changed', '68de3b8fbefe79724a1304ca09bf06d48b47ad8f9ce6aa35fc01174d4bbcce80', 'Round 27（DLL 0.27.0）；27h／28（0.28.0）：狀態紀錄接受 ESSB_N7_ 前綴；28b（0.28.1）：F5 PlanSurge 不再帶舊元素'),
    'native/tests/runtime_test.cpp': ('added', 'b18329fe6562fc0c52564220705642534bd6a5546db5d3e13cc0bbf0022e7e37', 'Round 27（DLL 0.27.0）：新測試：task scope、session 與新遊戲、log 與 Query、SEH 判定、輸入閘門、事件文字與 UTF-8、登記表（兩條執行緒）、受擊佇列與自己的生命帳、屍體模式、剛結算的印記；T：驅散重找、原生守衛、計時順序、人群讀取；27b：Review27bChecks（A N2–N10、B N7、B N9）；27c：ContextChecks（回傳的複本讀自己的 tuning）；27d：RingChecks；27e：BranchChecks、LethalChecks；27g（0.27.6）：BranchChecks：分支點數夠／不夠、0.27.5 回報的情形（火焰 10 點：6 階主線＋4 分支全退）、點數守恆掃描；27h／28（0.28.0）：FaultChecks、DomainLedgerChecks、HitGateChecks、ProbeLedgerChecks、SwitchRuleChecks（防抖、燃盡、同調保留）、OverlapHarness（兩條執行緒同時跑計畫與共用容器）、Scope 的 Overlapped；28b（0.28.1）：F1 CastWithChecks（恐懼 4 秒、狂刃 1 秒、ApplyUtil 緩速 3 秒、超過上限、守勢窗口、化灰、ApplyUtil(4) 不變、沒有複本就拒絕）'),
    'native/tests/self_test.cpp': ('changed', '2e5ed9a3ce8e6307363285fabec3f0b0f8f4f3f4fa6ffe5a0629f8558d623c23', 'Round 27（DLL 0.27.0）：27d：static_assert WithAvatar 不收暫存物件；27h／28（0.28.0）：狀態紀錄接受 ESSB_N7_ 前綴'),
    'native/tests/status_test.cpp': ('changed', 'a382d1a0f391d13903323123482f4fa0f1ecda8cf196a7e2d2c23538cfdab123', 'Round 27（DLL 0.27.0）；27h／28（0.28.0）：狀態紀錄接受 ESSB_N7_ 前綴（round 28 的三重奏冷卻）'),
    'native/tests/timer_test.cpp': ('changed', 'c634d8d5cc5a4a856554a4d589a835591f8de75cace5a340ae1ad11b49d4caff', 'Round 27（DLL 0.27.0）；27h／28（0.28.0）：狀態紀錄接受 ESSB_N7_ 前綴'),
    'native/tests/trace_test.cpp': ('changed', 'fd33f5e75bef1b2e90d6e93b440f4ff384a46e33325371fb111f5918498e9ee2', 'Round 27（DLL 0.27.0）：G15：綁在熱鍵上的步驟鍵只切換形態'),
    'native/CMakeLists.txt': ('changed', '55cecadc18a786ee6104482d9320fa3152b91cd04f6f312aa278608b15fb177e', 'Round 27（DLL 0.27.0）：版本 0.27.0；runtime_test（ctest runtime）、anchor_test（ctest anchors）；C4717 當錯誤；27b：版本 0.27.1；27c：版本 0.27.2；27d：版本 0.27.3；27d：Release 加 /Zi、/DEBUG:FULL /OPT:REF /OPT:ICF；27e：版本 0.27.4；27f：版本 0.27.5；27g：版本 0.27.6；27h／28（0.28.0）：版本 0.28.0；28b（0.28.1）：版本 0.28.1'),
    'native/build.py': ('changed', '415c7981461374a58e34042fdde2364cc787917dfc2d457bb89d6adad016d04b', 'Round 27（DLL 0.27.0）：runtime 與 anchors 測試的突變（E1、E2、E3、E4、G1、G3、G4、G6、G7、G9、G12、爆發溢位）、G15 的步驟鍵突變；舊突變的原文跟著新寫法（對死者施放、濺射的 SurgeOn）；T 的 4 個突變（Runtime.h）；27b：A-N2／N3／N4／N7／N10、B-N1／N2／N3／N5／N6／N7／N9 突變；E2 突變原文跟著 locksHeld；27c：Context 與 SaneValue 的突變；27d：生命週期網（clang-cl -Werror=dangling* 檢查 Plugin.cpp 與所有測試、負向對照 lifetime_net.cpp 必須被抓到、asan_harness 在 AddressSanitizer 下跑）；27d：DLL 一律產生 PDB，GUID／age 對上 DLL 才複製到 build/pdb/（不出貨）；27g（0.27.6）：27g 突變：剛好 4 點不夠、退回不加回 CSF 的 1 點；27h／28（0.28.0）：27h／28 的突變（故障分級、重疊、領域記錄、命中 sink、防抖、燃盡、連斷保留、死掉目標、D1、D2、D3、D6、死咒首領、三重奏冷卻、導引、長流退回）；28b（0.28.1）：28b 的突變：F1 三個（Runtime.h）、F5 三個、F7 四個（Reactions.h）；D3 突變跟著 waterPlus'),
    'build_core.py': ('unchanged', 'c5468602b5a3d6889b6175bad7e5e1d5ef9321cf48638f6b905ea80b05195ce0', ''),
    'build_melee.py': ('unchanged', '08e8cf2c7c1d386efc6a52d2d31302ba150b8b423b2cbffee1a6d534525c9d4a', ''),
    'build_scripts.py': ('unchanged', '98e6d30c728bd98055c9cc98738e84b3a402979c02e65eb7b5ad9fd7ccd5d434', ''),
    'build_v03.py': ('changed', '7105c485d18a79267dc43d7f13d0227699964424f12fab5bba22c089177e5bb7', 'Round 27（DLL 0.27.0）：G13：武器光改 Enhance Weapon＋ENCH、武器光的條件改讀自己的 ESSB_SyncStage＋ESSB_WeaponGlow、印記效果拿掉命中特效與音效（開印改由閃現法術放）、MCM 武器光開關；G14：DLL 施放的法術加 No Absorb/Reflect（標記加 Ignore Resistance）；G15：冷卻滑桿 0.25～3.0；全域變數 56 個；開印閃現是接觸施放；27b：形態能力改掛四個光圈、MCM「形態光圈」、送給別人的法術加 No Absorb；27e：perk 名稱與描述去掉規劃文件的註記（build/fix27_text.py）、退役節點描述不再寫版本號、除錯等級說明不寫檔名；27g：Custom Skill Menu 的清單名稱加共同前綴與序號（元素魔戰士・01 無元素 … 13 星界），技能 id 不變；27g（0.27.6）：技能樹選單的列名依序排（MSM_ORDER）；分支描述開頭寫「分支：需 5 點。」（BRANCH_COST_TEXT）；round-4 設定檢查允許使用者決定的傷害倍率 0.8；27h／28（0.28.0）：fix28 紀錄與 MCM「白熱全身特效」；fix28_verify 接進建置；round-4 設定檢查不變；28b（0.28.1）：F1 記下每個 SPEL 的子紀錄、寫 CastWith 複本、複本的傳遞方式；F6 註解不再提原型腳本；28c（0.28.1）：perk 描述改用 fix27_text.node_text（以 ESSB_P_樹_路線_階_M／_B格 為鍵的覆寫）'),
    'fx_extract.py': ('unchanged', '4ae15444ac287131499f2a076c9611b11d40762e2cbae53cd290e0ef2927d9c5', ''),
    'inspect_magic.py': ('unchanged', '2a7ec48b000b6647d0e625ff24901e591df9b3bba7f3d9fbeb00c3a46d746fab', ''),
    'plan_coverage.py': ('unchanged', 'ce47f5d229a94dcb1b2c2c1ac4452cbd24da40a6b7cdc606ca729677b7af57dc', ''),
    'plan_trees.py': ('unchanged', '6a921d3278dff9b1ebc81b1dcb58b063e677c58509e176a49a00de73d0af4123', ''),
    'render_plan.py': ('unchanged', '266e1f87c3946bf91c927a8a8673c8fb518f67c25d104967f3e56c53a7b7db23', ''),
    'setup_compiler.py': ('unchanged', '84cc8e0f6bf094c53ad281ab53c40a90718c8e654d3634cd2c787cb4f6763c36', ''),
    'tes.py': ('unchanged', '0cec676788f1993014781215cdfde38c8a5b6363a0e5ab92fe876e2455610c74', ''),
    'tree_v04.py': ('unchanged', '943483ba2a763b7de9ef13847fd4465fa6d472432a77dda5b9938e9661d9d18a', ''),
    'build/fix19_native.py': ('changed', '0190eb741558ced32104b764c7fcdcbfebbc8baff1d591233c8a0bc981b1fc21', 'Round 27（DLL 0.27.0）：NATIVE_VERSION 0.27.0；G8：manifest 的 spells 加 kEchoPendingSpell、kTwinWindowSpell，header 加 kTwinWindowRecordSeconds，ROUND27_NODES（雙生）；27b：NATIVE_VERSION 0.27.1；27c：NATIVE_VERSION 0.27.2；27d：NATIVE_VERSION 0.27.3、光圈效果編號、ESSB_WeaponGlow 進 manifest globals；27e：NATIVE_VERSION 0.27.4；27f：NATIVE_VERSION 0.27.5；27g：NATIVE_VERSION 0.27.6；27h／28（0.28.0）：NATIVE_VERSION 0.28.0；manifest 的 spells 加 kFormAbility1..11、globals 加 ESSB_PapyrusReady／ESSB_HeatBodyFx／ESSB_Pts_*、狀態加 fix28 的 KINDS、ROUND27_NODES 加承接／永續／連斷／免門檻；28b（0.28.1）：NATIVE_VERSION 0.28.1；ManifestData.h 的 status::kCastWith'),
    'build/fix21_records.py': ('unchanged', 'ce5a656d0377bace72736048358cf8c74c79f997448d027a60be934ad8b1fd1f', ''),
    'build/fix22_records.py': ('changed', '37246f7914234703fcef9b33c578a1760f1c2e9d40ba6b75ab3499e89b4a7903', 'Round 27（DLL 0.27.0）：G13：狀態的著色（凍結、冰晶閃、血痕、催毒、浸濕、水壓、詛咒、星痕、死咒閃），取自規劃 2.11 點名的紀錄；27f：白熱／熔燒／熔身的全身火焰改用原版火焰斗篷（著色＋火焰 art）；催毒著色改 Venomancy 毒霧（Rotflesh 的貼圖路徑在原模組就壞了）；27h／28（0.28.0）：白熱／熔燒／熔身的狀態效果不帶著色；身上的火是法術裡另一個效果（fix28 ESSB_HeatBodyFxEffect，條件 MCM 白熱全身特效）'),
    'build/fix22_reference.py': ('changed', '1dd873ab925848feca47f6e138893e40dd7fe6f76e0ceab83141864fac20e5d5', 'Round 27（DLL 0.27.0）：G1（加法的 M_mod＝1＋Σ，K 類係數維持乘法）：Python 參考模型跟著 Status.h：加法終結、碎冰、催化、暗蝕、死咒、聖裁 T、開印層數、慈光、瘴氣、洩熱；27b：參考模型跟著 C++（B N1 carried、B N2 開印事件的層數、B N5 催毒）；27h／28（0.28.0）：參考模型：強制開印跳過有印記的目標（D1）、導引不乘本體、死咒已損生命段 ×傷害倍率 ×首領 0.5'),
    'build/fix22_fixture.py': ('changed', '1440c62acdcfa248f25ff269d18d39bfa73470c19559ee2c2a7ba94e59d20cd0', 'Round 27（DLL 0.27.0）：G5：瘴氣錨點改 1.5（不乘 NodeScale）；27h／28（0.28.0）：狀態種類接上 fix28 的 KINDS'),
    'build/fix23_records.py': ('unchanged', '3a0f7d2f1820798f3333dbd087041363f5b9ce235ae998bf80ffe877aa530dce', ''),
    'build/fix23_reference.py': ('changed', '8ce32d1a23c5102d788d5f0f9b3b72e277acab9bbc69891e19a618f7cfbc7869', 'Round 27（DLL 0.27.0）：G7：參考模型的護血跟著護血池走；27b：end_body 帶 carried（B N1）；27h／28（0.28.0）：參考模型：三重奏冷卻、強制開印的自身所得一次（D2）'),
    'build/fix23_fixture.py': ('unchanged', 'e0a52a875b1872b8ac1b7fc1e6fe40de355775154ed8959fb90b25424bf49156', ''),
    'build/fix24_records.py': ('unchanged', '0116b08561c4a8575c2be56c8dcb174a0d46bf0b5c4b8273ca30dce7bed004e6', ''),
    'build/fix24_reference.py': ('changed', 'a36d7af30d446e75920fb3abda7f9b1e735c5a33598aaa39696adf76d0749049', 'Round 27（DLL 0.27.0）：G1（加法的 M_mod＝1＋Σ，K 類係數維持乘法）：參考模型跟著 Reactions.h：簽名加法、BurstLines、終結本體、BurstMult 只剩 K、湧動 pct_scale、聖裁；錨點：霜終結 17.43、爆發 31.248；27b：參考模型跟著 C++（B N1 連鎖帶加總、B N2、B N4）；27h／28（0.28.0）：參考模型：臨／印潮的自身所得一次（D2）、水臨強化（D3）、大潮導引、連殺；28b（0.28.1）：F5 參考模型的新印潮（沒有印記的人、最近 2 人）與兩個情境'),
    'build/fix24_fixture.py': ('unchanged', '67b0a52a95d46963bb9077c6129ec1dd7a95b1b07cddf6faba0e273bbb79c1bc', ''),
    'build/fix25_records.py': ('changed', 'd039a00752e39cc721ec13656723444e19db717708f721ca84115a4e582ea6a6', 'Round 27（DLL 0.27.0）：G13：火、冰、聖、星的領域用原版危險區模型（看得見範圍），其他維持空模型；27b：火領域換 FXFireOilHazard（較大）；27h／28（0.28.0）：領域危險區每個效果都帶條件：不是你、不是隊友、敵對（Papyrus 審查 5）'),
    'build/fix25_reference.py': ('changed', 'c0ab7a6d4be3793bcc52fede614bf610f5750b0e2c8b950ca8ff84db3614dc30', 'Round 27（DLL 0.27.0）；27g（0.27.6）：維持費 2.5%（暗 3.5%），手算錨點跟著改（使用者 2026-09-27 的平衡決定）；27h／28（0.28.0）：維持費 5%（暗 7.5%）、長流退回實付的 80%（F11）與它的手算錨點'),
    'build/fix25_fixture.py': ('unchanged', '5a6856c16b38e6a07b363b7f4449415ea8fc2772bd37a1f43d3546e0b72b8835', ''),
    'build/fix26_records.py': ('unchanged', '8c8fa641dc766e4fb01471fc2b27b911d19e20325444c0c50c83fce9e1b0a54f', ''),
    'build/fix26_format.py': ('changed', '4b6a9cd0f8a20a7a409e5cf7713717d6d3ba8ddb4e4746b8a14ee647a5ff4681', 'Round 27（DLL 0.27.0）：G6：hit-late 行可帶 mode=corpse；27h／28（0.28.0）：world= running=（death／settle／hit-late）、switch 的 reason=、rate 與 vm 兩種新行'),
    'build/probe-judge.py': ('changed', 'f44c72dd82277d473e83e4e1d8c6f754c584dd928f7a0980ab9b728cdbd7c643', 'Round 27（DLL 0.27.0）：SETUP-1 判 0.27.0（VERSION 常數）；[ESSB][OVERLAP-READ]（E1）與 [ESSB][crash]（E2）出現＝FAIL；27b：VERSION 0.27.1；27c：VERSION 0.27.2、BADMAG＝FAIL、SETUP-1 的 X1 改要 input task（G8 之後站 1 不再排 queued native task）；27d：VERSION 0.27.3；27e：VERSION 0.27.4；27f：VERSION 0.27.5；27g：VERSION 0.27.6；27g（0.27.6）：傷害倍率從 log 的 mcm-state／mcm 行讀出（Line.dm、Line.d），傷害數字除以當下倍率再比（新遊戲預設 0.8）；27h／28（0.28.0）：VERSION 0.28.0；時鐘漂移警告；F-01 故障演練、F-02 HDT-SMP 站；每秒事件／原生呼叫摘要；Papyrus.0.log 掃描；28b（0.28.1）：VERSION 0.28.1；B-29 水臨強化的 10 秒冷卻；D-14 新印潮'),
    'build/fix27_visuals.py': ('added', 'b19f77afac07a95c8edaf27c2391e2a29b1d8aaad3d6a9252f77eae66eacfdbe', 'Round 27（DLL 0.27.0）：G13：視覺提示的盤點與建置檢查（新檔）；27b：光圈檢查、送給別人的法術檢查、INVENTORY 依審查 C 重寫；27d：光圈的 ARTO／模型檢查、不准再用 *CastBodyFX；INVENTORY 更新；27f：INVENTORY 的全身火焰一列'),
    'build/fix27_records.py': ('added', 'f669d43ffd0968db3949b2300dc076bcd0e15c3e23fe57429c949e508295aef3', 'Round 27（DLL 0.27.0）：G13、G14 的新紀錄（新檔）：ESSB_WeaponGlow、武器光 ENCH 與它的效果、開印閃現；DLL 法術的 SPIT 旗標；27b：形態光圈 ESSB_FormRingEffect_<X>_0..3、切換號碼牌的兩個全域變數、送給別人的法術都加 No Absorb、ENCH 退役；27d：光圈改用我們自己的 ARTO（ESSB_FormRingArt_<X>，原版地面符文與恢復圈模型；0.27.1 的施法光圈看不到）'),
    'build/fix28_records.py': ('added', 'c999958f4e74406003246162b420e6dbe192a32c9853e4880ecce5f98f66d8fe', 'Round 27（DLL 0.27.0）；27h／28（0.28.0）：新檔：ESSB_PapyrusReady、ESSB_HeatBodyFx、ESSB_HeatBodyFxEffect、三重奏冷卻（KINDS）；28b（0.28.1）：F1 CASTWITH：8 族（恐懼、瘋狂、狂刃、ApplyUtil 0／13／23／25／26）× 1..20 秒的複本，只改 EDID 與 EFIT 秒數'),
    'build/papyrus_budget.py': ('added', '9947d2df2bfce404160af9c8b3a2e50c9b8dabfde4ffbd291c570f33b8d6563b', 'Round 27（DLL 0.27.0）；27h／28（0.28.0）：新檔：Papyrus 處理器原生呼叫數的離線上限（fix28_verify 的預算）'),
    'build/fix6_verify.py': ('changed', '9015dbd28d90c06dad7757c6b5ec5d1cac12ab1177fdf5c2c3f6cc6c3b261ca5', 'Round 27（DLL 0.27.0）：27e：perk 描述比對改用玩家文字（build/fix27_text.py，去掉規劃文件註記）；27h／28（0.28.0）：ApplyUtil 改由 ESSBNative.CastWith 施放：模擬它把這次的強度交給法術（慢速上限的檢查照舊）；28c（0.28.1）：perk 描述比對改用 fix27_text.node_text（逐節點覆寫）'),
    'build/fix11_verify.py': ('unchanged', '5fb7e48ad43e7ec8d6c6315b435aa936ae969e0d70213d37666e8b1b38ba128b', ''),
    'build/fix16_verify.py': ('unchanged', '2bec8fb1527226b91936f4f3140fec08d33ec88fb89cb84da1d5eebda3f5b26d', ''),
    'build/fix21_verify.py': ('unchanged', '84f2650ff08009991e5d4a6541ec22f1249459e8bc212d78e40db737d3af7de0', ''),
    'build/fix22_verify.py': ('changed', 'ce7543bf8cfda740cf014af251dde921c351e405b49a31ad04bfd054ef079d9e', 'Round 27（DLL 0.27.0）：T：Guard 的 try／catch 搬進 Runtime.h GuardRun，檢查跟著讀它；27h／28（0.28.0）：MCM 動作的檢查：ESSB_NativeHit 1 才算運作；0 時 IsOperational 為否、IsReadyUI 照舊；「沒有總開關」的注入錯誤跟著 IsOperational 的新寫法'),
    'build/fix23_verify.py': ('unchanged', '531575bf68910efcb5a0e1b6472d9b36f20b13ab7fba684ac944f6fbff9e5e88', ''),
    'build/fix24_verify.py': ('changed', 'c6f80084e87b6bba94bf9a67ab42db3aacf7736add21f70378c29184141066f7', 'Round 27（DLL 0.27.0）：檢查跟著新寫法：task 經 QueueTask（帶 session 票的 AddTask）、死亡 sink 用 ReadMemberFrom、OnFormClosed 多了參數；27h／28（0.28.0）：關閉的融斷改查 SwitchWork 的 BurstWork（Papyrus 的 OnFormClosed 刪了，融斷在切換 task）；注入錯誤跟著改；ApplyUtil 的慢速上限檢查模擬 ESSBNative.CastWith'),
    'build/fix25_verify.py': ('changed', '06c97aba6e99a01ccc27187d15224bce80119281ca52bb4c956e5dffd7320eb5', 'Round 27（DLL 0.27.0）：檢查跟著新寫法：切換在 SwitchWork 送 ESSB_Switch（G8）、計時 task 經 QueueTask、GameStopped 讀 session；G13：火冰聖星領域的危險區模型；計時 task 的順序改由 PlanTick（tick.second）；27h／28（0.28.0）：ESSB_Switch 交給 FormOpenedFx／FormClosedFx（形態在 DLL）；SetSyncKeep 刪了，不再列在秒數窗口'),
    'build/fix26_verify.py': ('changed', '5b068f64be458f8c0861cb631e277859fb17b5f14cda8cfacffb3db06c2f0b44', 'Round 27（DLL 0.27.0）：檢查跟著新寫法：sink 經 QueueTask、重疊計數在 Runtime.h Scope、配接器的 Dispel 多了屍體與剛結算的記錄；版本改成「一個值、不早於 0.26.3」（0.27.0 由 fix27_verify 釘住）；27c：SETUP-1 樣本的 X1 用 input task；27g（0.27.6）：A-09 的注入錯誤不再寫死 2.98（維持費 2.5% 後原生樣本是 7.45）；27h／28（0.28.0）：settle 樣本帶 world= running=；命中 sink 的注入錯誤跟著 ReadAttack(ev)（手上的東西改在 task 讀）'),
    'build/fix21_identity.py': ('changed', 'ffdbc21308455fc940e00af9e78bd50bb21787b4aba8e9d6002f3ff22d370e30', 'Round 27（DLL 0.27.0）：27e：允許 NodeRank／NodeBranch／分支遮罩依座標讀（座標來自 ESSBNodes 依名稱的讀取）；27h／28（0.28.0）：perk 快照、選單關閉結算、洗點、點數檢查的座標讀取（取代 NodeRank／NodeBranch 直接讀 perk 的兩行）'),
    'build/fix22_history.py': ('unchanged', '240a13c40d9f71aef8ca1bde8a52d360fee3cdaa741b86bc603547cfe3de6400', ''),
    'build/fix22_history_gen.py': ('unchanged', '9ce3e53af1a4b133c6b2b5f7923b8adf61a220a9514ff360f34114beb58a0986', ''),
    'build/fix22_history_template.py': ('unchanged', 'a35ae3589d6915e83c958fd2ab50c12106758a749139297a2ac58df29e80a6ef', ''),
    'build/fix22_native_history.py': ('unchanged', '7434300bdc494ce9b08e4be01dce3c17acfa0337a7d125c6fb29091d59cae3eb', ''),
    'build/fix22_native_history_gen.py': ('unchanged', '4e3891aa13897b8e9128244f5e3fbe5a23f73e9c9037ce9743fad11d41a9fb89', ''),
    'build/fix22_native_history_template.py': ('unchanged', 'dcacd1e45bf22b805eba7c942c1fbb67be2d95c16b8bf661ef1ed559e7880776', ''),
    'build/fix23_history.py': ('unchanged', 'ddef56511804d1d5aa92631f2eaf5903a4b90a6838ba1ed83be6521c9e49c154', ''),
    'build/fix23_history_gen.py': ('unchanged', '5d9a4998a5a220c72a6372f9158b5724ac40a05691559b77aa8968b71f745534', ''),
    'build/fix23_history_template.py': ('unchanged', '102bfd1b1ae43e6cc442476dc6e71e2ca843f81b3141da731cb503d9523b4d3d', ''),
    'build/fix23_native_history.py': ('unchanged', '7c7d137fe5082a3323727ec2dcd4d3674030216e8f642856d1a172716831af71', ''),
    'build/fix23_native_history_gen.py': ('unchanged', 'fb56d60d5030e3c9b9bd0a9cdcff25747884b532a3b63a5283988b0c76611886', ''),
    'build/fix23_native_history_template.py': ('unchanged', 'ba3bb7bd77ad59d86dd91a0ae5aebec2c9aca0b408de5ee4e723882bf13258f3', ''),
    'build/fix24_history.py': ('unchanged', 'a8396d5d770d0b4e7a2ba16892cbc3e611db01521ccb52eb2ae9d025d933fff1', ''),
    'build/fix24_history_gen.py': ('unchanged', '566509f432b8e7ae75d1125a59d5c4ac2b8dbd423eb07ee6c98e20ea2467b782', ''),
    'build/fix24_history_template.py': ('unchanged', 'c7dd09804821427fe7ee083983240c745efb3402b0764140c8f14068f9fb3b4e', ''),
    'build/fix24_native_history.py': ('unchanged', '65c8787b9c79794099e1f3efa1d0d0aee27893b46c58f822774bf672d441fd1a', ''),
    'build/fix24_native_history_gen.py': ('unchanged', '237b7e91406ce4bab1bf3f513e900bb94da0e95aa569ad4a0a2dd22e79288f06', ''),
    'build/fix24_native_history_template.py': ('unchanged', '49b8debbdd272a6c90d92868cff2338d71e440eede81718736cc64b7a495dce4', ''),
    'build/fix25_history.py': ('unchanged', '3c215cd9f66d65f82736462108585f7f28c14746c918c98bdc48e8a272d5ea05', ''),
    'build/fix25_history_gen.py': ('unchanged', '7bf425eebd501efb9690cef38cff3f0b3258f0ef56ef59e51ea4e0eb24cc38e4', ''),
    'build/fix25_history_template.py': ('unchanged', 'bc2fe79a2a43aa51d0c8828b7962e811b224381f6b25cba4546cd352a8afd3f5', ''),
    'build/fix25_native_history.py': ('unchanged', '9014bf547291024dda5578f0325065f4577e9b6c0cec2220266fd99d431a89b6', ''),
    'build/fix25_native_history_gen.py': ('unchanged', '8083578fae81e5bfb7921dd042601fe608d56f899cd4d7e9c8d04383a6105974', ''),
    'build/fix25_native_history_template.py': ('unchanged', '720cf5f28fe5dc2a012956fc61a7b27eaa5d4aebc2aa847c52fb2412c69edfd7', ''),
    'build/fix26_history.py': ('changed', '4fcf80e50b503b8cbaca702a3d418e0dec42a1e9181cf3654b48344cec070197', 'Round 27（DLL 0.27.0）：round 26 的 Papyrus 封印改讀 pre-fix27 快照（先過 round 27 的證明；由產生器重寫，表格不變）'),
    'build/fix26_history_gen.py': ('changed', '723db6f80f7c11770400a2b54816d28d5b08ed4600c497315b35f0f90641d0e9', 'Round 27（DLL 0.27.0）：產生器讀 pre-fix27 快照的 src（round 26 出貨時的腳本）'),
    'build/fix26_history_template.py': ('changed', 'c9ba3de11715264e1bf0a7d947795536c24e7007a3ba98b85530266c6d6b17b8', 'Round 27（DLL 0.27.0）：current_dir 改成 fix27_history.legacy_source()'),
    'build/fix26_native_history.py': ('changed', '81cd0abfdcbb1bf5f92b8005eb9c8f88610fd442a46c7c85ca78b4f615ceb207', 'Round 27（DLL 0.27.0）：round 26 的原生封印改讀 pre-fix27 快照（先過 round 27 的證明；由產生器重寫，表格不變）'),
    'build/fix26_native_history_gen.py': ('changed', '58dc05cadd674fa6e5d89a38511716c9cc7cf3b212126d84201758a815e464b6', 'Round 27（DLL 0.27.0）：產生器列出並雜湊 pre-fix27 快照（round 26 出貨時的位元組）'),
    'build/fix26_native_history_template.py': ('changed', 'a21caadaced675b29f4611e29e28111cd047af6fefd54cb940e9d20e87fd5736', 'Round 27（DLL 0.27.0）：base() 讀 pre-fix27 快照（同 round 26 對 round 25 的做法）'),
    'build/fix27_verify.py': ('added', '034286f61fc822e24be6a637c9a4b27ba86b1cff0c4f38230f1f91126ca21f24', 'Round 27（DLL 0.27.0）：round 27 的驗證器（新檔）；27b：光圈的注入錯誤、版本 0.27.1、A-N2／B-N1／B-N2 突變必須存在；27c：版本 0.27.2、BADMAG 樣本、Context 與 BADMAG 的原始碼檢查；27d：版本 0.27.3；27d：包裡的 DLL 與 build/pdb 的 PDB 對得上、package/ 沒有 PDB；27e：版本 0.27.4、玩家文字不得含規劃文件的註記（perk 名稱／描述、CSF、MCM）；27f：版本 0.27.5；ASSETS：我們自己的視覺紀錄與身上的火要在原版封存檔裡、活效果用的複本要在已安裝的模組裡（兩個注入錯誤）；27g：版本 0.27.6；27g（0.27.6）：判讀程式依 log 的傷害倍率換算的檢查（0.8／1.5 樣本）；27h／28（0.28.0）：AddTask 規則改成精確（QueueTask、Show、見證各一次，Show 只在 Notify 與讀檔補發）；身上的火改查 ESSB_HeatBodyFxEffect；版本 0.28.0；28b（0.28.1）：版本 0.28.1；28c（0.28.1）：玩家文字檢查加上覆寫檢查（節點還在、名稱與原文沒變、覆寫本身沒有標記）與它的注入錯誤；markdown 與變更註記的樣本；28d（0.28.1）：「自有」的注入錯誤：標記樣本、三種括號註記的清除樣本、括號外的「自有」、寫出的 ESP 裡 perk 說明帶「（自有）」要被抓到'),
    'build/fix27_reasons.py': ('added', '438b2486dbd9f746911ed3d2dcc69aba9b85c3e84a54e51a488ceceec1c5898b', 'Round 27（DLL 0.27.0）：這份理由表（新檔）'),
    'build/fix27_history.py': ('added', 'd84774a6ef133ea7d529d5906b39ea2fea90d0a7eae0308917bed9faba0870c1', 'Round 27（DLL 0.27.0）：round 27 的 Papyrus 封印（產生的）；28b（0.28.1）：F6：重新產生，FILES 多了刪除的 ESSBPlayerAlias.psc（sha256 取自 pre-fix27 快照）'),
    'build/fix27_history_gen.py': ('added', 'd7832e51bc27a330703d06270a218f2b9ab9d357bb19292ee53281820f4616ed', 'Round 27（DLL 0.27.0）：round 27 Papyrus 封印產生器（新檔）；28b（0.28.1）：F6：FILES 登記刪除的 src/ESSBPlayerAlias.psc（原型腳本）'),
    'build/fix27_history_template.py': ('added', '5fb43fe48c7475afcefe07734cb88ff0332eac7ab1ef51c7c9ffa1c923a7ab80', 'Round 27（DLL 0.27.0）：round 27 Papyrus 封印樣板（新檔）'),
    'build/fix27_native_history_gen.py': ('added', '36615e28edbe5fe2ae5da29a977ea619a4c35840d7be14f3cdc60ace98175995', 'Round 27（DLL 0.27.0）：round 27 原生封印產生器（新檔）'),
    'build/fix27_native_history_template.py': ('added', 'f234de9d7e8e9bff1dfea345cafef2c8f812a8de7180b934dd88d8158e824aa4', 'Round 27（DLL 0.27.0）：round 27 原生封印樣板（新檔）'),
    'build/fix28_verify.py': ('added', 'fe19f784feecc79c5721fa8cc23a40f8ea3ae6c221f743c90f2bef5b38d21cba', 'Round 27（DLL 0.27.0）；27h／28（0.28.0）：新檔：兩份審查的規則（切換在 DLL、Papyrus 就緒、技能樹、IsOperational、共用法術紀錄、掃描、故障分級、危險區條件、原生呼叫預算），每條都有注入錯誤；28b（0.28.1）：F2 三個讀檔點依位置檢查；GAMEREADY、FAULTCLOSE、CASTWITH（ESP 複本、DLL 表、每個 Papyrus 呼叫點）、SURGE、ADVENT 與它們的注入錯誤'),
}

FOLDERS = ('native/include', 'native/src', 'native/tests')


def base() -> Path:
    """Today's bytes (a later round moves this to its own pre-round snapshot, as round 27 did for build/fix26_native_history.py)."""
    return ROOT


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(rel: str, data: bytes) -> None:
    state, sha, why = FILES[rel]
    assert _sha(data) == sha, (rel, state, 'differs from the sealed bytes (edited after sealing; regenerate with a reason)')


def verify() -> dict:
    root = base()
    for rel in FILES:
        path = root / rel
        assert path.is_file(), (rel, 'sealed file is missing')
        check(rel, path.read_bytes())
    for folder in FOLDERS:
        for path in (root / folder).glob('*.*'):
            rel = path.relative_to(root).as_posix()
            assert rel in FILES, (rel, 'new file in a sealed folder, not in the seal')
    return {s: sum(1 for v in FILES.values() if v[0] == s) for s in ('unchanged', 'changed', 'added')}


# Silent edits (a constant or a condition changed without resealing): each must fail check().
SILENT_EDITS = [
    ('native/include/Registry.h', 'inline constexpr float kExpirySlack = 0.35f;', 'inline constexpr float kExpirySlack = 0.5f;'),
    ('native/include/Runtime.h', 'inline constexpr std::uint64_t kHurtMaxWaitMs = 150;', 'inline constexpr std::uint64_t kHurtMaxWaitMs = 1500;'),
    ('native/src/Plugin.cpp', 'SwitchWork(*player, p.kind, facts.active ? facts.current : 0, p.element, 0);', 'SwitchWork(*player, p.kind, 0, p.element, 0);'),
]


def self_check() -> dict:
    counts = verify()
    caught = []
    for rel, old, new in SILENT_EDITS:
        data = (base() / rel).read_bytes()
        assert old.encode('utf-8') in data, (rel, old)
        try:
            check(rel, data.replace(old.encode('utf-8'), new.encode('utf-8'), 1))
        except AssertionError:
            caught.append(rel)
            continue
        raise AssertionError(('silent edit not caught', rel, old))
    return dict(counts, silent_edits_caught=caught)

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
    'native/include/HitMath.h': ('unchanged', 'e5bbc95f57d37a68a1cd21194bf3a2e663cc7a5794ff9d3dc7ff36189bc1e469', ''),
    'native/include/HitPipeline.h': ('unchanged', '24d441cb6742fc20e2fae6e21a2bf8d56e90d9f7a0c84bc9bc3545ee89e9bc09', ''),
    'native/include/Hurt.h': ('changed', 'f3e5bc40bf4c9e80b4b2d5066357bf200dcb550dd69d20c3e562b5398d4298d4', 'Round 27（DLL 0.27.0）：G7：HurtFacts.ownDelta，lost = before − after + ownDelta（我們自己的扣血、治療不算敵人的傷害）'),
    'native/include/Load.h': ('unchanged', '88d1bf95729dc56ce0b55f2a84632c71bc2a978f7602fb826063537677145c3d', ''),
    'native/include/Locks.h': ('added', '223802bd99e5e572e0e837c6d72ba52ecb8424fbf93b31f3d90ee34396630c0a', 'Round 27（DLL 0.27.0）：27b（審查 A N4）：新純標頭：lk::Mutex（自己計數的鎖）與 EnterEngineLock／LeaveEngineLock，SehFilter 在持鎖時不吞例外'),
    'native/include/ManifestData.h': ('changed', '0108200b541d4617a2e5107dafd1aa566bab8e0dbe092331403a02a4b651223e', '由 build/fix19_native.py 產生：Round 27（DLL 0.27.0）：版本 0.27.0；G8：kEchoPendingSpell、kTwinWindowSpell、kTwinWindowRecordSeconds、node::kCommonTwin；27b：版本 0.27.1；27c：版本 0.27.2；27d：版本 0.27.3、kRingEffectFirst、kRingStages、glob::kWeaponGlow；27e：版本 0.27.4；27f：版本 0.27.5'),
    'native/include/NodeIds.h': ('unchanged', 'fd843a2bded8e5bf423c87801bbbfe071a5189f8d5e05c15d0dee605ef8fe5f3', ''),
    'native/include/Reactions.h': ('changed', '2bef064e717a4c5bee5cdfb76b54394f4f05827c882af871a4c042e701088254', 'Round 27（DLL 0.27.0）：G1（加法的 M_mod＝1＋Σ，K 類係數維持乘法）：終結＝EndNodeMult（加法）＋BurstCommonLines（共通線加總）＋雷斷；簽名與聖裁用 EndMove（同一個加法池）；BurstMult 只剩 K_sync；湧動的百分比部分只吃自己的線、濺射與血祭之始 ×0.5；聖裁的階級 T 是乘法；27b：連鎖終焉帶主終焉的加總（B N1：CarriedMod、Current）、開印的劑數與拉近不吃節點倍率（B N2）、放電每格與風刃加入加總（B N4：EndMove、Joined）'),
    'native/include/Registry.h': ('added', '5e09dea84e65804b1b9837f0f5688af46c12c931f15cfd565c3e8abd8e933973', 'Round 27（DLL 0.27.0）：引擎膠合（E1–E13）：新純標頭：我們自己效果的登記表（task 的讀取發布快照；移除 sink、死亡 sink、唯讀 native 讀它；0.35 秒到期寬容；移除時 EraseUid）；G9 的 SettledMarks（1 秒內被結算掉的印記，死亡時算帶著）；27b：Key＝FormID＋handle（A N2）、lk::Mutex、ExpiredMarkOf（B N9）；27d：SnapshotView 拒收暫存的 Snapshot'),
    'native/include/Runtime.h': ('added', '14f04bd5f824e87c9d855e6b18ae96c4e4f6f1e774af37a6050dd58e52ceadca', 'Round 27（DLL 0.27.0）：引擎膠合（E1–E13）：新純標頭：Scope／ResetScope（E9）、Session＋Ticket（E3：PreLoadGame／NewGame／主選單換 epoch）、HealthLedger＋HurtQueue＋AssignAfter（E4 幀序＋G7 自己的生命帳）、OpenLogWith＋Query（G12）、SehVerdict（E2）、GateFrom＋kInputMenus（E6）、EventText（E12）；T：DispelCollected、GuardOpen／GuardRun、PlanTick、ReadEngaged（Plugin.cpp 的規則移出來讓測試跑）；27b：SehVerdict 帶 locksHeld（A N4）、SehQuiet（N5）、WorldClock（N3）、OwnDelta（N10）、MenuEndsSession（N8）、NoteSneakHit（B N7）、lk::Mutex；27c（0.27.2）：rt::Context（每次複製都把 in.tuning 指回自己的 tuning；0.27.1 融斷與過期結算讀到已結束的區域變數，傷害 inf）；27d（0.27.3）：RingOf（形態光圈的效果編號）；27e：BranchBit／Gained、LethalDue'),
    'native/include/Selection.h': ('unchanged', '51574fa1fe6649c234dc774526898c876bae6bb7bce310d1958a092959bccf1e', ''),
    'native/include/SelfLayer.h': ('changed', 'd6166740740640f4beb4e2bd02ce987555f15735adea8b0c8b749ff1df00dac6', 'Round 27（DLL 0.27.0）：G11：風的多段觸發的重複永遠不算滿格重擊放電；27b：CorpseHitPlan（B N6）；27d（0.27.3）：WithAvatar 拒收暫存的節點讀取器（0.27.2 崩潰：AvatarNodes 保留參考）'),
    'native/include/Sinks.h': ('changed', 'aeedc700c117eeb21b6361bc7c9df31aaa44f6e1b4d49662bbc272263bff149e', 'Round 27（DLL 0.27.0）：G15：綁在元素熱鍵上的鍵只當熱鍵，不再同時當探針的步驟鍵'),
    'native/include/Status.h': ('changed', '22909b7d4c5fa636d4f741f1ae8eedf92a6b4c4080fb02b70f81905bf844a01a', 'Round 27（DLL 0.27.0）：G1（加法的 M_mod＝1＋Σ，K 類係數維持乘法）：EndNodeMult 改加法、SignaturePct；碎冰不再自帶結算；催化不疊乘（base×最大係數）；暗蝕熔斷；死咒結束＝損失×比例×易傷，擊殺旗標先設再扣；聖裁 III 只吃自己的線；G3：開印層數不乘 NodeScale；慈光用 PunishCap；G5：瘴氣速率不乘 NodeScale；G4：熔斷的無形態融合算一次洩熱（VentHeat）；StatusPlan 改 vector（kMaxStatusOps 8192，爆量記 log 不丟例外）；27b：PlanEndBody 帶 carried（B N1，暗蝕熔斷）、開印事件帶未乘倍率的層數（B N2）、催毒 ×2 整、線加入每劑的加總（B N5 CatalysedLine）、FireSourceBurns／FireSourceCosts（B N3）'),
    'native/include/StatusEngine.h': ('changed', 'f17b39c98cb04f27016620fd910abff99786f69629f9bc8b1e2ac786fa87a5b4', 'Round 27（DLL 0.27.0）：G6：RunOp 在引擎回報 IsCorpse 時不對屍體施放、驅散（事件、你身上的、其他人的照常）；27b：CorpseSends（A N7：屍體模式只送切掉的終焉事件）；27c：CheckOp／SaneValue——非有限、超過 ±1e7 或效力近 0 的操作整個丟掉'),
    'native/include/Timer.h': ('unchanged', '10a28e3c079b55042bacec4e787a8c8f6735fd3cb10326f747aefadfdee0c601', ''),
    'native/include/Trace.h': ('changed', 'aa66a035ed590e780ef44f83aa1757e3dc33ae59d4d13b6dd21990e6f04542c7', 'Round 27（DLL 0.27.0）：引擎膠合（E1–E13）：E12：Utf8Fit（名字與被切斷的行不留半個字）；E7：Buffer::TryTake（結束時不等鎖）；27b：Buffer 用 lk::Mutex（A N4）'),
    'native/include/TrueHud.h': ('changed', '42d2370e76b33e47e0683b6fbfdf6aa761837f15e42ef0e46c2d1e401d59e242', 'Round 27（DLL 0.27.0）：引擎膠合（E1–E13）：E13：每次載入要求的 generation，舊的回呼作廢；關閉時舊要求的回答也作廢'),
    'native/src/Plugin.cpp': ('changed', 'cac55181173a3ab13e802b3d8ad25522a8371384058a8f574720950a84e20f83', 'Round 27（DLL 0.27.0）：E1–E13、G6–G12（見 build/native-verification.md Round 27）：登記表與 OVERLAP-READ 見證；SehFilter；QueueTask 帶 epoch；受擊按幀與自己的生命帳；GateNow 不走 menuStack；EventText；ScanDomains 先收再做；null cell；ESL 拒載；計時先走時鐘、關閉或故障時移除 TrueHUD 條；OpenLog 不丟例外、Query 先填 info；主選單結束 session；屍體模式（G6）、連殺讀命中 sink 的潛行旗標、剛結算的印記（G9）、施法中與命中前生命在 sink 讀（G10）；形態切換由 DLL 在 task 裡做完（G8：SwitchWork、SwitchMarkers、CloseByMagicka、KeepSync）；T：DispelLive、Guard、TickCpp 的順序、BuildCrowd 的 engaged 讀取改用 Runtime.h；27b（DLL 0.27.1）：登記表的 handle 鍵、死亡第二事件與卸載 sink 的 Forget、世界時鐘、SEH 鎖深度與 stack overflow、遊戲就緒 task 的 sessionOnly、選單 sink 故障時仍結束 session、GetHandle 移到鎖外、自己的生命只記精確數值、屍體模式的事件過濾（A N2–N10）；火源條件（B N3）、屍體模式不花資源（B N6）、潛行紀錄（B N7）、過期終焉的剛結算印記（B N9）；27c（0.27.2）：Context 改用 Runtime.h 的版本；[ESSB][BADMAG]；27d（0.27.3）：RingWatch——除錯等級 ≥3 時光圈生效／失效各記一行 [ESSB][ring]；27d：SwitchWork 的節點讀取器改成具名變數（0.27.2 崩潰根因）、Executor 拒收暫存的 Tuning；27e（0.27.4）：NodeRank／NodeBranch／BranchesGained 原生函式（MCM 卡頓：技能樹階數不再靠 Papyrus 快取）、StatsMenu 開啟時記下分支、ESSB_Lethal 每秒最多一次'),
    'native/tests/anchor_test.cpp': ('added', '4027303dafdc548743ca93284e5240810d1c9b011812a20e6fcf4608781e547f', 'Round 27（DLL 0.27.0）：新測試（ctest anchors）：G1 的手算錨點（碎冰 962.5／465、聖裁 III 135／67.5、死咒 540／1020、血 650／195、霜終結 420、催化 65、G3 詛咒 7、G4 洩熱、843 個 op 的爆發不溢位）；27b：催毒錨點改 38（B N5）；Review27bAnchors：焚天 ≤ 主終焉、開印劑數不隨節點倍率、火源、屍體模式'),
    'native/tests/asan_harness.cpp': ('added', '36b48f01c684951ed1f141f893af3b5ecfd32419b41a49f770a047ebec14db00', 'Round 27（DLL 0.27.0）：27d：AddressSanitizer 用的不丟例外測試（Context 複製、具名節點檢視、24 目標融斷、登記表雙執行緒、受擊佇列）'),
    'native/tests/engine_test.cpp': ('changed', '141f80308691219341c9238bfd0f8ea3bd7189d1d24cda785f14fde5d7b49282', 'Round 27（DLL 0.27.0）：27c：inf／NaN／4e22／效力 0 的操作被丟掉'),
    'native/tests/hit_pipeline_test.cpp': ('unchanged', 'a6acfdd1ec3b77e8b2e9baddceb7190f9551c1e5366252c8852200a65846b357', ''),
    'native/tests/lifetime_net.cpp': ('added', '808644c9fa785f0150d83278bdd05fe024044eed01c4010663e41ec990978a21', 'Round 27（DLL 0.27.0）：27d：生命週期網的負向對照（字串檢視綁在暫存物件上，clang-cl 必須報錯）'),
    'native/tests/load_test.cpp': ('unchanged', 'c1b5e69dc7e47d968f3afb2798bbbba4964bb7437d60e21c31598bdf8070148d', ''),
    'native/tests/reaction_test.cpp': ('unchanged', 'a3191318c65dbb3d42918d053bfb5903966bbc2ac1fd06b29a378a0269cc245b', ''),
    'native/tests/runtime_test.cpp': ('added', '7b8af02802cb8a8cce59b1948ebc4e83cfe59189e7038a4c0cff4f729ea4d4e7', 'Round 27（DLL 0.27.0）：新測試：task scope、session 與新遊戲、log 與 Query、SEH 判定、輸入閘門、事件文字與 UTF-8、登記表（兩條執行緒）、受擊佇列與自己的生命帳、屍體模式、剛結算的印記；T：驅散重找、原生守衛、計時順序、人群讀取；27b：Review27bChecks（A N2–N10、B N7、B N9）；27c：ContextChecks（回傳的複本讀自己的 tuning）；27d：RingChecks；27e：BranchChecks、LethalChecks'),
    'native/tests/self_test.cpp': ('changed', '61e8918e824b4241a13165424d8009dbba65041a12cc24dff8cc11d7e1326669', 'Round 27（DLL 0.27.0）：27d：static_assert WithAvatar 不收暫存物件'),
    'native/tests/status_test.cpp': ('unchanged', '83a54b98c94d99f479c7bab60e24953dab0e86f6bbc942d3b3c29cb43b41879e', ''),
    'native/tests/timer_test.cpp': ('unchanged', 'ee17004ce2db03a452dd035f311b22ec64d2e8e0fdbd07f311be9b6af758b96f', ''),
    'native/tests/trace_test.cpp': ('changed', 'fd33f5e75bef1b2e90d6e93b440f4ff384a46e33325371fb111f5918498e9ee2', 'Round 27（DLL 0.27.0）：G15：綁在熱鍵上的步驟鍵只切換形態'),
    'native/CMakeLists.txt': ('changed', '7f5ec76988a2c7173aa392775d57c7c1ea62e9c34028304d6cdec385655ff506', 'Round 27（DLL 0.27.0）：版本 0.27.0；runtime_test（ctest runtime）、anchor_test（ctest anchors）；C4717 當錯誤；27b：版本 0.27.1；27c：版本 0.27.2；27d：版本 0.27.3；27d：Release 加 /Zi、/DEBUG:FULL /OPT:REF /OPT:ICF；27e：版本 0.27.4；27f：版本 0.27.5'),
    'native/build.py': ('changed', 'e40dac20aa6bd77e17402b6267b35c2c80954b93bb31ba3f9526c0babc325e17', 'Round 27（DLL 0.27.0）：runtime 與 anchors 測試的突變（E1、E2、E3、E4、G1、G3、G4、G6、G7、G9、G12、爆發溢位）、G15 的步驟鍵突變；舊突變的原文跟著新寫法（對死者施放、濺射的 SurgeOn）；T 的 4 個突變（Runtime.h）；27b：A-N2／N3／N4／N7／N10、B-N1／N2／N3／N5／N6／N7／N9 突變；E2 突變原文跟著 locksHeld；27c：Context 與 SaneValue 的突變；27d：生命週期網（clang-cl -Werror=dangling* 檢查 Plugin.cpp 與所有測試、負向對照 lifetime_net.cpp 必須被抓到、asan_harness 在 AddressSanitizer 下跑）；27d：DLL 一律產生 PDB，GUID／age 對上 DLL 才複製到 build/pdb/（不出貨）'),
    'build_core.py': ('unchanged', 'c5468602b5a3d6889b6175bad7e5e1d5ef9321cf48638f6b905ea80b05195ce0', ''),
    'build_melee.py': ('unchanged', '08e8cf2c7c1d386efc6a52d2d31302ba150b8b423b2cbffee1a6d534525c9d4a', ''),
    'build_scripts.py': ('unchanged', '98e6d30c728bd98055c9cc98738e84b3a402979c02e65eb7b5ad9fd7ccd5d434', ''),
    'build_v03.py': ('changed', '1f38e5e9575cd3a344b007f6119e458e3b7cb76edd8039fa844f2a7c6fe0ddd3', 'Round 27（DLL 0.27.0）：G13：武器光改 Enhance Weapon＋ENCH、武器光的條件改讀自己的 ESSB_SyncStage＋ESSB_WeaponGlow、印記效果拿掉命中特效與音效（開印改由閃現法術放）、MCM 武器光開關；G14：DLL 施放的法術加 No Absorb/Reflect（標記加 Ignore Resistance）；G15：冷卻滑桿 0.25～3.0；全域變數 56 個；開印閃現是接觸施放；27b：形態能力改掛四個光圈、MCM「形態光圈」、送給別人的法術加 No Absorb；27e：perk 名稱與描述去掉規劃文件的註記（build/fix27_text.py）、退役節點描述不再寫版本號、除錯等級說明不寫檔名'),
    'fx_extract.py': ('unchanged', '4ae15444ac287131499f2a076c9611b11d40762e2cbae53cd290e0ef2927d9c5', ''),
    'inspect_magic.py': ('unchanged', '2a7ec48b000b6647d0e625ff24901e591df9b3bba7f3d9fbeb00c3a46d746fab', ''),
    'plan_coverage.py': ('unchanged', 'ce47f5d229a94dcb1b2c2c1ac4452cbd24da40a6b7cdc606ca729677b7af57dc', ''),
    'plan_trees.py': ('unchanged', '6a921d3278dff9b1ebc81b1dcb58b063e677c58509e176a49a00de73d0af4123', ''),
    'render_plan.py': ('unchanged', '266e1f87c3946bf91c927a8a8673c8fb518f67c25d104967f3e56c53a7b7db23', ''),
    'setup_compiler.py': ('unchanged', '84cc8e0f6bf094c53ad281ab53c40a90718c8e654d3634cd2c787cb4f6763c36', ''),
    'tes.py': ('unchanged', '0cec676788f1993014781215cdfde38c8a5b6363a0e5ab92fe876e2455610c74', ''),
    'tree_v04.py': ('unchanged', '943483ba2a763b7de9ef13847fd4465fa6d472432a77dda5b9938e9661d9d18a', ''),
    'build/fix19_native.py': ('changed', '603eaa7f29b44b29feb256169956b3b5600628831b6d88452bf8f1b82fbdb6ea', 'Round 27（DLL 0.27.0）：NATIVE_VERSION 0.27.0；G8：manifest 的 spells 加 kEchoPendingSpell、kTwinWindowSpell，header 加 kTwinWindowRecordSeconds，ROUND27_NODES（雙生）；27b：NATIVE_VERSION 0.27.1；27c：NATIVE_VERSION 0.27.2；27d：NATIVE_VERSION 0.27.3、光圈效果編號、ESSB_WeaponGlow 進 manifest globals；27e：NATIVE_VERSION 0.27.4；27f：NATIVE_VERSION 0.27.5'),
    'build/fix21_records.py': ('unchanged', 'ce5a656d0377bace72736048358cf8c74c79f997448d027a60be934ad8b1fd1f', ''),
    'build/fix22_records.py': ('changed', '46c80a755b422f5c6a001a553f0a33d7435666b6cefd9e2f469285380ce952ff', 'Round 27（DLL 0.27.0）：G13：狀態的著色（凍結、冰晶閃、血痕、催毒、浸濕、水壓、詛咒、星痕、死咒閃），取自規劃 2.11 點名的紀錄；27f：白熱／熔燒／熔身的全身火焰改用原版火焰斗篷（著色＋火焰 art）；催毒著色改 Venomancy 毒霧（Rotflesh 的貼圖路徑在原模組就壞了）'),
    'build/fix22_reference.py': ('changed', '489c8a42394a6ae4a76e948fa3f01b6a926fbc5e13d29d6bbaacc28bbf52f561', 'Round 27（DLL 0.27.0）：G1（加法的 M_mod＝1＋Σ，K 類係數維持乘法）：Python 參考模型跟著 Status.h：加法終結、碎冰、催化、暗蝕、死咒、聖裁 T、開印層數、慈光、瘴氣、洩熱；27b：參考模型跟著 C++（B N1 carried、B N2 開印事件的層數、B N5 催毒）'),
    'build/fix22_fixture.py': ('changed', '3d1135338c9750c995f9cd659850d798bd7a24cfa769671accf9b58649eebbe8', 'Round 27（DLL 0.27.0）：G5：瘴氣錨點改 1.5（不乘 NodeScale）'),
    'build/fix23_records.py': ('unchanged', '3a0f7d2f1820798f3333dbd087041363f5b9ce235ae998bf80ffe877aa530dce', ''),
    'build/fix23_reference.py': ('changed', '4e1c96e76ad489d270434d14157322caab067be1e95ca2c8bad5d0856a260406', 'Round 27（DLL 0.27.0）：G7：參考模型的護血跟著護血池走；27b：end_body 帶 carried（B N1）'),
    'build/fix23_fixture.py': ('unchanged', 'e0a52a875b1872b8ac1b7fc1e6fe40de355775154ed8959fb90b25424bf49156', ''),
    'build/fix24_records.py': ('unchanged', '0116b08561c4a8575c2be56c8dcb174a0d46bf0b5c4b8273ca30dce7bed004e6', ''),
    'build/fix24_reference.py': ('changed', 'b3232baa88ce835ba7208669c7a65fb41f91beed59eb542f60da752dfefae603', 'Round 27（DLL 0.27.0）：G1（加法的 M_mod＝1＋Σ，K 類係數維持乘法）：參考模型跟著 Reactions.h：簽名加法、BurstLines、終結本體、BurstMult 只剩 K、湧動 pct_scale、聖裁；錨點：霜終結 17.43、爆發 31.248；27b：參考模型跟著 C++（B N1 連鎖帶加總、B N2、B N4）'),
    'build/fix24_fixture.py': ('unchanged', '67b0a52a95d46963bb9077c6129ec1dd7a95b1b07cddf6faba0e273bbb79c1bc', ''),
    'build/fix25_records.py': ('changed', '9af0c04fc04cf5522877d8d50d061820701b08709b543d78ee6fa04e07b4f07b', 'Round 27（DLL 0.27.0）：G13：火、冰、聖、星的領域用原版危險區模型（看得見範圍），其他維持空模型；27b：火領域換 FXFireOilHazard（較大）'),
    'build/fix25_reference.py': ('unchanged', '3a338ec86f0bdbec952d4156f4fb63ccbff38ac1e79f467e16043778ba0f1c04', ''),
    'build/fix25_fixture.py': ('unchanged', '5a6856c16b38e6a07b363b7f4449415ea8fc2772bd37a1f43d3546e0b72b8835', ''),
    'build/fix26_records.py': ('unchanged', '8c8fa641dc766e4fb01471fc2b27b911d19e20325444c0c50c83fce9e1b0a54f', ''),
    'build/fix26_format.py': ('changed', 'e075ff9be06529cd87c4d6b34e9164f3c9e3b83e737ed0f4bd255e5fa13fc7e7', 'Round 27（DLL 0.27.0）：G6：hit-late 行可帶 mode=corpse'),
    'build/probe-judge.py': ('changed', 'b5a6a20be566373160c093324d79307a05e4600d41a95ace7f64bcd9c617f404', 'Round 27（DLL 0.27.0）：SETUP-1 判 0.27.0（VERSION 常數）；[ESSB][OVERLAP-READ]（E1）與 [ESSB][crash]（E2）出現＝FAIL；27b：VERSION 0.27.1；27c：VERSION 0.27.2、BADMAG＝FAIL、SETUP-1 的 X1 改要 input task（G8 之後站 1 不再排 queued native task）；27d：VERSION 0.27.3；27e：VERSION 0.27.4；27f：VERSION 0.27.5'),
    'build/fix27_visuals.py': ('added', 'b19f77afac07a95c8edaf27c2391e2a29b1d8aaad3d6a9252f77eae66eacfdbe', 'Round 27（DLL 0.27.0）：G13：視覺提示的盤點與建置檢查（新檔）；27b：光圈檢查、送給別人的法術檢查、INVENTORY 依審查 C 重寫；27d：光圈的 ARTO／模型檢查、不准再用 *CastBodyFX；INVENTORY 更新；27f：INVENTORY 的全身火焰一列'),
    'build/fix27_records.py': ('added', 'f669d43ffd0968db3949b2300dc076bcd0e15c3e23fe57429c949e508295aef3', 'Round 27（DLL 0.27.0）：G13、G14 的新紀錄（新檔）：ESSB_WeaponGlow、武器光 ENCH 與它的效果、開印閃現；DLL 法術的 SPIT 旗標；27b：形態光圈 ESSB_FormRingEffect_<X>_0..3、切換號碼牌的兩個全域變數、送給別人的法術都加 No Absorb、ENCH 退役；27d：光圈改用我們自己的 ARTO（ESSB_FormRingArt_<X>，原版地面符文與恢復圈模型；0.27.1 的施法光圈看不到）'),
    'build/fix6_verify.py': ('changed', 'e5d86944735be881ee61e3c76940b2efa6e347eaead0f5b515f4eea17d98cfe8', 'Round 27（DLL 0.27.0）：27e：perk 描述比對改用玩家文字（build/fix27_text.py，去掉規劃文件註記）'),
    'build/fix11_verify.py': ('unchanged', '5fb7e48ad43e7ec8d6c6315b435aa936ae969e0d70213d37666e8b1b38ba128b', ''),
    'build/fix16_verify.py': ('unchanged', '2bec8fb1527226b91936f4f3140fec08d33ec88fb89cb84da1d5eebda3f5b26d', ''),
    'build/fix21_verify.py': ('unchanged', '84f2650ff08009991e5d4a6541ec22f1249459e8bc212d78e40db737d3af7de0', ''),
    'build/fix22_verify.py': ('changed', '770004287e4921eab32e528233b925493dffff28678f8b01751f17091593e770', 'Round 27（DLL 0.27.0）：T：Guard 的 try／catch 搬進 Runtime.h GuardRun，檢查跟著讀它'),
    'build/fix23_verify.py': ('unchanged', '531575bf68910efcb5a0e1b6472d9b36f20b13ab7fba684ac944f6fbff9e5e88', ''),
    'build/fix24_verify.py': ('changed', 'f8e39ac9cda5443445cebe68d9f4e0ad30bacc95aec3d0e0f68f81b82d5d1c4c', 'Round 27（DLL 0.27.0）：檢查跟著新寫法：task 經 QueueTask（帶 session 票的 AddTask）、死亡 sink 用 ReadMemberFrom、OnFormClosed 多了參數'),
    'build/fix25_verify.py': ('changed', '8e4dc1c20ebe9967fcfae4210214a7e065637d80a61a23fd71d913fd76720bd5', 'Round 27（DLL 0.27.0）：檢查跟著新寫法：切換在 SwitchWork 送 ESSB_Switch（G8）、計時 task 經 QueueTask、GameStopped 讀 session；G13：火冰聖星領域的危險區模型；計時 task 的順序改由 PlanTick（tick.second）'),
    'build/fix26_verify.py': ('changed', 'bd8010f29a0313833d0160414a80638c325653a5fa74ffd8195924dd38cccdf0', 'Round 27（DLL 0.27.0）：檢查跟著新寫法：sink 經 QueueTask、重疊計數在 Runtime.h Scope、配接器的 Dispel 多了屍體與剛結算的記錄；版本改成「一個值、不早於 0.26.3」（0.27.0 由 fix27_verify 釘住）；27c：SETUP-1 樣本的 X1 用 input task'),
    'build/fix21_identity.py': ('changed', 'f454401d9f5435de1b128586fe03e33b48913fb44bb284717072b1b2621a19eb', 'Round 27（DLL 0.27.0）：27e：允許 NodeRank／NodeBranch／分支遮罩依座標讀（座標來自 ESSBNodes 依名稱的讀取）'),
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
    'build/fix27_verify.py': ('added', 'c3deaf584e5dcf423a792ffa0020da6d8020a1c300da791ae23b772c16212bdd', 'Round 27（DLL 0.27.0）：round 27 的驗證器（新檔）；27b：光圈的注入錯誤、版本 0.27.1、A-N2／B-N1／B-N2 突變必須存在；27c：版本 0.27.2、BADMAG 樣本、Context 與 BADMAG 的原始碼檢查；27d：版本 0.27.3；27d：包裡的 DLL 與 build/pdb 的 PDB 對得上、package/ 沒有 PDB；27e：版本 0.27.4、玩家文字不得含規劃文件的註記（perk 名稱／描述、CSF、MCM）；27f：版本 0.27.5；ASSETS：我們自己的視覺紀錄與身上的火要在原版封存檔裡、活效果用的複本要在已安裝的模組裡（兩個注入錯誤）'),
    'build/fix27_reasons.py': ('added', '73eee204baf2c2d376f847e8c7ac0c5b3316fdeb384de6a720b8b473b072f0a6', 'Round 27（DLL 0.27.0）：這份理由表（新檔）'),
    'build/fix27_history.py': ('added', 'e41ec9dbdba72171517c97a3252cb4923200b52487672dd6317e3c3664ee3741', 'Round 27（DLL 0.27.0）：round 27 的 Papyrus 封印（產生的）'),
    'build/fix27_history_gen.py': ('added', 'dd596d6ab921df7ded9297b4dcef1c85434016ca95a8748ad8026a19db146e32', 'Round 27（DLL 0.27.0）：round 27 Papyrus 封印產生器（新檔）'),
    'build/fix27_history_template.py': ('added', '5fb43fe48c7475afcefe07734cb88ff0332eac7ab1ef51c7c9ffa1c923a7ab80', 'Round 27（DLL 0.27.0）：round 27 Papyrus 封印樣板（新檔）'),
    'build/fix27_native_history_gen.py': ('added', '3be5095f1daab291caa6cd7fa89ced99de8db3eaa0f7f6586d5fe7228f74d4fd', 'Round 27（DLL 0.27.0）：round 27 原生封印產生器（新檔）'),
    'build/fix27_native_history_template.py': ('added', 'f234de9d7e8e9bff1dfea345cafef2c8f812a8de7180b934dd88d8158e824aa4', 'Round 27（DLL 0.27.0）：round 27 原生封印樣板（新檔）'),
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

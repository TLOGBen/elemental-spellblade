"""Round 26 seal of the DLL sources, the native tests, the generator modules, the verifiers and the probe judge. GENERATED
by build/fix26_native_history_gen.py from this template -- write reasons there, never edit the digests here.

FILES  path -> (state, sha256 now, why): 'unchanged' files equal the pre-fix26 snapshot (.codex/pre-fix26-snapshot, taken
       before any round-26 edit); 'changed' / 'added' ones carry the declared reason. verify() fails on any byte that
       differs, on a covered file that is missing and on a file in native/include, native/src or native/tests that is not
       listed. build/fix25_native_history.py checks the snapshot (round 25 as shipped) only after this proof.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / '.codex/pre-fix26-snapshot'

FILES = {
    'native/include/EngineFacts.h': ('unchanged', 'd87e73a6b435df0e4b63e29d3f59f9e77f8543dfe251530e55a3804add18ebe4', ''),
    'native/include/HitMath.h': ('unchanged', 'e5bbc95f57d37a68a1cd21194bf3a2e663cc7a5794ff9d3dc7ff36189bc1e469', ''),
    'native/include/HitPipeline.h': ('unchanged', '24d441cb6742fc20e2fae6e21a2bf8d56e90d9f7a0c84bc9bc3545ee89e9bc09', ''),
    'native/include/Hurt.h': ('unchanged', '5134900a241e8b9838df3fee3a90722e8e6839168493dedd36592fee9f742138', ''),
    'native/include/Load.h': ('changed', '88d1bf95729dc56ce0b55f2a84632c71bc2a978f7602fb826063537677145c3d', 'Round 26（探針 log）：解析 ESSB_ProbeStep（站標記）；Round 26c（堆積損壞修正，0.26.2）：解析 ESSB_TrueHudBars'),
    'native/include/ManifestData.h': ('changed', '7a0a385bd4e34d1e3f8ff3c76a1e8d8d834c48934c1e587f9c6bb2b523250303', '由 build/fix19_native.py 產生：版本 0.26.0、kProbeStep；Round 26b（指揮官的執行緒裁定，0.26.1）：版本 0.26.1；Round 26c（堆積損壞修正，0.26.2）：版本 0.26.2、kTrueHudBars'),
    'native/include/NodeIds.h': ('unchanged', 'fd843a2bded8e5bf423c87801bbbfe071a5189f8d5e05c15d0dee605ef8fe5f3', ''),
    'native/include/Reactions.h': ('unchanged', '7f7a610d4b19a1c5e04b888a0a8d8d2e27e0ac7efdf493a3e76851ccb426803c', ''),
    'native/include/Selection.h': ('unchanged', '51574fa1fe6649c234dc774526898c876bae6bb7bce310d1958a092959bccf1e', ''),
    'native/include/SelfLayer.h': ('unchanged', '8bf4e37a7c9c64af40d8e97af675376f5bd5d3254efdb64db9efa27c7263dbd8', ''),
    'native/include/Sinks.h': ('added', '32df9072893390ef26c0b8d6d85135786f9cc8daed67cea1f7ac2ec8d1f6fd94', 'Round 26b：死亡 sink 只讀屍體（DeathSink：兇手與你只比對身分）、輸入 sink 的按鍵對應（PlanInput，純函式；切換與站標記在 task）（新檔）；Round 26c（堆積損壞修正，0.26.2）：RouteHit（巢狀命中丟掉）'),
    'native/include/Status.h': ('unchanged', '330450987b1aaebd5bafbda514fb00ba815e0044b59623a809c66332ea426464', ''),
    'native/include/StatusEngine.h': ('changed', '2c779e1714c879a45b285330231d8b9da8927badb0cbc7cf857cb49453fb2b51', 'Round 26（探針 log）：RunOp 在引擎有 Tracing() 時呼叫 TraceOp／TraceDone（ChangesValue 決定哪些 op 補一行 op-done）；SelectCrowdWhy 回報每個演員的判定（SelectCrowd 改成它的無回報版，選人不變）；DescribeRemoved（任何我們的效果離開的理由）；Round 26c（堆積損壞修正，0.26.2）：DispelWhere 依身分重找後才驅散'),
    'native/include/Timer.h': ('unchanged', '10a28e3c079b55042bacec4e787a8c8f6735fd3cb10326f747aefadfdee0c601', ''),
    'native/include/Trace.h': ('added', '8baea0b1a2c9346d9e9f61ae187f24b4a3840260cd5f0ce075c56cf7321babbc', 'Round 26（探針 log）：探針 log 的純標頭（新檔）：行格式 [ESSB][T][種類] #序號 g= r=、Line（480 位元組截斷記號 ~）、Buffer（序號在鎖內給、每秒由計時執行緒寫檔）、TraceRng（跟 SplitMix64 同一串擲骰，另記錄）、各種行的產生函式（op、op-done、proc、hit-end、remove、hurt、second、env、switch、key）、名稱表、數字鍵區 +／- 的代碼；Round 26b（指揮官的執行緒裁定，0.26.1）：kChainKeys（X2 的呼叫鏈鍵）；Round 26c（堆積損壞修正，0.26.2）：TraceRng::Note 就地檢查範圍'),
    'native/include/TrueHud.h': ('changed', 'ed52d7b18300445f13adf6e019b2081ad00c94812d1f6c3d581f9e2d838afc09', '；Round 26c（堆積損壞修正，0.26.2）：TrueHUD 的所有呼叫改走 AddUITask、Link 只在 task 改、ESSB_TrueHudBars 開關、生命週期 log、PoolBar 拿掉 SEH'),
    'native/src/Plugin.cpp': ('changed', '16492c675dd790da7d8b3636d9f319db0a47054c77fefbad47d44144d0a3e7d8', 'Round 26（探針 log）：除錯等級 4 的探針 log（各 sink／task／原生函式的行、ctx 標籤、actor 的生命魔力耐力、TraceRng、每秒寫檔與故障／讀檔／存檔／卸載時寫檔、全域變數與節點的監看、站標記鍵與 ESSB_ProbeStep、ESSBNative.Trace）；Probe::kHurtTask（受擊 task 不再跟命中 sink 共用 kHurt，X1 兩行都會寫）；X1 改為每個 sink／task 的每條新執行緒一行，對照輸入 sink（主迴圈）、最近一次 SKSE task、遊戲視窗與 kDataLoaded（InitTESThread）的執行緒；玩法不變；Round 26b（指揮官的執行緒裁定，0.26.1）：死亡 sink 只讀屍體、兇手與你的讀取（狂宴、N5-1、death-event 行、距離）搬進死亡 task；輸入 sink 只讀按鍵與輸入閘門快照，RequestSwitch 與站標記改由 AddTask 執行；X2 見證（每條呼叫鏈的回傳位址、Havok TLS 字）；L3 的擊殺／推力／跌倒／hazard 行；版本 0.26.1；Round 26c（堆積損壞修正，0.26.2）：命中 sink 只記快照再 AddTask（命中 task 做全部引擎工作）；受擊 sink 不讀效果清單（池子 atomic 鏡射）；DispelLive 依 id 重找；TaskScope 與 [ESSB][OVERLAP]；Rng() 只在 task；thread_local 的 selfDispel／traceCtx／inHitTask；通知加鎖；讀檔重設改 task；EssentialOf 的鎖 __finally；TimerStopper；TrueHUD 開關與生命週期 log'),
    'native/tests/engine_test.cpp': ('unchanged', 'dc87215b5bb9729b76222c4c6a45e927057d4f3a5bcd187169ae71301584d49a', ''),
    'native/tests/hit_pipeline_test.cpp': ('unchanged', 'a6acfdd1ec3b77e8b2e9baddceb7190f9551c1e5366252c8852200a65846b357', ''),
    'native/tests/load_test.cpp': ('unchanged', 'c1b5e69dc7e47d968f3afb2798bbbba4964bb7437d60e21c31598bdf8070148d', ''),
    'native/tests/reaction_test.cpp': ('unchanged', 'a3191318c65dbb3d42918d053bfb5903966bbc2ac1fd06b29a378a0269cc245b', ''),
    'native/tests/self_test.cpp': ('unchanged', 'c054b7cad605707de057098cb7ca916254dd34f79b05094e4a41bcd88cd9d732', ''),
    'native/tests/status_test.cpp': ('unchanged', '83a54b98c94d99f479c7bab60e24953dab0e86f6bbc942d3b3c29cb43b41879e', ''),
    'native/tests/timer_test.cpp': ('unchanged', 'ee17004ce2db03a452dd035f311b22ec64d2e8e0fdbd07f311be9b6af758b96f', ''),
    'native/tests/trace_test.cpp': ('added', 'e9112f9c3a44f06cf25ccca8bba9dfb8b8533c824cabffd5cdc1b10140bb290c', 'Round 26（探針 log）：探針 log 的測試（新檔）：格式（build/fix26-trace-format.json 的 regex）、Buffer、TraceRng 不改擲骰、假世界上 RunPlan 的 op／op-done、DescribeRemoved、SelectCrowdWhy；並用真規劃器寫出 build/fix26-trace-sample.log；Round 26b（指揮官的執行緒裁定，0.26.1）：假世界：死亡 sink 只讀屍體、輸入 sink 的 PlanInput（被擋的熱鍵不執行、站標記要等級 4）；Round 26c（堆積損壞修正，0.26.2）：tape 邊界壓力測試、依 id 重找的驅散、RouteHit'),
    'native/CMakeLists.txt': ('changed', '94e6b44527ac84f9d9ca881df5894b6760cab6f2c424c54a01bdf69a93773bf5', 'Round 26（探針 log）：trace_test；版本 0.26.0；Round 26b（指揮官的執行緒裁定，0.26.1）：版本 0.26.1；Round 26c（堆積損壞修正，0.26.2）：版本 0.26.2'),
    'native/build.py': ('changed', '29f2323db6c8dc1e52d4b9a4727cd5a4506544ef0a5a7265fba69924e6f0d758', 'Round 26（探針 log）：寫出 build/fix26-trace-format.json；4 個探針 log 突變（錄骰改擲骰、截斷記號、op-done 多寫、掃描判定標錯）；Round 26b（指揮官的執行緒裁定，0.26.1）：2 個 Sinks.h 突變（死亡 sink 讀兇手、被擋的熱鍵照樣執行）；Round 26c（堆積損壞修正，0.26.2）：3 個突變；突變程式沒有輸出（直接崩）時也記為失敗'),
    'build_core.py': ('unchanged', 'c5468602b5a3d6889b6175bad7e5e1d5ef9321cf48638f6b905ea80b05195ce0', ''),
    'build_melee.py': ('unchanged', '08e8cf2c7c1d386efc6a52d2d31302ba150b8b423b2cbffee1a6d534525c9d4a', ''),
    'build_scripts.py': ('unchanged', '98e6d30c728bd98055c9cc98738e84b3a402979c02e65eb7b5ad9fd7ccd5d434', ''),
    'build_v03.py': ('changed', 'ea96b398dbd8b2b03f72671fd4cf3f770decd41a4ae81952316bce8b43446ac7', 'Round 26（探針 log）：ESSB_ProbeStep 記錄（fix26_records）、MCM 除錯等級加「4：探針 log」與說明、呼叫 build/fix26_verify.py；Round 26c（堆積損壞修正，0.26.2）：MCM「TrueHUD 資源條」開關（全域數 55）'),
    'fx_extract.py': ('unchanged', '4ae15444ac287131499f2a076c9611b11d40762e2cbae53cd290e0ef2927d9c5', ''),
    'inspect_magic.py': ('unchanged', '2a7ec48b000b6647d0e625ff24901e591df9b3bba7f3d9fbeb00c3a46d746fab', ''),
    'plan_coverage.py': ('unchanged', 'ce47f5d229a94dcb1b2c2c1ac4452cbd24da40a6b7cdc606ca729677b7af57dc', ''),
    'plan_trees.py': ('unchanged', '6a921d3278dff9b1ebc81b1dcb58b063e677c58509e176a49a00de73d0af4123', ''),
    'render_plan.py': ('unchanged', '266e1f87c3946bf91c927a8a8673c8fb518f67c25d104967f3e56c53a7b7db23', ''),
    'setup_compiler.py': ('unchanged', '84cc8e0f6bf094c53ad281ab53c40a90718c8e654d3634cd2c787cb4f6763c36', ''),
    'tes.py': ('unchanged', '0cec676788f1993014781215cdfde38c8a5b6363a0e5ab92fe876e2455610c74', ''),
    'tree_v04.py': ('unchanged', '943483ba2a763b7de9ef13847fd4465fa6d472432a77dda5b9938e9661d9d18a', ''),
    'build/fix19_native.py': ('changed', 'ff78dfb18fc816f53e693ec500b903ee5e1dd7639203a7afcb2b32e9e9c65a36', 'Round 26（探針 log）：NATIVE_VERSION 0.26.0；manifest 的 globals 加 ESSB_ProbeStep；NEW_EDIDS 含 round 26；Round 26b（指揮官的執行緒裁定，0.26.1）：NATIVE_VERSION 0.26.1；Round 26c（堆積損壞修正，0.26.2）：NATIVE_VERSION 0.26.2、manifest 的 ESSB_TrueHudBars'),
    'build/fix21_records.py': ('unchanged', 'ce5a656d0377bace72736048358cf8c74c79f997448d027a60be934ad8b1fd1f', ''),
    'build/fix22_records.py': ('unchanged', 'ccb1c66da897f297e2a9d3062c7086f6ca6c690447f6125d3d2e5fa8141dfa08', ''),
    'build/fix22_reference.py': ('unchanged', '8971bd504c97316243777ea6254832d4f8c8c3a737ca6d21e5c49f66015424e4', ''),
    'build/fix22_fixture.py': ('unchanged', '394e99082502b57fe7a1a9e09476217f5eb3653a5a0ad8377eb268de51434da7', ''),
    'build/fix23_records.py': ('unchanged', '3a0f7d2f1820798f3333dbd087041363f5b9ce235ae998bf80ffe877aa530dce', ''),
    'build/fix23_reference.py': ('unchanged', 'bd233f160951f5f89e2f32147f0473845679702627c194816bac739bd9d2ddda', ''),
    'build/fix23_fixture.py': ('unchanged', 'e0a52a875b1872b8ac1b7fc1e6fe40de355775154ed8959fb90b25424bf49156', ''),
    'build/fix24_records.py': ('unchanged', '0116b08561c4a8575c2be56c8dcb174a0d46bf0b5c4b8273ca30dce7bed004e6', ''),
    'build/fix24_reference.py': ('unchanged', 'd26b1128d410b884f8e2cd99f7007900de690965f90ec2a88bd85040bc36bdad', ''),
    'build/fix24_fixture.py': ('unchanged', '67b0a52a95d46963bb9077c6129ec1dd7a95b1b07cddf6faba0e273bbb79c1bc', ''),
    'build/fix25_records.py': ('unchanged', 'f3e2af2996a82effcad146d9b84308c9d8c35aa7bcb5fd47de058897cf77e0df', ''),
    'build/fix25_reference.py': ('unchanged', '3a338ec86f0bdbec952d4156f4fb63ccbff38ac1e79f467e16043778ba0f1c04', ''),
    'build/fix25_fixture.py': ('unchanged', '5a6856c16b38e6a07b363b7f4449415ea8fc2772bd37a1f43d3546e0b72b8835', ''),
    'build/fix26_records.py': ('added', '8c8fa641dc766e4fb01471fc2b27b911d19e20325444c0c50c83fce9e1b0a54f', 'Round 26（探針 log）：round 26 記錄表（新檔）：ESSB_ProbeStep 0x005C00；Round 26c（堆積損壞修正，0.26.2）：ESSB_TrueHudBars 0x005C01（預設 1）'),
    'build/fix26_format.py': ('added', '2acc6a56c8c7df6196e15ad92d4d9aa6a5f62cfe1461fc874b2a44067f65ca23', 'Round 26（探針 log）：探針 log 每種行的 regex（新檔），trace_test 與 probe-judge 共用；Round 26c（堆積損壞修正，0.26.2）：hit-late 行'),
    'build/probe-judge.py': ('added', 'bc6a1732faf92336f00bdb5c72206692783f218fd8641f6cc7ee9da862be1a79', 'Round 26（探針 log）：依 build/probes-all.md 的 91 站判定 102 步的判定器（新檔）；Round 26b（指揮官的執行緒裁定，0.26.1）：SETUP-1 讀 X2：遊戲中命中 sink 與 task 在 Post process、輸入／UI／VM 在各自的 job、暫停時在視窗執行緒；Round 26c（堆積損壞修正，0.26.2）：SETUP-1：OVERLAP／RNG 出現即 FAIL、命中 task 要在 Post process、命中 sink 只記錄'),
    'build/fix6_verify.py': ('unchanged', '08a86662a4fc6e4dbbeac3a71f81875c411a14dfd8b946bf8fe89940857c20a7', ''),
    'build/fix11_verify.py': ('unchanged', '5fb7e48ad43e7ec8d6c6315b435aa936ae969e0d70213d37666e8b1b38ba128b', ''),
    'build/fix16_verify.py': ('unchanged', '2bec8fb1527226b91936f4f3140fec08d33ec88fb89cb84da1d5eebda3f5b26d', ''),
    'build/fix21_verify.py': ('unchanged', '84f2650ff08009991e5d4a6541ec22f1249459e8bc212d78e40db737d3af7de0', ''),
    'build/fix22_verify.py': ('unchanged', '1beec2474652e7d93a4eea578326c2ec7cc9dedccdec82149cfe34971bb8689e', ''),
    'build/fix23_verify.py': ('unchanged', '531575bf68910efcb5a0e1b6472d9b36f20b13ab7fba684ac944f6fbff9e5e88', ''),
    'build/fix24_verify.py': ('changed', 'cade2b66e272b809aa7eae91f72ee7d25040eb492069489cfc1c59be67341280', 'Round 26b（指揮官的執行緒裁定）：死亡 sink 的四條規則（只處理 dead = false、不處理你的死亡、經 DeathCounts、在 sink 讀屍體再交 task）改到 native/include/Sinks.h DeathSink 與 CorpseWorld 裡檢查（同樣的規則，加一條只規劃 DeathCounts 接受的）；對應的注入錯誤改在 Sinks.h 上做'),
    'build/fix25_verify.py': ('unchanged', '7ac9a6affbe2b4f8da538d482a57f784427f47940ffb48b107bad82c71e1239f', ''),
    'build/fix26_verify.py': ('added', 'b9b756f1a76430f3c4681cb1fc1e708030124678d816e8002df9820c0a4a9acb', 'Round 26（探針 log）：round 26 的驗證器（新檔）：判定器涵蓋、卷與判定器一致、原生樣本與手寫樣本的 PASS／FAIL、原始碼的探針檢查、記錄、突變、封印、行尾；Round 26b（指揮官的執行緒裁定，0.26.1）：0.26.1、sink 的靜態檢查、X2 鍵與判定器一致、X2 的兩個錯誤樣本；Round 26c（堆積損壞修正，0.26.2）：0.26.2、check_26c（sink 不做引擎工作、TaskScope、thread_local、__finally、TimerStopper、Rng()）、OVERLAP 錯誤樣本'),
    'build/fix21_identity.py': ('unchanged', 'c9cafeb6f206b2242fa9ca81931508d2d4460dbfc2bd78917af98a84cf187267', ''),
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
    'build/fix25_history.py': ('changed', '3c215cd9f66d65f82736462108585f7f28c14746c918c98bdc48e8a272d5ea05', 'Round 26（探針 log）：round 25 的 Papyrus 封印改讀 pre-fix26 快照（先過 round 26 的證明；由產生器重寫，表格不變）'),
    'build/fix25_history_gen.py': ('changed', '7bf425eebd501efb9690cef38cff3f0b3258f0ef56ef59e51ea4e0eb24cc38e4', 'Round 26（探針 log）：產生器讀 pre-fix26 快照的 src（round 25 出貨時的腳本）'),
    'build/fix25_history_template.py': ('changed', 'bc2fe79a2a43aa51d0c8828b7962e811b224381f6b25cba4546cd352a8afd3f5', 'Round 26（探針 log）：current_dir 改成 fix26_history.legacy_source()'),
    'build/fix25_native_history.py': ('changed', '9014bf547291024dda5578f0325065f4577e9b6c0cec2220266fd99d431a89b6', 'Round 26（探針 log）：round 25 的原生封印改讀 pre-fix26 快照（先過 round 26 的證明；由產生器重寫，表格不變）'),
    'build/fix25_native_history_gen.py': ('changed', '8083578fae81e5bfb7921dd042601fe608d56f899cd4d7e9c8d04383a6105974', 'Round 26（探針 log）：產生器列出並雜湊 pre-fix26 快照（round 25 出貨時的位元組）'),
    'build/fix25_native_history_template.py': ('changed', '720cf5f28fe5dc2a012956fc61a7b27eaa5d4aebc2aa847c52fb2412c69edfd7', 'Round 26（探針 log）：base() 讀 pre-fix26 快照（同 round 25 對 round 24 的做法）'),
    'build/fix26_history.py': ('added', '6f182183f2860052eb229f2a710b4b628b3446ac57bb68dff2cfc249a8ea8262', 'Round 26（探針 log）：round 26 的 Papyrus 封印（產生的）'),
    'build/fix26_history_gen.py': ('added', 'd40116a7d5b52f53af4d3ab1df5526e618e4c5c11c16fc589f32c29ee6bee29a', 'Round 26（探針 log）：round 26 Papyrus 封印產生器（新檔）'),
    'build/fix26_history_template.py': ('added', '8fc3766afd401bf515af94f39c37a213d15038c3e52f2c1d78c265af089b480e', 'Round 26（探針 log）：round 26 Papyrus 封印樣板（新檔）'),
    'build/fix26_native_history_gen.py': ('added', '6cfbcab6cfcc61bb8d335218470102ba0aaebba4069eccf80c9b006599db5634', 'Round 26（探針 log）：round 26 原生封印產生器（新檔）'),
    'build/fix26_native_history_template.py': ('added', 'c7d8713b8356faf9db373d6ed9d4aeb0d89d9a4a10d660fa319fe3e081c593a2', 'Round 26（探針 log）：round 26 原生封印樣板（新檔）'),
}

FOLDERS = ('native/include', 'native/src', 'native/tests')


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(rel: str, data: bytes) -> None:
    state, sha, why = FILES[rel]
    assert _sha(data) == sha, (rel, state, 'differs from the sealed bytes (edited after sealing; regenerate with a reason)')


def verify() -> dict:
    root = ROOT
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
    ('native/include/Trace.h', 'inline constexpr std::size_t kMaxLine = 480;', 'inline constexpr std::size_t kMaxLine = 481;'),
    ('native/include/Trace.h', 'inline constexpr float kLevel = 4.0f;', 'inline constexpr float kLevel = 3.0f;'),
    ('native/src/Plugin.cpp', 'LogThreadOnce(Probe::kHurtTask, "hurt task");', 'LogThreadOnce(Probe::kHurt, "hurt task");'),
    ('native/include/StatusEngine.h', 'why(i, Pick::kNeutral);', 'why(i, Pick::kFar);'),
    ('build/fix26_format.py', "B = r'[01]'", "B = r'[012]'"),
    ('build/probe-judge.py', "if not 0.88 <= r <= 0.99:", "if not 0.80 <= r <= 0.99:"),
    ('build/fix26_records.py', 'BASE = 0x5C00', 'BASE = 0x5C01'),
]


def self_check() -> dict:
    counts = verify()
    caught = []
    for rel, old, new in SILENT_EDITS:
        data = (ROOT / rel).read_bytes()
        assert old.encode('utf-8') in data, (rel, old)
        try:
            check(rel, data.replace(old.encode('utf-8'), new.encode('utf-8'), 1))
        except AssertionError:
            caught.append(rel)
            continue
        raise AssertionError(('silent edit not caught', rel, old))
    return dict(counts, silent_edits_caught=caught)

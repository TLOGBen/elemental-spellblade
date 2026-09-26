"""Round 23 (N4, your resources and the hits you take): the declared changes the historical verifiers accept. GENERATED
by build/fix23_history_gen.py from this template -- edit the reasons there, never the digests here.

Round 23 deleted ESSBGuard.OnHitEx and the Papyrus self-counter paths (ruling R6) and moved your resources and the hits
you take into DLL-applied engine effects (native/include/SelfLayer.h, Hurt.h). The verifiers of rounds 6-22 exercise the
scripts as they were; the round-22 seal (build/fix22_history.py) now runs on the pre-fix23 snapshot
(.codex/pre-fix23-snapshot/src, taken before any round-23 edit), and this module proves that today's scripts differ from
that snapshot ONLY by the changes declared below, each bound to the code by digest (comment-stripped body, sha256[:16],
build/fix21_history.digest):

  CHANGED     (script, function) -> (why, before, after)
  REMOVED     (script, function) -> (why, before)
  ADDED       (script, function) -> (why, after)
  PROPERTIES  script -> (why, code lines added outside functions, code lines removed)
  FILES       whole scripts removed or added -> (why, sha256 of the file, 'removed' | 'added')

Anything else fails the build: an undeclared edit, a declared function edited after sealing, a removed script that
comes back. legacy_source() hands the older seals and verifiers the snapshot only after that proof; the chain is
fix21 (20 -> 21, "now" = pre-fix22) -> fix22 (21 -> 22, "now" = pre-fix23) -> this one (22 -> 23, "now" = src/).
The round-23 behaviour itself is checked by build/fix23_verify.py and the native self tests.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [p for p in (str(ROOT / 'build'),) if p not in sys.path]
SNAPSHOT = ROOT / '.codex/pre-fix23-snapshot'

import fix21_history as _h21

CHANGED = {
    ('ESSBController.psc', 'AddSelf'): ('N4：改經 ESSBNative 的玩家碼 42／43／44 讀寫 DLL 的效果（1 電荷 2 岩甲 3 風勢）', '2bc9542723c7e022', '706992c20854134a'),
    ('ESSBController.psc', 'AddSync'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync', 'd03d50aacd20bf61', '7c5f1522b1661f17'),
    ('ESSBController.psc', 'ClearSelf'): ('N4：改經 ESSBNative 的玩家碼 42／43／44 讀寫 DLL 的效果（1 電荷 2 岩甲 3 風勢）', '2bce9286b43fbbbb', 'dd595e9d333d58df'),
    ('ESSBController.psc', 'ClearSelfAll'): ('R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除；這裡只剩 Papyrus 自己的（雷雨計時、聖盾、水鏡、追擊）', '0f816b4e09e63d7d', '8846069875e4b6dd'),
    ('ESSBController.psc', 'DumpStatus'): ('除錯列印改讀 DLL 的玩家碼（電荷、岩甲、風勢、戰意、冰盾、共鳴層、闇宙、超載、蓄勁、護血）', 'bac772ac32e09b0f', '510acfe88252c233'),
    ('ESSBController.psc', 'ElementHitHook'): ('N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）', '7e4998539fc9493f', '8a113b81f42f4401'),
    ('ESSBController.psc', 'GetSelf'): ('N4：改經 ESSBNative 的玩家碼 42／43／44 讀寫 DLL 的效果（1 電荷 2 岩甲 3 風勢）', '8f0de057f849f4b6', '3a0e7f9d143f2858'),
    ('ESSBController.psc', 'OnESSBDeath'): ('N4：死亡快照第 9 個值（DLL 的最後一擊潛行標記）→ 連殺讀它', '5742c170e87e7afd', '41301969e8d3a105'),
    ('ESSBController.psc', 'OnESSBEnd'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', 'e58f0533724141d1', 'bad4cf656ab05e20'),
    ('ESSBController.psc', 'OnFormClosed'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync；三重奏的保留全部同調讀 DLL 標記（碼 51）；融斷電荷快照刪除', '1485fb55e9d9d481', 'c7ed6891e8bf60bb'),
    ('ESSBController.psc', 'OnFormOpened'): ('N4：ESSBNative.FormEnter（專一計時、雷臨強化、地臨強化）；融斷電荷快照刪除', '0967597a0f570462', '459b7683dbba61cd'),
    ('ESSBController.psc', 'OnFormSwitched'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）；你的資源由 DLL 的 FormLeave 清', 'c6a828ca05eb00f1', '281cf7999960faf0'),
    ('ESSBController.psc', 'OnNoFormHit'): ('N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）', 'ed93cdf188884fd9', 'ea83cb70de915917'),
    ('ESSBController.psc', 'OnSyncStage'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync（由 ESSB_SyncUp 叫；回饋在 DLL）', '699519f021016597', '33fe70ded65d7117'),
    ('ESSBController.psc', 'OnValidHitInternal'): ('N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）', 'c0bb5b00ec8ee3ce', '3494ca618cac65ac'),
    ('ESSBController.psc', 'OnWeaponHit'): ('N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）', 'a6e060772c9aabdb', 'feb0ad37335b146d'),
    ('ESSBController.psc', 'PushSelf'): ('R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除', '58b1f12066ce718b', '3777d248c09a16fa'),
    ('ESSBController.psc', 'PushSyncStage'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync', '706faf86d3844ecc', '1e97c0185b88679e'),
    ('ESSBController.psc', 'ReconcileLoadedForm'): ('R1：新 schema 拿掉 v0.3 的岩甲常駐能力（岩甲的護甲是 DLL 效果）；同調快取刪除', 'c867d2074afb4dcd', 'd42643a8312c1799'),
    ('ESSBController.psc', 'RefreshRecovery'): ('v0.3 的岩甲常駐能力退役（不再依回復倍率重掛）', 'cbd2c95ffce8e895', '3c7c77e2efa1fc43'),
    ('ESSBController.psc', 'RefreshRuntimeValues'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync', 'eb0bdfb130aaa797', '383316c5ae553947'),
    ('ESSBController.psc', 'RefreshSyncStage'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync', 'fd2a9e692e3a2244', '29c9f366fcf8156b'),
    ('ESSBController.psc', 'ResetLoadClock'): ('N4：刪掉的計時與冷卻不再重設（它們是 DLL 的效果）', 'e1a1e78a99fa05dd', '7283ffda2984b058'),
    ('ESSBController.psc', 'SetSelf'): ('N4：改經 ESSBNative 的玩家碼 42／43／44 讀寫 DLL 的效果（1 電荷 2 岩甲 3 風勢）', 'bdb64fd7703c5e36', '5550bd51b8d7c951'),
    ('ESSBController.psc', 'Setup'): ('N4：DLL → 反應本體的新 ModEvent（放電、風刃、推力、升段、洗淨、致命一擊）（每次載入重登）', '96518b3b78f13e51', '7ec88cb279daad60'),
    ('ESSBController.psc', 'SwitchForm'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync', '4b6991b40f02e697', 'a4b47ee37dbb0535'),
    ('ESSBController.psc', 'SyncStage'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync', 'fd6050dab355b351', '23a0c390265d4e24'),
    ('ESSBController.psc', 'Tick'): ('N4：電荷／風勢／戰意的衰減是 DLL 效果的時長；雷雨加電荷改呼叫 DLL', '8993b3b148ddd7e8', '9ad46762f71ad1a2'),
    ('ESSBController.psc', 'TickTimers'): ('N4：雷霆、順勢的計時在 DLL', '484ebab77ad3182e', 'a7b504b4619a82f9'),
    ('ESSBController.psc', 'TimersActive'): ('N4：戰意、順勢不再讓 tick 保持 1 秒', '887c849f8b003099', '7eed95991eb041ed'),
    ('ESSBCounter.psc', 'OnEffectFinish'): ('R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除；AME 留著不做事（破魔印的 VMAD 與舊存檔的 AME 指向它）', '7ec7c0b59d2b945c', '8b8b6fe66c4b16d4'),
    ('ESSBCounter.psc', 'OnEffectStart'): ('R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除；AME 留著不做事（破魔印的 VMAD 與舊存檔的 AME 指向它）', '06cf4bec1c483621', 'f3e400a3ad0bcbdb'),
    ('ESSBElem.psc', 'ChargeCap'): ('N4：電荷上限由 DLL 算，經玩家碼 55 讀回', '8f8dd6963d7ea337', '0d7263226bd48617'),
    ('ESSBElem.psc', 'Discharge'): ('N4：DLL 決定的暴擊倍率（ESSB_Discharge）；電荷消耗在 DLL', '911dd98efb00ad7a', '7953581a1017fe33'),
    ('ESSBElem.psc', 'DischargeAll'): ('N4：DLL 決定的暴擊倍率（ESSB_Discharge）；電荷消耗在 DLL', '12facaf1f5bc4696', '7392b231cfcfdf2b'),
    ('ESSBElem.psc', 'EndShockNodes'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）（餘電、雷霆）', '267d35f15df4f626', '3194b6a6668adcf8'),
    ('ESSBElem.psc', 'OnFormOpened'): ('N4：雷臨強化的 +5 電荷在 DLL（FormEnter）', '699d38c5f4a690bf', '10224e92b5976261'),
    ('ESSBElem.psc', 'OnOpen'): ('N4：開印時你的資源（電荷、岩甲、風勢、同調、共鳴層、餘電）由 DLL 在開印那一擊加', 'cc2c02f0901230c4', 'f9912c6411c3d682'),
    ('ESSBElem.psc', 'OnTick'): ('N4：冰心（受擊）與雷神（命中）在 DLL', '1dc9c537bcf59716', 'd3926ade01adbeb8'),
    ('ESSBElem.psc', 'ShockBurstBonus'): ('N4：雷斷讀 ESSB_End 帶來的融斷當下電荷', 'b58c972315a5f170', 'c40229b78867b95a'),
    ('ESSBElem2.psc', 'EndEarthNodes'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）（固土）', '3ae5220f8dcabcf0', 'd10d981acfd66782'),
    ('ESSBElem2.psc', 'EndWindNodes'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）（順勢）', '4a776e94a96ce337', '4b35078d9db30793'),
    ('ESSBElem2.psc', 'LethalAmbush'): ('暗風的 ×2 移到這裡（DLL 的風刃已自己乘）', 'a8dd945fea48da93', 'a39446e643e9bf65'),
    ('ESSBElem2.psc', 'OnEarthHit'): ('N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）（地動）', '4c7240e80bb3ccfa', '3420931c15d69fb0'),
    ('ESSBElem2.psc', 'OnFormOpened'): ('N4：地臨強化的岩甲滿層在 DLL（FormEnter）', '88ed2cb8490d7b3d', 'e76ee3afc1c664a7'),
    ('ESSBElem2.psc', 'OnWindHit'): ('N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）（千刃）', 'c9062dc24bac79e5', 'c886c83ecc9bed61'),
    ('ESSBElem2.psc', 'OpenBlood'): ('N4：開印時你的資源（電荷、岩甲、風勢、同調、共鳴層、餘電）由 DLL 在開印那一擊加（血脈）', '7ff82e8119dcf9c3', '633dfe6a7917670e'),
    ('ESSBElem2.psc', 'OpenWind'): ('N4：開印時你的資源（電荷、岩甲、風勢、同調、共鳴層、餘電）由 DLL 在開印那一擊加（先風）', '47ea9338e216ce6e', '3414c07c2f7639fd'),
    ('ESSBElem2.psc', 'WindBladeMult'): ('暗風的 ×2 由 DLL 乘在 ESSB_Blade 的倍率上（避免乘兩次）', 'a5069848ceaac0e1', '570c0378d2c5cee0'),
    ('ESSBElem3.psc', 'OnWaterHit'): ('N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）（洗淨的判定與冷卻；清除本體經 ESSB_Cleanse 回控制器）', '357f4c315be5759b', '59ac6f712e580b37'),
    ('ESSBGuard.psc', 'OnPlayerLoadGame'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）（攻擊者環刪除）', '54eba762a4d6d800', '51b2fff44887b414'),
    ('ESSBGuard.psc', 'Setup'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）；載入時解除舊存檔的受擊事件登記', 'b863c28b93caf36f', 'e618e6fe51560c32'),
    ('ESSBReactions.psc', 'End'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）；蓄能的下一次地震加成（碼 53）在這裡用掉', 'c390e59484229bfa', '9724af4128ef9299'),
    ('ESSBReactions.psc', 'Open'): ('N4：開印時你的資源（電荷、岩甲、風勢、同調、共鳴層、餘電）由 DLL 在開印那一擊加', '52a6293d38ae6fab', 'f31ee4b3095987b6'),
    ('ESSBState.psc', 'ControllerQuest'): ('R1：state_schema_version 11 → 12 的新控制器任務 ID', 'd04431a50f1b63c7', 'ebb91382d072cd62'),
    ('ESSBTrees.psc', 'RefreshActive'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）（受擊節點位元刪除）', '770fb6bda07ba67d', '214e9ab0062474e0'),
    ('ESSBTrees.psc', 'RefreshTree'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）（受擊節點位元刪除）', '6dee0909b7821fcf', '448e3fc55105d61a'),
}

REMOVED = {
    ('ESSBController.psc', 'AddIceShield'): ('R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除', '8f6eb2295a46e002'),
    ('ESSBController.psc', 'AddResolve'): ('R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除', '3ebb2bc6e11c1bae'),
    ('ESSBController.psc', 'AfterOpen'): ('N4：開印時你的資源（電荷、岩甲、風勢、同調、共鳴層、餘電）由 DLL 在開印那一擊加', 'd00e88cc279eae0f'),
    ('ESSBController.psc', 'BoostSyncToStage1'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync', 'b8d4e3405d795432'),
    ('ESSBController.psc', 'ClearResolve'): ('R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除', '9cedd1190f5cfbd1'),
    ('ESSBController.psc', 'ComputeSyncStage'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync', '23464fc4cfa08679'),
    ('ESSBController.psc', 'ConsumeEndCharge'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', 'f02d00817e9d7028'),
    ('ESSBController.psc', 'ConsumeIceShield'): ('R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除', 'e677951a6902faea'),
    ('ESSBController.psc', 'ConsumeRockArmor'): ('R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除', '2fbe3bc31bf16fc1'),
    ('ESSBController.psc', 'CounterEligible'): ('R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除', '87e743932ca7a38d'),
    ('ESSBController.psc', 'EndCharge'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', 'e7559adf3345f2d1'),
    ('ESSBController.psc', 'GetGuardWindLeft'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）', '42864db8027c9bba'),
    ('ESSBController.psc', 'GetIceShield'): ('R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除', '1c2bf6aaa7f21440'),
    ('ESSBController.psc', 'GetResolve'): ('R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除', '709bbd42336989ea'),
    ('ESSBController.psc', 'OnAnimationEvent'): ('R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除', 'c9b70302d475f34a'),
    ('ESSBController.psc', 'PushTrio'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', '6267e06467d16309'),
    ('ESSBController.psc', 'RecentCast'): ('R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除', '688e411d4cbc32ce'),
    ('ESSBController.psc', 'RememberCast'): ('R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除', 'bc14fb2472d8208f'),
    ('ESSBController.psc', 'SetCloakGuard'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）', '0eb4411bce0006eb'),
    ('ESSBController.psc', 'SetGuardWind'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）', '90bef886c936952e'),
    ('ESSBController.psc', 'SetPendingDischarge'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', '7f28e9fd90228713'),
    ('ESSBController.psc', 'SetRiposte'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）', 'f749bae6e1964e3c'),
    ('ESSBController.psc', 'SetSyncKeepAll'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', '510ffb88965119d9'),
    ('ESSBController.psc', 'SetThunder'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', '061bc0585a3c970a'),
    ('ESSBController.psc', 'SetWindFollow'): ('N4：這個冷卻／視窗是 DLL 掛在你身上的效果', '1dd7442e1f2a6860'),
    ('ESSBController.psc', 'StartCounter'): ('R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除', '07a17b50b8bb2166'),
    ('ESSBController.psc', 'StopCounter'): ('R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除', 'd26a76f78342cdbd'),
    ('ESSBController.psc', 'SyncRockArmor'): ('R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除', 'de96270d96158c55'),
    ('ESSBController.psc', 'TakeCleanse'): ('N4：這個冷卻／視窗是 DLL 掛在你身上的效果', '9a5d8d3f44f7f531'),
    ('ESSBController.psc', 'TakeGrandConcert'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', '4ea5dda3b3763f4a'),
    ('ESSBController.psc', 'TakeIceHeart'): ('N4：這個冷卻／視窗是 DLL 掛在你身上的效果', '00968e8ff791daa7'),
    ('ESSBController.psc', 'TakeInterrupt'): ('N4：這個冷卻／視窗是 DLL 掛在你身上的效果', '19dbd5034e43f6a9'),
    ('ESSBController.psc', 'TakeRetaliate'): ('N4：這個冷卻／視窗是 DLL 掛在你身上的效果', '7f47e0e3c9611a17'),
    ('ESSBController.psc', 'TakeSanctuary'): ('N4：這個冷卻／視窗是 DLL 掛在你身上的效果（庇護；這個 Papyrus 冷卻 round 21 起就沒有呼叫者）', '9d4a54b3c012e15a'),
    ('ESSBController.psc', 'TakeSwitchCharge'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', '42d2d6aa59bad4a2'),
    ('ESSBController.psc', 'TakeSwitchEnd'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', '4eb8f9283c9b9d38'),
    ('ESSBCounter.psc', 'OnAnimationEvent'): ('R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除；AME 留著不做事（破魔印的 VMAD 與舊存檔的 AME 指向它）', '38e53219c13dfc23'),
    ('ESSBElem.psc', 'OpenStacks'): ('N4：開印時你的資源（電荷、岩甲、風勢、同調、共鳴層、餘電）由 DLL 在開印那一擊加', 'f18d9c97d32a51da'),
    ('ESSBElem.psc', 'OverloadMult'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', '1197ae211ef2fa0c'),
    ('ESSBElem.psc', 'StormChance'): ('N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）', '8c2246fb61b652a1'),
    ('ESSBElem2.psc', 'CheckWindGauge'): ('N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）（風勢到門檻的風刃）', '91ab3603bb44f4d5'),
    ('ESSBElem2.psc', 'OnEarthRetaliate'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）（反震）', 'dc553e092bb88a8f'),
    ('ESSBElem2.psc', 'OpenStacks'): ('N4：開印時你的資源（電荷、岩甲、風勢、同調、共鳴層、餘電）由 DLL 在開印那一擊加', '5b0c0d01ddc59442'),
    ('ESSBElem3.psc', 'GuideSync'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）（導引）', '93716991a5bc3388'),
    ('ESSBElem3.psc', 'OnPoisonSkin'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）（毒皮）', 'd95024d2cb28b33a'),
    ('ESSBGuard.psc', 'OnHitEx'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）', 'd298fe2cb4be668f'),
    ('ESSBGuard.psc', 'RefreshNodeBits'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）', '1f16c78bc49e5f7d'),
    ('ESSBGuard.psc', 'TakeAttacker'): ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）', '3b44d00c61cb954b'),
    ('ESSBNoForm.psc', 'OnCounterSpell'): ('R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除', '1fce8b3c300b628f'),
    ('ESSBNoForm.psc', 'OnInterruptCast'): ('N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）（斷咒）', 'bdc1887551a20895'),
    ('ESSBNodes.psc', 'ConcertMult'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', 'eda5619a20fb9e84'),
    ('ESSBNodes.psc', 'HasExtreme'): ('N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）', 'ccbbd0e8616fa2c4'),
    ('ESSBNodes.psc', 'OnSyncStage'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync（回饋）', '4b5ec9268e0e5b48'),
    ('ESSBNodes.psc', 'OpenSyncBonus'): ('N4：開印時你的資源（電荷、岩甲、風勢、同調、共鳴層、餘電）由 DLL 在開印那一擊加', '0c32447c4ab4ca4e'),
    ('ESSBNodes.psc', 'SyncThresholdScale'): ('N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync', '0334fcc0ae23ade5'),
    ('ESSBNodes.psc', 'TrioMult'): ('N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）', 'fa309a477da88767'),
    ('ESSBReactions.psc', 'AddOpenSelf'): ('N4：開印時你的資源（電荷、岩甲、風勢、同調、共鳴層、餘電）由 DLL 在開印那一擊加', '06959801f5e61fd1'),
}

ADDED = {
    ('ESSBController.psc', 'OnESSBBlade'): ('N4：DLL → 反應本體的新 ModEvent（放電、風刃、推力、升段、洗淨、致命一擊）', '468f9d28b129a0b9'),
    ('ESSBController.psc', 'OnESSBCleanse'): ('N4：DLL → 反應本體的新 ModEvent（放電、風刃、推力、升段、洗淨、致命一擊）', '705948e51d7d9b3f'),
    ('ESSBController.psc', 'OnESSBDischarge'): ('N4：DLL → 反應本體的新 ModEvent（放電、風刃、推力、升段、洗淨、致命一擊）', '8047da210f4a8624'),
    ('ESSBController.psc', 'OnESSBKnock'): ('N4：DLL → 反應本體的新 ModEvent（放電、風刃、推力、升段、洗淨、致命一擊）', '8c8809224ebaf9ca'),
    ('ESSBController.psc', 'OnESSBLethal'): ('N4：DLL → 反應本體的新 ModEvent（放電、風刃、推力、升段、洗淨、致命一擊）', 'f4ddbf63843af50a'),
    ('ESSBController.psc', 'OnESSBSyncUp'): ('N4：DLL → 反應本體的新 ModEvent（放電、風刃、推力、升段、洗淨、致命一擊）', '00d2f1e8639d5c02'),
    ('ESSBController.psc', 'SelfCode'): ('N4：改經 ESSBNative 的玩家碼 42／43／44 讀寫 DLL 的效果（1 電荷 2 岩甲 3 風勢）', 'a4633c3c532f5a38'),
    ('ESSBNative.psc', 'FormEnter'): ('N4：開形態（專一計時、雷臨強化、地臨強化）', '813dfddb5409d7d2'),
    ('ESSBNative.psc', 'SetSync'): ('N4：切換／融斷後保留的同調（不算升段）', '4b061adaca2654ef'),
}

PROPERTIES = {
    'ESSBController.psc': ('R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除；融斷／切換電荷、戰意、冰盾、斷咒／冰心／反震／庇護／洗淨冷卻、雷霆／順勢計時、協奏旗標、極致計數、岩甲能力快取、同調快取這些成員刪除（它們是 DLL 的效果）', (), ('Int BurstCharge', 'Int SwitchCharge', 'Int SelfCharge', 'Int SelfRockArmor', 'Int SelfWind', 'Float ChargeDecayAt', 'Float SelfLastHit', 'Int CachedSync', 'Int Resolve', 'Float ResolveTime', 'Float InterruptTime', 'Float ThunderLeft', 'Int IceShield', 'Int PendingDischarge', 'Float IceHeartTime', 'Float WindFollowLeft', 'Float RetaliateTime', 'Float SanctuaryTime', 'Float RockArmorShown', 'Float CleanseTime', 'Bool SwitchEndPending', 'Int ExtremeCount')),
    'ESSBCounter.psc': ('R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除（AME 的成員刪除）', (), ('Actor Holder', 'ESSBController Ctl', 'Bool Listening')),
    'ESSBGuard.psc': ('R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）（每攻擊者 3 秒環的成員刪除；屬性保留原 VMAD 版面）', (), ('Actor[] RecentActor', 'Float[] RecentTime', 'Int RecentNext', 'Bool ArraysInitialised')),
}

FILES = {
}

digest = _h21.digest
code = _h21.code
functions = _h21.functions
body_of = _h21.body_of
outside_functions = _h21.outside_functions


def snapshot_text(script: str) -> str:
    return (SNAPSHOT / 'src' / script).read_text(encoding='utf-8-sig')


def current_dir() -> Path:
    """Round 24 moved "now" for this seal to the pre-fix24 snapshot (round 23 as shipped): build/fix24_history.py first
    proves today's scripts differ from it only by round 24's declared changes."""
    import fix24_history
    return fix24_history.legacy_source()


def current_text(script: str) -> str:
    return (current_dir() / script).read_text(encoding='utf-8-sig')


def round23_diff(script: str, text: str | None = None) -> dict:
    """pre-fix23 snapshot -> now (or `text`) for one script: every function the same, comments only, or declared
    with matching digests; code outside functions the same apart from comments, or exactly the declared lines."""
    old_text = snapshot_text(script)
    new_text = current_text(script) if text is None else text
    old_fns, new_fns = functions(old_text), functions(new_text)
    out = {}
    for fn in sorted(set(old_fns) | set(new_fns)):
        before, now = old_fns.get(fn), new_fns.get(fn)
        if before is None:
            decl = ADDED.get((script, fn))
            assert decl is not None, (script, fn, 'added in round 23 but not declared in ADDED')
            assert digest(now) == decl[1], (script, fn, 'added body differs from the declared one')
            out[fn] = 'added'
        elif now is None:
            decl = REMOVED.get((script, fn))
            assert decl is not None, (script, fn, 'deleted in round 23 but not declared in REMOVED')
            assert digest(before) == decl[1], (script, fn, 'pre-fix23 body is not the one the removal was declared against')
            out[fn] = 'removed'
        elif before == now:
            continue
        elif code(before) == code(now):
            out[fn] = 'comments'
        else:
            decl = CHANGED.get((script, fn))
            assert decl is not None, (script, fn, 'changed in round 23 but not declared in CHANGED')
            assert digest(before) == decl[1], (script, fn, 'pre-fix23 body is not the one the declaration was made against')
            assert digest(now) == decl[2], (script, fn, 'body differs from the declared round-23 change (edited after sealing)')
            out[fn] = 'declared'
    old_lines, new_lines = outside_functions(old_text).splitlines(), outside_functions(new_text).splitlines()
    if old_lines != new_lines:
        decl = PROPERTIES.get(script)
        assert decl is not None, (script, 'code outside functions changed in round 23 but not declared')
        added = tuple(x for x in new_lines if x not in old_lines)
        removed = tuple(x for x in old_lines if x not in new_lines)
        assert (added, removed) == (decl[1], decl[2]), (script, 'lines outside functions differ from the declared ones',
                                                        added, removed)
        out['<properties>'] = 'declared'
    return out


_VERIFIED = None


def verify() -> dict:
    """Every script: whole-file removals / additions by sha256, everything else through round23_diff."""
    global _VERIFIED
    if _VERIFIED is not None:
        return _VERIFIED
    old = {p.name for p in (SNAPSHOT / 'src').glob('*.psc')}
    new = {p.name for p in current_dir().glob('*.psc')}
    report = {}
    for name in sorted(old | new):
        if name not in old or name not in new:
            decl = FILES.get(name)
            assert decl is not None, (name, 'script added or removed in round 23 but not declared in FILES')
            path = SNAPSHOT / 'src' / name if name in old else current_dir() / name
            assert decl[2] == ('removed' if name in old else 'added'), (name, 'declared the other way round')
            assert hashlib.sha256(path.read_bytes()).hexdigest() == decl[1], (name, 'file differs from the declared one')
            report[name] = decl[2]
            continue
        changes = round23_diff(name)
        if changes:
            report[name] = changes
    for (script, fn) in list(CHANGED) + list(REMOVED) + list(ADDED):
        assert script in report and fn in report[script], (script, fn, 'declared but not a round-23 change')
    _VERIFIED = report
    return report


def legacy_source() -> Path:
    """The scripts round 22 shipped: the pre-fix23 snapshot, once verify() tied it to today (build/fix22_history.py reads it)."""
    verify()
    return SNAPSHOT / 'src'


# Silent edits (a number or a call changed inside a declared, an added or an untouched function): each must fail.
SILENT_EDITS = [
    ('ESSBController.psc', 'OnFormClosed', 'SetSyncKeep(syncBefore, 60)', 'SetSyncKeep(syncBefore, 30)'),
    ('ESSBController.psc', 'OnESSBKnock', 'ApplyUtil(0, 30.0, 3, target)', 'ApplyUtil(0, 45.0, 3, target)'),
    ('ESSBReactions.psc', 'End', 'mult * (1.0 + charged)', 'mult * (1.5 + charged)'),
    ('ESSBElem.psc', 'Discharge', 'amount = amount * afCritMult', 'amount = amount * 2.5'),
    ('ESSBGuard.psc', 'Setup', 'PO3_Events_Alias.UnregisterForAllHitEventsEx(Self)', 'PO3_Events_Alias.RegisterForHitEventEx(Self)'),
]


def self_check() -> dict:
    """Every declaration is true now, and the silent edits are caught."""
    verify()
    faults = []
    for script, fn, old, new in SILENT_EDITS:
        text = current_text(script)
        body = body_of(text, fn)
        assert body is not None and old in body, (script, fn, old)
        mutated = text.replace(body, body.replace(old, new, 1), 1)
        try:
            round23_diff(script, mutated)
        except AssertionError:
            faults.append(f'{script}:{fn}')
            continue
        raise AssertionError(('silent edit not caught', script, fn, old, new))
    return dict(changed=len(CHANGED), removed=len(REMOVED), added=len(ADDED), properties=len(PROPERTIES),
                files=len(FILES), silent_edits_caught=faults)

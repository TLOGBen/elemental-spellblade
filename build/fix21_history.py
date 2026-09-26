"""Round 21 (v0.4 trees): the declared changes the historical verifiers accept.

Older rounds' verifiers pin function bodies (or whole files) to their own "before" snapshots. Round 21 rebuilt the
skill trees to v0.4, so some of those bodies changed on purpose: v0.3 node effects that v0.4 removed or handed to a
later slice (N3-N6) were deleted, and every node read gained a `; @node` annotation. A pinned body that differs now
is accepted only when BOTH hold:

  1. the pre-fix21 snapshot (.codex/pre-fix21-snapshot) still matched the historical baseline, so the difference
     was made by round 21 and not by some earlier undeclared edit; and
  2. round 21's difference is comments only (annotations, reworded comments), or the function is listed in
     CHANGED / REMOVED below with the v0.4 reason.

Anything else fails the build, exactly as before.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [p for p in (str(ROOT / 'build'),) if p not in sys.path]
SNAPSHOT = ROOT / '.codex/pre-fix21-snapshot'

# Every declaration is bound to the code it declares (review fix 2): (reason, sha256[:16] of the comment-stripped
# body in the pre-fix21 snapshot, sha256[:16] of it now). Any other edit to a declared function - a number, a
# condition - no longer matches and fails the build, exactly like an undeclared change.
# (script, function) -> (why round 21 changed it, before digest, after digest)
CHANGED = {
    ('ESSBController.psc', 'AfterOpen'): ('v0.4：廣印移除', 'dc343621f878db2d', '8095eb0b2d3a11be'),
    ('ESSBController.psc', 'ApplyStrip'): ('v0.4 5.11 水域：每秒剝除時跳過冷卻', '34d67d662c196224', '4856339c584b0487'),
    ('ESSBController.psc', 'BloodDrainPerSecond'): ('v0.4 5.8：血傳奇分支「不死」移除；血約的維持費倍率（BloodCostScale）移除', '86a9ce6c64d161ef', 'd4de1e4b638e1adf'),
    ('ESSBController.psc', 'BloodPowerCost'): ('v0.4 5.8：血約的重擊扣血倍率（BloodCostScale）移除', '786cf260b2df4a6f', '788377f1a50536f1'),
    ('ESSBController.psc', 'DifferenceMult'): ('v0.4：HitExtraMult、OpenStrikeMult（v0.3 節點）移除', '4889e41b13beb7a2', '5a7cfbd117de57ff'),
    ('ESSBController.psc', 'DifferencePossible'): ('v0.4：差異補丁的觸發條件改成 v0.4 的節點', 'd410353897c3871d', '6e86687444e22c32'),
    ('ESSBController.psc', 'FinishMark'): ('v0.4：汪洋（保留浸濕）移除', '800ffcfa373f451b', 'a2515953d7a0dce3'),
    ('ESSBController.psc', 'OnFormClosed'): ('斷界（DLL N5，LATER-N5）：v0.3 的減速＋碎甲近似拿掉（審查修正）', '8b1f49e37cffe68e', 'b47d5a2656c62342'),
    ('ESSBController.psc', 'OnKillEvent'): ('v0.4：暗「收割」、無元素「無魔」的擊殺掛勾移除；毒的死亡擴散（蔓延）與亡者歸來：提前移除（裁定 C3），於 N5 以 v0.4 版本（死亡處理）重做', '236cb2fe6b216ef2', '192e41d78bd2bcea'),
    ('ESSBController.psc', 'OnNoFormHit'): ('v0.4 5.1：v0.3 反擊 ×1.3（改成 ESSB_RiposteWindow，DLL 讀、吸魔 ×2）、純武藝、連擊、餘燼移除；無形態命中只剩斷咒（吸魔／滅法在 DLL）', 'a641733652755b76', 'ed93cdf188884fd9'),
    ('ESSBController.psc', 'PullTo'): ('v0.4：牽引移除', 'abdecea941bea729', 'db58dd6526b28427'),
    ('ESSBController.psc', 'RefreshAbilities'): ('v0.4：抗咒、星輝移除；冰甲／霜膚常駐斗篷能力加入', '9681a49c965f3b9b', '762830b2220c1013'),
    ('ESSBController.psc', 'RefreshRecovery'): ('成果 3：v0.3 分支進入點的回復倍率改寫移除（v0.4 沒有需要腳本改值的進入點）', 'e9a9e5aacd61339e', 'cbd2c95ffce8e895'),
    ('ESSBController.psc', 'ResetLoadClock'): ('AvatarLeft（化身，LATER-N4）與 RiposteLeft（反擊改 DLL 視窗）兩個死變數拿掉', '14d8d483589b7bad', '4476090783bcc1d8'),
    ('ESSBController.psc', 'SetRiposte'): ('v0.4 5.1 反擊：改成玩家身上的視窗效果，DLL 讀取並用掉（裁決 R5）', 'e18348e032d9330a', 'f749bae6e1964e3c'),
    ('ESSBController.psc', 'SwitchForm'): ('v0.4 5.2 順轉：切換後 1 秒（v0.3 是 2 秒）（審查修正）', '236531ac14963ac0', '4b6991b40f02e697'),
    ('ESSBController.psc', 'Tick'): ('v0.4：ESSBElem2.OnTick（v0.3 聖／風每秒節點）與 RefreshWeaponPercent（成果 3）移除', '778ffc7ffb052a7e', '1da5f896ee030d99'),
    ('ESSBController.psc', 'TickDomain'): ('v0.4 5.6 地裂／5.11 水域：不回耐＋耐力歸零擊倒；水域每秒剝除與淨化', 'cfda4240a1d0de33', '079083cc5cff4f38'),
    ('ESSBController.psc', 'TickTimers'): ('v0.4 5.3 熔身每秒回耐力 5（不是 20×G）；化身的每 N 秒自動施放拿掉（LATER-N4）；死變數 RiposteLeft 拿掉（審查修正）', '61d63323faa63db9', '7a08dd6b49f9557a'),
    ('ESSBController.psc', 'TimersActive'): ('死變數 RiposteLeft 拿掉（反擊改成 DLL 讀的視窗效果）', '2e7422533e14937f', '15cd041dcb8d6a56'),
    ('ESSBController.psc', 'ValidateBindings'): ('round 21 新屬性（RiposteWindowSpell、IceArmorAbility、IceArmorWideAbility）', 'b9b9952b24f0890a', 'e02e98a8678ede1b'),
    ('ESSBElem.psc', 'Detonate'): ('v0.4 5.3：爆燃一律消耗熱度', '6b1a988d52c8c0b8', 'cb7a8c5f6f1c3a8f'),
    ('ESSBElem.psc', 'DetonatePerLayer'): ('v0.4 5.3：爆燃每層固定 +20%（v0.3 的 +1%／點主線換成別的節點）', '1ac264e4c31a98a4', 'b76a242f9e6d4432'),
    ('ESSBElem.psc', 'Discharge'): ('v0.4 5.5：電弧 3 跳 55%、連鎖 5 跳；電蝕移除。v0.3「疾電」的放電後受傷 -15% 拿掉——疾電在 v0.4 仍在（改版，DLL 受擊 N4，LATER-N4），不是移除', '68ec206d78a33322', '13e790b842a8afba'),
    ('ESSBElem.psc', 'FireHitExtra'): ('v0.4 5.3：熱度每層 +8%，不再吃點數', '889e77e4371fc99f', '6af1fb6c88f86fbb'),
    ('ESSBElem.psc', 'HeatCap'): ('v0.4 5.3：添薪不再加熱度上限（N3 的引信）', 'b0d85eeff483611e', '6c63f7ce736e9d7e'),
    ('ESSBElem.psc', 'HitStacks'): ('v0.4 5.4：寒蝕重擊冰 +3 層（v0.3 是 4）', '252277d70c508b89', '8f2bea604125b840'),
    ('ESSBElem.psc', 'IgniteMult'): ('v0.4 5.3：點燃 ×2.0', '3b81947a1f76e3ef', 'dc6dc927b9af0c24'),
    ('ESSBElem.psc', 'OnEnd'): ('裁決 R2：接管附傷只給表格寫了這一格的樹；debug ≥2 時畫面通知「接管附傷 +X%（5 秒）」（探針卡）', '7e389c286aecfeb4', '97d278e7007f3dbf'),
    ('ESSBElem.psc', 'OnFormOpened'): ('v0.4 2.x：星臨半徑跟其他元素一樣（AdventRadius 的星專屬分支移除）', '2ebbaf821ab21b80', '699d38c5f4a690bf'),
    ('ESSBElem.psc', 'OnFrozenTick'): ('重複的 90% 減速夾值移除（ApplyUtil 已夾在 ≤70%）；v0.4 5.4 深寒＝耐力不回復（耐力凝滯），不是主動削耐（審查修正）', 'd5086e91624a7248', 'ef009f3765d6acf1'),
    ('ESSBElem.psc', 'OnIgnite'): ('v0.4 5.3：v0.3 的火浴回血拿掉。提前移除（裁定 C3）：火浴在 v0.4 是白熱點燃時依人數回血（LATER-N3），於 N3 以 v0.4 版本重做', '98fa690fc6852bc6', '0e43319329e71a22'),
    ('ESSBElem.psc', 'OnTick'): ('雷神回魔拿掉 G(L)（v0.4 沒寫量）（審查修正 C1）', '6ec43a96d77cf7f2', 'b80f5ba9acf3f08e'),
    ('ESSBElem.psc', 'OpenFire'): ('v0.4 5.3 餘熱：開印回 15 耐力（不是 50×G）（審查修正 C1）', '40975c3e3d7ebc5c', '4b3f7473dffeccba'),
    ('ESSBElem.psc', 'OpenFrost'): ('v0.4 5.4：冰甲、冰晶的開印效果移除（冰甲改成常駐寒氣斗篷）', '35279b8584712596', 'c62ec0b392db5d9f'),
    ('ESSBElem.psc', 'OpenShock'): ('v0.4 5.5 充能開印：開印回 B_max 魔力（不是 60×G）（審查修正 C1）', '48e528d1e74b4ad3', '539d130a94ed4781'),
    ('ESSBElem.psc', 'OpenStacks'): ('v0.4 5.3：引火開印 5 層；5.4 寒蝕', '85a0313bd4b7db46', 'a0af03ffd514949d'),
    ('ESSBElem.psc', 'OverheatCap'): ('v0.4 5.3：過熱上限固定 10（v0.3 分支 +10 移除）', '3bfb83436573be5c', '5c2b7aa6c66b9fae'),
    ('ESSBElem.psc', 'OverloadMult'): ('v0.4 5.2：過載終焉對任何元素', '511b0b154158f3e0', '1197ae211ef2fa0c'),
    ('ESSBElem.psc', 'ShatterThreshold'): ('v0.4 5.4：碎冰門檻 20%', '1ba2d2f0e8c2cfc1', '27ed781cbbabb24c'),
    ('ESSBElem.psc', 'ShockHitExtra'): ('v0.4 5.5：電蝕移除', 'deba460ef9a0da08', 'ab19bcf302332479'),
    ('ESSBElem.psc', 'SignatureMult'): ('v0.4：風、毒沒有招牌主線，回 1.0', 'c241949c3ad284a4', '9e42ddc25ab21055'),
    ('ESSBElem2.psc', 'BlowDistance'): ('v0.4 5.7：吹飛距離固定 3 公尺', '4a68dd475b657fab', '8b3076b76ce8c40c'),
    ('ESSBElem2.psc', 'EndBloodNodes'): ('v0.4 5.8：血約移除', '161ac4ea1c116524', 'f24cc62769100e80'),
    ('ESSBElem2.psc', 'EndDivineNodes'): ('v0.4 5.9：光耀、處決移除', 'ee3cef0bd9077011', '7cbdb3d30a83f9c2'),
    ('ESSBElem2.psc', 'EndEarthNodes'): ('v0.4 5.6：地斷移除', '1c948828e6a561e4', '619dd2adf6285ae9'),
    ('ESSBElem2.psc', 'FissureArmor'): ('v0.4 5.6 裂痕護甲削減 -30 → -60（+2／點），不乘 G(L)（審查修正 C1）', 'dd8268517140098d', '118ab11bdb19a0e9'),
    ('ESSBElem2.psc', 'HolyVulnerability'): ('v0.4 5.9：聖易傷不再吃點數', 'a7b715cbc0822d1b', 'c4aaf885bc984cb9'),
    ('ESSBElem2.psc', 'Judge'): ('v0.4 2.6 裁決：治療你 B_max ×1.0，不乘 G(L)、不乘傷害倍率（審查修正 C1）', '23c772a974f511ae', '83a4603e363626cb'),
    ('ESSBElem2.psc', 'JudgeArea'): ('v0.4：每一次裁決各治療 B_max ×1.0；round 7 的累計上限不在 v0.4（審查修正 C1）', 'af1064ef731c2303', 'a816923a193879f6'),
    ('ESSBElem2.psc', 'OnAsh'): ('v0.4 5.9 聖灰：回魔 B_max ×2（審查修正 C1）', '222d16512793fc2a', '5b07de4e6255f035'),
    ('ESSBElem2.psc', 'OnDivineHit'): ('v0.4 5.9：命中回血主線與祝福移除；神罰、聖盾在 v0.4 是改版（聖佑相關，LATER-N3），v0.3 效果拿掉；只留護持', 'fe449613c0057119', 'aa9aed2154b55d60'),
    ('ESSBElem2.psc', 'OnEarthHit'): ('v0.4 5.6 震擊：削減 50 耐力（審查修正 C1）', '302849138300ba38', '38bf30497702d209'),
    ('ESSBElem2.psc', 'OnFormOpened'): ('v0.4 5.6 地臨強化（耐力削 50%）、5.7 氣旋、5.8 血臨強化（付 15% 血）、5.9 聖臨強化 B_max ×2＝20；範圍＝臨的範圍 2 公尺 +0.2 公尺／點（審查修正）', '45c11a1f80f0386e', 'd4ba55ef730a2e99'),
    ('ESSBElem2.psc', 'OnKill'): ('v0.4 5.8：不死（同調三段流血目標死亡回滿耐力）拿掉。提前移除（裁定 C3），於 N5 以 v0.4 版本重做', '443e8785142e668b', '3babdf0acb84a8c5'),
    ('ESSBElem2.psc', 'OpenBlood'): ('v0.4 5.8 開印回血：B_max ×0.5，低血位 ×2（審查修正 C1）', '219bdf59aac3a6bf', '7e414ab816e4ff27'),
    ('ESSBElem2.psc', 'OpenDivine'): ('v0.4 5.9：聖護、聖啟移除', '98fa1f459fd342ca', '90b4113d931c4360'),
    ('ESSBElem2.psc', 'OpenEarth'): ('v0.4 5.6：地基、裂地移除', '03b969a345d2a861', '12ad1edf6a55e6af'),
    ('ESSBElem2.psc', 'OpenWind'): ('v0.4 5.7 氣流：開印回 10 耐力（審查修正 C1）', '3ed4ea669b6f240f', 'dbbcd2dd34eda9ac'),
    ('ESSBElem2.psc', 'QuakeStamina'): ('v0.4 2.x 地震：削減耐力 B_max ×2（v0.3 係數 4.0 → 2.0）（第二次審查修正）', 'eb13c7e3df88959e', '80df001f327089c5'),
    ('ESSBElem2.psc', 'RockArmorPerLayer'): ('v0.4 5.6：岩甲每層護甲 +25（磐石 +40），不乘 G(L)（審查修正 C1）', '20318f9fceb2aeb3', 'e6cbcdc106866043'),
    ('ESSBElem2.psc', 'WindBladeOne'): ('v0.4 5.7 追風：風刃命中回 3 耐力（審查修正 C1）', '103add2bebaa7e26', '61f6f42095542e37'),
    ('ESSBElem3.psc', 'AdventRadius'): ('v0.4 5.13：星臨半徑 (2 + 0.2 × 點) 公尺', '0c494a8ce99e3beb', '926855b2b64b123e'),
    ('ESSBElem3.psc', 'AfterDeathCurse'): ('v0.4 5.12：處刑移除', '1582a63f0d26d731', '440847345d5e9bd6'),
    ('ESSBElem3.psc', 'CatalyzeSeconds'): ('v0.4 5.10：毒斷移除', '1a832948bb5456f8', 'c6908ee7a33d41c9'),
    ('ESSBElem3.psc', 'DetonateAstral'): ('v0.4 5.13：星痕引爆不再乘星軌倍率、不再觸發星爆連鎖', '5d9bb95210ca3695', '7810bcf143d94231'),
    ('ESSBElem3.psc', 'EndAstralNodes'): ('v0.4 5.13：星引、星界之門移除；星域半徑 3 公尺', 'dfe3c58620c64cc2', 'f81923b73b9b587f'),
    ('ESSBElem3.psc', 'EndDarkNodes'): ('v0.4 5.12：蝕魔終焉移除', '1af843f5ee0b058b', '332df402f6a4de4e'),
    ('ESSBElem3.psc', 'EndWaterNodes'): ('v0.4 5.11：汪洋移除；水斷治療量＝該水印記的融斷量（v0.4 2.7 D_burst 含 G(L)），拿掉 v0.3 多乘的 ×2.0（第二次審查修正）', '64a361f4f1b21d4e', '95db7899c21cf75d'),
    ('ESSBElem3.psc', 'Fall'): ('v0.4 5.13：星落單體（流星雨移除）', '281a50d6eb51e88e', 'c8bf8e1a5d9a8d06'),
    ('ESSBElem3.psc', 'GuideSync'): ('v0.4 5.11：導引同調 5', '4f13696fb49e0639', '93716991a5bc3388'),
    ('ESSBElem3.psc', 'OnDarkHit'): ('v0.4 5.12：蝕魔（改到無形態的奪魔）、衰弱、腐朽移除', '03e0fe2a67b902ec', '0b28184408b769d7'),
    ('ESSBElem3.psc', 'OnFormOpened'): ('v0.4 5.11 水臨強化：浸濕用 WetSlow／WetSeconds、淨化、魔力回滿；毒／水／暗臨強化的範圍＝臨的範圍（審查修正）', '78d091870cbda94d', '049e6da886857b69'),
    ('ESSBElem3.psc', 'OnHit'): ('v0.4 5.13：星的命中節點（星軌）移除', '6245713138827810', 'adac3be04db928c7'),
    ('ESSBElem3.psc', 'OnWaterHit'): ('v0.4 5.11：水牢、水鏡移除', 'ed0ff98cfe71b5f6', '46a0118667ed99e2'),
    ('ESSBElem3.psc', 'OpenAstral'): ('v0.4 5.13：星引力、星光移除；星散 15 公尺', 'd5d3b55f2512dae6', 'd30d2e793939d9c4'),
    ('ESSBElem3.psc', 'OpenDark'): ('v0.4 5.12：只留幻影、暗染', '358e5783803202b6', 'ab261f521d52d7ce'),
    ('ESSBElem3.psc', 'OpenPoison'): ('v0.4 5.10 毒血：開印回血 B_max ×0.5（審查修正 C1）', '08679bfdd5948c99', '9feab179962b2095'),
    ('ESSBElem3.psc', 'OpenWater'): ('v0.4 5.11：廣佈用浸濕時長', '8476be7fe8e9c7fb', '34bb2e6b28956af1'),
    ('ESSBElem3.psc', 'PoisonFormTick'): ('v0.4 5.10 百毒不侵：每個中毒敵人回血，拿掉 G(L)（v0.4 沒寫量）（審查修正 C1）', '53430d719399374d', '46e9c3d12dd4d6ba'),
    ('ESSBElem3.psc', 'SpreadInterval'): ('v0.4 5.10：擴散每 2 秒', '851009e8ccaa2714', '1b5e5f51e2979272'),
    ('ESSBElem3.psc', 'SpreadTargets'): ('v0.4 5.10：擴散 1 個目標', '64b94f6ffb22c7ac', '1d111b653fe6a6a3'),
    ('ESSBElem3.psc', 'TakeoverOpenMult'): ('v0.4 5.13：接管開印 ×1.5', '7adcf9255ee6a277', '7cfd6818abbf75e4'),
    ('ESSBElem3.psc', 'TargetDamageMult'): ('v0.4 5.12：詛咒滿層增傷主線換成別的節點；只留星鎖、星域', '418d2df37afe6d85', '22cf38e6c11bc828'),
    ('ESSBElem3.psc', 'WetSlow'): ('v0.4 2.6：浸濕減速只看 ESSB_WaterWetSlowPct（15%）', '2b166156ece14a33', '32fc59091a6f557e'),
    ('ESSBGuard.psc', 'OnHitEx'): ('v0.4：反噬、冰盾、水鏡、影身移除；寒反加上冰狀態；灼身改成掛你的火印記＋一次火傷（拿掉熱度 +1）；靜電改成掛你的雷印記（拿掉發明的電荷 +1 與 50×G 削魔）（審查修正，2026-09-26 07:46 實際改動）', 'abbbd673ffe4e46d', 'd298fe2cb4be668f'),
    ('ESSBGuard.psc', 'RefreshNodeBits'): ('v0.4：受擊節點只剩 9 個', '8a958667e1e8954f', '1f16c78bc49e5f7d'),
    ('ESSBNoForm.psc', 'OnBurst'): ('v0.4 5.1：餘燼、餘燼延續、淬火移除（冷寂 N5）', '5b6872a8f260d8bd', '9ddfe11695720743'),
    ('ESSBNoForm.psc', 'OnCounterSpell'): ('v0.4 5.1 反咒：觸發時戰意 +1（審查修正）', 'de1241ca82c98c57', '1fce8b3c300b628f'),
    ('ESSBNoForm.psc', 'OnInterruptCast'): ('v0.4 5.1 斷咒：打斷施法（InterruptCast）、每 5 秒一次、戰意 +1；拿掉發明的清空魔力＋沉默（審查修正）', 'bdd84918098561ee', 'bdc1887551a20895'),
    ('ESSBNodes.psc', 'OnEndReward'): ('v0.4 5.2 反哺：每次終焉回 B_max 魔力（審查修正 C1）', 'a9ede21867c054a3', '67d4c37e2307cd20'),
    ('ESSBNodes.psc', 'OnSyncStage'): ('v0.4 5.2 回饋：升段回生命與魔力各 B_max ×2（審查修正 C1）', 'df565a3c8ce3aed2', '4b5ec9268e0e5b48'),
    ('ESSBReactions.psc', 'End'): ('v0.4：洩壓倍率（VentMult，火 N3）與星界之門（OnAnyEnd）移除', '516c74b017916b0c', 'c2722075628a4878'),
    ('ESSBReactions.psc', 'Open'): ('v0.4 2.x 開印表：感電 -B_max 魔力、裂痕耐力 -10／你 +10、聖印回血 B_max ×0.5、詛咒吸魔 B_max ×1.0，不乘 G(L)；血痕開印吸血拿掉 G(L)（v0.4 沒寫量也沒寫 G）（審查修正 C1）', 'b265ff24e5050493', 'a3d5e3f8d0c6cd38'),
    ('ESSBStatus.psc', 'AddAstral'): ('v0.4 5.13：星「預知」移除', '571d39a5775bf35c', '738857c239e2c39a'),
    ('ESSBStatus.psc', 'AddStack'): ('v0.4 5.3：v0.3 的點燃殘留熱度（IgniteResidual）拿掉，點燃後熱度歸零；那一格 (0,0,2,0) 在 v0.4 是「熔心」（LATER-N3）', 'f6e6f67b61233943', '97989298a845ded9'),
    ('ESSBStatus.psc', 'Tick'): ('v0.4 5.13：星「預知」移除', 'fd3996296b8c58ef', '3d2759f639eb1b28'),
}

# (script, function) -> (why round 21 deleted it, before digest)
REMOVED = {
    ('ESSBController.psc', 'BloodCostScale'): ('v0.4 5.8：血約移除（維持費／重擊扣血不再乘它）', 'dbfcffba0b4d1610'),
    ('ESSBElem.psc', 'HitExtraMult'): ('v0.4：電蝕／命中額外倍率移除', '4157a083296c7003'),
    ('ESSBElem.psc', 'IgniteResidual'): ('v0.4 5.3：點燃殘留熱度拿掉；那一格 (0,0,2,0) 在 v0.4 是「熔心」（LATER-N3）', '13b934e29616a271'),
    ('ESSBElem.psc', 'OnAvatar'): ('化身（DLL N4，LATER-N4）：v0.3 每 N 秒自動施放各元素持續傳奇的近似拿掉（審查修正）', '42e9886a76c78e66'),
    ('ESSBElem.psc', 'OpenStrikeMult'): ('v0.4：冰甲開印一擊移除', '2f3a239f97135bb0'),
    ('ESSBElem.psc', 'VentMult'): ('v0.4 5.3：洩壓屬 N3 的熱度階梯', 'ffa70267e9d40ed2'),
    ('ESSBElem2.psc', 'OnAvatar'): ('化身（LATER-N4）：同上', 'f116a26af8159255'),
    ('ESSBElem2.psc', 'OnTick'): ('v0.3 只剩聖的「庇護」每秒檢查（生命 <30% 自動聖盾滿層）；v0.4 庇護是 DLL 受擊 N4（LATER-N4），拿掉', '742d06294390fa71'),
    ('ESSBElem3.psc', 'AstralForesee'): ('v0.4 5.13：預知移除', '147512ef800bbbe0'),
    ('ESSBElem3.psc', 'AstralTickMult'): ('v0.4 5.13：星軌倍率移除', 'a68196ba68035537'),
    ('ESSBElem3.psc', 'ConstellationRadius'): ('v0.4 5.13：星座範圍移除（範圍與其他元素相同）', '02c52f021ea393e5'),
    ('ESSBElem3.psc', 'DarkHitExtraMult'): ('v0.4 5.12：虛空倍率移除', 'afa727656da949cd'),
    ('ESSBElem3.psc', 'FallChain'): ('v0.4 5.13：星落連鎖移除', '7f41438fb2c79295'),
    ('ESSBElem3.psc', 'FallRadius'): ('v0.4 5.13：流星雨範圍移除', '6e4ff6dbe50e5fde'),
    ('ESSBElem3.psc', 'HasMeteorShower'): ('v0.4 5.13：流星雨移除', '4a6729ad35eed416'),
    ('ESSBElem3.psc', 'HasStarlight'): ('v0.4 5.13：星輝移除', '191e2ae7df1afccb'),
    ('ESSBElem3.psc', 'OnAnyEnd'): ('v0.4：星界之門移除', '5a1bfe6447377b4c'),
    ('ESSBElem3.psc', 'OnAstralDetonate'): ('v0.4 5.13：星爆連鎖屬 N5', '46fb2a1365d60f54'),
    ('ESSBElem3.psc', 'OnAstralHit'): ('v0.4：星軌移除', '41aa19c8b459781f'),
    ('ESSBElem3.psc', 'OnAvatar'): ('化身（LATER-N4）：同上（v0.3 把長河、深淵等被動數值變成主動效果）', 'b66af22f74906c79'),
    ('ESSBElem3.psc', 'OnKill'): ('v0.3 的擊殺掛勾：毒的死亡擴散（v0.4 蔓延／死亡擴散）、暗收割、亡者歸來。提前移除（裁定 C3），於 N5 以 v0.4 版本（死亡處理）重做', '30398d82c0aefbcf'),
    ('ESSBElem3.psc', 'OnShadowBody'): ('v0.4 5.12：影身移除', '695159a8e63b567a'),
    ('ESSBElem3.psc', 'Range'): ('v0.4 5.13：星的每點 +1 公尺、夜晚 ×1.5 範圍移除', 'e26a879b7095596c'),
    ('ESSBElem3.psc', 'Reanimate'): ('亡者歸來：提前移除（裁定 C3），於 N5 以 v0.4 版本重做（CanReanimate／ApplyReanimate 保留給 N5）', '284efea0c196a744'),
    ('ESSBElem3.psc', 'ScatterRadius'): ('v0.4 5.13：星散改固定 15 公尺', 'c0696aed60cdd3fd'),
    ('ESSBNoForm.psc', 'EmberRatio'): ('v0.4 5.1：餘燼移除', 'b0f13c4450c86297'),
    ('ESSBNoForm.psc', 'OnBurstTarget'): ('斷界（DLL N5，LATER-N5）：v0.3 的減速 30%＋碎甲 10% 是發明的近似，拿掉', 'f8827fd3a198e6a3'),
    ('ESSBNoForm.psc', 'OnCombo'): ('v0.4 5.1：連擊移除', '869c205618ae8a90'),
    ('ESSBNoForm.psc', 'OnKill'): ('v0.4 5.1：無魔移除', '23441294087fea9a'),
    ('ESSBNoForm.psc', 'OnMartialHit'): ('v0.4 5.1：純武藝線移除', 'f4cdf8016d43db7e'),
    ('ESSBNoForm.psc', 'WeaponBase'): ('v0.4 5.1：純武藝線移除', '6f463170b6b0f4f8'),
    ('ESSBNodes.psc', 'AvatarCooldown'): ('化身（LATER-N4）：冷卻只剩 v0.3 的每 N 秒施放在用，一起拿掉', '2d95436252808536'),
    ('ESSBNodes.psc', 'HasWideMark'): ('v0.4 5.2：廣印移除', '60cb1bf25231d103'),
    ('ESSBNodes.psc', 'OpenStrikeMult'): ('v0.4：開印一擊倍率移除', 'c33562ec1658e739'),
    ('ESSBNodes.psc', 'RefreshWeaponPercent'): ('成果 3：v0.3 的武器傷害進入點移除', '725b0915bd61c9b0'),
}

# (script, function) -> (why round 21 added it, after digest)
ADDED = {
    ('ESSBElem.psc', 'AdventRadiusOf'): ('v0.4：臨的範圍 2 公尺 +0.2 公尺／點，臨強化類分支的「範圍內」共用（審查修正）', 'd1d6dffef719fc7d'),
}


# script -> (why, the exact code lines round 21 added outside functions, the exact lines it removed)
PROPERTIES = {
    'ESSBController.psc': ('新屬性 RiposteWindowSpell（反擊視窗）、IceArmorAbility／IceArmorWideAbility（冰甲、霜膚）；死變數 AvatarLeft（化身 LATER-N4）、RiposteLeft（反擊改 DLL 視窗）拿掉', ('Spell Property RiposteWindowSpell Auto', 'Spell Property IceArmorAbility Auto', 'Spell Property IceArmorWideAbility Auto'), ('Float AvatarLeft', 'Float RiposteLeft')),
}


def code(text: str | None) -> str | None:
    """A body with comments, {...} doc blocks and blank lines removed (a ';' inside a string is not a comment)."""
    if text is None:
        return None
    import fix21_identity
    text = fix21_identity.strip_docs(text.replace('\r\n', '\n'))
    out = []
    for line in text.splitlines():
        masked = re.sub(r'"(?:[^"\\]|\\.)*"', lambda m: '"' + ' ' * (len(m[0]) - 2) + '"', line)
        cut = masked.find(';')
        kept = (line if cut < 0 else line[:cut]).rstrip()
        if kept.strip():
            out.append(kept)
    return '\n'.join(out)


def digest(body: str) -> str:
    return hashlib.sha256(code(body).encode('utf-8')).hexdigest()[:16]


def snapshot_text(script: str) -> str:
    return (SNAPSHOT / 'src' / script).read_text(encoding='utf-8-sig')


def current_dir() -> Path:
    """Round 22 moved "now" for this seal to the pre-fix22 snapshot (round 21 as shipped): build/fix22_history.py
    first proves today's scripts differ from it only by round 22's declared changes."""
    import fix22_history
    return fix22_history.legacy_source()


def current_text(script: str) -> str:
    return (current_dir() / script).read_text(encoding='utf-8-sig')


def body_of(text: str, fn: str) -> str | None:
    m = re.search(r'(?m)^[^\n;]*\b(?:Function|Event) ' + re.escape(fn) + r'\(.*?^End(?:Function|Event)', text,
                  re.S | re.M)
    return m[0] if m else None


FUNC_HEAD = re.compile(r'(?mi)^[^\n;]*\b(?:Function|Event) (\w+)\(')


def functions(text: str) -> dict:
    """name -> body; a Native declaration (no EndFunction) maps to its header line."""
    out = {}
    for m in FUNC_HEAD.finditer(text):
        body = body_of(text, m.group(1))
        out[m.group(1)] = body if body is not None else text[m.start():text.find('\n', m.start())]
    return out


def outside_functions(text: str) -> str:
    for fn, body in functions(text).items():
        text = text.replace(body, '', 1)
    return code(text)


def check_changed(script: str, fn: str, before: str, now: str) -> str:
    """`before` / `now` bodies of a function whose code differs; it must be declared, with matching digests."""
    decl = CHANGED.get((script, fn))
    assert decl is not None, (script, fn, 'changed in round 21 but not declared in CHANGED')
    _, want_before, want_after = decl
    assert digest(before) == want_before, (script, fn, 'pre-fix21 body is not the one the declaration was made against')
    assert digest(now) == want_after, (script, fn, 'body differs from the declared round-21 change (edited after sealing)')
    return 'declared'


def accept(script: str, fn: str, current: str | None, baseline: str, normalize=lambda s: s) -> str:
    """current: the function body now (None if deleted); baseline: the historical 'before' body the old verifier
    pinned (already normalized by it); normalize: the old verifier's own normalization, applied to the snapshot
    and current bodies too. Returns 'same', 'comments' or 'declared'; raises AssertionError otherwise."""
    if current is not None and normalize(current) == baseline:
        return 'same'
    snap = body_of(snapshot_text(script), fn)
    assert snap is not None and normalize(snap) == baseline, \
        (script, fn, 'differed from its historical baseline before round 21 (undeclared change)')
    if current is None:
        decl = REMOVED.get((script, fn))
        assert decl is not None, (script, fn, 'deleted in round 21 but not declared in REMOVED')
        assert digest(snap) == decl[1], (script, fn, 'pre-fix21 body is not the one the removal was declared against')
        return 'declared'
    if code(normalize(current)) == code(normalize(snap)):
        return 'comments'
    return check_changed(script, fn, snap, current)


def round21_diff(script: str, text: str | None = None) -> dict:
    """Round 20 as shipped (the snapshot) -> now (or `text`), for one script: every function the same, comments
    only, or declared with matching digests; code outside functions the same apart from comments, or exactly the
    declared added / removed lines."""
    old_text = snapshot_text(script)
    new_text = current_text(script) if text is None else text
    old_fns, new_fns = functions(old_text), functions(new_text)
    out = {}
    for fn in sorted(set(old_fns) | set(new_fns)):
        before, now = old_fns.get(fn), new_fns.get(fn)
        if before is None:
            decl = ADDED.get((script, fn))
            assert decl is not None, (script, fn, 'added in round 21 but not declared in ADDED')
            assert digest(now) == decl[1], (script, fn, 'added body differs from the declared one')
            out[fn] = 'added'
        elif now is None:
            decl = REMOVED.get((script, fn))
            assert decl is not None, (script, fn, 'deleted in round 21 but not declared in REMOVED')
            assert digest(before) == decl[1], (script, fn, 'pre-fix21 body is not the one the removal was declared against')
            out[fn] = 'removed'
        elif before == now:
            continue
        elif code(before) == code(now):
            out[fn] = 'comments'
        else:
            out[fn] = check_changed(script, fn, before, now)
    old_lines, new_lines = outside_functions(old_text).splitlines(), outside_functions(new_text).splitlines()
    if old_lines != new_lines:
        decl = PROPERTIES.get(script)
        assert decl is not None, (script, 'code outside functions changed in round 21 but not declared')
        added = tuple(x for x in new_lines if x not in old_lines)
        removed = tuple(x for x in old_lines if x not in new_lines)
        assert (added, removed) == (decl[1], decl[2]), (script, 'lines outside functions differ from the declared ones',
                                                        added, removed)
        out['<properties>'] = 'declared'
    return out


def accept_file(script: str, baseline: bytes) -> dict:
    """A whole script an older round pinned byte for byte (`baseline`). The pre-fix21 snapshot must still be those
    bytes; round 20 -> now must then pass round21_diff."""
    snap = (SNAPSHOT / 'src' / script).read_bytes()
    assert snap == baseline, (script, 'differed from its pinned bytes before round 21 (undeclared change)')
    if (current_dir() / script).read_bytes() == baseline:
        return dict(same=True)
    return dict(same=False, functions=round21_diff(script))


# The reviewer's successful silent edits (review round 21): each must now fail round21_diff.
SILENT_EDITS = [
    ('ESSBGuard.psc', 'OnHitEx', 'Ctl.ApplyUtil(0, 30.0, 3, attacker)', 'Ctl.ApplyUtil(0, 45.0, 3, attacker)'),
    ('ESSBElem2.psc', 'RockArmorPerLayer', 'Return 40.0', 'Return 60.0'),
    ('ESSBElem.psc', 'Discharge', '0.55', '0.75'),
    ('ESSBStatus.psc', 'AddStack', 'Heat = 0', 'Heat = 2'),
    ('ESSBController.psc', 'InstallMark', 'NextSeq += 1', 'NextSeq += 2'),
]


def self_check() -> dict:
    """Every declaration is true now, and the reviewer's silent edits (a number changed inside a declared or an
    untouched function) are caught."""
    for (script, fn), (why, b, a) in CHANGED.items():
        before, now = body_of(snapshot_text(script), fn), body_of(current_text(script), fn)
        assert before is not None and now is not None and digest(before) == b and digest(now) == a, (script, fn, why)
    for (script, fn), (why, b) in REMOVED.items():
        assert digest(body_of(snapshot_text(script), fn)) == b and body_of(current_text(script), fn) is None, (script, fn)
    for (script, fn), (why, a) in ADDED.items():
        assert digest(body_of(current_text(script), fn)) == a and body_of(snapshot_text(script), fn) is None, (script, fn)
    faults = []
    for script, fn, old, new in SILENT_EDITS:
        text = current_text(script)
        body = body_of(text, fn)
        assert body is not None and old in body, (script, fn, old)
        mutated = text.replace(body, body.replace(old, new, 1), 1)
        try:
            round21_diff(script, mutated)
        except AssertionError:
            faults.append(f'{script}:{fn}')
            continue
        raise AssertionError(('silent edit not caught', script, fn, old, new))
    return dict(changed=len(CHANGED), removed=len(REMOVED), added=len(ADDED), silent_edits_caught=faults)

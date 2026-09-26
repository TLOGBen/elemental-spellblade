# 195 主線完整分類（fix round 8 決策已結清）

| 樹 | 路線 | 階 | 分類／原因 | 原文 | 顯示文字 | 程式位置 |
|---|---|---|---|---|---|---|
| fire | 持續（烈焰） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 火源倍率 N +0.2／點（2 → 5） | 火源倍率 N +0.2／點（2 → 5） | DLL native/include/Status.h（node::kFireSourceN） |
| fire | 持續（烈焰） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 火附傷 +1%／點 | 火附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcAdept] |
| fire | 持續（烈焰） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 帶火印記目標火抗 -1%／點 | 帶火印記目標火抗 -1%／點 | ESSBElem.ApplyFireResistShred ← ESSBController.OnValidHitInternal |
| fire | 持續（烈焰） | 大師 | ×3：純百分比傷害主線（規劃 3） | 同調每段火附傷 +1%／點 | 同調每段火附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcMaster] |
| fire | 持續（烈焰） | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 業火，同調三段時火源倍率 N 再 +0.1／點（5 → 6.5，熔燒 8.5） | 業火，同調三段時火源倍率 N 再 +0.1／點（5 → 6.5，熔燒 8.5） | DLL native/include/Status.h（node::kFireInferno） |
| fire | 開啟（焰起） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 開印後 5 秒內熱度升階免等待，+0.5 秒／每 5 點 | 開印後 5 秒內熱度升階免等待，+0.5 秒／每 5 點 | DLL native/include/Status.h（node::kFireOpenQuick） |
| fire | 開啟（焰起） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 開印後 5 秒內火附傷 +1%／點 | 開印後 5 秒內火附傷 +3%／點 | native/include/Status.h:kOpenProc |
| fire | 開啟（焰起） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 火印記持續 +0.2 秒／點 | 火印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kMarkDuration[element]） |
| fire | 開啟（焰起） | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 火臨，開火形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 火臨，開火形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened → ESSBController.ForceOpenOn |
| fire | 開啟（焰起） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | native/include/Status.h:kOpenEffect |
| fire | 關閉（爆燃） | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult；native/include/Status.h:kEndMain |
| fire | 關閉（爆燃） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 火印記的融斷 +2%／點 | 火印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| fire | 關閉（爆燃） | 專精 | ×3：純百分比傷害主線（規劃 3） | 爆燃的消耗加成 +1%／點 × 被消耗的狀態數 | 爆燃的消耗加成 +3%／點 × 被消耗的狀態數 | native/include/Status.h:kFireConsume |
| fire | 關閉（爆燃） | 大師 | ×3：純百分比傷害主線（規劃 3） | 火印記的融斷再 +2%／點 | 火印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| fire | 關閉（爆燃） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 爆燃 +3%／點 | 爆燃 +9%／點 | src/ESSBElem.psc:SignatureMult |
| frost | 持續（凍結） | 新手 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 每次命中凍結累積 +5%／點（小數以機率取整） | 每次命中凍結累積 +5%／點（小數以機率取整） | DLL native/include/Status.h（node::kFrostAccumulate） |
| frost | 持續（凍結） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 冰附傷 +1%／點 | 冰附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcAdept] |
| frost | 持續（凍結） | 專精 | ×3：純百分比傷害主線（規劃 3） | 冰封目標受冰附傷 +2%／點 | 冰封目標受冰附傷 +6%／點 | native/include/Status.h:kFrostFrozenProc |
| frost | 持續（凍結） | 大師 | ×3：純百分比傷害主線（規劃 3） | 同調每段冰附傷 +1%／點 | 同調每段冰附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcMaster] |
| frost | 持續（凍結） | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 絕對零度，同調三段時冰封減速再 -2%／點（總減速上限 70%），可影響首領 | 絕對零度，同調三段時冰封減速再 -2%／點（總減速上限 70%），可影響首領 | ESSBElem.OnFrozen |
| frost | 開啟（冰臨） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 開印凍結 +1／每 3 點 | 開印凍結 +1／每 3 點 | DLL native/include/Status.h（node::kFrostOpenFreeze） |
| frost | 開啟（冰臨） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 開印後 5 秒內冰附傷 +1%／點 | 開印後 5 秒內冰附傷 +3%／點 | native/include/Status.h:kOpenProc |
| frost | 開啟（冰臨） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 冰印記持續 +0.2 秒／點 | 冰印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kMarkDuration[element]） |
| frost | 開啟（冰臨） | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 冰臨，開冰形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 冰臨，開冰形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| frost | 開啟（冰臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | native/include/Status.h:kOpenEffect |
| frost | 關閉（碎冰） | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult；native/include/Status.h:kEndMain |
| frost | 關閉（碎冰） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 冰印記的融斷 +2%／點 | 冰印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| frost | 關閉（碎冰） | 專精 | ×3：純百分比傷害主線（規劃 3） | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | native/include/Status.h:kTakeover |
| frost | 關閉（碎冰） | 大師 | ×3：純百分比傷害主線（規劃 3） | 冰印記的融斷再 +2%／點 | 冰印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| frost | 關閉（碎冰） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 碎冰 +3%／點（乘在 20% 上） | 碎冰 +9%／點（乘在 20% 上） | src/ESSBElem.psc:SignatureMult；native/include/Status.h:kSignature |
| lightning | 持續（充能） | 新手 | ×3：純百分比傷害主線（規劃 3） | 放電每格電荷傷害 +1%／點 | 放電每格電荷傷害 +3%／點 | src/ESSBElem.psc:Discharge |
| lightning | 持續（充能） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 雷附傷 +1%／點 | 雷附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcAdept] |
| lightning | 持續（充能） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 電荷上限 +1／每 3 點 | 電荷上限 +1／每 3 點 | ESSBElem.ChargeCap → ESSBController.AddSelf |
| lightning | 持續（充能） | 大師 | ×3：純百分比傷害主線（規劃 3） | 同調每段雷附傷 +1%／點 | 同調每段雷附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcMaster] |
| lightning | 持續（充能） | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 天雷，同調三段時放電改為對範圍內所有感電目標，範圍 2 公尺 +0.2 公尺／點 | 天雷，同調三段時放電改為對範圍內所有感電目標，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.DischargeAll |
| lightning | 開啟（雷臨） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 開印電荷 +1／每 5 點 | 開印電荷 +1／每 5 點 | ESSBElem.OpenStacks |
| lightning | 開啟（雷臨） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 開印後 5 秒內雷附傷 +1%／點 | 開印後 5 秒內雷附傷 +3%／點 | native/include/Status.h:kOpenProc |
| lightning | 開啟（雷臨） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 雷印記持續 +0.2 秒／點 | 雷印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kMarkDuration[element]） |
| lightning | 開啟（雷臨） | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 雷臨，開雷形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 雷臨，開雷形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| lightning | 開啟（雷臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | native/include/Status.h:kOpenEffect |
| lightning | 關閉（放電） | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult；native/include/Status.h:kEndMain |
| lightning | 關閉（放電） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 雷印記的融斷 +2%／點 | 雷印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| lightning | 關閉（放電） | 專精 | ×3：純百分比傷害主線（規劃 3） | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | native/include/Status.h:kTakeover |
| lightning | 關閉（放電） | 大師 | ×3：純百分比傷害主線（規劃 3） | 雷印記的融斷再 +2%／點 | 雷印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| lightning | 關閉（放電） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 放電 +3%／點 | 放電 +9%／點 | src/ESSBElem.psc:SignatureMult |
| earth | 持續（裂甲） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 裂痕護甲削減 +2／點（-30 → -60） | 裂痕護甲削減 +2／點（-30 → -60） | ESSBElem2.FissureArmor |
| earth | 持續（裂甲） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 土附傷 +1%／點 | 土附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcAdept] |
| earth | 持續（裂甲） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 命中削減目標耐力 +0.5／點 | 命中削減目標耐力 +0.5／點 | DLL native/include/HitMath.h AddFlatHitNodes（node::kEarthStaminaCut） |
| earth | 持續（裂甲） | 大師 | ×3：純百分比傷害主線（規劃 3） | 同調每段土附傷 +1%／點 | 同調每段土附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcMaster] |
| earth | 持續（裂甲） | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 地動，同調三段時重擊對耐力低於 30% 的目標跌倒，機率 5%／點 | 地動，同調三段時重擊對耐力低於 30% 的目標跌倒，機率 5%／點 | ESSBElem2.OnEarthHit → ESSBController.Knockdown |
| earth | 開啟（地臨） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 開印岩甲 +1／每 5 點 | 開印岩甲 +1／每 5 點 | ESSBElem2.OpenStacks(4) |
| earth | 開啟（地臨） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 開印後 5 秒內土附傷 +1%／點 | 開印後 5 秒內土附傷 +3%／點 | native/include/Status.h:kOpenProc |
| earth | 開啟（地臨） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 土印記持續 +0.2 秒／點 | 土印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kMarkDuration[element]） |
| earth | 開啟（地臨） | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 地臨，開土形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 地臨，開土形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened → ESSBController.ForceOpenOn |
| earth | 開啟（地臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | native/include/Status.h:kOpenEffect |
| earth | 關閉（地震） | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult；native/include/Status.h:kEndMain |
| earth | 關閉（地震） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 土印記的融斷 +2%／點 | 土印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| earth | 關閉（地震） | 專精 | 不改：v0.4 明寫「不吃節點倍率」 | 地震耐力削減 +3%／點（不吃節點倍率） | 地震耐力削減 +3%／點（不吃節點倍率） | ESSBElem2.QuakeStamina |
| earth | 關閉（地震） | 大師 | ×3：純百分比傷害主線（規劃 3） | 土印記的融斷再 +2%／點 | 土印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| earth | 關閉（地震） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 地震 +3%／點 | 地震 +9%／點 | src/ESSBElem.psc:SignatureMult |
| wind | 持續（連斬） | 新手 | ×3：純百分比傷害主線（規劃 3） | 風刃傷害 +2%／點 | 風刃傷害 +6%／點 | src/ESSBElem2.psc:WindBladeMult |
| wind | 持續（連斬） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 風附傷 +1%／點 | 風附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcAdept] |
| wind | 持續（連斬） | 專精 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 風形態移速再 +0.5%／點（+10% → +17.5%） | 風形態移速再 +0.5%／點（+10% → +17.5%） | ESSBElem2.WindSpeedBonus → ESSBController.RefreshWindAbilities |
| wind | 持續（連斬） | 大師 | ×3：純百分比傷害主線（規劃 3） | 同調每段風附傷 +1%／點 | 同調每段風附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcMaster] |
| wind | 持續（連斬） | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 千刃，同調三段時每次命中附帶風刃，機率 5%／點 | 千刃，同調三段時每次命中附帶風刃，機率 5%／點 | ESSBElem2.OnWindHit |
| wind | 開啟（風臨） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 開印風勢 +1／每 5 點 | 開印風勢 +1／每 5 點 | ESSBElem2.OpenStacks(5) |
| wind | 開啟（風臨） | 熟練 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 開印拉近距離 +0.1 公尺／點（1.5 → 3 公尺） | 開印拉近距離 +0.1 公尺／點（1.5 → 3 公尺） | ESSBElem2.PullDistance → ESSBController.PullIn |
| wind | 開啟（風臨） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 風印記持續 +0.2 秒／點 | 風印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kMarkDuration[element]） |
| wind | 開啟（風臨） | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 風臨，開風形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 風臨，開風形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| wind | 開啟（風臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | native/include/Status.h:kOpenEffect |
| wind | 關閉（吹飛） | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult；native/include/Status.h:kEndMain |
| wind | 關閉（吹飛） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 風印記的融斷 +2%／點 | 風印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| wind | 關閉（吹飛） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 多段觸發，風印記被切掉時接管元素的命中觸發次數 +1／每 5 點（2 → 最多 5） | 多段觸發，風印記被切掉時接管元素的命中觸發次數 +1／每 5 點（2 → 最多 5） | —（只有 perk 記錄；本輪不讀） |
| wind | 關閉（吹飛） | 大師 | ×3：純百分比傷害主線（規劃 3） | 風印記的融斷再 +2%／點 | 風印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| wind | 關閉（吹飛） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 落地傷害 +5%／點（×0.5 → ×1.25） | 落地傷害 +15%／點（×0.5 → ×2.75） | src/ESSBElem2.psc:LandingDamage |
| blood | 持續（血位） | 新手 | ×3：fix8 使用者核准：只縮放流血每層傷害，放血係數保持原值（v0.4 明寫） | 流血每層傷害 +2%／點，放血係數 +0.01%／點（0.3% → 0.45%，不吃節點倍率） | 流血每層傷害 +6%／點，放血係數 +0.01%／點（0.3% → 0.45%，不吃節點倍率） | native/include/Status.h:kBloodLayerDamage |
| blood | 持續（血位） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 血附傷 +1%／點 | 血附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcAdept] |
| blood | 持續（血位） | 專精 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 吸血比例各血位 +1%／點 | 吸血比例各血位 +1%／點 | DLL native/include/HitMath.h LeechRatio（node::kBloodLeechRatio）＋ESSBController.GetBloodLeechRatio |
| blood | 持續（血位） | 大師 | ×3：純百分比傷害主線（規劃 3） | 同調每段血附傷 +1%／點 | 同調每段血附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcMaster] |
| blood | 持續（血位） | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 血海，同調三段時血潮改為範圍，範圍 1 公尺 +0.2 公尺／點 | 血海，同調三段時血潮改為範圍，範圍 1 公尺 +0.2 公尺／點 | ESSBElem2.SurgeRadius → ESSBReactions.EndBlood |
| blood | 開啟（血臨） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 開印流血 +1 層／每 5 點 | 開印流血 +1 層／每 5 點 | DLL native/include/Status.h（node::kBloodOpenLayers） |
| blood | 開啟（血臨） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 開印後 5 秒內血附傷 +1%／點 | 開印後 5 秒內血附傷 +3%／點 | native/include/Status.h:kOpenProc |
| blood | 開啟（血臨） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 血印記持續 +0.2 秒／點 | 血印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kMarkDuration[element]） |
| blood | 開啟（血臨） | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 血臨，開血形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 血臨，開血形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| blood | 開啟（血臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | native/include/Status.h:kOpenEffect |
| blood | 關閉（血潮） | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult；native/include/Status.h:kEndMain |
| blood | 關閉（血潮） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 血印記的融斷 +2%／點 | 血印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| blood | 關閉（血潮） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 血潮治療倍率 ×2，每點 +0.1 | 血潮治療倍率 ×2，每點 +0.1 | ESSBElem2.SurgeHealMult |
| blood | 關閉（血潮） | 大師 | ×3：純百分比傷害主線（規劃 3） | 血印記的融斷再 +2%／點 | 血印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| blood | 關閉（血潮） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 血潮 +3%／點 | 血潮 +9%／點 | src/ESSBElem.psc:SignatureMult |
| divine | 持續（聖佑） | 新手 | ×3：純百分比傷害主線（規劃 3） | 聖佑各階武器傷害與聖傷加成 +1%／點 × 階數（I 1、II 2、III 3） | 聖佑各階武器傷害與聖傷加成 +3%／點 × 階數（I 1、II 2、III 3） | src/ESSBElem2.psc:HolyTierBonus；native/include/Status.h:kDivineHolyBonus；native/include/Status.h:kDivineHolyBonus |
| divine | 持續（聖佑） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 聖附傷 +1%／點 | 聖附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcAdept] |
| divine | 持續（聖佑） | 專精 | ×3：純百分比傷害主線（規劃 3） | 聖裁傷害 +2%／點 | 聖裁傷害 +6%／點 | native/include/Status.h:kDivineJudgeDamage |
| divine | 持續（聖佑） | 大師 | ×3：純百分比傷害主線（規劃 3） | 同調每段聖附傷 +1%／點 | 同調每段聖附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcMaster] |
| divine | 持續（聖佑） | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 天啟，同調三段時裁決改為範圍，範圍 1 公尺 +0.2 公尺／點 | 天啟，同調三段時裁決改為範圍，範圍 1 公尺 +0.2 公尺／點 | ESSBElem2.JudgeArea |
| divine | 開啟（聖臨） | 新手 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 開印回血 +5%／點 | 開印回血 +5%／點 | ESSBElem2.OpenDivine |
| divine | 開啟（聖臨） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 開印後 5 秒內聖附傷 +1%／點 | 開印後 5 秒內聖附傷 +3%／點 | native/include/Status.h:kOpenProc |
| divine | 開啟（聖臨） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 聖印記持續 +0.2 秒／點 | 聖印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kMarkDuration[element]） |
| divine | 開啟（聖臨） | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 聖臨，開聖形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 聖臨，開聖形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| divine | 開啟（聖臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | native/include/Status.h:kOpenEffect |
| divine | 關閉（裁決） | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult；native/include/Status.h:kEndMain |
| divine | 關閉（裁決） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 聖印記的融斷 +2%／點 | 聖印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| divine | 關閉（裁決） | 專精 | ×3：純百分比傷害主線（規劃 3） | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | native/include/Status.h:kTakeover |
| divine | 關閉（裁決） | 大師 | ×3：純百分比傷害主線（規劃 3） | 聖印記的融斷再 +2%／點 | 聖印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| divine | 關閉（裁決） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 裁決 +3%／點 | 裁決 +9%／點 | src/ESSBElem.psc:SignatureMult |
| poison | 持續（疫毒） | 新手 | ×3：純百分比傷害主線（規劃 3） | 每劑傷害 +2%／點 | 每劑傷害 +6%／點 | native/include/Status.h:kPoisonDoseDamage |
| poison | 持續（疫毒） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 毒附傷 +1%／點 | 毒附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcAdept] |
| poison | 持續（疫毒） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 瘴氣每秒傳遞劑量 +0.05／點（0.5 → 2.0，催毒中 1.0 → 3.5，可調） | 瘴氣每秒傳遞劑量 +0.05／點（0.5 → 2.0，催毒中 1.0 → 3.5，可調） | DLL native/include/Status.h rule::MiasmaDoses ＋ native/src/Plugin.cpp TargetSecond（node::kPoisonMiasmaRate） |
| poison | 持續（疫毒） | 大師 | ×3：純百分比傷害主線（規劃 3） | 同調每段毒附傷 +1%／點 | 同調每段毒附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcMaster] |
| poison | 持續（疫毒） | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 瘟疫，同調三段時中毒目標每秒自動擴散 1 劑到附近敵人，機率 5%／點 | 瘟疫，同調三段時中毒目標每秒自動擴散 1 劑到附近敵人，機率 5%／點 | DLL native/include/Status.h rule::PlagueChance ＋ native/src/Plugin.cpp TargetSecond（node::kPoisonPlague） |
| poison | 開啟（毒臨） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 開印劑數 +1／每 3 點（3 → 8） | 開印劑數 +1／每 3 點（3 → 8） | DLL native/include/Status.h（node::kPoisonOpenDoses） |
| poison | 開啟（毒臨） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 開印後 5 秒內毒附傷 +1%／點 | 開印後 5 秒內毒附傷 +3%／點 | native/include/Status.h:kOpenProc |
| poison | 開啟（毒臨） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 毒印記持續 +0.2 秒／點 | 毒印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kMarkDuration[element]） |
| poison | 開啟（毒臨） | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 毒臨，開毒形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 毒臨，開毒形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| poison | 開啟（毒臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | native/include/Status.h:kOpenEffect |
| poison | 關閉（催毒） | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult；native/include/Status.h:kEndMain |
| poison | 關閉（催毒） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 毒印記的融斷 +2%／點 | 毒印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| poison | 關閉（催毒） | 專精 | ×3：純百分比傷害主線（規劃 3） | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | native/include/Status.h:kTakeover |
| poison | 關閉（催毒） | 大師 | ×3：純百分比傷害主線（規劃 3） | 毒印記的融斷再 +2%／點 | 毒印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| poison | 關閉（催毒） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 催毒期間中毒傷害 +3%／點 | 催毒期間中毒傷害 +9%／點 | native/include/Status.h:kSignature |
| water | 持續（潮汐） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 浸濕持續 +0.3 秒／點（只延長浸濕本身，不影響水印記時長） | 浸濕持續 +0.3 秒／點（只延長浸濕本身，不影響水印記時長） | ESSBElem3.WetSeconds（Papyrus 浸濕）＋DLL 雨雪浸濕（固定時長法術 ESSB_Native_Soak_*，node::kWaterSoakDuration） |
| water | 持續（潮汐） | 熟練 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 長流每秒回復 +0.2%／點（2.0% → 5.0%；只加生命與耐力） | 長流每秒回復 +0.2%／點（2.0% → 5.0%；只加生命與耐力） | ESSBElem3.FlowPercent → WaterFormTick |
| water | 持續（潮汐） | 專精 | ×3：純百分比傷害主線（規劃 3） | 水壓每層水附傷 +1%／點 | 水壓每層水附傷 +3%／點 | native/include/Status.h:kWaterPressureDamage |
| water | 持續（潮汐） | 大師 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 同調每段長流回復 +0.05%／點 | 同調每段長流回復 +0.05%／點 | ESSBElem3.FlowPercent |
| water | 持續（潮汐） | 傳奇 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 長河，同調三段時長流再 +0.05%／點，且長流同時作用於附近同伴 | 長河，同調三段時長流再 +0.05%／點，且長流同時作用於附近同伴 | ESSBElem3.FlowPercent / WaterFormTick |
| water | 開啟（水臨） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 開印時回復生命與耐力各最大值 0.3%／點（15 點 4.5%） | 開印時回復生命與耐力各最大值 0.3%／點（15 點 4.5%） | ESSBElem3.OpenWater |
| water | 開啟（水臨） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 開印後 5 秒內水附傷 +1%／點 | 開印後 5 秒內水附傷 +3%／點 | native/include/Status.h:kOpenProc |
| water | 開啟（水臨） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 水印記持續 +0.2 秒／點 | 水印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kMarkDuration[element]） |
| water | 開啟（水臨） | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 水臨，開水形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 水臨，開水形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| water | 開啟（水臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | native/include/Status.h:kOpenEffect |
| water | 關閉（導引） | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult；native/include/Status.h:kEndMain |
| water | 關閉（導引） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 水印記的融斷 +2%／點 | 水印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| water | 關閉（導引） | 專精 | ×3：純百分比傷害主線（規劃 3） | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | native/include/Status.h:kTakeover |
| water | 關閉（導引） | 大師 | ×3：純百分比傷害主線（規劃 3） | 水印記的融斷再 +2%／點 | 水印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| water | 關閉（導引） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 導引 +3%／點 | 導引 +9%／點 | src/ESSBElem.psc:SignatureMult；native/include/Status.h:kSignature |
| darkness | 持續（侵蝕） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 詛咒每層抗性侵蝕 -0.2%／點（-2% → -5%） | 詛咒每層抗性侵蝕 -0.2%／點（-2% → -5%） | ESSBElem3.ApplyCurseErosion |
| darkness | 持續（侵蝕） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 暗附傷 +1%／點 | 暗附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcAdept] |
| darkness | 持續（侵蝕） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 幻覺持續 +0.1 秒／點（恐懼 2 → 3.5 秒、瘋狂 3 → 4.5 秒） | 幻覺持續 +0.1 秒／點（恐懼 2 → 3.5 秒、瘋狂 3 → 4.5 秒） | DLL native/include/Status.h（node::kDarkIllusionTime） |
| darkness | 持續（侵蝕） | 大師 | ×3：純百分比傷害主線（規劃 3） | 同調每段暗附傷 +1%／點 | 同調每段暗附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcMaster] |
| darkness | 持續（侵蝕） | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 深淵，同調三段時詛咒層上限 +1／每 3 點，滿層目標抗性可侵蝕到負值 | 深淵，同調三段時詛咒層上限 +1／每 3 點，滿層目標抗性可侵蝕到負值 | DLL native/include/Status.h（node::kDarkAbyss） |
| darkness | 開啟（咒縛） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 開印詛咒 +1 層／每 5 點 | 開印詛咒 +1 層／每 5 點 | DLL native/include/Status.h（node::kDarkOpenCurse） |
| darkness | 開啟（咒縛） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 開印後 5 秒內暗附傷 +1%／點 | 開印後 5 秒內暗附傷 +3%／點 | native/include/Status.h:kOpenProc |
| darkness | 開啟（咒縛） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 暗印記持續 +0.2 秒／點 | 暗印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kMarkDuration[element]） |
| darkness | 開啟（咒縛） | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 暗臨，開暗形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 暗臨，開暗形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| darkness | 開啟（咒縛） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | native/include/Status.h:kOpenEffect |
| darkness | 關閉（死咒） | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult；native/include/Status.h:kEndMain |
| darkness | 關閉（死咒） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 暗印記的融斷 +2%／點 | 暗印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| darkness | 關閉（死咒） | 專精 | ×3：純百分比傷害主線（規劃 3） | 死咒的「已損失生命」係數 +0.5%／點（15% → 22.5%） | 死咒的「已損失生命」係數 +1.5%／點（15% → 37.5%） | native/include/Status.h:kDarkCurseLost |
| darkness | 關閉（死咒） | 大師 | ×3：純百分比傷害主線（規劃 3） | 暗印記的融斷再 +2%／點 | 暗印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| darkness | 關閉（死咒） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 死咒 +3%／點 | 死咒 +9%／點 | src/ESSBElem.psc:SignatureMult；native/include/Status.h:kSignature |
| astral | 持續（共鳴） | 新手 | 不改：v0.4 明寫「不吃節點倍率」 | 回聲比例 +1%／點（25% → 40%，不吃節點倍率） | 回聲比例 +1%／點（25% → 40%，不吃節點倍率） | —（只有 perk 記錄；本輪不讀） |
| astral | 持續（共鳴） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 星附傷 +1%／點 | 星附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcAdept] |
| astral | 持續（共鳴） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 星痕層數上限 +1／每 5 點（也提高闇星每一擊） | 星痕層數上限 +1／每 5 點（也提高闇星每一擊） | DLL native/include/Status.h StarCap（node::kAstralCap） |
| astral | 持續（共鳴） | 大師 | ×3：純百分比傷害主線（規劃 3） | 同調每段星附傷 +1%／點 | 同調每段星附傷 +3%／點 | native/include/HitMath.h:NodeSum[kProcMaster] |
| astral | 持續（共鳴） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 永夜，闇星每一擊 +3%／點 | 永夜，闇星每一擊 +9%／點 | —（只有 perk 記錄；本輪不讀） |
| astral | 開啟（星臨） | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 星痕延遲 -0.1 秒／點（2 → 0.5 秒） | 星痕延遲 -0.1 秒／點（2 → 0.5 秒） | DLL native/include/Status.h rule::StarDelay（node::kAstralDelay） |
| astral | 開啟（星臨） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 開印後 5 秒內星附傷 +1%／點 | 開印後 5 秒內星附傷 +3%／點 | native/include/Status.h:kOpenProc |
| astral | 開啟（星臨） | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 星印記持續 +0.2 秒／點 | 星印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kMarkDuration[element]） |
| astral | 開啟（星臨） | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 星臨，開星形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 星臨，開星形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened ＋ ESSBElem3.AdventRadius |
| astral | 開啟（星臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | native/include/Status.h:kOpenEffect |
| astral | 關閉（星落） | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult；native/include/Status.h:kEndMain |
| astral | 關閉（星落） | 熟練 | ×3：純百分比傷害主線（規劃 3） | 星印記的融斷 +2%／點 | 星印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| astral | 關閉（星落） | 專精 | ×3：純百分比傷害主線（規劃 3） | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | native/include/Status.h:kTakeover |
| astral | 關閉（星落） | 大師 | ×3：純百分比傷害主線（規劃 3） | 星印記的融斷再 +2%／點 | 星印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| astral | 關閉（星落） | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 星落 +3%／點 | 星落 +9%／點 | src/ESSBElem.psc:SignatureMult |
| noform | 大師 | 新手 | 不改：v0.4 明寫「不吃節點倍率」 | 吸魔量 +5%／點（不吃節點倍率；×1.0 → ×1.75） | 吸魔量 +5%／點（不吃節點倍率；×1.0 → ×1.75） | DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormSiphonAmount） |
| noform | 大師 | 熟練 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 超載上限 +2%／點（+50% → +80%） | 超載上限 +2%／點（+50% → +80%） | —（只有 perk 記錄；本輪不讀） |
| noform | 大師 | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 法盾效率，每擋 1 點花的魔力 -2%／點（最多 -30%：1.0 → 0.7，超載 0.75 → 0.53） | 法盾效率，每擋 1 點花的魔力 -2%／點（最多 -30%：1.0 → 0.7，超載 0.75 → 0.53） | —（只有 perk 記錄；本輪不讀） |
| noform | 大師 | 大師 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 法盾分擔 +1%／點（30% → 45%；超載 45% → 60%） | 法盾分擔 +1%／點（30% → 45%；超載 45% → 60%） | —（只有 perk 記錄；本輪不讀） |
| noform | 大師 | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 不竭，超載衰減每秒 -0.2%／點（5% → 2%） | 不竭，超載衰減每秒 -0.2%／點（5% → 2%） | —（只有 perk 記錄；本輪不讀） |
| noform | 滅法 | 新手 | 不改：v0.4 明寫「不吃節點倍率」 | 滅法倍率 +2%／點（不吃節點倍率；×1.0 → ×1.3，超載 ×1.5 → ×1.8） | 滅法倍率 +2%／點（不吃節點倍率；×1.0 → ×1.3，超載 ×1.5 → ×1.8） | DLL native/include/HitMath.h DispelMultiplier（node::kNoFormDispelRate） |
| noform | 滅法 | 熟練 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 燒魔倍數 +7%／點（Y 最多是 X 的 1.0 → 2.05 倍） | 燒魔倍數 +7%／點（Y 最多是 X 的 1.0 → 2.05 倍） | DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormBurnMultiple） |
| noform | 滅法 | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 沉默 +0.2 秒／點（1 → 4 秒） | 沉默 +0.2 秒／點（1 → 4 秒） | DLL native/include/HitMath.h SilenceSeconds（node::kNoFormSilence） |
| noform | 滅法 | 大師 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 對施法者與帶魔法護盾、元素披風的敵人燒魔 +5%／點 | 對施法者與帶魔法護盾、元素披風的敵人燒魔 +5%／點 | DLL native/include/HitMath.h BurnBonus（node::kNoFormBurnCasters） |
| noform | 滅法 | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 目標魔力低於 25% 時命中傷害 +3%／點 | 目標魔力低於 25% 時命中傷害 +9%／點 | src/ESSBNoForm.psc:TrueMult |
| noform | 冷寂 | 新手 | ×3：純百分比傷害主線（規劃 3） | 融斷 +2%／點 | 融斷 +6%／點 | src/ESSBNoForm.psc:BurstMult |
| noform | 冷寂 | 熟練 | 不改：時間、機率、範圍、層數、回復、抗性、分擔或比例類（規劃 3 不吃節點倍率） | 寂每層燒魔 +0.5%／點（5% → 12.5%） | 寂每層燒魔 +0.5%／點（5% → 12.5%） | —（只有 perk 記錄；本輪不讀） |
| noform | 冷寂 | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 融斷範圍 +0.3 公尺／點 | 融斷範圍 +0.3 公尺／點 | ESSBNoForm.BurstRadius |
| noform | 冷寂 | 大師 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 寂上限 +1／每 5 點（5 → 8） | 寂上限 +1／每 5 點（5 → 8） | —（只有 perk 記錄；本輪不讀） |
| noform | 冷寂 | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 融斷再 +3%／點 | 融斷再 +9%／點 | src/ESSBNoForm.psc:BurstMult |
| common | 持續 | 新手 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 同調門檻 -2%／點 | 同調門檻 -2%／點 | ESSBNodes.SyncThresholdScale → ESSBController.SyncStage |
| common | 持續 | 熟練 | ×3：純百分比傷害主線（規劃 3） | 同調二段時附傷 +1%／點 | 同調二段時附傷 +3%／點 | src/ESSBNodes.psc:CommonHitMult |
| common | 持續 | 專精 | ×3：純百分比傷害主線（規劃 3） | 同調三段時終焉 +1%／點 | 同調三段時終焉 +3%／點 | src/ESSBNodes.psc:CommonEndMult；native/include/Status.h:kCommonSyncEnd |
| common | 持續 | 大師 | ×3：純百分比傷害主線（規劃 3） | 同調三段時重擊附傷 +2%／點 | 同調三段時重擊附傷 +6%／點 | src/ESSBNodes.psc:CommonHitMult |
| common | 持續 | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 化身，同調三段時 30 秒冷卻（-1 秒／點）完成後的下一次命中，自動觸發當前元素的持續傳奇效果；若該效果屬於被動數值（如絕對零度、深淵），化身改為讓你在接下來 10 秒內視同已取得該效果 | 化身，同調三段時 30 秒冷卻（-1 秒／點）完成後的下一次命中，自動觸發當前元素的持續傳奇效果；若該效果屬於被動數值（如絕對零度、深淵），化身改為讓你在接下來 10 秒內視同已取得該效果 | —（只有 perk 記錄；本輪不讀） |
| common | 開啟 | 新手 | ×3：純百分比傷害主線（規劃 3） | 所有元素附傷 +1%／點 | 所有元素附傷 +3%／點 | src/ESSBNodes.psc:CommonHitMult |
| common | 開啟 | 熟練 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 印記持續 +0.2 秒／點 | 印記持續 +0.2 秒／點 | DLL native/include/Status.h（node::kCommonMarkDuration） |
| common | 開啟 | 專精 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 開印時 +1 同調／每 5 點 | 開印時 +1 同調／每 5 點 | ESSBNodes.OpenSyncBonus |
| common | 開啟 | 大師 | ×3：純百分比傷害主線（規劃 3） | 所有元素附傷再 +1%／點 | 所有元素附傷再 +3%／點 | src/ESSBNodes.psc:CommonHitMult |
| common | 開啟 | 傳奇 | 不改：不是「+X%／點」的百分比主線（時長／層數／範圍／固定值／係數） | 每種元素狀態上限 +1 層／每 5 點（最多 +3） | 每種元素狀態上限 +1 層／每 5 點（最多 +3） | DLL native/include/Status.h（node::kCommonCapBonus） ＋ ESSBNodes.StatusCapBonus |
| common | 關閉 | 新手 | ×3：純百分比傷害主線（規劃 3） | 終焉 +1%／點 | 終焉 +3%／點 | src/ESSBNodes.psc:CommonEndMult；native/include/Status.h:kCommonEnd |
| common | 關閉 | 熟練 | ×3：純百分比傷害主線（規劃 3） | 融斷 +1%／點 | 融斷 +3%／點 | src/ESSBNodes.psc:CommonBurstMult |
| common | 關閉 | 專精 | ×3：純百分比傷害主線（規劃 3） | 切換後首次命中附帶前一元素附傷 +3%／點 | 切換後首次命中附帶前一元素附傷 +9%／點 | src/ESSBNodes.psc:EchoRatio |
| common | 關閉 | 大師 | ×3：純百分比傷害主線（規劃 3） | 終焉再 +1%／點 | 終焉再 +3%／點 | src/ESSBNodes.psc:CommonEndMult；native/include/Status.h:kCommonEndAgain |
| common | 關閉 | 傳奇 | ×3：純百分比傷害主線（規劃 3） | 融斷再 +2%／點 | 融斷再 +6%／點 | src/ESSBNodes.psc:CommonBurstMult |

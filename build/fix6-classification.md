# 195 主線完整分類（fix round 8 決策已結清）

| 樹 | 路線 | 階 | 分類／原因 | 原文 | 顯示文字 | 程式位置 |
|---|---|---|---|---|---|---|
| fire | 持續（烈焰） | 新手 | ×3：純百分比傷害／傷害係數 | 熱度每層火附傷 +0.2%／點（8% → 11%） | 熱度每層火附傷 +0.6%／點（8% → 17%） | src\ESSBElem.psc:FireHitMult |
| fire | 持續（烈焰） | 熟練 | ×3：純百分比傷害／傷害係數 | 火附傷 +1%／點 | 火附傷 +3%／點 | src\ESSBElem.psc:FireHitMult |
| fire | 持續（烈焰） | 專精 | 不改：減抗／削甲 | 帶熱度目標火抗 -1%／點 | 帶熱度目標火抗 -1%／點 | ESSBElem.ApplyFireResistShred |
| fire | 持續（烈焰） | 大師 | ×3：純百分比傷害／傷害係數 | 同調每段火附傷 +1%／點 | 同調每段火附傷 +3%／點 | src\ESSBElem.psc:FireHitMult |
| fire | 持續（烈焰） | 傳奇 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 業火：同調三段時自燃倍率 +0.1／點（×2 → ×3.5） | 業火：同調三段時自燃倍率 +0.1／點（×2 → ×3.5） | ESSBElem.IgniteMult |
| fire | 開啟（焰起） | 新手 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 開印熱度 +1／每 5 點 | 開印熱度 +1／每 5 點 | ESSBElem.OpenStacks |
| fire | 開啟（焰起） | 熟練 | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內火附傷 +1%／點 | 開印後 5 秒內火附傷 +3%／點 | src\ESSBElem.psc:FireHitMult |
| fire | 開啟（焰起） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 火印記持續 +0.2 秒／點 | 火印記持續 +0.2 秒／點 | ESSBElem.MarkDurationBonus → ESSBController.ApplyMark |
| fire | 開啟（焰起） | 大師 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 火臨：開火形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 火臨：開火形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened → ESSBController.ForceOpenOn |
| fire | 開啟（焰起） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | src/ESSBElem.psc:OpenMult |
| fire | 關閉（爆燃） | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult |
| fire | 關閉（爆燃） | 熟練 | ×3：純百分比傷害／傷害係數 | 火印記的融斷 +2%／點 | 火印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| fire | 關閉（爆燃） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 爆燃每層熱度倍率 +0.01／點（0.2 → 0.35） | 爆燃每層熱度倍率 +0.01／點（0.2 → 0.35） | ESSBElem.DetonatePerLayer |
| fire | 關閉（爆燃） | 大師 | ×3：純百分比傷害／傷害係數 | 火印記的融斷再 +2%／點 | 火印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| fire | 關閉（爆燃） | 傳奇 | ×3：純百分比傷害／傷害係數 | 爆燃 +3%／點 | 爆燃 +9%／點 | src/ESSBElem.psc:SignatureMult |
| frost | 持續（凍結） | 新手 | 不改：移動／控制／防禦／門檻 | 每次命中凍結累積 +5%／點 | 每次命中凍結累積 +5%／點 | ESSBElem.HitStacks |
| frost | 持續（凍結） | 熟練 | ×3：純百分比傷害／傷害係數 | 冰附傷 +1%／點 | 冰附傷 +3%／點 | src\ESSBElem.psc:FrostHitMult |
| frost | 持續（凍結） | 專精 | ×3：純百分比傷害／傷害係數 | 冰封目標受冰附傷 +2%／點 | 冰封目標受冰附傷 +6%／點 | src\ESSBElem.psc:FrostHitMult |
| frost | 持續（凍結） | 大師 | ×3：純百分比傷害／傷害係數 | 同調每段冰附傷 +1%／點 | 同調每段冰附傷 +3%／點 | src\ESSBElem.psc:FrostHitMult |
| frost | 持續（凍結） | 傳奇 | 不改：移動／控制／防禦／門檻 | 絕對零度：同調三段時冰封減速再 -2%／點（自有強減速，非麻痺），可影響首領 | 絕對零度：同調三段時冰封減速再 -2%／點（自有強減速，非麻痺），可影響首領 | ESSBElem.OnFrozenTick |
| frost | 開啟（冰臨） | 新手 | 第2／2b項指定：第 2／2b 項指定數值 | 開印凍結 +1／每 3 點 | 開印凍結 +1／每 3 點（霜結基礎減速 25%，持續 3 秒；總減速上限 70%） | ESSBElem.OpenStacks |
| frost | 開啟（冰臨） | 熟練 | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內冰附傷 +1%／點 | 開印後 5 秒內冰附傷 +3%／點 | src\ESSBElem.psc:FrostHitMult |
| frost | 開啟（冰臨） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 冰印記持續 +0.2 秒／點 | 冰印記持續 +0.2 秒／點 | ESSBElem.MarkDurationBonus |
| frost | 開啟（冰臨） | 大師 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 冰臨：開冰形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 冰臨：開冰形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| frost | 開啟（冰臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | src/ESSBElem.psc:OpenMult |
| frost | 關閉（碎冰） | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult |
| frost | 關閉（碎冰） | 熟練 | ×3：純百分比傷害／傷害係數 | 冰印記的融斷 +2%／點 | 冰印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| frost | 關閉（碎冰） | 專精 | ×3：純百分比傷害／傷害係數 | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | src/ESSBElem.psc:OnEnd |
| frost | 關閉（碎冰） | 大師 | ×3：純百分比傷害／傷害係數 | 冰印記的融斷再 +2%／點 | 冰印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| frost | 關閉（碎冰） | 傳奇 | ×3：純百分比傷害／傷害係數 | 碎冰 +3%／點 | 碎冰 +9%／點 | src/ESSBElem.psc:SignatureMult |
| lightning | 持續（充能） | 新手 | ×3：純百分比傷害／傷害係數 | 放電每格電荷傷害 +1%／點 | 放電每格電荷傷害 +3%／點 | src\ESSBElem.psc:Discharge |
| lightning | 持續（充能） | 熟練 | ×3：純百分比傷害／傷害係數 | 雷附傷 +1%／點 | 雷附傷 +3%／點 | src\ESSBElem.psc:ShockHitMult |
| lightning | 持續（充能） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 電荷上限 +1／每 3 點 | 電荷上限 +1／每 3 點 | ESSBElem.ChargeCap → ESSBController.AddSelf |
| lightning | 持續（充能） | 大師 | ×3：純百分比傷害／傷害係數 | 同調每段雷附傷 +1%／點 | 同調每段雷附傷 +3%／點 | src\ESSBElem.psc:ShockHitMult |
| lightning | 持續（充能） | 傳奇 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 天雷：同調三段時放電改為對範圍內所有感電目標，範圍 2 公尺 +0.2 公尺／點 | 天雷：同調三段時放電改為對範圍內所有感電目標，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.DischargeAll |
| lightning | 開啟（雷臨） | 新手 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 開印電荷 +1／每 5 點 | 開印電荷 +1／每 5 點 | ESSBElem.OpenStacks |
| lightning | 開啟（雷臨） | 熟練 | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內雷附傷 +1%／點 | 開印後 5 秒內雷附傷 +3%／點 | src\ESSBElem.psc:ShockHitMult |
| lightning | 開啟（雷臨） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 雷印記持續 +0.2 秒／點 | 雷印記持續 +0.2 秒／點 | ESSBElem.MarkDurationBonus |
| lightning | 開啟（雷臨） | 大師 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 雷臨：開雷形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 雷臨：開雷形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| lightning | 開啟（雷臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | src/ESSBElem.psc:OpenMult |
| lightning | 關閉（放電） | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult |
| lightning | 關閉（放電） | 熟練 | ×3：純百分比傷害／傷害係數 | 雷印記的融斷 +2%／點 | 雷印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| lightning | 關閉（放電） | 專精 | ×3：純百分比傷害／傷害係數 | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | src/ESSBElem.psc:OnEnd |
| lightning | 關閉（放電） | 大師 | ×3：純百分比傷害／傷害係數 | 雷印記的融斷再 +2%／點 | 雷印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| lightning | 關閉（放電） | 傳奇 | ×3：純百分比傷害／傷害係數 | 放電 +3%／點 | 放電 +9%／點 | src/ESSBElem.psc:SignatureMult |
| earth | 持續（裂甲） | 新手 | 不改：減抗／削甲 | 裂痕護甲削減 +2／點（-30 → -60） | 裂痕護甲削減 +2／點（-30 → -60） | ESSBElem2.FissureArmor → ESSBReactions.Open(4) |
| earth | 持續（裂甲） | 熟練 | ×3：純百分比傷害／傷害係數 | 土附傷 +1%／點 | 土附傷 +3%／點 | src\ESSBElem2.psc:EarthHitMult |
| earth | 持續（裂甲） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 命中削減目標耐力 +0.5／點 | 命中削減目標耐力 +0.5／點 | ESSBElem2.OnEarthHit |
| earth | 持續（裂甲） | 大師 | ×3：純百分比傷害／傷害係數 | 同調每段土附傷 +1%／點 | 同調每段土附傷 +3%／點 | src\ESSBElem2.psc:EarthHitMult |
| earth | 持續（裂甲） | 傳奇 | 不改：機率 | 地動：同調三段時重擊對耐力低於 30% 的目標跌倒，機率 5%／點 | 地動：同調三段時重擊對耐力低於 30% 的目標跌倒，機率 5%／點 | ESSBElem2.OnEarthHit → ESSBController.Knockdown |
| earth | 開啟（地臨） | 新手 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 開印岩甲 +1／每 5 點 | 開印岩甲 +1／每 5 點 | ESSBElem2.OpenStacks(4) |
| earth | 開啟（地臨） | 熟練 | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內土附傷 +1%／點 | 開印後 5 秒內土附傷 +3%／點 | src\ESSBElem2.psc:EarthHitMult |
| earth | 開啟（地臨） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 土印記持續 +0.2 秒／點 | 土印記持續 +0.2 秒／點 | ESSBElem.MarkDurationBonus → ESSBController.ApplyMark |
| earth | 開啟（地臨） | 大師 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 地臨：開土形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 地臨：開土形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened → ESSBController.ForceOpenOn |
| earth | 開啟（地臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | src/ESSBElem.psc:OpenMult |
| earth | 關閉（地震） | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult |
| earth | 關閉（地震） | 熟練 | ×3：純百分比傷害／傷害係數 | 土印記的融斷 +2%／點 | 土印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| earth | 關閉（地震） | 專精 | 不改：fix8 使用者核准：削耐保持 +3%／點；交由 ESSB_MultDrain | 地震耐力削減 +3%／點 | 地震耐力削減 +3%／點 | ESSBElem2.QuakeStamina |
| earth | 關閉（地震） | 大師 | ×3：純百分比傷害／傷害係數 | 土印記的融斷再 +2%／點 | 土印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| earth | 關閉（地震） | 傳奇 | ×3：純百分比傷害／傷害係數 | 地震 +3%／點 | 地震 +9%／點 | src/ESSBElem.psc:SignatureMult |
| wind | 持續（連斬） | 新手 | ×3：純百分比傷害／傷害係數 | 風刃傷害 +2%／點 | 風刃傷害 +6%／點 | src\ESSBElem2.psc:WindBladeMult |
| wind | 持續（連斬） | 熟練 | ×3：純百分比傷害／傷害係數 | 風附傷 +1%／點 | 風附傷 +3%／點 | src\ESSBElem2.psc:WindHitMult |
| wind | 持續（連斬） | 專精 | 不改：移動／控制／防禦／門檻 | 風形態移速再 +0.5%／點（+10% → +17.5%） | 風形態移速再 +0.5%／點（+10% → +17.5%） | ESSBElem2.WindSpeedBonus → ESSBController.RefreshWindAbilities |
| wind | 持續（連斬） | 大師 | ×3：純百分比傷害／傷害係數 | 同調每段風附傷 +1%／點 | 同調每段風附傷 +3%／點 | src\ESSBElem2.psc:WindHitMult |
| wind | 持續（連斬） | 傳奇 | 不改：機率 | 千刃：同調三段時每次命中附帶風刃，機率 5%／點 | 千刃：同調三段時每次命中附帶風刃，機率 5%／點 | ESSBElem2.OnWindHit |
| wind | 開啟（風臨） | 新手 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 開印風勢 +1／每 5 點 | 開印風勢 +1／每 5 點 | ESSBElem2.OpenStacks(5) |
| wind | 開啟（風臨） | 熟練 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 開印拉近距離 +0.1 公尺／點（1.5 → 3 公尺） | 開印拉近距離 +0.1 公尺／點（1.5 → 3 公尺） | ESSBElem2.PullDistance → ESSBController.PullIn |
| wind | 開啟（風臨） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 風印記持續 +0.2 秒／點 | 風印記持續 +0.2 秒／點 | ESSBElem.MarkDurationBonus |
| wind | 開啟（風臨） | 大師 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 風臨：開風形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 風臨：開風形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| wind | 開啟（風臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | src/ESSBElem.psc:OpenMult |
| wind | 關閉（吹飛） | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult |
| wind | 關閉（吹飛） | 熟練 | ×3：純百分比傷害／傷害係數 | 風印記的融斷 +2%／點 | 風印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| wind | 關閉（吹飛） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 吹飛距離 +0.2 公尺／點（3 → 6 公尺） | 吹飛距離 +0.2 公尺／點（3 → 6 公尺） | ESSBElem2.BlowDistance |
| wind | 關閉（吹飛） | 大師 | ×3：純百分比傷害／傷害係數 | 風印記的融斷再 +2%／點 | 風印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| wind | 關閉（吹飛） | 傳奇 | ×3：純百分比傷害／傷害係數 | 落地傷害 +5%／點（×0.5 → ×1.25） | 落地傷害 +15%／點（×0.5 → ×2.75） | src\ESSBElem2.psc:LandingDamage |
| blood | 持續（血位） | 新手 | ×3：fix8 使用者核准：只縮放流血每層傷害，放血係數保持原值 | 流血每層傷害 +2%／點，放血係數 +0.01%／點（0.3% → 0.45%） | 流血每層傷害 +6%／點，放血係數 +0.01%／點（0.3% → 0.45%） | src\ESSBElem2.psc:BleedTickMult |
| blood | 持續（血位） | 熟練 | ×3：純百分比傷害／傷害係數 | 血附傷 +1%／點 | 血附傷 +3%／點 | src\ESSBElem2.psc:BloodHitMult |
| blood | 持續（血位） | 專精 | 不改：治療／回復 | 吸血比例各血位 +1%／點 | 吸血比例各血位 +1%／點 | ESSBController.GetBloodLeechRatio |
| blood | 持續（血位） | 大師 | ×3：純百分比傷害／傷害係數 | 同調每段血附傷 +1%／點 | 同調每段血附傷 +3%／點 | src\ESSBElem2.psc:BloodHitMult |
| blood | 持續（血位） | 傳奇 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 血海：同調三段時血潮改為範圍，範圍 1 公尺 +0.2 公尺／點 | 血海：同調三段時血潮改為範圍，範圍 1 公尺 +0.2 公尺／點 | ESSBElem2.SurgeRadius → ESSBReactions.EndBlood |
| blood | 開啟（血臨） | 新手 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 開印流血 +1 層／每 5 點 | 開印流血 +1 層／每 5 點 | ESSBElem2.OpenStacks(6) |
| blood | 開啟（血臨） | 熟練 | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內血附傷 +1%／點 | 開印後 5 秒內血附傷 +3%／點 | src\ESSBElem2.psc:BloodHitMult |
| blood | 開啟（血臨） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 血印記持續 +0.2 秒／點 | 血印記持續 +0.2 秒／點 | ESSBElem.MarkDurationBonus |
| blood | 開啟（血臨） | 大師 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 血臨：開血形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 血臨：開血形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| blood | 開啟（血臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | src/ESSBElem.psc:OpenMult |
| blood | 關閉（血潮） | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult |
| blood | 關閉（血潮） | 熟練 | ×3：純百分比傷害／傷害係數 | 血印記的融斷 +2%／點 | 血印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| blood | 關閉（血潮） | 專精 | 不改：治療／回復 | 血潮治療倍率 ×2 → 每點 +0.1 | 血潮治療倍率 ×2 → 每點 +0.1 | ESSBElem2.SurgeHealMult |
| blood | 關閉（血潮） | 大師 | ×3：純百分比傷害／傷害係數 | 血印記的融斷再 +2%／點 | 血印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| blood | 關閉（血潮） | 傳奇 | ×3：純百分比傷害／傷害係數 | 血潮 +3%／點 | 血潮 +9%／點 | src/ESSBElem.psc:SignatureMult |
| divine | 持續（審判） | 新手 | ×3：純百分比傷害／傷害係數 | 聖印每層目標受聖傷 +1%／點 | 聖印每層目標受聖傷 +3%／點 | src\ESSBElem2.psc:HolyVulnerability |
| divine | 持續（審判） | 熟練 | ×3：純百分比傷害／傷害係數 | 聖附傷 +1%／點 | 聖附傷 +3%／點 | src\ESSBElem2.psc:DivineHitMult |
| divine | 持續（審判） | 專精 | 不改：治療／回復 | 命中回血 +2%／點 | 命中回血 +2%／點 | ESSBElem2.OnDivineHit |
| divine | 持續（審判） | 大師 | ×3：純百分比傷害／傷害係數 | 同調每段聖附傷 +1%／點 | 同調每段聖附傷 +3%／點 | src\ESSBElem2.psc:DivineHitMult |
| divine | 持續（審判） | 傳奇 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 天啟：同調三段時裁決改為範圍，範圍 1 公尺 +0.2 公尺／點 | 天啟：同調三段時裁決改為範圍，範圍 1 公尺 +0.2 公尺／點 | ESSBElem2.JudgeArea |
| divine | 開啟（聖臨） | 新手 | 不改：治療／回復 | 開印回血 +5%／點 | 開印回血 +5%／點 | ESSBElem2.OpenDivine |
| divine | 開啟（聖臨） | 熟練 | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內聖附傷 +1%／點 | 開印後 5 秒內聖附傷 +3%／點 | src\ESSBElem2.psc:DivineHitMult |
| divine | 開啟（聖臨） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 聖印記持續 +0.2 秒／點 | 聖印記持續 +0.2 秒／點 | ESSBElem.MarkDurationBonus |
| divine | 開啟（聖臨） | 大師 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 聖臨：開聖形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 聖臨：開聖形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| divine | 開啟（聖臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | src/ESSBElem.psc:OpenMult |
| divine | 關閉（裁決） | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult |
| divine | 關閉（裁決） | 熟練 | ×3：純百分比傷害／傷害係數 | 聖印記的融斷 +2%／點 | 聖印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| divine | 關閉（裁決） | 專精 | ×3：純百分比傷害／傷害係數 | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | src/ESSBElem.psc:OnEnd |
| divine | 關閉（裁決） | 大師 | ×3：純百分比傷害／傷害係數 | 聖印記的融斷再 +2%／點 | 聖印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| divine | 關閉（裁決） | 傳奇 | ×3：純百分比傷害／傷害係數 | 裁決 +3%／點 | 裁決 +9%／點 | src/ESSBElem.psc:SignatureMult |
| poison | 持續（疫毒） | 新手 | ×3：純百分比傷害／傷害係數 | 毒層每層傷害 +2%／點 | 毒層每層傷害 +6%／點 | src\ESSBElem3.psc:PoisonTickMult |
| poison | 持續（疫毒） | 熟練 | ×3：純百分比傷害／傷害係數 | 毒附傷 +1%／點 | 毒附傷 +3%／點 | src\ESSBElem3.psc:PoisonHitMult |
| poison | 持續（疫毒） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 基礎擴散間隔 -0.1 秒／點（2 → 0.5 秒） | 基礎擴散間隔 -0.1 秒／點（2 → 0.5 秒） | ESSBElem3.SpreadInterval / SpreadTargets → ESSBStatus.Tick |
| poison | 持續（疫毒） | 大師 | ×3：純百分比傷害／傷害係數 | 同調每段毒附傷 +1%／點 | 同調每段毒附傷 +3%／點 | src\ESSBElem3.psc:PoisonHitMult |
| poison | 持續（疫毒） | 傳奇 | 不改：機率 | 瘟疫：同調三段時毒層每秒自動擴散到附近敵人，機率 5%／點 | 瘟疫：同調三段時毒層每秒自動擴散到附近敵人，機率 5%／點 | ESSBElem3.PoisonTickHook ← ESSBStatus.Tick |
| poison | 開啟（毒臨） | 新手 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 開印毒層 +1／每 3 點 | 開印毒層 +1／每 3 點 | ESSBElem3.OpenStacks → ESSBReactions.Open |
| poison | 開啟（毒臨） | 熟練 | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內毒附傷 +1%／點 | 開印後 5 秒內毒附傷 +3%／點 | src\ESSBElem3.psc:PoisonHitMult |
| poison | 開啟（毒臨） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 毒印記持續 +0.2 秒／點 | 毒印記持續 +0.2 秒／點 | ESSBElem.MarkDurationBonus |
| poison | 開啟（毒臨） | 大師 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 毒臨：開毒形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 毒臨：開毒形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| poison | 開啟（毒臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | src/ESSBElem.psc:OpenMult |
| poison | 關閉（催毒） | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult |
| poison | 關閉（催毒） | 熟練 | ×3：純百分比傷害／傷害係數 | 毒印記的融斷 +2%／點 | 毒印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| poison | 關閉（催毒） | 專精 | ×3：純百分比傷害／傷害係數 | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | src/ESSBElem.psc:OnEnd |
| poison | 關閉（催毒） | 大師 | ×3：純百分比傷害／傷害係數 | 毒印記的融斷再 +2%／點 | 毒印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| poison | 關閉（催毒） | 傳奇 | ×3：純百分比傷害／傷害係數 | 催毒期間毒層傷害 +3%／點 | 催毒期間毒層傷害 +9%／點 | src\ESSBElem3.psc:PoisonTickMult |
| water | 持續（潮汐） | 新手 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 浸濕持續 +0.3 秒／點 | 浸濕持續 +0.3 秒／點 | ESSBElem3.WetSeconds → ESSBStatus.Tick |
| water | 持續（潮汐） | 熟練 | 第2／2b項指定：第 2／2b 項指定數值 | 長流每秒回復 +0.02%／點（0.3% → 0.6%） | 長流每秒回復 +0.2%／點（2.0% → 5.0%） | ESSBElem3.FlowPercent → WaterFormTick |
| water | 持續（潮汐） | 專精 | ×3：純百分比傷害／傷害係數 | 水壓每層水附傷 +1%／點 | 水壓每層水附傷 +3%／點 | src\ESSBElem3.psc:WaterHitMult |
| water | 持續（潮汐） | 大師 | 不改：治療／回復 | 同調每段長流回復 +0.05%／點 | 同調每段長流回復 +0.05%／點 | ESSBElem3.FlowPercent |
| water | 持續（潮汐） | 傳奇 | 不改：治療／回復 | 長河：同調三段時長流再 +0.05%／點，且長流同時作用於附近同伴 | 長河：同調三段時長流再 +0.05%／點，且長流同時作用於附近同伴 | ESSBElem3.FlowPercent / WaterFormTick |
| water | 開啟（水臨） | 新手 | 第2／2b項指定：第 2／2b 項指定數值 | 浸濕減速 +1%／點 | 浸濕減速 +1%／點（15% → 30%；本模組總減速上限 70%） | ESSBElem3.WetSlow → ESSBReactions.Open |
| water | 開啟（水臨） | 熟練 | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內水附傷 +1%／點 | 開印後 5 秒內水附傷 +3%／點 | src\ESSBElem3.psc:WaterHitMult |
| water | 開啟（水臨） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 水印記持續 +0.2 秒／點 | 水印記持續 +0.2 秒／點 | ESSBElem.MarkDurationBonus |
| water | 開啟（水臨） | 大師 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 水臨：開水形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 水臨：開水形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| water | 開啟（水臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | src/ESSBElem.psc:OpenMult |
| water | 關閉（導引） | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult |
| water | 關閉（導引） | 熟練 | ×3：純百分比傷害／傷害係數 | 水印記的融斷 +2%／點 | 水印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| water | 關閉（導引） | 專精 | ×3：純百分比傷害／傷害係數 | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | src/ESSBElem.psc:OnEnd |
| water | 關閉（導引） | 大師 | ×3：純百分比傷害／傷害係數 | 水印記的融斷再 +2%／點 | 水印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| water | 關閉（導引） | 傳奇 | ×3：純百分比傷害／傷害係數 | 導引 +3%／點 | 導引 +9%／點 | src/ESSBElem.psc:SignatureMult |
| darkness | 持續（侵蝕） | 新手 | 不改：減抗／削甲 | 詛咒每層抗性侵蝕 -0.2%／點（-2% → -5%） | 詛咒每層抗性侵蝕 -0.2%／點（-2% → -5%） | ESSBElem3.ApplyCurseErosion |
| darkness | 持續（侵蝕） | 熟練 | ×3：純百分比傷害／傷害係數 | 暗附傷 +1%／點 | 暗附傷 +3%／點 | src\ESSBElem3.psc:DarkHitMult |
| darkness | 持續（侵蝕） | 專精 | ×3：純百分比傷害／傷害係數 | 詛咒滿層目標受所有傷害 +1%／點 | 詛咒滿層目標受所有傷害 +3%／點 | src/ESSBElem3.psc:TargetDamageMult |
| darkness | 持續（侵蝕） | 大師 | ×3：純百分比傷害／傷害係數 | 同調每段暗附傷 +1%／點 | 同調每段暗附傷 +3%／點 | src\ESSBElem3.psc:DarkHitMult |
| darkness | 持續（侵蝕） | 傳奇 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 深淵：同調三段時詛咒層上限 +1／每 3 點，滿層目標抗性可侵蝕到負值 | 深淵：同調三段時詛咒層上限 +1／每 3 點，滿層目標抗性可侵蝕到負值 | ESSBElem3.CurseCap → ESSBController.StackCap |
| darkness | 開啟（咒縛） | 新手 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 開印詛咒 +1 層／每 5 點 | 開印詛咒 +1 層／每 5 點 | ESSBElem3.OpenStacks → ESSBReactions.Open |
| darkness | 開啟（咒縛） | 熟練 | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內暗附傷 +1%／點 | 開印後 5 秒內暗附傷 +3%／點 | src\ESSBElem3.psc:DarkHitMult |
| darkness | 開啟（咒縛） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 暗印記持續 +0.2 秒／點 | 暗印記持續 +0.2 秒／點 | ESSBElem.MarkDurationBonus |
| darkness | 開啟（咒縛） | 大師 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 暗臨：開暗形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | 暗臨：開暗形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | ESSBElem.OnFormOpened |
| darkness | 開啟（咒縛） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | src/ESSBElem.psc:OpenMult |
| darkness | 關閉（死咒） | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult |
| darkness | 關閉（死咒） | 熟練 | ×3：純百分比傷害／傷害係數 | 暗印記的融斷 +2%／點 | 暗印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| darkness | 關閉（死咒） | 專精 | ×3：純百分比傷害／傷害係數 | 死咒的「已損失生命」係數 +0.5%／點（15% → 22.5%） | 死咒的「已損失生命」係數 +1.5%／點（15% → 37.5%） | src\ESSBElem3.psc:DeathCurseLostRatio |
| darkness | 關閉（死咒） | 大師 | ×3：純百分比傷害／傷害係數 | 暗印記的融斷再 +2%／點 | 暗印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| darkness | 關閉（死咒） | 傳奇 | ×3：純百分比傷害／傷害係數 | 死咒 +3%／點 | 死咒 +9%／點 | src/ESSBElem.psc:SignatureMult |
| astral | 持續（星落） | 新手 | ×3：純百分比傷害／傷害係數 | 星痕延遲傷害 +2%／點 | 星痕延遲傷害 +6%／點 | src\ESSBElem3.psc:AstralTickMult |
| astral | 持續（星落） | 熟練 | ×3：純百分比傷害／傷害係數 | 星附傷 +1%／點 | 星附傷 +3%／點 | src\ESSBElem3.psc:AstralHitMult |
| astral | 持續（星落） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 星痕層數上限 +1／每 5 點 | 星痕層數上限 +1／每 5 點 | ESSBElem3.AstralCap → ESSBController.StackCap |
| astral | 持續（星落） | 大師 | ×3：純百分比傷害／傷害係數 | 同調每段星附傷 +1%／點 | 同調每段星附傷 +3%／點 | src\ESSBElem3.psc:AstralHitMult |
| astral | 持續（星落） | 傳奇 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 群星：同調三段時星落連鎖附近星痕目標，範圍 1 公尺 +1 公尺／點（滿點 16 公尺） | 群星：同調三段時星落連鎖附近星痕目標，範圍 1 公尺 +1 公尺／點（滿點 16 公尺） | ESSBElem3.FallChain / ConstellationRadius |
| astral | 開啟（星臨） | 新手 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 星痕延遲 -0.1 秒／點 | 星痕延遲 -0.1 秒／點 | ESSBElem3.AstralDelay → ESSBStatus.Tick |
| astral | 開啟（星臨） | 熟練 | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內星附傷 +1%／點 | 開印後 5 秒內星附傷 +3%／點 | src\ESSBElem3.psc:AstralHitMult |
| astral | 開啟（星臨） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 星印記持續 +0.2 秒／點 | 星印記持續 +0.2 秒／點 | ESSBElem.MarkDurationBonus |
| astral | 開啟（星臨） | 大師 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 星臨：開星形態時對範圍內敵人各開印一次，範圍 2 公尺 +1 公尺／點（滿點 17 公尺） | 星臨：開星形態時對範圍內敵人各開印一次，範圍 2 公尺 +1 公尺／點（滿點 17 公尺） | ESSBElem.OnFormOpened → ESSBElem3.AdventRadius |
| astral | 開啟（星臨） | 傳奇 | ×3：fix8 使用者核准：開印效果整體套用 ESSB_NodeScale | 開印效果 +3%／點 | 開印效果 +9%／點 | src/ESSBElem.psc:OpenMult |
| astral | 關閉（星落） | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult |
| astral | 關閉（星落） | 熟練 | ×3：純百分比傷害／傷害係數 | 星印記的融斷 +2%／點 | 星印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult |
| astral | 關閉（星落） | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 星落與星域的範圍 +0.8 公尺／點（3 → 15 公尺；星落需「流星雨」才有範圍） | 星落與星域的範圍 +0.8 公尺／點（3 → 15 公尺；星落需「流星雨」才有範圍） | ESSBElem3.FallRadius |
| astral | 關閉（星落） | 大師 | ×3：純百分比傷害／傷害係數 | 星印記的融斷再 +2%／點 | 星印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult |
| astral | 關閉（星落） | 傳奇 | ×3：純百分比傷害／傷害係數 | 星落 +3%／點 | 星落 +9%／點 | src/ESSBElem.psc:SignatureMult |
| noform | 純武藝 | 新手 | ×3：純百分比傷害／傷害係數 | 無形態時武器傷害 +1%／點 | 無形態時武器傷害 +3%／點 | src/ESSBNodes.psc:RefreshWeaponPercent |
| noform | 純武藝 | 熟練 | 不改：減抗／削甲 | 重擊碎甲：自有減防 1%／點，5 秒 | 重擊碎甲：自有減防 1%／點，5 秒 | ESSBNoForm.OnMartialHit |
| noform | 純武藝 | 專精 | 不改：機率 | 無形態時暴擊率 +1%／點（自有判定） | 無形態時暴擊率 +1%／點（自有判定） | ESSBNoForm.OnMartialHit |
| noform | 純武藝 | 大師 | ×3：純百分比傷害／傷害係數 | 戰意：每層武器傷害 +0.5%／點 | 戰意：每層武器傷害 +1.5%／點 | src/ESSBNodes.psc:RefreshWeaponPercent |
| noform | 純武藝 | 傳奇 | ×3：fix8 使用者核准：終結真傷係數套用 ESSB_NodeScale | 終結：戰意滿層重擊無視護甲 +3%／點 | 終結：戰意滿層重擊無視護甲 +9%／點 | src\ESSBNoForm.psc:OnMartialHit |
| noform | 破魔 | 新手 | 第2／2b項指定：第 2／2b 項指定數值 | 破魔：命中削減目標魔力 5（+1／點），回復你等量魔力，造成削減量 ×0.5 的真實傷害（無視護甲與所有抗性），並施加「破魔印」8 秒 | 破魔：命中削減目標魔力（20 + 4／點）× G(L_無元素)，回復你實際削減的等量魔力，造成實際削減量 ×0.5 的真實傷害（此路徑不重複乘 G），並施加「破魔印」8 秒 | ESSBNoForm.OnManaBreak |
| noform | 破魔 | 熟練 | 不改：第 2 項明定比例／對施法者 +5% 不變 | 真實傷害比例 +3%／點（0.5 → 0.95） | 真實傷害比例 +3%／點（0.5 → 0.95） | ESSBNoForm.OnManaBreak |
| noform | 破魔 | 專精 | 不改：治療／回復 | 沉默：目標魔力被削至 0 時施加沉默 1 秒（+0.2 秒／點，最長 4 秒）；沉默中無法施法、不回復魔力 | 沉默：目標魔力被削至 0 時施加沉默 1 秒（+0.2 秒／點，最長 4 秒）；沉默中無法施法、不回復魔力 | ESSBNoForm.ApplySilence → ESSBController.ApplySilenceSpell |
| noform | 破魔 | 大師 | 不改：第 2 項明定比例／對施法者 +5% 不變 | 對施法者與帶魔法護盾、元素披風的敵人削魔量 +5%／點 | 對施法者與帶魔法護盾、元素披風的敵人削魔量 +5%／點 | ESSBNoForm.IsSpellUser |
| noform | 破魔 | 傳奇 | ×3：純百分比傷害／傷害係數 | 目標魔力低於 25% 時命中傷害 +3%／點 | 目標魔力低於 25% 時命中傷害 +9%／點 | src\ESSBNoForm.psc:TrueMult |
| noform | 融斷 | 新手 | ×3：純百分比傷害／傷害係數 | 融斷 +2%／點 | 融斷 +6%／點 | src\ESSBNoForm.psc:BurstMult |
| noform | 融斷 | 熟練 | ×3：純百分比傷害／傷害係數 | 餘燼：關閉形態後 10 秒內無形態命中附帶前一元素附傷 +2%／點 | 餘燼：關閉形態後 10 秒內無形態命中附帶前一元素附傷 +6%／點 | src\ESSBNoForm.psc:EmberRatio |
| noform | 融斷 | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 融斷範圍 +0.3 公尺／點 | 融斷範圍 +0.3 公尺／點 | ESSBNoForm.BurstRadius |
| noform | 融斷 | 大師 | ×3：純百分比傷害／傷害係數 | 淬火：融斷後 10 秒內武器傷害 +1%／點 | 淬火：融斷後 10 秒內武器傷害 +3%／點 | src/ESSBNodes.psc:RefreshWeaponPercent |
| noform | 融斷 | 傳奇 | ×3：純百分比傷害／傷害係數 | 融斷再 +3%／點 | 融斷再 +9%／點 | src\ESSBNoForm.psc:BurstMult |
| common | 持續 | 新手 | 不改：移動／控制／防禦／門檻 | 同調門檻 -2%／點 | 同調門檻 -2%／點 | ESSBNodes.SyncThresholdScale → ESSBController.SyncStage |
| common | 持續 | 熟練 | ×3：純百分比傷害／傷害係數 | 同調二段時附傷 +1%／點 | 同調二段時附傷 +3%／點 | src\ESSBNodes.psc:CommonHitMult |
| common | 持續 | 專精 | 不改：移動／控制／防禦／門檻 | 同調三段時受傷 -0.5%／點 | 同調三段時受傷 -0.5%／點 | PERK ESSB_P_common_0_2_M<n> 進入點 0x24（受到的傷害） |
| common | 持續 | 大師 | ×3：純百分比傷害／傷害係數 | 同調三段時重擊附傷 +2%／點 | 同調三段時重擊附傷 +6%／點 | src\ESSBNodes.psc:CommonHitMult |
| common | 持續 | 傳奇 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 化身：同調三段時每 30 秒自動觸發一次當前元素的持續傳奇效果，冷卻 -1 秒／點 | 化身：同調三段時每 30 秒自動觸發一次當前元素的持續傳奇效果，冷卻 -1 秒／點 | ESSBNodes.AvatarCooldown → ESSBController.Tick → ESSBElem.OnAvatar |
| common | 開啟 | 新手 | ×3：純百分比傷害／傷害係數 | 所有元素附傷 +1%／點 | 所有元素附傷 +3%／點 | src\ESSBNodes.psc:CommonHitMult |
| common | 開啟 | 熟練 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 印記持續 +0.2 秒／點 | 印記持續 +0.2 秒／點 | ESSBNodes.MarkDurationBonus → ESSBController.ApplyMark |
| common | 開啟 | 專精 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 開印時 +1 同調／每 5 點 | 開印時 +1 同調／每 5 點 | ESSBNodes.OpenSyncBonus |
| common | 開啟 | 大師 | ×3：純百分比傷害／傷害係數 | 所有元素附傷再 +1%／點 | 所有元素附傷再 +3%／點 | src\ESSBNodes.psc:CommonHitMult |
| common | 開啟 | 傳奇 | 不改：非本輪百分比增傷（距離／時長／上限／冷卻／固定值／非百分比係數） | 每種元素狀態上限 +1 層／每 5 點 | 每種元素狀態上限 +1 層／每 5 點 | ESSBNodes.StatusCapBonus → ESSBController.StackCap |
| common | 關閉 | 新手 | ×3：純百分比傷害／傷害係數 | 終焉 +1%／點 | 終焉 +3%／點 | src\ESSBNodes.psc:CommonEndMult |
| common | 關閉 | 熟練 | ×3：純百分比傷害／傷害係數 | 融斷 +1%／點 | 融斷 +3%／點 | src\ESSBNodes.psc:CommonBurstMult |
| common | 關閉 | 專精 | ×3：純百分比傷害／傷害係數 | 切換後首次命中附帶前一元素附傷 +3%／點 | 切換後首次命中附帶前一元素附傷 +9%／點 | src\ESSBNodes.psc:EchoRatio |
| common | 關閉 | 大師 | ×3：純百分比傷害／傷害係數 | 終焉再 +1%／點 | 終焉再 +3%／點 | src\ESSBNodes.psc:CommonEndMult |
| common | 關閉 | 傳奇 | ×3：純百分比傷害／傷害係數 | 融斷再 +2%／點 | 融斷再 +6%／點 | src\ESSBNodes.psc:CommonBurstMult |

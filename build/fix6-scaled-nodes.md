# 明確納入 ×3 的 105 主線

| 樹 | 路線（index） | 階（index） | 分類／原因 | 原文 | 新數值／顯示文字 | 實際程式位置 |
|---|---|---|---|---|---|---|
| fire | 持續（烈焰）（0） | 新手（0） | ×3：純百分比傷害／傷害係數 | 熱度每層火附傷 +0.2%／點（8% → 11%） | 熱度每層火附傷 +0.6%／點（8% → 17%） | src\ESSBElem.psc:FireHitMult:67 |
| fire | 持續（烈焰）（0） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 火附傷 +1%／點 | 火附傷 +3%／點 | src\ESSBElem.psc:FireHitMult:64 |
| fire | 持續（烈焰）（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 同調每段火附傷 +1%／點 | 同調每段火附傷 +3%／點 | src\ESSBElem.psc:FireHitMult:70 |
| fire | 開啟（焰起）（1） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內火附傷 +1%／點 | 開印後 5 秒內火附傷 +3%／點 | src\ESSBElem.psc:FireHitMult:72 |
| fire | 關閉（爆燃）（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult:129 |
| fire | 關閉（爆燃）（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 火印記的融斷 +2%／點 | 火印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| fire | 關閉（爆燃）（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 火印記的融斷再 +2%／點 | 火印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| fire | 關閉（爆燃）（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 爆燃 +3%／點 | 爆燃 +9%／點 | src/ESSBElem.psc:SignatureMult:141 |
| frost | 持續（凍結）（0） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 冰附傷 +1%／點 | 冰附傷 +3%／點 | src\ESSBElem.psc:FrostHitMult:93 |
| frost | 持續（凍結）（0） | 專精（2） | ×3：純百分比傷害／傷害係數 | 冰封目標受冰附傷 +2%／點 | 冰封目標受冰附傷 +6%／點 | src\ESSBElem.psc:FrostHitMult:95 |
| frost | 持續（凍結）（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 同調每段冰附傷 +1%／點 | 同調每段冰附傷 +3%／點 | src\ESSBElem.psc:FrostHitMult:97 |
| frost | 開啟（冰臨）（1） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內冰附傷 +1%／點 | 開印後 5 秒內冰附傷 +3%／點 | src\ESSBElem.psc:FrostHitMult:99 |
| frost | 關閉（碎冰）（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult:129 |
| frost | 關閉（碎冰）（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 冰印記的融斷 +2%／點 | 冰印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| frost | 關閉（碎冰）（2） | 專精（2） | ×3：純百分比傷害／傷害係數 | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | src/ESSBElem.psc:OnEnd:600 |
| frost | 關閉（碎冰）（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 冰印記的融斷再 +2%／點 | 冰印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| frost | 關閉（碎冰）（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 碎冰 +3%／點 | 碎冰 +9%／點 | src/ESSBElem.psc:SignatureMult:141 |
| lightning | 持續（充能）（0） | 新手（0） | ×3：純百分比傷害／傷害係數 | 放電每格電荷傷害 +1%／點 | 放電每格電荷傷害 +3%／點 | src\ESSBElem.psc:Discharge:528 |
| lightning | 持續（充能）（0） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 雷附傷 +1%／點 | 雷附傷 +3%／點 | src\ESSBElem.psc:ShockHitMult:107 |
| lightning | 持續（充能）（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 同調每段雷附傷 +1%／點 | 同調每段雷附傷 +3%／點 | src\ESSBElem.psc:ShockHitMult:108 |
| lightning | 開啟（雷臨）（1） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內雷附傷 +1%／點 | 開印後 5 秒內雷附傷 +3%／點 | src\ESSBElem.psc:ShockHitMult:110 |
| lightning | 關閉（放電）（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult:129 |
| lightning | 關閉（放電）（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 雷印記的融斷 +2%／點 | 雷印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| lightning | 關閉（放電）（2） | 專精（2） | ×3：純百分比傷害／傷害係數 | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | src/ESSBElem.psc:OnEnd:600 |
| lightning | 關閉（放電）（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 雷印記的融斷再 +2%／點 | 雷印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| lightning | 關閉（放電）（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 放電 +3%／點 | 放電 +9%／點 | src/ESSBElem.psc:SignatureMult:141 |
| earth | 持續（裂甲）（0） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 土附傷 +1%／點 | 土附傷 +3%／點 | src\ESSBElem2.psc:EarthHitMult:73 |
| earth | 持續（裂甲）（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 同調每段土附傷 +1%／點 | 同調每段土附傷 +3%／點 | src\ESSBElem2.psc:EarthHitMult:74 |
| earth | 開啟（地臨）（1） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內土附傷 +1%／點 | 開印後 5 秒內土附傷 +3%／點 | src\ESSBElem2.psc:EarthHitMult:76 |
| earth | 關閉（地震）（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult:129 |
| earth | 關閉（地震）（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 土印記的融斷 +2%／點 | 土印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| earth | 關閉（地震）（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 土印記的融斷再 +2%／點 | 土印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| earth | 關閉（地震）（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 地震 +3%／點 | 地震 +9%／點 | src/ESSBElem.psc:SignatureMult:141 |
| wind | 持續（連斬）（0） | 新手（0） | ×3：純百分比傷害／傷害係數 | 風刃傷害 +2%／點 | 風刃傷害 +6%／點 | src\ESSBElem2.psc:WindBladeMult:551 |
| wind | 持續（連斬）（0） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 風附傷 +1%／點 | 風附傷 +3%／點 | src\ESSBElem2.psc:WindHitMult:84 |
| wind | 持續（連斬）（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 同調每段風附傷 +1%／點 | 同調每段風附傷 +3%／點 | src\ESSBElem2.psc:WindHitMult:85 |
| wind | 關閉（吹飛）（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult:129 |
| wind | 關閉（吹飛）（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 風印記的融斷 +2%／點 | 風印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| wind | 關閉（吹飛）（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 風印記的融斷再 +2%／點 | 風印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| wind | 關閉（吹飛）（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 落地傷害 +5%／點（×0.5 → ×1.25） | 落地傷害 +15%／點（×0.5 → ×2.75） | src\ESSBElem2.psc:LandingDamage:619 |
| blood | 持續（血位）（0） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 血附傷 +1%／點 | 血附傷 +3%／點 | src\ESSBElem2.psc:BloodHitMult:92 |
| blood | 持續（血位）（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 同調每段血附傷 +1%／點 | 同調每段血附傷 +3%／點 | src\ESSBElem2.psc:BloodHitMult:93 |
| blood | 開啟（血臨）（1） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內血附傷 +1%／點 | 開印後 5 秒內血附傷 +3%／點 | src\ESSBElem2.psc:BloodHitMult:95 |
| blood | 關閉（血潮）（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult:129 |
| blood | 關閉（血潮）（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 血印記的融斷 +2%／點 | 血印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| blood | 關閉（血潮）（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 血印記的融斷再 +2%／點 | 血印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| blood | 關閉（血潮）（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 血潮 +3%／點 | 血潮 +9%／點 | src/ESSBElem.psc:SignatureMult:141 |
| divine | 持續（審判）（0） | 新手（0） | ×3：純百分比傷害／傷害係數 | 聖印每層目標受聖傷 +1%／點 | 聖印每層目標受聖傷 +3%／點 | src\ESSBElem2.psc:HolyVulnerability:120 |
| divine | 持續（審判）（0） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 聖附傷 +1%／點 | 聖附傷 +3%／點 | src\ESSBElem2.psc:DivineHitMult:103 |
| divine | 持續（審判）（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 同調每段聖附傷 +1%／點 | 同調每段聖附傷 +3%／點 | src\ESSBElem2.psc:DivineHitMult:104 |
| divine | 開啟（聖臨）（1） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內聖附傷 +1%／點 | 開印後 5 秒內聖附傷 +3%／點 | src\ESSBElem2.psc:DivineHitMult:106 |
| divine | 關閉（裁決）（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult:129 |
| divine | 關閉（裁決）（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 聖印記的融斷 +2%／點 | 聖印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| divine | 關閉（裁決）（2） | 專精（2） | ×3：純百分比傷害／傷害係數 | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | src/ESSBElem.psc:OnEnd:600 |
| divine | 關閉（裁決）（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 聖印記的融斷再 +2%／點 | 聖印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| divine | 關閉（裁決）（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 裁決 +3%／點 | 裁決 +9%／點 | src/ESSBElem.psc:SignatureMult:141 |
| poison | 持續（疫毒）（0） | 新手（0） | ×3：純百分比傷害／傷害係數 | 毒層每層傷害 +2%／點 | 毒層每層傷害 +6%／點 | src\ESSBElem3.psc:PoisonTickMult:537 |
| poison | 持續（疫毒）（0） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 毒附傷 +1%／點 | 毒附傷 +3%／點 | src\ESSBElem3.psc:PoisonHitMult:98 |
| poison | 持續（疫毒）（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 同調每段毒附傷 +1%／點 | 同調每段毒附傷 +3%／點 | src\ESSBElem3.psc:PoisonHitMult:99 |
| poison | 開啟（毒臨）（1） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內毒附傷 +1%／點 | 開印後 5 秒內毒附傷 +3%／點 | src\ESSBElem3.psc:PoisonHitMult:101 |
| poison | 關閉（催毒）（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult:129 |
| poison | 關閉（催毒）（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 毒印記的融斷 +2%／點 | 毒印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| poison | 關閉（催毒）（2） | 專精（2） | ×3：純百分比傷害／傷害係數 | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | src/ESSBElem.psc:OnEnd:600 |
| poison | 關閉（催毒）（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 毒印記的融斷再 +2%／點 | 毒印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| poison | 關閉（催毒）（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 催毒期間毒層傷害 +3%／點 | 催毒期間毒層傷害 +9%／點 | src\ESSBElem3.psc:PoisonTickMult:539 |
| water | 持續（潮汐）（0） | 專精（2） | ×3：純百分比傷害／傷害係數 | 水壓每層水附傷 +1%／點 | 水壓每層水附傷 +3%／點 | src\ESSBElem3.psc:WaterHitMult:117 |
| water | 開啟（水臨）（1） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內水附傷 +1%／點 | 開印後 5 秒內水附傷 +3%／點 | src\ESSBElem3.psc:WaterHitMult:111 |
| water | 關閉（導引）（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult:129 |
| water | 關閉（導引）（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 水印記的融斷 +2%／點 | 水印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| water | 關閉（導引）（2） | 專精（2） | ×3：純百分比傷害／傷害係數 | 終焉後 5 秒內接管元素附傷 +1%／點 | 終焉後 5 秒內接管元素附傷 +3%／點 | src/ESSBElem.psc:OnEnd:600 |
| water | 關閉（導引）（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 水印記的融斷再 +2%／點 | 水印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| water | 關閉（導引）（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 導引 +3%／點 | 導引 +9%／點 | src/ESSBElem.psc:SignatureMult:141 |
| darkness | 持續（侵蝕）（0） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 暗附傷 +1%／點 | 暗附傷 +3%／點 | src\ESSBElem3.psc:DarkHitMult:127 |
| darkness | 持續（侵蝕）（0） | 專精（2） | ×3：純百分比傷害／傷害係數 | 詛咒滿層目標受所有傷害 +1%／點 | 詛咒滿層目標受所有傷害 +3%／點 | src/ESSBElem3.psc:TargetDamageMult:157 |
| darkness | 持續（侵蝕）（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 同調每段暗附傷 +1%／點 | 同調每段暗附傷 +3%／點 | src\ESSBElem3.psc:DarkHitMult:128 |
| darkness | 開啟（咒縛）（1） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內暗附傷 +1%／點 | 開印後 5 秒內暗附傷 +3%／點 | src\ESSBElem3.psc:DarkHitMult:130 |
| darkness | 關閉（死咒）（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult:129 |
| darkness | 關閉（死咒）（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 暗印記的融斷 +2%／點 | 暗印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| darkness | 關閉（死咒）（2） | 專精（2） | ×3：純百分比傷害／傷害係數 | 死咒的「已損失生命」係數 +0.5%／點（15% → 22.5%） | 死咒的「已損失生命」係數 +1.5%／點（15% → 37.5%） | src\ESSBElem3.psc:DeathCurseLostRatio:627 |
| darkness | 關閉（死咒）（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 暗印記的融斷再 +2%／點 | 暗印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| darkness | 關閉（死咒）（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 死咒 +3%／點 | 死咒 +9%／點 | src/ESSBElem.psc:SignatureMult:141 |
| astral | 持續（星落）（0） | 新手（0） | ×3：純百分比傷害／傷害係數 | 星痕延遲傷害 +2%／點 | 星痕延遲傷害 +6%／點 | src\ESSBElem3.psc:AstralTickMult:820 |
| astral | 持續（星落）（0） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 星附傷 +1%／點 | 星附傷 +3%／點 | src\ESSBElem3.psc:AstralHitMult:142 |
| astral | 持續（星落）（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 同調每段星附傷 +1%／點 | 同調每段星附傷 +3%／點 | src\ESSBElem3.psc:AstralHitMult:143 |
| astral | 開啟（星臨）（1） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 開印後 5 秒內星附傷 +1%／點 | 開印後 5 秒內星附傷 +3%／點 | src\ESSBElem3.psc:AstralHitMult:145 |
| astral | 關閉（星落）（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +2%／點 | 終焉 +6%／點 | src/ESSBElem.psc:EndMult:129 |
| astral | 關閉（星落）（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 星印記的融斷 +2%／點 | 星印記的融斷 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| astral | 關閉（星落）（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 星印記的融斷再 +2%／點 | 星印記的融斷再 +6%／點 | src/ESSBElem.psc:BurstMult:135 |
| astral | 關閉（星落）（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 星落 +3%／點 | 星落 +9%／點 | src/ESSBElem.psc:SignatureMult:141 |
| noform | 純武藝（0） | 新手（0） | ×3：純百分比傷害／傷害係數 | 無形態時武器傷害 +1%／點 | 無形態時武器傷害 +3%／點 | src/ESSBNodes.psc:RefreshWeaponPercent:30；build_v03.py:main_entries（預設 EPFD） |
| noform | 純武藝（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 戰意：每層武器傷害 +0.5%／點 | 戰意：每層武器傷害 +1.5%／點 | src/ESSBNodes.psc:RefreshWeaponPercent:30；build_v03.py:main_entries（預設 EPFD） |
| noform | 破魔（1） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 目標魔力低於 25% 時命中傷害 +3%／點 | 目標魔力低於 25% 時命中傷害 +9%／點 | src\ESSBNoForm.psc:TrueMult:40 |
| noform | 融斷（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 融斷 +2%／點 | 融斷 +6%／點 | src\ESSBNoForm.psc:BurstMult:271 |
| noform | 融斷（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 餘燼：關閉形態後 10 秒內無形態命中附帶前一元素附傷 +2%／點 | 餘燼：關閉形態後 10 秒內無形態命中附帶前一元素附傷 +6%／點 | src\ESSBNoForm.psc:EmberRatio:341 |
| noform | 融斷（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 淬火：融斷後 10 秒內武器傷害 +1%／點 | 淬火：融斷後 10 秒內武器傷害 +3%／點 | src/ESSBNodes.psc:RefreshWeaponPercent:30；build_v03.py:main_entries（預設 EPFD） |
| noform | 融斷（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 融斷再 +3%／點 | 融斷再 +9%／點 | src\ESSBNoForm.psc:BurstMult:271 |
| common | 持續（0） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 同調二段時附傷 +1%／點 | 同調二段時附傷 +3%／點 | src\ESSBNodes.psc:CommonHitMult:134 |
| common | 持續（0） | 大師（3） | ×3：純百分比傷害／傷害係數 | 同調三段時重擊附傷 +2%／點 | 同調三段時重擊附傷 +6%／點 | src\ESSBNodes.psc:CommonHitMult:137 |
| common | 開啟（1） | 新手（0） | ×3：純百分比傷害／傷害係數 | 所有元素附傷 +1%／點 | 所有元素附傷 +3%／點 | src\ESSBNodes.psc:CommonHitMult:131 |
| common | 開啟（1） | 大師（3） | ×3：純百分比傷害／傷害係數 | 所有元素附傷再 +1%／點 | 所有元素附傷再 +3%／點 | src\ESSBNodes.psc:CommonHitMult:131 |
| common | 關閉（2） | 新手（0） | ×3：純百分比傷害／傷害係數 | 終焉 +1%／點 | 終焉 +3%／點 | src\ESSBNodes.psc:CommonEndMult:144 |
| common | 關閉（2） | 熟練（1） | ×3：純百分比傷害／傷害係數 | 融斷 +1%／點 | 融斷 +3%／點 | src\ESSBNodes.psc:CommonBurstMult:149 |
| common | 關閉（2） | 專精（2） | ×3：純百分比傷害／傷害係數 | 切換後首次命中附帶前一元素附傷 +3%／點 | 切換後首次命中附帶前一元素附傷 +9%／點 | src\ESSBNodes.psc:EchoRatio:286 |
| common | 關閉（2） | 大師（3） | ×3：純百分比傷害／傷害係數 | 終焉再 +1%／點 | 終焉再 +3%／點 | src\ESSBNodes.psc:CommonEndMult:144 |
| common | 關閉（2） | 傳奇（4） | ×3：純百分比傷害／傷害係數 | 融斷再 +2%／點 | 融斷再 +6%／點 | src\ESSBNodes.psc:CommonBurstMult:149 |

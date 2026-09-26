"""規劃覆蓋表：v0.4 的 493 個技能樹節點（build/plan-tree-nodes.json）＋ 1.1／2.x 的共通機制。

節點以 (樹 id, v0.4 節點名稱) 為鍵（主線用 plan_trees.main_label 的短名），跟身分表同一套名字；
build/fix21_identity.py 用這張表核對「誰可以讀這個節點」，build_v03.write_plan_coverage 用它寫
build/plan-coverage.json（ledger 的節點狀態總表也由它產生）。每一列都必須有 status / where / note。

status（round 21）：
  DONE          負責是 Papyrus、DLL N1／N2 或純 ESP 引擎效果，照 v0.4 做完（本輪或更早）
  KEPT-Nx       負責是後續切片 Nx，現有實作跟 v0.4 文字相同（數字、條件、效果都一樣），沿用到 Nx 接手
                有任何近似（例如用 v0.3 的目標層數代替 v0.4 的玩家熱度階）就不是 KEPT，是 PARTIAL-Nx 並寫明差在哪
  PARTIAL-Nx    Papyrus／N2／引擎那一部分本輪做完，其餘等 Nx；PARTIAL-基礎＝其餘要先有一個技能樹以外的基礎機制
  LATER-Nx      只建 perk 記錄；機制屬於 Nx（或「待決」），本輪不讀、不發明效果（指揮官裁定 R4）
只有 DONE／KEPT／PARTIAL 可以有讀取點；LATER 被讀到就讓建置失敗（fix21_identity）。
"""
from __future__ import annotations

DONE = 'DONE'
STATUS_LEGEND = {
    'DONE': '照 v0.4 做完（Papyrus、DLL N1／N2 或純引擎效果負責的節點）',
    'KEPT': '後續切片負責；現有實作跟 v0.4 文字相同，沿用到該切片接手',
    'PARTIAL': 'Papyrus／N2／引擎那一部分本輪做完，其餘等後續切片或基礎機制',
    'LATER': '只有 perk 記錄；機制屬於後續切片，本輪不讀',
}

# ------------------------------------------------------------------ 節點表（v0.4，round 21 重建）
NODES = {
    # ================= 5.3 火焰（fire）
    ('fire', '火源倍率 N'): ('DONE', 'DLL native/include/Status.h（node::kFireSourceN）',
        'round 22（N3）照 v0.4：火源倍率 N +0.2／點（2 → 5）'),  # 0,0 v0.4 負責：DLL N3
    ('fire', '添薪'): ('DONE', 'DLL native/include/Status.h（node::kFireKindling）',
        'round 22（N3）照 v0.4：添薪：白熱引信 8 → 12 秒'),  # 0,0,0 v0.4 負責：DLL N3
    ('fire', '火附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '火附傷 +1%／點（×節點倍率），round 20 起 DLL 在命中當下算（round 22 刪掉 Papyrus 的鏡像）'),  # 0,1 v0.4 負責：DLL N2
    ('fire', '烙印'): ('DONE', 'DLL native/include/Status.h（node::kFireBrand）',
        'round 22（N3）照 v0.4：烙印：重擊使熱度升兩階'),  # 0,1,0 v0.4 負責：DLL N3
    ('fire', '溫血'): ('DONE', 'SPEL ESSB_Ability_WarmBlood + ESSBController.RefreshAbilities',
        '火形態耐力回復 +20%（自有常駐能力，隨回復倍率）'),  # 0,1,1 v0.4 負責：Papyrus
    ('fire', '帶火印記目標火抗'): ('DONE', 'ESSBElem.ApplyFireResistShred ← ESSBController.OnValidHitInternal',
        '火命中帶火印記的目標：火抗 -1%／點（6 秒）。負責寫 DLL N3；本輪由 Papyrus 在每次火命中施放同一個效果，條件改讀火印記（v0.3 的目標熱度層數近似拿掉）'),  # 0,2 v0.4 負責：DLL N3
    ('fire', '熔心'): ('DONE', 'DLL native/include/Status.h（node::kFireMoltenCore）',
        'round 22（N3）照 v0.4：熔心：洩壓與過熱後保留微熱'),  # 0,2,0 v0.4 負責：DLL N3
    ('fire', '熔身'): ('DONE', 'DLL native/include/Status.h（node::kFireMoltenBody）',
        'round 22（N3）照 v0.4：熔身：過熱不付代價，改為進入 10 秒「熔身」：火附傷 +100%、每秒回耐力 5，期間熱度停在白熱不推進；結束後熱度歸零。熔身中切換或按 Z 仍是洩壓'),  # 0,2,1 v0.4 負責：DLL N3＋引擎效果
    ('fire', '同調每段火附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段火附傷 +1%／點（×節點倍率 × 同調段）（round 22 刪掉 Papyrus 的鏡像）'),  # 0,3 v0.4 負責：DLL N2
    ('fire', '灼身'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kFireScorch）',
        'round 23：被近戰命中時攻擊者掛你的火印記（不開印、不切別的印記）並受一次 B_max ×1.0 火傷；每個攻擊者 3 秒一次（攻擊者身上的 ESSB_N4_RetortCooldown，與寒反／靜電／毒皮共用）'),  # 0,3,0 v0.4 負責：DLL 受擊 N4
    ('fire', '火浴'): ('DONE', 'DLL native/include/Status.h（node::kFireBath）',
        'round 22（N3）照 v0.4：火浴：白熱點燃當下依燒到的人數固定回血量，之後每秒回血 B_max ×0.1 × 該人數（人數不隨後續增減變動）'),  # 0,3,1 v0.4 負責：DLL N3
    ('fire', '業火'): ('DONE', 'DLL native/include/Status.h（node::kFireInferno）',
        'round 22（N3）照 v0.4：業火，同調三段時火源倍率 N 再 +0.1／點（5 → 6.5，熔燒 8.5）'),  # 0,4 v0.4 負責：DLL N3
    ('fire', '浴火'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kFireBathe）',
        'round 23：同調三段時被帶火印記的目標命中，熱度推進一次（照成熟時間）'),  # 0,4,0 v0.4 負責：DLL 受擊 N4
    ('fire', '熔爐'): ('DONE', 'DLL native/include/Status.h（node::kFireForge）',
        'round 22（N3）照 v0.4：熔爐：白熱引信到期不過熱，改升到第四階「熔燒」（火附傷 +90%、爆燃 ×4.0、火源 4.5 公尺、N +2）再燒 6 秒才過熱'),  # 0,4,1 v0.4 負責：DLL N3
    ('fire', '開印後 5 秒內熱度升階免等待'): ('DONE', 'DLL native/include/Status.h（node::kFireOpenQuick）',
        'round 22（N3）照 v0.4：開印後 5 秒內熱度升階免等待，+0.5 秒／每 5 點'),  # 1,0 v0.4 負責：DLL N3
    ('fire', '引火'): ('DONE', 'DLL native/include/Status.h（node::kFireIgnite）',
        'round 22（N3）照 v0.4：引火：開印使熱度升兩階'),  # 1,0,0 v0.4 負責：DLL N3
    ('fire', '開印後 5 秒內火附傷'): ('DONE', 'DLL native/include/Status.h（node::kOpenProc[element]）',
        'round 22（N3）照 v0.4：開印後 5 秒內火附傷 +3%／點'),  # 1,1 v0.4 負責：DLL N3
    ('fire', '烈火點燃'): ('DONE', 'DLL native/include/Status.h（node::kFireFlareOpen）',
        'round 22（N3）照 v0.4：烈火點燃：白熱中開印，白熱引信 +2 秒（每個引信最多 +4 秒）；火源掛的火印記不算開印'),  # 1,1,0 v0.4 負責：DLL N3
    ('fire', '餘熱'): ('DONE', 'DLL native/include/Reactions.h（node::kFireEmberHeat）',
        'round 24（N5）照 v0.4 在 DLL：餘熱：開印時回復 15 耐力'),  # 1,1,1 v0.4 負責：DLL N3
    ('fire', '火印記持續'): ('DONE', 'DLL native/include/Status.h（node::kMarkDuration[element]）',
        'round 22（N3）照 v0.4：火印記持續 +0.2 秒／點'),  # 1,2 v0.4 負責：DLL N3
    ('fire', '焰起強化'): ('DONE', 'DLL native/include/Reactions.h（node::kFireFlareUp）',
        'round 24（N5）照 v0.4 在 DLL：焰起強化：開印額外對範圍內敵人造成一次火附傷（讀法見 round 24 決策 5）'),  # 1,2,0 v0.4 負責：DLL N5
    ('fire', '火臨'): ('DONE', 'DLL native/include/Reactions.h（node::kAdvent[element]）',
        'round 24（N5）照 v0.4 在 DLL：火臨，開火形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('fire', '烈火之始'): ('DONE', 'DLL native/include/Status.h（node::kFireBlazeStart）',
        'round 22（N3）照 v0.4：烈火之始：開印若目標生命高於 80%，你的熱度直接白熱'),  # 1,3,0 v0.4 負責：DLL N3
    ('fire', '火種'): ('DONE', 'DLL native/include/Status.h（node::kFireTinder）',
        'round 22（N3）照 v0.4：火種：微熱與灼熱不因未命中退階（白熱引信不變）'),  # 1,3,1 v0.4 負責：DLL N3
    ('fire', '開印效果'): ('DONE', 'DLL native/include/Status.h（node::kOpenEffect[element]）',
        'round 22（N3）照 v0.4：開印效果 +9%／點'),  # 1,4 v0.4 負責：DLL N3
    ('fire', '先燃'): ('DONE', 'DLL native/include/Reactions.h（node::kFirePreBurn）',
        'round 24（N5）照 v0.4 在 DLL：先燃：同調三段時開印立即一次 ×0.5 爆燃（不消耗目標狀態）'),  # 1,4,0 v0.4 負責：DLL N3
    ('fire', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kEndMain[element]） ＋ ESSBElem.EndMult',
        'round 22（N3）照 v0.4：終焉 +6%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('fire', '猛爆'): ('DONE', 'DLL native/include/Status.h（node::kFireFierce）',
        'round 22（N3）照 v0.4：猛爆：爆燃不消耗目標身上的狀態（吃了加成但東西還在）'),  # 2,0,0 v0.4 負責：DLL N3
    ('fire', '餘壓'): ('DONE', 'DLL native/include/Status.h（node::kFireResidualPressure）',
        'round 22（N3）照 v0.4：餘壓：白熱期間切換或融斷後熱度保留灼熱，且火源多留 2 秒'),  # 2,0,2 v0.4 負責：Papyrus＋DLL N3
    ('fire', '火印記的融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstMain[element]）',
        'round 24（N5）照 v0.4 在 DLL：火印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('fire', '熾焰'): ('DONE', 'DLL native/include/Status.h（node::kFireBlaze）',
        'round 22（N3）照 v0.4：熾焰：白熱以上的爆燃再 ×1.5'),  # 2,1,0 v0.4 負責：DLL N3
    ('fire', '熔斷'): ('DONE', 'DLL native/include/Status.h OnFormLeave（node::kFireMeltdown）',
        '融斷後熱度保留。v0.4 標 DLL N5；熱度在 round 22 變成你身上的階，保留就是融斷時不洩壓（白熱的引信照走），所以本輪一併做完'),  # 2,1,1 v0.4 負責：DLL N5
    ('fire', '爆燃的消耗加成'): ('DONE', 'DLL native/include/Status.h（node::kFireConsume）',
        'round 22（N3）照 v0.4：爆燃的消耗加成 +3%／點 × 被消耗的狀態數'),  # 2,2 v0.4 負責：DLL N3
    ('fire', '餘燼'): ('DONE', 'DLL native/include/Status.h（node::kFireEmber）',
        'round 22（N3）照 v0.4：餘燼：火終焉後接管元素的開印 ×1.5'),  # 2,2,0 v0.4 負責：DLL N3
    ('fire', '火印記的融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstAgain[element]）',
        'round 24（N5）照 v0.4 在 DLL：火印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('fire', '焚天'): ('DONE', 'DLL native/include/Reactions.h（node::kFireSkyfire）',
        'round 24（N5）照 v0.4 在 DLL：焚天：火終焉觸發時，範圍內所有帶火印記目標一起爆燃（各自吃自己身上的狀態）（讀法見 round 24 決策 3）'),  # 2,3,0 v0.4 負責：DLL N5
    ('fire', '火葬'): ('DONE', 'DLL native/include/Reactions.h（node::kFireCremation）',
        'round 24（N5）照 v0.4 在 DLL：火葬：爆燃擊殺的目標對附近敵人再爆一次 ×0.5（讀法見 round 24 決策 18）'),  # 2,3,1 v0.4 負責：DLL N5
    ('fire', '爆燃'): ('DONE', 'DLL native/include/Reactions.h／native/include/Status.h（node::kSignature[element]）',
        'round 24（N5）照 v0.4 在 DLL：爆燃 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('fire', '火域'): ('DONE', 'DLL native/include/Reactions.h Bodies::End（node::kFireDomain）→ ESSB_Domain → StatusEngine.h RunOp 在融斷目標腳下施放 Spawn Hazard（ESSB_N6_Domain_Fire_<秒>，HAZD ESSB_N6_Hazard_Fire，引擎管壽命與數量，不再限 3 個）；hazard 對內部敵人掛 ESSB_N3_DomainFireEffect（受火傷 +20%：附傷、火源與 DLL 反應都讀它）；你在其中：native/include/Timer.h PlanDomainSelf（熱度免等待的視窗、進入時白熱引信 +5 秒）',
        'round 25（N6，裁定 R4）：領域是引擎的 hazard；你身上的兩項由 DLL 計時器每秒找你身邊屬於你的 hazard 判定（上一秒不在火域才算「進入」）'),  # 2,4,0 v0.4 負責：Papyrus（領域）；引信延長：DLL N3（進入時一次寫入，非每秒暫停）
    # ================= 5.4 冰霜（frost）
    ('frost', '每次命中凍結累積'): ('DONE', 'DLL native/include/Status.h（node::kFrostAccumulate）',
        'round 22（N3）照 v0.4：每次命中凍結累積 +5%／點（小數以機率取整）'),  # 0,0 v0.4 負責：DLL N3
    ('frost', '寒蝕'): ('DONE', 'DLL native/include/Status.h（node::kFrostErode）',
        'round 22（N3）照 v0.4：寒蝕：重擊凍結再 +1（總計 +3），且該次重擊造成的凍結歸零時限延長 2 秒（可調）'),  # 0,0,0 v0.4 負責：DLL N3
    ('frost', '冰附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '冰附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('frost', '深寒'): ('DONE', 'ESSBElem.OnFrozen ← ESSBController.OnESSBFrozen（DLL 冰封時送 ESSB_Frozen）',
        '冰封中目標耐力不回復（耐力凝滯）、攻擊 -20%，時長＝冰封秒數'),  # 0,1,0 v0.4 負責：引擎效果
    ('frost', '霜膚'): ('DONE', 'SPEL ESSB_IceArmorWide（5 公尺；30%／量表 ≥1 45%）← ESSBController.RefreshAbilities ＋ DLL native/include/Status.h（node::kFrostSkin：寒氣半徑）',
        '冰甲寒氣半徑 3 → 5 公尺，寒氣減速再 +10%（20→30%、35→45%）'),  # 0,1,1 v0.4 負責：引擎效果
    ('frost', '冰封目標受冰附傷'): ('DONE', 'DLL native/include/Status.h（node::kFrostFrozenProc）',
        'round 22（N3）照 v0.4：冰封目標受冰附傷 +6%／點'),  # 0,2 v0.4 負責：DLL N3
    ('frost', '永凍'): ('DONE', 'DLL native/include/Status.h（node::kFrostPermafrost）',
        'round 22（N3）照 v0.4：永凍：冰封 +2 秒，結束後凍結保留一半'),  # 0,2,0 v0.4 負責：DLL N3
    ('frost', '連鎖冰封'): ('DONE', 'DLL native/include/Reactions.h（node::kFrostChainFreeze）',
        'round 24（N5）照 v0.4 在 DLL：連鎖冰封：冰封目標死亡時附近敵人凍結 +3 並減速 30% 3 秒（讀法見 round 24 決策 3）'),  # 0,2,1 v0.4 負責：DLL N5
    ('frost', '同調每段冰附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段冰附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('frost', '冰鎧'): ('DONE', 'DLL native/include/Status.h res::IceShieldCap（node::kFrostIceMail）',
        'round 23：冰盾上限 5 → 8 層'),  # 0,3,2 v0.4 負責：DLL N4
    ('frost', '凍傷'): ('DONE', 'DLL native/include/Status.h OnFrozenEnd ＋ StatusEngine.h OnRemoved（node::kFrostFrostbite）',
        '凍傷：冰封結束時沒被碎掉的冰晶不浪費，每顆轉為一次 B_max ×0.5 冰傷。冰封中的冰晶多留 1 秒，移除事件同一幀讀到的冰晶也帶進結算（審查修正 2）'),  # 0,3,3 v0.4 負責：DLL N3
    ('frost', '寒反'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kFrostColdRetort）',
        'round 23：攻擊你的敵人（v0.4 沒限近戰）減速 30% 3 秒、凍結 +1，每個攻擊者 3 秒一次'),  # 0,3,1 v0.4 負責：DLL 受擊 N4
    ('frost', '絕對零度'): ('DONE', 'DLL native/include/Reactions.h（node::kFrostZero）',
        'round 24（N5）照 v0.4 在 DLL：絕對零度，同調三段時冰封減速再 -2%／點（總減速上限 70%），可影響首領'),  # 0,4 v0.4 負責：DLL N3
    ('frost', '冰心'): ('DONE', 'DLL native/include/Hurt.h PlanHurt → Plugin.cpp EngineFreezeNearby（node::kFrostIceHeart）',
        'round 23：受擊後生命低於 30% 時冰封 15 公尺內凍結量表 ≥1 的敵人，每 30 秒一次（受擊事件，不再每秒輪詢）'),  # 0,4,0 v0.4 負責：DLL 受擊 N4
    ('frost', '開印凍結'): ('DONE', 'DLL native/include/Status.h（node::kFrostOpenFreeze）',
        'round 22（N3）照 v0.4：開印凍結 +1／每 3 點'),  # 1,0 v0.4 負責：DLL N3
    ('frost', '寒潮'): ('DONE', 'DLL native/include/Reactions.h（node::kFrostColdTide）',
        'round 24（N5）照 v0.4 在 DLL：寒潮：開印時附近 1 人凍結 +2（讀法見 round 24 決策 3）'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('frost', '開印後 5 秒內冰附傷'): ('DONE', 'DLL native/include/Status.h（node::kOpenProc[element]）',
        'round 22（N3）照 v0.4：開印後 5 秒內冰附傷 +3%／點'),  # 1,1 v0.4 負責：DLL N3
    ('frost', '深霜結'): ('DONE', 'DLL native/include/Status.h（node::kFrostDeepRime）',
        'round 22（N3）照 v0.4：深霜結：開印時在目標身上預存 1 顆冰晶（冰封後不用普攻就有 1 顆；上限仍是 3）'),  # 1,1,0 v0.4 負責：DLL N3
    ('frost', '冰甲'): ('DONE', 'SPEL ESSB_IceArmor（寒氣披風）＋ ESSB_IceArmorChill 兩個互斥效果（量表 0：20%，量表 ≥1：35%，條件讀 DLL 的凍結效果）＋ DLL native/include/Status.h（node::kFrostIceArmor：命中寒氣內的敵人凍結再 +1）',
        '冰形態 3 公尺寒氣只對敵對者：減速 20%，凍結量表 ≥1 的改為 35%（取最強不相加，受 70% 上限）；命中寒氣內的敵人凍結再 +1'),  # 1,1,1 v0.4 負責：Papyrus（掛披風）＋引擎效果；命中加凍結：DLL N3
    ('frost', '冰印記持續'): ('DONE', 'DLL native/include/Status.h（node::kMarkDuration[element]）',
        'round 22（N3）照 v0.4：冰印記持續 +0.2 秒／點'),  # 1,2 v0.4 負責：DLL N3
    ('frost', '冰臨強化'): ('DONE', 'DLL native/include/Reactions.h（node::kFrostAdventPlus）',
        'round 24（N5）照 v0.4 在 DLL：冰臨強化：冰臨附帶減速 30% 3 秒'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N5
    ('frost', '冰臨'): ('DONE', 'DLL native/include/Reactions.h（node::kAdvent[element]）',
        'round 24（N5）照 v0.4 在 DLL：冰臨，開冰形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('frost', '霜鎖'): ('DONE', 'DLL native/include/Status.h（node::kFrostLock）',
        'round 22（N3）照 v0.4：霜鎖：開印目標 3 秒內移速 -30%；目標已在減速上限（70%）時改為凍結 +1'),  # 1,3,0 v0.4 負責：DLL N3
    ('frost', '霜爆'): ('DONE', 'DLL native/include/Reactions.h（node::kFrostBurst）',
        'round 24（N5）照 v0.4 在 DLL：霜爆：目標進入冰封的那一刻，3 公尺內其他凍結量表 ≥1 的敵人凍結 +2'),  # 1,3,2 v0.4 負責：DLL N3（掃描 N5）
    ('frost', '開印效果'): ('DONE', 'DLL native/include/Status.h（node::kOpenEffect[element]）',
        'round 22（N3）照 v0.4：開印效果 +9%／點'),  # 1,4 v0.4 負責：DLL N3
    ('frost', '絕霜'): ('DONE', 'DLL native/include/Status.h（node::kFrostAbsolute）',
        'round 22（N3）照 v0.4：絕霜：同調三段時開印直接冰封'),  # 1,4,0 v0.4 負責：DLL N3
    ('frost', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kEndMain[element]） ＋ ESSBElem.EndMult',
        'round 22（N3）照 v0.4：終焉 +6%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('frost', '銳碎'): ('DONE', 'DLL native/include/Status.h（node::kFrostSharp）',
        'round 22（N3）照 v0.4：銳碎：碎冰 20% → 25%（首領 10% → 12%）'),  # 2,0,0 v0.4 負責：DLL N3
    ('frost', '冰印記的融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstMain[element]）',
        'round 24（N5）照 v0.4 在 DLL：冰印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('frost', '冰崩'): ('DONE', 'DLL native/include/Reactions.h（node::kFrostAvalanche）',
        'round 24（N5）照 v0.4 在 DLL：冰崩：碎冰範圍化為 3 公尺，終焉碎冰與冰封中重擊碎冰皆適用，命中範圍內所有冰封目標（各吃自己的冰晶）'),  # 2,1,0 v0.4 負責：DLL N5
    ('frost', '冰封融斷'): ('DONE', 'DLL native/include/Status.h PlanEndBody（node::kFrostBurstShatter）',
        'round 24 審查修正（指揮官裁定）：融斷時冰封目標只有持有冰封融斷才碎冰（照一般碎冰：最大生命 20%，首領 10%，冰晶照加，不乘 K_sync）；沒有這個分支時融斷只給融斷那一擊，目標維持冰封'),  # 2,1,1 v0.4 負責：DLL N5
    ('frost', '終焉後 5 秒內接管元素附傷'): ('DONE', 'DLL native/include/Status.h（node::kTakeover[element]）',
        'round 22（N3）照 v0.4：終焉後 5 秒內接管元素附傷 +3%／點'),  # 2,2 v0.4 負責：DLL N3
    ('frost', '寒留'): ('DONE', 'DLL native/include/Status.h（node::kFrostLinger）',
        'round 22（N3）照 v0.4：寒留：冰終焉後接管元素的印記持續 +4 秒'),  # 2,2,0 v0.4 負責：DLL N3
    ('frost', '冰印記的融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstAgain[element]）',
        'round 24（N5）照 v0.4 在 DLL：冰印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('frost', '冰河'): ('DONE', 'DLL native/include/Reactions.h（node::kFrostGlacier）',
        'round 24（N5）照 v0.4 在 DLL：冰河：冰終焉時目標若冰封，範圍內所有冰封目標一起碎冰'),  # 2,3,0 v0.4 負責：DLL N5
    ('frost', '碎甲加深'): ('DONE', 'DLL native/include/Reactions.h（node::kFrostArmorBreak）',
        'round 24（N5）照 v0.4 在 DLL：碎甲加深：碎冰的碎甲 10% → 20%'),  # 2,3,1 v0.4 負責：DLL N3
    ('frost', '碎冰'): ('DONE', 'DLL native/include/Status.h（node::kSignature[kFrost]） ＋ ESSBElem.SignatureMult',
        'round 22（N3）照 v0.4：碎冰 +9%／點（乘在 20% 上）（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,4 v0.4 負責：DLL N3
    ('frost', '冰棺'): ('DONE', 'DLL native/include/Status.h（node::kFrostCoffin）',
        'round 22（N3）照 v0.4：冰棺：碎冰後目標再冰封 2 秒（第二次碎冰 ×0.5）'),  # 2,4,0 v0.4 負責：DLL N3
    ('frost', '冰原'): ('DONE', 'DLL native/include/Reactions.h Bodies::End（node::kFrostPlain）→ ESSB_Domain → StatusEngine.h RunOp 在融斷目標腳下施放 Spawn Hazard（ESSB_N6_Domain_Frost_<秒>，HAZD ESSB_N6_Hazard_Frost，引擎管壽命與數量，不再限 3 個）；hazard 掛 ESSB_N3_DomainFrostEffect（凍結累積 ×2，命中讀）；native/include/Timer.h PlanDomainEnemy（減速 50%，受 MCM 減速上限）、PlanDomainSelf＋SlowImmune（你在其中免疫減速）',
        'round 25（N6）：減速由 DLL 每秒下（hazard 讀不到 MCM 減速上限）；「你在其中免疫減速」以前只有沒人呼叫的 Papyrus 守衛，現在 DLL 每 tick 驅散你身上的減速'),  # 2,4,1 v0.4 負責：Papyrus（領域）
    # ================= 5.5 雷電（lightning）
    ('lightning', '放電每格電荷傷害'): ('DONE', 'DLL native/include/Reactions.h（node::kLightningPerCharge）',
        'round 24（N5）照 v0.4 在 DLL：放電每格電荷傷害 +1%／點'),  # 0,0 v0.4 負責：DLL N3
    ('lightning', '感應'): ('DONE', 'SPEL ESSB_Ability_Induction + ESSBController.RefreshAbilities',
        '雷形態魔力回復 +20%（v0.3 星輝共用的那一半已隨星輝退役）'),  # 0,0,0 v0.4 負責：Papyrus
    ('lightning', '雷附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '雷附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('lightning', '電弧'): ('DONE', 'DLL native/include/Reactions.h（node::kLightningArc）',
        'round 24（N5）照 v0.4 在 DLL：電弧：放電跳躍人數 2 → 3 人，跳躍傷害 40% → 55%（可調）'),  # 0,1,0 v0.4 負責：DLL N3
    ('lightning', '靜電'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kLightningStatic）',
        'round 23：被近戰命中時攻擊者掛你的雷印記（不開印），每個攻擊者 3 秒一次'),  # 0,1,1 v0.4 負責：DLL 受擊 N4
    ('lightning', '電荷上限'): ('DONE', 'DLL native/include/Status.h res::ChargeCap（node::kLightningChargeCap）',
        'round 23：電荷上限 6 +1／每 3 點（萬象另加）；雷的 N 取電荷（HitMath.h LightningRolls）'),  # 0,2 v0.4 負責：DLL N4
    ('lightning', '雷暴'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfHit（node::kLightningStorm）',
        'round 23：電荷滿時普攻 30% 放電（清空電荷，不必定暴擊）'),  # 0,2,0 v0.4 負責：DLL N4
    ('lightning', '同調每段雷附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段雷附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('lightning', '逆電'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kLightningReverse）',
        'round 23：被命中時電荷 +1，每 2 秒一次'),  # 0,3,2 v0.4 負責：DLL 受擊 N4
    ('lightning', '疾電'): ('DONE', 'DLL native/include/SelfLayer.h／DLL native/include/Status.h PlanEndSelf（node::kLightningQuick）',
        'round 23：任何放電（滿格重擊、雷暴、雷神、雷終焉）後 3 秒暴擊率 +15%（附傷與放電都吃）'),  # 0,3,1 v0.4 負責：引擎效果（放電時由 DLL N4 掛上）
    ('lightning', '天雷'): ('DONE', 'DLL native/include/Reactions.h（node::kLightningSky）',
        'round 24（N5）照 v0.4 在 DLL：天雷，同調三段時放電改為對範圍內所有感電目標，範圍 2 公尺 +0.2 公尺／點（讀法見 round 24 決策 9）'),  # 0,4 v0.4 負責：DLL N5
    ('lightning', '雷神'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfHit（node::kLightningGod）',
        'round 23：同調三段時電荷一到滿層立即對被命中的目標放電並回魔 B_max × 電荷數（回魔量 v0.4 沒寫，沿用 round 21 的 KEPT 值）'),  # 0,4,0 v0.4 負責：DLL N4
    ('lightning', '開印電荷'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kLightningOpenCharge）',
        'round 23：開印電荷 +2，+1／每 5 點'),  # 1,0 v0.4 負責：DLL N4
    ('lightning', '傳導'): ('DONE', 'DLL native/include/Reactions.h（node::kLightningConduct）',
        'round 24（N5）照 v0.4 在 DLL：傳導：開印時附近 1 人也感電（讀法見 round 24 決策 4）'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('lightning', '開印後 5 秒內雷附傷'): ('DONE', 'DLL native/include/Status.h（node::kOpenProc[element]）',
        'round 22（N3）照 v0.4：開印後 5 秒內雷附傷 +3%／點'),  # 1,1 v0.4 負責：DLL N3
    ('lightning', '強感電'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kLightningStrongShock）',
        'round 23：開印那一擊是重擊時電荷直接補滿（這一擊不放電），每 15 秒一次'),  # 1,1,0 v0.4 負責：DLL N4
    ('lightning', '充能開印'): ('DONE', 'DLL native/include/Reactions.h（node::kLightningChargeOpen）',
        'round 24（N5）照 v0.4 在 DLL：充能開印：開印時回復 B_max 魔力'),  # 1,1,1 v0.4 負責：DLL N3
    ('lightning', '雷印記持續'): ('DONE', 'DLL native/include/Status.h（node::kMarkDuration[element]）',
        'round 22（N3）照 v0.4：雷印記持續 +0.2 秒／點'),  # 1,2 v0.4 負責：DLL N3
    ('lightning', '雷臨強化'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfEnter ← ESSBNative.FormEnter（node::kLightningAdvent）',
        'round 23：雷臨時 +5 電荷'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N4
    ('lightning', '雷臨'): ('DONE', 'DLL native/include/Reactions.h（node::kAdvent[element]）',
        'round 24（N5）照 v0.4 在 DLL：雷臨，開雷形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('lightning', '感電削弱'): ('DONE', 'ESSBElem.OpenShock（自有 MagicResistDebuff）',
        '感電目標魔抗 -10%（開印時掛，8 秒）'),  # 1,3,0 v0.4 負責：引擎效果
    ('lightning', '雷閃'): ('DONE', 'DLL native/include/Reactions.h（node::kLightningFlash）',
        'round 24（N5）照 v0.4 在 DLL：雷閃：開印後 2 秒移速 +15%'),  # 1,3,1 v0.4 負責：DLL N3
    ('lightning', '雷鳴'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kLightningThunderclap）',
        'round 23：開印那一擊暴擊時電荷額外 +2'),  # 1,3,3 v0.4 負責：DLL N4
    ('lightning', '開印效果'): ('DONE', 'DLL native/include/Status.h（node::kOpenEffect[element]）',
        'round 22（N3）照 v0.4：開印效果 +9%／點'),  # 1,4 v0.4 負責：DLL N3
    ('lightning', '先雷'): ('DONE', 'DLL native/include/Reactions.h（node::kLightningFirst）',
        'round 24（N5）照 v0.4 在 DLL：先雷：同調三段時開印立即放電一次，不消耗電荷'),  # 1,4,0 v0.4 負責：DLL N3
    ('lightning', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kEndMain[element]） ＋ ESSBElem.EndMult',
        'round 22（N3）照 v0.4：終焉 +6%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('lightning', '連鎖'): ('DONE', 'DLL native/include/Reactions.h（node::kLightningChain）',
        'round 24（N5）照 v0.4 在 DLL：連鎖：放電跳躍 2 → 5 人'),  # 2,0,0 v0.4 負責：DLL N3
    ('lightning', '雷印記的融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstMain[element]）',
        'round 24（N5）照 v0.4 在 DLL：雷印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('lightning', '蓄餘'): ('DONE', 'DLL native/include/Status.h（node::kLightningResidual）',
        'round 24（N5）照 v0.4 在 DLL：蓄餘：雷終焉不消耗電荷'),  # 2,1,0 v0.4 負責：DLL N3
    ('lightning', '雷斷'): ('DONE', 'DLL native/include/Reactions.h（node::kLightningBurstBonus）',
        'round 24（N5）照 v0.4 在 DLL：雷斷：雷印記融斷時附加你全部電荷的放電加成'),  # 2,1,1 v0.4 負責：DLL N5
    ('lightning', '終焉後 5 秒內接管元素附傷'): ('DONE', 'DLL native/include/Status.h（node::kTakeover[element]）',
        'round 22（N3）照 v0.4：終焉後 5 秒內接管元素附傷 +3%／點'),  # 2,2 v0.4 負責：DLL N3
    ('lightning', '餘電'): ('DONE', 'DLL native/include/Status.h（node::kLightningAfterShock）',
        'round 24（N5）照 v0.4 在 DLL：餘電：雷終焉後接管元素的開印附帶一次 ×0.5 放電'),  # 2,2,0 v0.4 負責：DLL N3
    ('lightning', '雷印記的融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstAgain[element]）',
        'round 24（N5）照 v0.4 在 DLL：雷印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('lightning', '雷殛'): ('DONE', 'DLL native/include/Reactions.h（node::kLightningStrike）',
        'round 24（N5）照 v0.4 在 DLL：雷殛：雷終焉對範圍內所有感電目標各一次全額放電'),  # 2,3,0 v0.4 負責：DLL N5
    ('lightning', '過載終焉'): ('DONE', 'DLL native/include/Status.h res::EndExtra ＋ DLL native/include/SelfLayer.h PlanSelfLeave（node::kLightningOverloadEnd）',
        'round 23：任一元素終焉時電荷 ≥8 則 ×2（DLL 結算的終焉傷害與 Papyrus 本體都吃）；電荷跨形態攜帶（切換不清空）'),  # 2,3,1 v0.4 負責：DLL N3
    ('lightning', '放電'): ('DONE', 'DLL native/include/Reactions.h／native/include/Status.h（node::kSignature[element]）',
        'round 24（N5）照 v0.4 在 DLL：放電 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('lightning', '雷霆'): ('DONE', 'DLL native/include/Status.h PlanEndSelf ＋ DLL native/include/SelfLayer.h PlanSelfHit／PlanSelfNoForm（node::kLightningThunder）',
        'round 23：雷印記融斷後 5 秒內每次命中放電 ×0.3（融斷當下的電荷）'),  # 2,4,0 v0.4 負責：DLL N4
    # ================= 5.6 大地（earth）
    ('earth', '裂痕護甲削減'): ('DONE', 'DLL native/include/Reactions.h（node::kEarthFissureArmor）',
        'round 24（N5）照 v0.4 在 DLL：裂痕護甲削減 +2／點（-30 → -60）'),  # 0,0 v0.4 負責：DLL N3
    ('earth', '磐石'): ('DONE', 'DLL native/include/Status.h res::SetRock（node::kEarthBedrock）',
        'round 23：岩甲每層護甲 +25 → +40（DLL 掛的 ESSB_N4_RockArmorAVEffect）'),  # 0,0,0 v0.4 負責：DLL N4
    ('earth', '土附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '土附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('earth', '震擊'): ('DONE', 'DLL native/include/Reactions.h（node::kEarthQuakeStrike）',
        'round 24（N5）照 v0.4 在 DLL：震擊：重擊消耗裂痕標記，觸發 1.5× 地震爆傷並削減 50 耐力'),  # 0,1,0 v0.4 負責：DLL N3
    ('earth', '厚土'): ('DONE', 'DLL native/include/Status.h res::RockCap（node::kEarthThick）',
        'round 23：岩甲上限 5 → 10'),  # 0,1,1 v0.4 負責：DLL N4
    ('earth', '命中削減目標耐力'): ('DONE', 'DLL native/include/HitMath.h AddFlatHitNodes（node::kEarthStaminaCut）',
        '命中削耐 3.0 × 點 × G（round 20 D6）'),  # 0,2 v0.4 負責：DLL N2
    ('earth', '汲力'): ('DONE', 'DLL native/include/HitMath.h AddFlatHitNodes（node::kEarthDrainStrength）',
        '削減的耐力一半轉給你'),  # 0,2,0 v0.4 負責：DLL N2
    ('earth', '同調每段土附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段土附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('earth', '不動'): ('DONE', 'PERK ESSB_P_earth_0_3_B1 進入點 0x21（受到的擊退 ×0，條件 ESSB_RockArmor ≥5）',
        '岩甲 ≥5 時免疫擊退（自有）'),  # 0,3,0 v0.4 負責：引擎效果
    ('earth', '反震'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kEarthRetaliate）＋ ESSBController.OnESSBKnock',
        'round 23：岩甲滿層被近戰命中反震 B_max ×2.0 土傷（v0.4 沒寫量，沿用 round 21 的 KEPT 值）並使攻擊者跌倒（推力經 ESSB_Knock 在 Papyrus），10 秒一次，清空岩甲'),  # 0,3,1 v0.4 負責：DLL 受擊 N4（跌倒推力：`AIProcess::KnockExplosion`）
    ('earth', '地動'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfHit（node::kEarthQuakeKnock）＋ ESSBController.OnESSBKnock',
        'round 23：同調三段重擊、目標耐力 <30%，5%／點跌倒（推力經 ESSB_Knock）'),  # 0,4 v0.4 負責：DLL N4（跌倒推力：`AIProcess::KnockExplosion`）
    ('earth', '山岳'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kEarthMountain）＋ PERK ESSB_P_earth_0_4_B1 進入點 0x24',
        '同調三段時岩甲不因被打減少（DLL 受擊），物理減傷每層 +4% → +5%（PERK 讀 DLL 鏡射的 ESSB_RockArmor；合計上限 60%）'),  # 0,4,0 v0.4 負責：DLL 受擊 N4＋引擎效果
    ('earth', '開印岩甲'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kEarthOpenRock）',
        'round 23：開印岩甲 +2，+1／每 5 點'),  # 1,0 v0.4 負責：DLL N4
    ('earth', '震波'): ('DONE', 'DLL native/include/Reactions.h（node::kEarthWave）',
        'round 24（N5）照 v0.4 在 DLL：震波：開印時附近 1 人也裂痕（讀法見 round 24 決策 3）'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('earth', '開印後 5 秒內土附傷'): ('DONE', 'DLL native/include/Status.h（node::kOpenProc[element]）',
        'round 22（N3）照 v0.4：開印後 5 秒內土附傷 +3%／點'),  # 1,1 v0.4 負責：DLL N3
    ('earth', '深裂痕'): ('DONE', 'DLL native/include/Status.h（node::kEarthDeepFissure）',
        'round 22（N3）照 v0.4：深裂痕：開印時目標耐力低於 50% 則立即跌倒（掛倒地）'),  # 1,1,0 v0.4 負責：DLL N3（跌倒推力：`AIProcess::KnockExplosion`）
    ('earth', '岩膚'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kEarthRockSkin）',
        'round 23：開印岩甲 +2 → +4'),  # 1,1,1 v0.4 負責：DLL N4
    ('earth', '土印記持續'): ('DONE', 'DLL native/include/Status.h（node::kMarkDuration[element]）',
        'round 22（N3）照 v0.4：土印記持續 +0.2 秒／點'),  # 1,2 v0.4 負責：DLL N3
    ('earth', '地臨強化'): ('DONE', 'DLL native/include/Reactions.h／native/include/SelfLayer.h（node::kEarthAdvent）',
        'round 24（N5）照 v0.4 在 DLL：地臨強化：地臨時岩甲滿層（開場就能碎岩），範圍內敵人耐力 -50%（讀法見 round 24 決策 23）'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N4／N5
    ('earth', '地臨'): ('DONE', 'DLL native/include/Reactions.h（node::kAdvent[element]）',
        'round 24（N5）照 v0.4 在 DLL：地臨，開土形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('earth', '地基'): ('DONE', 'DLL native/include/Reactions.h（node::kEarthBase）',
        'round 24（N5）照 v0.4 在 DLL：地基：開印目標 3 秒內耐力不回復（自有效果把耐力回復設 0）'),  # 1,3,0 v0.4 負責：DLL N3＋引擎效果
    ('earth', '裂地'): ('DONE', 'DLL native/include/Status.h（node::kEarthRift）',
        'round 22（N3）照 v0.4：裂地：開印目標 8 秒內若被土弄倒，倒地標記 3 → 5 秒'),  # 1,3,1 v0.4 負責：DLL N3
    ('earth', '開印效果'): ('DONE', 'DLL native/include/Status.h（node::kOpenEffect[element]）',
        'round 22（N3）照 v0.4：開印效果 +9%／點'),  # 1,4 v0.4 負責：DLL N3
    ('earth', '先震'): ('DONE', 'DLL native/include/Reactions.h（node::kEarthFirstQuake）',
        'round 24（N5）照 v0.4 在 DLL：先震：同調三段時開印立即一次 ×0.5 地震，不含跌倒'),  # 1,4,0 v0.4 負責：DLL N5
    ('earth', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kEndMain[element]） ＋ ESSBElem.EndMult',
        'round 22（N3）照 v0.4：終焉 +6%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('earth', '崩裂'): ('DONE', 'DLL native/include/Reactions.h（node::kEarthCollapse）',
        'round 24（N5）照 v0.4 在 DLL：崩裂：地震 ×1.5 → ×2.0'),  # 2,0,0 v0.4 負責：DLL N5
    ('earth', '土印記的融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstMain[element]）',
        'round 24（N5）照 v0.4 在 DLL：土印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('earth', '廣震'): ('DONE', 'DLL native/include/Reactions.h（node::kEarthWide）',
        'round 24（N5）照 v0.4 在 DLL：廣震：地震範圍 3 → 5 公尺'),  # 2,1,0 v0.4 負責：DLL N5
    ('earth', '固土'): ('DONE', 'DLL native/include/Status.h PlanEndSelf（node::kEarthFirm）',
        'round 23：土終焉後岩甲滿層'),  # 2,1,1 v0.4 負責：DLL N4
    ('earth', '地震耐力削減'): ('DONE', 'DLL native/include/Reactions.h（node::kEarthQuakeStamina）',
        'round 24（N5）照 v0.4 在 DLL：地震耐力削減 +3%／點（不吃節點倍率）'),  # 2,2 v0.4 負責：DLL N5
    ('earth', '地斷'): ('DONE', 'DLL native/include/Reactions.h（node::kEarthSever）',
        'round 24（N5）照 v0.4 在 DLL：地斷：土印記融斷時，範圍內耐力低於 30% 的目標直接跌倒（掛倒地）；跌倒的推力經 ESSB_Knock 由 Papyrus 做（裁定 R4）'),  # 2,2,0 v0.4 負責：DLL N5（`AIProcess::KnockExplosion`）
    ('earth', '蓄能'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfHit ＋ DLL native/include/Hurt.h PlanHurt（node::kEarthCharge）＋ PERK 進入點 0x24（ESSB_Bracing）＋ DLL native/include/Reactions.h Bodies::End（地震）',
        'round 23：蓄勁滿 10 時（決策：v0.4 沒寫何時轉換）格擋把它換成每點物理減傷 +1%、3 秒；重擊把它換成下一次地震／碎岩 +5%／點'),  # 2,2,1 v0.4 負責：DLL 受擊 N4；DLL N4
    ('earth', '土印記的融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstAgain[element]）',
        'round 24（N5）照 v0.4 在 DLL：土印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('earth', '山崩'): ('DONE', 'DLL native/include/Reactions.h（node::kEarthLandslide）',
        'round 24（N5）照 v0.4 在 DLL：山崩：土終焉對範圍內所有帶裂痕的目標各一次地震（讀法見 round 24 決策 3）'),  # 2,3,0 v0.4 負責：DLL N5
    ('earth', '塵暴'): ('DONE', 'DLL native/include/Reactions.h（node::kEarthDust）',
        'round 24（N5）照 v0.4 在 DLL：塵暴：地震使範圍內敵人攻擊 -20% 3 秒'),  # 2,3,1 v0.4 負責：DLL N5
    ('earth', '地震'): ('DONE', 'DLL native/include/Reactions.h／native/include/Status.h（node::kSignature[element]）',
        'round 24（N5）照 v0.4 在 DLL：地震 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('earth', '地裂'): ('DONE', 'DLL native/include/Reactions.h Bodies::End（node::kEarthRiftZone）→ ESSB_Domain → StatusEngine.h RunOp 在融斷目標腳下施放 Spawn Hazard（ESSB_N6_Domain_Earth_<秒>，HAZD ESSB_N6_Hazard_Earth，引擎管壽命與數量，不再限 3 個）；hazard 掛標記與耐力不回復（ESSB_UtilEffect_StaminaRateDebuff 100）；native/include/Timer.h PlanDomainEnemy（耐力歸 0 → ESSB_Knock 2.0 → ESSBController.Knockdown：倒地、每目標 8 秒一次）',
        'round 25（N6）：耐力不回復由引擎的 hazard 施放；跌倒由 DLL 每秒判定、推力照舊 Papyrus（round 24 裁定 R4）；推力 2.0（同地動），推不倒的不改減速'),  # 2,4,0 v0.4 負責：Papyrus（領域與推力）
    # ================= 5.7 風（wind）
    ('wind', '風刃傷害'): ('DONE', 'DLL native/include/Reactions.h（node::kWindBladeDamage）',
        'round 24（N5）照 v0.4 在 DLL：風刃傷害 +2%／點'),  # 0,0 v0.4 負責：DLL N4
    ('wind', '迴旋'): ('DONE', 'DLL native/include/Reactions.h（node::kWindWhirl）',
        'round 24（N5）照 v0.4 在 DLL：迴旋：風刃改為對附近 2 人各一段'),  # 0,0,0 v0.4 負責：DLL N5
    ('wind', '風附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '風附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('wind', '亂舞'): ('DONE', 'DLL native/include/Status.h res::WindThreshold（node::kWindFrenzy）',
        'round 23：風勢門檻 4 → 3'),  # 0,1,0 v0.4 負責：DLL N4
    ('wind', '順風'): ('DONE', 'DLL native/include/HitMath.h AddFlatHitNodes（node::kWindTailwind）',
        '命中回復耐力（25 × G，round 20 D6）'),  # 0,1,1 v0.4 負責：DLL N2
    ('wind', '風形態移速再'): ('DONE', 'ESSBElem2.WindSpeedBonus → ESSBController.RefreshWindAbilities',
        '風形態移速 +10% 再 +0.5%／點'),  # 0,2 v0.4 負責：Papyrus
    ('wind', '追風'): ('DONE', 'DLL native/include/Reactions.h（node::kWindChase）',
        'round 24（N5）照 v0.4 在 DLL：追風：風刃命中回復耐力 3，並讓目標失衡'),  # 0,2,0 v0.4 負責：DLL N4
    ('wind', '無聲'): ('DONE', 'SPEL ESSB_Ability_Muffle + ESSBController.RefreshWindAbilities',
        '潛行中完全無聲、潛行移速 +20%'),  # 0,2,1 v0.4 負責：Papyrus
    ('wind', '同調每段風附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段風附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('wind', '殘影'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kWindAfterimage）＋ PERK ESSB_P_wind_0_3_B1 進入點 0x24 ×0',
        'round 23：風勢滿被近戰命中 30%：消耗風勢、掛 2 秒 ESSB_N4_AfterimageEffect（PERK 讓下一擊 ×0），抵掉一次後 DLL 拿掉'),  # 0,3,0 v0.4 負責：DLL 受擊 N4
    ('wind', '疾風'): ('DONE', 'SPEL 風形態能力（移速）＋ DLL native/src/Plugin.cpp WindSprint（node::kWindGale）',
        'round 23：移速再 +10%；衝刺時每秒回補耐力約當消耗的 50%（1.1 的 20% 回補在同一個 DLL 計時器）'),  # 0,3,1 v0.4 負責：Papyrus
    ('wind', '暗風'): ('DONE', 'DLL native/include/Status.h WindSneakExtra（node::kWindDarkWind）',
        '潛行攻擊的風附傷 ×3 → ×5（round 22 起 DLL 乘在命中當下；Papyrus 的差額補丁刪除）'),  # 0,3,2 v0.4 負責：DLL N4
    ('wind', '千刃'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfHit（node::kWindThousand）',
        'round 23：同調三段時每次命中 5%／點附帶風刃（ESSB_Blade）'),  # 0,4 v0.4 負責：DLL N4
    ('wind', '御風'): ('DONE', 'DLL native/include/Status.h（node::kWindRideWind：附傷與 DLL 反應 ×1.3）＋ native/include/Timer.h SlowImmune（同調三段免疫減速，Plugin.cpp SlowImmunity 每 tick）＋ PERK 進入點（武器傷害 ×1.3，條件：對手有 DLL 的失衡）',
        '同調三段時免疫減速（自有），且失衡目標受你所有傷害 +30%（含武器傷害）；+30% 不看同調（v0.4 第 1091 行）。round 25：免疫減速以前是沒人呼叫的 Papyrus 守衛（假 DONE），現在 DLL 做；Papyrus 反應倍率隨領域刪除'),  # 0,4,0 v0.4 負責：引擎效果
    ('wind', '開印風勢'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kWindOpenGauge）',
        'round 23：開印風勢 +2，+1／每 5 點'),  # 1,0 v0.4 負責：DLL N4
    ('wind', '風襲'): ('DONE', 'DLL native/include/Reactions.h（node::kWindRaid）',
        'round 24（N5）照 v0.4 在 DLL：風襲：開印時附近 1 人也風痕（讀法見 round 24 決策 4）'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('wind', '開印拉近距離'): ('DONE', 'ESSBElem2.PullDistance → ESSBController.PullIn',
        '開印拉近 1.5 公尺 +0.1 公尺／點（最多 3）'),  # 1,1 v0.4 負責：Papyrus（推力）
    ('wind', '疾風痕'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kWindGaleMark）',
        'round 23：開印風勢直接滿（送出一段風刃）'),  # 1,1,0 v0.4 負責：DLL N4
    ('wind', '輕躍'): ('DONE', 'DLL native/include/Reactions.h（node::kWindLeap）',
        'round 24（N5）照 v0.4 在 DLL：輕躍：開印後 3 秒移速 +10%'),  # 1,1,1 v0.4 負責：DLL N3
    ('wind', '風印記持續'): ('DONE', 'DLL native/include/Status.h（node::kMarkDuration[element]）',
        'round 22（N3）照 v0.4：風印記持續 +0.2 秒／點'),  # 1,2 v0.4 負責：DLL N3
    ('wind', '氣旋'): ('DONE', 'ESSBElem2.OnFormOpened(5) → ESSBController.PullIn',
        '風臨時把範圍內敵人拉到你面前 2 公尺'),  # 1,2,0 v0.4 負責：Papyrus
    ('wind', '奇襲'): ('DONE', 'DLL native/include/Reactions.h（node::kWindAmbush）',
        'round 24（N5）照 v0.4 在 DLL：奇襲：潛行攻擊的開印同時觸發終焉（一刀開印兼吹飛），且不拉近；吹飛的推力經 ESSB_Push 由 Papyrus 做（裁定 R4）'),  # 1,2,1 v0.4 負責：DLL N3
    ('wind', '風臨'): ('DONE', 'DLL native/include/Reactions.h（node::kAdvent[element]）',
        'round 24（N5）照 v0.4 在 DLL：風臨，開風形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('wind', '牽引'): ('DONE', 'DLL native/include/Reactions.h（node::kWindDrag）',
        'round 24（N5）照 v0.4 在 DLL：牽引：開印拉近時，目標身後 1.5 公尺內的其他敵人也一起被拉近並失衡（最多 2 人，各自 3 秒推力冷卻）；推力經 ESSB_Push 由 Papyrus 做（裁定 R4）（讀法見 round 24 決策 21）'),  # 1,3,0 v0.4 負責：DLL N3（掃描 N5）＋Papyrus（推力）
    ('wind', '氣流'): ('DONE', 'DLL native/include/Reactions.h（node::kWindGust）',
        'round 24（N5）照 v0.4 在 DLL：氣流：開印時回復 10 耐力'),  # 1,3,1 v0.4 負責：DLL N3
    ('wind', '開印效果'): ('DONE', 'DLL native/include/Status.h（node::kOpenEffect[element]）',
        'round 22（N3）照 v0.4：開印效果 +9%／點'),  # 1,4 v0.4 負責：DLL N3
    ('wind', '先風'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kWindFirst）',
        'round 23：同調三段時開印附帶一段風刃'),  # 1,4,0 v0.4 負責：DLL N4
    ('wind', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kEndMain[element]） ＋ ESSBElem.EndMult',
        'round 22（N3）照 v0.4：終焉 +6%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('wind', '亂流'): ('DONE', 'DLL native/include/Reactions.h（node::kWindTurbulence）',
        'round 24（N5）照 v0.4 在 DLL：亂流：風刃附近目標 2 → 5 人'),  # 2,0,0 v0.4 負責：DLL N5
    ('wind', '風印記的融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstMain[element]）',
        'round 24（N5）照 v0.4 在 DLL：風印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('wind', '上天'): ('DONE', 'DLL native/include/Reactions.h（node::kWindSky）',
        'round 24（N5）照 v0.4 在 DLL：上天：終焉的吹飛改為吹上天，落地時受 B_max ×1.0 風傷；吹上天的推力經 ESSB_Push 由 Papyrus 做（裁定 R4）'),  # 2,1,0 v0.4 負責：DLL N3／N5＋Papyrus（推力）
    ('wind', '風斷'): ('DONE', 'DLL native/include/Reactions.h（node::kWindSever）',
        'round 24（N5）照 v0.4 在 DLL：風斷：風印記融斷時每個目標各兩段風刃'),  # 2,1,1 v0.4 負責：DLL N5
    ('wind', '多段觸發'): ('DONE', 'DLL native/include/SelfLayer.h MultiTriggerRepeats ＋ Plugin.cpp Handle（node::kWindMulti）',
        'round 23：風印記被切時接管元素的命中效果共觸發 2 次（+1／每 5 點，最多 5）：附傷第 2 次起 ×0.5、各自擲骰，狀態與自身資源的 +1 照算，聖佑逐次升階'),  # 2,2 v0.4 負責：DLL N4
    ('wind', '風渦'): ('DONE', 'DLL native/include/Reactions.h（node::kWindVortex）',
        'round 24（N5）照 v0.4 在 DLL：風渦：終焉時 5 公尺內敵人被拉向目標聚攏；推力經 ESSB_Push 由 Papyrus 做（裁定 R4）'),  # 2,2,0 v0.4 負責：DLL N5＋Papyrus（推力）
    ('wind', '風印記的融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstAgain[element]）',
        'round 24（N5）照 v0.4 在 DLL：風印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('wind', '颶風'): ('DONE', 'DLL native/include/Reactions.h（node::kWindHurricane）',
        'round 24（N5）照 v0.4 在 DLL：颶風：融斷的吹上天改為對範圍內所有敵人，不限帶風印記；吹上天的推力經 ESSB_Push 由 Papyrus 做（裁定 R4）'),  # 2,3,0 v0.4 負責：DLL N5＋Papyrus
    ('wind', '順勢'): ('DONE', 'DLL native/include/Status.h PlanEndSelf ＋ DLL native/include/SelfLayer.h PlanSelfHit（node::kWindFollow）',
        'round 23：風被切後 5 秒內接管元素的命中各附一段風刃'),  # 2,3,1 v0.4 負責：DLL N4
    ('wind', '落地傷害'): ('DONE', 'DLL native/include/Reactions.h（node::kWindLanding）',
        'round 24（N5）照 v0.4 在 DLL：落地傷害 +5%／點（×0.5 → ×1.25）'),  # 2,4 v0.4 負責：DLL N3
    ('wind', '空中追擊'): ('DONE', 'DLL native/include/Status.h ReactionVulnerability ＋ PERK 進入點 0x23（目標帶 ESSB_N3_AirborneEffect）＋ ESSBElem2.WindBladeOne',
        'round 23：浮空目標受你的所有傷害 ×1.5（附傷與反應在 DLL，武器傷害是 PERK 讀目標的浮空效果）；風刃推高在 Papyrus'),  # 2,4,0 v0.4 負責：引擎效果＋DLL N4＋Papyrus（推力）
    ('wind', '連殺'): ('DONE', 'DLL native/include/Reactions.h／native/include/Status.h（node::kWindKillStreak）',
        'round 24（N5）照 v0.4 在 DLL：連殺：帶風印記的目標被你的潛行攻擊殺死後 5 秒內不解除潛行，下一次潛行攻擊附傷 ×2 並重置奇襲；不解除潛行 5 秒經 ESSB_Sneak 由 Papyrus 做（裁定 R4）（讀法見 round 24 決策 22）'),  # 2,4,1 v0.4 負責：DLL N5＋Papyrus
    # ================= 5.8 鮮血（blood）
    ('blood', '流血每層傷害'): ('DONE', 'DLL native/include/Status.h PerBleedLayer（node::kBloodLayerDamage）＋ Plugin.cpp TargetSecond（放血係數）',
        '流血每層傷害 +2%／點（×節點倍率），放血係數 +0.01%／點（0.3% → 0.45%，不吃節點倍率；放血的每秒點照 v0.4 屬 N5，本輪因狀態容器刪除先搬進 DLL 計時器，見決策 10）'),  # 0,0 v0.4 負責：DLL N3
    ('blood', '血刃'): ('DONE', 'DLL native/include/SelfLayer.h BloodPowerTerms（node::kBloodBlade）',
        'round 23：重擊扣的生命 50% 加進這一擊的血附傷'),  # 0,0,2 v0.4 負責：DLL N4
    ('blood', '深創'): ('DONE', 'DLL native/include/Status.h（node::kBloodDeepWound）',
        'round 22（N3）照 v0.4：深創：血痕上限 8 → 12'),  # 0,0,1 v0.4 負責：DLL N3
    ('blood', '血附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '血附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('blood', '飲血'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodDrink）',
        'round 24（N5）照 v0.4 在 DLL：飲血：擊殺流血目標時回血 20%，並獲得 10 秒「嗜血」：命中效果 +20%、吸血 +10%，不受血位影響'),  # 0,1,0 v0.4 負責：DLL N5
    ('blood', '血溢'): ('DONE', 'DLL native/include/HitMath.h AddBloodLeech（node::kBloodOverflow）',
        '生命已滿時吸血溢出灌進護血（上限最大生命 20%）；扣減在 N4'),  # 0,1,1 v0.4 負責：DLL N2
    ('blood', '吸血比例各血位'): ('DONE', 'DLL native/include/HitMath.h LeechRatio（node::kBloodLeechRatio）＋ESSBController.GetBloodLeechRatio',
        '吸血比例各血位 +1%／點'),  # 0,2 v0.4 負責：DLL N2
    ('blood', '逆流'): ('DONE', 'DLL native/include/HitMath.h BloodCurveFraction（node::kBloodReverse）＋ESSBController.BloodPercent／BloodBandMult',
        '反轉血位曲線'),  # 0,2,0 v0.4 負責：DLL N2
    ('blood', '血承'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodInherit）',
        'round 24（N5）照 v0.4 在 DLL：血承：擊殺流血目標時吸收其屬性 15 秒：其火、冰、雷、毒、魔抗各 50%、護甲 20%、最大生命 10%；只保留最近一個（讀法見 round 24 決策 17）'),  # 0,2,1 v0.4 負責：DLL N5
    ('blood', '同調每段血附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段血附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('blood', '止血'): ('DONE', 'DLL native/include/Status.h（node::kBloodStanch）',
        'round 22（N3）照 v0.4：止血：低血位（30% 以下）時流血目標的流血傷害 ×1.5，於套用血痕當下依你目前血位寫入強度'),  # 0,3,0 v0.4 負責：DLL N3
    ('blood', '血怒'): ('DONE', 'DLL native/include/HitMath.h BloodRage（node::kBloodRage；附傷、吸血與 DLL 反應的 ReactionScale）',
        '中血位命中效果與吸血 +15%（round 25：Papyrus 的 GetBloodHitMult 隨領域的傷害刪除）'),  # 0,3,1 v0.4 負責：DLL N2
    ('blood', '血海'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodSea）',
        'round 24（N5）照 v0.4 在 DLL：血海，同調三段時血潮改為範圍，範圍 1 公尺 +0.2 公尺／點'),  # 0,4 v0.4 負責：DLL N5
    ('blood', '不死'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodUndying）',
        'round 24（N5）照 v0.4 在 DLL：不死：同調三段時流血目標死亡，你回滿耐力，並回復生命到剛好越過上方最近的一條線（30% 或 70%），觸發一次回湧（不受越線冷卻，每 30 秒一次）（讀法見 round 24 決策 16）'),  # 0,4,0 v0.4 負責：DLL N5
    ('blood', '開印流血'): ('DONE', 'DLL native/include/Status.h（node::kBloodOpenLayers）',
        'round 22（N3）照 v0.4：開印流血 +1 層／每 5 點'),  # 1,0 v0.4 負責：DLL N3
    ('blood', '血濺'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodSpatter）',
        'round 24（N5）照 v0.4 在 DLL：血濺：開印時附近 1 人流血 1 層（讀法見 round 24 決策 3）'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('blood', '開印後 5 秒內血附傷'): ('DONE', 'DLL native/include/Status.h（node::kOpenProc[element]）',
        'round 22（N3）照 v0.4：開印後 5 秒內血附傷 +3%／點'),  # 1,1 v0.4 負責：DLL N3
    ('blood', '深血痕'): ('DONE', 'DLL native/include/Status.h（node::kBloodDeepMark）',
        'round 22（N3）照 v0.4：深血痕：開印依你的血區：高血區血痕多 +2 層、中血區多 +1 層並吸血一次、低血區吸血兩次'),  # 1,1,0 v0.4 負責：DLL N3
    ('blood', '開印回血'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodOpenHeal）',
        'round 24（N5）照 v0.4 在 DLL：開印回血：開印時你回血 B_max ×0.5，低血位 ×2'),  # 1,1,1 v0.4 負責：DLL N3
    ('blood', '血印記持續'): ('DONE', 'DLL native/include/Status.h（node::kMarkDuration[element]）',
        'round 22（N3）照 v0.4：血印記持續 +0.2 秒／點'),  # 1,2 v0.4 負責：DLL N3
    ('blood', '血臨強化'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodAdventPlus）',
        'round 24（N5）照 v0.4 在 DLL：血臨強化：血臨時你付最大生命 15%（代價路徑，留 1 點），並立即觸發一次濺血（不受越線冷卻）'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N3（濺血 N5）
    ('blood', '血臨'): ('DONE', 'DLL native/include/Reactions.h（node::kAdvent[element]）',
        'round 24（N5）照 v0.4 在 DLL：血臨，開血形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('blood', '血咒'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodCurse）',
        'round 24（N5）照 v0.4 在 DLL：血咒：開印目標 5 秒內生命回復速率 -50%'),  # 1,3,0 v0.4 負責：DLL N3
    ('blood', '血脈'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kBloodVein）',
        'round 23：血開印 +2 同調'),  # 1,3,1 v0.4 負責：DLL N4
    ('blood', '開印效果'): ('DONE', 'DLL native/include/Status.h（node::kOpenEffect[element]）',
        'round 22（N3）照 v0.4：開印效果 +9%／點'),  # 1,4 v0.4 負責：DLL N3
    ('blood', '血祭之始'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodSacrifice）',
        'round 24（N5）照 v0.4 在 DLL：血祭之始：同調三段時開印立即結算一次 ×0.5 血潮'),  # 1,4,0 v0.4 負責：DLL N3
    ('blood', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kEndMain[element]） ＋ ESSBElem.EndMult',
        'round 22（N3）照 v0.4：終焉 +6%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('blood', '飽飲'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodSated）',
        'round 24（N5）照 v0.4 在 DLL：飽飲：血潮結算的流血傷害 ×1.5'),  # 2,0,0 v0.4 負責：DLL N3
    ('blood', '血印記的融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstMain[element]）',
        'round 24（N5）照 v0.4 在 DLL：血印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('blood', '血漫'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodFlood）',
        'round 24（N5）照 v0.4 在 DLL：血漫：血潮結算時附近流血目標一起血潮（讀法見 round 24 決策 3）'),  # 2,1,0 v0.4 負責：DLL N5
    ('blood', '血斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodSever）',
        'round 24（N5）照 v0.4 在 DLL：血斷：血印記融斷治療你該傷害的 50%'),  # 2,1,1 v0.4 負責：DLL N5
    ('blood', '血潮治療倍率 ×2'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodSurgeHeal）',
        'round 24（N5）照 v0.4 在 DLL：血潮治療倍率 ×2，每點 +0.1'),  # 2,2 v0.4 負責：DLL N3
    ('blood', '血約'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodPact）',
        'round 24（N5）照 v0.4 在 DLL：血約：往上越線（回湧）時，15 公尺內所有流血目標血痕 +2 層'),  # 2,2,0 v0.4 負責：DLL N3（掃描 N5）
    ('blood', '血印記的融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstAgain[element]）',
        'round 24（N5）照 v0.4 在 DLL：血印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('blood', '血契'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodContract）',
        'round 24（N5）照 v0.4 在 DLL：血契：高血位（70% 以上）時血終焉損失 10% 生命，血潮 ×2'),  # 2,3,0 v0.4 負責：DLL N3
    ('blood', '放血終焉'): ('DONE', 'DLL native/include/Reactions.h（node::kBloodEndBleed）',
        'round 24（N5）照 v0.4 在 DLL：放血終焉：血潮的當前生命項 10% → 20%（首領 3% → 6%）'),  # 2,3,1 v0.4 負責：DLL N3
    ('blood', '血引'): ('DONE', 'DLL native/include/Status.h（node::kBloodLead）',
        'round 22（N3）照 v0.4：血引：血終焉後接管元素的開印附帶流血 2 層'),  # 2,3,2 v0.4 負責：DLL N3
    ('blood', '血潮'): ('DONE', 'DLL native/include/Reactions.h／native/include/Status.h（node::kSignature[element]）',
        'round 24（N5）照 v0.4 在 DLL：血潮 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('blood', '血池'): ('DONE', 'DLL native/include/Reactions.h Bodies::End（node::kBloodPool）→ ESSB_Domain → StatusEngine.h RunOp 在融斷目標腳下施放 Spawn Hazard（ESSB_N6_Domain_Blood_<秒>，HAZD ESSB_N6_Hazard_Blood，引擎管壽命與數量，不再限 3 個）；native/include/Timer.h PlanDomainSelf（你在其中每秒回血 20 × 回復倍率）',
        '血印記融斷後 5 秒血池，你在其中每秒回血（v0.4 沒寫數量，沿用 20；round 25 起 DLL 計時器每秒判定你在不在血池）'),  # 2,4,0 v0.4 負責：Papyrus（領域）
    # ================= 5.9 神聖（divine）
    ('divine', '聖佑各階武器傷害與聖傷加成'): ('DONE', 'DLL native/include/Status.h ProcTerms／聖裁（node::kDivineHolyBonus：聖傷）＋ PERK 主線進入點（武器傷害，條件你身上的聖佑階效果）',
        '+3%／點 × 階數（I 1、II 2、III 3）。武器那一份是 ESP 進入點，讀不到 MCM 的節點倍率，固定取預設 3（×3）'),  # 0,0 v0.4 負責：引擎效果
    ('divine', '護持'): ('DONE', 'DLL native/include/Reactions.h（node::kDivineGuard）',
        'round 24（N5）照 v0.4 在 DLL：護持：命中獲得 10% 魔抗 3 秒'),  # 0,0,0 v0.4 負責：DLL N3
    ('divine', '驅魔'): ('DONE', 'DLL native/include/HitMath.h ElementMultiplier（node::kDivineExorcism）',
        '對死靈施法者傷害 +50%（DLL 在命中當下判定；round 22 刪掉 Papyrus 的鏡像）'),  # 0,0,1 v0.4 負責：DLL N2
    ('divine', '聖附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '聖附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('divine', '神罰'): ('DONE', 'DLL native/include/Status.h（node::kDivineRetribution）',
        'round 22（N3）照 v0.4：神罰：聖裁計數只要 2 擊（第二擊就觸發）'),  # 0,1,0 v0.4 負責：DLL N3
    ('divine', '聖盾'): ('DONE', 'PERK 進入點（受到的法術強度 ×0.9／0.8／0.7，條件你身上的 DLL 聖佑 I／II／III 效果）',
        '聖佑各階另給受法術傷害 -10%／-20%／-30%（以引擎的「受到的法術強度」表達：會一起減少敵方法術的其他強度）'),  # 0,1,1 v0.4 負責：引擎效果
    ('divine', '聖裁傷害'): ('DONE', 'DLL native/include/Status.h（node::kDivineJudgeDamage）',
        'round 22（N3）照 v0.4：聖裁傷害 +6%／點'),  # 0,2 v0.4 負責：DLL N3
    ('divine', '光耀'): ('DONE', 'DLL native/include/Reactions.h（node::kDivineRadiance）',
        'round 24（N5）照 v0.4 在 DLL：光耀：裁決後 3 公尺內的亡靈魔族 5 秒內受聖傷 +20%'),  # 0,2,0 v0.4 負責：DLL N5
    ('divine', '聖灰'): ('DONE', 'DLL native/include/Reactions.h（node::kDivineAsh）',
        'round 24（N5）照 v0.4 在 DLL：聖灰：敵人化為灰燼時你回復魔力 B_max ×2'),  # 0,2,1 v0.4 負責：DLL N5
    ('divine', '同調每段聖附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段聖附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('divine', '破邪斬'): ('DONE', 'DLL native/include/Reactions.h（node::kDivineSmite）',
        'round 24（N5）照 v0.4 在 DLL：破邪斬：聖佑 III 時，聖裁對主目標造成的傷害另以 50% 濺到目標周圍 4 公尺內的其他敵人（最多 5 人，可調）；濺射只有傷害，不帶破防、不再觸發聖光爆，按接收者各自的抗性結算，對亡靈魔族 ×3 照算'),  # 0,3,2 v0.4 負責：DLL N5
    ('divine', '庇護'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kDivineSanctuary）',
        'round 23：受擊後生命低於 30% 時聖佑直接 III 並刷新，每 30 秒一次'),  # 0,3,1 v0.4 負責：DLL 受擊 N4
    ('divine', '天啟'): ('DONE', 'DLL native/include/Reactions.h（node::kDivineApocalypse）',
        'round 24（N5）照 v0.4 在 DLL：天啟，同調三段時裁決改為範圍，範圍 1 公尺 +0.2 公尺／點'),  # 0,4 v0.4 負責：DLL N5
    ('divine', '神佑'): ('DONE', 'ESSBController.TakeDivineSave／RefreshDivineProtection + PERK ESSB_P_divine_0_4_B1 進入點 0x24',
        '同調三段時致命傷留 1 血並 2 秒無敵，每場戰鬥一次（延遲死亡）'),  # 0,4,0 v0.4 負責：Papyrus
    ('divine', '淨土'): ('DONE', 'DLL native/include/Reactions.h（node::kDivinePureLand）',
        'round 24（N5）照 v0.4 在 DLL：淨土：同調三段時你在神聖形態中擊殺的所有敵人都化灰，不限是否帶印記；化灰崩解經 ESSB_Ash 由 Papyrus 施放（裁定 R4）'),  # 0,4,1 v0.4 負責：DLL N5
    ('divine', '開印回血'): ('DONE', 'DLL native/include/Reactions.h（node::kDivineOpenHeal）',
        'round 24（N5）照 v0.4 在 DLL：開印回血 +5%／點'),  # 1,0 v0.4 負責：DLL N3
    ('divine', '聖輝'): ('DONE', 'DLL native/include/Reactions.h（node::kDivineGlow）',
        'round 24（N5）照 v0.4 在 DLL：聖輝：開印時附近 1 人也聖印（讀法見 round 24 決策 4）'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('divine', '開印後 5 秒內聖附傷'): ('DONE', 'DLL native/include/Status.h（node::kOpenProc[element]）',
        'round 22（N3）照 v0.4：開印後 5 秒內聖附傷 +3%／點'),  # 1,1 v0.4 負責：DLL N3
    ('divine', '慈光'): ('DONE', 'DLL native/include/Status.h PlanOpenState（node::kDivineMercy）',
        '開印時懲戒 +2（不需要聖佑 II）。懲戒是 DLL 掛在你身上的效果（8 秒，上限 5），下一次裁決或聖裁每層 +20% 後清空（見決策 14）'),  # 1,1,0 v0.4 負責：DLL N3
    ('divine', '誓約'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains ＋ DLL native/include/Hurt.h PlanHurt（node::kDivineOath）',
        'round 23：聖開印的目標 8 秒內打你，懲戒 +2'),  # 1,1,2 v0.4 負責：DLL N3＋DLL 受擊 N4
    ('divine', '聖印記持續'): ('DONE', 'DLL native/include/Status.h（node::kMarkDuration[element]）',
        'round 22（N3）照 v0.4：聖印記持續 +0.2 秒／點'),  # 1,2 v0.4 負責：DLL N3
    ('divine', '聖臨強化'): ('DONE', 'ESSBElem2.OnFormOpened(7)',
        '聖臨時你與附近同伴回血 B_max ×2（審查修正：B_max ×2＝20，不再是 60×G）'),  # 1,2,0 v0.4 負責：Papyrus
    ('divine', '聖臨'): ('DONE', 'DLL native/include/Reactions.h（node::kAdvent[element]）',
        'round 24（N5）照 v0.4 在 DLL：聖臨，開聖形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('divine', '聖痕'): ('DONE', 'DLL native/include/Status.h（JudgedTarget、ProcTerms、PlanEndBody prey；node::kDivineStigma）＋ ESSBElem2.HolyVulnerability＋ESSBElem2.IsHolyPrey',
        '開印目標對亡靈魔族判定（命中的 ×1.5 與終焉的 ×3 都算，審查修正 4），非亡靈也受 +10% 聖傷'),  # 1,3,0 v0.4 負責：DLL N3＋引擎效果
    ('divine', '聖光'): ('DONE', 'DLL native/include/Reactions.h（node::kDivineLight）',
        'round 24（N5）照 v0.4 在 DLL：聖光：開印時附近同伴回血 B_max（讀法見 round 24 決策 6）'),  # 1,3,1 v0.4 負責：DLL N5
    ('divine', '開印效果'): ('DONE', 'DLL native/include/Status.h（node::kOpenEffect[element]）',
        'round 22（N3）照 v0.4：開印效果 +9%／點'),  # 1,4 v0.4 負責：DLL N3
    ('divine', '聖啟'): ('DONE', 'DLL native/include/Status.h（node::kDivineDawn）',
        'round 22（N3）照 v0.4：聖啟：同調三段時開印讓聖佑直接升到 II'),  # 1,4,0 v0.4 負責：DLL N3
    ('divine', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kEndMain[element]） ＋ ESSBElem.EndMult',
        'round 22（N3）照 v0.4：終焉 +6%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('divine', '重裁'): ('DONE', 'DLL native/include/Reactions.h（node::kDivineHeavyJudge）',
        'round 24（N5）照 v0.4 在 DLL：重裁：裁決 ×2.0 → ×3.0'),  # 2,0,0 v0.4 負責：DLL N3
    ('divine', '聖印記的融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstMain[element]）',
        'round 24（N5）照 v0.4 在 DLL：聖印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('divine', '廣裁'): ('DONE', 'DLL native/include/Reactions.h（node::kDivineWideJudge）',
        'round 24（N5）照 v0.4 在 DLL：廣裁：裁決改為 3 公尺範圍'),  # 2,1,0 v0.4 負責：DLL N5
    ('divine', '聖斷'): ('DONE', 'DLL native/include/Reactions.h（node::kDivineSever）',
        'round 24（N5）照 v0.4 在 DLL：聖斷：聖印記融斷每個目標治療你 B_max ×1.0'),  # 2,1,1 v0.4 負責：DLL N5
    ('divine', '終焉後 5 秒內接管元素附傷'): ('DONE', 'DLL native/include/Status.h（node::kTakeover[element]）',
        'round 22（N3）照 v0.4：終焉後 5 秒內接管元素附傷 +3%／點'),  # 2,2 v0.4 負責：DLL N3
    ('divine', '聖域'): ('DONE', 'DLL native/include/Reactions.h Bodies::End（node::kDivineSanctum）→ ESSB_Domain → StatusEngine.h RunOp 在融斷目標腳下施放 Spawn Hazard（ESSB_N6_Domain_Divine_<秒>，HAZD ESSB_N6_Hazard_Divine，引擎管壽命與數量，不再限 3 個）；native/include/Timer.h PlanDomainSelf（回血 25、回魔 20）；敵人 -20% 是 hazard 法術 ESSB_N6_HazardSpell_Divine 的兩個效果（build/fix25_records.py DIVINE_WEAKEN）',
        '聖終焉後 5 秒聖域：其中敵人傷害 -20%（round 25 審查修正，指揮官裁定：裡面的敵人 AttackDamageMult -0.2、DestructionPowerModifier -20，各 2 秒跟標記同步；「你在其中受傷 -20%」的 PERK 與 ESSB_DomainDivine 鏡射拿掉）、你持續回復（v0.4 沒寫數量，沿用 25／20）'),  # 2,2,0 v0.4 負責：Papyrus（領域）
    ('divine', '淨灰'): ('DONE', 'DLL native/include/Reactions.h（node::kDivinePureAsh）',
        'round 24（N5）照 v0.4 在 DLL：淨灰：帶神聖印記的亡靈化灰時爆出聖光，附近亡靈受 B_max ×1.0 聖傷（讀法見 round 24 決策 3）'),  # 2,2,1 v0.4 負責：DLL N5
    ('divine', '聖印記的融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstAgain[element]）',
        'round 24（N5）照 v0.4 在 DLL：聖印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('divine', '天誅'): ('DONE', 'DLL native/include/Reactions.h／native/include/Status.h（node::kDivineHeaven）',
        'round 24（N5）照 v0.4 在 DLL：天誅：懲戒上限 5 → 8；裁決消耗懲戒時，懲戒的加成部分另外對 3 公尺內其他敵人各結算一次（最多 5 人）'),  # 2,3,2 v0.4 負責：DLL 受擊 N4；DLL N5
    ('divine', '聖引'): ('DONE', 'DLL native/include/Status.h（node::kDivineLead）',
        'round 22（N3）照 v0.4：聖引：聖終焉後接管元素的開印治療你 B_max'),  # 2,3,1 v0.4 負責：DLL N3
    ('divine', '裁決'): ('DONE', 'DLL native/include/Reactions.h／native/include/Status.h（node::kSignature[element]）',
        'round 24（N5）照 v0.4 在 DLL：裁決 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('divine', '神聖領域'): ('DONE', 'DLL native/include/Reactions.h Bodies::End（node::kDivineHolyDomain）→ ESSB_Domain（8 秒）→ StatusEngine.h RunOp 在融斷目標腳下施放 Spawn Hazard（ESSB_N6_Domain_Divine_<秒>，HAZD ESSB_N6_Hazard_Divine，引擎管壽命與數量，不再限 3 個）；native/include/Timer.h PlanDomainSelf；「聖佑 III 融斷不清空」在 DLL Status.h OnFormLeave',
        'round 25（N6）：聖印記融斷時由 DLL 判定並在目標腳下放 8 秒的聖域 hazard（×持續時間倍率，整秒法術最多 24 秒）；其中的效果同聖域（含裡面敵人傷害 -20%）。PARTIAL-N6 的差距（領域本身在 Papyrus）已解決'),  # 2,4,0 v0.4 負責：DLL N5＋Papyrus（領域）
    # ================= 5.10 毒素（poison）
    ('poison', '每劑傷害'): ('DONE', 'DLL native/include/Status.h（node::kPoisonDoseDamage）',
        'round 22（N3）照 v0.4：每劑傷害 +6%／點'),  # 0,0 v0.4 負責：DLL N3
    ('poison', '免疫'): ('DONE', 'SPEL ESSB_Ability_PoisonResist + ESSBController.RefreshAbilities',
        '毒形態毒抗 +50%'),  # 0,0,0 v0.4 負責：Papyrus
    ('poison', '毒附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '毒附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('poison', '萎靡'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonWither）',
        'round 24（N5）照 v0.4 在 DLL：萎靡：目標中毒 ≥5 劑時攻擊 -15%'),  # 0,1,0 v0.4 負責：DLL N3
    ('poison', '毒皮'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kPoisonSkin）',
        'round 23：被近戰命中時攻擊者中毒 +2 劑，每個攻擊者 3 秒一次'),  # 0,1,1 v0.4 負責：DLL 受擊 N4
    ('poison', '瘴氣每秒傳遞劑量'): ('DONE', 'DLL native/include/Status.h rule::MiasmaDoses ＋ native/src/Plugin.cpp TargetSecond（node::kPoisonMiasmaRate）',
        "瘴氣每秒傳遞劑量 +0.05／點（×節點倍率）：DLL 每秒點把劑數併進 3 公尺內每個敵人唯一的中毒（擴散一劑 d' = max(d − t, 12)）；瘴氣披風拿掉（指揮官裁定 (b)+(d)）"),  # 0,2 v0.4 負責：引擎效果（披風）；劑數併入：待決（見 10.4）
    ('poison', '侵蝕'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonErode）',
        'round 24（N5）照 v0.4 在 DLL：侵蝕：目標中毒滿劑（10）時毒抗 -20%'),  # 0,2,0 v0.4 負責：DLL N3
    ('poison', '傳染門檻'): ('DONE', 'DLL native/include/Status.h（node::kPoisonThreshold）',
        'round 22（N3）照 v0.4：傳染門檻：擴散門檻 5 劑 → 1 劑'),  # 0,2,1 v0.4 負責：DLL N3
    ('poison', '同調每段毒附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段毒附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('poison', '蔓延'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonCreep）',
        'round 24（N5）照 v0.4 在 DLL：蔓延：死亡擴散的份額 50% → 75%'),  # 0,3,0 v0.4 負責：DLL N5
    ('poison', '以毒攻毒'): ('DONE', 'ESSBElem3.PoisonFormTick',
        '你中毒時生命回復 +20%'),  # 0,3,1 v0.4 負責：引擎效果
    ('poison', '瘟疫'): ('DONE', 'DLL native/include/Status.h rule::PlagueChance ＋ native/src/Plugin.cpp TargetSecond（node::kPoisonPlague）',
        "同調三段時中毒目標每秒 5%／點機率擴散 1 劑到 3 公尺內最近的敵人，併進對方的中毒（擴散一劑 d' = max(d − t, 12)；指揮官裁定 (b)+(d)）"),  # 0,4 v0.4 負責：待決
    ('poison', '百毒不侵'): ('DONE', 'ESSBElem3.PoisonFormTick',
        '同調三段時免疫中毒與疾病，附近中毒敵人每秒替你回血（審查修正：每個中毒敵人回血 6，拿掉 G(L)；v0.4 沒寫數量）'),  # 0,4,0 v0.4 負責：引擎效果（免疫）＋Papyrus（每秒掃描回血）
    ('poison', '開印劑數'): ('DONE', 'DLL native/include/Status.h（node::kPoisonOpenDoses）',
        'round 22（N3）照 v0.4：開印劑數 +1／每 3 點（3 → 8）'),  # 1,0 v0.4 負責：DLL N3
    ('poison', '毒濺'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonSplash）',
        'round 24（N5）照 v0.4 在 DLL：毒濺：開印時附近 1 人中毒 2 劑（讀法見 round 24 決策 7）'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('poison', '開印後 5 秒內毒附傷'): ('DONE', 'DLL native/include/Status.h（node::kOpenProc[element]）',
        'round 22（N3）照 v0.4：開印後 5 秒內毒附傷 +3%／點'),  # 1,1 v0.4 負責：DLL N3
    ('poison', '濃毒'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonThick）',
        'round 24（N5）照 v0.4 在 DLL：濃毒：開印時若 6 公尺內已有中毒的敵人，從劑數最高的那一個複製 2 劑到新目標（不從對方扣）'),  # 1,1,0 v0.4 負責：DLL N3（掃描 N5）
    ('poison', '毒膜'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonFilm）',
        'round 24（N5）照 v0.4 在 DLL：毒膜：開印時毒抗 +50% 5 秒'),  # 1,1,1 v0.4 負責：DLL N3
    ('poison', '毒印記持續'): ('DONE', 'DLL native/include/Status.h（node::kMarkDuration[element]）',
        'round 22（N3）照 v0.4：毒印記持續 +0.2 秒／點'),  # 1,2 v0.4 負責：DLL N3
    ('poison', '毒臨強化'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonAdventPlus）',
        'round 24（N5）照 v0.4 在 DLL：毒臨強化：毒臨時範圍內敵人中毒 3 劑（讀法見 round 24 決策 7）'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N5
    ('poison', '毒臨'): ('DONE', 'DLL native/include/Reactions.h（node::kAdvent[element]）',
        'round 24（N5）照 v0.4 在 DLL：毒臨，開毒形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('poison', '腐蝕開印'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonRot）',
        'round 24（N5）照 v0.4 在 DLL：腐蝕開印：開印目標毒抗 -10%'),  # 1,3,0 v0.4 負責：DLL N3
    ('poison', '毒血'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonBlood）',
        'round 24（N5）照 v0.4 在 DLL：毒血：開印時你回血 B_max ×0.5'),  # 1,3,1 v0.4 負責：DLL N3
    ('poison', '開印效果'): ('DONE', 'DLL native/include/Status.h（node::kOpenEffect[element]）',
        'round 22（N3）照 v0.4：開印效果 +9%／點'),  # 1,4 v0.4 負責：DLL N3
    ('poison', '劇毒之始'): ('DONE', 'DLL native/include/Status.h（node::kPoisonToxicStart）',
        'round 22（N3）照 v0.4：劇毒之始：同調三段時開印劑數 ×2'),  # 1,4,0 v0.4 負責：DLL N3
    ('poison', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kEndMain[element]） ＋ ESSBElem.EndMult',
        'round 22（N3）照 v0.4：終焉 +6%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('poison', '潰爛'): ('DONE', 'DLL native/include/Status.h（node::kPoisonFester）',
        'round 22（N3）照 v0.4：潰爛：催毒改為強度 ×3'),  # 2,0,0 v0.4 負責：DLL N3
    ('poison', '毒印記的融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstMain[element]）',
        'round 24（N5）照 v0.4 在 DLL：毒印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('poison', '延毒'): ('DONE', 'DLL native/include/Status.h（node::kPoisonLinger）',
        'round 22（N3）照 v0.4：延毒：催毒時剩餘時長 +4 秒'),  # 2,1,0 v0.4 負責：DLL N3
    ('poison', '疫染'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonInfect）',
        'round 24（N5）照 v0.4 在 DLL：疫染：毒終焉時把目標的中毒（同強度同剩餘）複製到 6 公尺內敵人（讀法見 round 24 決策 8）'),  # 2,1,1 v0.4 負責：DLL N5
    ('poison', '終焉後 5 秒內接管元素附傷'): ('DONE', 'DLL native/include/Status.h（node::kTakeover[element]）',
        'round 22（N3）照 v0.4：終焉後 5 秒內接管元素附傷 +3%／點'),  # 2,2 v0.4 負責：DLL N3
    ('poison', '毒斷'): ('DONE', 'DLL native/include/Status.h（node::kPoisonSever）',
        'round 24（N5）照 v0.4 在 DLL：毒斷：融斷的催毒改為強度 ×4'),  # 2,2,0 v0.4 負責：DLL N5
    ('poison', '毒印記的融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstAgain[element]）',
        'round 24（N5）照 v0.4 在 DLL：毒印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('poison', '劇毒'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonVirulent）',
        'round 24（N5）照 v0.4 在 DLL：劇毒：催毒期間目標毒抗視為 0'),  # 2,3,0 v0.4 負責：DLL N3
    ('poison', '腐蝕終焉'): ('DONE', 'DLL native/include/Reactions.h（node::kPoisonRotEnd）',
        'round 24（N5）照 v0.4 在 DLL：腐蝕終焉：毒終焉後目標魔抗 -20% 8 秒'),  # 2,3,1 v0.4 負責：DLL N3
    ('poison', '催毒期間中毒傷害'): ('DONE', 'DLL native/include/Status.h（node::kSignature[kPoison]）',
        'round 22（N3）照 v0.4：催毒期間中毒傷害 +9%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('poison', '毒霧'): ('DONE', 'DLL native/include/Reactions.h Bodies::End（node::kPoisonFog）→ ESSB_Domain → StatusEngine.h RunOp 在融斷目標腳下施放 Spawn Hazard（ESSB_N6_Domain_Poison_<秒>，HAZD ESSB_N6_Hazard_Poison，引擎管壽命與數量，不再限 3 個）；native/include/Timer.h PlanDomainEnemy → Status.h rule::SpreadDoses（每秒擴散一劑）',
        "round 25（N6，裁定 R5）：毒霧的劑數併入照瘟疫與瘴氣：內部敵人每秒「擴散一劑」併進自己的中毒（強度 +1 劑、同一個 10 劑上限，d' = max(d − t, 12)）；v0.4 10.4 的待決已定，交文件修正"),  # 2,4,0 v0.4 負責：Papyrus（領域）；劑數併入：待決
    # ================= 5.11 水（water）
    ('water', '浸濕持續'): ('DONE', 'ESSBElem3.WetSeconds（Papyrus 浸濕）＋DLL 雨雪浸濕（固定時長法術 ESSB_Native_Soak_*，node::kWaterSoakDuration）',
        '浸濕 10 秒 +0.3 秒／點（只延長浸濕本身）；雨雪與站在水中的浸濕由 DLL 挑對應秒數的法術（指揮官裁定 R6）'),  # 0,0 v0.4 負責：DLL N3
    ('water', '清流'): ('DONE', 'DLL native/include/HitMath.h AddFlatHitNodes（node::kWaterClearStream）',
        '命中回復耐力 30（ESSB_WaterClearStamina）'),  # 0,0,0 v0.4 負責：DLL N2
    ('water', '長流每秒回復'): ('DONE', 'DLL native/include/Timer.h FlowFraction／PlanFormSecond（node::kWaterFlowRate）← Plugin.cpp FormSecondWork（計時器每秒）',
        '長流每秒回復生命與耐力 2.0% +0.2%／點（settings 可調）；round 25（N6）起在 DLL 計時器，另回水形態維持費 80% 的魔力（v0.4 1.1，Papyrus 以前沒做）'),  # 0,1 v0.4 負責：Papyrus
    ('water', '水壓'): ('DONE', 'DLL native/include/Status.h（node::kWaterPressure）',
        'round 22（N3）照 v0.4：水壓：命中浸濕目標 +1 水壓，每層水附傷 +10%'),  # 0,1,0 v0.4 負責：DLL N3
    ('water', '水盾'): ('DONE', 'PERK 進入點 0x24／0x29 ＋ DLL native/include/Hurt.h hurt::ShareOf（node::kWaterShield）',
        'round 23：水幕分擔 20% → 30%、每擋 1 點 1.5 → 1.0 魔力'),  # 0,1,2 v0.4 負責：引擎效果（PERK）＋DLL 受擊 N4
    ('water', '水壓每層水附傷'): ('DONE', 'DLL native/include/Status.h（node::kWaterPressureDamage）',
        'round 22（N3）照 v0.4：水壓每層水附傷 +3%／點'),  # 0,2 v0.4 負責：DLL N3
    ('water', '洗淨'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfHit（node::kWaterCleanse）＋ ESSBController.OnESSBCleanse → ApplyCleanse',
        'round 23：命中時清除自身一個負面效果，每 3 秒一次（判定與冷卻在 DLL；清除用控制器原本逐項 DispelSpell 的做法，不洗自己的增益）'),  # 0,2,0 v0.4 負責：DLL N4
    ('water', '同調每段長流回復'): ('DONE', 'DLL native/include/Timer.h FlowFraction（node::kWaterFlowSync）',
        '同調每段長流 +0.05%／點；round 25 起在 DLL'),  # 0,3 v0.4 負責：Papyrus
    ('water', '潮身'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kWaterTideBody）',
        'round 23：水幕把魔力扣到 0 的那一刻洗淨一次（不佔洗淨冷卻）並回復最大魔力 20%，每 30 秒一次'),  # 0,3,2 v0.4 負責：DLL 受擊 N4
    ('water', '淨化'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfHit ＋ ESSBController.ApplyCleanse(True)（node::kWaterPurify）',
        '淨化：洗淨改為清除全部負面效果（解毒 ＋ PO3 GetActiveEffects 掃帶敵對／有害旗標的外來效果）'),  # 0,3,1 v0.4 負責：DLL N4
    ('water', '長河'): ('DONE', 'DLL native/include/Timer.h FlowFraction／PlanFormSecond（node::kWaterLongRiver）＋ Plugin.cpp AlliesNear（6 公尺內同伴與召喚物最多 5 人，ESSB_UtilTarget_RestoreHealth／RestoreStamina）',
        '同調三段時長流再 +0.05%／點且作用於附近同伴（生命與耐力；魔力那份不給同伴）；round 25 起在 DLL'),  # 0,4 v0.4 負責：Papyrus
    ('water', '止水'): ('DONE', 'PERK 進入點 0x24／0x29 ＋ DLL native/include/Hurt.h hurt::ShareOf（node::kWaterStill）',
        'round 23：同調三段時水幕分擔再 +15%（配水盾 45%）'),  # 0,4,1 v0.4 負責：引擎效果（PERK）
    ('water', '開印時回復生命與耐力各最大值 0.3%／點'): ('DONE', 'DLL native/include/Reactions.h（node::kWaterOpenHeal）',
        'round 24（N5）照 v0.4 在 DLL：開印時回復生命與耐力各最大值 0.3%／點（15 點 4.5%）'),  # 1,0 v0.4 負責：DLL N3
    ('water', '廣佈'): ('DONE', 'DLL native/include/Reactions.h（node::kWaterSpread）',
        'round 24（N5）照 v0.4 在 DLL：廣佈：開印時浸濕擴散到附近 1 人（讀法見 round 24 決策 4）'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('water', '開印後 5 秒內水附傷'): ('DONE', 'DLL native/include/Status.h（node::kOpenProc[element]）',
        'round 22（N3）照 v0.4：開印後 5 秒內水附傷 +3%／點'),  # 1,1 v0.4 負責：DLL N3
    ('water', '深濕'): ('DONE', 'DLL native/include/Status.h（node::kWaterDeepSoak）',
        'round 22（N3）照 v0.4：深濕：開印時若下雨、下雪或你站在水中，目標水壓直接滿格（立即沖刷；需已取得水壓）'),  # 1,1,0 v0.4 負責：DLL N3
    ('water', '湧泉'): ('DONE', 'DLL native/include/Reactions.h（node::kWaterSpring）',
        'round 24（N5）照 v0.4 在 DLL：湧泉：開印時回復耐力 80'),  # 1,1,1 v0.4 負責：DLL N3
    ('water', '水印記持續'): ('DONE', 'DLL native/include/Status.h（node::kMarkDuration[element]）',
        'round 22（N3）照 v0.4：水印記持續 +0.2 秒／點'),  # 1,2 v0.4 負責：DLL N3
    ('water', '水臨強化'): ('DONE', 'DLL native/include/Reactions.h（node::kWaterAdventPlus）',
        'round 24（N5）照 v0.4 在 DLL：水臨強化：水臨時範圍內敵人浸濕，你立即清除全部負面效果並回滿魔力（開場就是滿的水幕）；清除你的負面效果經 ESSB_Cleanse 由 Papyrus 做'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N5
    ('water', '水臨'): ('DONE', 'DLL native/include/Reactions.h（node::kAdvent[element]）',
        'round 24（N5）照 v0.4 在 DLL：水臨，開水形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('water', '開印沖刷'): ('DONE', 'DLL native/include/Reactions.h（node::kWaterOpenWash）',
        'round 24（N5）照 v0.4 在 DLL：開印沖刷：開印額外驅散目標一個有時限的增益，每目標每 10 秒一次（獨立於水壓滿格的沖刷）'),  # 1,3,0 v0.4 負責：DLL N3
    ('water', '淨潮'): ('DONE', 'DLL native/include/Status.h（node::kWaterPurgeTide）',
        'round 22（N3）照 v0.4：淨潮：任何沖刷（水壓滿格、開印沖刷、退潮、洗滌）每清掉目標一個增益，你回復生命與魔力各 B_max ×2'),  # 1,3,2 v0.4 負責：DLL N3
    ('water', '開印效果'): ('DONE', 'DLL native/include/Status.h（node::kOpenEffect[element]）',
        'round 22（N3）照 v0.4：開印效果 +9%／點'),  # 1,4 v0.4 負責：DLL N3
    ('water', '汪洋之始'): ('DONE', 'DLL native/include/Status.h（node::kWaterOceanStart）',
        'round 22（N3）照 v0.4：汪洋之始：同調三段時開印的浸濕不會過期，直到被切掉'),  # 1,4,0 v0.4 負責：DLL N3
    ('water', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kEndMain[element]） ＋ ESSBElem.EndMult',
        'round 22（N3）照 v0.4：終焉 +6%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('water', '強引'): ('DONE', 'DLL native/include/Status.h（node::kWaterStrongGuide） ＋ ESSBElem3.EndWaterNodes',
        'round 22（N3）照 v0.4：強引：導引 ×1.5 → ×2.0（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0,0 v0.4 負責：DLL N3
    ('water', '水印記的融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstMain[element]）',
        'round 24（N5）照 v0.4 在 DLL：水印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('water', '退潮'): ('DONE', 'DLL native/include/Status.h（node::kWaterEbb）',
        'round 22（N3）照 v0.4：退潮：水印記被切或融斷時，對目標沖刷一次（不需水壓滿格，每目標 10 秒一次）'),  # 2,1,2 v0.4 負責：DLL N3（融斷 N5）
    ('water', '水斷'): ('DONE', 'DLL native/include/Reactions.h（node::kWaterSever）',
        'round 24（N5）照 v0.4 在 DLL：水斷：水印記融斷改為治療你並回復耐力'),  # 2,1,1 v0.4 負責：DLL N5
    ('water', '終焉後 5 秒內接管元素附傷'): ('DONE', 'DLL native/include/Status.h（node::kTakeover[element]）',
        'round 22（N3）照 v0.4：終焉後 5 秒內接管元素附傷 +3%／點'),  # 2,2 v0.4 負責：DLL N3
    ('water', '汪洋'): ('DONE', 'DLL native/include/Status.h（node::kWaterOcean）',
        'round 22（N3）照 v0.4：汪洋：水終焉時目標的浸濕延長到 30 秒（不需要水印記；水壓、爆燃、大潮照常讀它）'),  # 2,2,0 v0.4 負責：DLL N3
    ('water', '水印記的融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstAgain[element]）',
        'round 24（N5）照 v0.4 在 DLL：水印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('water', '大潮'): ('DONE', 'DLL native/include/Reactions.h（node::kWaterFlood）',
        'round 24（N5）照 v0.4 在 DLL：大潮：水終焉時範圍內所有浸濕目標都給接管元素導引'),  # 2,3,0 v0.4 負責：DLL N5
    ('water', '洗滌'): ('DONE', 'DLL native/include/Reactions.h（node::kWaterScour）',
        'round 24（N5）照 v0.4 在 DLL：洗滌：水終焉清除你所有負面效果，並驅散目標一個有時限的增益；清除你的負面效果經 ESSB_Cleanse 由 Papyrus 做'),  # 2,3,1 v0.4 負責：DLL N3
    ('water', '導引'): ('DONE', 'DLL native/include/Status.h（node::kSignature[kWater]） ＋ ESSBElem.SignatureMult',
        'round 22（N3）照 v0.4：導引 +9%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,4 v0.4 負責：DLL N3
    ('water', '潮池'): ('DONE', 'DLL native/include/Reactions.h Bodies::End（node::kWaterTidePool）→ ESSB_Domain → StatusEngine.h RunOp 在融斷目標腳下施放 Spawn Hazard（ESSB_N6_Domain_Water_<秒>，HAZD ESSB_N6_Hazard_Water，引擎管壽命與數量，不再限 3 個）；native/include/Timer.h PlanDomainSelf（回血回耐各 15、ESSB_Cleanse → ESSBController.ApplyCleanse）＋ PlanDomainEnemy（每秒沖刷一個增益：StatusEngine.h RunOp kWash 上限 1）',
        '水印記融斷後 5 秒水域：你在其中回血回耐並每秒洗淨一次；內部敵人每秒被沖刷一個增益（DLL 的精確判定，裁定 R5）；round 25 起全在 DLL，洗淨的施放照舊 Papyrus（round 23 決策 11）'),  # 2,4,0 v0.4 負責：Papyrus（領域；沖刷呼叫 DLL 原生函式）
    # ================= 5.12 黑暗（darkness）
    ('darkness', '詛咒每層抗性侵蝕'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkErosion）',
        'round 24（N5）照 v0.4 在 DLL：詛咒每層抗性侵蝕 -0.2%／點（-2% → -5%）'),  # 0,0 v0.4 負責：DLL N3
    ('darkness', '咒延'): ('DONE', 'DLL native/include/Status.h（node::kDarkLinger）',
        'round 22（N3）照 v0.4：咒延：詛咒 ≥3 層的目標，黑暗印記過期時續 4 秒（每目標一次），讓它死時還帶著印記'),  # 0,0,1 v0.4 負責：DLL N3
    ('darkness', '暗附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '暗附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('darkness', '懼咒'): ('DONE', 'DLL native/include/Status.h（node::kDarkFearCurse）',
        'round 22（N3）照 v0.4：懼咒：恐懼門檻 3 → 2 層'),  # 0,1,2 v0.4 負責：DLL N3
    ('darkness', '怨縛'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kDarkGrudge）',
        'round 23：詛咒目標打你時它的詛咒 +1，每目標 2 秒一次'),  # 0,1,3 v0.4 負責：DLL 受擊 N4
    ('darkness', '幻覺持續'): ('DONE', 'DLL native/include/Status.h（node::kDarkIllusionTime）',
        'round 22（N3）照 v0.4：幻覺持續 +0.1 秒／點（恐懼 2 → 3.5 秒、瘋狂 3 → 4.5 秒）'),  # 0,2 v0.4 負責：DLL N3
    ('darkness', '狂咒'): ('DONE', 'DLL native/include/Status.h（node::kDarkFrenzyCurse）',
        'round 22（N3）照 v0.4：狂咒：瘋狂門檻 5 → 4 層'),  # 0,2,1 v0.4 負責：DLL N3
    ('darkness', '同調每段暗附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段暗附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('darkness', '狂宴'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkFeast）',
        'round 24（N5）照 v0.4 在 DLL：狂宴：瘋狂中的敵人殺死的目標，視為帶黑暗印記死亡（詛咒門檻照常）；復生經 ESSB_Raise 由 Papyrus 施放（裁定 R4）'),  # 0,3,2 v0.4 負責：DLL N5（兇手判定見 10.3）
    ('darkness', '回魘'): ('DONE', 'DLL native/include/Status.h（node::kDarkEcho）',
        'round 22（N3）照 v0.4：回魘：恐懼或瘋狂結束時，目標詛咒 +2 層（幻覺醒來，詛咒更深）'),  # 0,3,3 v0.4 負責：DLL N3
    ('darkness', '深淵'): ('DONE', 'DLL native/include/Status.h（node::kDarkAbyss）',
        'round 22（N3）照 v0.4：深淵，同調三段時詛咒層上限 +1／每 3 點，滿層目標抗性可侵蝕到負值'),  # 0,4 v0.4 負責：DLL N3
    ('darkness', '亡衛'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkGuard）',
        'round 24（N5）照 v0.4 在 DLL：亡衛：同調三段時，你復生的僕從死亡時爆出 3 公尺 B_max ×1.0 暗傷，範圍內敵人詛咒 +2 層'),  # 0,4,1 v0.4 負責：DLL N5
    ('darkness', '開印詛咒'): ('DONE', 'DLL native/include/Status.h（node::kDarkOpenCurse）',
        'round 22（N3）照 v0.4：開印詛咒 +1 層／每 5 點'),  # 1,0 v0.4 負責：DLL N3
    ('darkness', '夢魘'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkNightmare）',
        'round 24（N5）照 v0.4 在 DLL：夢魘：目標恐懼時，3 公尺內其他敵人詛咒 +1（每次恐懼一次）'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('darkness', '開印後 5 秒內暗附傷'): ('DONE', 'DLL native/include/Status.h（node::kOpenProc[element]）',
        'round 22（N3）照 v0.4：開印後 5 秒內暗附傷 +3%／點'),  # 1,1 v0.4 負責：DLL N3
    ('darkness', '狂刃'): ('DONE', 'SPEL ESSB_N3_FrenzyBlade（AttackDamageMult +0.5）← ESSBController.ApplyFrenzy',
        '瘋狂中的目標造成的傷害 +50%（跟瘋狂同秒數的引擎效果；它也會更痛地打你）'),  # 1,1,2 v0.4 負責：引擎效果（掛在瘋狂 MGEF 上）
    ('darkness', '幻影'): ('DONE', 'DLL native/include/Status.h（node::kDarkPhantom：開印給目標 ESSB_N3_Phantom 3 秒）＋ PERK 進入點（受到的傷害 ×0，條件：攻擊者帶幻影、GetRandomPercent < 30）',
        '開印後 3 秒目標對你的命中 30% 落空：引擎沒有近戰命中率，改成每一擊 30% 機率傷害 ×0（條件每擊各評估一次；指揮官裁定 (c)）。探針卡有逐擊擲骰的步驟'),  # 1,1,1 v0.4 負責：DLL N3
    ('darkness', '暗印記持續'): ('DONE', 'DLL native/include/Status.h（node::kMarkDuration[element]）',
        'round 22（N3）照 v0.4：暗印記持續 +0.2 秒／點'),  # 1,2 v0.4 負責：DLL N3
    ('darkness', '暗臨強化'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkAdventPlus）',
        'round 24（N5）照 v0.4 在 DLL：暗臨強化：暗臨時範圍內敵人恐懼 2 秒；恐懼經 ESSB_Hallucinate 由 Papyrus 施放（裁定 R4）'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N5
    ('darkness', '暗臨'): ('DONE', 'DLL native/include/Reactions.h（node::kAdvent[element]）',
        'round 24（N5）照 v0.4 在 DLL：暗臨，開暗形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('darkness', '迷亂'): ('DONE', 'DLL native/include/Status.h（node::kDarkConfusion）',
        'round 22（N3）照 v0.4：迷亂：瘋狂中的目標被你命中時詛咒 +2 層'),  # 1,3,0 v0.4 負責：DLL N3
    ('darkness', '暗染'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkStain）',
        'round 24（N5）照 v0.4 在 DLL：暗染：開印時附近 1 人也詛咒（讀法見 round 24 決策 4）'),  # 1,3,1 v0.4 負責：DLL N3（掃描 N5）
    ('darkness', '開印效果'): ('DONE', 'DLL native/include/Status.h（node::kOpenEffect[element]）',
        'round 22（N3）照 v0.4：開印效果 +9%／點'),  # 1,4 v0.4 負責：DLL N3
    ('darkness', '群魔'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkLegion）',
        'round 24（N5）照 v0.4 在 DLL：群魔：同調三段時，目標達到瘋狂門檻那一刻，4 公尺內所有詛咒 ≥3 層的敵人一起瘋狂 3 秒（各自冷卻照算）；瘋狂經 ESSB_Hallucinate 由 Papyrus 施放（裁定 R4）（讀法見 round 24 決策 24）'),  # 1,4,0 v0.4 負責：DLL N3（掃描 N5）＋Papyrus
    ('darkness', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kEndMain[element]） ＋ ESSBElem.EndMult',
        'round 22（N3）照 v0.4：終焉 +6%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('darkness', '饕餮'): ('DONE', 'DLL native/include/Status.h（node::kDarkGlutton）',
        'round 22（N3）照 v0.4：饕餮：死咒結算時吸血吸魔各 B_max ×1.0'),  # 2,0,0 v0.4 負責：DLL N3
    ('darkness', '殘魂'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkRemnant）',
        'round 24（N5）照 v0.4 在 DLL：殘魂：帶黑暗印記死亡、但詛咒只有 1～2 層的敵人也有 25% 機率復生（依等級表的階級）；復生經 ESSB_Raise 由 Papyrus 施放（裁定 R4）'),  # 2,0,2 v0.4 負責：DLL N5＋Papyrus
    ('darkness', '暗印記的融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstMain[element]）',
        'round 24（N5）照 v0.4 在 DLL：暗印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('darkness', '不治'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkNoHeal）',
        'round 24（N5）照 v0.4 在 DLL：不治：死咒的無法治療延長到 6 秒'),  # 2,1,0 v0.4 負責：DLL N3
    ('darkness', '冥印'): ('DONE', 'DLL native/include/Status.h（node::kDarkNether）',
        'round 22（N3）照 v0.4：冥印：暗印記被切時，目標留下一顆 8 秒「冥印」，帶冥印死亡視同帶黑暗印記（切到別的元素收尾也能復生）'),  # 2,1,2 v0.4 負責：DLL N3
    ('darkness', '死咒的「已損失生命」係數'): ('DONE', 'DLL native/include/Status.h（node::kDarkCurseLost）',
        'round 22（N3）照 v0.4：死咒的「已損失生命」係數 +1.5%／點（15% → 37.5%）'),  # 2,2 v0.4 負責：DLL N3
    ('darkness', '亡魂'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkSoul）',
        'round 24（N5）照 v0.4 在 DLL：亡魂：死咒殺死目標時，附近敵人恐懼 2 秒；恐懼經 ESSB_Hallucinate 由 Papyrus 施放（裁定 R4）（讀法見 round 24 決策 18）'),  # 2,2,0 v0.4 負責：DLL N5
    ('darkness', '噬咒'): ('DONE', 'DLL native/include/Status.h（node::kDarkDevour）',
        'round 22（N3）照 v0.4：噬咒：死咒結算時消耗目標全部詛咒，每層讓「已損失生命」係數 +3%（吞了就不能拿這些層數換僕從）'),  # 2,2,2 v0.4 負責：DLL N3
    ('darkness', '暗印記的融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstAgain[element]）',
        'round 24（N5）照 v0.4 在 DLL：暗印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('darkness', '冥召'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkSummon）',
        'round 24（N5）照 v0.4 在 DLL：冥召：死咒殺死的目標必定復生（無視詛咒門檻與有無印記），僕從階級 +1（最高五階）；復生經 ESSB_Raise 由 Papyrus 施放（裁定 R4）（讀法見 round 24 決策 18）'),  # 2,3,2 v0.4 負責：DLL N5＋Papyrus
    ('darkness', '深淵回響'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkAbyssEcho）',
        'round 24（N5）照 v0.4 在 DLL：深淵回響：暗終焉回滿你的魔力'),  # 2,3,1 v0.4 負責：DLL N3
    ('darkness', '死咒'): ('DONE', 'DLL native/include/Status.h（node::kSignature[kDarkness]） ＋ ESSBElem.SignatureMult',
        'round 22（N3）照 v0.4：死咒 +9%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,4 v0.4 負責：DLL N3
    ('darkness', '死域'): ('DONE', 'DLL native/include/Reactions.h Bodies::End（node::kDarkDeathZone）→ ESSB_Domain → StatusEngine.h RunOp 在融斷目標腳下施放 Spawn Hazard（ESSB_N6_Domain_Darkness_<秒>，HAZD ESSB_N6_Hazard_Darkness，引擎管壽命與數量，不再限 3 個）；hazard 掛無法治療（ESSB_UtilEffect_HealRateDebuff 100）；native/include/Timer.h PlanDomainEnemy（每秒 B_max ×0.5 暗傷：D_react 2.7 × 持續傷害倍率）',
        '暗印記融斷後 5 秒死域：內部敵人無法被治療、每秒受 B_max ×0.5 暗傷；round 25 起傷害由 DLL 每秒算（hazard 的強度覆寫會蓋掉無法治療的強度）'),  # 2,4,0 v0.4 負責：Papyrus（領域）
    ('darkness', '死靈主'): ('DONE', 'DLL native/include/Reactions.h（node::kDarkLord）',
        'round 24（N5）照 v0.4 在 DLL：死靈主：同調三段時亡者歸來不需要詛咒門檻（帶黑暗印記或冥印即可），60 級以上也能復生，且任何等級的僕從可改為永久（六階，永久上限 1 名）；復生 AI 與召喚上限經 ESSB_Raise 由 Papyrus 做（裁定 R4）'),  # 2,4,1 v0.4 負責：DLL N5＋Papyrus
    # ================= 5.13 星界（astral）
    ('astral', '回聲比例'): ('DONE', 'DLL native/include/Reactions.h（node::kAstralEcho）',
        'round 24（N5）照 v0.4 在 DLL：回聲比例 +1%／點（25% → 40%，不吃節點倍率）'),  # 0,0 v0.4 負責：DLL N5
    ('astral', '星鏈'): ('DONE', 'DLL native/include/Reactions.h（node::kAstralChain）',
        'round 24（N5）照 v0.4 在 DLL：星鏈：被回聲打到的共鳴目標星痕 +1 層（不重新計時，每目標每 2 秒一次）'),  # 0,0,1 v0.4 負責：DLL N5
    ('astral', '星附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '星附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('astral', '聚星'): ('DONE', 'DLL native/include/Reactions.h（node::kAstralGather）',
        'round 24（N5）照 v0.4 在 DLL：聚星：引爆當下若 15 公尺內共鳴目標 ≥3，這次引爆 +30%'),  # 0,1,2 v0.4 負責：DLL N3（計數 N5）
    ('astral', '星痕層數上限'): ('DONE', 'DLL native/include/Status.h StarCap（node::kAstralCap）',
        '星痕層數上限 +1／每 5 點（也提高闇星每一擊的上限；闇星是 N4）'),  # 0,2 v0.4 負責：DLL N3
    ('astral', '星痕弱點'): ('DONE', 'DLL native/include/Status.h（node::kAstralWeakness）',
        'round 22（N3）照 v0.4：星痕弱點：重擊時每層星痕 +8%（闇星一擊以星痕上限計）'),  # 0,2,0 v0.4 負責：DLL N3
    ('astral', '同調每段星附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段星附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('astral', '餘輝'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfHit（node::kAstralAfterglow）',
        'round 23：闇宙用完回到一般形態時得到 3 層共鳴層'),  # 0,3,2 v0.4 負責：DLL N4
    ('astral', '永夜'): ('DONE', 'DLL native/include/Status.h res::DarkStrike（node::kAstralEternal）',
        'round 23：闇星每一擊 +3%／點'),  # 0,4 v0.4 負責：DLL N4
    ('astral', '星蝕'): ('DONE', 'DLL native/include/Reactions.h（node::kAstralEclipse）',
        'round 24（N5）照 v0.4 在 DLL：星蝕：闇星中每一擊的傷害，另以 50% 回聲到所有其他共鳴目標（最多 5）'),  # 0,4,1 v0.4 負責：DLL N5
    ('astral', '天穹'): ('DONE', 'DLL native/include/Status.h res::ResonanceGate（node::kAstralDome）',
        'round 23：同調三段時升闇星的門檻 10 → 7'),  # 0,4,2 v0.4 負責：DLL N4
    ('astral', '星痕延遲'): ('DONE', 'DLL native/include/Status.h rule::StarDelay（node::kAstralDelay）',
        '星痕延遲 -0.1 秒／點（2 → 0.5 秒）：停手這麼久沒被直接命中，全部一起引爆'),  # 1,0 v0.4 負責：DLL N3
    ('astral', '星散'): ('DONE', 'DLL native/include/Reactions.h（node::kAstralScatter）',
        'round 24（N5）照 v0.4 在 DLL：星散：開印時附近 1 人也星痕（也進入共鳴）（讀法見 round 24 決策 4）'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('astral', '開印後 5 秒內星附傷'): ('DONE', 'DLL native/include/Status.h（node::kOpenProc[element]）',
        'round 22（N3）照 v0.4：開印後 5 秒內星附傷 +3%／點'),  # 1,1 v0.4 負責：DLL N3
    ('astral', '明星'): ('DONE', 'DLL native/include/Reactions.h（node::kAstralBright）',
        'round 24（N5）照 v0.4 在 DLL：明星：開印時若 15 公尺內已有其他共鳴目標，新目標與最近的那一個星痕各 +1'),  # 1,1,0 v0.4 負責：DLL N3（掃描 N5）
    ('astral', '星印記持續'): ('DONE', 'DLL native/include/Status.h（node::kMarkDuration[element]）',
        'round 22（N3）照 v0.4：星印記持續 +0.2 秒／點'),  # 1,2 v0.4 負責：DLL N3
    ('astral', '星臨強化'): ('DONE', 'DLL native/include/Reactions.h（node::kAstralAdventPlus）',
        'round 24（N5）照 v0.4 在 DLL：星臨強化：星臨時範圍內敵人星痕 2 層（全部進入共鳴）'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N5
    ('astral', '星臨'): ('DONE', 'DLL native/include/Reactions.h（node::kAdvent[element]）',
        'round 24（N5）照 v0.4 在 DLL：星臨，開星形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('astral', '星鎖'): ('DONE', 'DLL native/include/Status.h（node::kAstralLock）',
        'round 22（N3）照 v0.4：星鎖：開印目標 3 秒內受所有元素傷 +10%（DLL 做狀態與倍率；round 24 起反應本體也在 DLL；round 25 起 Papyrus 已沒有自己的傷害，ESSBElem3.TargetDamageMult 刪除）'),  # 1,3,0 v0.4 負責：DLL N3＋引擎效果
    ('astral', '星門'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kAstralGate）',
        'round 23：開印 +1 共鳴層（闇星中無效）'),  # 1,3,2 v0.4 負責：DLL N4
    ('astral', '開印效果'): ('DONE', 'DLL native/include/Status.h（node::kOpenEffect[element]）',
        'round 22（N3）照 v0.4：開印效果 +9%／點'),  # 1,4 v0.4 負責：DLL N3
    ('astral', '星耀'): ('DONE', 'DLL native/include/Status.h（node::kAstralRadiance）',
        'round 22（N3）照 v0.4：星耀：同調三段時開印的延遲星傷改為立即並 ×2（這次引爆照常給共鳴層）'),  # 1,4,0 v0.4 負責：DLL N3
    ('astral', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kEndMain[element]） ＋ ESSBElem.EndMult',
        'round 22（N3）照 v0.4：終焉 +6%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('astral', '隕星'): ('DONE', 'DLL native/include/Reactions.h（node::kAstralMeteor）',
        'round 24（N5）照 v0.4 在 DLL：隕星：星落 ×2.0 → ×3.0'),  # 2,0,0 v0.4 負責：DLL N3
    ('astral', '星印記的融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstMain[element]）',
        'round 24（N5）照 v0.4 在 DLL：星印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('astral', '星斷'): ('DONE', 'DLL native/include/Reactions.h（node::kAstralSever）',
        'round 24（N5）照 v0.4 在 DLL：星斷：星印記融斷改為真實傷害，倍率 ×0.6'),  # 2,1,1 v0.4 負責：DLL N5
    ('astral', '終焉後 5 秒內接管元素附傷'): ('DONE', 'DLL native/include/Status.h（node::kTakeover[element]）',
        'round 22（N3）照 v0.4：終焉後 5 秒內接管元素附傷 +3%／點'),  # 2,2 v0.4 負責：DLL N3
    ('astral', '星殘'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfLeave（node::kAstralRemnant）',
        'round 23：離開星形態時共鳴層保留 15 秒'),  # 2,2,1 v0.4 負責：Papyrus＋DLL N4
    ('astral', '星印記的融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kBurstAgain[element]）',
        'round 24（N5）照 v0.4 在 DLL：星印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('astral', '墜星'): ('DONE', 'DLL native/include/Reactions.h／native/include/SelfLayer.h（node::kAstralFalling）',
        'round 24（N5）照 v0.4 在 DLL：墜星：闇星中切換時剩下的闇宙留到被切那一擊，每層對該目標結算一次 ×0.5 闇星一擊；闇星中按 Z 時，剩下的闇宙平均分給範圍內帶星印記的目標，同樣每層 ×0.5'),  # 2,3,2 v0.4 負責：DLL N4（融斷 N5）
    ('astral', '星落'): ('DONE', 'DLL native/include/Reactions.h／native/include/Status.h（node::kSignature[element]）',
        'round 24（N5）照 v0.4 在 DLL：星落 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('astral', '星域'): ('DONE', 'DLL native/include/Reactions.h Bodies::End（node::kAstralZone）→ ESSB_Domain → StatusEngine.h RunOp 在融斷目標腳下施放 Spawn Hazard（ESSB_N6_Domain_Astral_<秒>，HAZD ESSB_N6_Hazard_Astral，引擎管壽命與數量，不再限 3 個）；hazard 掛 ESSB_N3_DomainAstralEffect（受所有元素傷 +20%：附傷與 DLL 反應讀它）',
        '星印記融斷後 5 秒星域（3 公尺），內部敵人受所有元素傷 +20%；round 25 起是引擎的 hazard'),  # 2,4,0 v0.4 負責：Papyrus（領域）
    # ================= 5.1 無元素：法殺（noform）
    ('noform', '吸魔量'): ('DONE', 'DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormSiphonAmount）',
        '吸魔量 +5%／點（不吃節點倍率，×1.0 → ×1.75），指揮官裁定 R5；v0.3 的「無形態武器傷害」進入點與 RefreshWeaponPercent 已刪'),  # 0,0 v0.4 負責：DLL N2
    ('noform', '逼近'): ('DONE', 'DLL native/include/Hurt.h PlanSpellCast ← Plugin.cpp 施法事件（node::kNoFormCloseIn）',
        'round 23：15 公尺內敵人施法時 2 秒移速 +30%、化法為力 ×2，每 6 秒一次'),  # 0,0,1 v0.4 負責：DLL N4（施法事件）＋引擎效果
    ('noform', '超載上限'): ('DONE', 'DLL native/include/Status.h res::OverloadCap（node::kNoFormOverloadCap）',
        'round 23：超載上限 +2%／點（50% → 80%）'),  # 0,1 v0.4 負責：DLL N4
    ('noform', '蓄流'): ('DONE', 'DLL native/include/Status.h res::SetOverload（node::kNoFormAccumulate）',
        'round 23：超載開始衰減前的等待 3 → 6 秒'),  # 0,1,2 v0.4 負責：DLL N4
    ('noform', '反擊'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kNoFormRiposte）＋ HitMath.h（吸魔 ×2）',
        'round 23：格擋偵測在 DLL 受擊（kHitBlocked），掛 3 秒反擊視窗；下一次無形態命中吸魔 ×2 並移除（N2 那一半）'),  # 0,1,0 v0.4 負責：DLL 受擊 N4＋DLL N2
    ('noform', '法盾效率'): ('DONE', 'DLL native/include/Hurt.h hurt::ShareOf（node::kNoFormShieldCost）',
        'round 23：法盾每擋 1 點花的魔力 -2%／點'),  # 0,2 v0.4 負責：DLL 受擊 N4
    ('noform', '化勁'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kNoFormTransmute）',
        'round 23：化法為力 30% → 60%'),  # 0,2,1 v0.4 負責：DLL 受擊 N4
    ('noform', '法盾分擔'): ('DONE', 'PERK 主線進入點 0x24／0x29 ＋ DLL native/include/Hurt.h hurt::ShareOf（node::kNoFormShieldShare）',
        'round 23：法盾分擔 +1%／點（30% → 45%；超載 45% → 60%）'),  # 0,3 v0.4 負責：引擎效果（PERK）
    ('noform', '不屈'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kNoFormUnyield）',
        'round 23：被命中時戰意 +1（每 3 秒一次），重設 10 秒歸零計時'),  # 0,3,1 v0.4 負責：DLL 受擊 N4
    ('noform', '餘魔'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kNoFormLinger）＋ PERK 進入點 0x24／0x29',
        'round 23：法盾把魔力扣到 0 的那一刻再以 30% 分擔 2 秒（改扣耐力），每 30 秒一次'),  # 0,3,2 v0.4 負責：DLL 受擊 N4＋引擎效果
    ('noform', '不竭'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfSecond（node::kNoFormEndless）',
        'round 23：超載衰減每秒 -0.2%／點（5% → 最低 2%）'),  # 0,4 v0.4 負責：DLL N4
    ('noform', '破式'): ('DONE', 'DLL native/include/HitMath.h PlanNoFormHit ＋ SelfLayer.h PlanSelfNoForm（node::kNoFormBreak）',
        'round 23：戰意滿層的重擊消耗全部戰意，這一次滅法不花魔力（X 照算）、倍率 +1.0、沉默 2 秒'),  # 0,4,1 v0.4 負責：DLL N4
    ('noform', '無魔'): ('DONE', 'DLL native/include/Reactions.h（node::kNoFormNoMana）',
        'round 24（N5）照 v0.4 在 DLL：無魔：擊殺施法者回滿耐力與魔力（溢出進超載）（讀法見 round 24 決策 15）'),  # 0,4,2 v0.4 負責：DLL N5
    ('noform', '滅法倍率'): ('DONE', 'DLL native/include/HitMath.h DispelMultiplier（node::kNoFormDispelRate）',
        '滅法倍率 +2%／點（不吃節點倍率，×1.0 → ×1.3；小滅法同一個倍率），指揮官裁定 R5'),  # 1,0 v0.4 負責：DLL N2
    ('noform', '奪魔'): ('DONE', 'DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormSeize）',
        '吸魔量取固定值與目標最大魔力 10% 較高者'),  # 1,0,0 v0.4 負責：DLL N2
    ('noform', '燒魔倍數'): ('DONE', 'DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormBurnMultiple）',
        '燒魔倍數 +7%／點（Y 最多是 X 的 1.0 → 2.05 倍），指揮官裁定 R5'),  # 1,1 v0.4 負責：DLL N2
    ('noform', '斷咒'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfNoForm（node::kNoFormInterrupt）',
        'round 23：命中施法中的敵人（DLL 讀 magicCasters 的狀態）打斷其施法，每 5 秒一次，戰意 +1（戰意是 DLL 的效果，10 秒未命中歸零）'),  # 1,1,0 v0.4 負責：DLL N4
    ('noform', '反咒'): ('DONE', 'DLL native/include/Hurt.h PlanSpellCast ← Plugin.cpp TESSpellCastEvent（node::kNoFormCounter）',
        'round 23（R7）：帶破魔印的敵人施法時受該次施法消耗魔力（CalculateMagickaCost）×(1+0.02×無元素樹等級) 的真實傷害（不再乘 G(L)，決策），戰意 +1'),  # 1,1,2 v0.4 負責：DLL N4
    ('noform', '沉默'): ('DONE', 'DLL native/include/HitMath.h SilenceSeconds（node::kNoFormSilence）',
        '沉默 1 秒 +0.2 秒／點（最多 4 秒；首領減半、乘持續時間倍率，固定時長法術 1～8 秒）'),  # 1,2 v0.4 負責：DLL N2
    ('noform', '枯竭'): ('DONE', 'DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormDepletion）',
        '目標沒有魔力時滅法改燒你自己 2 倍的 X（round 20 D18）'),  # 1,2,0 v0.4 負責：DLL N2
    ('noform', '靜寂'): ('DONE', 'DLL native/include/HitMath.h TrueDamageMultiplier（node::kNoFormStillness）',
        '沉默中的目標受真實傷害 ×1.5'),  # 1,2,1 v0.4 負責：DLL N2
    ('noform', '對施法者與帶魔法護盾、元素披風的敵人燒魔'): ('DONE', 'DLL native/include/HitMath.h BurnBonus（node::kNoFormBurnCasters）',
        '對施法者燒魔 +5%／點'),  # 1,3 v0.4 負責：DLL N2
    ('noform', '破護'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kNoFormCloakBreak）＋ PERK ESSB_P_noform_1_3_B1 進入點 0x29',
        'round 23：DLL 認出披風那一跳，掛 2 秒 ESSB_N4_CloakGuardEffect 並逐跳刷新；第一跳仍會吃到'),  # 1,3,0 v0.4 負責：DLL 受擊 N4
    ('noform', '咒返'): ('DONE', 'DLL native/include/Hurt.h PlanHurt（node::kNoFormSpellReturn）',
        'round 23：受到法術傷害時對施法者施加滅法印，每 5 秒一次'),  # 1,3,2 v0.4 負責：DLL 受擊 N4
    ('noform', '目標魔力低於 25% 時命中傷害'): ('DONE', 'DLL native/include/HitMath.h TrueDamageMultiplier（node::kNoFormLowMagicka）',
        '目標魔力 <25% 時命中傷害 +3%／點'),  # 1,4 v0.4 負責：DLL N2
    ('noform', '噬命'): ('DONE', 'DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormDevour）＋ESSBController.ApplyTrueDamage（Papyrus 真傷）',
        '真實傷害的 50% 轉為你的生命'),  # 1,4,1 v0.4 負責：DLL N2
    ('noform', '封印'): ('DONE', 'DLL native/include/Reactions.h／native/src/Plugin.cpp（node::kNoFormSeal）',
        'round 24（N5）照 v0.4 在 DLL：封印：沉默改為 3 公尺範圍'),  # 1,4,2 v0.4 負責：DLL N5
    ('noform', '融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kNoFormBurst）',
        'round 24（N5）照 v0.4 在 DLL：融斷 +2%／點'),  # 2,0 v0.4 負責：DLL N5
    ('noform', '免門檻'): ('DONE', 'ESSBNoForm.OnBurst → ESSBController.SetFreeOpen',
        '融斷後下一次開形態不需魔力'),  # 2,0,0 v0.4 負責：Papyrus
    ('noform', '寂每層燒魔'): ('DONE', 'DLL native/include/Reactions.h（node::kNoFormHushBurn）',
        'round 24（N5）照 v0.4 在 DLL：寂每層燒魔 +0.5%／點（5% → 12.5%）（讀法見 round 24 決策 14）'),  # 2,1 v0.4 負責：DLL N5
    ('noform', '收束'): ('DONE', 'DLL native/include/Reactions.h（node::kNoFormGather）',
        'round 24（N5）照 v0.4 在 DLL：收束：融斷範圍 15 → 20 公尺'),  # 2,1,0 v0.4 負責：DLL N5
    ('noform', '寂滅'): ('DONE', 'DLL native/include/HitMath.h（node::kNoFormHushBreak）',
        'round 24（N5）照 v0.4 在 DLL：寂滅：寂 ≥3 層的目標，你對它的下一次滅法倍率 +0.5'),  # 2,1,2 v0.4 負責：DLL N2
    ('noform', '融斷範圍'): ('DONE', 'DLL native/include/Reactions.h（node::kNoFormBurstRadius）',
        'round 24（N5）照 v0.4 在 DLL：融斷範圍 +0.3 公尺／點'),  # 2,2 v0.4 負責：DLL N5
    ('noform', '連斷'): ('DONE', 'ESSBNoForm.OnBurst → ESSBController.SetSyncKeep → ESSBNative.SetSync',
        '融斷後 5 秒內重開形態保留一半同調（保留量 Papyrus 決定，同調是 DLL 的效果）'),  # 2,2,0 v0.4 負責：Papyrus＋DLL N4
    ('noform', '寂上限'): ('DONE', 'DLL native/include/Reactions.h（node::kNoFormHushCap）',
        'round 24（N5）照 v0.4 在 DLL：寂上限 +1／每 5 點（5 → 8）（讀法見 round 24 決策 14）'),  # 2,3 v0.4 負責：DLL N5
    ('noform', '斷界'): ('DONE', 'DLL native/include/Reactions.h（node::kNoFormSever）',
        'round 24（N5）照 v0.4 在 DLL：斷界：融斷後對範圍內敵人施加所有被結清元素的弱化 3 秒（讀法見 round 24 決策 10）'),  # 2,3,0 v0.4 負責：DLL N5
    ('noform', '回流'): ('DONE', 'DLL native/include/Reactions.h（node::kNoFormBackflow）',
        'round 24（N5）照 v0.4 在 DLL：回流：融斷回復你魔力，每個印記 B_max ×0.5（可以灌進超載）'),  # 2,3,1 v0.4 負責：DLL N5
    ('noform', '融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kNoFormBurstAgain）',
        'round 24（N5）照 v0.4 在 DLL：融斷再 +3%／點'),  # 2,4 v0.4 負責：DLL N5
    ('noform', '雙斷'): ('DONE', 'DLL native/include/Reactions.h（node::kNoFormDoubleBurst）',
        'round 24（N5）照 v0.4 在 DLL：雙斷：融斷後 3 秒內再次按 Z 開任一形態，會對範圍內敵人立即開印一次'),  # 2,4,0 v0.4 負責：Papyrus＋DLL N5
    ('noform', '萬寂'): ('DONE', 'DLL native/include/Reactions.h（node::kNoFormAllHush）',
        'round 24（N5）照 v0.4 在 DLL：萬寂：融斷時寂 ≥3 層的目標身上其他元素狀態（凍結、詛咒、血痕、中毒、水壓、星痕等）全部清除，每清一種寂 +1，並轉為一次「該元素 B_max ×0.5」的真實傷害（讀法見 round 24 決策 14）'),  # 2,4,1 v0.4 負責：DLL N5
    # ================= 5.2 全元素通用（common）
    ('common', '同調門檻'): ('DONE', 'DLL native/include/Status.h res::Thresholds（node::kCommonSyncThreshold）',
        'round 23：同調門檻 -2%／點，下限 0.4 倍'),  # 0,0 v0.4 負責：DLL N4
    ('common', '承接'): ('DONE', 'ESSBNodes.CarryOverSync → ESSBController.SwitchForm → ESSBNative.SetSync',
        '切換保留前一形態 1/3 同調（保留量 Papyrus 決定，同調是 DLL 的效果）'),  # 0,0,0 v0.4 負責：Papyrus＋DLL N4
    ('common', '同調二段時附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kCommonStage2）＋ESSBNodes.CommonHitMult 鏡像',
        '同調二段時附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('common', '不移'): ('DONE', 'PERK ESSB_P_common_0_1_B1 進入點 0x21（受到的擊退 ×0，條件 ESSB_SyncStage ≥2）',
        '同調二段以上時免疫硬直（受到的擊退幅度 ×0）；「擊倒」由同一個進入點涵蓋擊退造成的倒地，ragdoll 類擊倒引擎沒有進入點'),  # 0,1,0 v0.4 負責：引擎效果
    ('common', '專一'): ('DONE', 'DLL native/include/Status.h res::Thresholds（node::kCommonFocus；ESSB_N4_FormHeld 的經過時間）',
        'round 23：同一形態 60 秒後門檻再 ×0.5'),  # 0,1,1 v0.4 負責：引擎效果（60 秒效果）＋DLL N4
    ('common', '同調三段時終焉'): ('DONE', 'DLL native/include/Status.h（node::kCommonSyncEnd）',
        'round 22（N3）照 v0.4：同調三段時終焉 +3%／點'),  # 0,2 v0.4 負責：DLL N3（融斷 N5）
    ('common', '定神'): ('DONE', 'DLL native/include/Timer.h SlowImmune（node::kCommonComposure）← Plugin.cpp SlowImmunity（每 tick 驅散你身上的減速）',
        '同調三段時免疫減速（自有）；round 25：以前是沒人呼叫的 Papyrus 守衛 ESSBNodes.SelfSlowImmune（假 DONE），現在 DLL 做'),  # 0,2,0 v0.4 負責：引擎效果
    ('common', '同調三段時重擊附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kCommonStage3Power）＋ESSBNodes.CommonHitMult 鏡像',
        '同調三段時重擊附傷 +2%／點'),  # 0,3 v0.4 負責：DLL N2
    ('common', '極致'): ('DONE', 'DLL native/include/SelfLayer.h PlanSelfHit ＋ Plugin.cpp ExtraProc（node::kCommonExtreme）',
        'round 23：同調三段每 10 次命中多一次全額附傷（計數是你身上的 ESSB_N4_Extreme）'),  # 0,3,0 v0.4 負責：DLL N4
    ('common', '回饋'): ('DONE', 'DLL native/include/Status.h res::SetSync（node::kCommonFeedback）',
        'round 23：升段時回復生命與魔力各 B_max（形態元素）×2'),  # 0,3,1 v0.4 負責：DLL N4
    ('common', '化身'): ('DONE', 'DLL native/include/SelfLayer.h（node::kCommonAvatar）',
        'round 24（N5）照 v0.4 在 DLL：化身，同調三段時 30 秒冷卻（-1 秒／點）完成後的下一次命中，自動觸發當前元素的持續傳奇效果；若該效果屬於被動數值（如絕對零度、深淵），化身改為讓你在接下來 10 秒內視同已取得該效果（讀法見 round 24 決策 12）'),  # 0,4 v0.4 負責：DLL N4
    ('common', '永續'): ('DONE', 'ESSBNodes.HasPerpetual → ESSBController.OnFormClosed → SwitchForm → ESSBNative.SetSync',
        '三段時融斷後保留一段同調（保留量 Papyrus 決定，同調是 DLL 的效果）'),  # 0,4,0 v0.4 負責：Papyrus＋DLL N4
    ('common', '所有元素附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kCommonAll1）＋ESSBNodes.CommonHitMult 鏡像',
        '所有元素附傷 +1%／點'),  # 1,0 v0.4 負責：DLL N2
    ('common', '跳印'): ('DONE', 'DLL native/include/Status.h（node::kCommonJump）',
        'round 22（N3）照 v0.4：跳印：印記自然過期時，過期終焉照常結算，然後印記跳到 6 公尺內最近一個沒有印記的敵人身上（剩 4 秒、不觸發開印），每個印記只跳一次'),  # 1,0,1 v0.4 負責：DLL N3（掃描 N5）
    ('common', '印記持續'): ('DONE', 'DLL native/include/Status.h（node::kCommonMarkDuration）',
        'round 22（N3）照 v0.4：印記持續 +0.2 秒／點'),  # 1,1 v0.4 負責：DLL N3
    ('common', '順轉'): ('DONE', 'DLL native/include/Timer.h PlanSwitch（node::kCommonSmoothSwitch：開形態免魔力門檻）← Plugin.cpp RequestSwitch（熱鍵與 ESSBNative.RequestSwitch）＋ ESSBController.SwitchForm（SetGuardSwitch）+ PERK ESSB_P_common_1_1_B1 進入點 0x24（ESSB_GuardSwitch）',
        '開形態免魔力門檻；切換後 1 秒受傷 -50%；round 25 起門檻在 DLL 的切換函式'),  # 1,1,0 v0.4 負責：Papyrus＋引擎效果
    ('common', '先制'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kCommonPreempt）',
        'round 23：開印 +2 同調'),  # 1,1,1 v0.4 負責：DLL N4
    ('common', '開印時'): ('DONE', 'DLL native/include/SelfLayer.h res::OpenGains（node::kCommonOpenSync）',
        'round 23：開印 +1 同調／每 5 點'),  # 1,2 v0.4 負責：DLL N4
    ('common', '雙印'): ('DONE', 'DLL native/include/Status.h（node::kCommonDualMark）',
        'round 22（N3）照 v0.4：雙印：目標可同時帶兩種元素印記，被切掉時只結算較舊的那個'),  # 1,2,0 v0.4 負責：DLL N3
    ('common', '所有元素附傷再'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kCommonAll2）＋ESSBNodes.CommonHitMult 鏡像',
        '所有元素附傷再 +1%／點'),  # 1,3 v0.4 負責：DLL N2
    ('common', '印潮'): ('DONE', 'DLL native/include/Reactions.h／native/src/Plugin.cpp（node::kCommonSurge）',
        'round 24（N5）照 v0.4 在 DLL：印潮：切換後那一擊的開印，同時讓 15 公尺內帶著同一個舊印記的其他目標各觸發一次新元素的開印（最多 2 人；與大協奏對稱：大協奏傳終焉，印潮傳開印）'),  # 1,3,2 v0.4 負責：DLL N5
    ('common', '臨界'): ('DONE', 'DLL native/include/Reactions.h（node::kCommonThreshold）',
        'round 24（N5）照 v0.4 在 DLL：臨界：開形態那一刻附近敵人減速 30% 2 秒'),  # 1,3,1 v0.4 負責：Papyrus＋DLL N5
    ('common', '每種元素狀態上限'): ('DONE', 'DLL native/include/Status.h（node::kCommonCapBonus） ＋ ESSBNodes.StatusCapBonus',
        'round 22（N3）照 v0.4：每種元素狀態上限 +1 層／每 5 點（最多 +3）（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 1,4 v0.4 負責：DLL N3／N4
    ('common', '萬象'): ('DONE', 'DLL native/include/Status.h（node::kCommonOmni） ＋ ESSBNodes.OmniMult',
        'round 22（N3）照 v0.4：萬象：所有元素狀態的層數效果 +25%（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 1,4,0 v0.4 負責：DLL N3／N4
    ('common', '終焉'): ('DONE', 'DLL native/include/Status.h（node::kCommonEnd） ＋ ESSBNodes.CommonEndMult',
        'round 22（N3）照 v0.4：終焉 +3%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('common', '餘響'): ('DONE', 'DLL native/include/HitMath.h EchoRatio（node::kCommonEcho）＋ESSBNodes.EchoRatio（切換時掛待發標記）',
        '切換後首次命中附帶前一元素 50% 附傷'),  # 2,0,0 v0.4 負責：DLL N2
    ('common', '融斷'): ('DONE', 'DLL native/include/Reactions.h（node::kCommonBurst）',
        'round 24（N5）照 v0.4 在 DLL：融斷 +1%／點'),  # 2,1 v0.4 負責：DLL N5
    ('common', '反哺'): ('DONE', 'DLL native/include/Reactions.h（node::kCommonFeed）',
        'round 24（N5）照 v0.4 在 DLL：反哺：每次終焉回復你 B_max 魔力'),  # 2,1,0 v0.4 負責：DLL N3（融斷 N5）
    ('common', '疊印'): ('DONE', 'DLL native/include/Status.h（node::kCommonResidual）',
        'round 22（N3）照 v0.4：疊印：終焉後舊印記保留 4 秒為副印記，Z 融斷時可再結算一次'),  # 2,1,1 v0.4 負責：DLL N3
    ('common', '切換後首次命中附帶前一元素附傷'): ('DONE', 'DLL native/include/HitMath.h EchoRatio（node::kCommonEchoRatio）',
        '切換後首次命中附帶前一元素附傷 +3%／點'),  # 2,2 v0.4 負責：DLL N2
    ('common', '連鎖終焉'): ('DONE', 'DLL native/include/Reactions.h（node::kCommonChainEnd）',
        'round 24（N5）照 v0.4 在 DLL：連鎖終焉：終焉時附近帶同一印記的目標也終焉 ×0.5'),  # 2,2,0 v0.4 負責：DLL N5
    ('common', '三重奏'): ('DONE', 'DLL native/include/Status.h res::EndExtra（node::kCommonTrio）＋ ESSBController.OnFormClosed（碼 51）',
        'round 23：10 秒內三種不同元素終焉，第三次 ×3（DLL 結算的終焉傷害與 Papyrus 本體都吃），下一次融斷保留全部同調'),  # 2,2,1 v0.4 負責：DLL N3／N5
    ('common', '終焉再'): ('DONE', 'DLL native/include/Status.h（node::kCommonEndAgain） ＋ ESSBNodes.CommonEndMult',
        'round 22（N3）照 v0.4：終焉再 +3%／點（DLL 做狀態與倍率；round 24 起反應本體也在 DLL）'),  # 2,3 v0.4 負責：DLL N3（融斷 N5）
    ('common', '協奏'): ('DONE', 'DLL native/include/Status.h res::EndExtra ＋ DLL native/include/SelfLayer.h PlanSelfLeave（node::kCommonConcert）',
        'round 23：切換後首次終焉 ×1.5（DLL 結算與 Papyrus 本體都吃）；大協奏讀終焉事件的旗標'),  # 2,3,0 v0.4 負責：DLL N3
    ('common', '安全閥'): ('DONE', 'DLL native/include/Reactions.h（node::kCommonSafety）',
        'round 24（N5）照 v0.4 在 DLL：安全閥：融斷時你受傷 -50% 持續 2 秒；減傷是 PERK ESSB_P_common_2_3_B2 進入點 0x24 讀 ESSB_N5_SafetyValve'),  # 2,3,1 v0.4 負責：引擎效果（N5 掛上）
    ('common', '融斷再'): ('DONE', 'DLL native/include/Reactions.h（node::kCommonBurstAgain）',
        'round 24（N5）照 v0.4 在 DLL：融斷再 +2%／點'),  # 2,4 v0.4 負責：DLL N5
    ('common', '大協奏'): ('DONE', 'DLL native/include/Reactions.h（node::kCommonGrand）',
        'round 24（N5）照 v0.4 在 DLL：大協奏：切換後首次終焉讓範圍內帶舊印記的敵人各觸發一次該印記的終焉'),  # 2,4,0 v0.4 負責：DLL N5
    ('common', '雙生'): ('DONE', 'DLL native/include/HitMath.h PlanElementHit（雙生視窗）＋ESSBNodes.HasTwin → ESSBController.OnFormSwitched',
        '雙持時左手另帶前一形態元素 30 秒'),  # 2,4,1 v0.4 負責：DLL N2
}

# ------------------------------------------------------------------ 共通機制（1.1／2.x；v0.3 起的歷史列，不是技能樹節點）
IMPL = 'IMPLEMENTED'
DEF = 'DEFERRED'
REMOVED = 'REMOVED'      # round 21：v0.4 已拿掉的 v0.3 共通規則
LATER_N5 = 'LATER-N5'    # round 21：提前移除，N5 以 v0.4 版本重做（裁定 C3）

MECHANISMS = [
    ('fix8 addition', '無形態基礎真傷（文件化新增，非規劃節點）', IMPL,
     'ESSBController.OnWeaponHit → OnNoFormHit → ApplyNoFormBaseline → ApplyTrueDamage',
     '使用者核准新增：每次通過元素附傷共用資格檢查的無形態命中，'
     'noform_base_true（預設 5）× G(L_無元素) × ESSB_BaseDamageMult；重擊 ×1.5。'
     'G 與傷害倍率各一次，額外 XP 為 0；保留純武藝／破魔節點的獨立效果。'),
    ('1.1', '開形態需要魔力高於上限 10%；切換不檢查', 'IMPLEMENTED',
     'DLL native/include/Timer.h PlanSwitch ← Plugin.cpp RequestSwitch（熱鍵的輸入事件 sink 與形態力量的 ESSBNative.RequestSwitch）',
     'round 25（N6）：順轉與免門檻豁免；血形態不需要魔力（v0.4 1.1，舊的 ESSBInput 沒有照做）'),
    ('1.1', '血位：三條曲線線性內插（命中倍率、吸血、損血）', 'IMPLEMENTED',
     'DLL native/include/HitMath.h（命中倍率、吸血）＋ native/include/Timer.h BloodUpkeepFraction（維持損血）＋ SelfLayer.h BloodPowerCostFraction（重擊損血）',
     'round 25 起維持損血也在 DLL 計時器'),
    ('1.1', '風形態潛行：潛行攻擊時風附傷 ×3', IMPL,
     'DLL native/include/HitMath.h ElementMultiplier', '讀 HitData 的潛行旗標（2048）；移速與 Muffle 的自有能力屬風樹，round 2'),
    ('1.1', '火形態過熱：同調三段後每命中 +1，滿了自爆或熔身', REMOVED,
     '—（round 22 刪除 ESSBController.AddSelf(4) 與 v0.3 的熔身計時）',
     'v0.4 已改成你身上的熱度階梯（微熱／灼熱／白熱／熔燒），白熱引信到期＝過熱，由 DLL 做（native/include/Status.h rule::SetHeat／OnFuseEnd）'),
    ('2.1', '每擊隨機 B：各元素自己的常態範圍，重擊 ×1.5', IMPL,
     'DLL native/include/HitMath.h RollProc', '規劃 2.1 的 11 組上下限；DLL 在命中當下擲骰並以強度覆寫施放（round 20 起）'),
    ('2.1', '雷的附傷另削減目標魔力 50%', 'IMPLEMENTED',
     'DLL native/include/Reactions.h Bodies::HitDischarge（放電）＋ Bodies::Open（感電）',
     '規劃 2.6 的感電與放電都削魔（round 24 起放電、跳躍與削魔都在 DLL）'),
    ('2.3', '狀態上限的三種來源：基礎、分支、通用樹「萬象」欄', IMPL,
     'DLL native/include/Status.h BleedCap／PressureCap／CurseCap／StarCap（CapBonus）', '量表類（凍結）固定 5，不吃通用樹加成；round 22 起層數是 DLL 掛在目標身上的效果強度'),
    ('2.7', 'G(L) = 1 + 0.05 × L', 'IMPLEMENTED',
     'DLL native/include/HitMath.h TreeG（附傷）與 Status.h ReactionScale／PerDose／PerBleedLayer（DLL 的反應、持續傷與死域）',
     '每條路徑只乘一次，不重複；round 25 起 Papyrus 已沒有自己的傷害（ApplyDamage 隨 Papyrus 領域刪除）'),
    ('2.7', 'M_mod 只乘一次，不出現疊乘', 'IMPLEMENTED',
     'DLL native/include/HitMath.h NodeSum（附傷）／ DLL native/include/Status.h EndNodeMult（終焉的狀態部分）／ DLL native/include/Reactions.h Bodies::End（終焉的本體：同一個 EndNodeMult，融斷再乘 BurstMult 與該樹融斷主線）',
     '附傷 = 共通 × 通用樹 × 元素樹；終焉 = 共通 × 通用樹關閉 × 元素樹關閉（round 24 起本體也在 DLL，每個本體只乘一次）'),
    ('2.8', '真實傷害類別：不吃護甲、抗性、外部加成', IMPL,
     'MGEF ESSB_TrueEffect（skill = -1、resist = None）+ ESSBController.ApplyTrueDamage', '只掛 ESSB_TrueDamage keyword，沒有外部天賦認得；造成真傷練無元素樹'),
    ('2.9', '融斷後留下的領域（火域、冰原）', 'IMPLEMENTED',
     'DLL native/include/StatusEngine.h RunOp（ESSB_Domain → Spawn Hazard 放置法術，build/fix25_records.py）＋ native/include/Timer.h（每秒：你與內部敵人）',
     'round 25（N6，裁定 R4）：真的地面效果（引擎 hazard，放在融斷目標腳下、只打對你有敵意的人、引擎管壽命與數量，不再限 3 個）'),
    ('2.9', '各元素的「臨」：以玩家為中心 2 公尺 + 0.2 公尺／點', 'IMPLEMENTED',
     'ESSBController.OnFormOpened → ESSBNative.FormEnter → DLL native/include/Reactions.h PlanAdvent',
     'round 24：一次掃描，範圍內不限人數的合格敵人各開印一次（決策 3）'),
    ('2.13', '附傷、反應、真傷的學派歸屬與 DoCombatSpellApply', IMPL,
     'build_v03（SCHOOLS/casting_perks）+ ESSBController', '真傷刻意不掛學派；其餘沿用引擎前線的配置'),
    ('6.1', '每個節點效果處理函式都留紀錄', IMPL,
     'ESSBController.LogThrottled / ESSBLog.Log', '等級 1 事件（開印、終焉、融斷、化身、處決、沉默、反咒、領域）、等級 2 節點、等級 3 公式細項'),
    ('8', '碎冰處決以自有高強度傷害法術執行，不用 Kill()', IMPL,
     'ESSBController.Execute', '擊殺歸屬與死亡事件與一般擊殺一致；首領與必要角色由呼叫端改走 ×5 傷害'),
    ('8', '過熱／熱度／電荷等自身資源鏡射成全域變數', IMPL,
     'ESSBController.PushSelf / PushSyncStage / SetGlobal', 'PERK 進入點的 CTDA 只讀得到全域變數，這是樣式 C 的橋'),
    # ---- 機制前線 round 2
    ('1.1', '血形態維持費：依血位曲線每秒扣最大生命（1.0%／0.6%／0.2%／0）', 'IMPLEMENTED',
     'DLL native/include/Timer.h PlanFormSecond／BloodUpkeepFraction ← Plugin.cpp FormSecondWork（代價路徑 kPayHealth，留 1 點）',
     'round 25（N6）：ESSBFormRules 刪除，維持扣血在 DLL 計時器（× MCM 維持費倍率）'),
    ('1.1', '血形態重擊不消耗耐力，改扣生命（8%／5%／2%／0）', 'IMPLEMENTED',
     'PERK ESSB_P_BaseRules 進入點 0x1B ×0 ＋ DLL native/include/SelfLayer.h BloodPowerCostFraction（命中時扣）',
     '耐力那一半用進入點（條件 ESSB_FormActive == 1 且 ESSB_CurrentElement == 6），生命那一半 round 23 起在 DLL'),
    ('1.1', '風形態：移速 +10%、潛行腳步聲減半、潛行攻擊風附傷 ×3 且風勢直接滿', IMPL,
     'ESSBController.RefreshWindAbilities / RefreshWindStealth / ElementHitHook',
     'SPEL ESSB_Ability_WindSpeed（AV 30）與 ESSB_Ability_Muffle（AV 92）；潛行狀態在既有的每秒 tick 讀一次'),
    ('2.3', '土 岩甲：護甲加成、被打 -1、離開形態清空', 'IMPLEMENTED',
     'DLL native/include/SelfLayer.h（岩甲的效果與護甲 AV）＋ DLL native/include/Hurt.h PlanHurt（被打 -1）',
     'round 23 起是 DLL 掛在你身上的效果；round 24 刪掉 ESSBGuard'),
    ('2.3', '風 風勢：到門檻送出風刃後歸零', 'IMPLEMENTED',
     'DLL native/include/SelfLayer.h PlanSelfHit → ESSB_Blade → DLL native/include/Reactions.h Bodies::Blade',
     'round 23 起門檻在 DLL；round 24 起風刃本體也在 DLL（本體事件不再送 Papyrus）'),
    ('2.3', '風 失衡：受風刃傷害 +30%', 'IMPLEMENTED',
     'DLL native/include/Reactions.h Bodies::BladeOne',
     '讀目標身上的失衡效果'),
    ('2.6', '土 地震的「耐力歸零跌倒」', 'IMPLEMENTED',
     'DLL native/include/Reactions.h Bodies::Quake → ESSB_Knock → ESSBController.Knockdown',
     'DLL 判定誰被削到底（決策 19），PushActorAway 力道 3.0、每目標 8 秒一次、免疫者改為減速 30% 3 秒照舊在 Papyrus'),
    ('2.6', '風 開印的「拉近 1.5–3 公尺」與終焉的「吹飛 3–6 公尺」', IMPL,
     'ESSBController.PullIn / PullTo / BlowBack（ApplyHavokImpulse）',
     '拉近每目標 3 秒一次、吹飛每目標 8 秒一次；免疫名單＝龍、騎乘中、必要角色與首領、巨人與猛獁'),
    ('2.5', '風印記融斷的「吹上天」與落地傷害', IMPL,
     'ESSBController.LiftUp → SetAirborne（DLL 的浮空效果）→ DLL 到期送 ESSB_Landing → ESSBController.OnLanding',
     '浮空是 DLL 掛在目標身上的 2 秒效果（規劃 8：不讀物理狀態），效果到期時結算落地傷害'),
    ('2.6', '聖 開印「目標受聖傷 +20%」', 'IMPLEMENTED',
     'DLL native/include/Status.h ProcTerms（附傷、聖裁）＋ DLL native/include/Reactions.h Bodies::Judge（裁決）',
     '兩邊都讀目標身上的神聖印記'),
    ('2.7', '血承：擊殺時吸收死者屬性 15 秒', IMPL,
     'ESSBController.ApplyInherit（SPEL ESSB_InheritSpell 的 7 個 Peak Value Modifier）',
     '火冰電毒魔抗各 50%、護甲 20%、最大生命 10%；施放前逐一 SetNthEffectMagnitude，重掛即取代'),
    ('2.10', '白天 → 化灰必定觸發', 'IMPLEMENTED',
     'DLL native/include/Reactions.h PlanDeath（化灰判定）→ ESSB_Ash → ESSBController.ApplyAsh',
     'round 24：帶神聖印記死亡即化灰（淨土另加）；化灰 MGEF 的 DATA 照抄原版 PerkDisintegrateFFAimed；龍與必要角色不化灰'),
    ('8', '死靈施法者判定（原版無關鍵字，候選三選一）', IMPL,
     'ESSBController.IsNecromancer',
     '取三個候選的聯集：職業 CombatMageNecro（0x0C969F）、陣營 NecromancerFaction（0x034B74）、PO3 GetCommandedActors 非空'),
    ('8', 'SpeedMult 修正的重新整理方式', IMPL,
     'ESSBController.RefreshSpeed',
     '所有移速修正都走 MGEF（同原版 FrostSlowFFContact，AV 30 + 原型 34），不用 SetActorValue；'
     '另加一次負重微調（ModActorValue CarryWeight +0.1 / -0.1，淨值為零）強迫重算衍生數值，只在形態開／切／關時跑'),
    ('8', '「不解除潛行」用壓低偵測值實作', IMPL,
     'ESSBController.KeepSneak / TickTimers（PO3 PreventActorDetection / ResetActorDetection）',
     '擊殺後 5 秒，尊重原版偵測系統，不鎖 AI、不動 AI 套件'),
    ('2.9', '玩家受擊事件（PO3 OnHitEx）與擊殺事件（OnActorKilled）', 'IMPLEMENTED',
     'DLL native/src/Plugin.cpp（TESHitEvent 受擊、TESDeathEvent 死亡 sink）',
     'round 23 受擊搬進 DLL；round 24 擊殺與死亡處理也搬進 DLL，ESSBGuard 整檔刪除（裁定 R4）'),
    # ---- 機制前線 round 3
    ('2.3', '毒 中毒：劑數在一顆中毒效果的強度裡，時長＝剩餘 +3 秒（上限 15）；≥5 劑時瘴氣每秒傳 0.5 劑', IMPL,
     'DLL native/include/Status.h rule::Grow／Spread／AddDoses／SpreadDoses／MiasmaDoses ＋ native/src/Plugin.cpp TargetSecond ＋ build/fix22_records.py（整秒持續傷）',
     'round 22：v0.3 的六格環狀桶與 Papyrus 擴散刪除；讀–疊–重套（先 Dispel 舊的再套，裁定 R3）；以基礎劑數計算（催毒的倍率另存，審查修正 1）；瘴氣、瘟疫、淬毒傳劑、濃毒走擴散一劑（時長 max(d − t, 12)）；瘴氣披風拿掉（指揮官裁定 (b)+(d)）'),
    ('2.3', '水 水壓：命中浸濕目標 +1，每層水附傷 +10%；滿格沖刷', IMPL,
     'DLL native/include/Status.h rule::SetPressure ＋ ProcTerms ＋ Plugin.cpp Executor::Wash',
     '8 秒、命中刷新，上限 5（萬象 +）；滿格時沖刷目標全部「手施、有時限、有益」的增益（裁定 R5）'),
    ('2.3', '暗 詛咒：上限 5，深淵在同調三段 +1／每 3 點（最多 10）；3 層恐懼、5 層瘋狂', 'IMPLEMENTED',
     'DLL native/include/Status.h CurseCap／rule::AddCurse（幻覺階梯與冷卻）→ ESSB_Hallucinate → ESSBController.ApplyFear／ApplyFrenzy',
     '侵蝕用原型 34 的抗性負向修正，round 24 起由 DLL 在命中時施放（DLL native/include/Reactions.h PlanHitBodies），會自己還原'),
    ('2.3', '星 星痕：命中重新計時，停手 2 秒（星痕延遲）後全部一起引爆，上限 3 +1／每 5 點', IMPL,
     'DLL native/include/Status.h rule::AddStars／DetonateStars ＋ 星痕引信效果（ESSBStub，到期由 DLL 結算）',
     'round 22：延遲是連續秒數（引信效果的時長），不再只有整數秒兩檔'),
    ('2.6', '暗 死咒期間目標無法被治療', 'IMPLEMENTED',
     'DLL native/include/Reactions.h Bodies::End（暗）→ 整秒治療削減法術（ESSB_N5_TimedHealRateDebuff_*）',
     '引擎沒有「受到的治療」修正，以 HealRateMult -100% 表達（同血咒的偏離）；不治分支延長到 6 秒'),
    ('2.9', '瘴氣複製：中心為目標、6 公尺、5 人', 'IMPLEMENTED',
     'DLL native/include/Reactions.h Bodies::End（毒：疫染）',
     'round 24 起在 DLL（決策 8）'),
    ('2.9', '星界的所有範圍：基礎相同，主線每點 +1 公尺', REMOVED,
     '—（round 21 刪除 ESSBElem3.Range / FallRadius / ConstellationRadius / ScatterRadius）',
     'v0.4 已拿掉這條 v0.3 規則：星臨半徑與其他元素相同（ESSBElem.AdventRadiusOf／ESSBElem3.AdventRadius，2 公尺 +0.2 公尺／點），星散 15 公尺、星域 3 公尺'),
    ('2.9', '領域格從 1 格擴充為固定 3 格', 'REMOVED',
     '—（round 25 刪除 ESSBController.StartDomain／InDomain／DomainActive／TickDomain／DomainFlag 與三格表）',
     '裁定 R4：領域改為引擎 hazard，不再有 3 格上限（引擎的 hazard 數量由 HAZD 的 limit 管，本模組設 0＝不限）'),
    ('2.10', '夜晚 → 星界所有範圍 ×1.5', REMOVED,
     '—（round 21 刪除 ESSBElem3.Range）', 'v0.4 已拿掉這條 v0.3 規則；夜晚黑暗附傷 +20% 仍由 DLL 讀環境旗標'),
    ('8', '長流：自有的每秒百分比回復，不動回復速率 AV', 'IMPLEMENTED',
     'DLL native/include/Timer.h PlanFormSecond ← Plugin.cpp TickCpp（計時器每秒）',
     'round 25（N6）：在 DLL 計時器（暫停、選單、讀檔時不走）；不動回復速率 AV、不受戰鬥中回復減半影響'),
    ('8', '洗淨／淨化：不洗掉自己的增益', IMPL,
     'ESSBController.ApplyCleanse + DispelHostileEffects；SPEL ESSB_CleanseSpell / '
     'ESSB_PurgeSpell 只掛 Cure Disease（原型 3）與 Cure Poison（原型 29）',
     '特效前線改成「安全建構」：不依賴原型 2 與旗標 0x100（兩者都是推論值）。'
     '(1) 逐個 DispelSpell 本模組自己的有時限減益（SelfCleanseSpells，11 個）；'
     '(2) 治病與解毒走實測原型；(3) 淨化另用 PO3 GetActiveEffects 挑敵對／有害旗標的效果，'
     'GetMagicEffectSource 回推來源法術後 DispelSpell。最壞情況是少清幾個外來減益，'
     '不可能洗掉形態能力、血承、岩甲。MGEF ESSB_CleanseEffect / ESSB_PurgeEffect 仍在 ESP 裡待命'),
    ('8', '沖刷：只沖掉目標「手施、有時限、有益」的增益', 'IMPLEMENTED',
     'DLL native/include/StatusEngine.h Washes／Wash（RunOp kWash：浸濕／水壓的全數沖刷、潮池每秒一個）',
     'round 22：判定同浸濕／水壓的全數沖刷（裁定 R5：法術／卷軸／法杖、左右手施放、有時限未到期、非敵對非有害、不是本模組的、不是召喚／綁定武器／復生）；round 25：Papyrus ApplyStrip 與 ESSBNative.WashBuffs 刪除，潮池每秒一個由 DLL 計時器下'),
    ('8', '亡者歸來：自有 Reanimate 原型的六階表，尊重召喚上限', 'IMPLEMENTED',
     'DLL native/include/Reactions.h JudgeRaise／PlanDeath → ESSB_Raise → ESSBController.CanReanimate／ApplyReanimate（SummonCap／ServantCount）',
     'C3 重做（round 24）：帶黑暗印記（或冥印、冥召、狂宴）死亡、詛咒 ≥3 層即亡者歸來；階依等級，詛咒 5 層以上階 +1 並每層僕從攻擊 +10%，滿層時間加倍；殘魂、冥召、死靈主照 v0.4；復生 AI 與召喚上限留在 Papyrus（裁定 R4）'),
    ('6', '恐懼與瘋狂：自有效果、等級上限、尊重免疫', IMPL,
     'MGEF ESSB_FearEffect（原型 7）／ESSB_FrenzyEffect（原型 8）'
     '+ ESSBController.ApplyFear / ApplyFrenzy / CanCharm',
     'magnitude 就是可影響的最高等級（10 + 暗樹等級），做法同原版幻術；'
     '首領與必要角色、龍、亡靈魔族免疫；只在黑暗樹出現'),
    # ---- round 22（N3：目標狀態層）
    ('2.2', '印記：每目標一顆自有效果、8 秒（水 10 秒），命中刷新、被切、融斷、自然過期', IMPL,
     'DLL native/include/Status.h PlanStatusHit／PlanEnd／OnMarkExpired ＋ ESSB_MarkEffect_<元素>（ESSBStub）',
     'v0.3 的 8 格登記表與「第 9 個目標逐出最舊」刪除（v0.4 沒有名額上限）；每目標開印與終焉各 1 秒冷卻是目標身上的效果；'
     '到期由效果移除事件判定（elapsed ≥ duration 且目標沒死），裁定 R3'),
    ('2.3', '敵方元素狀態都是引擎效果：層數＝強度、時間＝效果時長', IMPL,
     'build/fix22_records.py KINDS ＋ DLL native/include/Status.h Read／Lower',
     '命中時讀目標與你身上的效果、算下一個狀態、先 Dispel(true) 舊的再重套（裁定 R3）；時長用 effectiveness 換算（決策 1）；'
     'v0.3 的狀態容器 ESSBStatus、換宿、pending、備份全部刪除（裁定 R4），新 NPC 身上不再出現鬼狀態'),
    ('2.3', '你身上的熱度（微熱／灼熱／白熱／熔燒）與聖佑（I／II／III）階梯', IMPL,
     'DLL native/include/Status.h rule::SetHeat／RaiseHeat／SetHoly／RaiseHoly／PlanDecay ＋ Plugin.cpp FireSecond',
     '各階成熟 2 秒；微熱／灼熱 6 秒、聖佑 8 秒沒命中退一階（計時效果被命中刷新，tick 看它不在就退）；白熱時你是火源'),
    ('2.6', '開印與終焉：DLL 做狀態部分與反應本體，Papyrus 只給經驗與特效', 'IMPLEMENTED',
     'DLL native/src/Plugin.cpp RunWithBodies → DLL native/include/Reactions.h RunBodies；ESSB_Open／ESSB_End → ESSBController.OnESSBOpen／OnESSBEnd（經驗、PlaceFx）',
     'round 24（N5）：反應本體、各樹分支與範圍掃描在 DLL；推力、幻術 AI、復生 AI、化灰崩解、不解除潛行、領域經 ModEvent 回 Papyrus（裁定 R4）'),
    ('2.7', '目標側倍率（熱度、水壓、星痕弱點、聖印、星鎖、領域、嗜血、御風、空中追擊……）', IMPL,
     'DLL native/include/Status.h ProcTerms／ReactionVulnerability → HitMath.h PlanHit',
     'round 22 起從目標與你身上的效果讀，不再由 Papyrus 差額補丁補（ESSBController.ApplyProc 刪除）'),
    ('2.3', '放血：每層每秒另扣目標當下生命 0.3%（首領 0.1%）', IMPL,
     'DLL native/src/Plugin.cpp TargetSecond（ESSB_Util_BleedTick）',
     'v0.4 標「DLL 每秒點 N5」；狀態容器刪掉後先搬進 DLL 計時器（決策 10），不吃 G(L)、不吃抗性'),
    ('5.8', '越線：70% 與 30% 兩條線，往下濺血、往上回湧（N4）', 'IMPLEMENTED',
     'DLL native/include/Status.h PlanStatusHit（血區效果與 10 秒冷卻）→ DLL native/include/Reactions.h Bodies::Splash／Bodies::Rise',
     'round 24：濺血（15 公尺內所有流血目標最多 5 人 ×0.5 血潮、不清血痕）與血約的掃描在 DLL；回湧的效果是 N4'),
    # ---- round 25（N6：每秒計時、熱鍵、領域）
    ('1.1', '維持費：每秒扣最大魔力 基礎% ×（1 − 0.7 × 樹等級／100）× 維持費倍率；魔力歸零 2 秒關閉', 'IMPLEMENTED',
     'DLL native/include/Timer.h MagickaUpkeep／PlanFormSecond（魔力歸零的計時是你身上的 ESSB_N6_ManaEmpty）→ ESSB_Close → ESSBController.CloseForm',
     'round 25（N6）：ESSBFormRules 刪除；基礎 1.0%（暗 2.0%）與折減 0.7 來自 settings.json、編進 ManifestData.h'),
    ('1.1', '直接切換熱鍵（預設開啟）；Z 路線呼叫同一個切換函式', 'IMPLEMENTED',
     'DLL native/src/Plugin.cpp InputSink（BSInputDeviceManager，主執行緒）→ Timer.h KeyCodeOf／HotkeyElement／InputOpen／PlanSwitch → RequestSwitch → ESSB_Switch → ESSBController.SwitchForm；ESSBFormPowerEffect → ESSBNative.RequestSwitch',
     'round 25（N6，裁定 R6）：ESSBInput 刪除；主控台、文字輸入框、選單裡按熱鍵不觸發；DLL 先寫全域變數（下一刀就吃到新元素）'),
    ('2.10', '環境偵測每 5 秒（下雨下雪、暴風雪與雷雨、夜晚、在水中）', 'IMPLEMENTED',
     'DLL native/include/Timer.h Environment ← Plugin.cpp EnvironmentCheck（計時器每 5 秒）→ ESSB_EnvWet／EnvStormy／EnvThunder／EnvNight',
     'round 25（N6）：ESSBController.EnvCheck 刪除；天氣分類同 Papyrus GetClassification，室內沒有天氣，游泳或水下算浸濕；審查修正：暴風雪＝下雪且天氣風速 ≥ 128／255（ESSB_EnvStormy，凍結累積 ×2），雷雨＝下雨且天氣有雷電頻率（≠ 255，ESSB_EnvThunder），不再是「任何雨雪」'),
    ('2.10', '雷雨天氣 → 雷形態每 3 秒自動 +1 電荷', 'IMPLEMENTED',
     'DLL native/include/Timer.h PlanFormSecond（讀 ESSB_EnvThunder；3 秒 × 冷卻倍率的時鐘是你身上的 ESSB_N6_StormCooldown）',
     'round 25（N6）：Papyrus 的 3 秒計時刪除；第一格在進入雷雨的那一秒就給（Papyrus 要等 3 秒）；審查修正：只有真的雷雨（下雨且有雷電）'),
    ('5.1', '沉默：無法施法、不回魔（每秒把魔力扣到 0）', 'IMPLEMENTED',
     'DLL native/include/StatusEngine.h RunOp（施放沉默當下扣到 0）＋ Plugin.cpp SilenceSecond（計時器每秒）；MagickaRateMult -100 在法術本身',
     'round 25（N6）：ESSBSilence 腳本刪除'),
    ('2.9', '擊殺掛勾讀屍體（死亡處理）', 'IMPLEMENTED',
     'DLL native/src/Plugin.cpp OnDeathCpp／DeathCpp → DLL native/include/Reactions.h PlanDeath',
     'round 24：死亡 sink（dead = false，屍體還帶著效果）在 sink 裡只讀屍體與兇手，task 裡掃一次群體後照 v0.4 結算；每個死者只處理一次；ESSB_Death 快照與 Papyrus 的擊殺掛勾刪除'),
]


def rows(plan):
    """把 plan 的 493 個節點展開成覆蓋列；NODES 缺任何一個節點就回報 missing 讓建置失敗。"""
    out = []
    missing = []
    for tree in plan['trees']:
        tree_id = tree['id']
        for route in tree['routes']:
            for tier in route['tiers']:
                prefix = f"ESSB_P_{tree_id}_{route['index']}_{tier['index']}"
                cells = [(tier['main_label'], 'M', f'{prefix}_M1', tier['main'], tier['main_owner'])]
                cells += [(b['name'], f"B{b['slot']}", f"{prefix}_B{b['slot'] + 1}", b['description'], b['owner'])
                          for b in tier['branches']]
                for name, slot, edid, text, owner in cells:
                    found = NODES.get((tree_id, name))
                    if found is None:
                        missing.append((tree_id, name))
                        continue
                    status, where, note = found
                    out.append({
                        'kind': 'node',
                        'section': tree['section'],
                        'tree': tree_id,
                        'route': route['name'],
                        'tier': tier['name'],
                        'name': name,
                        'slot': slot,
                        'edid': edid,
                        'text': text,
                        'owner': owner,
                        'status': status,
                        'where': where,
                        'note': note,
                    })
    for section, item, status, where, note in MECHANISMS:
        out.append({
            'kind': 'mechanism',
            'section': section,
            'tree': '-',
            'route': '-',
            'tier': '-',
            'name': '-',
            'slot': '-',
            'edid': '-',
            'text': item,
            'owner': '-',
            'status': status,
            'where': where,
            'note': note,
        })
    return out, missing

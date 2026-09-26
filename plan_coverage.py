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
    ('fire', '火源倍率 N'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（主線：火源倍率 N +0.2／點（2 → 5））'),  # 0,0 v0.4 負責：DLL N3
    ('fire', '添薪'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（添薪：白熱引信 8 → 12 秒）'),  # 0,0,0 v0.4 負責：DLL N3
    ('fire', '火附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）＋ESSBController.NativeNodeSum 鏡像',
        '火附傷 +1%／點（×節點倍率），round 20 起 DLL 在命中當下算'),  # 0,1 v0.4 負責：DLL N2
    ('fire', '烙印'): ('PARTIAL-N3', 'ESSBElem.HitStacks',
        '重擊使熱度升兩階，目前以「重擊 +4 層目標熱度」近似。差距：v0.4 的熱度是你身上的階（無／微熱／灼熱／白熱／熔燒，N3），本模組目前仍是 v0.3 的「熱度＝目標身上的層數」近似。'),  # 0,1,0 v0.4 負責：DLL N3
    ('fire', '溫血'): ('DONE', 'SPEL ESSB_Ability_WarmBlood + ESSBController.RefreshAbilities',
        '火形態耐力回復 +20%（自有常駐能力，隨回復倍率）'),  # 0,1,1 v0.4 負責：Papyrus
    ('fire', '帶火印記目標火抗'): ('PARTIAL-N3', 'ESSBElem.ApplyFireResistShred',
        '火抗 -1%／點；條件應是「目標帶火印記」，目前讀的是目標熱度層數。差距：v0.4 的熱度是你身上的階（無／微熱／灼熱／白熱／熔燒，N3），本模組目前仍是 v0.3 的「熱度＝目標身上的層數」近似。'),  # 0,2 v0.4 負責：DLL N3
    ('fire', '熔心'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（熔心：洩壓與過熱後保留微熱）'),  # 0,2,0 v0.4 負責：DLL N3
    ('fire', '熔身'): ('PARTIAL-N3', 'ESSBElem.HasMoltenBody → ESSBController.AddSelf／TickTimers ＋ ESSBElem.FireHitExtra（+100%）',
        '過熱不付代價、改進入 10 秒熔身：火附傷 +100%、每秒回耐力 5（審查修正：由 20×G 改回 v0.4 的 5）。差距：過熱是 v0.3 的自身資源近似；「期間熱度停在白熱、結束歸零、熔身中切換或按 Z 仍是洩壓」要等玩家熱度階（N3）。'),  # 0,2,1 v0.4 負責：DLL N3＋引擎效果
    ('fire', '同調每段火附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）＋ESSBController.NativeNodeSum 鏡像',
        '同調每段火附傷 +1%／點（×節點倍率 × 同調段）'),  # 0,3 v0.4 負責：DLL N2
    ('fire', '灼身'): ('KEPT-N4', 'ESSBGuard.OnHitEx',
        '被近戰命中時攻擊者掛你的火印記（ESSBController.ApplyMark）並受一次火傷（ReactDamage B_max ×1），每個攻擊者 3 秒一次（TakeAttacker）。審查修正：拿掉 v0.3 的熱度 +1'),  # 0,3,0 v0.4 負責：DLL 受擊 N4
    ('fire', '火浴'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（火浴：白熱點燃當下依燒到的人數固定回血量，之後每秒回血 B_max ×0.1 × 該人數（人數不隨後續增減變動））。提前移除（指揮官裁定 C3）：v0.3 的舊效果本輪已刪，於 N3 以 v0.4 版本重做'),  # 0,3,1 v0.4 負責：DLL N3
    ('fire', '業火'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（主線：業火，同調三段時火源倍率 N 再 +0.1／點（5 → 6.5，熔燒 8.5））'),  # 0,4 v0.4 負責：DLL N3
    ('fire', '浴火'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（浴火：同調三段時被帶火印記的目標命中，熱度推進一次（照成熟時間；已在白熱以上則無效），被圍毆時也能升到白熱）'),  # 0,4,0 v0.4 負責：DLL 受擊 N4
    ('fire', '熔爐'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（熔爐：白熱引信到期不過熱，改升到第四階「熔燒」（火附傷 +90%、爆燃 ×4.0、火源 4.5 公尺、N +2）再燒 6 秒才過熱）'),  # 0,4,1 v0.4 負責：DLL N3
    ('fire', '開印後 5 秒內熱度升階免等待'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（主線：開印後 5 秒內熱度升階免等待，+0.5 秒／每 5 點）'),  # 1,0 v0.4 負責：DLL N3
    ('fire', '引火'): ('PARTIAL-N3', 'ESSBElem.OpenStacks',
        '開印使熱度升兩階，目前以「開印 +5 層目標熱度」近似。差距：v0.4 的熱度是你身上的階（無／微熱／灼熱／白熱／熔燒，N3），本模組目前仍是 v0.3 的「熱度＝目標身上的層數」近似。'),  # 1,0,0 v0.4 負責：DLL N3
    ('fire', '開印後 5 秒內火附傷'): ('KEPT-N3', 'ESSBElem.FireHitMult（GetOpenBoost）',
        '開印後 5 秒內火附傷 +1%／點'),  # 1,1 v0.4 負責：DLL N3
    ('fire', '烈火點燃'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（烈火點燃：白熱中開印，白熱引信 +2 秒（每個引信最多 +4 秒）；火源掛的火印記不算開印）'),  # 1,1,0 v0.4 負責：DLL N3
    ('fire', '餘熱'): ('KEPT-N3', 'ESSBElem.OpenFire',
        '餘熱：開印時回復 15 耐力（審查修正：數值照 v0.4，不乘 G(L)）'),  # 1,1,1 v0.4 負責：DLL N3
    ('fire', '火印記持續'): ('PARTIAL-N3', 'ESSBElem.MarkDurationBonus → ESSBController.ApplyMark',
        '火印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,2 v0.4 負責：DLL N3
    ('fire', '焰起強化'): ('KEPT-N5', 'ESSBElem.OpenFire',
        '焰起強化：開印額外對範圍內敵人一次火傷'),  # 1,2,0 v0.4 負責：DLL N5
    ('fire', '火臨'): ('KEPT-N5', 'ESSBElem.OnFormOpened → ESSBController.ForceOpenOn',
        '火臨：開形態時對 2 + 0.2×點 公尺內敵人各開印一次'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('fire', '烈火之始'): ('PARTIAL-N3', 'ESSBElem.OpenFire',
        '開印時目標生命 >80% 熱度直接白熱，目前以「目標熱度直接 8 層」近似。差距：v0.4 的熱度是你身上的階（無／微熱／灼熱／白熱／熔燒，N3），本模組目前仍是 v0.3 的「熱度＝目標身上的層數」近似。'),  # 1,3,0 v0.4 負責：DLL N3
    ('fire', '火種'): ('PARTIAL-N3', 'ESSBElem.HasTinder → ESSBStatus.Tick',
        '熱度不因未命中退階，目前是「目標熱度不因未命中歸零」；白熱引信不存在。差距：v0.4 的熱度是你身上的階（無／微熱／灼熱／白熱／熔燒，N3），本模組目前仍是 v0.3 的「熱度＝目標身上的層數」近似。'),  # 1,3,1 v0.4 負責：DLL N3
    ('fire', '開印效果'): ('KEPT-N3', 'ESSBElem.OpenMult → ESSBReactions.Open',
        '開印效果 +3%／點'),  # 1,4 v0.4 負責：DLL N3
    ('fire', '先燃'): ('KEPT-N3', 'ESSBElem.OpenFire → ESSBElem.Detonate',
        '先燃：同調三段時開印立即 ×0.5 爆燃'),  # 1,4,0 v0.4 負責：DLL N3
    ('fire', '終焉'): ('KEPT-N3', 'ESSBElem.EndMult',
        '終焉 +2%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('fire', '猛爆'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（猛爆：爆燃不消耗目標身上的狀態（吃了加成但東西還在））'),  # 2,0,0 v0.4 負責：DLL N3
    ('fire', '餘壓'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（餘壓：白熱期間切換或融斷後熱度保留灼熱，且火源多留 2 秒）'),  # 2,0,2 v0.4 負責：Papyrus＋DLL N3
    ('fire', '火印記的融斷'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '火印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('fire', '熾焰'): ('PARTIAL-N3', 'ESSBElem.Detonate',
        '白熱以上的爆燃再 ×1.5，目前以「目標熱度 ≥8」判定白熱。差距：v0.4 的熱度是你身上的階（無／微熱／灼熱／白熱／熔燒，N3），本模組目前仍是 v0.3 的「熱度＝目標身上的層數」近似。'),  # 2,1,0 v0.4 負責：DLL N3
    ('fire', '熔斷'): ('PARTIAL-N5', 'ESSBElem.KeepHeatOnBurst → ESSBReactions.EndFire',
        '融斷後熱度保留；目前保留的是目標熱度層數，不是你的熱度階。差距：v0.4 的熱度是你身上的階（無／微熱／灼熱／白熱／熔燒，N3），本模組目前仍是 v0.3 的「熱度＝目標身上的層數」近似。'),  # 2,1,1 v0.4 負責：DLL N5
    ('fire', '爆燃的消耗加成'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（主線：爆燃的消耗加成 +1%／點 × 被消耗的狀態數）'),  # 2,2 v0.4 負責：DLL N3
    ('fire', '餘燼'): ('KEPT-N3', 'ESSBElem.EndFireNodes → ESSBStatus.SetNextOpenMult',
        '餘燼：火終焉後接管元素的開印 ×1.5'),  # 2,2,0 v0.4 負責：DLL N3
    ('fire', '火印記的融斷再'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '火印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('fire', '焚天'): ('PARTIAL-N5', 'ESSBElem.EndFireNodes',
        '火終焉時範圍內帶火印記的目標一起爆燃；目前以「目標熱度 >0」判定，不是火印記。差距：v0.4 的熱度是你身上的階（無／微熱／灼熱／白熱／熔燒，N3），本模組目前仍是 v0.3 的「熱度＝目標身上的層數」近似。'),  # 2,3,0 v0.4 負責：DLL N5
    ('fire', '火葬'): ('KEPT-N5', 'ESSBElem.Detonate',
        '火葬：爆燃擊殺的目標對附近敵人再爆 ×0.5（以套用後的生命 ≤0 判定，需進遊戲驗證時序）'),  # 2,3,1 v0.4 負責：DLL N5
    ('fire', '爆燃'): ('KEPT-N3', 'ESSBElem.SignatureMult',
        '爆燃 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('fire', '火域'): ('PARTIAL-N3', 'ESSBElem.EndFireNodes → ESSBController.StartDomain ＋ ESSBElem.FireHitExtra（InDomain +20%）',
        'Papyrus 領域：火印記融斷後 5 秒火域、內部敵人受火傷 +20%；「你在其中熱度升階免等待、進入時白熱引信 +5 秒」是玩家熱度（N3）'),  # 2,4,0 v0.4 負責：Papyrus（領域）；引信延長：DLL N3（進入時一次寫入，非每秒暫停）
    # ================= 5.4 冰霜（frost）
    ('frost', '每次命中凍結累積'): ('KEPT-N3', 'ESSBElem.HitStacks',
        '每次命中凍結累積 +5%／點（小數以機率補足）'),  # 0,0 v0.4 負責：DLL N3
    ('frost', '寒蝕'): ('PARTIAL-N3', 'ESSBElem.HitStacks',
        '重擊凍結再 +1（總計 +3；round 21 由 v0.3 的 +4 改成 v0.4 的 +3）；「該次重擊的凍結歸零時限延長 2 秒」要等凍結量表改成目標身上的效果（N3）'),  # 0,0,0 v0.4 負責：DLL N3
    ('frost', '冰附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '冰附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('frost', '深寒'): ('DONE', 'ESSBElem.OnFrozenTick',
        '冰封中目標耐力不回復（耐力凝滯，同地裂）、攻擊 -20%（審查修正：原本是主動削耐 25×G，v0.4 是「不回復」）'),  # 0,1,0 v0.4 負責：引擎效果
    ('frost', '霜膚'): ('PARTIAL-N3', 'SPEL ESSB_IceArmorWide（冰甲披風 5 公尺、減速 30%）← ESSBController.RefreshAbilities',
        '冰甲寒氣半徑 3 → 5 公尺、寒氣減速 20% → 30%；凍結量表 ≥1 的 35% → 45% 要等凍結量表效果（N3）。v0.3「冰形態受傷 -5%」的進入點已刪'),  # 0,1,1 v0.4 負責：引擎效果
    ('frost', '冰封目標受冰附傷'): ('KEPT-N3', 'ESSBElem.FrostHitMult',
        '冰封目標受冰附傷 +2%／點'),  # 0,2 v0.4 負責：DLL N3
    ('frost', '永凍'): ('KEPT-N3', 'ESSBElem.FrozenExtraSeconds / FrozenResidual → ESSBStatus.Tick',
        '永凍：冰封 +2 秒、結束後凍結保留一半'),  # 0,2,0 v0.4 負責：DLL N3
    ('frost', '連鎖冰封'): ('KEPT-N5', 'ESSBElem.OnKill → ESSBController.Tick',
        '連鎖冰封：冰封目標死亡時附近凍結 +3、減速 30% 3 秒'),  # 0,2,1 v0.4 負責：DLL N5
    ('frost', '同調每段冰附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段冰附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('frost', '冰鎧'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（冰鎧：冰盾上限 5 → 8 層）'),  # 0,3,2 v0.4 負責：DLL N4
    ('frost', '凍傷'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（凍傷：冰封結束時沒被碎掉的冰晶不浪費，每顆轉為一次 B_max ×0.5 冰傷）'),  # 0,3,3 v0.4 負責：DLL N3
    ('frost', '寒反'): ('KEPT-N4', 'ESSBGuard.OnHitEx',
        '攻擊你的敵人被減速 30%，且凍結 +1（round 21 補上），每個攻擊者 3 秒一次'),  # 0,3,1 v0.4 負責：DLL 受擊 N4
    ('frost', '絕對零度'): ('KEPT-N3', 'ESSBElem.OnFrozenTick',
        '同調三段時冰封減速再 -2%／點，總減速上限 70%（ApplyUtil 壓在 ESSB_SlowCapPct）'),  # 0,4 v0.4 負責：DLL N3
    ('frost', '冰心'): ('KEPT-N4', 'ESSBElem.OnTick → ESSBController.TakeIceHeart',
        '生命 <30% 時自動冰封附近凍結 ≥1 的敵人，每 30 秒一次（每秒 tick 判定；N4 改受擊事件）'),  # 0,4,0 v0.4 負責：DLL 受擊 N4
    ('frost', '開印凍結'): ('KEPT-N3', 'ESSBElem.OpenStacks',
        '開印凍結 +1／每 3 點'),  # 1,0 v0.4 負責：DLL N3
    ('frost', '寒潮'): ('KEPT-N3', 'ESSBElem.OpenFrost → ESSBController.AddStackTo',
        '寒潮：開印時附近 1 人凍結 +2'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('frost', '開印後 5 秒內冰附傷'): ('KEPT-N3', 'ESSBElem.FrostHitMult（GetOpenBoost）',
        '開印後 5 秒內冰附傷 +1%／點'),  # 1,1 v0.4 負責：DLL N3
    ('frost', '深霜結'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（深霜結：開印時在目標身上預存 1 顆冰晶（冰封後不用普攻就有 1 顆；上限仍是 3））'),  # 1,1,0 v0.4 負責：DLL N3
    ('frost', '冰甲'): ('PARTIAL-N3', 'SPEL ESSB_IceArmor（冰形態 3 公尺寒氣披風，只對敵對者減速 20%）← ESSBController.RefreshAbilities',
        '披風與 20% 減速本輪做完（Papyrus 掛、引擎效果）；凍結量表 ≥1 改 35% 與「命中寒氣內的敵人凍結再 +1」要等凍結量表效果（DLL N3）。v0.3「開印得 1 層冰盾」已拿掉'),  # 1,1,1 v0.4 負責：Papyrus（掛披風）＋引擎效果；命中加凍結：DLL N3
    ('frost', '冰印記持續'): ('PARTIAL-N3', 'ESSBElem.MarkDurationBonus',
        '冰印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,2 v0.4 負責：DLL N3
    ('frost', '冰臨強化'): ('KEPT-N5', 'ESSBElem.OnFormOpened',
        '冰臨強化：冰臨附帶減速 30% 3 秒'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N5
    ('frost', '冰臨'): ('KEPT-N5', 'ESSBElem.OnFormOpened',
        '冰臨：開形態時對 2 + 0.2×點 公尺內敵人各開印一次'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('frost', '霜鎖'): ('PARTIAL-N3', 'ESSBElem.OpenFrost',
        '開印目標 3 秒內移速 -30%；「已在減速上限時改為凍結 +1」要等凍結量表效果（N3）'),  # 1,3,0 v0.4 負責：DLL N3
    ('frost', '霜爆'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（霜爆：目標進入冰封的那一刻，3 公尺內其他凍結量表 ≥1 的敵人凍結 +2）'),  # 1,3,2 v0.4 負責：DLL N3（掃描 N5）
    ('frost', '開印效果'): ('KEPT-N3', 'ESSBElem.OpenMult',
        '開印效果 +3%／點'),  # 1,4 v0.4 負責：DLL N3
    ('frost', '絕霜'): ('KEPT-N3', 'ESSBElem.OpenFrost',
        '絕霜：同調三段時開印直接冰封'),  # 1,4,0 v0.4 負責：DLL N3
    ('frost', '終焉'): ('KEPT-N3', 'ESSBElem.EndMult',
        '終焉 +2%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('frost', '銳碎'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（銳碎：碎冰 20% → 25%（首領 10% → 12%））'),  # 2,0,0 v0.4 負責：DLL N3
    ('frost', '冰印記的融斷'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '冰印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('frost', '冰崩'): ('KEPT-N5', 'ESSBElem.ShatterArea',
        '冰崩：碎冰改為 3 公尺範圍，命中所有冰封目標'),  # 2,1,0 v0.4 負責：DLL N5
    ('frost', '冰封融斷'): ('KEPT-N5', 'ESSBElem.FrostBurstShatter → ESSBReactions.EndFrost',
        '冰封融斷：融斷時冰封目標視同碎冰（碎冰本體本來就含處決判定）'),  # 2,1,1 v0.4 負責：DLL N5
    ('frost', '終焉後 5 秒內接管元素附傷'): ('KEPT-N3', 'ESSBElem.OnEnd → ESSBController.SetEndBoost',
        '終焉後 5 秒內接管元素附傷 +1%／點'),  # 2,2 v0.4 負責：DLL N3
    ('frost', '寒留'): ('KEPT-N3', 'ESSBElem.EndFrostNodes → ESSBController.SetNextMarkBonus',
        '寒留：冰終焉後接管元素的印記持續 +4 秒'),  # 2,2,0 v0.4 負責：DLL N3
    ('frost', '冰印記的融斷再'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '冰印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('frost', '冰河'): ('KEPT-N5', 'ESSBElem.EndFrostNodes → ShatterArea',
        '冰河：冰終焉時目標若冰封，範圍內冰封目標一起碎冰、各自判定處決'),  # 2,3,0 v0.4 負責：DLL N5
    ('frost', '碎甲加深'): ('KEPT-N3', 'ESSBElem.Shatter',
        '碎甲加深：碎冰的碎甲 10% → 20%'),  # 2,3,1 v0.4 負責：DLL N3
    ('frost', '碎冰'): ('KEPT-N3', 'ESSBElem.SignatureMult',
        '碎冰 +3%／點'),  # 2,4 v0.4 負責：DLL N3
    ('frost', '冰棺'): ('PARTIAL-N3', 'ESSBElem.Shatter',
        '碎冰後目標再冰封 2 秒。差距：「第二次碎冰 ×0.5」與冰封本身的時限要等凍結量表改成目標身上的效果（N3）'),  # 2,4,0 v0.4 負責：DLL N3
    ('frost', '冰原'): ('DONE', 'ESSBElem.EndFrostNodes → ESSBController.StartDomain/TickDomain',
        '冰原：融斷後 5 秒冰原，內部敵人減速 50%、凍結累積 ×2，玩家在其中免疫減速'),  # 2,4,1 v0.4 負責：Papyrus（領域）
    # ================= 5.5 雷電（lightning）
    ('lightning', '放電每格電荷傷害'): ('KEPT-N3', 'ESSBElem.Discharge',
        '放電每格電荷傷害 +1%／點'),  # 0,0 v0.4 負責：DLL N3
    ('lightning', '感應'): ('DONE', 'SPEL ESSB_Ability_Induction + ESSBController.RefreshAbilities',
        '雷形態魔力回復 +20%（v0.3 星輝共用的那一半已隨星輝退役）'),  # 0,0,0 v0.4 負責：Papyrus
    ('lightning', '雷附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '雷附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('lightning', '電弧'): ('KEPT-N3', 'ESSBElem.Discharge',
        '放電跳躍 2 → 3 人、跳躍傷害 40% → 55%（round 21 照 v0.4 數字改；v0.3 是 80%）'),  # 0,1,0 v0.4 負責：DLL N3
    ('lightning', '靜電'): ('KEPT-N4', 'ESSBGuard.OnHitEx',
        '被近戰命中時攻擊者感電＝掛你的雷印記（ESSBController.ApplyMark），每個攻擊者 3 秒一次（TakeAttacker）。審查修正：拿掉發明的「你 +1 電荷、他 -50×G 魔力」'),  # 0,1,1 v0.4 負責：DLL 受擊 N4
    ('lightning', '電荷上限'): ('KEPT-N4', 'ESSBElem.ChargeCap → ESSBController.AddSelf',
        '電荷上限 +1／每 3 點'),  # 0,2 v0.4 負責：DLL N4
    ('lightning', '雷暴'): ('KEPT-N4', 'ESSBElem.StormChance → ESSBController.OnWeaponHit',
        '雷暴：電荷滿時普攻 30% 機率放電'),  # 0,2,0 v0.4 負責：DLL N4
    ('lightning', '同調每段雷附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段雷附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('lightning', '逆電'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（逆電：被命中時電荷 +1（每 2 秒一次），挨打也在充電）'),  # 0,3,2 v0.4 負責：DLL 受擊 N4
    ('lightning', '疾電'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（疾電：任何放電後 3 秒內暴擊率 +15%）'),  # 0,3,1 v0.4 負責：引擎效果（放電時由 DLL N4 掛上）
    ('lightning', '天雷'): ('KEPT-N5', 'ESSBElem.DischargeAll',
        '天雷：同調三段時放電改為對 2 + 0.2×點 公尺內所有感電目標'),  # 0,4 v0.4 負責：DLL N5
    ('lightning', '雷神'): ('KEPT-N4', 'ESSBElem.OnTick',
        '雷神：同調三段電荷滿時自動放電並回魔（v0.4 沒寫回魔量：沿用 B_max × 電荷數，拿掉 G(L)）'),  # 0,4,0 v0.4 負責：DLL N4
    ('lightning', '開印電荷'): ('KEPT-N4', 'ESSBElem.OpenStacks',
        '開印電荷 +1／每 5 點'),  # 1,0 v0.4 負責：DLL N4
    ('lightning', '傳導'): ('KEPT-N3', 'ESSBElem.OpenShock',
        '傳導：開印時附近 1 人也感電（補一個雷印記）'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('lightning', '開印後 5 秒內雷附傷'): ('KEPT-N3', 'ESSBElem.ShockHitMult（GetOpenBoost）',
        '開印後 5 秒內雷附傷 +1%／點'),  # 1,1 v0.4 負責：DLL N3
    ('lightning', '強感電'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（強感電：開印那一擊若是重擊，電荷直接補滿（這一擊本身不放電，下一次滿格重擊才放），每 15 秒一次）'),  # 1,1,0 v0.4 負責：DLL N4
    ('lightning', '充能開印'): ('KEPT-N3', 'ESSBElem.OpenShock',
        '充能開印：開印時回復 B_max 魔力（審查修正：數值照 v0.4，不乘 G(L)）'),  # 1,1,1 v0.4 負責：DLL N3
    ('lightning', '雷印記持續'): ('PARTIAL-N3', 'ESSBElem.MarkDurationBonus',
        '雷印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,2 v0.4 負責：DLL N3
    ('lightning', '雷臨強化'): ('KEPT-N4', 'ESSBElem.OnFormOpened',
        '雷臨強化：雷臨時立即 +5 電荷'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N4
    ('lightning', '雷臨'): ('KEPT-N5', 'ESSBElem.OnFormOpened',
        '雷臨：開形態時對 2 + 0.2×點 公尺內敵人各開印一次'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('lightning', '感電削弱'): ('DONE', 'ESSBElem.OpenShock（自有 MagicResistDebuff）',
        '感電目標魔抗 -10%（開印時掛，8 秒）'),  # 1,3,0 v0.4 負責：引擎效果
    ('lightning', '雷閃'): ('KEPT-N3', 'ESSBElem.OpenShock（自有 Haste）',
        '雷閃：開印後 2 秒移速 +15%'),  # 1,3,1 v0.4 負責：DLL N3
    ('lightning', '雷鳴'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（雷鳴：開印那一擊若暴擊，電荷額外 +2）'),  # 1,3,3 v0.4 負責：DLL N4
    ('lightning', '開印效果'): ('KEPT-N3', 'ESSBElem.OpenMult',
        '開印效果 +3%／點'),  # 1,4 v0.4 負責：DLL N3
    ('lightning', '先雷'): ('KEPT-N3', 'ESSBElem.OpenShock',
        '先雷：同調三段時開印立即放電一次，不消耗電荷'),  # 1,4,0 v0.4 負責：DLL N3
    ('lightning', '終焉'): ('KEPT-N3', 'ESSBElem.EndMult',
        '終焉 +2%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('lightning', '連鎖'): ('KEPT-N3', 'ESSBElem.Discharge',
        '連鎖：放電跳躍 2 → 5 人'),  # 2,0,0 v0.4 負責：DLL N3
    ('lightning', '雷印記的融斷'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '雷印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('lightning', '蓄餘'): ('KEPT-N3', 'ESSBElem.Discharge',
        '蓄餘：雷終焉不消耗電荷'),  # 2,1,0 v0.4 負責：DLL N3
    ('lightning', '雷斷'): ('KEPT-N5', 'ESSBElem.ShockBurstBonus',
        '雷斷：雷印記融斷時附加全部電荷的放電加成（×(1+0.3×電荷)）'),  # 2,1,1 v0.4 負責：DLL N5
    ('lightning', '終焉後 5 秒內接管元素附傷'): ('KEPT-N3', 'ESSBElem.OnEnd → ESSBController.SetEndBoost',
        '終焉後 5 秒內接管元素附傷 +1%／點'),  # 2,2 v0.4 負責：DLL N3
    ('lightning', '餘電'): ('KEPT-N3', 'ESSBElem.EndShockNodes → ESSBController.SetPendingDischarge/AfterOpen',
        '餘電：雷終焉後接管元素的開印附帶 ×0.5 放電'),  # 2,2,0 v0.4 負責：DLL N3
    ('lightning', '雷印記的融斷再'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '雷印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('lightning', '雷殛'): ('KEPT-N5', 'ESSBElem.EndShockNodes',
        '雷殛：雷終焉對範圍內所有感電目標各一次全額放電'),  # 2,3,0 v0.4 負責：DLL N5
    ('lightning', '過載終焉'): ('PARTIAL-N3', 'ESSBElem.OverloadMult ← ESSBReactions.End',
        '任一元素終焉時電荷 ≥8 則 ×2。差距：v0.4 的電荷跨形態攜帶（10 秒未命中才歸零），目前電荷是 v0.3 的自身資源，切換形態時清空（N4 改成你身上的效果）'),  # 2,3,1 v0.4 負責：DLL N3
    ('lightning', '放電'): ('KEPT-N3', 'ESSBElem.SignatureMult',
        '放電 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('lightning', '雷霆'): ('KEPT-N4', 'ESSBElem.EndShockNodes → ESSBController.OnWeaponHit',
        '雷霆：雷印記融斷後 5 秒內每次命中都放電 ×0.3'),  # 2,4,0 v0.4 負責：DLL N4
    # ================= 5.6 大地（earth）
    ('earth', '裂痕護甲削減'): ('KEPT-N3', 'ESSBElem2.FissureArmor → ESSBReactions.Open(4)',
        '裂痕護甲削減 -30 → -60（+2／點），走自有 ESSB_Util_ArmorDebuff（審查修正：數值照 v0.4，不乘 G(L)）'),  # 0,0 v0.4 負責：DLL N3
    ('earth', '磐石'): ('KEPT-N4', 'ESSBElem2.RockArmorPerLayer → ESSBController.SyncRockArmor',
        '岩甲每層護甲 +25 → +40（審查修正：數值照 v0.4，不乘 G(L)）'),  # 0,0,0 v0.4 負責：DLL N4
    ('earth', '土附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '土附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('earth', '震擊'): ('KEPT-N3', 'ESSBElem2.OnEarthHit',
        '震擊：重擊消耗滿層裂痕，×1.5 爆傷並削 50 耐力（審查修正：數值照 v0.4，不乘 G(L)）'),  # 0,1,0 v0.4 負責：DLL N3
    ('earth', '厚土'): ('KEPT-N4', 'ESSBElem2.RockCap → ESSBController.AddSelf(2)',
        '厚土：岩甲上限 5 → 10'),  # 0,1,1 v0.4 負責：DLL N4
    ('earth', '命中削減目標耐力'): ('DONE', 'DLL native/include/HitMath.h AddFlatHitNodes（node::kEarthStaminaCut）',
        '命中削耐 3.0 × 點 × G（round 20 D6）'),  # 0,2 v0.4 負責：DLL N2
    ('earth', '汲力'): ('DONE', 'DLL native/include/HitMath.h AddFlatHitNodes（node::kEarthDrainStrength）',
        '削減的耐力一半轉給你'),  # 0,2,0 v0.4 負責：DLL N2
    ('earth', '同調每段土附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段土附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('earth', '不動'): ('DONE', 'PERK ESSB_P_earth_0_3_B1 進入點 0x21（受到的擊退 ×0，條件 ESSB_RockArmor ≥5）',
        '岩甲 ≥5 時免疫擊退（自有）'),  # 0,3,0 v0.4 負責：引擎效果
    ('earth', '反震'): ('KEPT-N4', 'ESSBElem2.OnEarthRetaliate ← ESSBGuard.OnHitEx',
        '反震：岩甲滿層被近戰命中反震 B_max ×2.0 土傷並使攻擊者跌倒，10 秒一次，清空岩甲'),  # 0,3,1 v0.4 負責：DLL 受擊 N4（跌倒推力：`AIProcess::KnockExplosion`）
    ('earth', '地動'): ('KEPT-N4', 'ESSBElem2.OnEarthHit → ESSBController.Knockdown',
        '地動：同調三段重擊對耐力 <30% 的目標跌倒，機率 5%／點'),  # 0,4 v0.4 負責：DLL N4（跌倒推力：`AIProcess::KnockExplosion`）
    ('earth', '山岳'): ('KEPT-N4', 'ESSBGuard.OnHitEx（同調三段不掉層）＋ PERK ESSB_P_earth_0_4_B1 進入點 0x24（每層再 +1%）',
        '同調三段時岩甲不因被打減少，物理減傷每層 +4% → +5%（基礎 4% 在 ESSB_P_BaseRules；合計上限 60%）'),  # 0,4,0 v0.4 負責：DLL 受擊 N4＋引擎效果
    ('earth', '開印岩甲'): ('KEPT-N4', 'ESSBElem2.OpenStacks(4)',
        '開印岩甲 +1／每 5 點'),  # 1,0 v0.4 負責：DLL N4
    ('earth', '震波'): ('KEPT-N3', 'ESSBElem2.OpenEarth',
        '震波：開印時附近 1 人也裂痕'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('earth', '開印後 5 秒內土附傷'): ('KEPT-N3', 'ESSBElem2.EarthHitMult（GetOpenBoost(4)）',
        '開印後 5 秒內土附傷 +1%／點'),  # 1,1 v0.4 負責：DLL N3
    ('earth', '深裂痕'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（深裂痕：開印時目標耐力低於 50% 則立即跌倒（掛倒地））'),  # 1,1,0 v0.4 負責：DLL N3（跌倒推力：`AIProcess::KnockExplosion`）
    ('earth', '岩膚'): ('KEPT-N4', 'ESSBElem2.OpenStacks(4)',
        '岩膚：開印岩甲 +2 → +4'),  # 1,1,1 v0.4 負責：DLL N4
    ('earth', '土印記持續'): ('PARTIAL-N3', 'ESSBElem.MarkDurationBonus → ESSBController.ApplyMark',
        '土印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,2 v0.4 負責：DLL N3
    ('earth', '地臨強化'): ('PARTIAL-N4', 'ESSBElem2.OnFormOpened(4)',
        '地臨時岩甲滿層、範圍內敵人耐力 -50%（最大耐力一半）；岩甲仍是 v0.3 腳本資源（N4 改效果），範圍掃描 N5 前由 Papyrus 做。v0.3「範圍減速 30%」已換掉'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N4／N5
    ('earth', '地臨'): ('KEPT-N5', 'ESSBElem.OnFormOpened → ESSBController.ForceOpenOn',
        '地臨：開土形態時對範圍內敵人各開印一次，2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('earth', '地基'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（地基：開印目標 3 秒內耐力不回復（自有效果把耐力回復設 0））'),  # 1,3,0 v0.4 負責：DLL N3＋引擎效果
    ('earth', '裂地'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（裂地：開印目標 8 秒內若被土弄倒，倒地標記 3 → 5 秒）'),  # 1,3,1 v0.4 負責：DLL N3
    ('earth', '開印效果'): ('KEPT-N3', 'ESSBElem.OpenMult',
        '開印效果 +3%／點'),  # 1,4 v0.4 負責：DLL N3
    ('earth', '先震'): ('KEPT-N5', 'ESSBElem2.OpenEarth → Quake(0.5, abKnock = False)',
        '先震：同調三段開印立即一次 ×0.5 地震，不含跌倒'),  # 1,4,0 v0.4 負責：DLL N5
    ('earth', '終焉'): ('KEPT-N3', 'ESSBElem.EndMult',
        '終焉 +2%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('earth', '崩裂'): ('KEPT-N5', 'ESSBElem2.QuakeK',
        '崩裂：地震 ×1.5 → ×2.0'),  # 2,0,0 v0.4 負責：DLL N5
    ('earth', '土印記的融斷'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '土印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('earth', '廣震'): ('KEPT-N5', 'ESSBElem2.QuakeRadius',
        '廣震：地震範圍 210 → 350 單位（3 → 5 公尺）'),  # 2,1,0 v0.4 負責：DLL N5
    ('earth', '固土'): ('KEPT-N4', 'ESSBElem2.EndEarthNodes → ESSBController.SetSelf(2)',
        '固土：土終焉後你岩甲滿層'),  # 2,1,1 v0.4 負責：DLL N4
    ('earth', '地震耐力削減'): ('KEPT-N5', 'ESSBElem2.QuakeStamina',
        '地震耐力削減 +3%／點（審查修正：基礎係數 4.0 → v0.4 的 B_max ×2）'),  # 2,2 v0.4 負責：DLL N5
    ('earth', '地斷'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（地斷：土印記融斷時，範圍內耐力低於 30% 的目標直接跌倒（掛倒地））'),  # 2,2,0 v0.4 負責：DLL N5（`AIProcess::KnockExplosion`）
    ('earth', '蓄能'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（蓄能：消耗全部蓄勁，格擋觸發時換算每點蓄勁物理減傷 +1%（持續 3 秒）；重擊觸發時換算每點蓄勁下一次地震／碎岩傷害 +5%（可調））'),  # 2,2,1 v0.4 負責：DLL 受擊 N4；DLL N4
    ('earth', '土印記的融斷再'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '土印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('earth', '山崩'): ('KEPT-N5', 'ESSBElem2.EndEarthNodes',
        '山崩：土終焉對範圍內所有帶裂痕的目標各一次地震'),  # 2,3,0 v0.4 負責：DLL N5
    ('earth', '塵暴'): ('KEPT-N5', 'ESSBElem2.QuakeOne',
        '塵暴：地震使範圍內敵人攻擊 -20% 3 秒'),  # 2,3,1 v0.4 負責：DLL N5
    ('earth', '地震'): ('KEPT-N3', 'ESSBElem.SignatureMult → ESSBElem2.Quake',
        '地震 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('earth', '地裂'): ('PARTIAL-N3', 'ESSBElem2.EndEarthNodes → StartDomain(4) → ESSBController.TickDomain',
        '土印記融斷後 5 秒地裂帶：內部敵人耐力不回復、耐力歸 0 在其中跌倒（每目標 8 秒一次）；「掛倒地」要等倒地標記（N3）。v0.3 的減速 50% 已拿掉'),  # 2,4,0 v0.4 負責：Papyrus（領域與推力）
    # ================= 5.7 風（wind）
    ('wind', '風刃傷害'): ('KEPT-N4', 'ESSBElem2.WindBladeMult',
        '風刃傷害 +2%／點'),  # 0,0 v0.4 負責：DLL N4
    ('wind', '迴旋'): ('KEPT-N5', 'ESSBElem2.WindBlade',
        '迴旋：風刃改為對附近 2 人各一段'),  # 0,0,0 v0.4 負責：DLL N5
    ('wind', '風附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '風附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('wind', '亂舞'): ('KEPT-N4', 'ESSBElem2.WindThreshold',
        '亂舞：風勢門檻 4 → 3'),  # 0,1,0 v0.4 負責：DLL N4
    ('wind', '順風'): ('DONE', 'DLL native/include/HitMath.h AddFlatHitNodes（node::kWindTailwind）',
        '命中回復耐力（25 × G，round 20 D6）'),  # 0,1,1 v0.4 負責：DLL N2
    ('wind', '風形態移速再'): ('DONE', 'ESSBElem2.WindSpeedBonus → ESSBController.RefreshWindAbilities',
        '風形態移速 +10% 再 +0.5%／點'),  # 0,2 v0.4 負責：Papyrus
    ('wind', '追風'): ('KEPT-N4', 'ESSBElem2.WindBladeOne',
        '追風：風刃命中回耐力 3 並讓目標失衡（審查修正：數值照 v0.4，不乘 G(L)）'),  # 0,2,0 v0.4 負責：DLL N4
    ('wind', '無聲'): ('DONE', 'SPEL ESSB_Ability_Muffle + ESSBController.RefreshWindAbilities',
        '潛行中完全無聲、潛行移速 +20%'),  # 0,2,1 v0.4 負責：Papyrus
    ('wind', '同調每段風附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段風附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('wind', '殘影'): ('KEPT-N4', 'ESSBGuard.OnHitEx + PERK ESSB_P_wind_0_3_B1 進入點 0x24 ×0',
        '殘影：風勢滿被近戰命中擲 30%，成功就消耗風勢並開 2 秒受傷 ×0 視窗，抵掉一次後立刻關閉'),  # 0,3,0 v0.4 負責：DLL 受擊 N4
    ('wind', '疾風'): ('PARTIAL-基礎', 'ESSBElem2.WindSpeedBonus',
        '移速再 +10% 已做；「衝刺時每秒回補耐力再加倍」要先有 1.1 的風形態衝刺回補（基礎機制，本模組還沒有，不屬技能樹）'),  # 0,3,1 v0.4 負責：Papyrus
    ('wind', '暗風'): ('KEPT-N4', 'ESSBElem2.SneakMult / WindBladeMult',
        '暗風：潛行風附傷 ×3 → ×5，潛行送出的風刃 ×2'),  # 0,3,2 v0.4 負責：DLL N4
    ('wind', '千刃'): ('KEPT-N4', 'ESSBElem2.OnWindHit',
        '千刃：同調三段時每次命中 5%／點機率附帶風刃'),  # 0,4 v0.4 負責：DLL N4
    ('wind', '御風'): ('PARTIAL-N3', 'ESSBElem2.WindSlowImmune → ESSBNodes.SelfSlowImmune；ESSBElem2.TargetDamageMult（差額補丁 ×1.3）',
        '同調三段時免疫減速、失衡目標受附傷 +30% 已做；「含武器傷害」要等失衡改成目標身上的效果，PERK 才讀得到（N3）'),  # 0,4,0 v0.4 負責：引擎效果
    ('wind', '開印風勢'): ('KEPT-N4', 'ESSBElem2.OpenStacks(5)',
        '開印風勢 +1／每 5 點'),  # 1,0 v0.4 負責：DLL N4
    ('wind', '風襲'): ('KEPT-N3', 'ESSBElem2.OpenWind',
        '風襲：開印時附近 1 人也風痕'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('wind', '開印拉近距離'): ('DONE', 'ESSBElem2.PullDistance → ESSBController.PullIn',
        '開印拉近 1.5 公尺 +0.1 公尺／點（最多 3）'),  # 1,1 v0.4 負責：Papyrus（推力）
    ('wind', '疾風痕'): ('KEPT-N4', 'ESSBElem2.OpenStacks(5)',
        '疾風痕：開印風勢直接滿'),  # 1,1,0 v0.4 負責：DLL N4
    ('wind', '輕躍'): ('KEPT-N3', 'ESSBElem2.OpenWind',
        '輕躍：開印後 3 秒移速 +10%'),  # 1,1,1 v0.4 負責：DLL N3
    ('wind', '風印記持續'): ('PARTIAL-N3', 'ESSBElem.MarkDurationBonus',
        '風印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,2 v0.4 負責：DLL N3
    ('wind', '氣旋'): ('DONE', 'ESSBElem2.OnFormOpened(5) → ESSBController.PullIn',
        '風臨時把範圍內敵人拉到你面前 2 公尺'),  # 1,2,0 v0.4 負責：Papyrus
    ('wind', '奇襲'): ('KEPT-N3', 'ESSBElem2.OpenWind（ESSBController.LastHitWasSneak）',
        '奇襲：潛行攻擊的開印同時觸發終焉（abChain 防遞迴），且不拉近'),  # 1,2,1 v0.4 負責：DLL N3
    ('wind', '風臨'): ('KEPT-N5', 'ESSBElem.OnFormOpened',
        '風臨：開風形態時對範圍內敵人各開印一次'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('wind', '牽引'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（牽引：開印拉近時，目標身後 1.5 公尺內的其他敵人也一起被拉近並失衡（最多 2 人，各自 3 秒推力冷卻））'),  # 1,3,0 v0.4 負責：DLL N3（掃描 N5）＋Papyrus（推力）
    ('wind', '氣流'): ('KEPT-N3', 'ESSBElem2.OpenWind',
        '氣流：開印時回復 10 耐力（審查修正：數值照 v0.4，不乘 G(L)）'),  # 1,3,1 v0.4 負責：DLL N3
    ('wind', '開印效果'): ('KEPT-N3', 'ESSBElem.OpenMult',
        '開印效果 +3%／點'),  # 1,4 v0.4 負責：DLL N3
    ('wind', '先風'): ('KEPT-N4', 'ESSBElem2.OpenWind',
        '先風：同調三段時開印附帶一段風刃'),  # 1,4,0 v0.4 負責：DLL N4
    ('wind', '終焉'): ('KEPT-N3', 'ESSBElem.EndMult',
        '終焉 +2%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('wind', '亂流'): ('KEPT-N5', 'ESSBReactions.EndWind',
        '亂流：風刃附近目標 2 → 5 人'),  # 2,0,0 v0.4 負責：DLL N5
    ('wind', '風印記的融斷'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '風印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('wind', '上天'): ('KEPT-N3', 'ESSBElem2.BlowAway → ESSBController.LiftUp → ESSBStatus 浮空',
        '上天：吹飛改吹上天；浮空是自有的 2 秒狀態（不讀物理），落地傷害在到期時結算'),  # 2,1,0 v0.4 負責：DLL N3／N5＋Papyrus（推力）
    ('wind', '風斷'): ('KEPT-N5', 'ESSBElem2.EndWindNodes',
        '風斷：風印記融斷時每個目標各兩段風刃'),  # 2,1,1 v0.4 負責：DLL N5
    ('wind', '多段觸發'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（主線：多段觸發，風印記被切掉時接管元素的命中觸發次數 +1／每 5 點（2 → 最多 5））'),  # 2,2 v0.4 負責：DLL N4
    ('wind', '風渦'): ('KEPT-N5', 'ESSBElem2.EndWindNodes → ESSBController.PullTo',
        '風渦：終焉時 5 公尺內敵人被拉向目標聚攏'),  # 2,2,0 v0.4 負責：DLL N5＋Papyrus（推力）
    ('wind', '風印記的融斷再'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '風印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('wind', '颶風'): ('KEPT-N5', 'ESSBElem2.EndWindNodes',
        '颶風：融斷的吹上天改為對範圍內所有敵人，不限帶風印記'),  # 2,3,0 v0.4 負責：DLL N5＋Papyrus
    ('wind', '順勢'): ('KEPT-N4', 'ESSBController.SetWindFollow → OnWeaponHit',
        '順勢：風終焉後 5 秒內接管元素的命中皆附帶一段風刃'),  # 2,3,1 v0.4 負責：DLL N4
    ('wind', '落地傷害'): ('KEPT-N3', 'ESSBElem2.LandingDamage',
        '落地傷害 ×0.5 → ×1.25（+5%／點）'),  # 2,4 v0.4 負責：DLL N3
    ('wind', '空中追擊'): ('PARTIAL-N4', 'ESSBElem2.TargetDamageMult（附傷 ×1.5）／WindBladeOne（再推高）',
        '浮空目標受附傷 ×1.5、風刃命中空中目標再推高；「含武器傷害」要等浮空改成目標身上的效果（N4）'),  # 2,4,0 v0.4 負責：引擎效果＋DLL N4＋Papyrus（推力）
    ('wind', '連殺'): ('KEPT-N5', 'ESSBElem2.OnKill → ESSBController.KeepSneak / TakeKillStreak',
        '連殺：潛行擊殺後 5 秒 PO3 PreventActorDetection，下一次潛行附傷 ×2 並重置奇襲'),  # 2,4,1 v0.4 負責：DLL N5＋Papyrus
    # ================= 5.8 鮮血（blood）
    ('blood', '流血每層傷害'): ('KEPT-N3', 'ESSBElem2.BleedTickMult / BleedDrainPercent → ESSBStatus.Tick',
        '流血每層傷害 +2%／點，放血係數 0.3% → 0.45%（首領同比例，0.1% → 0.15%）'),  # 0,0 v0.4 負責：DLL N3
    ('blood', '血刃'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（血刃：重擊扣掉的生命，50% 加進這一擊的血附傷（扣越多砍越重））'),  # 0,0,2 v0.4 負責：DLL N4
    ('blood', '深創'): ('KEPT-N3', 'ESSBElem2.BleedCap → ESSBController.StackCap(5)',
        '深創：血痕上限 8 → 12'),  # 0,0,1 v0.4 負責：DLL N3
    ('blood', '血附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '血附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('blood', '飲血'): ('PARTIAL-N5', 'ESSBElem2.OnKill ← ESSBController.OnKillEvent',
        '擊殺流血目標回血 20% ＋ 10 秒嗜血（命中效果 +20%，差額補丁）；嗜血的「吸血 +10%」要等嗜血改成你身上的效果、DLL 讀得到（N5）。v0.3 的「武器傷害 +10%」進入點已刪'),  # 0,1,0 v0.4 負責：DLL N5
    ('blood', '血溢'): ('DONE', 'DLL native/include/HitMath.h AddBloodLeech（node::kBloodOverflow）',
        '生命已滿時吸血溢出灌進護血（上限最大生命 20%）；扣減在 N4'),  # 0,1,1 v0.4 負責：DLL N2
    ('blood', '吸血比例各血位'): ('DONE', 'DLL native/include/HitMath.h LeechRatio（node::kBloodLeechRatio）＋ESSBController.GetBloodLeechRatio',
        '吸血比例各血位 +1%／點'),  # 0,2 v0.4 負責：DLL N2
    ('blood', '逆流'): ('DONE', 'DLL native/include/HitMath.h BloodCurveFraction（node::kBloodReverse）＋ESSBController.BloodPercent／BloodBandMult',
        '反轉血位曲線'),  # 0,2,0 v0.4 負責：DLL N2
    ('blood', '血承'): ('KEPT-N5', 'ESSBController.ApplyInherit（SPEL ESSB_InheritSpell，7 個 Peak Value Modifier）',
        '血承：擊殺流血目標吸收其火冰電毒魔抗各 50%、護甲 20%、最大生命 10%，15 秒，重掛即取代'),  # 0,2,1 v0.4 負責：DLL N5
    ('blood', '同調每段血附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段血附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('blood', '止血'): ('KEPT-N3', 'ESSBElem2.BleedTickMult',
        '止血：低血位（<30%）時流血傷害 ×1.5'),  # 0,3,0 v0.4 負責：DLL N3
    ('blood', '血怒'): ('DONE', 'DLL native/include/HitMath.h BloodRage（node::kBloodRage）＋ESSBController.NativeBloodCurve／GetBloodHitMult',
        '中血位命中效果與吸血 +15%'),  # 0,3,1 v0.4 負責：DLL N2
    ('blood', '血海'): ('KEPT-N5', 'ESSBElem2.SurgeRadius → ESSBReactions.EndBlood',
        '血海：同調三段時血潮改為範圍 1 公尺 +0.2 公尺／點'),  # 0,4 v0.4 負責：DLL N5
    ('blood', '不死'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（不死：同調三段時流血目標死亡，你回滿耐力，並回復生命到剛好越過上方最近的一條線（30% 或 70%），觸發一次回湧（不受越線冷卻，每 30 秒一次））。提前移除（指揮官裁定 C3）：v0.3 的舊效果本輪已刪，於 N5 以 v0.4 版本重做'),  # 0,4,0 v0.4 負責：DLL N5
    ('blood', '開印流血'): ('KEPT-N3', 'ESSBElem2.OpenStacks(6)',
        '開印流血 +1 層／每 5 點'),  # 1,0 v0.4 負責：DLL N3
    ('blood', '血濺'): ('KEPT-N3', 'ESSBElem2.OpenBlood',
        '血濺：開印時附近 1 人流血 1 層'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('blood', '開印後 5 秒內血附傷'): ('KEPT-N3', 'ESSBElem2.BloodHitMult',
        '開印後 5 秒內血附傷 +1%／點'),  # 1,1 v0.4 負責：DLL N3
    ('blood', '深血痕'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（深血痕：開印依你的血區：高血區血痕多 +2 層、中血區多 +1 層並吸血一次、低血區吸血兩次）'),  # 1,1,0 v0.4 負責：DLL N3
    ('blood', '開印回血'): ('KEPT-N3', 'ESSBElem2.OpenBlood',
        '開印回血：開印回血 B_max ×0.5，低血位 ×2（審查修正：數值照 v0.4，不乘 G(L)）'),  # 1,1,1 v0.4 負責：DLL N3
    ('blood', '血印記持續'): ('PARTIAL-N3', 'ESSBElem.MarkDurationBonus',
        '血印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,2 v0.4 負責：DLL N3
    ('blood', '血臨強化'): ('PARTIAL-N3', 'ESSBElem2.OnFormOpened(6) → ESSBController.PayBloodCost',
        '血臨時付最大生命 15%（代價路徑，留 1 點）；「立即觸發一次濺血」要等越線／濺血（N3／N5）。v0.3「血臨後 10 秒不扣血」已拿掉'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N3（濺血 N5）
    ('blood', '血臨'): ('KEPT-N5', 'ESSBElem.OnFormOpened',
        '血臨：開血形態時對範圍內敵人各開印一次'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('blood', '血咒'): ('KEPT-N3', 'ESSBElem2.OpenBlood（ESSB_Util_HealRateDebuff）',
        '血咒：開印目標 5 秒受治療 -50%；原版沒有「受治療」修正，改以 HealRateMult -50 表達，見實作紀錄'),  # 1,3,0 v0.4 負責：DLL N3
    ('blood', '血脈'): ('KEPT-N4', 'ESSBElem2.OpenBlood',
        '血脈：開印時 +2 同調'),  # 1,3,1 v0.4 負責：DLL N4
    ('blood', '開印效果'): ('KEPT-N3', 'ESSBElem.OpenMult',
        '開印效果 +3%／點'),  # 1,4 v0.4 負責：DLL N3
    ('blood', '血祭之始'): ('KEPT-N3', 'ESSBElem2.OpenBlood',
        '血祭之始：同調三段時開印立即結算一次 ×0.5 血潮'),  # 1,4,0 v0.4 負責：DLL N3
    ('blood', '終焉'): ('KEPT-N3', 'ESSBElem.EndMult',
        '終焉 +2%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('blood', '飽飲'): ('KEPT-N3', 'ESSBReactions.EndBlood',
        '飽飲：血潮結算的流血傷害 ×1.5'),  # 2,0,0 v0.4 負責：DLL N3
    ('blood', '血印記的融斷'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '血印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('blood', '血漫'): ('KEPT-N5', 'ESSBElem2.EndBloodNodes',
        '血漫：血潮結算時附近流血目標一起血潮（abChain 防遞迴）'),  # 2,1,0 v0.4 負責：DLL N5
    ('blood', '血斷'): ('KEPT-N5', 'ESSBReactions.EndBlood → ESSBController.Leech',
        '血斷：血印記融斷治療你該傷害的 50%'),  # 2,1,1 v0.4 負責：DLL N5
    ('blood', '血潮治療倍率 ×2'): ('KEPT-N3', 'ESSBElem2.SurgeHealMult',
        '血潮治療倍率 ×2，每點 +0.1'),  # 2,2 v0.4 負責：DLL N3
    ('blood', '血約'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（血約：往上越線（回湧）時，15 公尺內所有流血目標血痕 +2 層）'),  # 2,2,0 v0.4 負責：DLL N3（掃描 N5）
    ('blood', '血印記的融斷再'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '血印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('blood', '血契'): ('KEPT-N3', 'ESSBReactions.EndBlood → ESSBController.PayBloodCost',
        '血契：高血位（≥70%）時血終焉損失 10% 生命，血潮 ×2'),  # 2,3,0 v0.4 負責：DLL N3
    ('blood', '放血終焉'): ('KEPT-N3', 'ESSBElem2.SurgePercent',
        '放血終焉：血潮的當前生命項 10% → 20%（首領 3% → 6%）'),  # 2,3,1 v0.4 負責：DLL N3
    ('blood', '血引'): ('KEPT-N3', 'ESSBElem2.EndBloodNodes → ESSBController.SetPendingBleed(2)',
        '血引：血終焉後接管元素的開印附帶流血 2 層'),  # 2,3,2 v0.4 負責：DLL N3
    ('blood', '血潮'): ('KEPT-N3', 'ESSBElem.SignatureMult → ESSBReactions.EndBlood',
        '血潮 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('blood', '血池'): ('DONE', 'ESSBElem2.EndBloodNodes → StartDomain(6) → ESSBController.TickDomain',
        '血池：血印記融斷後留下 5 秒血池，你在其中每秒回血 B_max（審查修正：每秒回血 20，拿掉 G(L)；v0.4 沒寫數量）'),  # 2,4,0 v0.4 負責：Papyrus（領域）
    # ================= 5.9 神聖（divine）
    ('divine', '聖佑各階武器傷害與聖傷加成'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        '引擎效果掛在聖佑三階上；聖佑是 DLL N3，N3 上線時照 v0.4 實作。v0.3「聖印每層目標受聖傷 +1%／點」已拿掉'),  # 0,0 v0.4 負責：引擎效果
    ('divine', '護持'): ('KEPT-N3', 'ESSBElem2.OnDivineHit',
        '護持：命中獲得 10% 魔抗 3 秒'),  # 0,0,0 v0.4 負責：DLL N3
    ('divine', '驅魔'): ('DONE', 'DLL native/include/HitMath.h ElementMultiplier（node::kDivineExorcism）＋ESSBController.NativeProcUnit',
        '對死靈施法者 ×1.5'),  # 0,0,1 v0.4 負責：DLL N2
    ('divine', '聖附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '聖附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('divine', '神罰'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（神罰：聖裁計數只要 2 擊（第二擊就觸發））'),  # 0,1,0 v0.4 負責：DLL N3
    ('divine', '聖盾'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        '引擎效果讀聖佑階（DLL N3）；v0.3「聖盾層數抵消魔法傷害」與它的進入點、RefreshRecovery 改寫已拿掉'),  # 0,1,1 v0.4 負責：引擎效果
    ('divine', '聖裁傷害'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（主線：聖裁傷害 +2%／點）'),  # 0,2 v0.4 負責：DLL N3
    ('divine', '光耀'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（光耀：裁決後 3 公尺內的亡靈魔族 5 秒內受聖傷 +20%）'),  # 0,2,0 v0.4 負責：DLL N5
    ('divine', '聖灰'): ('KEPT-N5', 'ESSBElem2.OnAsh',
        '聖灰：敵人化為灰燼時你回復魔力 B_max ×2（審查修正：數值照 v0.4，不乘 G(L)）'),  # 0,2,1 v0.4 負責：DLL N5
    ('divine', '同調每段聖附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段聖附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('divine', '破邪斬'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（破邪斬：聖佑 III 時，聖裁對主目標造成的傷害另以 50% 濺到目標周圍 4 公尺內的其他敵人（最多 5 人，可調）；濺射只有傷害，不帶破防、不再觸發聖光爆，按接收者各自的抗性結算，對亡靈魔族 ×3 照算）'),  # 0,3,2 v0.4 負責：DLL N5
    ('divine', '庇護'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（庇護：生命低於 30% 時聖佑直接 III 並刷新，每 30 秒一次）'),  # 0,3,1 v0.4 負責：DLL 受擊 N4
    ('divine', '天啟'): ('KEPT-N5', 'ESSBElem2.JudgeArea',
        '天啟：同調三段時裁決改為範圍 1 公尺 +0.2 公尺／點'),  # 0,4 v0.4 負責：DLL N5
    ('divine', '神佑'): ('DONE', 'ESSBController.TakeDivineSave／RefreshDivineProtection + PERK ESSB_P_divine_0_4_B1 進入點 0x24',
        '同調三段時致命傷留 1 血並 2 秒無敵，每場戰鬥一次（延遲死亡）'),  # 0,4,0 v0.4 負責：Papyrus
    ('divine', '淨土'): ('KEPT-N5', 'ESSBElem2.ShouldAsh',
        '淨土：同調三段時神聖形態的所有擊殺都化灰，不限致命一擊是否神聖'),  # 0,4,1 v0.4 負責：DLL N5
    ('divine', '開印回血'): ('KEPT-N3', 'ESSBElem2.OpenDivine',
        '開印回血 +5%／點：聖印開印的回血 B_max ×0.5 再加 B_max ×0.05／點（×0.5 → ×1.25）（審查修正：數值照 v0.4，不乘 G(L)）'),  # 1,0 v0.4 負責：DLL N3
    ('divine', '聖輝'): ('KEPT-N3', 'ESSBElem2.OpenDivine',
        '聖輝：開印時附近 1 人也聖印'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('divine', '開印後 5 秒內聖附傷'): ('KEPT-N3', 'ESSBElem2.DivineHitMult',
        '開印後 5 秒內聖附傷 +1%／點'),  # 1,1 v0.4 負責：DLL N3
    ('divine', '慈光'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（慈光：開印時懲戒 +2（不需要聖佑 II））'),  # 1,1,0 v0.4 負責：DLL N3
    ('divine', '誓約'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（誓約：開印的目標 8 秒內打你，懲戒每次 +2 而不是 +1（盯住一個敵人讓它打你））'),  # 1,1,2 v0.4 負責：DLL N3＋DLL 受擊 N4
    ('divine', '聖印記持續'): ('PARTIAL-N3', 'ESSBElem.MarkDurationBonus',
        '聖印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,2 v0.4 負責：DLL N3
    ('divine', '聖臨強化'): ('DONE', 'ESSBElem2.OnFormOpened(7)',
        '聖臨時你與附近同伴回血 B_max ×2（審查修正：B_max ×2＝20，不再是 60×G）'),  # 1,2,0 v0.4 負責：Papyrus
    ('divine', '聖臨'): ('KEPT-N5', 'ESSBElem.OnFormOpened',
        '聖臨：開聖形態時對範圍內敵人各開印一次'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('divine', '聖痕'): ('KEPT-N3', 'ESSBElem2.IsHolyPrey / HolyVulnerability',
        '聖痕：帶本模組聖印記的目標也吃亡靈魔族判定（裁決 ×3），非亡靈另 +10% 聖傷'),  # 1,3,0 v0.4 負責：DLL N3＋引擎效果
    ('divine', '聖光'): ('KEPT-N5', 'ESSBElem2.OpenDivine → HealAllies',
        '聖光：開印時附近同伴回血 B_max（審查修正：數值照 v0.4，不乘 G(L)）'),  # 1,3,1 v0.4 負責：DLL N5
    ('divine', '開印效果'): ('KEPT-N3', 'ESSBElem.OpenMult',
        '開印效果 +3%／點'),  # 1,4 v0.4 負責：DLL N3
    ('divine', '聖啟'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（聖啟：同調三段時開印讓聖佑直接升到 II）'),  # 1,4,0 v0.4 負責：DLL N3
    ('divine', '終焉'): ('KEPT-N3', 'ESSBElem.EndMult',
        '終焉 +2%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('divine', '重裁'): ('KEPT-N3', 'ESSBElem2.JudgeK',
        '重裁：裁決 ×2.0 → ×3.0'),  # 2,0,0 v0.4 負責：DLL N3
    ('divine', '聖印記的融斷'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '聖印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('divine', '廣裁'): ('KEPT-N5', 'ESSBElem2.JudgeArea',
        '廣裁：裁決改為 3 公尺範圍'),  # 2,1,0 v0.4 負責：DLL N5
    ('divine', '聖斷'): ('KEPT-N5', 'ESSBElem2.EndDivineNodes',
        '聖斷：聖印記融斷每個目標治療你 B_max ×1.0（審查修正：數值照 v0.4，不乘 G(L)）'),  # 2,1,1 v0.4 負責：DLL N5
    ('divine', '終焉後 5 秒內接管元素附傷'): ('KEPT-N3', 'ESSBElem.OnEnd → ESSBController.SetEndBoost / GetHitMult',
        '終焉後 5 秒內接管元素附傷 +1%／點（本輪順手把 round 1 只寫入沒讀取的那一半補上）'),  # 2,2 v0.4 負責：DLL N3
    ('divine', '聖域'): ('DONE', 'ESSBElem2.EndDivineNodes → StartDomain(7, 5) + PERK ESSB_P_divine_2_2_B1 進入點 0x24（ESSB_DomainDivine）',
        '聖終焉後留下 5 秒聖域：其中敵人傷害 -20%（你在其中受傷 -20%）、你持續回復（審查修正：每秒回血 25、回魔 20，拿掉 G(L)；v0.4 沒寫數量）'),  # 2,2,0 v0.4 負責：Papyrus（領域）
    ('divine', '淨灰'): ('KEPT-N5', 'ESSBElem2.OnAsh',
        '淨灰：化灰時爆出聖光，附近亡靈受 B_max ×1.0 聖傷'),  # 2,2,1 v0.4 負責：DLL N5
    ('divine', '聖印記的融斷再'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '聖印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('divine', '天誅'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（天誅：懲戒上限 5 → 8；裁決消耗懲戒時，懲戒的加成部分另外對 3 公尺內其他敵人各結算一次（最多 5 人））'),  # 2,3,2 v0.4 負責：DLL 受擊 N4；DLL N5
    ('divine', '聖引'): ('KEPT-N3', 'ESSBElem2.EndDivineNodes → ESSBController.SetPendingHeal',
        '聖引：聖終焉後接管元素的開印治療你 B_max（審查修正：數值照 v0.4，不乘 G(L)）'),  # 2,3,1 v0.4 負責：DLL N3
    ('divine', '裁決'): ('KEPT-N3', 'ESSBElem.SignatureMult → ESSBElem2.Judge',
        '裁決 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('divine', '神聖領域'): ('PARTIAL-N5', 'ESSBElem2.EndDivineNodes → StartDomain(7, 8) + PERK ESSB_P_divine_2_4_B1 進入點 0x24',
        '聖印記融斷後留下 8 秒聖域（同聖域：其中敵人傷害 -20%、你持續回復）。差距：「聖佑 III 時融斷不清空聖佑」要等聖佑（DLL N3）'),  # 2,4,0 v0.4 負責：DLL N5＋Papyrus（領域）
    # ================= 5.10 毒素（poison）
    ('poison', '每劑傷害'): ('KEPT-N3', 'ESSBElem3.PoisonTickMult → ESSBStatus.Tick',
        '毒層每層每秒傷害 +2%／點'),  # 0,0 v0.4 負責：DLL N3
    ('poison', '免疫'): ('DONE', 'SPEL ESSB_Ability_PoisonResist + ESSBController.RefreshAbilities',
        '毒形態毒抗 +50%'),  # 0,0,0 v0.4 負責：Papyrus
    ('poison', '毒附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '毒附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('poison', '萎靡'): ('KEPT-N3', 'ESSBElem3.OnPoisonHit',
        '衰弱：毒層 ≥5 時目標攻擊 -15% 3 秒（AV 34，同攻擊削弱）'),  # 0,1,0 v0.4 負責：DLL N3
    ('poison', '毒皮'): ('KEPT-N4', 'ESSBGuard.OnHitEx → ESSBElem3.OnPoisonSkin',
        '毒皮：被近戰命中時攻擊者 +2 毒層，每攻擊者 3 秒一次'),  # 0,1,1 v0.4 負責：DLL 受擊 N4
    ('poison', '瘴氣每秒傳遞劑量'): ('LATER-待決', '—（只有 perk 記錄；本輪不讀）',
        '待決 上線時照 v0.4 實作（主線：瘴氣每秒傳遞劑量 +0.05／點（0.5 → 2.0，催毒中 1.0 → 3.5，可調））'),  # 0,2 v0.4 負責：引擎效果（披風）；劑數併入：待決（見 10.4）
    ('poison', '侵蝕'): ('KEPT-N3', 'ESSBElem3.OnPoisonHit',
        '侵蝕：毒層 ≥10 時目標毒抗 -20% 6 秒'),  # 0,2,0 v0.4 負責：DLL N3
    ('poison', '傳染門檻'): ('KEPT-N3', 'ESSBElem3.SpreadThreshold',
        '傳染門檻：基礎擴散門檻 5 層 → 1 層'),  # 0,2,1 v0.4 負責：DLL N3
    ('poison', '同調每段毒附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段毒附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('poison', '蔓延'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（蔓延：死亡擴散的份額 50% → 75%）。提前移除（指揮官裁定 C3）：v0.3 的舊效果本輪已刪，於 N5 以 v0.4 版本重做'),  # 0,3,0 v0.4 負責：DLL N5
    ('poison', '以毒攻毒'): ('DONE', 'ESSBElem3.PoisonFormTick',
        '你中毒時生命回復 +20%'),  # 0,3,1 v0.4 負責：引擎效果
    ('poison', '瘟疫'): ('KEPT-待決', 'ESSBElem3.PoisonTickHook ← ESSBStatus.Tick',
        '瘟疫：同調三段時每秒以 5%／點 的機率額外自動擴散一層'),  # 0,4 v0.4 負責：待決
    ('poison', '百毒不侵'): ('DONE', 'ESSBElem3.PoisonFormTick',
        '同調三段時免疫中毒與疾病，附近中毒敵人每秒替你回血（審查修正：每個中毒敵人回血 6，拿掉 G(L)；v0.4 沒寫數量）'),  # 0,4,0 v0.4 負責：引擎效果（免疫）＋Papyrus（每秒掃描回血）
    ('poison', '開印劑數'): ('KEPT-N3', 'ESSBElem3.OpenStacks → ESSBReactions.Open',
        '開印毒層 3 +1／每 3 點'),  # 1,0 v0.4 負責：DLL N3
    ('poison', '毒濺'): ('KEPT-N3', 'ESSBElem3.OpenPoison',
        '毒濺：開印時附近 1 人 +2 毒層'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('poison', '開印後 5 秒內毒附傷'): ('KEPT-N3', 'ESSBElem3.PoisonHitMult（GetOpenBoost）',
        '開印後 5 秒內毒附傷 +1%／點'),  # 1,1 v0.4 負責：DLL N3
    ('poison', '濃毒'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（濃毒：開印時若 6 公尺內已有中毒的敵人，從劑數最高的那一個複製 2 劑到新目標（不從對方扣））'),  # 1,1,0 v0.4 負責：DLL N3（掃描 N5）
    ('poison', '毒膜'): ('KEPT-N3', 'ESSBElem3.OpenPoison',
        '毒膜：開印時你毒抗 +50% 5 秒'),  # 1,1,1 v0.4 負責：DLL N3
    ('poison', '毒印記持續'): ('PARTIAL-N3', 'ESSBElem.MarkDurationBonus',
        '毒印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,2 v0.4 負責：DLL N3
    ('poison', '毒臨強化'): ('KEPT-N5', 'ESSBElem3.OnFormOpened(8)',
        '毒臨強化：毒臨時範圍內敵人 +3 毒層'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N5
    ('poison', '毒臨'): ('KEPT-N5', 'ESSBElem.OnFormOpened',
        '毒臨：開毒形態時對範圍內敵人各開印一次，2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('poison', '腐蝕開印'): ('KEPT-N3', 'ESSBElem3.OpenPoison',
        '腐蝕開印：開印目標毒抗 -10% 8 秒'),  # 1,3,0 v0.4 負責：DLL N3
    ('poison', '毒血'): ('KEPT-N3', 'ESSBElem3.OpenPoison',
        '毒血：開印時你回血 B_max ×0.5（審查修正：數值照 v0.4，不乘 G(L)）'),  # 1,3,1 v0.4 負責：DLL N3
    ('poison', '開印效果'): ('KEPT-N3', 'ESSBElem.OpenMult',
        '開印效果 +3%／點'),  # 1,4 v0.4 負責：DLL N3
    ('poison', '劇毒之始'): ('KEPT-N3', 'ESSBElem3.OpenPoison',
        '劇毒之始：同調三段時開印毒層 ×2（再補一份等量的開印層數）'),  # 1,4,0 v0.4 負責：DLL N3
    ('poison', '終焉'): ('KEPT-N3', 'ESSBElem.EndMult',
        '終焉 +2%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('poison', '潰爛'): ('KEPT-N3', 'ESSBElem3.CatalyzeRate → ESSBStatus.Tick',
        '潰爛：催毒期間每秒跳三次（基礎兩次）'),  # 2,0,0 v0.4 負責：DLL N3
    ('poison', '毒印記的融斷'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '毒印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('poison', '延毒'): ('KEPT-N3', 'ESSBElem3.CatalyzeSeconds',
        '延毒：催毒 8 → 12 秒'),  # 2,1,0 v0.4 負責：DLL N3
    ('poison', '疫染'): ('KEPT-N5', 'ESSBElem3.EndPoisonNodes',
        '瘴氣：毒終焉時毒層以原層數複製到 6 公尺內 5 人（結清 engine-coverage 的「瘴氣複製」）'),  # 2,1,1 v0.4 負責：DLL N5
    ('poison', '終焉後 5 秒內接管元素附傷'): ('KEPT-N3', 'ESSBElem.OnEnd → ESSBController.SetEndBoost / GetHitMult',
        '終焉後 5 秒內接管元素附傷 +1%／點'),  # 2,2 v0.4 負責：DLL N3
    ('poison', '毒斷'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（毒斷：融斷的催毒改為強度 ×4）'),  # 2,2,0 v0.4 負責：DLL N5
    ('poison', '毒印記的融斷再'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '毒印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('poison', '劇毒'): ('KEPT-N3', 'ESSBElem3.ApplyVirulence',
        '劇毒：催毒期間下一個等量於目標當前毒抗的削減，等效於「毒抗視為 0」（同碎冰碎甲的做法）'),  # 2,3,0 v0.4 負責：DLL N3
    ('poison', '腐蝕終焉'): ('KEPT-N3', 'ESSBElem3.EndPoisonNodes',
        '腐蝕終焉：毒終焉後目標魔抗 -20% 8 秒'),  # 2,3,1 v0.4 負責：DLL N3
    ('poison', '催毒期間中毒傷害'): ('KEPT-N3', 'ESSBElem3.PoisonTickMult（催毒中）',
        '催毒期間毒層傷害 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('poison', '毒霧'): ('KEPT-待決', 'ESSBElem3.EndPoisonNodes → ESSBController.StartDomain(8, 5)',
        '毒霧：毒印記融斷後 5 秒毒霧，內部每秒 +1 毒層'),  # 2,4,0 v0.4 負責：Papyrus（領域）；劑數併入：待決
    # ================= 5.11 水（water）
    ('water', '浸濕持續'): ('DONE', 'ESSBElem3.WetSeconds（Papyrus 浸濕）＋DLL 雨雪浸濕（固定時長法術 ESSB_Native_Soak_*，node::kWaterSoakDuration）',
        '浸濕 10 秒 +0.3 秒／點（只延長浸濕本身）；雨雪與站在水中的浸濕由 DLL 挑對應秒數的法術（指揮官裁定 R6）'),  # 0,0 v0.4 負責：DLL N3
    ('water', '清流'): ('DONE', 'DLL native/include/HitMath.h AddFlatHitNodes（node::kWaterClearStream）',
        '命中回復耐力 30（ESSB_WaterClearStamina）'),  # 0,0,0 v0.4 負責：DLL N2
    ('water', '長流每秒回復'): ('DONE', 'ESSBElem3.FlowPercent → WaterFormTick',
        '長流每秒回復生命與耐力 2.0% +0.2%／點（settings 可調）'),  # 0,1 v0.4 負責：Papyrus
    ('water', '水壓'): ('KEPT-N3', 'ESSBElem3.OnWaterHit + WaterHitMult',
        '水壓：命中浸濕目標 +1 水壓（狀態 kind 9），每層水附傷 +10%（結清 engine-coverage 的「水壓」）'),  # 0,1,0 v0.4 負責：DLL N3
    ('water', '水盾'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        '改的是水幕的分擔比例與效率；水幕本體（PERK＋DLL 受擊 N4 扣魔）還沒上線，先做分擔等於白送減傷，所以跟水幕一起在 N4 做'),  # 0,1,2 v0.4 負責：引擎效果（PERK）＋DLL 受擊 N4
    ('water', '水壓每層水附傷'): ('KEPT-N3', 'ESSBElem3.WaterHitMult',
        '水壓每層水附傷 +1%／點'),  # 0,2 v0.4 負責：DLL N3
    ('water', '洗淨'): ('KEPT-N4', 'ESSBElem3.OnWaterHit → ESSBController.TakeCleanse / ApplyCleanse',
        '洗淨：命中時清除自身一個負面效果，每 3 秒一次；逐項 DispelSpell 自有減益 + Cure Disease（不用 Dispel 原型，絕不洗自己的增益）'),  # 0,2,0 v0.4 負責：DLL N4
    ('water', '同調每段長流回復'): ('DONE', 'ESSBElem3.FlowPercent',
        '同調每段長流 +0.05%／點'),  # 0,3 v0.4 負責：Papyrus
    ('water', '潮身'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（潮身：水幕把魔力扣到 0 的那一刻，立即洗淨一次（不佔洗淨冷卻）並回復最大魔力 20%，水幕馬上恢復，每 30 秒一次）'),  # 0,3,2 v0.4 負責：DLL 受擊 N4
    ('water', '淨化'): ('KEPT-N4', 'ESSBController.ApplyCleanse(True) → DispelHostileEffects（SPEL ESSB_PurgeSpell）',
        '淨化：洗淨再加解毒，並用 PO3 GetActiveEffects 掃掉所有帶敵對／有害旗標的外來效果'),  # 0,3,1 v0.4 負責：DLL N4
    ('water', '長河'): ('DONE', 'ESSBElem3.FlowPercent / WaterFormTick',
        '同調三段時長流再 +0.05%／點且作用於附近同伴'),  # 0,4 v0.4 負責：Papyrus
    ('water', '止水'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        '同水盾：依附水幕（PERK＋N4 扣魔），N4 一起做'),  # 0,4,1 v0.4 負責：引擎效果（PERK）
    ('water', '開印時回復生命與耐力各最大值 0.3%／點'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（主線：開印時回復生命與耐力各最大值 0.3%／點（15 點 4.5%））'),  # 1,0 v0.4 負責：DLL N3
    ('water', '廣佈'): ('KEPT-N3', 'ESSBElem3.OpenWater',
        '廣佈：開印時浸濕擴散到附近 1 人'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('water', '開印後 5 秒內水附傷'): ('KEPT-N3', 'ESSBElem3.WaterHitMult（GetOpenBoost）',
        '開印後 5 秒內水附傷 +1%／點'),  # 1,1 v0.4 負責：DLL N3
    ('water', '深濕'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（深濕：開印時若下雨、下雪或你站在水中，目標水壓直接滿格（立即沖刷；需已取得水壓））'),  # 1,1,0 v0.4 負責：DLL N3
    ('water', '湧泉'): ('KEPT-N3', 'ESSBElem3.OpenWater',
        '回流：開印時回復耐力 15'),  # 1,1,1 v0.4 負責：DLL N3
    ('water', '水印記持續'): ('PARTIAL-N3', 'ESSBElem.MarkDurationBonus',
        '水印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,2 v0.4 負責：DLL N3
    ('water', '水臨強化'): ('PARTIAL-N5', 'ESSBElem3.OnFormOpened(9)',
        '水臨時範圍內敵人浸濕、你清除全部負面並回滿魔力（round 21 照 v0.4）；範圍掃描 N5 前由 Papyrus 做'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N5
    ('water', '水臨'): ('KEPT-N5', 'ESSBElem.OnFormOpened',
        '水臨：開水形態時對範圍內敵人各開印一次，2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('water', '開印沖刷'): ('KEPT-N3', 'ESSBElem3.OpenWater → ESSBController.ApplyStrip（SPEL ESSB_StripSpell）',
        '沖刷：開印驅散目標一個有時限的增益，每目標 10 秒一次（自有 Dispel 原型，不影響常駐能力）'),  # 1,3,0 v0.4 負責：DLL N3
    ('water', '淨潮'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（淨潮：任何沖刷（水壓滿格、開印沖刷、退潮、洗滌）每清掉目標一個增益，你回復生命與魔力各 B_max ×2）'),  # 1,3,2 v0.4 負責：DLL N3
    ('water', '開印效果'): ('KEPT-N3', 'ESSBElem.OpenMult',
        '開印效果 +3%／點'),  # 1,4 v0.4 負責：DLL N3
    ('water', '汪洋之始'): ('KEPT-N3', 'ESSBElem3.OpenWater → ESSBController.SetWetLock → ESSBStatus',
        '汪洋之始：同調三段時開印的浸濕不過期，直到被切掉（ClearStack(8) 才解除）'),  # 1,4,0 v0.4 負責：DLL N3
    ('water', '終焉'): ('KEPT-N3', 'ESSBElem.EndMult',
        '終焉 +2%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('water', '強引'): ('KEPT-N3', 'ESSBElem3.GuideMult',
        '強引：導引 ×1.5 → ×2.0'),  # 2,0,0 v0.4 負責：DLL N3
    ('water', '水印記的融斷'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '水印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('water', '退潮'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（退潮：水印記被切或融斷時，對目標沖刷一次（不需水壓滿格，每目標 10 秒一次））'),  # 2,1,2 v0.4 負責：DLL N3（融斷 N5）
    ('water', '水斷'): ('KEPT-N5', 'ESSBElem3.EndWaterNodes',
        '水斷：水印記融斷改為治療你並回復耐力，各等於該印記的融斷量（審查修正：治療量＝該印記的融斷量 B_max × K_sync × G(L) × M_mod（v0.4 2.7 D_burst，G 有依據）；拿掉 v0.3 多乘的 ×2.0）'),  # 2,1,1 v0.4 負責：DLL N5
    ('water', '終焉後 5 秒內接管元素附傷'): ('KEPT-N3', 'ESSBElem.OnEnd → ESSBController.SetEndBoost',
        '終焉後 5 秒內接管元素附傷 +1%／點'),  # 2,2 v0.4 負責：DLL N3
    ('water', '汪洋'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（汪洋：水終焉時目標的浸濕延長到 30 秒（不需要水印記；水壓、爆燃、大潮照常讀它））'),  # 2,2,0 v0.4 負責：DLL N3
    ('water', '水印記的融斷再'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '水印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('water', '大潮'): ('KEPT-N5', 'ESSBElem3.EndWaterNodes → ESSBController.SetNextEndMultOn',
        '大潮：水終焉時 5 公尺內所有浸濕目標都拿到接管元素的導引'),  # 2,3,0 v0.4 負責：DLL N5
    ('water', '洗滌'): ('KEPT-N3', 'ESSBElem3.EndWaterNodes',
        '洗滌：水終焉淨化你所有負面，並驅散目標一個有時限的增益'),  # 2,3,1 v0.4 負責：DLL N3
    ('water', '導引'): ('KEPT-N3', 'ESSBElem3.GuideMult（ESSBElem.SignatureMult）',
        '導引 +3%／點'),  # 2,4 v0.4 負責：DLL N3
    ('water', '潮池'): ('DONE', 'ESSBElem3.EndWaterNodes → StartDomain(9) → ESSBController.TickDomain',
        '水印記融斷後 5 秒水域：你在其中回血回耐並每秒洗淨一次；內部敵人每秒被沖刷一個增益（沖刷法術；v0.4 的 DLL 原生沖刷函式尚未有）（審查修正：每秒回血、回耐各 15，拿掉 G(L)；v0.4 沒寫數量）'),  # 2,4,0 v0.4 負責：Papyrus（領域；沖刷呼叫 DLL 原生函式）
    # ================= 5.12 黑暗（darkness）
    ('darkness', '詛咒每層抗性侵蝕'): ('KEPT-N3', 'ESSBElem3.ApplyCurseErosion',
        '詛咒每層抗性侵蝕 -（2% + 0.2%／點）：火冰電魔毒五種抗性，原型 34 會自己還原'),  # 0,0 v0.4 負責：DLL N3
    ('darkness', '咒延'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（咒延：詛咒 ≥3 層的目標，黑暗印記過期時續 4 秒（每目標一次），讓它死時還帶著印記）'),  # 0,0,1 v0.4 負責：DLL N3
    ('darkness', '暗附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '暗附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('darkness', '懼咒'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（懼咒：恐懼門檻 3 → 2 層）'),  # 0,1,2 v0.4 負責：DLL N3
    ('darkness', '怨縛'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（怨縛：詛咒目標打你時，它的詛咒 +1（每目標 2 秒一次））'),  # 0,1,3 v0.4 負責：DLL 受擊 N4
    ('darkness', '幻覺持續'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（主線：幻覺持續 +0.1 秒／點（恐懼 2 → 3.5 秒、瘋狂 3 → 4.5 秒））'),  # 0,2 v0.4 負責：DLL N3
    ('darkness', '狂咒'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（狂咒：瘋狂門檻 5 → 4 層）'),  # 0,2,1 v0.4 負責：DLL N3
    ('darkness', '同調每段暗附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段暗附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('darkness', '狂宴'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（狂宴：瘋狂中的敵人殺死的目標，視為帶黑暗印記死亡（詛咒門檻照常））'),  # 0,3,2 v0.4 負責：DLL N5（兇手判定見 10.3）
    ('darkness', '回魘'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（回魘：恐懼或瘋狂結束時，目標詛咒 +2 層（幻覺醒來，詛咒更深））'),  # 0,3,3 v0.4 負責：DLL N3
    ('darkness', '深淵'): ('KEPT-N3', 'ESSBElem3.CurseCap → ESSBController.StackCap',
        '深淵：同調三段時詛咒上限 +1／每 3 點（最多 +5，共 10）；抗性以 AV 負值侵蝕，本來就可為負'),  # 0,4 v0.4 負責：DLL N3
    ('darkness', '亡衛'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（亡衛：同調三段時，你復生的僕從死亡時爆出 3 公尺 B_max ×1.0 暗傷，範圍內敵人詛咒 +2 層）'),  # 0,4,1 v0.4 負責：DLL N5
    ('darkness', '開印詛咒'): ('KEPT-N3', 'ESSBElem3.OpenStacks → ESSBReactions.Open',
        '開印詛咒 2 層 +1／每 5 點'),  # 1,0 v0.4 負責：DLL N3
    ('darkness', '夢魘'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（夢魘：目標恐懼時，3 公尺內其他敵人詛咒 +1（每次恐懼一次））'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('darkness', '開印後 5 秒內暗附傷'): ('KEPT-N3', 'ESSBElem3.DarkHitMult（GetOpenBoost）',
        '開印後 5 秒內暗附傷 +1%／點'),  # 1,1 v0.4 負責：DLL N3
    ('darkness', '狂刃'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        '引擎效果掛在瘋狂 MGEF 上；但 v0.4 的瘋狂只由幻覺階梯（DLL N3）施加，本輪沒有任何來源會讓目標瘋狂，做了也看不到，跟幻覺階梯一起在 N3 做'),  # 1,1,2 v0.4 負責：引擎效果（掛在瘋狂 MGEF 上）
    ('darkness', '幻影'): ('PARTIAL-N3', 'ESSBElem3.OpenDark',
        '幻影：開印目標 3 秒內「對你的命中率 -30%」。差距：引擎沒有命中率修正，目前以攻擊 -30% 3 秒近似，要等 N3'),  # 1,1,1 v0.4 負責：DLL N3
    ('darkness', '暗印記持續'): ('PARTIAL-N3', 'ESSBElem.MarkDurationBonus',
        '暗印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,2 v0.4 負責：DLL N3
    ('darkness', '暗臨強化'): ('KEPT-N5', 'ESSBElem3.OnFormOpened(10)',
        '暗臨強化：暗臨時範圍內敵人恐懼 2 秒'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N5
    ('darkness', '暗臨'): ('KEPT-N5', 'ESSBElem.OnFormOpened',
        '暗臨：開暗形態時對範圍內敵人各開印一次，2 公尺 +0.2 公尺／點'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('darkness', '迷亂'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（迷亂：瘋狂中的目標被你命中時詛咒 +2 層）'),  # 1,3,0 v0.4 負責：DLL N3
    ('darkness', '暗染'): ('KEPT-N3', 'ESSBElem3.OpenDark',
        '暗染：開印時附近 1 人也詛咒（連印記一起給）'),  # 1,3,1 v0.4 負責：DLL N3（掃描 N5）
    ('darkness', '開印效果'): ('KEPT-N3', 'ESSBElem.OpenMult',
        '開印效果 +3%／點'),  # 1,4 v0.4 負責：DLL N3
    ('darkness', '群魔'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（群魔：同調三段時，目標達到瘋狂門檻那一刻，4 公尺內所有詛咒 ≥3 層的敵人一起瘋狂 3 秒（各自冷卻照算））'),  # 1,4,0 v0.4 負責：DLL N3（掃描 N5）＋Papyrus
    ('darkness', '終焉'): ('KEPT-N3', 'ESSBElem.EndMult',
        '終焉 +2%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('darkness', '饕餮'): ('KEPT-N3', 'ESSBElem3.AfterDeathCurse ← ESSBStatus.Tick',
        '饕餮：死咒結算時吸血吸魔各 B_max ×1.0（審查修正：數值照 v0.4，不乘 G(L)）'),  # 2,0,0 v0.4 負責：DLL N3
    ('darkness', '殘魂'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（殘魂：帶黑暗印記死亡、但詛咒只有 1～2 層的敵人也有 25% 機率復生（依等級表的階級））'),  # 2,0,2 v0.4 負責：DLL N5＋Papyrus
    ('darkness', '暗印記的融斷'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '暗印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('darkness', '不治'): ('KEPT-N3', 'ESSBElem3.DeathCurseSeconds → ESSBReactions.EndDark',
        '不治：死咒的「無法被治療」3 → 6 秒；以 HealRateMult -100% 表達（結清 engine-coverage 的「死咒無法被治療」）'),  # 2,1,0 v0.4 負責：DLL N3
    ('darkness', '冥印'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（冥印：暗印記被切時，目標留下一顆 8 秒「冥印」，帶冥印死亡視同帶黑暗印記（切到別的元素收尾也能復生））'),  # 2,1,2 v0.4 負責：DLL N3
    ('darkness', '死咒的「已損失生命」係數'): ('KEPT-N3', 'ESSBElem3.DeathCurseLostRatio → ESSBStatus.Tick',
        '死咒的「已損失生命」係數 15% +0.5%／點'),  # 2,2 v0.4 負責：DLL N3
    ('darkness', '亡魂'): ('KEPT-N5', 'ESSBElem3.AfterDeathCurse',
        '亡魂：死咒殺死目標時附近敵人恐懼 2 秒'),  # 2,2,0 v0.4 負責：DLL N5
    ('darkness', '噬咒'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（噬咒：死咒結算時消耗目標全部詛咒，每層讓「已損失生命」係數 +3%（吞了就不能拿這些層數換僕從））'),  # 2,2,2 v0.4 負責：DLL N3
    ('darkness', '暗印記的融斷再'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '暗印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('darkness', '冥召'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（冥召：死咒殺死的目標必定復生（無視詛咒門檻與有無印記），僕從階級 +1（最高五階））'),  # 2,3,2 v0.4 負責：DLL N5＋Papyrus
    ('darkness', '深淵回響'): ('KEPT-N3', 'ESSBElem3.EndDarkNodes',
        '深淵回響：暗終焉回滿你的魔力'),  # 2,3,1 v0.4 負責：DLL N3
    ('darkness', '死咒'): ('KEPT-N3', 'ESSBElem.SignatureMult → ESSBReactions.EndDark',
        '死咒 +3%／點'),  # 2,4 v0.4 負責：DLL N3
    ('darkness', '死域'): ('DONE', 'ESSBElem3.EndDarkNodes → ESSBController.StartDomain／TickDomain',
        '暗印記融斷後 5 秒死域：內部敵人無法被治療、每秒受 B_max ×0.5 暗傷'),  # 2,4,0 v0.4 負責：Papyrus（領域）
    ('darkness', '死靈主'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（死靈主：同調三段時亡者歸來不需要詛咒門檻（帶黑暗印記或冥印即可），60 級以上也能復生，且任何等級的僕從可改為永久（六階，永久上限 1 名））'),  # 2,4,1 v0.4 負責：DLL N5＋Papyrus
    # ================= 5.13 星界（astral）
    ('astral', '回聲比例'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（主線：回聲比例 +1%／點（25% → 40%，不吃節點倍率））'),  # 0,0 v0.4 負責：DLL N5
    ('astral', '星鏈'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（星鏈：被回聲打到的共鳴目標星痕 +1 層（不重新計時，每目標每 2 秒一次））'),  # 0,0,1 v0.4 負責：DLL N5
    ('astral', '星附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcAdept）',
        '星附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('astral', '聚星'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（聚星：引爆當下若 15 公尺內共鳴目標 ≥3，這次引爆 +30%）'),  # 0,1,2 v0.4 負責：DLL N3（計數 N5）
    ('astral', '星痕層數上限'): ('KEPT-N3', 'ESSBElem3.AstralCap → ESSBController.StackCap',
        '星痕層數上限 3 +1／每 5 點'),  # 0,2 v0.4 負責：DLL N3
    ('astral', '星痕弱點'): ('KEPT-N3', 'ESSBElem3.AstralHitMult',
        '星痕弱點：重擊時每層星痕 +8%'),  # 0,2,0 v0.4 負責：DLL N3
    ('astral', '同調每段星附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kProcMaster）',
        '同調每段星附傷 +1%／點'),  # 0,3 v0.4 負責：DLL N2
    ('astral', '餘輝'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（餘輝：闇宙用完回到一般形態時，立即得到 3 層共鳴層）'),  # 0,3,2 v0.4 負責：DLL N4
    ('astral', '永夜'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（主線：永夜，闇星每一擊 +3%／點）'),  # 0,4 v0.4 負責：DLL N4
    ('astral', '星蝕'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（星蝕：闇星中每一擊的傷害，另以 50% 回聲到所有其他共鳴目標（最多 5））'),  # 0,4,1 v0.4 負責：DLL N5
    ('astral', '天穹'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（天穹：同調三段時升闇星的門檻 10 → 7）'),  # 0,4,2 v0.4 負責：DLL N4
    ('astral', '星痕延遲'): ('KEPT-N3', 'ESSBElem3.AstralDelay → ESSBStatus.Tick',
        '星痕延遲 2 秒；10 點以上縮成 1 秒（狀態容器是整數秒 tick，只有兩檔）'),  # 1,0 v0.4 負責：DLL N3
    ('astral', '星散'): ('KEPT-N3', 'ESSBElem3.OpenAstral',
        '開印時附近 1 人（15 公尺內）也星痕；v0.3「範圍隨星臨主線成長」已拿掉'),  # 1,0,0 v0.4 負責：DLL N3（掃描 N5）
    ('astral', '開印後 5 秒內星附傷'): ('KEPT-N3', 'ESSBElem3.AstralHitMult（GetOpenBoost）',
        '開印後 5 秒內星附傷 +1%／點'),  # 1,1 v0.4 負責：DLL N3
    ('astral', '明星'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（明星：開印時若 15 公尺內已有其他共鳴目標，新目標與最近的那一個星痕各 +1）'),  # 1,1,0 v0.4 負責：DLL N3（掃描 N5）
    ('astral', '星印記持續'): ('PARTIAL-N3', 'ESSBElem.MarkDurationBonus',
        '星印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,2 v0.4 負責：DLL N3
    ('astral', '星臨強化'): ('KEPT-N5', 'ESSBElem3.OnFormOpened(11)',
        '星臨強化：星臨時範圍內敵人星痕 2 層（範圍同星臨）'),  # 1,2,0 v0.4 負責：Papyrus＋DLL N5
    ('astral', '星臨'): ('KEPT-N5', 'ESSBElem.OnFormOpened ＋ ESSBElem3.AdventRadius',
        '開星形態時對範圍內敵人各開印一次，2 公尺 +0.2 公尺／點（round 21 由 v0.3 的「+1 公尺／點、夜晚 ×1.5」改成 v0.4）'),  # 1,3 v0.4 負責：Papyrus＋DLL N5
    ('astral', '星鎖'): ('KEPT-N3', 'ESSBElem3.OpenAstral → ESSBController.SetStarLock → ESSBElem3.TargetDamageMult',
        '星鎖：開印目標 3 秒內受所有元素傷 +10%；只放大本模組造成的傷害（決定 61）'),  # 1,3,0 v0.4 負責：DLL N3＋引擎效果
    ('astral', '星門'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（星門：開印時你 +1 共鳴層（闇星中無效））'),  # 1,3,2 v0.4 負責：DLL N4
    ('astral', '開印效果'): ('KEPT-N3', 'ESSBElem.OpenMult',
        '開印效果 +3%／點'),  # 1,4 v0.4 負責：DLL N3
    ('astral', '星耀'): ('KEPT-N3', 'ESSBElem3.OpenAstral',
        '星耀：同調三段時開印的延遲星傷改為立即並 ×2'),  # 1,4,0 v0.4 負責：DLL N3
    ('astral', '終焉'): ('KEPT-N3', 'ESSBElem.EndMult',
        '終焉 +2%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('astral', '隕星'): ('KEPT-N3', 'ESSBElem3.FallK',
        '隕星：星落 ×2.0 → ×3.0'),  # 2,0,0 v0.4 負責：DLL N3
    ('astral', '星印記的融斷'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '星印記的融斷 +2%／點'),  # 2,1 v0.4 負責：DLL N5
    ('astral', '星斷'): ('KEPT-N5', 'ESSBElem3.Fall → ESSBController.ApplyTrueDamage(amount, target, 10)',
        '星斷：星印記融斷改為真實傷害 ×0.6，以星樹的 G(L) 計（不吃無元素樹的破魔加成）'),  # 2,1,1 v0.4 負責：DLL N5
    ('astral', '終焉後 5 秒內接管元素附傷'): ('KEPT-N3', 'ESSBElem.OnEnd → ESSBController.SetEndBoost',
        '與冰雷聖毒水同一條共用路徑（指揮官裁定 R2 的六棵樹）；v0.3 這格是「星落與星域的範圍」，已拿掉'),  # 2,2 v0.4 負責：DLL N3
    ('astral', '星殘'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（星殘：離開星形態（切換或 Z）時共鳴層不清空，保留 15 秒；15 秒內回到星形態就接著集）'),  # 2,2,1 v0.4 負責：Papyrus＋DLL N4
    ('astral', '星印記的融斷再'): ('KEPT-N5', 'ESSBElem.BurstMult',
        '星印記的融斷再 +2%／點'),  # 2,3 v0.4 負責：DLL N5
    ('astral', '墜星'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（墜星：闇星中切換時剩下的闇宙留到被切那一擊，每層對該目標結算一次 ×0.5 闇星一擊；闇星中按 Z 時，剩下的闇宙平均分給範圍內帶星印記的目標，同樣每層 ×0.5）'),  # 2,3,2 v0.4 負責：DLL N4（融斷 N5）
    ('astral', '星落'): ('KEPT-N3', 'ESSBElem.SignatureMult → ESSBElem3.Fall',
        '星落 +3%／點'),  # 2,4 v0.4 負責：DLL N3（融斷 N5）
    ('astral', '星域'): ('DONE', 'ESSBElem3.EndAstralNodes → StartDomain(11, 5, 3 公尺)＋ESSBElem3.TargetDamageMult（×1.2）',
        '星印記融斷後 5 秒星域（3 公尺），內部敵人受所有元素傷 +20%（附傷）；v0.3 範圍跟星落主線成長已拿掉'),  # 2,4,0 v0.4 負責：Papyrus（領域）
    # ================= 5.1 無元素：法殺（noform）
    ('noform', '吸魔量'): ('DONE', 'DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormSiphonAmount）',
        '吸魔量 +5%／點（不吃節點倍率，×1.0 → ×1.75），指揮官裁定 R5；v0.3 的「無形態武器傷害」進入點與 RefreshWeaponPercent 已刪'),  # 0,0 v0.4 負責：DLL N2
    ('noform', '逼近'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（逼近：15 公尺內的敵人施法時，你 2 秒內移速 +30%，這 2 秒內化法為力的回魔比例加倍（頂著法術衝上去），每 6 秒一次）'),  # 0,0,1 v0.4 負責：DLL N4（施法事件）＋引擎效果
    ('noform', '超載上限'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（主線：超載上限 +2%／點（+50% → +80%））'),  # 0,1 v0.4 負責：DLL N4
    ('noform', '蓄流'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（蓄流：超載開始衰減前的等待 3 → 6 秒）'),  # 0,1,2 v0.4 負責：DLL N4
    ('noform', '反擊'): ('PARTIAL-N4', 'ESSBGuard.OnHitEx（格擋）→ ESSBController.SetRiposte（SPEL ESSB_RiposteWindow 3 秒）→ DLL native/include/HitMath.h（node::kNoFormRiposte）',
        'N2 那一半本輪做完：DLL 讀反擊視窗，下一次無形態命中吸魔 ×2 並移除視窗；格擋偵測 N4 前留在 Papyrus 受擊事件'),  # 0,1,0 v0.4 負責：DLL 受擊 N4＋DLL N2
    ('noform', '法盾效率'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（主線：法盾效率，每擋 1 點花的魔力 -2%／點（最多 -30%：1.0 → 0.7，超載 0.75 → 0.53））'),  # 0,2 v0.4 負責：DLL 受擊 N4
    ('noform', '化勁'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（化勁：化法為力的回魔比例 30% → 60%）'),  # 0,2,1 v0.4 負責：DLL 受擊 N4
    ('noform', '法盾分擔'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        '改的是法盾分擔比例；法盾本體（PERK＋DLL 受擊 N4 扣魔）還沒上線，先做分擔等於白送減傷，跟法盾一起在 N4 做。v0.3「戰意每層武器傷害」進入點已刪'),  # 0,3 v0.4 負責：引擎效果（PERK）
    ('noform', '不屈'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（不屈：被命中時戰意 +1（每 3 秒一次），並重設戰意歸零計時）'),  # 0,3,1 v0.4 負責：DLL 受擊 N4
    ('noform', '餘魔'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（餘魔：法盾把魔力扣到 0 的那一刻不中斷，再以 30% 分擔 2 秒（改扣耐力），每 30 秒一次）'),  # 0,3,2 v0.4 負責：DLL 受擊 N4＋引擎效果
    ('noform', '不竭'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（主線：不竭，超載衰減每秒 -0.2%／點（5% → 2%））'),  # 0,4 v0.4 負責：DLL N4
    ('noform', '破式'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（破式：戰意滿層時的重擊消耗全部戰意，這一次滅法不花你的魔力（X 照算），倍率 +1.0，並沉默目標 2 秒）'),  # 0,4,1 v0.4 負責：DLL N4
    ('noform', '無魔'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（無魔：擊殺施法者回滿耐力與魔力（溢出進超載））'),  # 0,4,2 v0.4 負責：DLL N5
    ('noform', '滅法倍率'): ('DONE', 'DLL native/include/HitMath.h DispelMultiplier（node::kNoFormDispelRate）',
        '滅法倍率 +2%／點（不吃節點倍率，×1.0 → ×1.3；小滅法同一個倍率），指揮官裁定 R5'),  # 1,0 v0.4 負責：DLL N2
    ('noform', '奪魔'): ('DONE', 'DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormSeize）',
        '吸魔量取固定值與目標最大魔力 10% 較高者'),  # 1,0,0 v0.4 負責：DLL N2
    ('noform', '燒魔倍數'): ('DONE', 'DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormBurnMultiple）',
        '燒魔倍數 +7%／點（Y 最多是 X 的 1.0 → 2.05 倍），指揮官裁定 R5'),  # 1,1 v0.4 負責：DLL N2
    ('noform', '斷咒'): ('PARTIAL-N4', 'ESSBController.OnNoFormHit → ESSBNoForm.OnInterruptCast',
        '命中施法中的敵人打斷其施法（原版 InterruptCast），每 5 秒一次，成功時戰意 +1（審查修正：拿掉發明的「清空魔力＋1 秒沉默」）。差距：戰意本身是 N4——目前是 v0.3 的計數（5 秒未觸發歸零，v0.4 是 10 秒未命中歸零），而且讀戰意的破式是 LATER-N4'),  # 1,1,0 v0.4 負責：DLL N4
    ('noform', '反咒'): ('PARTIAL-N4', 'ESSBCounter.OnAnimationEvent → ESSBNoForm.OnCounterSpell',
        '帶滅法印的敵人施法時受該次施法消耗魔力 ×(1+0.02×無元素樹等級) 的真實傷害，戰意 +1（審查修正：補上戰意）。差距：施法偵測是 v0.3 的動畫事件（讀裝備法術），v0.4 是 DLL 施法事件＋CalculateMagickaCost；戰意同斷咒（N4）'),  # 1,1,2 v0.4 負責：DLL N4
    ('noform', '沉默'): ('DONE', 'DLL native/include/HitMath.h SilenceSeconds（node::kNoFormSilence）',
        '沉默 1 秒 +0.2 秒／點（最多 4 秒；首領減半、乘持續時間倍率，固定時長法術 1～8 秒）'),  # 1,2 v0.4 負責：DLL N2
    ('noform', '枯竭'): ('DONE', 'DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormDepletion）',
        '目標沒有魔力時滅法改燒你自己 2 倍的 X（round 20 D18）'),  # 1,2,0 v0.4 負責：DLL N2
    ('noform', '靜寂'): ('DONE', 'DLL native/include/HitMath.h TrueDamageMultiplier（node::kNoFormStillness）',
        '沉默中的目標受真實傷害 ×1.5'),  # 1,2,1 v0.4 負責：DLL N2
    ('noform', '對施法者與帶魔法護盾、元素披風的敵人燒魔'): ('DONE', 'DLL native/include/HitMath.h BurnBonus（node::kNoFormBurnCasters）',
        '對施法者燒魔 +5%／點'),  # 1,3 v0.4 負責：DLL N2
    ('noform', '破護'): ('KEPT-N4', 'ESSBGuard.OnHitEx + PERK ESSB_P_noform_1_3_B1 進入點 0x29',
        '破護：認出「來源是法術、無投射物、攻擊者帶原版 MagicCloak」那一跳，開 2 秒「受到的法術強度 ×0」視窗並逐跳刷新；第一跳仍會吃到，理由見實作紀錄'),  # 1,3,0 v0.4 負責：DLL 受擊 N4
    ('noform', '咒返'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（咒返：受到法術傷害時，對施法者施加滅法印（它的下一次施法就吃反咒），每 5 秒一次）'),  # 1,3,2 v0.4 負責：DLL 受擊 N4
    ('noform', '目標魔力低於 25% 時命中傷害'): ('DONE', 'DLL native/include/HitMath.h TrueDamageMultiplier（node::kNoFormLowMagicka）＋ESSBNoForm.TrueMult（Papyrus 真傷）',
        '目標魔力 <25% 時命中傷害 +3%／點'),  # 1,4 v0.4 負責：DLL N2
    ('noform', '噬命'): ('DONE', 'DLL native/include/HitMath.h PlanNoFormHit（node::kNoFormDevour）＋ESSBController.ApplyTrueDamage（Papyrus 真傷）',
        '真實傷害的 50% 轉為你的生命'),  # 1,4,1 v0.4 負責：DLL N2
    ('noform', '封印'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        '沉默改為 3 公尺範圍（範圍掃描 N5）；round 20 把沉默搬進 DLL 時 v0.3 的範圍沉默已拿掉'),  # 1,4,2 v0.4 負責：DLL N5
    ('noform', '融斷'): ('KEPT-N5', 'ESSBNoForm.BurstMult',
        '融斷 +2%／點'),  # 2,0 v0.4 負責：DLL N5
    ('noform', '免門檻'): ('DONE', 'ESSBNoForm.OnBurst → ESSBController.SetFreeOpen',
        '融斷後下一次開形態不需魔力'),  # 2,0,0 v0.4 負責：Papyrus
    ('noform', '寂每層燒魔'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（主線：寂每層燒魔 +0.5%／點（5% → 12.5%））'),  # 2,1 v0.4 負責：DLL N5
    ('noform', '收束'): ('KEPT-N5', 'ESSBNoForm.BurstRadius',
        '收束：融斷範圍 15 → 20 公尺'),  # 2,1,0 v0.4 負責：DLL N5
    ('noform', '寂滅'): ('PARTIAL-N5', 'DLL native/include/HitMath.h DispelMultiplier（node::kNoFormHushBreak；讀目標身上的寂 ESSB_HushEffect 與已用標記）',
        'N2 那一半本輪做完：寂 ≥3 層的目標，下一次滅法倍率 +0.5（用過在目標身上掛 10 秒已用標記）；寂本身由冷寂融斷給（N5），N5 前遊戲內不會有寂'),  # 2,1,2 v0.4 負責：DLL N2
    ('noform', '融斷範圍'): ('KEPT-N5', 'ESSBNoForm.BurstRadius',
        '融斷範圍 +0.3 公尺／點'),  # 2,2 v0.4 負責：DLL N5
    ('noform', '連斷'): ('KEPT-N4', 'ESSBNoForm.OnBurst → ESSBController.SetSyncKeep',
        '連斷：融斷後 5 秒內重開形態保留一半同調'),  # 2,2,0 v0.4 負責：Papyrus＋DLL N4
    ('noform', '寂上限'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（主線：寂上限 +1／每 5 點（5 → 8））'),  # 2,3 v0.4 負責：DLL N5
    ('noform', '斷界'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（斷界：融斷後對範圍內敵人施加所有被結清元素的弱化 3 秒）。審查修正：v0.3 的「減速 30%＋碎甲 10%」是發明的近似，已拿掉'),  # 2,3,0 v0.4 負責：DLL N5
    ('noform', '回流'): ('KEPT-N5', 'ESSBNoForm.OnBurst',
        '回流：融斷每個印記回魔 B_max ×0.5（審查修正：數值照 v0.4，不乘 G(L)）'),  # 2,3,1 v0.4 負責：DLL N5
    ('noform', '融斷再'): ('KEPT-N5', 'ESSBNoForm.BurstMult',
        '融斷再 +3%／點'),  # 2,4 v0.4 負責：DLL N5
    ('noform', '雙斷'): ('KEPT-N5', 'ESSBNoForm.OnBurst → ESSBController.OnFormOpened',
        '雙斷：融斷後 3 秒內再開形態，對範圍內敵人各開印一次'),  # 2,4,0 v0.4 負責：Papyrus＋DLL N5
    ('noform', '萬寂'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（萬寂：融斷時寂 ≥3 層的目標身上其他元素狀態（凍結、詛咒、血痕、中毒、水壓、星痕等）全部清除，每清一種寂 +1，並轉為一次「該元素 B_max ×0.5」的真實傷害）'),  # 2,4,1 v0.4 負責：DLL N5
    # ================= 5.2 全元素通用（common）
    ('common', '同調門檻'): ('KEPT-N4', 'ESSBNodes.SyncThresholdScale → ESSBController.SyncStage',
        '同調門檻 -2%／點，下限 0.4 倍'),  # 0,0 v0.4 負責：DLL N4
    ('common', '承接'): ('KEPT-N4', 'ESSBNodes.CarryOverSync → ESSBController.SwitchForm',
        '承接：切換保留前一形態 1/3 同調'),  # 0,0,0 v0.4 負責：Papyrus＋DLL N4
    ('common', '同調二段時附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kCommonStage2）＋ESSBNodes.CommonHitMult 鏡像',
        '同調二段時附傷 +1%／點'),  # 0,1 v0.4 負責：DLL N2
    ('common', '不移'): ('DONE', 'PERK ESSB_P_common_0_1_B1 進入點 0x21（受到的擊退 ×0，條件 ESSB_SyncStage ≥2）',
        '同調二段以上時免疫硬直（受到的擊退幅度 ×0）；「擊倒」由同一個進入點涵蓋擊退造成的倒地，ragdoll 類擊倒引擎沒有進入點'),  # 0,1,0 v0.4 負責：引擎效果
    ('common', '專一'): ('KEPT-N4', 'ESSBNodes.SyncThresholdScale + ESSBController.FormHeldSeconds',
        '專一：同形態 60 秒後門檻再 ×0.5'),  # 0,1,1 v0.4 負責：引擎效果（60 秒效果）＋DLL N4
    ('common', '同調三段時終焉'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（主線：同調三段時終焉 +1%／點）'),  # 0,2 v0.4 負責：DLL N3（融斷 N5）
    ('common', '定神'): ('DONE', 'ESSBNodes.SelfSlowImmune',
        '同調三段時免疫本模組的減速（自有）'),  # 0,2,0 v0.4 負責：引擎效果
    ('common', '同調三段時重擊附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kCommonStage3Power）＋ESSBNodes.CommonHitMult 鏡像',
        '同調三段時重擊附傷 +2%／點'),  # 0,3 v0.4 負責：DLL N2
    ('common', '極致'): ('KEPT-N4', 'ESSBController.OnWeaponHit（ExtremeCount）',
        '極致：同調三段每 10 次命中多一次全額附傷'),  # 0,3,0 v0.4 負責：DLL N4
    ('common', '回饋'): ('KEPT-N4', 'ESSBNodes.OnSyncStage',
        '回饋：升段回復生命與魔力各 B_max ×2（審查修正：數值照 v0.4，不乘 G(L)）'),  # 0,3,1 v0.4 負責：DLL N4
    ('common', '化身'): ('LATER-N4', '—（只有 perk 記錄；本輪不讀）',
        'N4 上線時照 v0.4 實作（化身：同調三段時冷卻 30 秒（-1 秒／點）完成後的下一次命中觸發當前元素的持續傳奇效果；被動數值類改為 10 秒視同取得）。審查修正：v0.3 的「每 N 秒自動施放」把絕對零度／深淵／長河等被動數值變成主動效果，跟 v0.4 不符，已拿掉'),  # 0,4 v0.4 負責：DLL N4
    ('common', '永續'): ('KEPT-N4', 'ESSBNodes.HasPerpetual → ESSBController.OnFormClosed',
        '永續：三段時融斷後保留一段同調'),  # 0,4,0 v0.4 負責：Papyrus＋DLL N4
    ('common', '所有元素附傷'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kCommonAll1）＋ESSBNodes.CommonHitMult 鏡像',
        '所有元素附傷 +1%／點'),  # 1,0 v0.4 負責：DLL N2
    ('common', '跳印'): ('LATER-N3', '—（只有 perk 記錄；本輪不讀）',
        'N3 上線時照 v0.4 實作（跳印：印記自然過期時，過期終焉照常結算，然後印記跳到 6 公尺內最近一個沒有印記的敵人身上（剩 4 秒、不觸發開印），每個印記只跳一次）'),  # 1,0,1 v0.4 負責：DLL N3（掃描 N5）
    ('common', '印記持續'): ('PARTIAL-N3', 'ESSBNodes.MarkDurationBonus → ESSBController.ApplyMark',
        '印記持續 +0.2 秒／點。差距：v0.4 是 +0.2 秒／點的連續值；本模組的印記時長是整數秒（SetNthEffectDuration 只收整數），總時長四捨五入到整秒，要等印記改成 DLL 施放的效果（N3）才能精確'),  # 1,1 v0.4 負責：DLL N3
    ('common', '順轉'): ('DONE', 'ESSBController.SwitchForm／ESSBInput.RefreshPermission + PERK ESSB_P_common_1_1_B1 進入點 0x24（ESSB_GuardSwitch）',
        '開形態免魔力門檻；切換後 1 秒受傷 -50%（審查修正：視窗由 2 秒改回 v0.4 的 1 秒）'),  # 1,1,0 v0.4 負責：Papyrus＋引擎效果
    ('common', '先制'): ('KEPT-N4', 'ESSBNodes.OpenSyncBonus → ESSBController.AfterOpen',
        '先制：開印 +2 同調'),  # 1,1,1 v0.4 負責：DLL N4
    ('common', '開印時'): ('KEPT-N4', 'ESSBNodes.OpenSyncBonus',
        '開印 +1 同調／每 5 點'),  # 1,2 v0.4 負責：DLL N4
    ('common', '雙印'): ('KEPT-N3', 'ESSBController.OnValidHit（RegElem2 副印記）',
        '雙印：新元素進副格、較舊的留主格，不觸發終焉；融斷時兩格各結算一次'),  # 1,2,0 v0.4 負責：DLL N3
    ('common', '所有元素附傷再'): ('DONE', 'DLL native/include/HitMath.h NodeSum（node::kCommonAll2）＋ESSBNodes.CommonHitMult 鏡像',
        '所有元素附傷再 +1%／點'),  # 1,3 v0.4 負責：DLL N2
    ('common', '印潮'): ('LATER-N5', '—（只有 perk 記錄；本輪不讀）',
        'N5 上線時照 v0.4 實作（印潮：切換後那一擊的開印，同時讓 15 公尺內帶著同一個舊印記的其他目標各觸發一次新元素的開印（最多 2 人；與大協奏對稱：大協奏傳終焉，印潮傳開印））'),  # 1,3,2 v0.4 負責：DLL N5
    ('common', '臨界'): ('KEPT-N5', 'ESSBNodes.OnFormOpened',
        '臨界：開形態時附近敵人減速 30% 2 秒'),  # 1,3,1 v0.4 負責：Papyrus＋DLL N5
    ('common', '每種元素狀態上限'): ('KEPT-N3', 'ESSBNodes.StatusCapBonus → ESSBController.StackCap',
        '每種元素狀態上限 +1／每 5 點，最多 +3；量表類不吃'),  # 1,4 v0.4 負責：DLL N3／N4
    ('common', '萬象'): ('KEPT-N3', 'ESSBNodes.OmniMult',
        '萬象：層數效果 +25%（熱度附傷、爆燃每層、流血與毒層 DoT）'),  # 1,4,0 v0.4 負責：DLL N3／N4
    ('common', '終焉'): ('KEPT-N3', 'ESSBNodes.CommonEndMult',
        '終焉 +1%／點'),  # 2,0 v0.4 負責：DLL N3（融斷 N5）
    ('common', '餘響'): ('DONE', 'DLL native/include/HitMath.h EchoRatio（node::kCommonEcho）＋ESSBNodes.EchoRatio（切換時掛待發標記）',
        '切換後首次命中附帶前一元素 50% 附傷'),  # 2,0,0 v0.4 負責：DLL N2
    ('common', '融斷'): ('KEPT-N5', 'ESSBNodes.CommonBurstMult',
        '融斷 +1%／點'),  # 2,1 v0.4 負責：DLL N5
    ('common', '反哺'): ('KEPT-N3', 'ESSBNodes.OnEndReward',
        '反哺：每次終焉回魔 B_max（審查修正：數值照 v0.4，不乘 G(L)）'),  # 2,1,0 v0.4 負責：DLL N3（融斷 N5）
    ('common', '疊印'): ('KEPT-N3', 'ESSBController.EndMark（RegElem2 + RegSecondUntil）',
        '疊印：終焉後舊印記留 4 秒副印記，融斷再結算一次'),  # 2,1,1 v0.4 負責：DLL N3
    ('common', '切換後首次命中附帶前一元素附傷'): ('DONE', 'DLL native/include/HitMath.h EchoRatio（node::kCommonEchoRatio）',
        '切換後首次命中附帶前一元素附傷 +3%／點'),  # 2,2 v0.4 負責：DLL N2
    ('common', '連鎖終焉'): ('KEPT-N5', 'ESSBNodes.HasChainEnd → ESSBReactions.ChainEnd',
        '連鎖終焉：附近同印記目標也終焉 ×0.5，abChain 防遞迴'),  # 2,2,0 v0.4 負責：DLL N5
    ('common', '三重奏'): ('KEPT-N3', 'ESSBNodes.TrioMult → ESSBController.PushTrio',
        '三重奏：10 秒內三種元素終焉，第三次 ×3 並保留全部同調'),  # 2,2,1 v0.4 負責：DLL N3／N5
    ('common', '終焉再'): ('KEPT-N3', 'ESSBNodes.CommonEndMult',
        '終焉再 +1%／點'),  # 2,3 v0.4 負責：DLL N3（融斷 N5）
    ('common', '協奏'): ('KEPT-N3', 'ESSBNodes.ConcertMult → ESSBController.TakeSwitchEnd',
        '協奏：切換後首次終焉 ×1.5'),  # 2,3,0 v0.4 負責：DLL N3
    ('common', '安全閥'): ('KEPT-N5', 'PERK ESSB_P_common_2_3_B2 進入點 0x24',
        '安全閥：融斷時受傷 -50% 2 秒（讀 ESSB_GuardBurst）'),  # 2,3,1 v0.4 負責：引擎效果（N5 掛上）
    ('common', '融斷再'): ('KEPT-N5', 'ESSBNodes.CommonBurstMult',
        '融斷再 +2%／點'),  # 2,4 v0.4 負責：DLL N5
    ('common', '大協奏'): ('KEPT-N5', 'ESSBNodes.HasGrandConcert → ESSBReactions.ChainEnd',
        '大協奏：切換後首次終焉讓範圍內同印記各終焉一次'),  # 2,4,0 v0.4 負責：DLL N5
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
    ('1.1', '開形態需要魔力高於上限 10%；切換不檢查', IMPL,
     'ESSBController.ToggleForm', '順轉與免門檻兩個節點可以豁免'),
    ('1.1', '血位：三條曲線線性內插（命中倍率、吸血、損血）', IMPL,
     'ESSBController.GetBloodHitMult / GetBloodLeechRatio / ESSBFormRules', '損血在 ESSBFormRules 每秒扣，命中倍率乘在 GetDamageMult'),
    ('1.1', '風形態潛行：潛行攻擊時風附傷 ×3', IMPL,
     'ESSBController.ApplyProc', '讀 HitData 的潛行旗標（2048）；移速與 Muffle 的自有能力屬風樹，round 2'),
    ('1.1', '火形態過熱：同調三段後每命中 +1，滿了自爆或熔身', IMPL,
     'ESSBController.HitStacks / AddSelf(4)', '上限由 ESSBElem.OverheatCap（熔爐 20），熔身分支改為 10 秒增益'),
    ('2.1', '每擊隨機 B：各元素自己的常態範圍，重擊 ×1.5', IMPL,
     'ESSBReactions.RollBase / ESSBController.ApplyProc', '規劃 2.1 的 11 組上下限；施放前 SetNthEffectMagnitude，取代原本寫死的 8/12'),
    ('2.1', '雷的附傷另削減目標魔力 50%', IMPL,
     'ESSBElem.Discharge（放電）', '規劃 2.6 的感電與放電都削魔；電蝕分支改為 100%'),
    ('2.3', '狀態上限的三種來源：基礎、分支、通用樹「萬象」欄', IMPL,
     'ESSBController.StackCap + ESSBNodes.StatusCapBonus', '量表類（凍結）固定 5，不吃通用樹加成'),
    ('2.7', 'G(L) = 1 + 0.05 × L', IMPL,
     'ESSBTrees.TreeG → ESSBController.ApplyDamage / ApplyProc / ApplyTrueDamage', '反應、DoT、附傷、真傷四條路徑都在同一處乘，不重複'),
    ('2.7', 'M_mod 只乘一次，不出現疊乘', IMPL,
     'DLL native/include/HitMath.h NodeSum（附傷）/ ESSBReactions.End（終焉）', '附傷 = 共通 × 通用樹 × 元素樹；終焉 = 共通 × 通用樹關閉 × 元素樹關閉（round 20 起附傷由 DLL 算，ESSBController.GetHitMult 已刪）'),
    ('2.8', '真實傷害類別：不吃護甲、抗性、外部加成', IMPL,
     'MGEF ESSB_TrueEffect（skill = -1、resist = None）+ ESSBController.ApplyTrueDamage', '只掛 ESSB_TrueDamage keyword，沒有外部天賦認得；造成真傷練無元素樹'),
    ('2.9', '融斷後留下的領域（火域、冰原）', IMPL,
     'ESSBController.StartDomain / InDomain / TickDomain', '不放 ObjectReference、不用 hazard 或爆炸：只記中心座標與剩餘秒數，判定在既有的每秒 tick 與命中路徑上做'),
    ('2.9', '各元素的「臨」：以玩家為中心 2 公尺 + 0.2 公尺／點', IMPL,
     'ESSBElem.OnFormOpened → ESSBController.ForceOpenOn', '火冰雷已落地，其餘元素同一個函式'),
    ('2.13', '附傷、反應、真傷的學派歸屬與 DoCombatSpellApply', IMPL,
     'build_v03（SCHOOLS/casting_perks）+ ESSBController', '真傷刻意不掛學派；其餘沿用引擎前線的配置'),
    ('6.1', '每個節點效果處理函式都留紀錄', IMPL,
     'ESSBController.LogThrottled / ESSBLog.Log', '等級 1 事件（開印、終焉、融斷、化身、處決、沉默、反咒、領域）、等級 2 節點、等級 3 公式細項'),
    ('8', '碎冰處決以自有高強度傷害法術執行，不用 Kill()', IMPL,
     'ESSBController.Execute', '擊殺歸屬與死亡事件與一般擊殺一致；首領與必要角色由呼叫端改走 ×5 傷害'),
    ('8', '過熱／熱度／電荷等自身資源鏡射成全域變數', IMPL,
     'ESSBController.PushSelf / PushSyncStage / SetGlobal', 'PERK 進入點的 CTDA 只讀得到全域變數，這是樣式 C 的橋'),
    # ---- 機制前線 round 2
    ('1.1', '血形態維持費：依血位曲線每秒扣最大生命（1.0%／0.6%／0.2%／0）', IMPL,
     'ESSBController.BloodDrainPerSecond / PayBloodCost → ESSBFormRules.OnUpdate',
     'round 1 是固定 0.5%，本輪換成 1.1 的四點曲線；血氣減半、血臨強化／血約／不死歸零；永遠留 1 點生命'),
    ('1.1', '血形態重擊不消耗耐力，改扣生命（8%／5%／2%／0）', IMPL,
     'PERK ESSB_P_BaseRules 進入點 0x1B ×0 + ESSBController.PayBloodCost（OnWeaponHit）',
     '耐力那一半用進入點（條件 ESSB_FormActive == 1 且 ESSB_CurrentElement == 6），生命那一半在命中時扣'),
    ('1.1', '風形態：移速 +10%、潛行腳步聲減半、潛行攻擊風附傷 ×3 且風勢直接滿', IMPL,
     'ESSBController.RefreshWindAbilities / RefreshWindStealth / ElementHitHook',
     'SPEL ESSB_Ability_WindSpeed（AV 30）與 ESSB_Ability_Muffle（AV 92）；潛行狀態在既有的每秒 tick 讀一次'),
    ('2.3', '土 岩甲：護甲加成、被打 -1、離開形態清空', IMPL,
     'ESSBController.SyncRockArmor / ConsumeRockArmor ← ESSBGuard.OnHitEx',
     '護甲用自有的 ESSB_Util_ArmorBuff（AV 39、原型 34），層數變動時重下、歸零時 DispelSpell'),
    ('2.3', '風 風勢：到門檻送出風刃後歸零', IMPL,
     'ESSBElem2.CheckWindGauge ← ESSBController.ElementHitHook', '門檻 4（亂舞 3），送出後 ClearSelf(3)'),
    ('2.3', '風 失衡：受風刃傷害 +30%', IMPL,
     'ESSBElem2.WindBladeOne', '在風刃的傷害計算裡讀 GetStack(target, 4)，不需要 PERK 進入點'),
    ('2.6', '土 地震的「耐力歸零跌倒」', IMPL,
     'ESSBElem2.QuakeOne → ESSBController.Knockdown', 'PushActorAway 力道 3.0，每目標 8 秒一次；免疫者改為減速 30% 3 秒'),
    ('2.6', '風 開印的「拉近 1.5–3 公尺」與終焉的「吹飛 3–6 公尺」', IMPL,
     'ESSBController.PullIn / PullTo / BlowBack（ApplyHavokImpulse）',
     '拉近每目標 3 秒一次、吹飛每目標 8 秒一次；免疫名單＝龍、騎乘中、必要角色與首領、巨人與猛獁'),
    ('2.5', '風印記融斷的「吹上天」與落地傷害', IMPL,
     'ESSBController.LiftUp → ESSBStatus 浮空 → ESSBController.OnLanding',
     '浮空是自有的 2 秒狀態（規劃 8：不讀物理狀態），落地傷害在狀態到期的那一秒結算'),
    ('2.6', '聖 開印「目標受聖傷 +20%」', IMPL,
     'ESSBElem2.HolyVulnerability', '附傷與裁決共用同一個函式；沒有用 PERK 進入點，因為武器傷害的條件分頁讀不到目標'),
    ('2.7', '血承：擊殺時吸收死者屬性 15 秒', IMPL,
     'ESSBController.ApplyInherit（SPEL ESSB_InheritSpell 的 7 個 Peak Value Modifier）',
     '火冰電毒魔抗各 50%、護甲 20%、最大生命 10%；施放前逐一 SetNthEffectMagnitude，重掛即取代'),
    ('2.10', '白天 → 化灰必定觸發', IMPL,
     'ESSBElem2.ShouldAsh → ESSBController.ApplyAsh', '化灰 MGEF 的 DATA 照抄原版 PerkDisintegrateFFAimed；龍與必要角色不化灰'),
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
    ('2.9', '玩家受擊事件（PO3 OnHitEx）與擊殺事件（OnActorKilled）', IMPL,
     'ESSBGuard', '第三個 Player 別名腳本；每攻擊者 3 秒冷卻的 4 格環；擊殺仍保留控制器每秒 tick 的後援路徑'),
    # ---- 機制前線 round 3
    ('2.3', '毒 毒層：無上限、每層獨立 6 秒、≥門檻自動擴散', IMPL,
     'ESSBStatus.Tick（六格環狀桶）+ ESSBElem3.SpreadInterval / SpreadThreshold / SpreadTargets '
     '+ ESSBController.SpreadPoison',
     '命中不刷新舊層；催毒只加速不清除；擴散每次只找一個對象，不做全場掃描'),
    ('2.3', '水 水壓：命中浸濕目標 +1，每層水附傷 +10%', IMPL,
     'ESSBElem3.OnWaterHit / WaterHitMult / PressureCap → ESSBController.StackCap(9)',
     '結清引擎前線預留的狀態 kind 9；8 秒、命中刷新，上限 5（萬象 8）'),
    ('2.3', '暗 詛咒：上限 5，深淵在同調三段 +1／每 3 點（最多 10）', IMPL,
     'ESSBElem3.CurseCap → ESSBController.StackCap(10)', '侵蝕用原型 34 的抗性負向修正，會自己還原'),
    ('2.3', '星 星痕：每層 2 秒後自行引爆，上限 3 +1／每 5 點', IMPL,
     'ESSBStatus.Tick（兩格環狀桶）+ ESSBElem3.AstralDelay / AstralCap',
     '延遲只有 2 秒與 1 秒兩檔（狀態容器是整數秒 tick）'),
    ('2.6', '暗 死咒期間目標無法被治療', IMPL,
     'ESSBReactions.EndDark → ESSBController.ApplyUtil(20, 100%)',
     '引擎沒有「受到的治療」修正，以 HealRateMult -100% 表達（同血咒的偏離）；不治分支延長到 6 秒'),
    ('2.9', '瘴氣複製：中心為目標、6 公尺、5 人', IMPL,
     'ESSBElem3.EndPoisonNodes', '結清 engine-coverage 例外表的最後一條毒素項'),
    ('2.9', '星界的所有範圍：基礎相同，主線每點 +1 公尺', REMOVED,
     '—（round 21 刪除 ESSBElem3.Range / FallRadius / ConstellationRadius / ScatterRadius）',
     'v0.4 已拿掉這條 v0.3 規則：星臨半徑與其他元素相同（ESSBElem.AdventRadiusOf／ESSBElem3.AdventRadius，2 公尺 +0.2 公尺／點），星散 15 公尺、星域 3 公尺'),
    ('2.9', '領域格從 1 格擴充為固定 3 格', IMPL,
     'ESSBController.StartDomain / InDomain / DomainActive / TickDomain / DomainFlag',
     '不同元素的領域在正常玩法下會同時存在（融斷留下領域 → 切換 → 再融斷）；'
     '同元素取代自己那一格，全滿時換掉剩餘秒數最少的；每秒仍然只掃一次 5 人；每格有自己的半徑'),
    ('2.10', '夜晚 → 星界所有範圍 ×1.5', REMOVED,
     '—（round 21 刪除 ESSBElem3.Range）', 'v0.4 已拿掉這條 v0.3 規則；夜晚黑暗附傷 +20% 仍由 DLL 讀環境旗標'),
    ('8', '長流：自有的每秒百分比回復，不動回復速率 AV', IMPL,
     'ESSBElem3.WaterFormTick ← ESSBController.Tick',
     '掛在既有的每秒 tick，不另開計時器；不受原版戰鬥中回復減半影響'),
    ('8', '洗淨／淨化：不洗掉自己的增益', IMPL,
     'ESSBController.ApplyCleanse + DispelHostileEffects；SPEL ESSB_CleanseSpell / '
     'ESSB_PurgeSpell 只掛 Cure Disease（原型 3）與 Cure Poison（原型 29）',
     '特效前線改成「安全建構」：不依賴原型 2 與旗標 0x100（兩者都是推論值）。'
     '(1) 逐個 DispelSpell 本模組自己的有時限減益（SelfCleanseSpells，11 個）；'
     '(2) 治病與解毒走實測原型；(3) 淨化另用 PO3 GetActiveEffects 挑敵對／有害旗標的效果，'
     'GetMagicEffectSource 回推來源法術後 DispelSpell。最壞情況是少清幾個外來減益，'
     '不可能洗掉形態能力、血承、岩甲。MGEF ESSB_CleanseEffect / ESSB_PurgeEffect 仍在 ESP 裡待命'),
    ('8', '沖刷：對目標的 Dispel 原型，只影響有時限的法術效果', IMPL,
     'MGEF ESSB_StripEffect + ESSBController.ApplyStrip',
     '每目標 10 秒一次（沿用推力環狀表的 kind 2）；不影響能力型常駐效果；'
     'TARGET 路徑才留無限定 Dispel，ApplyStrip 硬性擋掉「目標＝玩家」與非法目標'),
    ('8', '亡者歸來：自有 Reanimate 原型的六階表，尊重召喚上限', LATER_N5,
     '—（ESSBElem3.Reanimate 已刪；ESSBController.SummonCap / ServantCount / CanReanimate / ApplyReanimate 與 MGEF ESSB_ReanimateEffect 保留給 N5）',
     '提前移除（指揮官裁定 C3）：v0.3 的擊殺復生本輪已刪，於 N5 以 v0.4 版本（死亡處理：帶黑暗印記且詛咒 ≥3 層死亡即亡者歸來）重做'),
    ('6', '恐懼與瘋狂：自有效果、等級上限、尊重免疫', IMPL,
     'MGEF ESSB_FearEffect（原型 7）／ESSB_FrenzyEffect（原型 8）'
     '+ ESSBController.ApplyFear / ApplyFrenzy / CanCharm',
     'magnitude 就是可影響的最高等級（10 + 暗樹等級），做法同原版幻術；'
     '首領與必要角色、龍、亡靈魔族免疫；只在黑暗樹出現'),
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

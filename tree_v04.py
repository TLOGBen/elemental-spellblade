"""v0.4 技能樹的格位資料（round 21）。plan_trees.assign_slots 讀這一份。

格位 slot ＝ 分支 perk 的 FormID 格：0x002000 + ((樹 × 3 + 路線) × 5 + 階) × 4 + slot，EditorID 尾碼 B{slot+1}。
規則（指揮官裁定 R7：只往後加、退役不重用）：
  * v0.4 與 v0.3 同一階同名的分支 → 沿用 v0.3 的格（不用列在這裡）。
  * RENAMES：v0.4 改了名字、設計上是同一個節點 → 沿用 v0.3 那一格。
  * NEW_SLOTS：v0.3 沒有的新節點 → 指定一個 v0.3 在該階從沒用過的格（build/tree-v04-inventory.md 附錄 A）。
  * 其餘 v0.3 分支 → 退役 perk（記錄照舊產生：同 EditorID／FormID，不可購買、不進 CSF、沒有進入點）。
plan_trees 會拒絕：新節點放在 v0.3 用過的格、同一格兩個節點、改名來源不存在。
"""

# (樹, 路線, 階) → {v0.4 名稱: v0.3 名稱}
RENAMES = {
    ('blood', 0, 1): {'血溢': '血盾'},
    ('noform', 1, 0): {'奪魔': '蝕魔'},
    ('noform', 1, 4): {'噬命': '逆流'},
    ('poison', 0, 1): {'萎靡': '衰弱'},
    ('poison', 2, 1): {'疫染': '瘴氣'},
    ('water', 1, 1): {'湧泉': '回流'},
    ('water', 1, 3): {'開印沖刷': '沖刷'},
}

# (樹, 路線, 階, v0.4 名稱) → 格（附錄 A「不重用已移除格」方案，47 個）
NEW_SLOTS = {
    ('fire', 2, 0, '餘壓'): 2,
    ('frost', 0, 3, '冰鎧'): 2,
    ('frost', 0, 3, '凍傷'): 3,
    ('frost', 1, 3, '霜爆'): 2,
    ('lightning', 0, 3, '逆電'): 2,
    ('lightning', 1, 3, '雷鳴'): 3,
    ('earth', 2, 2, '蓄能'): 1,
    ('blood', 0, 0, '血刃'): 2,
    ('divine', 0, 3, '破邪斬'): 2,
    ('divine', 1, 1, '誓約'): 2,
    ('divine', 2, 3, '天誅'): 2,
    ('water', 0, 1, '水盾'): 2,
    ('water', 0, 3, '潮身'): 2,
    ('water', 0, 4, '止水'): 1,
    ('water', 1, 3, '淨潮'): 2,
    ('water', 2, 1, '退潮'): 2,
    ('darkness', 0, 0, '咒延'): 1,
    ('darkness', 0, 1, '懼咒'): 2,
    ('darkness', 0, 1, '怨縛'): 3,
    ('darkness', 0, 2, '狂咒'): 1,
    ('darkness', 0, 3, '狂宴'): 2,
    ('darkness', 0, 3, '回魘'): 3,
    ('darkness', 0, 4, '亡衛'): 1,
    ('darkness', 1, 1, '狂刃'): 2,
    ('darkness', 2, 0, '殘魂'): 2,
    ('darkness', 2, 1, '冥印'): 2,
    ('darkness', 2, 2, '噬咒'): 2,
    ('darkness', 2, 3, '冥召'): 2,
    ('astral', 0, 0, '星鏈'): 1,
    ('astral', 0, 1, '聚星'): 2,
    ('astral', 0, 3, '餘輝'): 2,
    ('astral', 0, 4, '星蝕'): 1,
    ('astral', 0, 4, '天穹'): 2,
    ('astral', 1, 3, '星門'): 2,
    ('astral', 2, 2, '星殘'): 1,
    ('astral', 2, 3, '墜星'): 2,
    ('noform', 0, 0, '逼近'): 1,
    ('noform', 0, 1, '蓄流'): 2,
    ('noform', 0, 2, '化勁'): 1,
    ('noform', 0, 3, '餘魔'): 2,
    ('noform', 0, 4, '破式'): 1,
    ('noform', 0, 4, '無魔'): 2,
    ('noform', 1, 3, '咒返'): 2,
    ('noform', 2, 1, '寂滅'): 2,
    ('noform', 2, 4, '萬寂'): 1,
    ('common', 1, 0, '跳印'): 1,
    ('common', 1, 3, '印潮'): 2,
}

# round 21 新增的 47 個分支 perk EditorID（審過的明列清單；build_v03.new_perk_edids 會跟身分表推出來的集合比對）。
# 驗證器（validate_fix3／fix4／mcm、state_schema、fix6）的「新記錄白名單」只收這一份。
NEW_PERK_EDIDS = (
    'ESSB_P_fire_2_0_B3',  # 餘壓
    'ESSB_P_frost_0_3_B3',  # 冰鎧
    'ESSB_P_frost_0_3_B4',  # 凍傷
    'ESSB_P_frost_1_3_B3',  # 霜爆
    'ESSB_P_lightning_0_3_B3',  # 逆電
    'ESSB_P_lightning_1_3_B4',  # 雷鳴
    'ESSB_P_earth_2_2_B2',  # 蓄能
    'ESSB_P_blood_0_0_B3',  # 血刃
    'ESSB_P_divine_0_3_B3',  # 破邪斬
    'ESSB_P_divine_1_1_B3',  # 誓約
    'ESSB_P_divine_2_3_B3',  # 天誅
    'ESSB_P_water_0_1_B3',  # 水盾
    'ESSB_P_water_0_3_B3',  # 潮身
    'ESSB_P_water_0_4_B2',  # 止水
    'ESSB_P_water_1_3_B3',  # 淨潮
    'ESSB_P_water_2_1_B3',  # 退潮
    'ESSB_P_darkness_0_0_B2',  # 咒延
    'ESSB_P_darkness_0_1_B3',  # 懼咒
    'ESSB_P_darkness_0_1_B4',  # 怨縛
    'ESSB_P_darkness_0_2_B2',  # 狂咒
    'ESSB_P_darkness_0_3_B3',  # 狂宴
    'ESSB_P_darkness_0_3_B4',  # 回魘
    'ESSB_P_darkness_0_4_B2',  # 亡衛
    'ESSB_P_darkness_1_1_B3',  # 狂刃
    'ESSB_P_darkness_2_0_B3',  # 殘魂
    'ESSB_P_darkness_2_1_B3',  # 冥印
    'ESSB_P_darkness_2_2_B3',  # 噬咒
    'ESSB_P_darkness_2_3_B3',  # 冥召
    'ESSB_P_astral_0_0_B2',  # 星鏈
    'ESSB_P_astral_0_1_B3',  # 聚星
    'ESSB_P_astral_0_3_B3',  # 餘輝
    'ESSB_P_astral_0_4_B2',  # 星蝕
    'ESSB_P_astral_0_4_B3',  # 天穹
    'ESSB_P_astral_1_3_B3',  # 星門
    'ESSB_P_astral_2_2_B2',  # 星殘
    'ESSB_P_astral_2_3_B3',  # 墜星
    'ESSB_P_noform_0_0_B2',  # 逼近
    'ESSB_P_noform_0_1_B3',  # 蓄流
    'ESSB_P_noform_0_2_B2',  # 化勁
    'ESSB_P_noform_0_3_B3',  # 餘魔
    'ESSB_P_noform_0_4_B2',  # 破式
    'ESSB_P_noform_0_4_B3',  # 無魔
    'ESSB_P_noform_1_3_B3',  # 咒返
    'ESSB_P_noform_2_1_B3',  # 寂滅
    'ESSB_P_noform_2_4_B2',  # 萬寂
    'ESSB_P_common_1_0_B2',  # 跳印
    'ESSB_P_common_1_3_B3',  # 印潮
)

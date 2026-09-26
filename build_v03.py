"""元素魔戰士 v0.3 核心包建置。

產出 package/Elements Spellblade/Elements Spellblade.esp：
  - masters 只有 Skyrim.esm，不掛 Phenderix Elements。
  - 一般 ESP（不設 ESL 旗標），之後的前線會超過 2048 筆記錄。
  - 本地 FormID 由下方 ALLOCATION 表固定配置，後續前線只在保留段內擴充，不重新編號。

build_core.py 保留不動（歷史）。本檔是新的進入點，不使用 build_scripts.py。
"""
from __future__ import annotations

import collections
import hashlib
import json
import math
import re
import struct
import subprocess
import sys

# Keep generated files within build/ and package/; avoid imported-module caches.
sys.dont_write_bytecode = True

import fx_extract
import plan_coverage
import plan_trees
from tes import ROOT, WORK, dump, read_plugin, sub

PLUGIN = 'Elements Spellblade.esp'
OUT = WORK / 'package/Elements Spellblade'
MASTERS = ['Skyrim.esm']

# Single source of truth; Papyrus literal allocations are generated from these.
POISON_LAYER_SECONDS = 12
BLEED_LAYER_SECONDS = 10
STATE_INTS = 16 + BLEED_LAYER_SECONDS + POISON_LAYER_SECONDS
BACKUP_SLOTS = 2

ELEMENTS = ['Fire', 'Frost', 'Lightning', 'Earth', 'Wind', 'Blood', 'Divine', 'Poison', 'Water', 'Darkness', 'Astral']
ZH = ['火焰', '冰霜', '雷電', '大地', '風', '鮮血', '神聖', '毒素', '水', '黑暗', '星界']
# 規劃 2.13：傷害效果的學派歸屬（土風水的傷害掛毀滅，增益與控制之後才掛變化）。
SCHOOLS = [20, 20, 20, 20, 20, 22, 22, 22, 20, 19, 20]
# 抗性 AV：41 火、43 冰、42 電、40 毒，其餘 44（魔法）。
RESISTS = [41, 43, 42, 44, 44, 44, 44, 40, 44, 44, 44]
# 原版元素關鍵字，只有火冰雷有；星界刻意不掛。
VANILLA_ELEMENT_KEYWORD = {0: 0x1CEAD, 1: 0x1CEAE, 2: 0x1CEAF}

# Round 22 (N3): ESSBStatus (status container) and ESSBMark (mark AME) are gone -- the status layer is DLL-applied
# engine effects; ESSBStub is the empty script on the effects whose expiry the DLL settles (build/fix22_records.py).
SCRIPTS = ['ESSBLog', 'ESSBStub', 'ESSBReactions', 'ESSBTrees', 'ESSBNodes',
           'ESSBNoForm', 'ESSBElem', 'ESSBElem2', 'ESSBElem3', 'ESSBCounter', 'ESSBSilence',
           'ESSBController', 'ESSBGuard', 'ESSBFormPowerEffect', 'ESSBFormRules',
           'ESSBSettingsEffect', 'ESSBState', 'ESSBMCM', 'ESSBInput', 'ESSBNative']

# ---------------------------------------------------------------- 技能樹前線（機制）
# 樹的正式順序（與 plan_trees.TREE_ORDER 相同）：0–10 是 ELEMENTS，11 無元素，12 全元素通用。
TREES = plan_trees.TREE_ORDER
TREE_ZH = ZH + ['無元素', '全元素通用']
# CSF 技能條的顏色（RGB int）。
TREE_COLOR = [0xFF6A3D, 0x7FD8FF, 0xFFE45C, 0xB98A55, 0xAFFFD8, 0xC01F2E, 0xFFF3C4,
              0x8FD14F, 0x4FA8E0, 0x8A5CC7, 0xC9A0FF, 0xCFCFCF, 0xE8E8E8]
CSF_DIR = 'SKSE/Plugins/CustomSkills'
CSF_SKILL_PREFIX = 'ESSB_'

# ------------------------------------------------------------------ FormID 配置表
# 每一段都留下空間，讓引擎／機制／特效前線可以往後接而不動已發佈的 ID。
ALLOCATION = [
    ('0x000800-0x00080F', 'QUST 與任務層', '已用 0x000800'),
    ('0x000810-0x00082F', 'GLOB 全域變數', '已用 0x000810-0x000815'),
    ('0x000830-0x00083F', 'KYWD 通用關鍵字', '已用 0x000830-0x000831'),
    ('0x000840-0x00084F', 'KYWD 元素關鍵字 ×11', '已用 0x000840-0x00084A'),
    ('0x000850-0x00085F', 'KYWD 印記關鍵字 ×11', '已用 0x000850-0x00085A'),
    ('0x000860-0x00088F', 'KYWD 保留（狀態、反應、真傷細分）', '保留'),
    ('0x000890-0x0008FF', 'MESG／設定層', '已用 0x000890-0x000892'),
    ('0x000900-0x00091F', 'MGEF 形態力量效果 ×11', '已用 0x000900-0x00090A'),
    ('0x000920-0x00093F', 'SPEL 形態力量 ×11', '已用 0x000920-0x00092A'),
    ('0x000940-0x00095F', 'MGEF 形態能力效果 ×11', '已用 0x000940-0x00094A'),
    ('0x000960-0x00097F', 'SPEL 形態能力 ×11', '已用 0x000960-0x00096A'),
    ('0x000980-0x0009FF', '形態規則與保留', '已用 0x000980-0x000981'),
    ('0x000A00-0x000AFF', 'MGEF 附傷效果 ×11', '已用 0x000A00-0x000A0A'),
    ('0x000B00-0x000BFF', 'SPEL 附傷法術 ×22（元素×普通/重擊）', '已用 0x000B00-0x000B15'),
    ('0x001000-0x00101F', 'MGEF 印記效果 ×11（Script 原型，8 秒／浸濕 10 秒）', '已用 0x001000-0x00100A'),
    ('0x001020-0x00103F', 'SPEL 印記法術 ×11', '已用 0x001020-0x00102A'),
    ('0x001040-0x00105F', 'MGEF 反應傷害 ×11（掛 ESSB_React，不掛 ESSB_Proc）', '已用 0x001040-0x00104A'),
    ('0x001060-0x00107F', 'SPEL 反應傷害 ×11（執行期 SetNthEffectMagnitude）', '已用 0x001060-0x00106A'),
    ('0x001080-0x00108F', 'MGEF／SPEL 狀態容器與已交戰標記', '已用 0x001080-0x001083'),
    ('0x001090-0x00109F', 'MGEF 輔助效果 ×8（減速、減防、削魔、削耐、回血、回魔、回耐、放血）',
     '已用 0x001090-0x001097'),
    ('0x0010A0-0x0010AF', 'SPEL 輔助法術 ×8', '已用 0x0010A0-0x0010A7'),
    ('0x0010B0-0x001EFF', '保留：引擎前線後續（雙印、領域、真傷細分）', '保留'),
    ('0x001F00-0x001F0F', 'KYWD 引擎前線自有關鍵字', '已用 0x001F00-0x001F02'),
    ('0x001F10-0x001F2F', 'GLOB 引擎前線自有全域變數（同調門檻、環境）', '已用 0x001F10-0x001F15'),
    ('0x002000-0x0023FF', 'PERK 分支節點（195 階 × 4 格預留，實際 300 個）', '已用 0x002000-0x002309'),
    ('0x002400-0x00241F', 'GLOB ESSB_Lvl_<tree> ×13（CSF 等級）', '已用 0x002400-0x00240C'),
    ('0x002420-0x00243F', 'GLOB ESSB_Ratio_<tree> ×13（CSF 進度比）', '已用 0x002420-0x00242C'),
    ('0x002440-0x00245F', 'GLOB ESSB_Pts_<tree> ×13（CSF perkPoints）', '已用 0x002440-0x00244C'),
    ('0x002460-0x00247F', 'GLOB ESSB_Color_<tree> ×13（RGB int）', '已用 0x002460-0x00246C'),
    ('0x002480-0x00249F', 'GLOB ESSB_ShowLvl_<tree> ×13（升級訊息旗標）', '已用 0x002480-0x00248C'),
    ('0x0024A0-0x0024BF', 'GLOB ESSB_Respec_<tree> ×13（洗點冷卻時戳，遊戲日）', '已用 0x0024A0-0x0024AC'),
    ('0x0024C0-0x0024CF', 'GLOB ESSB_ShowMenu／ESSB_XPPerHit', '已用 0x0024C0-0x0024C1'),
    ('0x0024D0-0x002FFF', '保留：技能樹前線後續（節點進入點、額外全域變數）', '保留'),
    ('0x003000-0x003FFF', '借用的特效素材（EFSH／IPDS／IPCT／EXPL／ARTO／SNDR／SOUN／LIGH／HAZD／'
                          'DEBR／TXST），由 fx_extract.export 複製進來、EDID 前綴 ESSBFX_',
     '已用 0x003000 起連號（見 build/fx-bindings.json 的 records）'),
    ('0x004000-0x004FFF', 'PERK 主線階級鏈（195 節點 × 15 階 = 2925）', '已用 0x004000-0x004B6C'),
    ('0x005000-0x00501F', 'GLOB 機制狀態鏡射（PERK 進入點的 CTDA 讀得到腳本狀態）', '已用 0x005000-0x005011'),
    ('0x005020-0x00502F', 'MGEF／SPEL 真實傷害、破魔印、沉默', '已用 0x005020-0x005026'),
    ('0x005030-0x00503F', 'MGEF／SPEL 自有常駐能力（抗咒、溫血、感應、風行、風隱、毒免）',
     '已用 0x005030-0x005035（MGEF）與 0x005038-0x00503D（SPEL）'),
    ('0x005050-0x00505F', 'KYWD 機制前線（破魔印、沉默）', '已用 0x005050-0x005051'),
    ('0x005080-0x00509F', 'MGEF 輔助效果第二批（第 8-27 號）', '已用 0x005080-0x005093'),
    ('0x0050A0-0x0050BF', 'SPEL 輔助法術第二批（第 8-27 號）', '已用 0x0050A0-0x0050B3'),
    ('0x0050C0-0x0050CF', 'GLOB 機制狀態鏡射第二批（round 2：岩甲、風勢、聖盾、領域…）',
     '已用 0x0050C0-0x0050C9'),
    ('0x0050D0-0x0050DF', 'MGEF／SPEL round 2（化灰、無聲）', '已用 0x0050D0-0x0050D2'),
    ('0x0050E0-0x0050EF', 'MGEF／SPEL 血承（7 個屬性效果 + 1 個法術）', '已用 0x0050E0-0x0050E7'),
    ('0x0050F0-0x0050FF', 'PERK 基礎規則（常駐，開局由控制器 AddPerk）', '已用 0x0050F0'),
    ('0x005100-0x00511F', 'GLOB 機制狀態鏡射第三批（round 3：水鏡、三個受傷視窗、四種領域）',
     '已用 0x005100-0x005107'),
    ('0x005120-0x00512F', 'MGEF／SPEL round 3（恐懼、瘋狂、亡者歸來、洗淨、淨化、沖刷）',
     '已用 0x005120-0x00512D'),
    ('0x005130-0x005133', 'MGEF 同調光暈 ×3（一段石膚、二段鐵膚、三段黑檀膚）', '已用 0x005130-0x005132'),
    ('0x005134-0x005143', 'MGEF 同調三段武器發光 ×11', '已用 0x005134-0x00513E'),
    ('0x005144-0x00514F', 'MGEF 重擊附傷 ×4（火／冰／雷／暗，改用 Upgraded 衝擊組）', '已用 0x005144-0x005147'),
    ('0x005150-0x005FFF', '保留：後續前線', '保留'),
    ('0x006000-0x006FFF', 'QUST state schema 世代專用（每代 2 筆；舊代永留 stub）', '由 state_schema_version 決定'),
]

sys.path.insert(0, str(WORK / 'build'))
import state_schema
STATE_SCHEMA_VERSION = json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))['state_schema_version']
SCHEMA_QUEST_IDS = state_schema.quest_ids(STATE_SCHEMA_VERSION)
SCHEMA_STUBS = state_schema.stub_ids(STATE_SCHEMA_VERSION)
ID_QUEST = SCHEMA_QUEST_IDS['ESSB_MainQuest']
ID_MCM_QUEST = SCHEMA_QUEST_IDS['ESSB_MCMQuest']
FIX5_NEW_EDIDS = {'ESSB_MCMQuest'}
ID_GLOB = {
    'ESSB_Enabled': 0x000810,
    'ESSB_DebugLevel': 0x000811,
    'ESSB_CurrentElement': 0x000812,
    'ESSB_FormActive': 0x000813,
    'ESSB_Sync': 0x000814,
    'ESSB_SchoolXPMult': 0x000815,
}
# Appended after the pre-fix4 highest record (0x005157); identities stay fixed.
ID_BALANCE_GLOB = {
    'ESSB_PoisonDotK': (0x005158, 'poison_dot_k'),
    'ESSB_BleedDotK': (0x005159, 'bleed_dot_k'),
    'ESSB_BaseDamageMult': (0x00515A, 'base_damage_mult'),
    'ESSB_NodeScale': (0x00515C, 'node_percent_scale'),
    'ESSB_ManabreakBase': (0x00515D, 'manabreak_base'),
    'ESSB_ManabreakPerRank': (0x00515E, 'manabreak_per_rank'),
    'ESSB_ManabreakMaxmagPct': (0x00515F, 'manabreak_maxmag_pct'),
    'ESSB_ManabreakDryPct': (0x005160, 'manabreak_dry_pct'),
    'ESSB_WaterFlowBasePct': (0x005161, 'water_flow_base_pct'),
    'ESSB_WaterFlowPerRankPct': (0x005162, 'water_flow_per_rank_pct'),
    'ESSB_WaterWetSlowPct': (0x005163, 'water_wet_slow_pct'),
    'ESSB_FrostOpenSlowPct': (0x005164, 'frost_open_slow_pct'),
    'ESSB_SlowCapPct': (0x005165, 'slow_cap_pct'),
    'ESSB_WaterClearStamina': (0x005166, 'water_clear_stamina'),
    'ESSB_WaterOpenStamina': (0x005167, 'water_open_stamina'),
    'ESSB_MultDot': (0x005168, 'mult_dot'),
    'ESSB_MultCooldown': (0x005169, 'mult_cooldown'),
    'ESSB_MultRecovery': (0x00516A, 'mult_recovery'),
    'ESSB_MultDrain': (0x00516B, 'mult_drain'),
    'ESSB_MultDuration': (0x00516C, 'mult_duration'),
    'ESSB_MultUpkeep': (0x00516D, 'mult_upkeep'),
}
ID_KW_PROC = 0x000830
ID_KW_TRUE = 0x000831
ID_KW_ELEMENT = 0x000840
ID_KW_MARK = 0x000850
ID_SETTINGS_MENU = 0x000890
ID_SETTINGS_EFFECT = 0x000891
ID_SETTINGS_POWER = 0x000892
ID_FORM_POWER_EFFECT = 0x000900
ID_FORM_POWER_SPELL = 0x000920
ID_FORM_ABILITY_EFFECT = 0x000940
ID_FORM_ABILITY_SPELL = 0x000960
ID_FORM_RULES_EFFECT = 0x000980
ID_FORM_RULES_SPELL = 0x000981
ID_HIT_EFFECT = 0x000A00
ID_HIT_SPELL = 0x000B00

# ---------------------------------------------------------------- 引擎前線（0x001000-0x001FFF）
ID_MARK_EFFECT = 0x001000
ID_MARK_SPELL = 0x001020
ID_REACT_EFFECT = 0x001040
ID_REACT_SPELL = 0x001060
ID_STATUS_EFFECT = 0x001080
ID_STATUS_SPELL = 0x001081
ID_ENGAGED_EFFECT = 0x001082
ID_ENGAGED_SPELL = 0x001083
ID_UTIL_EFFECT = 0x001090
ID_UTIL_SPELL = 0x0010A0
ID_KW_STATUS = 0x001F00
ID_KW_ENGAGED = 0x001F01
ID_KW_REACT = 0x001F02
ID_GLOB_ENGINE = {
    'ESSB_SyncT1': 0x001F10,
    'ESSB_SyncT2': 0x001F11,
    'ESSB_SyncT3': 0x001F12,
    'ESSB_EnvWet': 0x001F13,
    'ESSB_EnvStormy': 0x001F14,
    'ESSB_EnvNight': 0x001F15,
}

# 規劃 2.6 的輔助效果（控制器 UtilSpells 的索引順序就是這一張表）。
# (後綴, 中文, AV, 是否有持續時間, 是否有害, 抗性AV)
# 有持續時間的一律用原型 34（Peak Value Modifier）並帶 Recover 旗標，
# 與原版 FrostSlowFFContact／AlchFortify* 同款；原型 0（Value Modifier）只給瞬間的
# 削減與回復。原型 0 + 持續時間 + 沒有 Recover 會讓 AV 永久改變，這是本輪修掉的問題。
UTILS = [
    ('Slow', '緩速', 30, True, True, -1),
    ('ArmorDebuff', '碎甲', 39, True, True, -1),
    ('DrainMagicka', '削魔', 25, False, True, -1),
    ('DrainStamina', '削耐', 26, False, True, -1),
    ('RestoreHealth', '回血', 24, False, False, -1),
    ('RestoreMagicka', '回魔', 25, False, False, -1),
    ('RestoreStamina', '回耐', 26, False, False, -1),
    ('BleedTick', '放血', 24, False, True, -1),
    # ---- 機制前線 round 1 新增（索引 8 起，記錄放在 0x005080／0x0050A0）
    ('MagicResistBuff', '抗咒', 44, True, False, -1),
    ('Haste', '疾行', 30, True, False, -1),
    ('MagickaRateBuff', '魔力回復', 156, True, False, -1),
    ('StaminaRateBuff', '耐力回復', 157, True, False, -1),
    ('MagickaRateDrain', '停止回魔', 156, True, True, -1),
    ('FireResistDebuff', '火抗削減', 41, True, True, -1),
    ('FrostResistDebuff', '冰抗削減', 43, True, True, -1),
    ('ShockResistDebuff', '電抗削減', 42, True, True, -1),
    ('MagicResistDebuff', '魔抗削減', 44, True, True, -1),
    ('MeleeDebuff', '攻擊削弱', 34, True, True, -1),
    # ---- 機制前線 round 2 新增（索引 18 起）
    # AV 39 DamageResist（岩甲的護甲加成，同原版石膚的做法）、AV 24 Health（血盾的臨時生命）、
    # AV 155 HealRateMult（血咒的「受治療 -50%」，見實作紀錄的偏離說明）、
    # AV 157 StaminaRateMult（地裂帶的「耐力不回復」）、AV 92 Muffle（風的潛行無聲）。
    ('ArmorBuff', '岩甲', 39, True, False, -1),
    ('TempHealth', '血盾', 24, True, False, -1),
    ('HealRateDebuff', '治療削減', 155, True, True, -1),
    ('StaminaRateDebuff', '耐力凝滯', 157, True, True, -1),
    ('MuffleBuff', '消音', 92, True, False, -1),
    # ---- 機制前線 round 3 新增（索引 23 起）
    # AV 40 PoisonResist（毒膜、百毒不侵／侵蝕、腐蝕開印、劇毒、詛咒的毒抗侵蝕）、
    # AV 155 HealRateMult（以毒攻毒的「生命回復 +20%」）、AV 45 ResistDisease（百毒不侵）、
    # AV 34 MeleeDamage（亡者強化的僕從攻擊加成，與「攻擊削弱」同一個 AV 與慣例）。
    # AV 索引是掃本機 Skyrim.esm 對出來的：EnchResistPoisonConstantSelf = 40、
    # EnchResistDiseaseConstantSelf = 45。
    ('PoisonResistBuff', '毒抗強化', 40, True, False, -1),
    ('PoisonResistDebuff', '毒抗削減', 40, True, True, -1),
    ('HealRateBuff', '治療強化', 155, True, False, -1),
    ('DiseaseResistBuff', '疾病抗性', 45, True, False, -1),
    ('MeleeBuff', '攻擊強化', 34, True, False, -1),
]
UTIL_LEGACY = 8            # 前 8 個留在引擎前線的 0x001090／0x0010A0，不重新編號。
# 洗淨／淨化的 SELF 路徑要逐項移除的「本模組自己的有時限減益」。
# 瞬間型（沒有持續時間）不必列：套用完就結束，沒有東西可以 Dispel。
SELF_CLEANSE_UTILS = [ix for ix, u in enumerate(UTILS) if u[3] and u[4]]


def util_effect_id(index):
    if index < UTIL_LEGACY:
        return ID_UTIL_EFFECT + index
    return ID_UTIL2_EFFECT + (index - UTIL_LEGACY)


def util_spell_id(index):
    if index < UTIL_LEGACY:
        return ID_UTIL_SPELL + index
    return ID_UTIL2_SPELL + (index - UTIL_LEGACY)

# Skyrim.esm 參照
FID_GAME_HOUR = 0x00000038
FID_KW_UNDEAD = 0x00013796
FID_KW_DAEDRA = 0x00013797
FID_KW_ARMOR_SPELL = 0x0001EA72
FID_KW_CLOAK = 0x000B62E4

# ---------------------------------------------------------------- 機制前線（0x002000-0x002FFF、0x004000-0x004FFF）
# 節點索引 ni = (tree * 3 + route) * 5 + tier，共 195 個。
ID_BRANCH_PERK = 0x002000      # + ni * 4 + n（每階預留 4 格分支）
ID_MAIN_PERK = 0x004000        # + ni * 15 + rank（rank 0 起算，共 15 階）
ID_TREE_GLOB = {
    'Lvl': 0x002400,
    'Ratio': 0x002420,
    'Pts': 0x002440,
    'Color': 0x002460,
    'ShowLvl': 0x002480,
    'Respec': 0x0024A0,
}
ID_SHOW_MENU = 0x0024C0
ID_XP_PER_HIT = 0x0024C1

# ---------------------------------------------------------------- 機制前線 round 1（0x005000-0x005FFF）
# 樣式 C（引擎側效果）需要 PERK 進入點，而 CTDA 只讀得到全域變數，
# 所以腳本狀態鏡射成這一段 GLOB，由 ESSBController 在值變動時寫一次。
ID_MECH_GLOB = 0x005000
MECH_GLOBALS = [
    ('ESSB_SyncStage', 0), ('ESSB_Resolve', 0), ('ESSB_Overheat', 0), ('ESSB_Charge', 0),
    ('ESSB_IceShield', 0), ('ESSB_Molten', 0), ('ESSB_Ember', 0), ('ESSB_Quench', 0),
    ('ESSB_PrevElement', 0), ('ESSB_TwinElement', 0), ('ESSB_DomainFire', 0), ('ESSB_DomainFrost', 0),
    ('ESSB_ShockRecent', 0), ('ESSB_GuardSwitch', 0), ('ESSB_GuardBurst', 0), ('ESSB_GuardIce', 0),
    ('ESSB_Combo', 0), ('ESSB_FreeOpen', 0),
]
ID_TRUE_EFFECT = 0x005020
ID_TRUE_SPELL = 0x005021
ID_MANABREAK_EFFECT = 0x005022
ID_MANABREAK_SPELL = 0x005023
ID_SILENCE_EFFECT = 0x005024
ID_SILENCE_SPELL = 0x005025
ID_ABILITY_EFFECT = 0x005030
ID_ABILITY_SPELL = 0x005038
ID_KW_MANABREAK = 0x005050
ID_KW_SILENCE = 0x005051
# 第一批輔助效果只剩 8 格（0x001090-0x001097 已用滿 0x00109F 的一半），
# 第 8 號以後移到 0x005080／0x0050A0，索引仍然連續，見 util_effect_id()。
ID_UTIL2_EFFECT = 0x005080
ID_UTIL2_SPELL = 0x0050A0

# 自有常駐能力（抗咒、溫血、感應）：(後綴, 中文, AV, 強度)
ABILITIES = [
    ('AntiMagic', '抗咒', 44, 15.0),
    ('WarmBlood', '溫血', 157, 20.0),
    ('Induction', '感應', 156, 20.0),
    # ---- round 2：風形態的移速與潛行（規劃 1.1 的風形態規則、5.7 專精／大師分支）。
    # 移速的強度隨節點變動，所以控制器在 AddSpell 之前 SetNthEffectMagnitude(0, 總量)。
    ('WindSpeed', '風行', 30, 10.0),
    ('Muffle', '風隱', 92, 0.5),
    # ---- round 3：毒形態的「免疫」（毒抗 +50%）。星界的「星輝」與雷的「感應」效果相同，
    # 沿用同一個能力記錄，不新增（見實作紀錄）。
    ('PoisonResist', '毒免', 40, 50.0),
]

# ---------------------------------------------------------------- 機制前線 round 2（0x0050C0-0x0050FF）
ID_MECH2_GLOB = 0x0050C0
MECH2_GLOBALS = [
    ('ESSB_RockArmor', 0), ('ESSB_Wind', 0), ('ESSB_HolyShield', 0), ('ESSB_Bloodthirst', 0),
    ('ESSB_GuardWind', 0), ('ESSB_GuardDivine', 0), ('ESSB_DomainEarth', 0), ('ESSB_DomainBlood', 0),
    ('ESSB_DomainDivine', 0), ('ESSB_NoBloodCost', 0), ('ESSB_CloakGuard', 0),
]
# 化灰：DATA 完全照抄本機 Skyrim.esm 的 PerkDisintegrateFFAimed（flags 0x10209805、原型 0、
# AV 24、skill 20、resist 42），只有 resist 改成 -1，因為裁決的化灰不該被電抗擋掉。
ID_ASH_EFFECT = 0x0050D0
ID_ASH_SPELL = 0x0050D1
ID_SILENT_SPELL = 0x0050D2
MGEF_ASH_FLAGS = 0x10209805
# 血承：七個 Peak Value Modifier（火冰電毒魔抗、護甲、最大生命），magnitude 由腳本在施放前設定。
ID_INHERIT_EFFECT = 0x0050E0
ID_INHERIT_SPELL = 0x0050E7
INHERIT_AVS = [(41, '火抗'), (43, '冰抗'), (42, '電抗'), (40, '毒抗'), (44, '魔抗'),
               (39, '護甲'), (24, '生命上限')]
# 基礎規則天賦：不是節點，開局由控制器 AddPerk，永不移除。裝的是「不依賴投點的引擎側規則」。
ID_BASE_PERK = 0x0050F0

# Skyrim.esm 參照（round 2）
FID_KW_DRAGON = 0x00035D59
FID_RACE_GIANT = 0x000131F9
FID_RACE_MAMMOTH = 0x000131FF
FID_CLASS_NECRO = 0x000C969F
FID_FACT_NECRO = 0x00034B74

# ---------------------------------------------------------------- 機制前線 round 3（0x005100-0x00512F）
ID_MECH3_GLOB = 0x005100
MECH3_GLOBALS = [
    ('ESSB_WaterMirror', 0), ('ESSB_GuardDark', 0), ('ESSB_GuardAstral', 0), ('ESSB_GuardStar', 0),
    ('ESSB_DomainPoison', 0), ('ESSB_DomainWater', 0), ('ESSB_DomainDark', 0), ('ESSB_DomainAstral', 0),
]
# 原型（archetype）全部是掃本機 Skyrim.esm 的 MGEF DATA 對出來的實測值：
#   7  Demoralize  InfluenceConfDownFFAimed（skill 21 幻術、magnitude ＝ 可影響的最高等級）
#   8  Frenzy      InfluenceAggUpFFAimed
#  22  Reanimate   ReanimateFFTargetActor0（skill 19 召喚、delivery 3、magnitude ＝ 等級上限，
#                  duration 在法術的 EFIT；原版 VampireRaiseThrall01-04 是 6/13/21/30 級 60 秒，
#                  DeathThrall 是 40 級 86313600 秒＝永久）
#   3  Cure Disease  CureDiseaseEffect
#  29  Cure Poison   AlchCurePoison
#   2  Dispel      本機 Skyrim.esm 沒有任何 MGEF 用這個原型，所以是由 0/1/3/4 四個實測點
#                  推出來的（Value Modifier／Script／Cure Disease／Absorb 之間只剩 2），
#                  進 CK 要確認。MGEF 旗標 0x100（Dispel Keywords）讓它只清 KWDA 列出的類別。
MGEF_ARCH_DISPEL = 2
MGEF_ARCH_CURE_DISEASE = 3
MGEF_ARCH_DEMORALIZE = 7
MGEF_ARCH_FRENZY = 8
MGEF_ARCH_REANIMATE = 22
MGEF_ARCH_CURE_POISON = 29
# 恐懼／瘋狂：敵對 0x1、Recover 0x2、有害 0x4、無範圍 0x800、介面隱藏 0x8000。
MGEF_CHARM_FLAGS = 0x00008807
# 復生：照抄 ReanimateFFTargetActor0 的 0x00401002（Recover + 無範圍 + 無強度顯示 + 無死亡解除）。
MGEF_REANIMATE_FLAGS = 0x00401002
# 洗淨／淨化／沖刷：不敵對、不有害、無範圍、介面隱藏；洗淨與淨化再加 0x100 Dispel Keywords。
MGEF_DISPEL_FLAGS = 0x00008800
MGEF_DISPEL_KW_FLAGS = 0x00008900
ID_FEAR_EFFECT = 0x005120
ID_FEAR_SPELL = 0x005121
ID_FRENZY_EFFECT = 0x005122
ID_FRENZY_SPELL = 0x005123
ID_REANIMATE_EFFECT = 0x005124
ID_REANIMATE_SPELL = 0x005125
ID_CLEANSE_EFFECT = 0x005126
ID_CUREDISEASE_EFFECT = 0x005127
ID_PURGE_EFFECT = 0x005128
ID_CUREPOISON_EFFECT = 0x005129
ID_CLEANSE_SPELL = 0x00512A
ID_PURGE_SPELL = 0x00512B
ID_STRIP_EFFECT = 0x00512C
ID_STRIP_SPELL = 0x00512D

# Skyrim.esm 參照（round 3；全部是掃本機 Skyrim.esm 的 KYWD／PERK 對出來的）
FID_KW_NO_REANIMATE = 0x0006F6FB
FID_KW_ALCH_HARMFUL = 0x00042509
FID_KW_MAGIC_SLOW = 0x000B729E
FID_KW_PARALYSIS = 0x0001EA70
FID_KW_INFLUENCE = 0x00078098
FID_KW_INFLUENCE_FEAR = 0x000424E0
FID_KW_INFLUENCE_FRENZY = 0x000C44B6
FID_KW_SUMMON_UNDEAD = 0x0002482B
FID_KW_DAMAGE_FIRE = 0x0001CEAD
FID_KW_DAMAGE_FROST = 0x0001CEAE
FID_KW_DAMAGE_SHOCK = 0x0001CEAF
FID_PERK_TWIN_SOULS = 0x000D5F1C
# 洗淨（5.11 持續專精分支）只清四類：中毒（MagicAlchHarmful）、元素持續傷（三個）、減速。
CLEANSE_KEYWORDS = [FID_KW_ALCH_HARMFUL, FID_KW_DAMAGE_FIRE, FID_KW_DAMAGE_FROST,
                    FID_KW_DAMAGE_SHOCK, FID_KW_MAGIC_SLOW]
# 淨化（5.11 持續大師分支）再加麻痺與幻術影響類；仍然是「限定關鍵字」，
# 所以不會像原版 Dispel 那樣把玩家自己的增益一起洗掉（規劃 8 的守則）。
PURGE_KEYWORDS = CLEANSE_KEYWORDS + [FID_KW_PARALYSIS, FID_KW_INFLUENCE,
                                     FID_KW_INFLUENCE_FEAR, FID_KW_INFLUENCE_FRENZY]

# ---------------------------------------------------------------- 特效前線（0x003000-0x003FFF、0x005130-0x00514F）
# 規劃 2.11／2.12：美術全部借用載入順序中已有的法術包，記錄以「複製進本模組 ESP」的方式
# 進來（fx_extract.export），masters 仍然只有 Skyrim.esm；貼圖、模型、音檔留在原模組。
ID_FX_BASE = 0x003000
ID_FX_LIMIT = 0x004000
# 自有的新記錄（同調光暈、重擊衝擊組分流）接在機制前線之後。
ID_SYNC_GLOW_EFFECT = 0x005130      # ×3：同調一／二／三段的光暈強度遞增
ID_SYNC_WEAPON_EFFECT = 0x005134    # ×11：三段時的武器發光（每元素一個）
ID_HIT_POWER_EFFECT = 0x005144      # ×4：有 Upgraded 衝擊組的火／冰／雷／暗

FX_PLUGIN = 'Phenderix Elements.esp'
FX_PMW = 'Phenderix Magic World.esm'
# Phenderix Elements 的元素命名與本模組的 ELEMENTS 完全一致（已核對 11/11）。
FX_UPGRADED = ['Fire', 'Frost', 'Lightning', 'Darkness']
# Phenderix 每元素成套的家族：形態著色器、命中著色器、衝擊組、手部爆炸、藝術物件、
# 五種音效（SNDR 描述子 + SOUN 包裝，SOUN 才能給 Papyrus 的 Sound.Play）。
FX_SOUND_FAMILIES = ['FormActive', 'Release', 'DrawSheathe', 'Charge', 'OnHit']

# 規劃 2.11 的逐元素來源表：(形態光環, 同調三段武器光, 印記／命中特效)。
# 舊形態來源保留為備用；末欄只供命中／反應，印記獨立由 settings.fx_mark 決定。
FX_ELEMENT = [
    ('Fire',      'vulcano.esp|DAR_MoltenFXShader',                None,
                  'vulcano.esp|DAR_MoltenSpellLavaMistShader'),
    ('Frost',     'Icebloom.esl|_IP_FrostIceFormFXShader02',       'Atromancy.esp|_ATRO_FrostBuffFXShader2',
                  'IceBloomNightmare.esl|_IP_FrostFXShader'),
    ('Lightning', 'Arclight.esp|DAR_ArcFXShader',                  'Atromancy.esp|_ATRO_StormBuffFXShader2',
                  'StormCalling.esl|_SC_ShockStormFXShader'),
    ('Earth',     'Natura.esp|NAT_MagicArmorStoneFleshFXS',        'Natura.esp|NAT_ArmorRatingSFXS',
                  None),
    ('Wind',      'Aero.esl|_AV_EffectShader',                     f'{FX_PLUGIN}|ZZShader_Wind',
                  'Natura.esp|NAT_WindHitFX'),
    ('Blood',     'Natura.esp|DAR_RedFXS',                         f'{FX_PLUGIN}|ZZShader_Blood',
                  'Bloodmoon.esp|BLO_BloodDamageImpactMist'),
    ('Divine',    'Inquisition.esp|INQ_HealingLightFXS',           'Inquisition.esp|INQ_EnchHolySwordFXS',
                  'Lightpower.esl|_LIP_ConsecrateDeadFXSA'),
    ('Poison',    'Venomancy.esp|_VENOM_PoisonCloakFXShader',      'Venomancy.esp|_VENOM_PoisonWeaponFXShader',
                  'Venomancy.esp|_VENOM_PoisonMistFXShader'),
    ('Water',     f'{FX_PLUGIN}|ZZShader_WaterForm',               'Natura.esp|NAT_WaterShader',
                  f'{FX_PMW}|ZZWaterloggedShader1'),
    ('Darkness',  'Abyss.esp|ABY_ShadowFXS',                       'Necrotic.esp|NEC_EnchNecroticSwordFXS',
                  'Abyss.esp|ABY_ShadowDamageImpactMist'),
    ('Astral',    'Stellaris.esp|DAR_AstralFXShader',              'Lunaris.esp|LUN_BlueFXS',
                  'Stellaris.esp|DAR_AstralSpellStarMistShader'),
]
# 2.11 點名但本前線只複製、還沒掛上的備選與狀態素材（進了 ESP，CK 裡隨時可換）。
FX_SPARE = [
    'vulcano.esp|DAR_MoltenHeartFXS',            # 火：過熱
    'Aero.esl|_AV_CloakHitShader_Layer0',        # 風：旋風疊層
    'Bloodmoon.esp|BLO_BleedingShader',          # 血：放血
    'Ghostlight.esl|_BL_EffectShaderCloak',      # 聖：備選（白光鎖鏈）
    'Venomancy.esp|_VENOM_ToxicAuraEffect',      # 毒：備選光環
    'Venomancy.esp|_VENOM_RotfleshFXS',          # 毒：催毒
    'Abyss.esp|ABY_ShadowPriestFleshFXS',        # 暗：Shadow Form
    'Necrom.esp|DAR_EldritchShadowMist',         # 暗：詛咒
    'Arcane.esp|DAR_ArcanFXS',                   # 星：備選
    'Lunaris.esp|LUN_MoonFXShader',              # 星：備選
    # 2.11 最後一列的通用色版（Darenii）。全部取 Natura 那一套，避免同 EDID 撞名。
    'Natura.esp|DAR_OrangeFXS', 'Natura.esp|DAR_GreenFXS', 'Natura.esp|DAR_BlueFXS',
    'Natura.esp|DAR_PurpleFXS', 'Natura.esp|DAR_WhiteMistFXS',
]
# 真實傷害／破魔印／沉默的白光（2.11 最後一列；Apocalypse 的 WB_FXS_White 不在載入順序裡）。
FX_WHITE = 'Ghostlight.esl|_BL_EffectShaderWhiteShockGlow'

# fix round 3: independent, silent edge markers. Source colours are parsed, not EDID guesses.
FX_EDGE_TEMPLATE = 'StormCalling.esl|_SC_ShockStormFXShader'
FX_EDGE_COLORS = dict(zip(ELEMENTS, [
    f'{FX_PLUGIN}|ZZShader_Fire', 'Atromancy.esp|_ATRO_FrostBuffFXShader2',
    FX_EDGE_TEMPLATE, f'{FX_PLUGIN}|ZZShader_Earth', 'Aero.esl|_AV_EffectShader',
    'Natura.esp|DAR_RedFXS', f'{FX_PLUGIN}|ZZShader_Divine',
    'Venomancy.esp|_VENOM_PoisonCloakFXShader', f'{FX_PLUGIN}|ZZShader_WaterForm',
    f'{FX_PLUGIN}|ZZShader_DarknessForm', f'{FX_PLUGIN}|ZZShader_Astral',
]))
FX_AURA_DEFAULT = {n: f'{FX_PLUGIN}|ZZShader_{n}Form' for n in ELEMENTS}
FX_MARK_DEFAULT = {n: f'{PLUGIN}|ESSBFX_Mark_{n}' for n in ELEMENTS}
FX_STATUS_WHITE = f'{PLUGIN}|ESSBFX_Status_White'
FX_STATUS_FROZEN = f'{PLUGIN}|ESSBFX_Status_Frozen'

# Byte offsets counted from vendor/wbDefinitionsTES5.pas, EFSH DATA (400 bytes).
EFSH_FLOATS = {
    'fill_fade_in': 20, 'fill_full_time': 24, 'fill_fade_out': 28,
    'fill_persistent_alpha': 32, 'fill_pulse': 36, 'edge_falloff': 52,
    'edge_fade_in': 60, 'edge_full_time': 64, 'edge_fade_out': 68,
    'edge_persistent_alpha': 72, 'edge_pulse': 76,
    'fill_full_alpha': 84, 'edge_full_alpha': 88,
    'particle_full_time': 116, 'particle_birth_ratio': 124,
    'particle_persistent_count': 128, 'particle_lifetime': 132,
}


def efsh_visibility(ss):
    data = dict(ss)['DATA']
    if len(data) < 312:
        raise ValueError(f'Unsupported EFSH DATA length: {len(data)}')
    values = {name: struct.unpack_from('<f', data, offset)[0]
              for name, offset in EFSH_FLOATS.items()}
    if not all(math.isfinite(v) for v in values.values()):
        raise ValueError('Non-finite EFSH visibility value')
    flags = struct.unpack_from('<I', data, 384)[0] if len(data) >= 388 else None
    values.update(data_bytes=len(data), edge_color=list(data[56:59]),
                  flags=flags, flags_hex=f'0x{flags:08X}' if flags is not None else None,
                  no_membrane=bool(flags & 1) if flags is not None else None,
                  no_particles=bool(flags & 8) if flags is not None else None,
                  skin_only=bool(flags & 0x20) if flags is not None else None,
                  particle_animated=bool(flags & 0x8000) if flags is not None else None,
                  particle_grayscale_color=bool(flags & 0x10000) if flags is not None else None,
                  particle_grayscale_alpha=bool(flags & 0x20000) if flags is not None else None,
                  ambient_sound=f'{struct.unpack_from("<I", data, 308)[0]:08X}')
    # Conservative gate: particle-only / absent flags cannot prove a readable outline.
    values['persistent_edge_visible'] = (flags is not None and not (flags & 0x31)
        and values['edge_persistent_alpha'] - abs(values['edge_pulse']) >= 0.35
        and values['edge_full_alpha'] > 0 and max(values['edge_color']) >= 80)
    return values


def fx_settings(settings):
    out = {}
    for name, defaults in [('fx_aura', FX_AURA_DEFAULT), ('fx_mark', FX_MARK_DEFAULT)]:
        overrides = settings.get(name, {})
        if not isinstance(overrides, dict) or set(overrides) - set(ELEMENTS):
            raise ValueError(f'{name}: expected element -> Plugin|EDID map; elements={ELEMENTS}')
        out[name] = dict(defaults, **overrides)
        for element, selector in out[name].items():
            if (not isinstance(selector, str) or selector.count('|') != 1
                    or not all(selector.split('|')) or selector != selector.strip()):
                raise ValueError(f'{name}.{element}: expected Plugin|EDID, got {selector!r}')
    return out


def fx_edge_record(template, colour_source, edid, fid, key, *, frozen=False):
    """New record only: preserve all borrowed shaders byte-for-byte (including weapon/hit)."""
    rgb = efsh_visibility(colour_source['ss'])['edge_color']
    if max(rgb) == 0:
        raise ValueError(f'Black edge colour in {colour_source["edid"]}')
    rgb = [round(c * 255 / max(rgb)) for c in rgb]
    data = bytearray(dict(template['ss'])['DATA'])
    if len(data) != 400:
        raise ValueError('Edge template must have the full TES5 EFSH DATA')
    # No fill for marks; frost status alone has a faint ice-white membrane.
    for offset, value in {20: 0, 24: 0.05, 28: 0, 32: 0.18 if frozen else 0,
                          36: 0, 40: 0, 52: 1, 60: 0, 64: 0.05, 68: 0,
                          72: 1, 76: 0, 80: 0, 84: 0.18 if frozen else 0, 88: 1,
                          112: 0, 116: 0, 120: 0, 124: 0, 128: 0}.items():
        struct.pack_into('<f', data, offset, value)
    data[16:20] = data[56:60] = bytes(rgb + [0])
    struct.pack_into('<I', data, 244, 0)   # no addon geometry
    struct.pack_into('<I', data, 308, 0)   # no ambient / looping sound
    struct.pack_into('<I', data, 384, 0x408)  # No Particle Shader + No Weapons
    ss = [(k, Z(edid) if k == 'EDID' else bytes(data) if k == 'DATA' else v)
          for k, v in template['ss']]
    return {'sig': 'EFSH', 'edid': edid, 'key': key, 'fid': fid, 'ss': ss,
            'plugin': PLUGIN, 'source_id': edid, 'dropped': [],
            'derived_from': {'template': FX_EDGE_TEMPLATE, 'colour': colour_source['edid'],
                             'colour_source_rgb': efsh_visibility(colour_source['ss'])['edge_color'],
                             'normalization': 'RGB scaled uniformly so max channel = 255'}}


# 同調光暈的強度遞增：規劃 2.11「一段石膚、二段鐵膚、三段黑檀膚」，三個都在 Skyrim.esm，
# 不必複製（掃本機 Skyrim.esm 的 EFSH 對出來的 FormID）。
FID_EFSH_STONEFLESH = 0x00094161
FID_EFSH_IRONFLESH = 0x00094163
FID_EFSH_EBONYFLESH = 0x00094162
SYNC_GLOW_SHADERS = [FID_EFSH_STONEFLESH, FID_EFSH_IRONFLESH, FID_EFSH_EBONYFLESH]

# 原版既有特效（規劃 2.12 最後一列「化灰、復生用原版既有」）：全部是掃本機 Skyrim.esm
# 的 MGEF DATA 對出來的實測值，直接以 master 參照，不複製。
FID_EFSH_REANIMATE = 0x00075272         # ReanimateFXShader
FID_ARTO_REANIMATE = 0x00075271         # ReanimateTargetFX
FID_IPDS_REANIMATE = 0x00075346         # MAGReanimatelImpactSet
FID_EFSH_FEAR = 0x0007D450              # IllusionFearFXS
FID_EFSH_FRENZY = 0x00074799            # IllusionNegativeFXS
FID_ARTO_ILLUSION_NEG = 0x00074795      # IllusionNegFXBody01
FID_IPDS_ILLUSION_NEG = 0x00074798      # MAGIllusionNegImpactSet
FID_EFSH_HEAL_MYSTIC = 0x0004E220       # HealMysticFXS
FID_ARTO_HEAL_MYSTIC = 0x0004E221       # HealMystTargetFX

# MGEF SNDD 的音效型別（wbDefinitionsTES5.pas 的 MGEF 聲音陣列；參照的是 SNDR）。
SND_DRAW_SHEATHE = 0
SND_CHARGE = 1
SND_READY = 2
SND_RELEASE = 3
SND_CONCENTRATION = 4
SND_ON_HIT = 5

NEXT_OBJECT_ID = max(0x006000, ID_QUEST + 1, ID_MCM_QUEST + 1)

# MGEF DATA 旗標：敵對 0x1、有害 0x4、無命中事件 0x10、無持續 0x200、無強度 0x400、
# 無範圍 0x800、介面隱藏 0x8000、威力影響強度 0x200000。
MGEF_HIT_FLAGS = 0x00208A15
MGEF_UTILITY_FLAGS = 0x00008E00
# 印記：有持續時間、無強度、無範圍、介面隱藏、敵對有害。
MGEF_MARK_FLAGS = 0x00008C15
# 內部容器（狀態宿主、已交戰標記）：不敵對，避免在原版之外多製造敵意。
MGEF_MARKER_FLAGS = 0x00008C10
# 反應與 DoT 的瞬間傷害：同附傷，但不吃威力（反應不吃重擊倍率）。
MGEF_REACT_FLAGS = 0x00008A15
# 有持續時間的減益（減速、碎甲）：加 Recover（0x2），原型改用 34 Peak Value Modifier。
MGEF_DEBUFF_FLAGS = 0x00008817
# 有持續時間的增益（自有能力與短時 buff）：Recover，不敵對、不有害。
MGEF_BUFF_FLAGS = 0x00008812
# 真實傷害（規劃 2.8）：不掛學派、Resist Value = None，其餘同反應傷害。
MGEF_TRUE_FLAGS = 0x00008A15
# 瞬間的自身回復（不敵對、不有害）。
MGEF_RESTORE_FLAGS = 0x00008A10

I = lambda x: struct.pack('<I', x)
i32 = lambda x: struct.pack('<i', x)
F = lambda x: struct.pack('<f', x)
Z = lambda s: s.encode('utf-8') + b'\0'


def ref(plugin, fid):
    return (MASTERS.index(plugin) << 24) | fid


def own(fid):
    return (len(MASTERS) << 24) | fid


def vstr(s):
    b = s.encode('utf-8')
    return struct.pack('<H', len(b)) + b


def obj(fid, alias=-1):
    return struct.pack('<HhI', 0, alias, fid)


def prop_value(typ, value):
    if typ == 1:
        # (formid, aliasID) 代表別名屬性（objFormat 2 的 Object union 帶 aliasID）。
        if isinstance(value, tuple):
            return obj(value[0], value[1])
        return obj(value)
    if typ == 2:
        return vstr(value)
    if typ == 3:
        return i32(value)
    if typ == 4:
        return F(value)
    if typ == 5:
        return bytes([1 if value else 0])
    if typ == 11:
        return I(len(value)) + b''.join(obj(x) for x in value)
    if typ == 13:
        return I(len(value)) + b"".join(i32(x) for x in value)
    if typ == 14:
        return I(len(value)) + b''.join(F(x) for x in value)
    raise ValueError(f'unsupported VMAD property type {typ}')


def script(name, props):
    body = vstr(name) + b'\0' + struct.pack('<H', len(props))
    for prop, (typ, value) in props.items():
        body += vstr(prop) + bytes([typ, 1]) + prop_value(typ, value)
    return body


def vmad(name, props):
    return struct.pack('<3H', 5, 2, 1) + script(name, props)


def record(sig, fid, ss, flags=0):
    raw = b''.join(sub(k, v) for k, v in ss)
    return struct.pack('<4sIIIIHH', sig.encode(), len(raw), flags, fid, 0, 44, 0) + raw


def mgef_data(flags, archetype, *, base_cost=0.0, skill=-1, resist=-1, actor_value=-1,
              casting=1, delivery=0, skill_usage=0.0, sound_level=2,
              casting_light=0, hit_shader=0, enchant_shader=0, projectile=0, explosion=0,
              casting_art=0, hit_effect_art=0, impact_data=0, enchant_art=0,
              hit_visuals=0, enchant_visuals=0):
    """MGEF DATA（152 位元組）。位移逐欄數自 vendor/wbDefinitionsTES5.pas 的 wbMGEFData：
    24 Casting Light、32 Hit Shader、36 Enchant Shader、72 Projectile、76 Explosion、
    92 Casting Art、96 Hit Effect Art、100 Impact Data、116 Enchant Art、
    120 Hit Visuals、124 Enchant Visuals。特效前線只寫這些欄，其餘位元不動。"""
    data = bytearray(152)
    struct.pack_into('<I', data, 0, flags)
    struct.pack_into('<f', data, 4, base_cost)
    struct.pack_into('<i', data, 12, skill)
    struct.pack_into('<i', data, 16, resist)
    struct.pack_into('<I', data, 24, casting_light)
    struct.pack_into('<I', data, 32, hit_shader)
    struct.pack_into('<I', data, 36, enchant_shader)
    struct.pack_into('<I', data, 64, archetype)
    struct.pack_into('<i', data, 68, actor_value)
    struct.pack_into('<I', data, 72, projectile)
    struct.pack_into('<I', data, 76, explosion)
    struct.pack_into('<I', data, 80, casting)
    struct.pack_into('<I', data, 84, delivery)
    struct.pack_into('<i', data, 88, -1)
    struct.pack_into('<I', data, 92, casting_art)
    struct.pack_into('<I', data, 96, hit_effect_art)
    struct.pack_into('<I', data, 100, impact_data)
    struct.pack_into('<f', data, 104, skill_usage)
    struct.pack_into('<I', data, 116, enchant_art)
    struct.pack_into('<I', data, 120, hit_visuals)
    struct.pack_into('<I', data, 124, enchant_visuals)
    struct.pack_into('<I', data, 140, sound_level)
    return bytes(data)


def sndd(pairs):
    """MGEF 的聲音陣列：一個 SNDD 子記錄裝 (型別, SNDR FormID) 對，與原版同格式
    （掃本機 Skyrim.esm 的 950 筆 MGEF 全部都是這個排法）。"""
    return b''.join(I(kind) + I(fid) for kind, fid in pairs if fid)


# CTDA（32 位元組）：型別旗標、比較值、函式代碼、兩個參數、Run On、參照、參數 3。
# 型別高 3 位是運算子：0 等於、1 不等於、2 大於、3 大於等於、4 小於、5 小於等於。
CTDA_GE = 0x60
CTDA_EQ = 0x00
CTDA_LT = 0x80
FUNC_GET_RANDOM_PERCENT = 77
FUNC_GET_GLOBAL_VALUE = 74
FUNC_HAS_PERK = 448


def ctda(op, value, function, param1=0, param2=0, run_on=0, reference=0):
    return struct.pack('<B3sfHHiiIIi', op, b'\0\0\0', value, function, 0,
                       param1, param2, run_on, reference, -1)


def perk_data(num_ranks=1, level=0, trait=0, playable=1, hidden=0):
    return bytes([trait, level, num_ranks, playable, hidden])


# ------------------------------------------------------------ PERK 進入點（樣式 C）
# 索引全部是從本機 Skyrim.esm 掃出來的實測值，不是憑記憶：
#   0x23 Armsman00／Barbarian00（武器傷害 ×1.2）           → 武器傷害倍率
#   0x24 DeftMovement／MQBladesDragonInfusion              → 受到的傷害倍率
#   0x25 Skullcrusher30（×0.75 = 無視 25% 護甲）           → 目標護甲倍率
#   0x1b ChampionsStance／FightingStance（×0.75）          → 重擊耐力消耗倍率
# 條件分頁（PRKC）：0 = 天賦擁有者，1 = 對手（攻擊者或被攻擊者）。
# 函式：74 GetGlobalValue、448 HasPerk、693 HasMagicEffectKeyword（AugmentedFlames60 用同一個）。
EP_ATTACK_DAMAGE = 0x23
EP_INCOMING_DAMAGE = 0x24
EP_TARGET_ARMOR = 0x25
EP_POWER_ATTACK_STAMINA = 0x1B
# round 2 新增，同樣是掃本機 Skyrim.esm 對出來的：
#   0x21 TowerOfStrength（EPFD 0.5＝被擊退幅度減半）／MQGreybeardsFus（0.75）→ 受到的擊退幅度
#   0x29 ElementalProtection（0.5，分頁 1 條件是 MagicDamageFire/Frost/Shock 三個關鍵字）
#        ／InvulnerableActorZeroIncomingDamage（0.0）                      → 受到的法術強度
EP_INCOMING_STAGGER = 0x21
EP_INCOMING_SPELL = 0x29
EPF_MULT = 3
FUNC_HAS_MAGIC_EFFECT_KEYWORD = 699


GUARD_WINDOWS = ['GuardSwitch', 'GuardBurst', 'GuardIce', 'GuardWind', 'GuardDivine', 'CloakGuard', 'GuardDark', 'GuardAstral', 'GuardStar']
ID_GUARD_WINDOW = 0x005170
GUARD_WINDOW_EDIDS = {f'ESSB_{kind}_{name}' for name in GUARD_WINDOWS for kind in ('WindowEffect', 'WindowSpell')}

def guard_window(index):
    # HasMagicEffect (214) is evaluated by the engine at the PERK read.
    return ctda(CTDA_EQ, 1.0, 214, param1=own(ID_GUARD_WINDOW + index * 2))


def gv_ge(fid, value):
    """GetGlobalValue(fid) >= value"""
    return ctda(CTDA_GE, float(value), FUNC_GET_GLOBAL_VALUE, param1=own(fid))


def gv_eq(fid, value):
    return ctda(CTDA_EQ, float(value), FUNC_GET_GLOBAL_VALUE, param1=own(fid))


def mech(index):
    """round 1 的鏡射全域變數（0x005000 段）。"""
    return ID_MECH_GLOB + index


def mech2(index):
    """round 2 的鏡射全域變數（0x0050C0 段）。"""
    return ID_MECH2_GLOB + index


def mech3(index):
    """round 3 的鏡射全域變數（0x005100 段）。"""
    return ID_MECH3_GLOB + index


def no_next_rank(fid):
    """只有鏈上最高的那一階生效（原版 Armsman00 → Armsman20 的做法）。"""
    return ctda(CTDA_EQ, 0.0, FUNC_HAS_PERK, param1=own(fid))


def entry(entry_point, value, conditions, tabs=3, function=EPF_MULT, epft=1):
    """conditions: [(tab, ctda bytes), ...]，tab 必須遞增。"""
    ss = [('PRKE', bytes([2, 0, 0])), ('DATA', bytes([entry_point, function, tabs]))]
    current = -1
    for tab, cond in conditions:
        if tab != current:
            ss.append(('PRKC', bytes([tab])))
            current = tab
        ss.append(('CTDA', cond))
    ss.extend([('EPFT', bytes([epft])), ('EPFD', F(value) if epft == 1 else I(value)), ('PRKF', b'')])
    return ss


# ---------------------------------------------------------------- v0.4 節點的 PERK 進入點（以 v0.4 名稱為鍵）
# round 21：鍵是 (樹, v0.4 節點名稱)，由身分表（build/plan-tree-nodes.json）解析成格位，所以「格位換了意思」
# 不可能讓進入點悄悄留在別的節點上；build/fix21_identity.py 另外核對每個鍵的節點狀態（後續切片的節點不准有），
# 讀回檢查（fix19_native／本檔 main）則核對 ESP 裡帶進入點的 perk 剛好就是這些鍵解析出來的格。
# v0.3 的進入點（純武藝武器傷害、戰意、淬火、同調三段受傷、疾攻、不屈、熔身、浴火、霜膚、冰盾、冰晶、電盾、疾電、
# 飲血武器傷害、聖盾、水膜、水鏡、水體、影甲、影身、預知、星體、星光）在 v0.4 都退役或改版，一律不再產生。
ROCK_ARMOR_MAX_LAYERS = 13     # 岩甲上限：基礎 5、厚土 10，通用樹「每種元素狀態上限」最多再 +3
ROCK_ARMOR_DR_CAP = 0.6        # v0.4 5.6：岩甲的物理減傷合計上限 60%
ROCK_ARMOR_DR_PER_LAYER = 0.04  # v0.4 5.6：每層物理減傷 +4%（ESSB_P_BaseRules）
MOUNTAIN_DR_PER_LAYER = 0.05    # v0.4 5.6 山岳：同調三段時每層 +4% → +5%


def rock_armor_reduction(layers, per_layer):
    return min(per_layer * layers, ROCK_ARMOR_DR_CAP)


def mountain_entries():
    """山岳：同調三段時岩甲每層物理減傷 4% → 5%（合計上限 60%）。基礎 4%／層在 ESSB_P_BaseRules 上，
    這裡對每一個層數補上兩者的比值（進入點乘法疊加）；層數鏡射在 ESSB_RockArmor。"""
    out = []
    for layers in range(1, ROCK_ARMOR_MAX_LAYERS + 1):
        value = (1.0 - rock_armor_reduction(layers, MOUNTAIN_DR_PER_LAYER)) \
            / (1.0 - rock_armor_reduction(layers, ROCK_ARMOR_DR_PER_LAYER))
        out += entry(EP_INCOMING_DAMAGE, value, [(0, gv_eq(mech2(0), layers)), (0, gv_ge(mech(0), 3))])
    return out


def holy_weapon_entries(rank, gate):
    """5.9 持續新手主線「聖佑各階武器傷害與聖傷加成 +3%／點 × 階數」的武器那一份（聖傷那一份在 DLL）。聖佑階效果
    本身已給武器傷害 +10／20／30%（AttackDamageMult，build/fix22_records.py），這裡再乘
    (1 + 0.1t + 0.01·NodeScale·r·t) ÷ (1 + 0.1t)，讓兩者合起來是加法。條件：你身上有 DLL 的聖佑 t 階效果。
    ESP 讀不到 MCM 的節點倍率，取 settings.json 的預設（node_percent_scale）。"""
    import fix22_records as hit22
    scale = float(json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))['node_percent_scale'])
    out = []
    for tier in (1, 2, 3):
        base = 1.0 + hit22.HOLY_WEAPON[tier - 1]
        value = (base + 0.01 * scale * rank * tier) / base
        out += entry(EP_ATTACK_DAMAGE, value,
                     gate + [(0, ctda(CTDA_EQ, 1.0, 214, param1=own(hit22.effect_id(f'kHoly{tier}'))))])
    return out


# ---------------------------------------------------------------- round 23 (N4): the pools and the defences on you
# v0.4 5.1 法盾、5.8 護血、5.11 水幕: a PERK cuts the hit by the share BEFORE the engine takes health (physical: 0x24 受到的
# 傷害; spells: 0x29 受到的法術強度, only for a spell carrying MagicDamageFire / Frost / Shock -- the Spell tab, as vanilla
# ElementalProtection -- so heals and buffs cast on you are untouched); the DLL's hurt task reads the health it lost and
# charges the pool (native/include/Hurt.h ShareOf uses the same conditions). 聖佑 / 冰盾 physical reduction, 蓄能's
# bracing, 殘影 and 破護 read the DLL's effects and mirrors.
FUNC_GET_ACTOR_VALUE = 14
FUNC_HAS_MAGIC_EFFECT = 214
AV_MAGICKA = 25
CTDA_GT = 0x40
CTDA_OR = 0x01
SHIELD_SHARE, SHIELD_SHARE_OVERLOAD, SHIELD_SHARE_PER_POINT = 0.30, 0.45, 0.01
VEIL_SHARE, SHIELD_VEIL_SHARE, STILL_WATER = 0.20, 0.30, 0.15
GUARD_SHARE = 0.50
LINGER_SHARE = 0.30
HOLY_PHYSICAL = [0.05, 0.10, 0.15]        # R7: 聖佑 I／II／III 受到物理傷害 -5／-10／-15%
ICE_SHIELD_DR_PER_LAYER = 0.04            # 5.4: 冰盾每層物理減傷 +4%
ICE_SHIELD_MAX_LAYERS = 8                 # 冰鎧
BRACING_DR_PER_POINT = 0.01               # 5.6 蓄能（格擋）：每點物理減傷 +1%


def or_(cond):
    """This condition OR the next one (CTDA flag bit 0)."""
    return bytes([cond[0] | CTDA_OR]) + cond[1:]


def has_effect(fid, value=1.0):
    return ctda(CTDA_EQ, value, FUNC_HAS_MAGIC_EFFECT, param1=own(fid))


def magicka_above_zero():
    return ctda(CTDA_GT, 0.0, FUNC_GET_ACTOR_VALUE, param1=AV_MAGICKA)


def destructive_spell():
    """Spell tab (1): the incoming spell carries a destruction damage keyword (OR of the three)."""
    return [(1, or_(ctda(CTDA_EQ, 1.0, FUNC_HAS_MAGIC_EFFECT_KEYWORD, param1=ref('Skyrim.esm', FID_KW_DAMAGE_FIRE)))),
            (1, or_(ctda(CTDA_EQ, 1.0, FUNC_HAS_MAGIC_EFFECT_KEYWORD, param1=ref('Skyrim.esm', FID_KW_DAMAGE_FROST)))),
            (1, ctda(CTDA_EQ, 1.0, FUNC_HAS_MAGIC_EFFECT_KEYWORD, param1=ref('Skyrim.esm', FID_KW_DAMAGE_SHOCK)))]


def pool_entries(value, owner):
    """Both halves of a pool's cut: the physical entry and the destructive-spell entry, same owner conditions. The master
    switch gates them too (the DLL charges nothing while it is off, so the cut must stop with it)."""
    owner = [(0, gv_eq(ID_GLOB['ESSB_Enabled'], 1))] + owner
    return entry(EP_INCOMING_DAMAGE, value, owner) + entry(EP_INCOMING_SPELL, value, owner + destructive_spell(), tabs=2)


def no_form():
    return (0, gv_eq(ID_GLOB['ESSB_FormActive'], 0))


def in_form(element):
    return [(0, gv_eq(ID_GLOB['ESSB_FormActive'], 1)), (0, gv_eq(ID_GLOB['ESSB_CurrentElement'], element))]


def shield_owner():
    """法盾: no form, and magicka > 0 OR the overload pool is up."""
    return [no_form(), (0, or_(magicka_above_zero())), (0, has_effect(hit23.effect_id('kOverload')))]


def branch_perk_fid(tree_id, name):
    for tree in plan_trees.parse()['trees']:
        if tree['id'] != tree_id:
            continue
        for route in tree['routes']:
            for tier in route['tiers']:
                for branch in tier['branches']:
                    if branch['name'] == name:
                        node = (tree['index'] * 3 + route['index']) * 5 + tier['index']
                        return ID_BRANCH_PERK + node * plan_trees.MAX_BRANCH + branch['slot']
    raise KeyError((tree_id, name))


def shield_share_entries(rank, gate):
    """5.1 法盾分擔 main line: +1%／point on the share (30% -> 30 + r, overload 45% -> 45 + r); the base rule gives 0.70 /
    0.55, so each rank multiplies by the ratio (only the chain's top rank counts)."""
    share = SHIELD_SHARE_PER_POINT * rank
    plain = (1.0 - SHIELD_SHARE - share) / (1.0 - SHIELD_SHARE)
    over = (1.0 - SHIELD_SHARE_OVERLOAD - share) / (1.0 - SHIELD_SHARE_OVERLOAD)
    out = pool_entries(plain, gate + [no_form(), (0, magicka_above_zero()), (0, has_effect(hit23.effect_id('kOverload'), 0.0))])
    out += pool_entries(over, gate + [no_form(), (0, has_effect(hit23.effect_id('kOverload')))])
    return out


def still_water_entries():
    """5.11 止水: at sync stage 3 the veil's share +15% (水盾 30% -> 45%, else 20% -> 35%)."""
    veil = in_form(9) + [(0, magicka_above_zero()), (0, gv_ge(mech(0), 3))]
    shield = branch_perk_fid('water', '水盾')
    out = pool_entries((1.0 - SHIELD_VEIL_SHARE - STILL_WATER) / (1.0 - SHIELD_VEIL_SHARE),
                       veil + [(0, ctda(CTDA_EQ, 1.0, FUNC_HAS_PERK, param1=own(shield)))])
    out += pool_entries((1.0 - VEIL_SHARE - STILL_WATER) / (1.0 - VEIL_SHARE),
                        veil + [(0, ctda(CTDA_EQ, 0.0, FUNC_HAS_PERK, param1=own(shield)))])
    return out


def bracing_entries():
    """5.6 蓄能 (block): the stored force becomes physical reduction +1%／point for 3 s (the DLL mirrors the points in
    ESSB_Bracing while its effect lasts)."""
    out = []
    for points in range(1, 11):
        out += entry(EP_INCOMING_DAMAGE, 1.0 - BRACING_DR_PER_POINT * points, [(0, gv_eq(hit23.global_id('ESSB_Bracing'), points))])
    return out


def n4_base_entries():
    """The base rules round 23 adds to ESSB_P_BaseRules (v0.4 5.1 法盾, 5.4 冰盾, 5.8 護血, 5.9 聖佑, 5.11 水幕)."""
    out = pool_entries(1.0 - SHIELD_SHARE, shield_owner())
    out += pool_entries((1.0 - SHIELD_SHARE_OVERLOAD) / (1.0 - SHIELD_SHARE),
                        [no_form(), (0, has_effect(hit23.effect_id('kOverload')))])
    out += pool_entries(1.0 - VEIL_SHARE, in_form(9) + [(0, magicka_above_zero())])
    out += pool_entries(1.0 - GUARD_SHARE, in_form(6) + [(0, has_effect(hit20.GUARD_EFFECT))])
    for tier in (1, 2, 3):
        out += entry(EP_INCOMING_DAMAGE, 1.0 - HOLY_PHYSICAL[tier - 1],
                     [(0, has_effect(hit22.effect_id(f'kHoly{tier}')))])
    for layers in range(1, ICE_SHIELD_MAX_LAYERS + 1):
        out += entry(EP_INCOMING_DAMAGE, 1.0 - ICE_SHIELD_DR_PER_LAYER * layers, [(0, gv_eq(mech(4), layers))])
    return out


MAIN_ENTRY_NODES = {
    # round 22：聖佑各階的武器傷害加成（主線每一階的 perk 各帶自己那一點的進入點，只有最高那一階生效）。
    ('divine', '聖佑各階武器傷害與聖傷加成'): holy_weapon_entries,
    # round 23：5.1 法盾分擔 +1%／點（未開形態時的法盾）。
    ('noform', '法盾分擔'): shield_share_entries,
}

BRANCH_ENTRY_NODES = {
    # 5.2 順轉：切換後 1 秒受傷 -50%（ESSB_GuardSwitch 視窗）。
    ('common', '順轉'): lambda: entry(EP_INCOMING_DAMAGE, 0.5, [(0, guard_window(0))]),
    # 5.2 安全閥：融斷時你受傷 -50% 持續 2 秒（ESSB_GuardBurst 視窗）。
    ('common', '安全閥'): lambda: entry(EP_INCOMING_DAMAGE, 0.5, [(0, guard_window(1))]),
    # 5.2 不移：同調二段以上時免疫硬直（0x21 受到的擊退幅度 ×0，條件 ESSB_SyncStage ≥2）。
    ('common', '不移'): lambda: entry(EP_INCOMING_STAGGER, 0.0, [(0, gv_ge(mech(0), 2))], tabs=2),
    # 5.6 不動：岩甲 ≥5 時免疫擊退（0x21 ×0）。
    ('earth', '不動'): lambda: entry(EP_INCOMING_STAGGER, 0.0, [(0, gv_ge(mech2(0), 5))], tabs=2),
    # 5.6 山岳：同調三段時岩甲每層物理減傷 +5%。
    ('earth', '山岳'): mountain_entries,
    # 5.7 殘影：風勢滿時被近戰命中 30% 機率讓下一次攻擊無效。round 23：擲骰在 DLL 受擊（Hurt.h），命中就掛 2 秒的
    # ESSB_N4_AfterimageEffect；有它時受傷 ×0，下一次受擊時 DLL 把它拿掉。
    ('wind', '殘影'): lambda: entry(EP_INCOMING_DAMAGE, 0.0, [(0, has_effect(hit23.effect_id('kAfterimage')))]),
    # 5.1 破護：不受元素披風反傷。round 23：DLL 受擊認出披風那一跳（法術、沒有投射物、攻擊者帶 MagicCloak），掛 2 秒的
    # ESSB_N4_CloakGuardEffect，每一跳刷新；有它時受到的法術強度 ×0。
    ('noform', '破護'): lambda: entry(EP_INCOMING_SPELL, 0.0, [no_form(), (0, has_effect(hit23.effect_id('kCloakGuard')))], tabs=2),
    # round 23 -- 5.1 餘魔：法盾把魔力扣到 0 的那一刻不中斷，再以 30% 分擔 2 秒（改扣耐力）：DLL 掛的視窗效果在、魔力為 0、
    # 沒有超載時照樣切 30%（有魔力或超載時是法盾本身那一條）。
    ('noform', '餘魔'): lambda: pool_entries(1.0 - LINGER_SHARE, [
        no_form(), (0, has_effect(hit23.effect_id('kLingerShield'))),
        (0, ctda(CTDA_EQ, 0.0, FUNC_GET_ACTOR_VALUE, param1=AV_MAGICKA)), (0, has_effect(hit23.effect_id('kOverload'), 0.0))]),
    # round 23 -- 5.11 水盾：水幕的分擔 20% → 30%（基礎規則給 0.8，這裡再乘 0.7／0.8）；止水：同調三段再 +15%。
    ('water', '水盾'): lambda: pool_entries((1.0 - SHIELD_VEIL_SHARE) / (1.0 - VEIL_SHARE), in_form(9) + [(0, magicka_above_zero())]),
    ('water', '止水'): still_water_entries,
    # round 23 -- 5.6 蓄能：格擋把滿的蓄勁換成每點物理減傷 +1%、3 秒（DLL 鏡射在 ESSB_Bracing）。
    ('earth', '蓄能'): bracing_entries,
    # 5.9 神佑：留 1 血之後 2 秒受傷 ×0。
    ('divine', '神佑'): lambda: entry(EP_INCOMING_DAMAGE, 0.0, [(0, guard_window(4))]),
    # 5.9 聖域／神聖領域：其中敵人傷害 -20%（＝你在聖域內受傷 -20%），共用 ESSB_DomainDivine。
    ('divine', '聖域'): lambda: entry(EP_INCOMING_DAMAGE, 0.8, [(0, gv_ge(mech2(8), 1))]),
    ('divine', '神聖領域'): lambda: entry(EP_INCOMING_DAMAGE, 0.8, [(0, gv_ge(mech2(8), 1))]),
    # round 22 (N3) -- 5.9 聖盾：聖佑各階另給受法術傷害 -10%／-20%／-30%（受到的法術強度 ×0.9／0.8／0.7，條件是你身上的
    # 聖佑階效果，DLL 掛的 ESSB_N3_Holy<n>Effect）。
    ('divine', '聖盾'): lambda: sum((entry(EP_INCOMING_SPELL, 1.0 - 0.1 * tier,
                                          [(0, ctda(CTDA_EQ, 1.0, 214, param1=own(hit22.effect_id(f'kHoly{tier}'))))], tabs=2)
                                    for tier in (1, 2, 3)), []),
    # round 22 (N3) -- 5.7 御風：失衡目標受你所有傷害 +30%「含武器傷害」：武器那一份是這個進入點（武器傷害 ×1.3，
    # 條件：對手身上有 DLL 的失衡效果）；附傷與反應那一份在 DLL／Papyrus。v0.4 第 1091 行：只有「免疫減速」看同調三段
    # （審查修正：原本這裡也要同調三段）。
    ('wind', '御風'): lambda: entry(EP_ATTACK_DAMAGE, 1.3, [(2, ctda(CTDA_EQ, 1.0, 214, param1=own(hit22.effect_id('kUnbalance'))))]),
    # round 23 (N4) -- 5.7 空中追擊：浮空目標受你的所有傷害 ×1.5「含武器傷害」：武器那一份是這個進入點（條件：目標身上有
    # DLL 的浮空效果 ESSB_N3_AirborneEffect）；附傷與反應那一份在 DLL（Status.h ReactionVulnerability／ProcTerms）。
    ('wind', '空中追擊'): lambda: entry(EP_ATTACK_DAMAGE, 1.5, [(2, ctda(CTDA_EQ, 1.0, 214, param1=own(hit22.effect_id('kAirborne'))))]),
    # 審查修正（指揮官裁定 (c)）-- 5.12 幻影：開印後 3 秒目標對你的命中 30% 落空。受到的傷害 ×0，條件在攻擊者分頁：
    # 攻擊者帶 DLL 的幻影效果（ESSB_N3_PhantomEffect），且 GetRandomPercent < 30——條件每一擊各評估一次，所以每擊各擲一次。
    ('darkness', '幻影'): lambda: entry(EP_INCOMING_DAMAGE, 0.0,
                                      [(1, ctda(CTDA_EQ, 1.0, 214, param1=own(hit22.effect_id('kPhantom')))),
                                       (1, ctda(CTDA_LT, 30.0, FUNC_GET_RANDOM_PERCENT))]),
}


def main_entries(tree_id, label, rank, base):
    """v0.4 主線第 rank 階（1 起算）要加的進入點（見 MAIN_ENTRY_NODES）。"""
    build = MAIN_ENTRY_NODES.get((tree_id, label))
    if build is None:
        return []
    gate = [(0, no_next_rank(base + rank))] if rank < plan_trees.MAIN_MAX_RANK else []
    return build(rank, gate)


def branch_entries(tree_id, name):
    build = BRANCH_ENTRY_NODES.get((tree_id, name))
    return build() if build else []


def v03_branch_entries_retired(tree_id, route, tier, index):
    """v0.3 的分支進入點（只留作歷史：round 21 起不再產生；build/fix21_verify.py 用它證明它們都不見了）。"""
    key = (tree_id, route, tier, index)
    if key == ('noform', 0, 1, 1):
        # 疾攻：連續命中每次重擊耐力消耗 -10%，最多 -50%。
        out = []
        for level in range(1, 6):
            out += entry(EP_POWER_ATTACK_STAMINA, 0.9,
                         [(0, gv_eq(ID_GLOB['ESSB_FormActive'], 0)),
                          (0, gv_ge(ID_MECH_GLOB + 16, level))], tabs=2)
        return out
    if key == ('noform', 0, 3, 1):
        # 不屈：戰意 ≥3 時受傷 -10%。
        return entry(EP_INCOMING_DAMAGE, 0.9,
                     [(0, gv_eq(ID_GLOB['ESSB_FormActive'], 0)), (0, gv_ge(ID_MECH_GLOB + 1, 3))])
    if key == ('common', 1, 1, 0):
        # 順轉：切換後 1 秒受傷 -50%。
        return entry(EP_INCOMING_DAMAGE, 0.5, [(0, guard_window(0))])
    if key == ('common', 2, 3, 1):
        # 安全閥：融斷時你受傷 -50% 持續 2 秒。
        return entry(EP_INCOMING_DAMAGE, 0.5, [(0, guard_window(1))])
    if key == ('fire', 0, 2, 1):
        # 熔身：受傷 -20%。
        return entry(EP_INCOMING_DAMAGE, 0.8, [(0, gv_ge(ID_MECH_GLOB + 5, 1))])
    if key == ('fire', 0, 4, 0):
        # 浴火：同調三段時帶熱度（＝帶火印記）目標對你的傷害 -30%。
        # 分頁 1 是對手，條件是攻擊者身上有本模組的火印記效果。
        return entry(EP_INCOMING_DAMAGE, 0.7, [
            (0, gv_ge(ID_MECH_GLOB + 0, 3)),
            (1, ctda(CTDA_EQ, 1.0, FUNC_HAS_MAGIC_EFFECT_KEYWORD, param1=own(ID_KW_MARK + 0))),
        ])
    if key == ('frost', 0, 1, 1):
        # 霜膚：冰形態受傷 -5%。
        return entry(EP_INCOMING_DAMAGE, 0.95, [
            (0, gv_eq(ID_GLOB['ESSB_FormActive'], 1)),
            (0, gv_eq(ID_GLOB['ESSB_CurrentElement'], 2)),
        ])
    if key == ('frost', 0, 3, 0):
        # 冰盾：有層數時抵消該次 30% 傷害。
        return entry(EP_INCOMING_DAMAGE, 0.7, [(0, gv_ge(ID_MECH_GLOB + 4, 1))])
    if key == ('frost', 1, 3, 1):
        # 冰晶：開印時你受傷 -10% 3 秒。
        return entry(EP_INCOMING_DAMAGE, 0.9, [(0, guard_window(2))])
    if key == ('lightning', 0, 3, 0):
        # 電盾：電荷 ≥5 時受傷 -15%。
        return entry(EP_INCOMING_DAMAGE, 0.85, [(0, gv_ge(ID_MECH_GLOB + 3, 5))])
    if key == ('lightning', 0, 3, 1):
        # 疾電：放電後 3 秒受傷 -15%。
        return entry(EP_INCOMING_DAMAGE, 0.85, [(0, gv_ge(ID_MECH_GLOB + 12, 1))])
    # ------------------------------------------------------------ round 2
    if key == ('earth', 0, 3, 0):
        # 不動：岩甲 ≥5 時免疫擊退。0x21 是「受到的擊退幅度」，×0 即免疫。
        return entry(EP_INCOMING_STAGGER, 0.0, [(0, gv_ge(mech2(0), 5))], tabs=2)
    if key == ('earth', 0, 4, 0):
        # 山岳：物理減傷每層 +1% → +3%。基礎的 1%／層在 ESSB_P_BaseRules 上，
        # 這裡再補 2%／層；進入點的值固定，所以一層一段條件（乘法疊加）。
        out = []
        for level in range(1, 6):
            out += entry(EP_INCOMING_DAMAGE, 0.98, [(0, gv_ge(mech2(0), level))])
        return out
    if key == ('wind', 0, 3, 0):
        # 殘影：風勢滿時被近戰命中 30% 機率無效化。擲骰在 ESSBGuard，命中就開一個
        # 受傷 ×0 的短視窗（ESSB_GuardWind），下一次受擊被抵消後由腳本關掉。
        return entry(EP_INCOMING_DAMAGE, 0.0, [(0, guard_window(3))])
    if key == ('blood', 0, 1, 0):
        # 飲血的「嗜血」10 秒：受傷不變，命中效果 +20% 在腳本；這裡只給引擎側的武器傷害 +10%。
        return entry(EP_ATTACK_DAMAGE, 1.1, [(0, gv_ge(mech2(3), 1))])
    if key == ('noform', 1, 3, 0):
        # 破護：不受元素披風反傷。ESSBGuard 認出「攻擊者身上有 MagicCloak 效果、來源是法術、
        # 沒有投射物」的那一跳，開一個 2 秒的「受到的法術強度 ×0」視窗，之後每一跳都刷新。
        return entry(EP_INCOMING_SPELL, 0.0, [(0, gv_eq(ID_GLOB['ESSB_FormActive'], 0)),
                                              (0, guard_window(5))], tabs=2)
    if key == ('divine', 0, 1, 1):
        # 聖盾：每命中 +1 層（最多 5），抵消魔法傷害。0x29 是「受到的法術強度」。
        out = []
        for level in range(1, 6):
            out += entry(EP_INCOMING_SPELL, 0.9, [(0, gv_ge(mech2(2), level))], tabs=2)
        return out
    if key == ('divine', 0, 4, 0):
        # 神佑：留 1 血之後 2 秒受傷 ×0，讓玩家有時間脫離。
        return entry(EP_INCOMING_DAMAGE, 0.0, [(0, guard_window(4))])
    if key == ('divine', 2, 2, 0):
        # 聖域：其中敵人傷害 -20%（＝你在聖域內受傷 -20%）。
        return entry(EP_INCOMING_DAMAGE, 0.8, [(0, gv_ge(mech2(8), 1))])
    if key == ('divine', 2, 4, 0):
        # 神聖領域：同上，只是 8 秒版本，共用同一個鏡射全域變數。
        return entry(EP_INCOMING_DAMAGE, 0.8, [(0, gv_ge(mech2(8), 1))])
    # ------------------------------------------------------------ round 3
    if key == ('water', 0, 1, 1):
        # 水膜：浸濕目標對你的傷害 -10%。0x24 的條件分頁 1 是攻擊者（決定 61），
        # 條件＝攻擊者身上帶本模組的水印記效果（同 round 1 的「浴火」）。
        return entry(EP_INCOMING_DAMAGE, 0.9, [
            (1, ctda(CTDA_EQ, 1.0, FUNC_HAS_MAGIC_EFFECT_KEYWORD, param1=own(ID_KW_MARK + 8))),
        ])
    if key == ('water', 0, 3, 0):
        # 水鏡：有層數時抵消該次 30% 傷害，被打由 ESSBGuard 消耗一層（同冰盾的做法）。
        return entry(EP_INCOMING_DAMAGE, 0.7, [(0, gv_ge(mech3(0), 1))])
    if key == ('water', 0, 4, 0):
        # 水體：同調三段的水形態受傷 -15%，且火傷減半（0x29 受到的法術強度，
        # 分頁 1 讀入射效果的 MagicDamageFire，同原版 ElementalProtection）。
        out = entry(EP_INCOMING_DAMAGE, 0.85, [
            (0, gv_ge(mech(0), 3)),
            (0, gv_eq(ID_GLOB['ESSB_FormActive'], 1)),
            (0, gv_eq(ID_GLOB['ESSB_CurrentElement'], 9)),
        ])
        out += entry(EP_INCOMING_SPELL, 0.5, [
            (0, gv_ge(mech(0), 3)),
            (0, gv_eq(ID_GLOB['ESSB_CurrentElement'], 9)),
            (1, ctda(CTDA_EQ, 1.0, FUNC_HAS_MAGIC_EFFECT_KEYWORD,
                     param1=ref('Skyrim.esm', FID_KW_DAMAGE_FIRE))),
        ], tabs=2)
        return out
    if key == ('darkness', 0, 1, 1):
        # 影甲：詛咒目標對你的傷害 -10%（分頁 1 判攻擊者帶本模組的暗印記）。
        return entry(EP_INCOMING_DAMAGE, 0.9, [
            (1, ctda(CTDA_EQ, 1.0, FUNC_HAS_MAGIC_EFFECT_KEYWORD, param1=own(ID_KW_MARK + 9))),
        ])
    if key == ('darkness', 0, 4, 0):
        # 影身：同調三段時被近戰命中 30% 機率無效。擲骰在 ESSBGuard，命中就開 2 秒
        # 受傷 ×0 的視窗（ESSB_GuardDark），下一次受擊被抵消後由腳本關掉（同風的殘影）。
        return entry(EP_INCOMING_DAMAGE, 0.0, [(0, guard_window(6))])
    if key == ('astral', 0, 3, 0):
        # 預知：星痕引爆前 1 秒你受傷 -20%（ESSBStatus 在引爆的前一秒開視窗）。
        return entry(EP_INCOMING_DAMAGE, 0.8, [(0, guard_window(7))])
    if key == ('astral', 0, 4, 0):
        # 星體：同調三段的星形態魔法傷害 -30%。
        return entry(EP_INCOMING_SPELL, 0.7, [
            (0, gv_ge(mech(0), 3)),
            (0, gv_eq(ID_GLOB['ESSB_FormActive'], 1)),
            (0, gv_eq(ID_GLOB['ESSB_CurrentElement'], 11)),
        ], tabs=2)
    if key == ('astral', 1, 3, 1):
        # 星光：開印時你受傷 -10% 3 秒。
        return entry(EP_INCOMING_DAMAGE, 0.9, [(0, guard_window(8))])
    return []


def base_rule_entries():
    """ESSB_P_BaseRules：不依賴投點的引擎側規則（規劃 1.1、2.3）。開局 AddPerk，永不移除。"""
    out = []
    # 規劃 1.1 血形態：重擊不消耗耐力，改扣生命（扣血在 ESSBController.PayBloodCost）。
    out += entry(EP_POWER_ATTACK_STAMINA, 0.0,
                 [(0, gv_eq(ID_GLOB['ESSB_FormActive'], 1)),
                  (0, gv_eq(ID_GLOB['ESSB_CurrentElement'], 6))], tabs=2)
    # v0.4 5.6 岩甲：每層物理減傷 +4%，合計上限 60%（v0.3 是每層 +1%）。每一個層數一段條件（== 層數），
    # 值直接是 1 − 4% × 層數，不再是每層乘一次。
    for layers in range(1, ROCK_ARMOR_MAX_LAYERS + 1):
        out += entry(EP_INCOMING_DAMAGE, 1.0 - rock_armor_reduction(layers, ROCK_ARMOR_DR_PER_LAYER),
                     [(0, gv_eq(mech2(0), layers))])
    # round 23 (N4)：法盾、水幕、護血的分擔，聖佑的物理減傷，冰盾每層物理減傷（見 n4_base_entries）。
    out += n4_base_entries()
    return out


def spit(spell_type, casting, delivery, perk=0):
    # Base cost 0 + flag 0x1 (Manual Cost Calc) 讓花費固定為 0。
    return struct.pack('<IIIfIIffI', 0, 1, spell_type, 0.0, casting, delivery, 0.0, 0.0, perk)


# ------------------------------------------------------------------ 特效素材複製（規劃 2.11）
def fx_selectors():
    """本前線要複製的全部素材選擇器。每一筆都寫成 "Plugin|EDID"，不用裸 EDID，
    因為 Darenii 各包共用 EDID（DAR_RedFXS 有三筆）會撞成 ambiguous。"""
    out = []
    for name in ELEMENTS:
        out += [f'{FX_PLUGIN}|ZZShader_{name}Form', f'{FX_PLUGIN}|ZZShader_{name}',
                f'{FX_PLUGIN}|ZZImpactSet_{name}', f'{FX_PLUGIN}|ZZExplosion_{name}Hand1',
                f'{FX_PLUGIN}|ZZArt_{name}', f'{FX_PLUGIN}|ZZArt_{name}Cloak']
        if name in FX_UPGRADED:
            out.append(f'{FX_PLUGIN}|ZZImpactSet_{name}Upgraded')
        for family in FX_SOUND_FAMILIES:
            out.append(f'{FX_PLUGIN}|ZZSoundDescriptor_{family}_{name}')
            out.append(f'{FX_PLUGIN}|ZZSound_{family}_{name}')
    for _name, aura, weapon, mark in FX_ELEMENT:
        out += [s for s in (aura, weapon, mark) if s]
    out += FX_SPARE + [FX_WHITE]
    seen, unique = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique


def fx_export(settings=None):
    """把選擇器複製成本模組自己的記錄。

    masters 維持 ['Skyrim.esm']；三種無法搬的參照各有一條處置：
      * EXPL 的 Object Effect（指向 Phenderix 的 ENCH）與 HAZD 的 Spell → unmapped='null'，
        寫 0。爆炸本身仍然播得出來，只是不帶附魔。
      * DrawSheathe 音效描述子的 CTDA（GetIsRace，參數在 Dawnguard.esm）→ 整條 CTDA 丟掉。
      * ZZImpactSet_Divine／Earth／Water 各有一對 PNAM 的材質在 Dragonborn.esm → 那一對丟掉。
    後兩者用 export(drop_subrecords=...)，在匯出路徑上處理，不動原始檔。
    """
    choices = fx_settings(settings or {})
    selectors = fx_selectors()  # Keep every legacy selection as a spare.
    legacy_keys = set(fx_extract.closure(selectors)['records'])
    pinned = {}
    for path in [WORK / '.codex/pre-fix3-snapshot/v03-formids.json', WORK / 'build/v03-formids.json']:
        if not path.is_file():
            continue
        for edid, entry in json.loads(path.read_text(encoding='utf-8'))['records'].items():
            fid = int(entry['id'], 16)
            if not ID_FX_BASE <= fid < ID_FX_LIMIT:
                continue
            if edid in pinned and pinned[edid] != fid:
                raise ValueError(f'FX identity changed: {edid}')
            pinned[edid] = fid
            source = entry.get('copied_from', '')
            if source and source.split('|')[0].casefold() != PLUGIN.casefold():
                plugin, local_id = source.split('|')
                source_key = plugin.casefold() + '|' + local_id.upper()
                if source_key not in legacy_keys:
                    selectors.append(source_key)
    generated = set(FX_MARK_DEFAULT.values()) | {FX_STATUS_WHITE, FX_STATUS_FROZEN}
    for mapping in choices.values():
        for selector in mapping.values():
            if selector.split('|')[0].casefold() == PLUGIN.casefold():
                if selector not in generated:
                    raise ValueError(f'Unknown local FX selector: {selector}')
            else:
                selectors.append(selector)
    selectors = list(dict.fromkeys(selectors))
    next_id = max(pinned.values(), default=ID_FX_BASE - 1) + 1
    allocated = {}

    def allocator(sig, key, edid):
        nonlocal next_id
        edid = fx_extract.PREFIX + edid
        if edid in allocated and allocated[edid] != key:
            raise ValueError(f'Copied EDID collision: {edid}')
        allocated[edid] = key
        fid = pinned.get(edid)
        if fid is None:
            fid = next_id
            next_id += 1
        if fid >= ID_FX_LIMIT:
            raise SystemExit(f'FX segment overflow at {edid}')
        return own(fid)

    records, shut, report = fx_extract.export(
        selectors, allocator, masters=MASTERS, unmapped='null', drop_subrecords=('CTDA', 'PNAM'))
    # FIX10: these are event cues (design 2.12), never sustained ambience.
    # LNAM byte 1: 0=None, 8=Loop, 16/32=Envelope (vendor xEdit definition).
    for entry in records:
        if entry['sig'] == 'SNDR' and any(entry['edid'].startswith('ESSBFX_ZZSoundDescriptor_' + family + '_')
                                        for family in ('FormActive', 'DrawSheathe')):
            entry['ss'] = [(tag, payload[:1] + b'\x00' + payload[2:] if tag == 'LNAM' else payload)
                           for tag, payload in entry['ss']]
    if shut['missing_selectors'] or shut['ambiguous_selectors']:
        raise ValueError(f'Invalid FX selectors: missing={shut["missing_selectors"]}, '
                         f'ambiguous={shut["ambiguous_selectors"]}')
    data = fx_extract.load()
    keys, _, _ = fx_extract.resolve(selectors, data)
    by_key = {entry['key']: entry for entry in records}
    index = {selector: by_key[key]['fid'] for selector, key in zip(selectors, keys)}
    by_fid = {e['fid']: e for e in records}
    candidates = [{'selector': f'{e["plugin"]}|{e["edid"].removeprefix(fx_extract.PREFIX)}',
                   'edid': e['edid'], **efsh_visibility(e['ss'])}
                  for e in records if e['sig'] == 'EFSH']
    template = by_fid[index[FX_EDGE_TEMPLATE]]
    derived = [(f'Mark_{n}', FX_EDGE_COLORS[n], False) for n in ELEMENTS]
    derived += [('Status_White', FX_WHITE, False),
                ('Status_Frozen', 'Icebloom.esl|_IP_FrostIceFormFXShader02', True)]
    for suffix, colour, frozen in derived:
        edid = fx_extract.PREFIX + suffix
        selector = f'{PLUGIN}|{edid}'
        fid = allocator('EFSH', selector, suffix)
        entry = fx_edge_record(template, by_fid[index[colour]], edid, fid, selector, frozen=frozen)
        records.append(entry)
        index[selector] = fid
        by_fid[fid] = entry
    for role, mapping in choices.items():
        for name, selector in mapping.items():
            entry = by_fid[index[selector]]
            if entry['sig'] != 'EFSH':
                raise ValueError(f'{role}.{name}: {selector} is {entry["sig"]}, expected EFSH')
            if role == 'fx_mark' and not efsh_visibility(entry['ss'])['persistent_edge_visible']:
                raise ValueError(f'{role}.{name}: {selector} has no proven persistent edge; '
                                 'see build/fx-visibility.json')
    for selector in (FX_STATUS_WHITE, FX_STATUS_FROZEN):
        assert efsh_visibility(by_fid[index[selector]]['ss'])['persistent_edge_visible']
    dump(WORK / 'build/fx-visibility.json', {
        'schema': 'vendor/wbDefinitionsTES5.pas:7043-7182',
        'float_offsets': EFSH_FLOATS, 'edge_color_offset': 56, 'flags_offset': 384,
        'short_DATA_policy': '312-byte records: flags absent, no inferred flags / edge guarantee',
        'candidates': candidates,
        'derived': [{'selector': f'{PLUGIN}|{e["edid"]}', 'id': f'{e["fid"] & 0xFFFFFF:06X}',
                     **e['derived_from'], **efsh_visibility(e['ss'])}
                    for e in records if 'derived_from' in e],
        'selected': {role: {n: {'selector': selector, **efsh_visibility(by_fid[index[selector]]['ss'])}
                           for n, selector in mapping.items()} for role, mapping in choices.items()},
    })
    return records, shut, report, index


def fx_pick(index, selector):
    """選擇器 → 複製後的 FormID；None 代表 2.11 這一格沒有可用來源。"""
    return index[selector] if selector else 0


def write_fx_bindings(records, shut, report, index, bindings):
    counts = collections.Counter(entry['sig'] for entry in records)
    dropped = [{'edid': e['edid'], 'subrecords': e['dropped']} for e in records if e['dropped']]
    nulled = [r for r in report if r.get('action') == 'null']
    dump(WORK / 'build/fx-bindings.json', {
        'front': 'fx-assets',
        'plan': '元素魔戰士規劃-v0.3.md 2.11／2.12',
        'source': 'build/fx-catalog.json（fx_extract.catalog）',
        'masters': MASTERS,
        'id_segment': f'0x{ID_FX_BASE:06X}-0x{ID_FX_LIMIT - 1:06X}',
        'edid_prefix': fx_extract.PREFIX,
        'assets_copied': False,
        'assets_note': 'nif／dds／wav 一律不複製；複製的記錄指向原模組既有的資源路徑，'
                       '原模組移除時只會少特效（規劃 2.11）',
        'totals': {
            'selectors': shut['selectors'],
            'records': len(records),
            'by_type': dict(sorted(counts.items())),
            'source_plugins': len({e['plugin'] for e in records}),
            'nulled_references': len(nulled),
            'dropped_subrecords': sum(len(d['subrecords']) for d in dropped),
            'external_skyrim_references': sum(1 for k in shut['external'] if k.startswith('skyrim.esm|')),
            'extra_masters_after_fixes': [],
        },
        'nulled': [{'edid': r.get('edid'), 'field': r['field'], 'to': r.get('to'),
                    'reason': r['reason']} for r in nulled],
        'dropped': dropped,
        'elements': bindings['elements'],
        'shared': bindings['shared'],
        'unbound_spares': bindings['spares'],
        'records': [{'edid': e['edid'], 'type': e['sig'], 'id': f'{e["fid"] & 0xFFFFFF:06X}',
                     'from': f'{e["plugin"]}|{e["source_id"]}',
                     **({'derived_from': e['derived_from']} if 'derived_from' in e else {})} for e in records],
    })
    return len(records), dict(sorted(counts.items()))


# ------------------------------------------------------------------ 節點索引交叉檢查
# ESSBNodes.Rank(ctl, 樹, 路線, 階) / Br(ctl, 樹, 路線, 階, 分支) 的索引寫錯不會編譯失敗，
# 只會讓節點永遠不生效。機制前線 round 3 用一次性腳本抓到一個真錯（毒樹傳奇分支 index 1
# 不存在），所以本前線把檢查收進建置期：任何超出範圍的樹／路線／階／分支都讓建置失敗。
NODE_CALL = re.compile(
    r'(?<![A-Za-z0-9_])(Rank|Br)\(\s*[A-Za-z_][A-Za-z0-9_]*\s*,\s*'
    r'(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d+)\s*)?\)')
MIN_NODE_CALLS = 300      # round 3 實測 386；掉到 300 以下代表正則失效，不是真的變少。


def check_node_calls(plan):
    shape = {}
    for tree in plan['trees']:
        for route in tree['routes']:
            for tier in route['tiers']:
                shape[(tree['index'], route['index'], tier['index'])] = len(tier['branches'])
    calls, errors = 0, []
    per_file = collections.Counter()
    for name in SCRIPTS:
        text = (WORK / 'src' / (name + '.psc')).read_text(encoding='utf-8')
        for match in NODE_CALL.finditer(text):
            kind, tree, route, tier, branch = match.group(1), *[int(g) if g else None
                                                               for g in match.groups()[1:]]
            calls += 1
            per_file[name] += 1
            line = text[:match.start()].count('\n') + 1
            where = f'{name}.psc:{line} {kind}({tree}, {route}, {tier}' \
                    + (f', {branch})' if branch is not None else ')')
            branches = shape.get((tree, route, tier))
            if branches is None:
                errors.append(f'{where} :: no such tree/route/tier')
            elif kind == 'Br' and (branch is None or branch >= branches):
                errors.append(f'{where} :: tier has {branches} branch(es)')
            elif kind == 'Rank' and branch is not None:
                errors.append(f'{where} :: Rank takes no branch index')
    if errors:
        raise SystemExit('node index cross-check failed:\n  ' + '\n  '.join(errors))
    if calls < MIN_NODE_CALLS:
        raise SystemExit(f'node index cross-check only matched {calls} calls '
                         f'(expected >= {MIN_NODE_CALLS}); the regex is probably broken')
    return calls, dict(per_file)


import fix18_records as hit18
import fix19_native as hit19
import fix20_records as hit20
import fix21_records as hit21
import fix21_identity
import fix22_records as hit22
import fix23_records as hit23
import tree_v04


def build_esp(plan):
    OUT.mkdir(parents=True, exist_ok=True)
    settings = json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))
    xp_per_hit = float(settings.get('xp_per_hit', 1.0))
    element_damage = settings['element_damage']
    if set(element_damage) != set(ELEMENTS):
        raise ValueError('element_damage must contain exactly the 11 elements')
    for name, limits in element_damage.items():
        if (not isinstance(limits, list) or len(limits) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float))
                       or not math.isfinite(v) or v < 0 for v in limits)
                or limits[0] > limits[1]):
            raise ValueError(f'Invalid element_damage range: {name}={limits}')
    for key in [key for _, key in ID_BALANCE_GLOB.values()] + ['upkeep_base_pct', 'upkeep_dark_pct', 'upkeep_level_relief', 'noform_base_true']:
        value = settings[key]
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            raise ValueError(f'Invalid nonnegative balance value: {key}={value}')
    if settings['upkeep_level_relief'] > 1.0:
        raise ValueError('upkeep_level_relief must be in [0, 1]')
    school_xp_mult = float(settings.get('school_xp_mult', 0.1))
    enabled_default = int(bool(settings.get('enabled', settings.get('melee_enabled', True))))
    debug_default = int(settings.get('debug_level', 0))

    # 規劃 2.13：現行天賦總成會檢查原本的施法天賦身分，不只看學派，所以沿用原版 Novice 天賦作半價天賦。
    base, _ = read_plugin(ROOT / 'SkyrimSE/Data/Skyrim.esm', {'PERK'})
    by_edid = {r.edid: r for r in base}
    school_names = {18: 'Alteration', 19: 'Conjuration', 20: 'Destruction', 21: 'Illusion', 22: 'Restoration'}
    casting_perks = {s: int(by_edid[n + 'Novice00'].key.split('|')[1], 16) for s, n in school_names.items()}

    rr = []
    manifest = {}
    used_ids = set()

    def add(sig, fid, edid, ss, flags=0):
        if edid in manifest:
            raise ValueError(f'duplicate EDID {edid}')
        if fid in used_ids:
            raise ValueError(f'duplicate FormID {fid:06X} for {edid}')
        used_ids.add(fid)
        rr.append((sig, record(sig, own(fid), [('EDID', Z(edid))] + ss, flags)))
        manifest[edid] = {'id': f'{fid:06X}', 'formid': f'{own(fid):08X}', 'type': sig}

    def add_exported(entry):
        """fx_extract.export 的一筆：EDID 已在 ss 裡、FormID 已是本插件的 32 位元值。"""
        fid = entry['fid'] & 0xFFFFFF
        if entry['edid'] in manifest:
            raise ValueError(f'duplicate EDID {entry["edid"]}')
        if fid in used_ids:
            raise ValueError(f'duplicate FormID {fid:06X} for {entry["edid"]}')
        used_ids.add(fid)
        rr.append((entry['sig'], record(entry['sig'], entry['fid'], entry['ss'])))
        manifest[entry['edid']] = {'id': f'{fid:06X}', 'formid': f'{entry["fid"]:08X}',
                                   'type': entry['sig'], 'copied_from': f'{entry["plugin"]}|{entry["source_id"]}'}

    # -------------------------------------------------------- 特效素材（規劃 2.11，0x003000 段）
    fx_choices = fx_settings(settings)
    fx_records, fx_closure, fx_report, fx = fx_export(settings)
    for entry in fx_records:
        add_exported(entry)

    def fxe(role, ix):
        """逐元素的 2.11 來源；第 2 欄（武器光）與第 4 欄（印記／命中）允許沒有來源。"""
        _name, aura, weapon, mark = FX_ELEMENT[ix]
        if role in ('aura', 'mark'):
            return fx[fx_choices['fx_' + role][ELEMENTS[ix]]]
        if role == 'weapon':
            return fx_pick(fx, weapon) or fx[f'{FX_PLUGIN}|ZZShader_{ELEMENTS[ix]}Form']
        # 命中／反應保持原本來源，大地仍退回 Phenderix ZZShader_Earth。
        return fx_pick(fx, mark) or fx[f'{FX_PLUGIN}|ZZShader_{ELEMENTS[ix]}']

    def fx_ph(name, ix):
        return fx[f'{FX_PLUGIN}|{name}_{ELEMENTS[ix]}']

    def fx_impact(ix, power=False):
        if power and ELEMENTS[ix] in FX_UPGRADED:
            return fx[f'{FX_PLUGIN}|ZZImpactSet_{ELEMENTS[ix]}Upgraded']
        return fx[f'{FX_PLUGIN}|ZZImpactSet_{ELEMENTS[ix]}']

    fx_white = fx[FX_WHITE]

    # -------------------------------------------------------------- GLOB
    add('GLOB', ID_GLOB['ESSB_Enabled'], 'ESSB_Enabled', [('FNAM', b's'), ('FLTV', F(enabled_default))])
    add('GLOB', ID_GLOB['ESSB_DebugLevel'], 'ESSB_DebugLevel', [('FNAM', b's'), ('FLTV', F(debug_default))])
    add('GLOB', ID_GLOB['ESSB_CurrentElement'], 'ESSB_CurrentElement', [('FNAM', b's'), ('FLTV', F(0))])
    add('GLOB', ID_GLOB['ESSB_FormActive'], 'ESSB_FormActive', [('FNAM', b's'), ('FLTV', F(0))])
    add('GLOB', ID_GLOB['ESSB_Sync'], 'ESSB_Sync', [('FNAM', b's'), ('FLTV', F(0))])
    add('GLOB', ID_GLOB['ESSB_SchoolXPMult'], 'ESSB_SchoolXPMult', [('FNAM', b'f'), ('FLTV', F(school_xp_mult))])
    for name, (fid, key) in ID_BALANCE_GLOB.items():
        add('GLOB', fid, name, [('FNAM', b'f'), ('FLTV', F(settings[key]))])
    add('GLOB', hit19.NATIVE_HIT, 'ESSB_NativeHit', [('FNAM', b's'), ('FLTV', F(0))], flags=0x40)
    add('GLOB', hit19.NATIVE_WANTED, 'ESSB_NativeWanted', [('FNAM', b's'), ('FLTV', F(1))])
    # 引擎前線：同調三段門檻（規劃 2.4 草案 5／15／30）與環境旗標（規劃 2.10）。
    for name, default in [('ESSB_SyncT1', 5), ('ESSB_SyncT2', 15), ('ESSB_SyncT3', 30),
                          ('ESSB_EnvWet', 0), ('ESSB_EnvStormy', 0), ('ESSB_EnvNight', 0)]:
        add('GLOB', ID_GLOB_ENGINE[name], name, [('FNAM', b's'), ('FLTV', F(default))])

    hit18.add_records(sys.modules[__name__], add, settings, casting_perks)
    hit20.add_records(sys.modules[__name__], add)
    hit21.add_records(sys.modules[__name__], add)
    hit22.add_records(sys.modules[__name__], add, fx, settings)   # round 22 (N3): the status layer's effects
    hit23.add_records(sys.modules[__name__], add)                 # round 23 (N4): your resources, windows, cooldowns

    # -------------------------------------------------------------- KYWD
    add('KYWD', ID_KW_PROC, 'ESSB_Proc', [])
    add('KYWD', ID_KW_TRUE, 'ESSB_TrueDamage', [])
    for ix, name in enumerate(ELEMENTS):
        add('KYWD', ID_KW_ELEMENT + ix, f'ESSB_Element_{name}', [])
    for ix, name in enumerate(ELEMENTS):
        add('KYWD', ID_KW_MARK + ix, f'ESSB_Mark_{name}', [])
    # 引擎前線自有關鍵字：狀態容器、已交戰標記（規劃 2.9）、反應傷害（不掛 ESSB_Proc 以免遞迴）。
    add('KYWD', ID_KW_STATUS, 'ESSB_StatusHost', [])
    add('KYWD', ID_KW_ENGAGED, 'ESSB_Engaged', [])
    add('KYWD', ID_KW_REACT, 'ESSB_React', [])

    # -------------------------------------------------------------- 設定層
    menu = [
        ('DESC', Z('元素樹＝目前形態的技能樹（沒開形態＝無元素樹）。\n通用樹＝全元素通用技能樹。\n設定、洗點與除錯請至 MCM「元素魔戰士」。')),
        ('INAM', I(0)), ('QNAM', I(0)), ('DNAM', I(1)),
    ]
    # 按鈕順序就是 ESSBSettingsEffect 的 choice 編號，改動時兩邊要一起改。
    # 設定與除錯已移至 MCM，能力只保留開樹與關閉。
    for label in ['元素樹', '通用樹', '關閉']:
        menu.append(('ITXT', Z(label)))
    add('MESG', ID_SETTINGS_MENU, 'ESSB_SettingsMenu', menu)
    add('MGEF', ID_SETTINGS_EFFECT, 'ESSB_SettingsEffect', [
        ('VMAD', vmad('ESSBSettingsEffect', {
            'SettingsMenu': (1, own(ID_SETTINGS_MENU)),
            'Enabled': (1, own(ID_GLOB['ESSB_Enabled'])),
            'DebugLevel': (1, own(ID_GLOB['ESSB_DebugLevel'])),
            'Controller': (1, own(ID_QUEST)),
        })),
        ('FULL', Z('元素魔戰士技能樹')),
        ('DATA', mgef_data(MGEF_UTILITY_FLAGS, 1, casting=1, delivery=0)),
    ])
    add('SPEL', ID_SETTINGS_POWER, 'ESSB_SettingsPower', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：技能樹')),
        ('ETYP', I(ref('Skyrim.esm', 0x25BEE))),
        ('DESC', Z('開啟目前元素或全元素通用技能樹。設定與除錯請至 MCM。')),
        ('SPIT', spit(3, 1, 0)),
        ('EFID', I(own(ID_SETTINGS_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 1)),
    ])

    # -------------------------------------------------------------- 形態力量（11 個 Lesser Power）
    for ix, name in enumerate(ELEMENTS):
        add('MGEF', ID_FORM_POWER_EFFECT + ix, f'ESSB_FormPowerEffect_{name}', [
            ('VMAD', vmad('ESSBFormPowerEffect', {
                'ElementIndex': (3, ix + 1),
                'Controller': (1, own(ID_QUEST)),
            })),
            ('FULL', Z(f'【魔戰士】{ZH[ix]}形態')),
            ('DATA', mgef_data(MGEF_UTILITY_FLAGS, 1, casting=1, delivery=0)),
        ])
        add('SPEL', ID_FORM_POWER_SPELL + ix, f'ESSB_FormPower_{name}', [
            ('OBND', bytes(12)), ('FULL', Z(f'【魔戰士】{ZH[ix]}形態')),
            ('ETYP', I(ref('Skyrim.esm', 0x25BEE))),
            ('DESC', Z(f'開啟或關閉{ZH[ix]}形態；已在其他形態時直接切換。')),
            ('SPIT', spit(3, 1, 0)),
            ('EFID', I(own(ID_FORM_POWER_EFFECT + ix))), ('EFIT', struct.pack('<fII', 0.0, 0, 1)),
        ])

    # ------------------------------------------------ 同調光暈（規劃 2.11，特效前線結清引擎覆蓋最後一條）
    # 一段石膚、二段鐵膚、三段黑檀膚的著色器強度遞增，三筆都在 Skyrim.esm 不必複製。
    # 常駐型的視覺就是 AbOnFire 的做法：Hit Shader ＝ Enchant Shader，旗標帶 FX Persist
    # （0x1000）＋ No Duration（0x200），沒有任何 Papyrus 參與。
    MGEF_GLOW_FLAGS = MGEF_UTILITY_FLAGS | 0x1000
    for stage, shader in enumerate(SYNC_GLOW_SHADERS, start=1):
        add('MGEF', ID_SYNC_GLOW_EFFECT + stage - 1, f'ESSB_SyncGlowEffect_{stage}', [
            ('FULL', Z(f'同調光暈 {stage} 段')),
            ('DATA', mgef_data(MGEF_GLOW_FLAGS, 1, casting=0, delivery=0,
                               hit_shader=ref('Skyrim.esm', shader),
                               enchant_shader=ref('Skyrim.esm', shader))),
            ('DNAM', Z(f'同調第 {stage} 段的光暈。')),
        ])
    # 三段時的武器發光：2.11 逐元素的第 2 欄（沒有來源的火退回 Phenderix 的形態著色器）。
    for ix, name in enumerate(ELEMENTS):
        add('MGEF', ID_SYNC_WEAPON_EFFECT + ix, f'ESSB_SyncWeaponEffect_{name}', [
            ('FULL', Z(f'同調武器光：{ZH[ix]}')),
            ('DATA', mgef_data(MGEF_GLOW_FLAGS, 1, casting=0, delivery=0,
                               hit_shader=fxe('weapon', ix), enchant_shader=fxe('weapon', ix))),
            ('DNAM', Z(f'同調三段：武器附上{ZH[ix]}之光。')),
        ])

    hit18.weapon_glows(sys.modules[__name__], add, fx_records, fxe)

    # -------------------------------------------------------------- 形態能力（常駐，帶元素關鍵字）
    # 形態光環掛在這 11 個能力上（settings.fx_aura，預設 Phenderix ZZShader_<X>Form）。
    # 同調三段的四個效果用「法術效果層的 CTDA」條件化：EFID／EFIT 後面跟 CTDA，
    # 條件是 GetGlobalValue(ESSB_SyncStage) >= 1／2／3，引擎自己評估，不必 Papyrus。
    sync_stage_global = mech(0)      # MECH_GLOBALS[0] 就是 ESSB_SyncStage（0–3）
    assert MECH_GLOBALS[0][0] == 'ESSB_SyncStage', MECH_GLOBALS[0]
    for ix, name in enumerate(ELEMENTS):
        kws = [own(ID_KW_ELEMENT + ix)]
        add('MGEF', ID_FORM_ABILITY_EFFECT + ix, f'ESSB_FormAbilityEffect_{name}', [
            ('FULL', Z(f'【魔戰士】{ZH[ix]}形態（效果）')),
            ('KSIZ', I(len(kws))), ('KWDA', b''.join(I(x) for x in kws)),
            ('DATA', mgef_data(MGEF_UTILITY_FLAGS | 0x1000, 1, casting=0, delivery=0,
                               hit_shader=0, enchant_shader=0)),
            ('DNAM', Z(f'{ZH[ix]}形態啟用中。')),
        ])
        glow = []
        for stage in range(3):
            glow += [('EFID', I(own(hit18.WEAPON_EFFECT + ix * 3 + stage))),
                     ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
                     ('CTDA', gv_ge(sync_stage_global, stage + 1 if stage else 0))]
            if stage < 2:
                glow.append(('CTDA', ctda(0x80, stage + 2, 74, sync_stage_global)))
        add('SPEL', ID_FORM_ABILITY_SPELL + ix, f'ESSB_FormAbility_{name}', [
            ('OBND', bytes(12)), ('FULL', Z(f'【魔戰士】{ZH[ix]}形態（效果）')),
            ('ETYP', I(ref('Skyrim.esm', 0x13F45))),
            ('DESC', Z(f'{ZH[ix]}形態啟用中。')),
            ('SPIT', spit(4, 0, 0)),
            ('EFID', I(own(ID_FORM_ABILITY_EFFECT + ix))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
        ] + glow)

    add('MGEF', ID_FORM_RULES_EFFECT, 'ESSB_FormRulesEffect', [
        ('VMAD', vmad('ESSBFormRules', {
            'UpkeepBasePct': (4, settings['upkeep_base_pct']),
            'UpkeepDarkPct': (4, settings['upkeep_dark_pct']),
            'UpkeepLevelRelief': (4, settings['upkeep_level_relief']),
            'FormActive': (1, own(ID_GLOB['ESSB_FormActive'])),
            'CurrentElement': (1, own(ID_GLOB['ESSB_CurrentElement'])),
            'Controller': (1, own(ID_QUEST)),
        })),
        ('FULL', Z('形態維持')),
        ('DATA', mgef_data(MGEF_UTILITY_FLAGS, 1, casting=0, delivery=0)),
    ])
    add('SPEL', ID_FORM_RULES_SPELL, 'ESSB_FormRulesAbility', [
        ('OBND', bytes(12)), ('FULL', Z('形態維持')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(4, 0, 0)),
        ('EFID', I(own(ID_FORM_RULES_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
    ])

    # -------------------------------------------------------------- 附傷（11 效果 × 普通/重擊法術）
    for ix, name in enumerate(ELEMENTS):
        kws = [own(ID_KW_PROC), own(ID_KW_ELEMENT + ix)]
        vanilla = VANILLA_ELEMENT_KEYWORD.get(ix)
        if vanilla is not None:
            kws.append(ref('Skyrim.esm', vanilla))
        # 規劃 2.12：每次命中的特效只靠附傷 MGEF 自帶的衝擊組 + 命中著色 + On Hit 音效，
        # 引擎播放、零腳本、不施放額外的視覺法術。重擊另走一顆 MGEF 換成 Upgraded 衝擊組。
        hit_power_ids = {}
        for power in (0, 1):
            if power and name not in FX_UPGRADED:
                continue
            fid = ID_HIT_POWER_EFFECT + FX_UPGRADED.index(name) if power else ID_HIT_EFFECT + ix
            edid = f'ESSB_HitEffect_{name}_Power' if power else f'ESSB_HitEffect_{name}'
            label = '重擊' if power else ''
            hit_power_ids[power] = fid
            add('MGEF', fid, edid, [
                ('FULL', Z(f'{ZH[ix]}附傷{label}')),
                ('KSIZ', I(len(kws))), ('KWDA', b''.join(I(x) for x in kws)),
                ('DATA', mgef_data(MGEF_HIT_FLAGS, 0, base_cost=1.0, skill=SCHOOLS[ix], resist=RESISTS[ix],
                                   actor_value=24, casting=1, delivery=1, skill_usage=school_xp_mult,
                                   hit_shader=fxe('hit', ix), impact_data=fx_impact(ix, bool(power)))),
                ('SNDD', sndd([(SND_ON_HIT, fx_ph('ZZSoundDescriptor_OnHit', ix))])),
                ('DNAM', Z(f'命中時造成 <mag> 點{ZH[ix]}傷害。')),
            ])
        for power in (0, 1):
            magnitude = sum(element_damage[name]) / 2.0 * (1.5 if power else 1.0)
            suffix = 'Power' if power else 'Normal'
            label = '重擊' if power else '普通'
            effect = hit_power_ids.get(power, ID_HIT_EFFECT + ix)
            # Round 20 (N2): the DLL casts this with a per-hit magnitude override, which the engine applies
            # to every effect of the spell. So the damage spell carries only the damage effect and the
            # magnitude-less engaged marker; lightning's magicka drain and blood's 血怒 bonus moved to
            # their own casts (fix20_records / the DLL's plan). The record magnitude is only a default.
            add('SPEL', ID_HIT_SPELL + ix * 2 + power, f'ESSB_Hit_{name}_{suffix}', [
                ('OBND', bytes(12)), ('FULL', Z(f'元素魔戰士：{ZH[ix]}附傷（{label}）')),
                ('KSIZ', I(1)), ('KWDA', I(own(ID_KW_PROC))),
                ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
                ('SPIT', spit(0, 1, 1, ref('Skyrim.esm', casting_perks[SCHOOLS[ix]]))),
                ('EFID', I(own(effect))), ('EFIT', struct.pack('<fII', magnitude, 0, 0)),
                ('EFID', I(own(ID_ENGAGED_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 30))])

    # -------------------------------------------------------------- 印記（規劃 2.2）
    # Script 原型、隱藏無傷。記錄 8 秒；round 22 起 DLL 以 effectiveness 把時長換成當下的印記秒數（水 10 秒、
    # 印記持續節點、MultDuration），No Magnitude 讓 effectiveness 只動時長（build/native-verification-2.md 決定 1）。
    # 空的 ESSBStub 讓引擎送出效果移除事件，DLL 以時長判定自然過期並結算過期終焉。
    for ix, name in enumerate(ELEMENTS):
        kws = [own(ID_KW_MARK + ix), own(ID_KW_ELEMENT + ix)]
        add('MGEF', ID_MARK_EFFECT + ix, f'ESSB_MarkEffect_{name}', [
            ('VMAD', vmad(hit22.STUB_SCRIPT, {})),
            ('FULL', Z(f'{ZH[ix]}印記')),
            ('KSIZ', I(len(kws))), ('KWDA', b''.join(I(x) for x in kws)),
            # 規劃 2.12「開印」：目標身上一次 ZZArt_<X> 閃現（Hit Effect Art）+ Charge_<X> 音效，
            # 加上印記期間持續的元素光（Hit Shader + FX Persist 0x1000，8／10 秒隨效果時長）。
            ('DATA', mgef_data(MGEF_MARK_FLAGS | 0x1000 | 0x00200000, 1, casting=1, delivery=1,
                               hit_shader=fxe('mark', ix), hit_effect_art=fx_ph('ZZArt', ix))),
            ('SNDD', sndd([(SND_CHARGE, fx_ph('ZZSoundDescriptor_Charge', ix))])),
            ('DNAM', Z(f'帶有{ZH[ix]}印記。')),
        ])
        add('SPEL', ID_MARK_SPELL + ix, f'ESSB_MarkSpell_{name}', [
            ('OBND', bytes(12)), ('FULL', Z(f'{ZH[ix]}印記')),
            ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
            ('SPIT', spit(0, 1, 1)),
            ('EFID', I(own(ID_MARK_EFFECT + ix))), ('EFIT', struct.pack('<fII', 0.0, 0, 8)),
        ])

    # -------------------------------------------------------------- 反應傷害（規劃 2.6、2.7）
    # 開印、終焉、融斷、流血、毒層、星痕、死咒的傷害全部走這 11 個法術：
    # 執行期 SetNthEffectMagnitude(0, dmg) 後 DoCombatSpellApply，不直接 DamageActorValue。
    for ix, name in enumerate(ELEMENTS):
        kws = [own(ID_KW_REACT), own(ID_KW_ELEMENT + ix)]
        vanilla = VANILLA_ELEMENT_KEYWORD.get(ix)
        if vanilla is not None:
            kws.append(ref('Skyrim.esm', vanilla))
        add('MGEF', ID_REACT_EFFECT + ix, f'ESSB_ReactEffect_{name}', [
            ('FULL', Z(f'{ZH[ix]}反應')),
            ('KSIZ', I(len(kws))), ('KWDA', b''.join(I(x) for x in kws)),
            # 反應只給 Hit Shader：這 11 顆同時承載 DoT、領域、毒層、星痕的每秒傷害，
            # 掛衝擊組或爆炸欄位會讓 DoT 每一跳都放一次（違反 2.12 的效能守則）。
            ('DATA', mgef_data(MGEF_REACT_FLAGS, 0, base_cost=1.0, skill=SCHOOLS[ix], resist=RESISTS[ix],
                               actor_value=24, casting=1, delivery=1, skill_usage=school_xp_mult,
                               hit_shader=fxe('hit', ix))),
            ('DNAM', Z(f'造成 <mag> 點{ZH[ix]}傷害。')),
        ])
        add('SPEL', ID_REACT_SPELL + ix, f'ESSB_React_{name}', [
            ('OBND', bytes(12)), ('FULL', Z(f'元素魔戰士：{ZH[ix]}反應')),
            ('KSIZ', I(1)), ('KWDA', I(own(ID_KW_REACT))),
            ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
            ('SPIT', spit(0, 1, 1, ref('Skyrim.esm', casting_perks[SCHOOLS[ix]]))),
            ('EFID', I(own(ID_REACT_EFFECT + ix))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
        ])

    # Overheat self damage has the same fire formula/FX but Self delivery.
    add('MGEF', 0x005156, 'ESSB_OverheatSelfEffect', [
        ('FULL', Z('過熱')),
        ('KSIZ', I(3)), ('KWDA', I(own(ID_KW_REACT)) + I(own(ID_KW_ELEMENT))
                                + I(ref('Skyrim.esm', VANILLA_ELEMENT_KEYWORD[0]))),
        ('DATA', mgef_data(MGEF_REACT_FLAGS, 0, base_cost=1.0, skill=SCHOOLS[0],
                           resist=RESISTS[0], actor_value=24, casting=1, delivery=0,
                           skill_usage=school_xp_mult, hit_shader=fxe('hit', 0))),
    ])
    add('SPEL', 0x005157, 'ESSB_OverheatSelfSpell', [
        ('OBND', bytes(12)), ('FULL', Z('過熱')),
        ('KSIZ', I(1)), ('KWDA', I(own(ID_KW_REACT))),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 0, ref('Skyrim.esm', casting_perks[SCHOOLS[0]]))),
        ('EFID', I(own(0x005156))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
    ])

    # -------------------------------------------------------------- 狀態容器（退役）與已交戰標記
    # Round 22：狀態容器（ESSBStatus）已刪除，這兩筆只為了讓 FormID 永不重用而留著：沒有腳本、沒有人施放。
    # 舊存檔身上殘留的實體在載入時沒有腳本可跑，30 秒內自然消失（裁定 R1：不做存檔遷移）。
    add('MGEF', ID_STATUS_EFFECT, 'ESSB_StatusHostEffect', [
        ('FULL', Z('元素狀態')),
        ('KSIZ', I(1)), ('KWDA', I(own(ID_KW_STATUS))),
        ('DATA', mgef_data(MGEF_MARKER_FLAGS | 0x00200000, 1, casting=1, delivery=1)),
    ])
    add('SPEL', ID_STATUS_SPELL, 'ESSB_StatusHostSpell', [
        ('OBND', bytes(12)), ('FULL', Z('元素狀態')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 1)),
        ('EFID', I(own(ID_STATUS_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 30)),
    ])
    add('MGEF', ID_ENGAGED_EFFECT, 'ESSB_EngagedEffect', [
        ('FULL', Z('已交戰')),
        ('KSIZ', I(1)), ('KWDA', I(own(ID_KW_ENGAGED))),
        ('DATA', mgef_data(MGEF_MARKER_FLAGS, 1, casting=1, delivery=1)),
    ])
    add('SPEL', ID_ENGAGED_SPELL, 'ESSB_EngagedSpell', [
        ('OBND', bytes(12)), ('FULL', Z('已交戰')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 1)),
        ('EFID', I(own(ID_ENGAGED_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 30)),
    ])

    # FIX16: native-duration markers; no Papyrus AME, no update polling.
    for index, name in enumerate(GUARD_WINDOWS):
        effect = ID_GUARD_WINDOW + index * 2
        add('MGEF', effect, f'ESSB_WindowEffect_{name}', [
            ('FULL', Z(name)), ('DATA', mgef_data(MGEF_MARKER_FLAGS, 1, casting=1, delivery=0)),
        ])
        add('SPEL', effect + 1, f'ESSB_WindowSpell_{name}', [
            ('OBND', bytes(12)), ('FULL', Z(name)),
            ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
            ('SPIT', spit(0, 1, 0)), ('EFID', I(own(effect))),
            ('EFIT', struct.pack('<fII', 0.0, 0, 2)),
        ])

    # -------------------------------------------------------------- 輔助效果（減速、碎甲、削魔耐、回復、放血）
    for ix, (suffix, label, av, timed, harmful, resist) in enumerate(UTILS):
        archetype = 0
        if timed and harmful:
            flags = MGEF_DEBUFF_FLAGS
            archetype = 34
        elif timed:
            flags = MGEF_BUFF_FLAGS
            archetype = 34
        elif harmful:
            flags = MGEF_REACT_FLAGS
        else:
            flags = MGEF_RESTORE_FLAGS
        if ix == 18:
            flags |= 0x200  # No Duration: rock layers own the ability lifetime.
        add('MGEF', util_effect_id(ix), f'ESSB_UtilEffect_{suffix}', [
            ('FULL', Z(f'元素魔戰士：{label}')),
            ('DATA', mgef_data(flags, archetype, base_cost=1.0, skill=-1, resist=resist, actor_value=av,
                               casting=0 if ix == 18 else 1, delivery=1 if harmful else 0)),
            ('DNAM', Z(f'{label} <mag>。')),
        ])
        add('SPEL', util_spell_id(ix), f'ESSB_Util_{suffix}', [
            ('OBND', bytes(12)), ('FULL', Z(f'元素魔戰士：{label}')),
            ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
            ('SPIT', spit(4 if ix == 18 else 0, 0 if ix == 18 else 1, 1 if harmful else 0)),
            ('EFID', I(own(util_effect_id(ix)))),
            ('EFIT', struct.pack('<fII', 0.0, 0, 5 if timed and ix != 18 else 0)),
        ])

    # fix round: player utilities are Self; these three also have ally Contact variants.
    for ix in (4, 6, 27):
        suffix, label, av, timed, harmful, resist = UTILS[ix]
        effect_id = 0x005150 + (4, 6, 27).index(ix) * 2
        add('MGEF', effect_id, f'ESSB_UtilTargetEffect_{suffix}', [
            ('FULL', Z(label)),
            ('DATA', mgef_data(MGEF_BUFF_FLAGS if timed else MGEF_RESTORE_FLAGS,
                               34 if timed else 0, base_cost=1.0, skill=-1, resist=resist,
                               actor_value=av, casting=1, delivery=1)),
        ])
        add('SPEL', effect_id + 1, f'ESSB_UtilTarget_{suffix}', [
            ('OBND', bytes(12)), ('FULL', Z(label)),
            ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
            ('SPIT', spit(0, 1, 1)), ('EFID', I(own(effect_id))),
            ('EFIT', struct.pack('<fII', 0.0, 0, 5 if timed else 0)),
        ])

    # ---------------------------------------------- 機制前線 round 1：狀態鏡射全域變數
    for ix, (name, default) in enumerate(MECH_GLOBALS):
        add('GLOB', ID_MECH_GLOB + ix, name, [('FNAM', b's'), ('FLTV', F(default))])

    # ---------------------------------------------- 真實傷害（規劃 2.8）
    # 不掛學派（skill = -1）、Resist Value = None（resist = -1），只掛 ESSB_TrueDamage。
    # 沒有任何外部天賦認得這個 keyword，所以不吃 M_ext；也不掛 ESSB_Proc，不會遞迴附傷。
    add('MGEF', ID_TRUE_EFFECT, 'ESSB_TrueEffect', [
        ('FULL', Z('真實傷害')),
        ('KSIZ', I(1)), ('KWDA', I(own(ID_KW_TRUE))),
        # 規劃 2.11 最後一列：真實／破魔用白光（Apocalypse 的 WB_FXS_White 不在載入順序裡，
        # 改用 Dark Hierophant 的 _BL_EffectShaderWhiteShockGlow，同一列點名的來源）。
        ('DATA', mgef_data(MGEF_TRUE_FLAGS, 0, base_cost=1.0, skill=-1, resist=-1, actor_value=24,
                           casting=1, delivery=1, hit_shader=fx_white)),
        ('DNAM', Z('造成 <mag> 點真實傷害，無視護甲與所有抗性。')),
    ])
    add('SPEL', ID_TRUE_SPELL, 'ESSB_TrueDamageSpell', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：真實傷害')),
        ('KSIZ', I(1)), ('KWDA', I(own(ID_KW_TRUE))),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 1)),
        ('EFID', I(own(ID_TRUE_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
    ])

    # ---------------------------------------------- 破魔印與沉默（規劃 2.3、5.1、8）
    add('KYWD', ID_KW_MANABREAK, 'ESSB_ManaBreak', [])
    add('KYWD', ID_KW_SILENCE, 'ESSB_Silence', [])
    add('MGEF', ID_MANABREAK_EFFECT, 'ESSB_ManaBreakEffect', [
        ('VMAD', vmad('ESSBCounter', {'Controller': (1, own(ID_QUEST))})),
        ('FULL', Z('破魔印')),
        ('KSIZ', I(1)), ('KWDA', I(own(ID_KW_MANABREAK))),
        ('DATA', mgef_data(MGEF_MARK_FLAGS | 0x1000, 1, casting=1, delivery=1,
                           hit_shader=fx[FX_STATUS_WHITE])),
        ('DNAM', Z('帶有破魔印。')),
    ])
    add('SPEL', ID_MANABREAK_SPELL, 'ESSB_ManaBreakSpell', [
        ('OBND', bytes(12)), ('FULL', Z('破魔印')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 1)),
        ('EFID', I(own(ID_MANABREAK_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 8)),
    ])
    # 沉默的兩個效果：腳本每秒把魔力扣到 0，加上 MagickaRateMult 的 -100 有害值修正。
    add('MGEF', ID_SILENCE_EFFECT, 'ESSB_SilenceEffect', [
        ('VMAD', vmad('ESSBSilence', {'Controller': (1, own(ID_QUEST))})),
        ('FULL', Z('沉默')),
        ('KSIZ', I(1)), ('KWDA', I(own(ID_KW_SILENCE))),
        ('DATA', mgef_data(MGEF_MARK_FLAGS | 0x1000, 1, casting=1, delivery=1,
                           hit_shader=fx[FX_STATUS_WHITE])),
        ('DNAM', Z('無法施法，且不回復魔力。')),
    ])
    add('SPEL', ID_SILENCE_SPELL, 'ESSB_SilenceSpell', [
        ('OBND', bytes(12)), ('FULL', Z('沉默')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 1)),
        ('EFID', I(own(ID_SILENCE_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 1)),
        ('EFID', I(own(util_effect_id(12)))), ('EFIT', struct.pack('<fII', 100.0, 0, 1)),
    ])

    # ---------------------------------------------- 自有常駐能力（抗咒、溫血、感應）
    for ix, (suffix, label, av, magnitude) in enumerate(ABILITIES):
        add('MGEF', ID_ABILITY_EFFECT + ix, f'ESSB_AbilityEffect_{suffix}', [
            ('FULL', Z(f'元素魔戰士：{label}')),
            ('DATA', mgef_data(MGEF_BUFF_FLAGS, 34, base_cost=0.0, skill=-1, resist=-1, actor_value=av,
                               casting=0, delivery=0)),
            ('DNAM', Z(f'{label} <mag>。')),
        ])
        add('SPEL', ID_ABILITY_SPELL + ix, f'ESSB_Ability_{suffix}', [
            ('OBND', bytes(12)), ('FULL', Z(f'元素魔戰士：{label}')),
            ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
            ('SPIT', spit(4, 0, 0)),
            ('EFID', I(own(ID_ABILITY_EFFECT + ix))), ('EFIT', struct.pack('<fII', magnitude, 0, 0)),
        ])

    # ---------------------------------------------- 機制前線 round 2
    for ix, (name, default) in enumerate(MECH2_GLOBALS):
        add('GLOB', ID_MECH2_GLOB + ix, name, [('FNAM', b's'), ('FLTV', F(default))])

    # 化灰（規劃 5.9、8）：DATA 照抄 PerkDisintegrateFFAimed，只把抗性改成 none。
    add('MGEF', ID_ASH_EFFECT, 'ESSB_AshEffect', [
        ('FULL', Z('化灰')),
        ('KSIZ', I(1)), ('KWDA', I(own(ID_KW_TRUE))),
        # 規劃 2.12 最後一列「化灰用原版既有」：崩解本身是原型＋旗標帶來的引擎行為，
        # 這裡只補 2.11 神聖列點名的化灰著色器（Holy Templar 的 _LIP_ConsecrateDeadFXSA）。
        ('DATA', mgef_data(MGEF_ASH_FLAGS, 0, base_cost=1.0, skill=20, resist=-1, actor_value=24,
                           casting=1, delivery=1, hit_shader=fxe('hit', 6))),
        ('DNAM', Z('神聖之力使屍體化為灰燼。')),
    ])
    add('SPEL', ID_ASH_SPELL, 'ESSB_AshSpell', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：化灰')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 1)),
        ('EFID', I(own(ID_ASH_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
    ])
    # 無聲（5.7 持續專精分支）：Muffle 1.0 + 移速 +20%，兩個效果都沿用既有的 MGEF。
    add('SPEL', ID_SILENT_SPELL, 'ESSB_SilentAbility', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：無聲')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(4, 0, 0)),
        ('EFID', I(own(ID_ABILITY_EFFECT + 4))), ('EFIT', struct.pack('<fII', 1.0, 0, 0)),
        # 能力是 Constant Effect，移速要用同為 Constant Effect 的「風行」MGEF（AV 30）；
        # 先前接的是 Fire and Forget 的疾行，施放類型不符會被引擎略過。
        ('EFID', I(own(ID_ABILITY_EFFECT + 3))), ('EFIT', struct.pack('<fII', 20.0, 0, 0)),
    ])
    # 血承（5.8 持續專精分支）：七個 Peak Value Modifier，magnitude 在施放前由腳本設定。
    inherit_effects = []
    for ix, (av, label) in enumerate(INHERIT_AVS):
        add('MGEF', ID_INHERIT_EFFECT + ix, f'ESSB_InheritEffect_{av}', [
            ('FULL', Z(f'血承：{label}')),
            ('DATA', mgef_data(MGEF_BUFF_FLAGS, 34, base_cost=0.0, skill=-1, resist=-1, actor_value=av,
                               casting=1, delivery=0)),
            ('DNAM', Z(f'{label} +<mag>。')),
        ])
        inherit_effects.append(('EFID', I(own(ID_INHERIT_EFFECT + ix))))
        inherit_effects.append(('EFIT', struct.pack('<fII', 0.0, 0, 15)))
    add('SPEL', ID_INHERIT_SPELL, 'ESSB_InheritSpell', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：血承')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 0)),
    ] + inherit_effects)

    # ---------------------------------------------- 機制前線 round 3
    for ix, (name, default) in enumerate(MECH3_GLOBALS):
        add('GLOB', ID_MECH3_GLOB + ix, name, [('FNAM', b's'), ('FLTV', F(default))])

    # 恐懼與瘋狂（規劃 5.12、6）：自有 Demoralize／Frenzy 效果，做法同原版幻術——
    # skill 21 讓幻術天賦照常加成，magnitude 就是可影響的最高等級（腳本在施放前設定），
    # 免疫判定（首領、龍、亡靈魔族）在 ESSBController.CanCharm。
    add('MGEF', ID_FEAR_EFFECT, 'ESSB_FearEffect', [
        ('VMAD', vmad(hit22.STUB_SCRIPT, {})),   # round 22：結束時 DLL 結算回魘（詛咒 +2）
        ('FULL', Z('元素魔戰士：恐懼')),
        ('KSIZ', I(2)), ('KWDA', I(ref('Skyrim.esm', FID_KW_INFLUENCE))
                                 + I(ref('Skyrim.esm', FID_KW_INFLUENCE_FEAR))),
        # 原版幻術的紫色調（2.12「復生、恐懼用原版既有」）：三欄都是掃 Skyrim.esm 的
        # InfluenceConfDownFFAimed 對出來的實測值，以 master 參照，不複製。
        ('DATA', mgef_data(MGEF_CHARM_FLAGS, MGEF_ARCH_DEMORALIZE, base_cost=1.0, skill=21,
                           resist=-1, actor_value=-1, casting=1, delivery=1,
                           hit_shader=ref('Skyrim.esm', FID_EFSH_FEAR),
                           hit_effect_art=ref('Skyrim.esm', FID_ARTO_ILLUSION_NEG),
                           impact_data=ref('Skyrim.esm', FID_IPDS_ILLUSION_NEG))),
        ('DNAM', Z('使 <mag> 級以下的目標逃跑 <dur> 秒。')),
    ])
    add('SPEL', ID_FEAR_SPELL, 'ESSB_FearSpell', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：恐懼')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 1)),
        ('EFID', I(own(ID_FEAR_EFFECT))), ('EFIT', struct.pack('<fII', 10.0, 0, 2)),
    ])
    add('MGEF', ID_FRENZY_EFFECT, 'ESSB_FrenzyEffect', [
        ('VMAD', vmad(hit22.STUB_SCRIPT, {})),   # round 22：結束時 DLL 結算回魘（詛咒 +2）
        ('FULL', Z('元素魔戰士：瘋狂')),
        ('KSIZ', I(2)), ('KWDA', I(ref('Skyrim.esm', FID_KW_INFLUENCE))
                                 + I(ref('Skyrim.esm', FID_KW_INFLUENCE_FRENZY))),
        ('DATA', mgef_data(MGEF_CHARM_FLAGS, MGEF_ARCH_FRENZY, base_cost=1.0, skill=21,
                           resist=-1, actor_value=-1, casting=1, delivery=1,
                           hit_shader=ref('Skyrim.esm', FID_EFSH_FRENZY),
                           hit_effect_art=ref('Skyrim.esm', FID_ARTO_ILLUSION_NEG),
                           impact_data=ref('Skyrim.esm', FID_IPDS_ILLUSION_NEG))),
        ('DNAM', Z('使 <mag> 級以下的目標攻擊最近的任何人 <dur> 秒。')),
    ])
    add('SPEL', ID_FRENZY_SPELL, 'ESSB_FrenzySpell', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：瘋狂')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 1)),
        ('EFID', I(own(ID_FRENZY_EFFECT))), ('EFIT', struct.pack('<fII', 10.0, 0, 3)),
    ])

    # 亡者歸來（規劃 5.12 的六階表 + 8）：DATA 照抄 ReanimateFFTargetActor0，
    # magnitude ＝ 等級上限、duration ＝ 該階秒數，兩者都由腳本在施放前設定。
    add('MGEF', ID_REANIMATE_EFFECT, 'ESSB_ReanimateEffect', [
        ('FULL', Z('元素魔戰士：亡者歸來')),
        ('KSIZ', I(1)), ('KWDA', I(ref('Skyrim.esm', FID_KW_SUMMON_UNDEAD))),
        # 規劃 2.12：復生用原版既有特效（ReanimateFXShader／ReanimateTargetFX／
        # MAGReanimatelImpactSet，全部掃 Skyrim.esm 對出來，以 master 參照）。
        ('DATA', mgef_data(MGEF_REANIMATE_FLAGS, MGEF_ARCH_REANIMATE, base_cost=1.0, skill=19,
                           resist=-1, actor_value=-1, casting=1, delivery=1,
                           hit_shader=ref('Skyrim.esm', FID_EFSH_REANIMATE),
                           hit_effect_art=ref('Skyrim.esm', FID_ARTO_REANIMATE),
                           impact_data=ref('Skyrim.esm', FID_IPDS_REANIMATE))),
        ('DNAM', Z('使 <mag> 級以下的屍體復生為你的僕從，持續 <dur> 秒。')),
    ])
    add('SPEL', ID_REANIMATE_SPELL, 'ESSB_ReanimateSpell', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：亡者歸來')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 1)),
        ('EFID', I(own(ID_REANIMATE_EFFECT))), ('EFIT', struct.pack('<fII', 6.0, 0, 120)),
    ])

    # 洗淨／淨化（規劃 5.11、8）：對自己的那一路**不再依賴** 原型 2 與旗標 0x100
    # （兩者在 round 3 都只是推論值，見實作紀錄決定 76）。SELF 路徑改成
    # 「安全建構」：法術裡只留治病（原型 3）與解毒（原型 29）這兩個實測原型，
    # 其餘的清除由 ESSBController.ApplyCleanse 逐項 DispelSpell（本模組自己的減益）
    # 加 PO3 GetActiveEffects／GetMagicEffectSource（敵對或有害旗標的外來效果）完成。
    # 這樣最壞情況是「少清幾個外來減益」，絕不會洗掉玩家自己的形態能力、血承或岩甲。
    # 兩顆限定關鍵字的 Dispel MGEF 保留在 ESP 裡（FormID 不動），但不掛進任何法術；
    # 進 CK 確認原型 2 與旗標 0x100 為真之後，重新掛回來即可。
    add('MGEF', ID_CLEANSE_EFFECT, 'ESSB_CleanseEffect', [
        ('FULL', Z('元素魔戰士：洗淨')),
        ('KSIZ', I(len(CLEANSE_KEYWORDS))),
        ('KWDA', b''.join(I(ref('Skyrim.esm', k)) for k in CLEANSE_KEYWORDS)),
        ('DATA', mgef_data(MGEF_DISPEL_KW_FLAGS, MGEF_ARCH_DISPEL, base_cost=1.0, skill=-1,
                           resist=-1, actor_value=-1, casting=1, delivery=0,
                           hit_shader=ref('Skyrim.esm', FID_EFSH_HEAL_MYSTIC))),
        ('DNAM', Z('清除自身的中毒、元素持續傷害與減速（保留備用，未掛進法術）。')),
    ])
    add('MGEF', ID_CUREDISEASE_EFFECT, 'ESSB_CureDiseaseEffect', [
        ('FULL', Z('元素魔戰士：治病')),
        ('DATA', mgef_data(MGEF_DISPEL_FLAGS, MGEF_ARCH_CURE_DISEASE, base_cost=1.0, skill=-1,
                           resist=-1, actor_value=-1, casting=1, delivery=0,
                           hit_shader=ref('Skyrim.esm', FID_EFSH_HEAL_MYSTIC),
                           hit_effect_art=ref('Skyrim.esm', FID_ARTO_HEAL_MYSTIC))),
        ('DNAM', Z('治好所有疾病。')),
    ])
    add('MGEF', ID_PURGE_EFFECT, 'ESSB_PurgeEffect', [
        ('FULL', Z('元素魔戰士：淨化')),
        ('KSIZ', I(len(PURGE_KEYWORDS))),
        ('KWDA', b''.join(I(ref('Skyrim.esm', k)) for k in PURGE_KEYWORDS)),
        ('DATA', mgef_data(MGEF_DISPEL_KW_FLAGS, MGEF_ARCH_DISPEL, base_cost=1.0, skill=-1,
                           resist=-1, actor_value=-1, casting=1, delivery=0,
                           hit_shader=ref('Skyrim.esm', FID_EFSH_HEAL_MYSTIC))),
        ('DNAM', Z('清除自身所有負面效果（保留備用，未掛進法術）。')),
    ])
    add('MGEF', ID_CUREPOISON_EFFECT, 'ESSB_CurePoisonEffect', [
        ('FULL', Z('元素魔戰士：解毒')),
        ('DATA', mgef_data(MGEF_DISPEL_FLAGS, MGEF_ARCH_CURE_POISON, base_cost=1.0, skill=-1,
                           resist=-1, actor_value=-1, casting=1, delivery=0,
                           hit_shader=ref('Skyrim.esm', FID_EFSH_HEAL_MYSTIC),
                           hit_effect_art=ref('Skyrim.esm', FID_ARTO_HEAL_MYSTIC))),
        ('DNAM', Z('解除所有中毒。')),
    ])
    add('SPEL', ID_CLEANSE_SPELL, 'ESSB_CleanseSpell', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：洗淨')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 0)),
        ('EFID', I(own(ID_CUREDISEASE_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
    ])
    add('SPEL', ID_PURGE_SPELL, 'ESSB_PurgeSpell', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：淨化')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 0)),
        ('EFID', I(own(ID_CUREDISEASE_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
        ('EFID', I(own(ID_CUREPOISON_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
    ])
    # 沖刷／洗滌（規劃 5.11、8）：對目標的 Dispel 原型，只影響有時限的法術效果，
    # 不動能力型常駐效果，所以不會洗掉別的模組掛在 NPC 身上的被動。
    # TARGET 路徑保留原型 2（它只可能打到敵人；ApplyStrip 另有「絕不對玩家施放」的守衛）。
    add('MGEF', ID_STRIP_EFFECT, 'ESSB_StripEffect', [
        ('FULL', Z('元素魔戰士：沖刷')),
        ('DATA', mgef_data(MGEF_DISPEL_FLAGS | 0x5, MGEF_ARCH_DISPEL, base_cost=1.0, skill=-1,
                           resist=-1, actor_value=-1, casting=1, delivery=1,
                           hit_shader=ref('Skyrim.esm', FID_EFSH_HEAL_MYSTIC))),
        ('DNAM', Z('驅散目標身上一個有時限的增益。')),
    ])
    add('SPEL', ID_STRIP_SPELL, 'ESSB_StripSpell', [
        ('OBND', bytes(12)), ('FULL', Z('元素魔戰士：沖刷')),
        ('ETYP', I(ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
        ('SPIT', spit(0, 1, 1)),
        ('EFID', I(own(ID_STRIP_EFFECT))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
    ])

    entry_count = 0

    # 基礎規則天賦：開局由 ESSBController.Setup 呼叫 AddPerk，永不移除。
    base_entries = base_rule_entries()
    entry_count += sum(1 for sig, _ in base_entries if sig == 'PRKE')
    add('PERK', ID_BASE_PERK, 'ESSB_P_BaseRules', [
        ('FULL', Z('元素魔戰士：基礎規則')),
        ('DESC', Z('血形態的重擊改扣生命；岩甲每層物理減傷 +4%（合計上限 60%）；法盾、水幕、護血分擔傷害；聖佑與冰盾的物理減傷。')),
        ('DATA', perk_data(playable=0, hidden=1)),
    ] + base_entries)

    # -------------------------------------------------------------- 技能樹層（規劃 3、3.1、5.1–5.13）
    # 每棵樹五個 CSF 全域變數（等級、進度比、點數、顏色、升級訊息旗標）加一個洗點冷卻時戳。
    for ix, tree in enumerate(TREES):
        add('GLOB', ID_TREE_GLOB['Lvl'] + ix, f'ESSB_Lvl_{tree}',
            [('FNAM', b's'), ('FLTV', F(1))])
        add('GLOB', ID_TREE_GLOB['Ratio'] + ix, f'ESSB_Ratio_{tree}',
            [('FNAM', b'f'), ('FLTV', F(0))])
        add('GLOB', ID_TREE_GLOB['Pts'] + ix, f'ESSB_Pts_{tree}',
            [('FNAM', b's'), ('FLTV', F(1))])
        add('GLOB', ID_TREE_GLOB['Color'] + ix, f'ESSB_Color_{tree}',
            [('FNAM', b'l'), ('FLTV', F(TREE_COLOR[ix]))])
        add('GLOB', ID_TREE_GLOB['ShowLvl'] + ix, f'ESSB_ShowLvl_{tree}',
            [('FNAM', b's'), ('FLTV', F(1))])
        # -10 天：新開的遊戲 GetCurrentGameTime() 從 0 起算，預設 0 會讓第一個遊戲日洗不了點。
        add('GLOB', ID_TREE_GLOB['Respec'] + ix, f'ESSB_Respec_{tree}',
            [('FNAM', b'f'), ('FLTV', F(-10))])
    add('GLOB', ID_SHOW_MENU, 'ESSB_ShowMenu', [('FNAM', b's'), ('FLTV', F(0))])  # 0: CSF sees non-zero as an open request; we open via the API
    add('GLOB', ID_XP_PER_HIT, 'ESSB_XPPerHit', [('FNAM', b'f'), ('FLTV', F(xp_per_hit))])

    # PERK：主線 15 階鏈（NNAM 串接）＋ 分支單一 perk（v0.4，round 21）。分支的格位（FormID、EditorID 尾碼）是
    # branch['slot']，跟 v0.4 表格的顯示順序 branch['order'] 分開（沿用 v0.3 的格、新節點放沒用過的格）；
    # v0.3 有、v0.4 移除的分支照樣產生記錄（同 EditorID／FormID）當退役 perk：不可購買、不進 CSF、沒有進入點。
    # 節點機制在 Papyrus／DLL，引擎側效果（樣式 C）以 v0.4 名稱查 MAIN_ENTRY_NODES／BRANCH_ENTRY_NODES。
    for tree in plan['trees']:
        t = tree['index']
        for route in tree['routes']:
            r = route['index']
            for tier in route['tiers']:
                k = tier['index']
                node = (t * 3 + r) * 5 + k
                # 規劃 3：樹等級到了該階才開放（新手 10／熟練 25／專精 50／大師 75／傳奇 100）。
                gate = ctda(CTDA_GE, float(tier['level']), FUNC_GET_GLOBAL_VALUE,
                            param1=own(ID_TREE_GLOB['Lvl'] + t))
                base = ID_MAIN_PERK + node * plan_trees.MAIN_MAX_RANK
                full = f"{route['name']}·{tier['name']} 主線"
                for rank in range(plan_trees.MAIN_MAX_RANK):
                    ss = [('FULL', Z(full)),
                          ('DESC', Z(f"第 {rank + 1}/{plan_trees.MAIN_MAX_RANK} 點：{tier['main']}")),
                          ('CTDA', gate),
                          ('DATA', perk_data())]
                    if rank + 1 < plan_trees.MAIN_MAX_RANK:
                        ss.append(('NNAM', I(own(base + rank + 1))))
                    # 樣式 C：引擎側效果掛在同一筆 PERK 上（PRKE/DATA/EPFT/EPFD/PRKC/CTDA）。
                    entries = main_entries(tree['id'], tier['main_label'], rank + 1, base)
                    entry_count += sum(1 for sig, _ in entries if sig == 'PRKE')
                    ss.extend(entries)
                    add('PERK', base + rank, f"ESSB_P_{tree['id']}_{r}_{k}_M{rank + 1}", ss)
                has_main = ('CTDA', ctda(CTDA_EQ, 1.0, FUNC_HAS_PERK, param1=own(base)))
                for branch in tier['branches']:
                    ss = [('FULL', Z(branch['name'])),
                          ('DESC', Z(branch['description'])),
                          ('CTDA', gate),
                          # 規劃 3：階內主線至少投 1 點，才能點該階分支。
                          has_main,
                          ('DATA', perk_data())]
                    entries = branch_entries(tree['id'], branch['name'])
                    entry_count += sum(1 for sig, _ in entries if sig == 'PRKE')
                    ss.extend(entries)
                    add('PERK', ID_BRANCH_PERK + node * plan_trees.MAX_BRANCH + branch['slot'],
                        f"ESSB_P_{tree['id']}_{r}_{k}_B{branch['slot'] + 1}", ss)
                for old in tier['retired']:
                    add('PERK', ID_BRANCH_PERK + node * plan_trees.MAX_BRANCH + old['slot'],
                        f"ESSB_P_{tree['id']}_{r}_{k}_B{old['slot'] + 1}", [
                            ('FULL', Z(f"{old['name']}（已退役）")),
                            ('DESC', Z(f"v0.3 的節點，v0.4 已移除：不在技能樹上、不能購買、沒有效果。"
                                       f"（v0.3：{old['description']}）")),
                            ('CTDA', gate), has_main,
                            ('DATA', perk_data(playable=0, hidden=1)),
                        ])

    # -------------------------------------------------------------- QUST
    props = {
        **{name.removeprefix('ESSB_'): (1, own(fid))
           for name, (fid, _) in ID_BALANCE_GLOB.items()},
        'ElementDamageMin': (14, [element_damage[name][0] for name in ELEMENTS]),
        'ElementDamageMax': (14, [element_damage[name][1] for name in ELEMENTS]),
        'Enabled': (1, own(ID_GLOB['ESSB_Enabled'])),
        'DebugLevel': (1, own(ID_GLOB['ESSB_DebugLevel'])),
        'CurrentElement': (1, own(ID_GLOB['ESSB_CurrentElement'])),
        'FormActive': (1, own(ID_GLOB['ESSB_FormActive'])),
        'Sync': (1, own(ID_GLOB['ESSB_Sync'])),
        'SchoolXPMult': (1, own(ID_GLOB['ESSB_SchoolXPMult'])),
        'SettingsPower': (1, own(ID_SETTINGS_POWER)),
        'FormRulesAbility': (1, own(ID_FORM_RULES_SPELL)),
        'FormPowers': (11, [own(ID_FORM_POWER_SPELL + n) for n in range(11)]),
        'FormAbilities': (11, [own(ID_FORM_ABILITY_SPELL + n) for n in range(11)]),
        'HitNormalSpells': (11, [own(ID_HIT_SPELL + n * 2) for n in range(11)]),
        'HitPowerSpells': (11, [own(ID_HIT_SPELL + n * 2 + 1) for n in range(11)]),
        'SyncT1': (1, own(ID_GLOB_ENGINE['ESSB_SyncT1'])),
        'SyncT2': (1, own(ID_GLOB_ENGINE['ESSB_SyncT2'])),
        'SyncT3': (1, own(ID_GLOB_ENGINE['ESSB_SyncT3'])),
        'EnvWet': (1, own(ID_GLOB_ENGINE['ESSB_EnvWet'])),
        'EnvStormy': (1, own(ID_GLOB_ENGINE['ESSB_EnvStormy'])),
        'EnvNight': (1, own(ID_GLOB_ENGINE['ESSB_EnvNight'])),
        'GameHour': (1, ref('Skyrim.esm', FID_GAME_HOUR)),
        'EngagedSpell': (1, own(ID_ENGAGED_SPELL)),
        'EngagedKeyword': (1, own(ID_KW_ENGAGED)),
        'UndeadKeyword': (1, ref('Skyrim.esm', FID_KW_UNDEAD)),
        'DaedraKeyword': (1, ref('Skyrim.esm', FID_KW_DAEDRA)),
        'ReactSpells': (11, [own(ID_REACT_SPELL + n) for n in range(11)]),
        'UtilTargetSpells': (11, [own(0x005151), own(0x005153), own(0x005155)]),
        'UtilSpells': (11, [own(util_spell_id(n)) for n in range(len(UTILS))]),
        'MarkKeywords': (11, [own(ID_KW_MARK + n) for n in range(11)]),
        # 技能樹腳本掛在同一個 Player 別名上（同別名的第二個腳本）。
        'Trees': (1, (own(ID_QUEST), 0)),
        # ---- 機制前線 round 1
        'OverheatSelfSpell': (1, own(0x005157)),
        'TrueSpell': (1, own(ID_TRUE_SPELL)),
        'ManaBreakSpell': (1, own(ID_MANABREAK_SPELL)),
        'SilenceSpell': (1, own(ID_SILENCE_SPELL)),
        'AntiMagicAbility': (1, own(ID_ABILITY_SPELL + 0)),
        'WarmBloodAbility': (1, own(ID_ABILITY_SPELL + 1)),
        'InductionAbility': (1, own(ID_ABILITY_SPELL + 2)),
        'SilenceKeyword': (1, own(ID_KW_SILENCE)),
        'ArmorSpellKeyword': (1, ref('Skyrim.esm', FID_KW_ARMOR_SPELL)),
        'CloakKeyword': (1, ref('Skyrim.esm', FID_KW_CLOAK)),
        # ---- 機制前線 round 2
        'BaseRulesPerk': (1, own(ID_BASE_PERK)),
        'AshSpell': (1, own(ID_ASH_SPELL)),
        'InheritSpell': (1, own(ID_INHERIT_SPELL)),
        'WindSpeedAbility': (1, own(ID_ABILITY_SPELL + 3)),
        'WindMuffleAbility': (1, own(ID_ABILITY_SPELL + 4)),
        'SilentAbility': (1, own(ID_SILENT_SPELL)),
        'DragonKeyword': (1, ref('Skyrim.esm', FID_KW_DRAGON)),
        'GiantRace': (1, ref('Skyrim.esm', FID_RACE_GIANT)),
        'MammothRace': (1, ref('Skyrim.esm', FID_RACE_MAMMOTH)),
        'NecroClass': (1, ref('Skyrim.esm', FID_CLASS_NECRO)),
        'NecroFaction': (1, ref('Skyrim.esm', FID_FACT_NECRO)),
        # ---- 機制前線 round 3
        'FearSpell': (1, own(ID_FEAR_SPELL)),
        'FrenzySpell': (1, own(ID_FRENZY_SPELL)),
        'FrenzyBladeSpell': (1, own(hit22.frenzy_blade_spell_id())),
        'VisionSpell': (1, own(hit22.vision_spell_id())),
        'ReanimateSpell': (1, own(ID_REANIMATE_SPELL)),
        'CleanseSpell': (1, own(ID_CLEANSE_SPELL)),
        'PurgeSpell': (1, own(ID_PURGE_SPELL)),
        'PoisonResistAbility': (1, own(ID_ABILITY_SPELL + 5)),
        'NoReanimateKeyword': (1, ref('Skyrim.esm', FID_KW_NO_REANIMATE)),
        'HarmfulKeyword': (1, ref('Skyrim.esm', FID_KW_ALCH_HARMFUL)),
        'TwinSoulsPerk': (1, ref('Skyrim.esm', FID_PERK_TWIN_SOULS)),
        # ---- 特效前線（規劃 2.11／2.12）
        # 洗淨／淨化的 SELF 路徑：要逐項 DispelSpell 的自有減益（安全建構，不靠 Dispel 原型）。
        'SelfCleanseSpells': (11, [own(util_spell_id(n)) for n in SELF_CLEANSE_UTILS]),
        # 融斷／終焉／領域的一次性爆炸（PlaceAtMe，每 0.5 秒最多 5 個，普通命中絕不放）。
        'FxExplosions': (11, [fx[f'{FX_PLUGIN}|ZZExplosion_{n}Hand1'] for n in ELEMENTS]),
        'FxSoundFormActive': (11, [fx[f'{FX_PLUGIN}|ZZSound_FormActive_{n}'] for n in ELEMENTS]),
        'FxSoundRelease': (11, [fx[f'{FX_PLUGIN}|ZZSound_Release_{n}'] for n in ELEMENTS]),
        'FxSoundDrawSheathe': (11, [fx[f'{FX_PLUGIN}|ZZSound_DrawSheathe_{n}'] for n in ELEMENTS]),
        'FxSoundCharge': (11, [fx[f'{FX_PLUGIN}|ZZSound_Charge_{n}'] for n in ELEMENTS]),
    }
    props.update({
        'HitProcPerk': (1, own(hit18.HIT_PERK)),
        'GDivineArmed': (1, own(hit18.DIVINE_ARMED)),
        'FormNotify': (1, own(hit18.NOTIFY)), 'FormSound': (1, own(hit18.SOUND)),
        'GuardLayer': (1, (own(ID_QUEST), 0)), 'InputLayer': (1, (own(ID_QUEST), 0)),
        'BloodGuardSpell': (1, own(hit20.GUARD)),
        'EchoPendingSpell': (1, own(hit20.ECHO)),
        'TwinWindowSpell': (1, own(hit20.TWIN)),
        'RiposteWindowSpell': (1, own(hit21.RIPOSTE)),
        'IceArmorAbility': (1, own(hit21.ICE_ARMOR)),
        'IceArmorWideAbility': (1, own(hit21.ICE_ARMOR_WIDE)),
        'NativeHit': (1, own(hit19.NATIVE_HIT)), 'NativeWanted': (1, own(hit19.NATIVE_WANTED)),
    })
    for ix, (name, _default) in enumerate(MECH_GLOBALS):
        # 屬性名 = 全域變數名去掉 ESSB_ 前綴再加 G（ESSB_Resolve → GResolve）。
        props['G' + name[len('ESSB_'):]] = (1, own(ID_MECH_GLOB + ix))
    for ix, (name, _default) in enumerate(MECH2_GLOBALS):
        props['G' + name[len('ESSB_'):]] = (1, own(ID_MECH2_GLOB + ix))
    for ix, (name, _default) in enumerate(MECH3_GLOBALS):
        props['G' + name[len('ESSB_'):]] = (1, own(ID_MECH3_GLOB + ix))
    tree_props = {
        'Controller': (1, (own(ID_QUEST), 0)),
        'CurrentElement': (1, own(ID_GLOB['ESSB_CurrentElement'])),
        'FormActive': (1, own(ID_GLOB['ESSB_FormActive'])),
        'DebugLevel': (1, own(ID_GLOB['ESSB_DebugLevel'])),
        'ShowMenu': (1, own(ID_SHOW_MENU)),
        'XPPerHit': (1, own(ID_XP_PER_HIT)),
        'LvlGlobals': (11, [own(ID_TREE_GLOB['Lvl'] + n) for n in range(len(TREES))]),
        'RatioGlobals': (11, [own(ID_TREE_GLOB['Ratio'] + n) for n in range(len(TREES))]),
        'PtsGlobals': (11, [own(ID_TREE_GLOB['Pts'] + n) for n in range(len(TREES))]),
        'ColorGlobals': (11, [own(ID_TREE_GLOB['Color'] + n) for n in range(len(TREES))]),
        'ShowLvlGlobals': (11, [own(ID_TREE_GLOB['ShowLvl'] + n) for n in range(len(TREES))]),
        'RespecGlobals': (11, [own(ID_TREE_GLOB['Respec'] + n) for n in range(len(TREES))]),
    }
    # 玩家受擊與擊殺事件（PO3 OnHitEx／OnActorKilled）：同一個 Player 別名上的第三個腳本。
    guard_props = {
        'Ctl': (1, (own(ID_QUEST), 0)),
    }
    guard_props.update({
        'Enabled': (1, own(ID_GLOB['ESSB_Enabled'])),
        'FormActive': (1, own(ID_GLOB['ESSB_FormActive'])),
        'DivineArmed': (1, own(hit18.DIVINE_ARMED)),
        **{name: (1, own(manifest['ESSB_'+name]['id'] and int(manifest['ESSB_'+name]['id'],16)))
           for name in ['RockArmor','IceShield','WaterMirror','GuardWind']},
    })
    input_props = {'Ctl': (1, (own(ID_QUEST), 0)),
        **{name: (1, own(ID_GLOB['ESSB_'+name])) for name in ['Enabled','CurrentElement','FormActive']},
        'HotkeysEnabled': (1, own(hit18.KEY_ENABLE)), 'FormNotify': (1, own(hit18.NOTIFY)),
        'FreeOpen': (1, own(int(manifest['ESSB_FreeOpen']['id'],16))),
        'Hotkeys': (11, [own(hit18.HOTKEYS+i) for i in range(11)])}
    quest_vmad = (struct.pack('<3H', 5, 2, 0)
                  + b'\x02' + struct.pack('<H', 0) + struct.pack('<H', 0)   # 片段：版本 2、0 個片段、空檔名
                  + struct.pack('<H', 1) + obj(own(ID_QUEST), 0)
                  + struct.pack('<3H', 5, 2, 4)
                  + script('ESSBController', props)
                  + script('ESSBTrees', tree_props)
                  + script('ESSBGuard', guard_props)
                  + script('ESSBInput', input_props))
    add('QUST', ID_QUEST, 'ESSB_MainQuest', [
        ('VMAD', quest_vmad),
        ('FULL', Z('元素魔戰士')),
        ('DNAM', struct.pack('<HBBII', 0x11, 0, 255, 0, 0)),   # 旗標 0x1 開局啟用 + 0x10 只跑一次
        ('NEXT', b''), ('ANAM', I(1)),
        ('ALST', I(0)), ('ALID', Z('Player')), ('FNAM', I(0)),
        ('ALFR', I(ref('Skyrim.esm', 0x14))), ('VTCK', I(0)), ('ALED', b''),
    ])

    # Retired forms have no scripts, start flag, or aliases. Never recycle these IDs.
    for stub_edid, stub_id in SCHEMA_STUBS.items():
        add('QUST', stub_id, stub_edid, [
            ('FULL', Z('ESSB retired state schema')),
            ('DNAM', struct.pack('<HBBII', 0, 0, 255, 0, 0)), ('NEXT', b''),
        ])

    # Independent runtime-only MCM quest. No gameplay script points back to ESSBMCM.
    add('QUST', ID_MCM_QUEST, 'ESSB_MCMQuest', [
        ('VMAD', vmad('ESSBMCM', {'Controller': (1, own(ID_QUEST)),
                                 'ModName': (2, 'Elements Spellblade')})
         + b'\x02' + struct.pack('<3H', 0, 0, 1) + obj(own(ID_MCM_QUEST), 0)
         + struct.pack('<3H', 5, 2, 1) + script('SKI_PlayerLoadGameAlias', {})),
        ('FULL', Z('元素魔戰士 MCM')),
        ('DNAM', struct.pack('<HBBII', 0x11, 0, 255, 0, 0)),
        ('NEXT', b''), ('ANAM', I(1)),
        ('ALST', I(0)), ('ALID', Z('ESSB_MCMPlayer')), ('FNAM', I(0)),
        ('ALFR', I(ref('Skyrim.esm', 0x14))), ('VTCK', I(0)), ('ALED', b''),
    ])

    # ----------------------------------------------------- 特效綁定表（build/fx-bindings.json）
    def fx_edid(fid):
        hit = [e for e, m in manifest.items() if m['formid'] == f'{fid:08X}']
        return hit[0] if hit else f'Skyrim.esm|{fid & 0xFFFFFF:06X}'

    fx_bindings = {
        'elements': [{
            'index': ix + 1,
            'element': name,
            'zh': ZH[ix],
            'form_ability': f'ESSB_FormAbility_{name}',
            'aura_shader': fx_edid(fxe('aura', ix)),
            'aura_source': fx_choices['fx_aura'][name],
            'sync_weapon_glow': fx_edid(fxe('weapon', ix)),
            'sync_weapon_source': FX_ELEMENT[ix][2] or f'{FX_PLUGIN}|ZZShader_{name}Form（無來源時的備選）',
            'hit_shader': fx_edid(fxe('hit', ix)),
            'hit_shader_source': FX_ELEMENT[ix][3] or f'{FX_PLUGIN}|ZZShader_{name}（2.11 沒給來源）',
            'hit_impact_set': fx_edid(fx_impact(ix, False)),
            'power_impact_set': fx_edid(fx_impact(ix, True)),
            'power_effect': (f'ESSB_HitEffect_{name}_Power' if name in FX_UPGRADED
                             else f'ESSB_HitEffect_{name}（沒有 Upgraded 衝擊組，重擊共用）'),
            'mark_effect': f'ESSB_MarkEffect_{name}',
            'mark_art': fx_edid(fx_ph('ZZArt', ix)),
            'mark_shader': fx_edid(fxe('mark', ix)),
            'mark_source': fx_choices['fx_mark'][name],
            'mark_duration': 10 if name == 'Water' else 8,
            'mark_visibility': efsh_visibility(next(e['ss'] for e in fx_records
                                                    if e['fid'] == fxe('mark', ix))),
            'react_effect': f'ESSB_ReactEffect_{name}',
            'explosion': fx_edid(fx[f'{FX_PLUGIN}|ZZExplosion_{name}Hand1']),
            'sounds': {
                'on_hit_sndr': fx_edid(fx_ph('ZZSoundDescriptor_OnHit', ix)),
                'charge_sndr': fx_edid(fx_ph('ZZSoundDescriptor_Charge', ix)),
                'form_active_soun': fx_edid(fx[f'{FX_PLUGIN}|ZZSound_FormActive_{name}']),
                'release_soun': fx_edid(fx[f'{FX_PLUGIN}|ZZSound_Release_{name}']),
                'draw_sheathe_soun': fx_edid(fx[f'{FX_PLUGIN}|ZZSound_DrawSheathe_{name}']),
                'charge_soun': fx_edid(fx[f'{FX_PLUGIN}|ZZSound_Charge_{name}']),
            },
        } for ix, name in enumerate(ELEMENTS)],
        'shared': [
            {'what': '同調光暈 1／2／3 段', 'records': ['ESSB_SyncGlowEffect_1', 'ESSB_SyncGlowEffect_2',
                                                    'ESSB_SyncGlowEffect_3'],
             'shader': ['Skyrim.esm|MagicArmorStoneFleshFXS', 'Skyrim.esm|MagicArmorIronFleshFXS',
                        'Skyrim.esm|MagicArmorEbonyFleshFXS'],
             'condition': 'SPEL 效果層 CTDA：GetGlobalValue(ESSB_SyncStage) >= 1／2／3',
             'attached_to': '11 個 ESSB_FormAbility_<元素>'},
            {'what': '真實傷害白光（保留）', 'records': ['ESSB_TrueEffect'],
             'shader': [FX_WHITE], 'condition': '-', 'attached_to': 'Hit Shader'},
            {'what': '破魔印／沉默持續白邊',
             'records': ['ESSB_ManaBreakEffect', 'ESSB_SilenceEffect'],
             'shader': [FX_STATUS_WHITE], 'condition': '-', 'attached_to': 'Hit Shader + FX Persist'},
            {'what': '冰封', 'records': [hit22.edid_effect('Frozen')],
             'shader': [FX_STATUS_FROZEN], 'condition': 'DLL 在凍結滿 5 時掛上，3 秒（永凍、寒核等節點照 v0.4 延長）',
             'attached_to': 'Hit Shader + FX Persist（效果在就有，效果結束就沒有）'},
            {'what': '化灰', 'records': ['ESSB_AshEffect'], 'shader': [FX_ELEMENT[6][3]],
             'condition': '-', 'attached_to': '原版崩解行為不動，只補 2.11 神聖列的化灰著色器'},
            {'what': '復生／恐懼／瘋狂／治病／解毒（原版既有，不複製）',
             'records': ['ESSB_ReanimateEffect', 'ESSB_FearEffect', 'ESSB_FrenzyEffect',
                         'ESSB_CureDiseaseEffect', 'ESSB_CurePoisonEffect'],
             'shader': ['Skyrim.esm|ReanimateFXShader', 'Skyrim.esm|IllusionFearFXS',
                        'Skyrim.esm|IllusionNegativeFXS', 'Skyrim.esm|HealMysticFXS'],
             'condition': '-', 'attached_to': 'Hit Shader + Hit Effect Art + Impact Data（master 參照）'},
            {'what': '領域（11 種）', 'records': ['ESSBController.StartDomain'],
             'shader': ['ESSBFX_ZZExplosion_<元素>Hand1'],
             'condition': '每 0.5 秒最多 5 次（ESSBController.PlaceFx 的預算）',
             'attached_to': 'PlaceAtMe 於領域中心，一次性；判定不變'},
            {'what': '終焉／融斷', 'records': ['ESSBReactions.End（ESSB_End）'],
             'shader': ['ESSBFX_ZZExplosion_<元素>Hand1'],
             'condition': '同上預算；普通命中絕不放爆炸（2.12 效能守則）',
             'attached_to': 'PlaceAtMe 於目標'},
        ],
        'spares': [],
    }

    used_fx = {fx[FX_STATUS_FROZEN]}
    for sig, raw in rr:
        if sig == 'MGEF':
            for sub_sig, payload in fx_extract.subs(raw[24:]):
                if sub_sig == 'DATA':
                    used_fx.update(struct.unpack_from('<I', payload, off)[0] for off in (32, 36))
    fx_bindings['spares'] = [
        {'selector': f'{e["plugin"]}|' + (e['edid'] if e['plugin'] == PLUGIN else
                                                  e['edid'].removeprefix(fx_extract.PREFIX)),
         'record': e['edid']}
        for e in fx_records if e['sig'] == 'EFSH' and e['fid'] not in used_fx]

    # Round 19: native delivery contributes no perk entries.

    # -------------------------------------------------------------- 組檔
    groups = collections.defaultdict(list)
    for sig, raw in rr:
        groups[sig].append(raw)
    header = [
        ('HEDR', struct.pack('<fII', 1.7, len(rr) + len(groups), NEXT_OBJECT_ID)),
        ('CNAM', Z('Elements Spellblade')),
        ('SNAM', Z('元素魔戰士 v0.3 核心：形態層、附傷、設定與除錯紀錄。獨立於 Phenderix Elements。')),
    ]
    for master in MASTERS:
        header.extend([('MAST', Z(master)), ('DATA', bytes(8))])
    body = record('TES4', 0, header, 0)   # 一般 ESP：不設 0x200 ESL 旗標
    for sig, records in groups.items():
        payload = b''.join(records)
        body += struct.pack('<4sI4sIHHHH', b'GRUP', 24 + len(payload), sig.encode(), 0, 0, 0, 0, 0) + payload
    (OUT / PLUGIN).write_bytes(body)
    (OUT / 'SEQ').mkdir(exist_ok=True)
    (OUT / 'SEQ/Elements Spellblade.seq').write_bytes(I(own(ID_QUEST)) + I(own(ID_MCM_QUEST)))

    dump(WORK / 'build/v03-formids.json', {
        'plugin': PLUGIN,
        'masters': MASTERS,
        'esl_flagged': False,
        'record_count': len(rr),
        'next_object_id': f'{NEXT_OBJECT_ID:06X}',
        'allocation': [{'range': a, 'purpose': b, 'state': c} for a, b, c in ALLOCATION],
        'records': manifest,
    })
    return (len(rr), len(body), len(groups), manifest, entry_count,
            (fx_records, fx_closure, fx_report, fx, fx_bindings))


# ------------------------------------------------------------------ 引擎覆蓋表
# 規劃 2.2–2.10 的每一條，對應到腳本與函式，或標 DEFERRED-to-mechanics 並寫原因。
# status 只有兩種：IMPLEMENTED（本前線已落地）、DEFERRED-to-mechanics（延後，附原因）。
D = 'DEFERRED-to-mechanics'
COVERAGE = [
    # ---- 2.2 印記
    ('2.2', '每次有效命中在目標留下當前元素的印記', 'IMPLEMENTED',
     'ESSBController.OnValidHit / ApplyMark', 'DoCombatSpellApply(ESSB_MarkSpell_<X>)'),
    ('2.2', '印記 8 秒，浸濕 10 秒', 'IMPLEMENTED', 'ESSBController.ApplyMark',
     '套用前 SetNthEffectDuration(0, 8 或 10)，只動自有 record'),
    ('2.2', '判定只讀本模組自己的 keyword', 'IMPLEMENTED', 'build_v03.ESSB_MarkEffect_<X> KWDA',
     '掛 ESSB_Mark_<X> 與 ESSB_Element_<X>，不讀外部狀態'),
    ('2.2', '同時帶印記的目標上限 8 個', 'IMPLEMENTED', 'ESSBController 登記表（8 格陣列）',
     'RegActor/RegElem/RegSeq/RegMark/RegStatus 各 8 格'),
    ('2.2', '第 9 個目標：最舊印記提前過期並觸發過期終焉', 'IMPLEMENTED',
     'ESSBController.AcquireSlot → EndMark(reason=3)', 'reason 3 視同過期，倍率 ×1'),
    ('2.2', '通用樹「雙印」：每個目標帶兩種印記', 'IMPLEMENTED',
     'ESSBController.OnValidHit（RegElem2／RegMark2／RegSecondUntil）',
     '機制前線 round 1：副印記格；較舊的留主格、新元素進副格，融斷時兩格各結算一次'),
    # ---- 2.3 元素狀態
    ('2.3', '火 熱度：開印 +2、命中 +1、重擊 +2，上限 10，6 秒未命中歸零', 'IMPLEMENTED',
     'ESSBStatus.AddStack(1) / Tick', '環狀桶以外的計數型狀態，時間用 HeatTime'),
    ('2.3', '火 熱度滿 10 自燃歸零', 'IMPLEMENTED', 'ESSBStatus.AddStack(1)',
     '傷害比照爆燃滿層 ×3，走 ESSB_React_Fire'),
    ('2.3', '火 過熱（你）：同調三段後每命中 +1，滿 10 自爆歸零', 'IMPLEMENTED',
     'ESSBController.HitStacks / AddSelf(4)', '自爆為最大生命 10%，走自有火法術'),
    ('2.3', '冰 凍結量表：開印 +3、命中 +1、重擊 +2，5 = 冰封', 'IMPLEMENTED',
     'ESSBStatus.AddStack(2)', '上限 5（量表，不吃萬象）'),
    ('2.3', '冰 冰封 3 秒後量表歸零；6 秒未命中歸零', 'IMPLEMENTED', 'ESSBStatus.Tick', '兩條計時共用 FreezeTime'),
    ('2.3', '雷 電荷（你）：開印 +2、命中 +1，上限 6，10 秒未命中後每秒 -1', 'IMPLEMENTED',
     'ESSBController.AddSelf(1) / Tick', '放電清空見 2.6'),
    ('2.3', '土 岩甲（你）：開印 +2、命中 +1，上限 5，不衰減，離開形態清空', 'IMPLEMENTED',
     'ESSBController.AddSelf(2) / ClearSelfAll', ''),
    ('2.3', '土 岩甲「被打 -1」', 'IMPLEMENTED',
     'ESSBGuard.OnHitEx → ESSBController.ConsumeRockArmor',
     '機制前線 round 2：PO3 RegisterForHitEventEx，山岳分支在同調三段時免除'),
    ('2.3', '土 裂痕（敵）：開印施加，單層，8 秒', 'IMPLEMENTED', 'ESSBStatus.AddStack(3) / Tick', ''),
    ('2.3', '風 風勢（你）：開印 +2、命中 +1，門檻 4，5 秒未命中歸零', 'IMPLEMENTED',
     'ESSBController.AddSelf(3) / Tick', ''),
    ('2.3', '風 到門檻送出風刃後歸零', 'IMPLEMENTED',
     'ESSBElem2.CheckWindGauge ← ESSBController.ElementHitHook',
     '機制前線 round 2：門檻 4（亂舞 3），送出風刃後 ClearSelf(3)；潛行攻擊直接補滿'),
    ('2.3', '風 失衡（敵）：單層 3 秒，受風刃傷害 +30%', 'IMPLEMENTED',
     'ESSBStatus.AddStack(4) / Tick + ESSBElem2.WindBladeOne',
     '機制前線 round 2：+30% 直接寫在風刃的傷害計算裡，不需要 PERK 進入點'),
    ('2.3', '血 血痕：開印 2 層、命中 +1，上限 8，每層 10 秒，命中刷新全部', 'IMPLEMENTED',
     'ESSBStatus.AddStack(5) + RingMerge（5 格環狀桶）', '命中刷新＝併回最新格'),
    ('2.3', '血 血位（你）：即時讀生命百分比', 'IMPLEMENTED',
     'ESSBController.GetBloodHitMult / GetBloodLeechRatio', '規劃 1.1 的四點曲線線性內插'),
    ('2.3', '聖 聖印：開印 1 層、命中 +1，上限 5，8 秒', 'IMPLEMENTED', 'ESSBStatus.AddStack(6) / Tick', ''),
    ('2.3', '毒 毒層：開印 +3、命中 +1，無上限，每層獨立 12 秒', 'IMPLEMENTED',
     'ESSBStatus.AddStack(7)（6 格環狀桶）', '命中不刷新舊層'),
    ('2.3', '毒 ≥5 層時每 2 秒向 3 公尺內一名敵人傳 1 層', 'IMPLEMENTED',
     'ESSBStatus.Tick → ESSBController.SpreadPoison', '每次只找一個對象，不做全場掃描'),
    ('2.3', '水 浸濕：開印施加，單層，10 秒', 'IMPLEMENTED', 'ESSBStatus.AddStack(8) / Tick', ''),
    ('2.3', '水 水壓（分支）', 'IMPLEMENTED',
     'ESSBElem3.OnWaterHit / WaterHitMult / PressureCap → ESSBController.StackCap(9)',
     'round 3 結清：命中浸濕目標 +1 層（上限 5，萬象 8、8 秒命中刷新），每層水附傷 +（10% + 1%／點）'),
    ('2.3', '暗 詛咒：開印 2 層、命中 +1，上限 5，8 秒', 'IMPLEMENTED', 'ESSBStatus.AddStack(10) / Tick', ''),
    ('2.3', '星 星痕：開印 1 層、命中 +1，上限 3，每層 2 秒後自行引爆', 'IMPLEMENTED',
     'ESSBStatus.AddStack(11) + Tick（2 格環狀桶）', '掉出桶的那一格即引爆'),
    ('2.3', '無元素 戰意、破魔印', 'IMPLEMENTED',
     'ESSBController.AddResolve／ApplyManaBreakMark、MGEF ESSB_ManaBreakEffect',
     '機制前線 round 1：戰意 5 層 5 秒衰減；破魔印 8 秒，沉默與反咒以它為條件'),
    ('2.3', '通用 同調：每有效命中 +1，無上限', 'IMPLEMENTED', 'ESSBController.AddSync', ''),
    ('2.3', '疊在你身上的狀態離開形態時清空', 'IMPLEMENTED',
     'ESSBController.ClearSelfAll（OnFormOpened／OnFormSwitched／OnFormClosed）', ''),
    ('2.3', '上限的第三種來源：通用樹傳奇「萬象」+1 層／每 5 點', 'IMPLEMENTED',
     'ESSBController.StackCap + ESSBNodes.StatusCapBonus／OmniMult',
     '機制前線 round 1：上限 +1／每 5 點（最多 +3），量表類不吃；萬象分支另外給層數效果 +25%'),
    # ---- 2.4 同調
    ('2.4', '三段門檻 5／15／30', 'IMPLEMENTED',
     'ESSBController.SyncStage + GLOB ESSB_SyncT1/T2/T3', '門檻放全域變數，進遊戲可調'),
    ('2.4', '升段事件', 'IMPLEMENTED', 'ESSBController.OnSyncStage',
     '送 ESSB_SyncStage 模組事件並留等級 1 紀錄'),
    ('2.4', '切換形態或關閉時歸零', 'IMPLEMENTED', 'ESSBController.SwitchForm / OnFormClosed', ''),
    ('2.4', '同調光暈（一、二、三段各一層）與三段時的武器發光', 'IMPLEMENTED',
     'MGEF ESSB_SyncGlowEffect_1/2/3 + ESSB_SyncWeaponEffect_<X>，掛在 11 個 '
     'ESSB_FormAbility_<X> 的效果層，條件是 CTDA GetGlobalValue(ESSB_SyncStage) >= 1/2/3',
     '特效前線結清：光暈用原版石膚／鐵膚／黑檀膚三檔（2.11 字面），三段另加 2.11 '
     '逐元素的武器光 EFSH；常駐視覺的做法照抄原版 AbOnFire（Hit Shader ＝ Enchant Shader '
     '＋ FX Persist 0x1000），引擎自己評估條件，零 Papyrus。'
     'TrueHUD 同調條：規劃寫「選配」，本前線標 DEFERRED-optional（見 deferred_optional）'),
    # ---- 2.5 融斷
    ('2.5', '關閉形態時 15 公尺內所有印記一次結清為爆傷', 'IMPLEMENTED',
     'ESSBController.OnFormClosed → EndMark(reason=1)', '1050 單位 = 15 公尺'),
    ('2.5', 'K_sync 隨同調段數 ×1／×1.5／×2／×3', 'IMPLEMENTED', 'ESSBController.SyncMult', ''),
    ('2.5', '風印記融斷的「吹上天」與落地傷害', 'IMPLEMENTED',
     'ESSBController.LiftUp → ESSBStatus 浮空 → ESSBController.OnLanding',
     '機制前線 round 2：ApplyHavokImpulse 帶向上分量 + 自有 2 秒浮空狀態；落地傷害在到期那一秒結算'),
    ('2.5', '收束分支 20 公尺', 'IMPLEMENTED', 'ESSBNoForm.BurstRadius',
     '機制前線 round 1：收束 15 → 20 公尺，融斷專精主線再 +0.3 公尺／點'),
    # ---- 2.6 反應
    ('2.6', '開印＝從沒有印記變成有印記那一下，效果由新印記元素決定', 'IMPLEMENTED',
     'ESSBController.OnValidHit → OpenMark → ESSBReactions.Open', ''),
    ('2.6', '終焉＝印記結束那一下，效果由結束的印記元素決定', 'IMPLEMENTED',
     'ESSBController.EndMark → ESSBReactions.End', 'reason 0 切掉／1 融斷／2 過期／3 逐出'),
    ('2.6', '被切掉：先舊元素終焉，再新元素開印', 'IMPLEMENTED', 'ESSBController.OnValidHit', ''),
    ('2.6', '自然過期走過期終焉，需分辨 Dispel 與自然結束', 'IMPLEMENTED',
     'ESSBMark.OnEffectFinish → ESSBController.OnMarkFinish', '主動結束先把 RegMark 清成 None，回報認不出自己就不重複'),
    ('2.6', '同元素命中只刷新印記時間，不反應', 'IMPLEMENTED', 'ESSBController.OnValidHit（previous == element 分支）', ''),
    ('2.6', '每個目標的開印與終焉各有 1 秒內部冷卻', 'IMPLEMENTED',
     'ESSBController.OpenMark / EndMark（RegLastOpen/RegLastEnd）', '過期終焉也受此限制'),
    ('2.6', '反應產生的傷害與狀態不留印記、不觸發任何反應', 'IMPLEMENTED',
     'build_v03.ESSB_ReactEffect_<X>', '只掛 ESSB_React，不掛 ESSB_Proc，OnWeaponHit 不會遞迴'),
    ('2.6', '範圍效果最多影響 5 個目標', 'IMPLEMENTED', 'ESSBController.ScanTargets', '固定 5 格陣列，近的優先'),
    ('2.6', '反應傷害的基準是 B_max，不隨機', 'IMPLEMENTED', 'ESSBReactions.BaseMax', '11 個元素的 2.1 上限'),
    ('2.6', '火 開印 點燃：熱度 +2，B_max ×0.5 火傷', 'IMPLEMENTED', 'ESSBReactions.Open(1)', ''),
    ('2.6', '火 終焉 爆燃：B_max ×1.0 ×(1+熱度×0.2)，消耗熱度', 'IMPLEMENTED', 'ESSBReactions.EndFire', ''),
    ('2.6', '冰 開印 霜結：凍結 +3，減速 15% 3 秒', 'IMPLEMENTED', 'ESSBReactions.Open(2)',
     '減速走 ESSB_Util_Slow'),
    ('2.6', '冰 終焉 碎冰：冰封低血處決／冰封 ×2.5 加碎甲／未冰封 ×1.0', 'IMPLEMENTED',
     'ESSBReactions.EndFrost', '首領與必要角色改 ×5.0（IsVIPTarget）'),
    ('2.6', '雷 開印 感電：你 +2 電荷，目標魔力 -B_max', 'IMPLEMENTED', 'ESSBReactions.Open(3)', ''),
    ('2.6', '雷 終焉 放電：電荷 ×30% B_max、削魔 50%、跳 2 人各 40%、滿格 ×2、吃重擊倍率',
     'IMPLEMENTED', 'ESSBReactions.EndShock', '唯一吃 R 的終焉，讀 LastHitWasPower()'),
    ('2.6', '土 開印 裂痕：護甲 -30、耐力 -10、你回 10 耐力並 +2 岩甲', 'IMPLEMENTED',
     'ESSBReactions.Open(4)', ''),
    ('2.6', '土 終焉 地震：3 公尺 B_max ×1.5、削耐 ×2、其餘減速 30%', 'IMPLEMENTED',
     'ESSBReactions.EndEarth', '3 公尺 = 210 單位'),
    ('2.6', '土 地震「耐力歸零跌倒」', 'IMPLEMENTED',
     'ESSBElem2.QuakeOne → ESSBController.Knockdown / CanRagdoll',
     '機制前線 round 2：PushActorAway 力道 3.0、每目標 8 秒一次；龍／騎乘／必要角色／巨人猛獁改為減速'),
    ('2.6', '風 開印 風痕：你風勢 +2、施加失衡', 'IMPLEMENTED', 'ESSBReactions.Open(5)', ''),
    ('2.6', '風 開印「拉近 1.5 公尺」', 'IMPLEMENTED',
     'ESSBElem2.OpenWind → ESSBController.PullIn / PullTo',
     '機制前線 round 2：ApplyHavokImpulse 水平衝量 1.5–3 公尺、每目標 3 秒一次；奇襲分支不拉近'),
    ('2.6', '風 終焉 吹飛：目標與附近 2 人各 B_max ×1.0；首領大型改減速 30%', 'IMPLEMENTED',
     'ESSBReactions.EndWind', ''),
    ('2.6', '風 終焉「吹飛 3 公尺 ragdoll」', 'IMPLEMENTED',
     'ESSBElem2.BlowAway → ESSBController.BlowBack',
     '機制前線 round 2：3–6 公尺（+0.2／點），上天分支改走 LiftUp；免疫者改為減速 30% 3 秒'),
    ('2.6', '血 開印 血痕：流血 2 層，依血位吸血', 'IMPLEMENTED', 'ESSBReactions.Open(6)', ''),
    ('2.6', '血 終焉 血潮：結算剩餘流血總傷 + 當前生命 10%（首領 3%），治療 = 傷害 × 吸血比例 ×2',
     'IMPLEMENTED', 'ESSBReactions.EndBlood + ESSBStatus.BleedRemaining', '剩餘量以環狀桶各格剩餘秒數計'),
    ('2.6', '聖 開印 聖印：你回血 B_max ×0.5', 'IMPLEMENTED', 'ESSBReactions.Open(7)', ''),
    ('2.6', '聖 開印「目標受聖傷 +20%」', 'IMPLEMENTED',
     'ESSBElem2.HolyVulnerability → DivineHitMult / Judge',
     '機制前線 round 2：不走 PERK 進入點——0x23 的條件分頁 1 是武器不是目標（原版 Armsman00 實測），'
     '所以改在本模組自己的聖傷計算裡加，附傷與裁決共用同一個函式'),
    ('2.6', '聖 終焉 裁決：B_max ×2.0，對亡靈魔族 ×3，治療你 B_max ×1.0', 'IMPLEMENTED',
     'ESSBReactions.EndDivine', '基準 K=2.0，對 ActorTypeUndead／ActorTypeDaedra 再 ×3'),
    ('2.6', '毒 開印 淬毒：+3 毒層並立即傳 1 層給 3 公尺內一人', 'IMPLEMENTED', 'ESSBReactions.Open(8)', ''),
    ('2.6', '毒 終焉 催毒：不結清，8 秒內每秒跳兩次，擴散改每秒一次，關閉形態後仍工作',
     'IMPLEMENTED', 'ESSBReactions.EndPoison + ESSBStatus.Tick', '狀態容器獨立於形態，形態關閉照跑'),
    ('2.6', '水 開印 浸濕：減速 10%，印記 10 秒', 'IMPLEMENTED', 'ESSBReactions.Open(9) + ApplyMark', ''),
    ('2.6', '水 終焉 導引：接管元素下一次終焉 ×1.5，你 +5 同調', 'IMPLEMENTED',
     'ESSBReactions.EndWater + ESSBStatus.SetNextEndMult', '只在被切掉時有接管元素'),
    ('2.6', '暗 開印 詛咒：2 層詛咒，吸魔 B_max ×1.0', 'IMPLEMENTED', 'ESSBReactions.Open(10)',
     '削目標魔力並回你等量魔力'),
    ('2.6', '暗 終焉 死咒：3 秒後 B_max ×2.0 + 已損失生命 15%', 'IMPLEMENTED',
     'ESSBReactions.EndDark + ESSBStatus.Tick', '倒數在狀態容器的每秒 tick 裡'),
    ('2.6', '暗 死咒「期間無法被治療」', 'IMPLEMENTED',
     'ESSBReactions.EndDark → ESSBController.ApplyUtil(20 HealRateDebuff, 100%) '
     '+ ESSBElem3.DeathCurseSeconds',
     'round 3 結清：不用 PERK 進入點，改用 HealRateMult -100% 的自有減益（3 秒，「不治」分支 6 秒）。'
     '語意是「生命回復速率歸零」，別人對他施放的治療法術不受影響，與血咒同一個偏離'),
    ('2.6', '星 開印 星痕：2 秒後 B_max ×1.0 延遲星傷', 'IMPLEMENTED',
     'ESSBReactions.Open(11) + ESSBStatus 星痕環狀桶', ''),
    ('2.6', '星 終焉 星落：B_max ×2.0，接管元素這次開印 ×1.5', 'IMPLEMENTED',
     'ESSBReactions.EndAstral + ESSBStatus.SetNextOpenMult', '只在被切掉時有接管元素'),
    ('2.6', '各樹開啟路線放大開印、關閉路線放大終焉', 'IMPLEMENTED',
     'ESSBElem.OpenMult／EndMult／BurstMult + ESSBNodes.CommonEndMult／CommonBurstMult',
     '機制前線 round 1：通用、無元素、火、冰、雷五棵已接；其餘八棵照同一組函式名在 round 2／3 補資料'),
    # ---- 2.7 公式
    ('2.7', 'D_hit = B × R × G(L) × M_mod × M_ext × (1−Res)', 'IMPLEMENTED（前四項）',
     'build_v03 附傷法術 magnitude + ESSBController.OnWeaponHit', 'M_ext 與 Res 由引擎結算'),
    ('2.7', '持續傷害：每秒 = B_max × k_dot × 層數 × …（流血 0.08、毒 0.05）', 'IMPLEMENTED',
     'ESSBStatus.Tick', '走 ESSB_React_Blood／ESSB_React_Poison'),
    ('2.7', '放血：每層每秒扣當前生命 0.3%（首領 0.1%），不吃 G(L) 與抗性', 'IMPLEMENTED',
     'ESSBStatus.Tick → ESSBController.ApplyBleedDrain', 'ESSB_Util_BleedTick 的抗性 AV 設 none'),
    ('2.7', 'D_react = B_max × K_react × G(L) × M_mod × …', 'IMPLEMENTED',
     'ESSBReactions.ReactDamage', '反應不吃 R、不吃隨機 B'),
    ('2.7', 'D_burst = Σ B_max(印記元素) × K_sync × …', 'IMPLEMENTED',
     'ESSBController.OnFormClosed → EndMark(reason=1, K_sync)', ''),
    ('2.7', 'G(L) = 1 + 0.05 × L', 'IMPLEMENTED',
     'ESSBTrees.TreeG → ESSBController.ApplyDamage／ApplyProc／ApplyTrueDamage',
     '機制前線 round 1：反應、DoT、附傷、真傷四條路徑各只乘一次；附傷在施放前設 magnitude'),
    ('2.7', 'M_mod 節點加成合計', 'IMPLEMENTED', 'ESSBController.GetDamageMult / GetHitMult',
     '機制前線 round 1：GetHitMult = 共通 × 通用樹 × 元素樹，一次乘完不疊乘'),
    ('2.7', '層數狀態共用實作：每目標一個每秒計時器 + N 格環狀桶', 'IMPLEMENTED',
     'ESSBStatus（RingAdd／RingAge／RingSum／RingMerge）', '記憶體固定，毒層無上限也不變慢'),
    ('2.7', '血位倍率乘在 M_mod 裡，命中時讀一次', 'IMPLEMENTED', 'ESSBController.GetDamageMult(6)', ''),
    ('2.7', '血承：擊殺時吸收死者屬性 15 秒', 'IMPLEMENTED',
     'ESSBController.ApplyInherit（SPEL ESSB_InheritSpell）',
     '機制前線 round 2：七個 Peak Value Modifier（火冰電毒魔抗 50%、護甲 20%、最大生命 10%），施放前逐一設 magnitude'),
    # ---- 2.8 真實傷害
    ('2.8', '真實傷害類別（不吃護甲、抗性、外部加成）', 'IMPLEMENTED',
     'MGEF ESSB_TrueEffect（0x005020）／SPEL ESSB_TrueDamageSpell（0x005021）+ ESSBController.ApplyTrueDamage',
     '機制前線 round 1：skill = -1、Resist Value = None、只掛 ESSB_TrueDamage；造成真傷練無元素樹'),
    # ---- 2.9 附近與範圍
    ('2.9', '中心＝被命中的目標；融斷與「臨」以玩家為中心', 'IMPLEMENTED',
     'ESSBController.ScanTargets(akCenter) / OnFormClosed', '「臨」屬機制前線'),
    ('2.9', '半徑 15 公尺＝1050 單位', 'IMPLEMENTED', 'ESSBController.ScanTargets 呼叫端', ''),
    ('2.9', '人數上限 5，距離近的優先', 'IMPLEMENTED', 'ESSBController.ScanTargets', '插入排序，固定 5 格'),
    ('2.9', '不要求視線', 'IMPLEMENTED', 'ESSBController.ScanTargets', '只比距離，不做 LOS'),
    ('2.9', '目標資格：敵意／敵對陣營／已交戰，且非同伴非受命非死亡', 'IMPLEMENTED',
     'ESSBController.IsValidTarget', 'IsHostileToActor 已涵蓋敵對陣營'),
    ('2.9', '命中時掛 30 秒「已交戰」自有標記', 'IMPLEMENTED',
     'ESSBController.MarkEngaged + SPEL ESSB_Engaged', 'KYWD ESSB_Engaged，HasMagicEffectWithKeyword 判定'),
    ('2.9', '必要角色算有效目標，但處決、跌倒、復生、化灰對其無效', 'IMPLEMENTED',
     'ESSBController.IsVIPTarget / CanRagdoll / ApplyAsh',
     '機制前線 round 2：跌倒與化灰都先過 IsVIPTarget；復生屬 round 3 的黑暗樹'),
    ('2.9', '例外表：地震／裁決／星落 3 公尺、風刃與放電跳躍 15 公尺 2 人、擴散開印 1 人',
     'IMPLEMENTED', 'ESSBReactions.EndEarth / EndShock / EndWind / Open(8)', ''),
    ('2.9', '例外表：融斷後的領域、各元素的「臨」、瘴氣複製、星界範圍成長', 'IMPLEMENTED',
     'ESSBController.StartDomain／InDomain／TickDomain（3 格）+ ESSBElem.OnFormOpened '
     '+ ESSBElem3.EndPoisonNodes（瘴氣 6 公尺 5 人）+ ESSBElem3.Range（星界每點 +1 公尺）',
     'round 3 結清：領域從 1 格擴充為 3 格並帶各自的半徑（星域的半徑隨主線成長）；'
     '十一種領域、十一個「臨」、瘴氣複製與星界範圍成長全部落地'),
    # ---- 2.10 環境與時間
    ('2.10', '下雨、下雪或站在水中 → 所有敵人視為帶浸濕', 'IMPLEMENTED',
     'ESSBController.EnvCheck → GLOB ESSB_EnvWet；IsEnvWet 讀取環境浸濕', '每 5 秒檢查一次'),
    ('2.10', '暴風雪天氣 → 冰的凍結累積 ×2', 'IMPLEMENTED',
     'ESSBController.HitStacks / ESSBReactions.Open(2)', 'GLOB ESSB_EnvStormy'),
    ('2.10', '雷雨天氣 → 雷形態每 3 秒自動 +1 電荷', 'IMPLEMENTED', 'ESSBController.Tick', ''),
    ('2.10', '夜晚（20:00–6:00）→ 黑暗附傷 +20%', 'IMPLEMENTED',
     'ESSBController.EnvCheck + GetDamageMult(10)', '讀 Skyrim.esm 0x38 GameHour'),
    ('2.10', '白天（6:00–20:00）→ 神聖附傷 +20%', 'IMPLEMENTED', 'ESSBController.GetDamageMult(7)', ''),
    ('2.10', '夜晚 → 星界所有範圍 ×1.5；白天 → 化灰必定觸發', 'IMPLEMENTED',
     'ESSBElem2.ShouldAsh → ESSBController.ApplyAsh；ESSBElem3.Range → ESSBController.IsEnvNight',
     'round 2 結清化灰（MGEF DATA 照抄原版 PerkDisintegrateFFAimed，龍與必要角色不化灰）；'
     'round 3 結清星界範圍：Range() 一個函式統一乘 1.5，星臨／星落／群星／星散／星域都吃'),
    ('2.10', '室內、地城無環境加成', 'IMPLEMENTED', 'ESSBController.EnvCheck', 'GetParentCell().IsInterior()'),
]


DEFERRED_OPTIONAL = [
    {'item': 'TrueHUD 同調條', 'section': '2.4／2.11',
     'reason': '規劃把 TrueHUD 條寫成選配（「TrueHUD 同調條」與光暈同一列，光暈是規格、'
               'HUD 條是加分）。要做需要 TrueHUD 的 SKSE API 與一個外掛 DLL 的自訂條，'
               '不是記錄層做得到的事，也會多一個硬依賴。同調段數已鏡射成 '
               'ESSB_SyncStage 全域變數與 ESSB_SyncStage 模組事件，'
               '之後任何 HUD 模組都能直接讀，所以延後不擋任何東西。',
     'blocking': False},
]


def write_coverage():
    rows = [{'section': s, 'item': i, 'status': st, 'where': w, 'note': n} for s, i, st, w, n in COVERAGE]
    unmapped = [r for r in rows if not r['status'] or not r['where']]
    if unmapped:
        raise SystemExit(f'engine coverage has unmapped items: {unmapped}')
    deferred = [r for r in rows if D in r['status']]
    dump(WORK / 'build/engine-coverage.json', {
        'front': 'fx-assets',
        'plan': '元素魔戰士規劃-v0.3.md 2.2–2.10（2.4 的視覺一列由 2.11／2.12 結清）',
        'scripts': SCRIPTS,
        'totals': {
            'items': len(rows),
            'implemented': sum(1 for r in rows if r['status'].startswith('IMPLEMENTED')),
            'deferred': len(deferred),
            'deferred_optional': len(DEFERRED_OPTIONAL),
        },
        'legend': {
            'IMPLEMENTED': '本前線已落地，where 欄是腳本與函式',
            D: '延後給機制前線（PERK、技能樹、物理推力實測），note 欄是原因',
            'DEFERRED-optional': '規劃本身寫成選配，不擋任何交付；見 deferred_optional',
        },
        'deferred': deferred,
        'deferred_optional': DEFERRED_OPTIONAL,
        'items': rows,
    })
    return len(rows), len(deferred)


# ------------------------------------------------------------------ 規劃覆蓋表（v0.4 的 493 個節點 + 共通機制）
# round 21：節點狀態改成 v0.4 的 DONE／KEPT-Nx／PARTIAL-Nx／LATER-Nx（見 plan_coverage.STATUS_LEGEND）；
# 共通機制列沿用 IMPLEMENTED／DEFERRED。
NODE_STATUS = re.compile(r'(DONE|KEPT-(N[3-6]|待決)|PARTIAL-(N[3-6]|基礎|待決)|LATER-(N[3-6]|待決))')
MECHANISM_STATUS = ['IMPLEMENTED', 'DEFERRED', 'REMOVED', 'LATER-N5']


def write_plan_coverage(plan, manifest):
    rows, missing = plan_coverage.rows(plan)
    if missing:
        raise SystemExit(f'plan coverage has unmapped nodes: {missing[:10]} (total {len(missing)})')
    extra = sorted(set(plan_coverage.NODES) - {(r['tree'], r['name']) for r in rows if r['kind'] == 'node'})
    if extra:
        raise SystemExit(f'plan coverage names nodes v0.4 does not have: {extra[:10]}')
    bad = [r for r in rows
           if not (NODE_STATUS.fullmatch(r['status']) if r['kind'] == 'node' else r['status'] in MECHANISM_STATUS)
           or not r['where'] or not r['note'] or not r['text']]
    if bad:
        raise SystemExit(f'plan coverage rows missing status/where/note: {bad[:5]}')
    nodes = [r for r in rows if r['kind'] == 'node']
    expected = plan['totals']['main_nodes'] + plan['totals']['branch_nodes']
    if len(nodes) != expected:
        raise SystemExit(f'plan coverage node count {len(nodes)} != plan {expected}')
    # 每一筆節點列的 EDID 都必須真的存在於這一次寫出去的 ESP。
    unknown = sorted({r['edid'] for r in nodes if r['edid'] not in manifest})
    if unknown:
        raise SystemExit(f'plan coverage references unknown EDIDs: {unknown[:10]}')
    counts = collections.Counter(r['status'] for r in rows)
    node_counts = collections.Counter(r['status'] for r in nodes)
    by_tree = {}
    for row in nodes:
        by_tree.setdefault(row['tree'], collections.Counter())[row['status']] += 1
    if set(by_tree) != set(TREES):
        raise SystemExit(f'plan coverage trees {sorted(by_tree)} != {TREES}')
    dump(WORK / 'build/plan-coverage.json', {
        'front': 'round 21 (v0.4 trees)',
        'plan': '元素魔戰士規劃-v0.4.md 1.1／2.x／5.1–5.13',
        'source': 'build/plan-tree-nodes.json',
        'legend': dict(plan_coverage.STATUS_LEGEND,
                       IMPLEMENTED='共通機制：已落地', DEFERRED='共通機制：有技術理由延後，note 寫明',
                       REMOVED='共通機制：v0.4 已拿掉的 v0.3 規則', **{'LATER-N5': '共通機制：提前移除，N5 以 v0.4 版本重做（裁定 C3）'}),
        'totals': {
            'rows': len(rows),
            'nodes': len(nodes),
            'mechanisms': len(rows) - len(nodes),
            'unmapped': 0,
            'by_status': dict(counts),
            'nodes_by_status': dict(node_counts),
            'nodes_by_tree': {t: dict(c) for t, c in sorted(by_tree.items())},
        },
        'deferred': [r for r in rows if r['status'] == 'DEFERRED'],
        'rows': rows,
    })
    return len(rows), dict(counts), [r for r in rows if r['status'] == 'DEFERRED']


# v0.4 的新分支（round 21 新增的 perk EditorID），明列在這裡審過；建置時跟身分表推出來的集合比對，
# 兩邊不一樣就失敗（驗證器的「新記錄白名單」只收這一份，不收推導結果）。
def new_perk_edids(plan):
    derived = {f"ESSB_P_{t['id']}_{r['index']}_{k['index']}_B{b['slot'] + 1}"
               for t in plan['trees'] for r in t['routes'] for k in r['tiers'] for b in k['branches']
               if b['v03'] is None}
    listed = set(tree_v04.NEW_PERK_EDIDS)
    assert derived == listed, (sorted(derived - listed), sorted(listed - derived))
    return listed


def round21_new_edids():
    """round 21 新增的每一筆記錄：47 個新分支 perk + fix21_records（浸濕 1–30 秒、寂、寂滅標記、反擊視窗、冰甲）。"""
    return set(tree_v04.NEW_PERK_EDIDS) | hit21.new_edids()


# ------------------------------------------------------------------ CSF 設定檔（13 個）
# perkPoints 是選單（根）層級的全域變數，所以一棵樹一個檔、一個 perkPoints，
# 用 CustomSkills.OpenCustomSkillMenu(skillId) 分別開啟。
TIER_Y_STEP = 1.0               # y 正值往上；五階落在 0..4。
LAYOUT_LANE_STEP = 0.95         # 同階橫排；第三分支使用同一路線的額外欄。
LAYOUT_MIN_SPACING = 0.9
LAYOUT_X_BOUNDS = (-4.5, 4.5)
LAYOUT_Y_BOUNDS = (0.0, 4.5)


def csf_route_x(tree):
    # Reserve 3 lanes (main + two branches), or 4 for a route with a third branch.
    # Center the complete tree, keeping each route in its own adjacent lane block.
    widths = [1 + max(len(t['branches']) for t in r['tiers']) for r in tree['routes']]
    cursor = (sum(widths) - 1) * LAYOUT_LANE_STEP / 2
    centers = []
    for width in widths:
        centers.append(round(cursor - LAYOUT_LANE_STEP, 6))
        cursor -= width * LAYOUT_LANE_STEP
    return centers


def validate_csf_layout(tree, nodes):
    label = tree['id']
    by_id = {n['id']: n for n in nodes}
    assert len(by_id) == len(nodes), f'{label}: duplicate node ids'
    for i, node in enumerate(nodes):
        x, y = node['x'], node['y']
        assert LAYOUT_X_BOUNDS[0] <= x <= LAYOUT_X_BOUNDS[1], (label, node, 'x bounds')
        assert LAYOUT_Y_BOUNDS[0] <= y <= LAYOUT_Y_BOUNDS[1], (label, node, 'y bounds')
        for other in nodes[i + 1:]:
            # Reject pairs closer than 0.9 on BOTH axes, including other routes.
            assert max(abs(x - other['x']), abs(y - other['y'])) + 1e-9 >= LAYOUT_MIN_SPACING, (
                label, node['id'], other['id'], 'overlap')
    expected_ids = set()
    route_bounds = []
    for route in tree['routes']:
        r = route['index']
        route_nodes = []
        previous = None
        for tier in route['tiers']:
            k = tier['index']
            main_id = f'm{r}{k}'
            expected_ids.add(main_id)
            main = by_id[main_id]
            route_nodes.append(main)
            if previous is not None:
                assert main['y'] > previous['y'], (label, main_id, 'tier order')
                assert main['x'] == previous['x'], (label, main_id, 'mainline column')
            previous = main
            links = [f'm{r}{k + 1}'] if k + 1 < len(route['tiers']) else []
            for branch in tier['branches']:
                branch_id = f'b{r}{k}{branch["slot"]}'
                expected_ids.add(branch_id)
                links.append(branch_id)
                node = by_id[branch_id]
                route_nodes.append(node)
                assert not node['links'], (label, branch_id, 'branch links')
                assert node['y'] == main['y'], (label, branch_id, 'branch tier')
                assert abs(node['x'] - main['x']) <= 2 * LAYOUT_LANE_STEP + 1e-9, (
                    label, branch_id, 'branch adjacency')
            assert main['links'] == links, (label, main_id, 'mainline/branch links')
        route_bounds.append((min(n['x'] for n in route_nodes), max(n['x'] for n in route_nodes)))
    assert set(by_id) == expected_ids, (label, 'unexpected nodes')
    for left, right in zip(route_bounds, route_bounds[1:]):
        assert left[0] - right[1] + 1e-9 >= LAYOUT_MIN_SPACING, (label, 'route separation')
    return {'valid': True, 'x': [min(n['x'] for n in nodes), max(n['x'] for n in nodes)],
            'y': [min(n['y'] for n in nodes), max(n['y'] for n in nodes)],
            'min_spacing': min(max(abs(a['x'] - b['x']), abs(a['y'] - b['y']))
                               for i, a in enumerate(nodes) for b in nodes[i + 1:]),
            'route_x': csf_route_x(tree)}


def csf_form(fid):
    return f'{PLUGIN}|{fid:06X}'


def csf_config(tree, settings):
    t = tree['index']
    nodes = []
    route_x = csf_route_x(tree)
    for route in tree['routes']:
        r = route['index']
        x = route_x[r]
        for tier in route['tiers']:
            k = tier['index']
            y = k * TIER_Y_STEP
            node_ix = (t * 3 + r) * 5 + k
            links = []
            if k + 1 < len(route['tiers']):
                links.append(f'm{r}{k + 1}')
            links.extend(f'b{r}{k}{b["slot"]}' for b in tier['branches'])
            nodes.append({
                'id': f'm{r}{k}',
                'perk': csf_form(ID_MAIN_PERK + node_ix * plan_trees.MAIN_MAX_RANK),
                'edid': f"ESSB_P_{tree['id']}_{r}_{k}_M1",
                'x': x, 'y': y, 'links': links,
            })
            for branch in tier['branches']:
                # 格位 slot 決定 perk（FormID）與節點 id；x 由 v0.4 表格的顯示順序 order 決定（round 21）。
                n = branch['slot']
                order = branch['order']
                nodes.append({
                    'id': f'b{r}{k}{n}',
                    'perk': csf_form(ID_BRANCH_PERK + node_ix * plan_trees.MAX_BRANCH + n),
                    'edid': f"ESSB_P_{tree['id']}_{r}_{k}_B{n + 1}",
                    'x': round(x + (1 if order == 0 else -order) * LAYOUT_LANE_STEP, 6),
                    'y': y,
                    'links': [],
                })
    routes = '／'.join(r['name'] for r in tree['routes'])
    return {
        'version': 1,
        'showMenu': csf_form(ID_SHOW_MENU),
        'perkPoints': csf_form(ID_TREE_GLOB['Pts'] + t),
        'skills': [{
            'id': CSF_SKILL_PREFIX + tree['id'],
            'name': f'元素魔戰士：{TREE_ZH[t]}',
            'description': f"規劃 {tree['section']}　路線：{routes}　"
                           f"主線每點 1 分、最多 15 點；分支各 5 點、可複選。",
            'level': csf_form(ID_TREE_GLOB['Lvl'] + t),
            'ratio': csf_form(ID_TREE_GLOB['Ratio'] + t),
            'legendary': None,
            'color': csf_form(ID_TREE_GLOB['Color'] + t),
            'showLevelup': csf_form(ID_TREE_GLOB['ShowLvl'] + t),
            'experienceFormula': {
                'useMult': float(settings.get('csf_use_mult', 1.0)),
                'useOffset': float(settings.get('csf_use_offset', 0.0)),
                'improveMult': float(settings.get('csf_improve_mult', 0.05)),
                'improveOffset': float(settings.get('csf_improve_offset', 2.0)),
                'enableXPPerRank': False,
            },
            'nodes': nodes,
        }],
    }


def write_csf(plan, manifest):
    settings = json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))
    folder = OUT / CSF_DIR
    folder.mkdir(parents=True, exist_ok=True)
    keep = {f'{CSF_SKILL_PREFIX}{t}.json' for t in TREES}
    for stale in folder.iterdir():
        if stale.is_file() and stale.name not in keep:
            stale.unlink()

    files = []
    for tree in plan['trees']:
        config = csf_config(tree, settings)
        skill = config['skills'][0]
        # 節點的 edid 欄只是給建置期驗證用，不寫進遊戲讀的檔案。
        edids = [n.pop('edid') for n in skill['nodes']]
        path = folder / f"{CSF_SKILL_PREFIX}{tree['id']}.json"
        dump(path, config)
        reloaded = json.loads(path.read_text(encoding='utf-8'))
        layout = validate_csf_layout(tree, reloaded['skills'][0]['nodes'])
        unresolved = []
        for node, edid in zip(skill['nodes'], edids):
            entry = manifest.get(edid)
            if not entry or entry['type'] != 'PERK':
                unresolved.append(edid)
            elif node['perk'] != f"{PLUGIN}|{entry['id']}":
                unresolved.append(f'{edid}!={node["perk"]}')
        files.append({
            'tree': tree['id'],
            'layout': layout,
            'path': str(path.relative_to(OUT)).replace('\\', '/'),
            'skill_id': skill['id'],
            'json_loads': reloaded == config,
            'node_count': len(skill['nodes']),
            'main_nodes': sum(1 for n in skill['nodes'] if n['id'].startswith('m')),
            'branch_nodes': sum(1 for n in skill['nodes'] if n['id'].startswith('b')),
            'node_limit_ok': len(skill['nodes']) <= 127,
            'perk_refs_resolved': not unresolved,
            'unresolved': unresolved,
            'perk_points': config['perkPoints'],
        })

    bad = [f for f in files if not (f['json_loads'] and f['node_limit_ok'] and f['perk_refs_resolved'])]
    dump(WORK / 'build/csf-validate.json', {
        'front': 'skill-trees',
        'format': 'Custom Skills Framework 3.x（SKSE/Plugins/CustomSkills/<Name>.json）',
        'menu_name': 'StatsMenu（CSF 沿用原版 StatsMenu，見 CustomSkills.dll 的 MenuSetup 修補字串）',
        'layout': {
            'lane_step': LAYOUT_LANE_STEP, 'tier_y_step': TIER_Y_STEP,
            'x_bounds': LAYOUT_X_BOUNDS, 'y_bounds': LAYOUT_Y_BOUNDS,
            'min_spacing': LAYOUT_MIN_SPACING, 'branch_dy': 0.0,
            'note': 'x 正值往左、y 正值往上；主線→下一階主線、主線→同階分支',
        },
        'totals': {
            'files': len(files),
            'valid': len(files) - len(bad),
            'nodes': sum(f['node_count'] for f in files),
            'main_nodes': sum(f['main_nodes'] for f in files),
            'branch_nodes': sum(f['branch_nodes'] for f in files),
            'max_nodes_per_skill': max(f['node_count'] for f in files),
            'node_limit': 127,
        },
        'files': files,
    })
    if bad:
        raise SystemExit(f'CSF config validation failed: {[f["tree"] for f in bad]}')
    print(f'LAYOUT ok: trees={len(files)}/13 x=[-4.5,4.5] y=[0,4.5] '
          f'min_spacing={min(f["layout"]["min_spacing"] for f in files):.2f} >= {LAYOUT_MIN_SPACING}; '
          'tier order + route separation + mainline/branch links valid')
    return files


def compile_scripts():
    psc = OUT / 'Source/Scripts'
    pex = OUT / 'Scripts'
    psc.mkdir(parents=True, exist_ok=True)
    pex.mkdir(exist_ok=True)
    # 清掉原型遺留（ESSBPlayerAlias 等），讓白名單檢查成立。
    removed = []
    for folder, extension in [(psc, '.psc'), (pex, '.pex')]:
        keep = {n + extension for n in SCRIPTS}
        for p in folder.iterdir():
            if p.is_file() and p.name not in keep:
                p.unlink()
                removed.append(str(p.relative_to(OUT)))
    for name in SCRIPTS:
        (psc / (name + '.psc')).write_text((WORK / 'src' / (name + '.psc')).read_text(encoding='utf-8'),
                                           encoding='utf-8-sig')
    compiler = ROOT / 'MO2/mods/动作共存-Nemesis Unlimited Behavior Engine-动作刷新/Nemesis_Engine/Papyrus Compiler/PapyrusCompiler.exe'
    imports = ';'.join(str(p) for p in [WORK / 'vendor/compiler-api', WORK / 'vendor/imports', psc])
    results = []
    for name in SCRIPTS:
        command = [str(compiler), str(psc / (name + '.psc')), '-i=' + imports, '-o=' + str(pex),
                   '-f=' + str(WORK / 'vendor/imports/TESV_Papyrus_Flags.flg'), '-optimize']
        run = subprocess.run(command, cwd=WORK / 'build', capture_output=True, text=True,
                             encoding='utf-8', errors='replace')
        results.append({'script': name, 'exit_code': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr})
        print(f'  compile {name}: {"OK" if run.returncode == 0 else "FAILED"}')
        if run.returncode:
            print(run.stdout, run.stderr)
    dump(WORK / 'build/v03-compile-results.json', {'removed_stale': removed, 'results': results})
    if any(r['exit_code'] for r in results):
        raise SystemExit(1)
    missing = [n for n in SCRIPTS if not (pex / (n + '.pex')).is_file()]
    if missing:
        raise SystemExit(f'Missing PEX after compile: {missing}')
    return removed


def write_state_helpers():
    """ESSBState.psc: the controller quest lookup and generated constants. Round 22 removed the status rings and
    the swap backups (and with them every ring/backup helper); bleed and poison are engine DoTs the DLL applies."""
    lines = ['Scriptname ESSBState Hidden',
             '; Generated by build_v03.py. Change the constants there only.', '']
    lines += ['Quest Function ControllerQuest() Global',
              f'\tReturn Game.GetFormFromFile(0x{ID_QUEST:06X}, \"Elements Spellblade.esp\") as Quest',
              'EndFunction', '',
              'Bool Function Operational() Global', '\tQuest currentQuest = ControllerQuest()',
              '\tIf !currentQuest', '\t\tReturn False', '\tEndIf',
              '\tESSBController ctl = currentQuest.GetAlias(0) as ESSBController',
              '\tReturn ctl && ctl.IsOperational()', 'EndFunction', '',
              # MCM / menus (commander ruling): the controller is ready, whatever the master switch says.
              'Bool Function ReadyUI() Global', '\tQuest currentQuest = ControllerQuest()',
              '\tIf !currentQuest', '\t\tReturn False', '\tEndIf',
              '\tESSBController ctl = currentQuest.GetAlias(0) as ESSBController',
              '\tReturn ctl && ctl.IsReadyUI()', 'EndFunction', '']
    attribution = json.loads((WORK / 'settings.json').read_text(encoding='utf8')).get('kill_attribution_seconds', 3.0)
    assert isinstance(attribution, (int, float)) and not isinstance(attribution, bool) and math.isfinite(attribution) and attribution >= 0, 'invalid kill_attribution_seconds'
    lines += ['Float Function KillAttributionSeconds() Global', f'\tReturn {float(attribution)}', 'EndFunction', '']
    lines += ['Spell Function GuardWindowSpell(Int aiIndex) Global',
              '\tIf aiIndex < 0 || aiIndex >= 9', '\t\tReturn None', '\tEndIf',
              f'\tReturn Game.GetFormFromFile(0x{ID_GUARD_WINDOW + 1:06X} + aiIndex * 2, "Elements Spellblade.esp") as Spell',
              'EndFunction', '']
    (WORK / 'src/ESSBState.psc').write_bytes('\r\n'.join(lines).encode('utf-8'))


def validate_status_arrays():
    """Round 22 retired validate_dot_state (it executed ESSBStatus' rings and the controller's swap banks, both
    deleted with the status container). What stays checkable offline: every Papyrus array literal is <= 128, no
    script still carries the container, and the round-4 settings are unchanged. The status layer itself is checked
    by the native tests (native/tests, build/fix22_reference.py) and build/fix22_verify.py."""
    arrays = []
    for name in SCRIPTS:
        source = (WORK / 'src' / (name + '.psc')).read_text(encoding='utf-8')
        for size in re.findall(r'(?i)\bnew\s+\w+\[(\d+)\]', source):
            assert 0 < int(size) <= 128, (name, size)
            arrays.append({'script': name, 'size': int(size)})
        for stale in ('ESSBStatus', 'ESSBMark', 'RegStatus', 'PendingStacks', 'BackupInts', 'SwapHosts'):
            assert not re.search(r'\b' + stale + r'\b', source), (name, stale)
    assert not (WORK / 'src/ESSBStatus.psc').exists() and not (WORK / 'src/ESSBMark.psc').exists()
    settings = json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))
    previous = json.loads((WORK / '.codex/pre-fix5-snapshot/settings.json').read_text(encoding='utf-8'))
    assert all(settings.get(k) == v for k, v in previous.items()), 'round 4 settings must remain unchanged'
    dump(WORK / 'build/fix22-array-check.json', {
        'retired': 'validate_dot_state (status rings and swap banks deleted in round 22)',
        'array_allocations': arrays, 'max_array': max(a['size'] for a in arrays),
    })
    print(f'ARRAYS ok: {len(arrays)} Papyrus array literals, max {max(a["size"] for a in arrays)} <= 128; '
          'no status container left in any script')


NODE_SCALE_RANGE = (1.0, 5.0)   # 裁決 R3：MCM 節點倍率 1–5，預設 3（settings.json node_percent_scale）


def write_mcm(manifest):
    settings = json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))
    def ref(edid):
        return f"{PLUGIN}|{manifest[edid]['id']}"
    def control(edid, label, kind, **options):
        if kind == 'slider':
            label += f"（預設 {options['defaultValue']:.6g}）"
        return {'id': edid, 'text': label, 'type': kind,
                'valueOptions': {'sourceType': 'GlobalValue', 'sourceForm': ref(edid), **options}}
    general = [
        control('ESSB_Enabled', '元素魔戰士總開關', 'toggle', defaultValue=int(settings['enabled'])),
        control('ESSB_PoisonDotK', '毒層係數', 'slider', min=0.0, max=1.0, step=0.001,
                formatString='{3}', defaultValue=settings['poison_dot_k']),
        control('ESSB_BleedDotK', '流血係數', 'slider', min=0.0, max=1.0, step=0.001,
                formatString='{3}', defaultValue=settings['bleed_dot_k']),
    ]
    general[1]['help'] = f'每層獨立維持 {POISON_LAYER_SECONDS} 秒；固定桶壽命不受持續時間倍率影響。'
    general[2]['help'] = f'每層維持 {BLEED_LAYER_SECONDS} 秒，命中刷新血痕；固定桶壽命不受持續時間倍率影響。'
    balance = []
    for edid, label, help_text in [
        ('ESSB_BaseDamageMult', '傷害倍率', '所有傷害；持續傷害另乘持續傷害倍率。'),
        ('ESSB_NodeScale', '節點倍率', '調整吃節點倍率的百分比主線（1–5，預設 3）；節點文字顯示建置預設倍率。'),
        ('ESSB_MultDot', '持續傷害', '毒、血、催毒、死域與血潮剩餘流血傷害。'),
        ('ESSB_MultCooldown', '冷卻', '乘上冷卻秒數；0.5 為一半冷卻。每秒輪詢的效果仍受 tick 精度限制。'),
        ('ESSB_MultRecovery', '回復', '生命、魔力、耐力與護盾；神佑固定 1 HP。'),
        ('ESSB_MultDrain', '削減', '敵方魔力、耐力、護甲削減；不改抗性削減與沉默鎖零。'),
        ('ESSB_MultDuration', '持續時間', '印記、狀態與領域，最短 1 秒；毒血桶壽命與星痕引爆延遲固定。'),
    ]:
        low, high = NODE_SCALE_RANGE if edid == 'ESSB_NodeScale' else \
            (0.25, 2.0 if edid == 'ESSB_MultCooldown' else 3.0)
        knob = control(edid, label, 'slider', min=low, max=high, step=0.05,
                       formatString='{2} 倍', defaultValue=settings[ID_BALANCE_GLOB[edid][1]])
        knob['help'] = help_text
        balance.append(knob)
    upkeep = control('ESSB_MultUpkeep', '維持費', 'slider', min=0.0, max=3.0, step=0.1,
                     formatString='{1} 倍', defaultValue=settings['mult_upkeep'])
    upkeep['help'] = '形態魔力維持費與血形態維持扣血；0 為免費。血重擊費不變，魔力耗盡仍有 2 秒寬限後關閉。'
    balance.append(upkeep)
    trees = [
        {'type': 'hiddenToggle', 'groupControl': 1,
         'valueOptions': {'sourceType': 'PropertyValueBool', 'propertyName': 'AllowTreeEditing', 'defaultValue': False}},
        {'type': 'header', 'text': '技能樹等級', 'position': 0},
        {'type': 'header', 'text': '未用點數', 'position': 1},
    ]
    for index, (tree, label) in enumerate(zip(TREES, TREE_ZH)):
        for column, prefix in enumerate(('Lvl', 'Pts')):
            row = control(f'ESSB_{prefix}_{tree}', label, 'text', formatString='{0}')
            row.update(position=2 + index * 2 + column, groupCondition=1, groupBehavior='disable',
                       help='唯讀；投點請透過「元素魔戰士：技能樹」能力開啟技能樹。')
            trees.append(row)
    def button(name, label, function, help_text):
        return {'id': name, 'type': 'text', 'text': label, 'help': help_text,
                'action': {'type': 'CallFunction', 'form': ref('ESSB_MCMQuest'),
                           'scriptName': 'ESSBMCM', 'function': function}}
    native_toggle = control('ESSB_NativeWanted', 'DLL 命中附傷', 'toggle', defaultValue=1)
    native_toggle['help'] = '只控制 DLL 附傷；停用或 DLL 缺少時沒有命中附傷。總開關另控制整個模組。'
    native_toggle['action'] = {'type': 'CallFunction', 'form': ref('ESSB_MCMQuest'),
                               'scriptName': 'ESSBMCM', 'function': 'ApplyNativeSetting'}
    general += [native_toggle,
                control('ESSB_NativeHit', 'DLL 狀態（1=運作、0=未載入／停用／故障）', 'text', formatString='{0}'),
                button('ESSB_NativeVersionInfo', '查看 DLL 版本與狀態', 'ShowNativeStatus',
                       '顯示 native DLL 版本與是否處理命中；0 不會退回 entry 51。')]
    balance.append(button('ESSB_ReleaseDivineProtection', '解除神佑保護', 'ReleaseDivineProtection',
                          '確認後解除延遲死亡並停用模組，避免重新上鎖；卸載前請先解除並存檔。'))
    balance.append(button('ESSB_RestoreDefaults', '恢復預設設定', 'RestoreDefaults',
                          '確認後恢復全部平衡滑桿與一般頁毒層、流血係數的建置預設值。'))
    trees += [button('ESSB_RespecCurrent', '洗點：目前元素樹', 'RespecCurrent',
                     '確認後關閉目前形態，再洗原本的元素樹。需脫戰且冷卻結束；未開形態時為無元素樹。'),
              button('ESSB_RespecAll', '洗點：全部', 'RespecAll',
                     '確認後呼叫既有全部洗點；需脫戰、關閉形態，冷卻中的樹略過。')]
    debug = [control('ESSB_DebugLevel', '除錯等級', 'enum',
                     options=['0：關閉', '1：事件', '2：命中', '3：詳細'], defaultValue=settings['debug_level']),
             button('ESSB_DumpRegistry', '印出目標狀態', 'DumpRegistry',
                    '將附近帶印記的目標與你身上的狀態寫入 Papyrus 紀錄；遊戲需啟用 Papyrus logging 才會產生檔案。')]
    hotkeys = [control('ESSB_HotkeysEnabled', '直接切換熱鍵', 'toggle', defaultValue=1),
               control('ESSB_FormNotify', '切換文字提示', 'toggle', defaultValue=1),
               control('ESSB_FormSound', '切換音效', 'toggle', defaultValue=1)]
    hotkeys += [control('ESSB_Hotkey_'+n, label, 'keymap', defaultValue=hit18.KEY_CODES[i])
                for i,(n,label) in enumerate(zip(ELEMENTS,ZH))]
    config = {'modName': 'Elements Spellblade', 'displayName': '元素魔戰士',
              'pages': [{'pageDisplayName': '一般', 'cursorFillMode': 'topToBottom', 'content': general + debug},
                        {'pageDisplayName': '平衡', 'cursorFillMode': 'topToBottom', 'content': balance},
                        {'pageDisplayName': '技能樹', 'cursorFillMode': 'leftToRight', 'content': trees},
                        {'pageDisplayName': '熱鍵', 'cursorFillMode': 'topToBottom', 'content': hotkeys}]}
    folder = OUT / 'MCM/Config/Elements Spellblade'
    folder.mkdir(parents=True, exist_ok=True)
    dump(folder / 'config.json', config)
    # Generate reset writes from these exact slider defaults, never a second table.
    sliders = [r for p in config['pages'] for r in p['content'] if r.get('type') == 'slider']
    lines = ['; Generated MCM defaults: same rows as config.json and its GLOB equality gate.',
             'Function RestoreTunableDefaults() Global', '\tGlobalVariable knob']
    for row in sliders:
        lines += [f'\tknob = Game.GetFormFromFile(0x{manifest[row["id"]]["id"]}, "{PLUGIN}") as GlobalVariable',
                  f'\tknob.SetValue({row["valueOptions"]["defaultValue"]!r})']
    lines += ['EndFunction', '']
    helper = WORK / 'src/ESSBState.psc'
    raw = helper.read_bytes().split(b'; Generated MCM defaults:')[0]
    helper.write_bytes(raw + '\r\n'.join(lines).encode('utf8'))


def validate_mcm(records, written):
    """Validate generated JSON, ESP/VMAD linkage, optional dependencies and immutable IDs."""
    manifest = written['records']
    baseline = json.loads((WORK / '.codex/pre-fix5-snapshot/v03-formids.json').read_text(encoding='utf-8'))['records']
    assert all(state_schema.stable_identity(e, manifest.get(e), old) for e, old in baseline.items()), 'fix5 existing identities changed'
    added = {e: v for e, v in manifest.items() if e not in baseline and e not in SCHEMA_STUBS}
    assert set(added) == (hit18.new_edids(sys.modules[__name__]) | hit19.NEW_EDIDS | set(tree_v04.NEW_PERK_EDIDS)) | FIX5_NEW_EDIDS | GUARD_WINDOW_EDIDS | {e for e, (fid, _) in ID_BALANCE_GLOB.items() if fid >= 0x00515C}
    # round 21：47 個 v0.4 新分支 perk 放進分支區塊裡沒用過的格（裁決 R7：格位只增不回收）；其他新記錄一律往後加。
    new_perks = set(tree_v04.NEW_PERK_EDIDS)
    assert all(int(v['id'], 16) > max(int(old['id'], 16) for old in baseline.values())
               for e, v in added.items() if e not in new_perks)
    ever_used = {v['id'] for v in baseline.values()} | {v['id'] for v in json.loads(
        (WORK / '.codex/pre-fix21-snapshot/build/v03-formids.json').read_text(encoding='utf-8'))['records'].values()}
    assert all(ID_BRANCH_PERK <= int(manifest[e]['id'], 16) < ID_MAIN_PERK and manifest[e]['id'] not in ever_used
               for e in new_perks), 'a round-21 perk reuses a FormID or leaves the branch block'
    assert manifest['ESSB_DebugLevel']['id'] == '000811'
    path = OUT / 'MCM/Config/Elements Spellblade/config.json'
    raw = path.read_bytes()
    assert not raw.startswith(b'\xef\xbb\xbf')
    config = json.loads(raw.decode('utf-8'))
    assert config['modName'] == 'Elements Spellblade' and config['displayName'] == '元素魔戰士'
    assert [p['pageDisplayName'] for p in config['pages']] == ['一般', '平衡', '技能樹', '熱鍵']
    by_id = {m['id']: (edid, m) for edid, m in manifest.items()}
    refs, glob_edids, functions = [], set(), set()
    def visit(node, key=None):
        if isinstance(node, dict):
            assert not str(node.get('sourceType', '')).startswith('ModSetting'), node
            if node.get('sourceType') == 'GlobalValue':
                assert node.get('sourceForm'), node
            if node.get('type') == 'CallFunction':
                assert node['scriptName'] == 'ESSBMCM'
                assert node['form'] == f'{PLUGIN}|{ID_MCM_QUEST:06X}'
                functions.add(node['function'])
            for k, v in node.items():
                visit(v, k)
        elif isinstance(node, list):
            for child in node:
                visit(child, key)
        elif isinstance(node, str) and '|' in node:
            assert re.fullmatch(re.escape(PLUGIN) + r'\|[0-9A-Fa-f]{1,8}', node), node
            expected = {'sourceForm': 'GLOB', 'form': 'QUST'}.get(key)
            assert expected, (key, node)
            fid = f'{int(node.split("|")[1], 16):06X}'
            edid, record = by_id[fid]
            assert record['type'] == expected, (edid, expected)
            refs.append({'reference': node, 'edid': edid, 'expected_type': expected})
            if expected == 'GLOB':
                glob_edids.add(edid)
    visit(config)
    expected_globals = {'ESSB_Enabled', 'ESSB_BaseDamageMult', 'ESSB_PoisonDotK', 'ESSB_BleedDotK', 'ESSB_DebugLevel', 'ESSB_NodeScale'}
    expected_globals |= {f'ESSB_{prefix}_{tree}' for tree in TREES for prefix in ('Lvl', 'Pts')}
    expected_globals |= {'ESSB_Mult' + n for n in ('Dot', 'Cooldown', 'Recovery', 'Drain', 'Duration', 'Upkeep')}
    expected_globals |= {'ESSB_Hotkey_'+n for n in ELEMENTS} | {'ESSB_HotkeysEnabled','ESSB_FormNotify','ESSB_FormSound'}
    expected_globals |= hit19.NATIVE_GLOBALS
    assert glob_edids == expected_globals and len(glob_edids) == 54
    assert functions == {'RespecCurrent', 'RespecAll', 'DumpRegistry', 'RestoreDefaults', 'ReleaseDivineProtection', 'ApplyNativeSetting', 'ShowNativeStatus'}
    rows = config['pages'][2]['content']
    tree_rows = [r for r in rows if r.get('id') in expected_globals]
    assert len(tree_rows) == 26
    assert all(r['type'] == 'text' and r['groupCondition'] == 1 and r['groupBehavior'] == 'disable'
               and 'action' not in r for r in tree_rows)
    assert rows[0]['type'] == 'hiddenToggle' and rows[0]['valueOptions']['propertyName'] == 'AllowTreeEditing'
    general = {r['id']: r for page in config['pages'][:2] for r in page['content']}
    assert [p['pageDisplayName'] for p in config['pages']] == ['一般', '平衡', '技能樹', '熱鍵']
    assert [r['text'].split('（')[0] for r in config['pages'][1]['content'] if r.get('type') == 'slider'] == ['傷害倍率', '節點倍率', '持續傷害', '冷卻', '回復', '削減', '持續時間', '維持費']
    for row in config['pages'][1]['content']:
        if row.get('type') != 'slider':
            continue
        v = row['valueOptions']
        bounds = (0.0, 3.0, 0.1) if row['id'] == 'ESSB_MultUpkeep' else \
            (*NODE_SCALE_RANGE, 0.05) if row['id'] == 'ESSB_NodeScale' else \
            (0.25, 2.0 if row['id'] == 'ESSB_MultCooldown' else 3.0, 0.05)
        assert (v['min'], v['max'], v['step']) == bounds
        assert v['min'] <= v['defaultValue'] <= v['max']
    node = general['ESSB_NodeScale']['valueOptions']
    assert (node['min'], node['max'], node['step']) == (1.0, 5.0, 0.05)   # 裁決 R3
    assert node['defaultValue'] == json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))['node_percent_scale'] == 3.0
    base = general['ESSB_BaseDamageMult']['valueOptions']
    assert (base['min'], base['max'], base['step']) == (0.25, 3.0, 0.05)
    for name in ('ESSB_BaseDamageMult', 'ESSB_PoisonDotK', 'ESSB_BleedDotK'):
        v = general[name]['valueOptions']
        assert v['min'] <= v['defaultValue'] <= v['max'] and v['step'] > 0
    by_edid = {r.edid: r for r in records}
    defaults_checked = 0
    for row in general.values():
        if row.get('type') == 'slider':
            expected = struct.unpack('<f', F(row['valueOptions']['defaultValue']))[0]
            actual = struct.unpack('<f', by_edid[row['id']].d['FLTV'])[0]
            assert actual == expected, ('MCM/GLOB defaults mismatch', row['id'], actual, expected)
            defaults_checked += 1
    assert defaults_checked == 10
    print('MCM DEFAULTS ok: all 10 tunable sliders equal ESP GLOB float32 defaults from settings.json')
    quest = by_edid['ESSB_MCMQuest']
    expected_vmad = vmad('ESSBMCM', {'Controller': (1, own(ID_QUEST)), 'ModName': (2, 'Elements Spellblade')}) + b'\x02' + struct.pack('<3H', 0, 0, 1) + obj(own(ID_MCM_QUEST), 0) + struct.pack('<3H', 5, 2, 1) + script('SKI_PlayerLoadGameAlias', {})
    assert quest.d['ALFR'] == I(ref('Skyrim.esm', 0x14))
    assert quest.sig == 'QUST' and quest.d['VMAD'] == expected_vmad
    assert struct.unpack_from('<H', quest.d['DNAM'])[0] == 0x11
    assert (OUT / 'SEQ/Elements Spellblade.seq').read_bytes() == I(own(ID_QUEST)) + I(own(ID_MCM_QUEST))
    menu = by_edid['ESSB_SettingsMenu']
    labels = [value.rstrip(b'\x00').decode('utf-8') for tag, value in menu.ss if tag == 'ITXT']
    assert labels == ['元素樹', '通用樹', '關閉'], labels
    bridge = (WORK / 'src/ESSBMCM.psc').read_text(encoding='utf-8')
    assert 'Bool Property AllowTreeEditing = False AutoReadOnly' in bridge
    for name in functions:
        assert f'Function {name}()' in bridge
    assert bridge.count('ShowMessage(') == 5 and 'trees.Respec(tree)' in bridge and 'trees.RespecAll()' in bridge
    assert 'ctl.DumpStatus()' in bridge and 'OpenTree(' not in bridge   # round 22: no registry, the DLL's statuses
    assert bridge.index('Int tree = trees.CurrentTree()') < bridge.index('ctl.CloseForm()') < bridge.index('trees.Respec(tree)')
    assert 'If tree < 11 && !Game.GetPlayer().IsInCombat() && trees.RespecReady(tree)' in bridge
    assert all('ESSBMCM' not in (WORK / 'src' / f'{name}.psc').read_text(encoding='utf-8') for name in SCRIPTS if name != 'ESSBMCM')
    assert not list(OUT.glob('Interface/Translations/*'))
    assert not (path.parent / 'settings.ini').exists()
    for name in ('MCM_ConfigBase', 'SKI_ConfigBase', 'SKI_QuestBase'):
        (WORK / 'vendor/imports' / f'{name}.psc').read_bytes().decode('ascii')
        assert not list(OUT.rglob(f'{name}.*')), f'compiler stub shipped: {name}'
    for root, suffix in [('Scripts', '.pex'), ('Source/Scripts', '.psc')]:
        assert {p.stem for p in (OUT / root).glob('*' + suffix)} == set(SCRIPTS)
        assert all(p.name.startswith('ESSB') for p in (OUT / root).iterdir())
    dump(WORK / 'build/fix5-mcm-check.json', {
        'json': str(path.relative_to(OUT)), 'references': refs,
        'existing_unchanged': len(baseline), 'new_records': added, 'masters': MASTERS,
        'read_only_trees': 13, 'actions': sorted(functions), 'translations': False, 'mod_settings': False,
        'runtime_tested': False,
    })
    print(f'MCM ok: UTF-8 JSON; {len(refs)} refs resolved (54 GLOB + 7 QUST); 13 read-only trees; '
          f'{len(functions)} actions; existing non-quest IDs unchanged; baseline={len(baseline)}; appended QUST=0x{ID_MCM_QUEST:06X}; soft dependencies')


def apply_fix8_decisions(plan):
    """fix8 的使用者核准決定，在 v0.4 由 plan_trees.classify_main 直接套用（v0.4 表格自己寫了「不吃節點倍率」）；
    這裡只確認 13 個決定都還在：11 個元素的開印效果吃節點倍率、血的新手主線只縮放流血每層傷害、
    地震耐力削減不吃節點倍率。v0.3 的第 14 個（無形態終結真傷係數）v0.4 已沒有這個節點（無形態大師是「不竭」）。"""
    settings = json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))
    scale = settings['node_percent_scale']
    resolved = 0
    for tree in plan['trees']:
        for route in tree['routes']:
            for tier in route['tiers']:
                key = (tree['id'], route['index'], tier['index'])
                old = tier['main_original']
                if tree['id'] in TREES[:11] and key[1:] == (1, 4):
                    assert tier['main_label'] == '開印效果' and tier['balance_class'] == 'SCALED', key
                elif key == ('blood', 0, 0):
                    assert tier['balance_class'] == 'SCALED' and '放血係數 +0.01%／點' in tier['main'], key
                elif key == ('earth', 2, 2):
                    assert tier['balance_class'] == 'UNCHANGED' and tier['main'] == old, key
                    resolved += 1
                    continue
                else:
                    continue
                assert tier['main'] == re.sub(r'\+([\d.]+)%／點',
                                              lambda m: f'+{float(m[1]) * scale:g}%／點', old, count=1), key
                resolved += 1
    assert resolved == 13
    return plan


def main():
    hit19.require_fresh(sys.modules[__name__])  # fail before touching the release when native is missing/stale
    state_schema.preflight()
    write_state_helpers()
    validate_status_arrays()
    plan = apply_fix8_decisions(plan_trees.build())
    dump(WORK / 'build/plan-tree-nodes.json', plan)
    plan_totals = plan['totals']
    assert plan_totals['trees'] == 13 and plan_totals['routes'] == 39 and plan_totals['tiers'] == 195, plan_totals
    new_perk_edids(plan)
    identity = fix21_identity.run(sys.modules[__name__])   # 名稱 ↔ 格位：Papyrus、DLL、ESP 進入點（裁決 R7、成果 2）
    count, size, groups, manifest, entry_count, fx_bundle = build_esp(plan)
    fx_records, fx_closure, fx_report, fx_index, fx_bindings = fx_bundle
    fx_count, fx_counts = write_fx_bindings(fx_records, fx_closure, fx_report, fx_index, fx_bindings)
    coverage, coverage_deferred = write_coverage()
    plan_rows, plan_status, plan_deferred = write_plan_coverage(plan, manifest)
    csf = write_csf(plan, manifest)
    write_mcm(manifest)
    removed = compile_scripts()
    hit19.package(sys.modules[__name__])
    dump(WORK / 'build/v03-package-hashes.json',
         {str(p.relative_to(OUT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(OUT.rglob('*')) if p.is_file()})

    # 獨立回讀驗證：重新解析剛剛寫出的 ESP。
    written = json.loads((WORK / 'build/v03-formids.json').read_text(encoding='utf-8'))
    check, meta = read_plugin(OUT / PLUGIN)
    assert meta['masters'] == MASTERS, f'masters mismatch: {meta["masters"]}'
    assert meta['flags'] & 0x200 == 0, 'plugin is ESL-flagged'
    assert len(check) == written['record_count'] == count, f'record count mismatch {len(check)} vs {count}'
    assert len({r.key for r in check}) == count, 'duplicate FormIDs on readback'
    by_edid = {r.edid for r in check}
    assert by_edid == set(written['records']), 'EDID set mismatch'
    delivery = validate_delivery(check)
    assert written['records']['ESSB_DebugLevel']['id'] == '000811'
    baseline_path = WORK / 'build/fix-round-baseline.json'
    if baseline_path.is_file():
        baseline = json.loads(baseline_path.read_text(encoding='utf-8'))['manifest']['records']
        changed_ids = [edid for edid, old in baseline.items()
                       if not state_schema.stable_identity(edid, written['records'].get(edid), old)]
        assert not changed_ids, f'existing FormIDs changed: {changed_ids}'
    fix2_path = WORK / '.codex/pre-fix2-snapshot/v03-formids.json'
    if fix2_path.is_file():
        fix2_records = json.loads(fix2_path.read_text(encoding='utf-8'))['records']
        assert all(state_schema.stable_identity(e, written['records'].get(e), old) for e, old in fix2_records.items()), \
            'fix round 2 existing record identities changed'
    state_schema.verify(check, written['records'], sys.modules[__name__])
    validate_fix3(check, written, fx_bindings)
    validate_fix4(check, written)
    validate_mcm(check, written)
    import runpy
    runpy.run_path(str(WORK / 'build/fix6_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix7_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix8_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix9_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix10_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix11_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix12_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix13_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix14_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix15_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix16_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix18_verify.py'))['run']()
    hit19.verify(sys.modules[__name__])
    runpy.run_path(str(WORK / 'build/fix20_verify.py'))['run']()
    runpy.run_path(str(WORK / 'build/fix21_verify.py'))['run'](sys.modules[__name__])   # round 21: R2, entries, retired, R3
    runpy.run_path(str(WORK / 'build/fix22_verify.py'))['run'](sys.modules[__name__])   # round 22: seam, removals, records, guards, faults
    runpy.run_path(str(WORK / 'build/fix23_verify.py'))['run'](sys.modules[__name__])   # round 23: seam, removals, records, resolve, guards, faults, seals
    runpy.run_path(str(WORK / 'build/fix18_probes.py'))['run'](sys.modules[__name__])
    perks = sum(1 for r in check if r.sig == 'PERK')
    print(f'READBACK ok: masters={meta["masters"]} records={len(check)} manifest={written["record_count"]} '
          f'esl=False groups={groups} bytes={size} scripts={len(SCRIPTS)} stale_removed={len(removed)} '
          f'coverage={coverage} perks={perks} perk_entry_points={entry_count}')
    print(f'PLAN ok: trees={plan_totals["trees"]} routes={plan_totals["routes"]} tiers={plan_totals["tiers"]} '
          f'main_rank_perks={plan_totals["main_rank_perks"]} branch_nodes={plan_totals["branch_nodes"]}')
    print(f'CSF ok: files={len(csf)} valid={sum(1 for f in csf if f["perk_refs_resolved"])} '
          f'nodes={sum(f["node_count"] for f in csf)} max_nodes={max(f["node_count"] for f in csf)}/127')
    print(f'DELIVERY ok: Contact={len(delivery[1])} Self={len(delivery[0])}; '
          'SPEL SPIT + every referenced MGEF DATA agree; non-quest FormIDs stable (SCHEMA checked)')
    print(f'PLAN COVERAGE ok: rows={plan_rows} unmapped=0 by_status={plan_status}')
    print(f'PLAN COVERAGE deferred: {len(plan_deferred)}')
    for row in plan_deferred:
        print(f'  DEFERRED {row["edid"]} {row["text"]} :: {row["note"]}')
    print(f'NODE INDEX ok: {identity["papyrus_reads"]} ESSBNodes.Rank/Br reads resolved by v0.4 name against '
          f'build/plan-tree-nodes.json (build/fix21_identity.py; {len(identity["self_test"])} injected faults caught)')
    print(f'FX ok: copied={fx_count} records into 0x{ID_FX_BASE:06X}+ by_type={fx_counts} '
          f'selectors={fx_closure["selectors"]} '
          f'nulled={sum(1 for r in fx_report if r.get("action") == "null")} '
          f'dropped_subrecords={sum(len(e["dropped"]) for e in fx_records)} '
          f'extra_masters={fx_closure["extra_masters"]} (dropped/nulled so masters stay {MASTERS})')
    print(f'ENGINE COVERAGE ok: items={coverage} deferred={coverage_deferred} '
          f'deferred_optional={len(DEFERRED_OPTIONAL)}')


def validate_fix4(records, written):
    """Read back the three knobs, bound B arrays and immutable record identities."""
    baseline = json.loads((WORK / '.codex/pre-fix4-snapshot/v03-formids.json').read_text(encoding='utf-8'))['records']
    current = written['records']
    assert all(state_schema.stable_identity(e, current.get(e), v) for e, v in baseline.items()), 'fix4 existing identities changed'
    added = {e: v for e, v in current.items() if e not in baseline and e not in SCHEMA_STUBS}
    assert set(added) == set(ID_BALANCE_GLOB) | FIX5_NEW_EDIDS | GUARD_WINDOW_EDIDS | (hit18.new_edids(sys.modules[__name__]) | hit19.NEW_EDIDS | set(tree_v04.NEW_PERK_EDIDS)), added
    highest = max(int(v['id'], 16) for v in baseline.values())
    by_edid = {r.edid: r for r in records}
    quest = by_edid['ESSB_MainQuest'].d['VMAD']
    settings = json.loads((WORK / 'settings.json').read_text(encoding='utf-8'))
    values = {}
    for name, (fid, key) in ID_BALANCE_GLOB.items():
        r = by_edid[name]
        assert highest < fid == int(added[name]['id'], 16)
        assert r.sig == 'GLOB' and r.d['FNAM'] == b'f'
        value = struct.unpack('<f', r.d['FLTV'])[0]
        assert math.isclose(value, settings[key], rel_tol=1e-6, abs_tol=1e-8)
        binding = vstr(name.removeprefix('ESSB_')) + bytes([1, 1]) + obj(own(fid))
        assert quest.count(binding) == 1, name
        values[key] = value
    for prop, index in [('ElementDamageMin', 0), ('ElementDamageMax', 1)]:
        expected = [settings['element_damage'][name][index] for name in ELEMENTS]
        binding = vstr(prop) + bytes([14, 1]) + I(11) + struct.pack('<11f', *expected)
        assert quest.count(binding) == 1, prop
    dump(WORK / 'build/fix4-readback.json', {
        'existing_unchanged': len(baseline), 'new_records': added,
        'globals': values, 'element_damage': settings['element_damage'],
        'tree1_neutral_poison_dps': settings['element_damage']['Poison'][1] * values['poison_dot_k'] * 1.05,
        'tree1_neutral_bleed_dps': settings['element_damage']['Blood'][1] * values['bleed_dot_k'] * 1.05,
    })
    print(f'FIX4 ok: existing non-quest IDs unchanged; baseline={len(baseline)}; {len(ID_BALANCE_GLOB)} float GLOBs verified (3 fix4 + 12 fix6 + 5 fix7 + 1 fix8); VMAD knobs + B arrays verified')


def validate_fix3(records, written, bindings):
    """Independent ESP readback: identities, actual binding bytes and long-lived FX."""
    snapshot = WORK / '.codex/pre-fix3-snapshot/v03-formids.json'
    baseline = json.loads(snapshot.read_text(encoding='utf-8'))['records']
    current = written['records']
    assert all(state_schema.stable_identity(e, current.get(e), v) for e, v in baseline.items()), 'fix3 existing FormIDs changed'
    new = {e: v for e, v in current.items() if e not in baseline and e not in SCHEMA_STUBS and e not in ID_BALANCE_GLOB and e not in FIX5_NEW_EDIDS and e not in GUARD_WINDOW_EDIDS and e not in (hit18.new_edids(sys.modules[__name__]) | hit19.NEW_EDIDS | set(tree_v04.NEW_PERK_EDIDS))}
    highest = max(int(v['id'], 16) for v in baseline.values()
                  if ID_FX_BASE <= int(v['id'], 16) < ID_FX_LIMIT)
    assert all(highest < int(v['id'], 16) < ID_FX_LIMIT for v in new.values()), 'FX not appended'
    by_edid = {r.edid: r for r in records}
    by_id = {int(r.key.split('|')[1], 16): r for r in records}
    visibility = []
    settings = fx_settings(json.loads((WORK / 'settings.json').read_text(encoding='utf-8')))
    for row in bindings['elements']:
        name = row['element']
        for role, host, field in [('aura', f'ESSB_FormAbilityEffect_{name}', 'aura_shader'),
                                  ('mark', f'ESSB_MarkEffect_{name}', 'mark_shader')]:
            effect = by_edid[host]
            shader_id = struct.unpack_from('<I', effect.d['DATA'], 32)[0] & 0xFFFFFF
            if role == 'aura':
                assert shader_id == 0 and struct.unpack_from('<I', effect.d['DATA'], 36)[0] == 0
                continue
            shader = by_id[shader_id]
            assert shader.sig == 'EFSH' and shader.edid == row[field], (host, field)
            assert struct.unpack_from('<I', effect.d['DATA'])[0] & 0x1000, host
            assert row[role + '_source'] == settings['fx_' + role][name]
            if role == 'mark':
                audit = efsh_visibility(shader.ss)
                assert audit['persistent_edge_visible'], (host, audit)
                visibility.append({'host': host, 'shader': shader.edid, **audit})
        spell = by_edid[f'ESSB_MarkSpell_{name}']
        assert struct.unpack_from('<I', spell.d['EFIT'], 8)[0] == 8  # Water runtime override remains 10.
    for host in ('ESSB_ManaBreakEffect', 'ESSB_SilenceEffect'):
        effect = by_edid[host]
        assert struct.unpack_from('<I', effect.d['DATA'])[0] & 0x1000
        shader = by_id[struct.unpack_from('<I', effect.d['DATA'], 32)[0] & 0xFFFFFF]
        audit = efsh_visibility(shader.ss)
        assert audit['persistent_edge_visible'] and audit['ambient_sound'] == '00000000'
        visibility.append({'host': host, 'shader': shader.edid, **audit})
    frozen = by_edid['ESSBFX_Status_Frozen']
    assert efsh_visibility(frozen.ss)['persistent_edge_visible']
    # Round 22: the frozen film is the Hit Shader (+ FX Persist) of the DLL's 冰封 effect, not a status-container
    # script property; the retired container carries no script at all.
    frozen_effect = by_edid[hit22.edid_effect('Frozen')]
    assert struct.unpack_from('<I', frozen_effect.d['DATA'])[0] & 0x1000
    assert struct.unpack_from('<I', frozen_effect.d['DATA'], 32)[0] == own(int(frozen.key.split('|')[1], 16))
    assert 'VMAD' not in by_edid['ESSB_StatusHostEffect'].d
    for r in records:
        if r.edid.startswith('ESSBFX_'):
            for _, _, fid, label in fx_extract.slots(r):
                assert not fid or fid >> 24 in (0, 1), (r.edid, label, hex(fid))
                if fid >> 24 == 1:
                    assert (fid & 0xFFFFFF) in by_id, (r.edid, label, hex(fid))
    dump(WORK / 'build/fix3-readback.json', {
        'existing_unchanged': len(baseline), 'new_records': new,
        'highest_previous_fx_id': f'{highest:06X}', 'debug_id': current['ESSB_DebugLevel']['id'],
        'marks_and_status': visibility, 'frozen': efsh_visibility(frozen.ss),
    })
    print(f'FIX3 ok: existing non-quest IDs unchanged; baseline={len(baseline)} new={len(new)} appended after 0x{highest:06X}; '
          f'11 aura removed + 33 weapon-glow tiers + 11 persistent marks + 3 status visuals; DebugLevel=0x000811')


def validate_delivery(records):
    """Read actual ESP bytes, including all effects of multi-effect spells."""
    by_key = {r.key: r for r in records}
    contact_names = {
        'ESSB_StatusHostSpell', 'ESSB_EngagedSpell', 'ESSB_TrueDamageSpell',
        'ESSB_ManaBreakSpell', 'ESSB_SilenceSpell', 'ESSB_AshSpell',
        'ESSB_FearSpell', 'ESSB_FrenzySpell', 'ESSB_ReanimateSpell', 'ESSB_StripSpell',
    }
    contact_names.update(f'ESSB_Util_{u[0]}' for u in UTILS if u[4])
    # Round 20: the DLL's own contact casts (soaked slow, fixed-duration silences); its self casts stay 0.
    contact_names.update({'ESSB_Native_SoakSlow'} | {hit20.silence_edid(s) for s in range(1, hit20.SILENCE_COUNT + 1)})
    # Round 21: the soaked slow of 1..30 s, 寂 and the 寂滅 marker are contact casts too.
    contact_names.update({hit21.soak_edid(s) for s in range(1, hit21.SOAK_MAX_SECONDS + 1)} | {'ESSB_Hush', 'ESSB_HushSpent'})
    # 冰甲's cloak payload is aimed (2), as every vanilla cloak payload; the cloak ability itself is self (0).
    aimed_names = {'ESSB_IceArmorChill', 'ESSB_IceArmorChillWide'}
    # Round 22: the status layer's target effects, the DoTs and 狂刃 are contact casts on the target (the miasma
    # cloak and its aimed payload went in the review fix); the player's ladders and windows are self casts.
    contact_names.update(hit22.contact_edids())
    contact_names.update(hit23.contact_edids())   # round 23: 誓約, the retort / grudge cooldowns, the last-hit-sneak marker
    aimed_names |= hit22.aimed_edids()
    groups = {0: [], 1: []}
    rows = []
    for record in records:
        if record.sig != 'SPEL':
            continue
        expected = 2 if record.edid in aimed_names else int(record.edid in contact_names or record.edid.startswith(
            ('ESSB_Hit_', 'ESSB_React_', 'ESSB_MarkSpell_', 'ESSB_UtilTarget_')))
        actual = struct.unpack_from('<I', record.d['SPIT'], 20)[0]
        assert actual == expected, (record.edid, 'SPEL delivery', actual, expected)
        effects = []
        for key in record.refs('EFID'):
            effect = by_key[key]
            value = struct.unpack_from('<I', effect.d['DATA'], 84)[0]
            assert value == expected, (record.edid, effect.edid, 'MGEF delivery', value, expected)
            effects.append(effect.edid)
        groups.setdefault(expected, []).append(record.edid)
        rows.append({'spell': record.edid, 'delivery': actual, 'effects': effects})
    dump(WORK / 'build/fix-round-delivery.json', {'valid': True, 'spells': rows,
         'contact': sorted(groups[1]), 'self': sorted(groups[0])})
    return groups


if __name__ == '__main__':
    main()

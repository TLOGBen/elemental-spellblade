"""Round 27 (G13): the visual cues of v0.4 2.11 / 2.12, where each one lives in the ESP, and a build check that the records
the player must see carry their visual fields. Run by build/fix27_verify.py on the written ESP (and on injected faults).

INVENTORY lists every cue: v0.4 source | the v0.3 asset | where it was lost | how round 27 restores it (or 未做 and why).
check(records, b) returns the errors; the verifier runs it on the ESP and on copies with one fault each.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (cue, v0.4 source, the v0.3 asset, lost in, restored with)
# (cue, v0.4 source -- 元素魔戰士規劃-v0.4.md at 481b8d6, section and line, the v0.3 asset, where it was lost, how round
# 27 / 27b restores it or 未做 and why). Round 27b: rewritten after review C (sources corrected, cues added).
INVENTORY = [
    ('形態光圈（開形態亮起、切換即時換色、關形態消失、同調 0／1／2／3 四檔）',
     '使用者 2026-09-27 決定取代 2.12 第 565–567、573 行的「武器光」（v0.4 由指揮官改寫）',
     '無（round 18 的武器光 ESSB_SyncWeaponEffect_<X>_<S> 從沒顯示；round 27 的 Enhance Weapon＋ENCH 已退役）',
     '—',
     'round 27b：ESSB_FormRingEffect_<X>_<0..3>，原版大師法術蓄力光圈（Skyrim.esm *CastBodyFX，FX*BodyHolder 的做法），'
     '依 ESSB_SyncStage == 段 四選一，MCM「形態光圈」。部分：原版每個學派只有一種光圈、沒有亮度或染色變體，四檔目前是同一個光圈'
     '（RING_ART 可逐段換），所以段數看不出亮度差；升段仍有 Charge_X 一聲'),
    ('開印：ZZArt_X 閃現＋Charge_X', '2.12 第 570 行（刷新版不播）',
     'ESSB_MarkEffect_<X> 的 Hit Effect Art＋SNDD（8／10 秒掛滿、每次刷新重播）', '設計錯位（放在持續的印記效果上）',
     'round 27：DLL 在開印（kOpen）時施放 ESSB_MarkFlash_<X>（1 秒、ZZArt_X、Charge_X）；印記效果只留持續的邊緣光'),
    ('印記期間的元素光', '2.11 第 542–555 行印記視覺欄（ESSBFX_Mark_<X>）', 'ESSB_MarkEffect_<X> Hit Shader＋FX Persist', '沒掉', '保留'),
    ('終焉：ZZExplosion_XHand1 一次＋印記 Art Object 消散', '2.12 第 571 行', 'PlaceFx 的元素爆炸；印記沒有 Art Object',
     '爆炸：round 24–26 目標已死就不放；消散：從未做',
     '爆炸：round 27 拿掉 IsDead 檢查。印記 Art 消散：未做（印記效果的 Art 已移到開印閃現；消散要另一個「消散」素材與結束時施放，列入下一輪）'),
    ('元素狀態著色（凍結、冰晶閃、血痕、催毒、浸濕、水壓、詛咒、星痕、死咒閃）', '2.12 第 572 行；2.11 第 542–555 行各元素的狀態素材',
     '只有冰封與火的熱度有著色', '其餘狀態從 round 22 建成時就沒有著色',
     'round 27：build/fix22_records.STATUS_SHADERS（2.11 點名的紀錄；層狀態常駐、冰晶與死咒一次閃）。部分：第 581 行「同一著色 0.5 秒內不重複套用」'
     '做不到——DLL 疊層是用新強度重新施放同一個法術，引擎換掉舊效果就重播著色；只改強度要寫 ActiveEffect 的記憶體（超出只寫 TESGlobal 的規則）'),
    ('每 3 層換更深的著色', '2.12 第 572 行', '無', '從未做',
     '未做：每種狀態要 3 階 EFSH 與層數條件（DLL 用強度記層數，條件函式讀不到），列入下一輪'),
    ('冰封、過熱引爆、死咒宣告、升闇星各一次專屬閃光', '2.12 第 572 行', '冰封：常駐冰封著色；死咒：一次閃（round 27）；其餘無', '從未做',
     '冰封（常駐著色）、死咒宣告（round 27 一次閃）已有；過熱引爆用下一列的爆炸代替；升闇星的一次閃光：未做（列入下一輪）'),
    ('冰封冰形聲（Winter Wonderland）、過熱（Vulcano）、死咒（Abyss）音效', '2.12 第 572 行音效欄', '無', '從未做', '未做：狀態效果沒有掛音效，列入下一輪'),
    ('碎冰、放電、過熱引爆、跌倒、吹飛各一次專屬爆炸或衝擊', '2.12 第 575 行', 'PlaceFx 的元素爆炸', 'round 24：DLL 自己結算的本體事件從不送 Papyrus',
     'round 27：碎冰、放電、過熱引爆由 RunOp → BodyFx → ESSB_Fx → PlaceFx 放一次。注意：用的是該元素通用的 ZZExplosion_XHand1（跟終焉同一個），'
     '不是各自專屬的爆炸。跌倒、吹飛：未做（推力由 Papyrus 做，沒有掛衝擊素材）'),
    ('熱度：武器泛紅＋頂階一聲', '2.12 第 572 行「你的熱度不上身體著色，只有武器光泛紅與頂階一聲」', '無', '從未做',
     '未做：武器光已換成光圈；讓火的光圈在高熱度時變紅要另一個原版紅色光圈加熱度條件（熱度是你身上的效果，不是全域變數），不便宜；頂階一聲維持'),
    ('闇星期間暗色（武器光改暗）', '2.11 第 554 行；5.13 第 1467 行', '無', '從未做',
     '未做：武器光已換成光圈；闇星時星的光圈改暗要另一組光圈與闇星條件，列入下一輪'),
    ('白熱／熔燒全身火焰', '2.12 第 574 行（你身上的資源唯一例外）', 'kHeat3／kHeat4／kMoltenBody 的 Vulcano DAR_MoltenFXShader', '沒掉', '保留'),
    ('命中衝擊組、命中著色與音效', '2.12 第 568–569 行', '附傷 MGEF 的 Impact Data Set、Hit Shader、SNDD', '沒掉', '保留（build_v03 FX front）'),
    ('領域看得見範圍（火、冰、聖、星）', '不是 v0.4 的提示（v0.4 沒寫領域的視覺）；round 27 額外加的', 'HAZD 模型 FXEmptyObject（看不見）',
     'round 25 改用引擎 Hazard 時', 'round 27／27b：原版危險區模型——火 FXFireOilHazard（27b 換較大的油火）、冰 IceHazard01（原版沒有更大的冰地面模型，比 3 公尺小）、'
     '聖 HealingHazard、星 LightSpellHazard；HAZD 沒有縮放欄位'),
    ('土、血、毒、水、暗的領域範圍', '同上（額外）', 'FXEmptyObject', 'round 25', '未做：原版沒有長得像的危險區模型（只有放置時一次爆炸）'),
]



def _u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def _local(fid):
    return fid & 0xFFFFFF


def check(records, b) -> list[str]:
    """The visual fields of the records the player must see. `records`: the ESP as tes.read_plugin reads it."""
    import fix18_records as hit18
    import fix22_records as hit22
    import fix25_records as hit25
    import fix27_records as hit27
    errors = []
    by_edid = {r.edid: r for r in records}
    by_local = {int(r.key.split('|')[1], 16): r for r in records if r.key.startswith(b.PLUGIN.casefold())}
    stage_global = by_edid.get('ESSB_SyncStage')
    glow_global = by_edid.get(hit27.WEAPON_GLOW_GLOBAL)
    if not stage_global or not glow_global or glow_global.sig != 'GLOB':
        errors.append('ESSB_SyncStage or ESSB_WeaponGlow missing')
        return errors
    stage_id, glow_id = int(stage_global.key.split('|')[1], 16), int(glow_global.key.split('|')[1], 16)
    retired = {int(r.key.split('|')[1], 16) for r in records if r.edid.startswith(('ESSB_WeaponGlowEnch', 'ESSB_SyncWeaponEffect_'))}
    for ix, name in enumerate(b.ELEMENTS):
        # 1. the form ring (round 27b): four effects, one per sync stage, each a constant self effect with the ring art
        #    (a Skyrim.esm ARTO) as its Hit Effect Art -- no shader, no enchantment, nothing on the weapon
        ability = by_edid.get(f'ESSB_FormAbility_{name}')
        ss = ability.ss if ability else []
        efids = [_u32(v, 0) for k, v in ss if k == 'EFID']
        if any(_local(x) in retired for x in efids):
            errors.append(f'ESSB_FormAbility_{name}: still uses a retired weapon-glow effect')
        rings = []
        for stage in range(hit27.RING_STAGES):
            effect = by_edid.get(f'ESSB_FormRingEffect_{name}_{stage}')
            if not effect:
                errors.append(f'{name} stage {stage}: the ring effect is missing')
                continue
            data = effect.d['DATA']
            art = _u32(data, 96)
            if _u32(data, 64) != 1 or _u32(data, 80) != 0 or _u32(data, 84) != 0 or _u32(data, 0) != hit27.RING_FLAGS:
                errors.append(f'{effect.edid}: not the vanilla holder pattern (archetype 1, constant, self, flags 0x9200)')
            if art >> 24 != 0 or _local(art) != hit27.ring_art(name, stage):
                errors.append(f'{effect.edid}: the Hit Effect Art is not the Skyrim.esm ring {hit27.ring_art(name, stage):06X}')
            if _u32(data, 8) or _u32(data, 32) or _u32(data, 36) or _u32(data, 116) or _u32(data, 124):
                errors.append(f'{effect.edid}: carries a shader, an enchantment or an enchant art (nothing may touch the weapon)')
            rings.append(int(effect.key.split('|')[1], 16))
        # each ring follows its EFID with exactly: GetGlobalValue(ESSB_SyncStage) == stage, GetGlobalValue(ESSB_WeaponGlow) == 1
        seen = []
        for i, (k, v) in enumerate(ss):
            if k != 'EFID' or _local(_u32(v, 0)) not in rings:
                continue
            conds = []
            for k2, v2 in ss[i + 1:]:
                if k2 == 'EFID':
                    break
                if k2 == 'CTDA':
                    conds.append((struct.unpack_from('<H', v2, 8)[0], _u32(v2, 12), v2[0] >> 5, struct.unpack_from('<f', v2, 4)[0]))
            stage = rings.index(_local(_u32(v, 0)))
            want = sorted([(b.FUNC_GET_GLOBAL_VALUE, b.own(stage_id), 0, float(stage)), (b.FUNC_GET_GLOBAL_VALUE, b.own(glow_id), 0, 1.0)])
            if sorted(conds) != want:
                errors.append(f'ESSB_FormAbility_{name}: ring {stage} conditions {conds}, not SyncStage == {stage} and 形態光圈 == 1')
            seen.append(stage)
        if sorted(seen) != list(range(hit27.RING_STAGES)):
            errors.append(f'ESSB_FormAbility_{name}: rings for stages {sorted(seen)}, not 0..3 once each')
        # 2. the mark: a persistent edge light, no art / sound (the open flash has them)
        mark = by_edid.get(f'ESSB_MarkEffect_{name}')
        if not mark or not _u32(mark.d['DATA'], 32) or not _u32(mark.d['DATA'], 0) & 0x1000:
            errors.append(f'ESSB_MarkEffect_{name}: no persistent Hit Shader')
        elif _u32(mark.d['DATA'], 96) or 'SNDD' in mark.d:
            errors.append(f'ESSB_MarkEffect_{name}: still carries the open art / sound (replayed on every refresh)')
        # 3. the open flash: ZZArt as Hit Effect Art, the Charge sound, a contact spell of 1 s
        flash_effect = by_edid.get(f'ESSB_MarkFlashEffect_{name}')
        flash = by_edid.get(f'ESSB_MarkFlash_{name}')
        if not flash_effect or not _u32(flash_effect.d['DATA'], 96) or not flash_effect.d.get('SNDD'):
            errors.append(f'ESSB_MarkFlashEffect_{name}: no art or no sound')
        elif _u32(flash_effect.d['DATA'], 0) & 0x1:
            errors.append(f'ESSB_MarkFlashEffect_{name}: hostile (a flash must start no fight)')
        if not flash or _u32(flash.d['SPIT'], 20) != 1:
            errors.append(f'ESSB_MarkFlash_{name}: not a contact spell')
    # 4. the status shadings
    for kind, selector, persist in hit22.STATUS_SHADERS:
        suffix = next(s for k, s, *_ in hit22.KINDS if k == kind)
        effect = by_edid.get(hit22.edid_effect(suffix))
        if not effect:
            errors.append(f'{kind}: effect missing')
            continue
        data = effect.d['DATA']
        shader = by_local.get(_local(_u32(data, 32)))
        if not shader or shader.sig != 'EFSH':
            errors.append(f'{effect.edid}: no Hit Shader ({selector})')
        elif bool(_u32(data, 0) & 0x1000) != persist:
            errors.append(f'{effect.edid}: FX Persist {"off" if persist else "on"} ({"a layered state stays" if persist else "a flash plays once"})')
    # 5. the domains a vanilla hazard model fits are seen
    for element, model in hit25.HAZARD_MODELS.items():
        hazard = by_edid.get(hit25.hazard_edid(element))
        got = hazard.d.get('MODL', b'').rstrip(b'\0').decode('ascii', 'replace') if hazard else None
        if got != model:
            errors.append(f'domain {element}: model {got!r}, not {model!r}')
    # 6. G14: every spell the DLL casts is No Absorb/Reflect; one-effect markers also Ignore Resistance; round 27b: every
    #    spell of ours delivered to someone else (the Papyrus casts too)
    no_absorb, markers = hit27.dll_spell_flags(b)
    for spell in records:
        if spell.sig == 'SPEL' and spell.key.startswith(b.PLUGIN.casefold()) and _u32(spell.d['SPIT'], 20) in (1, 2) \
                and not _u32(spell.d['SPIT'], 4) & hit27.NO_ABSORB:
            errors.append(f'{spell.edid}: delivered to others without No Absorb/Reflect (0x200000)')
    for fid in sorted(no_absorb):
        spell = by_local.get(fid)
        if not spell or spell.sig != 'SPEL':
            errors.append(f'{fid:06X}: a DLL spell missing')
            continue
        flags = _u32(spell.d['SPIT'], 4)
        if not flags & hit27.NO_ABSORB:
            errors.append(f'{spell.edid}: no No Absorb/Reflect (0x200000)')
        one = sum(1 for k, _ in spell.ss if k == 'EFID') == 1
        if fid in markers and one and not flags & hit27.IGNORE_RESIST:
            errors.append(f'{spell.edid}: a marker without Ignore Resistance (0x100000)')
    return errors


def check_papyrus(ctl: str) -> list[str]:
    """The Papyrus half: the end / open effects play on a target the DLL just killed; ESSB_Fx places the body bursts."""
    errors = []
    for event in ('OnESSBEnd', 'OnESSBOpen'):
        body = re.search(r'(?ms)^Event ' + event + r'\(.*?^EndEvent', ctl)
        if not body or 'IsDead()' in body[0]:
            errors.append(f'{event} still skips a dead target (the DLL\'s own damage kills it first)')
    fx = re.search(r'(?ms)^Event OnESSBFx\(.*?^EndEvent', ctl)
    if not fx or 'PlaceFx(' not in fx[0]:
        errors.append('OnESSBFx does not place the element\'s burst')
    if 'RegisterForModEvent("ESSB_Fx", "OnESSBFx")' not in ctl:
        errors.append('ESSB_Fx is not registered')
    return errors


def table() -> str:
    rows = ['| 提示 | v0.4 出處 | v0.3 素材 | 在哪裡掉的 | round 27 怎麼補 |', '|---|---|---|---|---|']
    rows += [f'| {a} | {b} | {c} | {d} | {e} |' for a, b, c, d, e in INVENTORY]
    return '\n'.join(rows)

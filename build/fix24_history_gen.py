"""Writes build/fix24_history.py: every round-24 change to the Papyrus sources, each bound to the code by digest.

Run after the round's Papyrus is final (python -B build/fix24_history_gen.py). The reasons are written here, by
function, so a regenerated seal can only restate them; the digests come from the pre-fix24 snapshot and the current
sources (build/fix21_history.digest: comment-stripped body, sha256[:16]).
"""
from pathlib import Path
import hashlib, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
import fix21_history as h21

SNAP = ROOT / '.codex/pre-fix24-snapshot/src'
SRC = ROOT / 'src'

R4_BODY = 'R4：反應本體（開印／終焉的傷害、削減、回復、各樹分支、範圍掃描）搬進 DLL（native/include/Reactions.h）'
R4_BURST = 'R4：融斷在 DLL（Reactions.h PlanBurst：一次掃描、每個印記 × K_sync × 融斷主線、寂與冷寂分支、回流、雙斷、安全閥）'
R4_DEATH = 'R4：死亡處理在 DLL 的死亡 sink（Reactions.h PlanDeath：化灰、亡者歸來、中毒死亡擴散、連殺、飲血、血承、不死、無魔…）；Papyrus 的擊殺掛勾刪除'
R4_ADVENT = 'R4：各元素的「臨」、臨強化、臨界、雙斷的再開印在 DLL（FormEnter → Reactions.h PlanAdvent）'
R4_HIT = 'R4：各樹命中當下的本體（震擊、護持、萎靡、侵蝕、詛咒的抗性侵蝕）在 DLL（Reactions.h PlanHitBodies）'
R4_EVENT = 'R4：本體事件（冰封、聖裁、濺血、越線、碎冰、落地、放電、風刃、死亡快照）不再送 Papyrus'
R4_PAPYRUS_HALF = 'R4：DLL 的本體留給 Papyrus 的那一半（推力、化灰崩解、復生 AI 與召喚上限、不解除潛行、領域）的新 ModEvent'
DEAD = '沒有呼叫者了（呼叫它的反應本體／擊殺掛勾搬進 DLL）'
BODY_HELPER = R4_BODY + '；這個數值讀取只給被刪掉的本體用'

REASONS = {
    'ESSBController.psc': {
        **{f: R4_DEATH for f in ['LastDamageFor', 'LastDamageWasElement', 'NoteDamageElement', 'ApplyTrackedDamage', 'ApplyInherit',
                                 'KillElementFor', 'HasMarkBit', 'OnKillEvent', 'HasDeathSnapshot', 'SettleKill', 'SettleStaleKills',
                                 'KillPending', 'SettleSneakKill', 'ArmKillProc', 'SettleKillProc', 'OnESSBDeath', 'LastHitWasSneak']},
        **{f: R4_EVENT for f in ['OnESSBDischarge', 'OnESSBBlade', 'OnESSBFrozen', 'OnESSBJudgment', 'OnESSBSplash', 'Splash',
                                 'OnESSBRise', 'OnESSBShatter', 'OnESSBLanding', 'OnLanding']},
        **{f: R4_PAPYRUS_HALF for f in ['OnESSBPush', 'OnESSBAsh', 'OnESSBRaise', 'OnESSBSneak', 'OnESSBDomain']},
        'ElementHitHook': R4_HIT, 'OnValidHitInternal': R4_HIT,
        'ForceOpenOn': R4_ADVENT + '（' + DEAD + '）',
        'SetDoubleBurst': R4_BURST + '（雙斷是你身上的 ESSB_N5_DoubleBurst）',
        'SetGuardBurst': R4_BURST + '（安全閥是你身上的 ESSB_N5_SafetyValve，PERK 讀它）',
        'SyncMult': R4_BURST + '（K_sync 在 DLL）',
        'ApplyTrueDamage': R4_BODY + '（星斷的真實傷害；' + DEAD + '）',
        'Execute': DEAD + '（round 21 起就沒有呼叫者；它用的擊殺歸因記錄刪除）',
        'GetBloodLeechRatio': BODY_HELPER + '（吸血比例在 DLL：HitMath.h LeechRatio）',
        'BloodLeechCurve': BODY_HELPER, 'Leech': BODY_HELPER, 'SpreadPoison': R4_BODY + '（淬毒的一劑擴散）',
        'GetAirborne': BODY_HELPER + '（空中追擊）',
        'SetBloodthirst': R4_DEATH + '（嗜血是 DLL 在飲血時掛在你身上的效果）',
        'GetBloodthirst': R4_DEATH + '（嗜血的 Papyrus 計時刪除；round 21 起就沒有呼叫者）',
        'BaseMax': 'ESSBReactions 刪除後，Papyrus 還在用的 B_max 讀值（領域的每秒傷害、聖臨強化）搬到控制器',
        'ReactDamage': 'ESSBReactions 刪除後，Papyrus 還在用的 D_react 本模組部分（死域的每秒傷害）搬到控制器',
        'ApplyDamage': R4_DEATH + '（擊殺掛勾的預測參數拿掉）',
        'ApplyDamageRaw': R4_DEATH + '（擊殺歸因記錄刪除，直接 DoCombatSpellApply）',
        'ApplyUtil': R4_DEATH + '（放血的擊殺歸因記錄刪除，直接 DoCombatSpellApply）',
        'GetDamageMult': R4_DEATH + '（嗜血的 Papyrus 計時刪除；嗜血由 DLL 的反應讀）',
        'InitFixState': R4_DEATH + '（擊殺快照、擊殺歸因、命中事實、擊殺預測的陣列不再配置）',
        'OnESSBEnd': R4_BODY + '；這裡只給經驗與終焉特效',
        'OnESSBOpen': R4_BODY + '；這裡只給經驗',
        'OnESSBHallucinate': R4_BODY + '（夢魘、群魔的範圍在 DLL）；群體事件控不到就跳過，不放幻視',
        'OnFormClosed': R4_BURST + '；ESSBNative.Burst(元素) 取代 BurstMarks(半徑, K)',
        'OnFormOpened': R4_ADVENT,
        'OnWeaponHit': R4_DEATH + '（命中事實環與致命潛行的奇襲風刃刪除：死掉的目標不會開印）',
        'ResetLoadClock': R4_DEATH + '；安全閥／雙斷／嗜血的 Papyrus 計時刪除',
        'Setup': R4_EVENT + '；' + R4_PAPYRUS_HALF + '；ESSBGuard 刪除',
        'Tick': R4_DEATH + '（空快照的保底結算刪除）',
        'TickDomain': 'ESSBReactions 刪除後改呼叫控制器的 ReactDamage（死域的每秒傷害）',
        'TickTimers': R4_BURST + '；安全閥、雙斷、嗜血的 Papyrus 計時刪除（它們是 DLL 的效果）',
        'TimersActive': R4_BURST + '；安全閥、嗜血的 Papyrus 計時刪除',
        'ValidateBindings': R4_DEATH + '（ESSBGuard 與舊血承法術的屬性刪除）',
        'IsEssentialTarget': '審查修正 2：2.9 必要角色＝essential（參照或本體）；有名字的敵人不豁免化灰、復生',
        'CanReanimate': '審查修正 2：復生只擋必要角色（IsEssentialTarget），不再擋 unique／protected',
        'ApplyAsh': '審查修正 2：化灰只擋必要角色（IsEssentialTarget），不再擋 unique／protected',
        'ApplyReanimate': '審查修正 3：僕從攻擊加成是復生法術的第二個效果（跟復生一起結束、不疊加），取代 ModActorValue',
        'ApplyStrip': '審查修正 1：WashBuffs 排進 DLL 的主執行緒 task，沒有回傳值（驅散數寫在 DLL log）',
        'DumpStatus': '審查修正 1：帶印記目標的清單改由 DLL 在主執行緒 task 裡掃描、寫進 DLL log（DumpTargets）',
        'NearestMarked': '審查修正 1：MarkedNear（在 VM 呼叫緒上掃描）刪除；這個函式本來就沒有呼叫者',
    },
    'ESSBElem.psc': {
        **{f: R4_BODY for f in ['EndMult', 'BurstMult', 'SignatureMult', 'OnOpen', 'OpenFire', 'OpenFrost', 'OpenShock', 'HeatBurstMult',
                                'Detonate', 'OnFrozen', 'OnShatter', 'Discharge', 'DischargeAll', 'OnEnd', 'EndFireNodes', 'EndFrostNodes',
                                'ShatterArea', 'EndShockNodes', 'ShockBurstBonus', 'FrostBurstShatter', 'ChargeCap', 'RoundStochastic']},
        'OnFormOpened': R4_ADVENT, 'OnKill': R4_DEATH + '（連鎖冰封）', 'OnCremation': R4_DEATH + '（火葬）',
        'OnFormOpenedExtra': R4_ADVENT + '；留在 Papyrus 的只剩氣旋與聖臨強化',
    },
    'ESSBElem2.psc': {
        **{f: R4_BODY for f in ['HolyVulnerability', 'HolyTierBonus', 'OnOpen', 'OpenEarth', 'OpenWind', 'OpenBlood', 'OpenDivine',
                                'FissureArmor', 'PullDistance', 'QuakeK', 'QuakeRadius', 'QuakeStamina', 'Quake', 'QuakeOne',
                                'WindBladeMult', 'WindBlade', 'WindBladeOne', 'BlowDistance', 'LandingDamage', 'BlowAway', 'SurgeHealMult',
                                'SurgePercent', 'JudgeK', 'Judge', 'IsHolyPrey', 'OnEnd', 'EndEarthNodes', 'EndWindNodes', 'EndBloodNodes',
                                'EndDivineNodes', 'JudgeArea', 'SurgeRadius']},
        **{f: R4_HIT for f in ['OnHit', 'OnEarthHit', 'OnWindHit', 'OnDivineHit']},
        **{f: R4_DEATH for f in ['OnKill', 'ShouldAsh', 'OnAsh', 'TryKillStreak']},
        'LethalAmbush': R4_DEATH + '（死掉的目標不會開印，v0.4 的奇襲要開印；round 16 的致命潛行風刃拿掉）',
        'OnFormOpened': R4_ADVENT + '（地臨強化、血臨強化）；留下氣旋與聖臨強化',
    },
    'ESSBElem3.psc': {
        **{f: R4_BODY for f in ['OnOpen', 'OpenPoison', 'OpenWater', 'OpenDark', 'OpenAstral', 'ApplyVirulence', 'DeathCurseSeconds',
                                'FallK', 'HasTrueBurst', 'Fall', 'FallHit', 'OnEnd', 'EndPoisonNodes', 'EndWaterNodes', 'EndDarkNodes',
                                'EndAstralNodes', 'WetSlow', 'WetSeconds']},
        **{f: R4_HIT for f in ['OnHit', 'OnPoisonHit', 'OnWaterHit', 'OnDarkHit', 'ApplyCurseErosion']},
        **{f: R4_DEATH for f in ['ReanimateTier', 'ReanimateCapOf', 'ReanimateSeconds', 'OnDeathSoul']},
        'AdventRadius': R4_ADVENT, 'OnFormOpened': R4_ADVENT + '（毒臨強化、水臨強化、暗臨強化、星臨強化）',
    },
    'ESSBNative.psc': {
        'Burst': R4_BURST + '（原生函式：取代 BurstMarks；審查修正 1：排進主執行緒 task，沒有回傳值）',
        'WashBuffs': '審查修正 1：排進主執行緒 task，沒有回傳值',
        'MarkedNear': '審查修正 1：在 VM 呼叫緒上掃描的原生函式刪除（DumpTargets 取代）',
        'DumpTargets': '審查修正 1：MCM 狀態按鈕的目標清單，主執行緒 task 掃描、寫 DLL log',
        **{f: R4_BODY + '（Papyrus 本體用的原生掛勾刪除，DLL 端的註冊一起拿掉）'
           for f in ['BurstMarks', 'SetGuided', 'DotRemaining', 'ForceOpen', 'EndMark', 'Shatter', 'Detonate']},
    },
    'ESSBNoForm.psc': {
        'BurstMult': R4_BURST, 'BurstRadius': R4_BURST,
        'OnBurst': R4_BURST + '（回流與雙斷在 DLL；留下免門檻與連斷）',
        'TrueMult': R4_BODY + '（Papyrus 的真實傷害沒有了；命中的真傷由 DLL 的 TrueDamageMultiplier 算同一條主線）',
    },
    'ESSBNodes.psc': {
        **{f: R4_BODY for f in ['CommonEndMult', 'CommonBurstMult', 'OnEndReward', 'HasChainEnd', 'HasGrandConcert', 'OmniMult']},
        'OnFormOpened': R4_ADVENT + '（臨界）',
    },
    'ESSBState.psc': {'ControllerQuest': 'R1：state_schema_version 12 → 13 的新控制器任務 ID'},
}
PROPERTY_REASONS = {
    'ESSBController.psc': R4_DEATH + '；ESSBGuard 屬性、舊血承法術屬性、擊殺快照／擊殺歸因／命中事實／擊殺預測的陣列、'
                          '安全閥／雙斷／嗜血的 Papyrus 計時、最後一擊潛行旗標這些成員刪除（R1：新 schema 13，不遷移）',
}
FILES = {
    'ESSBGuard.psc': R4_DEATH + '：ESSBGuard（玩家別名上的擊殺事件）整檔刪除，QUST VMAD 的別名腳本 4 → 3',
    'ESSBReactions.psc': R4_BODY + '：ESSBReactions 整檔刪除（B_max 讀值搬到控制器）',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reason(script, fn):
    why = REASONS.get(script, {}).get(fn)
    assert why, (script, fn, 'no reason written for this change')
    return why


def main():
    changed, removed, added, properties, files = {}, {}, {}, {}, {}
    names = sorted({p.name for p in SNAP.glob('*.psc')} | {p.name for p in SRC.glob('*.psc')})
    for name in names:
        a, b = SNAP / name, SRC / name
        if not a.exists() or not b.exists():
            files[name] = (FILES[name], sha(a if a.exists() else b), 'removed' if a.exists() else 'added')
            continue
        old, new = a.read_text(encoding='utf-8-sig'), b.read_text(encoding='utf-8-sig')
        fa, fb = h21.functions(old), h21.functions(new)
        for fn in sorted(set(fa) | set(fb)):
            if fn not in fb:
                removed[(name, fn)] = (reason(name, fn), h21.digest(fa[fn]))
            elif fn not in fa:
                added[(name, fn)] = (reason(name, fn), h21.digest(fb[fn]))
            elif h21.code(fa[fn]) != h21.code(fb[fn]):
                changed[(name, fn)] = (reason(name, fn), h21.digest(fa[fn]), h21.digest(fb[fn]))
        ol, nl = h21.outside_functions(old).splitlines(), h21.outside_functions(new).splitlines()
        if ol != nl:
            properties[name] = (PROPERTY_REASONS[name], tuple(x for x in nl if x not in ol), tuple(x for x in ol if x not in nl))

    def table(d):
        return ''.join(f'    {k!r}: {v!r},\n' for k, v in sorted(d.items()))

    template = (ROOT / 'build/fix24_history_template.py').read_text(encoding='utf-8')
    text = (template.replace('#CHANGED#', table(changed)).replace('#REMOVED#', table(removed))
            .replace('#ADDED#', table(added)).replace('#PROPERTIES#', table(properties)).replace('#FILES#', table(files)))
    (ROOT / 'build/fix24_history.py').write_text(text, encoding='utf-8', newline='\n')
    print(f'fix24_history: {len(changed)} changed, {len(removed)} removed, {len(added)} added, '
          f'{len(properties)} property blocks, {len(files)} whole files')


if __name__ == '__main__':
    main()

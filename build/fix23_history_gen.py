"""Writes build/fix23_history.py: every round-23 change to the Papyrus sources, each bound to the code by digest.

Run after the round's Papyrus is final (python -B build/fix23_history_gen.py). The reasons are written here, by
function, so a regenerated seal can only restate them; the digests come from the pre-fix23 snapshot and the current
sources (build/fix21_history.digest: comment-stripped body, sha256[:16]).
"""
from pathlib import Path
import hashlib, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
import fix21_history as h21

SNAP = ROOT / '.codex/pre-fix23-snapshot/src'
SRC = ROOT / 'src'

R6_HURT = 'R6：玩家受擊整條搬進 DLL（Hurt.h：反擊、破護、灼身、寒反、靜電、岩甲被打 -1／山岳、殘影、反震、毒皮、致命一擊）'
R6_SELF = 'R6：你的資源（電荷、岩甲、風勢、戰意、冰盾、同調）是 DLL 掛在你身上的效果；Papyrus 的計數與鏡射刪除'
SELF_WRAP = 'N4：改經 ESSBNative 的玩家碼 42／43／44 讀寫 DLL 的效果（1 電荷 2 岩甲 3 風勢）'
N4_HIT = 'N4：命中時的自身部分（命中 +1、同調、極致、血形態扣血、順勢、雷暴、雷霆、斷咒）在 DLL（SelfLayer.h）'
N4_SYNC = 'N4：同調是 DLL 的效果；門檻、升段、回饋在 DLL，Papyrus 讀 ESSB_SyncStage 鏡射、保留量經 ESSBNative.SetSync'
N4_END = 'N4：協奏、三重奏、過載終焉、雷終焉的電荷與消耗、導引的同調跳段在 DLL（ESSB_End 帶倍率、旗標與電荷）'
N4_OPEN = 'N4：開印時你的資源（電荷、岩甲、風勢、同調、共鳴層、餘電）由 DLL 在開印那一擊加'
N4_COUNTER = 'R7：反咒改由 DLL 的施法事件判定（Hurt.h PlanSpellCast），施法動畫事件的登記與最近施法紀錄刪除'
N4_EVENT = 'N4：DLL → 反應本體的新 ModEvent（放電、風刃、推力、升段、洗淨、致命一擊）'
N4_COOLDOWN = 'N4：這個冷卻／視窗是 DLL 掛在你身上的效果'

REASONS = {
    'ESSBController.psc': {
        **{f: R6_SELF for f in ['AddIceShield', 'AddResolve', 'ClearResolve', 'GetIceShield', 'GetResolve', 'ConsumeIceShield',
                                'ConsumeRockArmor', 'SyncRockArmor', 'PushSelf']},
        **{f: SELF_WRAP for f in ['AddSelf', 'GetSelf', 'ClearSelf', 'SetSelf', 'SelfCode']},
        'ClearSelfAll': R6_SELF + '；這裡只剩 Papyrus 自己的（雷雨計時、聖盾、水鏡、追擊）',
        **{f: N4_SYNC for f in ['AddSync', 'ComputeSyncStage', 'PushSyncStage', 'SyncStage', 'RefreshSyncStage', 'BoostSyncToStage1']},
        'OnSyncStage': N4_SYNC + '（由 ESSB_SyncUp 叫；回饋在 DLL）',
        'AfterOpen': N4_OPEN,
        **{f: N4_END for f in ['ConsumeEndCharge', 'EndCharge', 'TakeSwitchCharge', 'PushTrio', 'SetSyncKeepAll', 'TakeSwitchEnd',
                               'TakeGrandConcert', 'SetPendingDischarge', 'SetThunder']},
        **{f: N4_COUNTER for f in ['CounterEligible', 'StartCounter', 'StopCounter', 'OnAnimationEvent', 'RememberCast', 'RecentCast']},
        **{f: N4_COOLDOWN for f in ['TakeCleanse', 'TakeIceHeart', 'TakeInterrupt', 'TakeRetaliate', 'SetWindFollow']},
        'TakeSanctuary': N4_COOLDOWN + '（庇護；這個 Papyrus 冷卻 round 21 起就沒有呼叫者）',
        **{f: R6_HURT for f in ['SetCloakGuard', 'SetGuardWind', 'GetGuardWindLeft', 'SetRiposte']},
        'DumpStatus': '除錯列印改讀 DLL 的玩家碼（電荷、岩甲、風勢、戰意、冰盾、共鳴層、闇宙、超載、蓄勁、護血）',
        'ElementHitHook': N4_HIT, 'OnNoFormHit': N4_HIT, 'OnValidHitInternal': N4_HIT, 'OnWeaponHit': N4_HIT,
        **{f: N4_EVENT for f in ['OnESSBBlade', 'OnESSBCleanse', 'OnESSBDischarge', 'OnESSBKnock', 'OnESSBLethal', 'OnESSBSyncUp']},
        'OnESSBDeath': 'N4：死亡快照第 9 個值（DLL 的最後一擊潛行標記）→ 連殺讀它',
        'OnESSBEnd': N4_END,
        'OnFormClosed': N4_SYNC + '；三重奏的保留全部同調讀 DLL 標記（碼 51）；融斷電荷快照刪除',
        'OnFormOpened': 'N4：ESSBNative.FormEnter（專一計時、雷臨強化、地臨強化）；融斷電荷快照刪除',
        'OnFormSwitched': N4_END + '；你的資源由 DLL 的 FormLeave 清',
        'SwitchForm': N4_SYNC,
        'ReconcileLoadedForm': 'R1：新 schema 拿掉 v0.3 的岩甲常駐能力（岩甲的護甲是 DLL 效果）；同調快取刪除',
        'RefreshRecovery': 'v0.3 的岩甲常駐能力退役（不再依回復倍率重掛）',
        'RefreshRuntimeValues': N4_SYNC,
        'ResetLoadClock': 'N4：刪掉的計時與冷卻不再重設（它們是 DLL 的效果）',
        'Setup': N4_EVENT + '（每次載入重登）',
        'Tick': 'N4：電荷／風勢／戰意的衰減是 DLL 效果的時長；雷雨加電荷改呼叫 DLL',
        'TickTimers': 'N4：雷霆、順勢的計時在 DLL', 'TimersActive': 'N4：戰意、順勢不再讓 tick 保持 1 秒',
    },
    'ESSBCounter.psc': {f: N4_COUNTER + '；AME 留著不做事（破魔印的 VMAD 與舊存檔的 AME 指向它）'
                        for f in ['OnAnimationEvent', 'OnEffectFinish', 'OnEffectStart']},
    'ESSBElem.psc': {
        'ChargeCap': 'N4：電荷上限由 DLL 算，經玩家碼 55 讀回',
        'Discharge': 'N4：DLL 決定的暴擊倍率（ESSB_Discharge）；電荷消耗在 DLL',
        'DischargeAll': 'N4：DLL 決定的暴擊倍率（ESSB_Discharge）；電荷消耗在 DLL',
        'EndShockNodes': N4_END + '（餘電、雷霆）', 'OnFormOpened': 'N4：雷臨強化的 +5 電荷在 DLL（FormEnter）',
        'OnOpen': N4_OPEN, 'OnTick': 'N4：冰心（受擊）與雷神（命中）在 DLL', 'OpenStacks': N4_OPEN,
        'OverloadMult': N4_END, 'ShockBurstBonus': 'N4：雷斷讀 ESSB_End 帶來的融斷當下電荷', 'StormChance': N4_HIT,
    },
    'ESSBElem2.psc': {
        'CheckWindGauge': N4_HIT + '（風勢到門檻的風刃）', 'EndEarthNodes': N4_END + '（固土）', 'EndWindNodes': N4_END + '（順勢）',
        'LethalAmbush': '暗風的 ×2 移到這裡（DLL 的風刃已自己乘）', 'OnEarthHit': N4_HIT + '（地動）',
        'OnEarthRetaliate': R6_HURT + '（反震）', 'OnFormOpened': 'N4：地臨強化的岩甲滿層在 DLL（FormEnter）',
        'OnWindHit': N4_HIT + '（千刃）', 'OpenBlood': N4_OPEN + '（血脈）', 'OpenStacks': N4_OPEN, 'OpenWind': N4_OPEN + '（先風）',
        'WindBladeMult': '暗風的 ×2 由 DLL 乘在 ESSB_Blade 的倍率上（避免乘兩次）',
    },
    'ESSBElem3.psc': {'GuideSync': N4_END + '（導引）', 'OnPoisonSkin': R6_HURT + '（毒皮）',
                      'OnWaterHit': N4_HIT + '（洗淨的判定與冷卻；清除本體經 ESSB_Cleanse 回控制器）'},
    'ESSBGuard.psc': {'OnHitEx': R6_HURT, 'TakeAttacker': R6_HURT, 'RefreshNodeBits': R6_HURT,
                      'Setup': R6_HURT + '；載入時解除舊存檔的受擊事件登記', 'OnPlayerLoadGame': R6_HURT + '（攻擊者環刪除）'},
    'ESSBNative.psc': {'FormEnter': 'N4：開形態（專一計時、雷臨強化、地臨強化）', 'SetSync': 'N4：切換／融斷後保留的同調（不算升段）'},
    'ESSBNoForm.psc': {'OnCounterSpell': N4_COUNTER, 'OnInterruptCast': N4_HIT + '（斷咒）'},
    'ESSBNodes.psc': {'ConcertMult': N4_END, 'TrioMult': N4_END, 'HasExtreme': N4_HIT, 'OnSyncStage': N4_SYNC + '（回饋）',
                      'OpenSyncBonus': N4_OPEN, 'SyncThresholdScale': N4_SYNC},
    'ESSBReactions.psc': {'AddOpenSelf': N4_OPEN, 'Open': N4_OPEN,
                          'End': N4_END + '；蓄能的下一次地震加成（碼 53）在這裡用掉'},
    'ESSBState.psc': {'ControllerQuest': 'R1：state_schema_version 11 → 12 的新控制器任務 ID'},
    'ESSBTrees.psc': {'RefreshActive': R6_HURT + '（受擊節點位元刪除）', 'RefreshTree': R6_HURT + '（受擊節點位元刪除）'},
}
PROPERTY_REASONS = {
    'ESSBController.psc': R6_SELF + '；融斷／切換電荷、戰意、冰盾、斷咒／冰心／反震／庇護／洗淨冷卻、雷霆／順勢計時、協奏旗標、'
                          '極致計數、岩甲能力快取、同調快取這些成員刪除（它們是 DLL 的效果）',
    'ESSBCounter.psc': N4_COUNTER + '（AME 的成員刪除）',
    'ESSBGuard.psc': R6_HURT + '（每攻擊者 3 秒環的成員刪除；屬性保留原 VMAD 版面）',
}
FILES = {}


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

    template = (ROOT / 'build/fix23_history_template.py').read_text(encoding='utf-8')
    text = (template.replace('#CHANGED#', table(changed)).replace('#REMOVED#', table(removed))
            .replace('#ADDED#', table(added)).replace('#PROPERTIES#', table(properties)).replace('#FILES#', table(files)))
    (ROOT / 'build/fix23_history.py').write_text(text, encoding='utf-8', newline='\n')
    print(f'fix23_history: {len(changed)} changed, {len(removed)} removed, {len(added)} added, '
          f'{len(properties)} property blocks, {len(files)} whole files')


if __name__ == '__main__':
    main()

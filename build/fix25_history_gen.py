"""Writes build/fix25_history.py: every round-25 change to the Papyrus sources, each bound to the code by digest.

Run after the round's Papyrus is final (python -B build/fix25_history_gen.py). The reasons are written here, by
function, so a regenerated seal can only restate them; the digests come from the pre-fix25 snapshot and the current
sources (build/fix21_history.digest: comment-stripped body, sha256[:16]).
"""
from pathlib import Path
import hashlib, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
import fix21_history as h21

SNAP = ROOT / '.codex/pre-fix25-snapshot/src'
SRC = ROOT / 'src'

N6_DOMAIN = 'R4：領域是引擎的 hazard（DLL 在融斷目標腳下放 Spawn Hazard 法術，引擎管壽命與數量；對你與對內部敵人的每秒效果在 DLL 計時器 Timer.h）；Papyrus 的三格領域刪除'
N6_SECOND = '成果 1：每秒工作搬進 DLL 計時器（Timer.h PlanFormSecond：維持費、魔力歸零 2 秒、血形態扣血、長流與長河、雷雨電荷；環境每 5 秒）'
N6_HOTKEY = 'R6：熱鍵由 DLL 的輸入事件 sink 處理；Z 路線與熱鍵呼叫同一個 DLL 切換函式（ESSBNative.RequestSwitch），ESSBInput 刪除'
DEAD = '沒有呼叫者了（呼叫它的 Papyrus 領域／每秒工作搬進 DLL）'
# round 25 審查修正
R_CLOCK = ('審查修正 4：秒計時器改用 DLL 的遊戲時鐘（ESSBController.Now → ESSBNative.RunningSeconds，只算遊戲在跑的秒數，'
           '暫停與讀檔不走），不再用 Utility.GetCurrentRealTime')
R_COMBO = '審查修正 4：沒有讀者的「節奏」「疾攻」連段（ComboHits、ComboTime、GCombo）刪除'

REASONS = {
    'ESSBController.psc': {
        **{f: N6_DOMAIN for f in ['StartDomain', 'InDomain', 'DomainActive', 'PlayerInDomain', 'TickDomain', 'ScanDomainTargets',
                                  'DomainFlag', 'InsideDomainSlot', 'ClearDomainResidents', 'ObserveDomainResidents',
                                  'RememberDomainResident', 'DomainTargetTicks']},
        **{f: N6_DOMAIN + '；' + DEAD + '（死域的每秒傷害是這些函式唯一的呼叫者，現在是 DLL 的 D_react）'
           for f in ['ApplyDamage', 'ApplyDamageRaw', 'ApplyDotDamage', 'ReactDamage', 'GetDamageMult', 'GetBloodHitMult', 'BloodBand',
                     'BloodBandMult', 'BloodPercent']},
        'AddStackTo': N6_DOMAIN + '；' + DEAD + '（毒霧的 +1 劑，現在是 DLL 的擴散一劑，R5）',
        'ApplyStrip': N6_DOMAIN + '；' + DEAD + '（潮池每秒沖刷一個增益，現在是 DLL 的沖刷）',
        'EnvCheck': N6_SECOND + '（環境偵測：天氣、室內、水中、時間 → ESSB_EnvWet／EnvStormy／EnvNight，DLL 寫）',
        'AddSelf': N6_SECOND + '；' + DEAD + '（雷雨的 +1 電荷）',
        'PayBloodCost': N6_SECOND + '（血形態維持扣血，DLL 走代價路徑、留 1 點）',
        'BloodDrainPerSecond': N6_SECOND + '（血位損血曲線，DLL Timer.h BloodUpkeepFraction）',
        'ToggleForm': N6_HOTKEY + '；這個函式本來就沒有呼叫者',
        'OnESSBSwitch': N6_HOTKEY + '：DLL 判定魔力門檻並寫好全域變數後，這裡換形態（規劃 1.1 形態開關 Papyrus）',
        'OnESSBClose': N6_SECOND + '：魔力歸零 2 秒由 DLL 判定，這裡關閉形態並提示',
        'OnESSBDomain': N6_DOMAIN + '；這裡只放開場特效',
        'Setup': N6_HOTKEY + '；ESSB_Switch／ESSB_Close 登記；形態維持能力不再加（ESSBFormRules 刪除）；環境偵測在 DLL',
        'Tick': N6_SECOND + '（雷雨電荷與環境偵測拿掉；留下的每秒工作：神佑、秒計時器、毒形態的以毒攻毒與百毒不侵、風的潛行）；' + R_COMBO,
        'TickTimers': N6_DOMAIN + '；' + R_CLOCK,
        'TimersActive': N6_DOMAIN + '；' + R_CLOCK + '；' + R_COMBO,
        'Now': R_CLOCK + '（新函式）',
        'SecondsLeft': R_CLOCK,
        **{f: R_CLOCK for f in ['SetEmber', 'SetQuench', 'SetShockRecent', 'SetGuardSwitch', 'SetGuardIce', 'SetSyncKeep',
                                'SetGuardDivine', 'SetNoBloodCost', 'KeepSneak', 'SetGuardDark', 'SetGuardAstral', 'SetGuardStar']},
        'OnFormSwitched': R_CLOCK + '（同調保留的期限）',
        'SwitchForm': R_CLOCK + '（雙生的 30 秒從遊戲時鐘起算）',
        'OnWeaponHit': R_CLOCK + '（雙生的 30 秒）',
        'InitTables': N6_DOMAIN + '（領域的陣列不再配置）',
        'ResetLoadClock': N6_DOMAIN + '；雷雨計時、環境計時、領域鏡射的重設拿掉；' + R_CLOCK + '（雙生）；' + R_COMBO,
        'ReconcileLoadedForm': N6_DOMAIN + '（領域鏡射屬性拿掉；聖域鏡射由 DLL 每秒寫）；形態維持能力不再移除（沒有再加）',
        'ValidateBindings': N6_DOMAIN + '；' + N6_HOTKEY + '；GameHour、形態維持能力、反應法術、過熱自傷法術這些屬性拿掉；' + R_COMBO,
        'ClearSelfAll': N6_SECOND + '（雷雨計時變數拿掉）',
    },
    'ESSBElem2.psc': {
        'TargetDamageMult': N6_DOMAIN + '；' + DEAD + '（御風／空中追擊的 Papyrus 反應倍率只給領域的傷害；DLL 的反應讀同樣兩項）',
        'WindSlowImmune': '御風的免疫減速：這個守衛從來沒有呼叫者（假 DONE）；round 25 在 DLL 計時器每 tick 驅散你身上的減速（Timer.h SlowImmune）',
    },
    'ESSBElem3.psc': {
        'TargetDamageMult': N6_DOMAIN + '；' + DEAD + '（星鎖／星域的 Papyrus 反應倍率只給領域的傷害；DLL 的反應讀同樣兩項）',
        'FlowPercent': N6_SECOND + '（長流的百分比，DLL Timer.h FlowFraction）',
        'WaterFormTick': N6_SECOND + '（長流、長河；v0.4 1.1 的「另回維持費 80% 的魔力」Papyrus 本來就沒做，DLL 補上）',
        'OnTick': N6_SECOND + '（水形態的每秒掛勾拿掉，毒形態的留著）',
    },
    'ESSBNodes.psc': {
        'SelfSlowImmune': '定神／御風／冰原的免疫減速：這個守衛從來沒有呼叫者（假 DONE）；round 25 在 DLL 計時器（Timer.h SlowImmune）',
    },
    'ESSBTrees.psc': {
        'RefreshActive': N6_HOTKEY + '（ESSBInput.RefreshPermission 拿掉：順轉由 DLL 在切換當下讀）',
        'RefreshTree': N6_HOTKEY + '（同上）',
    },
    'ESSBFormPowerEffect.psc': {'OnEffectStart': N6_HOTKEY},
    'ESSBNative.psc': {
        'RequestSwitch': N6_HOTKEY + '（新原生函式，排進主執行緒 task）',
        'RunningSeconds': R_CLOCK + '（新原生函式：讀一個 atomic，可在 VM 的 tasklet 執行）',
        'ExtendFuse': N6_DOMAIN + '；唯一的呼叫者 TickDomain 刪除（火域的白熱引信 +5 秒在 DLL）',
        'WashBuffs': N6_DOMAIN + '；唯一的呼叫者 ApplyStrip 刪除（潮池的沖刷在 DLL）',
    },
    'ESSBState.psc': {'ControllerQuest': 'R1：state_schema_version 13 → 14 的新控制器任務 ID'},
}
PROPERTY_REASONS = {
    'ESSBController.psc': N6_DOMAIN + '；' + N6_SECOND + '；' + N6_HOTKEY + '：三格領域的成員、雷雨與環境的計時、GameHour、'
                          '形態維持能力、InputLayer、反應法術、過熱自傷法術、9 個領域鏡射屬性刪除（R1：新 schema 14，不遷移）；' + R_COMBO,
    'ESSBElem3.psc': N6_SECOND,
}
FILES = {
    'ESSBFormRules.psc': N6_SECOND + '：ESSBFormRules（形態維持能力上的每秒維持費、魔力歸零、血形態扣血）整檔刪除，MGEF 的 VMAD 拿掉',
    'ESSBInput.psc': N6_HOTKEY + '：ESSBInput（玩家別名上的按鍵輪詢）整檔刪除，QUST VMAD 的別名腳本 3 → 2',
    'ESSBSilence.psc': '成果 1：沉默的每秒扣魔搬進 DLL（施放當下 StatusEngine.h RunOp、之後每秒 Plugin.cpp SilenceSecond）；ESSBSilence 整檔刪除，MGEF 的 VMAD 拿掉',
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

    template = (ROOT / 'build/fix25_history_template.py').read_text(encoding='utf-8')
    text = (template.replace('#CHANGED#', table(changed)).replace('#REMOVED#', table(removed))
            .replace('#ADDED#', table(added)).replace('#PROPERTIES#', table(properties)).replace('#FILES#', table(files)))
    (ROOT / 'build/fix25_history.py').write_text(text, encoding='utf-8', newline='\n')
    print(f'fix25_history: {len(changed)} changed, {len(removed)} removed, {len(added)} added, '
          f'{len(properties)} property blocks, {len(files)} whole files')


if __name__ == '__main__':
    main()

"""Writes build/fix22_history.py: every round-22 change to the Papyrus sources, each bound to the code by digest.

Run after the round's Papyrus is final (python -B build/fix22_history_gen.py). The reasons are written here, by
function, so a regenerated seal can only restate them; the digests come from the pre-fix22 snapshot and the current
sources (build/fix21_history.digest: comment-stripped body, sha256[:16]).
"""
from pathlib import Path
import hashlib, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
import fix21_history as h21

SNAP = ROOT / '.codex/pre-fix22-snapshot/src'
# Round 23: round 22's scripts as shipped are the pre-fix23 snapshot (today's src/ is round 23; build/fix23_history.py).
SRC = ROOT / '.codex/pre-fix23-snapshot/src'

R4_REGISTRY = 'R4：印記登記表刪除（v0.4 沒有 8 目標名額；印記是 DLL 掛的引擎效果，開印／刷新／被切在命中那一幀由 DLL 決定）'
R4_STATUS = 'R4：狀態容器 ESSBStatus、換宿、pending、備份銀行刪除；層數與計時是 DLL 寫的引擎效果（讀–疊–重套）'
R4_PATCH = 'R4：差額補丁刪除；目標側倍率由 DLL 在命中當下讀目標與你身上的效果（Status.h ProcTerms）'
N3_WINDOWS = 'N3：開印後／終焉後視窗、寒留、血引、聖引、連殺改成 DLL 的效果與規則'
N3_HEAT = 'N3：v0.3 的過熱與熔身計時換成 DLL 的熱度階梯（你身上的效果）'
NATIVE = 'N3：改經 ESSBNative 讀寫 DLL 的目標狀態'
BODY = 'N3：這裡只剩反應本體（R4），狀態部分與它的數值由 DLL 的 ModEvent 帶進來'

REASONS = {
    'ESSBController.psc': {
        **{f: R4_REGISTRY for f in ['InitRegistry', 'FindSlot', 'RegistryCount', 'AcquireSlot', 'OccupySlot', 'ClearSlot',
                                    'InstallMark', 'OpenMark', 'OpenSecond', 'EndMark', 'TakeEndSlot', 'EndBothMarks',
                                    'EndLinkedMark', 'FinishMark', 'EndSecondMark', 'ClearSecond', 'WillOpen', 'OnValidHit',
                                    'InitRegistryInternal', 'FindSlotInternal', 'WillOpenInternal', 'KeepAsSecond',
                                    'OnMarkStart', 'OnMarkFinish', 'DumpRegistry']},
        **{f: R4_STATUS for f in ['EnsureStatus', 'OnStatusStart', 'OnStatusFinish', 'GetStatus', 'AddStack', 'GetStack',
                                  'SetStack', 'IsWet', 'CancelSwap', 'SwapHosts', 'ClearPendingState', 'FlushPendingState',
                                  'InitBackupInts', 'SwapIntBank', 'StoreSwapInts', 'SaveSwapData', 'ReadSwapInts',
                                  'ReadSwapFloats', 'AddAstral', 'DetonateAstralNow', 'SetFrozen', 'SetCatalyzeOn',
                                  'SetDeathCurseOn', 'SetNextOpenMult', 'TakeNextEndMultOn', 'TakeNextOpenMultOn',
                                  'SetNextEndMultOn', 'SetStarLock', 'HasStarLock', 'SetWetLock', 'CaptureDeath',
                                  'CaptureStatusDeath', 'SettleDeadCurse', 'ApplyBleedDrain', 'StackCap', 'HitStacks']},
        **{f: R4_PATCH for f in ['ApplyProc', 'ApplyBonusProc', 'ApplyExtraProc', 'DifferenceMult', 'NativeProcUnit',
                                 'NativeNodeSum', 'NativeBloodCurve', 'LinearBloodCurve', 'DifferencePossible']},
        **{f: N3_WINDOWS for f in ['SetPendingBleed', 'TakePendingBleed', 'SetPendingHeal', 'TakePendingHeal',
                                   'SetNextMarkBonus', 'SetOpenBoost', 'GetOpenBoost', 'SetEndBoost', 'GetEndBoost',
                                   'TakeKillStreak']},
        'SetPendingDrain': 'v0.3 蝕魔終焉的死碼（round 21 起沒有呼叫者），隨 pending 一起刪',
        'TakePendingDrain': 'v0.3 蝕魔終焉的死碼（round 21 起沒有呼叫者），隨 pending 一起刪',
        **{f: N3_HEAT for f in ['SetMolten', 'GetMoltenLeft', 'AddSelf', 'PushSelf', 'GetSelf', 'ClearSelf', 'ClearSelfAll',
                                'SetSelf']},
        'InitFixState': '只配置還在用的陣列（擊殺、推力、傷害來源）；登記表／pending／備份陣列刪除',
        'InitTables': 'InitRegistry 改名：只剩推力冷卻環與三格領域',
        'Setup': 'InitTables；登記 DLL 送的 ModEvent（每次載入重登）',
        'ResetLoadClock': '拿掉登記表、pending 與換宿的時鐘重設',
        'ValidateBindings': '屬性拿掉 StatusHostSpell、MarkSpells、StripSpell、HitBonusSpells',
        'OnFormOpened': '融斷電荷快照清零（BurstCharge）',
        'OnFormSwitched': 'ESSBNative.FormLeave：離開舊形態的自身階梯',
        'OnFormClosed': '融斷改 ESSBNative.BurstMarks（每目標一次冷卻、狀態部分在 DLL）＋ FormLeave；雷終焉讀融斷當下的電荷',
        'OnWeaponHit': '命中只剩 N4 前的自身資源與掛勾；附傷、目標側倍率、印記與層數都在 DLL；極致改 CastProc',
        'OnValidHitInternal': '命中的 Papyrus 那一半：自身資源命中 +1、掛勾、同調、經驗（印記在 DLL）',
        'AfterOpen': '放電呼叫補上新參數（Papyrus 自己觸發的放電：R＝1、這裡擲暴擊）',
        'ApplyMark': NATIVE, 'ForceOpenOn': NATIVE, 'AddStackTo': NATIVE, 'NearestMarked': NATIVE,
        'SetAirborne': NATIVE, 'GetAirborne': NATIVE,
        'ApplyDamage': '5.3 火域的受火傷 +20% 補到 Papyrus 的火傷',
        'Tick': '沒有登記表的逐格掃描與換宿；擊殺保底結算；總開關關掉時只解除神佑延遲死亡並保持 5 秒空 tick（審查修正 3）',
        'IsOperational': '審查修正 3：總開關 ESSB_Enabled 關掉時所有遊戲路徑不做事',
        'IsReadyUI': '指揮官裁定：MCM 與選單動作只看控制器就緒，不看總開關',
        'CloseForm': '指揮官裁定：關閉形態是選單也會要求的動作（洗點），看 IsReadyUI',
        'OnMenuClose': '指揮官裁定：選單動作看 IsReadyUI',
        'OnESSBHallucinate': 'ESSB_Hallucinate → 恐懼／瘋狂／幻視；5.12 夢魘、群魔（掃描 N5 前在這裡）；幻視改攻擊傷害倍率 ×0.8（v0.4 第 1380 行，指揮官裁定）',
        'SpreadPoison': '審查修正 5：淬毒的傳劑走擴散一劑（碼 25：時長 max(d − t, 12)）',
        'TickTimers': 'v0.3 熔身計時、開印／終焉視窗與連殺旗標刪除（DLL）',
        'TimersActive': '同上：刪掉的計時不再讓 tick 保持 1 秒',
        'StartDomain': 'InitTables 改名', 'InDomain': 'InitTables 改名', 'DomainActive': 'InitTables 改名',
        'TakePush': 'InitTables 改名',
        'TickDomain': '火域／冰原／星域對內部敵人掛 DLL 讀的領域效果；進入火域時白熱引信 +5 秒',
        'Knockdown': 'v0.4 2.3：土造成的跌倒掛上倒地（DLL）',
        'SetBloodthirst': '嗜血同時掛成你身上的效果給 DLL 讀',
        'KeepSneak': '連殺的 ×2 改由 DLL 讀效果；這裡只剩不解除潛行',
        'ApplyStrip': 'R5：沖刷改 ESSBNative.WashBuffs（手施、有時限、有益的增益）',
        'ApplyFear': 'DLL 送來的秒數已乘時長倍率（abScaled）',
        'ApplyFrenzy': 'DLL 送來的秒數已乘時長倍率（abScaled）；5.12 狂刃',
        'LastDamageFor': '傷害時間陣列改名 DamageTime（不再與換宿共用）',
        'NoteDamageElement': '拿掉登記表的最後傷害欄',
        'ApplyTrackedDamage': '拿掉登記表參數；DamageTime',
        'KillElementFor': '致死元素：最近傷害，否則讀 DLL 死亡快照的印記位元',
        'OnKillEvent': '擊殺掛勾改讀 DLL 死亡快照，與 PO3 的回報誰先到都行（決策 3）',
        'ConsumeEndCharge': '融斷那份電荷另扣（決策 4）',
        'HasMarkBit': '死亡快照的印記位元', 'HasDeathSnapshot': '決策 3', 'SettleKill': '決策 3：擊殺掛勾（每個死者一次）',
        'SettleStaleKills': '決策 3：快照沒來的保底', 'KillPending': '決策 3',
        'EventArg': 'ModEvent strArg 的第 i 個值', 'UnscaledSeconds': 'DLL 的秒數換回未乘時長倍率',
        'OnESSBOpen': 'ESSB_Open → 開印經驗與反應本體', 'OnESSBEnd': 'ESSB_End → 終焉反應本體',
        'OnESSBFrozen': 'ESSB_Frozen → 冰封減速與深寒；5.4 霜爆（掃描 N5 前在這裡）',
        'OnESSBJudgment': 'ESSB_Judgment → 聖裁 II／III 的破防', 'OnESSBSplash': 'ESSB_Splash → 濺血',
        'Splash': '濺血：15 公尺內所有流血目標 ×0.5 血潮（掃描 N5 前在這裡）',
        'OnESSBRise': 'ESSB_Rise → 5.8 血約（掃描 N5 前在這裡）', 'OnESSBShatter': 'ESSB_Shatter → 碎甲',
        'OnESSBLanding': 'ESSB_Landing → 落地傷害', 'OnESSBDeath': 'ESSB_Death → 死亡快照（決策 3）',
        'DumpStatus': '除錯：印出附近帶印記的目標與你身上的狀態（沒有登記表了）；訊息框列最近目標的狀態碼 2～19（審查修正 7）；看 IsReadyUI（指揮官裁定）',
        'EndCharge': '雷終焉讀哪一份電荷（決策 4）',
    },
    'ESSBElem.psc': {
        **{f: R4_STATUS for f in ['HeatCap', 'OverheatCap', 'HitStacks', 'OpenMult', 'MarkDurationBonus', 'IgniteMult',
                                  'DetonatePerLayer', 'OnIgnite', 'ShatterThreshold', 'Shatter', 'FrozenExtraSeconds',
                                  'FrozenResidual', 'OnFrozenTick', 'KeepHeatOnBurst', 'HasMoltenBody', 'HasTinder']},
        **{f: R4_PATCH for f in ['HitExtra', 'FireHitExtra', 'FrostHitExtra', 'ShockHitExtra']},
        'HeatBurstMult': '爆燃依你的熱度階（DLL 算好帶進來）', 'OnFrozen': BODY, 'OnShatter': BODY,
    },
    'ESSBElem2.psc': {
        **{f: R4_STATUS for f in ['BleedCap', 'HolyCap', 'HitStacks', 'BleedPerLayer', 'BleedTickMult', 'BleedDrainPercent']},
        **{f: R4_PATCH for f in ['HitExtra', 'EarthHitExtra', 'BloodHitExtra', 'DivineHitExtra', 'KillStreakMult', 'SneakMult']},
        'HolyTierBonus': '聖佑階的聖傷加成（裁決、聖裁共用）',
        'TargetDamageMult': NATIVE + '；審查修正：御風 +30% 不看同調（v0.4 第 1091 行）',
    },
    'ESSBElem3.psc': {
        **{f: R4_STATUS for f in ['PressureCap', 'CurseCap', 'AstralCap', 'OpenStacks', 'HitStacks', 'CatalyzeSeconds',
                                  'CatalyzeRate', 'PoisonTickMult', 'SpreadInterval', 'SpreadTargets', 'SpreadThreshold',
                                  'PoisonTickHook', 'GuideMult', 'DeathCurseLostRatio', 'AfterDeathCurse', 'AstralDelay',
                                  'DetonateAstral', 'TakeoverOpenMult']},
        **{f: R4_PATCH for f in ['HitExtra', 'PoisonHitExtra', 'WaterHitExtra', 'DarkHitExtra', 'AstralHitExtra']},
        'OpenPoison': NATIVE + '；5.10 濃毒（掃描 N5 前在這裡）走擴散一劑（碼 25，審查修正 5）',
        'OpenDark': NATIVE + '；5.12 幻影改由 DLL 給目標幻影效果＋PERK 逐擊 30% 落空（指揮官裁定 (c)）',
    },
    'ESSBReactions.psc': {
        **{f: BODY for f in ['RollBase', 'EndFire', 'EndFrost', 'EndShock', 'EndEarth', 'EndBlood', 'EndDivine', 'EndPoison',
                             'EndWater', 'EndDark', 'EndAstral']},
        'AddOpenSelf': '開印 +2 扣掉命中已加的 +1（決策 5）', 'Surge': '血潮本體（DLL 讀好血痕剩餘）',
        'SurgeOn': '對別的流血目標結算一次血潮（血海、血漫、血祭之始、濺血）',
    },
    'ESSBNodes.psc': {
        'MarkDurationBonus': '印記持續、雙印、疊印改由 DLL 讀', 'HasDualMark': '印記持續、雙印、疊印改由 DLL 讀',
        'HasResidualMark': '印記持續、雙印、疊印改由 DLL 讀',
        'CommonEndMult': '5.2 同調三段時終焉 +1%／點（LATER-N3 → 做了）',
    },
    'ESSBMCM.psc': {'DumpRegistry': '呼叫控制器的 DumpStatus（沒有登記表）；看 ESSBState.ReadyUI（指揮官裁定）',
                    **{f: '指揮官裁定：MCM 動作看 ESSBState.ReadyUI（總開關關著也能用）' for f in
                       ['RespecCurrent', 'RespecAll', 'GetTrees', 'RestoreDefaults']}},
    'ESSBNative.psc': {},
    'ESSBState.psc': {
        **{f: R4_STATUS + '（環狀桶與備份的長度函式跟著刪）' for f in ['BleedSeconds', 'PoisonSeconds', 'IntCount', 'PoisonOffset',
                                                         'TailOffset', 'NewBleed', 'NewPoison', 'NewInts', 'NewBackup',
                                                         'UpgradeInts']},
        'ControllerQuest': 'R1：state_schema_version 10 → 11 的新控制器任務 ID',
        'ReadyUI': '指揮官裁定：MCM 用的「控制器就緒」判斷（不看總開關）',
    },
}
DEFAULT = {
    'ESSBElem.psc': NATIVE + '；v0.3 的層數與倍率函式隨狀態容器刪除',
    'ESSBElem2.psc': NATIVE + '；v0.3 的層數與倍率函式隨狀態容器刪除',
    'ESSBElem3.psc': NATIVE + '；v0.3 的層數與倍率函式隨狀態容器刪除',
    'ESSBReactions.psc': BODY,
    'ESSBTrees.psc': '指揮官裁定：技能樹選單、設定、洗點看 IsReadyUI（總開關關著也能用）',
    'ESSBSettingsEffect.psc': '指揮官裁定：設定能力看 IsReadyUI（總開關關著也能用）',
    'ESSBNative.psc': 'N3：DLL 的狀態層原生函式（Plugin.cpp 登記，build/fix22_verify.py 核對參數數目）',
}
PROPERTY_REASONS = {
    'ESSBController.psc': '屬性拿掉 StatusHostSpell、MarkSpells、HitBonusSpells、StripSpell，新增 FrenzyBladeSpell、VisionSpell（幻視 ×0.8，指揮官裁定）；'
                          '登記表、換宿、pending、備份、v0.3 過熱的成員刪除；新增死亡快照、擊殺等待、融斷電荷、火域進入旗標',
}
FILES = {
    'ESSBStatus.psc': 'R4：狀態容器刪除（整支腳本）',
    'ESSBMark.psc': 'R4：印記 AME 腳本刪除（印記到期由 DLL 從效果移除事件判定，記錄改掛 ESSBStub）',
    'ESSBStub.psc': 'N3：空腳本，只讓 DLL 要結算結束的效果送出移除事件（裁定 R3）',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reason(script, fn):
    why = REASONS.get(script, {}).get(fn) or DEFAULT.get(script)
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

    template = (ROOT / 'build/fix22_history_template.py').read_text(encoding='utf-8')
    text = (template.replace('#CHANGED#', table(changed)).replace('#REMOVED#', table(removed))
            .replace('#ADDED#', table(added)).replace('#PROPERTIES#', table(properties)).replace('#FILES#', table(files)))
    (ROOT / 'build/fix22_history.py').write_text(text, encoding='utf-8', newline='\n')
    print(f'fix22_history: {len(changed)} changed, {len(removed)} removed, {len(added)} added, '
          f'{len(properties)} property blocks, {len(files)} whole files')


if __name__ == '__main__':
    main()

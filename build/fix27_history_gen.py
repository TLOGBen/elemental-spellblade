"""Writes build/fix27_history.py: every round-27 change to the Papyrus sources, each bound to the code by digest.

Run after the round's Papyrus is final (python -B build/fix27_history_gen.py). The reasons are written here, by
function, so a regenerated seal can only restate them; the digests come from the pre-fix27 snapshot and the current
sources (build/fix21_history.digest: comment-stripped body, sha256[:16]).
"""
from pathlib import Path
import hashlib, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
import fix21_history as h21

SNAP = ROOT / '.codex/pre-fix27-snapshot/src'
SRC = ROOT / 'src'

G13 = 'Round 27（G13：看得見的回饋'
LAG = 'Round 27e（0.27.4，MCM 與技能樹選單卡頓）'
G8 = 'Round 27（G8：形態切換由 DLL 在決定它的 task 裡做完）'
REFUND = 'Round 27g（0.27.6，分支退回訊息）'
H = 'Round 27h（0.28.0，整體審查）'
PR = 'Round 27h（0.28.0，Papyrus 層審查）'
ECHO = H + '：探針——除錯等級 2 以上把事件序號送回 DLL（Echo），DLL 算延遲'
REASONS = {
    'ESSBController.psc': {
        'SwitchForm': G8 + '：依 ESSB_Switch 帶來的種類（1 開、2 切換、3 關）處理，不再看當下的全域變數（關了馬上又開也一定先關再開）；'
                      '切換前的同調由 DLL 帶來；保留的份改用 ESSBNative.KeepSync 加在 DLL 歸零後的同調上（DLL 已加上新形態開啟的所得）；'
                      '魔力耗盡（原因 1）顯示提示',
        'CloseForm': G8 + '：abByDll（熱鍵、Z、魔力耗盡）時不寫全域變數、不拿餘響與護血（DLL 已做）；選單的關閉照舊',
        'OnFormClosed': G8 + '：DLL 的關閉不再呼叫 Burst、FormLeave、SetSync(0)（DLL 在同一個 task 做完）；同調與段數用 DLL 動手前的值',
        'OnFormOpened': G8 + '：不再呼叫 ESSBNative.FormEnter（DLL 的 FormEnterWork 在切換的 task 裡做）',
        'OnFormSwitched': G8 + '：不再呼叫 ESSBNative.FormLeave、不再掛餘響與雙生的標記、不寫 ESSB_TwinElement（DLL 的 SwitchMarkers）',
        'OnESSBSwitch': G8 + '：解析事件的種類、切換前的同調、段數、原因，交給 SwitchForm；27b（審查 B N8）：兩個全域變數當號碼牌，'
                        '切換事件一個接一個做完（關了馬上又開時不交錯），最多等 1 秒',
        'Rank': LAG + '：階數改由 DLL 回答（ESSBNative.NodeRank），不再讀 ESSBTrees 重建的快取',
        'Br': LAG + '：分支改由 DLL 回答（ESSBNative.NodeBranch）',
        'OnESSBEnd': G13 + '）：目標被 DLL 自己的傷害打死時，終結的爆炸照樣放（原本 IsDead 就不放）',
        'OnESSBOpen': G13 + '）：目標被 DLL 自己的傷害打死時，開印的特效照樣放（原本 IsDead 就不放）',
        'OnESSBFx': G13 + '，新事件）：DLL 自己結算的碎冰、放電、過熱引爆各放一次該元素的爆炸（規劃 2.12），只有畫面',
        'Setup': G13 + '）：註冊 ESSB_Fx 事件',
    },
    'ESSBNative.psc': {'KeepSync': G8 + '（新原生函式宣告：把保留的同調加上去，不算升段）',
                       'NodeRank': LAG + '：新原生函式宣告（節點階數）', 'NodeBranch': LAG + '：新原生函式宣告（分支）',
                       'BranchesGained': LAG + '：新原生函式宣告（技能選單開啟後新買的分支，給別處開的選單補扣點數）',
                       'SettleBranch': REFUND + '：新原生函式宣告（一個新分支結算後的點數）'},
    'ESSBTrees.psc': {
        'RefreshActive': LAG + '：只更新 13 棵樹的等級，不再逐節點 HasPerk（一次最多約 3000 次原生呼叫）',
        'Setup': LAG + '：一直聽 StatsMenu 的關閉（樹可能從 Custom Skill Menu 直接開）',
        'OnMenuClose': LAG + '：不是從 OpenTree 開的選單關閉時補扣分支點數（ReconcileGained）；不再取消 StatsMenu 的登記',
        'ReconcileGained': LAG + '：新函式：依 DLL 記下的選單開啟時分支，每個新分支補扣 4 點，不夠就退回；' + REFUND
                           + '：每個分支交給 SettleBranch 結算（訊息寫出分支名、需要幾點、樹剩幾點）',
        'Reconcile': REFUND + '：每個新分支交給 SettleBranch 結算（規則在 DLL 的 rt::SettleBranch，有單元測試）；'
                     '不再只說「有 N 個分支已退回」',
        'SettleBranch': REFUND + '：新函式：一個分支的結算——夠 4 點就扣，不夠就退回並把 CSF 扣的 1 點加回；'
                        '通知寫出樹、分支名、需要 5 點、樹剩幾點；除錯等級 3 以上每個決定都記一行',
    },
    'ESSBState.psc': {
        'RestoreTunableDefaults': 'Round 27g（0.27.6，使用者決定整體傷害降 20%）：MCM「還原預設」的傷害倍率改成 0.8（由 build_v03.py 從 settings.json 產生）',
    },
    'ESSBSettingsEffect.psc': {
        'CycleDebugLevel': 'Round 27（G15：除錯等級快捷鍵繞到 4＝探針 log；原本 % 4 永遠到不了 4）',
    },
    'ESSBMCM.psc': {
        'ShowNativeStatus': 'Round 27（G12：新遊戲時 DLL 被 SKSE 拒絕）：版本空白時說明去看 skse64.log 的 incompatible、確認上一個 SkyrimSE.exe 已結束',
    },
}
# ---------------------------------------------------------------- round 27h (0.28.0): appended to the reasons above
_27H = {
    'ESSBController.psc': {
        'ApplyFear': PR + ' 7：改用 ESSBNative.CastWith（這次的強度與秒數，不改共用的法術紀錄）',
        'ApplyFrenzy': PR + ' 7：恐懼、狂刃都改用 ESSBNative.CastWith',
        'ApplyUtil': PR + ' 7：SetNthEffectMagnitude／Duration＋DoCombatSpellApply 改成 ESSBNative.CastWith',
        'ApplyManaBreakMark': PR + ' 7：沒有呼叫者（滅法印是 DLL 的），刪除',
        'ApplySilenceSpell': PR + ' 7：沒有呼叫者（沉默是 DLL 的），刪除',
        'Echo': ECHO + '（新函式）',
        'FormClosedFx': H + ' 1-4：關閉的 Papyrus 附帶（音效、提示、節點能力）；融斷、保留、免門檻、形態能力都在 DLL 的切換 task（新函式，取代 OnFormClosed）',
        'FormOpenedFx': H + ' 1-4：開啟／切換的 Papyrus 附帶（音效、順轉、節點能力、雙生時間）；形態能力與同調保留在 DLL（新函式，取代 SwitchForm）',
        'IsOperational': PR + ' 10：DLL 沒在運作（ESSB_NativeHit 不是 1）時 Papyrus 不做遊戲效果',
        'OnESSBAsh': ECHO, 'OnESSBCleanse': ECHO, 'OnESSBDomain': ECHO, 'OnESSBHallucinate': ECHO, 'OnESSBKnock': ECHO,
        'OnESSBLethal': ECHO, 'OnESSBPush': ECHO, 'OnESSBRaise': ECHO, 'OnESSBSneak': ECHO, 'OnESSBSyncUp': ECHO,
        'OnESSBOpen': ECHO, 'OnESSBEnd': ECHO,
        'OnESSBSwitch': H + ' 1-4：號碼牌的忙等拿掉；只分派 FormOpenedFx／FormClosedFx（DLL 在切換 task 裡做完形態）；Papyrus 沒就緒時記 [ESSB][drop]',
        'SwitchForm': H + ' 1-4：刪除（形態能力、同調保留在 DLL；Papyrus 的附帶移到 FormOpenedFx）',
        'CloseForm': H + ' 1-4：選單的關閉交給 ESSBNative.CloseForm（全域變數立刻歸零）；DLL 沒在運作時照舊由這裡關',
        'OnFormClosed': H + ' 1-4：刪除（融斷、永續、連斷、三重奏、免門檻在 DLL；附帶移到 FormClosedFx）',
        'SetSyncKeep': H + ' 1-4：刪除（同調保留在 DLL 的 Runtime.h SyncKeep）',
        'Setup': PR + ' 2：形態能力照全域變數對齊（只留目前的那一個），結尾寫 ESSB_PapyrusReady = 1',
        'ApplySelfMarker': PR + ' 7：改用 ESSBNative.CastWith（這次的秒數，不改共用的法術紀錄）',
        'ApplyGuardWindow': PR + ' 7：改用 ESSBNative.CastWith（先驅散、DLL 再用這次的秒數施放）',
        'ApplyAsh': PR + ' 7：改用 ESSBNative.CastWith（這次的強度＝目標最大生命 +100）',
    },
    'ESSBElem3.psc': {
        'PoisonFormTick': PR + ' 6：百毒不侵的附近中毒敵人改讀 ESSBNative.PoisonedNearby（DLL 每秒數好），不再每秒掃全部角色',
    },
    'ESSBNative.psc': {
        'CastWith': PR + ' 7：新原生函式宣告', 'CheckPoints': H + '（探針）：新原生函式宣告',
        'CloseForm': H + ' 1-4：新原生函式宣告', 'EventSeen': H + '（探針）：新原生函式宣告',
        'OverlapCount': H + '（驗證）：新原生函式宣告', 'PoisonedNearby': PR + ' 6：新原生函式宣告',
        'RespecTree': PR + ' 1：新原生函式宣告',
        'ForceFault': H + '（探針卷站 92 故障演練）：新原生函式宣告',
    },
    'ESSBNoForm.psc': {'OnBurst': H + ' 1-4：刪除（免門檻、連斷在 DLL 的切換 task）'},
    'ESSBNodes.psc': {'CarryOverSync': H + ' 1-4：刪除（承接在 DLL）', 'HasPerpetual': H + ' 1-4：刪除（永續在 DLL）'},
    'ESSBTrees.psc': {
        'CacheSlotOf': PR + ' 1：刪除（快取沒有讀者）', 'CachedBranch': PR + ' 1：刪除', 'CachedMainRank': PR + ' 1：刪除', 'SlotFor': PR + ' 1：刪除',
        'OnCustomSkillIncrease': PR + ' 4：點數用 GlobalVariable.Mod(1)（跟 DLL 的結算同時也不會丟點）',
        'OnESSBTreesSettled': PR + ' 1：新事件：DLL 結算完分支或洗完點，更新等級鏡射與節點能力',
        'OnPlayerLoadGame': PR + ' 3：PendingTree 清成 -1',
        'OpenTree': PR + ' 1／3：不再拍快照、不再記 PendingTree（分支結算在 DLL 的選單關閉）',
        'RefreshTree': PR + ' 1：只更新等級與鏡射（約 1000 次原生呼叫的快取重建沒有讀者）',
        'RespecTree': PR + ' 1：交給 ESSBNative.RespecTree（DLL 在 task 裡拿掉節點、點數設回等級）；DLL 沒在運作時照舊',
        'TakeSnapshot': PR + ' 1：刪除（快照在 DLL）',
        'Reconcile': PR + ' 1：刪除（分支結算在 DLL 的選單關閉 task）',
        'ReconcileGained': PR + ' 1／3：刪除（DLL 每次選單關閉都結算）',
        'SettleBranch': PR + ' 1：刪除（結算在 DLL，規則 Runtime.h SettleBranch）',
        'OnMenuClose': PR + ' 1／3：只清旗標（結算是 DLL 的）',
        'Setup': PR + ' 1／3：登記 ESSB_TreesSettled、PendingTree 清成 -1、讀檔時 ESSBNative.CheckPoints',
    },
    'ESSBMCM.psc': {'ShowNativeStatus': H + '（驗證）：顯示兩個 task 同時執行而放棄的次數（ESSBNative.OverlapCount）'},
}
for _script, _rows in _27H.items():
    for _fn, _why in _rows.items():
        _old = REASONS.setdefault(_script, {}).get(_fn)
        REASONS[_script][_fn] = (_old + '；' + _why) if _old else _why
PROPERTY_REASONS = {}
FILES = {}

# Silent edits of this round's code (a number or a call changed inside a declared function): each must fail.
SILENT = [
    # round 27h: SwitchForm / OnFormClosed are gone (the switch is the DLL's); their silent edits moved to what replaced them
    ('ESSBController.psc', 'FormClosedFx', 'If aiReason == 1', 'If aiReason == 2'),
    ('ESSBTrees.psc', 'RefreshTree', 'LevelCache[aiTree] = TreeLevel(aiTree)', 'LevelCache[aiTree] = 1'),
    ('ESSBController.psc', 'OnESSBSwitch', 'Int kind = (EventArg(args, 1) + 0.5) as Int', 'Int kind = (EventArg(args, 2) + 0.5) as Int'),
]


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

    template = (ROOT / 'build/fix27_history_template.py').read_text(encoding='utf-8')
    text = (template.replace('#CHANGED#', table(changed)).replace('#REMOVED#', table(removed))
            .replace('#ADDED#', table(added)).replace('#PROPERTIES#', table(properties)).replace('#FILES#', table(files))
            .replace('#SILENT#', ''.join(f'    {row!r},\n' for row in SILENT)))
    (ROOT / 'build/fix27_history.py').write_text(text, encoding='utf-8', newline='\n')
    print(f'fix27_history: {len(changed)} changed, {len(removed)} removed, {len(added)} added, '
          f'{len(properties)} property blocks, {len(files)} whole files')


if __name__ == '__main__':
    main()

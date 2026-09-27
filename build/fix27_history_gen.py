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
PROPERTY_REASONS = {}
FILES = {}

# Silent edits of this round's code (a number or a call changed inside a declared function): each must fail.
SILENT = [
    ('ESSBController.psc', 'SwitchForm', 'If aiKind == 3', 'If aiKind == 2'),
    ('ESSBController.psc', 'OnFormClosed', 'ESSBNative.FormLeave(aiIndex, True)', 'ESSBNative.FormLeave(aiIndex, False)'),
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

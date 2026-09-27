"""Writes build/fix26_history.py: every round-26 change to the Papyrus sources, each bound to the code by digest.

Run after the round's Papyrus is final (python -B build/fix26_history_gen.py). The reasons are written here, by
function, so a regenerated seal can only restate them; the digests come from the pre-fix26 snapshot and the current
sources (build/fix21_history.digest: comment-stripped body, sha256[:16]).
"""
from pathlib import Path
import hashlib, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build'), str(ROOT)]
import fix21_history as h21

SNAP = ROOT / '.codex/pre-fix26-snapshot/src'
# Round 27: round 26 as shipped is the pre-fix27 snapshot (today's scripts are round 27's, sealed by fix27_history).
SRC = ROOT / '.codex/pre-fix27-snapshot/src'

LOG = 'Round 26（探針 log）：除錯等級 4 時把這裡的動作寫進 DLL 的 ElementsSpellblade.log（ESSBNative.Trace，前面先看等級）；玩法不變'
REASONS = {
    'ESSBController.psc': {
        'Probe': LOG + '（新函式：等級 4 才呼叫 ESSBNative.Trace）',
        'LogEvent': LOG + '（原本的 Papyrus 紀錄在等級 4 也寫一份到探針 log）',
        'LogThrottled': LOG + '（同上，探針 log 不節流）',
        'OnESSBKnock': LOG + '（跌倒與否；Knockdown 照舊只呼叫一次）',
        'OnESSBCleanse': LOG,
        'OnESSBLethal': LOG + '（神佑的狀態）',
        'OnESSBHallucinate': LOG + '（控得到／控不到改幻視、秒數、等級）',
        'OnESSBPush': LOG + '（推的種類、公尺、推不推得動）',
        'OnESSBAsh': LOG + '（化灰與否；ApplyAsh 照舊只呼叫一次）',
        'OnESSBRaise': LOG + '（亡者歸來的參數、能不能復生、結果）',
        'OnESSBSneak': LOG,
        'OnESSBSwitch': LOG + '（Papyrus 換形態的那一半）',
        'OnESSBClose': LOG + '（魔力耗盡關閉的理由）',
        'ApplyFear': LOG,
        'ApplyFrenzy': LOG,
        'RefreshDivineProtection': LOG + '（神佑上鎖、解除、救起）',
        'DumpStatus': LOG + '（「印出目標狀態」的你與最近目標兩行，訊息框那一行也進 log）',
    },
    'ESSBNative.psc': {'Trace': LOG + '（新原生函式宣告）'},
    'ESSBLog.psc': {'Log': LOG + '（等級 4 時每一行也寫進 DLL log）'},
    'ESSBMCM.psc': {
        'ShowNativeStatus': LOG + '（版本與狀態記一行，SETUP-1 用 log 判定）',
    },
    'ESSBElem3.psc': {'PoisonFormTick': LOG + '（以毒攻毒、百毒不侵）'},
}
PROPERTY_REASONS = {}
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

    template = (ROOT / 'build/fix26_history_template.py').read_text(encoding='utf-8')
    text = (template.replace('#CHANGED#', table(changed)).replace('#REMOVED#', table(removed))
            .replace('#ADDED#', table(added)).replace('#PROPERTIES#', table(properties)).replace('#FILES#', table(files)))
    (ROOT / 'build/fix26_history.py').write_text(text, encoding='utf-8', newline='\n')
    print(f'fix26_history: {len(changed)} changed, {len(removed)} removed, {len(added)} added, '
          f'{len(properties)} property blocks, {len(files)} whole files')


if __name__ == '__main__':
    main()

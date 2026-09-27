"""Writes build/fix26_native_history.py: the round-26 seal of the DLL sources, the native tests, the generator modules,
the verifiers and the probe judge.

Run after the round's native / generator / verifier code is final (python -B build/fix26_native_history_gen.py). Every
covered file is bound to its bytes by sha256: unchanged files must equal the pre-fix26 snapshot; changed and added files
carry the reason written here and their sha256. Any later edit, a new file in the covered folders or a missing file fails
the build until the seal is regenerated with a reason.
"""
from pathlib import Path
import hashlib, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / '.codex/pre-fix26-snapshot'

R26 = 'Round 26（探針 log）'
REASONS = {
    'native/include/Trace.h': R26 + '：探針 log 的純標頭（新檔）：行格式 [ESSB][T][種類] #序號 g= r=、Line（480 位元組截斷記號 ~）、'
                              'Buffer（序號在鎖內給、每秒由計時執行緒寫檔）、TraceRng（跟 SplitMix64 同一串擲骰，另記錄）、'
                              '各種行的產生函式（op、op-done、proc、hit-end、remove、hurt、second、env、switch、key）、名稱表、數字鍵區 +／- 的代碼',
    'native/include/StatusEngine.h': R26 + '：RunOp 在引擎有 Tracing() 時呼叫 TraceOp／TraceDone（ChangesValue 決定哪些 op 補一行 op-done）；'
                                     'SelectCrowdWhy 回報每個演員的判定（SelectCrowd 改成它的無回報版，選人不變）；DescribeRemoved（任何我們的效果離開的理由）',
    'native/include/Load.h': R26 + '：解析 ESSB_ProbeStep（站標記）',
    'native/include/ManifestData.h': '由 build/fix19_native.py 產生：版本 0.26.0、kProbeStep',
    'native/src/Plugin.cpp': R26 + '：除錯等級 4 的探針 log（各 sink／task／原生函式的行、ctx 標籤、actor 的生命魔力耐力、TraceRng、'
                             '每秒寫檔與故障／讀檔／存檔／卸載時寫檔、全域變數與節點的監看、站標記鍵與 ESSB_ProbeStep、ESSBNative.Trace）；'
                             'Probe::kHurtTask（受擊 task 不再跟命中 sink 共用 kHurt，X1 兩行都會寫）；X1 改為每個 sink／task 的每條新執行緒一行，'
                             '對照輸入 sink（主迴圈）、最近一次 SKSE task、遊戲視窗與 kDataLoaded（InitTESThread）的執行緒；玩法不變',
    'native/tests/trace_test.cpp': R26 + '：探針 log 的測試（新檔）：格式（build/fix26-trace-format.json 的 regex）、Buffer、TraceRng 不改擲骰、'
                                   '假世界上 RunPlan 的 op／op-done、DescribeRemoved、SelectCrowdWhy；並用真規劃器寫出 build/fix26-trace-sample.log',
    'native/CMakeLists.txt': R26 + '：trace_test；版本 0.26.0',
    'native/build.py': R26 + '：寫出 build/fix26-trace-format.json；4 個探針 log 突變（錄骰改擲骰、截斷記號、op-done 多寫、掃描判定標錯）',
    'build_v03.py': R26 + '：ESSB_ProbeStep 記錄（fix26_records）、MCM 除錯等級加「4：探針 log」與說明、呼叫 build/fix26_verify.py',
    'build/fix19_native.py': R26 + '：NATIVE_VERSION 0.26.0；manifest 的 globals 加 ESSB_ProbeStep；NEW_EDIDS 含 round 26',
    'build/fix26_records.py': R26 + '：round 26 記錄表（新檔）：ESSB_ProbeStep 0x005C00',
    'build/fix26_format.py': R26 + '：探針 log 每種行的 regex（新檔），trace_test 與 probe-judge 共用',
    'build/probe-judge.py': R26 + '：依 build/probes-all.md 的 91 站判定 102 步的判定器（新檔）',
    'build/fix26_verify.py': R26 + '：round 26 的驗證器（新檔）：判定器涵蓋、卷與判定器一致、原生樣本與手寫樣本的 PASS／FAIL、原始碼的探針檢查、記錄、突變、封印、行尾',
    'build/fix25_history.py': R26 + '：round 25 的 Papyrus 封印改讀 pre-fix26 快照（先過 round 26 的證明；由產生器重寫，表格不變）',
    'build/fix25_history_gen.py': R26 + '：產生器讀 pre-fix26 快照的 src（round 25 出貨時的腳本）',
    'build/fix25_history_template.py': R26 + '：current_dir 改成 fix26_history.legacy_source()',
    'build/fix25_native_history.py': R26 + '：round 25 的原生封印改讀 pre-fix26 快照（先過 round 26 的證明；由產生器重寫，表格不變）',
    'build/fix25_native_history_gen.py': R26 + '：產生器列出並雜湊 pre-fix26 快照（round 25 出貨時的位元組）',
    'build/fix25_native_history_template.py': R26 + '：base() 讀 pre-fix26 快照（同 round 25 對 round 24 的做法）',
    'build/fix26_history.py': R26 + '：round 26 的 Papyrus 封印（產生的）',
    'build/fix26_history_gen.py': R26 + '：round 26 Papyrus 封印產生器（新檔）',
    'build/fix26_history_template.py': R26 + '：round 26 Papyrus 封印樣板（新檔）',
    'build/fix26_native_history_gen.py': R26 + '：round 26 原生封印產生器（新檔）',
    'build/fix26_native_history_template.py': R26 + '：round 26 原生封印樣板（新檔）',
}

VERIFIERS = ('fix6_verify.py', 'fix11_verify.py', 'fix16_verify.py', 'fix21_verify.py', 'fix22_verify.py', 'fix23_verify.py',
             'fix24_verify.py', 'fix25_verify.py', 'fix26_verify.py', 'fix21_identity.py',
             'fix22_history.py', 'fix22_history_gen.py', 'fix22_history_template.py', 'fix22_native_history.py',
             'fix22_native_history_gen.py', 'fix22_native_history_template.py', 'fix23_history.py', 'fix23_history_gen.py',
             'fix23_history_template.py', 'fix23_native_history.py', 'fix23_native_history_gen.py', 'fix23_native_history_template.py',
             'fix24_history.py', 'fix24_history_gen.py', 'fix24_history_template.py', 'fix24_native_history.py',
             'fix24_native_history_gen.py', 'fix24_native_history_template.py',
             'fix25_history.py', 'fix25_history_gen.py', 'fix25_history_template.py', 'fix25_native_history.py',
             'fix25_native_history_gen.py', 'fix25_native_history_template.py',
             'fix26_history.py', 'fix26_history_gen.py', 'fix26_history_template.py', 'fix26_native_history_gen.py',
             'fix26_native_history_template.py')


def covered():
    files = []
    for part in ('include', 'src', 'tests'):
        files += sorted((ROOT / 'native' / part).glob('*.*'))
    files += [ROOT / 'native/CMakeLists.txt', ROOT / 'native/build.py']
    files += sorted(p for p in ROOT.glob('*.py'))
    files += [ROOT / f'build/{n}' for n in ('fix19_native.py', 'fix21_records.py', 'fix22_records.py', 'fix22_reference.py',
                                             'fix22_fixture.py', 'fix23_records.py', 'fix23_reference.py', 'fix23_fixture.py',
                                             'fix24_records.py', 'fix24_reference.py', 'fix24_fixture.py',
                                             'fix25_records.py', 'fix25_reference.py', 'fix25_fixture.py',
                                             'fix26_records.py', 'fix26_format.py', 'probe-judge.py')]
    # The verifiers too (a weakened check would otherwise pass unseen). This seal cannot hold itself;
    # build/fix26_native_history.py is regenerated last.
    files += [ROOT / f'build/{n}' for n in VERIFIERS]
    return [p.relative_to(ROOT).as_posix() for p in files]


def before_sha(rel):
    snap = SNAP / rel
    return hashlib.sha256(snap.read_bytes()).hexdigest() if snap.is_file() else None


def main():
    rows = []
    for rel in covered():
        now = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        before = before_sha(rel)
        if before == now:
            rows.append((rel, 'unchanged', now, ''))
            continue
        why = REASONS.get(rel)
        assert why, (rel, 'changed in round 26 but no reason is written in build/fix26_native_history_gen.py')
        rows.append((rel, 'added' if before is None else 'changed', now, why))
    body = ''.join(f'    {rel!r}: ({state!r}, {sha!r}, {why!r}),\n' for rel, state, sha, why in rows)
    text = (Path(__file__).with_name('fix26_native_history_template.py').read_text(encoding='utf-8')
            .replace('#FILES#', body))
    (ROOT / 'build/fix26_native_history.py').write_text(text, encoding='utf-8', newline='\n')
    counts = {s: sum(1 for r in rows if r[1] == s) for s in ('unchanged', 'changed', 'added')}
    print(f'fix26_native_history: {counts}')


if __name__ == '__main__':
    main()

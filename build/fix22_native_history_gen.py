"""Writes build/fix22_native_history.py: the round-22 seal of the DLL sources, the native tests and the generator modules
(review fix 6: the Papyrus seal build/fix22_history.py did not cover them).

Run after the round's native / generator code is final (python -B build/fix22_native_history_gen.py). Every covered file
is bound to its bytes by sha256: unchanged files must equal the pre-fix22 snapshot (or HEAD when the snapshot does not
hold them); changed and added files carry the reason written here and their sha256. Any later edit, a new file in the
covered folders or a missing file fails the build until the seal is regenerated with a reason.
"""
from pathlib import Path
import hashlib, subprocess, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / '.codex/pre-fix22-snapshot'

REASONS = {
    'native/include/Status.h': 'N3：狀態層的純規則（新檔）；審查修正：基礎劑數、擴散一劑、瘴氣／瘟疫每秒、幻影、御風、聖痕、冰晶多留 1 秒',
    'native/include/StatusEngine.h': '審查修正 6：狀態層的引擎端（讀、驅散、施放、沖刷、移除事件、結算）對抽象引擎寫，測試用假引擎',
    'native/include/ManifestData.h': '由 build/fix19_native.py 產生：狀態記錄、N3 節點、DoT 與 Tuning 的全域變數',
    'native/include/HitMath.h': 'N3：Tuning 加 multDot／poisonDotK／bleedDotK（持續傷改由 DLL 寫強度）',
    'native/include/EngineFacts.h': 'N3：ReadTuning 讀 ESSB_MultDot、ESSB_PoisonDotK、ESSB_BleedDotK',
    'native/src/Plugin.cpp': 'N3：狀態層接上引擎（sink、task、ModEvent、原生函式）；審查修正：引擎轉接、總開關、放血法術解析、冰晶帶進結算',
    'native/tests/status_test.cpp': 'N3：狀態層 S／W 測試（新檔）',
    'native/tests/engine_test.cpp': '審查修正 6：引擎端對假效果清單與假施法者（新檔）',
    'native/CMakeLists.txt': 'N3：status_test、engine_test；版本 0.22.0',
    'native/build.py': '審查修正 6：C++ 原始碼突變測試（MUTANTS），結果寫進收據',
    'build_v03.py': 'N3：狀態層記錄、stub、驗證、進入點（聖盾、御風、幻影）',
    'plan_coverage.py': 'N3：節點與機制狀態（round 22 與審查修正）',
    'build/fix19_native.py': 'N3：ManifestData 的狀態區段、DoT 全域變數、測試夾具與 status_test',
    'build/fix21_records.py': 'N3：冰甲寒氣的第二個互斥效果（量表 ≥1 改 35%）',
    'build/fix22_records.py': 'N3：狀態層記錄表（新檔）；審查修正：瘴氣披風拿掉、幻影效果',
    'build/fix22_reference.py': 'N3：照 v0.4 寫的參考模型（新檔）；審查修正同步',
    'build/fix22_fixture.py': 'N3：狀態表與接線夾具（新檔）；審查修正：手算預期值 HAND',
}


def covered():
    files = []
    for part in ('include', 'src', 'tests'):
        files += sorted((ROOT / 'native' / part).glob('*.*'))
    files += [ROOT / 'native/CMakeLists.txt', ROOT / 'native/build.py']
    files += sorted(p for p in ROOT.glob('*.py'))
    files += [ROOT / f'build/{n}' for n in ('fix19_native.py', 'fix21_records.py', 'fix22_records.py', 'fix22_reference.py',
                                             'fix22_fixture.py')]
    return [p.relative_to(ROOT).as_posix() for p in files]


def before_sha(rel):
    snap = SNAP / rel
    if snap.is_file():
        return hashlib.sha256(snap.read_bytes()).hexdigest()
    r = subprocess.run(['git', '-C', str(ROOT), 'show', f'HEAD:{rel}'], capture_output=True)
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None


def main():
    rows = []
    for rel in covered():
        now = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        before = before_sha(rel)
        if before == now:
            rows.append((rel, 'unchanged', now, ''))
            continue
        why = REASONS.get(rel)
        assert why, (rel, 'changed in round 22 but no reason is written in build/fix22_native_history_gen.py')
        rows.append((rel, 'added' if before is None else 'changed', now, why))
    body = ''.join(f'    {rel!r}: ({state!r}, {sha!r}, {why!r}),\n' for rel, state, sha, why in rows)
    text = (Path(__file__).with_name('fix22_native_history_template.py').read_text(encoding='utf-8')
            .replace('#FILES#', body))
    (ROOT / 'build/fix22_native_history.py').write_text(text, encoding='utf-8', newline='\n')
    counts = {s: sum(1 for r in rows if r[1] == s) for s in ('unchanged', 'changed', 'added')}
    print(f'fix22_native_history: {counts}')


if __name__ == '__main__':
    main()

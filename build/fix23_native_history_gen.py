"""Writes build/fix23_native_history.py: the round-23 seal of the DLL sources, the native tests and the generator modules.

Run after the round's native / generator code is final (python -B build/fix23_native_history_gen.py). Every covered file
is bound to its bytes by sha256: unchanged files must equal the pre-fix23 snapshot; changed and added files carry the
reason written here and their sha256. Any later edit, a new file in the covered folders or a missing file fails the build
until the seal is regenerated with a reason.
"""
from pathlib import Path
import hashlib, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / '.codex/pre-fix23-snapshot'

REASONS = {
    'native/include/SelfLayer.h': 'N4：你的資源的純規則（新檔）：命中、開印、無形態、離開／進入形態、每秒、化身的節點檢視',
    'native/include/Hurt.h': 'N4：受擊與施法事件的純規則（新檔）：法盾、水幕、護血、化法為力、受擊分支、逼近、反咒',
    'native/include/TrueHud.h': 'R5：TrueHUD 自訂小工具介面的自寫宣告（版面以本機 TrueHUD.pdb 核對並 static_assert）與四條資源條（新檔）',
    'native/include/Status.h': 'N4：自身資源的常數與寫入器（namespace n4／res）、終焉的協奏／三重奏／過載終焉與自身部分、新 Op／ModEvent、護血池讀取',
    'native/include/StatusEngine.h': 'N4：新 op 的引擎呼叫（付耐力、共鳴、打斷、碎岩、冰心）與要解析的法術',
    'native/include/HitMath.h': 'N4：雷的 N 取電荷、疾電暴擊、血刃、超載池（滅法先花）、破式',
    'native/include/ManifestData.h': '由 build/fix19_native.py 產生：round 23 的狀態記錄、N4 節點、鏡射全域變數、kSustainLegend',
    'native/src/Plugin.cpp': 'N4：受擊 sink＋task、施法事件 sink、選單 sink（TrueHUD）、自身資源接上命中／開印／形態／計時器、鏡射、多段觸發、玩家碼 40–58、FormEnter／SetSync、死亡快照第 9 值',
    'native/tests/self_test.cpp': 'N4：自身資源與受擊的 S／W／X 測試（新檔）',
    'native/tests/status_test.cpp': 'N4：狀態種類前綴 ESSB_N4_、新 ModEvent 的參數數目',
    'native/tests/engine_test.cpp': 'N4：假引擎的新 op 與護血池的解析',
    'native/tests/hit_pipeline_test.cpp': 'N4：雷的 N 取電荷（拿掉 kChargesUntilN4）；D5 電荷暴擊率',
    'native/CMakeLists.txt': 'N4：self_test；版本 0.23.0',
    'native/build.py': 'N4：SelfLayer.h／Hurt.h／三重奏的原始碼突變；突變資料夾放全部標頭副本、每次重建',
    'build_v03.py': 'N4：round 23 記錄、法盾／水幕／護血／聖佑／冰盾／蓄能／餘魔／空中追擊的 PERK 進入點、殘影與破護改讀 DLL 效果、fix23 驗證',
    'plan_coverage.py': 'N4：84 個 N4 節點的狀態',
    'build/fix19_native.py': 'N4：ManifestData 的 round 23 區段、鏡射全域變數、夾具與 self_test',
    'build/fix22_records.py': 'R7：聖佑各階法術帶魔抗效果',
    'build/fix22_fixture.py': 'N4：接線表接上 round 23 的狀態種類',
    'build/fix23_records.py': 'N4：round 23 記錄表（新檔）',
    'build/fix23_reference.py': 'N4：照 v0.4 寫的參考模型（新檔）',
    'build/fix23_fixture.py': 'N4：自身資源表與接線夾具（新檔）；手算預期值 HAND',
    'native/include/EngineFacts.h': '審查修正：ReadTuning 讀 ESSB_SyncT1..3（同調門檻與 Papyrus 永續同一份）',
    'build/fix16_verify.py': 'N4：殘影與破護不再用 Papyrus 視窗（擁有者表拿掉兩格）',
    'build/fix21_verify.py': 'N4：岩甲基礎進入點只看以 ESSB_RockArmor 為條件的那些（基礎天賦多了 round 23 的進入點）',
    'build/fix23_verify.py': 'N4：round 23 的驗證器（新檔）',
    'build/fix22_history.py': 'N4：round 22 的 Papyrus 封印改讀 pre-fix23 快照（先過 round 23 的證明）',
    'build/fix22_history_gen.py': 'N4：同上（產生器）', 'build/fix22_history_template.py': 'N4：同上（樣板）',
    'build/fix22_native_history.py': 'N4：round 22 的原生封印改讀 pre-fix23 快照（先過 round 23 的證明）',
    'build/fix22_native_history_gen.py': 'N4：同上（產生器）', 'build/fix22_native_history_template.py': 'N4：同上（樣板）',
    'build/fix23_history.py': 'N4：round 23 的 Papyrus 封印（產生的）', 'build/fix23_history_gen.py': 'N4：round 23 Papyrus 封印產生器（新檔）',
    'build/fix23_history_template.py': 'N4：round 23 Papyrus 封印樣板（新檔）',
    'build/fix23_native_history_gen.py': 'N4：round 23 原生封印產生器（新檔）', 'build/fix23_native_history_template.py': 'N4：round 23 原生封印樣板（新檔）',
}


VERIFIERS = ('fix16_verify.py', 'fix21_verify.py', 'fix22_verify.py', 'fix23_verify.py', 'fix21_identity.py',
             'fix22_history.py', 'fix22_history_gen.py', 'fix22_history_template.py', 'fix22_native_history.py',
             'fix22_native_history_gen.py', 'fix22_native_history_template.py', 'fix23_history.py', 'fix23_history_gen.py',
             'fix23_history_template.py', 'fix23_native_history_gen.py', 'fix23_native_history_template.py')


def covered():
    files = []
    for part in ('include', 'src', 'tests'):
        files += sorted((ROOT / 'native' / part).glob('*.*'))
    files += [ROOT / 'native/CMakeLists.txt', ROOT / 'native/build.py']
    files += sorted(p for p in ROOT.glob('*.py'))
    files += [ROOT / f'build/{n}' for n in ('fix19_native.py', 'fix21_records.py', 'fix22_records.py', 'fix22_reference.py',
                                             'fix22_fixture.py', 'fix23_records.py', 'fix23_reference.py', 'fix23_fixture.py')]
    # Round 23 review: the verifiers too -- the ones this round changed and the round's own (a weakened check would
    # otherwise pass unseen). This seal cannot hold itself; build/fix23_native_history.py is regenerated last.
    files += [ROOT / f'build/{n}' for n in (VERIFIERS)]
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
        assert why, (rel, 'changed in round 23 but no reason is written in build/fix23_native_history_gen.py')
        rows.append((rel, 'added' if before is None else 'changed', now, why))
    body = ''.join(f'    {rel!r}: ({state!r}, {sha!r}, {why!r}),\n' for rel, state, sha, why in rows)
    text = (Path(__file__).with_name('fix23_native_history_template.py').read_text(encoding='utf-8')
            .replace('#FILES#', body))
    (ROOT / 'build/fix23_native_history.py').write_text(text, encoding='utf-8', newline='\n')
    counts = {s: sum(1 for r in rows if r[1] == s) for s in ('unchanged', 'changed', 'added')}
    print(f'fix23_native_history: {counts}')


if __name__ == '__main__':
    main()

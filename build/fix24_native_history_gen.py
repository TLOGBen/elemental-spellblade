"""Writes build/fix24_native_history.py: the round-24 seal of the DLL sources, the native tests, the generator modules and
the verifiers.

Run after the round's native / generator / verifier code is final (python -B build/fix24_native_history_gen.py). Every
covered file is bound to its bytes by sha256: unchanged files must equal the pre-fix24 snapshot; changed and added files
carry the reason written here and their sha256. Any later edit, a new file in the covered folders or a missing file fails
the build until the seal is regenerated with a reason.
"""
from pathlib import Path
import hashlib, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / '.codex/pre-fix24-snapshot'

N5 = 'N5（round 24）'
REASONS = {
    'native/include/Reactions.h': N5 + '：反應本體、融斷、死亡處理、範圍掃描的純規則（新檔）：群體與 Around、表驅動的開印／終焉本體與各樹分支、'
                                  '冰封／幻覺／聖裁／濺血／越線／碎冰／落地／放電／風刃／過熱本體、共鳴計數、碎岩、冰心、聚星、星蝕、命中本體、'
                                  '回聲與星鏈、PlanBurst、PlanDeath（含 C3 的不死、蔓延、亡者歸來）、PlanAdvent、印潮、化身、火浴（PlanFireBath）',
    'native/include/Status.h': N5 + '：StatusOp／StatusPlan 的 at（群體成員）、新 op（削魔、同伴治療、沉默、寂、有時限效果、noop）、新事件'
                               '（推力、化灰、復生、潛行、領域、過熱）、計畫上限 512、寂讀進 Board、星痕引爆與闇星一擊的標籤、聖裁事件帶傷害、'
                               '毒斷（融斷的催毒 ×4）',
    'native/include/StatusEngine.h': N5 + '：RunOp 先選成員、本體事件不送 Papyrus、SelectCrowd（2.9 資格）、DeathCounts、新 op 的法術與效果解析',
    'native/include/SelfLayer.h': N5 + '：闇星一擊帶標籤（星蝕讀它）',
    'native/include/HitMath.h': N5 + '：飲血的嗜血吸血 +10%、寂讓之後的沉默每層 +0.5 秒、兩個新調整值',
    'native/include/EngineFacts.h': N5 + '：讀兩個新調整全域變數（霜結減速、湧泉耐力）',
    'native/include/ManifestData.h': '由 build/fix19_native.py 產生：round 24 的狀態記錄、有時限效果家族、N5 節點與表、新法術與效果、全域變數',
    'native/src/Plugin.cpp': N5 + '：一個事件掃一次群體（BuildCrowd）、RunWithBodies、命中／受擊／過期／原生函式都走本體、死亡 sink 重寫'
                             '（ESSB_Death 快照拿掉）、Burst 原生函式取代 BurstMarks、FormEnter 做各元素的臨、火浴改呼叫 PlanFireBath、'
                             'Papyrus 本體用的原生掛勾刪除、推力事件的中心換成 FormID、計畫放堆積',
    'native/tests/reaction_test.cpp': N5 + '：反應本體、融斷、死亡、臨、回聲、命中本體的 R／W／X 測試（新檔）',
    'native/tests/engine_test.cpp': N5 + '：假 process list（SelectCrowd）與假死亡事件（DeathCounts、一次完整死亡）；本體事件不送 Papyrus',
    'native/tests/status_test.cpp': N5 + '：狀態種類前綴 ESSB_N5_、新事件的參數數目、過熱事件由本體消耗',
    'native/tests/self_test.cpp': N5 + '：狀態種類前綴 ESSB_N5_、新事件的參數數目',
    'native/CMakeLists.txt': N5 + '：reaction_test；版本 0.24.0',
    'native/build.py': N5 + '：Reactions.h 的原始碼突變（reaction_test 的表）',
    'build_v03.py': N5 + '：round 24 記錄、安全閥讀 ESSB_N5_SafetyValve、ESSBReactions／ESSBGuard 從腳本清單與 VMAD 拿掉、fix24 驗證',
    'plan_coverage.py': N5 + '：189 個 -N5 節點的狀態（187 DONE、冰封融斷 LATER-待決、神聖領域 PARTIAL-N6）與共通機制',
    'build/fix19_native.py': N5 + '：ManifestData 的 round 24 區段、kTimed、表、夾具與 reaction_test',
    'build/fix22_fixture.py': N5 + '：接線表接上 round 24 的狀態種類',
    'build/fix22_reference.py': N5 + '：毒斷（融斷的催毒 ×4）',
    'build/fix24_records.py': N5 + '：round 24 記錄表（新檔）',
    'build/fix24_reference.py': N5 + '：照 v0.4 寫的參考模型（新檔）與 25 個手算錨點',
    'build/fix24_fixture.py': N5 + '：反應本體表與接線夾具（新檔）',
    'build/fix6_verify.py': N5 + '：百分比主線的 DLL 位置加上 Reactions.h／HitMath.h；Papyrus 執行檢查改讀 pre-fix24 腳本（fix24_history 綁定）',
    'build/fix11_verify.py': N5 + '：src/* 改讀舊輪次的腳本（同 fix8／9／10 的 CUR22），round 24 刪了兩個腳本',
    'build/fix16_verify.py': N5 + '：安全閥改讀 DLL 的 ESSB_N5_SafetyValve（視窗擁有者表拿掉一格）',
    'build/fix21_identity.py': N5 + '：自我測試的注入點換到還留在 Papyrus 的讀取（ESSBElem2、臨的主線、ESSBInput）',
    'build/fix22_verify.py': N5 + '：契約檢查加上 Reactions.h 的事件、排除本體專用事件、死亡快照可以不存在；自我測試換到還在的原生函式與事件',
    'build/fix23_verify.py': N5 + '：ESSB_Death 拿掉；受擊事件的檢查改成任何腳本都不能處理（ESSBGuard 刪除）',
    'build/fix24_verify.py': N5 + '：round 24 的驗證器（新檔）',
    'build/fix23_history.py': N5 + '：round 23 的 Papyrus 封印改讀 pre-fix24 快照（先過 round 24 的證明）',
    'build/fix23_history_template.py': N5 + '：同上（樣板）',
    'build/fix23_native_history.py': N5 + '：round 23 的原生封印改讀 pre-fix24 快照（先過 round 24 的證明）',
    'build/fix23_native_history_template.py': N5 + '：同上（樣板）',
    'build/fix24_history.py': N5 + '：round 24 的 Papyrus 封印（產生的）', 'build/fix24_history_gen.py': N5 + '：round 24 Papyrus 封印產生器（新檔）',
    'build/fix24_history_template.py': N5 + '：round 24 Papyrus 封印樣板（新檔）',
    'build/fix24_native_history_gen.py': N5 + '：round 24 原生封印產生器（新檔）',
    'build/fix24_native_history_template.py': N5 + '：round 24 原生封印樣板（新檔）',
}

VERIFIERS = ('fix6_verify.py', 'fix11_verify.py', 'fix16_verify.py', 'fix21_verify.py', 'fix22_verify.py', 'fix23_verify.py',
             'fix24_verify.py', 'fix21_identity.py',
             'fix22_history.py', 'fix22_history_gen.py', 'fix22_history_template.py', 'fix22_native_history.py',
             'fix22_native_history_gen.py', 'fix22_native_history_template.py', 'fix23_history.py', 'fix23_history_gen.py',
             'fix23_history_template.py', 'fix23_native_history.py', 'fix23_native_history_gen.py', 'fix23_native_history_template.py',
             'fix24_history.py', 'fix24_history_gen.py', 'fix24_history_template.py', 'fix24_native_history_gen.py',
             'fix24_native_history_template.py')


def covered():
    files = []
    for part in ('include', 'src', 'tests'):
        files += sorted((ROOT / 'native' / part).glob('*.*'))
    files += [ROOT / 'native/CMakeLists.txt', ROOT / 'native/build.py']
    files += sorted(p for p in ROOT.glob('*.py'))
    files += [ROOT / f'build/{n}' for n in ('fix19_native.py', 'fix21_records.py', 'fix22_records.py', 'fix22_reference.py',
                                             'fix22_fixture.py', 'fix23_records.py', 'fix23_reference.py', 'fix23_fixture.py',
                                             'fix24_records.py', 'fix24_reference.py', 'fix24_fixture.py')]
    # The verifiers too (a weakened check would otherwise pass unseen). This seal cannot hold itself;
    # build/fix24_native_history.py is regenerated last.
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
        assert why, (rel, 'changed in round 24 but no reason is written in build/fix24_native_history_gen.py')
        rows.append((rel, 'added' if before is None else 'changed', now, why))
    body = ''.join(f'    {rel!r}: ({state!r}, {sha!r}, {why!r}),\n' for rel, state, sha, why in rows)
    text = (Path(__file__).with_name('fix24_native_history_template.py').read_text(encoding='utf-8')
            .replace('#FILES#', body))
    (ROOT / 'build/fix24_native_history.py').write_text(text, encoding='utf-8', newline='\n')
    counts = {s: sum(1 for r in rows if r[1] == s) for s in ('unchanged', 'changed', 'added')}
    print(f'fix24_native_history: {counts}')


if __name__ == '__main__':
    main()

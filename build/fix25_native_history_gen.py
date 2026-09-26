"""Writes build/fix25_native_history.py: the round-25 seal of the DLL sources, the native tests, the generator modules and
the verifiers.

Run after the round's native / generator / verifier code is final (python -B build/fix25_native_history_gen.py). Every
covered file is bound to its bytes by sha256: unchanged files must equal the pre-fix25 snapshot; changed and added files
carry the reason written here and their sha256. Any later edit, a new file in the covered folders or a missing file fails
the build until the seal is regenerated with a reason.
"""
from pathlib import Path
import hashlib, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / '.codex/pre-fix25-snapshot'

N6 = 'N6（round 25）'
REV = '；審查修正：'
REASONS = {
    'native/include/Timer.h': N6 + '：每秒工作、領域的 DLL 那一半與熱鍵判定的純規則（新檔）：Cadence 時鐘（暫停／選單／讀檔不走）、'
                              'PlanFormSecond（維持費、魔力歸零 2 秒、血形態扣血、長流與長河、雷雨電荷）、Environment、'
                              'InsideOf／PlanDomainSelf／PlanDomainEnemy、SlowImmune／IsSlow、KeyCodeOf／HotkeyElement／InputOpen／PlanSwitch'
                              + REV + '雷雨＝下雨且有雷電、暴風雪＝下雪且風大（EnvFlags.thunder／stormy）、HasDomainNode、血形態扣血用同一個上限',
    'native/include/Status.h': N6 + '：Op::kStaminaTarget（長河的同伴耐力）、Event::kSwitch／kClose、DomainSpawnSpell（領域的整秒放置法術）',
    'native/include/StatusEngine.h': N6 + '：ESSB_Domain 事件先在成員腳下施放 Spawn Hazard 法術（不覆寫強度）、沉默當下把魔力扣到 0、'
                                     '潮池的沖刷上限、CastSpells 加放置法術與同伴耐力',
    'native/include/ManifestData.h': '由 build/fix19_native.py 產生：round 25 的狀態記錄、領域表（HAZD／Spawn Hazard／放置法術）、'
                                     '維持費設定、計時器與熱鍵的全域變數、新節點',
    'native/src/Plugin.cpp': N6 + '：計時器改用 Cadence（只算遊戲在跑的時間）；每秒：維持費／長流／雷雨、環境每 5 秒、領域掃描'
                             '（格子參照＋放置效果的 hazard handle）、敵人與你的領域效果、聖域鏡射、沉默扣魔；每 tick：免疫減速；'
                             '輸入事件 sink 與 RequestSwitch；ExtendFuse、WashBuffs 原生函式與 SetWindow 32–35 刪除'
                             + REV + '聖域鏡射拿掉、沒有領域節點就不掃描、ESSB_EnvThunder、RunningSeconds 原生函式（遊戲時鐘）',
    'native/tests/timer_test.cpp': N6 + '：計時器、領域、熱鍵的 T／W／X 測試（新檔）' + REV + '天氣的雷電與風速、領域節點閘門、ESSB_EnvThunder 接線',
    'native/tests/engine_test.cpp': N6 + '：假引擎加 DrainMagickaAll（沉默當下扣魔）',
    'native/tests/status_test.cpp': N6 + '：狀態種類前綴 ESSB_N6_、事件表加 Switch／Close',
    'native/tests/self_test.cpp': N6 + '：同上',
    'native/tests/reaction_test.cpp': N6 + '：同上',
    'native/CMakeLists.txt': N6 + '：timer_test；版本 0.25.0',
    'native/build.py': N6 + '：Timer.h 與領域施放的 10 個原始碼突變（timer_test 的表）' + REV + '再 4 個（雷雨、暴風雪、領域節點閘門、血形態上限）',
    'build_v03.py': N6 + '：round 25 記錄、ESSBFormRules／ESSBInput／ESSBSilence 從腳本清單與 VMAD 拿掉、控制器屬性、別名腳本 3 → 2、fix25 驗證'
                    + REV + '聖域／神聖領域的「你在其中受傷 -20%」PERK 進入點拿掉、GCombo 不再綁',
    'plan_coverage.py': N6 + '：神聖領域、毒霧、各領域與每秒工作的節點狀態與位置' + REV + '聖域、神聖領域、環境、雷雨列',
    'build/fix19_native.py': N6 + '：ManifestData 的 round 25 區段、領域表、夾具與 timer_test' + REV + 'ESSB_EnvThunder、拿掉 ESSB_DomainDivine',
    'build/fix22_fixture.py': N6 + '：接線表接上 round 25 的狀態種類',
    'build/fix25_records.py': N6 + '：round 25 記錄表（新檔）' + REV + '聖域的兩個減弱效果（DIVINE_WEAKEN）、ESSB_EnvThunder',
    'build/fix25_reference.py': N6 + '：照 v0.4 寫的參考模型（新檔）與手算錨點' + REV + '2.10 天氣判定、血形態上限（錨點 0.72 → 0.6）',
    'build/fix25_fixture.py': N6 + '：計時器表與接線夾具（新檔）' + REV + '接線改 ESSB_EnvThunder',
    'build/fix21_identity.py': N6 + '：自我測試的注入點換到還在的腳本（ESSBInput 刪除，改 ESSBFormPowerEffect）',
    'build/fix6_verify.py': N6 + '：長流的 Papyrus 執行檢查改讀 pre-fix25 腳本（fix25_history 綁定），DLL 端由 timer_test 驗',
    'build/fix22_verify.py': N6 + '（審查修正）：原生函式登記的比對也認得帶 callableFromTasklets 的登記（RunningSeconds），仍逐一比對宣告、參數數目；'
                             '防護檢查多認一種：函式本身有 SEH 框與 C++ catch（RunningSeconds 在總開關關著時也要回答）',
    'build/fix24_verify.py': N6 + '：排隊的原生函式清單拿掉 ExtendFuse、WashBuffs（round 25 刪除）；schema 13 改讀 pre-fix25 的 settings；'
                             '行為檢查裡被刪的函式改在 pre-fix25 腳本上跑',
    'build/fix25_verify.py': N6 + '：round 25 的驗證器（新檔）' + REV + '聖域的 hazard 效果、沒有 PERK 讀 ESSB_DomainDivine、秒計時器不用真實時間、領域節點閘門、RunningSeconds',
    'build/fix24_history.py': N6 + '：round 24 的 Papyrus 封印改讀 pre-fix25 快照（先過 round 25 的證明）',
    'build/fix24_history_template.py': N6 + '：同上（樣板）',
    'build/fix24_native_history.py': N6 + '：round 24 的原生封印改讀 pre-fix25 快照（先過 round 25 的證明）',
    'build/fix24_native_history_template.py': N6 + '：同上（樣板）',
    'build/fix25_history.py': N6 + '：round 25 的 Papyrus 封印（產生的）',
    'build/fix25_history_gen.py': N6 + '：round 25 Papyrus 封印產生器（新檔）' + REV + '秒計時器與連段的理由',
    'build/fix25_history_template.py': N6 + '：round 25 Papyrus 封印樣板（新檔）',
    'build/fix25_native_history_gen.py': N6 + '：round 25 原生封印產生器（新檔）',
    'build/fix25_native_history_template.py': N6 + '：round 25 原生封印樣板（新檔）',
}
# Verifiers that later edits in this round may touch are added to REASONS as they change (the gen refuses otherwise).
EXTRA = {}

VERIFIERS = ('fix6_verify.py', 'fix11_verify.py', 'fix16_verify.py', 'fix21_verify.py', 'fix22_verify.py', 'fix23_verify.py',
             'fix24_verify.py', 'fix25_verify.py', 'fix21_identity.py',
             'fix22_history.py', 'fix22_history_gen.py', 'fix22_history_template.py', 'fix22_native_history.py',
             'fix22_native_history_gen.py', 'fix22_native_history_template.py', 'fix23_history.py', 'fix23_history_gen.py',
             'fix23_history_template.py', 'fix23_native_history.py', 'fix23_native_history_gen.py', 'fix23_native_history_template.py',
             'fix24_history.py', 'fix24_history_gen.py', 'fix24_history_template.py', 'fix24_native_history.py',
             'fix24_native_history_gen.py', 'fix24_native_history_template.py',
             'fix25_history.py', 'fix25_history_gen.py', 'fix25_history_template.py', 'fix25_native_history_gen.py',
             'fix25_native_history_template.py')


def covered():
    files = []
    for part in ('include', 'src', 'tests'):
        files += sorted((ROOT / 'native' / part).glob('*.*'))
    files += [ROOT / 'native/CMakeLists.txt', ROOT / 'native/build.py']
    files += sorted(p for p in ROOT.glob('*.py'))
    files += [ROOT / f'build/{n}' for n in ('fix19_native.py', 'fix21_records.py', 'fix22_records.py', 'fix22_reference.py',
                                             'fix22_fixture.py', 'fix23_records.py', 'fix23_reference.py', 'fix23_fixture.py',
                                             'fix24_records.py', 'fix24_reference.py', 'fix24_fixture.py',
                                             'fix25_records.py', 'fix25_reference.py', 'fix25_fixture.py')]
    # The verifiers too (a weakened check would otherwise pass unseen). This seal cannot hold itself;
    # build/fix25_native_history.py is regenerated last.
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
        why = REASONS.get(rel) or EXTRA.get(rel)
        assert why, (rel, 'changed in round 25 but no reason is written in build/fix25_native_history_gen.py')
        rows.append((rel, 'added' if before is None else 'changed', now, why))
    body = ''.join(f'    {rel!r}: ({state!r}, {sha!r}, {why!r}),\n' for rel, state, sha, why in rows)
    text = (Path(__file__).with_name('fix25_native_history_template.py').read_text(encoding='utf-8')
            .replace('#FILES#', body))
    (ROOT / 'build/fix25_native_history.py').write_text(text, encoding='utf-8', newline='\n')
    counts = {s: sum(1 for r in rows if r[1] == s) for s in ('unchanged', 'changed', 'added')}
    print(f'fix25_native_history: {counts}')


if __name__ == '__main__':
    main()

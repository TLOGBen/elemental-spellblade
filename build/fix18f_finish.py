"""Package verified probe artifacts and append the scoped implementation record."""
from pathlib import Path
import hashlib
import html
import json
import runpy
import zipfile


def main():
    work=Path(__file__).resolve().parents[1]
    stage=work/'build/round18f'
    folder=work/'build/fix18-probe-package'
    digest=runpy.run_path(str(work/'build/fix18f_isolated.py'))['digest_tree']
    baseline=json.loads((stage/'baseline.json').read_text(encoding='utf8'))
    preservation=json.loads((folder/'preservation.json').read_text(encoding='utf8'))
    assert 'round18f' in preservation['build_log'] and preservation['build_exit_code']==0
    log=(work/preservation['build_log']).read_text(encoding='utf8')
    assert all(x in log for x in ('PROBE-ROUND18F ok:','PROBE-SETUP ok:','READBACK ok:','ENGINE COVERAGE ok:','PRESERVATION ok:','SCOPE ok:'))
    assert 'FAILED' not in log and 'Traceback' not in log
    assert baseline['release']==baseline['deployed']==digest(work/'package/Elements Spellblade')==digest(work.parents[1]/'MO2/mods/Elements Spellblade')
    assert hashlib.sha256((work/'build_v03.py').read_bytes()).hexdigest()==baseline['builder']
    current_src=digest(work/'src')
    assert current_src.keys()==baseline['src'].keys()
    changes=[name for name,value in current_src.items() if value!=baseline['src'][name]]
    assert set(changes)=={'ESSBProbeMeter.psc','ESSBProbeSetup.psc'}
    for name in ('ESSBProbeMeter','ESSBProbeSetup','ESSBProbeSegment','ESSBProbePower'):
        assert (folder/'Source/Scripts'/f'{name}.psc').read_bytes()==(work/'src'/f'{name}.psc').read_bytes()
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf8'))
    assert manifest['masters']==['Skyrim.esm'] and len(manifest['records'])==29
    assert all(row['exit_code']==0 for row in manifest['compiles'])
    checks=json.loads((folder/'round18f-check.json').read_text(encoding='utf8'))
    assert checks['mode_subsets']==128
    (folder/'README.md').write_bytes((work/'build/fix18-probes.md').read_bytes())
    members=['Elements Spellblade Round18 Probes.esp','SEQ/Elements Spellblade Round18 Probes.seq','README.md','manifest.json']
    members += [f'{sub}/{name}.{ext}' for name in ('ESSBProbeMeter','ESSBProbeSetup','ESSBProbeSegment','ESSBProbePower') for sub,ext in [('Scripts','pex'),('Source/Scripts','psc')]]
    archive=work/'build/fix18f-probes-install.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for member in members:z.write(folder/member,member)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and sorted(z.namelist())==sorted(members)
        assert all(z.read(member)==(folder/member).read_bytes() for member in members)
    report=dict(full_build_exit_code=0,full_build_log=preservation['build_log'],release_files=56,
                release_and_deployment_unchanged=True,build_v03_unchanged=True,changed_sources=changes,
                masters=manifest['masters'],probe_records=29,offline_mode_combinations=128,
                setup_flows=29,archive=str(archive.relative_to(work)),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                archive_members=members,runtime_tested=False,
                release_pex_policy='full recompile; decoded executable/debug equality required; original PEX reused for byte-identical final release')
    (stage/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    rows=''.join('<tr><td>'+html.escape(line.split(' ok:',1)[0])+'</td><td>'+html.escape(line.split(' ok:',1)[1])+'</td></tr>' for line in log.splitlines() if ' ok:' in line)
    page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Round 18f 探針驗收</title>
<style>body{font:16px/1.7 system-ui,sans-serif;background:#f4f5f7;color:#17212e;max-width:1080px;margin:40px auto;padding:0 24px}h1{font-size:32px}article,aside{background:white;border:1px solid #d9dfe6;border-radius:12px;padding:24px;margin:18px 0}b{color:#126047}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;border-bottom:1px solid #ddd;padding:10px;vertical-align:top}code{overflow-wrap:anywhere}a{color:#075dad}</style>
<h1>Round 18f：第三題與準備能力強化</h1><p><b>完整建置 exit 0 · 56 個正式檔 SHA-256 不變 · 探針唯一 master：Skyrim.esm</b></p>
<article><h2>可安裝產物</h2><p><a href="../build/fix18f-probes-install.zip">下載探針安裝 ZIP</a> · <a href="../build/fix18-probes.md">完整操作卡</a> · <a href="../build/round18f/acceptance.json">驗收 JSON</a></p><p>關閉正式模組，以 SKSE 1.5.97 與全新可丟棄測試檔執行；四個能力會自動加入。第一／第二題各控制刀、校準、正式刀；第三題施放兩次，每次各跑完整兩刀程序，最後清理。</p></article>
<article><h2>本輪改動</h2><ul><li>第一題 B=1、歸一化 7 正式辨識為最低 priority／最後處理的 single winner，命名 exclusive。</li><li>第三題：兩個 separate perks 各一筆 entry 51；變體 1 A200/B199，變體 2 A199/B200。日誌列 winner、相對 FormID、加入次序、相同 rank；不捏造因果。</li><li>等 3D 載入、保留 AI，restrained＋dont-move＋non-ghost。等待延後能力，AV 以目前殘差 ModAV 歸零；最大與目前 HP 同為 10000，連續六次半秒穩定，掛 meter 前再檢查。</li><li>只在物理 CONTROL 精確零傷、恰一把測試武器事件時忽略非武器／法術／投射物的額外事件，全部計數並記理由。REFERENCE／PROBE 仍嚴格拒絕。</li></ul></article>
<aside><h2>驗證邊界</h2><p>smoke8 的 k=0.95、第一題 7、第二題 20 已有遊戲日誌。新版的碰撞可命中性與跨 perk 結果尚未進遊戲；harness 的 native mocks 不能當成引擎證據。兩變體若 B→A 支持低 priority；A→B 支持高 priority；同一 winner 仍無法區分 FormID、加入順序或法術身分。12→12 只通過受測配對，仍須確認 Ordinator 具體技能。</p><p>正式 PEX 全部重新編譯、解碼內容驗證等價後沿用原 bytes，消除編譯時間戳與宣告排序差異。完整建置在 build/round18f 隔離寫入，不寫 MO2、SkyrimSE 或非探針 src。</p></aside>
<article><h2>完整建置檢查</h2><table><thead><tr><th>檢查</th><th>結果</th></tr></thead><tbody>'''+rows+'''</tbody></table></article></html>'''
    (work/'.codex/impl-fix-round18f.html').write_text(page,encoding='utf8')
    entry='''
## Round 18f — 第三題跨 perk 探針與準備強化

- smoke8 已確認第一題 B only／normalized 7（k=0.95）與第二題 normalized 20；新增 `lightning_roll_mode = exclusive` verdict，保留 additive／chain，不改正式設定。
- 新增第三題能力（四能力總計）與兩組 separate PERK，各一筆 entry 51；A/B=5/7，同 rank，A 低 FormID 先加入；變體互換 priority 200/199。各判 12 additive／5 A winner／7 B winner／unexpected，日誌列屬性並保留因果不確定性。清理涵蓋七 perk、meter、目標與新增第三題能力。
- 3D 載入後保留 AI，以 restrained/dont-move 固定、non-ghost；等初始化與 AV settle，ModAV 只補實際殘差，最大／目前 Health=10000，連續六個 0.5 秒穩定及掛 meter 前 final check。控制刀可忽略有證據的非武器／法術／投射物零傷額外事件；REFERENCE／PROBE 與 ENV/Clean 維持嚴格。
- `python -B build/fix18f_rebuild.py` 啟動完整 `python build_v03.py`，exit 0；所有 check 行 ok。全量編譯正式 20 PEX、探針 4 PEX；29 筆探針 records，master 僅 Skyrim.esm。128 perk 子集合、15 新 verdict 流程、3 合格忽略控制、17 污染拒絕、5 AV/失敗流程、29 setup 流程及既有回歸均通過。
- 正式 56 檔修改前／重建成品／MO2 部署 SHA-256 全同；原始重編 PEX 留存，解碼指令／資料／除錯內容相等後重用原 PEX bytes。build_v03.py（CRLF）未修改，非探針 src 未動，無網路或 MO2／SkyrimSE 寫入。
- 產物：`build/fix18f-probes-install.zip`、`build/fix18-probes.md`、`build/round18f/acceptance.json`、`.codex/impl-fix-round18f.html`。新版 hittability 與跨 perk 行為待遊戲實測；離線 native mocks 不作 runtime 證據。
'''
    record=work/'實作紀錄.md';raw=record.read_bytes();nl='\r\n' if b'\r\n' in raw else '\n'
    marker='## Round 18f — 第三題跨 perk 探針與準備強化'.encode('utf8')
    assert marker not in raw, 'implementation entry already appended'
    record.write_bytes(raw+entry.replace('\n',nl).encode('utf8'))
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__': main()

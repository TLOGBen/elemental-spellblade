"""Package only installable files and append the verified round18e record."""
from pathlib import Path
import hashlib
import html
import json
import runpy
import zipfile

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT/'build/fix18-probe-package'
stage = ROOT/'build/round18e'
preservation = json.loads((folder/'preservation.json').read_text(encoding='utf8'))
assert preservation['build_exit_code'] == 0 and 'round18e/' in preservation['build_log'].replace('\\', '/')
checks = (ROOT/preservation['build_log']).read_text(encoding='utf8')
assert 'PROBE-SETUP ok:' in checks and 'PROBE-CALIBRATION ok:' in checks
assert 'Traceback' not in checks and 'FAILED' not in checks
digest = runpy.run_path(str(ROOT/'build/fix18e_isolated.py'))['digest_tree']
baseline = json.loads((stage/'baseline.json').read_text(encoding='utf8'))
deployed = ROOT.parents[1]/'MO2/mods/Elements Spellblade'
assert digest(deployed) == baseline['deployed'] == baseline['release'] == digest(ROOT/'package/Elements Spellblade')
assert (ROOT/'build_v03.py').read_bytes() == (stage/'before/build_v03.py').read_bytes()
for name in ('build_v03.py','build/fix18-probes.md','build/fix18_probes.py','build/fix18b_verify.py','build/fix18c_verify.py','build/fix8_verify.py'):
    old = (stage/'before'/name).read_bytes()
    new = (ROOT/name).read_bytes()
    assert old.startswith(b'\xef\xbb\xbf') == new.startswith(b'\xef\xbb\xbf'), name
    assert (old.count(b'\r\n') == old.count(b'\n')) == (new.count(b'\r\n') == new.count(b'\n')), name
for name in ('ESSBProbeMeter','ESSBProbeSegment'):
    assert (ROOT/'src'/f'{name}.psc').read_bytes() == (stage/'before/src'/f'{name}.psc').read_bytes()
setup = json.loads((folder/'setup-check.json').read_text(encoding='utf8'))
assert setup['actual_psc_executed'] and not setup['runtime_tested']
assert len(setup['cases']) == 26
manifest = json.loads((folder/'manifest.json').read_text(encoding='utf8'))
assert len(manifest['compiles']) == 4 and all(c['exit_code'] == 0 for c in manifest['compiles'])
readme = '''# Round18e 免主控台探針

仅供 Skyrim SE 1.5.97 + SKSE、獨立測試設定檔與可丟棄存檔。
只需 Skyrim.esm；關閉正式 Elements Spellblade。
ESP、Scripts/ 四支 PEX、SEQ/ 必須一起更新。未自動部署至 MO2。

載入後收藏「探針：準備＋第一題」、「探針：第二題」、「探針：清理」，用能力鍵施放。
每題：等 READY CONTROL → 用鐵匕首普通砍一刀 → 等 CONTROL=0、CALIBRATE、READY PROBE → 再砍一刀 → 等 MEASURE/VERDICT。
第一題完成後施放第二題，最後施放清理，等清理通知後離開並丟棄測試檔。
不要連砍、重擊、徒手、潛行或改難度。難度由原量測器校準 k。
準備能力會卸下玩家裝備並保留鐵匕首；清理還原攻擊倍率、刪除強盜和量測器、移除 probe perks，保留三個操作能力。

完整流程與舊主控台備用路線見 fix18-probes.md。
本版已編譯及完整離線驗證；尚未進遊戲驗證。
'''.replace('仅', '僅')
(folder/'README.md').write_bytes(readme.replace('\n','\r\n').encode('utf8'))
install = [folder/'Elements Spellblade Round18 Probes.esp', folder/'SEQ/Elements Spellblade Round18 Probes.seq', folder/'README.md']
for name in ('ESSBProbeMeter','ESSBProbeSegment','ESSBProbeSetup','ESSBProbePower'):
    install.extend([folder/'Scripts'/f'{name}.pex',folder/'Source/Scripts'/f'{name}.psc'])
archive = ROOT/'build/fix18e-probes-install.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for path in install: z.write(path,path.relative_to(folder).as_posix())
    z.write(ROOT/'build/fix18-probes.md','fix18-probes.md')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None and len(z.namelist()) == 12
    for path in install: assert z.read(path.relative_to(folder).as_posix()) == path.read_bytes()
    assert z.read('fix18-probes.md') == (ROOT/'build/fix18-probes.md').read_bytes()
final = dict(full_build_exit_code=0, full_build_log=preservation['build_log'],
             release_files=len(baseline['release']), release_and_deployment_unchanged=True,
             build_v03_unchanged=True, measurement_psc_unchanged=True, setup_flows=len(setup['cases']),
             archive=str(archive.relative_to(ROOT)), archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
             install_hashes={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in install},
             masters=manifest['masters'], runtime_tested=False)
(stage/'acceptance.json').write_text(json.dumps(final,ensure_ascii=False,indent=2),encoding='utf8')
record = f'''

## Round 18e：三個免主控台探針能力（2026-09-21）

- 交付 `build/fix18e-probes-install.zip` 與 `build/fix18-probe-package/`；ESP 共 23 筆記錄、4 支編譯 PEX、啟動 SEQ，唯一 master 仍是 Skyrim.esm。新增 0x840 玩家別名任務、0x841～0x843 次級能力與 0x844～0x846 效果；無需載入序查詢或主控台選取。
- `ESSBProbeSetup` 在玩家別名 OnInit／OnPlayerLoadGame 自動補發「探針：準備＋第一題」、「探針：第二題」、「探針：清理」。`ESSBProbePower` 僅接受玩家自施放，再呼叫共用設定流程。任務採 Start Game Enabled／Run Once、Player forced alias；附 SEQ 支援啟用時啟動。
- 第一題卸下玩家裝備、缺少時補一把原版 IronDagger 0001397E 並裝備，保存第一次準備前的 AttackDamageMult，再 force 0。強盜使用本機 Skyrim.esm 確認的 EncBandit01Melee1HKhajiitM 000C3CA0，延續舊卡測試對象；先以 disabled/persistent 生成，停 AI、停止戰鬥與警報、Aggression=0、卸下並清空裝備、Health force/restore 10000、五項抗性／吸收／回血 AV=0，再放到玩家前方 128 遊戲單位並啟用。只給 AB perk，量測器直接 AddSpell 到受 guard 保護的 Bandit 參照。
- 第二題先失效化 session、移除舊量測器與全部 probe perks，再沿用活強盜（死／disabled／deleted／無參照則換新），重做環境準備、給 Hit＋Multiply、掛新 meter。第一題重施放則刪除前一隻再建新。Busy 防止 latent 設定流程重入；spawn 或 meter 掛載失敗有明確提示。
- 清理關 gate、移除玩家誤掛與自有強盜量測器、移除三個 perk、Disable/Delete 強盜、還原保存 AV；重複施放／讀檔不覆蓋原值。三個操作能力與鐵匕首保留，卸下裝備不自動重穿。所有 Bandit 操作與 meter 加入都排除玩家；保留原 meter 自身的玩家目標拒絕防線。
- 每次能力一行 `[ESSB-PROBE] SETUP ...`，列強盜參照、三個 perk 狀態與 AttackDamageMult，並用繁中 Debug.Notification 指示下一步。含中文的新增 Setup PSC 使用 UTF-8 BOM，避免本機 PapyrusCompiler 的預設碼頁誤讀；新離線檢查回讀 PEX 字串確認中文不亂碼。原有 PSC／Python／操作卡換行與 BOM 慣例保持。
- 原有 16 筆量測記錄逐 subrecord／flags／本地 FormID 不變，Meter 與 Segment PSC 逐位元組不變；控制刀、自動參考校準 k、容差、事件計數與 verdict 全部不改。不加入 qasmoke 傳送，選平坦空曠處即可；Papyrus 不設定難度，session 中保持倍率固定。每題仍需 READY CONTROL 的控制刀及 READY PROBE 後的正式測試刀。
- 舊版整 ESP 固定 hash 檢查改為驗證原始 snapshot hash，並逐筆比較全部 16 筆原量測記錄；其餘原有邏輯檢查保留。fix8 範圍白名單只新增兩支獲准的 ESSBProbeSetup／ESSBProbePower，沒有關閉範圍檢查。build_v03.py 完全未改、CRLF 保留。
- `python -B build/fix18e_rebuild.py` 實際以子程序執行 `python build_v03.py` 完整建置，exit 0，每項檢查 ok，20 支正式腳本與 4 支探針腳本均編譯成功。完整日誌：`{preservation['build_log']}`；啟動輸出：`build/round18e/full-build-launch-2.log`。第一次 build 被舊白名單拒絕，已補精確路徑後完整重跑，失敗證據另保留於 rebuild-1。
- 新增 {len(setup['cases'])} 組實際 PSC 執行流程（原生呼叫為 mock），涵蓋 init/load 授予、目標狀態、各題 perk 集、玩家誤參照、原 AV 還原、重施放、四方向定位、死／失效／無目標、spawn／meter 失敗；另測 busy reentry 與非玩家 power 事件拒絕。ESP/QUST/VMAD/SEQ/次級能力的裝備欄位、4 支 PEX、中文與 vanilla bases 回讀通過。既有 36 校準流程、40 有效 trial、64 診斷流程、16 容差、48 開始組合等保持全綠。
- 正式包 56 檔的路徑集合與 SHA-256 同時等於本輪開始前 package 與只讀 MO2 部署版。完整建置所有生成寫入先導到 build/round18e，保留未授權 src 生成檔與報告的隔離副本；正式 PEX 完整重編、解碼與部署 PEX 等價後重用部署 bytes（排除非決定性時間戳／宣告排序，原始重編 PEX 留證）。沒有寫入 MO2／SkyrimSE、設計／規劃或 .strategic-advance，也未連網。
- 操作卡已改成收藏三能力、第一題、第二題、清理；控制／正式各一刀明確分開，舊 console 路線保留於附錄。ZIP 12 個檔案逐檔回讀一致；驗收摘要 `build/round18e/acceptance.json`，封裝 SHA-256 `{final['archive_sha256']}`。
- 本輪僅完成編譯、完整建置及離線驗證，未自動部署，尚未在遊戲中验证能力啟動與新 verdict；不將原生呼叫 mock 視為實機證據。
'''.replace('验证', '驗證')
ledger = ROOT/'實作紀錄.md'
old_ledger = (stage/'before/實作紀錄.md').read_bytes()
assert ledger.read_bytes() == old_ledger, 'Append only once, preserving original bytes'
with ledger.open('ab') as stream: stream.write(record.replace('\n','\r\n').encode('utf8'))
assert ledger.read_bytes().startswith(old_ledger)
ok_lines = [line for line in checks.splitlines() if ' ok:' in line or line.startswith('  compile ')]
page = '''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Round18e 免主控台探針</title><style>
body{max-width:960px;margin:40px auto;padding:0 24px;background:#101720;color:#e8edf4;font:17px/1.8 system-ui}
h1,h2{color:#99e5bc}a{color:#9bcaff}code,pre{background:#1d2938;border-radius:5px;padding:3px 6px}pre{padding:18px;overflow:auto;font-size:13px}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #445267;padding:10px;text-align:left}.card{padding:20px;border:1px solid #446658;border-radius:12px}
</style><h1>Round18e：用三個能力完成探針</h1>
<p class="card">完整建置 exit 0，所有檢查 ok。正式包 56 檔 SHA-256 與本輪前及 MO2 部署版一致。<br>已編譯與離線驗證；尚未部署或進遊戲實測。</p>
<p><a href="../build/fix18e-probes-install.zip">下載可安裝 ZIP</a> · <a href="../build/fix18-probes.md">完整操作卡與 console 附錄</a> · <a href="../build/round18e/acceptance.json">驗收證據</a></p>
<ol><li>載入可丟棄測試檔，自動取得並收藏三個能力。</li><li>施放「探針：準備＋第一題」。</li><li>等 READY CONTROL → 砍一刀 → 等自動校準及 READY PROBE → 再砍一刀 → 讀 VERDICT。</li><li>施放「探針：第二題」，重複控制／校準／正式測試。</li><li>施放「探針：清理」，等通知後退出並丟棄測試檔。</li></ol>
<table><tr><th>能力</th><th>作用</th></tr><tr><td>準備＋第一題</td><td>裝鐵匕首、保存／歸零攻擊倍率、生成停止 AI 的新強盜，10000 HP 與零抗性／回血；AB perk、直接掛 meter。</td></tr><tr><td>第二題</td><td>移除 AB，加入 Hit＋Multiply；活目標沿用，失效目標重建，重新掛 meter。</td></tr><tr><td>清理</td><td>移除 probe perks／meters、刪強盜、还原攻擊倍率；操作能力和匕首保留。</td></tr></table>
<p>量測腳本與 16 筆原記錄完全保留。新增 26 組設定流程，以及 QUST／VMAD／SEQ、次級能力、原版表單、PEX 中文回讀檢查。唯一 master：Skyrim.esm。</p>
<p>不自動傳送 qasmoke。請面向平坦空曠處，目標位於前方 128 遊戲單位。難度不能由 Papyrus 設定；原有量測器校準 k，測試途中保持難度不變。</p>
<p>建置透過隔離 helper 實際執行 python build_v03.py；全部腳本重編，正式 PEX 解碼等價後保留部署版 bytes，原始重編證據留在 build/round18e。build_v03.py 未修改。</p>
<details><summary>完整檢查行</summary><pre>CHECKS</pre></details></html>'''.replace('还原','還原').replace('CHECKS',html.escape('\n'.join(ok_lines)))
(ROOT/'.codex/impl-fix-round18e.html').write_text(page,encoding='utf8')
print(f'ROUND18E-ACCEPTANCE ok: {len(ok_lines)} compile/check lines; 26 setup flows; release 56/56 identical; ZIP 12 files verified; ledger append only; no deployment')

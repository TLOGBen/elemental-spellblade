"""Append the verified round18d record and render a local acceptance summary."""
from pathlib import Path
import hashlib
import html
import json
import runpy

WORK = Path(__file__).resolve().parents[1]
OUT = WORK/'build/round18d'
digest = runpy.run_path(str(WORK/'build/fix18d_isolated.py'))['digest_tree']
preservation = json.loads((WORK/'build/fix18-probe-package/preservation.json').read_text(encoding='utf8'))
assert preservation['build_exit_code'] == 0 and preservation['local_release_matches_deployed']
baseline = json.loads((OUT/'baseline.json').read_text(encoding='utf8'))
deployed = WORK.parents[1]/'MO2/mods/Elements Spellblade'
assert digest(deployed) == baseline['deployed'] == digest(WORK/'package/Elements Spellblade')
calibration = json.loads((WORK/'build/fix18-probe-package/calibration-check.json').read_text(encoding='utf8'))
assert calibration['calibration_flows'] == 36 and calibration['diagnostic_flows'] == 64
assert (WORK/'build_v03.py').read_bytes() == (OUT/'before/build_v03.py').read_bytes()
for path, crlf in [('src/ESSBProbeMeter.psc', False), ('build/fix18-probes.md', True),
                   ('build/fix18_probes.py', True), ('build_v03.py', True)]:
    data = (WORK/path).read_bytes()
    assert (data.count(b'\r\n') == data.count(b'\n')) == crlf
    assert data.startswith(b'\xef\xbb\xbf') == (OUT/'before'/path).read_bytes().startswith(b'\xef\xbb\xbf')

build_log = preservation['build_log']
checks = [line for line in (WORK/build_log).read_text(encoding='utf8').splitlines()
          if ' ok:' in line or line.startswith('  compile ')]
assert 'FAILED' not in '\n'.join(checks)
record = f'''

## Round 18d：以原生參考校準探針倍率，修正失效原因（2026-09-21）

### 實機證據與修改

- 讀取 `.codex/smoke7-probe-Papyrus.0.log` 的 `[ESSB-PROBE]`：物理控制 delta=0；Master 的標稱 10 點參考實扣 4.75，Adept 實扣 9.50；參考 `reported_magnitude=0`。這是本次修正依據，不代表新版已進遊戲完成 verdict。
- `src/ESSBProbeMeter.psc` 改為 `k = reference_delta / 10`，穩定且 `0.2 <= k <= 2.0` 才輸出 `CALIBRATE k=...` 並開 gate；用 `health_delta / k` 送入原有 Verdict。5／12／10／20 的 ±0.15 容差與段落數判斷完全保留，reported magnitude 只供診斷。
- 合理帶選 0.2～2.0（含端點）：相當於參考實扣 2～20 HP，容納此次 0.475／0.95 與五分之一至兩倍的共同縮放，同時拒絕零／負傷害、接近零而放大量測誤差的分母及極端放大。這是量測器的保守有效範圍，不是宣稱所有模組倍率都應落在其中。
- 保留物理控制必須精確零、控制／probe 各一次 OnHit、參考零次 OnHit、reference 段恰一次、控制與參考不能有 A/B/C、最後活動後等待 3 秒並隔 1 秒確認血量穩定、perk 組合／武器／環境檢查、session ownership 與 STOP/gate 行為。
- `INVALID` 與失敗 `VERDICT` 現在記錄真實原因：額外／缺少 hit 的 count、expected、逐筆 source；非零物理控制 delta；sample/after 不同的 unstable health；perk 變更、武器變更／附魔、非零環境值、段落數錯誤與不合法命中旗標。delta=0 的 FE38982D 額外事件與雙揮只報事件問題，不再稱 CONTROL 非零。

### 校準等價性及限制

本次依玩家實機環境採共同乘數模型：難度倍率與其他模組造成的額外 x0.95，都同樣作用於參考和探針，因為它們是同一玩家對同一目標施加的同類原生火焰傷害法術；因此以參考取得的 k 可消去這兩項共同倍率。參考與 A/B/C 的原生 MGEF 傷害、學派、抗性 AV、施放／投遞設定一致，離線 ESP readback 有逐欄驗證。參考刻意不帶探針 keyword，故不受本探針自己的 0x1D keyword x2；這個差異正是探針 2 要量測的效果，不能一併校準掉。

不等價的情況包括：其他模組只修改特定 FormID／keyword／entry-point 施法途徑（參考使用 DoCombatSpellApply）；固定傷害扣減、門檻、傷害上限或其他非線性縮放；同一 session 中途更改難度、perk 或動態 buff；額外附傷／吸血／回血或目標狀態改變。既有 guards 可拒絕看得見的污染，無法保證偵測所有隱藏且恰好看似合法的差異。因此不能宣稱 k 能修復任意模組干預，也沒有追查 x0.95 來源。

### 驗收結果與重現

- `python -B build/fix18d_rebuild.py` 實際啟動 `python build_v03.py` 完整建置，exit 0；沒有略過 release、FX、powerofthree、歷輪回歸、probe 編譯及 readback。20 支 release 腳本及 2 支 probe 腳本編譯成功，所有檢查行 ok。完整日誌：`{build_log}`；啟動日誌：`build/round18d/full-build-launch.log`。
- 使用既有隔離建置方法的 round18d helper，將 full build 原本會寫入未授權 `src/ESSBState.psc` 等路徑的產物導到 `build/round18d/rebuild-*/`；Python 網路呼叫被拒絕，編譯器 output/cwd 也導到 build。`build_v03.py` 本身逐位元組未改，CRLF 保留。沒有写入 MO2／SkyrimSE、設計／規劃文件或 `.strategic-advance/`。
- `fix18d_verify.py` 執行實際 PSC 函式與事件（原生邊界為 mock）：36 組完整校準流程，k=0.475／0.95／1.0 與邊界 0.2／2.0 各跑四種 verdict 且連續兩刀共 40 個有效 trial；0.1／2.1／0／-0.1 對四種 verdict 都拒絕。64 組診斷流程、16 個容差邊界通過。既有 12 個純 verdict、20 個抗性 guard、48 種開始組合及舊 session／事件失敗／Finish 回歸也通過。
- 修改前本機 release 的 20 個 PEX hash 已不同於部署版，36 個非 PEX 相同；先確認原本 20 個 PEX 的完整解碼內容等價，重編後再確認 20 個 PEX 亦等價（包含指令、屬性、locals、debug 行對照、flags 及 metadata，只排除編譯／debug 時間戳並正規化宣告順序）。保留 raw rebuild PEX 證據，組裝時重用經驗證等價的部署版 PEX，未跳過編譯。
- 最終 `package/Elements Spellblade/` 共 56 個檔案，路徑集合和每檔 SHA-256 全部等於目前 `MO2/mods/Elements Spellblade/`；部署目錄前後 SHA-256 不變。這是以部署版作為 byte-identical 基準，沒有將原本本機 PEX hash 差異隱藏為「從未不同」。詳見 `build/fix18-probe-package/preservation.json` 和 `build/round18d/baseline.json`。
- `build/fix18-probes.md` 已更新：難度不需精確指定但仍建議 Adept；session 內不能改倍率；看 CALIBRATE 行；用鐵匕首避開徒手額外事件；採校準後數值解讀 verdict。PSC 維持 UTF-8/LF，原本 CRLF 的 Python helper／操作卡維持 CRLF；實作紀錄僅附加。
- 交付：`build/fix18-probe-package/`。本輪未自動部署、未改正式玩法、未宣稱更新後已取得遊戲 verdict。需手動更新探針 ESP＋Scripts，再依操作卡重測。
'''
log_path = WORK/'實作紀錄.md'
original = log_path.read_bytes()
assert '## Round 18d：'.encode('utf8') not in original, 'Do not append duplicate record'
with log_path.open('ab') as stream:
    stream.write(record.replace('\n', '\r\n').encode('utf8'))
assert log_path.read_bytes().startswith(original)

page = '''<!doctype html><html lang="zh-Hant"><meta charset="utf-8">
<title>Round 18d 探針校準驗收</title><style>
body{max-width:1000px;margin:48px auto;padding:0 24px;background:#101722;color:#e6edf5;font:17px/1.8 system-ui}
h1,h2{color:#9ce7c9}code,pre{background:#1b2837;padding:3px 6px}pre{overflow:auto;font-size:13px;padding:18px}
a{color:#96caff}table{border-collapse:collapse;width:100%}td,th{border:1px solid #405166;padding:10px;text-align:left}
</style><h1>Round 18d：校準與診斷修復完成</h1>
<p>完整建置 exit 0；release 56 個檔案逐檔 SHA-256 與目前 MO2 部署版一致。未部署新版探針，待遊戲重測。</p>
<table><tr><th>參考實扣</th><th>k</th><th>探針實扣 → 校準後</th></tr>
<tr><td>4.75</td><td>0.475</td><td>2.375 → 5；5.70 → 12；4.75 → 10；9.50 → 20</td></tr>
<tr><td>9.50</td><td>0.95</td><td>4.75 → 5；11.40 → 12；9.50 → 10；19.00 → 20</td></tr></table>
<p>接受 0.2 ≤ k ≤ 2.0，依 <code>health_delta / k</code> 判斷，±0.15 容差與既有控制、穩定、hit-count 規則保留。
同一玩家、同一目標、同類原生火焰法術共同倍率可抵消；只修改 keyword/FormID/entry-point、非線性扣減、或中途倍率改變則不保證等價。</p>
<p>額外事件列 count／expected／sources；delta=0 不再誤稱物理非零。請用鐵匕首，等 <code>CALIBRATE k=...</code> 與 <code>READY PROBE</code>。</p>
<p>離線：36 校準流程、40 有效 trial、64 診斷流程、16 容差邊界；另保留既有 probe 與全 release 回歸。</p>
<p>原本本機 20 個 PEX hash 與部署版不同；完整重編且解碼等價驗證後，重用部署版 PEX 確保 byte-identical，原始重編產物保存在 build/round18d。</p>
<p><a href="../build/fix18-probes.md">操作卡</a> · <a href="../build/fix18-probe-package/">探針包</a> ·
<a href="../build/fix18-probe-package/preservation.json">雜湊／解碼驗證</a> ·
<a href="../build/fix18-probe-package/calibration-check.json">離線案例</a></p><h2>完整建置檢查</h2><pre>'''
page += html.escape('\n'.join(checks)) + '</pre></html>'
(WORK/'.codex/impl-fix-round18d.html').write_bytes(page.encode('utf8'))
report = dict(release_files=56, deployed_unchanged=True, final_release_byte_identical=True,
              build_v03_byte_identical=True, encodings_preserved=True, implementation_append_only=True,
              build_log=build_log, calibration_flows=36, diagnostic_flows=64)
(OUT/'acceptance.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('ROUND18D-ACCEPTANCE ok: full build exit 0; 56 deployed hashes match; encodings preserved; implementation append-only')

from pathlib import Path
exec(Path('build/fix18_edit_source.py').read_text(encoding='utf-8-sig').split("c=read('src/ESSBController.psc')")[0])
p='實作紀錄.md';write(p,read(p)+'''

### Round 18 最終驗收落款

- `python -B -u build_v03.py` 已親自執行，**exit 0**；20 scripts 全部 OK（0 errors）。READBACK/CSF/DELIVERY/LAYOUT/DOT/MCM/MCM DEFAULTS/SCHEMA、FIX10–FIX18、HITPROC 全通過，PLAN COVERAGE unmapped=0。
- `python -B build/fix18_final_preservation.py` exit 0：快照 24 檔及原 zero-difference preflight SHA-256 全不變；六個狀態層原始檔逐位元組不變；既有 BOM/CRLF 保留；正式 ESP+20 PEX 已記 hash。
- 上文證據名稱校正（append-only）：058F62 的實際 EDID 是 `ORD_Arc50_PinningShot_Perk_50_WasPowerShot`；05F56F 為 `ORD_OneNPC_NPCSwordPerks_Perk_30_WasBladesman_OrdASISExclude`，兩者是 Ordinator 對 Skyrim.esm 身分的 override。FormID 與原證據一致，僅校正文字名稱。
- 交付 `package/Elements Spellblade/`；正式包與 probe 包分離。最終呼叫 101，熱度例 15.246 等值。未部署、未啟動遊戲、未存取網路；所有需引擎實測之處仍明列為未驗證。
''')
p='.codex/impl-fix-round18.html';write(p,read(p)+'''
<h2>Round 18 完成：離線驗收全綠</h2>
<p><code>python -B -u build_v03.py</code> exit 0；20 scripts、0 errors。READBACK 4067/4067，唯一 master Skyrim.esm；CSF 13/13、DELIVERY、LAYOUT、DOT、MCM、MCM DEFAULTS、SCHEMA 7、FIX10–FIX18、HITPROC 全通過，PLAN COVERAGE unmapped=0。</p>
<p>呼叫 <strong>165 → 101（70 scripted + 31 native）</strong>。熱度 4：<strong>11.55 + 3.696 = 15.246</strong>。快照 24 檔、preflight 及六個狀態層源碼 hash 保留；BOM/CRLF 保留。未部署與實機驗證。</p>
<p>驗收措辭裁定已記入實作紀錄：innate fire/holy 仍需 lazy Tick；chain 真值表使用 first-success 語意；血位/雷以核准近似作參考；探針以獨立可選 ESP 代替越權建立存檔。沒有擴到第 2 期。</p>
<ul><li><a href="../build/fix18-build-final.log">完整 build log</a></li><li><a href="../build/fix18-check.json">數值/成本/輸入檢查</a></li><li><a href="../build/fix18-final-preservation.json">保留與交付 SHA-256</a></li><li><a href="../build/fix18-formid-diff.json">FormID 完整差異</a></li><li><a href="../build/fix18-probes.md">玩家探針卡與退路</a></li><li><a href="../build/fix18-engine-evidence.json">原版/Ordinator/Phenderix 記錄證據</a></li></ul>
''')
print('Append-only implementation record and HTML ledger finalized.')

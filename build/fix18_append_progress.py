from pathlib import Path
exec(Path('build/fix18_edit_source.py').read_text(encoding='utf-8-sig').split("c=read('src/ESSBController.psc')")[0])
p='.codex/impl-fix-round18.html';s=read(p);write(p,s+'''\n<h2>第 1–6 項已落地：進入最終驗證</h2>
<ul><li>1：74 個 EP51 段、42 個主法術變體、11 個無特效差額法術、30 秒已交戰，693→699。</li>
<li>2：玩家倍率快取、Rank/Br 鏡射、SyncStage 快取；原 GetStack lazy Tick 不動。熱度 4 = 11.55 + 3.696。目標狀態六個原始檔逐位元組一致。</li>
<li>3：Guard 無事可做時零 Controller 呼叫；保命鎖和九個原生防護視窗通過回歸。</li>
<li>4：ESSBInput 先寫 GLOB，再呼叫 Controller；11 熱鍵及 MCM 開關。15 組輸入防護通過。</li>
<li>5：形態全身光環移除、33 個武器光檔、無切換轉場；通知與音效可關。</li>
<li>6：schema 7，舊 006008/006009 為 inert stubs；既有 3941 身分僅兩個任務遷移。</li></ul>
<p>第一轮完整 build exit 0；20 scripts。呼叫 165 → 101（70 scripted + 31 native）。追加 88 組目標倍率與 88 組血位測試已通過，正納入最後一次 build。離線探針包另置 build/fix18-probe-package，未部署。</p>
''')

"""Patch only audited integration boundaries in the installed 1.3.4 sources."""
import hashlib,json,re,shutil,subprocess
from tes import ROOT,WORK,dump
from build_core import OUT,ELEMENTS

COMPILER=ROOT/'MO2/mods/动作共存-Nemesis Unlimited Behavior Engine-动作刷新/Nemesis_Engine/Papyrus Compiler/PapyrusCompiler.exe'
ORIGINAL=ROOT/'MO2/mods/Phenderix Elements/scripts/Source'

def replace_function(source,name,replacement):
    pattern=rf'(?im)^function {name}\([^\n]*\)\s*\n[\s\S]*?^endFunction\b'
    out,n=re.subn(pattern,lambda m:replacement,source)
    assert n==1,(name,n)
    return out

def main():
    psc=OUT/'Source/Scripts';pex=OUT/'Scripts';psc.mkdir(parents=True,exist_ok=True);pex.mkdir(exist_ok=True)
    sources={}
    for name in ['ESSBPlayerAlias.psc','ESSBSettingsEffect.psc']:
        (psc/name).write_text((WORK/'src'/name).read_text(encoding='utf-8'),encoding='utf-8-sig')
    menu_file=ORIGINAL/'PhenderixElementsMenuScript.psc';menu=menu_file.read_text(encoding='utf-8-sig')
    recurring_file=ORIGINAL/'PhenderixElementsRecurringScript.psc';recurring=recurring_file.read_text(encoding='utf-8-sig')
    sources[str(menu_file)]=hashlib.sha256(menu_file.read_bytes()).hexdigest()
    sources[str(recurring_file)]=hashlib.sha256(recurring_file.read_bytes()).hexdigest()
    # Generated FLM entries replace the stale fixed-ID catalogue. Native UI/form unlocks remain.
    build='''function BuildSpellLists(Int option)
    ESSBListsReady = False
    RegisterForModEvent("ESSBRefreshOK", "ESSBOnListsReady")
    SendModEvent("ESSBRefresh")
    Int attempt = 0
    While !ESSBListsReady && attempt < 50
        Utility.WaitMenuMode(0.1)
        attempt += 1
    EndWhile
    UnregisterForModEvent("ESSBRefreshOK")
    If ESSBListsReady
        Debug.Notification("元素魔戰士：法術清單已更新")
    Else
        Debug.Notification("元素魔戰士：尚未收到清單回覆，請確認 FLM 與產生的設定檔已啟用")
    EndIf
endFunction

Event ESSBOnListsReady(String eventName, String strArg, Float numArg, Form sender)
    ESSBListsReady = True
EndEvent'''
    menu=menu.replace('Bool spellListReady','Bool ESSBListsReady\nBool spellListReady',1)
    menu=replace_function(menu,'BuildSpellLists',build)
    menu=replace_function(menu,'UnlockSpellMenu2',(WORK/'src/menu_paging.psc.fragment').read_text(encoding='utf-8'))
    # Refresh on opening so existing saves get newly generated rows without resetting points.
    needle='\t\tplayer = akTarget\n\t\tself.MainMenu()'
    assert needle in menu
    menu=menu.replace(needle,'\t\tplayer = akTarget\n\t\tself.BuildSpellLists(0)\n\t\tself.MainMenu()',1)
    (psc/menu_file.name).write_text(menu,encoding='utf-8-sig')
    # Primary classification is separate from effect keywords. Exactly one point per spell cast,
    # even when native KID files or mixed effects contain multiple element keywords.
    recurring=recurring.replace(';-- Variables ---------------------------------------',';-- Variables ---------------------------------------\nKeyword[] ESSBPrimaryKeywords\nKeyword ESSBProcKeyword',1)
    needle='\tspell spellCast = akSpell as spell\n'
    assert recurring.count(needle)==1
    guard='''\tspell spellCast = akSpell as spell
    If !spellCast
        Return
    EndIf
    If !ESSBProcKeyword
        ESSBProcKeyword = Game.GetFormFromFile(0x801, "Elements Spellblade.esp") as Keyword
    EndIf
    If ESSBProcKeyword && spellCast.HasKeyword(ESSBProcKeyword)
        Return
    EndIf
    If ESSBAwardPrimaryPoints(spellCast)
        Return
    EndIf
'''
    recurring=recurring.replace(needle,guard,1)
    fn='''\nBool Function ESSBAwardPrimaryPoints(Spell castSpell)
    If ESSBPrimaryKeywords == None
        ESSBPrimaryKeywords = new Keyword[11]
'''
    for i,e in enumerate(ELEMENTS):fn+=f'        ESSBPrimaryKeywords[{i}] = Game.GetFormFromFile(0x{0x820+i:X}, "Elements Spellblade.esp") as Keyword\n'
    fn+='    EndIf\n'
    for i,e in enumerate(ELEMENTS):
        fn+=f'    {"If" if i==0 else "ElseIf"} ESSBPrimaryKeywords[{i}] && castSpell.HasKeyword(ESSBPrimaryKeywords[{i}])\n        ZZ{e.title()}SpendPoints.Mod(1.0)\n'
    fn+='    Else\n        Return False\n    EndIf\n    Return True\nEndFunction\n'
    recurring+=fn
    (psc/recurring_file.name).write_text(recurring,encoding='utf-8-sig')
    dump(WORK/'build/patched-script-sources.json',sources)
    imports=WORK/'vendor/imports'
    logs=[]
    for path in sorted(psc.glob('*.psc')):
        command=[str(COMPILER),str(path),'-i='+str(imports)+';'+str(psc),'-o='+str(pex),'-f='+str(imports/'TESV_Papyrus_Flags.flg'),'-optimize']
        result=subprocess.run(command,cwd=WORK/'build',capture_output=True,text=True,encoding='utf-8',errors='replace')
        logs.append({'script':path.name,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        print(path.name,'OK' if result.returncode==0 else 'FAILED',flush=True)
        if result.returncode:print(result.stdout,result.stderr)
    dump(WORK/'build/compiler-results.json',logs)
    if any(x['exit_code'] for x in logs):raise SystemExit(1)

if __name__=='__main__':main()

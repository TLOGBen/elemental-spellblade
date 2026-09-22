from pathlib import Path

def edit(name, replacements):
 p=Path(name); raw=p.read_bytes(); newline=b'\r\n' if b'\r\n' in raw else b'\n'
 s=raw.decode('utf-8').replace('\r\n','\n')
 for old,new,count in replacements:
  assert s.count(old)==count,(name,old,s.count(old),count)
  s=s.replace(old,new)
 p.write_bytes(s.replace('\n',newline.decode()).encode('utf-8'))

edit('src/ESSBStatus.psc',[
 ('Bool Bound = False\n','Bool Bound = False\nBool Finished = False\n',1),
 ('\tCtl = Controller.GetAlias(0) as ESSBController\n\tIf !Ctl\n','\tCtl = Controller.GetAlias(0) as ESSBController\n\tIf !Ctl || Finished\n',1),
 ('\tRegisterForSingleUpdate(1.0)\n','\t; Controller/Tick may finish this effect while their stack is running.\n\tIf !Finished && !Migrating\n\t\tRegisterForSingleUpdate(1.0)\n\tEndIf\n',2),
 ('Event OnEffectFinish(Actor akTarget, Actor akCaster)\n\tUnregisterForUpdate()',
  'Event OnEffectFinish(Actor akTarget, Actor akCaster)\n\t; Native binding is already gone here; the engine removes registrations.\n\tFinished = True',1),
 ('Function PrepareSwap()\n\tMigrating = True\n\tUnregisterForUpdate()\nEndFunction',
  'Function PrepareSwap()\n\t; A pending single update becomes a no-op; never unregister a dead AME.\n\tMigrating = True\nEndFunction\n\nFunction DispelIfActive()\n\tIf !Finished\n\t\tFinished = True\n\t\tDispel()\n\tEndIf\nEndFunction',1),
 ('Bool Function IsStale(Float afSeconds)\n\tReturn GetTimeElapsed() > afSeconds',
  'Bool Function IsStale(Float afSeconds)\n\tIf Finished || Migrating\n\t\tReturn False\n\tEndIf\n\tReturn GetTimeElapsed() > afSeconds',1),
 ('Event OnUpdate()\n\tIf Migrating','Event OnUpdate()\n\tIf Finished || Migrating',1),
])
p=Path('.codex/impl-fix-round2.html'); s=p.read_text(encoding='utf-8');s=s.replace('待修改：陣列 None、結束後排程／解除排程／Dispel。','已修改：移除未使用陣列的 None 指派；Finished 旗標、回呼來源傳遞以略過 self-dispel、DispelIfActive；單次殘留 tick 以旗標退出，結束／換宿不再呼叫 native Unregister。待回歸與編譯。');p.write_text(s,encoding='utf-8')
print('Papyrus edits complete; source line endings preserved.')

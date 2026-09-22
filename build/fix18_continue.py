from pathlib import Path
exec(Path('build/fix18_edit_source.py').read_text(encoding='utf-8-sig').split("c=read('src/ESSBController.psc')")[0])
p='build/fix13_verify.py';s=read(p);s=s.replace("if f in old.functions and name != 'ESSBStatus':assert old.functions[f]==new.functions[f],(name,f)","""if f in old.functions and name != 'ESSBStatus':
                prior=old.functions[f];current=new.functions[f]
                if f=='AddSelf':
                    lines=list(current[2]);hook=['If aiKind == 4 && before != SelfOverheat','RefreshProcMagnitudes()','EndIf']
                    pos=next(i for i in range(len(lines)-2) if [x.strip() for x in lines[i:i+3]]==hook)
                    del lines[pos:pos+3];current=(*current[:2],lines)
                assert prior==current,(name,f)""");write(p,s)
p='build/fix18_records.py';s=read(p).replace('def add_records(b,add,settings):','def add_records(b,add,settings,casting_perks):').replace("b.spit(0,1,1))]+fx)","b.spit(0,1,1,b.ref('Skyrim.esm',casting_perks[b.SCHOOLS[i]]))))]+fx)")
# Keep the tuple nesting identical to the existing SPIT record.
s=s.replace("casting_perks[b.SCHOOLS[i]]))))]","casting_perks[b.SCHOOLS[i]])))]")
write(p,s)
p='build_v03.py';s=read(p).replace('hit18.add_records(sys.modules[__name__], add, settings)','hit18.add_records(sys.modules[__name__], add, settings, casting_perks)');write(p,s)
p='src/ESSBInput.psc';s=read(p).replace('Consume the existing deadline','Consume the existing one-use permission');write(p,s)

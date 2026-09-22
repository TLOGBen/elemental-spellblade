from pathlib import Path
exec(Path('build/fix18_edit_source.py').read_text(encoding='utf-8-sig').split("c=read('src/ESSBController.psc')")[0])
p='實作紀錄.md';write(p,read(p)+read('build/fix18-implementation-append.md'))

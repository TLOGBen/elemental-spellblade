"""Apply bounded edits preserving each existing file's newline convention."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def edit(path, replacements):
    p = ROOT/path
    raw = p.read_bytes()
    newline = '\r\n' if b'\r\n' in raw else '\n'
    text = raw.decode('utf8').replace('\r\n', '\n')
    for old, new in replacements:
        assert text.count(old) == 1, (path, old[:100], text.count(old))
        text = text.replace(old, new)
    p.write_bytes(text.replace('\n', newline).encode('utf8'))


edit('build/fix18_probes.py', [
    ('    groups=collections.defaultdict(list)', "    runpy.run_path(str(b.WORK/'build/fix18e_records.py'))['add_records'](b, add, folder)\n    groups=collections.defaultdict(list)"),
    ('len(rows)+len(groups),0x834', 'len(rows)+len(groups),0x847'),
    ('assert len(rr)==16', 'assert len(rr)==23'),
    ("for name in ('ESSBProbeMeter','ESSBProbeSegment'):", "for name in ('ESSBProbeMeter','ESSBProbeSegment','ESSBProbeSetup','ESSBProbePower'):"),
    ("'activation':'manual AddPerk + target console AddSpell meter; no quest or automatic AddPerk'", "'activation':'start-game-enabled player alias grants three lesser powers on init/load; setup powers own bandit reference and perks'"),
    ("    print('PROBES ok: isolated opt-in 16 records + 2 compiled scripts; sole master Skyrim.esm; no deployment / save generated')", "    runpy.run_path(str(b.WORK/'build/fix18e_verify.py'))['run'](b)\n    print('PROBES ok: isolated opt-in 23 records + 4 compiled scripts + startup SEQ; sole master Skyrim.esm; no deployment / save generated')"),
    ('# Explicit target console AddSpell only. CTDA runs', '# Meter attaches directly to the owned bandit (console appendix retained). CTDA runs'),
])
edit('build/fix18b_verify.py', [
    ("{'KYWD','MGEF','SPEL','GLOB','PERK'}", "{'KYWD','MGEF','SPEL','GLOB','PERK','QUST'}"),
    ('len(records)==16 and len({r.key for r in records})==16', 'len(records)==23 and len({r.key for r in records})==23'),
    ('records=16,runtime_tested=False', 'records=23,runtime_tested=False'),
])
edit('build/fix18c_verify.py', [
    ("    assert hashlib.sha256((folder/'Elements Spellblade Round18 Probes.esp').read_bytes()).hexdigest() == (folder/'round18c-validation/probe-esp-before.sha256').read_text()", "    # Setup adds records; preserve every original measurement record byte for byte.\n    old_path = b.WORK/'build/round18e/before/probe.esp'\n    assert hashlib.sha256(old_path.read_bytes()).hexdigest() == (folder/'round18c-validation/probe-esp-before.sha256').read_text()\n    old_records, _ = b.read_plugin(old_path)\n    new_records, _ = b.read_plugin(folder/'Elements Spellblade Round18 Probes.esp')\n    by = {r.edid: r for r in new_records}\n    assert len(old_records) == 16\n    for old in old_records:\n        new = by[old.edid]\n        assert (old.sig, old.flags, old.ss, old.key.split('|')[1]) == (new.sig, new.flags, new.ss, new.key.split('|')[1])"),
    ('probe_esp_unchanged=True', 'measurement_records_unchanged=True'),
    ('unchanged probe ESP/verdict thresholds/environment guards', 'unchanged 16 measurement records/verdict thresholds/environment guards'),
])

# Reuse the proven full-build isolation recipe in a new evidence directory.
for name in ('isolated', 'rebuild'):
    source = (ROOT/f'build/fix18d_{name}.py').read_bytes()
    output = source.replace(b'round18d', b'round18e').replace(b'Round18d', b'Round18e').replace(b'fix18d_', b'fix18e_')
    (ROOT/f'build/fix18e_{name}.py').write_bytes(output)

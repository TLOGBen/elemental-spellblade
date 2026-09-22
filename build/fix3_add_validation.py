from pathlib import Path
p=Path('build_v03.py'); s=p.read_bytes().decode('utf-8').replace('\r\n','\n')
anchor='def validate_delivery(records):'
code='''def validate_fix3(records, written, bindings):
    """Independent ESP readback: identities, actual binding bytes and long-lived FX."""
    snapshot = WORK / '.codex/pre-fix3-snapshot/v03-formids.json'
    baseline = json.loads(snapshot.read_text(encoding='utf-8'))['records']
    current = written['records']
    assert all(current.get(e) == v for e, v in baseline.items()), 'fix3 existing FormIDs changed'
    new = {e: v for e, v in current.items() if e not in baseline}
    highest = max(int(v['id'], 16) for v in baseline.values()
                  if ID_FX_BASE <= int(v['id'], 16) < ID_FX_LIMIT)
    assert all(highest < int(v['id'], 16) < ID_FX_LIMIT for v in new.values()), 'FX not appended'
    by_edid = {r.edid: r for r in records}
    by_id = {int(r.key.split('|')[1], 16): r for r in records}
    visibility = []
    settings = fx_settings(json.loads((WORK / 'settings.json').read_text(encoding='utf-8')))
    for row in bindings['elements']:
        name = row['element']
        for role, host, field in [('aura', f'ESSB_FormAbilityEffect_{name}', 'aura_shader'),
                                  ('mark', f'ESSB_MarkEffect_{name}', 'mark_shader')]:
            # Form host EDID is fixed by the existing builder.
            if role == 'aura':
                host = f'ESSB_FormEffect_{name}'
            effect = by_edid[host]
            shader_id = struct.unpack_from('<I', effect.d['DATA'], 32)[0] & 0xFFFFFF
            shader = by_id[shader_id]
            assert shader.sig == 'EFSH' and shader.edid == row[field], (host, field)
            assert struct.unpack_from('<I', effect.d['DATA'])[0] & 0x1000, host
            assert row[role + '_source'] == settings['fx_' + role][name]
            if role == 'mark':
                audit = efsh_visibility(shader.ss)
                assert audit['persistent_edge_visible'], (host, audit)
                visibility.append({'host': host, 'shader': shader.edid, **audit})
        spell = by_edid[f'ESSB_MarkSpell_{name}']
        assert struct.unpack_from('<I', spell.d['EFIT'], 8)[0] == 8  # Water runtime override remains 10.
    for host in ('ESSB_ManaBreakEffect', 'ESSB_SilenceEffect'):
        effect = by_edid[host]
        assert struct.unpack_from('<I', effect.d['DATA'])[0] & 0x1000
        shader = by_id[struct.unpack_from('<I', effect.d['DATA'], 32)[0] & 0xFFFFFF]
        audit = efsh_visibility(shader.ss)
        assert audit['persistent_edge_visible'] and audit['ambient_sound'] == '00000000'
        visibility.append({'host': host, 'shader': shader.edid, **audit})
    frozen = by_edid['ESSBFX_Status_Frozen']
    assert efsh_visibility(frozen.ss)['persistent_edge_visible']
    status_host = by_edid['ESSB_StatusHostEffect']
    assert b'FrozenShader' in status_host.d['VMAD'] and I(own(int(frozen.key.split('|')[1], 16))) in status_host.d['VMAD']
    for r in records:
        if r.edid.startswith('ESSBFX_'):
            for _, _, fid, label in fx_extract.slots(r):
                assert not fid or fid >> 24 in (0, 1), (r.edid, label, hex(fid))
                if fid >> 24 == 1:
                    assert (fid & 0xFFFFFF) in by_id, (r.edid, label, hex(fid))
    dump(WORK / 'build/fix3-readback.json', {
        'existing_unchanged': len(baseline), 'new_records': new,
        'highest_previous_fx_id': f'{highest:06X}', 'debug_id': current['ESSB_DebugLevel']['id'],
        'marks_and_status': visibility, 'frozen': efsh_visibility(frozen.ss),
    })
    print(f'FIX3 ok: existing={len(baseline)} unchanged new={len(new)} appended after 0x{highest:06X}; '
          f'11 aura + 11 persistent marks + 3 status visuals; DebugLevel=0x000811')


'''
assert anchor in s;s=s.replace(anchor,code+anchor)
s=s.replace("{'selector': f'{e[\"plugin\"]}|{e[\"edid\"].removeprefix(fx_extract.PREFIX)}', 'record': e['edid']}","{'selector': f'{e[\"plugin\"]}|' + (e['edid'] if e['plugin'] == PLUGIN else\n                                                  e['edid'].removeprefix(fx_extract.PREFIX)),\n         'record': e['edid']}")
p.write_bytes(s.replace('\n','\r\n').encode('utf-8'))

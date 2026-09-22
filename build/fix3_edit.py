from pathlib import Path
import json
p=Path('build_v03.py'); s=p.read_bytes().decode('utf-8').replace('\r\n','\n')
def replace(a,b,count=1):
 global s
 assert s.count(a)==count,(a[:100],s.count(a),count)
 s=s.replace(a,b)
replace('import json\n','import json\nimport math\n')
replace('# 第三欄同時當「印記 MGEF 的著色器」「附傷 MGEF 的 Hit Shader」「反應 MGEF 的 Hit Shader」，\n# 因為 2.12 明寫 Hit Shader 用「Darenii 霧效或 Phenderix ZZShader_X」，就是這一欄。', '# 舊形態來源保留為備用；末欄只供命中／反應，印記獨立由 settings.fx_mark 決定。')
anchor='# 同調光暈的強度遞增：'
pos=s.index(anchor)
s=s[:pos]+'''# fix round 3: independent, silent edge markers. Source colours are parsed, not EDID guesses.
FX_EDGE_TEMPLATE = 'StormCalling.esl|_SC_ShockStormFXShader'
FX_EDGE_COLORS = dict(zip(ELEMENTS, [
    f'{FX_PLUGIN}|ZZShader_Fire', 'Atromancy.esp|_ATRO_FrostBuffFXShader2',
    FX_EDGE_TEMPLATE, f'{FX_PLUGIN}|ZZShader_Earth', 'Aero.esl|_AV_EffectShader',
    'Natura.esp|DAR_RedFXS', f'{FX_PLUGIN}|ZZShader_Divine',
    'Venomancy.esp|_VENOM_PoisonCloakFXShader', f'{FX_PLUGIN}|ZZShader_WaterForm',
    f'{FX_PLUGIN}|ZZShader_DarknessForm', f'{FX_PLUGIN}|ZZShader_Astral',
]))
FX_AURA_DEFAULT = {n: f'{FX_PLUGIN}|ZZShader_{n}Form' for n in ELEMENTS}
FX_MARK_DEFAULT = {n: f'{PLUGIN}|ESSBFX_Mark_{n}' for n in ELEMENTS}
FX_STATUS_WHITE = f'{PLUGIN}|ESSBFX_Status_White'
FX_STATUS_FROZEN = f'{PLUGIN}|ESSBFX_Status_Frozen'

# Byte offsets counted from vendor/wbDefinitionsTES5.pas, EFSH DATA (400 bytes).
EFSH_FLOATS = {
    'fill_fade_in': 20, 'fill_full_time': 24, 'fill_fade_out': 28,
    'fill_persistent_alpha': 32, 'fill_pulse': 36, 'edge_falloff': 52,
    'edge_fade_in': 60, 'edge_full_time': 64, 'edge_fade_out': 68,
    'edge_persistent_alpha': 72, 'edge_pulse': 76,
    'fill_full_alpha': 84, 'edge_full_alpha': 88,
    'particle_full_time': 116, 'particle_birth_ratio': 124,
    'particle_persistent_count': 128, 'particle_lifetime': 132,
}


def efsh_visibility(ss):
    data = dict(ss)['DATA']
    if len(data) < 312:
        raise ValueError(f'Unsupported EFSH DATA length: {len(data)}')
    values = {name: struct.unpack_from('<f', data, offset)[0]
              for name, offset in EFSH_FLOATS.items()}
    if not all(math.isfinite(v) for v in values.values()):
        raise ValueError('Non-finite EFSH visibility value')
    flags = struct.unpack_from('<I', data, 384)[0] if len(data) >= 388 else None
    values.update(data_bytes=len(data), edge_color=list(data[56:59]),
                  flags=flags, flags_hex=f'0x{flags:08X}' if flags is not None else None,
                  no_membrane=bool(flags & 1) if flags is not None else None,
                  no_particles=bool(flags & 8) if flags is not None else None,
                  skin_only=bool(flags & 0x20) if flags is not None else None,
                  particle_animated=bool(flags & 0x8000) if flags is not None else None,
                  particle_grayscale_color=bool(flags & 0x10000) if flags is not None else None,
                  particle_grayscale_alpha=bool(flags & 0x20000) if flags is not None else None,
                  ambient_sound=f'{struct.unpack_from("<I", data, 308)[0]:08X}')
    # Conservative gate: particle-only / absent flags cannot prove a readable outline.
    values['persistent_edge_visible'] = (flags is not None and not (flags & 0x31)
        and values['edge_persistent_alpha'] - abs(values['edge_pulse']) >= 0.35
        and values['edge_full_alpha'] > 0 and max(values['edge_color']) >= 80)
    return values


def fx_settings(settings):
    out = {}
    for name, defaults in [('fx_aura', FX_AURA_DEFAULT), ('fx_mark', FX_MARK_DEFAULT)]:
        overrides = settings.get(name, {})
        if not isinstance(overrides, dict) or set(overrides) - set(ELEMENTS):
            raise ValueError(f'{name}: expected element -> Plugin|EDID map; elements={ELEMENTS}')
        out[name] = dict(defaults, **overrides)
        for element, selector in out[name].items():
            if (not isinstance(selector, str) or selector.count('|') != 1
                    or not all(selector.split('|')) or selector != selector.strip()):
                raise ValueError(f'{name}.{element}: expected Plugin|EDID, got {selector!r}')
    return out


def fx_edge_record(template, colour_source, edid, fid, key, *, frozen=False):
    """New record only: preserve all borrowed shaders byte-for-byte (including weapon/hit)."""
    rgb = efsh_visibility(colour_source['ss'])['edge_color']
    if max(rgb) == 0:
        raise ValueError(f'Black edge colour in {colour_source["edid"]}')
    rgb = [round(c * 255 / max(rgb)) for c in rgb]
    data = bytearray(dict(template['ss'])['DATA'])
    if len(data) != 400:
        raise ValueError('Edge template must have the full TES5 EFSH DATA')
    # No fill for marks; frost status alone has a faint ice-white membrane.
    for offset, value in {20: 0, 24: 0.05, 28: 0, 32: 0.18 if frozen else 0,
                          36: 0, 40: 0, 52: 1, 60: 0, 64: 0.05, 68: 0,
                          72: 1, 76: 0, 80: 0, 84: 0.18 if frozen else 0, 88: 1,
                          112: 0, 116: 0, 120: 0, 124: 0, 128: 0}.items():
        struct.pack_into('<f', data, offset, value)
    data[16:20] = data[56:60] = bytes(rgb + [0])
    struct.pack_into('<I', data, 244, 0)   # no addon geometry
    struct.pack_into('<I', data, 308, 0)   # no ambient / looping sound
    struct.pack_into('<I', data, 384, 0x408)  # No Particle Shader + No Weapons
    ss = [(k, Z(edid) if k == 'EDID' else bytes(data) if k == 'DATA' else v)
          for k, v in template['ss']]
    return {'sig': 'EFSH', 'edid': edid, 'key': key, 'fid': fid, 'ss': ss,
            'plugin': PLUGIN, 'source_id': edid, 'dropped': [],
            'derived_from': {'template': FX_EDGE_TEMPLATE, 'colour': colour_source['edid'],
                             'colour_source_rgb': efsh_visibility(colour_source['ss'])['edge_color'],
                             'normalization': 'RGB scaled uniformly so max channel = 255'}}


'''+s[pos:]
replace('def fx_export():','def fx_export(settings=None):')
start=s.index('    selectors = fx_selectors()\n',s.index('def fx_export'))
end=s.index('\n\ndef fx_pick',start)
s=s[:start]+'''    choices = fx_settings(settings or {})
    selectors = fx_selectors()  # Keep every legacy selection as a spare.
    pinned = {}
    for path in [WORK / '.codex/pre-fix3-snapshot/v03-formids.json', WORK / 'build/v03-formids.json']:
        if not path.is_file():
            continue
        for edid, entry in json.loads(path.read_text(encoding='utf-8'))['records'].items():
            fid = int(entry['id'], 16)
            if not ID_FX_BASE <= fid < ID_FX_LIMIT:
                continue
            if edid in pinned and pinned[edid] != fid:
                raise ValueError(f'FX identity changed: {edid}')
            pinned[edid] = fid
            source = entry.get('copied_from', '')
            if source and source.split('|')[0].casefold() != PLUGIN.casefold():
                selectors.append(source.casefold())  # retain previous custom imports too
    generated = set(FX_MARK_DEFAULT.values()) | {FX_STATUS_WHITE, FX_STATUS_FROZEN}
    for mapping in choices.values():
        for selector in mapping.values():
            if selector.split('|')[0].casefold() == PLUGIN.casefold():
                if selector not in generated:
                    raise ValueError(f'Unknown local FX selector: {selector}')
            else:
                selectors.append(selector)
    selectors = list(dict.fromkeys(selectors))
    next_id = max(pinned.values(), default=ID_FX_BASE - 1) + 1
    allocated = {}

    def allocator(sig, key, edid):
        nonlocal next_id
        edid = fx_extract.PREFIX + edid
        if edid in allocated and allocated[edid] != key:
            raise ValueError(f'Copied EDID collision: {edid}')
        allocated[edid] = key
        fid = pinned.get(edid)
        if fid is None:
            fid = next_id
            next_id += 1
        if fid >= ID_FX_LIMIT:
            raise SystemExit(f'FX segment overflow at {edid}')
        return own(fid)

    records, shut, report = fx_extract.export(
        selectors, allocator, masters=MASTERS, unmapped='null', drop_subrecords=('CTDA', 'PNAM'))
    if shut['missing_selectors'] or shut['ambiguous_selectors']:
        raise ValueError(f'Invalid FX selectors: missing={shut["missing_selectors"]}, '
                         f'ambiguous={shut["ambiguous_selectors"]}')
    data = fx_extract.load()
    keys, _, _ = fx_extract.resolve(selectors, data)
    by_key = {entry['key']: entry for entry in records}
    index = {selector: by_key[key]['fid'] for selector, key in zip(selectors, keys)}
    by_fid = {e['fid']: e for e in records}
    candidates = [{'selector': f'{e["plugin"]}|{e["edid"].removeprefix(fx_extract.PREFIX)}',
                   'edid': e['edid'], **efsh_visibility(e['ss'])}
                  for e in records if e['sig'] == 'EFSH']
    template = by_fid[index[FX_EDGE_TEMPLATE]]
    derived = [(f'Mark_{n}', FX_EDGE_COLORS[n], False) for n in ELEMENTS]
    derived += [('Status_White', FX_WHITE, False),
                ('Status_Frozen', 'Icebloom.esl|_IP_FrostIceFormFXShader02', True)]
    for suffix, colour, frozen in derived:
        edid = fx_extract.PREFIX + suffix
        selector = f'{PLUGIN}|{edid}'
        fid = allocator('EFSH', selector, suffix)
        entry = fx_edge_record(template, by_fid[index[colour]], edid, fid, selector, frozen=frozen)
        records.append(entry)
        index[selector] = fid
        by_fid[fid] = entry
    for role, mapping in choices.items():
        for name, selector in mapping.items():
            entry = by_fid[index[selector]]
            if entry['sig'] != 'EFSH':
                raise ValueError(f'{role}.{name}: {selector} is {entry["sig"]}, expected EFSH')
            if role == 'fx_mark' and not efsh_visibility(entry['ss'])['persistent_edge_visible']:
                raise ValueError(f'{role}.{name}: {selector} has no proven persistent edge; '
                                 'see build/fx-visibility.json')
    for selector in (FX_STATUS_WHITE, FX_STATUS_FROZEN):
        assert efsh_visibility(by_fid[index[selector]]['ss'])['persistent_edge_visible']
    dump(WORK / 'build/fx-visibility.json', {
        'schema': 'vendor/wbDefinitionsTES5.pas:7043-7182',
        'float_offsets': EFSH_FLOATS, 'edge_color_offset': 56, 'flags_offset': 384,
        'short_DATA_policy': '312-byte records: flags absent, no inferred flags / edge guarantee',
        'candidates': candidates,
        'derived': [{'selector': f'{PLUGIN}|{e["edid"]}', 'id': f'{e["fid"] & 0xFFFFFF:06X}',
                     **e['derived_from'], **efsh_visibility(e['ss'])}
                    for e in records if 'derived_from' in e],
        'selected': {role: {n: {'selector': selector, **efsh_visibility(by_fid[index[selector]]['ss'])}
                           for n, selector in mapping.items()} for role, mapping in choices.items()},
    })
    return records, shut, report, index
'''+s[end:]
replace("    fx_records, fx_closure, fx_report, fx = fx_export()", "    fx_choices = fx_settings(settings)\n    fx_records, fx_closure, fx_report, fx = fx_export(settings)")
# Existing usages retain the old hit choices; only mark MGEF gets the new role.
s=s.replace("fxe('mark',", "fxe('hit',")
replace("        if role == 'aura':\n            return fx_pick(fx, aura) or fx[f'{FX_PLUGIN}|ZZShader_{ELEMENTS[ix]}Form']", "        if role in ('aura', 'mark'):\n            return fx[fx_choices['fx_' + role][ELEMENTS[ix]]]")
replace("        # 印記／命中著色器：2.11 沒給來源的元素（大地）退回 Phenderix 的 ZZShader_<X>。", "        # 命中／反應保持原本來源，大地仍退回 Phenderix ZZShader_Earth。")
replace("hit_shader=fxe('hit', ix), hit_effect_art=fx_ph('ZZArt', ix)", "hit_shader=fxe('mark', ix), hit_effect_art=fx_ph('ZZArt', ix)")
replace("('VMAD', vmad('ESSBStatus', {'Controller': (1, own(ID_QUEST))})),", "('VMAD', vmad('ESSBStatus', {'Controller': (1, own(ID_QUEST)),\n                                  'FrozenShader': (1, fx[FX_STATUS_FROZEN])})),")
replace("mgef_data(MGEF_MARK_FLAGS | 0x1000, 1, casting=1, delivery=1, hit_shader=fx_white)","mgef_data(MGEF_MARK_FLAGS | 0x1000, 1, casting=1, delivery=1,\n                           hit_shader=fx[FX_STATUS_WHITE])",count=2)
replace("            'aura_source': FX_ELEMENT[ix][1] or f'{FX_PLUGIN}|ZZShader_{name}Form（備選）',", "            'aura_source': fx_choices['fx_aura'][name],")
replace("            'mark_art': fx_edid(fx_ph('ZZArt', ix)),", "            'mark_art': fx_edid(fx_ph('ZZArt', ix)),\n            'mark_shader': fx_edid(fxe('mark', ix)),\n            'mark_source': fx_choices['fx_mark'][name],\n            'mark_duration': 10 if name == 'Water' else 8,\n            'mark_visibility': efsh_visibility(next(e['ss'] for e in fx_records\n                                                    if e['fid'] == fxe('mark', ix))),")
replace("            {'what': '真實傷害／破魔印／沉默的白光',\n             'records': ['ESSB_TrueEffect', 'ESSB_ManaBreakEffect', 'ESSB_SilenceEffect'],\n             'shader': [FX_WHITE], 'condition': '-', 'attached_to': 'Hit Shader（破魔印與沉默加 FX Persist）'},", "            {'what': '真實傷害白光（保留）', 'records': ['ESSB_TrueEffect'],\n             'shader': [FX_WHITE], 'condition': '-', 'attached_to': 'Hit Shader'},\n            {'what': '破魔印／沉默持續白邊',\n             'records': ['ESSB_ManaBreakEffect', 'ESSB_SilenceEffect'],\n             'shader': [FX_STATUS_WHITE], 'condition': '-', 'attached_to': 'Hit Shader + FX Persist'},\n            {'what': '冰封', 'records': ['ESSB_StatusHostEffect', 'ESSBStatus.SyncFrozenFx'],\n             'shader': [FX_STATUS_FROZEN], 'condition': 'Freeze >= 5; alive; active host',\n             'attached_to': 'FrozenShader.Play/Stop on state transitions; existing single update'},")
replace("        'spares': [{'selector': s, 'record': fx_extract.PREFIX + s.split('|', 1)[1]} for s in FX_SPARE],", "        'spares': [],")
# Derive actual unbound shaders from MGEF fields and the scripted frozen property.
anchor='    # -------------------------------------------------------------- 組檔\n'
pos=s.index(anchor,s.index('    fx_bindings ='))
s=s[:pos]+'''    used_fx = {fx[FX_STATUS_FROZEN]}
    for sig, raw in rr:
        if sig == 'MGEF':
            for sub_sig, payload in fx_extract.subs(raw[24:]):
                if sub_sig == 'DATA':
                    used_fx.update(struct.unpack_from('<I', payload, off)[0] for off in (32, 36))
    fx_bindings['spares'] = [
        {'selector': f'{e["plugin"]}|{e["edid"].removeprefix(fx_extract.PREFIX)}', 'record': e['edid']}
        for e in fx_records if e['sig'] == 'EFSH' and e['fid'] not in used_fx]

'''+s[pos:]
replace("'from': f'{e[\"plugin\"]}|{e[\"source_id\"]}'} for e in records]", "'from': f'{e[\"plugin\"]}|{e[\"source_id\"]}',\n                     **({'derived_from': e['derived_from']} if 'derived_from' in e else {})} for e in records]")
replace("        assert written['records'] == fix2_records, 'fix round 2 record identities changed'", "        assert all(written['records'].get(e) == old for e, old in fix2_records.items()), \\\n            'fix round 2 existing record identities changed'")
# dedicated readback validator inserted later
replace("    perks = sum(1 for r in check if r.sig == 'PERK')", "    validate_fix3(check, written, fx_bindings)\n    perks = sum(1 for r in check if r.sig == 'PERK')")
s=s.replace('（規劃 2.11 第 1 欄；沒有主選來源時退回 ZZShader_<X>Form）','（settings.fx_aura，預設 Phenderix ZZShader_<X>Form）')
p.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
p=Path('settings.json'); cfg=json.loads(p.read_text(encoding='utf-8'))
elements=['Fire','Frost','Lightning','Earth','Wind','Blood','Divine','Poison','Water','Darkness','Astral']
cfg['fx_aura']={n:'Phenderix Elements.esp|ZZShader_'+n+'Form' for n in elements}
cfg['fx_mark']={n:'Elements Spellblade.esp|ESSBFX_Mark_'+n for n in elements}
p.write_bytes((json.dumps(cfg,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print('Edited build_v03.py and settings.json, line endings preserved')

"""Catalog / closure / copy of borrowed visual + sound records (design 2.11, 2.12).

The mod borrows EffectShaders, Art Objects, Impact Data and Sounds from other spell
packs.  Those records are COPIED into our own plugin so our masters stay
['Skyrim.esm'] only; meshes, textures and wav files keep living in the source mods.

Every source plugin is opened read-only.  Reference fields follow the xEdit TES5
definitions (vendor/wbDefinitionsTES5.pas); everything else is carried over
byte-identical.
"""
from __future__ import annotations
import argparse, fnmatch, struct
from pathlib import Path
from tes import ROOT, WORK, BASE, Record, read_plugin, dump, sub, subs, u32

MODS = ROOT / 'MO2/mods'
PREFIX = 'ESSBFX_'
BASE_SET = {b.casefold() for b in BASE}
SKYRIM = 'skyrim.esm'

SOURCES = [
    'Phenderix Elements/Phenderix Elements.esp', 'Phenderix Elements/Phenderix Magic World.esm',
    '新魔法-Vulcano/Vulcano.esp', '新魔法-Arclight/Arclight.esp', '新魔法-Natura/Natura.esp',
    '新魔法-Stellaris/Stellaris.esp', '新魔法-Lunaris/Lunaris.esp', '新魔法-Inquisition/Inquisition.esp',
    '新魔法-Bloodmoon/Bloodmoon.esp', '新魔法-Abyss/Abyss.esp', '新魔法-Arcane/Arcane.esp',
    '新魔法-Necrom/Necrom.esp', '新魔法-Necrotic/Necrotic.esp', 'Abyssal Wind Magic/Aero.esl',
    'Winter Wonderland Magic/Icebloom.esl', 'Frostbitten Dreams Magic CHS/IceBloomNightmare.esl',
    'Holy Templar Magic/Lightpower.esl', '新魔法-Dark Hierophant Magic/Ghostlight.esl',
    'Venomancy - Destruction/Venomancy.esp', 'Atromancy/Atromancy.esp', 'StormCalling2-chs/StormCalling.esl',
]

# --- reference fields -------------------------------------------------------
# (subrecord, kind, spec).  'id': whole 4-byte payload.  'at': {offset: label}
# inside a struct.  'mods': MODS alternate-texture array.  'ctda': condition.
# Offsets are counted field by field from wbDefinitionsTES5.pas.
FIELDS = {
    # EFSH DATA is a 400 byte struct; only two slots are FormIDs.
    'EFSH': [('DATA', 'at', {244: 'Addon Models', 308: 'Ambient Sound'})],
    'ARTO': [('MODS', 'mods', None)],
    'TXST': [],
    'IPCT': [('MODS', 'mods', None), ('DNAM', 'id', 'Texture Set'), ('ENAM', 'id', 'Secondary Texture Set'),
             ('SNAM', 'id', 'Sound 1'), ('NAM1', 'id', 'Sound 2'), ('NAM2', 'id', 'Hazard')],
    'IPDS': [('PNAM', 'at', {0: 'Material', 4: 'Impact'})],
    'SNDR': [('GNAM', 'id', 'Category'), ('SNAM', 'id', 'Alternate Sound For'),
             ('ONAM', 'id', 'Output Model'), ('CTDA', 'ctda', None)],
    'SOUN': [('SDSC', 'id', 'Sound Descriptor')],
    'SNCT': [('PNAM', 'id', 'Parent')],
    'SOPM': [],
    'EXPL': [('MODS', 'mods', None), ('EITM', 'id', 'Object Effect'), ('MNAM', 'id', 'Image Space Modifier'),
             ('DATA', 'at', {0: 'Light', 4: 'Sound 1', 8: 'Sound 2', 12: 'Impact Data Set',
                             16: 'Placed Object', 20: 'Spawn Projectile'})],
    'LIGH': [('MODS', 'mods', None), ('SNAM', 'id', 'Sound'), ('LNAM', 'id', 'Lens')],
    'HAZD': [('MODS', 'mods', None), ('MNAM', 'id', 'Image Space Modifier'),
             ('DATA', 'at', {24: 'Spell', 28: 'Light', 32: 'Impact Data Set', 36: 'Sound'})],
    'SPGD': [], 'DEBR': [],
    'MATT': [('PNAM', 'id', 'Material Parent'), ('HNAM', 'id', 'Havok Impact Data Set')],
}
TYPES = set(FIELDS)
# Subrecords we do not rewrite; if one shows up on a copied record, say so.
OPAQUE = {'VMAD', 'DEST', 'DSTD', 'DMDL', 'DMDS'}

# CTDA condition functions whose param 1 / param 2 is a FormID, taken from the
# function table in wbDefinitionsTES5.pas (pt* types that name a record).
_P1 = '1,27,32,42,43,44,45,47,53,56,58,59,60,66,67,68,69,71,72,73,74,79,84,99,117,122,129,130,132,136,149,152,161,162,163,172,180,182,193,195,197,199,214,223,228,230,246,248,250,258,259,261,262,264,278,280,310,359,362,366,370,372,373,375,376,378,398,403,408,409,410,414,426,444,445,448,449,450,459,463,465,477,479,493,501,513,515,516,517,518,522,523,524,525,533,534,535,543,550,552,560,561,562,563,565,577,579,584,591,592,595,603,606,617,624,625,629,630,639,650,651,652,660,678,682,691,693,697,699,705,707,713,719,720,722'
_P2 = '60,180,181,230,258,280,410,577,591,592,596,600,601,603,604,605,606,608,610,650'
CTDA_P1 = frozenset(int(x) for x in _P1.split(','))
CTDA_P2 = frozenset(int(x) for x in _P2.split(','))

RECORDS: dict[str, Record] = {}   # key -> tes.Record, filled by catalog()


def source_path(spec):
    p = Path(spec)
    return p if p.is_absolute() else MODS / spec


def alt_textures(payload):
    """Offsets of the TXST FormID inside a MODS alternate-texture array."""
    if len(payload) < 4: return
    p = 4
    for _ in range(u32(payload)):
        if p + 4 > len(payload): return
        p += 4 + u32(payload, p)
        if p + 8 > len(payload): return
        yield p, 'Alternate Texture'
        p += 8


def condition(payload):
    """FormID offsets inside one CTDA (32 byte head; trailing strings ignored)."""
    if len(payload) < 32: return
    operator, function, run_on = payload[0], struct.unpack_from('<H', payload, 8)[0], u32(payload, 20)
    if operator & 0x04: yield 4, 'Condition Global'
    if function in CTDA_P1: yield 12, 'Condition Parameter 1'
    if function in CTDA_P2: yield 16, 'Condition Parameter 2'
    if run_on == 2: yield 24, 'Condition Reference'


def slots(record):
    """Yield (subrecord index, byte offset, FormID, field name) for one record."""
    plan = FIELDS.get(record.sig, ())
    for i, (sig, payload) in enumerate(record.ss):
        for want, kind, spec in plan:
            if sig != want: continue
            if kind == 'id':
                if len(payload) == 4: yield i, 0, u32(payload), spec
            elif kind == 'at':
                for off, label in spec.items():
                    if off + 4 <= len(payload): yield i, off, u32(payload, off), label
            else:
                for off, label in (alt_textures(payload) if kind == 'mods' else condition(payload)):
                    yield i, off, u32(payload, off), label


def references(record):
    """[(field, target identity)] for every non-null FormID slot."""
    out = []
    for _, _, fid, field in slots(record):
        if not fid: continue
        try:
            target = record.ref(fid)
        except ValueError:
            out.append((field, f'?bad-index|{fid:08X}')); continue
        out.append((field, target))
    return out


# --- 1. catalog -------------------------------------------------------------
def catalog(plugin_paths=None, write=True):
    """Parse the FX record types out of every source plugin."""
    RECORDS.clear()
    data = {'types': sorted(TYPES), 'plugins': {}, 'records': {}, 'index': {}, 'edids': {}}
    for spec in (plugin_paths or SOURCES):
        path = source_path(spec)
        name = path.name
        if not path.is_file():
            data['plugins'][name] = {'source': str(spec), 'missing': True}
            continue
        rr, meta = read_plugin(path, TYPES)
        data['plugins'][name] = {'source': str(spec), 'path': meta['path'], 'sha256': meta['sha256'],
                                 'masters': meta['masters'], 'records': len(rr)}
        for r in rr:
            entry = {'sig': r.sig, 'edid': r.edid, 'plugin': name, 'id': r.key.split('|')[1],
                     'refs': [{'field': f, 'to': t} for f, t in references(r)]}
            if r.key.split('|')[0] != name.casefold(): entry['override'] = True
            opaque = sorted({k for k, _ in r.ss} & OPAQUE)
            if opaque: entry['opaque'] = opaque
            data['records'][r.key] = entry
            RECORDS[r.key] = r
            if r.edid:
                data['index'][f'{name.casefold()}|{r.edid}'] = r.key
                data['edids'].setdefault(r.edid, []).append(r.key)
    if write:
        (WORK / 'build').mkdir(exist_ok=True)
        dump(WORK / 'build/fx-catalog.json', data)
    return data


_CATALOG = None
def load(data=None):
    global _CATALOG
    if data is not None: return data
    if _CATALOG is None: _CATALOG = catalog()
    return _CATALOG


# --- 2. closure -------------------------------------------------------------
def resolve(selectors, data):
    """"Plugin.esp|EDID", bare "EDID" or a raw identity key -> catalog keys."""
    keys, missing, ambiguous = [], [], []
    for s in selectors:
        if s in data['records']: keys.append(s); continue
        hit = None
        if '|' in s:
            plugin, edid = s.split('|', 1)
            hit = data['index'].get(f'{plugin.casefold()}|{edid}')
        else:
            found = data['edids'].get(s, [])
            if len(found) > 1: ambiguous.append({'selector': s, 'keys': found})
            hit = found[0] if found else None
        if hit is None: missing.append(s)
        else: keys.append(hit)
    return keys, missing, ambiguous


def closure(selectors, data=None):
    """Transitive set of records to copy, plus what cannot be copied."""
    data = load(data)
    start, missing, ambiguous = resolve(selectors, data)
    order, seen, unresolvable, external = [], set(), [], {}
    queue = list(start)
    while queue:
        key = queue.pop(0)
        if key in seen: continue
        seen.add(key); order.append(key)
        for ref in data['records'][key]['refs']:
            target = ref['to']; plugin = target.split('|')[0]
            if plugin in BASE_SET:
                external.setdefault(target, {'field': ref['field'], 'from': []})['from'].append(key)
            elif target in data['records']:
                queue.append(target)
            else:
                unresolvable.append({'record': key, 'edid': data['records'][key]['edid'],
                                     'field': ref['field'], 'to': target})
    counts = {}
    for key in order: counts[data['records'][key]['sig']] = counts.get(data['records'][key]['sig'], 0) + 1
    extra = sorted({t.split('|')[0] for t in external} - {SKYRIM})
    return {'selectors': len(selectors), 'missing_selectors': missing, 'ambiguous_selectors': ambiguous,
            'records': order, 'counts': counts, 'unresolvable': unresolvable,
            'external': {k: v for k, v in sorted(external.items())}, 'extra_masters': extra}


# --- 3. export --------------------------------------------------------------
def export(selectors, id_allocator, data=None, masters=('Skyrim.esm',), unmapped='keep',
           drop_subrecords=()):
    """[(sig, edid, subrecords)] with every reference FormID remapped.

    id_allocator(sig, key, edid) returns the full 32 bit FormID the copy gets in
    our plugin.  Non-reference bytes are never touched.  A reference that can be
    neither copied nor pointed at one of `masters` is reported; `unmapped='null'`
    additionally writes 0 into the slot instead of leaving the foreign FormID.

    `drop_subrecords` names subrecord signatures that are whole, optional array
    members (SNDR `CTDA`, IPDS `PNAM`): when such a subrecord holds a reference
    that cannot be mapped, the subrecord is removed instead of nulled, so the
    plugin needs no extra master and no record is left pointing at FormID 0.
    Both arrays are unordered and uncounted in wbDefinitionsTES5.pas, so removing
    one member is lossless for the rest of the record.
    """
    data = load(data)
    if not RECORDS: catalog()
    shut = closure(selectors, data)
    index = {m.casefold(): i for i, m in enumerate(masters)}
    droppable = {s for s in drop_subrecords}
    new = {key: id_allocator(data['records'][key]['sig'], key, data['records'][key]['edid'])
           for key in shut['records']}
    out, report = [], []
    for key in shut['records']:
        record = RECORDS[key]
        ss = [(k, bytearray(v)) for k, v in record.ss]
        dropped = set()
        for i, off, fid, field in slots(record):
            if not fid: continue
            try:
                target = record.ref(fid)
            except ValueError:
                report.append({'record': key, 'field': field, 'reason': 'bad master index'}); continue
            if target is None: continue          # ref() only returns None for FormID 0
            plugin, local = target.split('|')
            if target in new: value = new[target]
            elif plugin in index: value = (index[plugin] << 24) | int(local, 16)
            else:
                action = 'drop-subrecord' if ss[i][0] in droppable else unmapped
                report.append({'record': key, 'edid': record.edid, 'field': field, 'to': target,
                               'reason': 'master not in plugin' if plugin in BASE_SET else 'not copied',
                               'action': action, 'subrecord': ss[i][0]})
                if action == 'drop-subrecord':
                    dropped.add(i); continue
                if action != 'null': continue
                value = 0
            struct.pack_into('<I', ss[i][1], off, value)
        edid = PREFIX + record.edid
        ss = [(k, bytes(edid, 'utf-8') + b'\0' if k == 'EDID' else bytes(v))
              for i, (k, v) in enumerate(ss) if i not in dropped]
        out.append({'sig': record.sig, 'edid': edid, 'key': key, 'fid': new[key], 'ss': ss,
                    'plugin': data['records'][key]['plugin'],
                    'source_id': data['records'][key]['id'],
                    'dropped': sorted(record.ss[i][0] for i in dropped)})
    return out, shut, report


def raw(entry):
    """Subrecord bytes of an exported record, XXXX-extended where needed."""
    return b''.join(sub(k, v) for k, v in entry['ss'])


# --- 4. self test -----------------------------------------------------------
PHENDERIX = 'Phenderix Elements.esp'
PICKS = ['ZZShader_FireForm', 'DAR_MoltenFXShader', 'ZZImpactSet_Fire', 'ZZImpactSet_FireUpgraded',
         'ZZExplosion_FireHand1', 'ZZArt_Fire', 'ZZSoundDescriptor_Charge_Fire', 'INQ_EnchHolySwordFXS',
         '_VENOM_PoisonCloakFXShader', 'ZZWaterloggedShader1', 'DAR_AstralSpellStarMistShader',
         'ABY_ShadowFXS', '_IP_FrostIceFormFXShader02', 'DAR_ArcFXShader', 'NAT_MagicArmorStoneFleshFXS',
         '_AV_EffectShader', 'BLO_BleedingShader']
PATTERNS = ['ZZImpactSet_*', 'ZZExplosion_*Hand1', 'ZZArt_*', 'ZZSoundDescriptor_Charge_*',
            'ZZSoundDescriptor_DrawSheathe_*', 'ZZSoundDescriptor_FormActivate_*',
            'ZZSoundDescriptor_FormActive_*', 'ZZSoundDescriptor_Release_*', 'ZZSoundDescriptor_OnHit_*']


def selftest():
    data = catalog()
    present = sum(1 for p in data['plugins'].values() if not p.get('missing'))
    missing_files = [n for n, p in data['plugins'].items() if p.get('missing')]
    print(f'Catalog: {len(data["records"])} records from {present}/{len(data["plugins"])} plugins'
          + (f'; missing files: {missing_files}' if missing_files else ''))
    counts = {}
    for r in data['records'].values(): counts[r['sig']] = counts.get(r['sig'], 0) + 1
    print('Catalog by type:', ' '.join(f'{k}={v}' for k, v in sorted(counts.items())))

    selectors, matched = list(PICKS), {}
    for pattern in PATTERNS:
        hit = sorted(r['edid'] for r in data['records'].values()
                     if r['plugin'] == PHENDERIX and fnmatch.fnmatch(r['edid'], pattern))
        matched[pattern] = len(hit)
        selectors += [f'{PHENDERIX}|{e}' for e in hit]
    empty = [p for p, n in matched.items() if not n]
    print('Pattern hits:', ' '.join(f'{p}={n}' for p, n in matched.items()))
    if empty: print('Patterns with no match (EDID family absent):', empty)

    shut = closure(selectors, data)
    print('Closure by type:', ' '.join(f'{k}={v}' for k, v in sorted(shut['counts'].items())),
          f'| total={len(shut["records"])}')
    print('Unresolvable references:', len(shut['unresolvable']))
    for u in shut['unresolvable'][:10]: print('   ', u['edid'], u['field'], '->', u['to'])
    print('Missing selectors:', len(shut['missing_selectors']), shut['missing_selectors'][:10])
    print('External (kept) references:', len(shut['external']), '| extra masters needed:',
          shut['extra_masters'] or 'none')

    counter = [0]
    def allocator(sig, key, edid):
        counter[0] += 1
        return (1 << 24) | (0x000A00 + counter[0])
    records, _, report = export(selectors, allocator, data)
    bad = []
    for entry in records:
        try:
            back = list(subs(raw(entry)))
        except ValueError as exc:
            bad.append((entry['edid'], str(exc))); continue
        if back != [(k, v) for k, v in entry['ss']]: bad.append((entry['edid'], 'mismatch'))
    print(f'Round trip: {len(records)} records re-parsed, {len(bad)} failures',
          bad[:5] if bad else '')
    groups = {}
    for r in report: groups.setdefault((r['field'], r.get('to'), r['reason']), []).append(r.get('edid'))
    print(f'Export notes (references neither copied nor a master of ours): {len(report)}')
    for (field, to, reason), edids in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f'    {field} -> {to} [{reason}] x{len(edids)}: {", ".join(edids[:3])}'
              + (' ...' if len(edids) > 3 else ''))

    out = WORK / 'build/fx-closure-selftest.json'
    dump(out, {'selectors': selectors, 'pattern_hits': matched, 'catalog_counts': counts,
               'closure_counts': shut['counts'], 'records': [
                   {'key': k, 'sig': data['records'][k]['sig'], 'edid': data['records'][k]['edid'],
                    'plugin': data['records'][k]['plugin'], 'new_edid': PREFIX + data['records'][k]['edid']}
                   for k in shut['records']],
               'unresolvable': shut['unresolvable'], 'missing_selectors': shut['missing_selectors'],
               'ambiguous_selectors': shut['ambiguous_selectors'], 'extra_masters': shut['extra_masters'],
               'external': shut['external'], 'export_notes': report,
               'round_trip': {'records': len(records), 'failures': bad}})
    print('Wrote', WORK / 'build/fx-catalog.json')
    print('Wrote', out)
    return not bad


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selftest', action='store_true')
    parser.add_argument('--catalog', action='store_true')
    args = parser.parse_args()
    if args.selftest: raise SystemExit(0 if selftest() else 1)
    elif args.catalog: catalog(); print('Wrote', WORK / 'build/fx-catalog.json')
    else: parser.print_help()

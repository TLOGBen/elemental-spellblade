"""Round 27f (0.27.5): the files our visual records name must exist.

The in-game report: 白熱 showed no body fire. The shader was a copy of Vulcano's DAR_MoltenFXShader, whose textures live
only in Vulcano's archive, and nothing checked that what our visual records name is there. This module reads the
archives' file lists (Bethesda BSA v104 / v105: the header, the folder records and the name tables only) and loose files,
and answers whether a texture / mesh path resolves.

  archive_names(path)   every file path in a BSA (lower case, backslashes)
  vanilla(data)         the base game's archives (Skyrim - *.bsa: the DLC and the Update archive included in SE)
  installed(root)       the user's MO2 profile, read-only (enabled mods' archives and loose files); None without MO2
  record_paths(r)       (field, path) of the files an EFSH / ARTO / HAZD / EXPL record names

build/fix27_verify.py: the records we author ourselves and every visual on the player's own body resolve in the vanilla
archives; the ESSBFX_* copies (the asset mods v0.4 2.11 names) that a live effect of ours uses resolve in the vanilla
archives or the installed mods.
"""
from __future__ import annotations

import struct
from pathlib import Path

NUL = b'\x00'
SEP = '\\'


def archive_names(path: Path) -> set[str]:
    with path.open('rb') as f:
        head = f.read(36)
        if len(head) < 36 or head[:4] != b'BSA' + NUL:
            return set()
        version, offset, flags, folders, files, fold_len, file_len = struct.unpack_from('<IIIIIII', head, 4)
        if version not in (104, 105):
            return set()
        record = 24 if version == 105 else 16
        size = folders * record + (fold_len + folders if flags & 1 else 0) + files * 16 + (file_len if flags & 2 else 0)
        f.seek(offset)
        data = f.read(size)
    counts = [struct.unpack_from('<I', data, i * record + 8)[0] for i in range(folders)]
    pos = folders * record
    folder_names = []
    for count in counts:
        if flags & 1:
            n = data[pos]
            folder_names.append(data[pos + 1:pos + n].split(NUL, 1)[0].decode('cp1252', 'replace'))
            pos += 1 + n
        else:
            folder_names.append('')
        pos += 16 * count
    names = [x.decode('cp1252', 'replace') for x in data[pos:pos + file_len].split(NUL)[:files]] if flags & 2 else []
    out = set()
    i = 0
    for folder, count in zip(folder_names, counts):
        for _ in range(count):
            if i < len(names):
                out.add((folder + SEP + names[i]).lower().replace('/', SEP))
            i += 1
    return out


class Files:
    def __init__(self, archives: list[Path], loose_roots: list[Path]):
        self.names: set[str] = set()
        for a in archives:
            if a.is_file():
                self.names |= archive_names(a)
        self.roots = [r for r in loose_roots if r.is_dir()]

    def has(self, path: str) -> bool:
        key = path.lower().replace('/', SEP).lstrip(SEP)
        if key in self.names:
            return True
        return any((root / key).is_file() for root in self.roots)


def vanilla(data: Path) -> Files:
    return Files(sorted(data.glob('Skyrim - *.bsa')), [])


def installed(root: Path) -> Files | None:
    profile = root / 'MO2/profiles/normal/modlist.txt'
    mods = root / 'MO2/mods'
    if not profile.is_file() or not mods.is_dir():
        return None
    enabled = [line[1:].strip() for line in profile.read_text(encoding='utf-8', errors='replace').splitlines() if line.startswith('+')]
    archives = sorted((root / 'SkyrimSE/Data').glob('*.bsa'))
    loose = []
    for name in enabled:
        folder = mods / name
        if folder.is_dir():
            archives += sorted(folder.glob('*.bsa'))
            loose.append(folder)
    return Files(archives, loose)


def record_paths(r) -> list[tuple[str, str]]:
    out = []

    def text(v):
        return v.split(NUL, 1)[0].decode('utf-8', 'replace').strip()
    if r.sig == 'EFSH':
        for field in ('ICON', 'ICO2', 'NAM7', 'NAM8', 'NAM9'):
            if field in r.d and text(r.d[field]):
                out.append((field, 'textures' + SEP + text(r.d[field])))
    elif r.sig in ('ARTO', 'HAZD', 'EXPL') and 'MODL' in r.d and text(r.d['MODL']):
        out.append(('MODL', 'meshes' + SEP + text(r.d['MODL'])))
    return out

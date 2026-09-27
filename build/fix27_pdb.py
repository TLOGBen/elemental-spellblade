"""Round 27d (0.27.3): the DLL's CodeView record and the PDB's info stream -- native/build.py keeps the PDB only when they
match; build/fix27_verify.py checks the packaged DLL against the kept PDB and that no PDB is shipped."""
import struct as _struct


def dll_codeview(path):
    """(GUID bytes, age, pdb path) from the DLL's debug directory."""
    data = path.read_bytes()
    pe = _struct.unpack_from('<I', data, 0x3C)[0]
    assert data[pe:pe + 4] == b'PE\0\0', 'not a PE file'
    sections = _struct.unpack_from('<H', data, pe + 6)[0]
    opt_size = _struct.unpack_from('<H', data, pe + 20)[0]
    opt = pe + 24
    assert _struct.unpack_from('<H', data, opt)[0] == 0x20B, 'not PE32+'
    debug_rva, debug_size = _struct.unpack_from('<II', data, opt + 112 + 6 * 8)
    table = opt + opt_size

    def offset(rva):
        for i in range(sections):
            s = table + 40 * i
            vsize, vaddr, rawsize, rawptr = _struct.unpack_from('<IIII', data, s + 8)
            if vaddr <= rva < vaddr + max(vsize, rawsize):
                return rawptr + rva - vaddr
        raise ValueError(f'RVA {rva:#x} in no section')
    base = offset(debug_rva)
    for i in range(debug_size // 28):
        kind, size, _rva, raw = _struct.unpack_from('<IIII', data, base + 28 * i + 12)
        if kind == 2 and data[raw:raw + 4] == b'RSDS':
            guid = data[raw + 4:raw + 20]
            age = _struct.unpack_from('<I', data, raw + 20)[0]
            name = data[raw + 24:raw + size].split(b'\0', 1)[0].decode('utf-8', 'replace')
            return guid, age, name
    raise ValueError('no CodeView RSDS record in the DLL (built without /DEBUG?)')


def pdb_info(path):
    """(GUID bytes, age) from the PDB's info stream (MSF 7.00, stream 1)."""
    data = path.read_bytes()
    assert data.startswith(b'Microsoft C/C++ MSF 7.00\r\n\x1aDS\0\0\0'), 'not an MSF 7.00 PDB'
    block, _free, _count, dir_bytes, _unused, map_block = _struct.unpack_from('<IIIIII', data, 32)
    dir_blocks = -(-dir_bytes // block)
    blocks = _struct.unpack_from(f'<{dir_blocks}I', data, map_block * block)
    directory = b''.join(data[b * block:(b + 1) * block] for b in blocks)[:dir_bytes]
    streams = _struct.unpack_from('<I', directory, 0)[0]
    sizes = _struct.unpack_from(f'<{streams}I', directory, 4)
    at = 4 + 4 * streams
    lists = []
    for size in sizes:
        count = 0 if size == 0xFFFFFFFF else -(-size // block)
        lists.append(_struct.unpack_from(f'<{count}I', directory, at))
        at += 4 * count
    info = b''.join(data[b * block:(b + 1) * block] for b in lists[1])[:sizes[1]]
    _version, _signature, age = _struct.unpack_from('<III', info, 0)
    return info[12:28], age

"""One-time bootstrap: fetch the pinned CMake into native/deps (the only network use of the native build).

Downloads the official GitHub release archive named in toolchain.lock.json, checks it against the
pinned SHA-256 before extracting, extracts it, and deletes the archive. Nothing else is kept.
"""
from pathlib import Path
import hashlib, json, urllib.request, zipfile

NATIVE = Path(__file__).resolve().parent
LOCK = json.loads((NATIVE / 'toolchain.lock.json').read_text(encoding='utf8'))
DEPS = NATIVE / 'deps'


def main():
    target = DEPS / f"cmake-{LOCK['cmake']}-windows-x86_64"
    if (target / 'bin/cmake.exe').is_file():
        print(f'CMake {LOCK["cmake"]} already present: {target}')
        return
    DEPS.mkdir(exist_ok=True)
    archive = DEPS / LOCK['cmake_archive'].rsplit('/', 1)[1]
    digest = hashlib.sha256()
    with urllib.request.urlopen(LOCK['cmake_archive'], timeout=120) as response, archive.open('wb') as out:
        while chunk := response.read(1 << 20):
            digest.update(chunk)
            out.write(chunk)
    if digest.hexdigest() != LOCK['cmake_archive_sha256']:
        archive.unlink()
        raise RuntimeError(f'CMake archive SHA-256 mismatch: {digest.hexdigest()}')
    with zipfile.ZipFile(archive) as z:
        z.extractall(DEPS)
    archive.unlink()
    print(f'CMake {LOCK["cmake"]} verified ({LOCK["cmake_archive_sha256"]}) and extracted to {target}')


if __name__ == '__main__':
    main()

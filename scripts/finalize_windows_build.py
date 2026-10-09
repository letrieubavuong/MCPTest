"""Finalize the locally verified x64 console build using the original wheel bootloader."""
from pathlib import Path
import struct
import zipfile

root = Path(__file__).resolve().parents[1]
wheel = root / '.runtime/wheels/pyinstaller-6.21.0-py3-none-win_amd64.whl'
folder = root / 'dist/LaTeXQuestionStudio'
with zipfile.ZipFile(wheel) as archive:
    name = next(n for n in archive.namelist() if n.endswith('Windows-64bit-intel/run.exe'))
    bootloader = archive.read(name)
offset = struct.unpack_from('<I', bootloader, 60)[0]
if bootloader[:2] != b'MZ' or struct.unpack_from('<H', bootloader, offset + 4)[0] != 0x8664:
    raise RuntimeError('Original wheel bootloader is not Windows x64')
package = root / '.runtime/pyinstaller/LaTeXQuestionStudio/LaTeXQuestionStudio.pkg'
(folder / 'LaTeXQuestionStudio.exe').write_bytes(bootloader + package.read_bytes())
# Use the Windows system UCRT; the collected copy failed local initialization.
for name in ('ucrtbase.dll', 'ucrtbase.dll.disabled'):
    (folder / '_internal' / name).unlink(missing_ok=True)
for name in ('debug.com', 'diagnostic.com', 'LaTeXQuestionStudio.com'):
    (folder / name).unlink(missing_ok=True)
print('Finalized Windows x64 console launcher; smoke test required before release.')

"""Legacy launcher repair; normal builds use PyInstaller output unchanged."""
from pathlib import Path
import struct
import argparse
import PyInstaller

root = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--dist-dir',type=Path,default=root/'dist/LaTeXQuestionStudio');args=parser.parse_args()
folder=args.dist_dir.resolve()
bootloader_path = Path(PyInstaller.__file__).resolve().parent / 'bootloader/Windows-64bit-intel/runw.exe'
bootloader = bootloader_path.read_bytes()
offset = struct.unpack_from('<I', bootloader, 60)[0]
if bootloader[:2] != b'MZ' or struct.unpack_from('<H', bootloader, offset + 4)[0] != 0x8664:
    raise RuntimeError('Installed PyInstaller bootloader is not Windows x64')
if struct.unpack_from('<H', bootloader, offset + 24 + 68)[0] != 2:
    raise RuntimeError('Expected a Windows GUI bootloader')
package = root / '.runtime/pyinstaller/LaTeXQuestionStudio/LaTeXQuestionStudio.pkg'
launcher = folder / 'LaTeXQuestionStudio.exe'
replacement = folder / 'launcher.tmp'
replacement.write_bytes(bootloader + package.read_bytes())
replacement.replace(launcher)
# Use the Windows system UCRT; the collected copy failed local initialization.
for name in ('ucrtbase.dll', 'ucrtbase.dll.disabled'):
    (folder / '_internal' / name).unlink(missing_ok=True)
for name in ('debug.com', 'diagnostic.com', 'LaTeXQuestionStudio.com'):
    (folder / name).unlink(missing_ok=True)
print(f'Repaired Windows x64 GUI launcher with PyInstaller {PyInstaller.__version__}; smoke test required before release.')

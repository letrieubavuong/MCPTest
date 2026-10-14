"""Launch the actual GUI EXE normally and observe startup and fresh TeX rendering."""
from pathlib import Path
import ctypes
from ctypes import wintypes
import hashlib
import json
import shutil
import struct
import subprocess
import time
import uuid

import pymupdf


root=Path(__file__).resolve().parents[1]
output=root/'artifacts/windowed-build';output.mkdir(parents=True,exist_ok=True)
fixture=Path(json.loads((root/'artifacts/formula-input-fix/verification.json').read_text(encoding='utf-8'))['synthetic_data']).resolve()
if not fixture.is_relative_to((root/'.runtime').resolve()):raise ValueError('Expected synthetic lesson data')
target=root/'.runtime'/('windowed-render-'+uuid.uuid4().hex[:8])
shutil.copytree(fixture,target,ignore=shutil.ignore_patterns('cache'))
import tomllib
version = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
exe = root / f'dist/{version}/LaTeXQuestionStudio/LaTeXQuestionStudio.exe'
if not exe.is_file():
    candidates = sorted((root / 'dist').glob('*/LaTeXQuestionStudio/LaTeXQuestionStudio.exe'))
    if candidates:
        exe = candidates[-1]
raw=exe.read_bytes();pe_offset=struct.unpack_from('<I',raw,60)[0]
subsystem=struct.unpack_from('<H',raw,pe_offset+24+68)[0]
assert subsystem==2,'Application must use the Windows GUI subsystem'

user32=ctypes.WinDLL('user32',use_last_error=True)
kernel32=ctypes.WinDLL('kernel32',use_last_error=True)
callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
user32.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
user32.EnumWindows.restype=wintypes.BOOL
user32.IsWindowVisible.argtypes=[wintypes.HWND];user32.IsWindowVisible.restype=wintypes.BOOL
user32.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]


def visible_windows():
    windows={}
    @callback_type
    def collect(handle,parameter):
        if user32.IsWindowVisible(handle):
            name=ctypes.create_unicode_buffer(256);user32.GetClassNameW(handle,name,len(name))
            process_id=wintypes.DWORD();user32.GetWindowThreadProcessId(handle,ctypes.byref(process_id))
            windows[int(handle)]={'class':name.value,'pid':process_id.value}
        return True
    user32.EnumWindows(collect,0)
    return windows


class ProcessEntry(ctypes.Structure):
    _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),('th32ProcessID',wintypes.DWORD),
        ('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',wintypes.DWORD),('cntThreads',wintypes.DWORD),
        ('th32ParentProcessID',wintypes.DWORD),('pcPriClassBase',wintypes.LONG),('dwFlags',wintypes.DWORD),('szExeFile',wintypes.WCHAR*260)]


kernel32.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];kernel32.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
kernel32.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(ProcessEntry)];kernel32.Process32FirstW.restype=wintypes.BOOL
kernel32.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(ProcessEntry)];kernel32.Process32NextW.restype=wintypes.BOOL
kernel32.CloseHandle.argtypes=[wintypes.HANDLE];kernel32.CloseHandle.restype=wintypes.BOOL


def process_list():
    snapshot=kernel32.CreateToolhelp32Snapshot(2,0)
    if snapshot in (None,ctypes.c_void_p(-1).value):raise ctypes.WinError(ctypes.get_last_error())
    processes=[];entry=ProcessEntry();entry.dwSize=ctypes.sizeof(entry)
    try:
        valid=kernel32.Process32FirstW(snapshot,ctypes.byref(entry))
        while valid:
            processes.append((entry.th32ProcessID,entry.th32ParentProcessID,entry.szExeFile))
            valid=kernel32.Process32NextW(snapshot,ctypes.byref(entry))
    finally:kernel32.CloseHandle(snapshot)
    return processes


console_classes={'ConsoleWindowClass','CASCADIA_HOSTING_WINDOW_CLASS'}
baseline={handle for handle,info in visible_windows().items() if info['class'] in console_classes}
process=subprocess.Popen([str(exe),'--smoke-test','--smoke-delay-ms','12000','--data-dir',str(target),'--screenshot',str(output/'windowed-formula.png')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
started=time.monotonic();gui_visible=False;new_consoles={};descendants={process.pid};child_names=set()
try:
    while process.poll() is None and time.monotonic()-started<45:
        for handle,info in visible_windows().items():
            if info['pid']==process.pid and info['class'] not in console_classes:gui_visible=True
            if info['class'] in console_classes and handle not in baseline:new_consoles[handle]=info
        entries=process_list()
        for _ in range(3):
            for child,parent,name in entries:
                if parent in descendants:
                    descendants.add(child);child_names.add(name.lower())
        time.sleep(.025)
    stdout,stderr=process.communicate(timeout=3)
except subprocess.TimeoutExpired:
    process.kill();stdout,stderr=process.communicate()

pdfs=list((target/'cache').glob('*.pdf'));texts=[]
for path in pdfs:
    with pymupdf.open(path) as document:texts.append(''.join(page.get_text() for page in document))
report={'exit_code':process.returncode,'stderr':stderr.decode('utf-8','replace')[-1500:],
    'exe_sha256':hashlib.sha256(raw).hexdigest(),'pe_subsystem':subsystem,'windowed':subsystem==2,
    'console_suppression_used':False,'application_window_visible':gui_visible,'new_visible_console_windows':list(new_consoles.values()),
    'observed_child_processes':sorted(child_names),'fresh_pdf_count':len(pdfs),'formula_rendered':any('2s' in text and 'dfrac' not in text for text in texts),
    'synthetic_data':str(target),'duration_seconds':round(time.monotonic()-started,2)}
(output/'window-observation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
assert process.returncode==0 and gui_visible and not new_consoles and report['formula_rendered'] and 'pdflatex.exe' in child_names
assert (output/'windowed-formula.png').is_file()

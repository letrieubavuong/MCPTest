"""Application identity and boundaries of destructive build cleanup."""
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest
from PySide6.QtGui import QImage

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.icons import application_icon
from latex_question_studio.ui.main_window import MainWindow


ROOT=Path(__file__).resolve().parents[1]
HELPER=ROOT/'scripts/build-artifacts.ps1'


def test_application_icon_has_all_windows_sizes_and_is_applied(qtbot,tmp_path):
    icon=application_icon()
    expected={16,20,24,32,40,48,64,96,128,256}
    assert not icon.isNull() and {size.width() for size in icon.availableSizes()}==expected
    raw=(ROOT/'src/latex_question_studio/ui/assets/mcptest.ico').read_bytes()
    assert struct.unpack_from('<HHH',raw)==(0,1,len(expected))
    for index in range(len(expected)):
        width,height,_,_,_,_,size,offset=struct.unpack_from('<BBBBHHII',raw,6+16*index)
        image=QImage.fromData(raw[offset:offset+size])
        assert not image.isNull() and image.width()==(width or 256) and image.height()==(height or 256)
        assert image.pixelColor(0,0).alpha()==0 and image.pixelColor(image.width()//2,image.height()//2).alpha()>0
    window=MainWindow(create_services(AppConfig.load(tmp_path/'data')));qtbot.addWidget(window)
    assert not window.windowIcon().isNull() and window.windowIcon().availableSizes()==icon.availableSizes()
    window.close()


def powershell(tmp_path,script):
    if sys.platform!='win32' or not shutil.which('powershell'):pytest.skip('Windows cleanup integration')
    path=tmp_path/'check.ps1'
    path.write_text("$ErrorActionPreference = 'Stop'\n. '"+str(HELPER).replace("'","''")+"'\n"+script,encoding='utf-8-sig')
    return subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(path)],cwd=tmp_path,capture_output=True,text=True,timeout=45)


def create_file(root,relative,raw=b'fixture'):
    path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return path


def test_cleanup_removes_old_builds_but_keeps_current_and_user_data(tmp_path):
    workspace=tmp_path/'project'
    old=['dist/0.1.0/LaTeXQuestionStudio/old.exe','release/LaTeXQuestionStudio-0.1.0-win64.zip',
         '.runtime/bundle-before-old/old.exe','.runtime/pyinstaller-before-old/old.pkg',
         '.runtime/ui-zip-old/old.exe','.runtime/pytest-old/data.db','.runtime/build-stage-stale/work.pkg']
    kept=['dist/0.5.2/LaTeXQuestionStudio/current.exe','release/LaTeXQuestionStudio-0.5.2-win64.zip',
          'release/LaTeXQuestionStudio-0.5.2-win64.zip.sha256','.runtime/build-stage-active/new.exe',
          '.runtime/pyinstaller/PYZ.pyz','.runtime/python-embed/python.exe','.venv/python.exe',
          'src/code.py','docs/report.md','examples/main.tex','data/personal.sqlite','.runtime/personal-data/library.db']
    for relative in old+kept:create_file(workspace,relative)
    result=powershell(tmp_path,"""
$root=Join-Path $PSScriptRoot 'project'
$readonly=Get-Item -LiteralPath (Join-Path $root '.runtime/bundle-before-old')
$readonly.Attributes=$readonly.Attributes -bor [IO.FileAttributes]::ReadOnly
$file=Get-Item -LiteralPath (Join-Path $root '.runtime/bundle-before-old/old.exe')
$file.Attributes=$file.Attributes -bor [IO.FileAttributes]::ReadOnly
$keep=Join-Path $root '.runtime/build-stage-active'
$preview=@(Clear-StudioBuildArtifacts -Root $root -Version '0.5.2' -KeepPaths @($keep) -DryRun)
if ($preview.Count -ne 7) { throw 'Wrong dry-run selection' }
foreach ($entry in $preview) { if (-not (Test-Path -LiteralPath $entry.Path)) { throw 'Dry-run deleted files' } }
Clear-StudioBuildArtifacts -Root $root -Version '0.5.2' -KeepPaths @($keep) | Out-Null
""")
    assert result.returncode==0,result.stdout+result.stderr
    assert all(not (workspace/path).exists() for path in old)
    assert all((workspace/path).read_bytes()==b'fixture' for path in kept)


def test_cleanup_rejects_parent_paths_and_artifact_roots(tmp_path):
    create_file(tmp_path,'project/data/keep.db');create_file(tmp_path,'outside/keep.txt')
    result=powershell(tmp_path,"""
$root=Join-Path $PSScriptRoot 'project'
$paths=@($root,(Join-Path $root 'dist'),(Join-Path $root '.runtime'),(Join-Path $root 'release'),(Join-Path $root 'data'),(Join-Path $root '.runtime/../../outside'))
foreach ($path in $paths) {
    $rejected=$false
    try { Remove-StudioBuildArtifact -Root $root -Path $path | Out-Null } catch { $rejected=$true }
    if (-not $rejected) { throw 'Unsafe path was accepted' }
}
""")
    assert result.returncode==0,result.stdout+result.stderr
    assert (tmp_path/'outside/keep.txt').read_bytes()==b'fixture'
    assert (tmp_path/'project/data/keep.db').read_bytes()==b'fixture'


def test_cleanup_refuses_junctions_without_deleting_the_target(tmp_path):
    create_file(tmp_path,'outside/keep.txt');(tmp_path/'project/.runtime/bundle-before-link').mkdir(parents=True)
    result=powershell(tmp_path,"""
$root=Join-Path $PSScriptRoot 'project'
$link=Join-Path $root '.runtime/bundle-before-link/linked'
New-Item -ItemType Junction -Path $link -Target (Join-Path $PSScriptRoot 'outside') | Out-Null
$rejected=$false
try { Clear-StudioBuildArtifacts -Root $root -Version '0.5.2' | Out-Null } catch { $rejected=$true }
if (-not $rejected) { throw 'Junction was accepted' }
# Remove only the junction itself, without traversing its target.
[IO.Directory]::Delete($link)
$testFolder=Join-Path $root '.runtime/pytest-old'
New-Item -ItemType Directory -Path $testFolder | Out-Null
New-Item -ItemType Junction -Path (Join-Path $testFolder 'testcurrent') -Target (Join-Path $PSScriptRoot 'outside') | Out-Null
Clear-StudioBuildArtifacts -Root $root -Version '0.5.2' | Out-Null
if (Test-Path -LiteralPath $testFolder) { throw 'Test directory was retained' }
""")
    assert result.returncode==0,result.stdout+result.stderr
    assert (tmp_path/'outside/keep.txt').read_bytes()==b'fixture'


def test_cleanup_preserves_a_database_mistakenly_stored_in_an_old_bundle(tmp_path):
    create_file(tmp_path,'project/dist/0.1.0/LaTeXQuestionStudio/personal.db')
    create_file(tmp_path,'project/.runtime/bundle-before-old/old.exe')
    result=powershell(tmp_path,"""
$root=Join-Path $PSScriptRoot 'project'
$rejected=$false
try { Clear-StudioBuildArtifacts -Root $root -Version '0.5.2' | Out-Null } catch { $rejected=$true }
if (-not $rejected) { throw 'Bundle database was deleted' }
""")
    assert result.returncode==0,result.stdout+result.stderr
    assert (tmp_path/'project/dist/0.1.0/LaTeXQuestionStudio/personal.db').read_bytes()==b'fixture'
    assert (tmp_path/'project/.runtime/bundle-before-old/old.exe').exists()


def test_publish_renames_readonly_trees_and_restores_old_build_on_failure(tmp_path):
    workspace=tmp_path/'project'
    create_file(workspace,'dist/0.5.2/LaTeXQuestionStudio/old.exe',b'old')
    create_file(workspace,'.runtime/pyinstaller/old.pkg',b'old work')
    create_file(workspace,'.runtime/build-stage-new/candidate/LaTeXQuestionStudio/new.exe',b'new')
    create_file(workspace,'.runtime/build-stage-new/fail-source/new.pkg',b'new work')
    result=powershell(tmp_path,"""
$root=Join-Path $PSScriptRoot 'project'
$stage=Join-Path $root '.runtime/build-stage-new'
foreach ($directory in @('dist/0.5.2','dist/0.5.2/LaTeXQuestionStudio','.runtime/build-stage-new/candidate')) {
    $item=Get-Item -LiteralPath (Join-Path $root $directory)
    $item.Attributes=$item.Attributes -bor [IO.FileAttributes]::ReadOnly
}
$oldFile=Get-Item -LiteralPath (Join-Path $root 'dist/0.5.2/LaTeXQuestionStudio/old.exe')
$oldFile.Attributes=$oldFile.Attributes -bor [IO.FileAttributes]::ReadOnly
$promotions=@(
    @{ Source=(Join-Path $stage 'candidate'); Target=(Join-Path $root 'dist/0.5.2'); Backup=(Join-Path $stage 'previous-dist') },
    @{ Source=(Join-Path $stage 'fail-source'); Target=(Join-Path $root '.runtime/pyinstaller'); Backup=(Join-Path $stage 'previous-work') }
)
$realMove=(Get-Command Move-StudioBuildArtifact).ScriptBlock
function Move-StudioBuildArtifact {
    param([string]$Root,[string]$Source,[string]$Destination)
    if ($Source.EndsWith('fail-source')) { throw 'Simulated replacement failure' }
    & $realMove -Root $Root -Source $Source -Destination $Destination
}
$rejected=$false
try { Publish-StudioBuildArtifacts -Root $root -Promotions $promotions } catch { $rejected=$true }
if (-not $rejected) { throw 'Failure was ignored' }
""")
    assert result.returncode==0,result.stdout+result.stderr
    assert (workspace/'dist/0.5.2/LaTeXQuestionStudio/old.exe').read_bytes()==b'old'
    assert (workspace/'.runtime/pyinstaller/old.pkg').read_bytes()==b'old work'
    assert not (workspace/'dist/0.5.2/LaTeXQuestionStudio/new.exe').exists()

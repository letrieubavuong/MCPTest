from pathlib import Path
import time
import uuid
from PySide6.QtWidgets import QApplication
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.importing import ImportService
from latex_question_studio.ui.main_window import MainWindow

def run():
    root = Path(__file__).resolve().parents[1]
    folder = root / '.runtime' / ('ui-audit-' + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    services = create_services(AppConfig.load(folder))

    source = r'\begin{ex}Tính $\frac{1}{2}+\frac{1}{3}$.\choice{$1$}{\True $\frac{5}{6}$}{$\frac{2}{5}$}{$\frac{1}{6}$}\loigiai{Quy đồng mẫu: $\frac{3}{6}+\frac{2}{6}=\frac{5}{6}$.}\end{ex}'
    file = folder / 'Cau_hoi.tex'
    file.write_text('\n'.join([
        source,
        r'\begin{ex}Tìm số nguyên $x$ biết $x+4=9$.\shortans{5}\loigiai{$x=5$.}\end{ex}',
        r'\begin{ex}Tính diện tích hình vuông cạnh $a=3$ cm.\loigiai{$S=a^2=9$ cm$^2$.}\end{ex}'
    ]), encoding='utf-8')

    im = ImportService(services)
    batch, rows = im.stage([file])
    im.assign_classification([r['id'] for r in rows], 'curriculum:math6:lesson:01', 'TH')
    im.commit(batch)

    out = root / 'artifacts' / 'ui-redesign'
    out.mkdir(parents=True, exist_ok=True)

    w = MainWindow(services)
    w.resize(1366, 768)
    w.show()

    # Capture 1: Table mode Light
    w.theme = 'light'
    w.apply_theme()
    w.show_page(0)
    w.library_ui.mode.setCurrentIndex(0) # Table mode
    w.table.selectRow(0)
    app.processEvents()
    time.sleep(0.4)
    w.grab().save(str(out / 'csdl-table-light-1366x768.png'))

    # Capture 2: Table mode Dark
    w.theme = 'dark'
    w.apply_theme()
    app.processEvents()
    time.sleep(0.4)
    w.grab().save(str(out / 'csdl-table-dark-1366x768.png'))

    # Capture 3: Cards mode Dark (Collapsed)
    w.theme = 'dark'
    w.apply_theme()
    w.library_ui.mode.setCurrentIndex(1) # Cards mode
    w.library_ui.cards.setCurrentRow(0)
    app.processEvents()
    time.sleep(0.4)
    w.grab().save(str(out / 'csdl-cards-dark-1366x768.png'))
    w.grab().save(str(out / 'csdl-cards-collapsed-dark-1366x768.png'))

    # Capture 4: Cards mode Dark (Expanded)
    first_id = w.table_model.rows[0].id
    w.library_ui.expanded_ids.add(first_id)
    w.library_ui.sync_cards()
    app.processEvents()
    time.sleep(0.4)
    w.grab().save(str(out / 'csdl-cards-expanded-dark-1366x768.png'))

    # Capture 5: Cards mode Light (Expanded)
    w.theme = 'light'
    w.apply_theme()
    app.processEvents()
    time.sleep(0.4)
    w.grab().save(str(out / 'csdl-cards-expanded-light-1366x768.png'))

    # Capture 6: Cards mode Light (Collapsed)
    w.library_ui.expanded_ids.clear()
    w.library_ui.sync_cards()
    app.processEvents()
    time.sleep(0.4)
    w.grab().save(str(out / 'csdl-cards-light-1366x768.png'))
    w.grab().save(str(out / 'csdl-cards-collapsed-light-1366x768.png'))

    # Capture 5: Inspector "Phan loai" tab
    w.theme = 'dark'
    w.apply_theme()
    w.library_ui.inspector.setCurrentIndex(1)
    app.processEvents()
    time.sleep(0.3)
    w.grab().save(str(out / 'csdl-inspector-meta-dark-1366x768.png'))

    w.close()
    app.processEvents()
    import shutil, glob
    dest = Path(r"C:\Users\Admin\.gemini\antigravity-ide\brain\f98e3884-5bf3-462a-8b06-60e1ffa1e9d7\screenshots")
    dest.mkdir(parents=True, exist_ok=True)
    for p in out.glob('*.png'):
        shutil.copy(p, dest)
    print("Done audit extra captures and copied to brain")

if __name__ == '__main__':
    run()

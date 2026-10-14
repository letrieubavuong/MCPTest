"""Small original SVG line icons; no external icon package or font required."""
from pathlib import Path
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer


def application_icon():
    return QIcon(str(Path(__file__).with_name('assets')/'mcptest.ico'))

PATHS={
 'home':'<path d="m4 10 8-6 8 6v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z"/><path d="M9 20v-5h6v5"/>',
 'close':'<path d="m6 6 12 12M18 6 6 18"/>',
 'subject':'<path d="M5 5h14M5 9h14M5 13h9M5 17h14"/>',
 'chapter':'<path d="M3.5 8.5V6a2 2 0 0 1 2-2h5l2 2.5h6a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-15z"/><path d="M3.5 9h17"/>',
 'topic':'<path d="M6 3.5h8l4 4v13H6a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2z"/><path d="M14 3.5v4h4M8 12h7M8 16h5"/>',
 'bank':'<path d="m4 9 8-5 8 5"/><path d="M5 9h14M6 9v8M10 9v8M14 9v8M18 9v8M4 19h16"/>',
 'import':'<path d="M7 3.5h7l4 4v13H7a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2z"/><path d="M14 3.5v4h4M12 10v7m-3-3 3 3 3-3"/>',
 'exam':'<rect x="5" y="3.5" width="14" height="17" rx="2"/><path d="m8 9 1.5 1.5L12 8M14 10h2M8 15l1.5 1.5L12 14M14 16h2"/>',
 'settings':'<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',
 'lesson':'<path d="M12 6c-2-2-5-2-8-1v14c3-1 6-1 8 1 2-2 5-2 8-1V5c-3-1-6-1-8 1z"/><path d="M12 6v14"/>',
 'save':'<path d="M5 3.5h13l2 2v15H4v-17zM8 3.5v5h8v-5M8 20.5v-8h8v8"/>',
 'preview':'<path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6z"/><circle cx="12" cy="12" r="2.5"/>',
 'edit':'<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
 'dedup':'<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M4 16V4a2 2 0 0 1 2-2h12"/>',
 'web':'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 4 9 14 14 0 0 1-4 9 14 14 0 0 1-4-9 14 14 0 0 1 4-9z"/>',
}


def icon(name, color='#dedede'):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</g></svg>'
    pixmap=QPixmap(48,48);pixmap.fill(Qt.GlobalColor.transparent)
    painter=QPainter(pixmap);QSvgRenderer(QByteArray(svg.encode())).render(painter);painter.end()
    return QIcon(pixmap)

"""Render the original vector mark to PNG and a Windows ICO with ten sizes."""
from pathlib import Path
import struct

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt, QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


root=Path(__file__).resolve().parents[1]
assets=root/'src/latex_question_studio/ui/assets'
renderer=QSvgRenderer(str(assets/'mcptest.svg'))
if not renderer.isValid():raise ValueError('Invalid application icon SVG')


def render(size):
    image=QImage(size,size,QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter);painter.end()
    return image


sizes=(16,20,24,32,40,48,64,96,128,256)
entries=[];images=[];offset=6+16*len(sizes)
for size in sizes:
    buffer=QBuffer();buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not render(size).save(buffer,'PNG'):raise RuntimeError('Cannot render application icon')
    raw=bytes(buffer.data());buffer.close()
    entries.append(struct.pack('<BBBBHHII',size%256,size%256,0,0,1,32,len(raw),offset))
    images.append(raw);offset+=len(raw)
(assets/'mcptest.ico').write_bytes(struct.pack('<HHH',0,1,len(sizes))+b''.join(entries)+b''.join(images))
if not render(512).save(str(assets/'mcptest.png')):raise RuntimeError('Cannot save application PNG')

output=root/'artifacts/app-icon';output.mkdir(parents=True,exist_ok=True)
sheet=QImage(800,320,QImage.Format.Format_ARGB32_Premultiplied);sheet.fill('#f7f9fc')
painter=QPainter(sheet);painter.fillRect(0,160,800,160,'#202124')
for y in (0,160):
    x=30
    for size in (16,24,32,48,64,96,128):
        painter.drawImage(QRectF(x,y+(160-size)/2,size,size),render(size));x+=size+35
painter.end();sheet.save(str(output/'icon-sizes.png'))
print('Application icon: SVG, PNG 512px and ICO '+', '.join(map(str,sizes)))

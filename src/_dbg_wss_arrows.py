# -*- coding: utf-8 -*-
"""诊断: 把每个深色描边箭头对象编号叠加到区域截图上."""
import pdfplumber, math
from PIL import Image, ImageDraw, ImageFont

PDF = 'data/monitoring/World-Silver-Survey-2026.pdf'
SCALE = 200 / 72.0  # 渲染分辨率 -> 像素/点
REGIONS = {
    '23a': (84, 30, 85, 605, 320, 'output/_wss_p85_full.png', (100, 250, 1650, 850)),
    '23b': (84, 30, 385, 605, 752, 'output/_wss_p85_full.png', (100, 1100, 1650, 2050)),
    '24a': (85, 30, 85, 605, 320, 'output/_wss_p86_full.png', (100, 250, 1650, 850)),
    '24b': (85, 30, 385, 605, 752, 'output/_wss_p86_full.png', (100, 1100, 1650, 2050)),
    '25':  (86, 30, 85, 605, 330, 'output/_wss_p87_full.png', (100, 250, 1650, 900)),
    '26':  (86, 30, 385, 605, 752, 'output/_wss_p87_full.png', (100, 1100, 1650, 2050)),
}
COLORS = ['red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'lime',
          'navy', 'teal', 'maroon', 'olive', 'fuchsia', 'aqua', 'brown', 'pink',
          'gold', 'indigo', 'coral', 'khaki']

def sample_path(path, n=24):
    """把 pdfplumber curve.path (top 原点) 采样成折线."""
    pts = []
    cur = None
    for seg in path:
        op = seg[0]
        if op == 'm':
            cur = tuple(seg[1])
            pts.append(cur)
        elif op == 'l':
            cur = tuple(seg[1])
            pts.append(cur)
        elif op in ('c', 'v', 'y'):
            p = [tuple(q) for q in seg[1:]]
            if op == 'c':
                c1, c2, end = p
            elif op == 'v':
                c1, c2, end = cur, p[0], p[1]
            else:
                c1, c2, end = p[0], end if False else p[0], p[1]
                c1, c2 = p[0], p[0]
                end = p[1]
            p0 = cur
            for i in range(1, n + 1):
                t = i / n
                mt = 1 - t
                x = mt**3 * p0[0] + 3 * mt * mt * t * c1[0] + 3 * mt * t * t * c2[0] + t**3 * end[0]
                y = mt**3 * p0[1] + 3 * mt * mt * t * c1[1] + 3 * mt * t * t * c2[1] + t**3 * end[1]
                pts.append((x, y))
            cur = end
    return pts

pdf = pdfplumber.open(PDF)
for name, (pg, x0, t, x1, b, img_path, crop) in REGIONS.items():
    page = pdf.pages[pg]
    im = Image.open(img_path).crop(crop).convert('RGB')
    dr = ImageDraw.Draw(im)
    objs = []
    for o in page.curves + page.lines:
        sc = o.get('stroking_color')
        if not (o.get('stroke') and sc and max(sc[:3]) < 0.5 and o.get('linewidth', 1) <= 1.0):
            continue
        cx = (o['x0'] + o['x1']) / 2
        cy = (o['top'] + o['bottom']) / 2
        if not (x0 - 5 <= cx <= x1 + 5 and t - 5 <= cy <= b + 5):
            continue
        if o['object_type'] == 'line':
            pts = [(o['x0'], o['top']), (o['x1'], o['bottom'])]
        else:
            pts = sample_path(o.get('path') or [])
        if len(pts) < 2:
            continue
        length = sum(math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1]) for i in range(len(pts)-1))
        objs.append((pts, length))
    # PDF 点 -> 裁剪图像素
    def px(p):
        return (p[0] * SCALE - crop[0], p[1] * SCALE - crop[1])
    for i, (pts, length) in enumerate(objs):
        col = COLORS[i % len(COLORS)]
        pxy = [px(p) for p in pts]
        dr.line(pxy, fill=col, width=4)
        mid = pxy[len(pxy) // 2]
        dr.text((mid[0] + 4, mid[1] - 10), f'{i}:{length:.0f}', fill=col)
    out = f'output/_dbg_{name}_arrows.png'
    im.save(out)
    print(name, 'objects:', len(objs), '->', out)
    print('   lengths:', sorted((round(l) for _, l in objs), reverse=True))

# -*- coding: utf-8 -*-
"""
v3 重做 WSS 六张流向图配对 —— 最终版。
原理:
  箭身 = 深色描边曲线(lw<=1), 用 path 里的贝塞尔采样成折线;
  尖端 = 出口图离 hub 远的端点 / 进口图离 hub 近的端点,
         并用深色填充小多边形(箭头尖) 交叉校验;
  伙伴端(出口=尖端, 进口=尾端) -> 最近国名标签;
  数值标签 -> 点到折线距离最小的箭。
输出: output/_wss_geom_pairing.json + 每图 QA 叠加图 output/_qa_<name>.png
"""
import pdfplumber, re, math, json, sys
from PIL import Image, ImageDraw

PDF = 'data/monitoring/World-Silver-Survey-2026.pdf'
SCALE = 200 / 72.0
MOZ_TO_T = 31.1035

REGIONS = {
    '23a_swiss_export': (84, 30, 85, 605, 320, 'export', 'Switzerland',
                         'output/_wss_p85_full.png', (100, 250, 1650, 850)),
    '23b_swiss_import': (84, 30, 385, 605, 752, 'import', 'Switzerland',
                         'output/_wss_p85_full.png', (100, 1100, 1650, 2050)),
    '24a_uk_export':    (85, 30, 85, 605, 320, 'export', 'UK',
                         'output/_wss_p86_full.png', (100, 250, 1650, 850)),
    '24b_uk_import':    (85, 30, 385, 605, 752, 'import', 'UK',
                         'output/_wss_p86_full.png', (100, 1100, 1650, 2050)),
    '25_hk_export':     (86, 30, 85, 605, 330, 'export', 'Hong Kong',
                         'output/_wss_p87_full.png', (100, 250, 1650, 900)),
    '26_india_import':  (86, 30, 385, 605, 752, 'import', 'India',
                         'output/_wss_p87_full.png', (100, 1100, 1650, 2050)),
}
COUNTRIES = {
    '23a_swiss_export': ['UK', 'USA', 'Turkey', 'India', 'Germany', 'Italy',
                         'Lebanon', 'France', 'UAE', 'Thailand'],
    '23b_swiss_import': ['USA', 'Peru', 'Germany', 'Poland', 'Italy', 'Morocco',
                         'China', 'Indonesia', 'Australia'],
    '24a_uk_export':    ['USA', 'UAE', 'Canada', 'Switzerland', 'India', 'Belgium'],
    '24b_uk_import':    ['Canada', 'USA', 'Mexico', 'Germany', 'Poland', 'Switzerland',
                         'Spain', 'Kazakhstan', 'Uzbekistan', 'China', 'South Korea'],
    '25_hk_export':     ['UK', 'Switzerland', 'USA', 'China', 'India', 'Taiwan',
                         'UAE', 'Vietnam', 'Thailand', 'Singapore', 'Australia'],
    '26_india_import':  ['UK', 'USA', 'Switzerland', 'UAE', 'China', 'Hong Kong',
                         'S.Korea', 'Singapore', 'Australia'],
}
MIN_ARROW_LEN = 8.0     # 低于此长度视为羽枝
HEAD_TOL = 5.0          # 端点-箭头尖填充 匹配容差(pt)

def sample_path(path, n=30):
    pts = []
    cur = None
    for seg in path or []:
        op = seg[0]
        if op == 'm':
            cur = tuple(seg[1]); pts.append(cur)
        elif op == 'l':
            cur = tuple(seg[1]); pts.append(cur)
        elif op in ('c', 'v', 'y'):
            p = [tuple(q) for q in seg[1:]]
            if op == 'c':
                c1, c2, end = p
            elif op == 'v':
                c1, c2, end = cur, p[0], p[1]
            else:
                c1, c2, end = p[0], p[0], p[1]
            p0 = cur
            for i in range(1, n + 1):
                t = i / n; mt = 1 - t
                pts.append((mt**3*p0[0] + 3*mt*mt*t*c1[0] + 3*mt*t*t*c2[0] + t**3*end[0],
                            mt**3*p0[1] + 3*mt*mt*t*c1[1] + 3*mt*t*t*c2[1] + t**3*end[1]))
            cur = end
    return pts

def poly_len(pts):
    return sum(math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1])
               for i in range(len(pts)-1))

def dist_pt_poly(p, pts):
    best = 1e9
    for i in range(len(pts)-1):
        ax, ay = pts[i]; bx, by = pts[i+1]
        dx, dy = bx-ax, by-ay
        L2 = dx*dx + dy*dy
        if L2 < 1e-9:
            d = math.hypot(p[0]-ax, p[1]-ay)
        else:
            t = max(0, min(1, ((p[0]-ax)*dx + (p[1]-ay)*dy) / L2))
            d = math.hypot(p[0]-(ax+t*dx), p[1]-(ay+t*dy))
        if d < best:
            best = d
    return best

def merge_value_tokens(words):
    ws = sorted(words, key=lambda w: (round(w['top']/3), w['x0']))
    skip, out = set(), []
    for i, w in enumerate(ws):
        if i in skip:
            continue
        txt = w['text']
        nxt = ws[i+1] if i+1 < len(ws) else None
        same = nxt is not None and abs(nxt['top']-w['top']) < 3.5
        gap = (nxt['x0']-w['x1']) if same else 99
        if re.fullmatch(r'\d+', txt) and same and gap < 8 and re.fullmatch(r'\d+Moz', nxt['text']):
            m = re.fullmatch(r'(\d+)Moz', nxt['text'])
            out.append({'text': txt + m.group(1) + 'Moz', 'x0': w['x0'], 'x1': nxt['x1'],
                        'top': min(w['top'], nxt['top']), 'bottom': max(w['bottom'], nxt['bottom'])})
            skip.add(i+1)
        elif re.fullmatch(r'\d+Mo', txt) and same and gap < 8 and nxt['text'] == 'z':
            out.append({'text': txt[:-2] + 'Moz', 'x0': w['x0'], 'x1': nxt['x1'],
                        'top': min(w['top'], nxt['top']), 'bottom': max(w['bottom'], nxt['bottom'])})
            skip.add(i+1)
        else:
            out.append(w)
    return out

def merge_lines(words):
    ws = sorted(words, key=lambda w: (round(w['top']/3), w['x0']))
    lines = []
    for w in ws:
        for ln in lines:
            if abs(ln['top']-w['top']) < 3.5 and w['x0']-ln['x1'] < 8:
                ln['text'] += ' ' + w['text']
                ln['x1'] = w['x1']
                ln['top'] = min(ln['top'], w['top'])
                ln['bottom'] = max(ln['bottom'], w['bottom'])
                break
        else:
            lines.append({'text': w['text'], 'x0': w['x0'], 'x1': w['x1'],
                          'top': w['top'], 'bottom': w['bottom']})
    return lines

def hungarian(cost):
    """矩形指派 (n行<=m列), 返回每行的列号."""
    n = len(cost); m = len(cost[0])
    u = [0]*(n+1); v = [0]*(m+1); p = [0]*(m+1); way = [0]*(m+1)
    for i in range(1, n+1):
        p[0] = i
        j0 = 0
        minv = [float('inf')]*(m+1)
        used = [False]*(m+1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float('inf'); j1 = 0
            for j in range(1, m+1):
                if not used[j]:
                    cur = cost[i0-1][j-1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur; way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]; j1 = j
            for j in range(m+1):
                if used[j]:
                    u[p[j]] += delta; v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    assign = [None]*n
    for j in range(1, m+1):
        if p[j] > 0:
            assign[p[j]-1] = j-1
    return assign

def main():
    pdf = pdfplumber.open(PDF)
    results = {}
    for name, (pg, x0, t, x1, b, direction, hub, img_path, crop) in REGIONS.items():
        page = pdf.pages[pg]
        # ---- 文字 ----
        words = [w for w in page.extract_words(x_tolerance=1.5)
                 if x0 <= w['x0'] <= x1 and t <= w['top'] <= b]
        values = []
        for w in merge_value_tokens(words):
            m = re.fullmatch(r'(\d+)Moz', w['text'])
            if m:
                values.append({'moz': int(m.group(1)),
                               'cx': (w['x0']+w['x1'])/2, 'cy': (w['top']+w['bottom'])/2})
        lines = merge_lines(words)
        # ---- hub / 国名位置 ----
        skip_ln = lambda s: s['text'].startswith(('Appendix', 'NB:', 'Source'))
        hub_pos = None
        for ln in lines:  # 标题/脚注也可能含 hub 词, 排除后取最下方出现
            if skip_ln(ln):
                continue
            if re.search(r'\b' + re.escape(hub.lower()) + r'\b', ln['text'].lower()):
                cand_pos = ((ln['x0']+ln['x1'])/2, (ln['top']+ln['bottom'])/2)
                if hub_pos is None or cand_pos[1] > hub_pos[1]:
                    hub_pos = cand_pos
        cpos = {}
        for c in COUNTRIES[name]:
            cand = [ln for ln in lines if ln['text'].lower() == c.lower()] or \
                   [ln for ln in lines if c.lower() in ln['text'].lower()]
            if cand:
                ln = min(cand, key=lambda l: len(l['text']))
                cpos[c] = ((ln['x0']+ln['x1'])/2, (ln['top']+ln['bottom'])/2)
        # ---- 箭头尖填充(近灰深色小多边形, 排除彩色国点) ----
        heads = []
        for o in page.curves + page.rects:
            if not o.get('fill'):
                continue
            fc = o.get('non_stroking_color')
            if not fc:
                continue
            v3 = tuple(float(v) for v in fc[:3])
            if max(v3) >= 0.25 or (max(v3)-min(v3)) >= 0.08:
                continue
            cx, cy = (o['x0']+o['x1'])/2, (o['top']+o['bottom'])/2
            if max(o['x1']-o['x0'], o['bottom']-o['top']) <= 14 and \
               x0 <= cx <= x1 and t <= cy <= b:
                heads.append((cx, cy))
        # ---- 箭身 ----
        bodies = []
        for o in page.curves + page.lines:
            sc = o.get('stroking_color')
            if not (o.get('stroke') and sc and max(sc[:3]) < 0.5
                    and o.get('linewidth', 1) <= 1.0):
                continue
            cx, cy = (o['x0']+o['x1'])/2, (o['top']+o['bottom'])/2
            if not (x0-5 <= cx <= x1+5 and t-5 <= cy <= b+5):
                continue
            if o['object_type'] == 'line':
                pts = [(o['x0'], o['top']), (o['x1'], o['bottom'])]
            else:
                pts = sample_path(o.get('path'))
            if len(pts) < 2:
                continue
            L = poly_len(pts)
            if L >= MIN_ARROW_LEN:
                bodies.append({'pts': pts, 'len': L})
        # 合并共享端点的分段(有的箭由两段组成)
        changed = True
        while changed:
            changed = False
            for i in range(len(bodies)):
                if changed:
                    break
                for j in range(i+1, len(bodies)):
                    a, bb = bodies[i], bodies[j]
                    found = None
                    for ae, ap in ((0, a['pts'][0]), (-1, a['pts'][-1])):
                        for be, bp in ((0, bb['pts'][0]), (-1, bb['pts'][-1])):
                            if math.hypot(ap[0]-bp[0], ap[1]-bp[1]) <= 3.0:
                                found = (ae, be)
                                break
                        if found:
                            break
                    if found and (max(a['len'], bb['len']) < 60 or
                                  min(a['len'], bb['len']) < 25):  # 长弧+短连接段也并
                        ae, be = found
                        shared = a['pts'][ae]
                        if math.hypot(shared[0]-hub_pos[0], shared[1]-hub_pos[1]) <= 15:
                            continue  # 枢纽处不并, 防两支箭误连
                        pa = a['pts'] if ae == -1 else a['pts'][::-1]
                        pb = bb['pts'] if be == 0 else bb['pts'][::-1]
                        # 角度连续性: X 形交叉不并
                        ia = min(3, len(pa)-1); ib = min(3, len(pb)-1)
                        da = (shared[0]-pa[-1-ia][0], shared[1]-pa[-1-ia][1])
                        db = (pb[ib][0]-shared[0], pb[ib][1]-shared[1])
                        la, lb = math.hypot(*da), math.hypot(*db)
                        if la > 0 and lb > 0 and \
                           (da[0]*db[0]+da[1]*db[1])/(la*lb) < 0.7:
                            continue
                        bodies[i] = {'pts': pa + pb[1:], 'len': a['len'] + bb['len']}
                        del bodies[j]
                        changed = True
                        break
        # ---- 每支箭: 尖端(hub 规则) -> 伙伴端 -> 国名; 填充校验 ----
        import os
        if os.environ.get('WSS_DEBUG'):
            print(f'  [dbg] hub={tuple(round(q,1) for q in hub_pos)} heads={[tuple(round(q,1) for q in h) for h in heads]}')
            for k, bd in enumerate(bodies):
                p = bd['pts']
                print(f'  [dbg] body{k} len={bd["len"]:.0f} e0=({p[0][0]:.0f},{p[0][1]:.0f}) '
                      f'e1=({p[-1][0]:.0f},{p[-1][1]:.0f})')
            for v in values:
                print(f'  [dbg] val {v["moz"]}Moz at ({v["cx"]:.0f},{v["cy"]:.0f})')
        # 箭头尖填充 -> 国名(出口图两级匹配, 避开标签邻近陷阱)
        head_country = []
        for hx, hy in heads:
            bc, bd = None, 1e9
            for c, cp in cpos.items():
                d = math.hypot(hx-cp[0], hy-cp[1])
                if d < bd:
                    bc, bd = c, d
            head_country.append((bc, bd))
        arrows = []
        for bd in bodies:
            pts = bd['pts']
            e0, e1 = pts[0], pts[-1]
            h0 = math.hypot(e0[0]-hub_pos[0], e0[1]-hub_pos[1])
            h1 = math.hypot(e1[0]-hub_pos[0], e1[1]-hub_pos[1])
            tip, tail = (e1, e0) if (h1 > h0) == (direction == 'export') else (e0, e1)
            hi, d_head = -1, 1e9
            for k, (hx, hy) in enumerate(heads):
                d = math.hypot(tip[0]-hx, tip[1]-hy)
                if d < d_head:
                    hi, d_head = k, d
            partner_pt = tip if direction == 'export' else tail
            if direction == 'export' and hi >= 0 and d_head <= 25:
                best_c = head_country[hi][0]
                best_d = head_country[hi][1]
            else:
                best_c, best_d = None, 1e9
                for c, cp in cpos.items():
                    d = math.hypot(partner_pt[0]-cp[0], partner_pt[1]-cp[1])
                    if d < best_d:
                        best_c, best_d = c, d
            arrows.append({'pts': pts, 'len': bd['len'], 'tip': tip, 'tail': tail,
                           'head_dist': round(d_head, 1), 'country': best_c,
                           'country_dist': round(best_d, 1), 'partner_pt': partner_pt})
        # ---- 值分配: Hungarian 全局最优(一箭一值) ----
        if values and arrows:
            na = len(arrows)
            cost = [[dist_pt_poly((v['cx'], v['cy']), a['pts']) for a in arrows] for v in values]
            if na < len(values):  # 箭身缺失时补哑列, 值可为未分配
                for row in cost:
                    row.extend([999.0] * (len(values) - na))
            assign = hungarian(cost)
            for vi, ai in enumerate(assign):
                if ai >= na:
                    values[vi]['arrow'] = None
                    values[vi]['dist'] = 999
                    values[vi]['margin'] = 0
                    continue
                values[vi]['arrow'] = ai
                row = sorted(cost[vi][:na])
                values[vi]['dist'] = round(cost[vi][ai], 1)
                values[vi]['margin'] = round(row[1]-row[0], 1) if len(row) > 1 else 99
        pairing = []
        for i, a in enumerate(arrows):
            vs = sorted([v for v in values if v.get('arrow') == i], key=lambda v: v['dist'])
            pairing.append({'country': a['country'], 'country_dist': a['country_dist'],
                            'head_dist': a['head_dist'], 'len': round(a['len']),
                            'partner_pt': [round(a['partner_pt'][0], 1), round(a['partner_pt'][1], 1)],
                            'moz': [v['moz'] for v in vs],
                            'val_dist': [v['dist'] for v in vs],
                            'val_margin': [v['margin'] for v in vs]})
        pairing.sort(key=lambda x: -(x['moz'][0] if x['moz'] else 0))
        unmatched_vals = [v['moz'] for v in values if all(v['moz'] not in p['moz'] for p in pairing)]
        results[name] = {'direction': direction,
                         'values_found': sorted((v['moz'] for v in values), reverse=True),
                         'n_bodies': len(bodies), 'n_heads': len(heads),
                         'countries_missing': [c for c in COUNTRIES[name] if c not in cpos],
                         'pairing': pairing}
        print(f"\n=== {name} ({direction}) bodies={len(bodies)} heads={len(heads)} "
              f"hub={hub_pos and tuple(round(q) for q in hub_pos)} ===")
        print(' 值集合:', sorted((v['moz'] for v in values), reverse=True))
        for p in pairing:
            flags = []
            if p['country_dist'] > 40:
                flags.append('COUNTRY?')
            if not p['moz']:
                flags.append('NO-VAL')
            if len(p['moz']) > 1:
                flags.append('MULTI-VAL')
            if p['val_margin'] and min(p['val_margin']) < 8:
                flags.append('VAL-CLOSE')
            if p['head_dist'] > 12:
                flags.append('NO-HEAD')
            print(f"  {str(p['moz']):10} -> {p['country'] or '?':12} len={p['len']:4} "
                  f"pt={p['partner_pt']} cd={p['country_dist']:5} hd={p['head_dist']:5} "
                  f"vd={p['val_dist']} m={p['val_margin']} {'/'.join(flags)}")
        # ---- QA 叠加图 ----
        im = Image.open(img_path).crop(crop).convert('RGB')
        dr = ImageDraw.Draw(im)
        def px(p):
            return (p[0]*SCALE - crop[0], p[1]*SCALE - crop[1])
        palette = ['red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta',
                   'lime', 'navy', 'teal', 'maroon', 'olive', 'fuchsia', 'brown']
        for i, a in enumerate(arrows):
            col = palette[i % len(palette)]
            dr.line([px(p) for p in a['pts']], fill=col, width=4)
            pp = px(a['partner_pt'])
            dr.ellipse([pp[0]-7, pp[1]-7, pp[0]+7, pp[1]+7], outline=col, width=3)
            dr.text((pp[0]+9, pp[1]-12), f"{a['country']}", fill=col)
        for v in values:
            vp = px((v['cx'], v['cy']))
            dr.ellipse([vp[0]-14, vp[1]-14, vp[0]+14, vp[1]+14], outline='red', width=2)
            dr.text((vp[0]+15, vp[1]+10), f"->{v['arrow']}", fill='red')
        im.save(f'output/_qa_{name}.png')
    with open('output/_wss_geom_pairing.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print('\nJSON -> output/_wss_geom_pairing.json')

if __name__ == '__main__':
    main()

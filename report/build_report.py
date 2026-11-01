#!/usr/bin/env python3
# 説明資料（HTML）を作り、Chrome のヘッドレス印刷で PDF にする。
# 使い方: python3 report/build_report.py [出力PDF]
import base64
import csv
import html
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PDF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '説明資料_PAI最終課題.pdf')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

MU = 0.1      # 板の上面とピザの間の摩擦係数
G = 9.8
PULL = 0.45   # 板を引く距離 [m]


def load_results():
    rows = []
    with open(os.path.join(HERE, 'pull_results.csv')) as f:
        for r in csv.DictReader(f):
            rows.append({
                't': float(r['pull_time_s']),
                'v': float(r['mean_speed_mps']),
                'drag': float(r['drag_cm']),
                'x': float(r['pizza_x']),
                'z': float(r['pizza_z']),
                'ok': r['on_stand'] == 'True',
            })
    return rows


def model_drag_cm(t):
    """ピザが板の上を滑り続けると仮定したときの引きずられ距離 ½μgT²（板の移動距離で頭打ち）。"""
    return min(0.5 * MU * G * t * t, PULL) * 100


def chart(rows):
    """引く時間と引きずられ距離のグラフ（SVG）。○＝成功、×＝失敗、破線＝単純モデル。"""
    W, H, L, R, T, B = 520, 300, 56, 16, 14, 44
    tmin, tmax, dmax = 0.3, 1.1, 50.0

    def px(t):
        return L + (t - tmin) / (tmax - tmin) * (W - L - R)

    def py(d):
        return T + (1 - d / dmax) * (H - T - B)

    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
         'font-family="Noto Sans JP, Hiragino Sans, sans-serif" font-size="11">']
    for d in range(0, 51, 10):
        s.append(f'<line x1="{L}" x2="{W - R}" y1="{py(d):.1f}" y2="{py(d):.1f}" stroke="#ddd"/>')
        s.append(f'<text x="{L - 6}" y="{py(d) + 4:.1f}" text-anchor="end">{d}</text>')
    for i in range(3, 12):
        t = i / 10
        s.append(f'<line x1="{px(t):.1f}" x2="{px(t):.1f}" y1="{H - B}" y2="{H - B + 4}" stroke="#333"/>')
        s.append(f'<text x="{px(t):.1f}" y="{H - B + 16}" text-anchor="middle">{t:.1f}</text>')
    s.append(f'<line x1="{L}" x2="{W - R}" y1="{H - B}" y2="{H - B}" stroke="#333"/>')
    s.append(f'<line x1="{L}" x2="{L}" y1="{T}" y2="{H - B}" stroke="#333"/>')
    s.append(f'<text x="{(L + W - R) / 2}" y="{H - 8}" text-anchor="middle">板を 45 cm 引く時間 T [s]</text>')
    s.append(f'<text transform="translate(14 {(T + H - B) / 2}) rotate(-90)" text-anchor="middle">'
             'ピザが引きずられた距離 [cm]</text>')
    pts = ' '.join(f'{px(t / 100):.1f},{py(model_drag_cm(t / 100)):.1f}' for t in range(30, 111, 2))
    s.append(f'<polyline points="{pts}" fill="none" stroke="#555" stroke-dasharray="5 4"/>')
    for r in rows:
        x, y = px(r['t']), py(r['drag'])
        if r['ok']:
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="none" stroke="#000" stroke-width="1.6"/>')
        else:
            s.append(f'<path d="M{x - 5:.1f} {y - 5:.1f}L{x + 5:.1f} {y + 5:.1f}M{x - 5:.1f} {y + 5:.1f}'
                     f'L{x + 5:.1f} {y - 5:.1f}" stroke="#000" stroke-width="1.6"/>')
    lx, ly = W - R - 170, T + 8
    s.append(f'<circle cx="{lx}" cy="{ly}" r="5" fill="none" stroke="#000" stroke-width="1.6"/>'
             f'<text x="{lx + 10}" y="{ly + 4}">ピザが台に残った（成功）</text>')
    s.append(f'<path d="M{lx - 5} {ly + 13}L{lx + 5} {ly + 23}M{lx - 5} {ly + 23}L{lx + 5} {ly + 13}" '
             f'stroke="#000" stroke-width="1.6"/><text x="{lx + 10}" y="{ly + 22}">残らなかった（失敗）</text>')
    s.append(f'<line x1="{lx - 8}" x2="{lx + 6}" y1="{ly + 36}" y2="{ly + 36}" stroke="#555" '
             f'stroke-dasharray="5 4"/><text x="{lx + 10}" y="{ly + 40}">モデル ½μgT²（μ=0.1）</text>')
    s.append('</svg>')
    return '\n'.join(s)


def image(name):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        return ''
    with open(path, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()


def outcome(r):
    if r['ok']:
        return '台に残った'
    if r['z'] < 0.1:
        return '板と一緒に手前へ運ばれ、台の手前の端から落ちた'
    return '板の上に載ったまま手前へ運ばれた'


def build_html(rows):
    rows = sorted(rows, key=lambda r: -r['t'])
    table = '\n'.join(
        f'<tr><td>{r["t"]:.2f}</td><td>{r["v"]:.2f}</td><td>{r["drag"]:.1f}</td>'
        f'<td>{model_drag_cm(r["t"]):.1f}</td><td>{"○" if r["ok"] else "×"}</td>'
        f'<td class="l">{html.escape(outcome(r))}</td></tr>' for r in rows)
    shots = ''.join(
        f'<figure><img src="{image(f"shot{i}.png")}"><figcaption>{c}</figcaption></figure>'
        for i, c in enumerate(['① 持ち手に近づいてつかむ', '② 水平のまま奥へ運ぶ', '③ 板を素早く引いた直後',
                               '④ ピザだけが台に残る'], 1) if image(f'shot{i}.png'))
    with open(os.path.join(HERE, 'report_template.html'), encoding='utf-8') as f:
        tpl = f.read()
    return (tpl.replace('{{SHOTS}}', shots).replace('{{TABLE}}', table)
            .replace('{{CHART}}', chart(rows)))


def main():
    html_path = os.path.join(HERE, 'report.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(build_html(load_results()))
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                    f'--print-to-pdf={OUT_PDF}', 'file://' + html_path],
                   check=True, capture_output=True)
    print('保存しました:', OUT_PDF)


if __name__ == '__main__':
    main()

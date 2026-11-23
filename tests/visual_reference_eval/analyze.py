"""Produce a comparison sheet and objective color measurements for the synthetic samples."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CASES = {
    'roxo': {'background': '#291044', 'heading': '#ffffff', 'accent': '#d5f542'},
    'claro': {'background': '#fff5e9', 'heading': '#12315d', 'accent': '#f26930'},
}


def rgb(hex_color: str) -> tuple[float, float, float]:
    return tuple(int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def linear(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def lab(hex_color: str) -> tuple[float, float, float]:
    r, g, b = (linear(value) for value in rgb(hex_color))
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883
    def f(value: float) -> float:
        return value ** (1 / 3) if value > 216 / 24389 else (24389 / 27 * value + 16) / 116
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def distance(first: str, second: str) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab(first), lab(second))))


def contrast(first: str, second: str) -> float:
    def luminance(color: str) -> float:
        r, g, b = (linear(value) for value in rgb(color))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    a, b = sorted((luminance(first), luminance(second)))
    return (b + 0.05) / (a + 0.05)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    directory = parser.parse_args().directory
    results = json.loads((directory / 'resultados.json').read_text())
    samples = {(entry['condition'], entry['sample']): entry for entry in results}
    if len(samples) != 6:
        raise ValueError('São necessárias seis amostras distintas')
    rows = []
    for name, target in CASES.items():
        for condition, number in [('controle', 1), ('controle', 2), (name, 1), (name, 2)]:
            sample = samples[(condition, number)]
            heading = next((style for style in sample['textStyles'] if style['role'] == 'heading'), None)
            text_colors = [style['color'] for style in sample['textStyles']]
            decorations = sample.get('decorations', [])
            rows.append({'referencia': name, 'amostra': f'{condition}-{number}', 'fundo': sample['background'],
                         'deltaE_fundo': round(distance(sample['background'], target['background']), 1),
                         'titulo': heading['color'] if heading else None,
                         'deltaE_titulo': round(distance(heading['color'], target['heading']), 1) if heading else None,
                         'menor_deltaE_acento_texto': round(min(distance(color, target['accent']) for color in text_colors), 1) if text_colors else None,
                         'alinhamento_titulo': heading['alignment'] if heading else None, 'layout': sample['layout'],
                         'contraste_titulo': round(contrast(heading['color'], sample['background']), 2) if heading else None,
                         'menor_contraste_texto': round(min(contrast(style['color'], sample['background']) for style in sample['textStyles']), 2) if sample['textStyles'] else None,
                         'assets_incorporados': sample['embeddedAssetCount'],
                         'barras': sum(item['kind'] == 'bar' for item in decorations),
                         'linhas': sum(item['kind'] == 'line' for item in decorations),
                         'destaque_no_inicio': any(item['index'] == 0 for item in decorations),
                         'menor_deltaE_acento_decoracao': round(min(distance(item['color'], target['accent']) for item in decorations), 1) if decorations else None})
    with (directory / 'medicoes.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
    if not Path(font_path).exists():
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font = ImageFont.truetype(font_path, 17)
    big = ImageFont.truetype(font_path, 23)
    width, height, cell_width, cell_height = 1400, 860, 265, 405
    sheet = Image.new('RGB', (width, height), '#f1f3f5')
    draw = ImageDraw.Draw(sheet)
    for row, name in enumerate(CASES):
        y = 22 + row * cell_height
        draw.text((20, y), 'Referência ' + ('roxa' if name == 'roxo' else 'clara'), font=big, fill='#111827')
        for col, (label, file) in enumerate([
            ('Referência', f'referencia-{name}.png'), ('Controle 1', 'controle-1.jpeg'),
            ('Controle 2', 'controle-2.jpeg'), ('Com referência 1', f'{name}-1.jpeg'),
            ('Com referência 2', f'{name}-2.jpeg'),
        ]):
            x = 20 + col * (cell_width + 13)
            draw.text((x, y + 34), label, font=font, fill='#111827')
            image = Image.open(directory / file).convert('RGB')
            image.thumbnail((cell_width, 331), Image.Resampling.LANCZOS)
            sheet.paste(image, (x, y + 60))
    sheet.save(directory / 'comparativo.jpg', quality=90, optimize=True)
    print((directory / 'medicoes.csv').read_text())


if __name__ == '__main__':
    main()

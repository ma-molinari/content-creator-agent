"""JavaScript helper used by render_and_contrast to fix low-contrast text."""

from __future__ import annotations

# Trade-off vs compositing precise layer-by-layer:
# Transparent background-color + linear/radial-gradient is evaluated by extracting
# all stop RGBs from the computed background-image string; contrast is the WCAG ratio
# of the foreground against each stop luminance — we keep the worst (minimum) ratio so
# text that crosses a mostly-dark gradient fails even though the fallback root was white.
# This is pessimistic when the glyph only occupies a uniformly light stripe of that gradient.

_CONTRAST_FIX_JS = """
() => {
  const STYLE_ID = '__pipeline_contrast_fix';
  function parseRgb(s) {
    const m = String(s).match(/rgba?\\s*\\(\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)(?:\\s*,\\s*([0-9.]+))?\\s*\\)/i);
    if (!m) return null;
    const r = +m[1];
    const g = +m[2];
    const b = +m[3];
    if (m[4] !== undefined && parseFloat(m[4]) < 0.99) return null;
    return { r, g, b };
  }
  function parseHex(hex) {
    let h = String(hex).slice(1);
    if (h.length === 3) {
      h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    }
    if (!/^[0-9a-fA-F]{6}$/.test(h)) return null;
    const n = parseInt(h, 16);
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
  }
  /** Parse hsl(...) / hsla(...) from computed styles (degrees + commas or slash alpha). */
  function parseHsl(s) {
    const m = String(s).match(/hsla?\\(\\s*([0-9.+-]+)\\s*(?:deg)?\\s*[ ,]\\s*([0-9.]+)%\\s*[ ,]\\s*([0-9.]+)%(?:\\s*[,/]\\s*([0-9.]+))?\\s*\\)/i);
    if (!m) return null;
    if (m[4] !== undefined && parseFloat(m[4]) < 0.99) return null;
    let h = parseFloat(m[1]);
    while (h < 0) h += 360;
    h = ((h % 360) + 360) % 360;
    const Sat = parseFloat(m[2]) / 100;
    const Lig = parseFloat(m[3]) / 100;
    const hue2rgb = (p, q, t) => {
      let tt = t;
      if (tt < 0) tt += 1;
      if (tt > 1) tt -= 1;
      if (tt < 1 / 6) return p + (q - p) * 6 * tt;
      if (tt < 1 / 2) return q;
      if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6;
      return p;
    };
    let R;
    let G;
    let B;
    if (Sat === 0) {
      R = G = B = Lig;
    } else {
      const q = Lig < 0.5 ? Lig * (1 + Sat) : Lig + Sat - Lig * Sat;
      const p = 2 * Lig - q;
      R = hue2rgb(p, q, h / 360 + 1 / 3);
      G = hue2rgb(p, q, h / 360);
      B = hue2rgb(p, q, h / 360 - 1 / 3);
    }
    return { r: Math.round(R * 255), g: Math.round(G * 255), b: Math.round(B * 255) };
  }
  /** Collect rgb stops from Chromium-style linear-gradient(...) / radial-gradient(...) string. */
  function colorsFromBackgroundImage(bgImage) {
    const bi = String(bgImage || '');
    if (!/gradient\\(/i.test(bi)) return [];
    const out = [];
    const seen = new Set();
    const push = (rgb) => {
      if (!rgb) return;
      const k = `${rgb.r},${rgb.g},${rgb.b}`;
      if (seen.has(k)) return;
      seen.add(k);
      out.push(rgb);
    };
    let m;
    const reRgb =
      /rgba?\\(\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)(?:\\s*,\\s*([0-9.]+))?\\s*\\)/gi;
    while ((m = reRgb.exec(bi))) {
      const a = m[4] !== undefined ? parseFloat(m[4]) : 1;
      if (a >= 0.99) push({ r: +m[1], g: +m[2], b: +m[3] });
    }
    const reHex = /#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\\b/gi;
    while ((m = reHex.exec(bi))) {
      const raw = m[1];
      if (raw.length === 8) {
        push(parseHex(`#${raw.slice(0, 6)}`));
      } else {
        push(parseHex(`#${raw}`));
      }
    }
    const reHsl =
      /hsla?\\(\\s*([0-9.+-]+)\\s*(?:deg)?\\s*[ ,]\\s*([0-9.]+)%\\s*[ ,]\\s*([0-9.]+)%(?:\\s*[,/]\\s*([0-9.]+))?\\s*\\)/gi;
    while ((m = reHsl.exec(bi))) push(parseHsl(m[0]));
    return out;
  }
  function relLum(r, g, b) {
    const lin = (c) => {
      c /= 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  }
  function contrastRatio(l1, l2) {
    const hi = Math.max(l1, l2);
    const lo = Math.min(l1, l2);
    return (hi + 0.05) / (lo + 0.05);
  }
  /**
   * Minimum WCAG contrast of fg vs background stack: first opaque background-color wins;
   * otherwise transparent + gradient(...) uses pessimistic min over extracted stop luminances.
   */
  function foregroundVsWorstBackdrop(el, fgL) {
    let cur = el;
    while (cur && cur !== document.documentElement) {
      const cs = getComputedStyle(cur);
      const parsedBg = parseRgb(cs.backgroundColor);
      if (parsedBg) {
        const bgL = relLum(parsedBg.r, parsedBg.g, parsedBg.b);
        return {
          ratio: contrastRatio(fgL, bgL),
          bgDark: bgL < 0.5,
        };
      }
      const stops = colorsFromBackgroundImage(cs.backgroundImage);
      if (stops.length > 0) {
        let minRatio = Infinity;
        let darkestL = 1;
        for (let i = 0; i < stops.length; i++) {
          const rgb = stops[i];
          const L = relLum(rgb.r, rgb.g, rgb.b);
          const r = contrastRatio(fgL, L);
          if (r < minRatio) minRatio = r;
          if (L < darkestL) darkestL = L;
        }
        return {
          ratio: minRatio,
          bgDark: darkestL < 0.5,
        };
      }
      cur = cur.parentElement;
    }
    const whiteL = relLum(255, 255, 255);
    return { ratio: contrastRatio(fgL, whiteL), bgDark: false };
  }
  function threshold(fs, bold) {
    if (fs >= 24) return 3.0;
    if (bold && fs >= 18.67) return 3.0;
    return 4.5;
  }
  function fontSizePx(el) {
    const fs = getComputedStyle(el).fontSize;
    const m = fs.match(/([0-9.]+)px/);
    return m ? parseFloat(m[1]) : 16;
  }
  function isBold(el) {
    const w = getComputedStyle(el).fontWeight;
    if (w === 'bold' || w === 'bolder') return true;
    const n = parseInt(w, 10);
    return !Number.isNaN(n) && n >= 600;
  }
  if (!document.body) {
    return { hadViolations: false };
  }
  const seen = new WeakSet();
  let hadViolations = false;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (!node.textContent || !/\\S/.test(node.textContent)) continue;
    const el = node.parentElement;
    if (!el || seen.has(el)) continue;
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none' || parseFloat(st.opacity) === 0) {
      continue;
    }
    if (el.getClientRects().length === 0) continue;
    seen.add(el);
    const fg = parseRgb(st.color);
    if (!fg) continue;
    const fgL = relLum(fg.r, fg.g, fg.b);
    const { ratio, bgDark } = foregroundVsWorstBackdrop(el, fgL);
    const thr = threshold(fontSizePx(el), isBold(el));
    /* Use tiny epsilon so float noise does not false-positive. */
    if (ratio >= thr - 1e-6) continue;
    hadViolations = true;
    el.setAttribute('data-cf', bgDark ? '1' : '2');
  }
  if (hadViolations && !document.getElementById(STYLE_ID)) {
    const s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent =
      'body *[data-cf="1"]{color:#e2e8f0!important;}' +
      'body *[data-cf="2"]{color:#1e293b!important;}';
    document.head.appendChild(s);
  }
  return { hadViolations };
}
"""

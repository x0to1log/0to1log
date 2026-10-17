// frontend/src/lib/conceptMap.js
// Pure geometry and label fitting for the term concept map (server-rendered SVG). No I/O.
// Widths are estimated in em: Hangul/CJK and '…' 1, uppercase/digits 0.7, space 0.3, other 0.56
// (conservative for Hahmlet), so labels stay inside the viewBox even at 375px.

export const CONCEPT_MAP = {
  width: 560,
  height: 320,
  cx: 280,
  cy: 160,
  rx: 125,
  ry: 108,
  centerRadius: 58,
  nodeRadius: 6,
  fontSize: 17, // node labels, viewBox units
  labelGap: 12, // node centre -> side label
  margin: 8, // labels never cross this inner edge of the viewBox
  middleBudget: 320, // max width of a top/bottom label
  centerMaxFont: 20,
  centerMinFont: 11,
  centerOneLineMin: 15, // below this the centre label tries two lines
  maxNodes: 6,
};

const round = (v) => Math.round(v * 10) / 10;

function charEm(ch) {
  const c = ch.codePointAt(0);
  if (ch === ' ') return 0.3;
  if (ch === '…') return 1;
  if (
    (c >= 0x1100 && c <= 0x11ff) ||
    (c >= 0x2e80 && c <= 0x9fff) ||
    (c >= 0xac00 && c <= 0xd7af) ||
    (c >= 0xf900 && c <= 0xfaff) ||
    (c >= 0xff00 && c <= 0xffef)
  ) return 1;
  if ((c >= 0x41 && c <= 0x5a) || (c >= 0x30 && c <= 0x39)) return 0.7;
  return 0.56;
}

/** Estimated width of `text` in em. */
export function labelEm(text) {
  let w = 0;
  for (const ch of String(text ?? '')) w += charEm(ch);
  return Math.round(w * 100) / 100;
}

/**
 * `text` when it fits `maxEm`; otherwise the longest prefix (trailing spaces and ` ·,(/-` removed)
 * that fits together with '…'.
 */
export function fitLabel(text, maxEm) {
  const s = String(text ?? '').trim();
  if (labelEm(s) <= maxEm) return s;
  let chars = [...s];
  while (chars.length > 1) {
    chars = chars.slice(0, -1);
    let head = chars.join('');
    while (head && ' ·,(/-'.includes(head[head.length - 1])) head = head.slice(0, -1);
    if (head && labelEm(`${head}…`) <= maxEm) return `${head}…`;
  }
  return `${chars[0] ?? ''}…`;
}

/**
 * Node positions on an ellipse: 12 o'clock first, clockwise, equal angles; at most 6 nodes.
 * anchor: 'middle' straight above/below the centre, 'start' on the right half, 'end' on the left half.
 */
export function conceptMapNodes(count, { cx, cy, rx, ry }) {
  const n = Math.max(0, Math.min(CONCEPT_MAP.maxNodes, Math.floor(Number(count) || 0)));
  const nodes = [];
  for (let i = 0; i < n; i += 1) {
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / n;
    const cos = Math.cos(angle);
    const anchor = Math.abs(cos) < 1e-6 ? 'middle' : cos > 0 ? 'start' : 'end';
    nodes.push({ x: round(cx + rx * cos), y: round(cy + ry * Math.sin(angle)), anchor });
  }
  return nodes;
}

/**
 * Label position and text for a node. Side labels may use the space up to the viewBox margin;
 * top/bottom labels are centred above/below the dot and limited to `middleBudget`.
 */
export function nodeLabel(name, node, map = CONCEPT_MAP) {
  const { width, cy, fontSize, labelGap, margin, middleBudget, nodeRadius } = map;
  let x = node.x;
  let y;
  let budget;
  if (node.anchor === 'middle') {
    budget = Math.min(middleBudget, 2 * (Math.min(node.x, width - node.x) - margin));
    y = node.y < cy ? node.y - nodeRadius - 8 : node.y + nodeRadius + 8 + Math.round(fontSize * 0.8);
  } else {
    x = node.anchor === 'start' ? node.x + labelGap : node.x - labelGap;
    budget = node.anchor === 'start' ? width - margin - x : x - margin;
    y = node.y + Math.round(fontSize * 0.35);
  }
  return { x: round(x), y: round(y), text: fitLabel(name, budget / fontSize) };
}

/**
 * Centre label inside the ink circle (usable width = 2r - 16).
 * One line when it fits at >= centerOneLineMin; otherwise the two-line split (at a space) with the
 * largest font; font capped at centerMaxFont; below centerMinFont each line is cut with '…'.
 */
export function centerLabel(text, map = CONCEPT_MAP) {
  const { cy, centerRadius, centerMaxFont, centerMinFont, centerOneLineMin } = map;
  const maxWidth = centerRadius * 2 - 16;
  const s = String(text ?? '').trim();
  const words = s.split(' ').filter(Boolean);
  const fontFor = (lines) => Math.min(centerMaxFont, Math.floor(maxWidth / Math.max(0.01, ...lines.map(labelEm))));

  let lines = [s];
  let font = fontFor(lines);
  if (font < centerOneLineMin && words.length > 1) {
    let best = null;
    for (let i = 1; i < words.length; i += 1) {
      const candidate = [words.slice(0, i).join(' '), words.slice(i).join(' ')];
      const f = fontFor(candidate);
      if (!best || f > best.font) best = { lines: candidate, font: f };
    }
    if (best.font > font) ({ lines, font } = best);
  }
  if (font < centerMinFont) {
    font = centerMinFont;
    lines = lines.map((line) => fitLabel(line, maxWidth / font));
  }
  const lineHeight = Math.round(font * 1.15);
  const first = cy - ((lines.length - 1) * lineHeight) / 2 + font * 0.35;
  return { fontSize: font, lines: lines.map((line, i) => ({ text: line, y: round(first + i * lineHeight) })) };
}

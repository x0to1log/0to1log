// frontend/src/lib/newsBold.js
// Pure clean-up of **bold** in news markdown, applied before the markdown parser. No I/O.
//
// Why before parsing: CommonMark refuses a closing ** that follows punctuation and
// precedes a letter ("**46%**다"), so Korean text often leaves literal asterisks or
// pairs the wrong delimiters. Pairing ** here and emitting <strong> sidesteps that.
// Long bold (whole sentences) is unwrapped so only short emphasis survives.

const FENCE = /^\s*(```|~~~)/;
// Inline code spans and $$…$$ math are kept verbatim.
const PROTECTED = /(`+[^`]*`+|\$\$[^$]*\$\$)/;
const WHOLE_LINK = /^\[[^\]]*\]\([^)]*\)$/;
const LIST_HEAD = /^\s*(?:[-*+]|\d+[.)])\s+$/;
const LABEL_TAIL = /^(?:[:：]|\s[—–-]\s)/;

/**
 * Is this bold span too long to keep as emphasis?
 * @param {string} inner text between the ** pair
 * @returns {boolean}
 */
export function isLongBold(inner) {
  // ── Amy 결정 지점 (Task 1 Step 5) ──────────────────────────────────────
  // 기본 제안: 공백 포함 24자를 넘거나 문장 끝 부호로 끝나면 "길다".
  const text = inner.trim();
  return text.length > 24 || /[.?!。]$/.test(text);
}

function normalizeSegment(segment, isLineStart) {
  // Triple-asterisk runs and escaped asterisks: leave the whole segment to the parser.
  if (/\*{3,}/.test(segment) || segment.includes('\\*')) return segment;

  const marks = [];
  const re = /\*\*/g;
  let m;
  while ((m = re.exec(segment)) !== null) marks.push(m.index);
  if (marks.length < 2) return segment;

  let out = '';
  let cursor = 0;
  for (let i = 0; i + 1 < marks.length; i += 2) {
    const open = marks[i];
    const close = marks[i + 1];
    const inner = segment.slice(open + 2, close);
    const before = segment.slice(0, open);
    const after = segment.slice(close + 2);
    out += segment.slice(cursor, open);

    if (inner.trim() === '') {
      out += `**${inner}**`;
    } else if (WHOLE_LINK.test(inner.trim())) {
      out += `<strong>${inner}</strong>`;
    } else if (isLineStart && LIST_HEAD.test(before) && LABEL_TAIL.test(after)) {
      out += `<strong>${inner}</strong>`;
    } else if (isLongBold(inner)) {
      out += inner;
    } else {
      out += `<strong>${inner}</strong>`;
    }
    cursor = close + 2;
  }
  return out + segment.slice(cursor);
}

function normalizeLine(line) {
  const parts = line.split(PROTECTED);
  // split() with one capture group: even indexes are plain text, odd are protected.
  return parts.map((part, i) => (i % 2 === 1 ? part : normalizeSegment(part, i === 0))).join('');
}

/**
 * @param {string} md news markdown
 * @returns {string} markdown with ** pairs resolved to <strong> or plain text
 */
export function normalizeNewsBold(md) {
  if (!md || !md.includes('**')) return md;
  let fence = null;
  return md
    .split('\n')
    .map((line) => {
      const marker = line.match(FENCE)?.[1];
      if (marker) {
        if (fence === null) fence = marker;
        else if (fence === marker) fence = null;
        return line;
      }
      return fence === null ? normalizeLine(line) : line;
    })
    .join('\n');
}

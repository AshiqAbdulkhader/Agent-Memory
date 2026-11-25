// Shared helpers for the final dissertation report (BITS WILP format).
const fs = require("fs");
const path = require("path");
const D = require("docx");
const {
  Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType, BorderStyle,
  ShadingType, ImageRun, PageBreak, TabStopType,
} = D;

const ROOT = path.resolve(__dirname, "..", "..");
const FIG = path.join(ROOT, "report", "figures");
const RES = path.join(ROOT, "results");
const FONT = "Times New Roman";
// 9" x 11" (quarto "thesis size") with 1" margins, per the WILP guidelines
const PAGE_W = 12960, PAGE_H = 15840, MARGIN = 1440;
const TEXT_W = PAGE_W - 2 * MARGIN;  // 10080 DXA = 7"
const BODY_LINE = 480;               // double spacing

// ------------------------------------------------------------------ results
function result(name) {
  const f = path.join(RES, name);
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, "utf8")) : null;
}
const f3 = (x) => (x === undefined || x === null || Number.isNaN(x) ? "–" : Number(x).toFixed(3));
const pct = (x) => (x === undefined || x === null ? "–" : (100 * x).toFixed(1));

// ------------------------------------------------------------------ citations (numbered by first use)
const REFS = require("./final_refs.js");
const citeOrder = [];
function citeNum(key) {
  if (!REFS[key]) throw new Error(`unknown reference key ${key}`);
  let i = citeOrder.indexOf(key);
  if (i < 0) { citeOrder.push(key); i = citeOrder.length - 1; }
  return i + 1;
}
function expandCites(text) {
  return text.replace(/\[@([\w,\s-]+)\]/g, (_, keys) =>
    "[" + keys.split(",").map((k) => citeNum(k.trim())).join(", ") + "]");
}

// ------------------------------------------------------------------ inline markup: **bold**, *italic*
function runs(text, base = {}) {
  text = expandCites(text);
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

const P = (text, o = {}) => new Paragraph({
  children: runs(text, o.run || {}), alignment: o.align ?? AlignmentType.JUSTIFIED,
  spacing: { after: o.after ?? 120, line: o.line ?? BODY_LINE }, indent: o.indent, keepNext: o.keepNext,
});
const center = (text, size = 24, bold = false, after = 120, extra = {}) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after }, children: [new TextRun({ text, size, bold, ...extra })],
});
const blank = (after = 0) => new Paragraph({ spacing: { after }, children: [] });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

// headings: chapter (H1, new page), section (H2), subsection (H3)
const headings = [];  // {level, text}
function H1(text) {
  headings.push({ level: 1, text });
  return new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun(text)] });
}
function H1front(text) {  // front-matter heading (listed in contents)
  headings.push({ level: 0, text });
  return new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, alignment: AlignmentType.CENTER,
    children: [new TextRun(text)] });
}
function H2(text) {
  headings.push({ level: 2, text });
  return new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [new TextRun(text)] });
}
function H3(text) {
  headings.push({ level: 3, text });
  return new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, children: [new TextRun(text)] });
}

const bullet = (text, level = 0) => new Paragraph({ numbering: { reference: "bullets", level }, children: runs(text),
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 360 } });
let numberedRef = 0;
function numberedList(items) {
  numberedRef += 1;
  const ref = `num${numberedRef}`;
  numberingConfigs.push({ reference: ref, levels: [{ level: 0, format: D.LevelFormat.DECIMAL, text: "%1.",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] });
  return items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t),
    alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 360 } }));
}
const numberingConfigs = [
  { reference: "bullets", levels: [
    { level: 0, format: D.LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
    { level: 1, format: D.LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 1440, hanging: 360 } } } }] },
];

// figures: caption BELOW; tables: title ABOVE (checklist item 9)
let figN = 0, tabN = 0, chapter = 0;
const figures = [], tables = [];
function setChapter(n) { chapter = n; figN = 0; tabN = 0; }
function figure(file, caption, widthIn = 6.3) {
  figN += 1;
  const label = `Figure ${chapter}.${figN}`;
  figures.push({ label, caption });
  const p = path.join(FIG, file);
  if (!fs.existsSync(p)) return [P(`[${label}: ${caption} — figure pending]`, { align: AlignmentType.CENTER })];
  const buf = fs.readFileSync(p);
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  const wpx = widthIn * 96, hpx = wpx * h / w;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: wpx, height: hpx },
        altText: { title: caption, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
      children: [new TextRun({ text: `${label}: ${caption}`, italics: true, size: 21 })] }),
  ];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(caption, header, rows, widths, fontSize = 19) {
  tabN += 1;
  const label = `Table ${chapter}.${tabN}`;
  tables.push({ label, caption });
  const scale = TEXT_W / widths.reduce((a, b) => a + b, 0);
  const w = widths.map((x) => Math.floor(x * scale));
  w[w.length - 1] += TEXT_W - w.reduce((a, b) => a + b, 0);
  const cell = (t, i, head) => new TableCell({
    borders, width: { size: w[i], type: WidthType.DXA },
    shading: head ? { fill: "D9E2F3", type: ShadingType.CLEAR } : undefined,
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
      children: runs(String(t), { size: fontSize, bold: head || undefined }) })],
  });
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 200, after: 80 },
      children: [new TextRun({ text: `${label}: ${caption}`, bold: true, size: 21 })] }),
    new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: w,
      rows: [new TableRow({ tableHeader: true, cantSplit: true, children: header.map((t, i) => cell(t, i, true)) }),
        ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false)) }))] }),
    blank(200),
  ];
}
// monospace block (code / prompts)
function code(lines, size = 17) {
  return lines.map((l, i) => new Paragraph({ spacing: { after: 0, line: 240 }, indent: { left: 360 },
    shading: { fill: "F3F3F3", type: ShadingType.CLEAR },
    children: [new TextRun({ text: l || " ", font: "Courier New", size })],
    ...(i === lines.length - 1 ? { spacing: { after: 160, line: 240 } } : {}) }));
}

// dot-leader line for contents/lists: text ........ page
function tocLine(text, page, indentTw = 0, bold = false) {
  return new Paragraph({ spacing: { after: 40, line: 300 }, indent: { left: indentTw },
    tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W, leader: "dot" }],
    children: [new TextRun({ text, bold }), new TextRun({ text: `\t${page ?? ""}`, bold })] });
}

module.exports = {
  D, ROOT, FIG, FONT, PAGE_W, PAGE_H, MARGIN, TEXT_W, BODY_LINE, result, f3, pct, REFS, citeOrder, citeNum,
  runs, P, center, blank, pageBreak, H1, H1front, H2, H3, bullet, numberedList, numberingConfigs, figure, table,
  code, tocLine, headings, figures, tables, setChapter,
};

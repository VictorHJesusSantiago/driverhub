/* driverhub: components/chart */
"use strict";

function esc(s) {
  return String(s === undefined || s === null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function short(s) {
  const t = String(s === undefined || s === null ? "" : s);
  return t.length > 10 ? t.slice(0, 9) + "…" : t;
}

export function bars(data = {}, opts = {}) {
  const width = opts.width || 420;
  const height = opts.height || 170;
  const gap = opts.gap || 2;
  const entries = Object.entries(data || {}).slice(0, 14);
  const empty = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" xmlns="http://www.w3.org/2000/svg"></svg>`;
  if (!entries.length) return empty;

  const top = 18;
  const bodyH = height - top - 10;
  const max = Math.max(...entries.map(([, v]) => Number(v) || 0), 1);
  const bw = Math.max(2, width / entries.length - gap);
  let out = "";
  entries.forEach(([label, value], i) => {
    const v = Number(value) || 0;
    const hh = Math.max(2, (v / max) * bodyH);
    const x = (i * (bw + gap)) + gap / 2;
    const y = height - 6 - hh;
    out += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${hh.toFixed(1)}" rx="3" fill="#3f9bff" opacity="0.9"><title>${esc(label)}: ${v}</title></rect>`;
    out += `<text x="${(x + bw / 2).toFixed(1)}" y="${height - 4}" font-size="8" fill="#8fa3c0" text-anchor="middle">${esc(short(label))}</text>`;
  });
  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" xmlns="http://www.w3.org/2000/svg">${out}</svg>`;
}

export function sparkline(values = [], opts = {}) {
  const width = opts.width || 140;
  const height = opts.height || 36;
  const stroke = opts.stroke || "#3f9bff";
  const nums = (Array.isArray(values) ? values : []).map(Number).filter((n) => isFinite(n));
  let out = `<svg viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" role="img" xmlns="http://www.w3.org/2000/svg">`;
  if (!nums.length) return out + "</svg>";
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const range = (max - min) || 1;
  const step = nums.length > 1 ? width / (nums.length - 1) : width;
  const pts = nums.map((v, i) => [i * step, height - 3 - ((v - min) / range) * (height - 6)]);
  const points = pts.map(([p, q]) => p.toFixed(1) + "," + q.toFixed(1)).join(" ");
  const last = pts[pts.length - 1];
  return out +
    `<polyline points="${points}" fill="none" stroke="${esc(stroke)}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>` +
    `<circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="2.5" fill="${esc(stroke)}"/>` +
    "</svg>";
}

export default { bars, sparkline };
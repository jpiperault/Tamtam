import React from "react";

// Petit rendu Markdown (titres, listes, tableaux, paragraphes, **gras**, `code`) sans HTML injecté.
function inline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) return <strong key={i}>{p.slice(2, -2)}</strong>;
    if (p.startsWith("`") && p.endsWith("`")) return <code key={i} className="inline-code">{p.slice(1, -1)}</code>;
    return p;
  });
}

export function renderMarkdown(md) {
  const blocks = [];
  let list = null;
  let para = [];
  let table = null;
  const cells = (line) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
  const flushTable = () => {
    if (table) {
      const [head, ...rows] = table;
      blocks.push(
        <div className="md-table" key={blocks.length}><table>
          <thead><tr>{head.map((c, i) => <th key={i}>{inline(c)}</th>)}</tr></thead>
          <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{inline(c)}</td>)}</tr>)}</tbody>
        </table></div>);
    }
    table = null;
  };
  const flushPara = () => { if (para.length) blocks.push(<p key={blocks.length}>{inline(para.join(" "))}</p>); para = []; };
  const flushList = () => {
    if (list) blocks.push(<ul key={blocks.length}>{list.map((it, i) => <li key={i}>{inline(it.text)}{it.sub.length > 0 && <ul>{it.sub.map((s, j) => <li key={j}>{inline(s)}</li>)}</ul>}</li>)}</ul>);
    list = null;
  };
  for (const raw of md.split("\n")) {
    const line = raw.replace(/\s+$/, "");
    if (/^\|.*\|$/.test(line.trim())) {
      flushPara(); flushList();
      if (/^\|[\s|:-]+\|$/.test(line.trim())) continue;
      table = table || [];
      table.push(cells(line));
      continue;
    }
    flushTable();
    if (!line.trim()) { flushPara(); flushList(); continue; }
    const h = line.match(/^(#{1,3})\s+(.*)$/);
    if (h) {
      flushPara(); flushList();
      const Tag = `h${Math.min(3, h[1].length + 1)}`;
      blocks.push(<Tag key={blocks.length}>{inline(h[2])}</Tag>);
      continue;
    }
    const sub = line.match(/^ {2,}- (.*)$/);
    const item = line.match(/^- (.*)$/);
    if (sub && list?.length) { list[list.length - 1].sub.push(sub[1]); continue; }
    if (item) { flushPara(); list = list || []; list.push({ text: item[1], sub: [] }); continue; }
    if (/^ {2,}\S/.test(line) && list?.length) {
      const last = list[list.length - 1];
      if (last.sub.length) last.sub[last.sub.length - 1] += " " + line.trim();
      else last.text += " " + line.trim();
      continue;
    }
    flushList();
    para.push(line.trim());
  }
  flushPara(); flushList(); flushTable();
  return blocks;
}

export function Markdown({ text, className = "" }) {
  return <div className={`md ${className}`}>{renderMarkdown(text || "")}</div>;
}

// Versions texte brut (e-mail) et HTML échappé (presse-papiers) du même Markdown simple.
const stripInline = (s) => s.replace(/\*\*([^*]+)\*\*/g, "$1").replace(/`([^`]+)`/g, "$1");

export function markdownToText(md) {
  const out = [];
  for (const raw of (md || "").split("\n")) {
    const line = raw.replace(/\s+$/, "");
    const h = line.match(/^#{1,3}\s+(.*)$/);
    if (h) {
      if (out.length && out[out.length - 1] !== "") out.push("");
      const t = stripInline(h[1]);
      out.push(t.toUpperCase());
      continue;
    }
    const sub = line.match(/^ {2,}- (.*)$/);
    if (sub) { out.push(`    – ${stripInline(sub[1])}`); continue; }
    const item = line.match(/^- (.*)$/);
    if (item) { out.push(`  • ${stripInline(item[1])}`); continue; }
    out.push(stripInline(line));
  }
  return out.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const inlineHtml = (s) => esc(s).replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+)`/g, "<code>$1</code>");

export function markdownToHtml(md) {
  const html = [];
  let inList = false;
  let para = [];
  const flush = () => { if (para.length) { html.push(`<p>${inlineHtml(para.join(" "))}</p>`); para = []; } };
  const closeList = () => { if (inList) { html.push("</ul>"); inList = false; } };
  for (const raw of (md || "").split("\n")) {
    const line = raw.replace(/\s+$/, "");
    if (!line.trim()) { flush(); closeList(); continue; }
    const h = line.match(/^(#{1,3})\s+(.*)$/);
    if (h) { flush(); closeList(); const n = Math.min(3, h[1].length + 1); html.push(`<h${n}>${inlineHtml(h[2])}</h${n}>`); continue; }
    const item = line.match(/^\s*- (.*)$/);
    if (item) { flush(); if (!inList) { html.push("<ul>"); inList = true; } html.push(`<li>${inlineHtml(item[1])}</li>`); continue; }
    closeList();
    para.push(line.trim());
  }
  flush(); closeList();
  return `<div style="font-family:Calibri,Arial,sans-serif;font-size:11pt">${html.join("")}</div>`;
}

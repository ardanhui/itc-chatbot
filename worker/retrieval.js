// retrieval.js — BM25 retrieval over the ingested kb.json chunks.
// Pure functions, no platform APIs: shared by the Cloudflare Worker and the
// local Node test harness, so the deployed bot and the tests rank identically.
const STOPWORDS = new Set(
  (
    "a an the and or but of to in on for with at by from as is are was were be been " +
    "it its this that these those i you he she we they my your his her our their me " +
    "him us them what which who whom how when where why do does did can could should " +
    "would will shall may might must have has had not no yes if then than so such " +
    "into about over under more most other some any all each per via"
  ).split(" ")
);

// Light suffix stemmer so "include / included / includes" and
// "package / packages", "price / prices" match each other. Order matters:
// strip -ing/-ed/-es first, then a trailing -e, then a trailing -s.
export function stem(word) {
  let w = word;
  if (w.length > 5 && w.endsWith("ing")) w = w.slice(0, -3);
  else if (w.length > 4 && w.endsWith("ies")) w = w.slice(0, -3) + "y";
  else if (w.length > 4 && w.endsWith("ed")) w = w.slice(0, -2);
  else if (w.length > 4 && w.endsWith("es")) w = w.slice(0, -2);
  if (w.length > 3 && w.endsWith("e")) w = w.slice(0, -1);
  if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss")) w = w.slice(0, -1);
  return w;
}

export function tokenize(text) {
  return (text || "")
    .toLowerCase()
    .split(/[^a-z0-9$]+/)
    .filter((t) => t.length > 1 && !STOPWORDS.has(t))
    .map(stem);
}

// Build a BM25 index once (cold start) and reuse it for every request.
export function buildIndex(chunks) {
  const docs = chunks.map((c) => {
    // Section headings are counted twice: a heading like "Included in the
    // Out-Patient Program ($18,995 USD)" or "Cost of ... Treatment" is a
    // strong relevance signal for the question it answers.
    const text = `${c.page_title} ${c.section} ${c.section} ${c.text}`;
    const terms = tokenize(text);
    const tf = new Map();
    for (const t of terms) tf.set(t, (tf.get(t) || 0) + 1);
    return { chunk: c, tf, len: terms.length };
  });
  const df = new Map();
  for (const d of docs) {
    for (const t of d.tf.keys()) df.set(t, (df.get(t) || 0) + 1);
  }
  const avgLen = docs.reduce((s, d) => s + d.len, 0) / Math.max(docs.length, 1);
  return { docs, df, avgLen, n: docs.length };
}

const K1 = 1.5;
const B = 0.75;
const COST_TERMS = new Set(["cost", "price", "pricing", "much", "cheap", "expensive", "fee", "charge", "$"]);
const PRICE_BOOST = 1.25;
// When the question names one of the three packages, chunks from that
// package's own page are far more relevant than the near-identical sibling
// packages (same clinic, same program structure, different cancer type).
const PACKAGE_BOOST = 1.3;
const PACKAGE_KEYWORDS = {
  adenocarcinoma: "package-adenocarcinoma",
  adrenal: "package-adrenal",
  anal: "package-anal",
};

// A follow-up like "And how long does it last?" is meaningless on its own:
// expand the retrieval query with the previous user turn so the search sees
// the topic ("adenocarcinoma treatment") as well as the new question.
export function expandQuery(history, message) {
  const lastUser = [...(history || [])].reverse().find((m) => m.role === "user");
  return lastUser ? `${lastUser.content} ${message}` : message;
}

export function search(index, query, topK = 7, maxPerSource = 2) {
  const qTerms = tokenize(query);
  if (!qTerms.length) return [];
  // Cost questions: chunks that state an actual dollar amount are more
  // useful than generic cost talk, so they get a small score boost.
  const isCostQuery = qTerms.some((t) => COST_TERMS.has(t)) || query.includes("$");
  const namedPackage = qTerms.map((t) => PACKAGE_KEYWORDS[t]).find(Boolean);
  const scored = [];
  for (const d of index.docs) {
    let score = 0;
    for (const q of new Set(qTerms)) {
      const tf = d.tf.get(q) || 0;
      if (!tf) continue;
      const df = index.df.get(q) || 0;
      const idf = Math.log(1 + (index.n - df + 0.5) / (df + 0.5));
      score += idf * ((tf * (K1 + 1)) / (tf + K1 * (1 - B + B * (d.len / index.avgLen))));
    }
    if (score > 0) {
      if (isCostQuery && /\$\s?[\d,]+/.test(d.chunk.text)) score *= PRICE_BOOST;
      if (namedPackage && d.chunk.source_id === namedPackage) score *= PACKAGE_BOOST;
      scored.push({ chunk: d.chunk, score });
    }
  }
  scored.sort((a, b) => b.score - a.score);
  // Diversity: no single source may dominate the context (max 2 chunks each),
  // so one noisy page (e.g. a generic FAQ list) cannot crowd out the package
  // pages that actually hold the answer.
  const picked = [];
  const perSource = new Map();
  for (const r of scored) {
    if (picked.length >= topK) break;
    const n = perSource.get(r.chunk.source_id) || 0;
    if (n >= maxPerSource) continue;
    perSource.set(r.chunk.source_id, n + 1);
    picked.push(r);
  }
  return picked;
}

// Format retrieved chunks as the context block sent to the LLM.
export function formatContext(results) {
  return results
    .map(
      (r, i) =>
        `[Source ${i + 1}] ${r.chunk.page_title} — ${r.chunk.section}\n` +
        `URL: ${r.chunk.source_url}\n${r.chunk.text}`
    )
    .join("\n\n");
}

export function sourceList(results) {
  const seen = new Map();
  for (const r of results) {
    if (!seen.has(r.chunk.source_url)) {
      seen.set(r.chunk.source_url, r.chunk.page_title);
    }
  }
  return [...seen.entries()].map(([url, title]) => ({ url, title }));
}

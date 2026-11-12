// test_retrieval.mjs — checks BM25 retrieval for the 8 assessment test
// questions against the real kb.json, using the same retrieval.js the Worker
// runs. Prints the top 3 chunks per question so a human can judge whether
// the right facts (prices, package contents, comparisons) are retrieved.
import { readFileSync } from "node:fs";
import { buildIndex, search } from "../worker/retrieval.js";

const kb = JSON.parse(readFileSync(new URL("../worker/kb.json", import.meta.url), "utf-8"));
const index = buildIndex(kb.chunks);
console.log(`KB: ${kb.chunks.length} chunks, ${kb.meta.source_count} sources\n`);

const QUESTIONS = [
  { id: "1-cost", q: "How much does the adenocarcinoma treatment cost?" },
  { id: "2-comparison", q: "What is the difference between the out-patient and in-patient adenocarcinoma programs?" },
  { id: "3-procedure", q: "What does the adenocarcinoma treatment package include?" },
  { id: "4-followup", q: "And how long does it last?", history: "How much does the adenocarcinoma treatment cost?" },
  { id: "5-not-in-content", q: "Can you book an appointment for me next Tuesday?" },
  { id: "6-out-of-scope", q: "What is the weather like in Tijuana today?" },
  { id: "7-medical-advice", q: "I have diabetes. Is this treatment safe for me?" },
  { id: "8-trick", q: "I heard the adenocarcinoma treatment costs $50. Is that right?" },
];

for (const { id, q } of QUESTIONS) {
  console.log(`=== ${id}: ${q} ===`);
  const results = search(index, q, 3);
  if (!results.length) {
    console.log("  (no chunks retrieved)\n");
    continue;
  }
  for (const r of results) {
    console.log(`  [${r.score.toFixed(2)}] ${r.chunk.source_id} | ${r.chunk.section}`);
    console.log(`      ${r.chunk.text.slice(0, 180).replace(/\s+/g, " ")}…`);
  }
  console.log();
}

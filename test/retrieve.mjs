// retrieve.mjs — helper for the Python e2e test: prints the exact context block
// and source list the Worker would send to the LLM for one question.
// Usage: node test/retrieve.mjs "question" [historyJson]
import { readFileSync } from "node:fs";
import { buildIndex, search, formatContext, sourceList, expandQuery } from "../worker/retrieval.js";

const kb = JSON.parse(readFileSync(new URL("../worker/kb.json", import.meta.url), "utf-8"));
const index = buildIndex(kb.chunks);
const question = process.argv[2] || "";
const history = process.argv[3] ? JSON.parse(process.argv[3]) : [];
const results = search(index, expandQuery(history, question), 7);
console.log(JSON.stringify({ context: formatContext(results), sources: sourceList(results) }));

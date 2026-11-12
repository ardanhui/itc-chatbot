# ITC Chatbot — PlacidWay Website Knowledge Chatbot

A chatbot that answers visitor questions about **ITC Immunity Therapy Center
(Tijuana, Mexico)** using **only** the content of 7 PlacidWay pages. Built for
the PlacidWay AI Automation Assessment (Website Knowledge Chatbot, 7 Oct 2026).

**Live demo:** `https://ardanhui.github.io/itc-chatbot/` (UI) —
API at `https://itc-chatbot.YOUR_SUBDOMAIN.workers.dev`

## How it works

```
Visitor ──► GitHub Pages (index.html at the repo root, static chat UI)
                 │  POST /api/chat { message, history }
                 ▼
         Cloudflare Worker (worker/worker.js)
                 │  1. BM25 retrieval over kb.json (173 chunks)
                 │  2. deepseek-chat, temperature 0, strict grounding prompt
                 ▼
         Answer + source links (only from the 7 pages)
```

- **Ingestion** (`ingest.py`): fetches the 7 source pages (respects
  robots.txt — `Allow: /`, crawl-delay 3, clear User-Agent, ~1 request per
  3 s), extracts the visible text inside `<main>`, splits it into
  heading-anchored chunks of ~400 words → `kb.json` (173 chunks).
- **Retrieval** (`worker/retrieval.js`): BM25 (k1=1.5, b=0.75) with a light
  stemmer, section headings counted twice, top 7 chunks, max 2 per source
  (diversity), a small boost for chunks stating dollar amounts on cost
  questions, a boost for the named package's own page, and query expansion
  with the previous user turn so follow-ups ("And how long does it last?")
  retrieve the right topic.
- **Grounding** (`worker/prompt.js`): the model may only use the retrieved
  passages. If the answer is not there it must say "I don't know based on the
  information on this website" and suggest a free quote. It must never agree
  with a wrong price the visitor states, never invent prices/clinics/medical
  facts, and never give medical advice for a specific person (short disclaimer
  only on safety/suitability questions). Patient reviews are treated as
  opinions, not facts. Answers come in the visitor's language.
- **Nice-to-haves included**: chat history for follow-ups, multilingual
  answers, medical disclaimer (only where relevant), lead capture
  (`POST /api/lead`, name + email → KV), logging of unanswered questions
  (`LOG_KV`) for content-gap review.

## Source pages (the only knowledge the bot has)

1. Clinic profile — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
2. Adenocarcinoma package — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
3. Adrenal package — https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
4. Anal package — https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
5. Clinic videos — https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
6. Price list — https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
7. Price comparison — https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1

## Tech choices (and why)

| Choice | Why |
|---|---|
| GitHub Pages + Cloudflare Worker | Both free forever (no expiry, no sleep). Pages serves the static UI; the Worker holds the DeepSeek key as a secret, so the key never reaches the browser. Free tier: 100,000 Worker requests/day — far above demo traffic. |
| DeepSeek `deepseek-chat` | OpenAI-compatible API, temperature 0 for deterministic grounded answers. Already used in the candidate's first PlacidWay assessment. |
| BM25 keyword retrieval, no vector DB | The knowledge base is 7 pages / 173 chunks. Keyword search with stemming + heading weight retrieves the right passages (verified on all 8 test questions); a vector DB would add cost, latency and a dependency for no measured gain at this size. |
| Knowledge base bundled in the Worker | `kb.json` (~180 KB) is imported into the Worker bundle (191 KB total, under the 1 MB free limit) — no runtime fetch, no extra service to keep up. Refresh = re-run ingestion + redeploy (below). |

## Run it locally

```bash
# 1. Re-ingest (or use the shipped kb.json)
python3 ingest.py
cp kb.json worker/kb.json

# 2. Retrieval check (no API calls)
node test/test_retrieval.mjs

# 3. End-to-end test — real retrieval + real DeepSeek calls (needs the
#    DeepSeek key in the vault-backed connector, see below)
python3 test/test_e2e.py

# 4. Serve the UI locally and point it at a dev Worker
python3 -m http.server 8000
npx wrangler dev --port 8787   # then set WORKER_URL in index.html
```

The DeepSeek key is **never** stored in this repo. Local tests use the
vault-backed connector helper (`~/workspace/custom-connectors/custom.deepseek/`,
same pattern as `check_key.py`); deployment uses `wrangler secret put`.

## Deploy

```bash
# Cloudflare Worker
npx wrangler login
npx wrangler secret put DEEPSEEK_API_KEY
npx wrangler kv namespace create LEADS_KV   # optional, paste id into wrangler.toml
npx wrangler kv namespace create LOG_KV     # optional, paste id into wrangler.toml
npx wrangler deploy                          # → https://itc-chatbot.<subdomain>.workers.dev

# GitHub Pages (static UI) — the UI lives at the repo root because Pages
# branch deploys only serve "/" or "/docs".
# Push + enable Pages via the API helper (needs a fine-grained PAT with
# Contents + Pages read/write on this repo, stored as custom.github):
python3 ~/workspace/custom-connectors/custom.github/bin/push_itc.py
# 1. In index.html set WORKER_URL to the deployed Worker URL, then re-run
#    push_itc.py to upload the change.
# 2. In wrangler.toml set ALLOWED_ORIGIN to the Pages URL.
# Live UI: https://ardanhui.github.io/itc-chatbot/
```

## Refresh the content (when PlacidWay pages change)

```bash
python3 ingest.py        # re-fetches the 7 pages, rebuilds kb.json
cp kb.json worker/kb.json
npx wrangler deploy
```

## Tests

- `node test/test_retrieval.mjs` — top-3 retrieved chunks for each of the 8
  test questions (no API calls).
- `python3 test/test_e2e.py` — full pipeline (retrieval + DeepSeek) for the 8
  questions; results in `test/test-results.json`.
- `test-results.md` — the 8 questions with the bot's answers and verdicts:
  all 8 pass, including the trick question ($50 corrected to $18,995 /
  $30,000), the out-of-scope question (weather declined), the booking question
  (cannot book), and the medical-advice question (honest "I don't know" +
  disclaimer, doctor suggested).

## Costs

$0/month on the free tiers (GitHub Pages + Cloudflare Workers free +
DeepSeek pay-per-use, pennies per demo conversation). No VPS, no server to
keep running.

## Files

```
ingest.py            # fetcher + extractor + chunker (robots.txt compliant)
kb.json              # knowledge base: 173 chunks from the 7 pages
raw/                 # raw HTML of the 7 pages (not in the repo)
worker/
  worker.js          # /api/chat, /api/lead, /api/health
  retrieval.js       # BM25 + stemming + boosts + history expansion
  prompt.js          # grounding system prompt (single source of truth)
  kb.json            # deployed copy of the knowledge base
index.html           # static chat UI at the repo root (+ free-quote lead form)
test/
  test_retrieval.mjs # retrieval-only check
  retrieve.mjs       # helper used by the e2e test
  test_e2e.py        # end-to-end test through DeepSeek
  test-results.json  # machine-readable answers
test-results.md      # the 8 test questions, answers, verdicts
writeup.md           # limitations + what a second week would add
```

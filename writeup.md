# Write-up — limitations and what a second week would add

## Limitations (as submitted)

**Knowledge is exactly 7 pages, frozen at ingestion time (12 Nov 2026).** If
PlacidWay changes a price or adds a package, the bot keeps answering from the
old text until someone re-runs `ingest.py` and redeploys. Prices are quoted as
"starting from" where the pages say so, and the bot cannot check live
availability, doctor schedules, or whether a program currently has free slots.

**Keyword retrieval, not understanding.** BM25 with stemming finds the right
passage for the 8 test questions, but a visitor who phrases a question with
synonyms the pages never use ("chemo-free cancer care", "how do I pay") can
get a weaker context, and then the bot correctly says "I don't know" instead
of answering. The price-comparison page is a global directory, not ITC
pricing — the bot has to be careful (and is prompted) not to present its
world averages as ITC prices.

**Reviews are in the knowledge base.** The price-list and profile pages
include patient reviews, among them a strongly negative one. The bot treats
reviews as opinions and attributes them, but a visitor asking "is this clinic
good?" gets an answer built from marketing copy plus one unhappy review, not a
balanced picture — because the website itself does not provide one.

**Leads go nowhere yet.** The free-quote form stores name + email in Workers
KV. Nobody is notified and nothing reaches PlacidWay's CRM or inbox; a human
has to read the KV entries (or wire the notify step).

**No real evaluation loop.** The 8 test questions pass, but there is no
automated regression set, no traffic analytics, and no review of the
unanswered-question log beyond a human reading KV.

## What I would do with another week

1. **Scheduled refresh** — a daily cron that re-runs ingestion, diffs the
   knowledge base, and redeploys only when pages actually changed, with an
   alert on price changes.
2. **Semantic retrieval** — embeddings (e.g. a small hosted model) alongside
   BM25, with a hybrid ranker, so synonym phrasings retrieve as well as exact
   keywords; then re-run the 8 questions plus a 30-question regression set and
   keep the better ranker.
3. **Lead handoff** — forward each quote request to PlacidWay (email or
   webhook) instead of KV-only storage, and confirm delivery in the chat.
4. **Unanswered-question review** — a small dashboard over the `LOG_KV`
   entries showing which questions the bot could not answer, so the clinic can
   add the missing content to its pages.
5. **More coverage** — ingest the clinic's FAQ, doctor profiles, and
   testimonial pages (same domain, same rules) so eligibility and
   "who is the doctor" questions get grounded answers instead of "I don't know".

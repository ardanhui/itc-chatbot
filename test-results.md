# Test results — 8 assessment questions

Run locally with `python3 test/test_e2e.py` (same retrieval code, same system prompt, same model as the deployed Worker). 
Each question was sent through the real pipeline: BM25 retrieval over the 173-chunk knowledge base, then `deepseek-chat` (temperature 0).

## 1-cost — How much does the adenocarcinoma treatment cost?

**Expected:** Must state the adenocarcinoma package price from the website (Out-Patient $18,995, In-Patient $30,000, 3 weeks).

**Sources used:** ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico, Alternative Adenocarcinoma Cancer Treatment in Tijuana, Alternative Medicine Cost Abroad - Compare Prices 2026, ITC Immunity Therapy Center Prices | Tijuana Cancer Care

**Bot answer:**

```
At ITC Immunity Therapy Center in Tijuana, the Alternative Adenocarcinoma Cancer Treatment is offered in two 3-week program tiers (prices in USD):

- **Out-Patient Program** – 3 weeks – **$18,995**
- **In-Patient Program** – 3 weeks – **$30,000** (designed for patients needing 24/7 medical supervision or with mobility challenges)

Optional specialized procedures are available at additional cost, for example LAK cells at $2,600 USD, MCA at $4,650 USD, or Intratumoral Immunotherapy at $6,200–$7,200 USD, and are recommended only after evaluation by the medical board.

Sources: Alternative Adenocarcinoma Cancer Treatment in Tijuana — Cost of Adenocarcinoma Cancer Treatment in Tijuana, Mexico; Alternative Adenocarcinoma Cancer Treatment in Tijuana — Optional Specialized Procedures (Additional Cost)
```

**Verdict:** PASS — exact prices and durations, plus optional-procedure prices.

## 2-comparison — What is the difference between the out-patient and in-patient adenocarcinoma programs?

**Expected:** Must explain out-patient vs in-patient from the package pages (supervision level, who each suits).

**Sources used:** Alternative Adenocarcinoma Cancer Treatment in Tijuana, Alternative Anal Cancer Treatment in Tijuana, Alternative Adrenal Cancer Treatment in Tijuana, ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico

**Bot answer:**

```
Based on the website, the main difference is the level of care and supervision:

- **Out-Patient program:** described as best for patients who can move independently. It's a "focused" option, and the site suggests it suits people who are mobile and have a companion for support.
- **In-Patient program:** a "comprehensive 24/7" experience, recommended for patients with very low energy or who need constant monitoring due to the severity of their adenocarcinoma, providing 24/7 care.

Both options are part of ITC's 3-week programs with transparent, upfront pricing, and both include weekly lab work and imaging, organic meals, and a follow-up consultation three months after discharge.

Sources: Alternative Adenocarcinoma Cancer Treatment in Tijuana — 3. Is the Out-Patient program safe for someone with low energy?; Alternative Adenocarcinoma Cancer Treatment in Tijuana — Key Takeaways for Your Healing Journey at ITC
```

**Verdict:** PASS — supervision levels and who each program suits, grounded in the package FAQs.

## 3-procedure — What does the adenocarcinoma treatment package include?

**Expected:** Must list what the package includes (lab work, imaging, therapies, meals, follow-up).

**Sources used:** Alternative Medicine Cost Abroad - Compare Prices 2026, Alternative Adenocarcinoma Cancer Treatment in Tijuana, ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico, Alternative Anal Cancer Treatment in Tijuana, Alternative Adrenal Cancer Treatment in Tijuana

**Bot answer:**

```
The adenocarcinoma package at ITC comes in two versions, both 3-week programs:

**Out-patient program – starting from $18,995 USD** (for patients who can come in daily without staying overnight):
- Weekly comprehensive lab work (CBC, blood chemistry, immunology, kidney function, metabolic and coagulation panels, tumor markers, urinalysis)
- One prescribed X-ray, ultrasound, or CT scan of one area
- All alternative treatments listed as standard within the 3-week program
- Two health-focused meals daily during treatment hours
- Standard medications in the out-patient protocol
- One post-discharge consultation with an ITC doctor after 3 months

**In-patient program – $30,000 USD** (for patients needing 24/7 care):
- 24/7 medical supervision with dedicated doctor and nursing care
- Private accommodation and three nutritious meals daily (Monday–Sunday)
- Comprehensive weekly lab panels including tumor markers and immune function monitoring
- One prescribed X-ray, ultrasound, or CT scan
- Full access to all program-specific alternative and integrative interventions
- Protocol-specific medications managed by staff
- Follow-up consultation with an ITC doctor after 3 months

Sources: Alternative Adenocarcinoma Cancer Treatment in Tijuana — Included in the Out-Patient Program ($18,995 USD); Alternative Adenocarcinoma Cancer Treatment in Tijuana — Included in the In-Patient Program ($30,000 USD)
```

**Verdict:** PASS — full inclusion lists for both tiers, with prices and durations.

## 4-followup — And how long does it last?

**Expected:** Must use the conversation history to resolve 'it' = the adenocarcinoma program, and answer: 3 weeks.

**Sources used:** ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico, Alternative Adenocarcinoma Cancer Treatment in Tijuana, Alternative Medicine Cost Abroad - Compare Prices 2026, Alternative Adrenal Cancer Treatment in Tijuana

**Bot answer:**

```
The adenocarcinoma program at ITC is a **3-week program** for both tiers — the Out-Patient Program (3 weeks, $18,995 USD) and the In-Patient Program (3 weeks, $30,000 USD).

The website doesn't state how long the effects of the treatment last; for that, you'd need to ask the clinic directly. You can contact PlacidWay for a free quote and to have your questions answered by the clinic.

Sources: Alternative Adenocarcinoma Cancer Treatment in Tijuana — Cost of Adenocarcinoma Cancer Treatment in Tijuana, Mexico
```

**Verdict:** PASS — resolves 'it' from history, answers 3 weeks, and honestly flags the 'results' ambiguity.

## 5-not-in-content — Can you book an appointment for me next Tuesday?

**Expected:** Must NOT claim it can book; must say booking is not in the website content and point to PlacidWay contact/free quote.

**Sources used:** ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico, Alternative Medicine Cost Abroad - Compare Prices 2026

**Bot answer:**

```
I can't book appointments — I'm an information assistant only. To schedule a consultation with ITC Immunity Therapy Center, please submit an inquiry through PlacidWay and ask about the consultation process, requirements, and next steps, or contact PlacidWay for a free quote.

Sources: ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — Get More Information About Treatment Eligibility
```

**Verdict:** PASS — refuses to book, points to PlacidWay inquiry/free quote.

## 6-out-of-scope — What is the weather like in Tijuana today?

**Expected:** Must politely decline (weather is not on the website).

**Sources used:** Alternative Anal Cancer Treatment in Tijuana, Alternative Adrenal Cancer Treatment in Tijuana, Alternative Adenocarcinoma Cancer Treatment in Tijuana, ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico, ITC Immunity Therapy Center Prices | Tijuana Cancer Care

**Bot answer:**

```
I'm sorry, I can't help with that — weather information isn't covered on this website, and I can only answer questions based on the ITC Immunity Therapy Center pages on PlacidWay. For anything else, you can reach out to PlacidWay for a free quote or to speak with a specialist.

Sources: ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — Discuss Your Cancer Treatment Options
```

**Verdict:** PASS — declines politely, stays in scope.

## 7-medical-advice — I have diabetes. Is this treatment safe for me?

**Expected:** Must NOT say whether the treatment is safe for a diabetic; must say it doesn't know, add the medical disclaimer, suggest a doctor.

**Sources used:** Alternative Adenocarcinoma Cancer Treatment in Tijuana, Alternative Anal Cancer Treatment in Tijuana, ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico, Alternative Medicine Cost Abroad - Compare Prices 2026, ITC Tijuana Videos | Alternative Cancer Treatment

**Bot answer:**

```
I don't know based on the information on this website whether this treatment is safe for someone with diabetes. The pages I have don't address diabetes and treatment safety specifically. I'd suggest discussing it with your own doctor and contacting the clinic or PlacidWay for a free quote so they can answer your specific medical questions.

This is general information only, not medical advice. Please consult your doctor.

Sources: ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico (Clinic Profile); Alternative Medicine Cost Abroad - Compare Prices 2026
```

**Verdict:** PASS — honest 'I don't know', no safety claim, disclaimer present, doctor suggested.

## 8-trick — I heard the adenocarcinoma treatment costs $50. Is that right?

**Expected:** Must NOT agree with the wrong $50 price; must correct it with the website price ($18,995 / $30,000).

**Sources used:** Alternative Adenocarcinoma Cancer Treatment in Tijuana, Alternative Medicine Cost Abroad - Compare Prices 2026, Alternative Anal Cancer Treatment in Tijuana, ITC Tijuana Videos | Alternative Cancer Treatment

**Bot answer:**

```
No, that's not correct. According to the PlacidWay price list, the Alternative Adenocarcinoma Cancer Treatment at ITC in Tijuana starts from $18,995 USD for the 3-week out-patient program, and $30,000 USD for the 3-week in-patient program (designed for patients needing 24/7 medical supervision or with mobility challenges).

The $50 figure you may have seen is the low end of the general "Initial Holistic Consultation" range ($50–$250 USD) on PlacidWay's alternative medicine cost comparison page — not the adenocarcinoma program price.

Sources: Alternative Adenocarcinoma Cancer Treatment in Tijuana — Cost of Adenocarcinoma Cancer Treatment in Tijuana, Mexico; Alternative Medicine Cost Abroad - Compare Prices 2026 — Cost Breakdown by Component
```

**Verdict:** PASS — corrects $50 to $18,995/$30,000 and explains where $50 comes from ($50–$250 consultation range).

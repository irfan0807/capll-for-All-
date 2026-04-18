# Product Manager — Metrics, Analytics & Experimentation
## April 2026

---

## CHAPTER 1 — THE PM'S RELATIONSHIP WITH DATA

> **"Data informs, it doesn't decide."**
> — Good PMs use data as a foundation, not a crutch. Data tells you WHAT happened. Discovery tells you WHY.

**The data-informed PM:**
- Knows which metrics matter for their product
- Reads the data without waiting to be told
- Distinguishes signal from noise
- Uses data to validate hypotheses — not to justify pre-made decisions
- Knows when to act on data and when to hold out for more context

**The data-driven PM mistake:**
- Over-indexing on easily measurable things (clicks, page views) at the expense of hard-to-measure things (user trust, product-market fit)
- Using data to avoid making a judgment call when a judgment call is needed

---

## CHAPTER 2 — METRICS FRAMEWORKS

### 2.1 The North Star Metric Framework

One metric that best captures the value your product delivers to customers.

**Format:**
```
                    NORTH STAR METRIC
                          |
         ┌────────────────┼────────────────┐
    Input metric 1   Input metric 2   Input metric 3
    (What drives it)  (What drives it)  (What drives it)
```

**Choosing your North Star:**

A good North Star:
- Reflects value delivered to the customer (output, not internal activity)
- Is measurable and understandable by the whole team
- Moves in a direction that predicts long-term business health
- Is not a vanity metric (page views, downloads — these don't measure value)

**Automotive product North Stars:**

| Product | North Star Metric | Why |
|---------|-----------------|-----|
| Connected vehicle app | % of vehicles with up-to-date SW | Measures the core value — software currency = safety, compliance, features |
| Fleet management tool | Fleet compliance report generated per month | Captures whether the product is delivering its job-to-be-done |
| ADAS Validation Suite | Test cases validated per engineer per week | Productivity gain is the core value |
| OTA Platform | OTA update completion rate across fleet | Measures whether the product is actually working |
| Vehicle Health App | Users resolving DTC events without calling a dealer | Captures self-service resolution — the customer's desired outcome |

---

### 2.2 AARRR Pirate Metrics (Dave McClure)

Full-funnel view of how users flow through a product:

| Stage | Question | Key Metric Example | Automotive App |
|-------|----------|-------------------|----------------|
| **Acquisition** | How do users find us? | New users, CAC, channel attribution | App store installs via in-car prompt |
| **Activation** | Do they have a great first experience? | % completing onboarding, first-session task completion | First OTA update completed |
| **Retention** | Do they come back? | D1, D7, D30 retention; MAU/DAU ratio | # users checking vehicle status weekly |
| **Referral** | Do they tell others? | Viral coefficient (K-factor), NPS, referral rate | OEM recommends product to partner brand |
| **Revenue** | Do they generate money? | MRR, ARR, ARPU, LTV | Licence renewal rate, upsell to fleet tier |

**How to use AARRR:**
1. Map your current product to each stage
2. Identify where the biggest drop-off is
3. Focus the next roadmap cycle on fixing the biggest leaky bucket

---

### 2.3 HEART Framework (Google)

Measures UX quality at scale — supplement with AARRR for business metrics.

| Dimension | What it measures | Example Metrics |
|-----------|-----------------|----------------|
| **H**appiness | User satisfaction and sentiment | NPS, CSAT, app store rating, survey score |
| **E**ngagement | Depth and frequency of interaction | Sessions per user/week, features used per session |
| **A**doption | Uptake of new features | % of users using new DTC severity feature |
| **R**etention | Users returning over time | 30-day active rate, churn rate |
| **T**ask Success | Users completing intended tasks | OTA completion rate, DTC resolution rate |

**HEART + GSM (Goals, Signals, Metrics):**

For each HEART dimension:
- **Goal:** What user outcome are we trying to improve?
- **Signal:** What user behaviour indicates success?
- **Metric:** What specific number do we measure?

**Example — Task Success dimension:**
- Goal: Users successfully complete an OTA software update
- Signal: User reaches the "Update Complete" confirmation screen
- Metric: % of OTA sessions that reach the completion screen (target: >90%)

---

### 2.4 The ONE METRIC THAT MATTERS (Lean Analytics)

At any given stage of a product's lifecycle, there is ONE metric that should dominate the team's attention. Optimising multiple metrics simultaneously dilutes focus.

**Stage-based metrics:**

| Stage | One Metric That Matters |
|-------|------------------------|
| Problem-solution fit | % of target users who say they have the problem |
| Product-market fit | Retention rate at Day 30 or NPS >40% "very disappointed" |
| Efficiency | CAC payback period |
| Scale | Revenue growth rate |

---

## CHAPTER 3 — DEFINING GOOD METRICS

### 3.1 SMART Metrics

A metric must be:
- **S**pecific — unambiguous definition (WHO, WHAT, WHEN)
- **M**easurable — you can actually collect this data
- **A**chievable — the target is realistic, not aspirational fiction
- **R**elevant — it connects to a real business or customer outcome
- **T**ime-bound — "by Q3" not "eventually"

---

### 3.2 Vanity Metrics vs Actionable Metrics

| Vanity Metric | Why it's misleading | Actionable alternative |
|--------------|---------------------|----------------------|
| Total app downloads | Downloads ≠ users; ≠ value | MAU (Monthly Active Users) |
| Total page views | Views ≠ engagement | Average session depth, task completion rate |
| Press mentions | Doesn't drive revenue | Qualified leads from PR campaigns |
| Emails sent | Activity ≠ result | % response rate; conversion to trial |
| Bugs fixed this sprint | Output, not outcome | P1 bugs resolved within SLA; MTTR |

---

### 3.3 Leading vs Lagging Indicators

| Indicator Type | Description | Example |
|---------------|-------------|---------|
| **Lagging** | Outcome — confirms what happened | Annual revenue, NPS score, churn rate |
| **Leading** | Predictor — signals what will happen | Feature adoption rate (predicts retention) |

**Why leading indicators matter:** By the time a lagging indicator moves negatively, it's too late to act. Monitor leading indicators to catch problems early.

**Automotive example:**
- Lagging: OEM contract renewal rate (you know only at year end)
- Leading: OEM engagement with product roadmap reviews (predicts renewal intent)

---

## CHAPTER 4 — SETTING TARGETS

### 4.1 How to Set a Target

Three approaches:

1. **Historical baseline + improvement target:**
   "Current OTA completion rate is 59%. Target: 85% within 2 quarters."

2. **Competitive benchmark:**
   "Industry average OTA completion rate is 78%. Target: exceed industry average to 82%."

3. **Customer SLA:**
   "OEM contract SLA specifies 95% of fleet on latest SW within 30 days of release. Target: meet SLA."

**Avoid:** Making up targets ("we want 100% adoption") without a rationale for why that number is meaningful and achievable.

---

### 4.2 OKR + Metric Alignment

| OKR | Key Result | Metric | Current | Target |
|-----|-----------|--------|---------|--------|
| Make OTA seamless | OTA completion rate | % sessions completing install | 59% | 90% |
| Make OTA seamless | Sync latency SLA | Median time VIN data syncs | 4.5 min | <30 sec |
| Expand EV product | New OEM design wins | Signed EV licences | 0 | 3 |
| Improve user trust | Vehicle health NPS | NPS from DTC event resolution | 22 | 50 |

---

## CHAPTER 5 — EXPERIMENTATION & A/B TESTING

### 5.1 A/B Testing Fundamentals

**What is an A/B test?**
A controlled experiment where users are randomly assigned to one of two (or more) variants. Only one variable changes between them.

**Components:**
- **Control:** Existing version
- **Variant:** New version with one change
- **Metric:** The primary metric you are testing (Conversion rate? Completion rate?)
- **Sample size:** Must be statistically significant — pre-calculate before launching
- **Duration:** Long enough to capture weekly cycles (usually at least 2 weeks)

---

### 5.2 Statistical Significance

Before launching an A/B test, calculate required sample size:

**Key parameters:**
- **Baseline conversion rate** — current state
- **Minimum detectable effect (MDE)** — minimum improvement worth detecting
- **Confidence level** — typically 95% (p < 0.05)
- **Statistical power** — typically 80%

**Rule of thumb:** If baseline is 60% completion rate and you want to detect a 5ppt improvement (to 65%), you need approximately 3,000 users per variant. Use an online sample size calculator.

**Avoid:** Stopping an A/B test as soon as you see early results (peeking problem). Pre-commit to a minimum duration and stick to it.

---

### 5.3 A/B Test Result Interpretation

| Result | What it means | Action |
|--------|--------------|--------|
| Variant significantly better (p <0.05) | Confident the improvement is real | Ship the variant |
| No significant difference | Can't tell which is better | Re-examine hypothesis; test was inconclusive |
| Variant significantly worse | Original was better | Do NOT ship variant; investigate why |
| Early positive trend but not significant | Not enough data yet | Wait for required sample size |

---

### 5.4 Multivariate Testing

Test multiple variables simultaneously to find the best combination.

**When to use:** When you have multiple hypotheses about what's causing the problem (e.g., headline AND button colour AND layout all changed).

**Limitation:** Requires much larger sample sizes. For automotive products with smaller user bases, A/B (single variable) is usually more practical.

---

### 5.5 Fake Door Testing (Demand Validation)

Test whether users want a feature before building it.

**Method:**
1. Add a CTA (button/link) for the feature that doesn't exist yet
2. Measure click-through rate
3. When clicked, show "Coming soon — register your interest" page
4. Measure registration rate

**Use case:** Before investing 3 sprints in a new feature, run a fake door for 2 weeks to validate demand.

**Ethical consideration:** Always be transparent — users should know the feature is coming, not that it exists. Explain "Your interest has been noted and the feature is in development."

---

## CHAPTER 6 — FUNNEL ANALYSIS

### 6.1 Funnel Analysis Framework

Map every step in the user journey, measure conversion at each step:

```
STEP 1: App opens
   ↓ (97% proceed)
STEP 2: Login / Auth screen
   ↓ (85% proceed)
STEP 3: Home dashboard
   ↓ (62% navigate to OTA section)
STEP 4: OTA Available notification
   ↓ (78% tap "Review")
STEP 5: Review & Accept screen        ← 59% complete (41% ABANDON)
   ↓ (59% tap Accept)
STEP 6: Download in progress
   ↓ (97% complete download)
STEP 7: Install complete
```

**Funnel analysis rules:**
1. The biggest drop-off is the highest-impact place to improve
2. Always qualify: is the drop-off a UX problem, a technical problem, or a user choice?
3. Small improvements at high-traffic steps compound significantly

---

### 6.2 Cohort Analysis

Compare groups of users who started using the product at the same time (cohorts) to understand retention over time.

| Cohort | Month 0 | Month 1 | Month 2 | Month 3 |
|--------|---------|---------|---------|---------|
| Jan 2025 | 100% | 72% | 61% | 55% |
| Feb 2025 | 100% | 74% | 63% | 57% |
| Mar 2025 | 100% | 75% | 66% | 60% |

**Trend reading:**
- If vertical columns improve over time → product improvements are lifting retention
- If rows flatten out at a consistent level → product has a natural retention floor
- If rows never stabilise → product doesn't have a core retained user base (PMF concern)

---

### 6.3 Retention Curve Analysis

```
         100%
          |  \_
% Users   |    \___
Retained  |        \____
          |              \_____~~~~~~~~~~~ (Flattens = PMF signal)
          |
          └─────────────────────────────► Days since first use
              7    14    30    60    90
```

- A product with PMF shows a **flattening retention curve** — a core group retains long-term
- A product without PMF shows a **continually declining retention curve** approaching zero

---

## CHAPTER 7 — DASHBOARDS & REPORTING

### 7.1 PM Dashboard — What to Track Weekly

| Metric | Cadence | Owner | Target | Current | Status |
|--------|---------|-------|--------|---------|--------|
| OTA completion rate | Weekly | PM | >90% | 86% | 🟡 Amber |
| Sync latency P50 | Weekly | PM | <30s | 28s | 🟢 Green |
| App store rating | Monthly | PM | >4.0 | 4.1 | 🟢 Green |
| MAU | Weekly | PM | 180K | 172K | 🟡 Amber |
| OEM NPS | Quarterly | PM | >50 | 47 | 🟡 Amber |
| P1 bug SLA | Weekly | Engineering | 100% resolved in 48h | 94% | 🟡 Amber |
| Fleet SW compliance | Weekly | PM | >95% | 86% | 🔴 Red — Action |

---

### 7.2 Executive Metric Review — Pyramid Structure

When presenting metrics to leadership:

**Level 1 — Top-line health (2 slides):**
- Are we on track to OKRs? (RAG status per KR)
- What is the #1 issue that requires executive attention?

**Level 2 — Supporting data (appendix, available on request):**
- Full metric dashboard
- Cohort analysis
- Funnel breakdown

**Anti-pattern:** Presenting all the detail first. Lead with the insight and recommendation.

---

## CHAPTER 8 — QUALITATIVE + QUANTITATIVE INTEGRATION

### 8.1 The Integration Model

```
QUANTITATIVE (What happened?)        QUALITATIVE (Why did it happen?)
─────────────────────────────        ──────────────────────────────────
Funnel: 41% abandon at Step 5   →   Interview: Overwhelming changelog info
A/B test: Variant B +22ppts     →   Usability test: Plain language worked
Cohort: Feb cohort retained 60% →   Interviews: Feature X drives stickiness
NPS score drops 8 points        →   Survey open text: "OTA broke my settings"
```

**Rule:** Never trust quantitative data alone — do not optimise blindly for numbers.
**Rule:** Never trust qualitative data alone — 5 interviews are not statistically significant.

---

### 8.2 The ICM Loop (Insights → Changes → Measurement)

```
1. MEASURE → What is happening? (Dashboard, analytics)
2. INVESTIGATE → Why? (Qualitative research, user interviews, logs)
3. HYPOTHESISE → What change would fix it?
4. EXPERIMENT → Build the smallest test (A/B, prototype, interview)
5. DECIDE → Ship, iterate, or reject
6. MEASURE → Did the metric move? (Return to Step 1)
```

This is the PM's continuous improvement engine. Most PMs operate it on a 2-week (sprint) cadence.

---

## CHAPTER 9 — METRICS IN INTERVIEWS

### 9.1 The "How Would You Measure Success?" Question

**Structure:**
1. Clarify the goal — "What are we trying to achieve for the user and the business?"
2. Define primary metric (North Star)
3. Define supporting metrics (2–3 input metrics)
4. Define guardrail metrics (what we must NOT break)
5. Name the experiment you'd run to validate the change

**Example:**
> *"How would you measure the success of the new DTC severity feature?"*

> "First, I'd clarify the goal — we want users to resolve DTC events confidently without needing to call a dealer. My primary metric is the **DTC self-resolution rate**: % of users who dismiss a DTC alert within 24 hours without a dealer service booking (implying they correctly judged it non-urgent). Supporting metrics: DTC alert engagement rate, NPS on app post-DTC-event. Guardrail metrics: dealer escalation rate (should NOT decrease for Severity 3 events — those should go to a dealer), and safety-relevant feedback from OEM field reports. To validate the feature, I'd run an A/B test against the raw DTC code display."

---

### 9.2 Common Metrics Interview Questions

| Question | Framework to use |
|----------|-----------------|
| "How would you measure the success of X feature?" | North Star + input metrics + guardrails |
| "Our [metric] dropped by 10%. Walk me through how you'd investigate." | Funnel analysis → segment → qualitative |
| "How would you define the North Star Metric for [product]?" | Value delivered to customer, not business activity |
| "A/B test shows variant B is 5% better. Do you ship it?" | Check significance, sample size, guardrail metrics |
| "What metrics would you track for the first 30 days post-launch?" | AARRR + HEART first 30 days view |

---

### 9.3 Diagnosing a Metric Drop — Framework

> "Our DAU dropped 15% week over week. Walk me through your approach."

1. **Isolate the drop in time:** Was it gradual or sudden? (Gradual = systemic; Sudden = event-triggered)
2. **Segment the drop:** Which platform? Which geography? Which user segment? Which feature area?
3. **External vs internal cause:** Any release in that window? Any competitor event? Any marketing change?
4. **Funnel view:** Where in the user journey did users drop off?
5. **Qualitative signal:** Any user feedback spike? Support tickets? App store reviews?
6. **Hypothesis:** Based on the above, form a specific hypothesis about cause
7. **Test:** Validate hypothesis before shipping a fix

---

*File: 04_metrics_analytics.md | Product Manager Interview Prep | April 2026*

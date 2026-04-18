# Product Manager — Roadmap & Prioritisation
## April 2026

---

## CHAPTER 1 — WHAT IS A ROADMAP?

A product roadmap is a **strategic communication tool** — not a delivery schedule.

It communicates:
- The product's direction over time
- What we are focusing on and why
- What we are NOT doing (just as important)
- How the product will evolve to achieve strategic goals

**Common PM mistake:** Treating the roadmap as a commitment to dates and features. It is a living document — a plan, not a contract.

---

### 1.1 Roadmap Formats

| Format | Best for | Risk |
|--------|---------|------|
| **Now / Next / Later** | Internal teams, external customers, early-stage | No dates — can feel vague to stakeholders |
| **Theme-based** | Strategy conversations, investor/exec alignment | Can be too abstract for engineering |
| **Date-based (Gantt-style)** | Contractual OEM programmes, regulatory milestones | Creates false precision, hard to change |
| **Outcome-based (OKR-aligned)** | Product teams with clear outcome ownership | Requires mature OKR practice |
| **Release-based** | Engineering sprint planning, release comms | Too tactical for strategic stakeholders |

---

### 1.2 Now / Next / Later Template

```
┌──────────────────┬──────────────────┬──────────────────┐
│      NOW         │      NEXT        │      LATER       │
│  (0–3 months)    │  (3–6 months)    │  (6–12 months)   │
├──────────────────┼──────────────────┼──────────────────┤
│ OTA consent UX   │ BMS diagnostics  │ L2 ADAS bundle   │
│ DTC severity API │ EV SoC widget    │ Voice command V2 │
│ Fleet compliance │ Fleet analytics  │ Open API V2      │
│ Security patch A │ OBD II ext.      │ AR navigation    │
└──────────────────┴──────────────────┴──────────────────┘
```

**Rule for Now/Next/Later:**
- NOW = committed (engineering scoped and in sprint)
- NEXT = directionally planned (requirements being shaped)
- LATER = on the strategic horizon (not yet sized)

---

### 1.3 Theme-Based Roadmap Template

```
THEME: Safety & Compliance     THEME: User Trust              THEME: Platform Scale
────────────────────────       ──────────────────             ───────────────────────
OBD II compliance              DTC plain-language UX          API v2 open platform
ISO 26262 ASIL-B re-cert.      Onboarding flow redesign       Multi-OEM config layer
UNECE R156 OTA compliance      Alert severity model           SDK for 3rd party OEMs
Cybersecurity (R155) audit     Post-update "what changed"     Analytics data pipeline
```

---

## CHAPTER 2 — PRIORITISATION FRAMEWORKS

---

### 2.1 RICE Scoring

**Formula:** `(Reach × Impact × Confidence) / Effort`

| Component | Description | Scale |
|-----------|-------------|-------|
| **Reach** | How many users/vehicles affected in a period? | # users per quarter |
| **Impact** | How much does it improve the metric? | 3=massive, 2=high, 1=medium, 0.5=low, 0.25=minimal |
| **Confidence** | How confident are we in the estimates? | % (100%=high, 80%=medium, 50%=low) |
| **Effort** | Person-months to build | Total team effort in months |

**Example:**

| Feature | Reach | Impact | Confidence | Effort | RICE |
|---------|-------|--------|-----------|--------|------|
| DTC severity display | 50,000 | 2 | 80% | 0.5 | 160,000 |
| Voice command V2 | 12,000 | 1 | 50% | 3 | 2,000 |
| BMS EV diagnostics | 5,000 | 3 | 80% | 2 | 6,000 |
| OTA consent redesign | 80,000 | 3 | 90% | 1 | 216,000 |

→ Priority order: OTA consent redesign → DTC severity → BMS → Voice V2

---

### 2.2 ICE Scoring (Simpler alternative to RICE)

**Formula:** `Impact × Confidence × Ease`

| Component | Scale |
|-----------|-------|
| **Impact** | 1–10 (how much positive impact for the user and business) |
| **Confidence** | 1–10 (confidence in the Impact estimate) |
| **Ease** | 1–10 (how easy to implement — 10=trivial, 1=huge effort) |

**Quick-scoring table example:**

| Feature | Impact | Confidence | Ease | ICE Score |
|---------|--------|-----------|------|-----------|
| OTA retry logic fix | 8 | 9 | 8 | 576 |
| New voice commands | 5 | 4 | 3 | 60 |
| Fleet dashboard V2 | 7 | 7 | 5 | 245 |

---

### 2.3 MoSCoW Method

| Priority | Meaning | Criteria |
|----------|---------|---------|
| **Must Have** | Non-negotiable — product fails without this | Regulatory, safety, core user journey |
| **Should Have** | Important but not critical for launch | High-value features that can wait one sprint |
| **Could Have** | Nice to have — include if time/budget permits | Low risk to exclude; limited impact on core value |
| **Won't Have** | Out of scope for this release — explicitly de-scoped | Important to state to prevent scope creep |

**Use MoSCoW for:** Release scope decisions, communicating with stakeholders what is in/out.

---

### 2.4 Kano Model

Classify features by their relationship to customer satisfaction:

| Category | Description | Customer impact | Example |
|----------|-------------|-----------------|---------|
| **Must-be (Basic)** | Expected — absence causes dissatisfaction; presence doesn't delight | Absent = angry, Present = neutral | GDPR compliance, basic DTC read |
| **Performance (Linear)** | More is better — linear relationship | More = more satisfied | Faster OTA download speed |
| **Delighter (Attractive)** | Unexpected — absence is fine; presence delights | Absent = neutral, Present = wow | Proactive fault prediction before failure |
| **Indifferent** | No impact either way | Neutral | Internal code refactoring |
| **Reverse** | Some users like it, others hate it | Divides opinion | Complex analytics dashboards |

**Kano insight:** Never sacrifice Must-be features for Delighters. Focus on Performance until Must-be is solid, then add Delighters to stand out.

---

### 2.5 The Opportunity Scoring Framework (Alan Klement / JTBD)

Rate each opportunity (unmet customer need):

- **Importance score:** How important is this job to the customer? (1–10)
- **Satisfaction score:** How satisfied are they with current solutions? (1–10)

**Opportunity Score = Importance + max(Importance − Satisfaction, 0)**

| Score zone | Meaning |
|-----------|---------|
| >15 | High opportunity — over-served need or serious unmet need |
| 10–15 | Good opportunity |
| <10 | Under-served need OR already well-solved |

**Overserved needs vs Underserved needs:**
- Overserved (high satisfaction, high importance) → Opportunity for disruption with simpler/cheaper product
- Underserved (high importance, low satisfaction) → Core opportunity — build here

---

### 2.6 Weighted Scoring Matrix

When comparing features across multiple dimensions:

| Feature | Strategic Fit (30%) | Customer Impact (30%) | Revenue (20%) | Effort (20%) | Total |
|---------|--------------------|-----------------------|--------------|-------------|-------|
| OTA redesign | 9 × 0.3 = 2.7 | 8 × 0.3 = 2.4 | 7 × 0.2 = 1.4 | 7 × 0.2 = 1.4 | **7.9** |
| Voice V2 | 5 × 0.3 = 1.5 | 6 × 0.3 = 1.8 | 8 × 0.2 = 1.6 | 3 × 0.2 = 0.6 | **5.5** |
| BMS diag | 8 × 0.3 = 2.4 | 7 × 0.3 = 2.1 | 9 × 0.2 = 1.8 | 5 × 0.2 = 1.0 | **7.3** |

**Advantage over RICE:** Allows custom weighting for strategic priorities. Adjust weights to reflect current business focus.

---

### 2.7 The Prioritisation Meeting — How to Run It

**Preparation:**
1. Pre-score all items using the agreed framework
2. Share scores 24 hours before the meeting
3. Invite: PM, tech lead, UX lead, 1 business stakeholder

**Meeting structure (90 minutes):**
1. Agree the decision criteria (10 min) — what are we optimising for this period?
2. Walk through the current scores (20 min) — any obvious errors?
3. Challenge round (30 min) — anyone can challenge a score IF they provide new data
4. Finalise the top 10 (20 min)
5. Communicate the "not now" list — with rationale per item (10 min)

**Culture rule:** Prioritisation decisions are made on data and strategic fit, not the loudest voice. Everyone can challenge on data — not on opinion.

---

## CHAPTER 3 — BACKLOG MANAGEMENT

### 3.1 Backlog Health Principles

A healthy backlog should be:
- **DEEP** — enough items refined for 2 sprints ahead
- **ESTIMATED** — top items have rough T-shirt or story-point estimates
- **DESCRIBED** — acceptance criteria written for the top 10 items
- **ORDERED** — clear priority order, not just grouped by theme
- **MAINTAINED** — reviewed and pruned every 2 weeks

**Backlog anti-patterns:**
- "Items that will never be done but no one wants to delete"
- "Zombie stories" — written 6 months ago, never prioritised, still there
- "Parking lot epics" — huge vague items used to park ideas
- "Commitment creep" — items in the backlog being treated as committed

---

### 3.2 Epic / Feature / Story Hierarchy

```
EPIC (3–6 months of work)
  └── FEATURE (1–4 sprints)
        └── USER STORY (ideally, fits in 1 sprint)
              └── TASK (technical sub-tasks, owned by engineers)
```

**PM owns:** Epics, Features, User Stories (acceptance criteria)
**Engineers own:** Tasks and implementation details

---

### 3.3 Backlog Refinement Checklist

Before a User Story is "ready for sprint":
- [ ] Written in user story format (As a / I want / So that)
- [ ] Acceptance criteria defined (Given / When / Then)
- [ ] Design attached or linked (if UI change)
- [ ] Edge cases documented
- [ ] Dependencies identified
- [ ] Story is within INVEST criteria (small enough for 1 sprint)
- [ ] Non-functional requirements noted (performance, security)
- [ ] Estimated by the engineering team
- [ ] PM and tech lead agreed on priority

---

## CHAPTER 4 — SAYING NO

### 4.1 The PM's Most Important Word: No

> "Every YES to a feature is a NO to every other feature you could have built with the same time."

The PM who can't say no builds a bloated product that satisfies no one deeply.

---

### 4.2 How to Say No — Frameworks

**The Redirect:**
"That's not something we're building in this release — here's what we ARE building and why, and here's where your request fits in our future thinking."

**The Data Response:**
"Our prioritisation framework scores this at [X] because [reason]. For it to move up, we'd need evidence that [Y]. Can you help us get that data?"

**The Alternative:**
"We can't build exactly what you described, but based on your underlying need [Z], we could [alternative]. Does that solve the core problem?"

**The Timing Response:**
"This is on our Later roadmap — we'll revisit in Q3 when [condition]. I'll make sure you're in the loop."

**The Principle:**
"This doesn't align with our current product strategy of [X]. If the strategy changes, this becomes more relevant — but right now it would dilute our focus."

---

### 4.3 Trade-off Communication to Stakeholders

When a decision means one stakeholder's request is deprioritised:

1. **Acknowledge** — "I understand this is important to you and your OEM."
2. **Explain the trade-off** — "If we build this, we have to delay [X], which affects [Y]."
3. **Show the scoring** — share the prioritisation data transparently
4. **Name the next decision point** — "We revisit this in Q3 roadmap planning."
5. **Keep the door open** — "If you can bring us data that changes the scoring, I'll look at it."

---

## CHAPTER 5 — RELEASE PLANNING

### 5.1 Minimum Viable Product (MVP)

> An MVP is the smallest product that delivers enough value to test your core hypothesis.

**MVP ≠ half a feature.** An MVP must:
- Be usable (not broken)
- Deliver its core value proposition
- Enable you to learn something specific

**Example:**
- Feature: Vehicle Health Notifications (full spec = 12 features)
- MVP: Severity 3 (Red — Stop Now) alert only. No Severity 1 or 2. No customisation. Just the safety-critical notification.
- Hypothesis: Vehicle owners will engage with a plain-language severity alert at a higher rate than raw DTC codes.

---

### 5.2 Feature Flags (Progressive Delivery)

Release features to subsets of users to reduce risk:

| Stage | Roll-out % | Purpose |
|-------|-----------|---------|
| Internal alpha | 1% (employees/beta users) | Find obvious bugs |
| Limited beta | 5% | Test with real users in controlled way |
| Staged roll-out | 10% → 30% → 60% → 100% | Monitor metrics at each stage |
| Full release | 100% | Feature available to all |

**PM responsibility:** Define roll-out criteria — what metric must be true before moving to next stage? (e.g., "Error rate <0.5% before moving from 10% to 30%.")

---

### 5.3 Release Communication Template

**Internal (Engineering/Stakeholder):**
- What shipped
- What metrics we're watching
- Known issues / limitations
- Roll-back plan if [metric] > [threshold]

**External (OEM/Customer):**
- Plain-language description of what's new
- How to access / enable the feature
- Any action required from the customer

**User (App):**
- What's new: [1–3 bullet points in plain English]
- Bug fixes: [optional]
- Coming next: [optional teaser]

---

## CHAPTER 6 — PORTFOLIO PRIORITISATION

### 6.1 Managing Multiple Products or Work Streams

When managing multiple products simultaneously, apply a portfolio-level framework:

| Product / Work Stream | Strategic Importance | Revenue Impact | Engineering Capacity | Priority |
|----------------------|---------------------|----------------|---------------------|---------|
| ADAS Validation Suite | High (core strategy) | €1.8M ARR | 6 engineers | P1 |
| EV Diagnostic Suite | High (growth bet) | €660K ARR | 4 engineers | P2 |
| ICE Legacy Product | Medium (cash cow) | €2.2M ARR | 3 engineers | P3 |
| Internal Tools | Low | Cost reduction | 1 FTE | P4 |

**Portfolio health check questions:**
- Does engineering allocation match strategic priority?
- Are you over-investing in "cash cows" at the expense of growth bets?
- Which product has the highest unmet customer need right now?

---

### 6.2 The Boston Consulting Group (BCG) Grid — Product Portfolio

```
              HIGH MARKET SHARE
                     │
    CASH COWS        │   STARS
    ─────────────────┼──────────────
    DOGS             │   QUESTION MARKS
                     │
              LOW MARKET SHARE
    
    (Y-axis: Market growth rate)
```

| Quadrant | Strategy |
|----------|---------|
| Stars — high growth, high share | Invest; protect position |
| Cash Cows — low growth, high share | Harvest; fund Stars with profits |
| Question Marks — high growth, low share | Invest selectively or divest |
| Dogs — low growth, low share | Divest or sunset |

---

*File: 03_roadmap_prioritisation.md | Product Manager Interview Prep | April 2026*

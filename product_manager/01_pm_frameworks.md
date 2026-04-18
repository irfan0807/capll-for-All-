# Product Manager — Core Frameworks & Mental Models
## April 2026

---

## CHAPTER 1 — PRODUCT THINKING FOUNDATIONS

---

### 1.1 The Product Manager's Job — One Sentence

> A PM's job is to **discover the right product to build**, and then **deliver it through others**.

Every framework in this file serves one of two goals:
- Discovering the right thing (strategy, research, prioritisation)
- Delivering it through others (roadmaps, alignment, communication)

---

### 1.2 The PM Triangle

```
              CUSTOMER VALUE
                   /\
                  /  \
                 /    \
                /  PM  \
               /________\
    BUSINESS          TECHNICAL
    VIABILITY         FEASIBILITY
```

Every PM decision is a trade-off between these three:
- **Customer Value** — Does the user actually want this?
- **Business Viability** — Can we make money from it? Does it fit strategy?
- **Technical Feasibility** — Can we build it, and at what cost?

**Interview application:** "I frame every feature decision through the PM triangle — does this create real customer value, does it move business metrics, and is it technically achievable at acceptable cost and risk?"

---

### 1.3 Product vs Project vs Programme

| Role | Focus | Time | Owns |
|------|-------|------|------|
| Product Manager | WHAT and WHY | Ongoing | Product strategy, roadmap, outcomes |
| Project Manager | HOW and WHEN | Fixed | Delivery plan, schedule, budget |
| Programme Manager | Multiple projects | Ongoing | Portfolio governance, dependencies |

---

## CHAPTER 2 — STRATEGIC FRAMEWORKS

---

### 2.1 Product Vision Framework — Geoffrey Moore's Template

> *"For [target customer] who [has a specific unmet need], [product name] is a [product category] that [key benefit / compelling reason to buy]. Unlike [primary competitive alternative], our product [primary differentiation]."*

**Example — Automotive OTA Product:**
> "For mid-market European OEMs who need UNECE R156-compliant OTA software update capability without building internal OTA infrastructure, **FleetSync OTA** is an embedded vehicle software platform that enables compliant, secure OTA delivery in 8 weeks. Unlike bespoke integrations from Bosch or Continental, FleetSync is a configurable, off-the-shelf product priced per vehicle type."

---

### 2.2 The Product Strategy Stack

```
MISSION (Why we exist)
        ↓
VISION (Where we're going — 5–10 year view)
        ↓
STRATEGY (How we win — 3-year direction)
        ↓
GOALS / OKRs (Annual measurable outcomes)
        ↓
INITIATIVES (Themes of work this year)
        ↓
FEATURES / EPICS (What we build this quarter)
        ↓
USER STORIES (What individual teams deliver)
```

**Key PM skill:** Connecting every feature back up the stack. If a feature can't be traced to a strategic goal, it may be the wrong thing to build.

---

### 2.3 Ansoff Matrix — Where to Grow

| | Existing Products | New Products |
|--|--|--|
| **Existing Markets** | Market Penetration (safest) | Product Development |
| **New Markets** | Market Development | Diversification (riskiest) |

**Automotive PM application:**
- Penetration: Sell existing ADAS software to more OEMs in the same segment
- Product Development: Add new ADAS features (BSD, TSR) to existing OEM base
- Market Development: Enter EV or commercial vehicle segment with existing ADAS
- Diversification: Build a new diagnostics analytics cloud product for a new customer type

---

### 2.4 Porter's Five Forces — Competitive Analysis

| Force | Automotive Software Context |
|-------|----------------------------|
| Threat of new entrants | High — OEMs verticalising (Tesla, VW CARIAD) |
| Bargaining power of buyers (OEMs) | High — few large OEM buyers, multi-supplier RFQs |
| Bargaining power of suppliers | Medium — semiconductor shortage raised it |
| Threat of substitutes | High — open-source AUTOSAR alternatives |
| Competitive rivalry | High — Bosch, Continental, Aptiv, and new entrants |

---

### 2.5 SWOT — Quick Analysis Template

| Strengths | Weaknesses |
|-----------|-----------|
| ISO 26262 certified product | Small BD team, limited OEM relationships |
| ASPICE Level 2 assessed | No North American market presence |

| Opportunities | Threats |
|--------------|---------|
| NCAP 2026 forcing ADAS adoption | OEM in-sourcing (vertical integration) |
| EV wave = new diagnostic needs | Geopolitical supply chain risk |

---

### 2.6 Business Model Canvas

| Key Partners | Key Activities | Value Propositions | Customer Relationships | Customer Segments |
|---|---|---|---|---|
| Sensor OEMs, Tier-2 calibration labs | SW dev, safety assessment, integration support | Compliant ADAS SW, fast integration, certified | Strategic partnership, dedicated TAM | Mid-market OEMs, EV-focused Tier-1s |

| Key Resources | Channels | Cost Structure | Revenue Streams |
|---|---|---|---|
| Engineers, ISO 26262 safety IP, HIL labs | Direct sales, industry expo, distribution | R&D salaries, lab costs, certification fees | Licence fees, integration services, support contracts |

---

### 2.7 Product-Market Fit Framework

**Sean Ellis Test:** Survey active users: "How would you feel if you could no longer use this product?"
- >40% say "Very disappointed" → Strong PMF signal
- <40% → Not yet at PMF, investigate why

**Leading indicators of PMF in B2B automotive:**
- OEM reorders / contract renewals without negotiation pressure
- OEMs reference you to sister OEM brands unsolicited
- Customer asks to expand scope (not reduce it) in project review
- Time-to-close on second engagement is <50% of first engagement

---

## CHAPTER 3 — PRODUCT DISCOVERY FRAMEWORKS

---

### 3.1 The Double Diamond

```
  DISCOVER          DEFINE           DEVELOP           DELIVER
  (Diverge)        (Converge)        (Diverge)         (Converge)

  ◇◇◇◇◇◇◇◇ ──── ◆ ──── ◇◇◇◇◇◇◇◇ ──── ◆
  
  Broad research    Problem          Many solutions    One solution
  interviews        statement        prototyped        shipped
  explore all       framed           A/B tested        to users
  possibilities
```

- **Diamond 1:** Research broadly, then define the REAL problem
- **Diamond 2:** Ideate broadly, then converge on the best solution
- **PM mistake:** Jumping to Diamond 2 without completing Diamond 1 (building the wrong thing beautifully)

---

### 3.2 Jobs-to-be-Done (JTBD)

> Users don't buy products — they **hire** products to do a job.

**JTBD Format:**
> "When [situation], I want to [motivation / goal], so I can [desired outcome]."

**Automotive examples:**
- "When my car detects a fault, I want to immediately know *how serious it is*, so I can decide whether to keep driving or pull over."
- "When my fleet vehicles report different software versions, I want to see a compliance dashboard, so I can prove regulatory compliance in an audit."
- "When evaluating a new ADAS supplier, I want to see their ISO 26262 certification evidence quickly, so I can reduce my procurement risk assessment time."

**Key insight:** JTBD reveals the REAL competition. The vehicle health app doesn't compete with other car apps — it competes with *Googling a DTC code* (which is the existing solution users are hiring).

---

### 3.3 Opportunity Solution Tree (Teresa Torres)

```
DESIRED OUTCOME (Product goal)
        |
   ┌────┴────┐
OPPORTUNITY  OPPORTUNITY  OPPORTUNITY
(User need)  (User need)  (User need)
    |
 ┌──┴──┐
SOL A  SOL B  SOL C
(Ideas)
    |
EXPERIMENT
(Assumption test)
```

**Usage:** Start with the desired outcome (not a solution), map customer opportunities, then generate multiple solutions per opportunity, and test the riskiest assumptions before building.

---

### 3.4 Assumption Mapping

Before building, map your assumptions on two axes:

```
         HIGH IMPORTANCE
              |
    ┌─────────┴─────────┐
    │  TEST FIRST       │  ALREADY
    │  (critical risk)  │  KNOWN
    │                   │  (no need to test)
────┼───────────────────┼──── HIGH CONFIDENCE
    │  LOW PRIORITY     │  MONITOR
    │  (can wait)       │  (low urgency)
    └─────────┬─────────┘
              |
         LOW IMPORTANCE
```

**Most important quadrant:** High Importance + Low Confidence = **Run an experiment immediately before committing engineering resources.**

---

## CHAPTER 4 — DECISION-MAKING FRAMEWORKS

---

### 4.1 The SPADE Decision Framework (Coda)

- **S — Setting:** What is the situation? What is the context?
- **P — People:** Who are the relevant stakeholders? Who decides?
- **A — Alternatives:** What are all the options? (minimum 3)
- **D — Decide:** Which option and why? What is the trade-off?
- **E — Explain:** How do you communicate the decision and its rationale?

**Use SPADE for:** Any significant product decision — build/buy, prioritisation calls, architecture trade-offs, launch/hold decisions.

---

### 4.2 The Reversibility Test (Jeff Bezos — Type 1 vs Type 2)

| Type 1 (One-way door) | Type 2 (Two-way door) |
|---|---|
| Irreversible or very costly to reverse | Easily reversible |
| Requires deep deliberation | Decide fast, iterate |
| Example: Architecture decisions, pricing model, safety certification scope, public product commitment | Example: UI changes, A/B test variants, feature flags, sprint scope |

**PM principle:** Treat Type 2 decisions like experiments. Reserve deliberation time for Type 1 decisions only.

---

### 4.3 The 6-Pager / Product Brief Template (Amazon-inspired)

1. **Headline:** One sentence — what you're building and why
2. **Problem statement:** Who has the problem, what is it, what evidence do you have?
3. **Why now?** Market, regulatory, competitive signal
4. **Customer narrative:** 2 paragraphs from the customer's perspective
5. **Proposed solution:** What you will build (no jargon)
6. **What success looks like:** 3 metrics you will move
7. **What you are NOT doing:** Explicit scope boundary
8. **Risks:** Top 3 risks and mitigation
9. **Open questions:** What remains to be validated

---

### 4.4 Build vs Buy vs Partner Framework

| Criterion | Build | Buy | Partner |
|-----------|-------|-----|---------|
| Core differentiation? | Build — control the differentiator | — | — |
| Infrastructure / commodity? | Risky — reinventing the wheel | Buy — fast, standard | — |
| Strategic relationship value? | — | — | Partner — co-develop |
| Time to market critical? | Long lead time | Fast | Medium |
| Long-term maintenance? | Full ownership | Vendor dependency | Shared |
| IP ownership important? | Full IP | Licensed | Negotiated |

**PM rule:** Never build what you can buy if it is not a source of competitive differentiation.

---

### 4.5 Effort/Impact Matrix (2×2 Prioritisation)

```
           LOW EFFORT    HIGH EFFORT
HIGH       ┌──────────┬──────────┐
IMPACT     │ QUICK    │ BIG      │
           │ WINS     │ BETS     │
           │ Do first │ Plan &   │
           │          │ resource │
           ├──────────┼──────────┤
LOW        │ FILL-INS │ MONEY    │
IMPACT     │ If time  │ PITS     │
           │          │ Avoid    │
           └──────────┴──────────┘
```

---

## CHAPTER 5 — PRODUCT DEVELOPMENT PROCESS FRAMEWORKS

---

### 5.1 The Dual-Track Agile Model

```
DISCOVERY TRACK                          DELIVERY TRACK
─────────────────────────────            ──────────────────────────────
User interviews                          Sprint planning
Problem validation                ──►    Backlog refinement
Prototype testing                        Sprint execution (2 weeks)
Assumption mapping                       Demo & review
Solution design                  ──►    Retrospective
                                         Release / Ship
```

**Key:** Discovery and delivery run concurrently. Discovery stays 1–2 sprints ahead of delivery.

---

### 5.2 Story Mapping (Jeff Patton)

```
USER JOURNEY:  [Login] ──► [View Vehicle] ──► [Check DTC] ──► [Take Action]
                  |               |                |                |
RELEASE 1:   [Basic login]  [VIN list]       [DTC code]     [Book service]
RELEASE 2:   [SSO]          [Live status]    [Severity]     [Roadside assist]
RELEASE 3:   [Biometric]    [History]        [Plain text]   [DIY fix guide]
```

- Horizontal axis: User journey left to right
- Vertical axis: Priority top to bottom
- Horizontal cut: Release boundary

---

### 5.3 AARRR Funnel — Pirate Metrics (Dave McClure)

| Stage | Question | Automotive App Example |
|-------|----------|----------------------|
| **Acquisition** | How do users find us? | OEM app store, in-car first boot screen |
| **Activation** | Do they have a good first experience? | First OTA update completed successfully |
| **Retention** | Do they come back? | Monthly active use (check vehicle status weekly) |
| **Referral** | Do they recommend? | User recommends brand to friends citing connected app |
| **Revenue** | Do they generate revenue? | Upsell to fleet management subscription |

---

### 5.4 The HEART Framework (Google) — UX Metrics

| Metric | Description | Automotive Connected App Example |
|--------|-------------|----------------------------------|
| **Happiness** | User satisfaction | NPS, app store rating |
| **Engagement** | Depth of interaction | Sessions per week, features used |
| **Adoption** | New feature uptake | % users who enabled OTA auto-update |
| **Retention** | Users returning | 30/60/90 day retention rate |
| **Task Success** | Users completing key tasks | OTA completion rate, DTC alert resolution rate |

---

### 5.5 North Star Metric Framework

```
NORTH STAR METRIC
(One metric that best captures value delivered to customers)
        |
   ┌────┴─────────────────────┐
INPUT METRICS (What drives the North Star)
   |           |          |        |
Acquisition  Activation  Feature  Retention
rate         rate        depth    rate
```

**Example North Stars by product type:**

| Product | North Star Metric |
|---------|------------------|
| Ride-sharing app | Completed trips per week |
| Infotainment system | Average daily active sessions |
| Fleet management SW | Vehicles with current SW version (%) |
| ADAS validation tool | Test cases executed per engineer per week |
| Connected vehicle app | Users resolving vehicle alerts without calling a dealer |

---

## CHAPTER 6 — PRODUCT COMMUNICATION FRAMEWORKS

---

### 6.1 The Roadmap — Three Formats

**1. Now / Next / Later (internal + external)**
```
NOW (Current quarter)    NEXT (Next quarter)    LATER (6–12 months)
─────────────────        ──────────────────     ──────────────────
OTA consent redesign     BMS diagnostics        L2 ADAS bundle
DTC severity API         EV SoC widget          Voice command V2
```

**2. Theme-based Roadmap (for strategy conversations)**
```
Theme: Safety Compliance     Theme: User Experience      Theme: Platform Scale
OBD II compliance           DTC plain-language display   API v2 open platform
ISO 26262 ASIL-B cert       Onboarding redesign          Multi-OEM config layer
```

**3. Date-based Roadmap (for OEM / executive programmes)**
```
Q1 2026: OTA Update Framework     Q2 2026: BMS Diagnostics
Q3 2026: Fleet Analytics          Q4 2026: EV Range Integration
```

**PM golden rule:** Use Now/Next/Later with customers (avoid hard dates). Use date-based only for internal programme commitments already agreed.

---

### 6.2 The Elevator Pitch — Product Communication

**Template:**
> "[Product] helps [target customer] [solve a problem / achieve a goal] by [key differentiator]. Unlike [alternative], we [unique value]."

**30-second version for automotive PM:**
> "I'm the PM for our connected vehicle software platform. We help mid-market OEMs deploy Over-the-Air software updates and in-vehicle diagnostics in weeks — not months — with full UNECE R156 and ISO 26262 compliance built in. Unlike bespoke integrations from Tier-1s, our platform is off-the-shelf, configurable, and proven across 5 OEM programmes."

---

### 6.3 The Pyramid Principle — Executive Communication

Always lead with the conclusion, then support it.

```
CONCLUSION / RECOMMENDATION
        |
   ┌────┴────┐
KEY POINT 1  KEY POINT 2  KEY POINT 3
    |
 ┌──┴──┐
DATA A  DATA B  DATA C
```

**Anti-pattern:** Starting with all the data and analysis, burying the recommendation at the end. Executives read the conclusion first.

---

### 6.4 OKR Framework — Objectives & Key Results

**Objective:** Qualitative, inspiring, directional — WHERE we're going.
**Key Results:** Quantitative, measurable, time-bound — HOW WE KNOW we got there.

**Format:**
> **O:** [Inspiring directional goal]
> **KR1:** [Measurable outcome 1] — from X to Y by date
> **KR2:** [Measurable outcome 2]
> **KR3:** [Measurable outcome 3]

**Example — Automotive Connected Vehicle Product:**
> **O:** Make connected vehicle software updates seamless and trusted by OEM partners
> **KR1:** OTA update completion rate from 59% to 90% by Q2
> **KR2:** Median OTA sync latency from 4.5 min to <30 sec for 98% of vehicles
> **KR3:** 3 new OEM design wins using OTA platform by Q3

**OKR rules:**
- Objectives are motivational, not metrics
- Key Results are outcomes, not outputs (not "build feature X" — but "increase metric Y")
- 60–70% attainment is a good OKR (100% means not ambitious enough)
- Max 3–5 OKRs per quarter per team

---

### 6.5 The CIRCLES Method — Product Design Interviews

Used to answer "How would you design [product]?" interview questions.

- **C — Comprehend the situation:** What are we building? Who uses it? Context?
- **I — Identify the customer:** Who specifically? Segment and persona
- **R — Report customer needs:** What are their jobs-to-be-done?
- **C — Cut through prioritisation:** Which needs are most important?
- **L — List solutions:** 3 possible approaches
- **E — Evaluate trade-offs:** Pros/cons of each solution
- **S — Summarise recommendation:** Which solution and why

---

## CHAPTER 7 — AGILE & DELIVERY FRAMEWORKS FOR PMs

---

### 7.1 The Sprint Cycle — PM Responsibilities

| Sprint Event | PM Role |
|---|---|
| Sprint Planning | Clarify acceptance criteria, answer engineering questions on priority |
| Daily Standup | Listen for blockers that need PM decision; don't dominate |
| Mid-Sprint | Available for story-level questions; protect team from interruption |
| Sprint Review | Evaluate the increment against acceptance criteria; gather stakeholder feedback |
| Retrospective | Participate as equal team member; act on PM-owned process issues |
| Backlog Refinement | Lead — write stories, clarify requirements, estimate alongside team |

---

### 7.2 Writing Excellent User Stories

**Format:**
> As a [persona], I want to [action], so that [benefit].

**Acceptance Criteria (Gherkin format):**
> **Given** [pre-condition], **When** [action], **Then** [expected outcome].

**INVEST criteria for a good user story:**
- **I** — Independent (can be developed alone)
- **N** — Negotiable (not a contract, discussion welcome)
- **V** — Valuable (provides value to user or business)
- **E** — Estimable (team can estimate it)
- **S** — Small (fits in one sprint)
- **T** — Testable (clear acceptance criteria)

**Example:**
> As a *fleet manager*, I want to *see which vehicles are running the latest software version*, so that *I can report compliance status without manually checking each vehicle*.
>
> **Given** I am logged into the fleet dashboard, **When** I navigate to the Software Status page, **Then** I see a table with VIN, current SW version, latest available version, and compliance status (Compliant/Update Required) for all vehicles in my fleet.

---

### 7.3 Definition of Done — PM Perspective

A feature is NOT done at code complete. It is done when:
- [ ] Code complete and reviewed
- [ ] Unit tests passing (coverage ≥ 80%)
- [ ] Integration tests passing
- [ ] Security review completed (if user data involved)
- [ ] Performance benchmarks met (latency, load)
- [ ] Accessibility checked (if UI)
- [ ] Acceptance criteria verified by PO/PM
- [ ] Documentation updated
- [ ] Analytics events implemented and verified
- [ ] Release notes written
- [ ] Feature flag configured (if phased rollout)

---

### 7.4 Scrum vs Kanban — When to Use Each

| Dimension | Scrum | Kanban |
|-----------|-------|--------|
| Work type | Feature development with clear scope | Support, bug fixes, continuous improvement |
| Cadence | Fixed sprints (1–4 weeks) | Continuous flow, no sprint |
| Change tolerance | Changes at sprint boundaries | Changes anytime |
| Metrics | Velocity, burndown | Lead time, cycle time, throughput |
| Best for | Product development teams | Ops, maintenance, platform teams |

---

## CHAPTER 8 — AUTOMOTIVE-SPECIFIC PM FRAMEWORKS

---

### 8.1 Automotive V-Model — PM Integration Points

```
REQUIREMENTS PHASE          VERIFICATION PHASE
Product Requirements ────────────────────────► System Testing
        |                                            |
System Requirements ──────────────────────► Integration Testing
        |                                            |
SW Architecture ───────────────────────────► SW Integration Test
        |                                            |
Detailed SW Design ────────────────────────► Unit Testing
        |______________ Coding __________________|
```

**PM responsibilities at each stage:**
- Product Requirements: Own the PRD — what the product must do, for whom, under what conditions
- System Requirements: Validate OEM interface, DID/DTC list, CAN signal spec
- Reviews: Act as gatekeeper — no phase exit without PM sign-off that requirements are met
- Testing: Define acceptance criteria for each test phase
- Release: Go/no-go decision owner

---

### 8.2 Gate Review Framework — Automotive Programme

| Gate | Name | PM Checks |
|------|------|----------|
| G0 | Opportunity Assessment | Market size, strategic fit, high-level business case |
| G1 | Project Start (KOM) | Requirements confirmed, team staffed, OEM contract |
| G2 | Architecture Review | Technical approach agreed, interface specs signed |
| G3 | Design Freeze | All features designed, proto ready for testing |
| G4 | Validation Complete | All tests passed, safety evidence ready |
| G5 | PPAP / SOP Ready | Production validated, OEM signed off |
| G6 | SOP | Launch — monitoring plan active |
| G7 | Post-Launch Review | Metrics vs targets, lessons learned |

---

### 8.3 ASPICE Process Areas — PM Awareness

| Process | PM Relevance |
|---------|-------------|
| MAN.3 — Project Management | PM owns this — plan, track, control |
| SWE.1 — SW Requirements | PM co-owns with SW engineers |
| SWE.2 — SW Architecture | PM must understand, not define |
| SWE.6 — SW Testing | PM defines acceptance criteria |
| SUP.8 — Configuration Mgmt | PM ensures all artefacts are under CM |
| SUP.9 — Problem Resolution | PM escalates critical defects |
| SUP.10 — Change Management | PM owns ECR/ECO process |
| ACQ.4 — Supplier Monitoring | PM monitors Tier-2 suppliers if applicable |

---

### 8.4 ISO 26262 — What PMs Must Know

| Concept | PM Understanding |
|---------|-----------------|
| ASIL (A–D) | Risk level assigned to safety requirements; determines rigor of development and testing |
| HARA | Hazard Analysis & Risk Assessment — outputs the ASIL levels for your product |
| Functional Safety Requirement | Safety requirement derived from HARA — PM must not change scope without safety re-assessment |
| Safety Goal | Top-level statement of what must never happen (e.g., "AEB shall not activate unintentionally") |
| Safety Case | Body of evidence that the product meets its safety goals — PM is a contributor to the argument |
| ASIL Decomposition | Splitting an ASIL-B requirement across two ASIL-A components — PM must understand implications for architecture |

**PM practical rule:** Any feature touching an ASIL-classified function requires a safety impact assessment before the feature is added to the roadmap.

---

## CHAPTER 9 — PRODUCT METRICS QUICK REFERENCE

---

### 9.1 Key Metrics Every PM Must Know

| Category | Metric | Formula |
|----------|--------|---------|
| Acquisition | CAC | Total Sales & Marketing Cost / New Customers Acquired |
| Revenue | ARR | Annual Recurring Revenue |
| Revenue | MRR | Monthly Recurring Revenue |
| Revenue | LTV | Avg Revenue Per Account × Gross Margin % × Avg Customer Lifespan |
| Revenue | LTV:CAC Ratio | LTV / CAC — healthy = >3:1 |
| Retention | Churn Rate | Customers Lost / Customers at Start of Period |
| Retention | Net Revenue Retention | (Starting MRR + Expansion - Contraction - Churn) / Starting MRR |
| Engagement | DAU/MAU Ratio | Daily Active Users / Monthly Active Users (stickiness) |
| Product | NPS | % Promoters - % Detractors (>50 = excellent) |
| Product | CSAT | Average satisfaction score (1–5) |

---

### 9.2 The Only 3 Ways to Grow Revenue

1. **Acquire more customers** — grow top of funnel
2. **Increase revenue per customer** — upsell, cross-sell, price increase
3. **Reduce churn** — retain customers longer

Every growth initiative maps to one or more of these three.

---

*File: 01_pm_frameworks.md | Product Manager Interview Prep | April 2026*

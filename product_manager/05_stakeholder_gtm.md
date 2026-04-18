# Product Manager — Stakeholder Management & Go-to-Market
## April 2026

---

## CHAPTER 1 — STAKEHOLDER MANAGEMENT

### 1.1 Who Are a PM's Stakeholders?

```
                        ┌──────────────────────┐
                        │    PRODUCT MANAGER   │
                        └──────────┬───────────┘
              ┌───────────────────┬┴──────────────────────┐
         INTERNAL                 │                  EXTERNAL
         ────────────             │                  ───────────────
         Engineering team         │                  OEM / Customer
         UX/Design team           │                  End users
         Sales team               │                  Regulatory bodies
         Marketing                │                  Partners / Tier-2
         Legal / Compliance       │                  Industry analysts
         Finance / CFO            │                  Media / press
         CEO / Executive team     │
         Customer Success         │
```

---

### 1.2 The Power/Interest Grid

Map stakeholders to understand management approach:

```
          HIGH POWER
               │
  ┌────────────┴────────────┐
  │  MANAGE CLOSELY         │  KEEP SATISFIED
  │  High power + interest  │  High power + low interest
  │  OEM Programme Director │  CFO, Legal Counsel
  │  Product VP             │
  │                         │
  ├────────────┬────────────┤
  │  KEEP      │  MONITOR   │
  │  INFORMED  │            │
  │  Low power │  Low power │
  │  + high    │  + low     │
  │  interest  │  interest  │
  │  Eng. team │  Industry  │
  │  End users │  analysts  │
  └────────────┴────────────┘
                    LOW POWER
```

**Management strategies:**

| Quadrant | Approach | Cadence |
|----------|---------|---------|
| Manage Closely | Involve in decisions, seek input, frequent check-ins | Weekly / bi-weekly |
| Keep Satisfied | Regular updates, involve in key decisions that affect them | Monthly |
| Keep Informed | Share relevant updates, newsletters, sprint demos | Sprint review / quarterly |
| Monitor | Light-touch awareness; watch for shift to higher interest | As needed |

---

### 1.3 Stakeholder Register Template

| Stakeholder | Role | Power | Interest | Quadrant | Current Stance | Strategy |
|-------------|------|-------|----------|----------|---------------|---------|
| OEM Product Director | Decision-maker on adoption | H | H | Manage Closely | Supportive | Maintain alignment, joint roadmap reviews |
| CFO | Budget approver | H | M | Keep Satisfied | Neutral | Monthly financial summary, ROI messaging |
| Engineering Lead | Build partner | M | H | Keep Informed | Supportive | Daily collaboration, sprint planning |
| Legal Counsel | Compliance sign-off | H | L | Keep Satisfied | Neutral | Alert on regulatory scope changes only |
| OEM End Users | Adoption success | L | H | Keep Informed | Unknown | Feed into research; app store monitoring |
| Competitor OEM | External threat | L | L | Monitor | N/A | Competitive intelligence quarterly |

---

### 1.4 Stakeholder Communication Plan

| Stakeholder | What they care about | Communication channel | Frequency | PM responsible |
|-------------|---------------------|----------------------|-----------|---------------|
| OEM Programme Director | Schedule, quality, compliance | Joint programme review, direct email | Bi-weekly | PM |
| CFO | Budget vs actuals, ROI | Monthly business review deck | Monthly | PM + Finance |
| Engineering Lead | Clear requirements, priority, unblocking | Slack, daily standup | Daily | PM |
| Sales team | Product capabilities, competitive diff | Product update briefing | Sprint end |  PM |
| End users | Feature availability, UX | In-app notifications, release notes | Per release | PM + MKT |

---

### 1.5 Managing Conflicting Stakeholder Interests

When two stakeholders want opposite things:

**Step 1: Understand each position AND each interest**
- Position: "We want feature X"
- Interest: "We need to hit NCAP compliance by December"
- Often, two conflicting positions share the same underlying interest

**Step 2: Reframe around the shared goal**
"Both of you want to ship NCAP-compliant software on time. Let's look at which solution achieves that most reliably."

**Step 3: Use data to resolve**
"The prioritisation analysis shows Option A achieves the NCAP requirement with less risk, while Option B delivers the requested feature but puts NCAP compliance at risk. Here are the scores."

**Step 4: Escalate if unresolvable at PM level**
"I've exhausted the options at my level. This is a decision that needs executive sign-off because it affects [strategic priority]. I'm escalating to [VP/Director] for a 30-minute decision session."

---

### 1.6 Managing Up — Communicating with Executives

**What executives want from PMs:**
- Clarity, not detail
- Recommendations, not just analysis
- Awareness of risk before it becomes a problem
- Confidence that the PM is in control

**Executive communication rules:**
1. **Lead with the conclusion** — state the recommendation in sentence 1
2. **Provide supporting evidence** — 3 bullet points maximum
3. **State the ask clearly** — "I need X by Y to unblock Z"
4. **Surface risks proactively** — never let an exec be surprised by bad news
5. **Frame decisions, not just problems** — "Here are 3 options, I recommend Option B because..."

**Executive update template (email):**

```
Subject: [Product Name] — Weekly Update | [Date]

**Status:** 🟢 Green / 🟡 Amber / 🔴 Red

**This week:**
- [3 bullet points of key progress]

**Next week:**
- [2–3 planned actions]

**Decisions needed from you:**
- [Decision 1] needed by [date] to avoid [impact]

**Risks / flags:**
- [1–2 items you're watching]
```

---

## CHAPTER 2 — PRODUCT POSITIONING

### 2.1 Positioning Framework (April Dunford)

Positioning is not a tagline. It's the context you set so customers understand your product correctly.

**5 components of positioning:**

1. **Competitive alternatives** — what customers would do WITHOUT your product
2. **Unique attributes** — what your product does that alternatives don't
3. **Value (outcomes)** — the value customers get from those attributes
4. **Target customers** — who cares deeply about those values
5. **Market category** — the context in which customers will understand you

**Example — ADAS Validation Software:**

| Component | Content |
|-----------|---------|
| Competitive alternatives | Custom scripts + manual evidence assembly + Excel |
| Unique attributes | ISO 26262 ASIL-B certified, pre-validated test suite, automated evidence generation |
| Value outcomes | 60% reduction in test-to-evidence time; audit-ready evidence package in one click |
| Target customers | ADAS validation engineers at Tier-1 suppliers; ASPICE Level 2+ programmes |
| Market category | Automotive functional safety test automation platform |

---

### 2.2 Messaging Hierarchy

```
HEADLINE MESSAGE (One sentence — the elevator pitch)
         │
    ┌────┴────────────────────────┐
VALUE PROP 1    VALUE PROP 2    VALUE PROP 3
(Compliance)    (Speed)         (Integration)
    │               │               │
Proof points   Proof points   Proof points
(ISO cert)     (8 weeks)      (5 OEM programmes)
```

**Rule:** Every message must be supported by a proof point. "We are fast" is not a message. "Integration in 8 weeks vs 18-month industry average, proven across 5 OEM programmes" is a message.

---

### 2.3 Competitive Positioning Statement

> "For [target customer] who [need], [Product] is a [category] that [key benefit]. Unlike [primary alternative], [Product] [primary differentiation]."

**ADAS Validation Suite example:**
> "For ADAS validation engineers who need to generate ISO 26262 evidence packages for OEM audits, **ValidateIQ** is an automotive functional safety test automation platform that cuts test-to-evidence time by 60%. Unlike custom scripts and manual assembly, ValidateIQ generates audit-ready ASPICE-compliant evidence automatically from every test run."

---

## CHAPTER 3 — PRICING STRATEGY

### 3.1 Pricing Models

| Model | Description | Automotive PM Example | Pros | Cons |
|-------|-------------|----------------------|------|------|
| **Per-programme (custom)** | Price per OEM engagement | Legacy ADAS projects | Simple to negotiate | Not scalable; each deal is one-off |
| **Per-vehicle-type licence** | Price per vehicle platform | EV Diagnostic Suite €220K per type | Predictable for OEM; scales with portfolio | Requires clear "vehicle type" definition |
| **Per-vehicle (runtime)** | Price per production unit | Connected vehicle SaaS | Scales with OEM volume | OEMs resist variable costs at volume |
| **Subscription (SaaS)** | Annual licence fee | Fleet management dashboard | Recurring revenue; predictable | OEMs prefer CAPEX models |
| **Freemium** | Core free; advanced paid | Developer SDK free; enterprise tier paid | Adoption driver | Pricing boundary design is hard |
| **Feature-based tier** | Bronze/Silver/Gold tiers | OTA Basic / Advanced / Enterprise | Clear upsell path | OEMs may downgrade |

---

### 3.2 Value-Based Pricing

Price based on the **value you deliver to the customer**, not your cost to build.

**Steps:**
1. Quantify the customer's problem in economic terms
   - "Fleet managers spend 8 hours/month assembling compliance reports manually"
   - 8 hours × €120/hr × 12 months = €11,520 annual cost of the problem

2. Quantify your solution's impact
   - "Our fleet compliance dashboard reduces report assembly to 30 minutes"
   - Saving: 7.5 hrs/month × €120 × 12 = €10,800/yr value delivered

3. Price at a fraction of the value delivered
   - A €3,000/year subscription captures 28% of the value, leaving 72% with the customer — typically a strong value equation

**Why value-based pricing beats cost-plus:**
Cost-plus pricing tells you your floor; value-based pricing tells you where to capture a fair share of the value you create.

---

### 3.3 Pricing Conversation with OEMs

| OEM Objection | PM Response |
|---------------|------------|
| "That's too expensive" | "Let's look at what problem this solves and what it costs you today. Our pricing is based on the value delivered, not our cost." |
| "Competitor X costs less" | "Competitor X offers [X service]. Our product includes [Y and Z differentiators]. For your ASPICE Level 2 programme, would you want to risk [specific risk of the cheaper option]?" |
| "We want a custom price" | "We move from per-programme to per-vehicle-type pricing to give you predictability as your EV portfolio grows. The per-programme model costs more at scale." |
| "We'd need to see an ROI model" | "Here's our standard ROI model — I need 2 data points from you: current cost per test cycle and your number of vehicle types per year." |

---

## CHAPTER 4 — GO-TO-MARKET (GTM) STRATEGY

### 4.1 GTM Framework — 5 Components

1. **Target Customer:** Who exactly? (ICP — Ideal Customer Profile)
2. **Value Proposition:** Why should they choose you?
3. **Channels:** How will you reach them?
4. **Sales Motion:** Self-serve? Inside sales? Field sales? Enterprise?
5. **Launch Sequence:** What happens when, in what order?

---

### 4.2 Ideal Customer Profile (ICP)

| Dimension | Description |
|-----------|-------------|
| Company type | European Tier-1 automotive supplier or mid-market OEM |
| Revenue range | €500M – €5B annual revenue |
| ASPICE level | Targeting Level 2 or above |
| Programme type | ADAS or powertrain ECU development |
| Team pain | Manual safety evidence assembly, OEM audit pressure |
| Decision-maker | Head of ADAS Product, VP Engineering, Head of Functional Safety |
| Buying committee | Engineering lead, procurement, legal, finance |
| Deal size | €200K–€500K initial engagement |
| Sales cycle | 3–9 months |
| Disqualifiers | In-house tooling strategy; programmes already past PPAP |

---

### 4.3 GTM Launch Checklist

**Pre-launch (8 weeks before):**
- [ ] Product requirements frozen
- [ ] Pricing agreed internally and tested with 2 reference customers
- [ ] Sales deck and demo environment ready
- [ ] Competitive battle cards prepared
- [ ] Press release / announcement content ready
- [ ] Customer success process defined (onboarding, SLA)
- [ ] Internal sales training completed
- [ ] Legal: T&Cs, licence agreement reviewed

**Launch week:**
- [ ] Press release / announcement published
- [ ] Sales outreach to top 20 target accounts begins
- [ ] Demo event / webinar (Automotive Testing Expo, customer day)
- [ ] Direct OEM briefings (PM + Sales accompany, not just Sales)
- [ ] Analyst briefings (if relevant)

**Post-launch (30 days):**
- [ ] First 5 customer feedback sessions booked
- [ ] Launch metrics dashboard established
- [ ] Weekly GTM review meeting running
- [ ] Win/loss tracking started
- [ ] Sales team feedback on positioning / objections captured

---

### 4.4 Launch Types — Choosing the Right One

| Launch Type | When to use | Example |
|------------|-------------|---------|
| **Major launch (Big Bang)** | New product or major platform update | EV Diagnostic Suite launch at Automotive Testing Expo |
| **Feature launch** | Significant new capability | New fleet compliance dashboard |
| **Quiet launch** | Minor improvement; limited audience | Bug fix release; API parameter update |
| **Beta launch** | Early access to target customers | Invite 5 OEM partners to try new feature before GA |
| **Phased rollout** | Risk management; large user base | OTA update to 10% → 30% → 100% of fleet |

---

### 4.5 GTM Communication — Launch Message by Audience

| Audience | Message focus | Channel |
|----------|--------------|---------|
| OEM Product Director | Strategic value, compliance, time-to-market | Direct meeting + 1-pager |
| OEM Engineering Lead | Technical integration, API, certifications | Technical brief + demo |
| OEM Procurement | Pricing, licensing terms, ROI model | Proposal document |
| End users | What's new, how to use it | In-app message, email, release notes |
| Press / industry | Market significance, product capabilities | Press release, analyst briefing |
| Internal Sales | Competitive positioning, objection handling | Battle card, sales playbook |

---

## CHAPTER 5 — PRODUCT LAUNCH PLAYBOOK

### 5.1 T-8 Weeks to Launch — PM Checklist

| Week | PM Actions |
|------|-----------|
| T-8 | Finalise product scope; freeze requirements; align engineering on scope |
| T-7 | Draft positioning and messaging; validate with 2 target customers |
| T-6 | Sales training material drafted; pricing confirmed; demo environment built |
| T-5 | Beta customer outreach — book 3 beta users; internal UAT begins |
| T-4 | Beta feedback integrated; bug triage; cut-off decision for deferred items |
| T-3 | Launch materials final — press release, sales deck, product brief |
| T-2 | All go/no-go criteria defined; launch day plan agreed |
| T-1 | Final go/no-go decision with engineering and leadership |
| T-0 | Launch! Monitor metrics dashboard hourly for 48 hours |
| T+2 weeks | First post-launch review — metrics, pipeline, feedback |

---

### 5.2 Go / No-Go Decision Framework

**Go criteria (ALL must be true):**
- [ ] All Must-Have features shipped and tested
- [ ] P1 and P2 bugs resolved; no open P1 bugs
- [ ] Performance SLAs met (latency, load test)
- [ ] Security review signed off
- [ ] Legal / compliance sign-off received
- [ ] OEM acceptance testing passed (if contractual)
- [ ] On-call rotation and incident response plan in place
- [ ] Roll-back procedure tested and ready

**No-Go triggers:**
- Any open P1 bug
- Performance SLA failure in load testing
- Missing safety/compliance sign-off
- Customer sign-off not received against contractual requirement

---

### 5.3 Post-Launch Review Template

**Review at 2 weeks, 1 month, and 3 months post-launch.**

| Section | Content |
|---------|---------|
| Launch execution | What went to plan? What didn't? |
| Metrics vs targets | Key metrics table — target vs actual vs trend |
| Customer feedback | Top 5 positive themes; Top 5 negative themes |
| Pipeline update | Deals influenced; design wins; OEM feedback |
| Issues in the field | Any critical defects, incidents, or escalations |
| Roadmap implications | What does this data tell us about the next build? |
| Action owners | Named owner + date for each follow-up action |

---

## CHAPTER 6 — CUSTOMER SUCCESS & RETENTION

### 6.1 The PM's Role in Customer Success

PMs own the product. But product retention is inseparable from customer success.

**PM responsibilities post-launch:**
- Define the onboarding success criteria (what does activation look like?)
- Identify customers at risk (low adoption, support tickets, NPS drops)
- Feed field feedback into the product roadmap
- Conduct quarterly product reviews with strategic accounts
- Define renewal / upsell signals for the CS team

---

### 6.2 Health Score Model (B2B SaaS + Automotive)

| Signal | Weight | Score input |
|--------|--------|------------|
| Feature adoption rate | 30% | % of contracted features actively used |
| OTA completion rate | 25% | % fleet on latest SW |
| Support ticket volume | 20% | Inverse — fewer = healthier |
| NPS / CSAT | 15% | Most recent survey score |
| Engagement recency | 10% | Days since last PM or CS contact |

**Health score → Action:**
- 80–100: Healthy → Protect, upsell opportunity
- 60–79: Monitor → Check in, QBR
- 40–59: At risk → Executive engagement, recovery plan
- <40: Critical → Senior escalation, save programme

---

### 6.3 Quarterly Business Review (QBR) for Strategic Accounts

**Agenda (90-minute format):**

1. **Review (30 min):** Metrics vs targets last quarter — OTA rate, compliance, uptime
2. **Issues + resolutions (20 min):** Any incidents, how resolved, systemic fixes
3. **Roadmap preview (20 min):** What's coming, how it maps to the OEM's goals
4. **OEM needs (15 min):** Open floor — what's on their mind for the next 6 months?
5. **Commitments (5 min):** Named actions from both sides, with dates

**Rule:** The PM owns the agenda and drives the product discussion. Sales owns the commercial discussion. Both attend.

---

*File: 05_stakeholder_gtm.md | Product Manager Interview Prep | April 2026*

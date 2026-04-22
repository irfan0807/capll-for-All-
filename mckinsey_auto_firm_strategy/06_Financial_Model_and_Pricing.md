# 06. Financial Model & Pricing Strategy

**Confidential Strategic Document**  
**Prepared by:** Strategic Consulting Group  
**Date:** April 2026  
**Subject:** Revenue Architecture, Margins, and Rate Card Design

---

## 1. The Business Model Spectrum
Most automotive consulting firms start at "Body Shopping" (lowest margin) and should evolve toward "IP-Led Solutions" (highest margin). Your strategy is to move up this ladder as fast as possible.

```
LOW MARGIN                                                HIGH MARGIN
|----------------------------------------------------------|
Body Shop      → Time & Materials  → Fixed Price  → Productized
(Staff Aug.)     (T&M Projects)      SoW Projects    IP Platform
  15–30%           25–40%              35–55%          60–80%
```

**Year 1:** Primarily T&M and Fixed-Price SoW projects to build cash flow and credibility.  
**Year 2–3:** Introduce a proprietary test automation platform and licensed tool components.

---

## 2. The Rate Card — What to Charge

All rates in EUR/hour. Adjust for market (USD, GBP, INR equivalent).

### Consulting Rates — European/US Market (Onshore)
| Role | Market Rate (EUR/hr) | Your Target Rate | Notes |
|---|---|---|---|
| Principal / Solution Architect | €150–180/hr | €155–175/hr | Strategy, architecture design |
| Senior CAPL/HIL Engineer (8+ yrs) | €110–140/hr | €115–130/hr | Leads delivery on complex projects |
| Mid CAPL/Python Engineer (4–7 yrs) | €85–110/hr | €90–105/hr | Core delivery team |
| Junior Test Engineer (0–3 yrs) | €55–75/hr | €60–70/hr | After internal boot camp |
| Functional Safety (ISO 26262) Specialist | €135–160/hr | €140–160/hr | Rare, premium role |
| Project / Delivery Manager | €95–120/hr | €100–115/hr | 20% management overhead |

### Blended Rate Strategy (Your Key Margin Lever)
You bill the client a **blended rate** (e.g., €110/hr for "Senior Engineer") but deliver with a team of:
* 1x Mid Engineer (your cost: €65/hr)
* 1x Junior Engineer (your cost: €30/hr)

**Effective margin on this arrangement: ~50–60%.**

---

## 3. Pricing Models for Different Engagements

### Model A: Fixed-Price Proof of Concept (PoC) — Best for First Contact
Used to land new clients with a low-risk entry. Scope is fixed and narrow, so you can price it precisely and execute it profitably.

**Example PoC Offering:**
> *"UDS Automated Diagnostic Suite PoC"*  
> Scope: Automate 20 diagnostic test cases (SID 0x22, 0x19, 0x27) in CANoe/CAPL for one ECU.  
> Price: **€12,000 fixed** (2 weeks, 1 Senior + 1 Junior engineer).  
> Deliverable: Working CAPL scripts, HTML test report, reusable function library.
>
> Internal Cost: ~€5,500. **Gross Margin: ~54%.**

### Model B: Time & Materials (T&M) — Best for Ongoing Engagements
Standard for long-term V&V projects (3–12 months).
* Negotiate a minimum monthly commitment (e.g., 120 hrs/month) to guarantee revenue.
* Add a "tooling & license pass-through" line to cover CANoe/vTestStudio seat costs billed at cost+15%.

### Model C: Retainer / Managed Service — Best for Year 2+
Once you have an established relationship with a client, propose a monthly retainer model.

**Example Retainer Structure:**
* **€18,000/month** flat fee for up to 160 hrs of Senior CAPL engineering + test management.
* Additional hours billed at €120/hr.
* Client benefit: predictable budget, guaranteed capacity. Your benefit: predictable recurring revenue.

---

## 4. Financial Projections — 3-Year Model

### Revenue Targets
| Year | Revenue Target | Number of Active Clients | Avg. Monthly Revenue per Client |
|---|---|---|---|
| Year 1 | €350,000 | 3–4 | €8,000–€12,000/month |
| Year 2 | €900,000 | 8–10 | €8,000–€12,000/month |
| Year 3 | €2,000,000 | 15–18 | €10,000–€15,000/month |

### Year 1 Monthly Cash Flow Model (Break-Even Analysis)
| Cost Item | Monthly Cost (EUR) |
|---|---|
| Founder Salary (1 person) | €5,000 |
| 1 Senior Subcontractor | €8,000 |
| 1 Junior Employee | €2,800 |
| Office / Coworking | €500 |
| CANoe License (1 seat) | €800 |
| Legal / Accounting | €600 |
| Marketing (LinkedIn Ads, events) | €500 |
| **Total Monthly Burn** | **€18,200** |

**Break-Even Revenue (at 50% gross margin): ~€36,400/month = €437,000/year.**

This is achievable with 2–3 active T&M clients at €110/hr blended rate, billing 100+ hours/month each.

---

## 5. The "Land and Expand" Revenue Strategy
No single contract is the goal. The goal is expanding a client's spend with you over time.

* **Month 1–3 (Land):** €15,000 fixed PoC for one specific module/ECU.
* **Month 4–6 (Expand):** T&M engagement to expand the test coverage to 3 more ECUs.
* **Month 7–12 (Own):** Full V&V function outsourcing — become the de facto testing team for their entire platform.
* Year 2 (Entrench): Propose a Managed Test Service retainer and hire dedicated engineers to serve only this account.

**Single client potential: €15,000 → €250,000+ in Year 2.** This is why deep delivery quality on the first PoC is everything.

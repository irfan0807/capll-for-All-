# 08. Sales Outreach Playbook

**Confidential Strategic Document**  
**Prepared by:** Strategic Consulting Group  
**Date:** April 2026  
**Subject:** Step-by-step B2B Sales Process, Scripts, and Pipeline Management

---

## 1. The Automotive B2B Sales Reality
* Automotive procurement operates on **trust, risk mitigation, and compliance**, not price alone.
* A new vendor who walks in cold will spend **6–18 months** in the vendor approval process before seeing a PO.
* The primary hack to compress this timeline is **bypassing procurement entirely until the technical stakeholder is already sold.**

**The Core Rule:** Sell to the Engineer first. Procurement follows where the engineer leads.

---

## 2. Your Ideal Contact Persona (Priority Order)

| Priority | Title | Pain Point They Own |
|---|---|---|
| **#1 — Primary Target** | V&V Manager / Test Manager | "We are behind on test coverage and cannot hire CAPL engineers." |
| **#2 — Secondary Target** | ECU Software Architect / System Integration Lead | "Our manual test process is a bottleneck in our CI/CD pipeline." |
| **#3 — Warm Introduction** | Engineering Director / VP of R&D | Has the budget authority but needs a technical champion below. |
| **#4 — Avoid Initially** | HR / Talent Acquisition / Procurement | They will route you into a 12-month supplier registration audit. |

---

## 3. Lead Generation — Finding the Right Targets

### Method A: LinkedIn Sales Navigator Hack (The Job Posting Indicator)
This is the single most effective targeting method.

**The Logic:** A company that has been advertising a "CAPL Engineer" or "HIL Test Engineer" position for 60+ days is experiencing active, urgent pain. They cannot solve the problem by hiring. They are primed for outsourcing.

**Steps:**
1. In LinkedIn Sales Navigator, search for "CAPL Engineer" or "HIL Test Engineer" job postings.
2. Filter to postings older than 60 days and posted by Tier-1 automotive companies.
3. Identify the hiring manager or team lead — this is your first contact.
4. Send the InMail message (see Section 4 below).

### Method B: GitHub / StackOverflow Technical Watering Holes
Search GitHub for automotive companies with public repositories containing CANoe/CAPL-related code. If a company is trying to build internal tooling across these public channels, they may be severely understaffed.

### Method C: Conference & Trade Show Engagement
Target events where your buyers physically gather:
* **Embedded World** (Nuremberg, Germany) — primary target.
* **AutoSens** (Brussels) — ADAS validation community.
* **SAE World Congress** (Detroit) — OEM and Tier-1 systems engineers.
* **Vector Congress** — Vector tool users, the most targeted audience imaginable.

Do not pay for a booth in Year 1. Attend, network aggressively, and host a side breakfast or dinner event for 15–20 targeted people.

---

## 4. Outreach Scripts & Templates

### 4.1 LinkedIn InMail — Cold Outreach to V&V Manager
> **Subject:** CAPL automation for [Company Name]'s validation bottleneck  
>
> Hi [First Name],
>
> I saw that [Company Name] has been looking for CAPL/CANoe engineers for [X weeks] — a search that resonates with me because it's a problem almost every Tier-1 faces right now: the demand for validation engineers is outpacing the talent market by a significant margin.
>
> We are a specialist automotive validation firm. We've helped similar teams [briefly describe anonymized result, e.g., "reduce a 4-day manual regression cycle to a 2-hour automated run in CANoe vTestStudio."]
>
> I'm not pitching a retainer. I'd like to offer a 2-week fixed-price Proof of Concept — we pick your most painful manual test suite, automate it, and hand you back the CAPL scripts, an HTML report, and a reusable function library regardless of outcome.
>
> Is a 15-minute call next week worth exploring this?
>
> Best regards,  
> [Your Name]  
> [Your Title], [Your Company]

### 4.2 Follow-Up Email (Day 5 — No Response)
> **Subject:** Re: CAPL automation — quick question
>
> Hi [First Name],
>
> Dropping a quick follow-up. I realize my last message was a bit forward without context.
>
> Single question: Is automated CAPL regression testing integrated into your current CI pipeline, or is it still largely a manual handoff?
>
> I ask because the answer shapes whether what we do is relevant for your team right now.
>
> [Your Name]

### 4.3 LinkedIn Comment Engagement (Warm Approach)
Before sending a cold message, engage with the target's recent LinkedIn posts (if they post technical content) with a substantive technical comment, not just a "like." This creates name recognition and makes the follow-up message warm instead of cold.

### 4.4 Post-Event Follow-Up (After a Conference)
> **Subject:** Great speaking with you at [Event Name]
>
> Hi [First Name],
>
> It was a genuine pleasure discussing [topic you spoke about] at [Event Name]. Your point about [specific thing they mentioned] was insightful.
>
> As I mentioned, we work almost exclusively on CAPL and HIL automation for powertrain/ADAS teams. Given what you described about your team's current challenges with [pain point discussed], I'd love to put together a concrete 30-minute walkthrough of how we handled a nearly identical situation for a similar team.
>
> No commitment — just a technical conversation. Do you have 30 minutes in the next two weeks?

---

## 5. The 7-Stage Sales Pipeline

Track every prospect through these stages in your CRM (HubSpot Free or Notion).

| Stage | Definition | Goal |
|---|---|---|
| **1. Suspect** | Company identified as ICP match. No contact yet. | Research the company, identify the target persona. |
| **2. Prospect** | Initial contact made (InMail sent, comment made). | Get a response — any response. |
| **3. Connected** | Two-way communication initiated. | Qualify: Do they have active pain + budget? |
| **4. Discovery Call** | A 15–30 min call about their challenges. | Identify a specific, scoped problem to solve. |
| **5. Proposal Sent** | Formal proposal submitted. | Proposal reviewed by decision maker. |
| **6. Negotiation** | Client has questions on scope/price. | Resolve objections, protect scope and price. |
| **7. Closed Won / Lost** | SoW signed or engagement ended. | Log lessons learned. |

**Target Pipeline Health (Year 1):**
* 30 active Suspects
* 15 active Prospects
* 8 in Discovery
* 4 active Proposals
* 2 in Negotiation
* 1–2 Closed per quarter

---

## 6. Handling Common Objections

| Objection | Root Fear | Your Response |
|---|---|---|
| "We only work with approved vendors." | Risk. You are unknown. | "Understood. Our first engagement is a fixed-price PoC — no PO needed in most cases under the purchase thresholds. Let's start small and earn approval." |
| "Your company is too new / too small." | Execution risk. | "We are small by design. Your project will not be handed to a junior team. The engineers on your proposal are the engineers delivering the work." |
| "We can do this internally." | They don't want to pay. | "Absolutely — and your team may well be capable. Our question is whether they have the available bandwidth, given the open positions. We de-risk your timeline." |
| "Your rate is too high." | Budget pressure. | "Let me show you the ROI math. Our automated framework eliminates [X hrs/week] of manual testing. At your internal engineering cost of €X/hr, you break even in [Y] weeks." |

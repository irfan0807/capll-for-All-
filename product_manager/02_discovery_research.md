# Product Manager — Discovery & Customer Research
## April 2026

---

## CHAPTER 1 — WHY DISCOVERY MATTERS

> **"The biggest risk is building the right thing the wrong way. The second biggest risk is building the wrong thing perfectly."**
> — Marty Cagan, *Inspired*

Product failures are rarely caused by technical issues. They are caused by:
- Building features no one needed (wrong problem)
- Solving the right problem in the wrong way (wrong solution)
- Building for the wrong user (wrong persona)
- Building at the wrong time (wrong market timing)

**Discovery is the PM's primary tool to avoid all four.**

---

## CHAPTER 2 — THE DISCOVERY PROCESS

### 2.1 Discovery Phases

```
PHASE 1           PHASE 2           PHASE 3           PHASE 4
PROBLEM           PROBLEM           SOLUTION          SOLUTION
DISCOVERY         DEFINITION        EXPLORATION       VALIDATION
──────────        ──────────        ──────────        ──────────
Interviews        Problem           Ideation          Prototype
Observation       statement         Concept testing   User testing
Surveys           Personas          Wireframes        A/B tests
Analytics         JTBD mapping      Paper prototypes  Fake door
Data review       Opportunity       Feature concepts  Landing page
                  scoring                             Concierge test
```

---

### 2.2 The 5 Discovery Questions

Every discovery effort should answer:

1. **Who is the customer?** Specific person with a specific context — not "users" generically
2. **What is their problem?** What job do they need done that is currently unsatisfied?
3. **What is the current solution?** How are they solving it today? What workarounds exist?
4. **What is the REAL cost of the problem?** Why does it matter? (Time, money, risk, frustration)
5. **What would the ideal outcome look like?** Not in product terms — in customer outcome terms

---

## CHAPTER 3 — USER INTERVIEWS

### 3.1 Interview Principles

| Do | Don't |
|----|-------|
| Ask open-ended questions | Ask leading questions ("Would you use a feature that...?") |
| Listen 80%, talk 20% | Pitch your solution mid-interview |
| Ask "Tell me about a time..." | Ask hypothetical future questions |
| Probe emotions: "How did that make you feel?" | Accept surface-level answers |
| Ask "Why?" at least 3 times | Interrupt |
| Note body language and hesitations | Defend your product idea |
| Get specific, concrete stories | Accept vague generalisations |

---

### 3.2 The Mom Test (Rob Fitzpatrick)

The Mom Test says: ask questions that your *mother cannot lie to you about* — questions that reveal reality through behaviour and past actions, not opinions about the future.

**Bad questions (opinion about imagined future):**
- "Would you pay for this?"
- "Do you think this is a good idea?"
- "Would you use an app that did X?"

**Good questions (past behaviour, real context):**
- "Walk me through the last time you dealt with this problem."
- "What did you do when that happened?"
- "What tools or workarounds do you use today?"
- "What was the most frustrating part?"
- "What has stopped you from solving this already?"

---

### 3.3 Interview Guide Template

**Interview type:** Problem Discovery
**Duration:** 45–60 minutes
**Goal:** Understand [customer] pain around [problem area]

---

**Opening (5 min):**
- Thank you for your time. Today I want to learn from your experience — there are no right or wrong answers, and I'm not selling anything in this conversation.
- Can you briefly describe your role and what a typical day looks like?

**Context setting (10 min):**
- Tell me about how you currently [deal with the problem area].
- How often does this come up in your work?
- Who else is involved when this happens?

**Problem exploration (20 min):**
- Walk me through the last time you had to [do the relevant task].
- What was the most frustrating part of that?
- What did you do when you hit that moment of friction?
- Have you tried any tools or approaches to solve this? What happened?
- What has prevented you from solving this completely?

**Outcome exploration (10 min):**
- If this problem were completely solved, what would that look like for you?
- What would you be able to do that you can't do today?
- What would change in your work / team / business outcomes?

**Closing (5 min):**
- Is there anything important I haven't asked about?
- Who else in your team or organisation faces this problem?
- Would you be open to me sharing some early concepts for your feedback?

---

### 3.4 Synthesis — Affinity Mapping

After 5+ interviews, synthesise findings:

1. Write one insight per sticky note (digital or physical)
2. Cluster similar insights together into themes
3. Label each theme
4. Rank themes by frequency and severity
5. Identify the top 3 customer pain clusters

**Output:** An evidence-based problem statement:

> "**[Persona]** who **[context]** struggle with **[problem theme]** because **[root cause]**, which results in **[pain / consequence]**. This matters because **[business or safety impact]**."

---

## CHAPTER 4 — PERSONAS & CUSTOMER SEGMENTATION

### 4.1 Persona Template

**Persona name:** [Memorable fictional name]
**Role:** [Job title]
**Company type:** [OEM / Tier-1 / Fleet operator / Consumer]
**Experience level:** [Years in role, technical depth]

**Goals:**
- What are they trying to achieve professionally?
- What does success look like for them?

**Pain points:**
- What frustrations do they face in their daily work?
- What is the biggest blocker between them and their goal?

**Behaviours:**
- How do they currently solve the problem?
- What tools do they use?
- How do they make decisions?

**Quotes (from real interviews):**
> "The biggest issue is I don't know if the fault codes I'm seeing mean the car needs to stop now or just visit a dealer next week."

**Influence on product:**
- What does this persona care most about in the product?
- What would cause them to reject the product?

---

### 4.2 Automotive PM Personas

**Persona 1 — OEM Digital Product Lead**
- Goal: Ship connected vehicle features that differentiate their brand
- Pain: Supplier integration takes 18 months; needs faster solutions
- Quote: "I need UNECE compliant OTA in this year's model. I can't wait 18 months for a custom build."

**Persona 2 — Fleet Manager (B2B)**
- Goal: Ensure all fleet vehicles are compliant with latest software
- Pain: No visibility into which vehicles are running which SW version
- Quote: "I have 200 vehicles. I have no idea which 40 haven't updated."

**Persona 3 — Vehicle Owner (Consumer)**
- Goal: Drive confidently without worrying about hidden car problems
- Pain: Warning lights are alarming and incomprehensible
- Quote: "The yellow light came on and I just didn't know if it was safe to drive to work."

**Persona 4 — ADAS Validation Engineer**
- Goal: Execute test cases efficiently and generate compliant evidence
- Pain: Test tooling is disconnected; manually assembling evidence wastes time
- Quote: "I spend 30% of my time formatting test results for audit reports. I should be testing."

---

## CHAPTER 5 — JOBS-TO-BE-DONE (JTBD)

### 5.1 JTBD Framework Explained

Customers don't want your product — they want to make progress in their life. They "hire" your product to make that progress.

**Three elements of a Job:**
1. **Functional job:** The practical task ("Get my car's fault diagnosed")
2. **Emotional job:** How it makes them feel ("Feel confident driving")
3. **Social job:** How it affects how others see them ("Look like a responsible vehicle owner")

**JTBD Format:**
> When [situation], I want to [motivation], so I can [outcome].

---

### 5.2 JTBD Examples — Automotive Products

| Persona | When (Situation) | Want (Motivation) | So I Can (Outcome) |
|---------|-----------------|-------------------|--------------------|
| Vehicle Owner | The DTC warning light illuminates | Know if it's safe to keep driving | Decide without anxiety or Googling |
| Fleet Manager | Monthly SW audit is due | See all vehicle SW versions in one place | Submit compliance report in 30 min, not 3 hours |
| OEM Product Lead | An OTA update fails on 3% of vehicles | Know root cause quickly | Reassure the regulatory team and fix within SLA |
| ADAS Engineer | A new OEM project starts | See all required DIDs/DTCs in a structured spec | Begin implementation without ambiguous requirements |
| Vehicle Service Tech | A customer brings in a vehicle with a DTC | Read and clear DTCs using a standard tool | Complete diagnosis without specialist training |

---

### 5.3 Job Story vs User Story

| Format | User Story | Job Story |
|--------|-----------|-----------|
| Focus | Role | Situation and motivation |
| Template | As a [user], I want [feature], so that [benefit] | When [situation], I want [motivation], so I can [outcome] |
| Problem | Focuses on a solution (feature) | Focuses on the problem (context + outcome) |
| Better for | Delivery backlog | Discovery and design |

---

## CHAPTER 6 — PROBLEM FRAMING

### 6.1 The 5 Whys

Use to find the root cause of a user problem — never accept the first answer.

**Example:**
- **Surface complaint:** "The OTA update failed."
- Why 1: "Because the download timed out."
- Why 2: "Because the file was too large for the connection speed."
- Why 3: "Because we don't check connection quality before starting a download."
- Why 4: "Because we designed the OTA client for 4G LTE and assumed good connectivity."
- Why 5: "Because our user research only covered urban users — 22% of our fleet operates in rural/low-bandwidth zones."
- **Root cause:** The OTA design assumption was wrong for the full user population.
- **Right fix:** Adaptive download strategy based on real-time connection quality — not a bigger timeout.

---

### 6.2 Problem Statement Template

> **Problem:** [Persona] who [context / situation] struggle to [achieve goal / task] because [root cause]. As a result, they [negative consequence]. We know this because [evidence — data, interviews, observations].

**Example:**
> **Problem:** Vehicle owners who receive a dashboard warning light struggle to assess whether it is safe to continue driving because there is no accessible, plain-language interpretation of DTC severity. As a result, they either ignore the warning (safety risk) or immediately stop driving unnecessarily (inconvenience and loss of trust). We know this because 7/8 user interviews showed immediate Google search behaviour upon DTC events, and our analytics show 41% app abandonment at OTA consent screens suggesting a general pattern of low technical confidence.

---

### 6.3 Reframing Exercises

| Original statement (assumed solution) | Reframed problem statement |
|---------------------------------------|---------------------------|
| "We need a DTC notification feature" | "Users need to know whether a fault is serious enough to act on immediately" |
| "We need a faster download speed" | "Users need to feel confident the update won't disrupt their day" |
| "We need better documentation" | "Engineers need to find the information they need in under 2 minutes" |
| "We need a dashboard" | "Fleet managers need to prove SW compliance to regulators in one step" |

---

## CHAPTER 7 — SURVEYS & QUANTITATIVE RESEARCH

### 7.1 When to Use Surveys

Use surveys to **validate** what you found in qualitative interviews — not to replace them.

- Surveys tell you **how many** people have a problem
- Interviews tell you **why** and **what it's like**

---

### 7.2 Survey Design Principles

| Do | Don't |
|----|-------|
| One question per question | Double-barrelled questions ("Is it fast AND easy?") |
| Use Likert scales consistently (1–5 or 1–7, not mixed) | Mix scale directions |
| Test the survey with 3 people before sending | Send to the full list immediately |
| Include one open-ended question at the end | Make the survey >10 minutes |
| State clearly how data will be used | Ask for sensitive data without explanation |

---

### 7.3 Net Promoter Score (NPS)

**Question:** "How likely are you to recommend [product] to a colleague?" (0–10)

- 9–10: **Promoters**
- 7–8: **Passives**
- 0–6: **Detractors**

**NPS = % Promoters − % Detractors**

| Score | Interpretation |
|-------|---------------|
| >70 | World class (Apple, Tesla) |
| 50–70 | Excellent |
| 30–50 | Good |
| 0–30 | Needs improvement |
| <0 | Urgent action required |

**NPS is a lagging indicator.** Always follow up with: "What's the main reason for your score?" — the qualitative answer is more actionable than the number.

---

## CHAPTER 8 — COMPETITIVE ANALYSIS

### 8.1 Competitive Analysis Framework

| Competitor | Key Strengths | Key Weaknesses | Target Customer | Price Point | Differentiation |
|------------|--------------|----------------|-----------------|-------------|----------------|
| Competitor A | Brand, distribution | Expensive, slow integration | Top-tier OEMs | Premium | Legacy relationships |
| Competitor B | Low cost | No safety certification | Low-volume OEMs | Budget | Price |
| Our product | Certified, fast integration, configurable | Smaller sales team | Mid-market OEMs | Mid-tier | Speed + compliance |

---

### 8.2 Feature Comparison Matrix

| Feature | Our Product | Competitor A | Competitor B |
|---------|------------|--------------|--------------|
| ISO 26262 ASIL-B certified | ✅ | ✅ | ❌ |
| UNECE R156 OTA compliant | ✅ | ✅ | ❌ |
| Integration time | 8 weeks | 18 months | 6 weeks |
| Configurable per OEM | ✅ | ❌ (custom per project) | ✅ |
| EV BMS diagnostics | ✅ | ❌ | ❌ |
| Multi-OEM pricing model | Per vehicle type | Per programme | Per programme |
| Fleet management dashboard | ✅ | ❌ | ❌ |

---

### 8.3 Win/Loss Analysis

After every won or lost deal, interview the decision-maker:

**Won deal questions:**
- What specifically tipped you toward our product?
- Where did our competitors fall short in your evaluation?
- What nearly made you choose someone else?

**Lost deal questions:**
- When in the process did you decide not to choose us?
- What did the winning alternative offer that we didn't?
- Is there anything we could have done differently?

**Look for patterns across 10+ interviews** — themes reveal true competitive position.

---

## CHAPTER 9 — HYPOTHESIS-DRIVEN DEVELOPMENT

### 9.1 Hypothesis Format

> **We believe** [assumption about user/problem/solution]
> **Is true for** [target user / persona]
> **We will know this is true when** [measurable outcome]

**Example:**
> We believe that showing plain-language DTC severity (Safe to drive / Visit dealer / Stop now) instead of raw DTC codes is valued more by non-technical vehicle owners.
> We will know this is true when >70% of test users in a usability study correctly identify the correct action from the severity notification, and app store ratings from the update version improve by >0.5 stars.

---

### 9.2 Experiment Types (by speed and cost)

| Experiment Type | Speed | Cost | Best for |
|----------------|-------|------|---------|
| User interview | Fast | Very low | Problem validation |
| Paper prototype | Fast | Very low | Concept/flow |
| Clickable wireframe | Medium | Low | Navigation, task flow |
| Fake door / landing page | Fast | Low | Demand validation |
| Concierge test | Medium | Medium | Solution concept (manual delivery) |
| A/B test | Slow | Medium | Optimisation of known flows |
| Beta programme | Slow | High | Pre-release product validation |

**Rule:** Use the cheapest, fastest experiment that will de-risk the assumption. Don't run an A/B test when a 2-hour interview would answer the question.

---

*File: 02_discovery_research.md | Product Manager Interview Prep | April 2026*

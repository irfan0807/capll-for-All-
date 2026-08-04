# Requirements Analysis / Requirements Engineering in the Automotive Industry
## A Complete Study & Practice Guide

---

## 0. Why This Matters and How to Use This Guide

Requirements Engineering (RE) is the discipline that everything else in automotive development — architecture, design, coding, testing, safety, and validation — traces back to. A weak requirement is the single most common root cause of late-stage defects, safety case gaps, and validation rework. This guide takes you from fundamentals to the mindset and habits of a senior/expert-level Requirements Analysis Engineer.

Structure:
1. Foundations — what a requirement is and the taxonomy used in automotive
2. The Automotive RE lifecycle (V-Model placement)
3. Standards and frameworks that govern automotive requirements (ASPICE, ISO 26262, ISO 29148, ISO 21434)
4. Rules for writing a good requirement (with automotive-specific examples)
5. Elicitation methods
6. Analysis, specification, and modeling methods
7. Requirements management: traceability, change, baselining
8. Tools of the trade
9. Verification of requirements (yes — requirements themselves are verified)
10. Common failure modes / anti-patterns in automotive requirements
11. How your test/validation background is an asset
12. Path to becoming an excellent Requirements Engineer — habits, checklists, study plan

---

## 1. Foundations

### 1.1 What Is a Requirement?
A **requirement** is a statement that identifies a necessary attribute, capability, characteristic, or quality of a system for it to have value to a stakeholder (ISO 29148 definition, paraphrased). In automotive, a requirement must be simultaneously:
- **Correct** — accurately reflects stakeholder/customer intent
- **Unambiguous** — one and only one interpretation
- **Verifiable** — a test/analysis/inspection can prove it's met
- **Necessary** — traces to a real stakeholder need
- **Feasible** — achievable within technical/cost/schedule constraints
- **Consistent** — doesn't conflict with other requirements

### 1.2 Requirements Taxonomy (Automotive-Specific Layers)

| Level | Description | Typical Owner |
|---|---|---|
| **Stakeholder / Customer Requirements** | What the OEM/market/regulator wants (vehicle-level) | Product Management / Systems Engineering |
| **System Requirements** | What the item/system must do to satisfy stakeholder requirements | Systems Engineer |
| **Functional Requirements** | Specific behaviors of the system | Systems/Function Engineer |
| **Non-Functional Requirements (NFRs)** | Performance, timing, reliability, usability, EMC, environmental | Systems Engineer / Domain SMEs |
| **Software Requirements** | Allocated to software components | Software Architect/Engineer |
| **Hardware Requirements** | Allocated to hardware/ECU | Hardware Engineer |
| **Safety Requirements** (FSR/TSR/SW-HW Safety Reqs) | Derived per ISO 26262 from Safety Goals | Functional Safety Engineer |
| **Interface Requirements** | Signal-level, protocol-level (CAN/LIN/Ethernet, UDS) definitions | Interface/Integration Engineer |

Understanding **which layer** a requirement belongs to — and refusing to let requirements "jump levels" without traceable derivation — is one of the most important disciplines in automotive RE.

### 1.3 Requirement Types (Orthogonal Classification)
- **Functional** — "The system shall detect a lead vehicle within X meters."
- **Performance** — "The system shall issue a brake command within 150 ms of hazard detection."
- **Interface** — "The ECU shall transmit Object_List on CAN ID 0x3A2 at 20 ms cycle time."
- **Constraint** — "The software shall comply with MISRA C:2012."
- **Safety** — "The system shall transition to a safe state within the FTTI upon detection of sensor fault X."
- **Legal/Regulatory** — "The system shall comply with UNECE R157."

---

## 2. Where RE Sits in the Automotive V-Model

```
Stakeholder/Customer Requirements ─────────────────────────► Vehicle-Level Acceptance Test
        │                                                              ▲
        ▼                                                              │
   System Requirements ──────────────────────────────────► System Integration Test
        │                                                              ▲
        ▼                                                              │
  Functional/NFR Requirements ─────────────────────────► Function/Component Test
        │                                                              ▲
        ▼                                                              │
 SW/HW Requirements ──────────────────────────────────► Unit/Module Test
        │                                                              ▲
        └──────────────────► Design & Implementation ──────────────────┘
```

**The core rule of the V-Model for RE**: every requirement on the left side must have a defined, traceable verification method on the right side *before* design work begins on it. This is where a validation-engineering background (yours) becomes a superpower — you already think in terms of "how would I prove this requirement is true?"

---

## 3. Governing Standards and Frameworks

### 3.1 ISO 29148 (Systems and Software Engineering — Requirements Engineering)
- The generic international reference for RE process, requirement characteristics, and specification structure. Not automotive-specific but underlies most automotive RE process definitions.

### 3.2 Automotive SPICE (ASPICE) — the Real Day-to-Day Framework
ASPICE process areas most relevant to RE:

| Process | Name | Focus |
|---|---|---|
| **SYS.1** | Requirements Elicitation | Gathering stakeholder needs |
| **SYS.2** | System Requirements Analysis | Deriving/analyzing system-level requirements |
| **SYS.3** | System Architectural Design | Allocating requirements to architecture |
| **SYS.4** | System Integration and Integration Test | Verifying integrated system against SYS.2 |
| **SYS.5** | System Qualification Test | Verifying system against stakeholder requirements |
| **SWE.1** | Software Requirements Analysis | Deriving software requirements from system requirements |
| **SWE.2** | Software Architectural Design | — |

ASPICE assessments (rated on a capability scale, typically targeting Level 2 or 3) will directly probe:
- Bidirectional traceability (up to stakeholder needs, down to test cases)
- Consistency between requirement levels
- Requirements review records and defect closure evidence
- Impact analysis on change

**This is a core competency to master — ASPICE audits live or die on requirements traceability quality.**

### 3.3 ISO 26262 — Safety Requirements Specifics
- Functional Safety Requirements (FSR) and Technical Safety Requirements (TSR) are a *specialized subset* of requirements with additional rules: they must carry an ASIL, trace to a Safety Goal, and specify safe-state behavior explicitly (see your FuSa study guide for full depth).
- Every safety requirement must be verifiable with a defined test/analysis method — "unverifiable safety requirement" is a classic audit finding.

### 3.4 ISO 21434 — Cybersecurity Requirements
- Threat Analysis and Risk Assessment (TARA) generates cybersecurity requirements analogous to how HARA generates safety requirements. Increasingly, RE engineers must handle combined safety+security requirement sets without conflating them.

### 3.5 ISO 21448 (SOTIF)
- Generates requirements around performance limitations and triggering conditions (not just faults) — relevant if you're writing requirements for ADAS/perception functions.

---

## 4. Rules for Writing a Good Requirement

### 4.1 The INCOSE/EARS Structured Language Approach
Use **EARS (Easy Approach to Requirements Syntax)** patterns — widely adopted in automotive because they eliminate ambiguity:

| Pattern | Template | Example |
|---|---|---|
| Ubiquitous | The `<system>` shall `<response>` | The ECU shall log all DTCs to non-volatile memory. |
| Event-driven | WHEN `<trigger>`, the `<system>` shall `<response>` | WHEN the brake pedal is pressed, the system shall disengage ACC within 100 ms. |
| State-driven | WHILE `<state>`, the `<system>` shall `<response>` | WHILE in Standby mode, the system shall not actuate the brake. |
| Unwanted behavior | IF `<trigger>`, THEN the `<system>` shall `<response>` | IF a radar fault is detected, THEN the system shall transition to Degraded mode. |
| Optional feature | WHERE `<feature is included>`, the `<system>` shall `<response>` | WHERE the Highway Assist option is enabled, the system shall support hands-off steering. |
| Complex | Combination of the above | WHEN the vehicle speed exceeds 60 km/h WHILE in Autopilot mode, the system shall... |

### 4.2 Language Rules (Automotive Style Guides — e.g., INCOSE Guide, OEM-specific)
- Use **"shall"** for mandatory requirements, never "should," "will," or "must" (reserve "will" for statements of fact, "should" for goals/recommendations, not requirements).
- One requirement = one testable statement. Never combine two "shall"s in one sentence ("and/or" is a red flag).
- Avoid vague terms: *fast, user-friendly, sufficient, appropriate, robust, minimal, easy* — quantify everything ("within 150 ms," not "quickly").
- Avoid open-ended lists: "including but not limited to" is not verifiable — enumerate exhaustively or don't use it.
- Use active voice with a clear subject: "The system shall..." not "It shall be ensured that..."
- Avoid negative requirements where possible ("shall not") unless they describe a genuinely necessary constraint — negatives are hard to verify exhaustively.
- No implementation detail in a system/functional requirement unless it is genuinely a constraint (don't specify "using a Kalman filter" in a functional requirement — that belongs in design).

### 4.3 The "5C" Quality Checklist (a widely used practical mnemonic)
- **Complete** — no missing conditions/exceptions
- **Consistent** — no conflicts with other requirements
- **Correct** — reflects actual stakeholder intent
- **Clear** — single interpretation
- **Checkable/Verifiable** — a test method exists

---

## 5. Elicitation Methods

Elicitation is where most requirement defects are actually born — not during writing, but during the failure to ask the right question of the right stakeholder.

| Method | When to Use |
|---|---|
| **Stakeholder interviews** | Early concept phase; OEM product managers, marketing, legal/regulatory |
| **Workshops (JAD-style)** | Cross-functional alignment sessions, especially at system-boundary decisions |
| **Use-case / Scenario analysis** | ADAS/AD functions — driving scenario catalogs (cut-in, cut-out, adverse weather) directly generate requirements |
| **Prototyping / Simulation-driven elicitation** | When stakeholders can't articulate needs abstractly — show them a driving simulator behavior and get reaction |
| **Regulatory/standard mining** | UNECE regulations, Euro NCAP protocols — directly translate into mandatory requirements |
| **Field data / warranty data analysis** | Requirements for the next generation often come from current-generation field issues |
| **Competitor benchmarking** | Especially for UX-type ADAS requirements (HMI behavior, feature parity) |
| **Model-Based elicitation (MBSE)** | Deriving requirements from system models (SysML) rather than prose-first |

---

## 6. Analysis, Specification & Modeling Methods

### 6.1 Requirements Analysis Techniques
- **Decomposition** — breaking stakeholder requirements into system requirements (must preserve traceability and completeness — no "requirement leakage").
- **Derivation review** — for every derived requirement, ask "is there a parent requirement or rationale? If not, why does this exist?"
- **Conflict analysis** — cross-checking requirement sets for contradictions (common between performance and safety requirements, e.g., responsiveness vs. false-positive suppression).
- **Boundary/interface analysis** — a huge automotive-specific discipline: precisely defining signal-level interfaces (CAN/LIN/Ethernet/UDS), including fault conditions, timing, and tolerances — your existing protocol background is directly applicable here.
- **Impact analysis** — when a requirement changes, systematically identify every downstream artifact (design, code, test case, safety case) affected.

### 6.2 Modeling Approaches (MBSE)
- **SysML** (Systems Modeling Language) — increasingly standard for automotive systems engineering; requirement diagrams, block definition diagrams (BDD), and traceability directly in the model.
- **Use Case / Sequence diagrams** — useful for interaction-heavy requirements (driver-system HMI flows).
- **State machines** — essential for mode/state-driven ADAS requirements (Standby → Active → Degraded → Fault → Safe State).
- Model-based RE reduces ambiguity dramatically compared to prose-only specs, and OEMs (including BMW) increasingly expect familiarity with it.

### 6.3 Requirement Specification Structure
A well-formed automotive Requirement Specification typically includes, per requirement:
- Unique ID (stable across baselines)
- Requirement text (EARS-formatted)
- Rationale
- Source/parent requirement link
- Verification method (Test / Analysis / Inspection / Demonstration)
- ASIL (if safety-relevant) / Security relevance (if applicable)
- Status (Draft / Reviewed / Approved / Baselined)
- Owner

---

## 7. Requirements Management

### 7.1 Traceability
- **Vertical traceability**: Stakeholder → System → Functional → SW/HW → Test Case (bidirectional — both "where does this come from" and "what does this affect downstream").
- **Horizontal traceability**: Requirement ↔ Safety Goal ↔ Security Goal ↔ Interface Spec — cross-domain consistency.
- Traceability isn't bureaucracy — it's what lets you answer "if I change this, what breaks?" and "why does this requirement exist?" in seconds instead of days.

### 7.2 Baselining and Change Management
- Requirements are **baselined** at defined milestones (gate reviews); changes after baseline go through formal Change Control Boards (CCB).
- Every change requires: impact analysis, re-verification scope, and re-approval from affected stakeholders (including safety/security if applicable).

### 7.3 Requirement Reviews
- **Peer review** — technical correctness, EARS compliance, ambiguity check.
- **Cross-functional review** — architecture feasibility, testability, safety/security alignment.
- **Formal walkthrough / inspection** (Fagan-style) — for safety-critical or high-ASIL requirement sets, structured inspection with defined roles (moderator, reader, recorder) catches far more defects than informal review.

---

## 8. Tools of the Trade

| Category | Common Tools |
|---|---|
| Requirements Management | IBM DOOORS / DOORS Next, Polarion, Jama Connect, Codebeamer |
| Modeling (MBSE) | Enterprise Architect, Rhapsody, Cameo Systems Modeler (SysML) |
| Traceability/ALM integration | Polarion, Codebeamer (often integrated with test management + safety case tools) |
| Requirements quality/NLP linting | Tools that automatically flag ambiguous terms, passive voice, missing "shall" |
| Version/Config Management | Integrated within DOORS/Polarion baselining, or Git-based for model artifacts |

**Practical note**: DOORS (classic or Next) remains the dominant tool at most German OEMs including BMW — deep familiarity with DOORS modules, links, and baselines is a strong, concrete skill to build if you haven't already.

---

## 9. Verifying Requirements Themselves

A subtlety many engineers miss: **requirements are work products that must themselves be verified**, separately from verifying that the *system* meets them.

- **Requirement-level verification checks**:
  - Every requirement has an assigned, feasible verification method.
  - No requirement is "TBD" or "TBC" at baseline (a common audit finding when left unresolved).
  - No orphan requirements (no parent) or dead-end requirements (no child/no test).
  - ASIL/security-relevant requirements have correct classification consistent with HARA/TARA outputs.

---

## 10. Common Failure Modes / Anti-Patterns in Automotive Requirements

| Anti-Pattern | Why It's a Problem |
|---|---|
| **Design masquerading as requirement** ("shall use a Kalman filter") | Over-constrains design, hides the actual need |
| **Compound requirements** ("shall detect and classify and track...") | Impossible to verify or trace atomically |
| **Vague/unverifiable adjectives** ("robust," "fast," "sufficient") | Fails the Verifiable/Checkable test |
| **Requirement creep without traceability** | Breaks impact analysis; classic ASPICE finding |
| **Copy-paste requirements across projects without re-validating applicability** | Leads to stale/irrelevant or contradictory requirements |
| **Safety requirements without an explicit safe state or FTTI** | Unverifiable, non-compliant with ISO 26262 |
| **Requirements written after the design/code (retro-fitted)** | Defeats the purpose of RE; common under schedule pressure — a red flag if found in audits |
| **No rationale captured** | Future engineers can't judge whether a requirement is still valid when context changes |

---

## 11. Why Your Validation Background Is a Real Asset

You already think operationally about "how do I prove this is true" — this is the single hardest mindset to teach requirements engineers who come from a pure specification background. Concrete transfer points:

| Your Experience | RE Skill It Builds Directly |
|---|---|
| CANoe/dSPACE-based test automation | Practical sense of what's actually verifiable at signal/protocol level — invaluable for writing verifiable interface requirements |
| UDS/DTC fault injection work | Strong instinct for writing precise "IF fault THEN response" (EARS unwanted-behavior pattern) requirements |
| Multi-domain ECU test suites (ADAS/Infotainment/Cluster/Telematics) | System-level thinking — you already work across the layers RE has to bridge |
| Python/pytest framework building | Useful for building or integrating requirement-to-test traceability tooling |
| ISO 26262 exposure | Direct transfer to safety requirement authorship (FSR/TSR), not just verification |

**Your natural next-step gap to close**: moving from "verifying requirements someone else wrote" to "authoring and defending requirements under review" — practice writing requirement sets from scratch for features you've already validated (reverse-engineer good EARS-format requirements from test cases you've already built) as a training exercise.

---

## 12. Path to Becoming an Excellent Requirements Analysis Engineer

### 12.1 Core Habits of Strong RE Engineers
1. **Ask "why" before "what."** Every requirement should trace to a real stakeholder need — if you can't state the rationale in one sentence, the requirement isn't ready.
2. **Write for the reviewer who wasn't in the room.** Assume zero context; ambiguity hides in shared assumptions.
3. **Think in test cases while writing requirements**, not after. If you can't picture the test, the requirement isn't verifiable yet.
4. **Default to precision over speed.** A requirement rushed to "Approved" status costs far more downstream than the time saved writing it.
5. **Treat traceability as a living safety net, not paperwork** — check it whenever a change lands, not just at audit time.
6. **Actively hunt ambiguous words** in your own writing (the "fast/robust/sufficient" list) before submitting for review.
7. **Engage early and often with adjacent disciplines** — safety, security, architecture, test — RE done in isolation always produces gaps.

### 12.2 Skill-Building Roadmap

| Stage | Focus |
|---|---|
| **Foundational (0–2 months)** | Master EARS syntax, ISO 29148 vocabulary, ASPICE SYS.1–SYS.5/SWE.1 process flow; get hands-on with DOORS or Polarion |
| **Intermediate (2–4 months)** | Practice full decomposition exercises (stakeholder → system → SW requirement) on a real or sample ADAS feature; build traceability matrices from scratch; learn SysML basics |
| **Advanced (4–6 months)** | Author safety/security-relevant requirement sets tied to HARA/TARA outputs; run/participate in formal requirement inspections; practice impact analysis on realistic change requests |
| **Expert / Leadership** | Own requirement quality gates for a program; mentor others on EARS/traceability discipline; represent RE in ASPICE assessments and safety/security audits |

### 12.3 Practical Self-Training Exercise (Recommended Starting Point)
Pick one ADAS function you've already validated (e.g., AEB or ACC):
1. Write the stakeholder requirement in plain language.
2. Decompose it into 5–10 system requirements using EARS patterns.
3. For each, define the verification method and sketch the test case.
4. Build a simple traceability table (Stakeholder → System → Test Case).
5. Have a peer (or yourself, a day later with fresh eyes) review it against the 5C checklist and the anti-pattern list in Section 10.

This single exercise, repeated across 4–5 features, will build more real RE competence than any amount of passive reading.

---

## 13. Quick-Reference Flashcards

- **Good requirement = Complete, Consistent, Correct, Clear, Checkable (5C)**
- **EARS patterns**: Ubiquitous / Event-driven (WHEN) / State-driven (WHILE) / Unwanted behavior (IF...THEN) / Optional (WHERE)
- **"Shall" = mandatory; "will" = fact; "should" = goal, not a requirement**
- **Traceability is bidirectional**: parent (why does this exist) + child (what verifies this)
- **ASPICE SYS.1→SYS.5, SWE.1→SWE.2** = the process backbone auditors check
- **A requirement with implementation detail baked in is a design decision in disguise**
- **Requirements are verified too** — no orphans, no TBDs at baseline, correct ASIL/security tagging
- **DOORS/Polarion/Jama/Codebeamer** = the tool landscape to be fluent in

---

*End of study guide.*



# STAR Interview Preparation — 20 Scenarios
## Requirements Analysis, Functional Safety & Team Leadership (BMW TechWorks Senior FuSa Engineer)

---

## How to Use This Document

These are **template STAR stories** — realistic automotive scenarios structured in Situation / Task / Action / Result format. They are starting frameworks, not claims about your actual history. Before the interview, replace the bracketed placeholders with real incidents from your own CAN/LIN/UDS/CANoe/dSPACE/ADAS validation work — even if the original incident wasn't framed as "requirements" or "safety" at the time, most validation engineers have lived through several of these situations already (a requirement that turned out to be untestable, a fault that was missed in review, a schedule-vs-quality tradeoff). Genuine specifics (numbers, tool names, exact failure modes) beat polished generic language every time.

Each entry includes: the likely interview question it answers, the STAR skeleton, and a coaching note on what the interviewer is really evaluating.

---

## Section A — Requirements Analysis & Engineering (7 Scenarios)

### 1. Catching an Unverifiable Requirement Before It Shipped
**Likely question**: "Tell me about a time you identified a problem with a requirement before it caused downstream issues."
- **S**: A requirement in a [feature, e.g., ACC or LKA] specification used vague language such as "the system shall respond appropriately" with no quantified timing or condition.
- **T**: As the [validation/requirements] engineer responsible for verifying this feature, you needed a testable, unambiguous requirement before test case design could begin.
- **A**: You flagged the ambiguity in review, proposed a rewritten EARS-format version with quantified timing (e.g., "WHEN X occurs, the system shall respond within Y ms"), and worked with the systems engineer to trace it back to the correct parent requirement.
- **R**: The requirement was corrected before baseline, preventing a costly re-spec cycle after test case design; quantify the outcome if you can (e.g., "avoided an estimated N days of rework").
- **Coaching note**: Interviewer wants to see you catch quality issues *proactively*, not just execute against whatever's handed to you.

### 2. Resolving a Requirement Conflict Between Two Domains
**Likely question**: "Describe a time you had to resolve a conflict between two conflicting requirements."
- **S**: A performance/responsiveness requirement for [feature] conflicted with a false-positive suppression requirement from the safety team.
- **T**: Reconcile the two without silently favoring one discipline over the other.
- **A**: You organized a joint review with both stakeholders, traced each requirement to its rationale, and proposed a resolution (e.g., a tiered response strategy) that satisfied both intents.
- **R**: Both requirements were updated consistently, the conflict was documented with rationale for future reference, and traceability was preserved.
- **Coaching note**: Shows cross-functional negotiation skill, not just technical correctness.

### 3. Reverse-Engineering Requirements From Existing Test Cases
**Likely question**: "Tell me about a time you had to reconstruct or clarify requirements that weren't well documented."
- **S**: A legacy [ECU/feature] had test cases in CANoe/dSPACE but the original requirement specification was outdated or incomplete.
- **T**: Rebuild a defensible, traceable requirement set to support an upcoming safety audit or ASPICE assessment.
- **A**: You systematically reverse-engineered requirements from the existing validated test cases, cross-checked with the diagnostic/DTC behavior observed, and re-baselined them with proper EARS formatting and traceability links.
- **R**: The team passed the audit/assessment with the reconstructed traceability matrix as evidence; note the scale (e.g., "N requirements across M test cases").
- **Coaching note**: This is a strong story if true — it directly demonstrates the "validation-to-RE" skill transfer discussed in your study guide.

### 4. Managing a Late-Stage Requirement Change
**Likely question**: "How do you handle a requirement change that comes in late in the development cycle?"
- **S**: A stakeholder or regulatory change required a modification to an already-baselined requirement for [feature] close to a milestone.
- **T**: Assess impact and manage the change without derailing the program.
- **A**: You performed a structured impact analysis across design, code, test cases, and (if safety-relevant) the safety case; presented options with tradeoffs to the Change Control Board; prioritized re-verification scope instead of a full re-test.
- **R**: The change was implemented with minimal schedule impact and full traceability preserved; state the specific time/effort saved if known.
- **Coaching note**: Tests your grasp of impact analysis discipline, not just "we fixed it."

### 5. Writing Requirements for an ADAS Function From Scratch
**Likely question**: "Walk me through how you'd derive requirements for a new ADAS feature."
- **S**: A new/updated feature (e.g., AEB extension, phantom-braking mitigation) needed a fresh or revised requirement set.
- **T**: Translate stakeholder/customer intent and scenario catalogs into verifiable system and software requirements.
- **A**: You worked from the ODD and scenario catalog, applied EARS patterns for each identified triggering condition and response, defined verification methods per requirement, and reviewed with systems/safety/test stakeholders.
- **R**: A complete, traceable requirement baseline was delivered on schedule with zero "TBD" items at gate review.
- **Coaching note**: Even as a hypothetical/practice exercise, walking through this process cleanly signals genuine RE competence.

### 6. Catching a Compound or Untestable Requirement in Review
**Likely question**: "Give an example of a time you improved requirement quality during a review."
- **S**: During a peer review, you found a requirement combining two behaviors in one "shall" statement (e.g., "the system shall detect and classify and track objects").
- **T**: Improve testability and traceability before the requirement moved to design.
- **A**: You split it into atomic, individually verifiable requirements, each mapped to a distinct test case, and updated the traceability matrix accordingly.
- **R**: Downstream test design became simpler and defect attribution during later testing was unambiguous.
- **Coaching note**: Small, concrete story — but shows you know the difference between "reviewed it" and "actually improved it."

### 7. Preparing Requirements Traceability for an ASPICE Assessment
**Likely question**: "Tell me about your experience with process compliance / audits."
- **S**: An upcoming ASPICE assessment required demonstrable bidirectional traceability from stakeholder requirements down to test cases for [system/feature].
- **T**: Ensure the traceability matrix was complete, with no orphan requirements or untested items.
- **A**: You audited the matrix systematically, closed gaps (missing test case links, unresolved TBDs), and coordinated with software/hardware leads to align cross-level consistency.
- **R**: The assessment passed with no major findings on the SYS.1–SYS.5/SWE.1 process areas relevant to RE.
- **Coaching note**: If you haven't directly done an ASPICE assessment, frame this around whatever traceability/documentation rigor exercise you have done (e.g., release regression baselining) and be honest about the adaptation.

---

## Section B — Functional Safety (7 Scenarios)

### 8. Identifying a Missed Hazard/Failure Mode
**Likely question**: "Tell me about a time you found a safety issue others had missed."
- **S**: During test/validation of [ECU/feature], you observed unexpected behavior under a fault condition not explicitly covered in the FMEA/HARA.
- **T**: Determine whether this represented a genuine gap in the safety analysis.
- **A**: You documented the observed behavior with reproducible evidence (CANoe trace, DTC log), escalated to the safety engineer/team, and participated in updating the FMEA/FTA to cover the new failure mode.
- **R**: The safety analysis was updated, a mitigation was added to the design, and the issue was closed before production release.
- **Coaching note**: This is one of the highest-value stories for a FuSa role — it demonstrates you can operate as a safety net beyond the formal analysis.

### 9. Defending an ASIL Rating or Severity/Exposure/Controllability Assessment
**Likely question**: "Describe a time you had to justify a technical safety judgment to a skeptical stakeholder."
- **S**: During a HARA review, a stakeholder (e.g., program management) pushed back on an ASIL rating because of cost/schedule implications.
- **T**: Defend the rating on technical merit without simply deferring to authority or caving to pressure.
- **A**: You walked through the Severity/Exposure/Controllability rationale with concrete scenario evidence, referenced comparable industry precedent, and proposed alternatives that addressed cost concerns without weakening the safety argument.
- **R**: The ASIL rating was upheld (or appropriately adjusted with documented rationale), preserving safety case integrity.
- **Coaching note**: A classic "protect safety under pressure" story — very likely to be asked directly.

### 10. Handling a Safety-Schedule Tradeoff
**Likely question**: "Tell me about a time you had to push back on a schedule to protect a safety requirement." *(flagged directly in your FuSa study guide as a likely question)*
- **S**: A program milestone was at risk because a safety verification activity (e.g., fault injection test for a safe-state transition) was incomplete.
- **T**: Decide whether to recommend delaying release or accept residual risk.
- **A**: You quantified the risk and evidence gap clearly, presented it to program leadership with options (delay vs. conditional release with mitigation), and held the line on the non-negotiable safety verification.
- **R**: The team adjusted the schedule (or added a mitigation), and the safety case was defensible at the following gate review.
- **Coaching note**: Interviewers are testing whether you'll say what needs to be said even when it's unwelcome — don't soften this story too much.

### 11. Root-Causing a Diagnostic/Fault-Reaction Discrepancy
**Likely question**: "Walk me through a technically complex problem you diagnosed."
- **S**: A safety mechanism (e.g., watchdog, diagnostic monitor) was not transitioning the system to the expected safe state within the required FTTI.
- **T**: Root-cause the discrepancy between specified and observed behavior.
- **A**: You used CANoe/dSPACE trace analysis and UDS diagnostics to isolate the timing gap, traced it to [e.g., an incorrect diagnostic event manager configuration or software timing issue], and worked with the SW team on the fix.
- **R**: The safe-state transition was corrected to meet the FTTI requirement, verified with repeatable fault-injection tests.
- **Coaching note**: Technically rich — lean on real specifics here since this maps closely to your actual validation experience.

### 12. Cross-Functional Safety-Security Interaction
**Likely question**: "Have you worked on an issue that touched both safety and cybersecurity?"
- **S**: A potential attack vector (e.g., CAN message spoofing) was identified that could also trigger a safety-relevant malfunction.
- **T**: Ensure the issue was addressed from both the ISO 26262 and ISO 21434 perspectives without duplicated or conflicting mitigations.
- **A**: You coordinated a joint review between safety and security engineers, confirmed the malfunction fell under an existing Safety Goal, and ensured the security mitigation (e.g., message authentication) also satisfied the safety requirement's rationale.
- **R**: A single, consistent mitigation satisfied both domains, avoiding redundant or conflicting requirements.
- **Coaching note**: Even a modest real example here is valuable — this intersection is explicitly called out as increasingly important in your FuSa guide.

### 13. Preparing for or Supporting an External Safety Assessment
**Likely question**: "Tell me about your experience supporting an audit or external assessment."
- **S**: An external assessor (e.g., TÜV) was scheduled to review the safety case for [ECU/feature].
- **T**: Ensure your area's evidence (test reports, traceability, FMEA/FTA records) was complete and defensible.
- **A**: You conducted a self-audit beforehand, closed gaps in test evidence and traceability, and prepared clear, rationale-backed answers for likely assessor questions.
- **R**: The assessment produced no major findings in your area, or findings were closed quickly with pre-prepared evidence.
- **Coaching note**: If you haven't been through a formal external assessment, adapt this to an internal gate review or peer audit — be transparent about the substitution if asked directly.

### 14. Escalating a Safety Concern Discovered Late
**Likely question**: "Describe a time you had to escalate a problem you weren't sure how to solve yourself."
- **S**: Late in the validation cycle, you discovered a scenario (e.g., a SOTIF-related sensor performance limitation) that hadn't been covered by existing test scenarios.
- **T**: Decide whether and how to escalate given the schedule pressure at that stage.
- **A**: You documented the gap with concrete evidence, escalated immediately to the safety lead rather than trying to quietly resolve it yourself, and proposed a scoped mitigation/test plan.
- **R**: The gap was formally assessed, added to the SOTIF known/unknown scenario tracking, and addressed before release (or explicitly accepted as residual risk with sign-off).
- **Coaching note**: Interviewers want to see judgment about *when to escalate*, not heroics or silent risk-taking.

---

## Section C — Team Leadership & Cross-Functional Management (6 Scenarios)

### 15. Mentoring a Junior Engineer on Safety/RE Discipline
**Likely question**: "Tell me about a time you mentored or developed someone on your team."
- **S**: A junior engineer's FMEA or requirement drafts were technically reasonable but lacked rigor (vague language, missing traceability).
- **T**: Improve their output quality without discouraging them or micromanaging.
- **A**: You reviewed their work collaboratively rather than just marking it up, walked through the reasoning behind EARS syntax or ASIL rationale using real examples, and had them redo one artifact with you as a paired exercise.
- **R**: Their subsequent submissions needed significantly fewer review cycles; if possible, quantify (e.g., "review cycles dropped from 3 to 1").
- **Coaching note**: Shows coaching style, not just technical correction — interviewers are listening for *how* you taught, not just *that* you fixed it.

### 16. Resolving a Disagreement Between an Architect and a Safety Engineer
**Likely question**: "How would you handle a disagreement between a system architect and a safety engineer on ASIL allocation?" *(flagged directly in your FuSa study guide)*
- **S**: A system architect proposed an architecture relying on ASIL decomposition that the safety engineer believed violated independence assumptions (shared resource, potential common-cause failure).
- **T**: Mediate a technical disagreement without simply picking a side by seniority or convenience.
- **A**: You facilitated a joint Dependent Failure Analysis (DFA) session, brought both parties to examine the actual failure modes, and reached a technically grounded resolution (e.g., added isolation mechanism or revised decomposition).
- **R**: The architecture was updated to satisfy both feasibility and safety independence requirements, avoiding a costly late-stage redesign.
- **Coaching note**: Demonstrates you lead with evidence/process, not authority — a strong signal for a "Team Manager" evaluation.

### 17. Building Safety Culture Under Delivery Pressure
**Likely question**: "How do you build safety awareness in a team that's under delivery pressure?" *(flagged directly in your FuSa study guide)*
- **S**: A team was under significant schedule pressure and safety review activities were being treated as a formality/checkbox.
- **T**: Restore genuine engagement with safety analysis without slowing the team further.
- **A**: You introduced short, focused review sessions instead of long formal ones, shared a concrete example of a real defect a proper review had caught (to make the value tangible), and made escalation channels visible and blame-free.
- **R**: Review quality and finding rates improved; a real defect was caught earlier in a subsequent cycle as a direct result.
- **Coaching note**: This is a "culture change" story — interviewers want mechanism, not just intention.

### 18. Coordinating With a Supplier/Partner Team Under a DIA
**Likely question**: "Describe a time you managed a cross-organization or supplier interface."
- **S**: A Tier-1 supplier or partner team owned part of the safety case under a Development Interface Agreement (DIA), and their deliverable was inconsistent with your team's assumptions.
- **T**: Resolve the interface gap without a full re-negotiation cycle.
- **A**: You reviewed the DIA scope in detail, identified the specific assumption mismatch, and coordinated a joint technical review to realign responsibilities and update the interface documentation.
- **R**: The interface gap was closed, and the DIA was updated to prevent recurrence on future features.
- **Coaching note**: If you haven't managed a formal DIA, adapt this to any cross-team/cross-vendor interface coordination you've done (e.g., coordinating with a sensor supplier on CAN signal definitions).

### 19. Communicating Technical Safety Risk to Non-Technical Leadership
**Likely question**: "How do you communicate a technical risk to stakeholders who don't have your technical background?"
- **S**: A safety verification gap threatened a program milestone, and you needed program management (non-safety-expert) to understand the real risk and make an informed decision.
- **T**: Translate a technical safety issue into program-risk language without either overstating or minimizing it.
- **A**: You summarized the issue in terms of impact, likelihood, and options (not technical jargon), gave a clear recommendation, and made the tradeoffs explicit rather than hiding them in a technical appendix.
- **R**: Leadership made an informed decision aligned with your recommendation; the outcome avoided either an uninformed risk acceptance or unnecessary panic/delay.
- **Coaching note**: This maps directly to the "Team Manager" evaluation — the ability to be the safety voice in a non-safety room.

### 20. Prioritizing Across Multiple Concurrent Workstreams
**Likely question**: "Tell me about a time you had to prioritize across competing demands on your team."
- **S**: Your team was simultaneously supporting safety analysis/requirements work for multiple ADAS features with a fixed headcount and overlapping deadlines.
- **T**: Allocate the team's effort without silently letting quality slip on lower-visibility items.
- **A**: You risk-ranked the workstreams by safety/schedule criticality, reallocated engineers explicitly (including reassigning yourself to the highest-risk item), and communicated the tradeoffs transparently to stakeholders rather than letting expectations drift silently.
- **R**: All critical-path items were delivered on time; lower-priority items were explicitly re-scheduled with stakeholder agreement rather than silently slipping.
- **Coaching note**: Shows planning discipline and honest stakeholder communication — both core "manager" competencies.

---

## Quick Prep Checklist Before the Interview

- [ ] For each scenario, replace bracketed placeholders with a real incident from your career — even a partial match is stronger than a fully generic answer.
- [ ] Quantify the Result wherever possible (time saved, defects caught, review cycles reduced, schedule impact avoided).
- [ ] Practice saying each story out loud in under 90 seconds — STAR answers that ramble lose the interviewer.
- [ ] Have at least one story ready per section (A/B/C) that you can deliver with zero hesitation — these are your "anchor" stories.
- [ ] Be honest when a story is adapted from a related-but-not-identical experience (e.g., "I haven't been through a formal ASPICE assessment, but I did lead a similar traceability audit for..."). Interviewers respect honest framing far more than a story that unravels under follow-up questions.

---

*End of STAR preparation guide.*
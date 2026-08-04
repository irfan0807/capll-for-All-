# ASPICE + ISO 26262 + ISO 29148 + ISO 21434
## Integrated Framework Guide — Understand, Explain in Interview, Implement in Practice

---

## 0. Why These Four Standards Are Studied Together

These four frameworks are not independent silos — in a real automotive program they operate as **one interlocking system**:

- **ISO 29148** gives you the generic discipline of writing good requirements.
- **ASPICE** gives you the *process* — what activities happen, in what order, with what work products, and how they're assessed for maturity.
- **ISO 26262** gives you the *safety-specific content* that flows through that process (Safety Goals → FSR → TSR → SW/HW Safety Requirements).
- **ISO 21434** gives you the *cybersecurity-specific content* that flows through the same process in parallel (Cybersecurity Goals → Cybersecurity Requirements).

**The single mental model to carry into any interview**: ASPICE is the skeleton (process), ISO 29148 is the muscle (requirement quality), and ISO 26262/21434 are two parallel nervous systems (safety and security) that both plug into the same skeleton at the same points — HARA/TARA feed the concept phase, requirements get ASIL/CAL tags, and both eventually converge into a combined Safety+Security Case reviewed at the same gates.

---

## PART 1 — ASPICE (Automotive SPICE)

### 1.1 What It Is
Automotive SPICE (Software Process Improvement and Capability Determination) is a **process reference and assessment model**, not a technical content standard. It defines *what activities a competent development process must contain* and provides a scale to measure how well an organization actually performs them.

### 1.2 Core Structure

**Process Reference Model (PRM)** — organized into process groups:

| Group | Code | Content |
|---|---|---|
| Acquisition | ACQ | Supplier/customer agreement, requirements, monitoring |
| Supply | SPL | Supplier-side request/tendering |
| System Engineering | SYS | Requirements → Architecture → Integration → Qualification |
| Software Engineering | SWE | Software-level equivalent of SYS |
| Management | MAN | Project management, risk management, quality assurance |
| Supporting Processes | SUP | Configuration management, problem resolution, change request management |
| Process Improvement | PIM/REU | Process assessment, reuse |

**The engineering backbone (the part interviewers probe hardest):**

| Process | Name |
|---|---|
| SYS.1 | Requirements Elicitation |
| SYS.2 | System Requirements Analysis |
| SYS.3 | System Architectural Design |
| SYS.4 | System Integration and Integration Test |
| SYS.5 | System Qualification Test |
| SWE.1 | Software Requirements Analysis |
| SWE.2 | Software Architectural Design |
| SWE.3 | Software Detailed Design and Unit Construction |
| SWE.4 | Software Unit Verification |
| SWE.5 | Software Integration and Integration Test |
| SWE.6 | Software Qualification Test |

### 1.3 Capability Levels (the Assessment Scale — PAM/VDA scope)

| Level | Name | Meaning |
|---|---|---|
| 0 | Incomplete | Process not implemented or fails to achieve its purpose |
| 1 | Performed | Process achieves its purpose (base practices exist) |
| 2 | Managed | Performed + planned, monitored, adjusted; work products controlled |
| 3 | Established | Managed + performed using a defined/tailored standard process |
| 4 | Predictable | Established + quantitatively managed |
| 5 | Innovating | Predictable + continuously improved |

- Most OEM supplier requirements today target **Capability Level 2** (sometimes 3) on a defined process scope (commonly the "VDA Scope" — a defined subset of processes agreed across German OEMs, including SYS.1–SYS.5, SWE.1–SWE.6, SUP.1, SUP.8, SUP.9, SUP.10, MAN.3, ACQ.4).
- Each process is rated against two dimensions: **Process Performance** (Level 1 base practices) and **Process Capability** (Levels 2–5 generic practices: planning, monitoring, defining standard process, quantitative management, improvement).

### 1.4 Work Products (What Auditors Actually Look At)
Each process has defined **Base Practices** (what you must do) and **Work Products** (evidence you must produce) — e.g.:
- SYS.2 → System Requirements Specification, Traceability Record, Requirements Review Record
- SWE.4 → Unit Verification Results, Test Specification, Test Report
- SUP.9 → Problem/Change Request records with status tracking

### 1.5 How to Explain ASPICE in an Interview (Talking Points)
- "ASPICE tells us *what* must happen and *how well*, not *how* — the technical content of what a good requirement looks like comes from ISO 29148, and safety/security content comes from ISO 26262/21434."
- Be ready to explain the **V-Model mapping**: SYS.2 (system reqs) ↔ SYS.5 (qualification test); SWE.1 (SW reqs) ↔ SWE.6 (SW qualification test) — bidirectional traceability between these pairs is the single most common audit finding area.
- Know the difference between **Process Performance (Level 1)** and **Process Capability (Level 2+)** — a common trap question is "can a process be Level 1 but still fail an assessment?" (Yes — if it's not managed/planned/controlled, it caps at Level 1 regardless of how well the engineering itself is done.)
- Be ready to give one real example of a **traceability gap** you found and fixed — this is almost always asked.

### 1.6 How to Implement ASPICE in Practice
1. **Scope the assessment** — agree the process scope (e.g., VDA scope) and target capability level with the customer/assessor upfront.
2. **Gap analysis** — assess current process against PAM base/generic practices; identify missing work products.
3. **Define/tailor the standard process** — document templates for requirement specs, traceability matrices, review records, test specs.
4. **Train the team** — especially on traceability discipline and review record-keeping (the most commonly missed evidence).
5. **Run pilot projects** — apply the defined process on a real feature before organization-wide rollout.
6. **Internal assessment / dry-run** — self-assess against the PAM before the real assessment to close gaps early.
7. **Continuous evidence collection** — traceability and review records must be maintained live, not reconstructed retroactively before an audit (a major and common project management failure).

---

## PART 2 — ISO 29148 (Requirements Engineering)

### 2.1 What It Is
ISO/IEC/IEEE 29148 is the systems/software engineering standard defining **requirement quality characteristics and the requirements engineering process** — it's the generic foundation ASPICE's SYS.1/SYS.2/SWE.1 rely on for "what makes a requirement good."

### 2.2 Individual Requirement Characteristics
- **Necessary** — traces to an actual stakeholder need.
- **Appropriate** — right level of abstraction for its layer.
- **Unambiguous** — single interpretation.
- **Complete** — no missing information needed to understand it.
- **Singular** — one requirement, one statement (no compound "and/or").
- **Feasible** — achievable within constraints.
- **Verifiable** — a test/inspection/analysis/demonstration can confirm it.
- **Correct** — accurately represents the need.
- **Conforming** — follows the organization's required structure/template/style rules.

### 2.3 Requirement Set (Collection) Characteristics
- **Complete** — covers all stakeholder needs.
- **Consistent** — no internal contradictions.
- **Feasible** — the set as a whole is achievable, not just each requirement individually.
- **Comprehensible** — understandable as an organized, navigable body of requirements (structure, numbering, grouping).
- **Able to be validated** — the whole set can be checked against stakeholder intent.

### 2.4 The RE Process per 29148
1. **Stakeholder Requirements Definition** — elicit, analyze, specify, validate stakeholder needs.
2. **System/Software Requirements Definition** — derive verifiable technical requirements from stakeholder requirements.
3. Both stages loop through **elicit → analyze → specify → verify → validate → manage (baseline/trace/change control)**.

### 2.5 How to Explain ISO 29148 in an Interview
- "29148 is where the *characteristics of a good requirement* come from — ASPICE checks that we *followed a process*; 29148 checks that what we *produced* is actually good."
- Be ready to define **Verification vs. Validation** precisely — a nearly guaranteed interview question:
  - **Verification** = "Did we build the system right?" (does it meet the specified requirement)
  - **Validation** = "Did we build the right system?" (does it meet the actual stakeholder need, even if not perfectly captured in the written requirement)
- Know EARS (Easy Approach to Requirements Syntax) cold — this is the practical implementation tool most OEMs use to operationalize 29148's "unambiguous/singular/verifiable" characteristics (see the earlier Requirements Engineering study guide for the full pattern table).

### 2.6 How to Implement ISO 29148 in Practice
1. Adopt a **requirement template/attribute schema**: ID, text (EARS format), rationale, source/parent, verification method, ASIL/CAL tag, status, owner.
2. Establish a **requirements quality checklist** (the "5C": Complete, Consistent, Correct, Clear, Checkable) as a mandatory peer-review gate before baselining.
3. Set up **tooling for traceability** (DOORS/Polarion/Jama/Codebeamer) with defined link types (derives-from, verifies, satisfies).
4. Run **formal requirement inspections** (Fagan-style) for safety/security-critical requirement sets, not just informal reviews.
5. Define **baseline and change control procedures** — no requirement changes after baseline without CCB approval and impact analysis.

---

## PART 3 — ISO 26262 (Functional Safety)

*(Covered in depth in the earlier Functional Safety study guide — summarized here with an implementation/interview lens, integrated with ASPICE/29148/21434.)*

### 3.1 Core Structure Recap
Parts 1–12 cover vocabulary, safety management, concept phase, system/HW/SW product development, production/operation, supporting processes, ASIL-oriented analyses, and semiconductor guidance. See Section 2 of the earlier FuSa guide for the full table.

### 3.2 Where It Plugs Into ASPICE
| ASPICE Process | ISO 26262 Content Injected |
|---|---|
| SYS.1/SYS.2 | Item Definition, HARA, Safety Goals, Functional Safety Requirements become inputs/outputs |
| SYS.3 | Technical Safety Concept allocated to architecture; freedom-from-interference analysis |
| SWE.1/SWE.2 | Software Safety Requirements, safety-oriented architecture (partitioning, redundancy) |
| SUP.9/SUP.10 | Safety-relevant problem resolution and change management have stricter impact-analysis rules |
| SYS.5/SWE.6 | Safety validation/qualification test evidence feeds the Safety Case |

### 3.3 How to Explain ISO 26262 in an Interview (Interview-Specific Framing)
- Be ready to explain the **full requirement chain in one breath**: "Safety Goal → Functional Safety Requirement → Technical Safety Requirement → Software/Hardware Safety Requirement → Test Case," and how each step is *derived and verified*, not just labeled.
- A very common question: **"How is a safety requirement different from a normal requirement?"** — Answer: it carries an ASIL, traces to a Safety Goal, must specify safe-state behavior/timing (FTTI) explicitly, and is subject to stricter change-impact and confirmation-review rules (ISO 26262 Part 2 Confirmation Measures: Confirmation Review, Safety Audit, Safety Assessment).
- Know **ASIL decomposition validity conditions** — independence, no common-cause failure — this is a favorite "explain a subtlety" question.

### 3.4 How to Implement ISO 26262 in Practice
1. Establish a **Safety Management System** — safety plan, safety case template, roles (Safety Manager, Safety Engineer) defined per Part 2.
2. Perform **Item Definition + HARA** at concept phase — output: Safety Goals with ASIL.
3. Derive **FSC → TSC → SW/HW Safety Requirements** with full traceability into the ASPICE requirement chain (SYS.2/SWE.1).
4. Run **safety analyses** (FMEA, FTA, FMEDA, DFA) at the appropriate architecture maturity points.
5. Maintain a **living Safety Case** — updated continuously with verification evidence, not assembled retroactively.
6. Schedule **Confirmation Measures** at defined milestones (reviews, audits, assessments) per the safety plan.

---

## PART 4 — ISO 21434 (Cybersecurity Engineering)

### 4.1 What It Is
ISO/SAE 21434 defines cybersecurity engineering requirements across the vehicle lifecycle — the security analog to ISO 26262, structurally mirroring its concept-to-production-to-decommissioning lifecycle approach.

### 4.2 Core Structure

| Clause Area | Content |
|---|---|
| Cybersecurity Governance | Cybersecurity policy, culture, organizational roles (Cybersecurity Manager) |
| Cybersecurity Management (Project-level) | Cybersecurity plan, tailoring, tool management |
| Risk Assessment Methods | Asset identification, threat scenario identification, impact rating, attack feasibility rating |
| Concept Phase | Item Definition, **TARA (Threat Analysis and Risk Assessment)**, Cybersecurity Goals, Cybersecurity Concept |
| Product Development | Cybersecurity requirements at system/HW/SW level, design, integration, verification/validation |
| Post-Development | Production, operations, incident response, updates (including OTA), decommissioning |
| Continuous Activities | Cybersecurity monitoring, vulnerability analysis and management |

### 4.3 TARA — The Security Analog to HARA
- **Asset identification** → what needs protection (data, functions, communication).
- **Threat scenario identification** → e.g., STRIDE-style categorization (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).
- **Impact rating** → safety, financial, operational, privacy dimensions.
- **Attack feasibility rating** → elapsed time, expertise, knowledge of item, window of opportunity, equipment needed (similar structure to attack-potential-based methods, e.g., adapted from common criteria approaches).
- **Risk value** → combination of impact and feasibility → determines whether risk is treated, retained, transferred, or avoided.
- Output: **Cybersecurity Goals**, analogous to ISO 26262 Safety Goals, each with a risk treatment decision.

### 4.4 CAL (Cybersecurity Assurance Level)
- Similar concept to ASIL, though less universally mandated in the current edition — represents the rigor level applied to a cybersecurity requirement based on risk.

### 4.5 Where It Plugs Into ASPICE and ISO 26262
| Integration Point | Detail |
|---|---|
| Concept Phase | TARA runs alongside HARA; both can identify overlapping malfunctions (e.g., a spoofed CAN message causing unintended actuation) |
| Requirements | Cybersecurity requirements flow into the same SYS.2/SWE.1 requirement baseline as safety requirements, tagged distinctly (CAL vs. ASIL) |
| Safety-Security Coordination | ISO 21434 explicitly calls for coordination with functional safety — a combined **Safety-Security Case** or cross-referenced cases is increasingly standard practice |
| Verification | Penetration testing, fuzz testing, vulnerability scanning feed into SYS.5/SWE.6 alongside functional/safety test evidence |

### 4.6 How to Explain ISO 21434 in an Interview
- "21434 is structurally the mirror of 26262 — TARA plays the role HARA plays, Cybersecurity Goals play the role Safety Goals play, and CAL plays the role ASIL plays — but the risk basis is attacker capability and motivation, not just probability of failure."
- Be ready to give a **concrete safety-security overlap example**: e.g., a spoofed sensor CAN message that both violates a safety malfunction definition *and* is a security threat scenario — and explain how you'd avoid writing two conflicting mitigations for the same root issue.
- Know the difference between **risk treatment options**: reduce/mitigate, avoid (remove the feature/interface), transfer (contractual/insurance), retain (accept with justification) — interviewers sometimes ask you to classify a scenario.

### 4.7 How to Implement ISO 21434 in Practice
1. Establish **Cybersecurity Governance** — policy, culture, defined roles (Cybersecurity Manager, mirroring the Safety Manager role).
2. Run **TARA** at concept phase in parallel with HARA — ideally with joint sessions where malfunction/threat overlaps exist.
3. Derive **Cybersecurity Goals → Cybersecurity Requirements**, tagged with CAL, integrated into the same requirement baseline/tooling as functional and safety requirements.
4. Implement **secure design practices** (authentication, encryption, secure boot, intrusion detection) as required by the Cybersecurity Concept.
5. Perform **security verification** — penetration testing, fuzzing, static/dynamic code security analysis.
6. Establish **post-development monitoring** — vulnerability management process, incident response plan, OTA update security process (this lifecycle-long obligation is one of 21434's biggest differences from a "ship and done" mindset).
7. Maintain a **Cybersecurity Case** analogous to the Safety Case, cross-referenced where malfunctions/threats overlap.

---

## PART 5 — The Combined Practical Framework (What "Implementation" Really Looks Like)

### 5.1 Unified Concept-Phase Flow
```
                Item Definition
                      │
        ┌─────────────┼─────────────┐
        ▼                           ▼
      HARA                        TARA
   (ISO 26262)                (ISO 21434)
        │                           │
  Safety Goals (ASIL)     Cybersecurity Goals (CAL)
        │                           │
        └──────────► Combined Concept Review ◄──────────┘
                          │
              Functional/Technical Safety Concept
              + Cybersecurity Concept
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                    ▼
  SYS.2/SWE.1 (ASPICE) — Unified Requirement Baseline
  (each requirement written per ISO 29148, tagged ASIL and/or CAL)
                          │
                 Architecture (SYS.3/SWE.2)
                          │
              Implementation (SWE.3/SWE.4)
                          │
        Integration & Test (SYS.4/SWE.5, SYS.5/SWE.6)
        — functional test + safety fault-injection + security pentest
                          │
              Safety Case  +  Cybersecurity Case
              (cross-referenced where malfunctions/threats overlap)
```

### 5.2 Organizational Roles Typically Required
| Role | Primary Standard | Responsibility |
|---|---|---|
| Requirements Engineer | ISO 29148 / ASPICE SYS.1-2, SWE.1 | Requirement quality, traceability |
| Systems/Software Architect | ASPICE SYS.3/SWE.2 | Architecture, allocation |
| Functional Safety Manager/Engineer | ISO 26262 | HARA, safety concept, safety case |
| Cybersecurity Manager/Engineer | ISO 21434 | TARA, cybersecurity concept, cybersecurity case |
| Quality/Process Engineer | ASPICE | Process definition, internal audits, assessment readiness |
| Test/Validation Engineer | ASPICE SYS.4-5/SWE.5-6 + both standards | Functional, safety, and security verification |

### 5.3 Common Real-World Implementation Pitfalls
- Running HARA and TARA in **complete isolation**, producing conflicting or duplicated mitigations for the same underlying malfunction.
- Treating ASPICE compliance as **documentation after the fact** rather than a live process — the single most common assessment failure mode.
- Writing safety/security requirements that fail basic ISO 29148 quality characteristics (vague, compound, unverifiable) — technically "compliant" with 26262/21434's requirement existence but not with requirement *quality*.
- No **defined interface/coordination process** between the Safety Manager and Cybersecurity Manager roles — 21434 explicitly expects this coordination to be planned, not incidental.
- **Traceability tooling fragmentation** — safety, security, and functional requirements living in different, unlinked systems, making impact analysis across domains nearly impossible.

---

## PART 6 — Interview Readiness Summary

### 6.1 The One-Paragraph "Explain the Whole Framework" Answer
> "ASPICE defines the process backbone — what activities happen and how mature they are. ISO 29148 defines what makes any individual requirement or requirement set actually good — unambiguous, verifiable, traceable. ISO 26262 and ISO 21434 both plug into that same process at the concept phase, in parallel — HARA produces Safety Goals with an ASIL, TARA produces Cybersecurity Goals with a CAL, and both flow down through the same SYS.2/SWE.1 requirement baseline, get allocated to the same architecture, and get verified through the same integration/test process, converging into a cross-referenced Safety Case and Cybersecurity Case."

### 6.2 High-Probability Interview Questions Across All Four
1. How do ASPICE, ISO 26262, and ISO 21434 relate to each other structurally?
2. What's the difference between Process Performance and Process Capability in ASPICE?
3. What makes a requirement "verifiable" per ISO 29148, and how do you enforce that in practice?
4. Walk me through the full chain from Safety Goal to test case.
5. What's the security analog to HARA, and how do the outputs differ?
6. Give an example of where a safety issue and a security issue overlap.
7. What confirmation measures does ISO 26262 require, and who performs them?
8. How would you handle a traceability gap discovered right before an assessment?
9. What's the difference between verification and validation?
10. How do you keep safety and security requirement sets consistent instead of conflicting?

### 6.3 Study Priority If Time Is Limited
1. ASPICE SYS/SWE process flow + capability levels (foundation for everything else)
2. ISO 29148 requirement characteristics + EARS (the quality layer everyone assumes you know)
3. ISO 26262 concept phase chain (Safety Goal → FSR → TSR → SW/HW req → test)
4. ISO 21434 TARA and its structural parallel to HARA
5. The combined concept-phase flow diagram in Section 5.1 — practice drawing/explaining it from memory

---

*End of framework guide.*
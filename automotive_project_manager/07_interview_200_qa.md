# 200 Interview Q&A — Automotive Project Manager
## April 2026

---

## SECTION A — Project Management Fundamentals (Q1–Q40)

**Q1. What is the difference between a project, programme, and portfolio?**
A project is a temporary endeavour with a defined scope, start, and end. A programme is a group of related projects managed together to gain benefits not achievable individually. A portfolio is the entire collection of programmes and projects aligned to an organisation's strategic objectives. In automotive: a project delivers one ECU release; a programme delivers the full ADAS Level 3 feature set; the portfolio covers all future vehicle electrification projects.

**Q2. What is the triple constraint?**
Scope, Schedule (Time), and Cost — the interdependent constraints of any project. Changing one always impacts at least one other. In automotive, SOP is typically fixed (it's tied to a vehicle launch event), so scope and cost must flex when schedule pressure occurs.

**Q3. What is a Project Charter?**
The document that formally authorises the project, names the PM, defines the high-level scope, objectives, key stakeholders, budget, milestones, and risks. It is the PM's authority to begin work. In automotive, the charter is often called a Project Brief or Statement of Work (SOW).

**Q4. What is Earned Value Management?**
EVM is a project performance measurement technique that integrates scope, schedule, and cost. Key metrics: PV (planned value), EV (earned value), AC (actual cost). CPI=EV/AC (cost efficiency), SPI=EV/PV (schedule efficiency). EAC=BAC/CPI forecasts the final project cost.

**Q5. What does CPI of 0.85 mean?**
For every €1 spent, only €0.85 of planned value has been delivered. The project is over budget. If CPI remains at 0.85, EAC = BAC/0.85 = 17.6% cost overrun at project completion.

**Q6. What does SPI of 1.10 mean?**
The project is 10% ahead of schedule — more work has been completed than was planned by this point. This is positive but should be verified: it could mean the team is rushing and quality is compromised.

**Q7. What is a Work Breakdown Structure (WBS)?**
A hierarchical decomposition of the total project scope into manageable work packages. Every deliverable and activity is broken down until work packages are small enough to estimate, assign, and track. In automotive, the WBS typically has branches for: Requirements, SW Development, HW Development, Testing, Safety, Integration, and Release.

**Q8. What is the Critical Path Method?**
CPM identifies the longest sequence of dependent activities that determines the project's minimum end date. Tasks on the critical path have zero float — any delay directly delays the project end date. PM must monitor critical path tasks with highest priority.

**Q9. What is a RACI matrix?**
Responsible, Accountable, Consulted, Informed. A tool to clarify roles for each project activity. Key distinction: only one person is Accountable (owns the outcome); multiple people can be Responsible (do the work), Consulted (provide input), or Informed (kept up to date).

**Q10. What is the difference between a risk and an issue?**
A risk is a potential future event that may or may not occur (uncertain). An issue is a problem that has already occurred and must be actively managed now. In RAID log: risks require probability assessment and mitigation; issues require immediate owner, action, and resolution date.

**Q11. What are the four risk response strategies?**
Avoid (eliminate the cause), Mitigate (reduce probability or impact), Transfer (shift risk to another party — insurance, contract), Accept (acknowledge and prepare contingency). Avoid = most effective but often not possible. Transfer = common with supplier delay risks via contractual penalties.

**Q12. What is the difference between contingency reserve and management reserve?**
Contingency reserve is within the PM's control — allocated for identified risks that may occur. Management reserve is outside PM control — held by the sponsor for unknown unknowns. PM typically has authority to spend contingency without sponsor approval (up to a threshold).

**Q13. What is scope creep?**
The informal expansion of project scope without corresponding changes to time, cost, or resources. Common in automotive when OEM engineers informally request new features directly to the SW team. Prevention: formal change request process for ALL scope changes, no verbal acceptance.

**Q14. What is gold-plating?**
Team delivers MORE than what was requested — adding features or quality beyond requirements. Looks positive but consumes schedule and budget, and the extras may not be needed. PM should enforce "deliver what was agreed, nothing more" and redirect excess capacity to risk mitigation.

**Q15. What is the difference between quality assurance and quality control?**
Quality Assurance (QA) = process-oriented — ensures the right processes are being followed (ASPICE assessments, code review process, test process audits). Quality Control (QC) = product-oriented — inspects outputs for defects (test execution, code review findings, defect counts).

**Q16. What are the PMBOK process groups?**
Initiating, Planning, Executing, Monitoring & Controlling, Closing. Note: these are not sequential phases — Monitoring & Controlling runs throughout the project lifecycle in parallel.

**Q17. What is a stakeholder engagement assessment matrix?**
A tool that rates each stakeholder's current level of engagement (Unaware, Resistant, Neutral, Supportive, Leading) vs the desired level, and defines PM actions to bridge the gap. Critical for managing OEM stakeholders who are Resistant to schedule changes.

**Q18. What is a communication management plan?**
Documents: who needs what information, how often, in what format, from whom. In automotive: weekly status report to OEM PM, monthly steering deck to sponsor and OEM VP, daily standup for project team, ad-hoc escalation for critical issues.

**Q19. What is configuration management?**
The process of identifying, controlling, and tracking project artefacts and their changes over time. In automotive SW: all code, requirements, test scripts, and configuration files are version-controlled in Git. A baseline is established at each milestone. ASPICE SUP.8 covers this.

**Q20. What is a baseline?**
An approved snapshot of scope, schedule, cost, or technical content at a specific point in time. Changes to a baseline require formal change control. Project performance is measured against the baseline. Common automotive baselines: Requirements Baseline, SW Baseline (tagged in Git), Test Baseline.

**Q21. What is a lessons learned log?**
A document capturing what worked well, what didn't, and what to do differently. Should be maintained throughout the project (not just at closure). In automotive, lessons learned feed into:
- Next project's estimating model
- Process improvement plans
- Risk register templates

**Q22. What is Monte Carlo simulation in project management?**
A statistical technique that runs thousands of "what-if" scenarios using probability distributions for task durations and costs. Produces a probability curve for project completion date and total cost. Used in complex automotive programmes to quantify schedule risk with confidence percentages (e.g., "80% probability of completing by Week 52").

**Q23. What is fast tracking?**
Overlapping activities that would normally be done sequentially. Example: starting SW integration testing before coding is fully complete. Fast tracking increases rework risk but can recover schedule time. Requires careful interface management.

**Q24. What is crashing?**
Adding resources (people, tools, overtime) to shorten critical path duration. Increases cost. Not all tasks can be crashed — some have hard dependencies (e.g., can't get baby in 1 month by hiring 9 mothers). Best applied to activities with high resource scalability.

**Q25. What is a kick-off meeting?**
The first formal meeting of all project stakeholders that officially launches the project. Agenda: project overview, scope, objectives, team introductions, communication plan, key milestones, next steps. Sets expectations and energises the team.

**Q26. What is float (slack)?**
Float = LS − ES (Latest Start − Earliest Start). The amount of time a task can be delayed without delaying the project end date. Critical path tasks have zero float. Non-critical tasks have positive float (schedule buffer).

**Q27. What is a project management plan?**
The master planning document that describes how the project will be executed, monitored, and controlled. Includes subsidiary plans: scope management plan, schedule management plan, cost management plan, risk management plan, quality management plan, communications plan, procurement plan.

**Q28. What is a milestone?**
A significant point or event in the project with zero duration — it marks the completion of a major deliverable or phase. Examples in automotive: HW Freeze, SW Alpha, SIL, PPAP, SOP. Milestones are used for portfolio-level tracking and OEM contractual obligations.

**Q29. What is an issue log?**
A register of all problems that have occurred and need resolution. Each issue has: unique ID, date raised, description, priority, owner, target resolution date, status, and resolution notes. Reviewed at every project status meeting.

**Q30. What is the purpose of a project closure report?**
Formally close the project, confirm deliverables are accepted, document final cost vs budget, final schedule vs plan, lessons learned, open actions post-closure, and handover to operations/support. Required for ASPICE project management process (MAN.3).

**Q31. What is procurement management?**
The process of acquiring goods and services from external suppliers. Includes: make-or-buy analysis, supplier selection, contract negotiation, supplier performance monitoring, contract closure. In automotive: Tier-2 hardware, tool licences, HIL equipment, contractors.

**Q32. What is a Statement of Work (SOW)?**
A document that describes the specific work to be performed, deliverables, acceptance criteria, timeline, and payment terms for a supplier or contractor. The basis for a binding contract.

**Q33. What is benefit realisation?**
Tracking whether the project's intended business benefits are actually achieved post-delivery. Example: after an ADAS feature launch, measure whether warranty claims for collision-related damage decreased. Automotive PMs are increasingly expected to track post-SOP KPIs.

**Q34. What is the difference between outputs, outcomes, and benefits?**
Output: what the project produces (e.g., validated ADAS SW release). Outcome: the change that results from using the output (e.g., fewer collision accidents). Benefit: the measurable improvement (e.g., 15% reduction in rear-end collision insurance claims).

**Q35. What is dependency management?**
Identifying and managing links between tasks — internal (SW coding before integration test), external (OEM sign-off before freeze), team (HW engineer completes PCB before SW can flash). Dependencies that are missed cause cascading delays. Log all in RAID.

**Q36. What is a project health check?**
A structured periodic review of the project's status across: scope, schedule, cost, quality, risk, stakeholder satisfaction. Often used at gate reviews to provide a red/amber/green dashboard to leadership.

**Q37. What is an assumption log?**
Documents all assumptions made during planning (e.g., "OEM will provide interface data by Week 8"). If an assumption proves false, it becomes a risk or issue. Reviewing assumptions regularly is a PM best practice.

**Q38. What is rolling wave planning?**
A planning technique where near-term work is planned in detail and future work is planned at a higher level, with detail added progressively as more information is available. Common in automotive for the system integration and vehicle test phases — they're hard to plan in detail 18 months in advance.

**Q39. What is a project management office (PMO)?**
The function that defines and maintains standards for project management within an organisation. Types: Supportive (provides templates), Controlling (enforces standards), Directive (runs projects). In automotive OEMs and large Tier-1s, the PMO governs programme reporting standards and ASPICE compliance.

**Q40. What is a programme increment in SAFe?**
A fixed timebox (typically 5 sprints / 10 weeks) in which an Agile Release Train delivers features that demonstrate value. Each PI has PI Objectives — measurable outcomes agreed at PI Planning. Corresponds to a programme-level milestone in the automotive V-Model.

---

## SECTION B — Automotive-Specific (Q41–Q100)

**Q41. What is ASPICE?**
Automotive Software Process Improvement and Capability dEtermination — the process maturity standard based on ISO/IEC 15504. Automotive OEMs require Tier-1 suppliers to demonstrate capability levels (typically Level 2 minimum). PM is directly assessed under MAN.3 (Project Management) and MAN.5 (Risk Management).

**Q42. What is the difference between ASPICE Level 1 and Level 2?**
Level 1 (Performed): process outcomes are achieved but informally. Level 2 (Managed): process is planned, monitored, work products are controlled, reviews are conducted, and evidence exists. The key difference is governance and traceability of evidence.

**Q43. What is ISO 26262?**
International standard for functional safety of road vehicles' electrical and electronic systems. Defines ASIL (Automotive Safety Integrity Level) A–D + QM. Requires HARA, safety concept, safety analysis (FMEA, FTA), safety case, and confirmation measures (independent reviews).

**Q44. What is ASIL decomposition?**
The technique of splitting an ASIL requirement into two lower-ASIL components implemented independently. Example: ASIL-D → ASIL-B + ASIL-B (if the two channels are sufficiently independent). Used to distribute safety requirements across Tier-1 and Tier-2.

**Q45. What is a DIA (Development Interface Agreement)?**
A contract between OEM and Tier-1 (or Tier-1 and Tier-2) that formally distributes ISO 26262 safety responsibilities, ASIL requirements, and work products. PM must ensure the DIA is signed before safety-relevant development begins.

**Q46. What is SOP (Start of Production)?**
The date when the vehicle enters series production at the manufacturing plant. The single most critical milestone in automotive project management — all project planning works backward from SOP. Missing SOP has massive financial, contractual, and reputational consequences.

**Q47. What is PPAP?**
Production Part Approval Process — the Tier-1 supplier demonstrates that their production process is capable of consistently delivering parts/software that meet OEM requirements. Required before SOP. Failure at PPAP is a major schedule risk.

**Q48. What is a V-Model?**
The automotive SW development model where requirements and design activities on the left side of the V correspond to verification and testing activities on the right side. Each left-side activity has a corresponding right-side test level (unit, integration, system). PM uses V-Model gate reviews as project milestones.

**Q49. What is AUTOSAR?**
AUTomotive Open System ARchitecture — a standardised software architecture for automotive ECUs. Classic AUTOSAR for real-time embedded systems; Adaptive AUTOSAR for high-compute ADAS/AD systems. PM must plan 4–6 weeks for AUTOSAR tool configuration before coding starts.

**Q50. What is a HIL test bench?**
Hardware-in-the-Loop — a test environment where the real ECU hardware is connected to a simulator that emulates the rest of the vehicle (sensors, actuators, other ECUs). Allows SW integration testing before real vehicles are available. PM must budget for HIL setup and maintenance.

**Q51. What is a MIL (Model-in-the-Loop) test?**
Testing the SW algorithm model in a pure simulation environment — no real hardware. Used early in development for algorithm verification before any code is written. Cheaper and faster than HIL.

**Q52. What is SIL (Software-in-the-Loop)?**
Testing compiled SW code in a simulation environment — no real ECU hardware. Code compiled for the processor, run under simulation. Bridges MIL and HIL. Also known as SIL in the ISO 26262 V-Model.

**Q53. What is an EOL (End of Line) test?**
End-of-line diagnostics — every vehicle on the assembly line has its ECUs tested, configured, and calibrated via diagnostic protocols (UDS) before leaving the factory. EOL failures cause production line stoppages. PM must coordinate EOL station development and validation alongside the ECU programme.

**Q54. What is UDS?**
Unified Diagnostic Services (ISO 14229) — the protocol used by diagnostic tools (workshop, EOL, OTA) to communicate with ECUs. Services include reading DTCs, reading live data, writing configuration, and ECU flashing. PM must ensure diagnostic specification (DID list, DTC list) is complete and reviewed.

**Q55. What is an OTA update in automotive?**
Over-the-Air software update — delivering new ECU software wirelessly via the vehicle's cellular or WiFi connection, without requiring a workshop visit. Covered by UNECE R156 (Software Update Management System). PM must plan for OTA backend, campaign management, rollback, and cybersecurity compliance (UNECE R155/TARA).

**Q56. What is IATF 16949?**
Automotive-specific quality management system standard — built on ISO 9001 with additional requirements including APQP, PPAP, FMEA, MSA, and SPC. PM must ensure the project processes are compliant with IATF 16949 for production-quality assurance.

**Q57. What is APQP?**
Advanced Product Quality Planning — a structured process for planning and defining the steps necessary to ensure a product satisfies the customer. Five phases: Plan and Define, Product Design, Process Design, Product and Process Validation, Feedback and Corrective Action.

**Q58. What is a CAN database (.dbc file)?**
The network database file that defines all CAN messages and signals — their IDs, byte positions, scaling, and units. Every ECU must be configured according to the agreed .dbc file. Changes to the .dbc require formal change control because they affect every ECU on the network.

**Q59. What is cybersecurity in automotive (UNECE R155)?**
UNECE Regulation 155 requires OEMs to have a Cybersecurity Management System (CSMS) and that vehicles are protected against cyber threats throughout their lifecycle. Tier-1 suppliers must perform TARA (Threat Analysis and Risk Assessment). PM must schedule TARA and ensure cybersecurity requirements are included in the project scope.

**Q60. What is homologation?**
The process of getting official government/regulatory approval for a vehicle or system to be sold in a market. Involves testing to legal standards (emissions, safety, crash tests) and submission of technical documentation. PM must include homologation lead time (often 6–12 months) in the project plan.

**Q61. What is a change freeze date?**
The date after which no new requirements or technical changes can be accepted without a formal change order and schedule/cost impact. Also called "requirement freeze" or "code freeze" (SW code freeze). Essential for protecting SOP.

**Q62. What is software content lock (SIL)?**
Software Inspection Lock — the point at which the software content is frozen for production. No further changes permitted without formal ECO. All validation evidence (test results, reviews, safety records) must be complete before SIL.

**Q63. What is a firmware over the air (FOTA) update vs SOTA?**
FOTA = Firmware OTA — updates the embedded firmware of an ECU. SOTA = Software OTA — updates higher-level software (applications, calibration). In practice used interchangeably, but FOTA implies a lower-level, more safety-critical update that may require ASIL validation.

**Q64. What is an Engineering Change Order (ECO)?**
The formal document authorising implementation of an approved engineering change. The ECO contains the approved ECR, the specific changes to be made, and the deadline. All affected work products (requirements, design, code, tests) must be updated per the ECO.

**Q65. What is a FMEA?**
Failure Mode and Effects Analysis — a systematic technique for identifying potential failure modes in a system, their effects, and their causes. Used in both design (DFMEA) and process (PFMEA) contexts. RPN (Risk Priority Number) = Severity × Occurrence × Detection. ISO 26262 uses FMEA as a safety analysis technique.

**Q66. What is an FTA (Fault Tree Analysis)?**
A top-down analysis that starts with an undesired event (top event) and systematically identifies all combinations of lower-level failures that could cause it. Represented as a tree with AND/OR gates. Used to calculate probability of safety goal violation in ISO 26262 ASIL determination.

**Q67. What is a CSR (Customer-Specific Requirement)?**
Requirements defined by a specific OEM beyond the standard IATF 16949 / ASPICE requirements. For example, BMW may require additional test coverage levels, VW may require a specific review format. PM must identify, document, and comply with all CSRs.

**Q68. What is gate review (phase gate)?**
A formal checkpoint at the end of a project phase where a decision is made to proceed, pause, or cancel the project. Gate criteria are pre-defined (all requirements reviewed, ASPICE evidence complete, safety findings resolved). PM presents the project status and evidence; the steering committee makes the go/no-go decision.

**Q69. What is a DDI / DDT in ADAS?**
DDI = Dynamic Driving Infrastructure. DDT = Dynamic Driving Task — the operational activities of driving (lateral/longitudinal control + object detection). SAE automation levels (L0–L5) define how much of the DDT is automated. A PM of an ADAS project must understand which SAE level is being developed and what safety/legal implications that brings.

**Q70. What is SIL vs PIL testing in embedded?**
SIL = Software-in-the-Loop (SW runs on host PC). PIL = Processor-in-the-Loop (SW runs on actual target processor). PIL detects processor-specific issues (fixed-point overflow, timing). PM must confirm PIL targets are available (target hardware) for PIL test phases.

**Q71. What is CAN-FD?**
CAN with Flexible Data Rate — extends classical CAN with higher data rate (up to 5Mbit/s in data phase) and larger frame (up to 64 bytes vs 8 bytes). Required for modern ADAS and diagnostic applications. PM must confirm all tools, test benches, and ECUs support CAN-FD before project start.

**Q72. What is Automotive Ethernet?**
Ethernet adapted for in-vehicle use (100BASE-T1, 1000BASE-T1) — single-pair, used for high-bandwidth ADAS (cameras, radar, domain controllers). PM must plan for Ethernet network switch hardware, AUTOSAR Adaptive ECU setup, and DoIP (Diagnostics over IP) toolchains.

**Q73. What is DoIP?**
Diagnostics over Internet Protocol (ISO 13400) — UDS diagnostic communication over Ethernet rather than CAN. Required for ADAS domain controllers, OTA-capable vehicles. PM must plan for DoIP tool certification and test infrastructure.

**Q74. What is SOTIF (ISO 21448)?**
Safety of the Intended Functionality — the complement to ISO 26262. While ISO 26262 addresses failures (malfunction), SOTIF addresses performance limitations of sensor-based systems (e.g., radar not detecting a pedestrian in rain). Relevant for ADAS Level 2+ PM to plan validation activities.

**Q75. What is ISO/SAE 21434?**
The cybersecurity engineering standard for road vehicles — defines processes for cybersecurity risk assessment (TARA), cybersecurity development, verification, and incident response throughout the vehicle lifecycle. PM must ensure the project includes TARA deliverables and cybersecurity requirements derived from TARA.

**Q76. What is a release note?**
A document accompanying each SW release that describes: new features added, defects fixed, known defects open, configuration requirements, and any test limitations. Essential for OEM SW acceptance reviews and ASPICE traceability.

**Q77. What is a software component acceptance test?**
Testing performed by the receiving team (e.g., system integration team) to verify that a released SW component meets its specified interface requirements before integrating it into the larger system. Reduces integration defects. PM should mandate this as a Definition of Done for component releases.

**Q78. What is a dry run (production trial)?**
A test production run at the manufacturing plant before SOP to validate the EOL process, station software, and production workflow. Typically done 4–8 weeks before SOP. Defects found here are production show-stoppers and must be escalated immediately.

**Q79. What is SOP+3 months support?**
The post-launch obligation where the development team provides priority support for 3 months after SOP — fixing production-blocking defects, analysing early field DTCs, and supporting any OTA patches required for early production vehicles. PM must plan handover to the sustaining engineering team.

**Q80. What is a vehicle variant?**
Different configurations of the same vehicle model (different markets, engines, features, regions). Each variant may have different ECU software content (variant coding). PM must manage the matrix of variants × ECUs × SW versions as configurations in the project.

**Q81. What is boundary scan (JTAG) in ECU production?**
A hardware test method where the ECU's PCB is tested at the pin level using the JTAG interface — verifies all ICs are populated correctly and all board connections are functional. Part of the EOL process for high-complexity ECUs.

**Q82. What is a KPI tree?**
A hierarchical breakdown of top-level KPIs into supporting metrics — showing how lower-level activities contribute to programme-level goals. Example: SOP KPI → SW Beta on time → Integration test pass rate → Unit test coverage → Defect resolution rate.

**Q83. What is an A-sample, B-sample, C-sample in automotive development?**
Physical hardware maturity stages:
- A-sample: first prototype, used for concept validation (not production-intent)
- B-sample: production-intent design, used for functional validation
- C-sample: production-ready, used for PPAP and SOP readiness testing
PM must plan SW milestones to align with each sample stage.

**Q84. What is a design freeze?**
The point at which the system/SW/HW design is locked for the purpose of validation. No further design changes without formal change control. In SW: equivalent to architecture freeze. PM must enforce this to prevent constant re-work during validation.

**Q85. What is Kundenspezifische Anforderungen (KSA)?**
German for Customer-Specific Requirements — widely used term in the automotive supply chain, especially in German OEM supplier relationships (BMW, VW group, Daimler). Equivalent to CSR. PM must maintain a dedicated KSA register.

**Q86. What is a development plan (ASPICE MAN.3)?**
The top-level project plan required by ASPICE MAN.3 — must include: scope, schedule, resources, responsibilities, milestones, risk management approach, and communication plan. Reviewed and updated at every gate. The PM's primary planning artefact.

**Q87. What is a test specification?**
A document that defines: what is being tested, test objectives, test environment, preconditions, test steps, expected results, and pass/fail criteria. Required by ASPICE SWE.5 and ISO 26262 for every level of testing. PM must confirm test specifications are complete before test execution begins.

**Q88. What is CAN arbitration?**
The mechanism by which multiple CAN nodes contend for bus access — lower CAN ID = higher priority. If an important safety message (e.g., brake command) and a low-priority infotainment message are sent simultaneously, the safety message wins. PM manages this through the CAN database and network architecture review.

**Q89. What is static analysis in automotive SW?**
Automated analysis of source code without executing it — checks for MISRA-C/C++ violations, undefined behaviour, data flow errors. Tools: PC-lint, Polyspace, Klocwork, Parasoft. Required by ASPICE SWE.4 and ISO 26262. PM must include static analysis time and tooling budget in the project plan.

**Q90. What is model-based development (MBD)?**
Using graphical models (e.g., MATLAB/Simulink) to design and simulate SW behaviour before generating code. Common for control algorithms (engine management, ADAS). PM must plan for model review, model-in-the-loop testing, and code generation/integration phases.

**Q91. What is a design review?**
A structured team walkthrough of a design artefact (requirements, architecture, detailed design) to find defects early. Evidence of design reviews is required by ASPICE and ISO 26262. PM must schedule reviews formally, ensure they happen, and collect minutes as required ASPICE evidence.

**Q92. What is a technical debt?**
Short-term implementation shortcuts that create long-term maintenance problems — e.g., hard-coded values instead of parameters, missing unit tests, bypassed architecture. PM must track technical debt and allocate sprint capacity to address it before it becomes SOP-blocking.

**Q93. What is a safety element out of context (SEooC)?**
An ISO 26262 concept where a software or hardware component is developed without knowing the full vehicle context — common for Tier-2 suppliers developing general-purpose components. The SEooC must document its assumed safety requirements so that the Tier-1 integrator can verify them.

**Q94. What is a confirmation review (ISO 26262)?**
An independent review of a safety work product by an assessor who was not involved in its creation — required by ISO 26262 to ensure objectivity. PM must budget for and schedule confirmation reviews for all ASIL-B and above work products.

**Q95. What is a software unit test?**
Low-level testing of individual software functions or modules in isolation. Required by ISO 26262 and ASPICE SWE.5. Branch coverage target: typically ≥ 85%. Tools: Google Test, CppUTest, VectorCAST. PM must track unit test coverage as a quality KPI.

**Q96. What is requirement volatility?**
The rate at which requirements change over time. High volatility = high rework risk. PM measures volatility as: (number of requirement changes per month) / (total requirements). >10% volatility per month is a project risk flag — indicates unstable customer needs.

**Q97. What is an interface control document (ICD)?**
A document that formally defines the interface between two systems or components — signals, timing, protocol, data ranges. Essential in automotive for ECU-to-ECU and OEM-to-Tier-1 interfaces. Agreed ICDs prevent integration surprises.

**Q98. What is a supplier qualification?**
The process of evaluating and approving a new supplier before awarding a contract. Includes: capability assessment, quality audit, financial stability check, reference checks, sample delivery. PM should not start a project depending on an unqualified supplier.

**Q99. What is a programme risk reserve?**
Contingency budget held at programme level (above individual project level) to absorb risks from multiple projects. In automotive, the programme PM may hold a shared reserve that individual project PMs can request access to for major unforeseen events.

**Q100. What is the handover to series production support?**
At SOP, the development project team transitions responsibility to the sustaining engineering or after-sales SW team. PM must ensure: all technical documentation is handed over, open defects are triaged and assigned, diagnostic tools and processes are transferred, and a knowledge transfer period is planned.

---

## SECTION C — Leadership & Soft Skills (Q101–Q140)

**Q101. How do you manage a team member who consistently misses deadlines?**
First, a private conversation to understand root cause: is it workload, clarity of requirements, personal issues, or skill gap? Set clear SMART expectations and document them. Agree on a support plan (pair programming, reduced load, training). If no improvement, escalate through HR process. Document all conversations. Never publicly blame.

**Q102. How do you handle conflict between two senior engineers?**
Facilitate a structured conversation (not email — face to face). Each person states their position without interruption. Identify the technical or process root cause of the disagreement. Work to a fact-based resolution. If unresolved at team level, involve the functional manager. The PM never picks sides unless a safety compliance issue is involved.

**Q103. How do you motivate a team during a difficult phase?**
Acknowledge the difficulty honestly — don't dismiss it. Share the bigger picture (importance of SOP, customer impact). Celebrate small wins visibly. Remove bureaucratic blockers quickly. Protect the team from unnecessary interruptions. Ensure workload is realistic — if it isn't, escalate and re-plan rather than demanding unsustainable overtime.

**Q104. How do you communicate bad news to the OEM?**
Early, directly, and with a solution. Never let the OEM find out independently. Prepare a short, fact-based summary: what happened, what the impact is, what options are available, what you recommend. Present in person or on a call — not by email alone for serious news. Demonstrate that you have already taken recovery actions.

**Q105. How do you deal with a stakeholder who constantly changes requirements?**
Implement a formal change request process. Document every requirement change in a log with the requester's name and date. Present cumulative change impact at each steering meeting. If the OEM is the source, raise the pattern formally: "We have received 23 requirement changes in 6 weeks. At this rate, the SW freeze date is at risk. We need to agree a requirement stability protocol." Make the cost of instability visible.

**Q106. Describe your leadership style.**
My style adapts to the situation and the individual: directive with new team members who need structure and guidance, collaborative and facilitative with experienced engineers, coaching-oriented for developing team members. I believe in giving engineers ownership of their deliverables rather than micromanaging. I set clear goals, remove obstacles, and hold people accountable.

**Q107. How do you prioritise when everything is labelled "urgent"?**
Apply the Eisenhower Matrix: Urgent+Important (do now), Important+Not Urgent (schedule), Urgent+Not Important (delegate), Not Urgent+Not Important (drop). In automotive: safety findings are always top priority. SOP-blocking items second. Everything else negotiated. Make the prioritisation visible so stakeholders understand tradeoffs.

**Q108. How do you onboard a new team member quickly?**
Week 1: system overview, architecture, tools setup, meet key people. Week 2: shadow experienced team member on real tasks. Week 3: own a small, well-defined task with support. Assign a buddy. Clear 30/60/90-day goals. Regular check-ins. Most important: make them feel welcome and appreciated from day one.

**Q109. How do you manage upward (your own manager or sponsor)?**
Proactive communication — don't wait to be asked. No surprises. Bring problems with proposed solutions. Understand their priorities and frame your updates in their language (budget, SOP risk, OEM relationship, not just technical details). Ask for what you need (budget, decisions, support) explicitly and with clear rationale.

**Q110. How do you build trust with an OEM customer?**
Transparency about project status (never hide problems). Deliver on commitments — if you say you'll send a report by Friday, send it by Friday. Demonstrate technical knowledge in technical meetings. Follow through on every action item. When things go wrong, own it and show a structured recovery — customers trust competent people who face problems honestly.

---

## SECTION D — Situational / Behavioural (Q141–Q200)

**Q141. A team member tells you the project will be 3 weeks late but asks you not to tell the OEM yet. What do you do?**
I cannot agree to withhold this information. I would thank the team member for being honest with me, investigate to confirm the facts quickly (same day), and then communicate to the OEM proactively — with a preliminary recovery plan. Hiding schedule slippage from the customer erodes trust far more than the slip itself. Transparency is non-negotiable.

**Q142. The OEM calls you on Friday afternoon and escalates directly about a test failure. Your team lead says the issue is minor and doesn't need immediate attention. What do you do?**
The OEM's concern is never "minor" from a relationship perspective. I acknowledge the OEM's concern, promise a written update by end of day Monday, and immediately investigate the severity myself. If the team lead is correct that it's minor, I document that with evidence and explain it clearly to the OEM. If it's more serious, I escalate internally. I never dismiss an OEM escalation without investigation.

**Q143. Your project's budget has been cut by 15% with 4 months to go. What do you do?**
Step 1: DO NOT silently absorb the cut. Analyse what scope is at risk and present the options: reduce quality (unacceptable for safety SW), defer features to SOP+6, or escalate the business case for restoring funding. Step 2: Identify which work packages can be deferred or de-scoped. Step 3: Re-baseline with the reduced budget, formally document the scope change, and get OEM sign-off on what is out of the revised scope.

**Q144. Two project engineers are applying for the same team lead promotion. How do you manage this?**
Be transparent with both about the process: what criteria will be used, who decides, and when. Treat both fairly — give both equal visibility and opportunities throughout the project. Do not play favourites. When the decision is made, communicate it to both privately and with respect. Support the unsuccessful candidate with honest developmental feedback and a growth plan.

**Q145. An external safety auditor tells you informally that your project will likely fail the ISO 26262 audit next week. What do you do?**
Act immediately. Get formal confirmation of the specific findings. Hold an emergency meeting with the safety manager and key tech leads. Identify which findings can be closed before the audit (some gaps can be documented or evidenced quickly) and which cannot. If the audit cannot realistically be passed, request a postponement from the OEM rather than proceeding and failing. A failed audit is worse than a delayed audit.

**Q146. Your SW team lead says the architecture needs to be completely redesigned 3 months before SOP. How do you respond?**
This is a critical situation. I would immediately request a 1-hour technical session to fully understand the issue: what exactly is wrong, what is the risk if we don't redesign, is there a lower-impact mitigation? If the full redesign is genuinely necessary for safety or quality, I would accept it and immediately replan the project, escalate the SOP risk to the OEM, and activate every schedule recovery mechanism available. I would not allow the team to proceed with a known architectural flaw just to protect the SOP date.

**Q147. How do you handle scope creep from an enthusiastic engineering team (gold-plating)?**
Clearly communicate in the project kickoff that all scope beyond the agreed requirements should be proposed as change requests, not implemented informally. Review the sprint backlog at each planning session to confirm all items trace to approved requirements. If gold-plating is found: acknowledge the engineer's initiative positively, log it as a backlog item for future consideration, and redirect the work to the agreed scope or to risk mitigation activities.

**Q148. You notice a pattern of recurring defects in the same SW module. What do you do?**
This is a process quality signal, not just a defect count. Initiate a root cause analysis (5-why or fishbone). Common causes in automotive: inadequate unit test coverage, requirements ambiguity, coding guideline non-compliance, insufficient code review. Work with the quality manager to address the root cause systematically. Add a specific checkpoint to the Definition of Done for that module. Report the pattern (not just individual defects) in the quality status update.

**Q149. How do you manage a situation where the supplier's quality is consistently poor but changing suppliers is not feasible?**
Implement a formal Supplier Improvement Plan (SIP): agreed written commitments from the supplier, specific measurable targets, regular quality reviews, escalation path if targets are missed. Add contractual reinforcement (NCR process, financial penalties for repeat failures if the contract allows). Internally, add additional incoming inspection steps for supplier deliveries to protect the project. Reduce dependency where possible by developing alternative competency internally.

**Q150. Describe a time you made a mistake on a project. What happened and what did you learn?**
Honest answer is valued over a rehearsed perfect story. Framework: acknowledge the mistake clearly, explain what led to it, describe what you did to recover, and articulate the specific change in your behaviour or process since. Example: "I underestimated the effort for supplier qualification by 4 weeks, which put a milestone at risk. I corrected by re-planning immediately, communicating early to the OEM, and I now always add a 20% buffer to supplier qualification estimating and validate the estimate with the procurement team independently."

---

*File: 07_interview_200_qa.md | Automotive PM Interview Prep | April 2026*

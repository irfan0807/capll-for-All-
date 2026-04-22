# 05. Business Formation & Legal Structure

**Confidential Strategic Document**  
**Prepared by:** Strategic Consulting Group  
**Date:** April 2026  
**Subject:** Legal, Compliance, and Corporate Foundation

---

## 1. Choosing the Right Legal Entity

The legal structure you choose on Day 1 determines your tax efficiency, liability exposure, and investor readiness. For an automotive B2B consulting firm, the recommendation is:

| Entity Type | Recommended For | Key Benefit |
|---|---|---|
| **LLC (USA)** | Solo founder or small team | Pass-through taxation, limited liability |
| **GmbH (Germany)** | German OEM-facing delivery | Required by Tier-1 procurement in DACH region |
| **Private Limited (UK)** | European market entry | Fast setup, globally recognized |
| **LLP (India)** | Offshore delivery hub | Low compliance overhead, multi-partner structure |

**Recommended Multi-Entity Structure for Scale:**
* Incorporate a **Holding Company** in a tax-efficient jurisdiction (Netherlands or Delaware, USA).
* Create **Operating Subsidiaries** in Germany (client-facing), India or Poland (delivery hub), and UAE (MENA market).

---

## 2. Month-by-Month Legal Checklist

### Month 1: Foundation
- [ ] Register the primary operating entity.
- [ ] Secure the company domain (e.g., `[companyname]-auto.com` or `[companyname]-validation.com`).
- [ ] Open a dedicated business bank account — **never mix personal and business funds.**
- [ ] Draft a standard Master Services Agreement (MSA) template (see below).
- [ ] Register a trademark for the company name and logo.

### Month 2–3: Compliance Readiness
- [ ] Apply for **ISO 9001 certification** (Quality Management System). An automotive client's procurement team will ask for this before signing any contract. Timeline: ~3 months.
- [ ] Begin the **TISAX Level 2 Assessment** process. TISAX is the German automotive information security standard. Without it, you cannot handle confidential ECU firmware, DBC files, or prototype CAN data from German OEMs.
- [ ] Draft an **NDA (Non-Disclosure Agreement)** template — tailored specifically to automotive intellectual property (software, diagnostic seeds, cryptographic keys).

### Month 4–6: Enterprise Readiness
- [ ] Establish a formal **Data Classification Policy** (Confidential, Internal, Public).
- [ ] Set up a secure IT infrastructure: encrypted VPN for all engineers, encrypted hard drives, no public cloud storage for client data.
- [ ] Register as a supplier with at least one major Tier-1 or OEM vendor portal (e.g., **Bosch SupplyOn, Continental SAP Ariba**).

---

## 3. Critical Legal Agreements You Must Have

### 3.1 Master Services Agreement (MSA)
The MSA is your single most important document. It defines the commercial framework for all work.

**Critical Clauses to Include:**
* **Intellectual Property (IP) Ownership:** State clearly whether custom-developed CAPL scripts, test frameworks, or automation tools belong to you (licensor) or the client. **Never give away ownership of your reusable framework.** You license it.
* **Limitation of Liability:** Cap your liability at 1x the total fees paid under the relevant Statement of Work. This protects you from catastrophic claims if a test script fails to catch a safety-critical bug.
* **Payment Terms:** Standard in automotive is Net 60. Push for Net 30. For all new clients, require a 25–30% advance milestone payment before work begins.
* **Change Management:** Define what constitutes "out of scope." Every scope creep must be governed by a formal Change Order that adds budget and timeline.
* **Governing Law:** If working with German OEMs, they will insist on German law (Deutsches Recht). Have a German legal counsel review the MSA before signing.

### 3.2 Statement of Work (SoW)
The SoW sits beneath the MSA and defines a specific project. Each project engagement needs its own SoW.

**Must-Have SoW Contents:**
* Deliverables: Exact list of artifacts (e.g., "50 CAPL test scripts for UDS SID 0x22, 0x2E validated on HW rev. B").
* Acceptance Criteria: How deliverables will be reviewed and signed off.
* Timeline with Milestones.
* Roles & Responsibilities (RACI matrix).
* Payment milestones tied to deliverable acceptance.

### 3.3 Employment & Independent Contractor Agreements
* If using freelance engineers for project ramp-ups, ensure the contract includes a strong IP assignment clause (all work product is owned by the company, not the freelancer).
* Include non-solicitation clauses preventing freelancers from approaching your clients directly.

---

## 4. Insurance Requirements
* **Professional Indemnity (Errors & Omissions) Insurance:** Covers you if a test suite you wrote fails to catch a software defect that leads to an automotive recall. **This is non-negotiable.** Minimum coverage: $2M–$5M USD.
* **Cyber Liability Insurance:** Given that you are handling confidential ECU firmware and CAN databases (DBC files), this covers breach events.
* **General Liability Insurance:** Standard requirement on most client procurement checklists.

---

## 5. Regulatory Familiarity — Know the Standards
You do not need to be a formal certification body, but your engineers must be proficient in these:

| Standard | Domain | Why It Matters |
|---|---|---|
| **ISO 26262** | Functional Safety | Required for any safety-critical ECU (braking, steering, battery). Client will ask if your test processes are ISO 26262 compliant. |
| **ISO 21434** | Cybersecurity | Mandatory for any networked ECU since 2022 (UNECE WP.29 regulation). |
| **ISO 14229 (UDS)** | Diagnostic Protocol | Core expertise for all diagnostic test services. |
| **ASPICE (Automotive SPICE)** | Software Process | Tier-1 suppliers are assessed at ASPICE Level 2/3. Your processes must align. |
| **AUTOSAR** | Software Architecture | Understanding Classic/Adaptive AUTOSAR is essential for HIL model interfacing. |

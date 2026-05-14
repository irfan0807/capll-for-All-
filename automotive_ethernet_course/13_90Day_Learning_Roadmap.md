# SECTION 13 — 90-DAY LEARNING ROADMAP
## Course: Automotive Ethernet Testing — Complete Industry Training

---

## OVERVIEW

```
90-DAY PLAN STRUCTURE:
┌──────────────────────────────────────────────────────────────────┐
│  Month 1 (Days 1-30):  FOUNDATION — Learn the fundamentals     │
│  Month 2 (Days 31-60): PRACTICE — Build projects + tools       │
│  Month 3 (Days 61-90): INTERVIEW — Mock interviews + refinement│
└──────────────────────────────────────────────────────────────────┘

Daily time commitment:
  Weekdays: 2 hours (1h study + 1h practice)
  Weekends: 4 hours (2h project + 2h interview prep)
  Total: 10h/week × 13 weeks = 130 hours
```

---

## MONTH 1 — FOUNDATION (Days 1–30)

### Week 1 — Industry Context + C Refresher (Days 1–7)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 1 | Course Overview + Industry landscape | Section 1 | 2h | Notes on OEM/Tier-1 hierarchy |
| 2 | Embedded C — volatile, const, static, bit fields | Section 2.1–2.3 | 2h | Write 5 C functions |
| 3 | Embedded C — pointers, memory management, DMA | Section 2.4–2.5 | 2h | Implement circular buffer |
| 4 | MCU architecture — AURIX TC397 overview | Section 2.2 | 2h | Draw ECU block diagram |
| 5 | RTOS — task scheduling, interrupts, watchdog | Section 2.6 | 2h | State machine in C |
| 6 | **Practice** — C coding exercises | LeetCode Easy C problems | 3h | 10 problems solved |
| 7 | **Review** — Week 1 flashcards + Q&A | Section 10 Q1–Q25 | 3h | Flashcard deck (Anki) |

### Week 2 — CAN + Ethernet Protocols (Days 8–14)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 8 | CAN — frame structure, arbitration, bit timing | Section 3.1–3.2 | 2h | CAN frame sketch |
| 9 | CAN FD + LIN overview | Section 3.3–3.4 | 2h | Protocol comparison table |
| 10 | Automotive Ethernet — 100BASE-T1, 1000BASE-T1 | Section 3.5 | 2h | PHY connection diagram |
| 11 | TCP/IP stack + UDP vs TCP decision guide | Section 3.6 | 2h | OSI model for automotive |
| 12 | VLAN (802.1Q) + TSN standards overview | Section 3.7–3.8 | 2h | VLAN segmentation diagram |
| 13 | **Wireshark Lab** — install, capture on PC Ethernet | Wireshark official | 3h | 10 filters practiced |
| 14 | **Review** — Week 2 Q&A + protocol quiz | Section 10 Q26–Q50 | 3h | Protocol cheat sheet |

### Week 3 — SOME/IP, DoIP, AUTOSAR (Days 15–21)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 15 | SOME/IP — architecture, 3 communication models | Section 3.9 | 2h | SOME/IP header decode |
| 16 | SOME/IP-SD — OfferService, Subscribe flow | Section 3.9 | 2h | SD sequence diagram |
| 17 | DoIP — protocol, routing activation, diagnostic message | Section 7.4 | 2h | DoIP wire-level sequence |
| 18 | AUTOSAR Classic — layered architecture, MCAL, BSW | Section 4.1–4.3 | 2h | AUTOSAR stack diagram |
| 19 | AUTOSAR Ethernet stack — SWC to wire flow | Section 4.4 | 2h | Trace one packet through stack |
| 20 | **Project** — Set up Python DoIP client (Project 1) | Section 12 | 3h | First DoIP connection |
| 21 | **Review** — AUTOSAR + SOME/IP Q&A | Section 10 Q66–Q80 | 3h | 20 Q&A answered |

### Week 4 — UDS Diagnostics + Testing Methodology (Days 22–30)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 22 | UDS services — session model, 0x10, 0x27, 0x22 | Section 7.1–7.2 | 2h | UDS service flow diagram |
| 23 | UDS — DTC status byte, 0x19, 0x2E, 0x31 | Section 7.1–7.2 | 2h | DTC status cheat sheet |
| 24 | UDS flashing sequence + bootloader | Section 7.6 | 2h | Flash sequence diagram |
| 25 | Test methodology — V-model, test types | Section 9.1 | 2h | Test hierarchy diagram |
| 26 | RTM + ASPICE basics | Section 9.4–9.5 | 2h | Sample RTM table |
| 27 | Defect lifecycle + bug writing | Section 9.6 | 2h | Write 3 sample bug reports |
| 28 | **Project** — Extend DoIP client: add UDS services | Section 12 | 3h | 10 UDS test cases automated |
| 29 | **Mock Interview 1** — 30 minutes self-recorded | Section 10 + 11 | 2h | Video review + notes |
| 30 | **Month 1 Review** — All notes, flashcards, Q&A | All sections | 3h | 100 Q&A answered total |

---

## MONTH 2 — PRACTICE (Days 31–60)

### Week 5 — CANoe + CAPL (Days 31–37)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 31 | CANoe overview — architecture, windows, setup | Section 6.1–6.2 | 2h | CANoe setup notes |
| 32 | CAPL — event handlers, variables, timers | Section 6.3 | 2h | First CAPL program |
| 33 | CAPL — CAN message handling, signal access | Section 6.4 | 2h | CAN message simulation |
| 34 | CAPL — Ethernet packet handling, SOME/IP monitor | Section 6.5 | 2h | SOME/IP CAPL node |
| 35 | CAPL — diagnostic scripting, UDS automation | Section 6.7 | 2h | CAPL diagnostic sequence |
| 36 | **Project** — Build CAPL SOME/IP test library (Project 16) | Section 12 | 3h | 5 reusable CAPL functions |
| 37 | **Review** — CAPL Q&A | Section 10 Q51–Q65 | 3h | 15 CAPL questions answered |

### Week 6 — Automotive Ethernet Testing Deep Dive (Days 38–44)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 38 | PHY + MAC layer test cases | Section 5.1–5.2 | 2h | 6 test cases written |
| 39 | Ethernet switch testing + port mirroring | Section 5.3 | 2h | Switch test setup diagram |
| 40 | TSN testing — gPTP, TAS test cases | Section 5.4 | 2h | 4 TSN test cases |
| 41 | SOME/IP validation test cases | Section 5.5 | 2h | 8 SOME/IP test cases |
| 42 | DoIP diagnostic test cases | Section 5.6 | 2h | 7 DoIP test cases |
| 43 | **Project** — SOME/IP event monitor (Project 2) | Section 12 | 3h | Live event monitoring |
| 44 | **Debug Lab** — Wireshark analysis of captured .pcap | Wireshark sample files | 3h | Analysis report |

### Week 7 — HIL Testing + AUTOSAR Deep Dive (Days 45–51)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 45 | MIL/SIL/HIL/VIL comparison | Section 8.1 | 2h | Comparison table |
| 46 | dSPACE SCALEXIO architecture | Section 8.2–8.3 | 2h | HIL bench diagram |
| 47 | CarMaker + closed-loop simulation | Section 8.4–8.5 | 2h | AEB test scenario design |
| 48 | Fault injection — categories and techniques | Section 8.6 | 2h | Fault injection test list |
| 49 | AUTOSAR DCM/DEM deep dive | Section 4.5 | 2h | DCM flow diagram |
| 50 | ISO 26262 — ASIL levels, safety testing | Section 9.7 | 2h | ASIL comparison table |
| 51 | **Project** — HIL automation framework skeleton (Project 7) | Section 12 | 3h | 3 automated HIL tests |

### Week 8 — Projects + Integration (Days 52–60)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 52 | **Project** — ARXML diff tool (Project 4) | Section 12 | 2h | Diff tool working |
| 53 | **Project** — SOME/IP config validator (Project 5) | Section 12 | 2h | Validator with 5 rules |
| 54 | **Project** — CAN signal logger (Project 3) | Section 12 | 2h | CAN log + decode |
| 55 | Integration — Connect Projects 1 + 2 + 5 | Section 12 | 2h | Mini framework |
| 56 | **GitHub** — Upload all projects with README | GitHub | 2h | 4 repos public |
| 57 | **Mock Interview 2** — 45 minutes with a friend | Section 10 + 11 | 3h | Feedback notes |
| 58 | **Debug Scenarios** — Practice 10 debugging Q&A | Section 10 Q81–Q100 | 2h | Written answers |
| 59 | **Project** — Automotive packet analyzer (Project 8) | Section 12 | 3h | HTML analysis report |
| 60 | **Month 2 Review** — All projects, all Q&A | All sections | 3h | Resume updated with projects |

---

## MONTH 3 — INTERVIEW PREPARATION (Days 61–90)

### Week 9 — STAR Stories + Resume (Days 61–67)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 61 | STAR format — study all 35 answers | Section 11 | 2h | 5 STAR answers selected |
| 62 | Personal STAR stories — adapt template to your experience | Section 11 | 2h | 10 personal STAR stories written |
| 63 | Resume — ATS optimization, project descriptions | Section 14 | 2h | Resume v1 draft |
| 64 | Resume — peer review (share with a friend/mentor) | — | 2h | Feedback incorporated |
| 65 | LinkedIn — headline, about section, skills | Section 14 | 2h | LinkedIn profile updated |
| 66 | **Mock Interview 3** — Full 60-min interview | Section 10 + 11 | 3h | Video recording review |
| 67 | **Review** — 5 weak areas from mock interview | Relevant sections | 3h | Strengthened answers |

### Week 10 — Company-Specific Preparation (Days 68–74)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 68 | Research Bosch / Continental / KPIT job description | LinkedIn, company site | 2h | Notes on required skills |
| 69 | Research Tata Elxsi / Harman job description | LinkedIn | 2h | Notes on required skills |
| 70 | **Company deep dive** — Bosch automotive Ethernet projects | News, LinkedIn | 2h | 5 talking points for Bosch |
| 71 | **Company deep dive** — KPIT AUTOSAR expertise | KPIT website, YouTube | 2h | 5 talking points for KPIT |
| 72 | **Targeted practice** — Questions for your target company | Section 10 relevant | 2h | 20 targeted Q&As |
| 73 | **Mock Interview 4** — Company-specific simulation | — | 3h | Feedback notes |
| 74 | **Review** — 5 weakest topics from all mocks so far | Relevant sections | 3h | Final notes |

### Week 11 — Technical Deep Practice (Days 75–81)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 75 | SOME/IP deep practice — 20 questions rapid-fire | Section 10 Q31–Q50 | 2h | All answered out loud |
| 76 | DoIP + UDS deep practice | Section 10 Q76–Q90 | 2h | All answered out loud |
| 77 | CAPL coding practice — write 5 scripts from scratch | Section 6 | 2h | 5 scripts without reference |
| 78 | C coding — signal packing, state machines | Section 2 | 2h | 5 C functions from scratch |
| 79 | Debugging scenarios — 10 scenario-based Q&A | Section 10 Q81–Q100 | 2h | All answered with reasoning |
| 80 | **Project** — Complete ADAS bench suite (Project 20) | Section 12 | 3h | Integrated framework |
| 81 | **Mock Interview 5** — Technical only | — | 3h | Strongest performance yet |

### Week 12 — Final Crash Course (Days 82–90)

| Day | Topic | Resource | Time | Output |
|-----|-------|----------|------|--------|
| 82 | Read Section 15 — All cheat sheets | Section 15 | 2h | Key facts memorized |
| 83 | Ethernet cheat sheet — recite all protocols | Section 15.1 | 2h | Spoken out loud |
| 84 | AUTOSAR cheat sheet — recite all modules | Section 15.2 | 2h | Written from memory |
| 85 | CAPL cheat sheet — write key functions | Section 15.3 | 2h | Written without reference |
| 86 | UDS/DoIP cheat sheet | Section 15.4 | 2h | Services table from memory |
| 87 | **Final Mock Interview** — Full 75-min simulation | All sections | 3h | Score yourself |
| 88 | Resume final polish + LinkedIn activity (post update) | Section 14 | 2h | Job applications sent |
| 89 | **Day off** — Mental rest before interviews | — | — | Relax |
| 90 | **Day 90** — First round interviews targeted | Your job applications | — | Interview day |

---

## DAILY STUDY HABITS

```
EFFECTIVE LEARNING HABITS:

MORNING (30 min):
  • Review 10 flashcards from previous day
  • Read one short topic section

MAIN STUDY BLOCK (60–90 min):
  • Deep focus: phone off, full attention
  • Take handwritten notes (better retention than typing)
  • Draw diagrams while reading (ECU diagrams, protocol flows)

EVENING (30 min):
  • Practice writing: answer 3 interview questions in writing
  • No passive reading — active recall only

WEEKLY HABIT:
  • Every Sunday: review all notes from the week
  • Test yourself: cover answers, recite from memory
  • Update Anki flashcard deck
```

---

## FREE LEARNING RESOURCES

### YouTube Channels
```
RECOMMENDED CHANNELS:
├── Vector Informatik GmbH — CANoe/CAPL/SOME/IP tutorials
├── dSPACE GmbH — HIL/SCALEXIO tutorials
├── Embetronicx — Embedded Linux, AUTOSAR basics
├── NXP Semiconductors — S32K, Ethernet PHY tutorials
├── ETAS GmbH — AUTOSAR tools tutorials
├── Khronos Group — OpenGL, GPU compute (for ADAS graphics)
└── Udemy (paid): "Embedded C", "Automotive Ethernet" courses
```

### Documentation & Standards
```
FREE DOCUMENTATION:
├── AUTOSAR.org — free AUTOSAR specifications (Classic R21-11)
│   URL: https://www.autosar.org/standards/classic-platform/
├── IEEE 802.1 Working Group — TSN standard summaries
│   URL: https://1.ieee802.org/tsn/
├── NXP Application Notes — TJA1100, SJA1110 datasheets
│   URL: https://www.nxp.com
├── Vector Knowledge Base — CAPL, CANoe guides
│   URL: https://kb.vector.com/
├── Wireshark Wiki — Protocol dissectors
│   URL: https://wiki.wireshark.org/
└── python-can library docs
    URL: https://python-can.readthedocs.io/
```

### Practice Environments
```
FREE PRACTICE TOOLS:
├── Wireshark — Ethernet/SOME/IP capture (free)
├── python-can + virtual CAN (socketcan on Linux) — CAN simulation
├── QEMU — Run ARM firmware in emulator
├── Virtual Box + Ubuntu — Linux Ethernet practice
├── GNS3 — Network topology simulation (VLAN, routing)
├── Scapy — Craft and send custom Ethernet packets
└── Simulink Trial — 30-day trial for MIL/SIL practice
```

### GitHub Repositories to Study
```
STUDY THESE REPOS:
├── github.com/linux-can/can-utils     — SocketCAN utilities
├── github.com/cantools/cantools       — DBC parsing in Python
├── github.com/eerimoq/asn1tools      — ASN.1 parsing (SOME/IP data types)
├── github.com/nicovank/automotive-...  — Automotive protocols
├── github.com/pywireshark/pyshark     — Python Wireshark bridge
└── github.com/stiebrs/someip          — SOME/IP Python implementation
```

---

## STUDY SCHEDULE TEMPLATES

### For Working Professionals (2–3 hours/day)
```
WORKING PROFESSIONAL ADAPTATION:

6:00 AM – 7:00 AM: Study session (before work)
  • Focus: theory and reading
  • No project work (context switching too hard)

7:00 PM – 8:30 PM: Practice session (after work)
  • Focus: coding, tool practice, project work

Weekend: 4 hours Saturday + 4 hours Sunday
  • Saturday AM: Project development
  • Saturday PM: Interview practice
  • Sunday AM: Weekly review + weak topics
  • Sunday PM: Mock interview + feedback
  
Timeline: 90 days → 3 months
At this pace: Fully interview-ready in 90 days
```

### For Full-Time Job Seekers (5–6 hours/day)
```
FULL-TIME STUDY SCHEDULE:

8:00 AM – 10:00 AM: Theory study (Sections 1-10)
10:00 AM – 12:00 PM: Project coding
12:00 PM – 1:00 PM: Lunch + walk (essential break)
1:00 PM – 3:00 PM: Practice coding + CAPL
3:00 PM – 4:30 PM: Interview Q&A practice
4:30 PM – 5:00 PM: Flashcard review

Timeline: 45 days (half the time!) to interview-ready
Week 7: Start applying while finishing Month 2
```

---

## PROGRESS TRACKING TEMPLATE

```
WEEKLY SELF-ASSESSMENT:

Week ___:
□ Sections read this week: ___
□ Interview questions answered: ___
□ Projects advanced: ___
□ Mock interviews done: ___

KNOWLEDGE SELF-RATING (1-10):
  Embedded C/C++:           ___
  CAN/CAN FD protocols:     ___
  Automotive Ethernet:      ___
  SOME/IP:                  ___
  DoIP/UDS:                 ___
  AUTOSAR Classic:          ___
  CANoe/CAPL:               ___
  HIL Testing:              ___
  Test Methodology:         ___
  STAR Stories:             ___

ACTION for lowest score: _____________________
```

---

*Next Section → [Section 14: Resume & LinkedIn](14_Resume_LinkedIn.md)*

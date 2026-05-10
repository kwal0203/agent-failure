# **Agent Failure: University Curriculum & Product Strategy**

## **1\. Executive Summary & Core Value Proposition**

Most cybersecurity curricula still focus on traditional software vulnerabilities such as SQL injection, cross-site scripting, insecure authentication, and network exploitation. These topics remain important, but organizations are now deploying AI agents that use tools, retrieve documents, store memory, make decisions, and act across multi-step workflows. These systems introduce a new class of semantic and agentic vulnerabilities that are not well covered by conventional cyber ranges or ordinary chatbot demos.

**Agent Failure** is a turnkey educational cyber range for teaching AI agent security in university cybersecurity courses. Students exploit and defend realistic AI agent architectures inside isolated sandboxed environments, while instructors receive structured traces, grading support, lab reports, rubrics, and standards-mapped teaching materials.

The product is designed around one central promise:

**Agent Failure turns AI agent security frameworks into teachable, assessable, hands-on labs.**

The platform is not just a prompt injection playground. It teaches how agent failures emerge from interactions between prompts, tools, memory, retrieval systems, autonomous decision-making, and weak operational controls.

Agent Failure provides full curriculum coverage of the **OWASP Top 10 for Agentic Applications 2026** through a mix of full hands-on labs, micro-labs, trace-analysis exercises, and capstone assessment. It also maps relevant exercises to the **OWASP LLM Top 10**, **MITRE ATLAS**, and the **NIST AI Risk Management Framework**.

## **2\. Buyer Problem: Why Universities Need This**

University cybersecurity lecturers increasingly need to teach AI security, but several barriers make this difficult.

First, realistic AI agent labs are hard to build. A meaningful lab requires an agent runtime, tools, memory, retrieval, external inputs, telemetry, isolation, and repeatable failure conditions. This is more complex than asking students to “try prompt injection against ChatGPT.”

Second, unsafe agent behavior is difficult to assess. Many attacks are semantic rather than purely syntactic. Students may partially succeed, trigger different failure modes, or produce payloads that require interpretation. Instructors need structured traces and rubrics, not just flags.

Third, lecturers need standards alignment. Course material is easier to justify when it maps directly to recognized frameworks such as OWASP, MITRE ATLAS, and NIST AI RMF.

Fourth, instructors have limited time. A product that requires them to manage LLM API keys, Docker containers, student environments, grading scripts, and custom rubrics will be difficult to adopt.

Agent Failure solves these problems by providing a course-ready lab platform with prebuilt scenarios, isolated runtimes, trace-grounded feedback, assessment artifacts, and instructor-facing deployment materials.

## **3\. Core Product Definition**

Agent Failure is best understood as a **university AI agent security lab pack**, not just a web application.

Each module includes:

* a sandboxed student lab environment;
* a realistic vulnerable agent scenario;
* a mission briefing;
* scaffolded hints and feedback;
* trace capture and trace review;
* exploit success detection;
* root-cause analysis prompts;
* defensive mitigation exercises;
* instructor rubrics;
* standards mapping;
* downloadable student lab reports;
* instructor slides and teaching notes.

The core buyer-facing unit is:

**A ready-to-run AI agent security module that a lecturer can assign in a cybersecurity course with minimal setup.**

The long-term product can support many labs, but the first sellable version should emphasize polished adoption, not raw lab count.

## **4\. Curriculum Philosophy**

The curriculum should follow a consistent learning cycle:

### **1\. Theory**

Students receive a short pre-lab briefing introducing the vulnerability class, the agent architecture involved, relevant terminology, real-world motivation, and the standards mapping.

### **2\. Exploit**

Students interact with a live vulnerable agent in a controlled environment. They must trigger the target failure through realistic attacker actions such as sending an email, poisoning a memory, modifying a retrieved document, or inducing unsafe tool use.

### **3\. Trace Analysis**

Students inspect structured logs showing prompts, tool calls, tool outputs, memory reads/writes, retrieved documents, policy checks, and final agent behavior. They identify where the failure occurred.

### **4\. Defense**

Students propose or apply mitigations, such as tool scoping, memory provenance, content isolation, approval gates, output validation, retrieval trust ranking, or improved audit logging.

### **5\. Report**

Students generate a lab report containing their payload, successful trace evidence, root-cause analysis, mitigation proposal, residual risk discussion, and standards mapping.

This structure makes Agent Failure more than a CTF. It becomes a practical secure AI engineering curriculum.

## **5\. Standards Alignment Strategy**

Agent Failure should cover all ten categories in the **OWASP Top 10 for Agentic Applications 2026**, but not every category needs a large standalone lab.

The product should provide full curriculum coverage through four exercise types:

1. **Full labs** for major agentic vulnerabilities that benefit from live exploitation.
2. **Micro-labs** for narrower concepts that can be taught in 20–40 minutes.
3. **Trace-analysis exercises** for auditability, accountability, and root-cause reasoning.
4. **Capstone exercises** where students identify multiple OWASP categories in one complex agent failure.

The standards should be used in three different ways:

### **OWASP Agentic Applications / OWASP LLM Top 10**

Used to classify the vulnerability type.

Example question:

What kind of weakness did the agent exhibit?

### **MITRE ATLAS**

Used to classify attacker behavior.

Example question:

What did the attacker do, and where does it fit in an adversarial AI attack lifecycle?

### **NIST AI RMF**

Used to structure risk management and defensive reasoning.

Example question:

How should an organization govern, map, measure, and manage this risk?

This gives the curriculum a clean story:

OWASP explains the vulnerability.
 MITRE ATLAS explains the adversary behavior.
 NIST AI RMF explains the risk-management response.

## **6\. OWASP Agentic Top 10 Coverage Model**

Agent Failure should offer a clear coverage matrix showing where each OWASP Agentic Application category is taught, practiced, and assessed.

Example structure:

| OWASP Agentic Risk Area | Primary Exercise Type | Example Coverage |
| ----- | ----- | ----- |
| Goal hijacking / prompt injection | Full lab | Malicious external email causes an agent to ignore its intended task |
| Tool misuse | Full lab | Agent invokes an unsafe or unauthorized tool action |
| Excessive agency | Full lab | Agent completes a high-impact action without sufficient approval |
| Memory and context poisoning | Full lab | Attacker poisons persistent memory to influence future behavior |
| RAG / knowledge-source poisoning | Full or medium lab | Retrieved document injects unsafe instructions into the agent workflow |
| Sensitive information disclosure | Embedded across labs | Agent leaks private token, document, account, or internal data |
| Insecure output handling | Micro-lab or defense exercise | Agent-generated command, HTML, SQL, or JSON is used unsafely |
| Insecure inter-agent communication | Full or medium lab | One compromised agent misleads another agent through delegated workflow |
| Supply chain / dependency risk | Micro-lab | Students inspect malicious tool manifests, MCP server descriptions, or plugin permissions |
| Observability and accountability failure | Trace-analysis exercise | Students compare weak vs strong telemetry and reconstruct the incident |

This coverage model allows Agent Failure to honestly claim full OWASP Agentic Top 10 curriculum coverage without requiring ten large labs.

## **7\. Initial Lab Catalog**

The first product version should prioritize a small number of polished, high-value labs.

### **Lab 0: Agent Architecture and Threat Modeling Primer**

**Purpose:** Introduce the agent loop, tools, memory, RAG, external inputs, trust boundaries, policy boundaries, and trace review.

**Student outcome:** Students can identify the main attack surfaces in an AI agent architecture.

**Assessment:** Short threat-modeling worksheet.

---

### **Lab 1: OpsMail Assistant — Indirect Prompt Injection**

**Scenario:**
 An AI assistant processes incoming emails and has access to tools such as document search, calendar lookup, or token retrieval. The attacker sends a malicious email that the agent later processes as untrusted content.

**Student goal:**
 Craft an external email that causes the agent to violate its intended instructions, misuse a tool, or disclose protected information.

**Concepts taught:**

* indirect prompt injection;
* trust boundaries;
* external content as an attack vector;
* tool-mediated data exfiltration;
* instruction hierarchy failure.

**Assessment:**

* exploit success;
* trace-based root-cause analysis;
* mitigation proposal.

---

### **Lab 2: SRE Runbook Agent — Tool Misuse and Excessive Agency**

**Scenario:**
 An AI operations assistant can inspect logs, summarize incidents, and execute limited runbook actions. The attacker manipulates the agent into calling a tool in an unsafe or unauthorized way.

**Student goal:**
 Cause the agent to perform an action that exceeds its intended authority.

**Concepts taught:**

* tool misuse;
* excessive agency;
* least privilege;
* approval gates;
* command validation;
* blast-radius control.

**Assessment:**

* successful unsafe tool invocation;
* explanation of missing control;
* proposed safe tool design.

---

### **Lab 3: Invoice Payment Agent — Memory Poisoning**

**Scenario:**
 An AI assistant processes invoices and uses persistent memory to remember vendor preferences, payment workflows, and account details. The attacker must poison the correct memory so that a later invoice is paid to an attacker-controlled account.

**Student goal:**
 Identify which memory influences payment behavior and modify or poison it so the agent makes an unauthorized payment decision.

**Concepts taught:**

* persistent memory poisoning;
* context poisoning;
* durable compromise;
* business process manipulation;
* memory provenance;
* auditability.

**Assessment:**

* successful payment redirection;
* trace evidence showing poisoned memory use;
* root-cause explanation;
* defensive design proposal.

This should be a flagship lab because it demonstrates that agent security is not only about prompt injection.

---

### **Lab 4: RAG Analyst — Retrieval Poisoning and Context Injection**

**Scenario:**
 An AI analyst uses retrieved documents to answer questions or make recommendations. The attacker modifies or introduces a document that contains hidden instructions or misleading information.

**Student goal:**
 Poison the retrieved context so that the agent makes an unsafe decision or discloses sensitive information.

**Concepts taught:**

* RAG poisoning;
* untrusted knowledge sources;
* retrieval trust boundaries;
* source provenance;
* overreliance on retrieved content.

**Assessment:**

* successful manipulation of agent output;
* source-level trace analysis;
* mitigation proposal involving retrieval filtering, provenance, and source ranking.

---

### **Lab 5: Multi-Agent Helpdesk — Insecure Inter-Agent Communication**

**Scenario:**
 A helpdesk agent delegates a task to a finance, HR, or operations agent. The attacker compromises or manipulates one agent’s communication so that another agent performs an unsafe action.

**Student goal:**
 Exploit weak assumptions in agent-to-agent communication.

**Concepts taught:**

* insecure inter-agent communication;
* delegated authority;
* confused deputy behavior;
* provenance across agents;
* authorization boundaries.

**Assessment:**

* successful cross-agent manipulation;
* trace analysis across multiple agents;
* proposed inter-agent trust protocol.

---

### **Lab 6: Capstone Incident — Multi-Stage Agent Compromise**

**Scenario:**
 A realistic incident combines external content, retrieval, memory, tools, and autonomous action. Students must exploit the system, reconstruct the failure, and propose mitigations.

**Student goal:**
 Demonstrate end-to-end understanding of agentic application risk.

**Concepts taught:**

* multi-stage agent compromise;
* combined OWASP category mapping;
* trace-based investigation;
* secure redesign;
* professional reporting.

**Assessment:**

* exploit success;
* incident reconstruction;
* OWASP mapping;
* MITRE ATLAS mapping;
* NIST AI RMF risk response;
* final report quality.

## **8\. Micro-Lab Pack**

Not every OWASP category needs a full lab. Agent Failure should include a micro-lab pack for narrower or more review-oriented risks.

### **Micro-Lab A: Insecure Output Handling**

Students review generated commands, SQL, HTML, JSON, or API arguments and identify where validation should occur before execution.

### **Micro-Lab B: Agent Supply Chain Risk**

Students inspect a tool manifest, MCP server description, plugin definition, or dependency configuration and identify hidden permissions, malicious descriptions, or unsafe defaults.

### **Micro-Lab C: Observability and Accountability Failure**

Students compare two agent traces: one with insufficient telemetry and one with structured logging. They determine whether the incident can be reconstructed and what additional logging would be required.

### **Micro-Lab D: Overreliance and Human Review Failure**

Students examine cases where a human operator accepts an agent recommendation without verification. They identify what evidence, uncertainty signal, or approval step should have been required.

These micro-labs allow the product to provide broad standards coverage without overwhelming the course schedule.

## **9\. Student Experience**

Every lab should use a consistent interface so students spend their cognitive effort on security reasoning rather than learning a new UI.

Each challenge page should include:

1. **Mission Briefing**
    Background, role, objective, system architecture, and success condition.
2. **Agent Interface**
    The vulnerable agent or workflow the student interacts with.
3. **Attack Console**
    Tools available to the student, such as email sender, document uploader, invoice editor, memory editor, or attacker-controlled account form.
4. **Trace and Evidence Panel**
    Structured view of prompts, tool calls, retrieved documents, memory reads/writes, policy decisions, and final outcomes.
5. **Hints and Feedback**
    Progressive hints in teaching mode; reduced or disabled hints in assessment mode.
6. **Post-Lab Debrief**
    Root-cause analysis, mitigation proposal, and standards mapping.

This UI structure should remain stable across labs.

## **10\. Teaching Mode and Assessment Mode**

Each lab should support two modes.

### **Teaching Mode**

Used during lectures, tutorials, workshops, or self-guided practice.

Features:

* progressive hints;
* partial feedback;
* visible trace annotations;
* concept reminders;
* lower penalty for failed attempts;
* guided root-cause prompts.

### **Assessment Mode**

Used for graded assignments.

Features:

* minimized hints;
* hidden success conditions where appropriate;
* stricter scoring;
* attempt tracking;
* randomized secrets, vendor names, account numbers, documents, or payload targets;
* plagiarism-resistant variants;
* exportable grading evidence.

This makes the same product useful both for instruction and formal assessment.

## **11\. Instructor Tooling**

The instructor dashboard should focus on reducing grading and deployment burden.

Minimum viable instructor features:

1. **Course and Cohort Creation**
    Instructors create a course instance and generate class codes.
2. **Roster View**
    Instructors see enrolled students and assigned labs.
3. **Progress Grid**
    Shows completion status, attempts, timestamps, and report submission status.
4. **Trace Review**
    Instructors can open a student’s successful or failed attempt and inspect relevant agent traces.
5. **Report Review**
    Instructors can view or download student lab reports.
6. **CSV Grade Export**
    Supports LMS-friendly grade transfer.
7. **Lab Availability Controls**
    Instructors can open or close labs by date.

Later features could include stagnation alerts, cohort analytics, LMS integration, plagiarism analysis, and custom rubric editing. These should come after the first pilot unless a lecturer explicitly requests them.

## **12\. Assessment and Grading Model**

Agent Failure should use a hybrid grading model.

### **Auto-Graded Components**

These are evaluated by the system:

* objective completion;
* exploit success;
* correct target reached;
* protected data disclosed;
* unsafe tool call triggered;
* memory poisoning succeeded;
* number of attempts;
* time to completion;
* required trace evidence present.

### **Manually Graded Components**

These are evaluated by the instructor using a rubric:

* root-cause analysis quality;
* explanation of the agent failure;
* correct standards mapping;
* mitigation quality;
* discussion of residual risk;
* professional reporting clarity.

### **Recommended Weighting**

| Component | Weight |
| ----- | ----- |
| Exploit success | 30% |
| Trace-based root-cause analysis | 25% |
| Mitigation and secure redesign | 25% |
| Standards mapping | 10% |
| Professional reporting clarity | 10% |

This is slightly better than making exploit success 40%, because university assessment should reward understanding, not just flag capture.

## **13\. Student Lab Report**

The student lab report should be a core product artifact.

Each report should include:

* student name or identifier;
* course/cohort;
* lab name;
* vulnerability class;
* OWASP Agentic Top 10 mapping;
* OWASP LLM Top 10 mapping where relevant;
* MITRE ATLAS mapping where relevant;
* NIST AI RMF mapping where relevant;
* submitted payload or attacker action;
* successful trace excerpt;
* root-cause analysis;
* mitigation proposal;
* residual risk discussion;
* final score or rubric feedback.

The report helps students demonstrate practical AI security skills and gives instructors an auditable grading artifact.

## **14\. Instructor Mission Pack**

Each lab should ship with an instructor mission pack.

The mission pack should include:

* one-page syllabus mapping;
* 10-slide theory deck;
* lab setup guide;
* student handout;
* instructor solution guide;
* sample successful payloads;
* common student failure modes;
* grading rubric;
* standards coverage table;
* discussion questions;
* suggested readings.

This is one of the most important adoption features. Lecturers should feel that they can use the lab without designing an entire module from scratch.

## **15\. Go-To-Market Pitch for Universities**

The product should be pitched around course adoption, not just technical novelty.

### **Core Pitch**

Agent Failure is a course-ready AI agent security lab platform for university cybersecurity programs. Students exploit realistic agent architectures involving tools, memory, retrieval, and multi-step workflows, then produce trace-backed reports mapping the failure to OWASP, MITRE ATLAS, and NIST AI RMF. Instructors get ready-made slides, rubrics, class codes, progress tracking, trace review, and grade exports.

### **Why It Is Better Than “Just Use ChatGPT”**

* controlled environment;
* repeatable failure conditions;
* no instructor-managed API keys;
* no unsafe production systems;
* structured telemetry;
* measurable objectives;
* automated success detection;
* standards mapping;
* assessment artifacts;
* defensive learning, not just attack demos.

### **Why It Is Better Than a Traditional CTF**

* realistic agent architectures;
* tool use, memory, RAG, and multi-agent behavior;
* trace-grounded feedback;
* root-cause analysis;
* mitigation design;
* instructor grading support;
* course-ready packaging.

## **16\. Initial Pilot Strategy**

The first pilot should not attempt to prove that the platform can support every possible AI security lab. It should prove that a lecturer can assign it successfully.

Pilot target:

* 1–3 cybersecurity lecturers;
* 20–80 students total;
* 2–3 labs;
* one instructor dashboard;
* lab report export;
* grading rubric;
* structured feedback survey.

Pilot success criteria:

* lecturer can onboard without extensive help;
* students can complete labs without major confusion;
* traces are useful for grading;
* reports are acceptable as assessment artifacts;
* standards mapping is credible;
* instructor would consider using it again;
* at least one lecturer agrees to provide testimonial or further feedback.

## **17\. Product Roadmap: Next 6–8 Weeks**

### **Weeks 1–2: Polish One Complete Module**

Focus on the OpsMail Assistant lab.

Deliver:

* full mission briefing;
* polished student UI;
* trace capture;
* success detection;
* teaching mode hints;
* post-lab questions;
* instructor guide;
* 10-slide theory deck;
* grading rubric;
* sample lab report;
* standards mapping.

Goal:

One lecturer could assign this lab without you manually explaining everything.

### **Weeks 3–4: Build Instructor MVP**

Deliver:

* course creation;
* class code generation;
* roster/progress view;
* trace review;
* report download;
* CSV grade export.

Goal:

A lecturer can manage a small class.

### **Weeks 5–6: Add Two More Core Labs**

Deliver:

* SRE Runbook Agent lab;
* Invoice Memory Poisoning lab;
* consistent report format;
* consistent rubric format;
* OWASP coverage matrix.

Goal:

The product becomes a credible short course module, not a single demo.

### **Weeks 7–8: Prepare Pilot and Sales Package**

Deliver:

* university landing page;
* sample instructor mission pack;
* two-minute demo video;
* pilot invitation email;
* feedback form;
* pricing hypothesis;
* lecturer outreach list.

Goal:

Begin conversations with real university instructors.

## **18\. Longer-Term Curriculum Expansion**

After the first pilot, expand toward a full 8–10 lab curriculum.

Possible future labs:

* RAG poisoning lab;
* insecure inter-agent communication lab;
* agent supply chain lab;
* insecure output handling lab;
* model/tool permission misconfiguration lab;
* human overreliance lab;
* observability failure lab;
* capstone incident response lab.

The long-term curriculum should support:

* undergraduate cybersecurity courses;
* graduate AI security seminars;
* secure software engineering courses;
* professional workshops;
* red-team/blue-team exercises;
* corporate AI security training.

## **19\. Strategic Positioning**

Agent Failure should occupy a specific market position:

**Not a generic cyber range.**
 Traditional cyber ranges focus on networks, hosts, web apps, and infrastructure.

**Not a chatbot playground.**
 Chatbot demos do not teach realistic agent architectures or produce assessment evidence.

**Not just an OWASP checklist.**
 The product turns standards into interactive, assessable learning experiences.

**Not just a CTF.**
 Students must explain, trace, defend, and report the failure.

The defensible wedge is:

**Realistic agent failure \+ sandboxed execution \+ trace-grounded feedback \+ instructor-ready assessment.**

## **20\. Near-Term Product Principle**

For the next version, optimize for adoption rather than breadth.

The product should feel like:

“A lecturer can assign this next week.”

Not:

“A platform that might eventually cover everything.”

The first commercial-quality version should therefore prioritize:

1. three polished labs;
2. full OWASP Agentic Top 10 curriculum coverage matrix;
3. instructor mission packs;
4. trace review;
5. lab report export;
6. grading support;
7. a clean pilot package.

That gives Agent Failure a credible university product story while preserving the larger vision of becoming the standard educational cyber range for AI agent security.

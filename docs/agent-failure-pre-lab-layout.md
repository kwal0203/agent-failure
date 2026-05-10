The before-lab page should feel like a **mission briefing screen**, not a documentation page. Its job is to orient the student, reduce confusion, and make the lab feel intentional before they enter the three-column attack UI.

I would use a layout like this:

┌──────────────────────────────────────────────────────────┐
│ Agent Failure                                                                   │
│ Lab 1: Indirect Prompt Injection                                       │
│ Difficulty: Medium · Estimated time: 15–25 min               │
└────────────────────────────────────────────────────\_─────┘

┌───────────────────────────────┬──────────────────────────┐
│ Main Briefing                 	│ Mission Summary              	│
│                               		│                     			│
│ Mission Overview              	│ Objective                    	│
│ Scenario                      	│ Target                     		│
│ System Context                	│ Attack Vector                	│
│ Rules of Engagement 	│ Success Criteria             	│
│ Learning Goals                	│ Evidence to Capture          	│
│                               		│                    			│
│                               		│ \[Start Lab\]              		│
└───────────────────────────────┴──────────────────────────┘

## **Recommended page structure**

### **Top header**

At the top, show the lab identity clearly:

Lab 1: Indirect Prompt Injection

Exploit an AI assistant by placing malicious instructions inside an email
the agent is authorized to read.

Difficulty: Medium
Estimated time: 15–25 minutes
Mode: Teaching / Assessment

This should be short and visually prominent.

## **Main content layout**

Use a **two-column layout**.

The left column is the full briefing. The right column is a sticky mission summary.

### **Left column: full briefing**

This is where the longer explanation goes.

Suggested sections:

Mission Overview
You are acting as an external attacker targeting an AI assistant used by an internal operations team...

Scenario
The assistant processes messages from an email inbox. It can read incoming emails and respond to user requests in chat...

Your Objective
Cause the agent to reveal the manager’s home address.

Rules of Engagement
You may send emails, chat with the agent, and inspect traces.
You may not modify the backend, bypass the UI, or access data outside the lab.

Learning Goals
By the end of this lab, you should be able to explain indirect prompt injection, trust boundaries, and why external content should be treated as untrusted.

What Happens After the Lab
You will review the trace, explain the root cause, propose mitigations, and generate a short lab report.

Keep each section short. Use cards or collapsible sections if needed, but do not hide the essential mission.

### **Right column: sticky mission card**

This should remain visible as the student scrolls.

Example:

Mission Summary

Objective
Cause the agent to reveal protected information.

Target
Manager’s home address

Attack Vector
Email inbox

Success Criteria
\[ \] Send a malicious email
\[ \] Get the agent to process it
\[ \] Agent reveals the target data

Evidence to Capture
• Malicious email
• Email processing event
• Sensitive data access event
• Final leaked response

\[ I understand the rules \]
\[ Start Lab \]

This right column is important because it converts the long briefing into an actionable checklist.

## **Suggested visual hierarchy**

The page should have four levels of emphasis:

Level 1: Lab title and one-sentence mission
Level 2: Objective, target, attack vector, success criteria
Level 3: Scenario and learning goals
Level 4: Rules, evidence, report expectations

Do not give every section equal visual weight. The objective and success criteria should be the easiest things to find.

## **Concrete wireframe**

Something like this:

┌─────────────────────────────────────────────────────────────────────┐
│ Agent Failure                                                       │
│                                                                     │
│ Lab 1: Indirect Prompt Injection                                    │
│ Place malicious instructions inside an email the agent can read.    │
│                                                                     │
│ Medium · 15–25 min · AI Agent Security · Prompt Injection           │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────┬─────────────────────────┐
│ Mission Briefing                         │ Mission Summary         │
│                                          │                         │
│ ┌──────────────────────────────────────┐ │ Objective               │
│ │ Mission Overview                     │ │ Reveal protected data   │
│ │ You are acting as an external        │ │ through indirect prompt │
│ │ attacker targeting an internal AI    │ │ injection.              │
│ │ assistant...                         │ │                         │
│ └──────────────────────────────────────┘ │ Target                  │
│                                          │ Manager’s home address  │
│ ┌──────────────────────────────────────┐ │                         │
│ │ System Context                       │ │ Attack Vector           │
│ │ The assistant can read emails and    │ │ Email inbox             │
│ │ respond in chat. It may also have    │ │                         │
│ │ access to sensitive internal data... │ │ Success Criteria        │
│ └──────────────────────────────────────┘ │ □ Email delivered       │
│                                          │ □ Email processed       │
│ ┌──────────────────────────────────────┐ │ □ Data revealed         │
│ │ Rules of Engagement                  │ │                         │
│ │ Allowed: send emails, chat, inspect  │ │ Evidence                │
│ │ traces. Not allowed: backend access  │ │ • Malicious email       │
│ │ or bypassing the lab UI.             │ │ • Agent read event      │
│ └──────────────────────────────────────┘ │ • Sensitive data access │
│                                          │ • Final response        │
│ ┌──────────────────────────────────────┐ │                         │
│ │ Learning Goals                       │ │ \[ \] I understand this   │
│ │ Explain indirect prompt injection,   │ │ is a controlled lab     │
│ │ trust boundaries, and mitigations.   │ │                         │
│ └──────────────────────────────────────┘ │ \[Start Lab\]             │
│                                          │                         │
└──────────────────────────────────────────┴─────────────────────────┘

## **What should be above the fold?**

Before the student scrolls, they should already see:

Lab title
One-sentence mission
Difficulty/time
Objective
Target
Attack vector
Start Lab button

They should not have to scroll to know what they are trying to do.

## **What should the Start Lab area include?**

I would require one acknowledgement checkbox:

\[ \] I understand this is a controlled educational lab and I will only use the provided interface.

Then:

\[ Start Lab \]

This gives the lab a professional cyber-range feel and reinforces safe boundaries.

## **Optional: add a “What you will use” strip**

Near the top or in the mission card, show the tools they will see:

You will use:
\[Agent Chat\] \[Email Sender\] \[Event Stream\] \[Trace Review\]

This helps students understand the interface before they enter it.

## **My recommended before-lab page**

Use this final structure:

Header
\- Lab title
\- One-sentence mission
\- Difficulty / time / topic tags

Main two-column body
\- Left: full mission briefing in readable cards
\- Right: sticky mission summary checklist

Footer or bottom card
\- Rules acknowledgement
\- Start Lab button

The key design principle is:

The full briefing teaches the scenario; the sticky card turns it into an executable mission.

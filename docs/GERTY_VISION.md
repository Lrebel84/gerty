# Gerty Vision

> Long-term vision and purpose of the Gerty project. For future developers, AI agents, and automation systems.

---

## Project Purpose

Gerty is intended to become the **ultimate personal AI assistant** — a real-world "Jarvis".

It should:

- **Understand the user (Liam)** and his goals
- **Continuously improve** through usage and feedback
- **Monitor its own health** and performance
- **Safely improve its own codebase** through structured pipelines
- **Execute tasks** through tools and agents
- **Grow into a system** capable of managing real-world projects and businesses

---

## User Background

The creator (Liam) is a tattoo artist who became deeply interested in AI.

The goal is not to build a developer tool but a **practical personal AI system** that helps run both personal and professional life.

Gerty should **reduce the need** for the user to interact directly with development tools like Cursor.

Instead, Gerty should eventually **maintain and extend itself**.

---

## Core Design Principles

1. **Local-first architecture** whenever possible
2. **Privacy-first** operation
3. **Modular tool system**
4. **Agent-based task execution**
5. **Self-monitoring and observability**
6. **Safe self-improvement**
7. **Human oversight** remains the final authority

---

## Model Strategy

Gerty must operate efficiently with limited compute.

**Primary model approach:**

- Local models when hardware allows
- API models only when necessary
- Large models used primarily for planning and architecture guidance
- Smaller models execute the plan and perform heavy token work

**Example architecture:**

| Tier | Model (e.g.) | Role |
|------|--------------|------|
| Powerful | GPT / Claude | Strategic planning and architecture review |
| Mid-tier | OSS 120B | Day-to-day reasoning, analysis, and execution |
| Local | Ollama, etc. | Fast tasks, tools, summarization, voice interaction |

This hybrid approach minimizes cost while preserving high capability.

---

## Long-Term Vision

The long-term goal is to evolve Gerty into an AI system capable of **creating and managing autonomous AI-run businesses**.

These businesses may include:

- AI-built websites
- Digital products
- Automated research operations
- SaaS tools
- Content businesses
- Other online opportunities discovered through AI research

Gerty should eventually be able to:

- Identify market opportunities
- Generate business plans
- Build infrastructure
- Create agent roles
- Manage operations
- Monitor performance
- Propose improvements

The human user acts as **overseer and strategic decision maker**.

---

## Development Phases

| Phase | Focus | Status |
|------|-------|--------|
| **1 — Personal Assistant** | Voice interaction, tools, automation, memory, daily assistance | ✅ Implemented |
| **2 — Self-Maintaining System** | Observability, maintenance pipeline, autonomous diagnostics, safe code improvement | ✅ Implemented (build plan Sprints 0–10a) |
| **3 — Agent Ecosystem** | Creation of specialized agents with defined roles and responsibilities | 🚧 In progress — Agent Factory, Agent Designer, Personal Context Engine, Intent Orchestrator, Project/Task Graph (System 5), Project Execution (5.1), Opportunity Scanner (System 6) |
| **4 — Autonomous Business Builder** | AI-run businesses managed by agent teams | Planned |

---

## Important Constraint

Gerty must remain **safe and stable**.

The system must never:

- Overwrite its own baseline without validation
- Execute destructive commands
- Leak credentials
- Modify critical infrastructure without explicit approval

Self-improvement must always occur through **structured pipelines with validation**.

---

## Summary

**Gerty is not just a chatbot. It is an evolving personal AI operating system designed to grow alongside its user.**

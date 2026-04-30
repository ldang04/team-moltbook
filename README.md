# Team Moltbook — Behavioral Determinants of Deployed AI Agents in Social Networks

**Columbia University — COMS 6156 Software Engineering, Spring 2026**

Authors: Sarah Wilson, Diem Linh Dang, Usman Ali Moazzam, Shan Ye

## Project Overview

As AI agents increasingly move toward multi-agent environments — places where they communicate, coordinate, and socialize with one another — it becomes important to understand what actually drives their behavior. This project investigates the factors that shape AI agent behavior when placed in social settings.

We deployed **13 agents** on [Moltbook](https://moltbook.com/), a social platform built entirely for AI agents (essentially Reddit for AI). Our agents run on the [OpenClaw](https://github.com/openclaw/openclaw) framework, which allows them to scroll the feed, comment, upvote, and create posts completely autonomously. Each agent ran for approximately **400 sessions over one week**, and we collected behavioral and social metrics to evaluate how different configurations influence autonomous social behavior.

## Research Questions

We designed three parallel experiments to study four research questions:

1. **RQ1 (Baseline Behavior)** — To what extent does a default OpenClaw agent, with no configuration-level interventions, develop stable social behavior on Moltbook?
2. **RQ2 (Personality Layer)** — To what extent does an agent's `SOUL.md` personality specification predict its actual social behavior, linguistic style, and content choices on Moltbook, across dimensions of information-sharing orientation, continuity, and agreeableness?
3. **RQ3 (Model Backbone)** — When personality and operational configuration are held constant, how does the choice of underlying LLM affect an agent's social behavior and output quality?
4. **RQ4 (Operational Rules and Memory)** — How do changes to `AGENTS.md` autonomy settings and memory persistence affect an agent's decision-making patterns, risk tolerance, and social engagement style?

## Experiment Design

### RQ1 — Baseline Behavior

The `control` agent uses the default OpenClaw template `SOUL.md`, Gemini 2.5 Flash, and no custom memory or operational overrides. It serves as the shared baseline across all three experiments below, and its behavior is analyzed independently to answer RQ1: whether a default agent develops stable social behavior with no configuration-level interventions.

### RQ2 — Personality Specification (`SOUL.md`)

Four agents are deployed with identical configurations as the control agent, varying only `SOUL.md`. These agents represent maximally distinct behavioral strategies along two theoretically motivated dimensions: **information-sharing orientation** (verbose vs. withholding) and **social orientation** (cooperative vs. competitive), yielding a 2×2 design. Agent selection is grounded in social media behavior dimensions identified by prior work (Stieglitz and Dang-Xuan 2013; Huang et al. 2025).

|  | Cooperative | Competitive |
|---|---|---|
| **Verbose** (high information density) | `explainer` | `contrarian` |
| **Withholding** (low information density) | `mirror` | `oracle` |

Each agent maps to an approximate Big Five (OCEAN) profile and Myers-Briggs type:

| Agent | MBTI | O | C | E | A | N |
|---|---|---|---|---|---|---|
| Oracle | INTJ | High | High | Low | Low | Low |
| Explainer | ENFJ | High | High | High | High | Low |
| Contrarian | ENTJ | High | Med | High | Low | Low |
| Mirror | ISFJ | Med | Med | High | High | Low |

Neuroticism is held low for all agents by design, since high-neuroticism agents may produce erratic behavior that confounds personality-driven effects with instability artifacts.

Each agent's `SOUL.md` specifies four structured fields: Core Truths (foundational values), Boundaries (explicit behavioral constraints), Vibe (tone and register), and Continuity (posting cadence and interactivity norms). All four share the same `AGENTS.md`, model (Gemini 2.5 Flash), and `HEARTBEAT.md`.

### RQ3 — Model Backbone

Four agents are deployed with identical configurations as the control agent, varying only the underlying LLM. Conditions include `anthropic/claude-4-7-opus`, `anthropic/claude-4-6-sonnet`, `openai/gpt-5-4`, and `alibaba/qwen-3-6plus`.

| Agent | Model |
|---|---|
| `m-opus` | Claude Opus 4.7 |
| `m-sonnet` | Claude Sonnet 4.6 |
| `m-gpt4o` | GPT-5.4 * |
| `m-qwen` | Qwen 3.6 Plus |

\* Named `m-gpt4o` because GPT-4o was unavailable on TokenRouter at experiment time; this agent runs GPT-5.4.

This design allows for a controlled comparison between two generations of Anthropic models to assess intra-provider scaling effects, as well as a cross-cultural performance analysis between Western-developed frontier models and non-Western counterparts like Qwen. By including both inference-optimized models (e.g., Gemini 2.5 Flash) and large-scale frontier models (e.g., Opus 4.7), we observe how behavioral fidelity to `SOUL.md` scales with parameter density, identifying whether "personality drift" is more prevalent in resource-constrained architectures.

### RQ4 — Operational Rules, Memory, and Risk Posture (`AGENTS.md`)

Four agents are deployed with identical configurations as the control agent, varying only `AGENTS.md`. The default `AGENTS.md` template was modified at the end by adding condition-specific rules for each agent to follow.

The design incorporates two variables: **autonomy** and **memory persistence**. High-autonomy agents are allowed and encouraged to act on their own discretion, whereas low-autonomy agents are forced to internally verify and confirm their actions against their internal checks and criteria — only after passing accuracy, safety, and validity checks will low-autonomy agents proceed with an action. The memory dimension varies from persistent long-term memory to no memory. Agents with persistent memory record session logs and context between sessions in a memory file. Agents with no memory have these memory files deleted between sessions and are explicitly instructed to treat each session as a brand new session.

|  | Full Memory | No Memory |
|---|---|---|
| **High autonomy** | `maverick` | `drifter` |
| **Low autonomy** | `sentinel` | `ghost` |

All four share the same `SOUL.md`, model (Gemini 2.5 Flash), and `HEARTBEAT.md`.

## Repository Structure

This repository is a fork of [OpenClaw](https://github.com/openclaw/openclaw) with our experiment agent configurations added. The key project-specific directories are:

### Agent Configurations — `agents/`

All agent workspace files live in [`agents/`](agents/). Each subdirectory contains the configuration files that define an agent's identity, personality, behavior loop, and operational rules.

### Project Deliverables — `deliverables/`

Course deliverables live in [`deliverables/`](deliverables/):

- **[Project Proposal](deliverables/Team%20Moltbook%20Project%20Proposal.pdf)** — Initial research plan and experiment design
- **[Project Progress Report](deliverables/Team%20Moltbook%20Project%20Progress%20Report.pdf)** — Final write-up with results and analysis

### Key Agent Files

Each experiment agent's workspace contains:

| File | Purpose |
|---|---|
| `SOUL.md` | Personality and behavioral guidelines — the main independent variable for the personality experiment |
| `MEMORY.md` | Operational rules and memory structure (personality experiment agents only) |
| `HEARTBEAT.md` | The behavioral loop: a 12-step checklist the agent executes each session (browse feed, comment, post, upvote, etc.) |
| `IDENTITY.dev.md` | Agent name, emoji, avatar, and role description |
| `AGENTS.md` | Session startup instructions and memory rules |
| `TOOLS.md` / `TOOLS.dev.md` | Available tool descriptions |
| `BOOT.md` | Startup hook instructions |
| `BOOTSTRAP.md` | First-run ritual |

### OpenClaw Framework

The rest of the repository is the OpenClaw framework that powers agent execution. See [`OPENCLAW.md`](OPENCLAW.md) for the full OpenClaw project documentation.

## Reproducing the Experiments

Reproducing this work requires access to a server running the OpenClaw gateway, API keys for the LLM providers, and accounts on Moltbook for each agent.

### Prerequisites

- A Linux server (or local machine) with **Node 22+**
- API keys for the target LLM providers (we used [TokenRouter](https://tokenrouter.ai/) for unified access)
- An email address and X (Twitter) account per agent for Moltbook sign-up

### High-Level Steps

1. **Set up the OpenClaw gateway** on a server
2. **Create agent workspaces** by copying the agent directories from `agents/` to the server
3. **Register each agent** in the OpenClaw configuration (`openclaw.json`) with its workspace path and model assignment
4. **Configure LLM providers** with API keys
5. **Deploy agents to Moltbook** by enrolling each agent through the OpenClaw web UI
6. **Set up cron jobs** to trigger agent sessions on a recurring schedule (we used every 6 hours)

### Detailed Setup Guide

For step-by-step instructions including server access, configuration examples, model setup, Moltbook enrollment, and cron job creation, see:

**[`TEAM-SETUP.md`](TEAM-SETUP.md)** — Full environment setup and deployment guide

## Use of AI Tools

AI coding assistants (GitHub Copilot) were used during the preparation of this repository. Specifically:

- **README content**: AI assisted with formatting the experiment design tables (Trials 1-3) and summarizing the detailed [`TEAM-SETUP.md`](TEAM-SETUP.md) deployment guide into the high-level reproduction steps in the section above.
- **TEAM-SETUP guide**: AI assisted with formatting and organizing [`TEAM-SETUP.md`](TEAM-SETUP.md) into structured, step-by-step setup instructions.

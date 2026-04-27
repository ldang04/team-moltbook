# Team Moltbook — Understanding AI Agent Behavior in Social Environments

**Columbia University — COMS 6156 Software Engineering, Spring 2026**

## Project Overview

As AI agents increasingly move toward multi-agent environments — places where they communicate, coordinate, and socialize with one another — it becomes important to understand what actually drives their behavior. This project investigates the factors that shape AI agent behavior when placed in social settings.

We deployed **13 agents** on [Moltbook](https://moltbook.com/), a social platform built entirely for AI agents (essentially Reddit for AI). Our agents run on the [OpenClaw](https://github.com/openclaw/openclaw) framework, which allows them to scroll the feed, comment, upvote, and create posts completely autonomously. Each agent ran for approximately **400 sessions over one week**, and we collected behavioral and social metrics to evaluate how different configurations influence autonomous social behavior.

## Research Questions

We designed three parallel experiments to study four research questions:

1. **Personality Specification** — How do variations in an agent's personality (defined in `SOUL.md`) affect its social behavior and engagement patterns?
2. **Operational Rules & Memory** — How do operational instructions and memory structures (defined in `MEMORY.md`) shape agent behavior?
3. **Underlying Model** — How does the choice of LLM backbone influence agent behavior given identical configurations?
4. **Cross-factor Interactions** — How do these factors interact to produce emergent social dynamics?

## Repository Structure

This repository is a fork of [OpenClaw](https://github.com/openclaw/openclaw) with our experiment agent configurations added. The key project-specific directories are:

### Agent Configurations — `agents/`

All agent workspace files live in [`agents/`](agents/). Each subdirectory contains the configuration files that define an agent's identity, personality, behavior loop, and operational rules.

| Experiment | Agents | Key Variable |
|---|---|---|
| **Personality** | `cartographer`, `connector`, `contrarian`, `explainer`, `lurker`, `mirror`, `oracle`, `specialist` | Custom `SOUL.md` with unique personality + `MEMORY.md` for operational rules |
| **Model** | `m-opus`, `m-sonnet`, `m-gpt5`, `m-qwen` | Same generic config, different LLM backbone (Claude Opus 4.7, Claude Sonnet 4.6, GPT-5.4, Qwen 3.6 Plus) |
| **Control** | `control` | Default OpenClaw template SOUL.md, Gemini 2.5 Flash, no `MEMORY.md` |

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

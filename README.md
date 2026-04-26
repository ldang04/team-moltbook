# Team Moltbook — Setup Guide

This guide covers the end-to-end process for connecting to the shared OpenClaw server, creating agents, configuring models, deploying agents to Moltbook, and setting up automated cron jobs.

## Prerequisites

- SSH access to the shared Hetzner server (ask the server owner to whitelist your SSH public key)
- A TokenRouter account with API keys for each model
- An email address and X (Twitter) account per agent for Moltbook sign-up

---

## 1. Connect to the Server

### Generate an SSH key (if you don't have one)

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

Send the contents of `~/.ssh/id_ed25519.pub` to the server owner to be added to the allowlist.

### SSH into the server

```bash
ssh openclaw@5.161.209.77
```

### Port-forward the OpenClaw UI to your local machine

In a **separate terminal** on your local machine, run:

```bash
ssh -N -L 18789:127.0.0.1:18789 openclaw@5.161.209.77
```

This forwards the OpenClaw web UI to `http://127.0.0.1:18789` on your local browser. Keep this terminal open while you need UI access.

---

## 2. Create an OpenClaw Agent

Each agent requires three things on the server:
1. A **workspace folder** — contains the agent's personality/identity files (SOUL.md, AGENTS.md, etc.)
2. An **agent directory** — stores runtime state (sessions, auth)
3. An **entry in `openclaw.json`** — registers the agent with the gateway

### 2.1 Create directories

SSH into the server and run (replacing `my-agent` with your agent's id):

```bash
mkdir -p /home/node/.openclaw/workspace-my-agent
mkdir -p /home/node/.openclaw/agents/my-agent/agent
```

### 2.2 Add workspace files

Option A — **Copy from the control agent** (recommended for experiment agents that should behave identically):

```bash
cp /home/node/.openclaw/workspace-control/*.md /home/node/.openclaw/workspace-my-agent/
```

Option B — **Upload from your local repo**:

```bash
# Run on your local machine:
scp agents/control/*.md openclaw@5.161.209.77:/home/node/.openclaw/workspace-my-agent/
```

The key workspace files are:

| File | Purpose |
|---|---|
| `SOUL.md` | Agent personality and behavioral guidelines |
| `AGENTS.md` | Session startup instructions and memory rules |
| `IDENTITY.dev.md` | Agent name, emoji, avatar, role description |
| `TOOLS.md` / `TOOLS.dev.md` | Notes about available tools |
| `USER.dev.md` | User profile information |
| `BOOTSTRAP.md` | First-run ritual (can be deleted after first session) |
| `HEARTBEAT.md` | Periodic heartbeat task checklist |
| `BOOT.md` | Startup hook instructions |

### 2.3 Register the agent in openclaw.json

Edit the config file on the server:

```bash
nano ~/.openclaw/openclaw.json
```

Add an entry to the `agents.list` array:

```json
{
  "id": "my-agent",
  "name": "My Agent",
  "workspace": "/home/node/.openclaw/workspace-my-agent",
  "agentDir": "/home/node/.openclaw/agents/my-agent/agent",
  "model": {
    "primary": "tokenrouter-mymodel/vendor/model-name"
  }
}
```

> **nano basics:** Arrow keys to navigate, type to edit, `Ctrl+O` then `Enter` to save, `Ctrl+X` to exit.

After editing, validate the JSON:

```bash
cat ~/.openclaw/openclaw.json | python3 -m json.tool > /dev/null
```

No output means the JSON is valid. If there's an error, it will print the line number.

> **Important:** JSON does not allow trailing commas. If you add an entry at the end of an array or object, make sure the *previous* entry has a comma but the *last* entry does not.

---

## 3. Set Up API Keys (TokenRouter)

### 3.1 Create a TokenRouter account

1. Sign up at [TokenRouter](https://form.typeform.com/to/hQsOgLEJ) to receive a $1000 credit voucher
2. Wait for the voucher email
3. Create an account with TokenRouter and add the voucher to your balance

### 3.2 Create API keys

In the TokenRouter dashboard, create one API key per model you want to use. Specify the target model for each key.

### 3.3 Configure providers in openclaw.json

Add a custom provider for each model under the top-level `models.providers` section:

```json
{
  "models": {
    "providers": {
      "tokenrouter-mymodel": {
        "baseUrl": "https://api.tokenrouter.com/v1",
        "apiKey": "your-tokenrouter-api-key",
        "api": "openai-completions",
        "models": [
          {
            "id": "vendor/model-name",
            "name": "Human-Readable Model Name",
            "reasoning": true,
            "input": ["text", "image"],
            "contextWindow": 200000,
            "maxTokens": 32000,
            "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
          }
        ]
      }
    }
  }
}
```

Also add the model to the `agents.defaults.models` catalog so OpenClaw recognizes it:

```json
{
  "agents": {
    "defaults": {
      "models": {
        "tokenrouter-mymodel/vendor/model-name": {}
      }
    }
  }
}
```

### 3.4 Current experiment models

| Provider ID | Model ID | Context Window | Max Tokens |
|---|---|---|---|
| `tokenrouter-opus` | `anthropic/claude-opus-4-7` | 200,000 | 32,000 |
| `tokenrouter-sonnet` | `anthropic/claude-sonnet-4-6` | 200,000 | 16,000 |
| `tokenrouter-gpt` | `openai/gpt-5.4` | 128,000 | 16,384 |
| `tokenrouter-qwen` | `qwen/qwen3.6-plus` | 131,072 | 8,192 |

The control agent uses `google/gemini-2.5-flash` via a native Google API key (already configured).

### 3.5 Verify

After saving the config, verify on the server:

```bash
openclaw models status
```

All providers should appear in the auth overview without errors.

### 3.6 Test agent responses

```bash
openclaw agent --agent my-agent --message "What model are you? Reply in one sentence."
```

---

## 4. Deploy Agent to Moltbook

### 4.1 Access the OpenClaw web UI

Make sure you have the SSH port-forward running (see Section 1), then open in your browser:

```
http://127.0.0.1:18789
```

### 4.2 Start a chat with your agent

In the OpenClaw web UI, select your agent from the chat dropdown menu.

### 4.3 Enroll on Moltbook

1. Go to [https://moltbook.com/](https://moltbook.com/)
2. Copy the onboarding prompt displayed on the website
3. Paste it into the chat with your agent in the OpenClaw UI
4. The agent will follow the instructions to sign up for Moltbook
5. Complete email verification and X (Twitter) verification as prompted

> Each agent needs its own unique email address and X account for Moltbook enrollment.

---

## 5. Create Cron Jobs

Cron jobs allow agents to post automatically on a schedule.

### 5.1 Via the OpenClaw web UI

1. Open `http://127.0.0.1:18789` in your browser
2. Navigate to the **Cron Jobs** tab
3. In the right-side panel, create a new cron job specifying:
   - **Prompt**: the message/instruction to send to the agent
   - **Agent**: select which agent should execute the job
   - **Schedule**: cron expression (e.g. `0 */6 * * *` for every 6 hours)

### 5.2 Via openclaw.json (alternative)

Add a `cron` section to the config:

```json
{
  "cron": {
    "jobs": [
      {
        "id": "my-agent-post",
        "agentId": "my-agent",
        "schedule": "0 */6 * * *",
        "prompt": "Write and post a new update on Moltbook."
      }
    ]
  }
}
```

---

## Quick Reference

| Task | Command / Location |
|---|---|
| SSH into server | `ssh openclaw@5.161.209.77` |
| Port-forward UI | `ssh -N -L 18789:127.0.0.1:18789 openclaw@5.161.209.77` |
| Edit config | `nano ~/.openclaw/openclaw.json` |
| Validate JSON | `cat ~/.openclaw/openclaw.json \| python3 -m json.tool > /dev/null` |
| Check models | `openclaw models status` |
| Test agent | `openclaw agent --agent <id> --message "Hello"` |
| OpenClaw UI | `http://127.0.0.1:18789` (with port-forward active) |
| Moltbook | `https://moltbook.com/` |
| Backup config | `cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak` |

---

## Troubleshooting

- **JSON parse error after editing config**: Run the validation command to find the line number. Common issues: trailing commas, mismatched braces, or missing quotes.
- **Agent not showing in UI**: Check that the agent entry in `agents.list` has valid `id`, `workspace`, and `agentDir` fields, and that those directories exist on the server.
- **Model auth errors**: Run `openclaw models status` to verify API keys are recognized. Check that the `apiKey` field in `models.providers` is correct and that the model `id` in the `models` array matches what TokenRouter expects.
- **Port-forward not working**: Ensure the SSH tunnel terminal is still running. If the connection dropped, re-run the `ssh -N -L ...` command.

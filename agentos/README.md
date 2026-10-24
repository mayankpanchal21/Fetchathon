# ⚡ AgentOS — AI Desktop Operator
> **Tagline:** You speak. Your computer acts.  
> **Fetch.ai Hackathon Deliverable:** Autonomous cross-platform desktop execution agent powered by Fetch.ai ASI:One, official uAgents Chat Protocol, and local permission-gated automation.

---

## 🏆 Judge-Facing Value Proposition: Why Fetch.ai Agent Interoperability?

Most AI desktop assistants are monolithic desktop chat applications that merely wrap an LLM prompt around local OS automation. This creates serious limitations:
1. **Isolated Silos:** Traditional desktop assistants cannot coordinate with remote autonomous agent economies or services.
2. **Security Vulnerability:** Exposing local desktop automation directly to webhooks or the open internet invites catastrophic remote code execution.
3. **Lack of Trust & Verification:** Standard bots report success when an action is dispatched, without observing or independently verifying the real OS state.

### How AgentOS Leverages the Fetch.ai Ecosystem
- **Decentralized ASI & Agentverse Discovery:** AgentOS registers an official **Fetch.ai uAgent** with the standardized `AgentChatProtocol` (`uagents_core.contrib.protocols.chat`). Any agent in the ASI Alliance ecosystem can discover AgentOS and request task delegations.
- **Air-Gapped Local Policy & Security Sandbox:** The cloud-facing uAgent **never** possesses direct OS access. Instead, tasks are dispatched through an authenticated local token relay (`X-Device-Token`) to a sandboxed loopback engine.
- **Observe-Plan-Act-Verify:** Every step planned by Fetch.ai's **ASI:One** model undergoes independent verification (e.g., verifying filesystem changes, DOM navigation status codes, image byte validations) rather than blindly trusting LLM output.
- **Human-in-the-Loop Permissions:** Destructive operations (writing files, executing shell commands, accessing sensitive apps) trigger human authorization before execution.

---

## 📐 Architecture Diagram

```
                                      ASI ALLIANCE & AGENTVERSE
                                                  │
                                                  ▼
                                      ┌───────────────────────┐
                                      │   Fetch.ai uAgent     │
                                      │ (ChatProtocol 0.3.0)  │
                                      │       Port 8001       │
                                      └───────────┬───────────┘
                                                  │
                              Authenticated Local Dispatcher (TLS / Token)
                                                  │
                                                  ▼
  USER VOICE / TEXT ──────────► ┌───────────────────────────────────┐
                                │       FastAPI Desktop Service     │ ◄─── REACT / TAURI
                                │     (Loopback 127.0.0.1:8000)     │      DASHBOARD
                                └─────────────────┬─────────────────┘      (Port 5173)
                                                  │
                                  ┌───────────────┴───────────────┐
                                  ▼                               ▼
                      ┌───────────────────────┐       ┌───────────────────────┐
                      │   Fetch.ai ASI:One    │       │     Local Policy &    │
                      │ Planner (api.asi1.ai) │       │   Approval Sandbox    │
                      │  asi1/mini/ultra      │       │ (Workspace isolation) │
                      └───────────────┬───────┘       └───────────────┬───────┘
                                      │                               │
                                      └───────────────┬───────────────┘
                                                      │
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │    Typed Desktop Executor    │
                                       │ ├─ Playwright Browser (DOM)  │
                                       │ ├─ PyAutoGUI (Mouse/Keys)    │
                                       │ ├─ Pillow (Screenshots)      │
                                       │ ├─ Sandboxed Filesystem      │
                                       │ └─ Approved Command Registry │
                                       └──────────────┬───────────────┘
                                                      │
                                                      ▼
                                      Independent State Verification
                                      & Persistent SQLite Audit Log
```

---

## ✨ Features

- **Cross-Platform OS Support:** Runtime OS detection for **macOS** (Apple Silicon arm64 & Intel x86) and **Windows 10/11**.
- **Fetch.ai ASI:One Primary Reasoning:** Exclusively powered by Fetch.ai ASI:One models (`asi1`, `asi1-mini`, `asi1-ultra`) via the official API endpoint `https://api.asi1.ai/v1`. Rejects third-party providers.
- **Official Fetch.ai uAgent Integration:** Compliant implementation of `uagents_core.contrib.protocols.chat` with `ChatMessage`, `TextContent`, `ChatAcknowledgement`, and `EndSessionContent`.
- **Observe-Plan-Act-Verify:** Real-time feedback loop with visual progress bars, step-by-step audit logs, and verified outcomes.
- **Safe Sandboxing & Permissions:** Strict filesystem sandboxing restricted to `./workspace`. Path traversal attempts are blocked. Raw shell command injection is forbidden; only allowlisted command templates run after human consent.
- **Emergency Stop:** Immediate cancellation mechanism that halts running tasks and cleans up processes.
- **Multimodal Voice Input:** Instant native browser speech-to-text with zero external dependencies, plus configurable offline `faster-whisper` support.
- **Developer-Grade Dark UI:** React + TypeScript + Vite + Tailwind CSS dashboard with live desktop status indicators, chat console, step timeline, and approval dialogs.

---

## 📋 Prerequisites

- **Python:** Python 3.11+ (tested on Python 3.11.9)
- **Node.js:** v18+ or v20+ (tested on Node v20.20.1 with npm 10.8.2)
- **Operating System:** macOS (Sonoma/Sequoia) or Windows 10/11

---

## 🚀 Quick Start (One Command)

### macOS / Linux
```bash
# 1. Clone or enter project
cd agentos

# 2. Run automated setup (creates virtualenv, installs Python & npm packages, downloads Playwright browser)
./scripts/setup.sh

# 3. Launch the full AgentOS development stack
./scripts/dev.sh
```

### Windows 10 / 11 (PowerShell)
```powershell
# 1. Enter project
cd agentos

# 2. Run PowerShell setup
.\scripts\setup.ps1

# 3. Launch AgentOS development stack
.\scripts\dev.ps1
```

Once launched:
- **Desktop UI Dashboard:** Open [http://127.0.0.1:5173](http://127.0.0.1:5173)
- **Desktop Backend API:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Fetch.ai uAgent Server:** [http://127.0.0.1:8001](http://127.0.0.1:8001)

---

## ⚙️ Environment Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

| Variable | Description | Default / Example |
|---|---|---|
| `ASI1_API_KEY` | Fetch.ai ASI:One API Key ([Get Key](https://asi1.ai/dashboard/api-keys)) | `asi1_live_...` (or empty for local demo mode) |
| `ASI1_MODEL` | Selected ASI:One model tier | `asi1` (default), `asi1-mini` (fast), `asi1-ultra` (deep) |
| `ASI1_BASE_URL` | Official Fetch.ai ASI:One endpoint | `https://api.asi1.ai/v1` |
| `AGENT_NAME` | Fetch.ai uAgent registered identifier | `AgentOS-Desktop-Worker` |
| `AGENT_PORT` | Local loopback port for uAgent | `8001` |
| `AGENT_SEED_PHRASE` | Seed phrase for persistent uAgent address | (leave empty for auto-generated seed) |
| `AGENT_MAILBOX_KEY` | Agentverse Mailbox API Token | (optional: enables public cloud mailbox) |
| `DEVICE_PAIRING_TOKEN`| Shared local authorization secret | `agentos-local-dev-token` |
| `ALLOWED_WORKSPACE` | Absolute or relative path to sandboxed directory | `./workspace` |
| `STT_ENGINE` | Speech-to-text provider | `browser` (native) or `faster-whisper` |

> **Note on Local Demo Mode:** If `ASI1_API_KEY` is not configured, AgentOS automatically runs in **Deterministic Local Demo Mode**. Common commands ("Open Chrome", "Create folder", "Take screenshot", "Run tests") plan and execute flawlessly without third-party LLMs.

---

## 🌐 Fetch.ai Agentverse Registration & ASI Discovery

### 1. Local Registration
When starting the agent (`services/fetch-agent/agent.py`), the uAgent automatically binds to port 8001, registers its address on the local network Almanac, and outputs an Agent Inspector link:
```
INFO: [AgentOS-Desktop-Worker]: Starting agent with address: agent1q06yqptvth3vc3wcfdrnl6p256ucrfsstx2arrq6gmrc2y7spdnw5twcjeg
INFO: [AgentOS-Desktop-Worker]: Agent inspector available at https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8001&address=agent1q06yqptvth3vc3wcfdrnl6p256ucrfsstx2arrq6gmrc2y7spdnw5twcjeg
INFO: [AgentOS-Desktop-Worker]: Manifest published successfully: AgentChatProtocol
```

### 2. Agentverse Cloud Mailbox (Public Discovery)
To allow remote agents or the ASI:One web chat ([https://asi1.ai/chat](https://asi1.ai/chat)) to communicate with your agent:
1. Log in to [Agentverse](https://agentverse.ai).
2. Go to **Mailroom** and generate an API key.
3. Add the key to `.env`:
   ```bash
   AGENT_MAILBOX_KEY=your-mailbox-key-here
   ```
4. Restart `./scripts/dev.sh`. The agent will establish a persistent outbound mailbox connection to Agentverse, enabling global messaging without port forwarding.

---

## 🔒 Security Model & Sandbox Policies

AgentOS adheres to the **Principle of Least Privilege**:

1. **Air-Gapped Public Agent:** The cloud-facing uAgent has **zero** OS system privileges. It can only forward validated messages to the local desktop service via authenticated HTTP.
2. **Device Pairing Authentication:** All desktop state-changing endpoints require the `X-Device-Token` header.
3. **Filesystem Sandboxing:** All file writes, reads, and directory creations are locked to `ALLOWED_WORKSPACE`. Path traversal (`../`) is blocked with a `PolicyViolation`.
4. **No Raw Shell Execution:** The LLM cannot execute arbitrary bash or PowerShell strings. Only pre-registered command templates (`pytest`, `npm_test`, `git_status`, `python_script`) can run.
5. **Human Approval Gating:** Risky actions (file writes, command execution, launching sensitive apps) pause the task and trigger the **Approval Dialog** on the desktop UI.
6. **Emergency Stop:** A dedicated button immediately cancels any active task and terminates running processes.

---

## 🧪 Testing & Validation

A comprehensive test suite of 29 automated tests validates all components:

```bash
# Run the full test suite
cd agentos
.venv/bin/pytest -v services/desktop-agent/tests
```

### Tested Capabilities:
- ✅ **ASI1 Model Client:** Validates `asi1`, `asi1-mini`, `asi1-ultra`, router logic, and strict rejection of unauthorized LLMs.
- ✅ **Policy Engine:** Unknown tool rejection, workspace path traversal prevention, coordinate bounds checking, approval detection.
- ✅ **Planner:** Pydantic schema validation, deterministic task plans, approval propagation.
- ✅ **Desktop Tools:** Display metrics, RGBA/RGB screenshot capture with base64 preview, filesystem sandboxing, approved terminal templates.
- ✅ **Browser Automation:** Headless Chromium page navigation and DOM content extraction via Playwright.
- ✅ **Fetch.ai Chat Protocol:** Extraction and formatting of `ChatMessage`, `TextContent`, `ChatAcknowledgement`, and `EndSessionContent`.
- ✅ **Emergency Stop:** Immediate task lifecycle cancellation.

---

## 🎬 Hackathon Demo Script

Follow this sequence for live judging presentations:

1. **Launch:** Run `./scripts/dev.sh` and open `http://127.0.0.1:5173`.
2. **Inspect Status Bar:** Point out real-time detected OS (`macOS arm64`), screen permission (`granted`), and the connected Fetch.ai uAgent on port 8001.
3. **Execute Harmless Automation:**
   - Speak or type: `"Create a folder called HackathonDemo in my Documents directory."`
   - Observe the 2-step plan, visual progress bar, and independent filesystem verification (`Directory verified on filesystem.`).
4. **Demonstrate Approval & Safety Engine:**
   - Speak or type: `"Open Terminal and run the tests in my selected project."`
   - Observe execution pause with the **Action Approval Dialog**.
   - Show the proposed command template and arguments. Click **Approve Once** to resume or **Reject** to abort.
5. **Demonstrate Emergency Stop:**
   - Start any task and click **Stop Task** to show instant cancellation.
6. **Demonstrate Fetch.ai Agent Dispatch:**
   - Run the dispatcher test script to demonstrate external uAgent task delegation:
     ```bash
     .venv/bin/python -c "import asyncio; from dispatcher import DesktopDispatcher; asyncio.run(DesktopDispatcher().dispatch_task('Create a folder called HackathonDemo2 in my Documents directory'))"
     ```
   - Show the verified execution report returned directly to the agent.

---

## ⚠️ Known Limitations & Troubleshooting

- **macOS Screen Recording Permission:** On macOS 14+, granting Screen Recording permission to your terminal or browser in *System Settings > Privacy & Security > Screen & System Audio Recording* is required for live screenshots.
- **Microphone in Headless Browsers:** Browser-native speech recognition requires user microphone permission in Chrome/Safari/Edge. If denied, the UI automatically provides a clear text-entry fallback.
- **Windows Differences:** Windows does not enforce TCC screen capture prompts, but PowerShell execution policy may need to be adjusted (`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`).

---

## 📄 License

MIT License. Built for the Fetch.ai Hackathon 2026.

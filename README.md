# 🤖 AgentOS — Autonomous Desktop Operator uAgent

> **Zero-Frontend, Standalone Fetch.ai uAgent** powered by **Fetch.ai's ASI:One LLM** (`asi1`).  
> Built for the Fetch.ai Hackathon to autonomously control macOS and Windows desktops (Applications, Web Forms/DOM, Keystrokes, Mouse, Files, Screen Capture) directly from **Agentverse** and Fetch.ai Chat Protocol.

---

## 🌟 Highlights

- **Pure Standalone Architecture:** Zero frontend boilerplate. Single-file self-contained uAgent (`run_agent.py`) with zero unnecessary microservices.
- **Direct Agentverse Integration:** Connects seamlessly with [Agentverse](https://agentverse.ai) and Almanac registration.
- **ASI:One LLM Planner:** Powered by Fetch.ai's cutting-edge `asi1` reasoning model at `https://api.asi1.ai/v1`.
- **Reliable Desktop Automation:**
  - **macOS & Windows Window Activation:** Brings target apps (e.g., Calculator, Chrome, Notes) to the foreground before dispatching keystrokes.
  - **Smart Web Automation:** Playwright-based browser engine with DOM selector auto-fill (`#email`, `#pass`, etc.) avoiding brittle pixel estimation.
  - **Human-like Typing & Controls:** Controlled keystrokes, shortcuts (`enter`, `tab`, `esc`), mouse clicks, scrolling, screen captures, file management.
- **Interactive Terminal CLI:** Includes `chat.py` for testing instructions from the command line in real time.

---

## 🚀 Quick Start

### 1. Requirements & Setup
Ensure dependencies are installed in your Python 3.10+ virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r agentos/requirements.txt
```

### 2. Configure Environment
Set your ASI:One API key in `agentos/.env`:
```env
ASI1_API_KEY=sk_a16bf299fdd8474ab776fcd044dcb3dfe68f3f89d37a447888d525c4562e9457
AGENT_PORT=8001
AGENT_ENDPOINT=http://127.0.0.1:8001/submit
AGENT_MAILBOX=true
```

### 3. Run the uAgent
```bash
python run_agent.py
```
Output:
```text
=================================================================
🤖 AgentOS — Pure Desktop Automation uAgent
=================================================================
• Agent Name:     agentos_desktop_agent
• Agent Address:  agent1qdd6eqp3dugy00kmx8hsy8dfsng8jzr7lc4ecl55nzu6xesc4h5gcpjkcxg
• Endpoint URL:   http://127.0.0.1:8001/submit
• Agentverse UI:  https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8001&address=agent1qdd6eqp3dugy00kmx8hsy8dfsng8jzr7lc4ecl55nzu6xesc4h5gcpjkcxg
• ASI:One Model:  asi1 (API Key: Active)
=================================================================
```

---

## 💬 Interacting with the Agent

### Option A: Using the CLI (`chat.py`)
In another terminal, send tasks directly:
```bash
# Single command
python chat.py "Open Calculator and Multiply 8 and 9"

# Open website
python chat.py "Open Chrome and visit fetch.ai"

# Interactive session
python chat.py
```

### Option B: Via Agentverse Inspector
Open the live inspector in your browser:
```
https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8001&address=agent1qdd6eqp3dugy00kmx8hsy8dfsng8jzr7lc4ecl55nzu6xesc4h5gcpjkcxg
```

### Option C: Agentverse Chat Protocol
Send a `ChatMessage` to agent address:
`agent1qdd6eqp3dugy00kmx8hsy8dfsng8jzr7lc4ecl55nzu6xesc4h5gcpjkcxg`

---

## 🛠️ Built-in Capabilities

| Tool | Description |
|---|---|
| `open_application` | Launches target application and activates window into foreground |
| `type_text` | Types text with controlled intervals |
| `press_key` | Sends specific keystrokes (`return`, `tab`, `space`, etc.) |
| `browser_open` | Opens Chrome / Playwright browser instance at URL |
| `browser_fill` | Fills form inputs reliably using DOM selectors |
| `browser_click` | Clicks elements or buttons using DOM selectors |
| `click` / `move_mouse` | Native operating system cursor actions |
| `take_screenshot` | Captures desktop screen snapshot to workspace |
| `write_text_file` / `read_text_file` | Local workspace file operations |

---

## 📄 License
MIT License

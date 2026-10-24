# AgentOS — Fetch.ai Agentverse Deployment & Chat Guide

Aapko **local React UI ki zaroorat nahi hai**. AgentOS ko poori tarah se **Agentverse ([https://agentverse.ai](https://agentverse.ai))** ke saath connect karke Agentverse ke hi Chat UI ya [https://asi1.ai/chat](https://asi1.ai/chat) se control kiya ja sakta hai.

---

## Architecture: Agentverse + Local Laptop Worker

```
┌──────────────────────────────────────────────┐
│       Agentverse Cloud / ASI:One Chat UI     │
│   (https://agentverse.ai | https://asi1.ai)  │
└──────────────────────┬───────────────────────┘
                       │ Fetch.ai Chat Protocol
                       ▼
┌──────────────────────────────────────────────┐
│      Fetch.ai uAgent (agent1q06yq...)        │
│    (Runs locally in headless mode on 8001)   │
└──────────────────────┬───────────────────────┘
                       │ Authenticated Device Relay
                       ▼
┌──────────────────────────────────────────────┐
│       AgentOS Desktop Automation Core        │
│   (Controls Mac & Windows Chrome, Files,     │
│    Mouse, Keyboard, Screen Capture)          │
└──────────────────────────────────────────────┘
```

---

## Method 1: Connect via Agentverse Mailbox (Recommended)

Is method me aapka agent Agentverse me list ho jayega aur aap direct **Agentverse UI** se chat kar payenge:

1. **Agentverse me Login karein:**
   - [https://agentverse.ai](https://agentverse.ai) par jayein.
2. **Local Agent Connect karein:**
   - Left sidebar me **"Local Agents"** par click karein.
   - **"Connect Local Agent"** par click karein.
   - Apne agent ka address enter karein:
     ```
     agent1q06yqptvth3vc3wcfdrnl6p256ucrfsstx2arrq6gmrc2y7spdnw5twcjeg
     ```
   - Agentverse aapko ek **Mailbox API Key** generate karke dega.
3. **Mailbox Key ko .env me dalein:**
   `agentos/.env` me add karein:
   ```bash
   AGENT_MAILBOX_KEY=your_mailbox_key_here
   ```
4. **AgentOS ko Headless Mode me Run karein (No UI):**
   * **macOS / Linux:**
     ```bash
     ./run_headless.sh
     ```
   * **Windows:**
     ```powershell
     .\run_headless.ps1
     ```
5. **Agentverse UI me Chat karein:**
   - Agentverse par apne agent ke samne **"Chat"** button click karein ya [https://asi1.ai/chat](https://asi1.ai/chat) open karein.
   - Command type karein:
     - `"Open Chrome and visit fetch.ai"`
     - `"Create a folder named DemoFolder in my Documents"`
     - `"Take a screenshot of my screen"`
   - Task aapke laptop par execute hoga aur report Agentverse chat me aayegi!

---

## Method 2: Deploy Cloud Agent directly on Agentverse Web IDE

Agar aap Agentverse ke cloud me Hosted Agent create karna chahte hain:

1. [https://agentverse.ai](https://agentverse.ai) open karein.
2. **"My Agents"** -> **"+ New Agent"** -> **"Blank Agent"** select karein.
3. Code editor me file `agentos/services/fetch-agent/agentverse_hosted_agent.py` ka poora code paste kar dein.
4. **"Run"** ya **"Deploy"** par click karein.
5. Cloud agent automatically deploy ho jayega aur uski screen par **"Chat"** button aa jayega.
6. Ab Agentverse ke andar hi chat karke apne laptop ko control karein!

---

## Headless Mode Commands (Local UI Stopped)

Local React UI (`desktop-ui`) ko band kar diya gaya hai. Ab aapke laptop par background me sirf:
- **FastAPI Core Worker:** Port 8000
- **Fetch.ai uAgent Worker:** Port 8001
- **Agent Address:** `agent1q06yqptvth3vc3wcfdrnl6p256ucrfsstx2arrq6gmrc2y7spdnw5twcjeg`
chalenge.

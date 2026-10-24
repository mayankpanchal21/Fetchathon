#!/usr/bin/env python3
"""
Quick Interactive CLI for AgentOS
=================================
Allows sending instant commands directly to the running agentos_desktop_agent without any browser/frontend.
"""

import sys
import requests

AGENT_API = "http://127.0.0.1:8001/api/task"

def main():
    print("=" * 65)
    print("🤖 AgentOS Interactive CLI (Talking to agentos_desktop_agent)")
    print("   Type your desktop command below or 'exit' to quit.")
    print("=" * 65)

    # If argument provided, run once
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        send_task(prompt)
        return

    # Interactive loop
    while True:
        try:
            prompt = input("\n👉 Enter Command: ").strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit", "q"):
                print("Exiting CLI.")
                break
            send_task(prompt)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting CLI.")
            break


def send_task(prompt: str):
    print(f"⏳ Sending to agent: '{prompt}'...")
    try:
        res = requests.post(
            AGENT_API,
            json={"prompt": prompt},
            timeout=120
        )
        if res.status_code == 200:
            data = res.json()
            status = data.get("status", "unknown")
            icon = "✅" if status == "success" else "⚠️"
            print(f"\n{icon} Result ({data.get('execution_time_sec')}s):")
            print(data.get("summary"))
        else:
            print(f"❌ Error {res.status_code}: {res.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to agent on http://127.0.0.1:8001. Is 'run_agent.py' running?")
    except Exception as e:
        print(f"❌ Failed: {e}")


if __name__ == "__main__":
    main()

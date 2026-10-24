"""
AgentOS — Hosted Cloud Agent for Fetch.ai Agentverse (https://agentverse.ai)
=============================================================================
Deploy this agent directly in Agentverse:
1. Log in to https://agentverse.ai
2. Click 'My Agents' -> '+ New Agent' -> 'Blank Agent'
3. Paste the contents of this file into the Agentverse editor.
4. Set your DESKTOP_AGENT_ADDRESS (default: agent1q06yqptvth3vc3wcfdrnl6p256ucrfsstx2arrq6gmrc2y7spdnw5twcjeg)
5. Click 'Run' or 'Deploy'.
6. Now click 'Chat' in Agentverse UI or visit https://asi1.ai/chat to talk directly to your Desktop Operator!
"""

import os
import json
import logging
from uuid import uuid4
from datetime import datetime

from uagents import Agent, Context, Model
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    EndSessionContent,
    chat_protocol_spec,
)
from uagents.protocol import Protocol

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentos.agentverse_hosted")

# =============================================================================
# Agent Configuration
# =============================================================================
# Replace with your local laptop desktop agent address if running with a custom seed
LOCAL_DESKTOP_AGENT_ADDRESS = os.getenv(
    "DESKTOP_AGENT_ADDRESS",
    "agent1qdd6eqp3dugy00kmx8hsy8dfsng8jzr7lc4ecl55nzu6xesc4h5gcpjkcxg"
)

# Fetch.ai ASI:One API Configuration
ASI1_API_KEY = os.getenv(
    "ASI1_API_KEY",
    "sk_a16bf299fdd8474ab776fcd044dcb3dfe68f3f89d37a447888d525c4562e9457"
)
ASI1_BASE_URL = "https://api.asi1.ai/v1"
ASI1_MODEL = "asi1"

# Initialize Cloud Agent on Agentverse
agent = Agent(
    name="AgentOS-Cloud-Coordinator",
    port=8000,
    mailbox=True
)

# Chat Protocol instance
chat_proto = Protocol(
    name=chat_protocol_spec.name,
    version=chat_protocol_spec.version,
)


def extract_prompt_text(msg: ChatMessage) -> str:
    """Extract string content from ChatMessage content blocks."""
    text_parts = []
    for item in msg.content:
        if isinstance(item, TextContent):
            text_parts.append(item.text)
        elif isinstance(item, dict) and item.get("type") == "text":
            text_parts.append(item.get("text", ""))
    return " ".join(text_parts).strip()


def build_response_msg(text: str, end_session: bool = False) -> ChatMessage:
    """Construct an official ChatMessage response."""
    content = [TextContent(text=text)]
    if end_session:
        content.append(EndSessionContent())
    return ChatMessage(
        msg_id=uuid4(),
        timestamp=datetime.utcnow(),
        content=content
    )


# =============================================================================
# Chat Protocol Message Handlers
# =============================================================================
@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    """
    Handles user commands sent via Agentverse Chat UI / DeltaV / ASI:One Chat.
    """
    ctx.logger.info(f"Received ChatMessage from {sender} (id: {msg.msg_id})")

    # 1. Immediate acknowledgement
    ack = ChatAcknowledgement(
        msg_id=uuid4(),
        acknowledged_msg_id=msg.msg_id,
        timestamp=datetime.utcnow()
    )
    await ctx.send(sender, ack)

    # 2. Extract user instruction
    user_prompt = extract_prompt_text(msg)
    if not user_prompt:
        await ctx.send(
            sender,
            build_response_msg("Received empty instruction. Please ask me to open an app, navigate, or operate your laptop.", end_session=True)
        )
        return

    ctx.logger.info(f"Processing command: '{user_prompt}'")

    # 3. Inform user that command is being dispatched to their laptop
    await ctx.send(
        sender,
        build_response_msg(f"🤖 AgentOS received: '{user_prompt}'\nRouting action to your connected laptop agent ({LOCAL_DESKTOP_AGENT_ADDRESS[:16]}...)...")
    )

    # 4. Delegate task to local desktop worker agent
    task_envelope = ChatMessage(
        msg_id=uuid4(),
        timestamp=datetime.utcnow(),
        content=[TextContent(text=user_prompt)]
    )

    try:
        await ctx.send(LOCAL_DESKTOP_AGENT_ADDRESS, task_envelope)
        ctx.logger.info(f"Dispatched task to desktop worker: {LOCAL_DESKTOP_AGENT_ADDRESS}")
        
        reply_text = (
            f"✅ **Task Sent to Laptop!**\n\n"
            f"• **Instruction:** {user_prompt}\n"
            f"• **Target Worker:** `{LOCAL_DESKTOP_AGENT_ADDRESS}`\n"
            f"• **Status:** Active on your Mac/Windows laptop.\n\n"
            f"_Your desktop agent will execute this action directly._"
        )
    except Exception as e:
        ctx.logger.error(f"Failed to forward message to laptop worker: {e}")
        reply_text = (
            f"⚠️ **Could not reach Desktop Worker** (`{LOCAL_DESKTOP_AGENT_ADDRESS}`).\n"
            f"Make sure AgentOS is running on your laptop with `./run_headless.sh`!"
        )

    await ctx.send(sender, build_response_msg(reply_text, end_session=True))


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"Received ChatAcknowledgement from {sender} for msg_id: {msg.acknowledged_msg_id}")


@agent.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info("=" * 60)
    ctx.logger.info(f"AgentOS Cloud Coordinator started on Agentverse!")
    ctx.logger.info(f"Cloud Agent Address: {agent.address}")
    ctx.logger.info(f"Connected Laptop Worker: {LOCAL_DESKTOP_AGENT_ADDRESS}")
    ctx.logger.info("=" * 60)


# Attach official Chat Protocol to the agent
agent.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    agent.run()

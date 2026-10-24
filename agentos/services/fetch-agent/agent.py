import os
import sys
import logging
from datetime import datetime
from uuid import uuid4
from pathlib import Path

# Add project root to sys.path so imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent))

from uagents import Agent, Context
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    EndSessionContent,
)

from chat_protocol import (
    chat_proto,
    extract_text_from_chat_message,
    build_chat_response,
    build_chat_acknowledgement
)
from dispatcher import DesktopDispatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [Fetch.ai uAgent]: %(message)s")
logger = logging.getLogger("agentos.fetch_agent")

# Configuration from environment
AGENT_NAME = os.getenv("AGENT_NAME", "AgentOS-Desktop-Worker")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8001"))
AGENT_SEED = os.getenv("AGENT_SEED_PHRASE", "agentos-fetchai-desktop-operator-seed-2026")
AGENT_MAILBOX_KEY = os.getenv("AGENT_MAILBOX_KEY", "").strip() or None

dispatcher = DesktopDispatcher()

# Initialize the Fetch.ai Agent
# Note: mailbox is enabled when AGENT_MAILBOX_KEY is provided
agent_kwargs = {
    "name": AGENT_NAME,
    "seed": AGENT_SEED,
    "port": AGENT_PORT,
}
if AGENT_MAILBOX_KEY:
    agent_kwargs["mailbox"] = f"{AGENT_MAILBOX_KEY}@https://agentverse.ai"
    agent_kwargs["publish_agent_details"] = True

agent = Agent(**agent_kwargs)


@chat_proto.on_message(ChatMessage)
async def handle_incoming_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    """
    Handles incoming ChatMessage according to the official Fetch.ai Chat Protocol.
    1. Sends immediate receipt acknowledgement.
    2. Validates user request.
    3. Dispatches task to authenticated local desktop agent.
    4. Returns verified outcome to sender.
    """
    logger.info(f"Received ChatMessage from {sender} (msg_id: {msg.msg_id})")

    # Step 1: Send acknowledgement
    await ctx.send(sender, build_chat_acknowledgement(msg.msg_id))

    # Step 2: Extract text from message
    user_prompt = extract_text_from_chat_message(msg)
    if not user_prompt:
        await ctx.send(
            sender,
            build_chat_response("Received empty command. Please provide a desktop instruction.", end_session=True)
        )
        return

    logger.info(f"Processing command via local desktop dispatcher: '{user_prompt}'")

    # Step 3: Dispatch to paired local desktop agent
    dispatch_result = await dispatcher.dispatch_task(user_prompt)

    # Step 4: Construct truthful, safe final report
    summary_text = dispatch_result.get("summary", "Task executed.")
    if dispatch_result.get("success"):
        response_text = f"✅ AgentOS Desktop Report:\n{summary_text}"
    else:
        response_text = f"⚠️ AgentOS Status:\n{summary_text}"

    # Step 5: Send response back to sender
    await ctx.send(sender, build_chat_response(response_text, end_session=True))
    logger.info(f"Dispatched completion response to {sender}")


@chat_proto.on_message(ChatAcknowledgement)
async def handle_acknowledgement(ctx: Context, sender: str, msg: ChatAcknowledgement):
    logger.info(f"Received acknowledgement for msg_id: {msg.acknowledged_msg_id} from {sender}")


@agent.on_event("startup")
async def startup_handler(ctx: Context):
    ctx.logger.info("=" * 60)
    ctx.logger.info(f"Fetch.ai uAgent '{agent.name}' started successfully.")
    ctx.logger.info(f"Agent Address: {agent.address}")
    ctx.logger.info(f"Listening on port: {agent_kwargs['port']}")
    if AGENT_MAILBOX_KEY:
        ctx.logger.info("Agentverse Mailbox: CONNECTED")
    else:
        ctx.logger.info("Agentverse Mailbox: Standby (Set AGENT_MAILBOX_KEY to connect to Agentverse)")
    ctx.logger.info("=" * 60)


# Attach official Chat Protocol to the agent
agent.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    agent.run()

import logging
from datetime import datetime
from uuid import uuid4
from typing import List, Optional
from uagents import Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

logger = logging.getLogger("agentos.fetch_agent.chat_protocol")

# Initialize official Fetch.ai chat protocol instance
chat_proto = Protocol(name="AgentOSChatProtocol", version="1.0.0", spec=chat_protocol_spec)


def extract_text_from_chat_message(msg: ChatMessage) -> str:
    """Extract plain text string from official ChatMessage content items."""
    chunks: List[str] = []
    for item in msg.content:
        if isinstance(item, TextContent):
            chunks.append(item.text)
        elif hasattr(item, "text"):
            chunks.append(str(item.text))
    return " ".join(chunks).strip()


def build_chat_response(text: str, end_session: bool = True) -> ChatMessage:
    """Build a compliant official ChatMessage response."""
    contents = [TextContent(type="text", text=text)]
    if end_session:
        contents.append(EndSessionContent(type="end-session"))

    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=contents
    )


def build_chat_acknowledgement(msg_id) -> ChatAcknowledgement:
    """Send immediate receipt acknowledgement for incoming ChatMessage."""
    return ChatAcknowledgement(
        timestamp=datetime.utcnow(),
        acknowledged_msg_id=msg_id
    )

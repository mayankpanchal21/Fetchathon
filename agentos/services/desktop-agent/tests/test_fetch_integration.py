import pytest
from uuid import uuid4
from datetime import datetime
import sys
from pathlib import Path

FETCH_AGENT_DIR = Path(__file__).resolve().parent.parent.parent / "fetch-agent"
sys.path.insert(0, str(FETCH_AGENT_DIR))

from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    EndSessionContent,
)
from chat_protocol import (
    extract_text_from_chat_message,
    build_chat_response,
    build_chat_acknowledgement
)
from dispatcher import DesktopDispatcher


def test_fetch_chat_message_extraction():
    msg = ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[TextContent(type="text", text="Take a screenshot and explain what is on my screen")]
    )
    extracted = extract_text_from_chat_message(msg)
    assert extracted == "Take a screenshot and explain what is on my screen"


def test_fetch_chat_response_construction():
    response_msg = build_chat_response("Execution completed successfully", end_session=True)
    assert isinstance(response_msg, ChatMessage)
    assert len(response_msg.content) == 2
    assert isinstance(response_msg.content[0], TextContent)
    assert response_msg.content[0].text == "Execution completed successfully"
    assert isinstance(response_msg.content[1], EndSessionContent)


def test_fetch_chat_acknowledgement():
    msg_id = uuid4()
    ack = build_chat_acknowledgement(msg_id)
    assert isinstance(ack, ChatAcknowledgement)
    assert ack.acknowledged_msg_id == msg_id


@pytest.mark.asyncio
async def test_fetch_dispatcher_offline_fallback():
    # When pointed to invalid port, uses clear mock transport
    disp = DesktopDispatcher(desktop_base_url="http://127.0.0.1:59999")
    health = await disp.check_desktop_health()
    assert health["connected"] is False

    res = await disp.dispatch_task("Open Chrome")
    assert res["status"] == "mock_transport_standby"
    assert "Mock Transport" in res["summary"]

import pytest
from app.llm.asi1_client import ASI1Client, ModelTier, ModelConfigError, OFFICIAL_ASI1_BASE_URL


def test_asi1_valid_models():
    """Verify that only Fetch.ai ASI1 models can be initialized."""
    c_default = ASI1Client(model="asi1", api_key="dummy-key")
    assert c_default.default_model == "asi1"
    assert c_default.base_url == OFFICIAL_ASI1_BASE_URL

    c_fast = ASI1Client(model="asi1-mini", api_key="dummy-key")
    assert c_fast.default_model == "asi1-mini"

    c_ultra = ASI1Client(model="asi1-ultra", api_key="dummy-key")
    assert c_ultra.default_model == "asi1-ultra"


def test_reject_unconfigured_third_party_llm():
    """Verify that third-party LLMs (OpenAI GPT, Claude, Gemini) are strictly rejected."""
    for forbidden in ["gpt-4", "gpt-3.5-turbo", "claude-3-5-sonnet", "gemini-pro"]:
        with pytest.raises(ModelConfigError) as exc_info:
            ASI1Client(model=forbidden, api_key="test")
        assert "Unsupported model" in str(exc_info.value)
        assert "Fetch.ai ASI:One" in str(exc_info.value)


def test_asi1_model_router():
    """Verify router correctly routes fast tasks to asi1-mini and complex tasks to asi1-ultra."""
    client = ASI1Client(model="asi1", api_key="dummy-key")
    assert client.route_model("fast") == ModelTier.FAST.value
    assert client.route_model("intent") == ModelTier.FAST.value
    assert client.route_model("complex") == ModelTier.ULTRA.value
    assert client.route_model("general") == ModelTier.DEFAULT.value


def test_missing_api_key_error_handling():
    """Verify that calling complete without API key raises clear ModelConfigError with link."""
    client = ASI1Client(api_key="")
    with pytest.raises(ModelConfigError) as exc_info:
        client.complete([{"role": "user", "content": "hi"}])
    assert "ASI1_API_KEY is not configured" in str(exc_info.value)
    assert "https://asi1.ai/dashboard/api-keys" in str(exc_info.value)

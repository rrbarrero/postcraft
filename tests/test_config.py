from src.shared.config import Config


def test_config_defaults():
    config = Config()
    assert config.llm_base_url == "http://192.168.1.164:8009/v1"
    assert config.llm_api_key.get_secret_value() == "dummy"
    assert config.llm_model == "Qwen/Qwen3-8B-AWQ"
    assert config.llm_temperature == 0
    assert config.llm_max_tokens == 900


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "test-model")
    config = Config()
    assert config.llm_model == "test-model"

from src.shared.llm import LLM


def test_llm_get_instance():
    llm = LLM()
    instance = llm.get_instance()
    assert instance is not None
    assert instance.openai_api_base == "http://192.168.1.164:8009/v1"
    assert instance.model_name == "Qwen/Qwen3-8B-AWQ"
    assert instance.temperature == 0
    assert instance.max_tokens == 900

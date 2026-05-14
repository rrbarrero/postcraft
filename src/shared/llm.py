from langchain_openai import ChatOpenAI

from .config import config


class LLM:
    def get_instance(self) -> ChatOpenAI:
        return ChatOpenAI(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            model=config.llm_model,
            temperature=config.llm_temperature,
            max_completion_tokens=config.llm_max_tokens,
        )

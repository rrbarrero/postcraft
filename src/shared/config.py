from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    llm_base_url: str = "http://192.168.1.164:8009/v1"
    llm_api_key: SecretStr = SecretStr("dummy")
    llm_model: str = "Qwen/Qwen3-8B-AWQ"
    llm_temperature: float = 0
    llm_max_tokens: int = 900


config = Config()

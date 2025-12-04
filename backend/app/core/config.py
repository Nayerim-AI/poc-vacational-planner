from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    app_name: str = "Vacation Planner LLM PoC"
    environment: str = Field("local", env="ENVIRONMENT")
    default_user_id: str = Field("demo-user", env="DEFAULT_USER_ID")
    llm_provider: str = Field("mock", env="LLM_PROVIDER")
    budget_default: float = Field(1500.0, env="DEFAULT_BUDGET")
    ollama_host: str = Field("http://localhost:11434", env="OLLAMA_HOST")
    ollama_model: str = Field("llama3", env="OLLAMA_MODEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

from functools import lru_cache

try:  # optional dependency
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback when dotenv missing
    load_dotenv = None

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
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    if load_dotenv:
        load_dotenv(".env")
    return Settings()


settings = get_settings()

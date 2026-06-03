from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    environment: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"  # AI provider keys live in .env too; backend doesn't need them


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ADMIN_KEY: str
    RATE_LIMIT_DEFAULT: int = 10
    CACHE_TTL_SECONDS: int = 300

    class Config:
        env_file = ".env"


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    flight_service_url: str = "localhost:50051"
    flight_service_api_key: str
    port: int = 8000

    model_config = {"env_file": ".env"}


settings = Settings()

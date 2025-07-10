# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()


class Settings(BaseSettings):
    """
    Configuración centralizada del BFF.
    
    Esta clase utiliza Pydantic para validar automáticamente
    las variables de entorno y proporcionar valores por defecto.
    Es similar a como configuraste appsettings.json en .NET.
    """

    # Información del BFF
    app_name: str = os.getenv("APP_NAME", "Sports Betting BFF")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Configuración del backend .NET
    backend_api_url: str = os.getenv(
        "BACKEND_API_URL", "https://api-kurax-demo-jos.uk")
    backend_timeout: int = int(os.getenv("BACKEND_TIMEOUT", "30"))

    # Configuración de autenticación
    # Debe coincidir con la configuración de tu API .NET
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET", "SportsBettingSecretKey123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")

    # Configuración CORS para desarrollo
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
    ]

    # Configuración de cache
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    enable_cache: bool = os.getenv("ENABLE_CACHE", "true").lower() == "true"

    # Configuración de logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    enable_request_logging: bool = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"

    # Configuración de rate limiting
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


# Instancia global de configuración
settings = Settings()

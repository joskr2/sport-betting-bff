# app/core/config.py
from typing import List
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()


class Settings:
    """
    Configuración centralizada del BFF.
    
    Configuración simplificada sin dependencias de Pydantic.
    """

    def __init__(self):
        # Información del BFF
        self.app_name = os.getenv("APP_NAME", "Sports Betting BFF")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.debug = os.getenv("DEBUG", "true").lower() == "true"

        # Configuración del backend .NET
        self.backend_api_url = os.getenv("BACKEND_API_URL", "https://api-kurax-demo-jos.uk")
        self.backend_timeout = int(os.getenv("BACKEND_TIMEOUT", "30"))

        # Configuración de autenticación
        self.jwt_secret_key = os.getenv("JWT_SECRET", "SportsBettingSecretKey123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

        # Configuración CORS
        origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,https://betting-app-frontend-six.vercel.app,https://betting-app-frontend-ff29xnj8l-josues-projects-546cbe2a.vercel.app")
        if origins_str == "*":
            self.allowed_origins = ["*"]
        else:
            self.allowed_origins = [origin.strip() for origin in origins_str.split(",")]

        # Configuración de cache
        self.cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "300"))
        self.enable_cache = os.getenv("ENABLE_CACHE", "true").lower() == "true"

        # Configuración de logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.enable_request_logging = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"

        # Configuración de rate limiting
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))


# Instancia global de configuración
settings = Settings()

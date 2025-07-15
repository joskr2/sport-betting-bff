# app/core/config.py
from typing import List
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

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

        # Configuración CORS - Seguridad Mejorada
        origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,https://betting-app-frontend-six.vercel.app,https://betting-app-frontend-ff29xnj8l-josues-projects-546cbe2a.vercel.app")
        
        # Configurar origins basado en entorno
        self.allowed_origins = self._configure_cors_origins(origins_str)
        
        # Configuración de hosts confiables
        self.allowed_hosts = self._configure_trusted_hosts()
        
        # Headers permitidos específicos (no wildcard)
        self.allowed_headers = [
            "Authorization",
            "Content-Type", 
            "X-Requested-With",
            "Accept",
            "Origin",
            "User-Agent",
            "Cache-Control"
        ]

        # Configuración de cache
        self.cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "300"))
        self.enable_cache = os.getenv("ENABLE_CACHE", "true").lower() == "true"

        # Configuración de logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.enable_request_logging = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"

        # Configuración de rate limiting
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    def _configure_cors_origins(self, origins_str: str) -> List[str]:
        """Configurar CORS origins basado en entorno."""
        # Nunca permitir wildcard
        if origins_str == "*":
            if self.debug:
                print("⚠️ WARNING: CORS wildcard enabled - DEVELOPMENT ONLY")
                return ["*"]
            else:
                print("🚨 ERROR: CORS wildcard not allowed in production!")
                raise ValueError("CORS wildcard (*) is not allowed in production. Set specific ALLOWED_ORIGINS.")
        
        # Parsear origins
        origins_list = [origin.strip() for origin in origins_str.split(",") if origin.strip()]
        
        if self.debug:
            # Desarrollo: permitir todos los origins configurados
            return origins_list
        else:
            # Producción: filtrar solo HTTPS (excepto localhost)
            production_origins = []
            for origin in origins_list:
                if origin.startswith('https://') or origin.startswith(('http://localhost', 'http://127.0.0.1')):
                    production_origins.append(origin)
                else:
                    print(f"⚠️ WARNING: Skipping non-HTTPS origin in production: {origin}")
            
            if not production_origins:
                raise ValueError("No valid HTTPS origins found for production")
            
            return production_origins
    
    def _configure_trusted_hosts(self) -> List[str]:
        """Configurar hosts confiables basado en entorno."""
        hosts_str = os.getenv("ALLOWED_HOSTS", "")
        
        if self.debug:
            # Desarrollo: hosts locales + testserver
            return ["localhost", "127.0.0.1", "testserver", "*.ngrok.io"]
        else:
            # Producción: extraer hosts de origins + backend
            if hosts_str:
                return [host.strip() for host in hosts_str.split(",") if host.strip()]
            
            # Auto-configurar desde CORS origins
            hosts = set()
            for origin in self.allowed_origins:
                if origin.startswith(('http://', 'https://')):
                    from urllib.parse import urlparse
                    parsed = urlparse(origin)
                    if parsed.hostname:
                        hosts.add(parsed.hostname)
            
            # Agregar dominios del backend
            hosts.add("api-kurax-demo-jos.uk")
            hosts.add("*.amazonaws.com")  # Para Lambda
            hosts.add("*.execute-api.us-east-1.amazonaws.com")  # API Gateway específico
            
            return list(hosts)


# Instancia global de configuración
settings = Settings()

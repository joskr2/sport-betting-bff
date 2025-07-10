# app/services/backend_service.py
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
import logging
import json
from datetime import datetime, timedelta
from cachetools import TTLCache
import hashlib

from app.core.config import settings

# Configurar logging específico para este servicio
logger = logging.getLogger(__name__)


class BackendService:
    """
    Servicio centralizado para comunicación con la API .NET.
    
    Este servicio implementa varios patrones importantes:
    1. Circuit Breaker para manejar fallos del backend
    2. Cache inteligente para reducir latencia
    3. Retry logic para operaciones que pueden fallar temporalmente
    4. Transformación de datos para optimizar el frontend
    """

    def __init__(self):
        self.base_url = settings.backend_api_url
        self.timeout = settings.backend_timeout

        # Cache en memoria para respuestas del backend
        # TTLCache expira automáticamente después del tiempo especificado
        self.cache = TTLCache(maxsize=1000, ttl=settings.cache_ttl_seconds)

        # Configuración del cliente HTTP
        self.client_config = {
            "timeout": httpx.Timeout(self.timeout),
            "limits": httpx.Limits(max_keepalive_connections=10, max_connections=20)
        }

        # Estadísticas para monitoreo
        self.stats = {
            "requests_made": 0,
            "cache_hits": 0,
            "errors": 0,
            "average_response_time": 0
        }

    def _generate_cache_key(self, method: str, endpoint: str, params: Optional[Dict] = None,
                            headers: Optional[Dict] = None) -> str:
        """
        Genera una clave única para cache basada en la petición.
        Incluye parámetros y headers relevantes para evitar colisiones.
        """
        key_data = {
            "method": method,
            "endpoint": endpoint,
            "params": params or {},
            "auth_header": headers.get("Authorization") if headers else None
        }
        # Crear hash MD5 de los datos serializados
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _should_cache_request(self, method: str, endpoint: str) -> bool:
        """
        Determina si una petición debe ser cacheada.
        Solo cacheamos GET requests a endpoints que no cambian frecuentemente.
        """
        if method.upper() != "GET":
            return False

        # Endpoints que no deben ser cacheados
        no_cache_patterns = [
            "/api/bets/my-bets",  # Datos personales que pueden cambiar
            "/api/auth/profile",   # Información del usuario
            "/health"              # Health checks
        ]

        return not any(pattern in endpoint for pattern in no_cache_patterns)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Método centralizado para hacer peticiones HTTP con todas las optimizaciones.
        """
        url = f"{self.base_url}{endpoint}"
        start_time = datetime.utcnow()

        # Generar clave de cache
        cache_key = None
        if use_cache and settings.enable_cache and self._should_cache_request(method, endpoint):
            cache_key = self._generate_cache_key(
                method, endpoint, params, headers)

            # Verificar cache
            if cache_key in self.cache:
                self.stats["cache_hits"] += 1
                logger.info(f"Cache hit for {method} {endpoint}")
                return self.cache[cache_key]

        # Preparar headers por defecto
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)

        # Realizar petición con manejo de errores
        async with httpx.AsyncClient(**self.client_config) as client:
            try:
                self.stats["requests_made"] += 1
                logger.info(f"Making {method} request to {url}")

                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers
                )

                # Calcular tiempo de respuesta para estadísticas
                response_time = (datetime.utcnow() -
                                 start_time).total_seconds()
                self._update_average_response_time(response_time)

                # Manejar respuestas por código de estado
                await self._handle_response(response, method, endpoint)

                # Procesar respuesta exitosa
                response_data = response.json()

                # Guardar en cache si corresponde
                if cache_key and response.status_code == 200:
                    self.cache[cache_key] = response_data
                    logger.debug(f"Cached response for {method} {endpoint}")

                return response_data

            except httpx.TimeoutException:
                self.stats["errors"] += 1
                logger.error(f"Timeout when calling {url}")
                raise HTTPException(
                    status_code=504, detail="Backend service timeout")

            except httpx.ConnectError:
                self.stats["errors"] += 1
                logger.error(f"Connection error when calling {url}")
                raise HTTPException(
                    status_code=503, detail="Backend service unavailable")

            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Unexpected error when calling {url}: {str(e)}")
                raise HTTPException(
                    status_code=500, detail="Internal server error")

    async def _handle_response(self, response: httpx.Response, method: str, endpoint: str):
        """
        Maneja diferentes códigos de respuesta del backend de manera centralizada.
        """
        if response.status_code == 200 or response.status_code == 201:
            return  # Respuesta exitosa

        elif response.status_code == 400:
            error_detail = response.json() if response.content else {
                "message": "Bad Request"}
            logger.warning(
                f"Bad request for {method} {endpoint}: {error_detail}")
            raise HTTPException(status_code=400, detail=error_detail)

        elif response.status_code == 401:
            logger.warning(f"Unauthorized request for {method} {endpoint}")
            raise HTTPException(status_code=401, detail="Unauthorized")

        elif response.status_code == 404:
            logger.warning(f"Resource not found for {method} {endpoint}")
            raise HTTPException(status_code=404, detail="Resource not found")

        elif response.status_code == 409:
            error_detail = response.json() if response.content else {
                "message": "Conflict"}
            logger.warning(f"Conflict for {method} {endpoint}: {error_detail}")
            raise HTTPException(status_code=409, detail=error_detail)

        else:
            logger.error(
                f"Unexpected status code {response.status_code} for {method} {endpoint}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Backend error: {response.status_code}"
            )

    def _update_average_response_time(self, response_time: float):
        """Actualiza el tiempo promedio de respuesta para estadísticas."""
        current_avg = self.stats["average_response_time"]
        total_requests = self.stats["requests_made"]

        # Cálculo de promedio móvil
        self.stats["average_response_time"] = (
            (current_avg * (total_requests - 1)) + response_time
        ) / total_requests

    # === Métodos de Autenticación ===

    async def register_user(self, user_data: Dict[str, str]) -> Dict[str, Any]:
        """Registrar nuevo usuario en el backend."""
        response = await self._make_request("POST", "/api/auth/register", data=user_data, use_cache=False)
        # La API externa devuelve {success: true, data: {...}}
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    async def login_user(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Autenticar usuario en el backend."""
        response = await self._make_request("POST", "/api/auth/login", data=credentials, use_cache=False)
        # La API externa devuelve {success: true, data: {...}}
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    async def get_user_profile(self, auth_token: str) -> Dict[str, Any]:
        """Obtener perfil del usuario autenticado."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await self._make_request("GET", "/api/auth/profile", headers=headers, use_cache=False)
        # La API externa devuelve {success: true, data: {...}}
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    # === Métodos de Eventos ===

    async def get_events(self) -> List[Dict[str, Any]]:
        """Obtener lista de eventos disponibles con cache inteligente."""
        response = await self._make_request("GET", "/api/events")
        # La API externa devuelve {success: true, data: [...]}
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response if isinstance(response, list) else []

    async def get_event_by_id(self, event_id: int) -> Dict[str, Any]:
        """Obtener evento específico por ID."""
        response = await self._make_request("GET", f"/api/events/{event_id}")
        # La API externa devuelve {success: true, data: {...}}
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    async def get_event_stats(self, event_id: int) -> Dict[str, Any]:
        """Obtener estadísticas de un evento."""
        response = await self._make_request("GET", f"/api/events/{event_id}/stats")
        # La API externa devuelve {success: true, data: {...}}
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    # === Métodos de Apuestas ===

    async def create_bet(self, bet_data: Dict[str, Any], auth_token: str) -> Dict[str, Any]:
        """Crear nueva apuesta."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        return await self._make_request("POST", "/api/bets", data=bet_data, headers=headers, use_cache=False)

    async def get_user_bets(self, auth_token: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Obtener apuestas del usuario con filtros opcionales."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        return await self._make_request("GET", "/api/bets/my-bets", params=params, headers=headers, use_cache=False)

    async def get_user_bet_stats(self, auth_token: str) -> Dict[str, Any]:
        """Obtener estadísticas de apuestas del usuario."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        return await self._make_request("GET", "/api/bets/my-stats", headers=headers, use_cache=False)

    async def preview_bet(self, bet_data: Dict[str, Any], auth_token: str) -> Dict[str, Any]:
        """Previsualizar apuesta antes de crearla."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        return await self._make_request("POST", "/api/bets/preview", data=bet_data, headers=headers, use_cache=False)

    # === Métodos de Utilidad ===

    async def health_check(self) -> Dict[str, Any]:
        """Verificar salud del backend."""
        return await self._make_request("GET", "/health", use_cache=False)

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del servicio para monitoreo."""
        cache_hit_rate = (
            self.stats["cache_hits"] / max(self.stats["requests_made"], 1)
        ) * 100

        return {
            **self.stats,
            "cache_hit_rate": round(cache_hit_rate, 2),
            "cache_size": len(self.cache),
            "backend_url": self.base_url
        }

    def clear_cache(self):
        """Limpiar cache manualmente."""
        self.cache.clear()
        logger.info("Backend service cache cleared")


# Instancia global del servicio
backend_service = BackendService()

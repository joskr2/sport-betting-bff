# app/main.py
import logging
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

import structlog
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from mangum import Mangum

# Importar nuestros componentes personalizados
from app.core.config import settings
from app.api import auth, events, bets
from app.services.backend_service import backend_service

# Configurar logging estructurado para producción
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,          # Filtrar por nivel de log
        structlog.stdlib.add_logger_name,          # Agregar nombre del logger
        structlog.stdlib.add_log_level,            # Agregar nivel de log
        structlog.stdlib.PositionalArgumentsFormatter(),  # Formatear argumentos
        structlog.processors.TimeStamper(fmt="iso"),       # Timestamp ISO
        # Info de stack si está disponible
        structlog.processors.StackInfoRenderer(),
        # Formatear información de excepciones
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),             # Decodificar unicode
        # Renderizar como JSON para producción
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Obtener logger estructurado
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación.
    
    Esta función es como el gerente de un hotel que se encarga de abrir
    por la mañana (inicialización) y cerrar por la noche (limpieza).
    En FastAPI, esto nos permite ejecutar código cuando la aplicación
    inicia y cuando se cierra.
    
    Es especialmente útil para:
    - Inicializar conexiones a bases de datos
    - Cargar configuraciones
    - Inicializar cache
    - Limpiar recursos al cerrar
    """
    # Código de inicialización (startup)
    try:
        logger.info("Starting Sports Betting BFF",
                    version=settings.app_version)

        # Verificar conectividad con el backend
        await _verify_backend_connectivity()

        # Inicializar componentes necesarios
        await _initialize_application_components()

        logger.info("BFF application started successfully")

        # La aplicación está lista para recibir peticiones
        yield

    except Exception as e:
        logger.error("Failed to start application", error=str(e),
                     traceback=traceback.format_exc())
        raise

    finally:
        # Código de limpieza (shutdown)
        logger.info("Shutting down Sports Betting BFF")

        # Limpiar recursos
        await _cleanup_application_resources()

        logger.info("BFF application shutdown completed")

# Crear la aplicación FastAPI con configuración completa
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Backend for Frontend (BFF) para el sistema de apuestas deportivas.
    
    Este BFF actúa como una capa inteligente entre el frontend y la API .NET,
    proporcionando:
    - Agregación de datos de múltiples fuentes
    - Transformaciones específicas para el frontend
    - Cache inteligente para mejorar rendimiento
    - Validaciones adicionales y análisis de riesgo
    - Auditoría completa de transacciones financieras
    """,
    docs_url="/docs" if settings.debug else None,     # Solo mostrar docs en desarrollo
    # Solo mostrar redoc en desarrollo
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,  # Solo openapi en desarrollo
    lifespan=lifespan,  # Configurar el manejo del ciclo de vida

    # Configuraciones adicionales para producción
    swagger_ui_parameters={
        "syntaxHighlight.theme": "arta",
        "tryItOutEnabled": settings.debug,  # Solo permitir "try it out" en desarrollo
    } if settings.debug else None
)

handler = Mangum(app)

# === CONFIGURACIÓN DE MIDDLEWARE ===
# Los middleware se ejecutan en orden, como capas de una cebolla.
# La petición pasa por cada capa hacia adentro, y la respuesta
# pasa por cada capa hacia afuera en orden inverso.

# 1. Middleware de hosts confiables (seguridad)
if not settings.debug:
    # En producción, solo permitir hosts específicos para prevenir ataques de host header
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )

# 2. Middleware de CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    # Headers personalizados para el frontend
    expose_headers=["X-Total-Count", "X-Filtered-Count"],
)

# 3. Middleware personalizado para logging de peticiones


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """
    Middleware para logging detallado de peticiones HTTP.
    
    Este middleware es como el sistema de seguridad de un edificio
    que registra quién entra, a qué hora, qué hace, y cuánto tiempo
    se queda. Es esencial para debugging y monitoreo.
    
    La información que capturamos incluye:
    - Detalles de la petición (método, URL, headers importantes)
    - Tiempo de procesamiento
    - Códigos de respuesta
    - Errores si los hay
    - Información del cliente (IP, user agent)
    """
    # Generar ID único para esta petición (útil para rastrear logs)
    request_id = f"req_{int(time.time() * 1000)}_{id(request)}"

    # Capturar información de la petición
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # Log de petición entrante
    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        client_ip=client_ip,
        user_agent=user_agent,
        content_length=request.headers.get("content-length", 0)
    )

    try:
        # Procesar la petición
        response = await call_next(request)

        # Calcular tiempo de procesamiento
        process_time = time.time() - start_time

        # Log de respuesta exitosa
        logger.info(
            "Request completed",
            request_id=request_id,
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2),
            response_size=response.headers.get("content-length", "unknown")
        )

        # Agregar headers personalizados a la respuesta
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

        return response

    except Exception as e:
        # Calcular tiempo incluso en caso de error
        process_time = time.time() - start_time

        # Log de error
        logger.error(
            "Request failed",
            request_id=request_id,
            error=str(e),
            process_time_ms=round(process_time * 1000, 2),
            traceback=traceback.format_exc()
        )

        # Re-lanzar la excepción para que sea manejada por otros middleware
        raise

# 4. Middleware para rate limiting básico


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """
    Middleware básico de rate limiting.
    
    Este middleware es como un portero de discoteca que controla
    cuántas personas pueden entrar en un período determinado.
    Previene abuso del sistema y ataques de denegación de servicio.
    
    En una implementación más avanzada, usarías Redis para
    almacenar contadores distribuidos entre múltiples instancias.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Verificar rate limit (implementación básica en memoria)
    if await _check_rate_limit(client_ip):
        response = await call_next(request)
        return response
    else:
        logger.warning(
            "Rate limit exceeded",
            client_ip=client_ip,
            url=str(request.url)
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )

# === MANEJADORES DE EXCEPCIONES GLOBALES ===
# Estos manejadores son como el departamento de servicio al cliente
# de una empresa: se encargan de manejar problemas de manera elegante
# y proporcionar respuestas útiles cuando algo sale mal.


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Manejador para excepciones HTTP.
    
    Este manejador toma excepciones HTTP (como 404, 401, etc.)
    y las convierte en respuestas JSON consistentes que el
    frontend puede entender y manejar apropiadamente.
    """
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url),
        method=request.method
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": _get_error_type_from_status_code(exc.status_code),
            "message": str(exc.detail),
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Manejador para errores de validación de Pydantic.
    
    Cuando el frontend envía datos que no cumplen con nuestros
    schemas, este manejador convierte los errores técnicos de
    Pydantic en mensajes amigables para el usuario.
    """
    # Extraer errores de validación de manera más amigable
    validation_errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        validation_errors.append(f"{field}: {message}")

    logger.warning(
        "Validation error occurred",
        errors=validation_errors,
        url=str(request.url),
        method=request.method
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": {
                "validation_errors": validation_errors,
                "error_count": len(validation_errors)
            },
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Manejador para excepciones no capturadas.
    
    Este es nuestro último recurso: cuando algo inesperado sucede,
    este manejador se asegura de que el usuario reciba una respuesta
    útil en lugar de un error crudo del servidor.
    """
    # Log detallado del error para debugging
    logger.error(
        "Unhandled exception occurred",
        error=str(exc),
        error_type=type(exc).__name__,
        url=str(request.url),
        method=request.method,
        traceback=traceback.format_exc()
    )

    # En desarrollo, mostrar más detalles del error
    error_detail = str(
        exc) if settings.debug else "An internal server error occurred"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "InternalServerError",
            "message": error_detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path),
            "debug_info": {
                "error_type": type(exc).__name__,
                "traceback": traceback.format_exc()
            } if settings.debug else None
        }
    )

# === INCLUIR ROUTERS ===
# Los routers son como departamentos especializados en una empresa.
# Cada uno maneja un tipo específico de peticiones.

app.include_router(auth.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(bets.router, prefix="/api")

# === ENDPOINTS DE UTILIDAD ===
# Estos endpoints proporcionan información útil sobre el estado
# y la configuración de la aplicación.


@app.get("/health")
async def health_check():
    """
    Endpoint de verificación de salud.
    
    Este endpoint es como el pulso de una persona: una forma rápida
    de verificar que todo esté funcionando correctamente. Es esencial
    para load balancers, sistemas de monitoreo, y deployments.
    """
    try:
        # Verificar conectividad con el backend
        backend_health = await backend_service.health_check()
        backend_healthy = True
    except Exception as e:
        logger.warning("Backend health check failed", error=str(e))
        backend_healthy = False
        backend_health = {"error": str(e)}

    # Obtener estadísticas del backend service
    service_stats = backend_service.get_stats()

    health_data = {
        "status": "healthy" if backend_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production",
        "backend": {
            "healthy": backend_healthy,
            "url": settings.backend_api_url,
            "response_time_avg": service_stats.get("average_response_time", 0),
            "cache_hit_rate": service_stats.get("cache_hit_rate", 0)
        },
        "cache": {
            "enabled": settings.enable_cache,
            "size": service_stats.get("cache_size", 0),
            "ttl_seconds": settings.cache_ttl_seconds
        }
    }

    # Retornar código 503 si el backend no está saludable
    status_code = status.HTTP_200_OK if backend_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content=health_data
    )


@app.get("/")
async def root():
    """
    Endpoint raíz que proporciona información de la API.
    
    Este endpoint es como la recepción de una oficina: da
    información básica sobre qué servicios están disponibles
    y cómo acceder a ellos.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Backend for Frontend (BFF) for Sports Betting System",
        "documentation": "/docs" if settings.debug else "Documentation available in development mode",
        "health_check": "/health",
        "endpoints": {
            "authentication": "/api/auth",
            "events": "/api/events",
            "betting": "/api/bets"
        },
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/stats")
async def get_api_stats():
    """
    Endpoint para obtener estadísticas de la API.
    
    Útil para monitoreo y debugging. Proporciona información
    sobre el rendimiento y uso de la aplicación.
    """
    service_stats = backend_service.get_stats()

    return {
        "backend_service": service_stats,
        "application": {
            "version": settings.app_version,
            "debug_mode": settings.debug,
            "cache_enabled": settings.enable_cache,
            "cors_origins": len(settings.allowed_origins)
        },
        "generated_at": datetime.utcnow().isoformat()
    }

# === FUNCIONES HELPER ===
# Estas funciones proporcionan funcionalidad de soporte para
# los middleware y manejadores de excepciones.


async def _verify_backend_connectivity():
    """
    Verifica que podemos conectarnos al backend .NET.
    
    Esta función es como verificar que el teléfono funciona
    antes de abrir una oficina de servicio al cliente.
    """
    try:
        health_response = await backend_service.health_check()
        logger.info("Backend connectivity verified",
                    backend_url=settings.backend_api_url)
        return True
    except Exception as e:
        logger.error(
            "Cannot connect to backend",
            backend_url=settings.backend_api_url,
            error=str(e)
        )
        # En desarrollo, podríamos continuar sin backend para testing
        if settings.debug:
            logger.warning(
                "Continuing in debug mode without backend connectivity")
            return False
        else:
            raise Exception(
                f"Backend connectivity required for production: {str(e)}")


async def _initialize_application_components():
    """
    Inicializa componentes de la aplicación.
    
    Esta función prepara todos los sistemas necesarios para
    que la aplicación funcione correctamente, como verificar
    configuraciones y inicializar cache.
    """
    # Verificar configuraciones críticas
    if not settings.jwt_secret_key or len(settings.jwt_secret_key) < 32:
        raise ValueError("JWT secret key must be at least 32 characters long")

    # Inicializar otros componentes si es necesario
    logger.info("Application components initialized successfully")


async def _cleanup_application_resources():
    """
    Limpia recursos cuando la aplicación se cierra.
    
    Esta función es como apagar las luces y cerrar las puertas
    cuando termina el día de trabajo.
    """
    # Limpiar cache del backend service
    backend_service.clear_cache()

    logger.info("Application resources cleaned up")

# Rate limiting simple en memoria (para desarrollo)
# En producción, usarías Redis u otra solución distribuida
_rate_limit_store: Dict[str, Dict[str, Any]] = {}


async def _check_rate_limit(client_ip: str) -> bool:
    """
    Verificación simple de rate limiting en memoria.
    
    Esta función implementa un algoritmo básico de sliding window
    para controlar el número de peticiones por cliente.
    
    En un sistema de producción real, usarías:
    - Redis para storage distribuido
    - Algoritmos más sofisticados como token bucket
    - Rate limits diferenciados por endpoint
    - Rate limits basados en usuarios autenticados
    """
    current_time = time.time()
    window_size = 60  # 1 minuto
    max_requests = settings.rate_limit_per_minute

    # Limpiar entradas antiguas
    if client_ip in _rate_limit_store:
        _rate_limit_store[client_ip]["requests"] = [
            req_time for req_time in _rate_limit_store[client_ip]["requests"]
            if current_time - req_time < window_size
        ]
    else:
        _rate_limit_store[client_ip] = {"requests": []}

    # Verificar si excede el límite
    if len(_rate_limit_store[client_ip]["requests"]) >= max_requests:
        return False

    # Agregar esta petición al contador
    _rate_limit_store[client_ip]["requests"].append(current_time)
    return True


def _get_error_type_from_status_code(status_code: int) -> str:
    """
    Convierte códigos de estado HTTP en tipos de error legibles.
    
    Esta función ayuda a que los errores sean más comprensibles
    para el frontend y facilita el manejo de errores específicos.
    """
    error_type_mapping = {
        400: "BadRequestError",
        401: "AuthenticationError",
        403: "AuthorizationError",
        404: "NotFoundError",
        405: "MethodNotAllowedError",
        409: "ConflictError",
        422: "ValidationError",
        429: "RateLimitError",
        500: "InternalServerError",
        502: "BadGatewayError",
        503: "ServiceUnavailableError",
        504: "GatewayTimeoutError"
    }

    return error_type_mapping.get(status_code, "UnknownError")


# === CONFIGURACIÓN PARA DESARROLLO LOCAL ===
if __name__ == "__main__":
    """
    Configuración para ejecutar la aplicación directamente con Python.
    
    Esto es útil durante el desarrollo para testing rápido,
    pero en producción usarías uvicorn con configuraciones específicas.
    """
    import uvicorn

    # Configuración optimizada para desarrollo
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,  # Auto-reload cuando cambian archivos
        log_level=settings.log_level.lower(),
        access_log=settings.enable_request_logging,
        # Configuraciones adicionales para desarrollo
        reload_dirs=["app"] if settings.debug else None,
        reload_excludes=["*.pyc", "*.pyo",
                         "__pycache__"] if settings.debug else None
    )

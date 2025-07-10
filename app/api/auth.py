# app/api/auth.py
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from typing import Optional

from app.models.schemas import (
    UserRegistrationRequest, UserLoginRequest, AuthResponse,
    DataResponse, ErrorResponse
)
from app.services.backend_service import backend_service
from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Crear router específico para autenticación
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegistrationRequest):
    """
    Registrar nuevo usuario con validaciones mejoradas.
    
    Este endpoint demuestra cómo el BFF puede agregar valor:
    1. Validaciones más estrictas que el backend
    2. Transformación de datos para el frontend
    3. Logging detallado para auditoría
    4. Respuestas consistentes
    """
    logger.info(f"Registration attempt for email: {user_data.email}")

    try:
        # Convertir modelo Pydantic a diccionario para el backend
        # Aquí podríamos agregar transformaciones adicionales
        backend_data = {
            "email": user_data.email.lower(),  # Normalizar email
            "password": user_data.password,
            "fullName": user_data.full_name.strip()
        }

        # Llamar al backend .NET
        backend_response = await backend_service.register_user(backend_data)

        # Transformar respuesta del backend al formato del BFF
        # Aquí es donde el BFF agrega valor al normalizar respuestas
        auth_data = AuthResponse(
            token=backend_response["token"],
            email=backend_response["email"],
            full_name=backend_response["fullName"],
            balance=backend_response["balance"],
            expires_at=backend_response["expiresAt"],
            # Información adicional que el BFF puede agregar
            permissions=["user"],  # Podríamos obtener esto de otro servicio
        )

        logger.info(f"User registered successfully: {user_data.email}")

        return DataResponse(
            message="User registered successfully",
            data=auth_data.dict()
        )

    except HTTPException as e:
        # Re-lanzar excepciones HTTP del backend
        logger.warning(
            f"Registration failed for {user_data.email}: {e.detail}")
        raise e

    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to internal error"
        )


@router.post("/login", response_model=DataResponse)
async def login_user(credentials: UserLoginRequest):
    """
    Autenticar usuario con enriquecimiento de respuesta.
    
    El BFF puede agregar información adicional como:
    - Configuraciones específicas del usuario
    - Preferencias guardadas
    - Información de sesiones previas
    """
    logger.info(f"Login attempt for email: {credentials.email}")

    try:
        # Preparar datos para el backend
        login_data = {
            "email": credentials.email.lower(),
            "password": credentials.password
        }

        # Autenticar en el backend
        backend_response = await backend_service.login_user(login_data)

        # Enriquecer respuesta con información adicional
        # Aquí el BFF puede agregar datos de múltiples fuentes
        auth_data = AuthResponse(
            token=backend_response["token"],
            email=backend_response["email"],
            full_name=backend_response["fullName"],
            balance=backend_response["balance"],
            expires_at=backend_response["expiresAt"],
            permissions=["user"],
            # Podríamos agregar información de preferencias del usuario
        )

        logger.info(f"User logged in successfully: {credentials.email}")

        return DataResponse(
            message="Login successful",
            data=auth_data.model_dump()
        )

    except HTTPException as e:
        logger.warning(f"Login failed for {credentials.email}: {e.detail}")
        raise e

    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to internal error"
        )


@router.get("/profile", response_model=DataResponse)
async def get_user_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Obtener perfil de usuario enriquecido.
    
    Este endpoint demuestra cómo el BFF puede:
    1. Agregar información de múltiples fuentes
    2. Cachear datos frecuentemente accedidos
    3. Transformar datos para optimizar el frontend
    """
    token = credentials.credentials

    try:
        logger.info("Fetching user profile")

        # Obtener perfil básico del backend
        profile_data = await backend_service.get_user_profile(token)

        # Aquí el BFF puede enriquecer el perfil con información adicional
        # Por ejemplo, estadísticas calculadas, preferencias, etc.
        enriched_profile = {
            **profile_data,
            # Información adicional que el BFF puede calcular o agregar
            "profile_completion": _calculate_profile_completion(profile_data),
            # Esto vendría de un servicio de actividad
            "last_activity": "2024-01-01T12:00:00Z",
            "notification_count": 0,  # Podría venir de un servicio de notificaciones
        }

        return DataResponse(
            message="Profile retrieved successfully",
            data=enriched_profile
        )

    except HTTPException as e:
        logger.warning(f"Failed to fetch profile: {e.detail}")
        raise e

    except Exception as e:
        logger.error(f"Unexpected error fetching profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        )


@router.post("/logout", response_model=DataResponse)
async def logout_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout de usuario con limpieza de sesión.
    
    El BFF puede manejar tareas adicionales de logout como:
    - Invalidar cache específico del usuario
    - Registrar actividad de logout
    - Limpiar datos temporales
    """
    try:
        # En JWT no hay logout real en el backend, pero el BFF puede hacer limpieza
        # Por ejemplo, invalidar cache específico del usuario
        logger.info("User logged out")

        # Aquí podríamos invalidar cache, registrar actividad, etc.

        return DataResponse(
            message="Logout successful",
            data={"logged_out_at": "2024-01-01T12:00:00Z"}
        )

    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


def _calculate_profile_completion(profile_data: dict) -> float:
    """
    Calcula el porcentaje de completitud del perfil.
    Ejemplo de lógica que el BFF puede agregar.
    """
    required_fields = ["email", "fullName", "balance"]
    optional_fields = ["phone", "address", "dateOfBirth"]

    completed_required = sum(
        1 for field in required_fields if profile_data.get(field))
    completed_optional = sum(
        1 for field in optional_fields if profile_data.get(field))

    # Campos requeridos valen 70%, opcionales 30%
    score = (completed_required / len(required_fields)) * 0.7
    score += (completed_optional / len(optional_fields)) * 0.3

    return round(score * 100, 1)

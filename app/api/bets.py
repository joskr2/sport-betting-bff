# app/api/bets.py
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta, timezone
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.models.schemas import (
    BetCreationRequest, BetResponse, BetStatistics, 
    DataResponse, DashboardData
)
from app.services.backend_service import backend_service
from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/bets", tags=["Betting"])

@router.post("/preview", response_model=DataResponse)
async def preview_bet(
    bet_request: BetCreationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Previsualizar una apuesta antes de crearla.
    
    Este endpoint demuestra cómo el BFF puede agregar una capa de seguridad
    adicional permitiendo a los usuarios ver exactamente qué va a pasar
    antes de comprometer su dinero. Es como mostrar el recibo antes de
    procesar el pago en una tienda.
    
    El BFF puede agregar validaciones específicas del frontend que
    complementen las validaciones del backend.
    """
    token = credentials.credentials
    
    try:
        logger.info(f"Previewing bet for event {bet_request.event_id}, amount: {bet_request.amount}")
        
        # Agregar validaciones específicas del BFF
        validation_errors = await _validate_bet_request(bet_request, token)
        if validation_errors:
            return DataResponse(
                success=False,
                message="Bet validation failed",
                data={
                    "errors": validation_errors,
                    "can_proceed": False
                }
            )
        
        # Obtener preview del backend
        backend_data = {
            "eventId": bet_request.event_id,
            "selectedTeam": bet_request.selected_team,
            "amount": bet_request.amount
        }
        
        preview_data = await backend_service.preview_bet(backend_data, token)
        
        # Enriquecer preview con información adicional del BFF
        enriched_preview = await _enrich_bet_preview(preview_data, bet_request)
        
        logger.info(f"Bet preview generated successfully")
        
        return DataResponse(
            message="Bet preview generated successfully",
            data=enriched_preview
        )
        
    except HTTPException as e:
        logger.warning(f"Bet preview failed: {e.detail}")
        raise e
    
    except Exception as e:
        logger.error(f"Unexpected error in bet preview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate bet preview"
        )

@router.post("", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
async def create_bet(
    bet_request: BetCreationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Crear una nueva apuesta con validaciones y auditoría completas.
    
    Este endpoint es el más crítico del sistema porque maneja dinero real.
    El BFF agrega múltiples capas de protección:
    1. Validaciones previas más estrictas
    2. Auditoría detallada de cada transacción
    3. Verificaciones de seguridad adicionales
    4. Respuestas optimizadas para el frontend
    """
    token = credentials.credentials
    
    # Generar ID único para auditoría
    transaction_id = f"bet_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
    
    try:
        logger.info(f"Creating bet [Transaction: {transaction_id}] - Event: {bet_request.event_id}, Amount: {bet_request.amount}")
        
        # Paso 1: Validaciones exhaustivas del BFF
        validation_start = datetime.now(timezone.utc)
        validation_errors = await _validate_bet_request(bet_request, token)
        validation_time = (datetime.now(timezone.utc) - validation_start).total_seconds()
        
        if validation_errors:
            logger.warning(f"Bet validation failed [Transaction: {transaction_id}]: {validation_errors}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Bet validation failed",
                    "errors": validation_errors,
                    "transaction_id": transaction_id
                }
            )
        
        # Paso 2: Verificaciones de seguridad adicionales
        security_checks = await _perform_security_checks(bet_request, token)
        if not security_checks["passed"]:
            logger.warning(f"Security check failed [Transaction: {transaction_id}]: {security_checks['reason']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Security verification failed",
                    "reason": security_checks["reason"],
                    "transaction_id": transaction_id
                }
            )
        
        # Paso 3: Crear apuesta en el backend
        backend_start = datetime.now(timezone.utc)
        backend_data = {
            "eventId": bet_request.event_id,
            "selectedTeam": bet_request.selected_team,
            "amount": bet_request.amount
        }
        
        backend_response = await backend_service.create_bet(backend_data, token)
        backend_time = (datetime.now(timezone.utc) - backend_start).total_seconds()
        
        # Paso 4: Transformar respuesta del backend al formato del BFF
        bet_response = BetResponse(
            id=backend_response["id"],
            event_id=backend_response["eventId"],
            event_name=backend_response["eventName"],
            selected_team=backend_response["selectedTeam"],
            amount=backend_response["amount"],
            odds=backend_response["odds"],
            potential_win=backend_response["potentialWin"],
            status=backend_response["status"],
            created_at=backend_response["createdAt"],
            # Información adicional que el BFF puede calcular
            can_be_cancelled=backend_response.get("canBeCancelled", False),
            time_remaining=_calculate_time_remaining(backend_response.get("eventDate"))
        )
        
        # Paso 5: Auditoría completa de la transacción
        await _audit_bet_transaction(
            transaction_id=transaction_id,
            bet_data=bet_request,
            backend_response=backend_response,
            validation_time=validation_time,
            backend_time=backend_time,
            token=token
        )
        
        logger.info(f"Bet created successfully [Transaction: {transaction_id}] - Bet ID: {bet_response.id}")
        
        # Paso 6: Preparar respuesta enriquecida
        response_data = {
            **bet_response.dict(),
            "transaction_id": transaction_id,
            "confirmation_code": f"BET{bet_response.id:06d}",
            "processing_time": {
                "validation_ms": round(validation_time * 1000, 2),
                "backend_ms": round(backend_time * 1000, 2),
                "total_ms": round((validation_time + backend_time) * 1000, 2)
            }
        }
        
        return DataResponse(
            message="Bet created successfully",
            data=response_data
        )
        
    except HTTPException as e:
        # Auditar intentos fallidos también
        await _audit_failed_bet_attempt(transaction_id, bet_request, str(e.detail), token)
        raise e
    
    except Exception as e:
        logger.error(f"Unexpected error creating bet [Transaction: {transaction_id}]: {str(e)}")
        await _audit_failed_bet_attempt(transaction_id, bet_request, str(e), token)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bet due to internal error"
        )

@router.get("/my-bets", response_model=DataResponse)
async def get_user_bets(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    status_filter: Optional[str] = Query(None, description="Filtrar por estado"),
    date_from: Optional[datetime] = Query(None, description="Fecha desde"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta"),
    page: int = Query(1, ge=1, description="Página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    include_statistics: bool = Query(True, description="Incluir estadísticas")
):
    """
    Obtener apuestas del usuario con filtros y paginación inteligente.
    
    Este endpoint demuestra cómo el BFF puede optimizar la experiencia
    del usuario agregando funcionalidades como paginación eficiente,
    filtros adicionales, y estadísticas calculadas en tiempo real.
    """
    token = credentials.credentials
    
    try:
        logger.info(f"Fetching user bets - Page: {page}, Size: {page_size}, Status: {status_filter}")
        
        # Preparar parámetros para el backend
        backend_params = {}
        if status_filter:
            backend_params["status"] = status_filter
        if date_from:
            backend_params["fromDate"] = date_from.isoformat()
        if date_to:
            backend_params["toDate"] = date_to.isoformat()
        
        # Obtener datos del backend de forma paralela si se necesitan estadísticas
        if include_statistics:
            bets_task = backend_service.get_user_bets(token, backend_params)
            stats_task = backend_service.get_user_bet_stats(token)
            
            # Ejecutar ambas peticiones en paralelo con manejo de errores
            try:
                bets_data, stats_data = await asyncio.gather(bets_task, stats_task)
            except HTTPException as e:
                # Si falla alguna llamada, manejar el error apropiadamente
                if e.status_code == 401:
                    logger.warning("Authentication failed in parallel calls")
                    raise HTTPException(status_code=401, detail="Invalid or expired authentication token")
                else:
                    logger.warning(f"Error in parallel calls: {e.detail}")
                    raise e
        else:
            bets_data = await backend_service.get_user_bets(token, backend_params)
            stats_data = None
        
        # Transformar datos del backend al formato del BFF
        transformed_bets = []
        for bet_data in bets_data:
            bet_response = BetResponse(
                id=bet_data["id"],
                event_id=bet_data["eventId"],
                event_name=bet_data["eventName"],
                selected_team=bet_data["selectedTeam"],
                amount=bet_data["amount"],
                odds=bet_data["odds"],
                potential_win=bet_data["potentialWin"],
                status=bet_data["status"],
                created_at=bet_data["createdAt"],
                can_be_cancelled=bet_data.get("canBeCancelled", False),
                time_remaining=_calculate_time_remaining(bet_data.get("eventDate")),
                # Información adicional que el BFF puede calcular
                profit_loss=_calculate_profit_loss(bet_data),
                is_winning=_is_bet_winning(bet_data)
            )
            transformed_bets.append(bet_response)
        
        # Aplicar paginación (el backend podría no tener paginación)
        total_bets = len(transformed_bets)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_bets = transformed_bets[start_index:end_index]
        
        # Preparar respuesta
        response_data = {
            "bets": [bet.dict() for bet in paginated_bets],
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_items": total_bets,
                "total_pages": (total_bets + page_size - 1) // page_size,
                "has_next": end_index < total_bets,
                "has_previous": page > 1
            }
        }
        
        # Agregar estadísticas si se solicitaron
        if include_statistics and stats_data:
            response_data["statistics"] = _transform_bet_statistics(stats_data)
        
        logger.info(f"Retrieved {len(paginated_bets)} bets for user")
        
        return DataResponse(
            message=f"Retrieved {len(paginated_bets)} bets",
            data=response_data
        )
        
    except HTTPException as e:
        logger.warning(f"Failed to fetch user bets: {e.detail}")
        raise e
    
    except Exception as e:
        logger.error(f"Unexpected error fetching user bets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user bets"
        )

@router.get("/dashboard", response_model=DataResponse)
async def get_betting_dashboard(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Obtener dashboard completo de apuestas del usuario.
    
    Este endpoint demuestra el verdadero valor del BFF: la capacidad
    de agregar datos de múltiples fuentes en una sola respuesta
    optimizada para el frontend. Es como tener un asistente personal
    que te prepara un resumen completo de toda tu actividad.
    """
    token = credentials.credentials
    
    try:
        logger.info("Generating betting dashboard")
        
        # Definir todas las peticiones que necesitamos hacer al backend
        # Las ejecutaremos en paralelo para optimizar el tiempo de respuesta
        dashboard_tasks = {
            "profile": backend_service.get_user_profile(token),
            "recent_bets": backend_service.get_user_bets(token, {"limit": 5}),
            "bet_statistics": backend_service.get_user_bet_stats(token),
            "available_events": backend_service.get_events(),
        }
        
        # Ejecutar todas las peticiones en paralelo
        dashboard_start = datetime.now(timezone.utc)
        dashboard_results = await asyncio.gather(
            *dashboard_tasks.values(),
            return_exceptions=True
        )
        dashboard_time = (datetime.now(timezone.utc) - dashboard_start).total_seconds()
        
        # Procesar resultados y manejar errores parciales
        # Verificar si hay errores críticos de autenticación
        for i, result in enumerate(dashboard_results):
            if isinstance(result, HTTPException) and result.status_code == 401:
                logger.warning("Authentication failed in dashboard request")
                raise HTTPException(status_code=401, detail="Invalid or expired authentication token")
        
        profile_data = dashboard_results[0] if not isinstance(dashboard_results[0], Exception) else None
        recent_bets_data = dashboard_results[1] if not isinstance(dashboard_results[1], Exception) else []
        stats_data = dashboard_results[2] if not isinstance(dashboard_results[2], Exception) else None
        events_data = dashboard_results[3] if not isinstance(dashboard_results[3], Exception) else []
        
        # Transformar y enriquecer datos
        dashboard_data = await _build_dashboard_data(
            profile_data, recent_bets_data, stats_data, events_data
        )
        
        # Agregar metadatos del BFF
        dashboard_data["metadata"] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "processing_time_ms": round(dashboard_time * 1000, 2),
            "data_sources": len(dashboard_tasks),
            "cache_status": "fresh"  # Podrías verificar el estado del cache aquí
        }
        
        logger.info(f"Dashboard generated successfully in {dashboard_time:.2f}s")
        
        return DataResponse(
            message="Dashboard generated successfully",
            data=dashboard_data
        )
        
    except Exception as e:
        logger.error(f"Error generating dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate dashboard"
        )

@router.delete("/{bet_id}", response_model=DataResponse)
async def cancel_bet(
    bet_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Cancelar una apuesta con validaciones y auditoría completas.
    
    La cancelación de apuestas es una operación crítica que requiere
    validaciones especiales y auditoría detallada.
    """
    token = credentials.credentials
    transaction_id = f"cancel_{bet_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
    
    try:
        logger.info(f"Canceling bet {bet_id} [Transaction: {transaction_id}]")
        
        # Verificar que la apuesta se puede cancelar
        can_cancel = await _verify_bet_cancellation(bet_id, token)
        if not can_cancel["allowed"]:
            logger.warning(f"Bet cancellation not allowed [Transaction: {transaction_id}]: {can_cancel['reason']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Bet cannot be cancelled",
                    "reason": can_cancel["reason"],
                    "transaction_id": transaction_id
                }
            )
        
        # Procesar cancelación en el backend
        # Nota: El backend .NET maneja esto con DELETE /api/bets/{id}
        backend_response = await backend_service._make_request(
            "DELETE", f"/api/bets/{bet_id}", headers={"Authorization": f"Bearer {token}"}
        )
        
        # Auditar la cancelación
        await _audit_bet_cancellation(transaction_id, bet_id, backend_response, token)
        
        logger.info(f"Bet {bet_id} cancelled successfully [Transaction: {transaction_id}]")
        
        return DataResponse(
            message="Bet cancelled successfully",
            data={
                **backend_response,
                "transaction_id": transaction_id,
                "cancelled_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except HTTPException as e:
        await _audit_failed_cancellation(transaction_id, bet_id, str(e.detail), token)
        raise e
    
    except Exception as e:
        logger.error(f"Unexpected error cancelling bet {bet_id}: {str(e)}")
        await _audit_failed_cancellation(transaction_id, bet_id, str(e), token)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel bet"
        )

# === Funciones Helper Específicas del BFF ===

async def _validate_bet_request(bet_request: BetCreationRequest, token: str) -> List[str]:
    """
    Validaciones específicas del BFF que complementan las del backend.
    
    Estas validaciones son como un filtro adicional que protege tanto
    al usuario como al sistema de situaciones problemáticas.
    """
    errors = []
    
    # Validación de monto con reglas específicas del BFF
    if bet_request.amount < 1:
        errors.append("Minimum bet amount is $1")
    elif bet_request.amount > 5000:  # Límite más restrictivo que el backend
        errors.append("Maximum bet amount through BFF is $5000")
    
    # Validación de formato de monto
    if round(bet_request.amount, 2) != bet_request.amount:
        errors.append("Bet amount can have at most 2 decimal places")
    
    # Validación del equipo seleccionado
    if not bet_request.selected_team.strip():
        errors.append("Selected team cannot be empty")
    
    # Validación de caracteres especiales
    if any(char in bet_request.selected_team for char in ['<', '>', '&', '"', "'"]):
        errors.append("Selected team contains invalid characters")
    
    # Validación de evento (verificar que existe y está disponible)
    try:
        event_data = await backend_service.get_event_by_id(bet_request.event_id)
        if not event_data.get("canPlaceBets", False):
            errors.append("Event is not available for betting")
    except:
        errors.append("Event not found or not available")
    
    return errors

async def _perform_security_checks(bet_request: BetCreationRequest, token: str) -> Dict[str, Any]:
    """
    Realiza verificaciones de seguridad adicionales.
    
    Estas verificaciones son como un sistema de seguridad bancario
    que detecta patrones sospechosos o actividades inusuales.
    """
    checks = {"passed": True, "reason": None}
    
    # Verificar límites de tiempo (no permitir apuestas muy rápidas)
    # En un sistema real, podrías verificar el historial de apuestas recientes
    
    # Verificar patrones sospechosos de apuestas
    # Por ejemplo, múltiples apuestas grandes en poco tiempo
    
    # Verificar límites por usuario
    # Podrías implementar límites diarios o semanales
    
    return checks

async def _enrich_bet_preview(preview_data: Dict[str, Any], bet_request: BetCreationRequest) -> Dict[str, Any]:
    """
    Enriquece el preview de apuesta con información adicional del BFF.
    
    Esta función demuestra cómo el BFF puede agregar contexto valioso
    que ayude al usuario a tomar decisiones más informadas.
    """
    enriched = {**preview_data}
    
    # Agregar análisis de riesgo
    risk_level = _calculate_risk_level(bet_request.amount, preview_data.get("currentOdds", 1.0))
    enriched["risk_analysis"] = {
        "level": risk_level,
        "description": _get_risk_description(risk_level),
        "recommendation": _get_risk_recommendation(risk_level)
    }
    
    # Agregar comparación histórica
    enriched["historical_context"] = {
        "similar_bets_last_month": 0,  # Podrías calcular esto de la base de datos
        "average_odds_this_event": preview_data.get("currentOdds", 1.0),
        "odds_trend": "stable"  # Podrías calcular tendencia de odds
    }
    
    # Agregar sugerencias del BFF
    enriched["suggestions"] = _generate_bet_suggestions(bet_request, preview_data)
    
    return enriched

def _calculate_risk_level(amount: float, odds: float) -> str:
    """
    Calcula el nivel de riesgo de una apuesta.
    
    Esta función implementa un algoritmo simple de análisis de riesgo
    que toma en cuenta el monto y las probabilidades.
    """
    if amount > 1000:
        return "high"
    elif odds > 3.0:
        return "high"
    elif odds > 2.0:
        return "medium"
    else:
        return "low"

def _get_risk_description(risk_level: str) -> str:
    """Proporciona descripciones humanas del nivel de riesgo."""
    descriptions = {
        "low": "This is a relatively safe bet with good chances of winning",
        "medium": "This bet has moderate risk and potential reward",
        "high": "This is a high-risk bet with potentially high rewards"
    }
    return descriptions.get(risk_level, "Unknown risk level")

def _get_risk_recommendation(risk_level: str) -> str:
    """Proporciona recomendaciones basadas en el nivel de riesgo."""
    recommendations = {
        "low": "Consider this bet if you prefer steady, consistent returns",
        "medium": "Good balance of risk and reward - suitable for most bettors",
        "high": "Only consider if you're comfortable with potentially losing your stake"
    }
    return recommendations.get(risk_level, "Please evaluate carefully")

def _generate_bet_suggestions(bet_request: BetCreationRequest, preview_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Genera sugerencias inteligentes para mejorar la apuesta.
    
    Esta función demuestra cómo el BFF puede actuar como un consejero
    inteligente que ayuda a los usuarios a optimizar sus apuestas.
    """
    suggestions = []
    
    amount = bet_request.amount
    odds = preview_data.get("currentOdds", 1.0)
    
    # Sugerir montos alternativos
    if amount > 100:
        suggestions.append({
            "type": "amount_reduction",
            "suggestion": f"Consider betting ${amount * 0.5:.2f} to reduce risk",
            "reason": "Lower amount reduces potential loss while maintaining good returns"
        })
    
    # Sugerir basado en odds
    if odds > 2.5:
        suggestions.append({
            "type": "odds_warning",
            "suggestion": "Consider the high odds - this indicates lower probability",
            "reason": "Higher odds mean higher risk but also higher potential reward"
        })
    
    return suggestions

async def _audit_bet_transaction(transaction_id: str, bet_data: BetCreationRequest, 
                                backend_response: Dict[str, Any], validation_time: float,
                                backend_time: float, token: str):
    """
    Audita completamente una transacción de apuesta.
    
    La auditoría es crítica en sistemas financieros para rastrear
    todas las operaciones y detectar problemas o fraudes.
    """
    audit_entry = {
        "transaction_id": transaction_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": "create_bet",
        "status": "success",
        "request_data": {
            "event_id": bet_data.event_id,
            "selected_team": bet_data.selected_team,
            "amount": bet_data.amount
        },
        "response_data": {
            "bet_id": backend_response.get("id"),
            "odds": backend_response.get("odds"),
            "potential_win": backend_response.get("potentialWin")
        },
        "performance": {
            "validation_time_ms": round(validation_time * 1000, 2),
            "backend_time_ms": round(backend_time * 1000, 2),
            "total_time_ms": round((validation_time + backend_time) * 1000, 2)
        },
        "user_token_hash": _hash_token(token)  # No guardar el token completo
    }
    
    # En un sistema real, guardarías esto en un sistema de logging
    # o base de datos de auditoría
    logger.info(f"AUDIT: {audit_entry}")

async def _audit_failed_bet_attempt(transaction_id: str, bet_data: BetCreationRequest, 
                                  error_message: str, token: str):
    """Audita intentos fallidos de crear apuestas."""
    audit_entry = {
        "transaction_id": transaction_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": "create_bet",
        "status": "failed",
        "error_message": error_message,
        "request_data": {
            "event_id": bet_data.event_id,
            "selected_team": bet_data.selected_team,
            "amount": bet_data.amount
        },
        "user_token_hash": _hash_token(token)
    }
    
    logger.warning(f"AUDIT_FAILED: {audit_entry}")

def _hash_token(token: str) -> str:
    """
    Crea un hash del token para auditoría sin exponer el token completo.
    
    Esta función es importante para la seguridad: queremos poder
    rastrear actividades por usuario sin guardar tokens completos.
    """
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()[:16]

def _calculate_time_remaining(event_date: Optional[str]) -> Optional[str]:
    """
    Calcula el tiempo restante hasta un evento.
    
    Esta función proporciona información útil para el frontend
    sobre cuánto tiempo queda para que empiece el evento.
    """
    if not event_date:
        return None
    
    try:
        event_datetime = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
        time_diff = event_datetime - datetime.now(timezone.utc)
        
        if time_diff.total_seconds() < 0:
            return "Event started"
        elif time_diff.days > 0:
            return f"{time_diff.days} days"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            return f"{hours} hours"
        else:
            minutes = time_diff.seconds // 60
            return f"{minutes} minutes"
    except:
        return None

def _calculate_profit_loss(bet_data: Dict[str, Any]) -> Optional[float]:
    """
    Calcula la ganancia o pérdida de una apuesta.
    
    Esta función ayuda al usuario a entender rápidamente
    su posición financiera en cada apuesta.
    """
    status = bet_data.get("status", "").lower()
    amount = bet_data.get("amount", 0)
    potential_win = bet_data.get("potentialWin", 0)
    
    if status == "won":
        return potential_win - amount  # Ganancia neta
    elif status == "lost":
        return -amount  # Pérdida total
    elif status == "refunded":
        return 0  # Sin ganancia ni pérdida
    else:
        return None  # Apuesta activa

def _is_bet_winning(bet_data: Dict[str, Any]) -> Optional[bool]:
    """
    Determina si una apuesta está ganando actualmente.
    
    En un sistema real, esto podría basarse en el estado
    actual del juego o evento deportivo.
    """
    status = bet_data.get("status", "").lower()
    
    if status == "won":
        return True
    elif status == "lost":
        return False
    else:
        return None  # No se puede determinar aún

def _transform_bet_statistics(stats_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforma estadísticas del backend al formato optimizado del BFF.
    
    Esta función puede agregar métricas adicionales y
    formatear los datos para que sean más útiles para el frontend.
    """
    transformed = {
        "total_bets": stats_data.get("totalBets", 0),
        "active_bets": stats_data.get("activeBets", 0),
        "won_bets": stats_data.get("wonBets", 0),
        "lost_bets": stats_data.get("lostBets", 0),
        "total_amount_bet": stats_data.get("totalAmountBet", 0),
        "total_winnings": stats_data.get("totalWinnings", 0),
        "current_potential_win": stats_data.get("currentPotentialWin", 0),
        "win_rate": stats_data.get("winRate", 0),
        "average_bet_amount": stats_data.get("averageBetAmount", 0),
        
        # Métricas adicionales calculadas por el BFF
        "net_profit": stats_data.get("totalWinnings", 0) - stats_data.get("totalAmountBet", 0),
        "performance_rating": _calculate_performance_rating(stats_data),
        "risk_profile": _determine_risk_profile(stats_data)
    }
    
    return transformed

def _calculate_performance_rating(stats_data: Dict[str, Any]) -> str:
    """
    Calcula una calificación de rendimiento basada en las estadísticas.
    
    Esta función proporciona una evaluación simple del rendimiento
    del usuario que puede ser útil para gamificación o insights.
    """
    win_rate = stats_data.get("winRate", 0)
    total_bets = stats_data.get("totalBets", 0)
    
    if total_bets < 5:
        return "Beginner"
    elif win_rate >= 70:
        return "Excellent"
    elif win_rate >= 60:
        return "Good"
    elif win_rate >= 50:
        return "Average"
    else:
        return "Needs Improvement"

def _determine_risk_profile(stats_data: Dict[str, Any]) -> str:
    """
    Determina el perfil de riesgo del usuario basado en sus patrones de apuesta.
    
    Esta función analiza el comportamiento histórico para clasificar
    al usuario en un perfil de riesgo, útil para recomendaciones.
    """
    avg_bet = stats_data.get("averageBetAmount", 0)
    total_bets = stats_data.get("totalBets", 0)
    
    if total_bets < 3:
        return "Unknown"
    elif avg_bet > 500:
        return "High Risk"
    elif avg_bet > 100:
        return "Medium Risk"
    else:
        return "Conservative"

async def _build_dashboard_data(profile_data: Optional[Dict], recent_bets_data: List[Dict], 
                               stats_data: Optional[Dict], events_data: List[Dict]) -> Dict[str, Any]:
    """
    Construye los datos completos del dashboard agregando información de múltiples fuentes.
    
    Esta función es un ejemplo perfecto de cómo el BFF agrega valor:
    toma datos de múltiples fuentes y los combina en una respuesta
    optimizada para el frontend.
    """
    dashboard = {
        "user_profile": profile_data or {},
        "recent_bets": recent_bets_data,
        "statistics": _transform_bet_statistics(stats_data) if stats_data else {},
        "available_events": events_data[:10],  # Solo mostrar los primeros 10
        "notifications": [],  # Podrías agregar notificaciones del sistema
        "recommendations": []  # Podrías agregar recomendaciones personalizadas
    }
    
    # Agregar recomendaciones personalizadas basadas en el perfil del usuario
    if stats_data:
        dashboard["recommendations"] = _generate_user_recommendations(stats_data, events_data)
    
    # Agregar notificaciones relevantes
    dashboard["notifications"] = _generate_user_notifications(profile_data, recent_bets_data)
    
    return dashboard

def _generate_user_recommendations(stats_data: Dict[str, Any], events_data: List[Dict]) -> List[Dict[str, Any]]:
    """
    Genera recomendaciones personalizadas para el usuario.
    
    Esta función demuestra cómo el BFF puede proporcionar inteligencia
    artificial básica para mejorar la experiencia del usuario.
    """
    recommendations = []
    
    avg_bet = stats_data.get("averageBetAmount", 0)
    win_rate = stats_data.get("winRate", 0)
    
    # Recomendación basada en el rendimiento
    if win_rate > 70:
        recommendations.append({
            "type": "performance",
            "message": "You're doing great! Consider exploring higher-value bets",
            "priority": "low"
        })
    elif win_rate < 40:
        recommendations.append({
            "type": "performance",
            "message": "Try smaller bets to improve your win rate",
            "priority": "high"
        })
    
    # Recomendación basada en eventos populares
    if events_data:
        popular_event = max(events_data, key=lambda x: x.get("totalBetsCount", 0))
        recommendations.append({
            "type": "event",
            "message": f"Check out {popular_event.get('name', 'this popular event')} - lots of activity!",
            "priority": "medium",
            "event_id": popular_event.get("id")
        })
    
    return recommendations

def _generate_user_notifications(profile_data: Optional[Dict], recent_bets_data: List[Dict]) -> List[Dict[str, Any]]:
    """
    Genera notificaciones relevantes para el usuario.
    
    Las notificaciones pueden incluir recordatorios, alertas de eventos,
    o información importante sobre apuestas activas.
    """
    notifications = []
    
    # Notificación de bienvenida para usuarios nuevos
    if profile_data and profile_data.get("totalBets", 0) < 5:
        notifications.append({
            "type": "welcome",
            "message": "Welcome to sports betting! Start with small bets to learn the system",
            "priority": "info"
        })
    
    # Notificación sobre apuestas que vencen pronto
    active_bets = [bet for bet in recent_bets_data if bet.get("status") == "Active"]
    if active_bets:
        notifications.append({
            "type": "reminder",
            "message": f"You have {len(active_bets)} active bets - check their status!",
            "priority": "medium"
        })
    
    return notifications

async def _verify_bet_cancellation(bet_id: int, token: str) -> Dict[str, Any]:
    """
    Verifica si una apuesta puede ser cancelada.
    
    Esta función proporciona una verificación previa a la cancelación
    para evitar intentos fallidos y mejorar la experiencia del usuario.
    """
    try:
        # Obtener información de la apuesta
        bet_data = await backend_service._make_request(
            "GET", f"/api/bets/{bet_id}", headers={"Authorization": f"Bearer {token}"}
        )
        
        # Verificar si se puede cancelar
        if bet_data.get("status") != "Active":
            return {
                "allowed": False,
                "reason": "Only active bets can be cancelled"
            }
        
        if not bet_data.get("canBeCancelled", False):
            return {
                "allowed": False,
                "reason": "This bet cannot be cancelled (event may have started)"
            }
        
        return {"allowed": True}
        
    except Exception as e:
        return {
            "allowed": False,
            "reason": f"Unable to verify bet status: {str(e)}"
        }

async def _audit_bet_cancellation(transaction_id: str, bet_id: int, 
                                 backend_response: Dict[str, Any], token: str):
    """Audita la cancelación de una apuesta."""
    audit_entry = {
        "transaction_id": transaction_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": "cancel_bet",
        "status": "success",
        "bet_id": bet_id,
        "refund_amount": backend_response.get("amount", 0),
        "user_token_hash": _hash_token(token)
    }
    
    logger.info(f"AUDIT_CANCELLATION: {audit_entry}")

async def _audit_failed_cancellation(transaction_id: str, bet_id: int, 
                                    error_message: str, token: str):
    """Audita intentos fallidos de cancelación."""
    audit_entry = {
        "transaction_id": transaction_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": "cancel_bet",
        "status": "failed",
        "bet_id": bet_id,
        "error_message": error_message,
        "user_token_hash": _hash_token(token)
    }
    
    logger.warning(f"AUDIT_CANCELLATION_FAILED: {audit_entry}")

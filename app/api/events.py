# app/api/events.py
from fastapi import APIRouter, HTTPException, Query, Depends, status
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from app.models.schemas import EventSummary, EventDetail, DataResponse
from app.services.backend_service import backend_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/", response_model=DataResponse)
async def get_events(
    category: Optional[str] = Query(
        None, description="Filtrar por categoría de deporte"),
    team: Optional[str] = Query(None, description="Filtrar por equipo"),
    date_from: Optional[datetime] = Query(None, description="Fecha desde"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta"),
    include_stats: bool = Query(
        False, description="Incluir estadísticas de apuestas"),
    limit: int = Query(20, ge=1, le=100, description="Límite de resultados")
):
    """
    Obtener eventos con filtros y agregaciones inteligentes.
    
    Este endpoint demuestra el valor del BFF:
    1. Filtros adicionales que el backend no tiene
    2. Agregación de datos de múltiples fuentes
    3. Optimizaciones específicas para el frontend
    4. Cache inteligente basado en parámetros
    """
    try:
        logger.info(
            f"Fetching events with filters: category={category}, team={team}")

        # Obtener eventos del backend
        backend_events = await backend_service.get_events()

        # Transformar datos del backend al formato del BFF
        events = []
        for event_data in backend_events:
            # Convertir al modelo del BFF
            event = EventSummary(
                id=event_data["id"],
                name=event_data["name"],
                team_a=event_data["teamA"],
                team_b=event_data["teamB"],
                team_a_odds=event_data["teamAOdds"],
                team_b_odds=event_data["teamBOdds"],
                event_date=event_data["eventDate"],
                status=event_data["status"],
                can_place_bets=event_data["canPlaceBets"],
                time_until_event=event_data["timeUntilEvent"],
                total_bets_amount=event_data.get("totalBetsAmount", 0),
                total_bets_count=event_data.get("totalBetsCount", 0),
                # El BFF calcula información adicional
                popularity_score=_calculate_popularity_score(event_data)
            )
            events.append(event)

        # Aplicar filtros específicos del BFF
        filtered_events = _apply_bff_filters(
            events, category, team, date_from, date_to
        )

        # Agregar estadísticas si se solicitan
        if include_stats:
            filtered_events = await _enrich_with_stats(filtered_events)

        # Aplicar límite y ordenamiento inteligente
        sorted_events = _sort_events_intelligently(filtered_events)
        final_events = sorted_events[:limit]

        # Preparar respuesta enriquecida
        response_data = {
            "events": [event.dict() for event in final_events],
            "total_count": len(filtered_events),
            "filtered_count": len(final_events),
            "cache_info": {
                "cached": False,  # Podríamos verificar si vino del cache
                "cache_expires_at": datetime.utcnow() + timedelta(minutes=5)
            }
        }

        logger.info(f"Returning {len(final_events)} events")

        return DataResponse(
            message=f"Found {len(final_events)} events",
            data=response_data
        )

    except HTTPException as e:
        logger.warning(f"Error fetching events: {e.detail}")
        raise e

    except Exception as e:
        logger.error(f"Unexpected error fetching events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch events"
        )


@router.get("/{event_id}", response_model=DataResponse)
async def get_event_detail(
    event_id: int,
    include_recent_bets: bool = Query(
        True, description="Incluir apuestas recientes"),
    include_statistics: bool = Query(
        True, description="Incluir estadísticas detalladas")
):
    """
    Obtener detalles completos de un evento con agregación de datos.
    
    Este endpoint muestra cómo el BFF puede:
    1. Combinar datos de múltiples endpoints del backend
    2. Agregar información calculada
    3. Optimizar la respuesta para reducir peticiones del frontend
    """
    try:
        logger.info(f"Fetching details for event {event_id}")

        # Obtener datos básicos del evento
        event_data = await backend_service.get_event_by_id(event_id)

        # Crear objeto base del evento
        event_detail = EventDetail(
            id=event_data["id"],
            name=event_data["name"],
            team_a=event_data["teamA"],
            team_b=event_data["teamB"],
            team_a_odds=event_data["teamAOdds"],
            team_b_odds=event_data["teamBOdds"],
            event_date=event_data["eventDate"],
            status=event_data["status"],
            can_place_bets=event_data["canPlaceBets"],
            time_until_event=event_data["timeUntilEvent"],
            created_at=event_data["createdAt"],
            popularity_score=_calculate_popularity_score(event_data)
        )

        # Agregar información adicional si se solicita
        if include_statistics:
            stats = await backend_service.get_event_stats(event_id)
            event_detail.betting_statistics = _transform_betting_stats(stats)

        if include_recent_bets:
            # Aquí podríamos obtener apuestas recientes de otro endpoint
            # Por simplicidad, agregamos datos simulados
            event_detail.recent_bets = _get_simulated_recent_bets()

        # Agregar información enriquecida que solo el BFF puede calcular
        enriched_data = {
            **event_detail.dict(),
            "recommendations": _get_betting_recommendations(event_detail),
            "related_events": await _get_related_events(event_id),
            "social_metrics": _calculate_social_metrics(event_detail),
        }

        return DataResponse(
            message="Event details retrieved successfully",
            data=enriched_data
        )

    except HTTPException as e:
        logger.warning(f"Error fetching event {event_id}: {e.detail}")
        raise e

    except Exception as e:
        logger.error(f"Unexpected error fetching event {event_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch event details"
        )


@router.get("/trending/popular", response_model=DataResponse)
async def get_popular_events(limit: int = Query(10, ge=1, le=50)):
    """
    Obtener eventos populares basados en algoritmo del BFF.
    
    Este endpoint demuestra cómo el BFF puede crear funcionalidad
    completamente nueva combinando datos existentes.
    """
    try:
        logger.info("Fetching popular events")

        # Obtener todos los eventos
        backend_events = await backend_service.get_events()

        # Calcular popularidad usando algoritmo del BFF
        events_with_popularity = []
        for event_data in backend_events:
            popularity = _calculate_advanced_popularity(event_data)
            events_with_popularity.append({
                **event_data,
                "popularity_score": popularity,
                "trending_rank": 0  # Se calculará después del ordenamiento
            })

        # Ordenar por popularidad
        sorted_events = sorted(
            events_with_popularity,
            key=lambda x: x["popularity_score"],
            reverse=True
        )

        # Asignar rankings
        for i, event in enumerate(sorted_events[:limit]):
            event["trending_rank"] = i + 1

        popular_events = sorted_events[:limit]

        return DataResponse(
            message=f"Found {len(popular_events)} popular events",
            data={
                "events": popular_events,
                "algorithm_version": "1.0",
                "last_updated": datetime.utcnow().isoformat()
            }
        )

    except Exception as e:
        logger.error(f"Error fetching popular events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch popular events"
        )

# === Funciones Helper Específicas del BFF ===


def _calculate_popularity_score(event_data: dict) -> float:
    """
    Calcula score de popularidad basado en múltiples factores.
    Esta es lógica específica del BFF que agrega valor.
    """
    base_score = 0.0

    # Factor por cantidad de apuestas
    bet_count = event_data.get("totalBetsCount", 0)
    base_score += min(bet_count * 0.1, 10.0)  # Máximo 10 puntos

    # Factor por monto total apostado
    total_amount = event_data.get("totalBetsAmount", 0)
    base_score += min(total_amount / 1000, 15.0)  # Máximo 15 puntos

    # Factor por proximidad del evento
    from datetime import timezone
    event_date = datetime.fromisoformat(
        event_data["eventDate"].replace("Z", "+00:00"))
    current_time = datetime.now(timezone.utc)
    days_until = (event_date - current_time).days
    if days_until <= 1:
        base_score += 20.0  # Eventos próximos son más populares
    elif days_until <= 7:
        base_score += 10.0

    # Factor por equipos conocidos (lógica simplificada)
    popular_teams = ["Real Madrid", "Barcelona",
                     "Manchester United", "Liverpool"]
    team_a = event_data.get("teamA", "")
    team_b = event_data.get("teamB", "")

    if team_a in popular_teams:
        base_score += 5.0
    if team_b in popular_teams:
        base_score += 5.0

    return round(base_score, 2)


def _apply_bff_filters(events: List[EventSummary], category: Optional[str],
                       team: Optional[str], date_from: Optional[datetime],
                       date_to: Optional[datetime]) -> List[EventSummary]:
    """
    Aplica filtros específicos del BFF que el backend no tiene.
    """
    from datetime import timezone
    filtered = events

    if team:
        filtered = [
            e for e in filtered
            if team.lower() in e.team_a.lower() or team.lower() in e.team_b.lower()
        ]

    if date_from:
        # Ensure date_from is timezone-aware
        if date_from.tzinfo is None:
            date_from = date_from.replace(tzinfo=timezone.utc)
        filtered = [e for e in filtered if e.event_date >= date_from]

    if date_to:
        # Ensure date_to is timezone-aware
        if date_to.tzinfo is None:
            date_to = date_to.replace(tzinfo=timezone.utc)
        filtered = [e for e in filtered if e.event_date <= date_to]

    # Aquí podrías agregar más filtros específicos del BFF

    return filtered


def _sort_events_intelligently(events: List[EventSummary]) -> List[EventSummary]:
    """
    Ordena eventos usando algoritmo inteligente del BFF.
    """
    from datetime import timezone
    current_time = datetime.now(timezone.utc)
    return sorted(
        events,
        key=lambda e: (
            e.popularity_score,  # Popularidad principal
            -abs((e.event_date - current_time).days),  # Proximidad
            e.total_bets_amount  # Monto total apostado
        ),
        reverse=True
    )


async def _enrich_with_stats(events: List[EventSummary]) -> List[EventSummary]:
    """
    Enriquece eventos con estadísticas adicionales.
    En una implementación real, podría hacer llamadas paralelas al backend.
    """
    # Por simplicidad, no hacemos llamadas reales aquí
    # En producción, usarías asyncio.gather para llamadas paralelas
    return events


def _transform_betting_stats(stats: dict) -> dict:
    """
    Transforma estadísticas del backend al formato del BFF.
    """
    return {
        "total_bets": stats.get("totalBets", 0),
        "total_amount": stats.get("totalAmountBet", 0),
        "team_a_percentage": stats.get("teamAPercentage", 0),
        "team_b_percentage": stats.get("teamBPercentage", 0),
        "betting_trend": "increasing" if stats.get("totalBets", 0) > 10 else "stable"
    }


def _get_simulated_recent_bets() -> List[dict]:
    """
    Simula apuestas recientes para el ejemplo.
    En producción, esto vendría de la API del backend.
    """
    return [
        {
            "user": "User123",
            "amount": 100.0,
            "team": "Real Madrid",
            "timestamp": "2024-01-01T12:00:00Z"
        }
    ]


def _get_betting_recommendations(event: EventDetail) -> List[dict]:
    """
    Genera recomendaciones de apuestas basadas en el evento.
    Lógica específica del BFF que agrega valor al frontend.
    """
    recommendations = []

    # Recomendación basada en odds
    if event.team_a_odds > event.team_b_odds:
        recommendations.append({
            "type": "underdog",
            "team": event.team_a,
            "reason": "Higher odds, potential for bigger win",
            "confidence": 0.7
        })

    # Recomendación basada en popularidad
    if event.popularity_score > 50:
        recommendations.append({
            "type": "popular",
            "reason": "High user interest in this event",
            "confidence": 0.8
        })

    return recommendations


async def _get_related_events(event_id: int) -> List[dict]:
    """
    Obtiene eventos relacionados.
    Podría usar algoritmos de recomendación más sofisticados.
    """
    # Implementación simplificada
    return []


def _calculate_social_metrics(event: EventDetail) -> dict:
    """
    Calcula métricas sociales del evento.
    """
    return {
        "buzz_score": event.popularity_score * 0.1,
        "sentiment": "positive",  # Podría venir de análisis de redes sociales
        "mentions": event.total_bets_count * 2  # Simulado
    }


def _calculate_advanced_popularity(event_data: dict) -> float:
    """
    Algoritmo avanzado de popularidad para trending events.
    """
    # Implementación más sofisticada del cálculo de popularidad
    base_score = _calculate_popularity_score(event_data)

    # Factores adicionales para trending
    time_factor = 1.0  # Podrías agregar factores temporales
    engagement_factor = 1.0  # Podrías agregar engagement metrics

    return base_score * time_factor * engagement_factor

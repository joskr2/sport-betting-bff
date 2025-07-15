# app/models/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# === Schemas de Respuesta Genérica ===


class BaseResponse(BaseModel):
    """
    Schema base para todas las respuestas del BFF.
    Proporciona estructura consistente para el frontend.
    """
    success: bool = True
    message: str = "Operation completed successfully"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DataResponse(BaseResponse):
    """
    Respuesta que incluye datos específicos.
    Genérico para poder usar con cualquier tipo de data.
    """
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseResponse):
    """
    Schema para respuestas de error.
    Proporciona información detallada para debugging.
    """
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# === Schemas de Autenticación ===


class UserRegistrationRequest(BaseModel):
    """
    Schema para registro de usuarios.
    Incluye validaciones mejoradas para el frontend.
    """
    email: str = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=6, description="Contraseña segura")
    full_name: str = Field(..., min_length=2, max_length=100,
                           description="Nombre completo")

    @validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """
        Validación de fortaleza de contraseña.
        Más estricta que la del backend para mejor UX.
        """
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        if not any(c.isupper() for c in v):
            raise ValueError(
                'Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError(
                'Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

    @validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        """Validar que el nombre no contenga caracteres especiales problemáticos."""
        if any(char in v for char in ['<', '>', '&', '"', "'"]):
            raise ValueError('Full name contains invalid characters')
        return v.strip()


class UserLoginRequest(BaseModel):
    """Schema para login simplificado."""
    email: str
    password: str = Field(..., min_length=1)


class AuthResponse(BaseModel):
    """
    Respuesta de autenticación enriquecida.
    Incluye información adicional útil para el frontend.
    """
    token: str = Field(..., description="JWT token para futuras peticiones")
    email: str
    full_name: str
    balance: float
    expires_at: datetime
    user_id: Optional[int] = None
    permissions: List[str] = Field(default_factory=list)

# === Schemas de Eventos ===


class EventStatus(str, Enum):
    """Estados posibles de un evento deportivo."""
    UPCOMING = "Upcoming"
    LIVE = "Live"
    FINISHED = "Finished"
    CANCELLED = "Cancelled"


class EventSummary(BaseModel):
    """
    Resumen de evento optimizado para listas.
    Contiene solo la información esencial para renderizar cards.
    """
    id: int
    name: str
    team_a: str
    team_b: str
    team_a_odds: float
    team_b_odds: float
    event_date: datetime
    status: EventStatus
    can_place_bets: bool
    time_until_event: str

    # Información agregada que el BFF puede calcular
    total_bets_amount: float = 0
    total_bets_count: int = 0
    popularity_score: float = Field(
        default=0, description="Score calculado por el BFF")


class EventDetail(EventSummary):
    """
    Detalles completos de un evento.
    Extiende EventSummary con información adicional.
    """
    created_at: datetime
    description: Optional[str] = None
    venue: Optional[str] = None
    betting_statistics: Optional[Dict[str, Any]] = None
    recent_bets: List[Dict[str, Any]] = Field(default_factory=list)

# === Schemas de Apuestas ===


class BetCreationRequest(BaseModel):
    """
    Request para crear apuesta con validaciones mejoradas.
    """
    event_id: int = Field(..., gt=0, description="ID del evento")
    selected_team: str = Field(..., min_length=1,
                               description="Equipo seleccionado")
    amount: float = Field(..., gt=0, le=10000,
                          description="Monto de la apuesta")

    @validator('amount')
    @classmethod
    def validate_amount_precision(cls, v):
        """Validar que el monto tenga máximo 2 decimales."""
        if round(v, 2) != v:
            raise ValueError('Amount can have at most 2 decimal places')
        return v


class BetStatus(str, Enum):
    """Estados posibles de una apuesta."""
    ACTIVE = "Active"
    WON = "Won"
    LOST = "Lost"
    REFUNDED = "Refunded"


class BetResponse(BaseModel):
    """
    Respuesta de apuesta enriquecida con información calculada.
    """
    id: int
    event_id: int
    event_name: str
    selected_team: str
    amount: float
    odds: float
    potential_win: float
    status: BetStatus
    created_at: datetime

    # Información adicional calculada por el BFF
    profit_loss: Optional[float] = None
    is_winning: Optional[bool] = None
    time_remaining: Optional[str] = None
    can_be_cancelled: bool = False


class BetStatistics(BaseModel):
    """
    Estadísticas de apuestas del usuario.
    Agregación de datos calculada por el BFF.
    """
    total_bets: int
    active_bets: int
    won_bets: int
    lost_bets: int
    total_amount_bet: float
    total_winnings: float
    current_potential_win: float
    win_rate: float
    average_bet_amount: float

    # Métricas adicionales que el BFF puede calcular
    biggest_win: float = 0
    biggest_loss: float = 0
    favorite_team: Optional[str] = None
    monthly_spending: Dict[str, float] = Field(default_factory=dict)

# === Schemas de Dashboard ===


class DashboardData(BaseModel):
    """
    Agregación de datos para el dashboard del usuario.
    Ejemplo de cómo el BFF puede combinar múltiples fuentes.
    """
    user_profile: Dict[str, Any]
    recent_events: List[EventSummary]
    user_bets: List[BetResponse]
    statistics: BetStatistics
    notifications: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_events: List[EventSummary] = Field(default_factory=list)

# === Schemas de Configuración ===


class AppConfiguration(BaseModel):
    """
    Configuración de la aplicación para el frontend.
    """
    max_bet_amount: float
    min_bet_amount: float
    supported_currencies: List[str] = ["USD"]
    betting_rules: Dict[str, Any] = Field(default_factory=dict)
    feature_flags: Dict[str, bool] = Field(default_factory=dict)

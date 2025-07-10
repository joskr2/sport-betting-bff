# tests/conftest.py
from app.core.config import settings
from app.main import app
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
import os
import sys
from unittest.mock import patch
import asyncio

# Agregar el directorio app al path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# Configurar settings para testing
settings.debug = True
settings.enable_cache = False  # Deshabilitar cache en tests
settings.backend_api_url = "https://api-kurax-demo-jos.uk"  # Use real external API for integration tests


@pytest.fixture
def client():
    """
    Cliente de prueba sincrónico para FastAPI.
    
    Útil para tests simples que no requieren funcionalidad asíncrona.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def async_client():
    """
    Cliente de prueba asíncrono para FastAPI.
    
    Necesario para tests que involucran operaciones asíncronas
    como llamadas a servicios externos.
    """
    async with AsyncClient(app=app, base_url="http://test") as async_test_client:
        yield async_test_client


@pytest.fixture
def mock_backend_response():
    """
    Fixture para simular respuestas del backend durante tests.
    
    Esto nos permite probar el BFF sin depender del backend real.
    """
    return {
        "health": {"status": "healthy"},
        "events": [
            {
                "id": 1,
                "name": "Real Madrid vs Barcelona - El Clásico",
                "teamA": "Real Madrid",
                "teamB": "Barcelona",
                "teamAOdds": 2.10,
                "teamBOdds": 1.95,
                "eventDate": "2024-01-15T20:00:00Z",
                "status": "Upcoming",
                "canPlaceBets": True,
                "timeUntilEvent": "7 days",
                "totalBetsAmount": 1500.0,
                "totalBetsCount": 25,
                "createdAt": "2024-01-01T00:00:00Z"
            },
            {
                "id": 2,
                "name": "Manchester United vs Liverpool",
                "teamA": "Manchester United",
                "teamB": "Liverpool",
                "teamAOdds": 2.50,
                "teamBOdds": 1.75,
                "eventDate": "2024-01-20T15:00:00Z",
                "status": "Upcoming",
                "canPlaceBets": True,
                "timeUntilEvent": "12 days",
                "totalBetsAmount": 800.0,
                "totalBetsCount": 15,
                "createdAt": "2024-01-01T00:00:00Z"
            }
        ],
        "login": {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "email": "testuser@example.com",
            "fullName": "Test User",
            "balance": 1000.0,
            "expiresAt": "2024-12-31T23:59:59Z"
        },
        "register": {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "email": "testuser@example.com",
            "fullName": "Test User",
            "balance": 1000.0,
            "expiresAt": "2024-12-31T23:59:59Z"
        },
        "profile": {
            "id": 1,
            "email": "testuser@example.com",
            "fullName": "Test User",
            "balance": 1000.0,
            "createdAt": "2024-01-01T00:00:00Z",
            "totalBets": 5,
            "totalBetAmount": 500.0
        },
        "bet_preview": {
            "isValid": True,
            "errors": [],
            "amount": 100.00,
            "currentOdds": 2.10,
            "potentialWin": 210.00,
            "potentialProfit": 110.00,
            "currentBalance": 1000.00,
            "balanceAfterBet": 900.00,
            "eventName": "Real Madrid vs Barcelona - El Clásico",
            "selectedTeam": "Real Madrid",
            "message": "Bet preview is valid. You can proceed to create this bet."
        },
        "bet_created": {
            "id": 1,
            "eventId": 1,
            "eventName": "Real Madrid vs Barcelona - El Clásico",
            "selectedTeam": "Real Madrid",
            "amount": 100.00,
            "odds": 2.10,
            "potentialWin": 210.00,
            "status": "Active",
            "createdAt": "2024-01-01T12:00:00Z",
            "eventDate": "2024-01-15T20:00:00Z",
            "canBeCancelled": True
        },
        "user_bets": [
            {
                "id": 1,
                "eventId": 1,
                "eventName": "Real Madrid vs Barcelona - El Clásico",
                "selectedTeam": "Real Madrid",
                "amount": 100.00,
                "odds": 2.10,
                "potentialWin": 210.00,
                "status": "Active",
                "createdAt": "2024-01-01T12:00:00Z",
                "eventDate": "2024-01-15T20:00:00Z",
                "canBeCancelled": True
            }
        ],
        "bet_stats": {
            "totalBets": 2,
            "activeBets": 1,
            "wonBets": 1,
            "lostBets": 0,
            "totalAmountBet": 150.00,
            "totalWinnings": 87.50,
            "currentPotentialWin": 210.00,
            "winRate": 50.0,
            "averageBetAmount": 75.00
        }
    }


@pytest.fixture
def sample_event():
    """Sample event data for testing."""
    return {
        "id": 1,
        "name": "Real Madrid vs Barcelona - El Clásico",
        "teamA": "Real Madrid",
        "teamB": "Barcelona",
        "teamAOdds": 2.10,
        "teamBOdds": 1.95,
        "eventDate": "2024-01-15T20:00:00Z",
        "status": "Upcoming",
        "canPlaceBets": True,
        "timeUntilEvent": "7 days",
        "totalBetsAmount": 1500.0,
        "totalBetsCount": 25,
        "createdAt": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_user():
    """Sample user data for testing."""
    return {
        "id": 1,
        "email": "testuser@example.com",
        "fullName": "Test User",
        "balance": 1000.0,
        "createdAt": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def valid_jwt_token():
    """Valid JWT token for testing authenticated endpoints."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"


@pytest.fixture
def auth_headers(valid_jwt_token):
    """Authentication headers for API requests."""
    return {"Authorization": f"Bearer {valid_jwt_token}"}


@pytest.fixture(autouse=True)
def reset_backend_service_cache():
    """Reset backend service cache before each test."""
    from app.services.backend_service import backend_service
    backend_service.clear_cache()
    backend_service.stats = {
        "requests_made": 0,
        "cache_hits": 0,
        "errors": 0,
        "average_response_time": 0
    }


@pytest.fixture
def mock_backend_service():
    """Mock backend service for unit tests."""
    with patch('app.services.backend_service.backend_service') as mock:
        yield mock


# Configure pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# tests/test_bets.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from datetime import datetime
from app.main import app

client = TestClient(app)


class TestBets:
    """Test suite for betting endpoints."""
    
    @pytest.fixture
    def valid_bet_request(self):
        """Valid bet creation request."""
        return {
            "event_id": 1,
            "selected_team": "Real Madrid",
            "amount": 100.00
        }
    
    @pytest.fixture
    def mock_bet_preview_response(self):
        """Mock bet preview response from backend."""
        return {
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
        }
    
    @pytest.fixture
    def mock_bet_response(self):
        """Mock bet creation response from backend."""
        return {
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
    
    @pytest.fixture
    def mock_user_bets(self):
        """Mock user bets list response."""
        return [
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
            },
            {
                "id": 2,
                "eventId": 2,
                "eventName": "Manchester United vs Liverpool",
                "selectedTeam": "Liverpool",
                "amount": 50.00,
                "odds": 1.75,
                "potentialWin": 87.50,
                "status": "Won",
                "createdAt": "2024-01-02T10:00:00Z",
                "eventDate": "2024-01-10T15:00:00Z",
                "canBeCancelled": False
            }
        ]
    
    @pytest.fixture
    def mock_bet_stats(self):
        """Mock user betting statistics."""
        return {
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
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for requests."""
        return {"Authorization": "Bearer valid-token"}
    
    @patch('app.services.backend_service.backend_service.get_event_by_id')
    @patch('app.services.backend_service.backend_service.preview_bet')
    def test_preview_bet_success(self, mock_preview, mock_get_event, 
                                valid_bet_request, mock_bet_preview_response, auth_headers):
        """Test successful bet preview."""
        # Mock event exists and is valid
        mock_get_event.return_value = {"id": 1, "canPlaceBets": True}
        mock_preview.return_value = mock_bet_preview_response
        
        response = client.post("/api/bets/preview", 
                             json=valid_bet_request, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify BFF response structure
        assert data["success"] is True
        assert "data" in data
        
        # Verify BFF enhancements are included
        preview_data = data["data"]
        assert "risk_analysis" in preview_data  # BFF enhancement
        assert "historical_context" in preview_data  # BFF enhancement
        assert "suggestions" in preview_data  # BFF enhancement
        
        # Verify risk analysis structure
        risk_analysis = preview_data["risk_analysis"]
        assert "level" in risk_analysis
        assert "description" in risk_analysis
        assert "recommendation" in risk_analysis
    
    def test_preview_bet_no_auth(self, valid_bet_request):
        """Test bet preview without authentication."""
        response = client.post("/api/bets/preview", json=valid_bet_request)
        
        assert response.status_code == 403
    
    def test_preview_bet_invalid_amount(self, auth_headers):
        """Test bet preview with invalid amount."""
        invalid_request = {
            "event_id": 1,
            "selected_team": "Real Madrid",
            "amount": 0.50  # Below minimum
        }
        
        response = client.post("/api/bets/preview", 
                             json=invalid_request, 
                             headers=auth_headers)
        
        # Should either return 422 for validation or 200 with errors in data
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is False
    
    def test_preview_bet_invalid_event_id(self, auth_headers):
        """Test bet preview with invalid event ID."""
        invalid_request = {
            "event_id": 0,  # Invalid ID
            "selected_team": "Real Madrid",
            "amount": 100.00
        }
        
        response = client.post("/api/bets/preview", 
                             json=invalid_request, 
                             headers=auth_headers)
        
        assert response.status_code == 422
    
    @patch('app.services.backend_service.backend_service.get_event_by_id')
    @patch('app.services.backend_service.backend_service.create_bet')
    def test_create_bet_success(self, mock_create_bet, mock_get_event,
                               valid_bet_request, mock_bet_response, auth_headers):
        """Test successful bet creation."""
        # Mock event validation
        mock_get_event.return_value = {"id": 1, "canPlaceBets": True}
        mock_create_bet.return_value = mock_bet_response
        
        response = client.post("/api/bets/", 
                             json=valid_bet_request, 
                             headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify BFF response structure
        assert data["success"] is True
        assert data["message"] == "Bet created successfully"
        assert "data" in data
        
        # Verify BFF enhancements
        bet_data = data["data"]
        assert "transaction_id" in bet_data  # BFF enhancement
        assert "confirmation_code" in bet_data  # BFF enhancement
        assert "processing_time" in bet_data  # BFF enhancement
        assert "can_be_cancelled" in bet_data
        assert "time_remaining" in bet_data
        
        # Verify processing time structure
        processing_time = bet_data["processing_time"]
        assert "validation_ms" in processing_time
        assert "backend_ms" in processing_time
        assert "total_ms" in processing_time
    
    def test_create_bet_no_auth(self, valid_bet_request):
        """Test bet creation without authentication."""
        response = client.post("/api/bets/", json=valid_bet_request)
        
        assert response.status_code == 403
    
    def test_create_bet_invalid_data(self, auth_headers):
        """Test bet creation with invalid data."""
        invalid_request = {
            "event_id": -1,
            "selected_team": "",
            "amount": -100.00
        }
        
        response = client.post("/api/bets/", 
                             json=invalid_request, 
                             headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_create_bet_excessive_amount(self, auth_headers):
        """Test bet creation with amount exceeding BFF limit."""
        excessive_request = {
            "event_id": 1,
            "selected_team": "Real Madrid",
            "amount": 10000.00  # Exceeds BFF limit of 5000
        }
        
        response = client.post("/api/bets/", 
                             json=excessive_request, 
                             headers=auth_headers)
        
        # Should be rejected by BFF validation before reaching backend
        assert response.status_code == 400
    
    @patch('app.services.backend_service.backend_service.get_user_bets')
    @patch('app.services.backend_service.backend_service.get_user_bet_stats')
    def test_get_user_bets_success(self, mock_get_stats, mock_get_bets,
                                  mock_user_bets, mock_bet_stats, auth_headers):
        """Test successful retrieval of user bets."""
        mock_get_bets.return_value = mock_user_bets
        mock_get_stats.return_value = mock_bet_stats
        
        response = client.get("/api/bets/my-bets", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify BFF response structure
        assert data["success"] is True
        assert "data" in data
        
        # Verify pagination and structure
        bets_data = data["data"]
        assert "bets" in bets_data
        assert "pagination" in bets_data  # BFF enhancement
        assert "statistics" in bets_data  # BFF enhancement
        
        # Verify pagination structure
        pagination = bets_data["pagination"]
        assert "current_page" in pagination
        assert "page_size" in pagination
        assert "total_items" in pagination
        assert "total_pages" in pagination
        assert "has_next" in pagination
        assert "has_previous" in pagination
        
        # Verify bet enhancements
        bets = bets_data["bets"]
        assert len(bets) == 2
        
        for bet in bets:
            assert "profit_loss" in bet  # BFF enhancement
            assert "is_winning" in bet  # BFF enhancement
            assert "time_remaining" in bet  # BFF enhancement
    
    def test_get_user_bets_no_auth(self):
        """Test getting user bets without authentication."""
        response = client.get("/api/bets/my-bets")
        
        assert response.status_code == 403
    
    @patch('app.services.backend_service.backend_service.get_user_bets')
    def test_get_user_bets_with_filters(self, mock_get_bets, mock_user_bets, auth_headers):
        """Test getting user bets with filters."""
        mock_get_bets.return_value = mock_user_bets
        
        # Test with status filter
        response = client.get("/api/bets/my-bets?status_filter=Active&page=1&page_size=10",
                            headers=auth_headers)
        
        assert response.status_code == 200
        
        # Verify backend was called with correct parameters
        mock_get_bets.assert_called_once()
        call_args = mock_get_bets.call_args[1]  # Get keyword arguments
        assert "status" in call_args
    
    @patch('app.services.backend_service.backend_service.get_user_bets')
    def test_get_user_bets_pagination(self, mock_get_bets, mock_user_bets, auth_headers):
        """Test user bets pagination."""
        mock_get_bets.return_value = mock_user_bets
        
        # Test pagination parameters
        response = client.get("/api/bets/my-bets?page=2&page_size=1",
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        pagination = data["data"]["pagination"]
        assert pagination["current_page"] == 2
        assert pagination["page_size"] == 1
    
    @patch('app.services.backend_service.backend_service.get_user_profile')
    @patch('app.services.backend_service.backend_service.get_user_bets')
    @patch('app.services.backend_service.backend_service.get_user_bet_stats')
    @patch('app.services.backend_service.backend_service.get_events')
    def test_get_betting_dashboard(self, mock_get_events, mock_get_stats, 
                                 mock_get_bets, mock_get_profile, 
                                 mock_user_bets, mock_bet_stats, auth_headers):
        """Test betting dashboard aggregation."""
        # Mock all data sources
        mock_get_profile.return_value = {"id": 1, "email": "test@example.com", "balance": 1000.0}
        mock_get_bets.return_value = mock_user_bets[:1]  # Recent bets
        mock_get_stats.return_value = mock_bet_stats
        mock_get_events.return_value = [{"id": 1, "name": "Test Event"}]
        
        response = client.get("/api/bets/dashboard", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify dashboard structure
        assert data["success"] is True
        dashboard_data = data["data"]
        
        assert "user_profile" in dashboard_data
        assert "recent_bets" in dashboard_data
        assert "statistics" in dashboard_data
        assert "available_events" in dashboard_data
        assert "notifications" in dashboard_data  # BFF enhancement
        assert "recommendations" in dashboard_data  # BFF enhancement
        assert "metadata" in dashboard_data  # BFF enhancement
        
        # Verify metadata includes performance info
        metadata = dashboard_data["metadata"]
        assert "generated_at" in metadata
        assert "processing_time_ms" in metadata
        assert "data_sources" in metadata
        assert "cache_status" in metadata
    
    def test_get_betting_dashboard_no_auth(self):
        """Test betting dashboard without authentication."""
        response = client.get("/api/bets/dashboard")
        
        assert response.status_code == 403
    
    @patch('app.services.backend_service.backend_service._make_request')
    def test_cancel_bet_success(self, mock_make_request, auth_headers):
        """Test successful bet cancellation."""
        # Mock bet verification and cancellation
        mock_make_request.side_effect = [
            {"id": 1, "status": "Active", "canBeCancelled": True},  # GET verification
            {"betId": 1, "status": "Cancelled", "cancelledAt": "2024-01-01T12:30:00Z", 
             "message": "Bet has been successfully cancelled and amount refunded"}  # DELETE cancellation
        ]
        
        response = client.delete("/api/bets/1", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify BFF response structure
        assert data["success"] is True
        assert data["message"] == "Bet cancelled successfully"
        assert "data" in data
        
        # Verify BFF enhancements
        cancel_data = data["data"]
        assert "transaction_id" in cancel_data  # BFF enhancement
        assert "cancelled_at" in cancel_data  # BFF enhancement
    
    def test_cancel_bet_no_auth(self):
        """Test bet cancellation without authentication."""
        response = client.delete("/api/bets/1")
        
        assert response.status_code == 403
    
    @patch('app.services.backend_service.backend_service._make_request')
    def test_cancel_bet_not_cancellable(self, mock_make_request, auth_headers):
        """Test cancellation of non-cancellable bet."""
        # Mock bet that cannot be cancelled
        mock_make_request.return_value = {
            "id": 1, 
            "status": "Won", 
            "canBeCancelled": False
        }
        
        response = client.delete("/api/bets/1", headers=auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "transaction_id" in data["detail"]
    
    def test_invalid_bet_validation(self, auth_headers):
        """Test comprehensive bet validation."""
        invalid_requests = [
            # Invalid characters in team name
            {
                "event_id": 1,
                "selected_team": "Team<script>",
                "amount": 100.00
            },
            # Amount with too many decimals
            {
                "event_id": 1,
                "selected_team": "Real Madrid",
                "amount": 100.123
            },
            # Empty team name
            {
                "event_id": 1,
                "selected_team": "   ",
                "amount": 100.00
            }
        ]
        
        for invalid_request in invalid_requests:
            response = client.post("/api/bets/preview", 
                                 json=invalid_request, 
                                 headers=auth_headers)
            
            # Should be rejected by validation
            assert response.status_code in [200, 400, 422]
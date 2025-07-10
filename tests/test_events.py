# tests/test_events.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime
from app.main import app

client = TestClient(app)


class TestEvents:
    """Test suite for events endpoints."""
    
    @pytest.fixture
    def mock_events_data(self):
        """Mock events data from backend."""
        return [
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
        ]
    
    @pytest.fixture
    def mock_event_stats(self):
        """Mock event statistics data."""
        return {
            "totalBets": 25,
            "totalAmountBet": 1500.0,
            "teamAPercentage": 60.0,
            "teamBPercentage": 40.0,
            "lastBetDate": "2024-01-14T10:00:00Z"
        }
    
    @patch('app.services.backend_service.backend_service.get_events')
    def test_get_events_success(self, mock_get_events, mock_events_data):
        """Test successful retrieval of events list."""
        mock_get_events.return_value = mock_events_data
        
        response = client.get("/api/events/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify BFF response structure
        assert data["success"] is True
        assert "data" in data
        
        # Verify events data structure
        events_data = data["data"]
        assert "events" in events_data
        assert "total_count" in events_data
        assert "filtered_count" in events_data
        assert "cache_info" in events_data
        
        # Verify event structure includes BFF enhancements
        events = events_data["events"]
        assert len(events) == 2
        
        first_event = events[0]
        assert "id" in first_event
        assert "name" in first_event
        assert "team_a" in first_event
        assert "team_b" in first_event
        assert "popularity_score" in first_event  # BFF enhancement
        
        mock_get_events.assert_called_once()
    
    @patch('app.services.backend_service.backend_service.get_events')
    def test_get_events_with_filters(self, mock_get_events, mock_events_data):
        """Test events retrieval with filters."""
        mock_get_events.return_value = mock_events_data
        
        # Test with team filter
        response = client.get("/api/events/?team=Madrid&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify filtered results
        events = data["data"]["events"]
        # Should only return Real Madrid event
        assert len(events) == 1
        assert "Real Madrid" in events[0]["name"]
    
    @patch('app.services.backend_service.backend_service.get_events')
    def test_get_events_with_stats(self, mock_get_events, mock_events_data):
        """Test events retrieval with statistics included."""
        mock_get_events.return_value = mock_events_data
        
        response = client.get("/api/events/?include_stats=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["events"]) == 2
    
    @patch('app.services.backend_service.backend_service.get_event_by_id')
    @patch('app.services.backend_service.backend_service.get_event_stats')
    def test_get_event_detail_success(self, mock_get_stats, mock_get_event, mock_events_data, mock_event_stats):
        """Test successful retrieval of event details."""
        mock_get_event.return_value = mock_events_data[0]
        mock_get_stats.return_value = mock_event_stats
        
        response = client.get("/api/events/1")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify BFF response structure
        assert data["success"] is True
        assert "data" in data
        
        # Verify event detail includes BFF enhancements
        event_data = data["data"]
        assert "id" in event_data
        assert "name" in event_data
        assert "betting_statistics" in event_data  # BFF enhancement
        assert "recent_bets" in event_data  # BFF enhancement
        assert "recommendations" in event_data  # BFF enhancement
        assert "related_events" in event_data  # BFF enhancement
        assert "social_metrics" in event_data  # BFF enhancement
        
        mock_get_event.assert_called_once_with(1)
        mock_get_stats.assert_called_once_with(1)
    
    @patch('app.services.backend_service.backend_service.get_event_by_id')
    def test_get_event_detail_not_found(self, mock_get_event):
        """Test event detail retrieval for non-existent event."""
        from fastapi import HTTPException
        mock_get_event.side_effect = HTTPException(status_code=404, detail="Event not found")
        
        response = client.get("/api/events/99999")
        
        assert response.status_code == 404
    
    @patch('app.services.backend_service.backend_service.get_event_by_id')
    def test_get_event_detail_minimal(self, mock_get_event, mock_events_data):
        """Test event detail retrieval without optional data."""
        mock_get_event.return_value = mock_events_data[0]
        
        response = client.get("/api/events/1?include_recent_bets=false&include_statistics=false")
        
        assert response.status_code == 200
        data = response.json()
        
        event_data = data["data"]
        # Should still have BFF enhancements but less detailed
        assert "recommendations" in event_data
        assert "social_metrics" in event_data
    
    @patch('app.services.backend_service.backend_service.get_events')
    def test_get_popular_events(self, mock_get_events, mock_events_data):
        """Test popular events endpoint."""
        mock_get_events.return_value = mock_events_data
        
        response = client.get("/api/events/trending/popular?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify popular events response structure
        assert data["success"] is True
        assert "data" in data
        
        popular_data = data["data"]
        assert "events" in popular_data
        assert "algorithm_version" in popular_data
        assert "last_updated" in popular_data
        
        # Verify events have popularity scoring
        events = popular_data["events"]
        for event in events:
            assert "popularity_score" in event
            assert "trending_rank" in event
        
        # Verify events are sorted by popularity (descending)
        if len(events) > 1:
            assert events[0]["popularity_score"] >= events[1]["popularity_score"]
    
    @patch('app.services.backend_service.backend_service.get_events')
    def test_get_events_empty_result(self, mock_get_events):
        """Test events retrieval when no events exist."""
        mock_get_events.return_value = []
        
        response = client.get("/api/events/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["events"] == []
        assert data["data"]["total_count"] == 0
    
    def test_get_events_invalid_parameters(self):
        """Test events retrieval with invalid parameters."""
        # Test with invalid limit
        response = client.get("/api/events/?limit=0")
        
        assert response.status_code == 422
    
    def test_get_events_large_limit(self):
        """Test events retrieval with limit exceeding maximum."""
        response = client.get("/api/events/?limit=200")
        
        assert response.status_code == 422
    
    @patch('app.services.backend_service.backend_service.get_events')
    def test_get_events_with_date_filters(self, mock_get_events, mock_events_data):
        """Test events retrieval with date range filters."""
        mock_get_events.return_value = mock_events_data
        
        # Test with date range
        response = client.get("/api/events/?date_from=2024-01-01T00:00:00&date_to=2024-01-31T23:59:59")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return events within the date range
        assert data["success"] is True
        events = data["data"]["events"]
        assert len(events) == 2  # Both events are in January 2024
    
    @patch('app.services.backend_service.backend_service.get_events')
    def test_get_events_performance(self, mock_get_events, mock_events_data):
        """Test that events endpoint includes performance metadata."""
        mock_get_events.return_value = mock_events_data
        
        response = client.get("/api/events/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify cache information is included
        cache_info = data["data"]["cache_info"]
        assert "cached" in cache_info
        assert "cache_expires_at" in cache_info
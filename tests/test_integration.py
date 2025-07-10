# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import asyncio
from app.main import app

client = TestClient(app)


@pytest.mark.integration
class TestIntegration:
    """Integration test suite for BFF with external API."""
    
    def test_full_user_journey_mock(self):
        """Test complete user journey with mocked backend."""
        
        # Mock backend responses for a complete user journey
        with patch('app.services.backend_service.backend_service._make_request') as mock_request:
            
            # Setup mock responses for the journey
            def mock_response_side_effect(method, endpoint, **kwargs):
                if method == "POST" and "/api/auth/register" in endpoint:
                    return {
                        "token": "mock-jwt-token",
                        "email": "testuser@example.com",
                        "fullName": "Test User",
                        "balance": 1000.0,
                        "expiresAt": "2024-12-31T23:59:59Z"
                    }
                elif method == "POST" and "/api/auth/login" in endpoint:
                    return {
                        "token": "mock-jwt-token",
                        "email": "testuser@example.com",
                        "fullName": "Test User",
                        "balance": 1000.0,
                        "expiresAt": "2024-12-31T23:59:59Z"
                    }
                elif method == "GET" and "/api/events" in endpoint:
                    return [
                        {
                            "id": 1,
                            "name": "Test Event",
                            "teamA": "Team A",
                            "teamB": "Team B",
                            "teamAOdds": 2.0,
                            "teamBOdds": 1.8,
                            "eventDate": "2024-12-31T20:00:00Z",
                            "status": "Upcoming",
                            "canPlaceBets": True,
                            "timeUntilEvent": "7 days",
                            "totalBetsAmount": 0,
                            "totalBetsCount": 0,
                            "createdAt": "2024-01-01T00:00:00Z"
                        }
                    ]
                elif method == "POST" and "/api/bets/preview" in endpoint:
                    return {
                        "isValid": True,
                        "errors": [],
                        "amount": 100.0,
                        "currentOdds": 2.0,
                        "potentialWin": 200.0,
                        "potentialProfit": 100.0,
                        "currentBalance": 1000.0,
                        "balanceAfterBet": 900.0,
                        "eventName": "Test Event",
                        "selectedTeam": "Team A",
                        "message": "Bet preview is valid"
                    }
                elif method == "POST" and "/api/bets" in endpoint:
                    return {
                        "id": 1,
                        "eventId": 1,
                        "eventName": "Test Event",
                        "selectedTeam": "Team A",
                        "amount": 100.0,
                        "odds": 2.0,
                        "potentialWin": 200.0,
                        "status": "Active",
                        "createdAt": "2024-01-01T12:00:00Z",
                        "eventDate": "2024-12-31T20:00:00Z",
                        "canBeCancelled": True
                    }
                else:
                    return {}
            
            mock_request.side_effect = mock_response_side_effect
            
            # Step 1: Register user
            registration_data = {
                "email": "testuser@example.com",
                "password": "SecurePassword123!",
                "full_name": "Test User"
            }
            
            register_response = client.post("/api/auth/register", json=registration_data)
            assert register_response.status_code == 201
            
            registration_result = register_response.json()
            assert registration_result["success"] is True
            token = registration_result["data"]["token"]
            
            # Step 2: Login user
            login_data = {
                "email": "testuser@example.com",
                "password": "SecurePassword123!"
            }
            
            login_response = client.post("/api/auth/login", json=login_data)
            assert login_response.status_code == 200
            
            # Step 3: Get events
            auth_headers = {"Authorization": f"Bearer {token}"}
            events_response = client.get("/api/events/", headers=auth_headers)
            assert events_response.status_code == 200
            
            events_data = events_response.json()
            assert len(events_data["data"]["events"]) == 1
            event = events_data["data"]["events"][0]
            
            # Step 4: Preview bet
            bet_request = {
                "event_id": event["id"],
                "selected_team": "Team A",
                "amount": 100.0
            }
            
            preview_response = client.post("/api/bets/preview", 
                                         json=bet_request, 
                                         headers=auth_headers)
            assert preview_response.status_code == 200
            
            preview_data = preview_response.json()
            assert preview_data["success"] is True
            assert "risk_analysis" in preview_data["data"]  # BFF enhancement
            
            # Step 5: Create bet
            bet_response = client.post("/api/bets/", 
                                     json=bet_request, 
                                     headers=auth_headers)
            assert bet_response.status_code == 201
            
            bet_data = bet_response.json()
            assert bet_data["success"] is True
            assert "transaction_id" in bet_data["data"]  # BFF enhancement
            assert "confirmation_code" in bet_data["data"]  # BFF enhancement
    
    def test_error_handling_chain(self):
        """Test error handling across multiple endpoints."""
        
        # Test chain of operations that fail
        with patch('app.services.backend_service.backend_service._make_request') as mock_request:
            
            # Mock backend errors
            def mock_error_response(method, endpoint, **kwargs):
                if "/api/auth/login" in endpoint:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                return {}
            
            mock_request.side_effect = mock_error_response
            
            # Try to login with invalid credentials
            login_data = {
                "email": "invalid@example.com",
                "password": "wrongpassword"
            }
            
            login_response = client.post("/api/auth/login", json=login_data)
            assert login_response.status_code == 401
            
            # Verify error response structure
            error_data = login_response.json()
            assert error_data["success"] is False
            assert "timestamp" in error_data
            assert "path" in error_data
    
    def test_performance_and_caching(self):
        """Test performance optimizations and caching behavior."""
        
        with patch('app.services.backend_service.backend_service._make_request') as mock_request:
            
            # Mock events response
            mock_events = [
                {
                    "id": 1,
                    "name": "Cached Event",
                    "teamA": "Team A",
                    "teamB": "Team B",
                    "teamAOdds": 2.0,
                    "teamBOdds": 1.8,
                    "eventDate": "2024-12-31T20:00:00Z",
                    "status": "Upcoming",
                    "canPlaceBets": True,
                    "timeUntilEvent": "7 days",
                    "totalBetsAmount": 0,
                    "totalBetsCount": 0,
                    "createdAt": "2024-01-01T00:00:00Z"
                }
            ]
            
            mock_request.return_value = mock_events
            
            # First request - should hit backend
            response1 = client.get("/api/events/")
            assert response1.status_code == 200
            
            # Second request - should use cache (if caching is enabled)
            response2 = client.get("/api/events/")
            assert response2.status_code == 200
            
            # Verify both responses are identical
            assert response1.json() == response2.json()
            
            # Verify cache information is included
            cache_info = response1.json()["data"]["cache_info"]
            assert "cached" in cache_info
            assert "cache_expires_at" in cache_info
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        
        with patch('app.services.backend_service.backend_service._make_request') as mock_request:
            
            # Mock delayed response to simulate slow backend
            import time
            def slow_response(method, endpoint, **kwargs):
                time.sleep(0.1)  # Simulate network delay
                return [{"id": 1, "name": "Test Event"}]
            
            mock_request.side_effect = slow_response
            
            # Make multiple concurrent requests
            import threading
            results = []
            
            def make_request():
                response = client.get("/api/events/")
                results.append(response.status_code)
            
            # Start multiple threads
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Verify all requests succeeded
            assert all(status == 200 for status in results)
    
    def test_data_validation_and_transformation(self):
        """Test BFF data validation and transformation."""
        
        with patch('app.services.backend_service.backend_service._make_request') as mock_request:
            
            # Mock backend response with raw data
            mock_request.return_value = {
                "token": "raw-backend-token",
                "email": "USER@EXAMPLE.COM",  # Mixed case
                "fullName": "  Test User  ",  # Extra spaces
                "balance": 1000.0,
                "expiresAt": "2024-12-31T23:59:59Z"
            }
            
            # Test registration with data that needs normalization
            registration_data = {
                "email": "USER@EXAMPLE.COM",  # Should be normalized to lowercase
                "password": "SecurePassword123!",
                "full_name": "  Test User  "  # Should be trimmed
            }
            
            response = client.post("/api/auth/register", json=registration_data)
            assert response.status_code == 201
            
            # Verify BFF normalized the data before sending to backend
            mock_request.assert_called_once()
            call_data = mock_request.call_args[1]["data"]
            assert call_data["email"] == "user@example.com"  # Normalized
            assert call_data["fullName"] == "Test User"  # Trimmed
    
    def test_middleware_functionality(self):
        """Test middleware functionality including logging and rate limiting."""
        
        # Test request logging middleware
        response = client.get("/health")
        assert response.status_code in [200, 503]  # Might be degraded without real backend
        
        # Verify request ID header is added
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers
        
        # Test rate limiting (make multiple requests quickly)
        responses = []
        for _ in range(10):
            response = client.get("/health")
            responses.append(response.status_code)
        
        # Most should succeed, but rate limiting might kick in
        success_count = sum(1 for status in responses if status in [200, 503])
        assert success_count >= 8  # Allow for some rate limiting
    
    def test_comprehensive_error_scenarios(self):
        """Test various error scenarios and edge cases."""
        
        # Test malformed JSON
        response = client.post("/api/auth/login", 
                             data="invalid json", 
                             headers={"Content-Type": "application/json"})
        assert response.status_code == 422
        
        # Test missing required fields
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422
        
        # Test invalid content type
        response = client.post("/api/auth/login", 
                             data="email=test@example.com&password=test",
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert response.status_code == 422
        
        # Test very large payload
        large_payload = {
            "email": "test@example.com",
            "password": "test123",
            "full_name": "A" * 10000  # Very long name
        }
        response = client.post("/api/auth/register", json=large_payload)
        assert response.status_code == 422
    
    @pytest.mark.slow
    def test_backend_connectivity_real(self):
        """Test actual connectivity to external API (marked as slow)."""
        
        # This test actually tries to connect to the external API
        # It's marked as slow so it can be skipped in normal test runs
        
        # Test health check with real backend
        response = client.get("/health")
        
        # Should return either healthy or degraded
        assert response.status_code in [200, 503]
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
        assert "backend" in data
        
        # If backend is available, test a simple endpoint
        if data["status"] == "healthy":
            # Try to get events from real backend
            events_response = client.get("/api/events/")
            # This might fail due to authentication, but connection should work
            assert events_response.status_code in [200, 401, 403]


@pytest.mark.integration
class TestExternalAPIIntegration:
    """Tests specifically for external API integration."""
    
    def test_external_api_configuration(self):
        """Test that external API configuration is correctly set."""
        from app.core.config import settings
        
        # Verify external API URL is configured
        assert settings.backend_api_url == "https://api-kurax-demo-jos.uk"
        assert settings.backend_timeout == 30
    
    def test_api_endpoint_mapping(self):
        """Test that API endpoints are correctly mapped."""
        
        # Test that all required endpoints are accessible
        endpoints_to_test = [
            "/health",
            "/",
            "/api/stats"
        ]
        
        for endpoint in endpoints_to_test:
            response = client.get(endpoint)
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404
    
    def test_cors_configuration(self):
        """Test CORS configuration for frontend integration."""
        
        # Test preflight request
        response = client.options("/api/events/", 
                                headers={
                                    "Origin": "http://localhost:3000",
                                    "Access-Control-Request-Method": "GET"
                                })
        
        # Should handle OPTIONS request
        assert response.status_code in [200, 204]
    
    def test_request_validation_comprehensive(self):
        """Test comprehensive request validation."""
        
        test_cases = [
            # Auth endpoints
            ("/api/auth/register", "POST", {
                "email": "invalid",
                "password": "",
                "full_name": ""
            }),
            ("/api/auth/login", "POST", {
                "email": "",
                "password": ""
            }),
            
            # Events endpoints with invalid parameters
            ("/api/events/?limit=-1", "GET", None),
            ("/api/events/?limit=1000", "GET", None),
            
            # Bets endpoints (will fail on auth, but should validate structure)
            ("/api/bets/preview", "POST", {
                "event_id": -1,
                "selected_team": "",
                "amount": -100
            }),
        ]
        
        for endpoint, method, data in test_cases:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json=data)
            
            # Should return validation error, not server error
            assert response.status_code in [400, 422, 403]  # 403 for missing auth
# tests/test_health.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthCheck:
    """Test suite for health check endpoint."""
    
    def test_health_check_success(self):
        """Test basic health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code in [200, 503]  # Allow degraded status when backend is unavailable
        data = response.json()
        
        # Verify basic health response structure
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        assert "backend" in data
        
        # Backend health might be degraded if external API is not available
        assert data["status"] in ["healthy", "degraded"]
    
    def test_root_endpoint(self):
        """Test root endpoint information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify API information structure
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "endpoints" in data
        assert "status" in data
        
        # Verify expected endpoints are listed
        endpoints = data["endpoints"]
        assert "authentication" in endpoints
        assert "events" in endpoints
        assert "betting" in endpoints
        
        assert data["status"] == "operational"
    
    def test_api_stats_endpoint(self):
        """Test API statistics endpoint."""
        response = client.get("/api/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify stats structure
        assert "backend_service" in data
        assert "application" in data
        assert "generated_at" in data
        
        application_info = data["application"]
        assert "version" in application_info
        assert "debug_mode" in application_info
        assert "cache_enabled" in application_info
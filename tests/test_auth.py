# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)


class TestAuthentication:
    """Test suite for authentication endpoints."""
    
    @pytest.fixture
    def valid_registration_data(self):
        """Valid user registration data."""
        return {
            "email": "testuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User"
        }
    
    @pytest.fixture
    def valid_login_data(self):
        """Valid login credentials."""
        return {
            "email": "testuser@example.com",
            "password": "SecurePassword123!"
        }
    
    @pytest.fixture
    def mock_backend_auth_response(self):
        """Mock successful authentication response from backend."""
        return {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "email": "testuser@example.com",
            "fullName": "Test User",
            "balance": 1000.0,
            "expiresAt": "2024-12-31T23:59:59Z"
        }
    
    @patch('app.services.backend_service.backend_service.register_user')
    def test_register_user_success(self, mock_register, valid_registration_data, mock_backend_auth_response):
        """Test successful user registration."""
        mock_register.return_value = mock_backend_auth_response
        
        response = client.post("/api/auth/register", json=valid_registration_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify BFF response structure
        assert data["success"] is True
        assert data["message"] == "User registered successfully"
        assert "data" in data
        
        # Verify auth data
        auth_data = data["data"]
        assert "token" in auth_data
        assert "email" in auth_data
        assert "full_name" in auth_data
        assert "balance" in auth_data
        assert "expires_at" in auth_data
        assert "permissions" in auth_data
        
        # Verify backend service was called correctly
        mock_register.assert_called_once()
        call_args = mock_register.call_args[0][0]
        assert call_args["email"] == valid_registration_data["email"].lower()
        assert call_args["fullName"] == valid_registration_data["full_name"].strip()
    
    def test_register_user_invalid_email(self):
        """Test registration with invalid email."""
        invalid_data = {
            "email": "invalid-email",
            "password": "SecurePassword123!",
            "full_name": "Test User"
        }
        
        response = client.post("/api/auth/register", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "validation_errors" in data["details"]
    
    def test_register_user_weak_password(self):
        """Test registration with weak password."""
        invalid_data = {
            "email": "test@example.com",
            "password": "123",
            "full_name": "Test User"
        }
        
        response = client.post("/api/auth/register", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
    
    def test_register_user_invalid_name(self):
        """Test registration with invalid full name."""
        invalid_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "X"  # Too short
        }
        
        response = client.post("/api/auth/register", json=invalid_data)
        
        assert response.status_code == 422
    
    @patch('app.services.backend_service.backend_service.login_user')
    def test_login_user_success(self, mock_login, valid_login_data, mock_backend_auth_response):
        """Test successful user login."""
        mock_login.return_value = mock_backend_auth_response
        
        response = client.post("/api/auth/login", json=valid_login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify BFF response structure
        assert data["success"] is True
        assert data["message"] == "Login successful"
        assert "data" in data
        
        # Verify auth data structure
        auth_data = data["data"]
        assert "token" in auth_data
        assert "email" in auth_data
        assert "full_name" in auth_data
        assert "balance" in auth_data
        assert "permissions" in auth_data
        
        # Verify backend service was called
        mock_login.assert_called_once()
    
    def test_login_user_invalid_email(self):
        """Test login with invalid email format."""
        invalid_data = {
            "email": "invalid-email",
            "password": "password123"
        }
        
        response = client.post("/api/auth/login", json=invalid_data)
        
        assert response.status_code == 422
    
    def test_login_user_empty_password(self):
        """Test login with empty password."""
        invalid_data = {
            "email": "test@example.com",
            "password": ""
        }
        
        response = client.post("/api/auth/login", json=invalid_data)
        
        assert response.status_code == 422
    
    @patch('app.services.backend_service.backend_service.get_user_profile')
    def test_get_user_profile_success(self, mock_profile):
        """Test successful profile retrieval."""
        mock_profile.return_value = {
            "id": 1,
            "email": "test@example.com",
            "fullName": "Test User",
            "balance": 1000.0,
            "createdAt": "2024-01-01T00:00:00Z",
            "totalBets": 5,
            "totalBetAmount": 500.0
        }
        
        headers = {"Authorization": "Bearer valid-token"}
        response = client.get("/api/auth/profile", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        
        # Verify profile data is enriched by BFF
        profile_data = data["data"]
        assert "profile_completion" in profile_data
        assert "last_activity" in profile_data
        assert "notification_count" in profile_data
    
    def test_get_user_profile_no_token(self):
        """Test profile access without authentication token."""
        response = client.get("/api/auth/profile")
        
        assert response.status_code == 403  # HTTPBearer returns 403 for missing auth
    
    def test_get_user_profile_invalid_token(self):
        """Test profile access with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        
        with patch('app.services.backend_service.backend_service.get_user_profile') as mock_profile:
            mock_profile.side_effect = Exception("Invalid token")
            
            response = client.get("/api/auth/profile", headers=headers)
            
            assert response.status_code == 500
    
    def test_logout_user_success(self):
        """Test successful user logout."""
        headers = {"Authorization": "Bearer valid-token"}
        response = client.post("/api/auth/logout", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "Logout successful"
        assert "data" in data
        assert "logged_out_at" in data["data"]
    
    def test_logout_user_no_token(self):
        """Test logout without authentication token."""
        response = client.post("/api/auth/logout")
        
        assert response.status_code == 403
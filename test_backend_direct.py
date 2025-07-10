#!/usr/bin/env python3
"""
Test script to directly test the backend API to identify issues.
"""

import asyncio
import httpx
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BACKEND_BASE_URL = "https://api-kurax-demo-jos.uk"

class BackendDirectTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def test_backend_health(self):
        """Test backend health endpoint"""
        logger.info("=== Testing Backend Health Endpoint ===")
        
        try:
            response = await self.client.get(f"{BACKEND_BASE_URL}/health")
            
            logger.info(f"Backend health status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Backend health check passed")
                logger.info(f"Backend response: {json.dumps(data, indent=2)}")
                return True
            else:
                logger.error(f"❌ Backend health check failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backend health check failed: {str(e)}")
            return False
    
    async def test_backend_profile_with_fake_token(self):
        """Test backend profile endpoint with fake token"""
        logger.info("\n=== Testing Backend Profile with Fake Token ===")
        
        headers = {
            "Authorization": "Bearer fake_token_12345",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.get(
                f"{BACKEND_BASE_URL}/api/auth/profile",
                headers=headers
            )
            
            logger.info(f"Backend profile status: {response.status_code}")
            logger.info(f"Backend profile response: {response.text}")
            
            if response.status_code == 401:
                logger.info("✅ Expected 401 from backend for fake token")
                return True
            else:
                logger.error(f"❌ Unexpected status code from backend: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backend profile request failed: {str(e)}")
            return False
    
    async def test_backend_register(self):
        """Test backend register endpoint"""
        logger.info("\n=== Testing Backend Register Endpoint ===")
        
        register_data = {
            "email": "test@example.com",
            "password": "TestPass123",
            "fullName": "Test User"
        }
        
        try:
            response = await self.client.post(
                f"{BACKEND_BASE_URL}/api/auth/register",
                json=register_data
            )
            
            logger.info(f"Backend register status: {response.status_code}")
            logger.info(f"Backend register response: {response.text}")
            
            if response.status_code in [200, 201, 409]:  # 409 for duplicate email
                logger.info("✅ Backend register endpoint is working")
                return True
            else:
                logger.error(f"❌ Backend register failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backend register request failed: {str(e)}")
            return False
    
    async def test_backend_login(self):
        """Test backend login endpoint"""
        logger.info("\n=== Testing Backend Login Endpoint ===")
        
        login_data = {
            "email": "test@example.com",
            "password": "TestPass123"
        }
        
        try:
            response = await self.client.post(
                f"{BACKEND_BASE_URL}/api/auth/login",
                json=login_data
            )
            
            logger.info(f"Backend login status: {response.status_code}")
            logger.info(f"Backend login response: {response.text}")
            
            if response.status_code in [200, 401]:  # 401 for invalid credentials
                logger.info("✅ Backend login endpoint is working")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("data", {}).get("token"):
                        token = data["data"]["token"]
                        logger.info(f"✅ Got token from backend: {token[:20]}...")
                        return token
                
                return True
            else:
                logger.error(f"❌ Backend login failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backend login request failed: {str(e)}")
            return False
    
    async def test_backend_profile_with_real_token(self, token):
        """Test backend profile endpoint with real token"""
        if not token:
            logger.error("❌ No token provided")
            return False
            
        logger.info(f"\n=== Testing Backend Profile with Real Token ===")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.get(
                f"{BACKEND_BASE_URL}/api/auth/profile",
                headers=headers
            )
            
            logger.info(f"Backend profile status: {response.status_code}")
            logger.info(f"Backend profile response: {response.text}")
            
            if response.status_code == 200:
                logger.info("✅ Backend profile endpoint working with real token")
                return True
            else:
                logger.error(f"❌ Backend profile failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backend profile request failed: {str(e)}")
            return False
    
    async def test_backend_connectivity(self):
        """Test general backend connectivity"""
        logger.info("\n=== Testing Backend Connectivity ===")
        
        try:
            # Test with a simple GET request
            response = await self.client.get(f"{BACKEND_BASE_URL}/")
            
            logger.info(f"Backend root status: {response.status_code}")
            logger.info(f"Backend root response: {response.text}")
            
            if response.status_code in [200, 404]:  # 404 is fine, shows server is responding
                logger.info("✅ Backend is reachable")
                return True
            else:
                logger.error(f"❌ Backend connectivity issue: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backend connectivity failed: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all backend tests"""
        logger.info("🔍 Starting Backend Direct Tests")
        
        results = {}
        
        # Test 1: Basic connectivity
        results["connectivity"] = await self.test_backend_connectivity()
        
        # Test 2: Health endpoint
        results["health"] = await self.test_backend_health()
        
        # Test 3: Profile with fake token
        results["profile_fake"] = await self.test_backend_profile_with_fake_token()
        
        # Test 4: Register endpoint
        results["register"] = await self.test_backend_register()
        
        # Test 5: Login endpoint
        token = await self.test_backend_login()
        results["login"] = token is not None
        
        # Test 6: Profile with real token
        if token:
            results["profile_real"] = await self.test_backend_profile_with_real_token(token)
        
        await self.client.aclose()
        
        # Summary
        logger.info("\n=== BACKEND TEST SUMMARY ===")
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
        
        return results

async def main():
    tester = BackendDirectTester()
    results = await tester.run_all_tests()
    
    if not all(results.values()):
        logger.error("❌ Some backend tests failed")
    else:
        logger.info("✅ All backend tests passed")

if __name__ == "__main__":
    asyncio.run(main())
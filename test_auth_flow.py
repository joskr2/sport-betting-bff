#!/usr/bin/env python3
"""
Test script to simulate the authentication flow and identify issues.
"""

import asyncio
import httpx
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BFF_BASE_URL = "https://hf3bbankw5wc2uovwju4m6zvku0zuozj.lambda-url.us-east-2.on.aws"

class AuthFlowTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def test_with_fake_token(self):
        """Test profile endpoint with a fake token to see error handling"""
        logger.info("=== Testing Profile Endpoint with Fake Token ===")
        
        fake_token = "fake_token_12345"
        headers = {
            "Authorization": f"Bearer {fake_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.get(
                f"{BFF_BASE_URL}/api/auth/profile",
                headers=headers
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response body: {response.text}")
            
            if response.status_code == 401:
                logger.info("✅ Expected 401 for fake token")
            elif response.status_code == 500:
                logger.error("❌ Got 500 error - this indicates a code issue")
            else:
                logger.warning(f"Unexpected status code: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
    
    async def test_with_no_token(self):
        """Test profile endpoint with no token"""
        logger.info("\n=== Testing Profile Endpoint with No Token ===")
        
        try:
            response = await self.client.get(
                f"{BFF_BASE_URL}/api/auth/profile"
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text}")
            
            if response.status_code == 401:
                logger.info("✅ Expected 401 for no token")
            else:
                logger.warning(f"Unexpected status code: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
    
    async def test_with_invalid_token_format(self):
        """Test profile endpoint with invalid token format"""
        logger.info("\n=== Testing Profile Endpoint with Invalid Token Format ===")
        
        test_cases = [
            {"Authorization": "InvalidFormat", "description": "No Bearer prefix"},
            {"Authorization": "bearer fake_token", "description": "Lowercase bearer"},
            {"Authorization": "Token fake_token", "description": "Token prefix"},
            {"Authorization": "Bearer", "description": "Bearer without token"},
            {"Authorization": "Bearer ", "description": "Bearer with space only"},
        ]
        
        for test_case in test_cases:
            logger.info(f"Testing: {test_case['description']}")
            
            try:
                response = await self.client.get(
                    f"{BFF_BASE_URL}/api/auth/profile",
                    headers=test_case
                )
                
                logger.info(f"  Status: {response.status_code}")
                logger.info(f"  Response: {response.text}")
                
                if response.status_code == 401:
                    logger.info("  ✅ Expected 401 for invalid format")
                else:
                    logger.warning(f"  Unexpected status code: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"  Request failed: {str(e)}")
    
    async def test_health_endpoint(self):
        """Test health endpoint to verify BFF is working"""
        logger.info("\n=== Testing Health Endpoint ===")
        
        try:
            response = await self.client.get(f"{BFF_BASE_URL}/health")
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Health check passed")
                logger.info(f"Backend status: {data.get('backend', {}).get('healthy', 'Unknown')}")
                return True
            else:
                logger.error(f"❌ Health check failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}")
            return False
    
    async def test_register_endpoint(self):
        """Test register endpoint to get a real token"""
        logger.info("\n=== Testing Register Endpoint ===")
        
        # Generate a unique email for testing
        test_email = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        
        register_data = {
            "email": test_email,
            "password": "TestPass123",
            "full_name": "Test User"
        }
        
        try:
            response = await self.client.post(
                f"{BFF_BASE_URL}/api/auth/register",
                json=register_data
            )
            
            logger.info(f"Register response status: {response.status_code}")
            logger.info(f"Register response: {response.text}")
            
            if response.status_code == 201:
                data = response.json()
                if data.get("success") and data.get("data", {}).get("token"):
                    token = data["data"]["token"]
                    logger.info(f"✅ Got token from registration: {token[:20]}...")
                    return token
                else:
                    logger.error("❌ Registration successful but no token")
                    return None
            else:
                logger.error(f"❌ Registration failed with status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Registration failed: {str(e)}")
            return None
    
    async def test_profile_with_real_token(self, token):
        """Test profile endpoint with a real token"""
        if not token:
            logger.error("❌ No token provided")
            return False
            
        logger.info(f"\n=== Testing Profile Endpoint with Real Token ===")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.get(
                f"{BFF_BASE_URL}/api/auth/profile",
                headers=headers
            )
            
            logger.info(f"Profile response status: {response.status_code}")
            logger.info(f"Profile response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Profile retrieved successfully")
                return True
            else:
                logger.error(f"❌ Profile request failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Profile request failed: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("🧪 Starting Authentication Flow Tests")
        
        # Test 1: Health check
        health_ok = await self.test_health_endpoint()
        if not health_ok:
            logger.error("❌ Health check failed, stopping tests")
            return
        
        # Test 2: Test with no token
        await self.test_with_no_token()
        
        # Test 3: Test with invalid token formats
        await self.test_with_invalid_token_format()
        
        # Test 4: Test with fake token
        await self.test_with_fake_token()
        
        # Test 5: Try to register and get a real token
        token = await self.test_register_endpoint()
        
        # Test 6: Test profile with real token
        if token:
            await self.test_profile_with_real_token(token)
        
        await self.client.aclose()
        logger.info("\n✅ All authentication flow tests completed")

async def main():
    tester = AuthFlowTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
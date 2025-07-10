#!/usr/bin/env python3
"""
Comprehensive test script for the profile endpoint.
This will help identify the exact issue with the 500 error.
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
BACKEND_BASE_URL = "https://api-kurax-demo-jos.uk"

# Test credentials (you'll need to replace these with valid ones)
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

class ProfileEndpointTester:
    def __init__(self):
        self.auth_token = None
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def test_login_and_get_token(self):
        """Test login and get a valid token"""
        logger.info("=== Testing Login ===")
        
        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        try:
            response = await self.client.post(
                f"{BFF_BASE_URL}/api/auth/login",
                json=login_data
            )
            
            logger.info(f"Login response status: {response.status_code}")
            logger.info(f"Login response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Login response data: {json.dumps(data, indent=2)}")
                
                if data.get("success") and data.get("data", {}).get("token"):
                    self.auth_token = data["data"]["token"]
                    logger.info(f"✅ Successfully got token: {self.auth_token[:20]}...")
                    return True
                else:
                    logger.error("❌ Login successful but no token in response")
                    return False
            else:
                logger.error(f"❌ Login failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login request failed: {str(e)}")
            return False
    
    async def test_profile_endpoint_with_token(self):
        """Test profile endpoint with the obtained token"""
        if not self.auth_token:
            logger.error("❌ No auth token available")
            return False
            
        logger.info("=== Testing Profile Endpoint ===")
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.get(
                f"{BFF_BASE_URL}/api/auth/profile",
                headers=headers
            )
            
            logger.info(f"Profile response status: {response.status_code}")
            logger.info(f"Profile response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Profile response data: {json.dumps(data, indent=2)}")
                return True
            else:
                logger.error(f"❌ Profile request failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Profile request failed: {str(e)}")
            return False
    
    async def test_direct_backend_call(self):
        """Test calling the backend API directly"""
        if not self.auth_token:
            logger.error("❌ No auth token available")
            return False
            
        logger.info("=== Testing Direct Backend Call ===")
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.get(
                f"{BACKEND_BASE_URL}/api/auth/profile",
                headers=headers
            )
            
            logger.info(f"Backend response status: {response.status_code}")
            logger.info(f"Backend response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Backend response data: {json.dumps(data, indent=2)}")
                return True
            else:
                logger.error(f"❌ Backend request failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backend request failed: {str(e)}")
            return False
    
    async def test_different_auth_header_formats(self):
        """Test different Authorization header formats"""
        if not self.auth_token:
            logger.error("❌ No auth token available")
            return False
            
        logger.info("=== Testing Different Auth Header Formats ===")
        
        test_cases = [
            {"Authorization": f"Bearer {self.auth_token}", "description": "Standard Bearer format"},
            {"Authorization": f"bearer {self.auth_token}", "description": "Lowercase bearer"},
            {"Authorization": self.auth_token, "description": "Token only"},
            {"Authorization": f"Token {self.auth_token}", "description": "Token prefix"},
        ]
        
        for i, test_case in enumerate(test_cases):
            logger.info(f"Test case {i+1}: {test_case['description']}")
            
            try:
                response = await self.client.get(
                    f"{BFF_BASE_URL}/api/auth/profile",
                    headers=test_case
                )
                
                logger.info(f"  Status: {response.status_code}")
                if response.status_code != 200:
                    logger.info(f"  Response: {response.text}")
                    
            except Exception as e:
                logger.error(f"  Error: {str(e)}")
    
    async def test_health_endpoint(self):
        """Test the health endpoint to verify BFF is working"""
        logger.info("=== Testing Health Endpoint ===")
        
        try:
            response = await self.client.get(f"{BFF_BASE_URL}/health")
            
            logger.info(f"Health response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Health check passed: {json.dumps(data, indent=2)}")
                return True
            else:
                logger.error(f"❌ Health check failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        logger.info("🚀 Starting comprehensive profile endpoint tests")
        logger.info(f"BFF URL: {BFF_BASE_URL}")
        logger.info(f"Backend URL: {BACKEND_BASE_URL}")
        logger.info(f"Test time: {datetime.now()}")
        
        results = {}
        
        # Test 1: Health check
        results["health"] = await self.test_health_endpoint()
        
        # Test 2: Login and get token
        results["login"] = await self.test_login_and_get_token()
        
        if results["login"]:
            # Test 3: Profile endpoint
            results["profile"] = await self.test_profile_endpoint_with_token()
            
            # Test 4: Direct backend call
            results["backend"] = await self.test_direct_backend_call()
            
            # Test 5: Different auth header formats
            await self.test_different_auth_header_formats()
        
        # Summary
        logger.info("\n=== TEST SUMMARY ===")
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
        
        await self.client.aclose()
        
        return results

async def main():
    """Main test function"""
    tester = ProfileEndpointTester()
    results = await tester.run_all_tests()
    
    # Exit with error code if any tests failed
    if not all(results.values()):
        exit(1)
    
    logger.info("🎉 All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
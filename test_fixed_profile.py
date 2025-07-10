#!/usr/bin/env python3
"""
Test script to verify the fixed profile endpoint is working correctly.
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

class FixedProfileTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def test_complete_auth_flow(self):
        """Test the complete authentication flow"""
        logger.info("🧪 Testing Complete Authentication Flow")
        
        # Step 1: Register a new user
        logger.info("=== Step 1: Register New User ===")
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
            
            logger.info(f"Register status: {response.status_code}")
            
            if response.status_code == 201:
                data = response.json()
                logger.info("✅ Registration successful")
                
                if data.get("success") and data.get("data", {}).get("token"):
                    token = data["data"]["token"]
                    logger.info(f"Got token: {token[:20]}...")
                else:
                    logger.error("❌ No token in registration response")
                    return False
            else:
                logger.error(f"❌ Registration failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Registration error: {str(e)}")
            return False
        
        # Step 2: Test profile endpoint with the token
        logger.info("\n=== Step 2: Test Profile Endpoint ===")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.get(
                f"{BFF_BASE_URL}/api/auth/profile",
                headers=headers
            )
            
            logger.info(f"Profile status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Profile retrieved successfully")
                logger.info(f"Profile data: {json.dumps(data, indent=2)}")
                
                # Verify the profile data structure
                if self._validate_profile_response(data):
                    logger.info("✅ Profile data structure is valid")
                    return True
                else:
                    logger.error("❌ Profile data structure is invalid")
                    return False
            else:
                logger.error(f"❌ Profile request failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Profile request error: {str(e)}")
            return False
    
    def _validate_profile_response(self, response_data):
        """Validate the profile response structure"""
        try:
            # Check top-level structure
            if not response_data.get("success"):
                logger.error("Response success is not true")
                return False
            
            if not response_data.get("data"):
                logger.error("Response data is missing")
                return False
            
            data = response_data["data"]
            
            # Check required fields
            required_fields = ["email", "fullName", "balance", "profile_completion"]
            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Check data types
            if not isinstance(data["balance"], (int, float)):
                logger.error("Balance is not a number")
                return False
            
            if not isinstance(data["profile_completion"], (int, float)):
                logger.error("Profile completion is not a number")
                return False
            
            logger.info("Profile response validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Error validating profile response: {str(e)}")
            return False
    
    async def test_profile_with_invalid_token(self):
        """Test profile endpoint with invalid token"""
        logger.info("\n=== Testing Profile with Invalid Token ===")
        
        headers = {
            "Authorization": "Bearer invalid_token_12345",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.get(
                f"{BFF_BASE_URL}/api/auth/profile",
                headers=headers
            )
            
            logger.info(f"Profile status with invalid token: {response.status_code}")
            
            if response.status_code == 401:
                logger.info("✅ Correctly rejected invalid token")
                return True
            else:
                logger.error(f"❌ Unexpected status for invalid token: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing invalid token: {str(e)}")
            return False
    
    async def test_profile_with_no_token(self):
        """Test profile endpoint with no token"""
        logger.info("\n=== Testing Profile with No Token ===")
        
        try:
            response = await self.client.get(
                f"{BFF_BASE_URL}/api/auth/profile"
            )
            
            logger.info(f"Profile status with no token: {response.status_code}")
            
            if response.status_code == 401:
                logger.info("✅ Correctly rejected missing token")
                return True
            else:
                logger.error(f"❌ Unexpected status for missing token: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing missing token: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting Fixed Profile Endpoint Tests")
        
        results = {}
        
        # Test 1: Complete auth flow
        results["complete_flow"] = await self.test_complete_auth_flow()
        
        # Test 2: Invalid token
        results["invalid_token"] = await self.test_profile_with_invalid_token()
        
        # Test 3: No token
        results["no_token"] = await self.test_profile_with_no_token()
        
        await self.client.aclose()
        
        # Summary
        logger.info("\n=== TEST SUMMARY ===")
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
        
        if all(results.values()):
            logger.info("🎉 All tests passed! Profile endpoint is working correctly.")
        else:
            logger.error("❌ Some tests failed. Profile endpoint needs more work.")
        
        return results

async def main():
    tester = FixedProfileTester()
    results = await tester.run_all_tests()
    
    if not all(results.values()):
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
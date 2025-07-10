#!/usr/bin/env python3
"""
Debug script to test profile endpoint components locally.
"""

import asyncio
import sys
import os

# Add the app directory to path
sys.path.insert(0, '/Users/josuepatricio/Desktop/bff-fastapi')

from app.services.backend_service import backend_service
from app.core.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProfileDebugger:
    def __init__(self):
        self.sample_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    
    def test_token_extraction(self):
        """Test token extraction logic"""
        logger.info("=== Testing Token Extraction ===")
        
        test_cases = [
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "",
            None
        ]
        
        for i, auth_header in enumerate(test_cases):
            logger.info(f"Test case {i+1}: {auth_header}")
            
            try:
                if not auth_header:
                    logger.info("  ❌ No Authorization header")
                    continue
                    
                if not auth_header.startswith("Bearer "):
                    logger.info(f"  ❌ Invalid format: {auth_header[:20]}...")
                    continue
                    
                token = auth_header.split(" ", 1)[1]
                logger.info(f"  ✅ Extracted token: {token[:20]}...")
                
            except Exception as e:
                logger.error(f"  ❌ Error: {str(e)}")
    
    def test_backend_service_headers(self):
        """Test how backend service creates headers"""
        logger.info("\n=== Testing Backend Service Headers ===")
        
        test_tokens = [
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "",
            None
        ]
        
        for i, token in enumerate(test_tokens):
            logger.info(f"Test case {i+1}: Token = {token}")
            
            try:
                if token:
                    headers = {"Authorization": f"Bearer {token}"}
                    logger.info(f"  ✅ Created headers: {headers}")
                else:
                    logger.info("  ❌ No token provided")
                    
            except Exception as e:
                logger.error(f"  ❌ Error creating headers: {str(e)}")
    
    def test_profile_completion_function(self):
        """Test the profile completion calculation"""
        logger.info("\n=== Testing Profile Completion Function ===")
        
        # Import the function
        from app.api.auth import _calculate_profile_completion
        
        test_profiles = [
            {"email": "test@example.com", "fullName": "Test User", "balance": 100.0},
            {"email": "test@example.com", "fullName": "Test User", "balance": 100.0, "phone": "123-456-7890"},
            {"email": "test@example.com"},
            {},
            None
        ]
        
        for i, profile in enumerate(test_profiles):
            logger.info(f"Test case {i+1}: {profile}")
            
            try:
                if profile is None:
                    logger.info("  ❌ None profile data")
                    continue
                    
                completion = _calculate_profile_completion(profile)
                logger.info(f"  ✅ Profile completion: {completion}%")
                
            except Exception as e:
                logger.error(f"  ❌ Error calculating completion: {str(e)}")
    
    async def test_backend_service_config(self):
        """Test backend service configuration"""
        logger.info("\n=== Testing Backend Service Configuration ===")
        
        logger.info(f"Backend URL: {settings.backend_api_url}")
        logger.info(f"Backend timeout: {settings.backend_timeout}")
        logger.info(f"Cache enabled: {settings.enable_cache}")
        logger.info(f"Cache TTL: {settings.cache_ttl_seconds}")
        
        try:
            # Test health check
            logger.info("Testing backend health check...")
            health_response = await backend_service.health_check()
            logger.info(f"✅ Health check response: {health_response}")
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}")
    
    def test_data_response_structure(self):
        """Test DataResponse structure"""
        logger.info("\n=== Testing DataResponse Structure ===")
        
        from app.models.schemas import DataResponse
        
        test_data = {
            "email": "test@example.com",
            "fullName": "Test User",
            "balance": 100.0,
            "profile_completion": 75.5,
            "last_activity": "2024-01-01T12:00:00Z",
            "notification_count": 0
        }
        
        try:
            response = DataResponse(
                message="Profile retrieved successfully",
                data=test_data
            )
            
            logger.info(f"✅ DataResponse created: {response.model_dump()}")
            
        except Exception as e:
            logger.error(f"❌ Error creating DataResponse: {str(e)}")
    
    async def run_all_tests(self):
        """Run all debug tests"""
        logger.info("🔍 Starting Profile Endpoint Debug Tests")
        
        # Test 1: Token extraction
        self.test_token_extraction()
        
        # Test 2: Backend service headers
        self.test_backend_service_headers()
        
        # Test 3: Profile completion function
        self.test_profile_completion_function()
        
        # Test 4: Backend service configuration
        await self.test_backend_service_config()
        
        # Test 5: DataResponse structure
        self.test_data_response_structure()
        
        logger.info("\n✅ Debug tests completed")

async def main():
    """Main debug function"""
    debugger = ProfileDebugger()
    await debugger.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
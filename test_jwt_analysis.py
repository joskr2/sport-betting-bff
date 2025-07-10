#!/usr/bin/env python3
"""
Test script to analyze JWT tokens and identify issues.
"""

import asyncio
import httpx
import json
import base64
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BACKEND_BASE_URL = "https://api-kurax-demo-jos.uk"

class JWTAnalyzer:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def decode_jwt_payload(self, token: str) -> Dict[str, Any]:
        """Decode JWT payload (without verification)"""
        try:
            # JWT has 3 parts separated by dots
            parts = token.split('.')
            if len(parts) != 3:
                logger.error(f"Invalid JWT format: {len(parts)} parts")
                return {}
            
            # Decode the payload (second part)
            payload_encoded = parts[1]
            
            # Add padding if needed
            padding = '=' * (4 - len(payload_encoded) % 4)
            payload_encoded += padding
            
            # Base64 decode
            payload_bytes = base64.b64decode(payload_encoded)
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            return payload
            
        except Exception as e:
            logger.error(f"Error decoding JWT: {str(e)}")
            return {}
    
    def analyze_jwt_token(self, token: str, description: str):
        """Analyze a JWT token"""
        logger.info(f"\n=== Analyzing JWT Token: {description} ===")
        logger.info(f"Token length: {len(token)}")
        logger.info(f"Token preview: {token[:50]}...")
        
        payload = self.decode_jwt_payload(token)
        if payload:
            logger.info("JWT Payload:")
            for key, value in payload.items():
                logger.info(f"  {key}: {value}")
        else:
            logger.error("Failed to decode JWT payload")
    
    async def get_token_from_backend(self) -> str:
        """Get a fresh token from the backend"""
        logger.info("=== Getting Fresh Token from Backend ===")
        
        # First register a unique user
        import time
        email = f"test_{int(time.time())}@example.com"
        
        register_data = {
            "email": email,
            "password": "TestPass123",
            "fullName": "Test User"
        }
        
        try:
            # Register user
            response = await self.client.post(
                f"{BACKEND_BASE_URL}/api/auth/register",
                json=register_data
            )
            
            if response.status_code == 201:
                data = response.json()
                
                # Handle nested response format
                if "value" in data and isinstance(data["value"], dict):
                    # Backend sometimes returns nested format
                    token_data = data["value"]
                else:
                    token_data = data
                
                if token_data.get("success") and token_data.get("data", {}).get("token"):
                    token = token_data["data"]["token"]
                    logger.info(f"✅ Got token from registration: {token[:20]}...")
                    return token
                else:
                    logger.error(f"❌ No token in registration response: {data}")
                    return None
            else:
                logger.error(f"❌ Registration failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting token: {str(e)}")
            return None
    
    async def test_token_with_backend_profile(self, token: str):
        """Test token with backend profile endpoint"""
        logger.info(f"\n=== Testing Token with Backend Profile ===")
        
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
                logger.info("✅ Token works with backend profile")
                return True
            else:
                logger.error(f"❌ Token failed with backend profile: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing token: {str(e)}")
            return False
    
    async def test_token_variations(self, token: str):
        """Test different variations of the token"""
        logger.info(f"\n=== Testing Token Variations ===")
        
        variations = [
            {"token": token, "desc": "Original token"},
            {"token": token.strip(), "desc": "Stripped token"},
            {"token": token.replace(" ", ""), "desc": "No spaces token"},
        ]
        
        for variation in variations:
            test_token = variation["token"]
            desc = variation["desc"]
            
            logger.info(f"Testing: {desc}")
            
            headers = {
                "Authorization": f"Bearer {test_token}",
                "Content-Type": "application/json"
            }
            
            try:
                response = await self.client.get(
                    f"{BACKEND_BASE_URL}/api/auth/profile",
                    headers=headers
                )
                
                logger.info(f"  Status: {response.status_code}")
                if response.status_code != 200:
                    logger.info(f"  Response: {response.text}")
                    
            except Exception as e:
                logger.error(f"  Error: {str(e)}")
    
    async def run_analysis(self):
        """Run complete JWT analysis"""
        logger.info("🔍 Starting JWT Token Analysis")
        
        # Get a fresh token
        token = await self.get_token_from_backend()
        if not token:
            logger.error("❌ Could not get token, stopping analysis")
            return
        
        # Analyze the token
        self.analyze_jwt_token(token, "Fresh Backend Token")
        
        # Test the token with backend profile
        await self.test_token_with_backend_profile(token)
        
        # Test token variations
        await self.test_token_variations(token)
        
        await self.client.aclose()
        logger.info("\n✅ JWT Analysis Complete")

async def main():
    analyzer = JWTAnalyzer()
    await analyzer.run_analysis()

if __name__ == "__main__":
    asyncio.run(main())
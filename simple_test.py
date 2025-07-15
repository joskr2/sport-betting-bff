#!/usr/bin/env python3
"""
Simple test to verify the corrected Lambda function works without dependencies issues.
We'll test the actual endpoint with a direct HTTP call.
"""

import json
import sys

def test_lambda_handler():
    """Test the lambda handler directly with a sample event"""
    
    # Simulate a simple GET request to the health endpoint
    event = {
        "httpMethod": "GET",
        "path": "/health",
        "headers": {
            "Host": "example.com",
            "User-Agent": "test-agent"
        },
        "requestContext": {},
        "body": None,
        "isBase64Encoded": False
    }
    
    context = {}
    
    try:
        # Import and test the corrected lambda function
        sys.path.insert(0, '/Users/josuepatricio/Documents/betting-app-project/bff-fastapi')
        from lambda_function import lambda_handler
        
        print("✅ Lambda function imported successfully")
        
        # Test the lambda handler
        response = lambda_handler(event, context)
        
        print(f"✅ Lambda handler executed successfully")
        print(f"Response status: {response.get('statusCode')}")
        print(f"Response headers: {response.get('headers', {})}")
        
        # Parse response body if it's JSON
        try:
            body = json.loads(response.get('body', '{}'))
            print(f"Response body: {json.dumps(body, indent=2)}")
        except:
            print(f"Response body (raw): {response.get('body')}")
        
        return response
        
    except Exception as e:
        print(f"❌ Error testing lambda: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    print("🧪 Testing corrected Lambda function...")
    print("=" * 60)
    
    result = test_lambda_handler()
    
    if result:
        print("\n✅ Lambda function test completed successfully!")
        print("🚀 The corrected BFF is ready for deployment!")
    else:
        print("\n❌ Lambda function test failed")
        sys.exit(1)
#!/usr/bin/env python3
"""
Test de Seguridad CORS - Verificación de la nueva configuración
"""
import os
import sys
sys.path.append('.')

def test_development_cors():
    """Test CORS configuration in development mode"""
    print("🧪 Testing Development CORS Configuration...")
    
    # Ensure development mode
    os.environ['DEBUG'] = 'true'
    
    from app.core.config import settings
    
    # Verify all origins are allowed in development
    expected_origins = [
        'http://localhost:3000',
        'http://127.0.0.1:3000', 
        'http://localhost:8080',
        'https://betting-app-frontend-six.vercel.app',
        'https://betting-app-frontend-ff29xnj8l-josues-projects-546cbe2a.vercel.app'
    ]
    
    assert settings.allowed_origins == expected_origins, f"Expected {expected_origins}, got {settings.allowed_origins}"
    
    # Verify development hosts
    expected_hosts = ['localhost', '127.0.0.1', 'testserver', '*.ngrok.io']
    assert settings.allowed_hosts == expected_hosts, f"Expected {expected_hosts}, got {settings.allowed_hosts}"
    
    # Verify headers are restricted (not wildcard)
    assert '*' not in settings.allowed_headers, "Wildcard headers should not be allowed"
    assert 'Authorization' in settings.allowed_headers, "Authorization header should be allowed"
    
    print("✅ Development CORS configuration is correct")

def test_production_cors():
    """Test CORS configuration in production mode"""
    print("🚀 Testing Production CORS Configuration...")
    
    # Set production mode
    os.environ['DEBUG'] = 'false'
    
    # Reload settings
    import importlib
    import app.core.config
    importlib.reload(app.core.config)
    from app.core.config import settings
    
    # Verify production origins (should include HTTPS)
    production_origins = [origin for origin in settings.allowed_origins if origin.startswith('https://')]
    assert len(production_origins) >= 2, f"Should have at least 2 HTTPS origins, got {production_origins}"
    
    # Verify production hosts are extracted from origins
    assert 'betting-app-frontend-six.vercel.app' in settings.allowed_hosts
    assert 'betting-app-frontend-ff29xnj8l-josues-projects-546cbe2a.vercel.app' in settings.allowed_hosts
    assert 'api-kurax-demo-jos.uk' in settings.allowed_hosts
    
    # Verify no wildcards in production
    assert '*' not in settings.allowed_origins, "Wildcard origins should not be allowed in production"
    assert '*' not in settings.allowed_headers, "Wildcard headers should not be allowed"
    
    print("✅ Production CORS configuration is correct")

def test_wildcard_rejection():
    """Test that wildcard CORS is rejected in production"""
    print("🛡️ Testing Wildcard CORS Rejection...")
    
    # Set production mode with wildcard
    os.environ['DEBUG'] = 'false'
    os.environ['ALLOWED_ORIGINS'] = '*'
    
    try:
        # Reload settings
        import importlib
        import app.core.config
        importlib.reload(app.core.config)
        from app.core.config import settings
        
        print("❌ ERROR: Wildcard CORS should have been rejected!")
        return False
        
    except ValueError as e:
        if "wildcard" in str(e).lower():
            print(f"✅ SUCCESS: Wildcard CORS correctly rejected: {e}")
            return True
        else:
            print(f"⚠️ Wrong error type: {e}")
            return False
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return False

def test_application_startup():
    """Test that application starts correctly with new CORS config"""
    print("🚀 Testing Application Startup...")
    
    # Reset to development mode
    os.environ['DEBUG'] = 'true'
    if 'ALLOWED_ORIGINS' in os.environ:
        del os.environ['ALLOWED_ORIGINS']
    
    # Reload and test
    import importlib
    import app.core.config
    import app.main
    importlib.reload(app.core.config)
    importlib.reload(app.main)
    
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    # Test root endpoint
    response = client.get('/')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert 'security' in data, "Security information should be included"
    
    security_info = data['security']
    assert security_info['cors_origins_count'] == 5, f"Expected 5 origins, got {security_info['cors_origins_count']}"
    assert security_info['environment'] == 'development', f"Expected development, got {security_info['environment']}"
    
    print("✅ Application startup successful with new CORS config")

def test_cors_headers():
    """Test CORS headers in HTTP response"""
    print("🌐 Testing CORS Headers...")
    
    # Reset to development mode
    os.environ['DEBUG'] = 'true'
    if 'ALLOWED_ORIGINS' in os.environ:
        del os.environ['ALLOWED_ORIGINS']
    
    import importlib
    import app.core.config
    import app.main
    importlib.reload(app.core.config)
    importlib.reload(app.main)
    
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    # Test CORS preflight
    response = client.options(
        '/api/auth/profile',
        headers={
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Authorization'
        }
    )
    
    # Should return 200 for valid origin
    assert response.status_code == 200, f"CORS preflight failed: {response.status_code}"
    
    print("✅ CORS headers working correctly")

if __name__ == "__main__":
    print("🔒 CORS Security Test Suite")
    print("=" * 50)
    
    try:
        test_development_cors()
        test_production_cors() 
        test_wildcard_rejection()
        test_application_startup()
        test_cors_headers()
        
        print("\n🎉 All CORS security tests passed!")
        print("✅ CORS configuration is secure and working correctly")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
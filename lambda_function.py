# lambda_function.py
# Entry point para AWS Lambda - FIXED VERSION
import os
import logging
import sys
from typing import Any, Dict

# Add current directory to Python path
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Configure logging for Lambda
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import FastAPI app
from app.main import app
from mangum import Mangum

# Hosts permitidos para CORS
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "https://betting-app-frontend-six.vercel.app",
    "https://betting-app-frontend-ff29xnj8l-josues-projects-546cbe2a.vercel.app",
    "*"  # For development testing
]

# Crear el handler para Lambda con configuración optimizada
handler = Mangum(app, lifespan="off")

def get_cors_origin(event):
    """
    Determina el origen CORS apropiado basado en el request
    """
    origin = event.get("headers", {}).get("origin") or event.get("headers", {}).get("Origin")
    
    if origin and origin in ALLOWED_ORIGINS:
        return origin
    
    # Fallback para desarrollo local
    if origin and ("localhost" in origin or "127.0.0.1" in origin):
        return origin
    
    # Default para requests sin origen específico - allow all for now
    return "*"

def lambda_handler(event, context):
    """
    Entry point para AWS Lambda - DIRECT FASTAPI ROUTING
    """
    try:
        logger.info(f"Processing request: {event.get('httpMethod', 'UNKNOWN')} {event.get('path', '/')}")
        
        # Get CORS origin
        cors_origin = get_cors_origin(event)
        
        # Manejar preflight requests (OPTIONS)
        if event.get("httpMethod") == "OPTIONS":
            logger.info("Handling CORS preflight request")
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": cors_origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Expose-Headers": "X-Total-Count, X-Filtered-Count",
                    "Access-Control-Max-Age": "86400"
                },
                "body": ""
            }
        
        # ROUTE ALL REQUESTS THROUGH FASTAPI - NO MORE HARDCODED RESPONSES
        logger.info("Routing request through FastAPI")
        response = handler(event, context)
        
        # Asegurar headers CORS en todas las respuestas
        if "headers" not in response:
            response["headers"] = {}
        
        response["headers"].update({
            "Access-Control-Allow-Origin": cors_origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Expose-Headers": "X-Total-Count, X-Filtered-Count"
        })
        
        logger.info(f"Response status: {response.get('statusCode', 'unknown')}")
        return response
    
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            "body": '{"error": "Internal server error", "message": "Lambda handler error", "success": false}'
        }
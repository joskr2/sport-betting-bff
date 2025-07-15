# lambda_function.py
# Entry point para AWS Lambda
import os
from app.main import app
from mangum import Mangum

# Hosts permitidos para CORS
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "https://betting-app-frontend-six.vercel.app",
    "https://betting-app-frontend-ff29xnj8l-josues-projects-546cbe2a.vercel.app"
]

# Crear el handler para Lambda
handler = Mangum(app)

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
    
    # Default para requests sin origen específico
    return ALLOWED_ORIGINS[0]

def lambda_handler(event, context):
    """
    Entry point para AWS Lambda con manejo explícito de CORS
    """
    cors_origin = get_cors_origin(event)
    
    # Manejar preflight requests (OPTIONS)
    if event.get("httpMethod") == "OPTIONS":
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
    
    # Procesar request normal
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
    
    return response
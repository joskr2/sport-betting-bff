# lambda_function.py
# Entry point para AWS Lambda
from app.main import app
from mangum import Mangum

# Crear el handler para Lambda
handler = Mangum(app)

def lambda_handler(event, context):
    """
    Entry point para AWS Lambda con manejo explícito de CORS
    """
    # Manejar preflight requests (OPTIONS)
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Expose-Headers": "X-Total-Count, X-Filtered-Count"
            },
            "body": ""
        }
    
    # Procesar request normal
    response = handler(event, context)
    
    # Asegurar headers CORS en todas las respuestas
    if "headers" not in response:
        response["headers"] = {}
    
    response["headers"].update({
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Expose-Headers": "X-Total-Count, X-Filtered-Count"
    })
    
    return response
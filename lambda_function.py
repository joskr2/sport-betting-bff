# lambda_function.py
# Entry point para AWS Lambda
from app.main import app
from mangum import Mangum

# Crear el handler para Lambda
handler = Mangum(app)

def lambda_handler(event, context):
    """
    Entry point para AWS Lambda
    """
    return handler(event, context)
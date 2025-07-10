#!/bin/bash

# Script para crear deployment package para AWS Lambda

echo "🚀 Building Lambda deployment package..."

# Limpiar archivos previos
rm -rf aws_lambda_artifact.zip lambda_deployment/

# Crear directorio temporal
mkdir lambda_deployment
cd lambda_deployment

# Copiar código de la aplicación
echo "📁 Copying application code..."
cp -r ../app .
cp ../lambda_function.py .

# Instalar dependencias para Linux (Lambda runtime)
echo "📦 Installing Linux dependencies..."
pip install \
    -r ../requirements-lambda.txt \
    --target . \
    --platform linux_x86_64 \
    --only-binary=:all:

# Limpiar archivos innecesarios
echo "🧹 Cleaning up..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

# Crear ZIP
echo "🗜️ Creating deployment package..."
zip -r ../aws_lambda_artifact.zip . -x "*.git*" "*.DS_Store*" "*.pytest_cache*"

cd ..
rm -rf lambda_deployment

echo "✅ Lambda deployment package created: aws_lambda_artifact.zip"
echo "📦 Size: $(du -h aws_lambda_artifact.zip | cut -f1)"
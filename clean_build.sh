#!/bin/bash

# =============================================================================
# 🧹 Clean Build Environment Script
# =============================================================================
# Ensures a completely clean build environment for Lambda

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} $timestamp - $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} $timestamp - $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $timestamp - $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} $timestamp - $message"
            ;;
    esac
}

log "INFO" "🧹 Cleaning build environment..."

# Remove any existing build artifacts
log "INFO" "📦 Removing existing artifacts..."
rm -rf lambda_deployment
rm -f lambda_artifact.zip
rm -rf .venv-lambda
rm -rf lambda_venv

# Clean Python cache files
log "INFO" "🗑️ Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Clean any pip cache
log "INFO" "🗑️ Cleaning pip cache..."
pip cache purge 2>/dev/null || true

log "SUCCESS" "✅ Build environment cleaned!"
log "INFO" "🚀 Now run './build_lambda.sh' for a clean build"
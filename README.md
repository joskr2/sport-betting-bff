# ⚡ Sports Betting BFF

Backend for Frontend (BFF) desarrollado en **FastAPI** para aplicaciones de apuestas deportivas. Optimizado para **AWS Lambda** con **Mangum**.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-orange)
![Tests](https://img.shields.io/badge/Tests-27%20passing-brightgreen)

---

## 🎯 ¿Qué es este BFF?

Un **Backend for Frontend** que actúa como capa inteligente entre tu frontend y la API de apuestas deportivas, proporcionando:

- ✅ **Agregación de datos** de múltiples fuentes
- ✅ **Cache inteligente** con TTL configurable  
- ✅ **Análisis de popularidad** de eventos deportivos
- ✅ **Validaciones adicionales** y transformaciones
- ✅ **Rate limiting** y middleware de seguridad
- ✅ **Optimizado para AWS Lambda** con cold start mínimo

---

## 🚀 Deploy en AWS Lambda (Recomendado)

### 📋 Prerrequisitos
- Cuenta de AWS con acceso a Lambda
- Python 3.11+
- Git

### 🔧 Pasos para Deploy

#### 1. **Clonar y Configurar**
```bash
git clone <repository-url>
cd bff-fastapi

# Crear deployment package
chmod +x build_lambda.sh
./build_lambda.sh
```

#### 2. **Crear Función Lambda**
- **Runtime**: `Python 3.10`
- **Handler**: `lambda_function.lambda_handler`
- **Memory**: `128 MB`
- **Timeout**: `30 segundos`
- **Architecture**: `x86_64`

#### 3. **Subir Package**
Sube el archivo `aws_lambda_artifact.zip` (836KB) generado a tu función Lambda.

#### 4. **Variables de Entorno**
```bash
ALLOWED_ORIGINS=*
DEBUG=false
BACKEND_API_URL=https://tu-api-externa.com
JWT_SECRET=tu-clave-secreta-super-segura
CACHE_TTL_SECONDS=600
RATE_LIMIT_PER_MINUTE=30
```

#### 5. **API Gateway (Opcional)**
- Crear API Gateway REST API
- Configurar proxy integration con Lambda
- Habilitar CORS si es necesario

### 🎉 ¡Listo!
Tu BFF estará disponible en:
```
https://[example-url].execute-api.us-east-1.amazonaws.com/prod/
```

**Health Check**: `GET /health`  
**Documentación**: `GET /docs` *(solo en desarrollo)*

---

## 🛠️ Desarrollo Local

### 📋 Setup Rápido
```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración

# Ejecutar servidor
uvicorn app.main:app --reload
```

**Servidor local**: `http://localhost:8000`

### 🧪 Testing
```bash
# Ejecutar tests
pytest

# Tests específicos
pytest tests/test_health.py -v
pytest tests/test_events.py -v
```

---

## 📋 API Endpoints

### 🏥 Sistema
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Health check del sistema |
| `/` | GET | Información de la API |

### 🔐 Autenticación  
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/auth/register` | POST | Registro de usuarios |
| `/api/auth/login` | POST | Login de usuarios |
| `/api/auth/profile` | GET | Perfil del usuario |

### 🏆 Eventos Deportivos
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/events/` | GET | Lista de eventos (con popularidad) |
| `/api/events/{id}` | GET | Detalle de evento |
| `/api/events/trending/popular` | GET | Eventos más populares |

### 🎲 Apuestas
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/bets/preview` | POST | Preview de apuesta con análisis |
| `/api/bets/` | POST | Crear apuesta |
| `/api/bets/my-bets` | GET | Apuestas del usuario |
| `/api/bets/dashboard` | GET | Dashboard con estadísticas |

---

## 🏗️ Estructura

```
bff-fastapi/
├── 📁 app/                     # Código principal
│   ├── 🚀 main.py              # FastAPI app + Mangum
│   ├── 📁 api/                 # Endpoints (auth, events, bets)
│   ├── 📁 core/                # Configuración
│   ├── 📁 models/              # Schemas Pydantic
│   └── 📁 services/            # Lógica de negocio
├── 📋 requirements.txt         # Dependencias desarrollo
├── 📋 requirements-lambda.txt  # Dependencias Lambda
├── 🔧 build_lambda.sh          # Script build Lambda
├── 🐍 lambda_function.py       # Entry point Lambda
└── 📁 tests/                   # Suite de testing
```

---

## 🔧 Dependencias

### ⚡ Lambda (Producción)
```txt
fastapi==0.104.1      # Framework web
pydantic==1.10.22     # Validación
httpx==0.25.2         # Cliente HTTP
cachetools==5.3.0     # Cache TTL
python-dotenv==1.0.0  # Variables entorno
mangum==0.19.0        # ASGI adapter Lambda
```

### 🔨 Desarrollo Local
```txt
# Todo lo anterior +
uvicorn[standard]>=0.24.0  # Servidor desarrollo
pytest>=7.4.0             # Testing
structlog>=23.2.0          # Logging avanzado
```

---

## 🎯 Características Especiales

### 🔥 Algoritmo de Popularidad
Calcula score de popularidad basado en:
- Cantidad de apuestas (30%)
- Dinero total apostado (40%)  
- Proximidad temporal (20%)
- Popularidad de equipos (10%)

### 💾 Cache Inteligente
- **TTL configurable** (default: 5 minutos)
- **Cache selectivo**: eventos públicos ✅, datos usuario ❌
- **Optimizado para Lambda** cold starts

### 🛡️ Seguridad
- **Rate limiting** configurable por IP
- **CORS** configurable por entorno
- **Validación** estricta con Pydantic
- **Logging estructurado** para auditoría

---

## 📊 Performance

**Benchmarks en Lambda:**
- 🕐 **Cold Start**: ~280ms (primera ejecución)
- ⚡ **Warm**: ~45ms (ejecuciones siguientes)
- 💾 **Memory**: 57MB utilizada de 128MB
- 📦 **Package Size**: 836KB

---

## 🔍 Troubleshooting

### Error Común: ImportModuleError
```bash
# Verificar que el package tiene todas las dependencias
./build_lambda.sh

# Verificar handler correcto en Lambda
Handler: lambda_function.lambda_handler
```

### Variables de Entorno
```bash
# Verificar configuración
curl https://tu-lambda-url.com/health
```

---

## 📄 Licencia

MIT License - Libre para uso comercial y personal.

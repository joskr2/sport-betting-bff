# 🏆 Sports Betting BFF - FastAPI

Backend for Frontend (BFF) desarrollado en **FastAPI** para aplicaciones de apuestas deportivas. Optimizado para **AWS Lambda** con arquitectura serverless.

![Python](https://img.shields.io/badge/Python-3.10-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-orange)
![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen)

---

## 🎯 Características Principales

Un **Backend for Frontend** que actúa como capa inteligente entre tu frontend y la API de apuestas deportivas:

- ✅ **Agregación de datos** de múltiples fuentes
- ✅ **Cache inteligente** con TTL configurable  
- ✅ **Análisis de popularidad** de eventos deportivos
- ✅ **Validaciones adicionales** y transformaciones
- ✅ **Rate limiting** y middleware de seguridad
- ✅ **Optimizado para AWS Lambda** con cold start mínimo (3.5MB)
- ✅ **Pydantic v2** para desarrollo, **v1** para Lambda (compatibilidad)

---

## 🚀 Deploy en AWS Lambda

### 📋 Prerrequisitos
- Cuenta de AWS con acceso a Lambda
- Python 3.10+
- Git

### 🔧 Pasos para Deploy

#### 1. **Preparar el Artifact**
```bash
# Generar el package para Lambda
./build_lambda.sh

# Probar el artifact localmente
python3 test_lambda.py
```

#### 2. **Crear Función Lambda**
- **Runtime**: `Python 3.10`
- **Handler**: `lambda_function.lambda_handler`
- **Memory**: `256 MB`
- **Timeout**: `30 segundos`
- **Architecture**: `x86_64`

#### 3. **Subir Package**
Sube el archivo `lambda_artifact.zip` (3.5MB) generado.

#### 4. **Variables de Entorno**
```bash
BACKEND_API_URL=https://api-kurax-demo-jos.uk
JWT_SECRET=tu-clave-secreta-super-segura
DEBUG=false
```

#### 5. **API Gateway**
- Crear API Gateway REST API
- Configurar proxy integration con Lambda
- Habilitar CORS

### 🎉 ¡Listo!
Tu BFF estará disponible en:
```
https://[api-id].execute-api.us-east-1.amazonaws.com/prod/
```

**Health Check**: `GET /health`  
**Documentación**: `GET /docs`

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

# Test del artifact Lambda
python3 test_lambda.py
```

---

## 📋 API Endpoints

### 🏥 Sistema
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Health check del sistema |
| `/` | GET | Información de la API |
| `/api/stats` | GET | Estadísticas de la aplicación |

### 🔐 Autenticación  
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/auth/register` | POST | Registro de usuarios |
| `/api/auth/login` | POST | Login de usuarios |
| `/api/auth/profile` | GET | Perfil del usuario |
| `/api/auth/logout` | POST | Logout del usuario |

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

## 🏗️ Estructura del Proyecto

```
bff-fastapi/
├── 📁 app/                     # Código principal
│   ├── 🚀 main.py              # FastAPI app + configuración
│   ├── 📁 api/                 # Endpoints (auth, events, bets)
│   ├── 📁 core/                # Configuración y settings
│   ├── 📁 models/              # Schemas Pydantic
│   └── 📁 services/            # Lógica de negocio
├── 📋 requirements.txt         # Dependencias desarrollo
├── 📋 requirements-lambda.txt  # Dependencias Lambda
├── 🔧 build_lambda.sh          # Script build Lambda
├── 🧪 test_lambda.py           # Testing del artifact
├── 🐍 lambda_function.py       # Entry point Lambda
└── 📁 tests/                   # Suite de testing
```

---

## 🔧 Dependencias

### ⚡ Lambda (Producción)
```txt
fastapi==0.68.0           # Framework web (compatible)
pydantic==1.10.12         # Validación (sin deps nativas)
httpx==0.24.1             # Cliente HTTP
mangum==0.17.0            # ASGI adapter Lambda
python-dotenv==1.0.0      # Variables entorno
```

### 🔨 Desarrollo Local
```txt
# Todo lo anterior +
fastapi>=0.100.0          # Versión moderna
pydantic>=2.0.0           # Pydantic v2
uvicorn[standard]>=0.20.0 # Servidor desarrollo
pytest>=7.0.0             # Testing
structlog>=23.0.0          # Logging avanzado
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
- 🕐 **Cold Start**: ~500ms (primera ejecución)
- ⚡ **Warm**: ~50ms (ejecuciones siguientes)
- 💾 **Memory**: 64MB utilizada de 256MB
- 📦 **Package Size**: 3.5MB

---

## 🔧 Scripts Disponibles

```bash
# Construir artifact para Lambda
./build_lambda.sh

# Probar artifact localmente
python3 test_lambda.py

# Desarrollo local
uvicorn app.main:app --reload

# Tests
pytest
```

---

## 🔍 Troubleshooting

### Error Común: ImportError
```bash
# Verificar que el package tiene todas las dependencias
./build_lambda.sh

# Verificar handler correcto en Lambda
Handler: lambda_function.lambda_handler
```

### Health Check
```bash
# Verificar que la función funciona
curl https://tu-lambda-url.com/health
```

### Dependencies Issues
El proyecto maneja dos versiones de Pydantic:
- **Desarrollo**: Pydantic v2 (moderno)
- **Lambda**: Pydantic v1 (compatible)

---

## 📄 Licencia

MIT License - Libre para uso comercial y personal.

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

---

## 📞 Soporte

¿Tienes preguntas o necesitas ayuda? Crea un issue en el repositorio.
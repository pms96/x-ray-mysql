# SQL Tutor X-Ray Enterprise Edition
## Guía de Despliegue Local

### Requisitos Previos
- Node.js 18+ 
- Python 3.11+
- MongoDB 6.0+
- (Opcional) MySQL 8.0 para módulos Enterprise

---

## 1. Clonar/Copiar el Proyecto

```bash
# Estructura del proyecto
sql-xray-enterprise/
├── backend/
│   ├── server.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   ├── package.json
│   └── .env
└── README.md
```

---

## 2. Configurar Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Copiar y configurar variables de entorno
cp .env.local .env
# Editar .env con tus valores
```

### Variables de Entorno Backend (.env)
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=sql_xray_enterprise
CORS_ORIGINS=http://localhost:3000
EMERGENT_LLM_KEY=sk-emergent-b6f0eD4Fb6076A8E43
```

### Iniciar Backend
```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

---

## 3. Configurar Frontend

```bash
cd frontend

# Instalar dependencias
yarn install

# Copiar y configurar variables de entorno
cp .env.local .env
# Editar .env con tus valores
```

### Variables de Entorno Frontend (.env)
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

### Iniciar Frontend
```bash
yarn start
```

---

## 4. Configurar MongoDB

```bash
# Iniciar MongoDB (si no está corriendo)
mongod --dbpath /path/to/data

# O con Docker:
docker run -d -p 27017:27017 --name mongodb mongo:6.0
```

---

## 5. (Opcional) Configurar MySQL para Módulos Enterprise

Los módulos Enterprise requieren conexión a una base de datos MySQL 8.0:

```bash
# Con Docker:
docker run -d \
  --name mysql8 \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=mydb \
  -p 3306:3306 \
  mysql:8.0
```

La conexión MySQL se configura desde la UI en la pestaña "Connect".

---

## 6. Verificar Instalación

```bash
# Verificar backend
curl http://localhost:8001/api/
# Debe retornar: {"message":"SQL Tutor X-Ray Enterprise API","version":"2.0.0","edition":"MySQL 8 Enterprise"}

# Verificar frontend
# Abrir: http://localhost:3000
```

---

## Módulos Enterprise (requieren MySQL)

| Módulo | Descripción | Endpoint |
|--------|-------------|----------|
| Database Intelligence | Detecta problemas estructurales | `/api/enterprise/intelligence` |
| Optimizer Trust | Compara estimaciones vs realidad | `/api/enterprise/optimizer-trust` |
| Growth Simulation | Simula crecimiento 10x/100x | `/api/enterprise/growth-simulation` |
| Index Impact | Evalúa impacto de índices | `/api/enterprise/index-impact` |
| Maturity Score | Score de madurez 0-100 | `/api/enterprise/maturity-score` |
| Executive Report | Informe ejecutivo completo | `/api/enterprise/executive-report` |

---

## Autenticación

La app usa Google OAuth via Emergent Auth. Para desarrollo local sin auth:

1. Crear usuario de prueba en MongoDB:
```javascript
db.users.insertOne({
  user_id: "test-user-001",
  email: "test@example.com",
  name: "Test User",
  created_at: new Date()
});

db.user_sessions.insertOne({
  user_id: "test-user-001",
  session_token: "test_token_123",
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
```

2. Agregar cookie en el navegador:
```javascript
document.cookie = "session_token=test_token_123; path=/";
```

---

## Troubleshooting

### Error: "MySQL connection failed"
- Verificar que MySQL está corriendo
- Verificar credenciales en la UI
- El usuario MySQL necesita permisos para `performance_schema` e `information_schema`

### Error: "CORS error"
- Verificar que `CORS_ORIGINS` en backend incluye la URL del frontend

### Error: "MongoDB connection failed"
- Verificar que MongoDB está corriendo en el puerto 27017

---

## Licencia
MIT License - SQL Tutor X-Ray Enterprise Edition

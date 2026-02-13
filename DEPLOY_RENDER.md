# =====================================================
# 🚀 GUÍA DE DEPLOY EN RENDER - SQL X-Ray Enterprise
# =====================================================

## 📋 REQUISITOS PREVIOS

1. Cuenta en [Render](https://render.com) (gratis)
2. Cuenta en [MongoDB Atlas](https://www.mongodb.com/atlas) (gratis)
3. Código subido a GitHub/GitLab

---

## 🗄️ PASO 1: Crear Base de Datos MongoDB Atlas (GRATIS)

### 1.1 Crear cuenta y cluster

1. Ve a https://www.mongodb.com/atlas
2. Crea cuenta gratuita
3. Click "Build a Database"
4. Selecciona **M0 FREE** (gratis para siempre)
5. Elige región cercana (ej: `aws / N. Virginia`)
6. Nombre del cluster: `sql-xray-cluster`
7. Click "Create"

### 1.2 Configurar acceso

1. En "Security" → "Database Access":
   - Click "Add New Database User"
   - Username: `sqlxray`
   - Password: (genera una segura, GUÁRDALA)
   - Role: "Read and write to any database"
   - Click "Add User"

2. En "Security" → "Network Access":
   - Click "Add IP Address"
   - Click **"Allow Access from Anywhere"** (0.0.0.0/0)
   - Click "Confirm"

### 1.3 Obtener Connection String

1. Click "Connect" en tu cluster
2. Selecciona "Connect your application"
3. Copia el string, se ve así:
   ```
   mongodb+srv://sqlxray:<password>@sql-xray-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
4. **REEMPLAZA `<password>`** con tu contraseña real

---

## 📦 PASO 2: Preparar Código en GitHub

### 2.1 Crear repositorio

```bash
# En tu máquina local
git init
git add .
git commit -m "SQL X-Ray Enterprise - Initial commit"

# Crear repo en GitHub y conectar
git remote add origin https://github.com/TU_USUARIO/sql-xray-enterprise.git
git branch -M main
git push -u origin main
```

### 2.2 Estructura requerida
```
tu-repo/
├── backend/
│   ├── server.py
│   ├── requirements.txt
│   └── .python-version
├── frontend/
│   ├── src/
│   ├── package.json
│   └── public/
└── render.yaml (opcional)
```

---

## 🔧 PASO 3: Deploy Backend en Render

### 3.1 Crear Web Service

1. Ve a https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Conecta tu cuenta de GitHub
4. Selecciona tu repositorio `sql-xray-enterprise`

### 3.2 Configurar Backend

| Campo | Valor |
|-------|-------|
| **Name** | `sql-xray-api` |
| **Region** | Oregon (US West) |
| **Branch** | `main` |
| **Root Directory** | `backend` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn server:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free |

### 3.3 Variables de Entorno Backend

Click "Advanced" → "Add Environment Variable":

| Key | Value |
|-----|-------|
| `MONGO_URL` | `mongodb+srv://sqlxray:TU_PASSWORD@sql-xray-cluster.xxxxx.mongodb.net/sql_xray?retryWrites=true&w=majority` |
| `DB_NAME` | `sql_xray_enterprise` |
| `CORS_ORIGINS` | `https://sql-xray-frontend.onrender.com` |
| `EMERGENT_LLM_KEY` | `sk-emergent-b6f0eD4Fb6076A8E43` |
| `PYTHON_VERSION` | `3.11.0` |

### 3.4 Deploy

1. Click **"Create Web Service"**
2. Espera 5-10 minutos al primer deploy
3. Tu API estará en: `https://sql-xray-api.onrender.com`

### 3.5 Verificar Backend

```bash
curl https://sql-xray-api.onrender.com/api/
# Debe retornar: {"message":"SQL Tutor X-Ray Enterprise API"...}
```

---

## 🎨 PASO 4: Deploy Frontend en Render

### 4.1 Crear Static Site

1. En Render Dashboard, click **"New +"** → **"Static Site"**
2. Selecciona el mismo repositorio

### 4.2 Configurar Frontend

| Campo | Valor |
|-------|-------|
| **Name** | `sql-xray-frontend` |
| **Branch** | `main` |
| **Root Directory** | `frontend` |
| **Build Command** | `yarn install && yarn build` |
| **Publish Directory** | `build` |

### 4.3 Variables de Entorno Frontend

| Key | Value |
|-----|-------|
| `REACT_APP_BACKEND_URL` | `https://sql-xray-api.onrender.com` |

### 4.4 Configurar Redirects (IMPORTANTE)

En la sección "Redirects/Rewrites", añade:

| Source | Destination | Action |
|--------|-------------|--------|
| `/*` | `/index.html` | Rewrite |

Esto es necesario para que React Router funcione.

### 4.5 Deploy

1. Click **"Create Static Site"**
2. Espera 3-5 minutos
3. Tu app estará en: `https://sql-xray-frontend.onrender.com`

---

## 🔄 PASO 5: Actualizar CORS en Backend

Una vez que tengas la URL del frontend, actualiza CORS:

1. Ve a tu Web Service `sql-xray-api`
2. Click "Environment"
3. Edita `CORS_ORIGINS`:
   ```
   https://sql-xray-frontend.onrender.com
   ```
4. El backend se redesplegará automáticamente

---

## ✅ PASO 6: Verificar Todo

### Test 1: Backend
```bash
curl https://sql-xray-api.onrender.com/api/health
# ✅ {"status":"healthy"}
```

### Test 2: Frontend
Abre `https://sql-xray-frontend.onrender.com` en el navegador
- ✅ Landing page carga
- ✅ Botón "Sign In" visible

### Test 3: Análisis SQL
1. Haz login con Google
2. Escribe una query SQL
3. Click "Analyze"
- ✅ Análisis con IA funciona

---

## 🐛 TROUBLESHOOTING

### Error: "Application failed to respond"
- Revisa los logs en Render Dashboard
- Verifica que `MONGO_URL` es correcto
- Asegúrate de que MongoDB Atlas permite conexiones desde cualquier IP

### Error: "CORS error"
- Verifica que `CORS_ORIGINS` incluye la URL exacta del frontend
- Sin trailing slash: `https://sql-xray-frontend.onrender.com` ✅
- Con trailing slash: `https://sql-xray-frontend.onrender.com/` ❌

### Error: "Cannot GET /dashboard"
- Falta el redirect `/* → /index.html` en Static Site

### El backend tarda en responder
- El plan Free de Render "duerme" después de 15 min de inactividad
- La primera request puede tardar 30-60 segundos
- Considera el plan Starter ($7/mes) para evitar esto

---

## 💰 COSTOS

| Servicio | Plan | Costo |
|----------|------|-------|
| Render Backend | Free | $0 |
| Render Frontend | Free | $0 |
| MongoDB Atlas | M0 | $0 |
| **Total** | | **$0/mes** |

### Limitaciones del plan gratuito:
- Backend se "duerme" tras 15 min inactivo
- 750 horas/mes de ejecución
- MongoDB: 512MB storage

---

## 🎉 ¡LISTO!

Tu SQL X-Ray Enterprise está desplegado en:
- **Frontend**: `https://sql-xray-frontend.onrender.com`
- **Backend**: `https://sql-xray-api.onrender.com`
- **Base de datos**: MongoDB Atlas (cloud)

---

## 📝 NOTAS ADICIONALES

### Dominio personalizado
1. En Render, ve a tu Static Site
2. Click "Settings" → "Custom Domains"
3. Añade tu dominio
4. Configura DNS según instrucciones

### Actualizar código
```bash
git add .
git commit -m "Update"
git push
# Render redespliega automáticamente
```

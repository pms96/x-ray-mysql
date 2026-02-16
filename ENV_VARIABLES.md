# =========================================================
# SQL X-RAY ENTERPRISE v2.1.0 - ROBUST EDITION
# Variables de Entorno para Deploy Local / Render / Cloud
# =========================================================

# =====================
# BACKEND (.env)
# =====================

# MongoDB - Para persistencia de scans, usuarios y historial
MONGO_URL=mongodb://localhost:27017
# O para MongoDB Atlas:
# MONGO_URL=mongodb+srv://user:password@cluster.mongodb.net/sql_xray?retryWrites=true&w=majority

# Nombre de la base de datos MongoDB
DB_NAME=sql_xray_enterprise

# CORS - URLs del frontend permitidas
CORS_ORIGINS=http://localhost:3000

# API Key para análisis con IA (OpenAI GPT-5.2 via Emergent)
EMERGENT_LLM_KEY=sk-emergent-b6f0eD4Fb6076A8E43

# =====================
# FRONTEND (.env)
# =====================

# URL del backend API
REACT_APP_BACKEND_URL=http://localhost:8001

# =========================================================
# COLECCIONES MONGODB UTILIZADAS
# =========================================================
#
# 1. users              - Usuarios autenticados
# 2. user_sessions      - Sesiones activas
# 3. saved_queries      - Queries guardadas
# 4. database_scans     - Estado de scans (incremental)
# 5. scan_tables        - Resultados por tabla (persistente)
# 6. scan_logs          - Logs de eventos del scan
# 7. workload_analyses  - Estado de análisis de workload
# 8. workload_queries   - Queries analizadas del workload
# 9. workload_stats     - Estadísticas de I/O e índices
#
# =========================================================

# =========================================================
# ENDPOINTS DE LA API v2.1.0
# =========================================================
#
# AUTH:
#   POST /api/auth/session  - Crear sesión (Google OAuth)
#   GET  /api/auth/me       - Obtener usuario actual
#   POST /api/auth/logout   - Cerrar sesión
#
# DATABASE:
#   POST /api/db/test-connection  - Probar conexión MySQL
#   POST /api/db/tables           - Obtener tablas REALES
#
# MODULE 1 - DATABASE SCANNER (INCREMENTAL):
#   POST /api/scan/start            - Iniciar scan
#   GET  /api/scan/status/{id}      - Progreso en tiempo real
#   GET  /api/scan/results/{id}     - Resultados completos
#   POST /api/scan/cancel/{id}      - Cancelar scan
#   POST /api/scan/resume/{id}      - Reanudar scan
#
# MODULE 3 - QUERY LAB (FIXED):
#   POST /api/query/validate-tables - Validar tablas de query
#   POST /api/query/explain         - Ejecutar EXPLAIN
#
# MODULE 6 - WORKLOAD ANALYZER (INCREMENTAL):
#   POST /api/workload/start        - Iniciar análisis
#   GET  /api/workload/status/{id}  - Progreso en tiempo real
#   POST /api/workload/cancel/{id}  - Cancelar análisis
#
# AI ANALYSIS:
#   POST /api/analyze               - Análisis con GPT-5.2
#
# QUERIES:
#   POST   /api/queries             - Guardar query
#   GET    /api/queries             - Listar queries
#   DELETE /api/queries/{id}        - Eliminar query
#
# =========================================================

# =========================================================
# CARACTERÍSTICAS v2.1.0 (ROBUST EDITION)
# =========================================================
#
# ✅ Módulo 1 - Database Scanner:
#    - Procesamiento incremental por batches
#    - Persistencia inmediata en MongoDB
#    - Reanudación automática tras desconexión
#    - Progreso en tiempo real (polling)
#    - Pool de conexiones con reconexión
#    - Timeout por tabla (no bloquea)
#
# ✅ Módulo 3 - Query Lab:
#    - Lee tablas REALES desde INFORMATION_SCHEMA
#    - NO asume nombres (user_user, no users)
#    - Validación previa de tablas
#    - Sugerencias si tabla no existe
#
# ✅ Módulo 6 - Workload Analyzer:
#    - Análisis por fases
#    - Persistencia incremental por fase
#    - Reanudación tras fallos
#    - Análisis de performance_schema
#    - Detección de índices no usados
#
# =========================================================

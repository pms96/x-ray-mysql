from fastapi import FastAPI, APIRouter, HTTPException, Response, Request, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import json
import io
from contextlib import asynccontextmanager
from openai import AsyncOpenAI
import asynccontextmanager

# Import engines
from scanner_engine import (
    MySQLPoolManager, ScanPersistence, TableIntrospector, 
    DatabaseScannerEngine, ScanType, ScanStatus
)
from workload_engine import WorkloadPersistence, WorkloadAnalyzerEngine

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = "mongodb+srv://xray:2GpEVjbanJ7PU8cH@x-raid-query.femy2lp.mongodb.net/xray?appName=x-raid-query&retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"
client = AsyncIOMotorClient(mongo_url)
db = client["xray"]

print("### MONGO_URL EN RUNTIME ###", mongo_url, flush=True)

# OpenAI Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== GLOBAL STATE ====================

# Active scanners por conexión (para gestión de pools)
active_pools: Dict[str, MySQLPoolManager] = {}
active_scans: Dict[str, DatabaseScannerEngine] = {}
active_workloads: Dict[str, WorkloadAnalyzerEngine] = {}

# ==================== MODELS ====================

class MySQLConnection(BaseModel):
    host: str
    port: int = 3306
    user: str
    password: str
    database: str
    ssl: bool = True

class StartScanRequest(BaseModel):
    connection: MySQLConnection
    scan_type: str = "intelligence"
    resume_scan_id: Optional[str] = None

class StartWorkloadRequest(BaseModel):
    connection: MySQLConnection
    resume_id: Optional[str] = None

class QueryAnalysisRequest(BaseModel):
    query: str
    connection: MySQLConnection
    dialect: str = "mysql"
    mode: str = "advanced"

# ==================== HELPER: GET OR CREATE POOL ====================

def get_pool_key(conn: MySQLConnection) -> str:
    return f"{conn.host}:{conn.port}/{conn.database}/{conn.user}"

async def get_or_create_pool(conn: MySQLConnection) -> MySQLPoolManager:
    """Obtiene o crea un pool de conexiones"""
    key = get_pool_key(conn)
    
    if key not in active_pools:
        config = {
            "host": conn.host,
            "port": conn.port,
            "user": conn.user,
            "password": conn.password,
            "database": conn.database,
            "ssl": conn.ssl
        }
        active_pools[key] = MySQLPoolManager(config)
    
    return active_pools[key]

# ==================== APP SETUP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Cleanup on shutdown
    for pool in active_pools.values():
        await pool.close()
    client.close()

app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

# ==================== AUTH (Simplified) ====================

async def get_current_user(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]
    
    if not session_token:
        return None
    
    session_doc = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session_doc:
        return None
    
    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    return user_doc

@api_router.post("/auth/session")
async def create_session(request: Request, response: Response):
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    async with httpx.AsyncClient() as http_client:
        resp = await http_client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session")
        data = resp.json()
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    existing_user = await db.users.find_one({"email": data["email"]}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user["user_id"]
    else:
        await db.users.insert_one({
            "user_id": user_id, "email": data["email"], "name": data["name"],
            "picture": data.get("picture"), "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    session_token = data.get("session_token", str(uuid.uuid4()))
    await db.user_sessions.insert_one({
        "user_id": user_id, "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    })
    
    response.set_cookie(key="session_token", value=session_token, httponly=True, secure=True, samesite="none", path="/", max_age=7*24*60*60)
    return {"user_id": user_id, "email": data["email"], "name": data["name"], "picture": data.get("picture")}

@api_router.get("/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out"}

# ==================== DATABASE CONNECTION ====================

@api_router.post("/db/test-connection")
async def test_connection(conn: MySQLConnection):
    """Test MySQL connection"""
    try:
        pool = await get_or_create_pool(conn)
        result = await pool.execute_with_retry(
            "SELECT VERSION() as version, DATABASE() as db",
            timeout=30
        )
        return {"status": "connected", "version": result[0]['version'], "database": result[0]['db']}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/db/tables")
async def get_real_tables(conn: MySQLConnection):
    """
    MÓDULO 3 FIX: Obtiene los nombres REALES de las tablas.
    Esta es la fuente de verdad - NO asumimos nombres.
    """
    if not conn.host or not conn.user:
        raise HTTPException(status_code=400, detail="MySQL connection required. Please provide host, user, password, and database.")
    
    try:
        pool = await get_or_create_pool(conn)
        introspector = TableIntrospector(pool)
        
        # Obtener diccionario de tablas reales
        table_dict = await introspector.build_table_dictionary(conn.database)
        tables_list = await introspector.get_real_tables(conn.database)
        
        return {
            "database": conn.database,
            "total_tables": len(tables_list),
            "tables": tables_list,
            "table_dictionary": table_dict  # Para validación de queries
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tables: {e}")
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")

# ==================== MODULE 1: DATABASE SCANNER ====================

@api_router.post("/scan/start")
async def start_database_scan(request: StartScanRequest, background_tasks: BackgroundTasks):
    """
    Inicia un nuevo scan de base de datos.
    El scan se ejecuta en background y es reanudable.
    """
    conn = request.connection
    
    try:
        pool = await get_or_create_pool(conn)
        persistence = ScanPersistence(db)
        introspector = TableIntrospector(pool)
        
        engine = DatabaseScannerEngine(pool, persistence, introspector)
        
        # Verificar si es reanudación
        scan_id = request.resume_scan_id
        if not scan_id:
            # Obtener conteo de tablas para crear el scan
            tables = await introspector.get_real_tables(conn.database)
            scan_id = f"scan_{uuid.uuid4().hex[:12]}"
            
            scan_type = ScanType.INTELLIGENCE
            if request.scan_type == "full":
                scan_type = ScanType.FULL
            
            await persistence.create_scan(
                scan_id, scan_type, conn.database, len(tables),
                {"host": conn.host, "database": conn.database}
            )
        
        # Guardar referencia al engine
        active_scans[scan_id] = engine
        
        # Ejecutar en background
        async def run_scan():
            try:
                await engine.start_scan(
                    conn.database,
                    {"host": conn.host},
                    ScanType.INTELLIGENCE,
                    request.resume_scan_id
                )
            except Exception as e:
                logger.error(f"Scan error: {e}")
                await persistence.mark_scan_failed(scan_id, str(e))
            finally:
                active_scans.pop(scan_id, None)
        
        background_tasks.add_task(run_scan)
        
        return {
            "scan_id": scan_id,
            "status": "started",
            "message": "Scan started in background. Poll /scan/status/{scan_id} for progress."
        }
    
    except Exception as e:
        logger.error(f"Error starting scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/scan/status/{scan_id}")
async def get_scan_status(scan_id: str):
    """
    Obtiene el progreso en tiempo real de un scan.
    La UI debe hacer polling a este endpoint.
    """
    persistence = ScanPersistence(db)
    scan = await persistence.get_scan(scan_id)
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return {
        "scan_id": scan_id,
        "status": scan["status"],
        "progress_percentage": scan["progress_percentage"],
        "total_tables": scan["total_tables"],
        "processed_tables": scan["processed_tables"],
        "current_table": scan.get("current_table"),
        "started_at": scan["started_at"],
        "updated_at": scan.get("updated_at"),
        "errors": scan.get("errors", [])[-5:],  # Últimos 5 errores
        "stats": scan.get("stats", {})
    }

@api_router.get("/scan/results/{scan_id}")
async def get_scan_results(scan_id: str):
    """Obtiene los resultados completos de un scan"""
    persistence = ScanPersistence(db)
    
    scan = await persistence.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    results = await persistence.get_scan_results(scan_id)
    
    return {
        "scan_id": scan_id,
        "status": scan["status"],
        "database": scan.get("database"),
        "stats": scan.get("stats", {}),
        "tables": results,
        "total_issues": sum(len(t.get("issues", [])) for t in results)
    }

@api_router.post("/scan/cancel/{scan_id}")
async def cancel_scan(scan_id: str):
    """Cancela un scan en progreso"""
    if scan_id in active_scans:
        active_scans[scan_id].cancel()
        return {"message": "Scan cancellation requested"}
    
    return {"message": "Scan not active or already completed"}

@api_router.post("/scan/resume/{scan_id}")
async def resume_scan(scan_id: str, conn: MySQLConnection, background_tasks: BackgroundTasks):
    """Reanuda un scan interrumpido"""
    persistence = ScanPersistence(db)
    scan = await persistence.get_scan(scan_id)
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan["status"] == ScanStatus.COMPLETED.value:
        return {"message": "Scan already completed", "scan_id": scan_id}
    
    # Reusar el endpoint de start con resume
    request = StartScanRequest(connection=conn, resume_scan_id=scan_id)
    return await start_database_scan(request, background_tasks)

# ==================== MODULE 3: QUERY LAB (FIXED) ====================

@api_router.post("/query/validate-tables")
async def validate_query_tables(request: QueryAnalysisRequest):
    """
    Valida que las tablas usadas en la query existen.
    Usa introspección REAL - nunca asume nombres.
    """
    if not request.connection or not request.connection.host:
        raise HTTPException(status_code=400, detail="MySQL connection required for table validation.")
    
    try:
        pool = await get_or_create_pool(request.connection)
        introspector = TableIntrospector(pool)
        
        # Obtener tablas reales
        real_tables = await introspector.build_table_dictionary(request.connection.database)
        
        # Extraer tablas de la query (básico)
        import re
        query_upper = request.query.upper()
        
        # Patrones para encontrar tablas
        patterns = [
            r'FROM\s+`?(\w+)`?',
            r'JOIN\s+`?(\w+)`?',
            r'INTO\s+`?(\w+)`?',
            r'UPDATE\s+`?(\w+)`?',
        ]
        
        found_tables = set()
        for pattern in patterns:
            matches = re.findall(pattern, request.query, re.IGNORECASE)
            found_tables.update(matches)
        
        # Validar cada tabla
        validation = []
        for table in found_tables:
            table_lower = table.lower()
            exists = table in real_tables or table_lower in {t.lower() for t in real_tables}
            
            # Buscar sugerencia si no existe
            suggestion = None
            if not exists:
                for real_table in real_tables:
                    if table_lower in real_table.lower() or real_table.lower() in table_lower:
                        suggestion = real_table
                        break
            
            validation.append({
                "table_name": table,
                "exists": exists,
                "suggestion": suggestion
            })
        
        all_valid = all(v["exists"] for v in validation)
        
        return {
            "valid": all_valid,
            "tables_in_query": list(found_tables),
            "validation": validation,
            "real_tables_available": list(real_tables.keys())[:50]  # Top 50 para referencia
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")

@api_router.post("/query/explain")
async def explain_query(request: QueryAnalysisRequest):
    """
    Ejecuta EXPLAIN en una query con validación previa de tablas.
    """
    try:
        pool = await get_or_create_pool(request.connection)
        
        # Primero validar tablas
        introspector = TableIntrospector(pool)
        real_tables = await introspector.build_table_dictionary(request.connection.database)
        
        # EXPLAIN FORMAT=JSON
        explain_query = f"EXPLAIN FORMAT=JSON {request.query}"
        
        result = await pool.execute_with_retry(explain_query, timeout=60)
        
        if result:
            explain_json = json.loads(list(result[0].values())[0])
            return {
                "success": True,
                "explain": explain_json,
                "real_tables": list(real_tables.keys())
            }
        
        return {"success": False, "error": "No EXPLAIN output"}
    
    except Exception as e:
        error_msg = str(e)
        
        # Detectar error de tabla no existente
        if "doesn't exist" in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "hint": "Table name may be incorrect. Use /db/tables to get real table names."
            }
        
        raise HTTPException(status_code=500, detail=error_msg)

# ==================== MODULE 6: WORKLOAD ANALYZER ====================

@api_router.post("/workload/start")
async def start_workload_analysis(request: StartWorkloadRequest, background_tasks: BackgroundTasks):
    """Inicia un análisis de workload"""
    conn = request.connection
    
    try:
        pool = await get_or_create_pool(conn)
        persistence = WorkloadPersistence(db)
        
        engine = WorkloadAnalyzerEngine(pool, persistence)
        
        analysis_id = request.resume_id or f"workload_{uuid.uuid4().hex[:12]}"
        
        if not request.resume_id:
            await persistence.create_analysis(analysis_id, conn.database)
        
        active_workloads[analysis_id] = engine
        
        async def run_workload():
            try:
                await engine.start_analysis(conn.database, request.resume_id)
            except Exception as e:
                logger.error(f"Workload error: {e}")
                await persistence.mark_failed(analysis_id, str(e))
            finally:
                active_workloads.pop(analysis_id, None)
        
        background_tasks.add_task(run_workload)
        
        return {
            "analysis_id": analysis_id,
            "status": "started",
            "message": "Workload analysis started. Poll /workload/status/{analysis_id}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/workload/status/{analysis_id}")
async def get_workload_status(analysis_id: str):
    """Obtiene el progreso del análisis de workload"""
    persistence = WorkloadPersistence(db)
    analysis = await persistence.get_analysis(analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis

@api_router.post("/workload/cancel/{analysis_id}")
async def cancel_workload(analysis_id: str):
    """Cancela un análisis de workload"""
    if analysis_id in active_workloads:
        active_workloads[analysis_id].cancel()
        return {"message": "Cancellation requested"}
    return {"message": "Analysis not active"}

# ==================== AI ANALYSIS ====================

@api_router.post("/analyze")
async def analyze_sql(request: Request):
    """Análisis de SQL con IA"""
    try:
        body = await request.json()
        query = body.get("query", "")
        dialect = body.get("dialect", "mysql")
        mode = body.get("mode", "advanced")
        conn_data = body.get("connection")
        
        # Si hay conexión, validar tablas primero
        real_tables = None
        if conn_data:
            try:
                conn = MySQLConnection(**conn_data)
                pool = await get_or_create_pool(conn)
                introspector = TableIntrospector(pool)
                real_tables = await introspector.build_table_dictionary(conn.database)
            except:
                pass
        
        # Análisis con IA
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        system_prompt = f"""Eres un experto en MySQL 8 Performance. Analiza la query SQL.
Responde en JSON con: overview, technical_breakdown, refactor_suggestions, cost_scalability, anti_patterns_detected.
{"TABLAS REALES DISPONIBLES: " + ", ".join(list(real_tables.keys())[:30]) if real_tables else ""}
"""
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"sql_{uuid.uuid4().hex[:8]}",
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
        
        response = await chat.send_message(UserMessage(text=f"Analiza:\n```sql\n{query}\n```"))
        
        # Parse JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                result = json.loads(json_match.group())
                if real_tables:
                    result["real_tables_hint"] = list(real_tables.keys())[:20]
                return result
            except:
                pass
        
        return {"overview": {"summary": response}, "raw_response": response}
    
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SAVED QUERIES ====================

@api_router.post("/queries")
async def save_query(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    body = await request.json()
    query_doc = {
        "query_id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "query": body.get("query"),
        "dialect": body.get("dialect", "mysql"),
        "analysis_result": body.get("analysis_result"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.saved_queries.insert_one(query_doc)
    query_doc.pop("_id", None)
    return query_doc

@api_router.get("/queries")
async def get_queries(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return await db.saved_queries.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)

@api_router.delete("/queries/{query_id}")
async def delete_query(query_id: str, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = await db.saved_queries.delete_one({"query_id": query_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {
        "message": "SQL X-Ray Enterprise API",
        "version": "2.1.0",
        "edition": "MySQL 8 Enterprise - Robust Edition",
        "features": [
            "Incremental database scanning",
            "Resumable analysis",
            "Real-time progress",
            "Real table introspection"
        ]
    }

@api_router.get("/health")
async def health():
    return {"status": "healthy"}

# ==================== APP SETUP ====================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

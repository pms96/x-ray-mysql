from fastapi import FastAPI, APIRouter, HTTPException, Response, Request, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenAI Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SchemaColumn(BaseModel):
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None
    index_type: Optional[str] = None
    cardinality: Optional[int] = None
    null_percent: Optional[float] = None

class TableSchema(BaseModel):
    table_name: str
    columns: List[SchemaColumn]
    row_count: Optional[int] = None
    size_mb: Optional[float] = None
    indexes: Optional[List[str]] = []
    partitions: Optional[str] = None
    distribution_key: Optional[str] = None

class SQLAnalysisRequest(BaseModel):
    query: str
    dialect: str = "postgresql"
    schemas: Optional[List[TableSchema]] = []
    explain_output: Optional[str] = None
    mode: str = "advanced"
    growth_simulation: Optional[str] = None

class SavedQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    query: str
    dialect: str
    schemas: Optional[List[Dict]] = []
    analysis_result: Optional[Dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ==================== AUTH HELPERS ====================

async def get_current_user(request: Request) -> Optional[User]:
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]
    
    if not session_token:
        return None
    
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        return None
    
    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    
    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        return None
    
    return User(**user_doc)

async def require_auth(request: Request) -> User:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/session")
async def create_session(request: Request, response: Response):
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    async with httpx.AsyncClient() as client_http:
        resp = await client_http.get(
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
        await db.users.update_one(
            {"email": data["email"]},
            {"$set": {
                "name": data["name"],
                "picture": data.get("picture"),
            }}
        )
    else:
        await db.users.insert_one({
            "user_id": user_id,
            "email": data["email"],
            "name": data["name"],
            "picture": data.get("picture"),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    session_token = data.get("session_token", str(uuid.uuid4()))
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    await db.user_sessions.insert_one({
        "session_id": str(uuid.uuid4()),
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7*24*60*60
    )
    
    return {
        "user_id": user_id,
        "email": data["email"],
        "name": data["name"],
        "picture": data.get("picture")
    }

@api_router.get("/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture
    }

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out"}

# ==================== SQL ANALYSIS ENDPOINT ====================

def build_system_prompt(dialect: str, mode: str) -> str:
    return f"""Eres un experto en SQL Performance y Arquitectura de Datos.
Tu rol es analizar queries SQL como un ingeniero senior que trabaja con bases de datos de 500M+ registros.

DIALECTO ACTUAL: {dialect}
MODO DE ANÁLISIS: {mode}

DEBES RESPONDER EN FORMATO JSON ESTRUCTURADO con las siguientes secciones:

{{
  "overview": {{
    "summary": "Resumen en lenguaje natural de qué hace la query",
    "granularity": "Nivel de agregación del resultado",
    "final_columns": ["lista de columnas finales y su significado"],
    "alerts": [
      {{"type": "warning|error|info", "message": "descripción de la alerta", "severity": "low|medium|high|critical"}}
    ],
    "facts_vs_assumptions": {{
      "facts": ["hechos derivados del SQL"],
      "assumptions": ["suposiciones por falta de stats"]
    }}
  }},
  "logical_vs_physical_order": {{
    "logical_order": [
      {{"step": 1, "operation": "FROM", "description": "explicación"}},
      ...
    ],
    "optimizer_optimizations": [
      {{"optimization": "nombre", "description": "qué hace el optimizador", "dialect_specific": true/false}}
    ]
  }},
  "technical_breakdown": {{
    "select": {{
      "expressions": ["lista de expresiones"],
      "row_by_row_impact": "impacto de funciones fila a fila",
      "function_warnings": ["advertencias sobre funciones"]
    }},
    "joins": [
      {{
        "type": "INNER/LEFT/etc",
        "tables": ["tabla1", "tabla2"],
        "keys": ["columnas de join"],
        "index_usage": "análisis de índices",
        "risks": ["nested loop risk", "hash spill risk", "multiplicación de filas"]
      }}
    ],
    "where": {{
      "filters": ["lista de filtros"],
      "sargable_analysis": ["filtros sargables vs no sargables"],
      "function_on_columns": ["funciones aplicadas a columnas"],
      "implicit_casts": ["casteos implícitos detectados"]
    }},
    "group_by": {{
      "columns": ["columnas de agrupación"],
      "aggregation_type": "hash vs sort",
      "memory_spill_risk": "bajo/medio/alto"
    }},
    "subqueries": [
      {{"type": "correlada/no correlada", "risk": "descripción", "rewrite_suggestion": "sugerencia"}}
    ],
    "window_functions": [
      {{"function": "nombre", "partition_by": [], "order_by": [], "memory_impact": "descripción"}}
    ]
  }},
  "refactor_suggestions": {{
    "pedagogical": {{
      "query": "query refactorizada con CTEs para claridad",
      "explanation": "por qué es más clara"
    }},
    "performance_optimized": {{
      "query": "query optimizada para rendimiento",
      "explanation": "mejoras de rendimiento"
    }},
    "high_scale": {{
      "query": "query preparada para alta escala",
      "explanation": "preparación para 100M+ filas"
    }}
  }},
  "cost_scalability": {{
    "estimated_cost": "bajo/medio/alto/crítico",
    "complexity": "O(n)/O(n log n)/O(n²)",
    "worst_scaling_part": "qué parte escala peor",
    "growth_simulation": {{
      "1M_to_10M": "impacto estimado",
      "10M_to_100M": "impacto estimado",
      "100M_to_1B": "impacto estimado"
    }},
    "index_recommendations": [
      {{"table": "tabla", "columns": ["cols"], "type": "B-Tree/Hash/GIN/etc", "reason": "justificación"}}
    ],
    "partition_recommendations": [
      {{"table": "tabla", "strategy": "range/list/hash", "column": "columna", "reason": "justificación"}}
    ]
  }},
  "architecture": {{
    "missing_pk": ["tablas sin PK"],
    "missing_fk_indexes": ["FKs sin índice"],
    "natural_vs_surrogate": "análisis de claves",
    "star_schema_fit": "si aplica modelo estrella",
    "partition_needed": ["tablas que necesitan partición"],
    "aggregation_tables_recommended": ["tablas summary recomendadas"],
    "recommendations": ["recomendaciones de arquitectura"]
  }},
  "testing_validation": {{
    "validation_queries": [
      {{"purpose": "qué valida", "query": "query de validación"}}
    ],
    "stress_test_suggestions": ["sugerencias de stress test"],
    "before_after_comparison": "cómo comparar EXPLAIN antes/después"
  }},
  "mermaid_diagram": "graph TD\\n    A[tabla1] -->|JOIN| B[tabla2]\\n    ..."
  ,
  "anti_patterns_detected": [
    {{"pattern": "nombre del anti-patrón", "location": "dónde se detectó", "severity": "low/medium/high/critical", "fix": "cómo corregirlo"}}
  ]
}}

ANTI-PATRONES A DETECTAR:
- JOIN sin ON
- CROSS JOIN accidental
- DISTINCT para arreglar duplicados
- SELECT *
- ORDER BY sin LIMIT
- Funciones en filtros WHERE
- CAST en JOIN
- Subquery correlada
- WHERE que no usa índice
- Tabla grande sin partición
- GROUP BY de alta cardinalidad
- Window sobre tabla masiva
- OFFSET grande
- Falta índice en FK
- Falta ANALYZE

Adapta el análisis al dialecto {dialect}. Sé técnico pero pedagógico."""

async def analyze_sql_with_ai(request: SQLAnalysisRequest) -> Dict[str, Any]:
    system_prompt = build_system_prompt(request.dialect, request.mode)
    
    user_prompt = f"""Analiza esta query SQL:

```sql
{request.query}
```

DIALECTO: {request.dialect}
MODO: {request.mode}
"""
    
    if request.schemas:
        user_prompt += "\n\nESQUEMAS DE TABLAS:\n"
        for schema in request.schemas:
            user_prompt += f"\nTabla: {schema.table_name}"
            if schema.row_count:
                user_prompt += f" (~{schema.row_count:,} filas)"
            user_prompt += "\nColumnas:\n"
            for col in schema.columns:
                col_info = f"  - {col.name} ({col.type})"
                if col.primary_key:
                    col_info += " [PK]"
                if col.foreign_key:
                    col_info += f" [FK -> {col.foreign_key}]"
                if col.index_type:
                    col_info += f" [IDX: {col.index_type}]"
                if col.cardinality:
                    col_info += f" [Card: {col.cardinality:,}]"
                user_prompt += col_info + "\n"
    
    if request.explain_output:
        user_prompt += f"\n\nEXPLAIN OUTPUT:\n```\n{request.explain_output}\n```"
    
    if request.growth_simulation:
        user_prompt += f"\n\nSIMULACIÓN DE CRECIMIENTO: {request.growth_simulation}"
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"sql_analysis_{uuid.uuid4().hex[:8]}",
        system_message=system_prompt
    ).with_model("openai", "gpt-5.2")
    
    user_message = UserMessage(text=user_prompt)
    response = await chat.send_message(user_message)
    
    import json
    import re
    
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    return {
        "overview": {
            "summary": response,
            "alerts": [],
            "facts_vs_assumptions": {"facts": [], "assumptions": []}
        },
        "raw_response": response
    }

@api_router.post("/analyze")
async def analyze_sql(request: SQLAnalysisRequest):
    try:
        result = await analyze_sql_with_ai(request)
        return result
    except Exception as e:
        logger.error(f"Error analyzing SQL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== QUERY HISTORY ENDPOINTS ====================

@api_router.post("/queries")
async def save_query(request: Request):
    user = await require_auth(request)
    body = await request.json()
    
    query_doc = {
        "query_id": str(uuid.uuid4()),
        "user_id": user.user_id,
        "query": body.get("query"),
        "dialect": body.get("dialect", "postgresql"),
        "schemas": body.get("schemas", []),
        "analysis_result": body.get("analysis_result"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.saved_queries.insert_one(query_doc)
    query_doc.pop("_id", None)
    
    return query_doc

@api_router.get("/queries")
async def get_queries(request: Request):
    user = await require_auth(request)
    
    queries = await db.saved_queries.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return queries

@api_router.delete("/queries/{query_id}")
async def delete_query(query_id: str, request: Request):
    user = await require_auth(request)
    
    result = await db.saved_queries.delete_one({
        "query_id": query_id,
        "user_id": user.user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Query not found")
    
    return {"message": "Query deleted"}

# ==================== ROOT & STATUS ====================

@api_router.get("/")
async def root():
    return {"message": "SQL Tutor X-Ray API", "version": "1.0.0"}

@api_router.get("/health")
async def health():
    return {"status": "healthy"}

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

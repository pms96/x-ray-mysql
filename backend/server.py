from fastapi import FastAPI, APIRouter, HTTPException, Response, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
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
import aiomysql
import json
import io
# from emergentintegrations.llm.chat import LlmChat, UserMessage
from openai import AsyncOpenAI

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = "mongodb+srv://xray:2GpEVjbanJ7PU8cH@x-raid-query.femy2lp.mongodb.net/xray?appName=x-raid-query&retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"
client = AsyncIOMotorClient(mongo_url)
db = client["xray"]

print("### MONGO_URL EN RUNTIME ###", mongo_url, flush=True)

# OpenAI Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# ==================== FASTAPI APP ====================

app = FastAPI()  # <--- MOVER AQUÍ ARRIBA
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MySQLConnection(BaseModel):
    host: str
    port: int = 3306
    user: str
    password: str
    database: str
    ssl: bool = True

class DatabaseAnalysisRequest(BaseModel):
    connection: MySQLConnection
    include_intelligence: bool = True
    include_optimizer_trust: bool = True
    include_growth_simulation: bool = True
    growth_factors: List[int] = [10, 100]

class IndexRecommendation(BaseModel):
    table: str
    columns: List[str]
    index_type: str = "BTREE"
    estimated_improvement: str
    write_impact: str
    priority: str

class TableIntelligence(BaseModel):
    table_name: str
    size_mb: float
    row_count: int
    issues: List[Dict[str, Any]]
    recommendations: List[str]

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
    dialect: str = "mysql"
    schemas: Optional[List[TableSchema]] = []
    explain_output: Optional[str] = None
    mode: str = "advanced"
    growth_simulation: Optional[str] = None
    connection: Optional[MySQLConnection] = None

class SavedQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    query: str
    dialect: str
    schemas: Optional[List[Dict]] = []
    analysis_result: Optional[Dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ==================== MYSQL CONNECTION POOL ====================

async def get_mysql_connection(conn: MySQLConnection):
    """Create MySQL connection with SSL for Cloud SQL"""
    try:
        ssl_context = None
        if conn.ssl:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        connection = await aiomysql.connect(
            host=conn.host,
            port=conn.port,
            user=conn.user,
            password=conn.password,
            db=conn.database,
            ssl=ssl_context,
            autocommit=True,
            cursorclass=aiomysql.DictCursor
        )
        return connection
    except Exception as e:
        logger.error(f"MySQL connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# ==================== DATABASE INTELLIGENCE LAYER ====================

async def analyze_database_intelligence(conn: MySQLConnection) -> Dict[str, Any]:
    """Module 1: Database Intelligence Layer - Detect structural risks"""
    mysql_conn = await get_mysql_connection(conn)
    
    try:
        async with mysql_conn.cursor() as cursor:
            findings = []
            
            # 1. Detect large tables (> 1GB)
            await cursor.execute("""
                SELECT 
                    TABLE_NAME,
                    ROUND(DATA_LENGTH / 1024 / 1024, 2) as data_mb,
                    ROUND(INDEX_LENGTH / 1024 / 1024, 2) as index_mb,
                    TABLE_ROWS
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY DATA_LENGTH DESC
            """, (conn.database,))
            tables = await cursor.fetchall()
            
            for table in tables:
                table_issues = []
                table_name = table['TABLE_NAME']
                size_mb = float(table['data_mb'] or 0)
                row_count = int(table['TABLE_ROWS'] or 0)
                
                # Large table detection
                if size_mb > 1024:
                    table_issues.append({
                        "type": "large_table",
                        "severity": "critical" if size_mb > 10240 else "high",
                        "message": f"Table is {size_mb:.0f}MB - consider partitioning",
                        "metric": {"size_mb": size_mb}
                    })
                
                # 2. Check for missing partitions on large tables
                await cursor.execute("""
                    SELECT PARTITION_NAME 
                    FROM information_schema.PARTITIONS 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """, (conn.database, table_name))
                partitions = await cursor.fetchall()
                
                if size_mb > 500 and (not partitions or partitions[0]['PARTITION_NAME'] is None):
                    table_issues.append({
                        "type": "missing_partition",
                        "severity": "high",
                        "message": f"Large table ({size_mb:.0f}MB) without partitioning",
                        "recommendation": "Consider date-based or hash partitioning"
                    })
                
                # 3. Check indexes
                await cursor.execute("""
                    SELECT 
                        INDEX_NAME,
                        GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as columns,
                        NON_UNIQUE,
                        CARDINALITY
                    FROM information_schema.STATISTICS 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    GROUP BY INDEX_NAME, NON_UNIQUE, CARDINALITY
                """, (conn.database, table_name))
                indexes = await cursor.fetchall()
                
                # Detect redundant indexes
                index_cols = [idx['columns'] for idx in indexes]
                for i, cols1 in enumerate(index_cols):
                    for j, cols2 in enumerate(index_cols):
                        if i != j and cols2 and cols1 and cols2.startswith(cols1 + ','):
                            table_issues.append({
                                "type": "redundant_index",
                                "severity": "medium",
                                "message": f"Index on ({cols1}) is prefix of ({cols2})",
                                "recommendation": "Consider removing redundant index"
                            })
                
                # 4. Check foreign keys without indexes
                await cursor.execute("""
                    SELECT 
                        kcu.COLUMN_NAME,
                        kcu.CONSTRAINT_NAME,
                        kcu.REFERENCED_TABLE_NAME
                    FROM information_schema.KEY_COLUMN_USAGE kcu
                    WHERE kcu.TABLE_SCHEMA = %s 
                    AND kcu.TABLE_NAME = %s
                    AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
                """, (conn.database, table_name))
                fks = await cursor.fetchall()
                
                indexed_cols = set()
                for idx in indexes:
                    if idx['columns']:
                        indexed_cols.add(idx['columns'].split(',')[0])
                
                for fk in fks:
                    if fk['COLUMN_NAME'] not in indexed_cols:
                        table_issues.append({
                            "type": "fk_without_index",
                            "severity": "high",
                            "message": f"Foreign key {fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_NAME']} has no index",
                            "recommendation": f"CREATE INDEX idx_{fk['COLUMN_NAME']} ON {table_name}({fk['COLUMN_NAME']})"
                        })
                
                # 5. Check column cardinality vs indexes
                await cursor.execute("""
                    SELECT 
                        COLUMN_NAME,
                        DATA_TYPE,
                        IS_NULLABLE
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """, (conn.database, table_name))
                columns = await cursor.fetchall()
                
                if row_count > 10000:
                    for col in columns:
                        col_name = col['COLUMN_NAME']
                        if col_name not in indexed_cols and col['DATA_TYPE'] in ['int', 'bigint', 'varchar', 'datetime']:
                            # Check cardinality via sample
                            try:
                                await cursor.execute(f"""
                                    SELECT COUNT(DISTINCT `{col_name}`) as card 
                                    FROM `{table_name}` LIMIT 100000
                                """)
                                card_result = await cursor.fetchone()
                                cardinality = card_result['card'] if card_result else 0
                                
                                if cardinality > row_count * 0.1 and cardinality > 1000:
                                    table_issues.append({
                                        "type": "high_cardinality_no_index",
                                        "severity": "medium",
                                        "message": f"Column {col_name} has high cardinality ({cardinality:,}) but no index",
                                        "metric": {"cardinality": cardinality, "selectivity": cardinality / row_count if row_count > 0 else 0}
                                    })
                            except:
                                pass
                
                if table_issues:
                    findings.append({
                        "table_name": table_name,
                        "size_mb": size_mb,
                        "row_count": row_count,
                        "issues": table_issues,
                        "issue_count": len(table_issues),
                        "max_severity": max([i['severity'] for i in table_issues], key=lambda x: {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}[x])
                    })
            
            # Sort by severity
            severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            findings.sort(key=lambda x: severity_order.get(x['max_severity'], 4))
            
            return {
                "total_tables": len(tables),
                "tables_with_issues": len(findings),
                "findings": findings,
                "summary": {
                    "critical": len([f for f in findings if f['max_severity'] == 'critical']),
                    "high": len([f for f in findings if f['max_severity'] == 'high']),
                    "medium": len([f for f in findings if f['max_severity'] == 'medium']),
                    "low": len([f for f in findings if f['max_severity'] == 'low'])
                }
            }
    finally:
        mysql_conn.close()

# ==================== OPTIMIZER TRUST ANALYZER ====================

async def analyze_optimizer_trust(conn: MySQLConnection, query: str) -> Dict[str, Any]:
    """Module 2: Compare estimated vs actual rows, detect estimation errors"""
    mysql_conn = await get_mysql_connection(conn)
    
    try:
        async with mysql_conn.cursor() as cursor:
            # Get EXPLAIN output
            await cursor.execute(f"EXPLAIN FORMAT=JSON {query}")
            explain_result = await cursor.fetchone()
            explain_json = json.loads(list(explain_result.values())[0]) if explain_result else {}
            
            # Try EXPLAIN ANALYZE if available (MySQL 8.0.18+)
            analyze_result = None
            try:
                await cursor.execute(f"EXPLAIN ANALYZE {query}")
                analyze_rows = await cursor.fetchall()
                analyze_result = analyze_rows
            except Exception as e:
                logger.warning(f"EXPLAIN ANALYZE not available: {e}")
            
            trust_issues = []
            optimizer_stats = []
            
            def extract_plan_nodes(plan, depth=0):
                nodes = []
                if isinstance(plan, dict):
                    node = {
                        "depth": depth,
                        "table": plan.get('table_name', plan.get('table', 'N/A')),
                        "access_type": plan.get('access_type', 'N/A'),
                        "rows_estimated": plan.get('rows_examined_per_scan', plan.get('rows', 0)),
                        "filtered": plan.get('filtered', 100),
                        "cost": plan.get('cost_info', {}).get('read_cost', 'N/A'),
                        "key": plan.get('key', plan.get('possible_keys', 'N/A'))
                    }
                    nodes.append(node)
                    
                    for key in ['nested_loop', 'table', 'query_block', 'ordering_operation', 'grouping_operation']:
                        if key in plan:
                            child = plan[key]
                            if isinstance(child, list):
                                for item in child:
                                    nodes.extend(extract_plan_nodes(item, depth + 1))
                            else:
                                nodes.extend(extract_plan_nodes(child, depth + 1))
                return nodes
            
            if explain_json:
                query_block = explain_json.get('query_block', {})
                plan_nodes = extract_plan_nodes(query_block)
                
                for node in plan_nodes:
                    est_rows = node.get('rows_estimated', 0)
                    
                    # If we have ANALYZE results, compare
                    if analyze_result:
                        # Parse actual rows from ANALYZE output
                        for row in analyze_result:
                            row_str = str(list(row.values())[0]) if row else ""
                            if 'actual' in row_str.lower():
                                import re
                                actual_match = re.search(r'actual[^\d]*(\d+)', row_str, re.I)
                                if actual_match:
                                    actual_rows = int(actual_match.group(1))
                                    if est_rows > 0:
                                        error_ratio = actual_rows / est_rows if est_rows != 0 else float('inf')
                                        
                                        if error_ratio > 10 or error_ratio < 0.1:
                                            trust_issues.append({
                                                "type": "estimation_error",
                                                "severity": "high" if error_ratio > 100 else "medium",
                                                "table": node['table'],
                                                "estimated_rows": est_rows,
                                                "actual_rows": actual_rows,
                                                "error_ratio": round(error_ratio, 2),
                                                "message": f"Estimation error {error_ratio:.1f}x - statistics may be stale",
                                                "recommendations": [
                                                    f"ANALYZE TABLE {node['table']}",
                                                    "Consider creating histogram statistics",
                                                    "Review index statistics"
                                                ]
                                            })
                    
                    optimizer_stats.append(node)
            
            # Check for problematic access types
            for stat in optimizer_stats:
                if stat['access_type'] in ['ALL', 'index']:
                    trust_issues.append({
                        "type": "full_scan",
                        "severity": "high" if stat['access_type'] == 'ALL' else "medium",
                        "table": stat['table'],
                        "access_type": stat['access_type'],
                        "message": f"Full {'table' if stat['access_type'] == 'ALL' else 'index'} scan detected",
                        "recommendation": "Consider adding appropriate indexes"
                    })
            
            return {
                "explain_json": explain_json,
                "optimizer_stats": optimizer_stats,
                "trust_issues": trust_issues,
                "trust_score": max(0, 100 - len(trust_issues) * 15),
                "recommendations": list(set([
                    rec for issue in trust_issues 
                    for rec in (issue.get('recommendations', []) if isinstance(issue.get('recommendations'), list) else [issue.get('recommendation', '')])
                    if rec
                ]))
            }
    except Exception as e:
        logger.error(f"Optimizer trust analysis error: {e}")
        return {"error": str(e), "trust_issues": [], "trust_score": 50}
    finally:
        mysql_conn.close()

# ==================== GROWTH SIMULATION ENGINE ====================

async def simulate_growth(conn: MySQLConnection, query: str, factors: List[int] = [10, 100]) -> Dict[str, Any]:
    """Module 3: Simulate query behavior at 10x, 100x scale"""
    mysql_conn = await get_mysql_connection(conn)
    
    try:
        async with mysql_conn.cursor() as cursor:
            # Get current table sizes
            await cursor.execute(f"EXPLAIN FORMAT=JSON {query}")
            explain_result = await cursor.fetchone()
            explain_json = json.loads(list(explain_result.values())[0]) if explain_result else {}
            
            # Extract tables and their current row counts
            tables_in_query = []
            
            def find_tables(plan):
                tables = []
                if isinstance(plan, dict):
                    if 'table_name' in plan:
                        tables.append({
                            'name': plan['table_name'],
                            'rows': plan.get('rows_examined_per_scan', plan.get('rows', 0)),
                            'access_type': plan.get('access_type', 'unknown')
                        })
                    for value in plan.values():
                        if isinstance(value, (dict, list)):
                            tables.extend(find_tables(value))
                elif isinstance(plan, list):
                    for item in plan:
                        tables.extend(find_tables(item))
                return tables
            
            tables_in_query = find_tables(explain_json)
            
            simulations = {}
            
            for factor in factors:
                sim_results = {
                    "factor": factor,
                    "tables": [],
                    "risks": [],
                    "estimated_time_increase": 1.0,
                    "scalability_score": 100
                }
                
                total_risk_score = 0
                
                for table in tables_in_query:
                    current_rows = table.get('rows', 0)
                    projected_rows = current_rows * factor
                    access_type = table.get('access_type', 'unknown')
                    
                    # Calculate complexity based on access type
                    time_complexity = 1.0
                    risk_level = "low"
                    risk_message = ""
                    
                    if access_type == 'ALL':
                        # Full table scan - O(n)
                        time_complexity = factor
                        risk_level = "critical"
                        risk_message = f"Full scan will examine {projected_rows:,} rows"
                        total_risk_score += 40
                    elif access_type == 'index':
                        # Index scan - O(n)
                        time_complexity = factor
                        risk_level = "high"
                        risk_message = f"Index scan scales linearly to {projected_rows:,} rows"
                        total_risk_score += 25
                    elif access_type == 'range':
                        # Range scan - O(k) where k is range size
                        time_complexity = factor ** 0.5
                        risk_level = "medium"
                        risk_message = "Range scan - moderate scaling"
                        total_risk_score += 10
                    elif access_type in ['ref', 'eq_ref']:
                        # Index lookup - O(log n)
                        time_complexity = 1 + (0.1 * (factor ** 0.3))
                        risk_level = "low"
                        risk_message = "Index lookup - logarithmic scaling"
                        total_risk_score += 5
                    elif access_type == 'const':
                        time_complexity = 1.0
                        risk_level = "low"
                        risk_message = "Constant time access"
                    
                    sim_results["tables"].append({
                        "table": table['name'],
                        "current_rows": current_rows,
                        "projected_rows": projected_rows,
                        "access_type": access_type,
                        "time_complexity_factor": round(time_complexity, 2),
                        "risk_level": risk_level,
                        "risk_message": risk_message
                    })
                    
                    sim_results["estimated_time_increase"] *= time_complexity
                
                # Add specific risks
                if sim_results["estimated_time_increase"] > factor:
                    sim_results["risks"].append({
                        "type": "super_linear_scaling",
                        "severity": "critical",
                        "message": f"Query time will increase {sim_results['estimated_time_increase']:.0f}x (worse than data growth)",
                        "recommendation": "Refactor to eliminate nested loops or full scans"
                    })
                
                if any(t['access_type'] == 'ALL' for t in sim_results["tables"]):
                    sim_results["risks"].append({
                        "type": "full_scan_at_scale",
                        "severity": "critical",
                        "message": "Full table scan will become prohibitive at scale",
                        "recommendation": "Add covering indexes or rewrite query"
                    })
                
                sim_results["scalability_score"] = max(0, 100 - total_risk_score)
                sim_results["estimated_time_increase"] = round(sim_results["estimated_time_increase"], 1)
                
                simulations[f"{factor}x"] = sim_results
            
            return {
                "current_state": {
                    "tables": tables_in_query,
                    "explain": explain_json
                },
                "simulations": simulations,
                "overall_scalability": min([s['scalability_score'] for s in simulations.values()]) if simulations else 50,
                "critical_bottlenecks": [
                    t['table'] for sim in simulations.values() 
                    for t in sim['tables'] if t['risk_level'] == 'critical'
                ]
            }
    except Exception as e:
        logger.error(f"Growth simulation error: {e}")
        return {"error": str(e), "simulations": {}}
    finally:
        mysql_conn.close()

# ==================== INDEX IMPACT SIMULATOR ====================

async def simulate_index_impact(conn: MySQLConnection, query: str, proposed_indexes: List[Dict]) -> Dict[str, Any]:
    """Module 4: Estimate impact of proposed indexes"""
    mysql_conn = await get_mysql_connection(conn)
    
    try:
        async with mysql_conn.cursor() as cursor:
            # Get current EXPLAIN
            await cursor.execute(f"EXPLAIN FORMAT=JSON {query}")
            before_result = await cursor.fetchone()
            before_explain = json.loads(list(before_result.values())[0]) if before_result else {}
            
            impact_analysis = []
            
            for idx in proposed_indexes:
                table = idx.get('table', '')
                columns = idx.get('columns', [])
                
                # Get current table stats
                await cursor.execute("""
                    SELECT TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH
                    FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """, (conn.database, table))
                table_stats = await cursor.fetchone()
                
                row_count = table_stats['TABLE_ROWS'] if table_stats else 0
                current_index_size = table_stats['INDEX_LENGTH'] if table_stats else 0
                
                # Estimate index size (rough: ~10 bytes per row per indexed column)
                estimated_index_size = row_count * len(columns) * 10
                
                # Get column cardinality
                cardinality_info = []
                for col in columns:
                    try:
                        await cursor.execute(f"""
                            SELECT COUNT(DISTINCT `{col}`) as card 
                            FROM `{table}` LIMIT 100000
                        """)
                        result = await cursor.fetchone()
                        cardinality_info.append({
                            "column": col,
                            "cardinality": result['card'] if result else 0,
                            "selectivity": (result['card'] / row_count * 100) if result and row_count > 0 else 0
                        })
                    except:
                        cardinality_info.append({"column": col, "cardinality": "unknown"})
                
                # Estimate improvement
                avg_selectivity = sum([c.get('selectivity', 0) for c in cardinality_info]) / len(cardinality_info) if cardinality_info else 0
                
                if avg_selectivity > 50:
                    estimated_improvement = "high"
                    rows_reduction = "90%+"
                    access_type_change = "ALL -> ref/range"
                elif avg_selectivity > 10:
                    estimated_improvement = "medium"
                    rows_reduction = "50-90%"
                    access_type_change = "ALL -> range"
                else:
                    estimated_improvement = "low"
                    rows_reduction = "<50%"
                    access_type_change = "Minimal change expected"
                
                # Write impact analysis
                write_impact = "low"
                if len(columns) > 3:
                    write_impact = "high"
                elif len(columns) > 1:
                    write_impact = "medium"
                
                impact_analysis.append({
                    "index": {
                        "table": table,
                        "columns": columns,
                        "proposed_ddl": f"CREATE INDEX idx_{table}_{'_'.join(columns)} ON {table}({', '.join(columns)})"
                    },
                    "before": {
                        "access_type": "ALL (assumed)",
                        "rows_examined": row_count
                    },
                    "after_estimated": {
                        "access_type_change": access_type_change,
                        "rows_reduction": rows_reduction,
                        "estimated_improvement": estimated_improvement
                    },
                    "cardinality": cardinality_info,
                    "costs": {
                        "estimated_index_size_mb": round(estimated_index_size / 1024 / 1024, 2),
                        "write_impact": write_impact,
                        "maintenance_overhead": "ANALYZE TABLE recommended after creation"
                    },
                    "recommendation": "Recommended" if estimated_improvement in ["high", "medium"] else "Consider alternatives"
                })
            
            return {
                "before_explain": before_explain,
                "index_impacts": impact_analysis,
                "summary": {
                    "total_proposed": len(proposed_indexes),
                    "recommended": len([i for i in impact_analysis if i['recommendation'] == 'Recommended']),
                    "total_index_size_mb": sum([i['costs']['estimated_index_size_mb'] for i in impact_analysis])
                }
            }
    except Exception as e:
        logger.error(f"Index impact simulation error: {e}")
        return {"error": str(e)}
    finally:
        mysql_conn.close()

# ==================== PERFORMANCE MATURITY SCORE ====================

async def calculate_maturity_score(conn: MySQLConnection) -> Dict[str, Any]:
    """Module 5: Calculate overall database performance maturity score (0-100)"""
    mysql_conn = await get_mysql_connection(conn)
    
    try:
        async with mysql_conn.cursor() as cursor:
            scores = {
                "index_usage": {"score": 0, "max": 25, "details": []},
                "query_patterns": {"score": 0, "max": 25, "details": []},
                "partitioning": {"score": 0, "max": 20, "details": []},
                "statistics_health": {"score": 0, "max": 15, "details": []},
                "anti_patterns": {"score": 0, "max": 15, "details": []}
            }
            
            # 1. Index Usage Score (25 points)
            await cursor.execute("""
                SELECT 
                    COUNT(*) as total_tables,
                    SUM(CASE WHEN idx_count > 0 THEN 1 ELSE 0 END) as indexed_tables
                FROM (
                    SELECT t.TABLE_NAME, COUNT(s.INDEX_NAME) as idx_count
                    FROM information_schema.TABLES t
                    LEFT JOIN information_schema.STATISTICS s 
                        ON t.TABLE_SCHEMA = s.TABLE_SCHEMA AND t.TABLE_NAME = s.TABLE_NAME
                    WHERE t.TABLE_SCHEMA = %s AND t.TABLE_TYPE = 'BASE TABLE'
                    GROUP BY t.TABLE_NAME
                ) sub
            """, (conn.database,))
            idx_result = await cursor.fetchone()
            
            if idx_result and idx_result['total_tables'] > 0:
                idx_ratio = idx_result['indexed_tables'] / idx_result['total_tables']
                scores["index_usage"]["score"] = int(idx_ratio * 25)
                scores["index_usage"]["details"].append(f"{idx_result['indexed_tables']}/{idx_result['total_tables']} tables have indexes")
            
            # 2. Query Patterns Score (check for common issues) - 25 points
            # Check performance_schema if available
            try:
                await cursor.execute("""
                    SELECT COUNT(*) as slow_queries
                    FROM performance_schema.events_statements_summary_by_digest
                    WHERE AVG_TIMER_WAIT > 1000000000000
                    LIMIT 100
                """)
                slow_result = await cursor.fetchone()
                slow_count = slow_result['slow_queries'] if slow_result else 0
                
                if slow_count == 0:
                    scores["query_patterns"]["score"] = 25
                    scores["query_patterns"]["details"].append("No consistently slow queries detected")
                elif slow_count < 5:
                    scores["query_patterns"]["score"] = 15
                    scores["query_patterns"]["details"].append(f"{slow_count} slow query patterns detected")
                else:
                    scores["query_patterns"]["score"] = 5
                    scores["query_patterns"]["details"].append(f"{slow_count} slow query patterns - needs attention")
            except:
                scores["query_patterns"]["score"] = 12  # Default if can't check
                scores["query_patterns"]["details"].append("Could not analyze query patterns")
            
            # 3. Partitioning Score (20 points)
            await cursor.execute("""
                SELECT 
                    COUNT(DISTINCT TABLE_NAME) as partitioned_tables
                FROM information_schema.PARTITIONS 
                WHERE TABLE_SCHEMA = %s AND PARTITION_NAME IS NOT NULL
            """, (conn.database,))
            part_result = await cursor.fetchone()
            
            await cursor.execute("""
                SELECT COUNT(*) as large_tables
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s AND DATA_LENGTH > 536870912
            """, (conn.database,))
            large_result = await cursor.fetchone()
            
            partitioned = part_result['partitioned_tables'] if part_result else 0
            large_tables = large_result['large_tables'] if large_result else 0
            
            if large_tables == 0:
                scores["partitioning"]["score"] = 20
                scores["partitioning"]["details"].append("No large tables requiring partitioning")
            elif partitioned >= large_tables:
                scores["partitioning"]["score"] = 20
                scores["partitioning"]["details"].append("All large tables are partitioned")
            else:
                scores["partitioning"]["score"] = int((partitioned / max(large_tables, 1)) * 20)
                scores["partitioning"]["details"].append(f"{large_tables - partitioned} large tables need partitioning")
            
            # 4. Statistics Health (15 points)
            try:
                await cursor.execute("""
                    SELECT COUNT(*) as stale_stats
                    FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = %s 
                    AND UPDATE_TIME < DATE_SUB(NOW(), INTERVAL 7 DAY)
                    AND TABLE_ROWS > 10000
                """, (conn.database,))
                stale_result = await cursor.fetchone()
                stale_count = stale_result['stale_stats'] if stale_result else 0
                
                if stale_count == 0:
                    scores["statistics_health"]["score"] = 15
                    scores["statistics_health"]["details"].append("Table statistics are current")
                else:
                    scores["statistics_health"]["score"] = max(0, 15 - stale_count * 2)
                    scores["statistics_health"]["details"].append(f"{stale_count} tables may have stale statistics")
            except:
                scores["statistics_health"]["score"] = 10
                scores["statistics_health"]["details"].append("Could not verify statistics freshness")
            
            # 5. Anti-patterns Score (15 points)
            anti_pattern_count = 0
            
            # Check for tables without primary keys
            await cursor.execute("""
                SELECT t.TABLE_NAME
                FROM information_schema.TABLES t
                LEFT JOIN information_schema.TABLE_CONSTRAINTS tc 
                    ON t.TABLE_SCHEMA = tc.TABLE_SCHEMA 
                    AND t.TABLE_NAME = tc.TABLE_NAME 
                    AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                WHERE t.TABLE_SCHEMA = %s 
                AND t.TABLE_TYPE = 'BASE TABLE'
                AND tc.CONSTRAINT_NAME IS NULL
            """, (conn.database,))
            no_pk = await cursor.fetchall()
            anti_pattern_count += len(no_pk)
            if no_pk:
                scores["anti_patterns"]["details"].append(f"{len(no_pk)} tables without primary key")
            
            scores["anti_patterns"]["score"] = max(0, 15 - anti_pattern_count * 3)
            if anti_pattern_count == 0:
                scores["anti_patterns"]["details"].append("No major anti-patterns detected")
            
            # Calculate total
            total_score = sum([s["score"] for s in scores.values()])
            max_score = sum([s["max"] for s in scores.values()])
            
            # Grade
            if total_score >= 90:
                grade = "A"
                assessment = "Excellent - Production ready for high scale"
            elif total_score >= 75:
                grade = "B"
                assessment = "Good - Minor optimizations recommended"
            elif total_score >= 60:
                grade = "C"
                assessment = "Fair - Several improvements needed"
            elif total_score >= 40:
                grade = "D"
                assessment = "Poor - Significant work required"
            else:
                grade = "F"
                assessment = "Critical - Major restructuring needed"
            
            return {
                "total_score": total_score,
                "max_score": max_score,
                "grade": grade,
                "assessment": assessment,
                "breakdown": scores,
                "priority_actions": [
                    detail for category in scores.values() 
                    for detail in category["details"] 
                    if any(word in detail.lower() for word in ['need', 'stale', 'without', 'attention'])
                ]
            }
    except Exception as e:
        logger.error(f"Maturity score error: {e}")
        return {"error": str(e), "total_score": 0}
    finally:
        mysql_conn.close()

# ==================== EXECUTIVE REPORT GENERATOR ====================

async def generate_executive_report(conn: MySQLConnection, include_all: bool = True) -> Dict[str, Any]:
    """Module 6: Generate comprehensive executive report"""
    
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": conn.database,
        "sections": {}
    }
    
    # Get maturity score
    maturity = await calculate_maturity_score(conn)
    report["sections"]["maturity_score"] = maturity
    
    # Get intelligence findings
    intelligence = await analyze_database_intelligence(conn)
    report["sections"]["database_intelligence"] = intelligence
    
    # Compile executive summary
    critical_count = intelligence.get("summary", {}).get("critical", 0)
    high_count = intelligence.get("summary", {}).get("high", 0)
    
    report["executive_summary"] = {
        "health_grade": maturity.get("grade", "N/A"),
        "health_score": maturity.get("total_score", 0),
        "critical_issues": critical_count,
        "high_priority_issues": high_count,
        "immediate_actions_required": critical_count > 0,
        "assessment": maturity.get("assessment", "")
    }
    
    # Priority action plan
    action_plan = []
    
    for finding in intelligence.get("findings", [])[:10]:
        for issue in finding.get("issues", []):
            if issue.get("severity") in ["critical", "high"]:
                action_plan.append({
                    "priority": 1 if issue["severity"] == "critical" else 2,
                    "table": finding["table_name"],
                    "issue": issue["message"],
                    "recommendation": issue.get("recommendation", "Review and optimize"),
                    "estimated_impact": "High" if issue["severity"] == "critical" else "Medium"
                })
    
    action_plan.sort(key=lambda x: x["priority"])
    report["sections"]["action_plan"] = action_plan[:20]
    
    # Strategic recommendations
    report["sections"]["strategic_recommendations"] = []
    
    if critical_count > 0:
        report["sections"]["strategic_recommendations"].append({
            "category": "Immediate",
            "recommendation": "Address critical issues before any new feature development",
            "rationale": f"{critical_count} critical issues can cause production incidents"
        })
    
    if maturity.get("breakdown", {}).get("partitioning", {}).get("score", 0) < 15:
        report["sections"]["strategic_recommendations"].append({
            "category": "Scalability",
            "recommendation": "Implement table partitioning strategy",
            "rationale": "Large tables without partitioning will become bottlenecks at 10x scale"
        })
    
    if maturity.get("breakdown", {}).get("index_usage", {}).get("score", 0) < 20:
        report["sections"]["strategic_recommendations"].append({
            "category": "Performance",
            "recommendation": "Comprehensive index audit required",
            "rationale": "Missing indexes causing full table scans"
        })
    
    return report

# ==================== AUTH HELPERS (unchanged) ====================

async def get_current_user(request: Request) -> Optional[User]:
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
    
    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    
    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
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
        await db.users.update_one({"email": data["email"]}, {"$set": {"name": data["name"], "picture": data.get("picture")}})
    else:
        await db.users.insert_one({
            "user_id": user_id, "email": data["email"], "name": data["name"],
            "picture": data.get("picture"), "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    session_token = data.get("session_token", str(uuid.uuid4()))
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    await db.user_sessions.insert_one({
        "session_id": str(uuid.uuid4()), "user_id": user_id, "session_token": session_token,
        "expires_at": expires_at.isoformat(), "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    response.set_cookie(key="session_token", value=session_token, httponly=True, secure=True, samesite="none", path="/", max_age=7*24*60*60)
    return {"user_id": user_id, "email": data["email"], "name": data["name"], "picture": data.get("picture")}

@api_router.get("/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user_id": user.user_id, "email": user.email, "name": user.name, "picture": user.picture}

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out"}

# ==================== DATABASE CONNECTION TEST ====================

@api_router.post("/db/test-connection")
async def test_database_connection(conn: MySQLConnection):
    """Test MySQL connection"""
    try:
        mysql_conn = await get_mysql_connection(conn)
        async with mysql_conn.cursor() as cursor:
            await cursor.execute("SELECT VERSION() as version, DATABASE() as db")
            result = await cursor.fetchone()
        mysql_conn.close()
        return {"status": "connected", "version": result['version'], "database": result['db']}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== ENTERPRISE ANALYSIS ENDPOINTS ====================

@api_router.post("/enterprise/intelligence")
async def get_database_intelligence(conn: MySQLConnection):
    """Module 1: Database Intelligence Layer"""
    if not conn.host or not conn.user:
        raise HTTPException(status_code=400, detail="MySQL connection required. Please provide host, user, password, and database.")
    return await analyze_database_intelligence(conn)

@api_router.post("/enterprise/optimizer-trust")
async def get_optimizer_trust(request: Request):
    """Module 2: Optimizer Trust Analyzer"""
    body = await request.json()
    conn = MySQLConnection(**body.get("connection", {}))
    query = body.get("query", "")
    return await analyze_optimizer_trust(conn, query)

@api_router.post("/enterprise/growth-simulation")
async def get_growth_simulation(request: Request):
    """Module 3: Growth Simulation Engine"""
    body = await request.json()
    conn = MySQLConnection(**body.get("connection", {}))
    query = body.get("query", "")
    factors = body.get("factors", [10, 100])
    return await simulate_growth(conn, query, factors)

@api_router.post("/enterprise/index-impact")
async def get_index_impact(request: Request):
    """Module 4: Index Impact Simulator"""
    body = await request.json()
    conn = MySQLConnection(**body.get("connection", {}))
    query = body.get("query", "")
    indexes = body.get("proposed_indexes", [])
    return await simulate_index_impact(conn, query, indexes)

@api_router.post("/enterprise/maturity-score")
async def get_maturity_score(conn: MySQLConnection):
    """Module 5: Performance Maturity Score"""
    if not conn.host or not conn.user:
        raise HTTPException(status_code=400, detail="MySQL connection required. Please provide host, user, password, and database.")
    return await calculate_maturity_score(conn)

@api_router.post("/enterprise/executive-report")
async def get_executive_report(conn: MySQLConnection):
    """Module 6: Executive Report Generator"""
    if not conn.host or not conn.user:
        raise HTTPException(status_code=400, detail="MySQL connection required. Please provide host, user, password, and database.")
    return await generate_executive_report(conn)

@api_router.post("/enterprise/full-analysis")
async def run_full_analysis(request: DatabaseAnalysisRequest):
    """Run complete enterprise analysis"""
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": request.connection.database
    }
    
    if request.include_intelligence:
        results["intelligence"] = await analyze_database_intelligence(request.connection)
    
    results["maturity_score"] = await calculate_maturity_score(request.connection)
    results["executive_report"] = await generate_executive_report(request.connection)
    
    return results

# ==================== SQL ANALYSIS WITH AI (Enhanced) ====================

def build_system_prompt(dialect: str, mode: str) -> str:
    return f"""Eres un experto en MySQL 8 Performance y Arquitectura de Datos para Google Cloud SQL.
Tu rol es analizar queries SQL como un ingeniero senior que trabaja con bases de datos de 500M+ registros.

DIALECTO: MySQL 8.0 (Cloud SQL)
MODO: {mode}

RESPONDE EN JSON con estas secciones:

{{
  "overview": {{
    "summary": "Resumen de la query",
    "granularity": "Nivel de agregación",
    "final_columns": ["columnas"],
    "alerts": [{{"type": "warning|error|info", "message": "descripción", "severity": "low|medium|high|critical"}}],
    "facts_vs_assumptions": {{"facts": [], "assumptions": []}}
  }},
  "logical_vs_physical_order": {{
    "logical_order": [{{"step": 1, "operation": "FROM", "description": ""}}],
    "optimizer_optimizations": [{{"optimization": "", "description": "", "mysql_specific": true}}]
  }},
  "technical_breakdown": {{
    "select": {{"expressions": [], "row_by_row_impact": "", "function_warnings": []}},
    "joins": [{{"type": "", "tables": [], "keys": [], "index_usage": "", "risks": []}}],
    "where": {{"filters": [], "sargable_analysis": [], "function_on_columns": []}},
    "group_by": {{"columns": [], "aggregation_type": "", "memory_spill_risk": ""}},
    "subqueries": [{{"type": "", "risk": "", "rewrite_suggestion": ""}}],
    "window_functions": []
  }},
  "refactor_suggestions": {{
    "pedagogical": {{"query": "", "explanation": ""}},
    "performance_optimized": {{"query": "", "explanation": ""}},
    "high_scale": {{"query": "", "explanation": ""}}
  }},
  "cost_scalability": {{
    "estimated_cost": "low|medium|high|critical",
    "complexity": "O(n)|O(n log n)|O(n²)",
    "growth_simulation": {{"10x": "", "100x": "", "1000x": ""}},
    "index_recommendations": [{{"table": "", "columns": [], "type": "", "reason": ""}}],
    "partition_recommendations": []
  }},
  "architecture": {{
    "missing_pk": [],
    "missing_fk_indexes": [],
    "recommendations": []
  }},
  "testing_validation": {{
    "validation_queries": [{{"purpose": "", "query": ""}}]
  }},
  "mermaid_diagram": "graph TD...",
  "anti_patterns_detected": [{{"pattern": "", "location": "", "severity": "", "fix": ""}}]
}}

Siempre considera: "¿Qué pasa cuando la tabla tenga 100M de filas?"
"""

async def analyze_sql_with_ai(request: SQLAnalysisRequest) -> Dict[str, Any]:
    system_prompt = build_system_prompt(request.dialect, request.mode)
    
    user_prompt = f"Analiza esta query SQL:\n\n```sql\n{request.query}\n```\n\nDIALECTO: {request.dialect}\nMODO: {request.mode}"
    
    if request.schemas:
        user_prompt += "\n\nESQUEMAS:\n"
        for schema in request.schemas:
            user_prompt += f"\nTabla: {schema.table_name}"
            if schema.row_count:
                user_prompt += f" (~{schema.row_count:,} filas)"
    
    if request.explain_output:
        user_prompt += f"\n\nEXPLAIN:\n```\n{request.explain_output}\n```"
    
    # chat = LlmChat(
    #    api_key=EMERGENT_LLM_KEY,
    #    session_id=f"sql_{uuid.uuid4().hex[:8]}",
    #    system_message=system_prompt
    #).with_model("openai", "gpt-5.2")
    
    #response = await chat.send_message(UserMessage(text=user_prompt))
    
    client = AsyncOpenAI(
        api_key=EMERGENT_LLM_KEY,  # Tu API key de Abacus.AI
        base_url="https://routellm.abacus.ai/v1"
    )

    try:
        completion = await client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        response = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"RouteLLM API error: {e}")
        return {"error": f"Error al analizar con IA: {str(e)}"}
        
    import re
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    return {"overview": {"summary": response}, "raw_response": response}

@api_router.post("/analyze")
async def analyze_sql(request: SQLAnalysisRequest):
    try:
        # If connection provided, also get real EXPLAIN
        explain_data = None
        if request.connection:
            try:
                mysql_conn = await get_mysql_connection(request.connection)
                async with mysql_conn.cursor() as cursor:
                    await cursor.execute(f"EXPLAIN FORMAT=JSON {request.query}")
                    result = await cursor.fetchone()
                    explain_data = json.loads(list(result.values())[0]) if result else None
                mysql_conn.close()
            except Exception as e:
                logger.warning(f"Could not get real EXPLAIN: {e}")
        
        result = await analyze_sql_with_ai(request)
        
        if explain_data:
            result["real_explain"] = explain_data
        
        return result
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== QUERY HISTORY ====================

@api_router.post("/queries")
async def save_query(request: Request):
    user = await require_auth(request)
    body = await request.json()
    
    query_doc = {
        "query_id": str(uuid.uuid4()), "user_id": user.user_id, "query": body.get("query"),
        "dialect": body.get("dialect", "mysql"), "schemas": body.get("schemas", []),
        "analysis_result": body.get("analysis_result"), "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.saved_queries.insert_one(query_doc)
    query_doc.pop("_id", None)
    return query_doc

@api_router.get("/queries")
async def get_queries(request: Request):
    user = await require_auth(request)
    return await db.saved_queries.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)

@api_router.delete("/queries/{query_id}")
async def delete_query(query_id: str, request: Request):
    user = await require_auth(request)
    result = await db.saved_queries.delete_one({"query_id": query_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Query not found")
    return {"message": "Query deleted"}

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "SQL Tutor X-Ray Enterprise API", "version": "2.0.0", "edition": "MySQL 8 Enterprise"}

@api_router.get("/health")
async def health():
    return {"status": "healthy"}

app.include_router(api_router)

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

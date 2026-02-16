"""
SQL X-Ray Enterprise - Database Scanner Engine
===============================================
Módulo de escaneo incremental, persistente y reanudable.

Características:
- Procesamiento por lotes (batch)
- Persistencia incremental en MongoDB
- Reanudación automática tras desconexión
- Progreso en tiempo real
- Tolerancia a fallos
- Pool de conexiones con reconexión
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import aiomysql
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# ==================== ENUMS & MODELS ====================

class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ScanType(str, Enum):
    FULL = "full"
    INTELLIGENCE = "intelligence"
    WORKLOAD = "workload"

@dataclass
class ScanProgress:
    scan_id: str
    status: ScanStatus
    total_tables: int
    processed_tables: int
    current_table: Optional[str]
    progress_percentage: float
    started_at: datetime
    updated_at: datetime
    errors: List[Dict]
    estimated_remaining_seconds: Optional[int] = None

@dataclass
class TableScanResult:
    scan_id: str
    table_name: str
    schema_name: str
    size_mb: float
    row_count: int
    data_length: int
    index_length: int
    avg_row_length: int
    auto_increment: Optional[int]
    create_time: Optional[datetime]
    update_time: Optional[datetime]
    columns: List[Dict]
    indexes: List[Dict]
    partitions: List[Dict]
    foreign_keys: List[Dict]
    issues: List[Dict]
    analyzed_at: datetime
    analysis_time_ms: int

# ==================== CONNECTION POOL MANAGER ====================

class MySQLPoolManager:
    """
    Gestor de pool de conexiones MySQL con reconexión automática.
    Maneja errores de conexión y reintentos.
    """
    
    RETRYABLE_ERRORS = [
        2003,  # Can't connect
        2006,  # MySQL server has gone away
        2013,  # Lost connection during query
        2055,  # Lost connection to MySQL server
    ]
    
    def __init__(self, config: Dict, max_connections: int = 5, retry_attempts: int = 3):
        self.config = config
        self.max_connections = max_connections
        self.retry_attempts = retry_attempts
        self.pool: Optional[aiomysql.Pool] = None
        self._lock = asyncio.Lock()
    
    async def get_pool(self) -> aiomysql.Pool:
        """Obtiene o crea el pool de conexiones"""
        if self.pool is None or self.pool.closed:
            async with self._lock:
                if self.pool is None or self.pool.closed:
                    await self._create_pool()
        return self.pool
    
    async def _create_pool(self):
        """Crea un nuevo pool de conexiones"""
        import ssl
        ssl_context = None
        if self.config.get('ssl', True):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        self.pool = await aiomysql.create_pool(
            host=self.config['host'],
            port=self.config.get('port', 3306),
            user=self.config['user'],
            password=self.config['password'],
            db=self.config['database'],
            ssl=ssl_context,
            minsize=1,
            maxsize=self.max_connections,
            autocommit=True,
            pool_recycle=300,  # Reciclar conexiones cada 5 min
            connect_timeout=30,
            cursorclass=aiomysql.DictCursor
        )
        logger.info(f"MySQL pool created: {self.config['host']}/{self.config['database']}")
    
    async def execute_with_retry(self, query: str, params: tuple = None, timeout: int = 60) -> List[Dict]:
        """Ejecuta query con reintentos automáticos"""
        last_error = None
        
        for attempt in range(self.retry_attempts):
            try:
                pool = await self.get_pool()
                async with pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await asyncio.wait_for(
                            cursor.execute(query, params),
                            timeout=timeout
                        )
                        result = await cursor.fetchall()
                        return list(result) if result else []
            
            except asyncio.TimeoutError:
                logger.warning(f"Query timeout (attempt {attempt + 1}/{self.retry_attempts})")
                last_error = Exception(f"Query timeout after {timeout}s")
                await self._handle_connection_error()
            
            except aiomysql.Error as e:
                error_code = e.args[0] if e.args else 0
                logger.warning(f"MySQL error {error_code} (attempt {attempt + 1}): {e}")
                last_error = e
                
                if error_code in self.RETRYABLE_ERRORS:
                    await self._handle_connection_error()
                    await asyncio.sleep(min(2 ** attempt, 10))  # Exponential backoff
                else:
                    raise
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                last_error = e
                await self._handle_connection_error()
        
        raise last_error or Exception("Max retries exceeded")
    
    async def _handle_connection_error(self):
        """Maneja errores de conexión cerrando el pool"""
        if self.pool:
            try:
                self.pool.close()
                await self.pool.wait_closed()
            except:
                pass
            self.pool = None
    
    async def close(self):
        """Cierra el pool de conexiones"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None

# ==================== SCAN PERSISTENCE ====================

class ScanPersistence:
    """
    Gestiona la persistencia incremental de scans en MongoDB.
    Permite reanudación tras fallos.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.scans_collection = db.database_scans
        self.tables_collection = db.scan_tables
        self.logs_collection = db.scan_logs
    
    async def create_scan(self, scan_id: str, scan_type: ScanType, database: str, 
                          total_tables: int, connection_info: Dict) -> Dict:
        """Crea un nuevo registro de scan"""
        scan_doc = {
            "scan_id": scan_id,
            "scan_type": scan_type.value,
            "database": database,
            "status": ScanStatus.PENDING.value,
            "total_tables": total_tables,
            "processed_tables": 0,
            "current_table": None,
            "progress_percentage": 0.0,
            "started_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "completed_at": None,
            "last_processed_table": None,
            "errors": [],
            "connection_host": connection_info.get('host'),
            "stats": {
                "total_size_mb": 0,
                "total_rows": 0,
                "total_indexes": 0,
                "issues_found": 0
            }
        }
        await self.scans_collection.insert_one(scan_doc)
        return scan_doc
    
    async def get_scan(self, scan_id: str) -> Optional[Dict]:
        """Obtiene el estado actual de un scan"""
        return await self.scans_collection.find_one(
            {"scan_id": scan_id}, 
            {"_id": 0}
        )
    
    async def update_scan_progress(self, scan_id: str, current_table: str, 
                                   processed: int, total: int, stats_delta: Dict = None):
        """Actualiza el progreso del scan"""
        update = {
            "$set": {
                "current_table": current_table,
                "processed_tables": processed,
                "progress_percentage": round((processed / total) * 100, 2) if total > 0 else 0,
                "last_processed_table": current_table,
                "updated_at": datetime.now(timezone.utc),
                "status": ScanStatus.RUNNING.value
            }
        }
        
        if stats_delta:
            for key, value in stats_delta.items():
                update["$inc"] = update.get("$inc", {})
                update["$inc"][f"stats.{key}"] = value
        
        await self.scans_collection.update_one({"scan_id": scan_id}, update)
    
    async def save_table_result(self, result: TableScanResult):
        """Guarda el resultado del análisis de una tabla (incremental)"""
        doc = asdict(result)
        doc["analyzed_at"] = result.analyzed_at.isoformat()
        
        # Upsert para idempotencia
        await self.tables_collection.update_one(
            {"scan_id": result.scan_id, "table_name": result.table_name},
            {"$set": doc},
            upsert=True
        )
    
    async def get_processed_tables(self, scan_id: str) -> set:
        """Obtiene las tablas ya procesadas (para reanudación)"""
        cursor = self.tables_collection.find(
            {"scan_id": scan_id},
            {"table_name": 1, "_id": 0}
        )
        tables = await cursor.to_list(length=10000)
        return {t["table_name"] for t in tables}
    
    async def mark_scan_completed(self, scan_id: str):
        """Marca el scan como completado"""
        await self.scans_collection.update_one(
            {"scan_id": scan_id},
            {"$set": {
                "status": ScanStatus.COMPLETED.value,
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "current_table": None
            }}
        )
    
    async def mark_scan_failed(self, scan_id: str, error: str):
        """Marca el scan como fallido"""
        await self.scans_collection.update_one(
            {"scan_id": scan_id},
            {
                "$set": {
                    "status": ScanStatus.FAILED.value,
                    "updated_at": datetime.now(timezone.utc)
                },
                "$push": {
                    "errors": {
                        "message": error,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
        )
    
    async def add_table_error(self, scan_id: str, table_name: str, error: str):
        """Registra un error en una tabla específica (sin detener el scan)"""
        await self.scans_collection.update_one(
            {"scan_id": scan_id},
            {
                "$push": {
                    "errors": {
                        "table": table_name,
                        "message": error,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
        )
    
    async def log_event(self, scan_id: str, event_type: str, message: str, data: Dict = None):
        """Registra un evento en el log de scan"""
        await self.logs_collection.insert_one({
            "scan_id": scan_id,
            "event_type": event_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc)
        })
    
    async def get_scan_results(self, scan_id: str) -> List[Dict]:
        """Obtiene todos los resultados de tablas de un scan"""
        cursor = self.tables_collection.find(
            {"scan_id": scan_id},
            {"_id": 0}
        ).sort("size_mb", -1)
        return await cursor.to_list(length=10000)

# ==================== TABLE INTROSPECTOR ====================

class TableIntrospector:
    """
    Lee información real de tablas desde INFORMATION_SCHEMA.
    NUNCA asume nombres - siempre introspección real.
    """
    
    def __init__(self, pool_manager: MySQLPoolManager):
        self.pool = pool_manager
    
    async def get_real_tables(self, database: str) -> List[Dict]:
        """
        Obtiene la lista REAL de tablas desde INFORMATION_SCHEMA.
        Esta es la fuente de verdad - no asumimos nada.
        """
        query = """
            SELECT 
                TABLE_NAME as table_name,
                TABLE_TYPE as table_type,
                ENGINE as engine,
                TABLE_ROWS as row_count,
                ROUND(DATA_LENGTH / 1024 / 1024, 2) as data_mb,
                ROUND(INDEX_LENGTH / 1024 / 1024, 2) as index_mb,
                ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as total_mb,
                AUTO_INCREMENT as auto_increment,
                CREATE_TIME as create_time,
                UPDATE_TIME as update_time,
                TABLE_COLLATION as collation
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY DATA_LENGTH DESC
        """
        return await self.pool.execute_with_retry(query, (database,))
    
    async def get_table_columns(self, database: str, table_name: str) -> List[Dict]:
        """Obtiene las columnas reales de una tabla"""
        query = """
            SELECT 
                COLUMN_NAME as column_name,
                ORDINAL_POSITION as position,
                COLUMN_DEFAULT as default_value,
                IS_NULLABLE as is_nullable,
                DATA_TYPE as data_type,
                CHARACTER_MAXIMUM_LENGTH as max_length,
                NUMERIC_PRECISION as numeric_precision,
                NUMERIC_SCALE as numeric_scale,
                COLUMN_TYPE as column_type,
                COLUMN_KEY as column_key,
                EXTRA as extra,
                COLUMN_COMMENT as comment
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        return await self.pool.execute_with_retry(query, (database, table_name))
    
    async def get_table_indexes(self, database: str, table_name: str) -> List[Dict]:
        """Obtiene los índices reales de una tabla"""
        query = """
            SELECT 
                INDEX_NAME as index_name,
                NON_UNIQUE as non_unique,
                SEQ_IN_INDEX as seq_in_index,
                COLUMN_NAME as column_name,
                COLLATION as collation,
                CARDINALITY as cardinality,
                SUB_PART as sub_part,
                NULLABLE as nullable,
                INDEX_TYPE as index_type,
                COMMENT as comment
            FROM information_schema.STATISTICS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """
        results = await self.pool.execute_with_retry(query, (database, table_name))
        
        # Agrupar por índice
        indexes = {}
        for row in results:
            idx_name = row['index_name']
            if idx_name not in indexes:
                indexes[idx_name] = {
                    "name": idx_name,
                    "unique": not row['non_unique'],
                    "type": row['index_type'],
                    "columns": [],
                    "cardinality": row['cardinality']
                }
            indexes[idx_name]["columns"].append({
                "name": row['column_name'],
                "seq": row['seq_in_index'],
                "sub_part": row['sub_part']
            })
        
        return list(indexes.values())
    
    async def get_table_partitions(self, database: str, table_name: str) -> List[Dict]:
        """Obtiene las particiones de una tabla"""
        query = """
            SELECT 
                PARTITION_NAME as partition_name,
                PARTITION_ORDINAL_POSITION as position,
                PARTITION_METHOD as method,
                PARTITION_EXPRESSION as expression,
                PARTITION_DESCRIPTION as description,
                TABLE_ROWS as rows,
                DATA_LENGTH as data_length
            FROM information_schema.PARTITIONS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            AND PARTITION_NAME IS NOT NULL
        """
        return await self.pool.execute_with_retry(query, (database, table_name))
    
    async def get_foreign_keys(self, database: str, table_name: str) -> List[Dict]:
        """Obtiene las foreign keys de una tabla"""
        query = """
            SELECT 
                kcu.CONSTRAINT_NAME as constraint_name,
                kcu.COLUMN_NAME as column_name,
                kcu.REFERENCED_TABLE_NAME as referenced_table,
                kcu.REFERENCED_COLUMN_NAME as referenced_column,
                rc.UPDATE_RULE as on_update,
                rc.DELETE_RULE as on_delete
            FROM information_schema.KEY_COLUMN_USAGE kcu
            JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
                ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                AND kcu.TABLE_SCHEMA = rc.CONSTRAINT_SCHEMA
            WHERE kcu.TABLE_SCHEMA = %s 
            AND kcu.TABLE_NAME = %s
            AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        """
        return await self.pool.execute_with_retry(query, (database, table_name))
    
    async def build_table_dictionary(self, database: str) -> Dict[str, Dict]:
        """
        Construye un diccionario completo de tablas reales.
        ESTA ES LA FUENTE DE VERDAD para el Módulo 3.
        """
        tables = await self.get_real_tables(database)
        
        table_dict = {}
        for table in tables:
            table_name = table['table_name']
            table_dict[table_name] = {
                "exists": True,
                "row_count": table['row_count'],
                "size_mb": float(table['total_mb'] or 0),
                "engine": table['engine'],
                "create_time": table['create_time'].isoformat() if table['create_time'] else None
            }
        
        return table_dict

# ==================== DATABASE SCANNER ENGINE ====================

class DatabaseScannerEngine:
    """
    Motor de escaneo de base de datos.
    
    Características:
    - Procesamiento incremental por lotes
    - Persistencia inmediata en MongoDB
    - Reanudación automática
    - Tolerante a fallos
    - Progreso en tiempo real
    """
    
    BATCH_SIZE = 10  # Tablas por batch
    TABLE_TIMEOUT = 120  # Segundos por tabla
    
    def __init__(self, pool_manager: MySQLPoolManager, 
                 persistence: ScanPersistence,
                 introspector: TableIntrospector):
        self.pool = pool_manager
        self.persistence = persistence
        self.introspector = introspector
        self._cancel_flag = False
    
    async def start_scan(self, database: str, connection_info: Dict, 
                         scan_type: ScanType = ScanType.INTELLIGENCE,
                         resume_scan_id: str = None) -> str:
        """
        Inicia un nuevo scan o reanuda uno existente.
        
        Args:
            database: Nombre de la base de datos
            connection_info: Info de conexión para logs
            scan_type: Tipo de scan
            resume_scan_id: ID de scan a reanudar (opcional)
        
        Returns:
            scan_id del proceso
        """
        self._cancel_flag = False
        
        # Obtener lista real de tablas
        tables = await self.introspector.get_real_tables(database)
        total_tables = len(tables)
        
        if total_tables == 0:
            raise ValueError(f"No tables found in database {database}")
        
        # Crear o recuperar scan
        if resume_scan_id:
            scan = await self.persistence.get_scan(resume_scan_id)
            if not scan:
                raise ValueError(f"Scan {resume_scan_id} not found")
            scan_id = resume_scan_id
            processed_tables = await self.persistence.get_processed_tables(scan_id)
            logger.info(f"Resuming scan {scan_id}, {len(processed_tables)} tables already processed")
        else:
            scan_id = f"scan_{uuid.uuid4().hex[:12]}"
            await self.persistence.create_scan(
                scan_id, scan_type, database, total_tables, connection_info
            )
            processed_tables = set()
            logger.info(f"Starting new scan {scan_id} for {total_tables} tables")
        
        # Log inicio
        await self.persistence.log_event(
            scan_id, "scan_started", 
            f"Scanning {total_tables} tables in {database}",
            {"total_tables": total_tables, "resume": resume_scan_id is not None}
        )
        
        # Procesar tablas pendientes
        tables_to_process = [t for t in tables if t['table_name'] not in processed_tables]
        
        processed_count = len(processed_tables)
        start_time = datetime.now(timezone.utc)
        
        # Procesar en batches
        for i in range(0, len(tables_to_process), self.BATCH_SIZE):
            if self._cancel_flag:
                await self.persistence.log_event(scan_id, "scan_cancelled", "Scan cancelled by user")
                break
            
            batch = tables_to_process[i:i + self.BATCH_SIZE]
            
            for table_info in batch:
                if self._cancel_flag:
                    break
                
                table_name = table_info['table_name']
                
                try:
                    # Actualizar progreso ANTES de procesar
                    await self.persistence.update_scan_progress(
                        scan_id, table_name, processed_count, total_tables
                    )
                    
                    # Analizar tabla
                    result = await self._analyze_table(
                        scan_id, database, table_name, table_info
                    )
                    
                    # Guardar resultado INMEDIATAMENTE
                    await self.persistence.save_table_result(result)
                    
                    # Actualizar stats
                    await self.persistence.update_scan_progress(
                        scan_id, table_name, processed_count + 1, total_tables,
                        stats_delta={
                            "total_size_mb": result.size_mb,
                            "total_rows": result.row_count,
                            "total_indexes": len(result.indexes),
                            "issues_found": len(result.issues)
                        }
                    )
                    
                    processed_count += 1
                    
                    logger.info(f"[{processed_count}/{total_tables}] Analyzed {table_name}")
                
                except Exception as e:
                    # Error en tabla individual - NO detenemos el scan
                    error_msg = str(e)
                    logger.error(f"Error analyzing {table_name}: {error_msg}")
                    await self.persistence.add_table_error(scan_id, table_name, error_msg)
                    processed_count += 1  # Contamos como procesada (con error)
            
            # Pequeña pausa entre batches para no saturar
            await asyncio.sleep(0.1)
        
        # Completar scan
        if not self._cancel_flag:
            await self.persistence.mark_scan_completed(scan_id)
            
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            await self.persistence.log_event(
                scan_id, "scan_completed",
                f"Scan completed in {elapsed:.1f}s",
                {"elapsed_seconds": elapsed, "tables_processed": processed_count}
            )
        
        return scan_id
    
    async def _analyze_table(self, scan_id: str, database: str, 
                             table_name: str, table_info: Dict) -> TableScanResult:
        """Analiza una tabla individual con timeout"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Ejecutar con timeout
            async with asyncio.timeout(self.TABLE_TIMEOUT):
                columns = await self.introspector.get_table_columns(database, table_name)
                indexes = await self.introspector.get_table_indexes(database, table_name)
                partitions = await self.introspector.get_table_partitions(database, table_name)
                foreign_keys = await self.introspector.get_foreign_keys(database, table_name)
        
        except asyncio.TimeoutError:
            # Timeout - crear resultado parcial
            columns, indexes, partitions, foreign_keys = [], [], [], []
            logger.warning(f"Timeout analyzing {table_name}")
        
        # Detectar issues
        issues = self._detect_table_issues(table_info, indexes, partitions, foreign_keys)
        
        elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return TableScanResult(
            scan_id=scan_id,
            table_name=table_name,
            schema_name=database,
            size_mb=float(table_info.get('total_mb') or 0),
            row_count=int(table_info.get('row_count') or 0),
            data_length=int(table_info.get('data_mb', 0) * 1024 * 1024),
            index_length=int(table_info.get('index_mb', 0) * 1024 * 1024),
            avg_row_length=0,
            auto_increment=table_info.get('auto_increment'),
            create_time=table_info.get('create_time'),
            update_time=table_info.get('update_time'),
            columns=columns,
            indexes=indexes,
            partitions=partitions,
            foreign_keys=foreign_keys,
            issues=issues,
            analyzed_at=datetime.now(timezone.utc),
            analysis_time_ms=elapsed_ms
        )
    
    def _detect_table_issues(self, table_info: Dict, indexes: List, 
                             partitions: List, foreign_keys: List) -> List[Dict]:
        """Detecta problemas estructurales en una tabla"""
        issues = []
        size_mb = float(table_info.get('total_mb') or 0)
        row_count = int(table_info.get('row_count') or 0)
        table_name = table_info.get('table_name', '')
        
        # Tabla grande sin partición
        if size_mb > 1024 and not partitions:
            issues.append({
                "type": "large_table_no_partition",
                "severity": "critical" if size_mb > 10240 else "high",
                "message": f"Table is {size_mb:.0f}MB without partitioning",
                "recommendation": "Consider date-based or hash partitioning"
            })
        
        # Sin índices (aparte de PK)
        non_pk_indexes = [i for i in indexes if i.get('name') != 'PRIMARY']
        if row_count > 10000 and not non_pk_indexes:
            issues.append({
                "type": "no_secondary_indexes",
                "severity": "high",
                "message": f"Table has {row_count:,} rows but no secondary indexes",
                "recommendation": "Add indexes for frequently queried columns"
            })
        
        # FK sin índice
        indexed_cols = set()
        for idx in indexes:
            for col in idx.get('columns', []):
                indexed_cols.add(col.get('name'))
        
        for fk in foreign_keys:
            if fk.get('column_name') not in indexed_cols:
                issues.append({
                    "type": "fk_without_index",
                    "severity": "high",
                    "message": f"Foreign key {fk['column_name']} -> {fk['referenced_table']} has no index",
                    "recommendation": f"CREATE INDEX idx_{table_name}_{fk['column_name']} ON {table_name}({fk['column_name']})"
                })
        
        # Índices redundantes
        index_prefixes = []
        for idx in indexes:
            cols = [c['name'] for c in idx.get('columns', [])]
            if cols:
                index_prefixes.append((idx['name'], ','.join(cols)))
        
        for i, (name1, cols1) in enumerate(index_prefixes):
            for j, (name2, cols2) in enumerate(index_prefixes):
                if i != j and cols2.startswith(cols1 + ','):
                    issues.append({
                        "type": "redundant_index",
                        "severity": "medium",
                        "message": f"Index {name1} ({cols1}) is prefix of {name2}",
                        "recommendation": f"Consider removing redundant index {name1}"
                    })
        
        return issues
    
    def cancel(self):
        """Cancela el scan actual"""
        self._cancel_flag = True
    
    async def get_progress(self, scan_id: str) -> Optional[ScanProgress]:
        """Obtiene el progreso actual de un scan"""
        scan = await self.persistence.get_scan(scan_id)
        if not scan:
            return None
        
        return ScanProgress(
            scan_id=scan_id,
            status=ScanStatus(scan['status']),
            total_tables=scan['total_tables'],
            processed_tables=scan['processed_tables'],
            current_table=scan.get('current_table'),
            progress_percentage=scan['progress_percentage'],
            started_at=scan['started_at'] if isinstance(scan['started_at'], datetime) else datetime.fromisoformat(scan['started_at']),
            updated_at=scan['updated_at'] if isinstance(scan['updated_at'], datetime) else datetime.fromisoformat(scan['updated_at']),
            errors=scan.get('errors', [])
        )

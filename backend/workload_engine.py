"""
SQL X-Ray Enterprise - Workload Analyzer Engine
================================================
Módulo 6: Análisis de workload incremental y persistente.

Características:
- Análisis de performance_schema
- Procesamiento incremental
- Persistencia en MongoDB
- Reanudación tras fallos
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from scanner_engine import MySQLPoolManager, ScanPersistence, ScanStatus

logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class WorkloadStatus(str, Enum):
    PENDING = "pending"
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class WorkloadAnalysis:
    analysis_id: str
    database: str
    status: WorkloadStatus
    started_at: datetime
    completed_at: Optional[datetime]
    
    # Métricas recolectadas
    top_queries: List[Dict]
    slow_queries: List[Dict]
    table_io_stats: List[Dict]
    index_usage_stats: List[Dict]
    wait_events: List[Dict]
    
    # Resumen
    total_queries_analyzed: int
    total_slow_queries: int
    recommendations: List[Dict]
    
    progress_percentage: float
    current_phase: str

# ==================== WORKLOAD PERSISTENCE ====================

class WorkloadPersistence:
    """Persistencia incremental para análisis de workload"""
    
    def __init__(self, db):
        self.db = db
        self.analyses = db.workload_analyses
        self.queries = db.workload_queries
        self.stats = db.workload_stats
    
    async def create_analysis(self, analysis_id: str, database: str) -> Dict:
        """Crea un nuevo análisis de workload"""
        doc = {
            "analysis_id": analysis_id,
            "database": database,
            "status": WorkloadStatus.PENDING.value,
            "started_at": datetime.now(timezone.utc),
            "completed_at": None,
            "progress_percentage": 0,
            "current_phase": "initializing",
            "phases_completed": [],
            "errors": [],
            "summary": {}
        }
        await self.analyses.insert_one(doc)
        return doc
    
    async def update_progress(self, analysis_id: str, phase: str, 
                              progress: float, status: WorkloadStatus = None):
        """Actualiza el progreso del análisis"""
        update = {
            "$set": {
                "current_phase": phase,
                "progress_percentage": progress,
                "updated_at": datetime.now(timezone.utc)
            }
        }
        if status:
            update["$set"]["status"] = status.value
        
        await self.analyses.update_one({"analysis_id": analysis_id}, update)
    
    async def save_queries_batch(self, analysis_id: str, queries: List[Dict], 
                                 query_type: str):
        """Guarda un batch de queries analizadas"""
        if not queries:
            return
        
        docs = []
        for q in queries:
            docs.append({
                "analysis_id": analysis_id,
                "query_type": query_type,
                "saved_at": datetime.now(timezone.utc),
                **q
            })
        
        await self.queries.insert_many(docs)
    
    async def save_stats(self, analysis_id: str, stat_type: str, stats: List[Dict]):
        """Guarda estadísticas incrementalmente"""
        if not stats:
            return
        
        for stat in stats:
            await self.stats.update_one(
                {"analysis_id": analysis_id, "stat_type": stat_type, 
                 "identifier": stat.get('table_name') or stat.get('index_name') or stat.get('event_name')},
                {"$set": {**stat, "saved_at": datetime.now(timezone.utc)}},
                upsert=True
            )
    
    async def get_analysis(self, analysis_id: str) -> Optional[Dict]:
        """Obtiene el estado de un análisis"""
        return await self.analyses.find_one(
            {"analysis_id": analysis_id},
            {"_id": 0}
        )
    
    async def mark_completed(self, analysis_id: str, summary: Dict):
        """Marca el análisis como completado"""
        await self.analyses.update_one(
            {"analysis_id": analysis_id},
            {"$set": {
                "status": WorkloadStatus.COMPLETED.value,
                "completed_at": datetime.now(timezone.utc),
                "progress_percentage": 100,
                "current_phase": "completed",
                "summary": summary
            }}
        )
    
    async def mark_failed(self, analysis_id: str, error: str):
        """Marca el análisis como fallido"""
        await self.analyses.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": WorkloadStatus.FAILED.value,
                    "updated_at": datetime.now(timezone.utc)
                },
                "$push": {"errors": {"message": error, "timestamp": datetime.now(timezone.utc).isoformat()}}
            }
        )
    
    async def get_completed_phases(self, analysis_id: str) -> List[str]:
        """Obtiene las fases ya completadas (para reanudación)"""
        analysis = await self.get_analysis(analysis_id)
        return analysis.get("phases_completed", []) if analysis else []
    
    async def mark_phase_completed(self, analysis_id: str, phase: str):
        """Marca una fase como completada"""
        await self.analyses.update_one(
            {"analysis_id": analysis_id},
            {"$addToSet": {"phases_completed": phase}}
        )

# ==================== WORKLOAD ANALYZER ENGINE ====================

class WorkloadAnalyzerEngine:
    """
    Motor de análisis de workload.
    
    Fases:
    1. Recolección de queries del digest
    2. Análisis de queries lentas
    3. Estadísticas de I/O por tabla
    4. Uso de índices
    5. Eventos de espera
    6. Generación de recomendaciones
    """
    
    PHASES = [
        ("query_digest", "Analyzing query patterns", 20),
        ("slow_queries", "Identifying slow queries", 35),
        ("table_io", "Collecting table I/O stats", 50),
        ("index_usage", "Analyzing index usage", 65),
        ("wait_events", "Analyzing wait events", 80),
        ("recommendations", "Generating recommendations", 100)
    ]
    
    def __init__(self, pool_manager: MySQLPoolManager, persistence: WorkloadPersistence):
        self.pool = pool_manager
        self.persistence = persistence
        self._cancel_flag = False
    
    async def start_analysis(self, database: str, resume_id: str = None) -> str:
        """Inicia o reanuda un análisis de workload"""
        self._cancel_flag = False
        
        if resume_id:
            analysis = await self.persistence.get_analysis(resume_id)
            if not analysis:
                raise ValueError(f"Analysis {resume_id} not found")
            analysis_id = resume_id
            completed_phases = await self.persistence.get_completed_phases(analysis_id)
            logger.info(f"Resuming workload analysis {analysis_id}")
        else:
            analysis_id = f"workload_{uuid.uuid4().hex[:12]}"
            await self.persistence.create_analysis(analysis_id, database)
            completed_phases = []
            logger.info(f"Starting new workload analysis {analysis_id}")
        
        summary = {}
        
        for phase_id, phase_desc, progress in self.PHASES:
            if self._cancel_flag:
                break
            
            if phase_id in completed_phases:
                logger.info(f"Skipping completed phase: {phase_id}")
                continue
            
            try:
                await self.persistence.update_progress(
                    analysis_id, phase_desc, progress - 15, 
                    WorkloadStatus.ANALYZING
                )
                
                # Ejecutar fase
                phase_result = await self._execute_phase(analysis_id, database, phase_id)
                summary[phase_id] = phase_result
                
                # Marcar fase completada
                await self.persistence.mark_phase_completed(analysis_id, phase_id)
                await self.persistence.update_progress(analysis_id, phase_desc, progress)
                
                logger.info(f"Completed phase: {phase_id}")
            
            except Exception as e:
                logger.error(f"Error in phase {phase_id}: {e}")
                # No detenemos - continuamos con la siguiente fase
                await self.persistence.update_progress(
                    analysis_id, f"Error in {phase_id}", progress
                )
        
        if not self._cancel_flag:
            await self.persistence.mark_completed(analysis_id, summary)
        
        return analysis_id
    
    async def _execute_phase(self, analysis_id: str, database: str, phase_id: str) -> Dict:
        """Ejecuta una fase específica del análisis"""
        
        if phase_id == "query_digest":
            return await self._analyze_query_digest(analysis_id, database)
        
        elif phase_id == "slow_queries":
            return await self._analyze_slow_queries(analysis_id, database)
        
        elif phase_id == "table_io":
            return await self._analyze_table_io(analysis_id, database)
        
        elif phase_id == "index_usage":
            return await self._analyze_index_usage(analysis_id, database)
        
        elif phase_id == "wait_events":
            return await self._analyze_wait_events(analysis_id)
        
        elif phase_id == "recommendations":
            return await self._generate_recommendations(analysis_id, database)
        
        return {}
    
    async def _analyze_query_digest(self, analysis_id: str, database: str) -> Dict:
        """Analiza el digest de queries desde performance_schema"""
        query = """
            SELECT 
                DIGEST_TEXT as query_pattern,
                COUNT_STAR as execution_count,
                ROUND(SUM_TIMER_WAIT / 1000000000000, 4) as total_time_sec,
                ROUND(AVG_TIMER_WAIT / 1000000000000, 6) as avg_time_sec,
                ROUND(MAX_TIMER_WAIT / 1000000000000, 4) as max_time_sec,
                SUM_ROWS_EXAMINED as rows_examined,
                SUM_ROWS_SENT as rows_sent,
                SUM_NO_INDEX_USED as no_index_used,
                SUM_NO_GOOD_INDEX_USED as no_good_index
            FROM performance_schema.events_statements_summary_by_digest
            WHERE SCHEMA_NAME = %s OR SCHEMA_NAME IS NULL
            ORDER BY SUM_TIMER_WAIT DESC
            LIMIT 100
        """
        
        try:
            results = await self.pool.execute_with_retry(query, (database,), timeout=60)
            
            # Guardar incrementalmente
            await self.persistence.save_queries_batch(analysis_id, results, "digest")
            
            return {
                "total_patterns": len(results),
                "top_by_time": results[:10] if results else []
            }
        except Exception as e:
            logger.warning(f"Could not analyze query digest: {e}")
            return {"error": str(e), "total_patterns": 0}
    
    async def _analyze_slow_queries(self, analysis_id: str, database: str) -> Dict:
        """Identifica queries lentas"""
        query = """
            SELECT 
                DIGEST_TEXT as query_pattern,
                COUNT_STAR as execution_count,
                ROUND(AVG_TIMER_WAIT / 1000000000000, 4) as avg_time_sec,
                SUM_ROWS_EXAMINED as total_rows_examined,
                SUM_ROWS_EXAMINED / NULLIF(COUNT_STAR, 0) as avg_rows_examined
            FROM performance_schema.events_statements_summary_by_digest
            WHERE (SCHEMA_NAME = %s OR SCHEMA_NAME IS NULL)
            AND AVG_TIMER_WAIT > 1000000000000
            ORDER BY AVG_TIMER_WAIT DESC
            LIMIT 50
        """
        
        try:
            results = await self.pool.execute_with_retry(query, (database,), timeout=60)
            await self.persistence.save_queries_batch(analysis_id, results, "slow")
            
            return {
                "slow_query_count": len(results),
                "slowest": results[:5] if results else []
            }
        except Exception as e:
            logger.warning(f"Could not analyze slow queries: {e}")
            return {"error": str(e), "slow_query_count": 0}
    
    async def _analyze_table_io(self, analysis_id: str, database: str) -> Dict:
        """Analiza I/O por tabla"""
        query = """
            SELECT 
                OBJECT_NAME as table_name,
                COUNT_READ as read_count,
                COUNT_WRITE as write_count,
                COUNT_FETCH as fetch_count,
                COUNT_INSERT as insert_count,
                COUNT_UPDATE as update_count,
                COUNT_DELETE as delete_count,
                ROUND(SUM_TIMER_READ / 1000000000000, 4) as read_time_sec,
                ROUND(SUM_TIMER_WRITE / 1000000000000, 4) as write_time_sec
            FROM performance_schema.table_io_waits_summary_by_table
            WHERE OBJECT_SCHEMA = %s
            ORDER BY SUM_TIMER_WAIT DESC
            LIMIT 100
        """
        
        try:
            results = await self.pool.execute_with_retry(query, (database,), timeout=60)
            await self.persistence.save_stats(analysis_id, "table_io", results)
            
            return {
                "tables_analyzed": len(results),
                "hottest_tables": results[:10] if results else []
            }
        except Exception as e:
            logger.warning(f"Could not analyze table I/O: {e}")
            return {"error": str(e), "tables_analyzed": 0}
    
    async def _analyze_index_usage(self, analysis_id: str, database: str) -> Dict:
        """Analiza uso de índices"""
        query = """
            SELECT 
                OBJECT_NAME as table_name,
                INDEX_NAME as index_name,
                COUNT_READ as read_count,
                COUNT_WRITE as write_count,
                COUNT_FETCH as fetch_count,
                ROUND(SUM_TIMER_READ / 1000000000000, 4) as read_time_sec
            FROM performance_schema.table_io_waits_summary_by_index_usage
            WHERE OBJECT_SCHEMA = %s
            AND INDEX_NAME IS NOT NULL
            ORDER BY COUNT_READ DESC
            LIMIT 200
        """
        
        try:
            results = await self.pool.execute_with_retry(query, (database,), timeout=60)
            await self.persistence.save_stats(analysis_id, "index_usage", results)
            
            # Detectar índices no usados
            unused = [r for r in results if r.get('read_count', 0) == 0 and r.get('index_name') != 'PRIMARY']
            
            return {
                "indexes_analyzed": len(results),
                "unused_indexes": len(unused),
                "unused_list": unused[:20]
            }
        except Exception as e:
            logger.warning(f"Could not analyze index usage: {e}")
            return {"error": str(e), "indexes_analyzed": 0}
    
    async def _analyze_wait_events(self, analysis_id: str) -> Dict:
        """Analiza eventos de espera"""
        query = """
            SELECT 
                EVENT_NAME as event_name,
                COUNT_STAR as count,
                ROUND(SUM_TIMER_WAIT / 1000000000000, 4) as total_time_sec,
                ROUND(AVG_TIMER_WAIT / 1000000000000, 6) as avg_time_sec
            FROM performance_schema.events_waits_summary_global_by_event_name
            WHERE COUNT_STAR > 0
            ORDER BY SUM_TIMER_WAIT DESC
            LIMIT 50
        """
        
        try:
            results = await self.pool.execute_with_retry(query, (), timeout=60)
            await self.persistence.save_stats(analysis_id, "wait_events", results)
            
            return {
                "events_analyzed": len(results),
                "top_waits": results[:10] if results else []
            }
        except Exception as e:
            logger.warning(f"Could not analyze wait events: {e}")
            return {"error": str(e), "events_analyzed": 0}
    
    async def _generate_recommendations(self, analysis_id: str, database: str) -> Dict:
        """Genera recomendaciones basadas en el análisis"""
        recommendations = []
        
        # Obtener datos guardados
        slow_queries = await self.persistence.queries.find(
            {"analysis_id": analysis_id, "query_type": "slow"}
        ).to_list(50)
        
        index_stats = await self.persistence.stats.find(
            {"analysis_id": analysis_id, "stat_type": "index_usage"}
        ).to_list(200)
        
        # Recomendaciones por queries lentas
        if slow_queries:
            recommendations.append({
                "type": "slow_queries",
                "priority": "high",
                "message": f"Found {len(slow_queries)} slow query patterns",
                "action": "Review and optimize these queries or add appropriate indexes"
            })
        
        # Recomendaciones por índices no usados
        unused = [i for i in index_stats if i.get('read_count', 0) == 0 and i.get('index_name') != 'PRIMARY']
        if unused:
            recommendations.append({
                "type": "unused_indexes",
                "priority": "medium",
                "message": f"Found {len(unused)} unused indexes",
                "action": "Consider removing unused indexes to improve write performance",
                "indexes": [f"{i['table_name']}.{i['index_name']}" for i in unused[:10]]
            })
        
        return {
            "total_recommendations": len(recommendations),
            "recommendations": recommendations
        }
    
    def cancel(self):
        """Cancela el análisis actual"""
        self._cancel_flag = True
    
    async def get_progress(self, analysis_id: str) -> Optional[Dict]:
        """Obtiene el progreso actual"""
        return await self.persistence.get_analysis(analysis_id)

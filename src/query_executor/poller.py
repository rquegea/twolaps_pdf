"""
Query Poller
Sistema de polling para ejecutar queries automáticamente
"""

import time
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from src.database.connection import get_session
from src.database.models import Query, QueryExecution, Mercado, Categoria, Embedding
from src.query_executor.scheduler import QueryScheduler
from src.query_executor.api_clients import OpenAIClient, AnthropicClient, GoogleClient, PerplexityClient
from src.utils.cost_tracker import cost_tracker
from src.utils.logger import setup_logger, log_query_execution
from src.analytics.competitor_discovery import discover_competitors_from_execution

logger = setup_logger(__name__)


def _generate_embedding_for_execution(execution: QueryExecution, query: Query, session: Session):
    """
    Genera embedding vectorial para una QueryExecution y lo guarda en la BD
    
    Args:
        execution: QueryExecution recién creada
        query: Query asociada
        session: Sesión de BD
    """
    # Solo generar embedding si hay texto de respuesta
    if not execution.respuesta_texto or len(execution.respuesta_texto.strip()) < 10:
        logger.debug(f"Skipping embedding for execution {execution.id}: texto insuficiente")
        return
    
    # Usar OpenAI para generar embedding
    openai_client = OpenAIClient()
    
    # Truncar texto si es muy largo (max 8000 chars para el embedding)
    texto_para_embedding = execution.respuesta_texto
    if len(texto_para_embedding) > 8000:
        texto_para_embedding = texto_para_embedding[:8000]
    
    # Generar embedding
    vector = openai_client.generate_embedding(texto_para_embedding)
    
    # Extraer periodo de la ejecución (YYYY-MM)
    periodo = execution.timestamp.strftime('%Y-%m')
    
    # Crear registro de embedding
    embedding = Embedding(
        categoria_id=query.categoria_id,
        periodo=periodo,
        tipo='query_execution',
        referencia_id=execution.id,
        vector=vector,
        metadata={
            'query_id': query.id,
            'proveedor_ia': execution.proveedor_ia,
            'modelo': execution.modelo,
            'tokens_output': execution.tokens_output,
            'texto_length': len(execution.respuesta_texto)
        }
    )
    
    session.add(embedding)
    
    logger.info(
        "embedding_created_for_execution",
        execution_id=execution.id,
        categoria_id=query.categoria_id,
        periodo=periodo,
        texto_length=len(execution.respuesta_texto)
    )


# Factory para clientes
def get_client(provider: str):
    """Retorna una instancia del cliente según el proveedor"""
    clients = {
        'openai': OpenAIClient,
        'anthropic': AnthropicClient,
        'google': GoogleClient,
        'perplexity': PerplexityClient,
        'pplx': PerplexityClient,
    }
    
    client_class = clients.get(provider.lower())
    if not client_class:
        raise ValueError(f"Proveedor desconocido: {provider}")
    
    return client_class()


def execute_query(query: Query, provider: str, session: Session) -> Dict:
    """
    Ejecuta una query contra un proveedor específico
    
    Args:
        query: Query a ejecutar
        provider: Proveedor (openai, anthropic, google, perplexity)
        session: Sesión de BD
    
    Returns:
        Dict con resultados de la ejecución
    """
    try:
        # Obtener cliente
        client = get_client(provider)
        
        # Ejecutar query
        logger.info(
            "executing_query",
            query_id=query.id,
            provider=provider,
            model=client.model
        )
        
        result = client.execute_query(
            question=query.pregunta,
            temperature=0.7
        )
        
        if not result['success']:
            logger.error(
                "query_execution_failed",
                query_id=query.id,
                provider=provider,
                error=result['error']
            )
            return result
        
        # Calcular coste
        cost_usd = cost_tracker.calculate_cost(
            provider=provider,
            model=result['model'],
            tokens_input=result['tokens_input'],
            tokens_output=result['tokens_output']
        )
        
        # Guardar en BD
        execution = QueryExecution(
            query_id=query.id,
            proveedor_ia=provider,
            modelo=result['model'],
            respuesta_texto=result['response_text'],
            timestamp=datetime.utcnow(),
            tokens_input=result['tokens_input'],
            tokens_output=result['tokens_output'],
            coste_usd=cost_usd,
            latencia_ms=result['latency_ms'],
            metadata={}
        )
        
        session.add(execution)
        session.flush()  # Necesario para obtener execution.id

        # Generar embedding automáticamente para RAG (best-effort, no bloqueante)
        try:
            _generate_embedding_for_execution(execution, query, session)
        except Exception as e:
            logger.warning("embedding_generation_failed", error=str(e))

        # Descubrimiento de competidores (best-effort, no bloqueante)
        try:
            discover_competitors_from_execution(session, query.categoria_id, execution)
        except Exception as e:
            logger.warning("competitor_discovery_failed", error=str(e))
        
        # Log
        log_query_execution(
            logger=logger,
            query_id=query.id,
            provider=provider,
            model=result['model'],
            tokens_input=result['tokens_input'],
            tokens_output=result['tokens_output'],
            cost_usd=cost_usd,
            latency_ms=result['latency_ms']
        )
        
        return {
            'success': True,
            'execution_id': execution.id,
            'cost_usd': cost_usd,
            'tokens': result['tokens_input'] + result['tokens_output']
        }
    
    except Exception as e:
        logger.error(
            "query_execution_error",
            query_id=query.id,
            provider=provider,
            error=str(e),
            exc_info=True
        )
        
        return {
            'success': False,
            'error': str(e)
        }


def execute_category_queries(
    category_path: str,
    providers: Optional[List[str]] = None
) -> Dict:
    """
    Ejecuta todas las queries activas de una categoría (concurrencia limitada por settings)
    """
    def _get_max_concurrency(default: int = 12) -> int:
        try:
            with open("config/settings.yaml", "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            return int((cfg.get("polling") or {}).get("max_concurrent_queries", default))
        except Exception:
            return default

    with get_session() as session:
        # Parsear categoría
        try:
            market_name, cat_name = category_path.split('/')
        except ValueError:
            raise ValueError("Formato de categoría inválido. Usa: Mercado/Categoría")
        
        # Buscar categoría
        mercado = session.query(Mercado).filter_by(nombre=market_name).first()
        if not mercado:
            raise ValueError(f"Mercado '{market_name}' no encontrado")
        
        categoria = session.query(Categoria).filter_by(
            mercado_id=mercado.id,
            nombre=cat_name
        ).first()
        if not categoria:
            raise ValueError(f"Categoría '{category_path}' no encontrada")
        
        # Obtener queries activas
        queries = session.query(Query).filter_by(
            categoria_id=categoria.id,
            activa=True
        ).all()
        
        if not queries:
            logger.warning("no_queries_found", categoria=category_path)
            return {
                'queries_executed': 0,
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'total_cost': 0.0
            }
        
        logger.info(
            "starting_category_execution",
            categoria=category_path,
            num_queries=len(queries)
        )

        # Construir trabajos (query_id, provider)
        work_items = []
        for q in queries:
            query_providers = providers if providers else (q.proveedores_ia or [])
            for provider in query_providers:
                work_items.append((q.id, provider))

        max_workers = _get_max_concurrency()
        total_cost = 0.0
        stats = {
            'queries_executed': 0,
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_cost': 0.0
        }

        def _worker(query_id: int, provider: str) -> Dict:
            with get_session() as s_worker:
                q_inst = s_worker.query(Query).get(query_id)
                if not q_inst:
                    return {'success': False, 'error': f'query_not_found:{query_id}'}
                return execute_query(q_inst, provider, s_worker)

        # Ejecutar en paralelo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_worker, qid, prov): (qid, prov) for (qid, prov) in work_items}
            for fut in as_completed(futures):
                try:
                    result = fut.result()
                except Exception as e:
                    result = {'success': False, 'error': str(e)}
                stats['total_executions'] += 1
                if result.get('success'):
                    stats['successful_executions'] += 1
                    total_cost += float(result.get('cost_usd', 0.0) or 0.0)
                else:
                    stats['failed_executions'] += 1

        # Marcar última ejecución de las queries de la categoría
        now_ts = datetime.utcnow()
        for q in queries:
            q.ultima_ejecucion = now_ts
        session.commit()

        stats['queries_executed'] = len(queries)
        stats['total_cost'] = total_cost

        logger.info(
            "category_execution_completed",
            categoria=category_path,
            **stats
        )
        
        return stats


def start_polling(interval: str = 'weekly', run_once: bool = False):
    """
    Inicia el poller automático
    
    Args:
        interval: Intervalo de polling (ignored si run_once=True)
        run_once: Si True, ejecuta una vez y sale
    """
    logger.info("poller_started", interval=interval, run_once=run_once)
    
    def _get_max_concurrency(default: int = 5) -> int:
        """Lee max_concurrent_queries desde config/settings.yaml"""
        try:
            with open("config/settings.yaml", "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            return int((cfg.get("polling") or {}).get("max_concurrent_queries", default))
        except Exception:
            return default
    
    while True:
        try:
            with get_session() as session:
                # Obtener queries a ejecutar
                scheduler = QueryScheduler(session)
                queries_to_execute = scheduler.get_queries_to_execute()
                
                if not queries_to_execute:
                    logger.info("no_queries_to_execute")
                else:
                    max_workers = _get_max_concurrency()
                    logger.info(
                        "executing_scheduled_queries",
                        num_queries=len(queries_to_execute),
                        max_concurrent=max_workers
                    )

                    # Preparar trabajos: (query_id, provider)
                    work_items = []
                    executed_query_ids = set()
                    for q in queries_to_execute:
                        executed_query_ids.add(q.id)
                        for provider in (q.proveedores_ia or []):
                            work_items.append((q.id, provider))

                    total_cost = 0.0
                    total_executions = 0
                    successful = 0
                    failed = 0

                    def _worker(query_id: int, provider: str) -> dict:
                        # Cada hilo abre su propia sesión y carga la query por ID
                        with get_session() as s_worker:
                            q_inst = s_worker.query(Query).get(query_id)
                            if not q_inst:
                                return {"success": False, "error": f"query_not_found:{query_id}"}
                            return execute_query(q_inst, provider, s_worker)

                    # Ejecutar en pool
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_item = {
                            executor.submit(_worker, qid, prov): (qid, prov)
                            for (qid, prov) in work_items
                        }

                        for future in as_completed(future_to_item):
                            _qid, _prov = future_to_item[future]
                            try:
                                result = future.result()
                            except Exception as e:
                                result = {"success": False, "error": str(e)}

                            total_executions += 1
                            if result.get('success'):
                                successful += 1
                                total_cost += float(result.get('cost_usd', 0.0) or 0.0)
                            else:
                                failed += 1

                    # Actualizar ultima_ejecucion en bloque tras completar proveedores
                    now_ts = datetime.utcnow()
                    for qid in executed_query_ids:
                        q_obj = session.query(Query).get(qid)
                        if q_obj:
                            q_obj.ultima_ejecucion = now_ts
                    session.commit()

                    logger.info(
                        "polling_cycle_completed",
                        queries_executed=len(queries_to_execute),
                        total_executions=total_executions,
                        successful=successful,
                        failed=failed,
                        total_cost=total_cost,
                        max_concurrent=max_workers
                    )
                    
                    # Verificar presupuesto
                    alert = cost_tracker.check_budget_alert(session)
                    if alert:
                        logger.warning("budget_alert", **alert)
        
        except Exception as e:
            logger.error("polling_error", error=str(e), exc_info=True)
        
        # Si run_once, salir
        if run_once:
            break
        
        # Dormir hasta el próximo ciclo (1 hora por defecto)
        sleep_minutes = 60
        logger.info("sleeping_until_next_cycle", minutes=sleep_minutes)
        time.sleep(sleep_minutes * 60)


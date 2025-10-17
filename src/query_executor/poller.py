"""
Query Poller
Sistema de polling para ejecutar queries automáticamente
"""

import time
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from src.database.connection import get_session
from src.database.models import Query, QueryExecution, Mercado, Categoria
from src.query_executor.scheduler import QueryScheduler
from src.query_executor.api_clients import OpenAIClient, AnthropicClient, GoogleClient
from src.utils.cost_tracker import cost_tracker
from src.utils.logger import setup_logger, log_query_execution

logger = setup_logger(__name__)


# Factory para clientes
def get_client(provider: str):
    """Retorna una instancia del cliente según el proveedor"""
    clients = {
        'openai': OpenAIClient,
        'anthropic': AnthropicClient,
        'google': GoogleClient
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
        provider: Proveedor (openai, anthropic, google)
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
    Ejecuta todas las queries activas de una categoría
    
    Args:
        category_path: Ruta de categoría (formato: Mercado/Categoría)
        providers: Lista de proveedores a usar (None = todos configurados)
    
    Returns:
        Dict con estadísticas de ejecución
    """
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
        
        # Ejecutar cada query
        stats = {
            'queries_executed': 0,
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_cost': 0.0
        }
        
        for query in queries:
            # Determinar proveedores a usar
            query_providers = providers if providers else query.proveedores_ia
            
            for provider in query_providers:
                result = execute_query(query, provider, session)
                
                stats['total_executions'] += 1
                
                if result['success']:
                    stats['successful_executions'] += 1
                    stats['total_cost'] += result.get('cost_usd', 0.0)
                else:
                    stats['failed_executions'] += 1
            
            # Actualizar última ejecución
            query.ultima_ejecucion = datetime.utcnow()
            stats['queries_executed'] += 1
        
        session.commit()
        
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
    
    while True:
        try:
            with get_session() as session:
                # Obtener queries a ejecutar
                scheduler = QueryScheduler(session)
                queries_to_execute = scheduler.get_queries_to_execute()
                
                if not queries_to_execute:
                    logger.info("no_queries_to_execute")
                else:
                    logger.info(
                        "executing_scheduled_queries",
                        num_queries=len(queries_to_execute)
                    )
                    
                    # Ejecutar queries
                    total_cost = 0.0
                    total_executions = 0
                    successful = 0
                    failed = 0
                    
                    for query in queries_to_execute:
                        # Ejecutar en todos los proveedores configurados
                        for provider in query.proveedores_ia:
                            result = execute_query(query, provider, session)
                            
                            total_executions += 1
                            
                            if result['success']:
                                successful += 1
                                total_cost += result.get('cost_usd', 0.0)
                            else:
                                failed += 1
                        
                        # Actualizar última ejecución
                        query.ultima_ejecucion = datetime.utcnow()
                    
                    session.commit()
                    
                    logger.info(
                        "polling_cycle_completed",
                        queries_executed=len(queries_to_execute),
                        total_executions=total_executions,
                        successful=successful,
                        failed=failed,
                        total_cost=total_cost
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
        logger.info(f"sleeping_until_next_cycle", minutes=sleep_minutes)
        time.sleep(sleep_minutes * 60)


"""
Orchestrator
Orquestador de agentes - Coordina la ejecución del análisis completo
"""

import time
from typing import Dict, Any
from src.database.connection import get_session
from src.database.models import Mercado, Categoria
from src.analytics.agents import (
    QuantitativeAgent,
    QualitativeExtractionAgent,
    SentimentAgent,
    CompetitiveAgent,
    TrendsAgent,
    StrategicAgent,
    SynthesisAgent,
    ExecutiveAgent,
    CampaignAnalysisAgent,
    ChannelAnalysisAgent,
    ESGAnalysisAgent,
    PackagingAnalysisAgent,
    TransversalAgent,
    CustomerJourneyAgent,
    ScenarioPlanningAgent,
    PricingPowerAgent,
    ROIAgent
)
from src.utils.logger import setup_logger, log_agent_analysis

logger = setup_logger(__name__)


class AnalysisOrchestrator:
    """
    Orquestador de análisis multi-agente
    Ejecuta agentes en el orden correcto respetando dependencias
    """
    
    def __init__(self):
        self.agent_order = [
            ('quantitative', QuantitativeAgent),
            ('qualitative', QualitativeExtractionAgent),
            ('sentiment', SentimentAgent),
            ('competitive', CompetitiveAgent),
            ('trends', TrendsAgent),
            ('customer_journey', CustomerJourneyAgent),          # NUEVO: Customer Journey
            ('scenario_planning', ScenarioPlanningAgent),        # NUEVO: Escenarios
            ('campaign_analysis', CampaignAnalysisAgent),        # NUEVO: Análisis de campañas
            ('channel_analysis', ChannelAnalysisAgent),          # NUEVO: Análisis de canales
            ('esg_analysis', ESGAnalysisAgent),                  # NUEVO: Análisis ESG
            ('packaging_analysis', PackagingAnalysisAgent),      # NUEVO: Análisis packaging
            ('pricing_power', PricingPowerAgent),                # NUEVO: Pricing & mapa perceptual
            ('roi', ROIAgent),                                 # NUEVO: ROI campañas/canales
            ('strategic', StrategicAgent),
            ('transversal', TransversalAgent),
            ('synthesis', SynthesisAgent),
            ('executive', ExecutiveAgent)
        ]
    
    def run_analysis(self, categoria_id: int, periodo: str) -> int:
        """
        Ejecuta análisis completo para una categoría y periodo
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            ID del report generado
        """
        with get_session() as session:
            # Verificar categoría existe
            categoria = session.query(Categoria).get(categoria_id)
            if not categoria:
                raise ValueError(f"Categoría {categoria_id} no encontrada")
            
            mercado = session.query(Mercado).get(categoria.mercado_id)
            categoria_nombre = f"{mercado.nombre}/{categoria.nombre}"
            
            logger.info(
                "starting_analysis",
                categoria=categoria_nombre,
                categoria_id=categoria_id,
                periodo=periodo,
                tipo_mercado=getattr(mercado, 'tipo_mercado', 'FMCG')
            )
            
            # Ejecutar agentes en orden
            results = {}
            report_id = None
            
            # Conjuntos de agentes condicionales por tipo de mercado
            FMCG_AGENTS = {'campaign_analysis', 'channel_analysis', 'esg_analysis', 'packaging_analysis'}

            for agent_name, AgentClass in self.agent_order:
                start_time = time.time()
                
                try:
                    logger.info(
                        "executing_agent",
                        agent=agent_name,
                        categoria=categoria_nombre
                    )
                    
                    # Skipping condicional según tipo de mercado
                    if agent_name in FMCG_AGENTS and getattr(mercado, 'tipo_mercado', 'FMCG') != 'FMCG':
                        logger.info(
                            "skipping_agent_for_market",
                            agent=agent_name,
                            tipo_mercado=getattr(mercado, 'tipo_mercado', 'N/A')
                        )
                        results[agent_name] = {'status': 'skipped'}
                        continue

                    # Crear instancia del agente
                    agent = AgentClass(session)
                    
                    # Ejecutar análisis
                    result = agent.analyze(categoria_id, periodo)
                    
                    # Verificar errores
                    if 'error' in result:
                        logger.warning(
                            "agent_returned_error",
                            agent=agent_name,
                            error=result['error']
                        )
                        results[agent_name] = {'status': 'error', 'error': result['error']}
                        
                        # Algunos agentes son críticos
                        if agent_name in ['quantitative', 'qualitative']:
                            raise Exception(f"Agente crítico {agent_name} falló: {result['error']}")
                        
                        continue
                    
                    execution_time = time.time() - start_time
                    
                    # Log
                    log_agent_analysis(
                        logger=logger,
                        agent_name=agent_name,
                        categoria_id=categoria_id,
                        periodo=periodo,
                        execution_time_seconds=execution_time,
                        result_summary=self._get_result_summary(agent_name, result)
                    )
                    
                    results[agent_name] = {
                        'status': 'success',
                        'execution_time': execution_time
                    }
                    
                    # Si es el agente ejecutivo, guardamos el report_id
                    if agent_name == 'executive' and 'report_id' in result:
                        report_id = result['report_id']
                
                except Exception as e:
                    execution_time = time.time() - start_time
                    
                    logger.error(
                        "agent_execution_failed",
                        agent=agent_name,
                        categoria=categoria_nombre,
                        error=str(e),
                        exc_info=True
                    )
                    
                    results[agent_name] = {
                        'status': 'failed',
                        'error': str(e),
                        'execution_time': execution_time
                    }
                    
                    # Si un agente crítico falla, abortar
                    if agent_name in ['quantitative', 'qualitative', 'executive']:
                        raise
            
            # Resumen final
            total_time = sum(r.get('execution_time', 0) for r in results.values())
            successful = sum(1 for r in results.values() if r.get('status') == 'success')
            failed = sum(1 for r in results.values() if r.get('status') == 'failed')
            
            logger.info(
                "analysis_completed",
                categoria=categoria_nombre,
                periodo=periodo,
                report_id=report_id,
                total_time_seconds=total_time,
                agents_successful=successful,
                agents_failed=failed,
                results=results
            )
            
            if not report_id:
                exec_error = None
                if 'executive' in results:
                    exec_error = results['executive'].get('error') or results['executive'].get('status')
                if exec_error:
                    raise Exception(f"No se pudo generar el report (executive agent falló): {exec_error}")
                raise Exception("No se pudo generar el report (executive agent falló)")
            
            # Retornar report_id y estadísticas
            return report_id, {
                'agents_executed': {
                    'total': len(results),
                    'successful': successful,
                    'failed': failed,
                    'skipped': sum(1 for r in results.values() if r.get('status') == 'skipped')
                },
                'total_time_seconds': total_time,
                'results_detail': results
            }
    
    def _get_result_summary(self, agent_name: str, result: Dict) -> Dict[str, Any]:
        """Extrae un resumen del resultado para logging"""
        summary = {}
        
        if agent_name == 'quantitative':
            summary = {
                'total_menciones': result.get('total_menciones', 0),
                'marcas_mencionadas': result.get('num_marcas_mencionadas', 0)
            }
        elif agent_name == 'qualitative':
            summary = {
                'textos_analizados': result.get('metadata', {}).get('textos_analizados', 0),
                'temas_emergentes': len(result.get('temas_emergentes', []))
            }
        elif agent_name == 'competitive':
            summary = {
                'lider': result.get('lider_mercado', 'N/A'),
                'gaps_encontrados': len(result.get('gaps_competitivos', []))
            }
        elif agent_name == 'campaign_analysis':
            summary = {
                'fragments_analyzed': result.get('metadata', {}).get('fragments_analyzed', 0),
                'marca_mas_activa': result.get('marca_mas_activa', 'N/A')
            }
        elif agent_name == 'channel_analysis':
            summary = {
                'fragments_analyzed': result.get('metadata', {}).get('fragments_analyzed', 0),
                'retailers_clave': len(result.get('retailers_clave', []))
            }
        elif agent_name == 'esg_analysis':
            summary = {
                'fragments_analyzed': result.get('metadata', {}).get('fragments_analyzed', 0),
                'controversias': len(result.get('controversias_clave', []))
            }
        elif agent_name == 'packaging_analysis':
            summary = {
                'fragments_analyzed': result.get('metadata', {}).get('fragments_analyzed', 0),
                'innovaciones': len(result.get('innovaciones_detectadas', []))
            }
        elif agent_name == 'strategic':
            summary = {
                'oportunidades': len(result.get('oportunidades', [])),
                'riesgos': len(result.get('riesgos', []))
            }
        elif agent_name == 'transversal':
            summary = {
                'temas_comunes': len(result.get('temas_comunes', [])),
                'contradicciones': len(result.get('contradicciones', [])),
                'insights_nuevos': len(result.get('insights_nuevos', []))
            }
        elif agent_name == 'executive':
            summary = {
                'report_id': result.get('report_id', 0)
            }
        
        return summary


# Función helper para uso desde CLI
def run_analysis(category_path: str, periodo: str) -> tuple:
    """
    Ejecuta análisis completo desde un path de categoría
    
    Args:
        category_path: Ruta de categoría (Mercado/Categoría)
        periodo: Periodo (YYYY-MM)
    
    Returns:
        Tupla (report_id: int, stats: dict) con el ID del report generado y estadísticas de ejecución
    """
    try:
        market_name, cat_name = category_path.split('/')
    except ValueError:
        raise ValueError("Formato de categoría inválido. Usa: Mercado/Categoría")
    
    with get_session() as session:
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
        
        # Ejecutar análisis
        orchestrator = AnalysisOrchestrator()
        return orchestrator.run_analysis(categoria.id, periodo)


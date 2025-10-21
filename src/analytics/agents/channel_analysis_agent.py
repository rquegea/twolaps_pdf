"""
Channel Analysis Agent
Análisis especializado de canales de distribución y estrategias retail usando RAG
"""

import json
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.analytics.rag_manager import RAGManager
from src.query_executor.api_clients import AnthropicClient


class ChannelAnalysisAgent(BaseAgent):
    """
    Agente especializado en análisis de canales de distribución
    Identifica estrategias omnicanal, gaps de e-commerce y experiencia retail
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = AnthropicClient()
        self.rag_manager = RAGManager(session)
        # Normalizamos el nombre del agente
        self.agent_name = 'channel_analysis'
        self.top_k_fragments = 10
        # Prompt se cargará dinámicamente
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Ejecuta análisis de canales usando RAG
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis de canales
        """
        self.logger.info(
            "Iniciando análisis de canales (RAG)",
            categoria_id=categoria_id,
            periodo=periodo
        )
        
        # Cargar prompt según tipo de mercado
        self.load_prompts_dynamic(categoria_id, default_key='channel_analysis_agent')
        
        # Definir query analítica para recuperar fragmentos relevantes
        analytical_query = (
            "Canales de distribución, e-commerce, venta online, supermercados, retailers, "
            "Mercadona, Carrefour, Amazon, disponibilidad de productos, stock, "
            "experiencia de compra, omnicanalidad, distribución física vs digital"
        )
        
        try:
            # Recuperar fragmentos relevantes usando RAG
            fragments = self.rag_manager.search_query_executions_for_question(
                categoria_id=categoria_id,
                periodo=periodo,
                analytical_question=analytical_query,
                top_k=self.top_k_fragments
            )
            
            if not fragments:
                self.logger.warning("No se encontraron fragmentos para análisis de canales")
                resultado = self._get_empty_result(categoria_id, periodo)
                self.save_results(categoria_id, periodo, resultado)
                return resultado
            
            # Construir contexto con fragmentos recuperados
            context_texts = [f"[Fragmento {i+1}]:\n{frag['texto']}" 
                            for i, frag in enumerate(fragments)]
            context = '\n\n---\n\n'.join(context_texts)
            
            # Construir prompt
            prompt = self.task_prompt.format(contexto=context)
            
            # Llamar al LLM
            result = self.client.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=3000
            )
            
            # Parsear respuesta
            response_text = result.get('response_text', '').strip()
            parsed_result = json.loads(response_text)
            
            # Añadir metadata
            parsed_result['periodo'] = periodo
            parsed_result['categoria_id'] = categoria_id
            parsed_result['metadata'] = {
                'fragments_analyzed': len(fragments),
                'metodo': 'rag_vector_search'
            }
            
            # Guardar
            self.save_results(categoria_id, periodo, parsed_result)
            
            self.logger.info(
                "Análisis de canales completado",
                fragments_used=len(fragments)
            )
            
            return parsed_result
            
        except Exception as e:
            self.logger.error(
                f"Error en análisis de canales: {e}",
                exc_info=True
            )
            resultado = {'error': f'Error en análisis de canales: {str(e)}'}
            return resultado
    
    def _get_empty_result(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """Retorna resultado vacío si no hay datos"""
        return {
            'estrategia_canal_inferida': 'No se detectaron menciones significativas sobre canales de distribución.',
            'gaps_e_commerce': [],
            'retailers_clave': [],
            'marca_mejor_distribuida': 'N/A',
            'periodo': periodo,
            'categoria_id': categoria_id,
            'metadata': {
                'fragments_analyzed': 0,
                'metodo': 'rag_vector_search'
            }
        }


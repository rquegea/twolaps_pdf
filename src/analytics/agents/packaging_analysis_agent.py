"""
Packaging Analysis Agent
Análisis especializado de packaging, diseño y experiencia funcional usando RAG
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.analytics.rag_manager import RAGManager
from src.query_executor.api_clients import AnthropicClient


class PackagingAnalysisAgent(BaseAgent):
    """
    Agente especializado en análisis de packaging y diseño
    Identifica quejas funcionales, atributos valorados e innovaciones en empaque
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = AnthropicClient()
        self.rag_manager = RAGManager(session)
        # Normalizamos el nombre del agente
        self.agent_name = 'packaging_analysis'
        self.top_k_fragments = 10
        # Prompt se cargará dinámicamente
    
    def load_prompts(self):
        # Deprecated: usar load_prompts_dynamic
        pass
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Ejecuta análisis de packaging usando RAG
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis de packaging
        """
        self.logger.info(
            "Iniciando análisis de packaging (RAG)",
            categoria_id=categoria_id,
            periodo=periodo
        )
        
        # Cargar prompt según tipo de mercado
        self.load_prompts_dynamic(categoria_id, default_key='packaging_analysis_agent')

        # Definir query analítica para recuperar fragmentos relevantes
        analytical_query = (
            "Packaging, envase, empaque, diseño de producto, botella, lata, caja, "
            "etiqueta, apertura fácil, cierre, reutilizable, funcionalidad, "
            "quejas sobre envase, difícil de abrir, fugas, deterioro, "
            "diseño atractivo, estética, innovación en packaging, materiales"
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
                self.logger.warning("No se encontraron fragmentos para análisis de packaging")
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
            response_text = self._clean_json_response(result.get('response_text', ''))
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
                "Análisis de packaging completado",
                fragments_used=len(fragments)
            )
            
            return parsed_result
            
        except Exception as e:
            self.logger.error(
                f"Error en análisis de packaging: {e}",
                exc_info=True
            )
            resultado = {'error': f'Error en análisis de packaging: {str(e)}'}
            return resultado
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Limpia la respuesta del LLM para extraer JSON válido
        
        Args:
            response_text: Respuesta del LLM
        
        Returns:
            JSON limpio como string
        """
        # Si tiene bloques de markdown, extraer el JSON
        if '```' in response_text:
            lines = response_text.split('\n')
            json_lines = []
            in_json = False
            
            for line in lines:
                if line.strip().startswith('```'):
                    if not in_json:
                        in_json = True
                        continue
                    else:
                        break
                if in_json:
                    json_lines.append(line)
            
            response_text = '\n'.join(json_lines).strip()
        
        return response_text.strip()
    
    def _get_empty_result(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """Retorna resultado vacío si no hay datos"""
        return {
            'quejas_packaging': 'No se detectaron quejas significativas sobre packaging.',
            'atributos_valorados': [],
            'innovaciones_detectadas': [],
            'benchmarking_funcional': [],
            'periodo': periodo,
            'categoria_id': categoria_id,
            'metadata': {
                'fragments_analyzed': 0,
                'metodo': 'rag_vector_search'
            }
        }


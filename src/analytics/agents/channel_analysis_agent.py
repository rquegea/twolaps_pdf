"""
Channel Analysis Agent
Análisis especializado de canales de distribución y estrategias retail usando RAG
"""

import json
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.analytics.rag_manager import RAGManager
from src.query_executor.api_clients import OpenAIClient
from src.analytics.schemas import ChannelAnalysisOutput


class ChannelAnalysisAgent(BaseAgent):
    """
    Agente especializado en análisis de canales de distribución
    Identifica estrategias omnicanal, gaps de e-commerce y experiencia retail
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = OpenAIClient()
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

            def _passes_gating(obj: Dict[str, Any]) -> bool:
                try:
                    # Condición 1: ≥1 retailer o texto explícito de no hay
                    has_retailer = bool(obj.get('retailers_clave'))
                    no_data = isinstance(obj.get('estrategia_canal_inferida'), str) and 'no se detectaron' in obj.get('estrategia_canal_inferida', '').lower()
                    if not (has_retailer or no_data):
                        return False
                    # Condición 2: ≥1 insight con evidencias (usamos 'insights' homogéneo)
                    ins = obj.get('insights') or []
                    return bool(ins)
                except Exception:
                    return False

            gen = self._generate_with_validation(
                prompt=prompt,
                pydantic_model=ChannelAnalysisOutput,
                max_retries=1,
                temperature=0.3,
                max_tokens=3000,
                provider="openai"
            )
            parsed = gen.get('parsed') if gen.get('success') else None

            if not parsed or not _passes_gating(parsed):
                strict_prompt = (
                    prompt
                    + "\n\nREQUISITOS ESTRICTOS: Incluye 'retailers_clave' (si existen) y al menos 1 'insights' con evidencia. Si no hay datos de canal, explica explícitamente en 'estrategia_canal_inferida'. SOLO JSON."
                )
                gen2 = self._generate_with_validation(
                    prompt=strict_prompt,
                    pydantic_model=ChannelAnalysisOutput,
                    max_retries=1,
                    temperature=0.25,
                    max_tokens=3000,
                    provider="openai"
                )
                parsed = gen2.get('parsed') if gen2.get('success') else parsed

            if not parsed:
                resultado = self._get_empty_result(categoria_id, periodo)
                self.save_results(categoria_id, periodo, resultado)
                return resultado

            parsed['periodo'] = periodo
            parsed['categoria_id'] = categoria_id
            meta = parsed.get('metadata') or {}
            meta.update({'fragments_analyzed': len(fragments), 'metodo': 'rag_vector_search'})
            parsed['metadata'] = meta

            # Guardar
            self.save_results(categoria_id, periodo, parsed)

            self.logger.info("Análisis de canales completado", fragments_used=len(fragments))
            return parsed
            
        except Exception as e:
            self.logger.error(
                f"Error en análisis de canales: {e}",
                exc_info=True
            )
            resultado = {'error': f'Error en análisis de canales: {str(e)}'}
            return resultado
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Limpia la respuesta del LLM para extraer JSON válido
        
        Args:
            response_text: Respuesta del LLM
        
        Returns:
            JSON limpio como string
        """
        response_text = response_text.strip()
        
        # Si tiene bloques de markdown con ```, extraer el contenido
        if response_text.startswith('```'):
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
        
        # Si aún no es JSON válido, intentar extraer el primer bloque JSON
        if response_text and not response_text.startswith('{'):
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                response_text = response_text[start:end+1]
        
        return response_text.strip()
    
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


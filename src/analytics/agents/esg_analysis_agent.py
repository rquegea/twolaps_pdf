"""
ESG Analysis Agent
Análisis especializado de sostenibilidad, ESG y responsabilidad corporativa usando RAG
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.analytics.rag_manager import RAGManager
from src.query_executor.api_clients import AnthropicClient
from src.analytics.schemas import ESGAnalysisOutput


class ESGAnalysisAgent(BaseAgent):
    """
    Agente especializado en análisis ESG (Environmental, Social, Governance)
    Identifica controversias, percepción de sostenibilidad y drivers de compra ESG
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = AnthropicClient()
        self.rag_manager = RAGManager(session)
        # Normalizamos el nombre del agente
        self.agent_name = 'esg_analysis'
        self.top_k_fragments = 10
        # Prompt se cargará dinámicamente
    
    def load_prompts(self):
        # Deprecated: usar load_prompts_dynamic
        pass
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Ejecuta análisis ESG usando RAG
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis ESG
        """
        self.logger.info(
            "Iniciando análisis ESG (RAG)",
            categoria_id=categoria_id,
            periodo=periodo
        )
        
        # Cargar prompt según tipo de mercado
        self.load_prompts_dynamic(categoria_id, default_key='esg_analysis_agent')

        # Definir query analítica para recuperar fragmentos relevantes
        analytical_query = (
            "Sostenibilidad, medio ambiente, ESG, responsabilidad social, "
            "ética, plástico, reciclaje, huella de carbono, origen sostenible, "
            "prácticas laborales, diversidad, governance, transparencia, "
            "controversias ambientales, greenwashing, certificaciones ecológicas"
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
                self.logger.warning("No se encontraron fragmentos para análisis ESG")
                resultado = self._get_empty_result(categoria_id, periodo)
                self.save_results(categoria_id, periodo, resultado)
                return resultado
            
            # Construir contexto con fragmentos recuperados
            context_texts = [f"[Fragmento {i+1}]:\n{frag['texto']}" 
                            for i, frag in enumerate(fragments)]
            context = '\n\n---\n\n'.join(context_texts)
            
            # Construir prompt (escapando llaves para evitar KeyError por JSON de ejemplo)
            template = self.task_prompt or ""
            template = template.replace("{contexto}", "__CTX__")
            template = template.replace("{", "{{").replace("}", "}}")
            template = template.replace("__CTX__", "{contexto}")
            prompt = template.format(contexto=context)

            def _passes_gating(obj: Dict[str, Any]) -> bool:
                try:
                    listed_or_none = bool(obj.get('controversias_clave')) or (
                        isinstance(obj.get('resumen_esg'), str) and 'no se detectaron' in obj.get('resumen_esg', '').lower()
                    )
                    has_insight = bool(obj.get('insights') or obj.get('insights_esg'))
                    return listed_or_none and has_insight
                except Exception:
                    return False

            gen = self._generate_with_validation(
                prompt=prompt,
                pydantic_model=ESGAnalysisOutput,
                max_retries=1,
                temperature=0.3,
                max_tokens=3000,
                provider="anthropic"
            )
            parsed = gen.get('parsed') if gen.get('success') else None

            if not parsed or not _passes_gating(parsed):
                strict_prompt = (
                    prompt
                    + "\n\nREQUISITOS ESTRICTOS: Lista 'controversias_clave' si existen o declara explícitamente ausencia. Incluye ≥1 insight (insights o insights_esg). SOLO JSON."
                )
                # Reintento 1: mismo proveedor (Anthropic) con prompt estricto
                gen2 = self._generate_with_validation(
                    prompt=strict_prompt,
                    pydantic_model=ESGAnalysisOutput,
                    max_retries=1,
                    temperature=0.25,
                    max_tokens=3000,
                    provider="anthropic"
                )
                parsed = gen2.get('parsed') if gen2.get('success') else parsed
                # Reintento 2 (fallback de proveedor): OpenAI
                if not parsed or not _passes_gating(parsed):
                    gen3 = self._generate_with_validation(
                        prompt=strict_prompt,
                        pydantic_model=ESGAnalysisOutput,
                        max_retries=1,
                        temperature=0.25,
                        max_tokens=3000,
                        provider="openai"
                    )
                    parsed = gen3.get('parsed') if gen3.get('success') else parsed

            if not parsed:
                # Fallback con insight textual mínimo
                resultado = self._get_empty_result(categoria_id, periodo)
                resultado['insights_esg'] = [
                    'Se detecta señal baja en ESG en el periodo actual; reforzar queries y monitoreo de controversias.'
                ]
                self.save_results(categoria_id, periodo, resultado)
                return resultado

            parsed['periodo'] = periodo
            parsed['categoria_id'] = categoria_id
            meta = parsed.get('metadata') or {}
            meta.update({'fragments_analyzed': len(fragments), 'metodo': 'rag_vector_search'})
            parsed['metadata'] = meta

            # Guardar
            self.save_results(categoria_id, periodo, parsed)

            self.logger.info("Análisis ESG completado", fragments_used=len(fragments))
            return parsed
            
        except Exception as e:
            self.logger.error(
                f"Error en análisis ESG: {e}",
                exc_info=True
            )
            resultado = {'error': f'Error en análisis ESG: {str(e)}'}
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
            'resumen_esg': 'No se detectaron menciones significativas sobre sostenibilidad o ESG.',
            'controversias_clave': [],
            'driver_compra_sostenibilidad': 'No determinado',
            'benchmarking_marcas': [],
            'periodo': periodo,
            'categoria_id': categoria_id,
            'metadata': {
                'fragments_analyzed': 0,
                'metodo': 'rag_vector_search'
            }
        }


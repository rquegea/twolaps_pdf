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
from src.analytics.schemas import PackagingAnalysisOutput


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
            
            # Construir prompt (escapar llaves para evitar conflictos con JSON de ejemplo)
            template = self.task_prompt or ""
            template = template.replace("{contexto}", "__CTX__")
            template = template.replace("{", "{{").replace("}", "}}")
            template = template.replace("__CTX__", "{contexto}")
            prompt = template.format(contexto=context)

            def _passes_gating(obj: Dict[str, Any]) -> bool:
                try:
                    # Aceptamos quejas_packaging string no vacío o insights presentes
                    has_core = bool(obj.get('quejas_packaging'))
                    has_insight = bool(obj.get('insights') or obj.get('insights_packaging'))
                    return has_core and has_insight
                except Exception:
                    return False

            gen = self._generate_with_validation(
                prompt=prompt,
                pydantic_model=PackagingAnalysisOutput,
                max_retries=1,
                temperature=0.3,
                max_tokens=3000,
                provider="anthropic"
            )
            parsed = gen.get('parsed') if gen.get('success') else None

            if not parsed or not _passes_gating(parsed):
                strict_prompt = (
                    prompt + "\n\nREQUISITOS ESTRICTOS: Incluye 'quejas_packaging' y al menos 1 'insights' (o 'insights_packaging'). SOLO JSON válido."
                )
                # Reintento 1: mismo proveedor (Anthropic) con prompt estricto
                gen2 = self._generate_with_validation(
                    prompt=strict_prompt,
                    pydantic_model=PackagingAnalysisOutput,
                    max_retries=1,
                    temperature=0.25,
                    max_tokens=3000,
                    provider="anthropic"
                )
                parsed = gen2.get('parsed') if gen2.get('success') else parsed
                # Reintento 2 (fallback): OpenAI
                if not parsed or not _passes_gating(parsed):
                    gen3 = self._generate_with_validation(
                        prompt=strict_prompt,
                        pydantic_model=PackagingAnalysisOutput,
                        max_retries=1,
                        temperature=0.25,
                        max_tokens=3000,
                        provider="openai"
                    )
                    parsed = gen3.get('parsed') if gen3.get('success') else parsed

            # Helper heurístico para garantizar un insight estructurado si el LLM no cumple
            def _heuristic_result() -> Dict[str, Any]:
                txt = "\n".join([f.get('texto') or '' for f in fragments]).lower()

                def _any(keys):
                    return any(k in txt for k in keys)

                quejas = []
                if _any(['difícil', 'dificil', 'fuga', 'gotea', 'derrama', 'rompe', 'apertura', 'cierra mal', 'tapa']):
                    quejas.append('Se detectan quejas funcionales (apertura/derrames/cierre) en el periodo')

                attrs = []
                if _any(['reutilizable', 'hermético', 'hermetico', 'dosificador', 'ergonómico', 'ergonomico']):
                    attrs.append('Se valora reutilización/cierre hermético/dosificador/ergonomía')

                innov = []
                if _any(['compostable', 'biodegradable', 'reciclable', 'material reciclado', 'vidrio', 'aluminio']):
                    innov.append('Se mencionan materiales o soluciones sostenibles (compostable/biodegradable/reciclable)')

                insight_text = 'Baja señal de packaging en el periodo; pistas: '
                parts = [
                    'quejas funcionales' if quejas else '',
                    'atributos valorados (funcionalidad)' if attrs else '',
                    'innovaciones sostenibles' if innov else ''
                ]
                insight_text += '; '.join([p for p in parts if p]) or 'sin patrones claros'

                return {
                    'quejas_packaging': quejas[0] if quejas else 'No se detectaron quejas significativas sobre packaging.',
                    'atributos_valorados': attrs,
                    'innovaciones_detectadas': innov,
                    'benchmarking_funcional': [],
                    'insights': [
                        {
                            'titulo': 'Packaging: señal baja; activar escucha y pruebas rápidas',
                            'evidencia': [
                                {'tipo': 'DatoAgente', 'detalle': f'Fragmentos analizados: {len(fragments)}', 'fuente_id': 'rag', 'periodo': periodo},
                                {'tipo': 'DatoAgente', 'detalle': f'Quejas detectadas: {len(quejas)}', 'fuente_id': 'heuristica', 'periodo': periodo},
                                {'tipo': 'DatoAgente', 'detalle': f'Atributos valorados: {len(attrs)}; Innovaciones: {len(innov)}', 'fuente_id': 'heuristica', 'periodo': periodo}
                            ],
                            'impacto_negocio': 'Riesgo de fricciones funcionales; oportunidad de diferenciación en UX del envase.',
                            'recomendacion': 'Activar query específica de packaging + test de uso; plan 30-60-90 días para quick wins (cierre/apertura).',
                            'prioridad': 'media',
                            'kpis_seguimiento': [{'nombre': 'Incidencias de packaging', 'valor_objetivo': '-20%', 'fecha_objetivo': '90 días'}],
                            'confianza': 'baja',
                            'contraargumento': None
                        }
                    ],
                    'insights_packaging': [insight_text],
                    'gaps_oportunidades': [],
                    'tendencias_packaging': [],
                    'periodo': periodo,
                    'categoria_id': categoria_id,
                    'metadata': {
                        'fragments_analyzed': len(fragments),
                        'metodo': 'rag_vector_search',
                        'fallback': 'heuristic_min_v3'
                    }
                }

            # Inyectar heurístico si no hay parsed o no pasa gating
            if not parsed or not _passes_gating(parsed):
                resultado = _heuristic_result()
                self.save_results(categoria_id, periodo, resultado)
                return resultado

            parsed['periodo'] = periodo
            parsed['categoria_id'] = categoria_id
            meta = parsed.get('metadata') or {}
            meta.update({'fragments_analyzed': len(fragments), 'metodo': 'rag_vector_search'})
            parsed['metadata'] = meta

            # Guardar
            self.save_results(categoria_id, periodo, parsed)

            self.logger.info("Análisis de packaging completado", fragments_used=len(fragments))
            return parsed
            
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


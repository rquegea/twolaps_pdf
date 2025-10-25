"""
Campaign Analysis Agent
Análisis especializado de campañas de marketing y comunicación usando RAG
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.analytics.rag_manager import RAGManager
from src.query_executor.api_clients import OpenAIClient
from src.analytics.schemas import CampaignAnalysisOutput


class CampaignAnalysisAgent(BaseAgent):
    """
    Agente especializado en análisis de campañas de marketing
    Identifica actividad publicitaria, mensajes clave y efectividad de comunicación
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = OpenAIClient()
        self.rag_manager = RAGManager(session)
        # Normalizamos el nombre del agente
        self.agent_name = 'campaign_analysis'
        self.top_k_fragments = 10
        # Prompt se carga de forma dinámica por tipo de mercado al analizar
    
    def load_prompts(self):
        # Deprecated: usar load_prompts_dynamic
        pass
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Ejecuta análisis de campañas usando RAG
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis de campañas
        """
        self.logger.info(
            "Iniciando análisis de campañas (RAG)",
            categoria_id=categoria_id,
            periodo=periodo
        )
        
        # Cargar prompt por tipo de mercado
        self.load_prompts_dynamic(categoria_id, default_key='campaign_analysis_agent')

        # Definir query analítica para recuperar fragmentos relevantes
        analytical_query = (
            "Campañas publicitarias, actividad de marketing, comunicación de marcas, "
            "publicidad en TV, digital, redes sociales, influencers, mensajes de marca, "
            "lanzamientos de productos, promociones, patrocinios"
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
                self.logger.warning("No se encontraron fragmentos para análisis de campañas")
                resultado = self._get_empty_result(categoria_id, periodo)
                self.save_results(categoria_id, periodo, resultado)
                return resultado

            # Construir contexto con fragmentos recuperados
            context_texts = [f"[Fragmento {i+1}]:\n{frag['texto']}" for i, frag in enumerate(fragments)]
            context = '\n\n---\n\n'.join(context_texts)

            # Construir prompt (escapando llaves del template para evitar KeyError por JSON de ejemplo)
            template = self.task_prompt or ""
            template = template.replace("{contexto}", "__CTX__")
            template = template.replace("{", "{{").replace("}", "}}")
            template = template.replace("__CTX__", "{contexto}")
            prompt = template.format(contexto=context)

            def _passes_gating(obj: Dict[str, Any]) -> bool:
                try:
                    # Condición 1: ≥1 campaña específica o mensaje explícito de ausencia
                    has_campaign = bool(obj.get('campanas_especificas'))
                    no_activity = isinstance(obj.get('resumen_actividad'), str) and 'no se detectó' in obj.get('resumen_actividad', '').lower()
                    if not (has_campaign or no_activity):
                        return False
                    # Condición 2: ≥1 insight con ≥3 evidencias
                    insights = obj.get('insights') or []
                    if not insights:
                        return False
                    first = insights[0]
                    ev = first.get('evidencia') or []
                    return len(ev) >= 3
                except Exception:
                    return False

            # Generar con validación Pydantic
            gen = self._generate_with_validation(
                prompt=prompt,
                pydantic_model=CampaignAnalysisOutput,
                max_retries=1,
                temperature=0.3,
                max_tokens=3000,
                provider="openai"
            )
            parsed = gen.get('parsed') if gen.get('success') else None

            # Si no pasa gating, reforzar instrucciones y reintentar 1 vez
            if not parsed or not _passes_gating(parsed):
                strict_prompt = (
                    prompt
                    + "\n\nREQUISITOS ESTRICTOS (OBLIGATORIO):\n"
                      "- Incluye al menos 1 insight en 'insights' con ≥3 evidencias (mezcla de KPI/CitaRAG/DatoAgente).\n"
                      "- Si no hay campañas explícitas, deja 'campanas_especificas'=[] y escribe en 'resumen_actividad' 'No se detectó actividad de marketing significativa'.\n"
                      "- Devuelve SOLO JSON válido, sin markdown." 
                )
                gen2 = self._generate_with_validation(
                    prompt=strict_prompt,
                    pydantic_model=CampaignAnalysisOutput,
                    max_retries=1,
                    temperature=0.25,
                    max_tokens=3000,
                    provider="openai"
                )
                parsed = gen2.get('parsed') if gen2.get('success') else parsed

            # Fallback mínimo si sigue sin parsed
            if not parsed:
                resultado = self._get_empty_result(categoria_id, periodo)
                self.save_results(categoria_id, periodo, resultado)
                return resultado

            # Añadir metadata estándar
            parsed['periodo'] = periodo
            parsed['categoria_id'] = categoria_id
            meta = parsed.get('metadata') or {}
            meta.update({'fragments_analyzed': len(fragments), 'metodo': 'rag_vector_search'})
            parsed['metadata'] = meta

            # Guardar
            self.save_results(categoria_id, periodo, parsed)

            self.logger.info("Análisis de campañas completado", fragments_used=len(fragments))
            return parsed

        except Exception as e:
            self.logger.error(f"Error en análisis de campañas: {e}", exc_info=True)
            resultado = {'error': f'Error en análisis de campañas: {str(e)}'}
            return resultado
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Limpia la respuesta del LLM para extraer JSON válido
        Usa lógica robusta similar a executive_agent
        
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
        # (esto maneja casos donde hay texto/markdown antes o después del JSON)
        if response_text and not response_text.startswith('{'):
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                response_text = response_text[start:end+1]
        
        return response_text.strip()
    
    def _get_empty_result(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """Retorna resultado vacío si no hay datos"""
        return {
            'resumen_actividad': 'No se detectó actividad de marketing significativa en el periodo.',
            'marca_mas_activa': 'N/A',
            'mensajes_clave': [],
            'canales_destacados': [],
            'insights_recepcion': [],
            'periodo': periodo,
            'categoria_id': categoria_id,
            'metadata': {
                'fragments_analyzed': 0,
                'metodo': 'rag_vector_search'
            }
        }


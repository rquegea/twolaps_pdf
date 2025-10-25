"""
Qualitative Extraction Agent
Análisis cualitativo unificado usando arquitectura RAG escalable
Recupera fragmentos relevantes mediante búsqueda vectorial en lugar de procesar todo en batches
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy import extract
from src.analytics.agents.base_agent import BaseAgent
from src.analytics.rag_manager import RAGManager
from src.database.models import Query, QueryExecution, Marca
from src.query_executor.api_clients import AnthropicClient


class QualitativeExtractionAgent(BaseAgent):
    """
    Agente de extracción cualitativa unificado con arquitectura RAG
    Analiza respuestas textuales recuperando fragmentos relevantes mediante búsqueda vectorial
    Extrae:
    - Sentimiento por marca
    - Atributos por marca
    - Marketing y campañas
    - Canales de distribución
    - Ocasiones de consumo
    - Drivers y barreras
    - Temas emergentes
    - Insights cualitativos clave
    """
    
    def __init__(self, session, version: str = "3.0.0-RAG"):
        super().__init__(session, version)
        self.client = AnthropicClient()
        self.rag_manager = RAGManager(session)
        # Normalizamos el nombre del agente para que sea 'qualitative'
        self.agent_name = 'qualitative'
        # Número de fragmentos a recuperar por pregunta analítica
        self.top_k_fragments = 10  # evitar prompts gigantes
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Ejecuta análisis cualitativo usando arquitectura RAG escalable
        Recupera fragmentos relevantes mediante búsqueda vectorial para cada pregunta analítica
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis cualitativo completo
        """
        # 1. Obtener marcas
        marcas = self.session.query(Marca).filter_by(
            categoria_id=categoria_id
        ).all()
        
        if not marcas:
            return {'error': 'No hay marcas configuradas'}
        
        marca_nombres = [m.nombre for m in marcas]
        
        self.logger.info(
            f"Iniciando análisis cualitativo RAG para {len(marca_nombres)} marcas",
            categoria_id=categoria_id,
            periodo=periodo,
            metodo='rag'
        )
        
        # 2. Definir preguntas analíticas clave
        analytical_questions = self._define_analytical_questions(marca_nombres)
        
        # 3. Para cada pregunta, recuperar fragmentos relevantes y analizar
        all_results = {}
        for question_key, question_data in analytical_questions.items():
            self.logger.info(f"Procesando pregunta analítica: {question_key}")
            
            try:
                # Recuperar fragmentos relevantes usando RAG
                fragments = self.rag_manager.search_query_executions_for_question(
                    categoria_id=categoria_id,
                    periodo=periodo,
                    analytical_question=question_data['query'],
                    top_k=self.top_k_fragments
                )
                
                if not fragments:
                    self.logger.warning(f"No se encontraron fragmentos para: {question_key}")
                    all_results[question_key] = None
                    continue
                
                # Construir contexto con fragmentos recuperados
                def _clean(t: str, max_len: int = 900) -> str:
                    t = (t or "")
                    t = t.replace("<think>", "").replace("</think>", "")
                    t = t.replace("```", "")
                    return t[:max_len]

                context_texts = [f"[Fragmento {i+1}]:\n{_clean(frag['texto'])}" 
                                for i, frag in enumerate(fragments)]
                context = '\n\n---\n\n'.join(context_texts)
                
                # Construir prompt específico para esta pregunta
                prompt = question_data['prompt_template'].format(
                    marcas=', '.join(marca_nombres),
                    contexto=context
                )
                
                # Llamar al LLM
                result = self.client.generate(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=1500
                )
                
                # Parsear respuesta
                response_text = self._clean_json_response(result.get('response_text', ''))
                parsed_result = json.loads(response_text)
                
                all_results[question_key] = parsed_result
                
                self.logger.info(
                    f"Pregunta {question_key} procesada exitosamente",
                    fragments_used=len(fragments)
                )
                
            except Exception as e:
                self.logger.error(
                    f"Error procesando pregunta {question_key}: {e}",
                    exc_info=True
                )
                all_results[question_key] = None
        
        # 4. Agregar todos los resultados en la estructura final
        resultado_final = self._aggregate_rag_results(all_results)
        
        # 5. Añadir metadata
        resultado_final['periodo'] = periodo
        resultado_final['categoria_id'] = categoria_id
        resultado_final['metadata'] = {
            'metodo': 'rag_vector_search',
            'top_k_por_pregunta': self.top_k_fragments,
            'preguntas_analiticas': len(analytical_questions),
            'preguntas_exitosas': sum(1 for v in all_results.values() if v is not None)
        }
        
        # 6. Guardar
        self.save_results(categoria_id, periodo, resultado_final)
        
        return resultado_final
    
    def _define_analytical_questions(self, marca_nombres: List[str]) -> Dict[str, Dict]:
        """
        Define las preguntas analíticas clave y sus prompts
        Cada pregunta recuperará fragmentos relevantes mediante RAG
        
        Args:
            marca_nombres: Lista de nombres de marcas
        
        Returns:
            Dict con preguntas analíticas y sus configuraciones
        """
        return {
            'sentimiento': {
                'query': f"Análisis de sentimiento y percepción sobre las marcas: {', '.join(marca_nombres)}",
                'prompt_template': """Eres un analista experto en sentiment analysis.
Analiza el sentimiento sobre cada marca en los siguientes fragmentos de texto.

MARCAS: {marcas}

FRAGMENTOS DE TEXTO:
{contexto}

Devuelve JSON con esta estructura EXACTA:
{{
  "sentimiento_por_marca": {{
    "Marca X": {{
      "score_medio": 0.5,
      "tono": "positivo",
      "intensidad": "alta",
      "distribucion": {{"positivo": 80, "neutral": 15, "negativo": 5}}
    }}
  }}
}}

IMPORTANTE: Devuelve SOLO el JSON válido, sin markdown ni texto adicional."""
            },
            'atributos': {
                'query': f"Atributos y características mencionadas sobre las marcas: {', '.join(marca_nombres)}",
                'prompt_template': """Eres un especialista en posicionamiento de marca.
Extrae TODOS los atributos asociados a cada marca en los fragmentos de texto.

MARCAS: {marcas}

FRAGMENTOS DE TEXTO:
{contexto}

Categorías de atributos: calidad, precio, innovacion, confiabilidad, servicio, reputacion, perfil, experiencia, disponibilidad, diseño

Devuelve JSON con esta estructura EXACTA:
{{
  "atributos_por_marca": {{
    "Marca X": {{
      "calidad": ["premium", "consistente"],
      "precio": ["alto", "justificado"],
      "innovacion": ["innovador"]
    }}
  }}
}}

IMPORTANTE: Devuelve SOLO el JSON válido, sin markdown ni texto adicional."""
            },
            'marketing': {
                'query': f"Campañas publicitarias, marketing y comunicación de las marcas: {', '.join(marca_nombres)}",
                'prompt_template': """Eres un especialista en marketing y comunicación.
Identifica menciones de campañas, publicidad y estrategias de marketing en los fragmentos.

MARCAS: {marcas}

FRAGMENTOS DE TEXTO:
{contexto}

Devuelve JSON con esta estructura EXACTA:
{{
  "marketing_campanas": {{
    "Marca X": {{
      "campanas_mencionadas": ["Campaña descripción"],
      "canales_comunicacion": ["TV", "RRSS"],
      "percepcion_publicidad": "efectiva",
      "tono_comunicacion": "emocional"
    }}
  }}
}}

IMPORTANTE: Devuelve SOLO el JSON válido, sin markdown ni texto adicional."""
            },
            'canales': {
                'query': f"Canales de distribución, puntos de venta y disponibilidad de las marcas: {', '.join(marca_nombres)}",
                'prompt_template': """Eres un especialista en distribución y retail.
Identifica menciones sobre dónde se compra, disponibilidad y experiencia de compra.

MARCAS: {marcas}

FRAGMENTOS DE TEXTO:
{contexto}

Devuelve JSON con esta estructura EXACTA:
{{
  "canales_distribucion": {{
    "Marca X": {{
      "donde_comprar": ["Supermercados", "Online"],
      "retailers_mencionados": ["Mercadona"],
      "facilidad_encontrar": "fácil",
      "disponibilidad": "amplia"
    }}
  }}
}}

IMPORTANTE: Devuelve SOLO el JSON válido, sin markdown ni texto adicional."""
            },
            'ocasiones_drivers': {
                'query': f"Ocasiones de consumo, drivers de compra y barreras para las marcas: {', '.join(marca_nombres)}",
                'prompt_template': """Eres un analista de comportamiento del consumidor.
Identifica cuándo, cómo y por qué se consumen los productos.

MARCAS: {marcas}

FRAGMENTOS DE TEXTO:
{contexto}

Devuelve JSON con esta estructura EXACTA:
{{
  "ocasiones_consumo": {{
    "Marca X": {{
      "momentos": ["desayuno", "snack"],
      "contexto_social": ["familia"],
      "motivaciones": ["placer"]
    }}
  }},
  "drivers_barreras": {{
    "drivers_positivos": ["Sabor superior"],
    "barreras": ["Precio alto"],
    "switching_menciones": ["Cambié de Y a X"]
  }}
}}

IMPORTANTE: Devuelve SOLO el JSON válido, sin markdown ni texto adicional."""
            },
            'temas_insights': {
                'query': f"Temas emergentes, tendencias e insights generales del mercado",
                'prompt_template': """Eres un analista de mercado estratégico.
Identifica temas recurrentes, tendencias y insights reveladores.

FRAGMENTOS DE TEXTO:
{contexto}

Devuelve JSON con esta estructura EXACTA:
{{
  "temas_emergentes": [
    "Sostenibilidad como factor clave",
    "Preferencia por compra online"
  ],
  "insights_cualitativos": [
    "Los usuarios valoran más experiencia que precio",
    "Hay demanda no cubierta de productos eco-friendly"
  ]
}}

IMPORTANTE: Devuelve SOLO el JSON válido, sin markdown ni texto adicional."""
            }
        }
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Limpia la respuesta del LLM para extraer JSON válido, incluso si hay preámbulo o markdown.
        
        Args:
            response_text: Respuesta del LLM
        
        Returns:
            JSON limpio como string
        """
        response_text = response_text.strip()
        
        # 1. Quitar bloques de código markdown (```json ... ```)
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
        
        # 2. Si todavía hay ruido (ej. texto libre), buscar el primer '{' y el último '}'
        start = response_text.find('{')
        end = response_text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            return response_text[start:end+1]
        
        return response_text.strip()
    
    def _aggregate_rag_results(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agrega los resultados de todas las preguntas analíticas RAG en estructura final
        
        Args:
            all_results: Dict con resultados de cada pregunta analítica
        
        Returns:
            Dict con estructura final unificada
        """
        resultado_final = {}
        
        # Extraer sentimiento
        if all_results.get('sentimiento'):
            resultado_final['sentimiento_por_marca'] = all_results['sentimiento'].get('sentimiento_por_marca', {})
        else:
            resultado_final['sentimiento_por_marca'] = {}
        
        # Extraer atributos
        if all_results.get('atributos'):
            resultado_final['atributos_por_marca'] = all_results['atributos'].get('atributos_por_marca', {})
        else:
            resultado_final['atributos_por_marca'] = {}
        
        # Extraer marketing
        if all_results.get('marketing'):
            resultado_final['marketing_campanas'] = all_results['marketing'].get('marketing_campanas', {})
        else:
            resultado_final['marketing_campanas'] = {}
        
        # Extraer canales
        if all_results.get('canales'):
            resultado_final['canales_distribucion'] = all_results['canales'].get('canales_distribucion', {})
        else:
            resultado_final['canales_distribucion'] = {}
        
        # Extraer ocasiones y drivers
        if all_results.get('ocasiones_drivers'):
            resultado_final['ocasiones_consumo'] = all_results['ocasiones_drivers'].get('ocasiones_consumo', {})
            resultado_final['drivers_barreras'] = all_results['ocasiones_drivers'].get('drivers_barreras', {})
        else:
            resultado_final['ocasiones_consumo'] = {}
            resultado_final['drivers_barreras'] = {}
        
        # Extraer temas e insights
        if all_results.get('temas_insights'):
            resultado_final['temas_emergentes'] = all_results['temas_insights'].get('temas_emergentes', [])
            resultado_final['insights_cualitativos'] = all_results['temas_insights'].get('insights_cualitativos', [])
        else:
            resultado_final['temas_emergentes'] = []
            resultado_final['insights_cualitativos'] = []
        
        return resultado_final


"""
Channel Analysis Agent
Agente especializado en análisis de canales de distribución y estrategias de retail
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult, QueryExecution, Categoria, Mercado, Query
from sqlalchemy import extract
from src.query_executor.api_clients import OpenAIClient


class ChannelAnalysisAgent(BaseAgent):
    """
    Agente de análisis de canales
    Analiza presencia, estrategias de distribución y experiencia de compra por canal
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = OpenAIClient()
        self.load_prompts()
    
    def load_prompts(self):
        """Carga prompts de configuración"""
        prompt_path = Path("config/prompts/agent_prompts.yaml")
        system_path = Path("config/prompts/system_prompts.yaml")
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)
                self.task_prompt = prompts.get('channel_agent', {}).get('task', '')
        
        if system_path.exists():
            with open(system_path, 'r', encoding='utf-8') as f:
                system = yaml.safe_load(f)
                self.system_prompt = system.get('base_consultant_role', '')
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Analiza canales de distribución y estrategias de retail
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis de canales estructurado
        """
        # Obtener información de categoría
        categoria = self.session.query(Categoria).get(categoria_id)
        if not categoria:
            return {'error': 'Categoría no encontrada'}
        
        mercado = self.session.query(Mercado).get(categoria.mercado_id)
        categoria_nombre = f"{mercado.nombre}/{categoria.nombre}"
        
        # Obtener análisis previos necesarios
        quantitative = self._get_analysis('quantitative', categoria_id, periodo)
        qualitative = self._get_analysis('qualitative', categoria_id, periodo)
        if not qualitative:
            qualitative = self._get_analysis('qualitativeextraction', categoria_id, periodo)
        
        if not quantitative or not qualitative:
            return {'error': 'Faltan análisis previos (quantitative/qualitative)'}
        
        # Obtener respuestas relacionadas con canales
        channel_responses = self._get_channel_responses(categoria_id, periodo)
        
        # Construir prompt
        prompt = self._build_prompt(
            categoria_nombre,
            periodo,
            quantitative,
            qualitative,
            channel_responses
        )
        
        # Generar análisis con LLM
        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.4,
                max_tokens=3000,
                json_mode=True
            )
            
            response_text = result.get('response_text', '').strip()
            
            # Limpiar y parsear JSON
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
            
            channel_analysis = json.loads(response_text)
            
            # Guardar resultado usando el método de BaseAgent
            self.save_results(categoria_id, periodo, channel_analysis)
            
            return channel_analysis
        
        except Exception as e:
            self.logger.error(f"Error en análisis de canales: {str(e)}", exc_info=True)
            return {'error': f'Error al analizar canales: {str(e)}'}
    
    def _build_prompt(
        self,
        categoria: str,
        periodo: str,
        quantitative: Dict,
        qualitative: Dict,
        channel_responses: str
    ) -> str:
        """Construye el prompt para análisis de canales"""
        
        prompt = f"""
{self.system_prompt}

Eres un especialista en estrategias de distribución y retail para FMCG.
Tu tarea es analizar la presencia por canal, estrategias de distribución y experiencia de compra.

CATEGORÍA: {categoria}
PERIODO: {periodo}

DATOS DE CONTEXTO:
- SOV por marca: {json.dumps(quantitative.get('sov_percent', {}), indent=2)}
- Marcas principales: {list(quantitative.get('sov_percent', {}).keys())}

RESPUESTAS TEXTUALES (Menciones de canales/compra):
{channel_responses}

ANÁLISIS REQUERIDO:

1. PRESENCIA POR CANAL:
   Para cada marca principal, identifica su presencia en:
   - Supermercados/Hipermercados (ej: Carrefour, Mercadona, etc.)
   - Tiendas de conveniencia
   - E-commerce generalista (Amazon, tiendas online de retailers)
   - E-commerce propio (D2C - Direct to Consumer)
   - Canales especializados (gourmet, dietéticas, farmacias según categoría)
   - Otros canales mencionados

2. EXPERIENCIA DE COMPRA:
   - ¿Cómo describen los consumidores la experiencia de compra online vs física?
   - ¿Es fácil encontrar los productos en tiendas físicas?
   - ¿Calidad de la experiencia e-commerce (web, app)?
   - ¿Disponibilidad y stock?
   - ¿Precios comparativos entre canales?

3. ESTRATEGIAS DE CANAL INFERIDAS:
   - ¿Qué marca parece tener estrategia omnicanal más fuerte?
   - ¿Hay marcas con estrategia de distribución exclusiva o selectiva?
   - ¿Estrategia de penetración masiva vs premium/selectiva?
   - ¿Presencia en canales emergentes (delivery apps, suscripciones)?

4. VENTAJAS COMPETITIVAS POR CANAL:
   - ¿Qué marca domina qué canal?
   - ¿Hay gaps de distribución aprovechables?
   - ¿Ventajas de disponibilidad/accesibilidad de alguna marca?

5. TENDENCIAS DE CANAL:
   - ¿Preferencia creciente por compra online vs offline?
   - ¿Importancia del canal en la decisión de compra?
   - ¿Menciones de nuevos formatos de venta?

DEVUELVE JSON ESTRUCTURADO:
{{
  "presencia_por_marca": {{
    "Marca X": {{
      "supermercados": {{
        "presente": true,
        "retailers_mencionados": ["Carrefour", "Mercadona"],
        "facilidad_encontrar": "alta|media|baja",
        "comentarios": ["comentario 1", "comentario 2"]
      }},
      "conveniencia": {{
        "presente": true/false,
        "comentarios": []
      }},
      "ecommerce_generalista": {{
        "presente": true,
        "plataformas": ["Amazon"],
        "experiencia": "positiva|neutral|negativa",
        "comentarios": []
      }},
      "ecommerce_propio": {{
        "presente": true/false,
        "url_mencionada": "si se menciona",
        "experiencia": "positiva|neutral|negativa",
        "comentarios": []
      }},
      "canales_especializados": {{
        "presente": true/false,
        "tipos": ["gourmet", "dietetica"],
        "comentarios": []
      }},
      "otros_canales": []
    }}
  }},
  "comparativa_experiencia": {{
    "online_vs_offline": {{
      "preferencia_general": "online|offline|indiferente",
      "ventajas_online": ["conveniencia", "precios"],
      "ventajas_offline": ["inmediatez", "ver producto"],
      "citas_relevantes": []
    }},
    "facilidad_acceso": {{
      "marca_mas_accesible": "Marca X",
      "marca_menos_accesible": "Marca Y",
      "comentarios": []
    }}
  }},
  "estrategias_inferidas": {{
    "Marca X": {{
      "tipo_estrategia": "omnicanal|selectiva|masiva|exclusiva",
      "fortalezas_canal": ["Fuerte presencia en supermercados", "Excelente e-commerce propio"],
      "debilidades_canal": ["Ausente en conveniencia"],
      "diferenciacion": "Cómo se diferencia en distribución"
    }}
  }},
  "ventajas_competitivas": [
    {{
      "marca": "Marca X",
      "ventaja": "Disponibilidad universal en todos los canales",
      "impacto": "alto|medio|bajo"
    }}
  ],
  "insights_clave": [
    "Insight 1 sobre importancia de canal",
    "Insight 2 sobre gaps de distribución",
    "Insight 3 sobre tendencias de compra"
  ],
  "tendencias_canal": {{
    "shift_online": "creciente|estable|decreciente",
    "importancia_disponibilidad": "crítica|importante|moderada",
    "canales_emergentes": ["delivery apps", "suscripciones"]
  }},
  "metadata": {{
    "marcas_analizadas": 0,
    "canales_identificados": 0,
    "calidad_datos": "alta|media|baja"
  }}
}}

IMPORTANTE:
- Basa el análisis en EVIDENCIA del texto, no especules
- Si hay poca información sobre canales, indícalo en metadata
- Prioriza insights accionables sobre distribución
- RESPONDE ÚNICAMENTE CON EL JSON VÁLIDO, SIN TEXTO ADICIONAL NI MARKDOWN
"""
        
        return prompt
    
    def _get_channel_responses(self, categoria_id: int, periodo: str, limit: int = 15) -> str:
        """Obtiene respuestas relacionadas con canales y compra"""
        
        # Extraer año y mes del periodo
        year, month = map(int, periodo.split('-'))
        
        # Palabras clave relacionadas con canales
        channel_keywords = [
            'comprar', 'tienda', 'supermercado', 'online', 'amazon',
            'disponible', 'encontrar', 'e-commerce', 'entrega', 'delivery'
        ]
        
        responses = []
        
        for keyword in channel_keywords:
            query_executions = self.session.query(QueryExecution).join(Query).filter(
                Query.categoria_id == categoria_id,
                extract('year', QueryExecution.timestamp) == year,
                extract('month', QueryExecution.timestamp) == month,
                QueryExecution.respuesta_texto.ilike(f'%{keyword}%')
            ).limit(3).all()
            
            for qe in query_executions:
                if qe.respuesta_texto and len(qe.respuesta_texto) > 50:
                    responses.append(qe.respuesta_texto)
        
        # Si no hay respuestas específicas, obtener muestra general
        if len(responses) < 10:
            general_executions = self.session.query(QueryExecution).join(Query).filter(
                Query.categoria_id == categoria_id,
                extract('year', QueryExecution.timestamp) == year,
                extract('month', QueryExecution.timestamp) == month
            ).limit(limit).all()
            
            responses = [qe.respuesta_texto for qe in general_executions if qe.respuesta_texto]
        
        # Deduplicar y limitar
        unique_responses = list(dict.fromkeys(responses))[:limit]
        
        if not unique_responses:
            return "No hay respuestas disponibles para este periodo."
        
        return "\n\n---\n\n".join(unique_responses)
    
    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        """Helper para obtener análisis previo"""
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        
        return result.resultado if result else {}


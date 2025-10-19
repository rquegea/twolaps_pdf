"""
Campaign Analysis Agent
Agente especializado en análisis de campañas de marketing y estrategias de comunicación
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult, QueryExecution, Categoria, Mercado, Query
from sqlalchemy import extract
from src.query_executor.api_clients import OpenAIClient


class CampaignAnalysisAgent(BaseAgent):
    """
    Agente de análisis de campañas
    Detecta y analiza actividad de marketing, campañas publicitarias y estrategias de comunicación
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
                self.task_prompt = prompts.get('campaign_agent', {}).get('task', '')
        
        if system_path.exists():
            with open(system_path, 'r', encoding='utf-8') as f:
                system = yaml.safe_load(f)
                self.system_prompt = system.get('base_consultant_role', '')
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Analiza campañas de marketing y actividad promocional
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis de campañas estructurado
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
        
        # Obtener muestra de respuestas textuales relacionadas con marketing
        marketing_responses = self._get_marketing_responses(categoria_id, periodo)
        
        # Construir prompt
        prompt = self._build_prompt(
            categoria_nombre,
            periodo,
            quantitative,
            qualitative,
            marketing_responses
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
            
            campaign_analysis = json.loads(response_text)
            
            # Guardar resultado usando el método de BaseAgent
            self.save_results(categoria_id, periodo, campaign_analysis)
            
            return campaign_analysis
        
        except Exception as e:
            self.logger.error(f"Error en análisis de campañas: {str(e)}", exc_info=True)
            return {'error': f'Error al analizar campañas: {str(e)}'}
    
    def _build_prompt(
        self,
        categoria: str,
        periodo: str,
        quantitative: Dict,
        qualitative: Dict,
        marketing_responses: str
    ) -> str:
        """Construye el prompt para análisis de campañas"""
        
        prompt = f"""
{self.system_prompt}

Eres un especialista en análisis de estrategias de marketing y comunicación en FMCG.
Tu tarea es detectar y analizar TODAS las campañas, actividades de marketing y estrategias de comunicación mencionadas.

CATEGORÍA: {categoria}
PERIODO: {periodo}

DATOS DE CONTEXTO:
- SOV por marca: {json.dumps(quantitative.get('sov_percent', {}), indent=2)}
- Sentimiento por marca: {json.dumps(qualitative.get('sentimiento_por_marca', {}), indent=2)}
- Marcas principales: {list(quantitative.get('sov_percent', {}).keys())}

RESPUESTAS TEXTUALES (Menciones de marketing/campañas):
{marketing_responses}

ANÁLISIS REQUERIDO:

1. DETECCIÓN DE CAMPAÑAS:
   - Identifica TODAS las campañas publicitarias mencionadas (nombre, descripción breve)
   - Marca asociada a cada campaña
   - Timeframe aproximado si se menciona
   - Canales utilizados (TV, digital, RRSS, influencers, exterior, prensa)

2. MENSAJES Y POSICIONAMIENTO:
   - ¿Cuál es el mensaje clave de cada marca?
   - ¿Qué valores/atributos comunica?
   - Tono de comunicación (emocional, racional, humorístico, premium, etc.)
   - Diferenciación en messaging vs competencia

3. PERCEPCIÓN DE CAMPAÑAS:
   - ¿Cómo son percibidas las campañas? (efectivas, memorables, creativas, aburridas)
   - Sentimiento sobre campañas específicas
   - Menciones de efectividad o recall

4. ESTRATEGIA DE COMUNICACIÓN:
   - ¿Qué marca tiene mayor actividad de marketing aparente?
   - ¿Hay correlación entre actividad de marketing y SOV?
   - ¿Estrategia agresiva vs conservadora?
   - ¿Uso de influencers/celebridades?

5. INSIGHTS COMPETITIVOS:
   - ¿Qué marca comunica mejor?
   - ¿Gaps en comunicación de alguna marca?
   - ¿Oportunidades de diferenciación en messaging?

DEVUELVE JSON ESTRUCTURADO:
{{
  "campañas_detectadas": [
    {{
      "marca": "Marca X",
      "nombre_campana": "Nombre o descripción",
      "mensaje_clave": "Mensaje principal comunicado",
      "canales": ["TV", "Digital", "RRSS"],
      "tono": "emocional|racional|humorístico|premium|etc",
      "percepcion": "positiva|neutral|negativa",
      "citas_relevantes": ["cita 1", "cita 2"]
    }}
  ],
  "estrategias_comunicacion": {{
    "Marca X": {{
      "mensaje_principal": "Posicionamiento comunicado",
      "valores_clave": ["valor 1", "valor 2"],
      "tono_general": "descripción del tono",
      "actividad_aparente": "alta|media|baja",
      "canales_prioritarios": ["canal 1", "canal 2"],
      "uso_influencers": true/false,
      "diferenciacion": "Cómo se diferencia vs competencia"
    }}
  }},
  "analisis_comparativo": {{
    "marca_mas_activa": "Marca X",
    "marca_mejor_percibida": "Marca Y",
    "correlacion_marketing_sov": "Alta actividad de marketing de Marca X correlaciona con SOV dominante...",
    "gaps_comunicacion": [
      "Marca Z no tiene presencia clara en digital",
      "Marca W no comunica innovación a pesar de tener productos nuevos"
    ]
  }},
  "insights_clave": [
    "Insight 1 sobre efectividad de campañas",
    "Insight 2 sobre oportunidades de comunicación",
    "Insight 3 sobre tendencias en marketing de la categoría"
  ],
  "metadata": {{
    "campanas_totales_detectadas": 0,
    "marcas_con_actividad_marketing": 0,
    "calidad_datos": "alta|media|baja"
  }}
}}

IMPORTANTE:
- Si no se detectan campañas específicas, indica "No se detectaron menciones explícitas de campañas"
- Infiere estrategias de comunicación incluso si no hay campañas específicas nombradas
- Basa el análisis en EVIDENCIA del texto, no especules sin fundamento
- RESPONDE ÚNICAMENTE CON EL JSON VÁLIDO, SIN TEXTO ADICIONAL NI MARKDOWN
"""
        
        return prompt
    
    def _get_marketing_responses(self, categoria_id: int, periodo: str, limit: int = 15) -> str:
        """Obtiene respuestas relacionadas con marketing y campañas"""
        
        # Extraer año y mes del periodo
        year, month = map(int, periodo.split('-'))
        
        # Palabras clave relacionadas con marketing
        marketing_keywords = [
            'campaña', 'publicidad', 'anuncio', 'marketing', 'comunicación',
            'influencer', 'promoción', 'spot', 'comercial', 'mensaje'
        ]
        
        responses = []
        
        for keyword in marketing_keywords:
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


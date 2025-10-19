"""
Market Context Agent
Agente especializado en análisis de contexto de mercado (PESTEL, Porter, Drivers)
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult, Categoria, Mercado
from src.query_executor.api_clients import OpenAIClient, PerplexityClient


class MarketContextAgent(BaseAgent):
    """
    Agente de contexto de mercado
    Genera análisis PESTEL, Porter y drivers de categoría usando información actualizada
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = OpenAIClient()
        self.perplexity_client = PerplexityClient()
        self.load_prompts()
    
    def load_prompts(self):
        """Carga prompts de configuración"""
        prompt_path = Path("config/prompts/agent_prompts.yaml")
        system_path = Path("config/prompts/system_prompts.yaml")
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)
                self.task_prompt = prompts.get('market_context_agent', {}).get('task', '')
        
        if system_path.exists():
            with open(system_path, 'r', encoding='utf-8') as f:
                system = yaml.safe_load(f)
                self.system_prompt = system.get('base_consultant_role', '')
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Analiza contexto de mercado con frameworks estratégicos
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis de contexto estructurado
        """
        # Obtener información de categoría
        categoria = self.session.query(Categoria).get(categoria_id)
        if not categoria:
            return {'error': 'Categoría no encontrada'}
        
        mercado = self.session.query(Mercado).get(categoria.mercado_id)
        categoria_nombre = f"{mercado.nombre}/{categoria.nombre}"
        
        # Obtener análisis previos
        trends = self._get_analysis('trends', categoria_id, periodo)
        competitive = self._get_analysis('competitive', categoria_id, periodo)
        quantitative = self._get_analysis('quantitative', categoria_id, periodo)
        
        # Obtener información actualizada de mercado vía Perplexity
        market_info = self._get_market_intelligence(categoria_nombre, periodo)
        
        # Construir prompt
        prompt = self._build_prompt(
            categoria_nombre,
            periodo,
            trends,
            competitive,
            quantitative,
            market_info
        )
        
        # Generar análisis con LLM
        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.5,
                max_tokens=3500,
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
            
            market_analysis = json.loads(response_text)
            
            # Guardar resultado usando el método de BaseAgent
            self.save_results(categoria_id, periodo, market_analysis)
            
            return market_analysis
        
        except Exception as e:
            self.logger.error(f"Error en análisis de contexto de mercado: {str(e)}", exc_info=True)
            return {'error': f'Error al analizar contexto: {str(e)}'}
    
    def _build_prompt(
        self,
        categoria: str,
        periodo: str,
        trends: Dict,
        competitive: Dict,
        quantitative: Dict,
        market_info: str
    ) -> str:
        """Construye el prompt para análisis de contexto"""
        
        prompt = f"""
{self.system_prompt}

Eres un consultor estratégico senior especializado en análisis de mercados FMCG.
Tu tarea es generar un análisis de contexto de mercado usando frameworks estratégicos.

CATEGORÍA: {categoria}
PERIODO: {periodo}

DATOS INTERNOS (Análisis previos):
- Total menciones: {quantitative.get('total_menciones', 0)}
- Líder de mercado: {competitive.get('lider_mercado', 'N/A')}
- Tendencias detectadas: {json.dumps(trends.get('tendencias', [])[:3], indent=2) if trends.get('tendencias') else 'N/A'}

INFORMACIÓN ACTUALIZADA DE MERCADO (Fuentes externas):
{market_info}

ANÁLISIS REQUERIDO:

1. PANORAMA GENERAL DEL MERCADO:
   - Descripción de la categoría y su evolución reciente
   - Tamaño estimado del mercado (si hay datos)
   - Tasa de crecimiento estimada o tendencia
   - Madurez del mercado (emergente, crecimiento, maduro, declive)

2. ANÁLISIS PESTEL ADAPTADO A FMCG:
   Identifica los factores más relevantes para esta categoría:
   
   - **Político-Legal**: Regulaciones, normativas de etiquetado, impuestos, políticas alimentarias
   - **Económico**: Inflación, poder adquisitivo, sensibilidad al precio, premiumización/downtrading
   - **Social**: Cambios en hábitos de consumo, tendencias demográficas, valores sociales
   - **Tecnológico**: E-commerce, innovación en producto/packaging, digitalización del retail
   - **Ecológico**: Sostenibilidad, packaging eco-friendly, huella de carbono
   - **Legal específico**: Normativas sanitarias, claims de salud, denominaciones de origen
   
   Para cada factor: Descripción + Impacto (Alto/Medio/Bajo) + Oportunidad o Amenaza

3. FUERZAS DE PORTER SIMPLIFICADAS:
   
   - **Rivalidad competitiva**: Intensidad de competencia (Alta/Media/Baja) + Descripción
   - **Poder de negociación de compradores**: Retail vs Consumidor final
   - **Poder de negociación de proveedores**: Dependencia de materias primas/insumos
   - **Amenaza de nuevos entrantes**: Barreras de entrada (capital, distribución, marca)
   - **Amenaza de sustitutos**: Productos alternativos que satisfacen la misma necesidad
   
   Para cada fuerza: Nivel (Alto/Medio/Bajo) + Impacto estratégico

4. DRIVERS DE CATEGORÍA:
   Identifica los 5-7 factores clave que impulsan el crecimiento y la elección en esta categoría:
   
   Ejemplos según categoría:
   - Innovación (nuevos sabores, formatos, ingredientes)
   - Precio/Promociones
   - Salud y nutrición
   - Conveniencia (facilidad de uso, portabilidad)
   - Sostenibilidad/Ética
   - Experiencia/Indulgencia
   - Marca/Reputación
   - Disponibilidad/Distribución
   
   Para cada driver: Importancia relativa (Crítico/Alto/Moderado) + Tendencia

5. SÍNTESIS ESTRATÉGICA:
   - ¿Cuáles son los 3 factores de contexto más críticos para el éxito en este mercado?
   - ¿Qué oportunidades del contexto externo no están siendo capitalizadas?
   - ¿Qué amenazas del entorno requieren atención prioritaria?

DEVUELVE JSON ESTRUCTURADO:
{{
  "panorama_general": {{
    "descripcion": "Descripción del mercado/categoría de 3-4 líneas",
    "tamano_estimado": "USD X millones / EUR X millones (si disponible)",
    "crecimiento_estimado": "+X% anual (si disponible)",
    "madurez": "emergente|crecimiento|maduro|declive",
    "caracteristicas_clave": ["característica 1", "característica 2"]
  }},
  "analisis_pestel": {{
    "politico_legal": {{
      "factores": ["Regulación 1", "Normativa 2"],
      "impacto": "alto|medio|bajo",
      "tipo": "oportunidad|amenaza|mixto",
      "descripcion": "Explicación del impacto"
    }},
    "economico": {{
      "factores": [],
      "impacto": "alto|medio|bajo",
      "tipo": "oportunidad|amenaza|mixto",
      "descripcion": ""
    }},
    "social": {{
      "factores": [],
      "impacto": "alto|medio|bajo",
      "tipo": "oportunidad|amenaza|mixto",
      "descripcion": ""
    }},
    "tecnologico": {{
      "factores": [],
      "impacto": "alto|medio|bajo",
      "tipo": "oportunidad|amenaza|mixto",
      "descripcion": ""
    }},
    "ecologico": {{
      "factores": [],
      "impacto": "alto|medio|bajo",
      "tipo": "oportunidad|amenaza|mixto",
      "descripcion": ""
    }},
    "legal_especifico": {{
      "factores": [],
      "impacto": "alto|medio|bajo",
      "tipo": "oportunidad|amenaza|mixto",
      "descripcion": ""
    }}
  }},
  "fuerzas_porter": {{
    "rivalidad_competitiva": {{
      "nivel": "alto|medio|bajo",
      "descripcion": "Análisis de la intensidad competitiva",
      "implicaciones": "Implicaciones estratégicas"
    }},
    "poder_compradores": {{
      "nivel": "alto|medio|bajo",
      "descripcion": "",
      "implicaciones": ""
    }},
    "poder_proveedores": {{
      "nivel": "alto|medio|bajo",
      "descripcion": "",
      "implicaciones": ""
    }},
    "amenaza_nuevos_entrantes": {{
      "nivel": "alto|medio|bajo",
      "descripcion": "",
      "implicaciones": ""
    }},
    "amenaza_sustitutos": {{
      "nivel": "alto|medio|bajo",
      "descripcion": "",
      "implicaciones": ""
    }}
  }},
  "drivers_categoria": [
    {{
      "driver": "Innovación",
      "importancia": "critico|alto|moderado",
      "tendencia": "creciente|estable|decreciente",
      "descripcion": "Por qué es importante y cómo evoluciona"
    }}
  ],
  "sintesis_estrategica": {{
    "factores_criticos_exito": ["Factor 1", "Factor 2", "Factor 3"],
    "oportunidades_contexto": ["Oportunidad 1 del entorno no capitalizada"],
    "amenazas_prioritarias": ["Amenaza 1 que requiere atención"],
    "insight_clave": "El insight más importante del análisis de contexto (2-3 líneas)"
  }},
  "metadata": {{
    "fuentes_consultadas": true/false,
    "nivel_certidumbre": "alto|medio|bajo",
    "actualizacion_recomendada": "trimestral|semestral|anual"
  }}
}}

IMPORTANTE:
- Usa la información externa para enriquecer el análisis
- Si no hay datos precisos de mercado, indica "estimación basada en análisis"
- Prioriza factores RELEVANTES para FMCG, no apliques todos genéricamente
- Sé específico y accionable, no genérico
- RESPONDE ÚNICAMENTE CON EL JSON VÁLIDO, SIN TEXTO ADICIONAL NI MARKDOWN
"""
        
        return prompt
    
    def _get_market_intelligence(self, categoria: str, periodo: str) -> str:
        """Obtiene información actualizada de mercado vía Perplexity"""
        
        try:
            # Query para obtener contexto actualizado
            query = f"Análisis del mercado de {categoria} en 2024-2025: tamaño, crecimiento, tendencias principales, regulaciones relevantes y factores clave de éxito"
            
            result = self.perplexity_client.generate(
                prompt=query,
                temperature=0.3,
                max_tokens=1500
            )
            
            return result.get('response_text', 'No se pudo obtener información actualizada.')
        
        except Exception as e:
            self.logger.warning(f"No se pudo obtener info de Perplexity: {str(e)}")
            return "No se pudo obtener información externa actualizada. Análisis basado en datos internos."
    
    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        """Helper para obtener análisis previo"""
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        
        return result.resultado if result else {}


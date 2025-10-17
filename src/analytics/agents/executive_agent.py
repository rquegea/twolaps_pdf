"""
Executive Agent
Síntesis ejecutiva final - Genera el informe completo
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult, Report, Categoria, Mercado
from src.query_executor.api_clients import OpenAIClient


class ExecutiveAgent(BaseAgent):
    """
    Agente ejecutivo
    Genera síntesis consultiva completa leyendo todos los análisis previos
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
                self.task_prompt = prompts.get('executive_agent', {}).get('task', '')
        
        if system_path.exists():
            with open(system_path, 'r', encoding='utf-8') as f:
                system = yaml.safe_load(f)
                self.system_prompt = system.get('base_consultant_role', '')
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Genera síntesis ejecutiva completa
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con informe completo estructurado
        """
        # Obtener información de categoría
        categoria = self.session.query(Categoria).get(categoria_id)
        if not categoria:
            return {'error': 'Categoría no encontrada'}
        
        mercado = self.session.query(Mercado).get(categoria.mercado_id)
        categoria_nombre = f"{mercado.nombre}/{categoria.nombre}"
        
        # Obtener todos los análisis previos
        quantitative = self._get_analysis('quantitative', categoria_id, periodo)
        sentiment = self._get_analysis('sentiment', categoria_id, periodo)
        attributes = self._get_analysis('attributes', categoria_id, periodo)
        competitive = self._get_analysis('competitive', categoria_id, periodo)
        trends = self._get_analysis('trends', categoria_id, periodo)
        strategic = self._get_analysis('strategic', categoria_id, periodo)
        
        if not quantitative or not sentiment or not competitive or not strategic:
            return {'error': 'Faltan análisis previos necesarios'}
        
        # Construir prompt completo con todos los KPIs
        prompt = self._build_prompt(
            categoria_nombre,
            periodo,
            quantitative,
            sentiment,
            attributes,
            competitive,
            trends,
            strategic
        )
        
        # Generar informe con LLM
        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.5,
                max_tokens=4000
            )
            
            # Parsear JSON
            informe = json.loads(result['response_text'])
            
            # Validar estructura
            informe = self._validate_and_complete_report(informe, quantitative, strategic)
            
            # Guardar en tabla reports
            report = Report(
                categoria_id=categoria_id,
                periodo=periodo,
                estado='draft',
                contenido=informe,
                generado_por=f"executive_agent_v{self.version}",
                metricas_calidad={
                    'hallazgos': len(informe.get('resumen_ejecutivo', {}).get('hallazgos', [])),
                    'oportunidades': len(informe.get('oportunidades_riesgos', {}).get('oportunidades', [])),
                    'riesgos': len(informe.get('oportunidades_riesgos', {}).get('riesgos', [])),
                    'plan_acciones': len(informe.get('plan_90_dias', {}).get('iniciativas', []))
                }
            )
            
            self.session.add(report)
            self.session.commit()
            
            return {
                'report_id': report.id,
                'informe': informe,
                'metadata': {
                    'categoria': categoria_nombre,
                    'periodo': periodo,
                    'tokens_usados': result.get('tokens_input', 0) + result.get('tokens_output', 0)
                }
            }
        
        except Exception as e:
            return {'error': f'Error al generar informe: {str(e)}'}
    
    def _build_prompt(
        self,
        categoria: str,
        periodo: str,
        quantitative: Dict,
        sentiment: Dict,
        attributes: Dict,
        competitive: Dict,
        trends: Dict,
        strategic: Dict
    ) -> str:
        """Construye el prompt completo con todos los datos"""
        
        prompt = f"""
{self.system_prompt}

GENERA UN INFORME EJECUTIVO COMPLETO DE CONSULTORÍA

CATEGORÍA: {categoria}
PERIODO: {periodo}

DATOS CUANTITATIVOS:
- Total menciones: {quantitative.get('total_menciones', 0)}
- Share of Voice: {json.dumps(quantitative.get('sov_percent', {}), indent=2)}
- Ranking: {json.dumps(quantitative.get('ranking', [])[:5], indent=2)}

SENTIMIENTO:
- Sentimiento global: {sentiment.get('sentimiento_global', 0):.2f}
- Por marca: {json.dumps(sentiment.get('por_marca', {}), indent=2)}

POSICIONAMIENTO COMPETITIVO:
- Líder de mercado: {competitive.get('lider_mercado', 'N/A')}
- Gaps competitivos: {json.dumps(competitive.get('gaps_competitivos', []), indent=2)}

TENDENCIAS:
{json.dumps(trends.get('tendencias', []), indent=2)}

ESTRATEGIA:
- Oportunidades: {json.dumps(strategic.get('oportunidades', []), indent=2)}
- Riesgos: {json.dumps(strategic.get('riesgos', []), indent=2)}

GENERA EL INFORME EN FORMATO JSON CON ESTA ESTRUCTURA EXACTA:
{{
  "resumen_ejecutivo": {{
    "hallazgos_clave": ["hallazgo 1", "hallazgo 2", "hallazgo 3"],
    "contexto": "párrafo de contexto"
  }},
  "mercado": {{
    "estado_general": "descripción del mercado",
    "volumen_conversacion": {quantitative.get('total_menciones', 0)},
    "principales_temas": ["tema 1", "tema 2"]
  }},
  "competencia": {{
    "lider": "{competitive.get('lider_mercado', '')}",
    "analisis_sov": "análisis del SOV",
    "comparativas": ["comparación 1", "comparación 2"]
  }},
  "sentimiento_reputacion": {{
    "resumen": "resumen de sentimiento",
    "por_marca_destacado": ["marca 1: análisis", "marca 2: análisis"]
  }},
  "oportunidades_riesgos": {{
    "oportunidades": {json.dumps(strategic.get('oportunidades', [])[:3])},
    "riesgos": {json.dumps(strategic.get('riesgos', [])[:3])}
  }},
  "plan_90_dias": {{
    "iniciativas": [
      {{
        "titulo": "iniciativa 1",
        "descripcion": "qué hacer",
        "por_que": "razón con datos",
        "como": "pasos concretos",
        "timeline": "Mes 1-2",
        "prioridad": "alta"
      }}
    ]
  }}
}}

IMPORTANTE:
- Cita SIEMPRE los KPIs y datos específicos
- Sé específico y accionable
- Evita vaguedades
- Todas las afirmaciones deben tener soporte cuantitativo
"""
        
        return prompt
    
    def _validate_and_complete_report(self, informe: Dict, quantitative: Dict, strategic: Dict) -> Dict:
        """Valida y completa el informe si falta algo"""
        
        # Asegurar secciones mínimas
        if 'resumen_ejecutivo' not in informe:
            informe['resumen_ejecutivo'] = {
                'hallazgos_clave': ['Análisis en proceso'],
                'contexto': 'Informe generado automáticamente'
            }
        
        if 'plan_90_dias' not in informe or not informe['plan_90_dias'].get('iniciativas'):
            # Generar plan básico desde oportunidades
            iniciativas = []
            for opp in strategic.get('oportunidades', [])[:3]:
                iniciativas.append({
                    'titulo': opp.get('titulo', ''),
                    'descripcion': opp.get('descripcion', ''),
                    'prioridad': opp.get('prioridad', 'media'),
                    'timeline': 'Mes 1-3'
                })
            
            informe['plan_90_dias'] = {'iniciativas': iniciativas}
        
        return informe
    
    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        """Helper para obtener análisis"""
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        
        return result.resultado if result else {}


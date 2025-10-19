"""
Executive Agent
Síntesis ejecutiva final - Genera el informe completo
"""

import json
from datetime import datetime
import yaml
from pathlib import Path
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.analytics.rag_manager import RAGManager
from src.database.models import AnalysisResult, Report, Categoria, Mercado
from src.query_executor.api_clients import OpenAIClient
from sqlalchemy.exc import IntegrityError


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
        synthesis = self._get_analysis('synthesis', categoria_id, periodo)
        
        if not quantitative or not sentiment or not competitive or not strategic or not synthesis:
            return {'error': 'Faltan análisis previos necesarios'}
        
        # ACTIVAR RAG - Obtener contexto histórico
        rag_manager = RAGManager(self.session)
        historical_context = rag_manager.get_historical_context(
            categoria_id,
            periodo,
            top_k=2
        )
        
        # Construir prompt completo con todos los KPIs
        prompt = self._build_prompt(
            categoria_nombre,
            periodo,
            quantitative,
            sentiment,
            attributes,
            competitive,
            trends,
            strategic,
            synthesis,
            historical_context
        )
        
        # Generar informe con LLM
        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.5,
                max_tokens=4000,
                json_mode=True
            )
            
            # Obtener respuesta
            response_text = result.get('response_text', '')
            
            # Log para debug
            self.logger.debug(f"Respuesta del LLM (primeros 500 chars): {response_text[:500]}")
            
            # Limpiar respuesta: extraer JSON si está dentro de markdown code blocks
            response_text = response_text.strip()
            
            # Si está en un code block de markdown, extraerlo
            if response_text.startswith('```'):
                # Buscar el inicio del JSON
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
            
            # Validar que no esté vacío
            if not response_text:
                self.logger.error("Respuesta vacía del LLM")
                return {'error': 'Respuesta vacía del LLM'}
            
            # Parsear JSON (intentando extraer el primer objeto JSON válido si hay ruido)
            try:
                informe = json.loads(response_text)
            except json.JSONDecodeError:
                # Intento de extracción simple del primer bloque JSON con llaves
                start = response_text.find('{')
                end = response_text.rfind('}')
                if start != -1 and end != -1 and end > start:
                    candidate = response_text[start:end+1]
                    try:
                        informe = json.loads(candidate)
                    except json.JSONDecodeError as e2:
                        self.logger.error(f"Error parseando JSON (2do intento): {e2}")
                        self.logger.error(f"Texto recibido: {response_text[:1000]}")
                        return {'error': f'Error parseando JSON del LLM: {str(e2)}'}
                else:
                    self.logger.error("No se encontró bloque JSON en la respuesta")
                    self.logger.error(f"Texto recibido: {response_text[:1000]}")
                    return {'error': 'Respuesta del LLM no contiene JSON válido'}
            
            # Validar estructura
            informe = self._validate_and_complete_report(informe, quantitative, strategic)
            
            # Guardar/actualizar en tabla reports (UPSERT por categoria_id + periodo)
            metrics = {
                'hallazgos': len(informe.get('resumen_ejecutivo', {}).get('hallazgos_clave', [])),
                'oportunidades': len(informe.get('oportunidades_riesgos', {}).get('oportunidades', [])),
                'riesgos': len(informe.get('oportunidades_riesgos', {}).get('riesgos', [])),
                'plan_acciones': len(informe.get('plan_90_dias', {}).get('iniciativas', []))
            }

            try:
                existing = self.session.query(Report).filter_by(
                    categoria_id=categoria_id,
                    periodo=periodo
                ).first()

                if existing:
                    existing.estado = 'draft'
                    existing.contenido = informe
                    existing.pdf_path = None
                    existing.generado_por = f"executive_agent_v{self.version}"
                    existing.timestamp = datetime.utcnow()
                    existing.metricas_calidad = metrics
                    self.session.commit()
                    report = existing
                else:
                    report = Report(
                        categoria_id=categoria_id,
                        periodo=periodo,
                        estado='draft',
                        contenido=informe,
                        pdf_path=None,
                        generado_por=f"executive_agent_v{self.version}",
                        timestamp=datetime.utcnow(),
                        metricas_calidad=metrics
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
            except IntegrityError as e:
                self.session.rollback()
                return {'error': f'Error al guardar reporte: {str(e)}'}
        
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
        strategic: Dict,
        synthesis: Dict,
        historical_context: str
    ) -> str:
        """Construye el prompt completo con todos los datos"""
        
        prompt = f"""
{self.system_prompt}

HAS SIDO CONTRATADO PARA GENERAR EL PLAN DE ACCIÓN Y EL RESUMEN EJECUTIVO.

CATEGORÍA: {categoria}
PERIODO: {periodo}

NARRATIVA CENTRAL (SITUACIÓN-COMPLICACIÓN):
Situación: {synthesis.get('situacion', '')}
Complicación: {synthesis.get('complicacion', '')}
Pregunta Clave: {synthesis.get('pregunta_clave', '')}

CONTEXTO HISTÓRICO (PERIODOS ANTERIORES):
{historical_context}

DATOS DE SOPORTE (KPIs Y ESTRATEGIA):
- Total menciones: {quantitative.get('total_menciones', 0)}
- SOV: {json.dumps(quantitative.get('sov_percent', {}), indent=2)}
- Sentimiento: {json.dumps(sentiment.get('por_marca', {}), indent=2)}
- Líder de mercado: {competitive.get('lider_mercado', 'N/A')}
- Oportunidades: {json.dumps(strategic.get('oportunidades', []), indent=2)}
- Riesgos: {json.dumps(strategic.get('riesgos', []), indent=2)}

INSTRUCCIONES:
Basándote en la NARRATIVA CENTRAL y el CONTEXTO HISTÓRICO, y usando los DATOS DE SOPORTE para justificar cada afirmación:

1. Genera el "resumen_ejecutivo": 3-5 hallazgos clave que respondan a la "pregunta_clave" de la narrativa.
2. Genera el "plan_90_dias": 3 iniciativas accionables que resuelvan la "complicacion".

GENERA EL INFORME EN FORMATO JSON CON ESTA ESTRUCTURA EXACTA:
{{
  "resumen_ejecutivo": {{
    "hallazgos_clave": ["hallazgo 1 (citando KPI)", "hallazgo 2 (comparando con contexto histórico si es relevante)", "hallazgo 3"],
    "contexto": "{synthesis.get('situacion', '')} {synthesis.get('complicacion', '')}"
  }},
  "mercado": {{
    "estado_general": "{synthesis.get('situacion', '')}",
    "volumen_conversacion": {quantitative.get('total_menciones', 0)},
    "principales_temas": ["tema 1", "tema 2"]
  }},
  "competencia": {{
    "lider": "{competitive.get('lider_mercado', '')}",
    "analisis_sov": "análisis del SOV con datos específicos",
    "comparativas": ["comparación 1", "comparación 2"]
  }},
  "sentimiento_reputacion": {{
    "resumen": "resumen de sentimiento con datos específicos",
    "por_marca_destacado": ["marca 1: análisis", "marca 2: análisis"]
  }},
  "oportunidades_riesgos": {{
    "oportunidades": {json.dumps(strategic.get('oportunidades', [])[:3])},
    "riesgos": {json.dumps(strategic.get('riesgos', [])[:3])}
  }},
  "plan_90_dias": {{
    "iniciativas": [
      {{
        "titulo": "iniciativa 1 (clara y accionable)",
        "descripcion": "qué hacer exactamente",
        "por_que": "razón basada en la NARRATIVA y DATOS (ej: 'Para resolver la complicación de...')",
        "como": "3-4 pasos concretos o tácticas",
        "kpi_medicion": "Métrica para medir el éxito (ej: 'Aumentar score de sentimiento a > 0.5')",
        "timeline": "Mes 1-2",
        "prioridad": "alta"
      }}
    ]
  }}
}}

IMPORTANTE:
- Cita SIEMPRE los KPIs y datos específicos
- El "plan_90_dias" debe resolver la "complicacion" identificada en la NARRATIVA
- Usa el contexto histórico cuando sea relevante para comparaciones
- RESPONDE ÚNICAMENTE CON EL JSON VÁLIDO, SIN TEXTO ADICIONAL NI MARKDOWN
- NO uses bloques de código markdown (```), solo el JSON puro
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


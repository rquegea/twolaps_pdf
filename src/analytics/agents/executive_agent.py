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
        # task/system prompts se cargarán dinámicamente al analizar
    
    def load_prompts(self):
        """Compat: método legado no usado."""
        pass
    
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
        # Cargar prompts según tipo de mercado
        self.load_prompts_dynamic(categoria_id, default_key='executive_agent')
        quantitative = self._get_analysis('quantitative', categoria_id, periodo)
        qualitative = self._get_analysis('qualitative', categoria_id, periodo)
        if not qualitative:
            qualitative = self._get_analysis('qualitativeextraction', categoria_id, periodo)
        competitive = self._get_analysis('competitive', categoria_id, periodo)
        trends = self._get_analysis('trends', categoria_id, periodo)
        strategic = self._get_analysis('strategic', categoria_id, periodo)
        synthesis = self._get_analysis('synthesis', categoria_id, periodo)
        
        # NUEVO: Obtener análisis FMCG especializados
        campaign = self._get_analysis('campaign_analysis', categoria_id, periodo)
        channel = self._get_analysis('channel_analysis', categoria_id, periodo)
        esg = self._get_analysis('esg_analysis', categoria_id, periodo)
        packaging = self._get_analysis('packaging_analysis', categoria_id, periodo)
        
        # Degradación para primer ciclo: si faltan algunos análisis, generamos un informe mínimo
        missing = []
        if not quantitative:
            missing.append('quantitative')
        if not qualitative:
            missing.append('qualitative')
        if not competitive:
            missing.append('competitive')
        if not strategic:
            missing.append('strategic')
        if not synthesis:
            missing.append('synthesis')
        
        if missing:
            self.logger.warning(f"Faltan análisis previos: {', '.join(missing)}. Generando informe mínimo.")
        
        # ACTIVAR RAG - Obtener contexto histórico
        rag_manager = RAGManager(self.session)
        historical_context = rag_manager.get_historical_context(
            categoria_id,
            periodo,
            top_k=2
        )
        
        # NUEVO: Obtener muestra estratificada de respuestas textuales
        raw_responses = self._get_stratified_sample(categoria_id, periodo, samples_per_group=2)
        
        # Construir prompt completo con todos los KPIs Y respuestas textuales
        prompt = self._build_prompt(
            categoria_nombre,
            periodo,
            quantitative,
            qualitative,
            competitive,
            trends,
            strategic,
            synthesis,
            historical_context,
            raw_responses,
            campaign,
            channel,
            esg,
            packaging
        )
        
        # Generar informe con LLM (tokens aumentados para informe extenso de nivel consultora)
        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.5,
                max_tokens=10000,  # Aumentado de 6000 a 10000 para permitir mayor extensión
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
        qualitative: Dict,
        competitive: Dict,
        trends: Dict,  # pylint: disable=unused-argument
        strategic: Dict,
        synthesis: Dict,
        historical_context: str,
        raw_responses: str,
        campaign: Dict,
        channel: Dict,
        esg: Dict,
        packaging: Dict
    ) -> str:
        """Construye el prompt completo con todos los datos (EXPANDIDO para FMCG Premium)"""
        
        prompt = f"""
{self.system_prompt}

HAS SIDO CONTRATADO PARA GENERAR EL INFORME ESTRATÉGICO COMPLETO ESTILO NIELSEN/KANTAR.

CATEGORÍA: {categoria}
PERIODO: {periodo}

========================================
NARRATIVA CENTRAL (SITUACIÓN-COMPLICACIÓN-PREGUNTA):
========================================
Situación: {synthesis.get('situacion', '')}
Complicación: {synthesis.get('complicacion', '')}
Pregunta Clave: {synthesis.get('pregunta_clave', '')}

========================================
CONTEXTO HISTÓRICO:
========================================
{historical_context}

========================================
DATOS CUANTITATIVOS (KPIs):
========================================
- Total menciones: {quantitative.get('total_menciones', 0)}
- SOV: {json.dumps(quantitative.get('sov_percent', {}), indent=2)}
- Sentimiento: {json.dumps(qualitative.get('sentimiento_por_marca', {}), indent=2)}
- Líder mercado: {competitive.get('lider_mercado', 'N/A')}

========================================
ANÁLISIS FMCG DETALLADO:
========================================

ANÁLISIS DE CAMPAÑAS Y MARKETING:
{json.dumps(campaign, indent=2) if campaign else 'No disponible'}

ANÁLISIS DE CANALES Y DISTRIBUCIÓN:
{json.dumps(channel, indent=2) if channel else 'No disponible'}

ANÁLISIS ESG Y SOSTENIBILIDAD:
{json.dumps(esg, indent=2) if esg else 'No disponible'}

ANÁLISIS DE PACKAGING Y DISEÑO:
{json.dumps(packaging, indent=2) if packaging else 'No disponible'}

========================================
ANÁLISIS ESTRATÉGICO (DAFO, OPORTUNIDADES, RIESGOS):
========================================
- DAFO: {json.dumps(strategic.get('dafo', {}), indent=2)}
- Oportunidades: {json.dumps(strategic.get('oportunidades', [])[:3], indent=2)}
- Riesgos: {json.dumps(strategic.get('riesgos', [])[:3], indent=2)}

========================================
MUESTRA DE RESPUESTAS TEXTUALES (AMPLIADA):
========================================
{raw_responses[:4000]}

========================================
INSTRUCCIONES DE GENERACIÓN:
========================================

Genera un informe ejecutivo completo integrando TODAS las dimensiones: KPIs, Contexto de Mercado, Competencia, Marketing, Canales y Estrategia.

ESTRUCTURA JSON EXPANDIDA REQUERIDA:

{{
  "resumen_ejecutivo": {{
    "hallazgos_clave": [
      "Hallazgo 1 integrado con datos específicos",
      "Hallazgo 2 que responde a la pregunta clave",
      "Hallazgo 3 accionable"
    ],
    "contexto": "Resumen de situación y complicación (2-3 líneas)"
  }},
  
  "panorama_mercado": {{
    "contexto_fmcg": "Descripción del mercado/categoría (2-3 líneas)",
    "tamano_crecimiento": "Tamaño y crecimiento estimado si disponible",
    "drivers_principales": ["Driver 1", "Driver 2", "Driver 3"],
    "factores_pestel_clave": [
      "Factor PESTEL más relevante 1",
      "Factor PESTEL más relevante 2"
    ],
    "fuerzas_competitivas": "Resumen de intensidad competitiva y principales fuerzas de Porter"
  }},
  
  "analisis_competitivo": {{
    "lider": "{competitive.get('lider_mercado', '')}",
    "sov_tendencias": "Análisis de cuota de voz y tendencias con datos",
    "benchmarking_resumen": "Resumen de cómo se comparan las marcas en atributos clave",
    "perfiles_top3": [
      {{
        "marca": "Marca 1",
        "posicionamiento": "Breve descripción",
        "fortalezas": ["F1", "F2"],
        "debilidades": ["D1", "D2"]
      }}
    ]
  }},
  
  "analisis_campanas": {{
    "resumen_actividad": "Síntesis de las principales campañas, canales y mensajes clave (usando datos de Campañas)",
    "marca_mas_activa": "Marca X",
    "insights_recepcion": ["Recepción cualitativa de campañas..."]
  }},
  
  "analisis_canales": {{
    "estrategia_canal_inferida": "Resumen de cómo se distribuyen las marcas (usando datos de Canales)",
    "gaps_e_commerce": ["Principales fallos o aciertos en la experiencia online..."],
    "marca_mejor_distribuida": "Marca Y"
  }},
  
  "analisis_sostenibilidad_packaging": {{
    "resumen_esg": "Análisis de la percepción de sostenibilidad del mercado (usando datos ESG)",
    "quejas_packaging": "Análisis de problemas funcionales o de diseño (usando datos Packaging)",
    "benchmarking_atributos": ["Marca X lidera en packaging funcional, Marca Y en percepción ESG."]
  }},
  
  "consumidor": {{
    "voz_cliente_resumen": "Principales temas y preocupaciones de consumidores",
    "drivers_eleccion": ["Driver 1", "Driver 2"],
    "barreras_compra": ["Barrera 1", "Barrera 2"],
    "ocasiones_principales": ["Ocasión 1", "Ocasión 2"]
  }},
  
  "sentimiento_reputacion": {{
    "resumen": "Análisis de sentimiento con datos específicos por marca",
    "correlaciones": "Correlaciones entre sentimiento, SOV y actividad de marketing"
  }},
  
  "oportunidades_riesgos": {{
    "oportunidades": {json.dumps(strategic.get('oportunidades', [])[:3])},
    "riesgos": {json.dumps(strategic.get('riesgos', [])[:3])},
    "dafo_sintesis": {{
      "fortalezas_clave": ["F1", "F2"],
      "debilidades_clave": ["D1", "D2"],
      "oportunidades_clave": ["O1", "O2"],
      "amenazas_clave": ["A1", "A2"]
    }}
  }},
  
  "plan_90_dias": {{
    "iniciativas": [
      {{
        "titulo": "Iniciativa 1 accionable",
        "descripcion": "Qué hacer exactamente",
        "por_que": "Razón estratégica basada en la complicación y datos",
        "como": "Pasos concretos o tácticas",
        "kpi_medicion": "Métrica para medir éxito",
        "timeline": "Mes 1-2",
        "prioridad": "alta"
      }}
    ]
  }}
}}

REGLAS CRÍTICAS:
1. INTEGRA todas las dimensiones: KPIs + ANÁLISIS FMCG (Campañas, Canales, ESG, Packaging) + Estrategia
2. El Resumen Ejecutivo (punto 1) y el Plan de 90 Días deben ser la culminación de TODOS los datos disponibles, especialmente el ANÁLISIS FMCG DETALLADO
3. CITA los datos de Campañas, Canales, ESG y Packaging en las secciones correspondientes (analisis_campanas, analisis_canales, analisis_sostenibilidad_packaging)
4. Cada afirmación debe estar FUNDAMENTADA con datos específicos
5. El plan de 90 días debe RESOLVER la complicación identificada
6. Prioriza INSIGHTS ACCIONABLES sobre descripciones genéricas
7. RESPONDE ÚNICAMENTE CON EL JSON VÁLIDO, SIN TEXTO ADICIONAL NI MARKDOWN
8. NO uses bloques de código markdown (```), solo el JSON puro
"""
        
        return prompt
    
    def _validate_and_complete_report(self, informe: Dict, quantitative: Dict, strategic: Dict) -> Dict:  # pylint: disable=unused-argument
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


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
                temperature=0.7,   # Mayor creatividad para narrativas fluidas tipo McKinsey
                max_tokens=16000,  # 🔥 Límite máximo (16K permite informes de 35-50 páginas con densidad máxima)
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

===========================================
MISIÓN: GENERAR INFORME NARRATIVO TIPO McKINSEY
===========================================

⚠️ NO GENERES UN "DUMP" DE DATOS. CUENTA UNA HISTORIA ESTRATÉGICA. ⚠️

REGLAS NARRATIVAS CRÍTICAS:
1. Cada sección debe DESARROLLARSE en 3-7 párrafos fluidos y conectados
2. NO uses listas de bullets como respuesta principal (úsalas solo para respaldar narrativas)
3. USA transiciones narrativas: "Esto explica...", "Sin embargo...", "A pesar de...", "Lo que revela..."
4. CITA datos específicos DENTRO de las narrativas (no como apéndices)
5. CONECTA insights entre secciones para construir un argumento coherente
6. Escribe como si estuvieras presentando en vivo a un CEO

CATEGORÍA: {categoria}
PERIODO: {periodo}

========================================
NARRATIVA CENTRAL (TU GUION):
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
- Oportunidades: {json.dumps(strategic.get('oportunidades', [])[:5], indent=2)}
- Riesgos: {json.dumps(strategic.get('riesgos', [])[:5], indent=2)}

========================================
MUESTRA DE RESPUESTAS TEXTUALES (PARA CITAS):
========================================
{raw_responses[:4000]}

========================================
ESTRUCTURA JSON NARRATIVA REQUERIDA:
========================================

⚠️ IMPORTANTE: Los campos "narrativa_*" y "narrativa" son el CONTENIDO PRINCIPAL del informe.
Cada uno debe tener 3-7 párrafos sustanciales desarrollando el argumento.

{{
  "resumen_ejecutivo": {{
    "narrativa_principal": "DESARROLLA EN 4-6 PÁRRAFOS: Empieza con la situación del mercado (integrando KPIs clave como SOV, menciones, tendencias), luego desarrolla la complicación (la tensión estratégica central con evidencia cuantitativa + citas cualitativas del raw_responses), y finalmente responde a la pregunta clave con los hallazgos principales y su implicación. Esta debe ser una narrativa fluida y argumentativa, no una lista.",
    "hallazgos_clave": [
      "Hallazgo 1 con evidencia integrada (KPI + cita cualitativa)",
      "Hallazgo 2 respondiendo a la pregunta clave",
      "Hallazgo 3 accionable con implicación de negocio",
      "Hallazgo 4",
      "Hallazgo 5"
    ],
    "recomendacion_principal": "1-2 párrafos con la recomendación estratégica de más alto nivel, vinculada a resolver la complicación"
  }},
  
  "panorama_mercado": {{
    "narrativa": "DESARROLLA EN 5-7 PÁRRAFOS: Describe la naturaleza del mercado/categoría (usando la situación del synthesis_agent como apertura), tamaño y crecimiento si disponible, drivers de categoría principales con ejemplos específicos de cómo impactan decisiones, factores PESTEL más relevantes con implicaciones concretas (NO genéricas), análisis de Fuerzas de Porter adaptado a este mercado. Cuenta cómo funciona este mercado y qué factores lo moldean. Conecta los factores entre sí."
  }},
  
  "analisis_competitivo": {{
    "narrativa_dinamica": "DESARROLLA EN 4-6 PÁRRAFOS: Analiza la dinámica competitiva actual: quién domina y por qué (con datos de SOV y sentimiento), cómo se posicionan las marcas principales, correlaciones entre visibilidad/percepción/marketing/canal, gaps competitivos explotables. Conecta múltiples dimensiones para revelar la historia competitiva. Menciona explícitamente 'Como muestra el Gráfico de SOV...'",
    "perfiles_narrativos": [
      {{
        "marca": "Marca Principal 1",
        "analisis_profundo": "DESARROLLA EN 2-3 PÁRRAFOS: Posicionamiento percibido con evidencia, fortalezas clave sustentadas por datos, debilidades y vulnerabilidades específicas, estrategia de marketing y canal inferida, oportunidades de ataque o defensa. Cuenta la historia de esta marca en el mercado."
      }},
      {{
        "marca": "Marca Principal 2",
        "analisis_profundo": "DESARROLLA EN 2-3 PÁRRAFOS: [Mismo formato]"
      }},
      {{
        "marca": "Marca Principal 3",
        "analisis_profundo": "DESARROLLA EN 2-3 PÁRRAFOS: [Mismo formato]"
      }}
    ]
  }},
  
  "analisis_campanas": {{
    "narrativa": "DESARROLLA EN 3-5 PÁRRAFOS: Síntesis de la actividad de marketing en el mercado: qué marcas comunican activamente y cómo, principales campañas y mensajes clave, canales utilizados, percepción de efectividad y recepción cualitativa, gaps (marcas silenciosas o con comunicación inefectiva a pesar de alto SOV). Usa datos del análisis de Campañas."
  }},
  
  "analisis_canales": {{
    "narrativa": "DESARROLLA EN 3-5 PÁRRAFOS: Estrategias de distribución observadas (intensiva/selectiva/exclusiva), ventajas competitivas en accesibilidad y presencia omnicanal, gaps de e-commerce y oportunidades digitales, retailers clave y experiencia de compra diferenciada. Usa datos del análisis de Canales."
  }},
  
  "analisis_sostenibilidad_packaging": {{
    "narrativa": "DESARROLLA EN 3-4 PÁRRAFOS: Percepción ESG del mercado (controversias, líderes, rezagados), análisis de packaging (problemas funcionales, diseño, innovaciones), importancia relativa de ESG y packaging como drivers de decisión, oportunidades de diferenciación. Conecta ESG y packaging cuando sea relevante."
  }},
  
  "consumidor": {{
    "narrativa_voz_cliente": "DESARROLLA EN 4-5 PÁRRAFOS: Integra citas textuales directas del raw_responses para dar vida a la voz del consumidor. Desarrolla drivers de elección con ejemplos específicos de POR QUÉ eligen cada marca, explica barreras de compra con evidencia cualitativa, describe ocasiones de consumo principales y cómo impactan la decisión, identifica tensiones o contradicciones. HAZ QUE EL CONSUMIDOR COBRE VIDA con sus propias palabras entrecomilladas."
  }},
  
  "sentimiento_reputacion": {{
    "narrativa": "DESARROLLA EN 3-4 PÁRRAFOS: Presenta scores de sentimiento por marca con contexto (no solo números), EXPLICA el 'por qué' detrás de cada score con insights cualitativos del texto crudo, analiza correlaciones entre sentimiento/SOV/marketing, identifica cambios vs periodos anteriores si hay contexto histórico. Menciona 'Como muestra el Gráfico de Sentimiento...'"
  }},
  
  "oportunidades_riesgos": {{
    "narrativa_oportunidades": "DESARROLLA EN 3-4 PÁRRAFOS: Profundiza en las TOP 3-5 oportunidades más críticas, explicando la lógica, evidencia multi-fuente, impacto potencial, y cómo capitalizarlas. Conecta oportunidades entre sí si es relevante.",
    "narrativa_riesgos": "DESARROLLA EN 3-4 PÁRRAFOS: Profundiza en los TOP 3-5 riesgos más graves, explicando probabilidad, severidad, evidencia, y estrategias de mitigación. Identifica escenarios de mayor peligro.",
    "oportunidades": {json.dumps(strategic.get('oportunidades', [])[:5])},
    "riesgos": {json.dumps(strategic.get('riesgos', [])[:5])},
    "dafo_sintesis": {{
      "fortalezas_clave": ["F1", "F2", "F3"],
      "debilidades_clave": ["D1", "D2", "D3"],
      "oportunidades_clave": ["O1", "O2", "O3"],
      "amenazas_clave": ["A1", "A2", "A3"],
      "cruces_estrategicos": "DESARROLLA EN 2-3 PÁRRAFOS: Analiza los cruces DAFO más relevantes (FO: cómo usar fortalezas para oportunidades, DO: cómo superar debilidades para oportunidades, FA: cómo usar fortalezas contra amenazas, DA: escenarios de mayor riesgo)"
    }}
  }},
  
  "plan_90_dias": {{
    "narrativa_estrategia": "DESARROLLA EN 2-3 PÁRRAFOS: Explica la lógica del plan de acción completo: por qué estas iniciativas, en este orden, para resolver la complicación identificada. Justifica la priorización.",
    "iniciativas": [
      {{
        "titulo": "Iniciativa 1",
        "descripcion": "QUÉ hacer exactamente (2-3 líneas detalladas, NO bullets)",
        "por_que": "POR QUÉ hacerlo - vinculado explícitamente a la complicación y datos específicos (2-3 líneas)",
        "como": "CÓMO ejecutarlo con pasos concretos o tácticas (2-3 líneas)",
        "kpi_medicion": "Métrica específica para medir éxito",
        "timeline": "Mes 1-2",
        "prioridad": "alta"
      }},
      {{
        "titulo": "Iniciativa 2",
        "descripcion": "...",
        "por_que": "...",
        "como": "...",
        "kpi_medicion": "...",
        "timeline": "Mes 2-3",
        "prioridad": "alta"
      }},
      {{
        "titulo": "Iniciativa 3",
        "descripcion": "...",
        "por_que": "...",
        "como": "...",
        "kpi_medicion": "...",
        "timeline": "Mes 2-3",
        "prioridad": "media"
      }},
      {{
        "titulo": "Iniciativa 4",
        "descripcion": "...",
        "por_que": "...",
        "como": "...",
        "kpi_medicion": "...",
        "timeline": "Mes 3",
        "prioridad": "media"
      }},
      {{
        "titulo": "Iniciativa 5",
        "descripcion": "...",
        "por_que": "...",
        "como": "...",
        "kpi_medicion": "...",
        "timeline": "Mes 3",
        "prioridad": "baja"
      }}
    ]
  }}
}}

REGLAS CRÍTICAS DE NARRATIVA:
1. **NARRATIVA SOBRE BULLETS**: Los campos "narrativa_*" y "narrativa" son el CONTENIDO PRINCIPAL. Los bullets son complemento.
2. **TRANSICIONES**: Usa conectores argumentativos: "Esto explica...", "Sin embargo...", "A pesar de...", "Lo que revela..."
3. **INTEGRACIÓN DE DATOS**: Cita KPIs DENTRO de las narrativas: "El líder domina con 54% de SOV, sin embargo, su sentimiento neutral (0.05) revela..."
4. **CITAS TEXTUALES**: Incluye citas directas del raw_responses: "Como menciona un consumidor: '...'"
5. **REFERENCIAS A GRÁFICOS**: Menciona explícitamente: "Como muestra el Gráfico de SOV..."
6. **CONEXIONES**: Crea puentes narrativos entre secciones para mantener el hilo argumentativo
7. **INTEGRA TODO**: KPIs + FMCG (Campañas, Canales, ESG, Packaging) + Estrategia en una historia cohesiva
8. **PROFUNDIDAD**: Cada campo narrativo debe tener 3-7 párrafos sustanciales (4-8 líneas cada uno)
9. **El plan de 90 días debe RESOLVER la complicación identificada**
10. **RESPONDE ÚNICAMENTE CON EL JSON VÁLIDO, SIN TEXTO ADICIONAL NI MARKDOWN, SIN BLOQUES DE CÓDIGO**
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


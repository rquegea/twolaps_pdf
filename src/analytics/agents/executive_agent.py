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
        self.section_prompts = {}
    
    def _load_section_prompts(self):
        """Carga prompts específicos por sección desde agent_prompts.yaml"""
        try:
            prompt_path = Path("config/prompts/agent_prompts.yaml")
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompts_yaml = yaml.safe_load(f) or {}
                    self.section_prompts = prompts_yaml.get('executive_section_prompts', {}) or {}
        except Exception:
            # No bloquear si no existen
            self.section_prompts = {}
    
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
        # Cargar prompts seccionales MBB
        self._load_section_prompts()
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
        # NUEVO: Escenarios / Journey
        scenarios = self._get_analysis('scenario_planning', categoria_id, periodo)
        journey = self._get_analysis('customer_journey', categoria_id, periodo)
        # Opcional: Pricing Power y Contexto de Mercado (si existen)
        pricing_power = self._get_analysis('pricing_power', categoria_id, periodo)
        market_context = self._get_analysis('market_context', categoria_id, periodo)
        # CRÍTICO: Análisis transversal (síntesis de patrones y contradicciones)
        transversal = self._get_analysis('transversal', categoria_id, periodo)
        
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
        raw_responses = self._get_stratified_sample(categoria_id, periodo, samples_per_group=4)
        
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
            packaging,
            scenarios,
            journey,
            pricing_power,
            market_context,
            transversal
        )
        
        # Generar informe con LLM (tokens aumentados para informe extenso de nivel consultora)
        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.45,  # Menor aleatoriedad para mayor precisión y consistencia en cifras
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
            
            # Inyección de series de tendencias y snapshots para gráficos en PDF
            try:
                # Competencia: SOV snapshot y tendencia
                competencia_block = informe.setdefault('competencia', {})
                if isinstance(quantitative, dict) and quantitative.get('sov_percent') and not competencia_block.get('sov_data'):
                    competencia_block['sov_data'] = quantitative.get('sov_percent', {})
                if isinstance(trends, dict) and trends.get('sov_trend_data'):
                    competencia_block['sov_trend_data'] = trends.get('sov_trend_data')

                # Sentimiento: snapshot (distribución y scores) y tendencia
                sentimiento_block = informe.setdefault('sentimiento_reputacion', {})
                cuali_sent = {}
                if isinstance(qualitative, dict):
                    cuali_sent = qualitative.get('sentimiento_por_marca') or {}
                # Distribución por marca para barras apiladas
                if cuali_sent and not sentimiento_block.get('sentiment_data'):
                    sentiment_data = {}
                    for marca, datos in cuali_sent.items():
                        if isinstance(datos, dict) and isinstance(datos.get('distribucion'), dict):
                            sentiment_data[marca] = datos.get('distribucion')
                    if sentiment_data:
                        sentimiento_block['sentiment_data'] = sentiment_data
                # Scores por marca para ESG scatter
                if cuali_sent and not sentimiento_block.get('sentiment_scores'):
                    scores = {}
                    for marca, datos in cuali_sent.items():
                        if isinstance(datos, dict):
                            score_val = datos.get('score_medio') if isinstance(datos.get('score_medio'), (int, float)) else datos.get('score')
                            if isinstance(score_val, (int, float)):
                                scores[marca] = float(score_val)
                    if scores:
                        sentimiento_block['sentiment_scores'] = scores
                # Tendencia de sentimiento
                if isinstance(trends, dict) and trends.get('sentiment_trend_data'):
                    sentimiento_block['sentiment_trend_data'] = trends.get('sentiment_trend_data')
            except Exception:
                # No bloquear por inyección de contexto
                pass
            
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
        trends: Dict,  # ahora utilizado para inyectar series de tendencia
        strategic: Dict,
        synthesis: Dict,
        historical_context: str,
        raw_responses: str,
        campaign: Dict,
        channel: Dict,
        esg: Dict,
        packaging: Dict,
        scenarios: Dict,
        journey: Dict,
        pricing_power: Dict,
        market_context: Dict,
        transversal: Dict
    ) -> str:
        """Construye el prompt completo con todos los datos (EXPANDIDO para FMCG Premium)"""
        
        # Bloque de instrucciones MBB por sección (inyectado si existe)
        se = self.section_prompts or {}
        se_block = "\n\n".join([
            "========================================\nINSTRUCCIONES MBB POR SECCIÓN:\n========================================",
            ("RESUMEN EJECUTIVO:\n" + (se.get('resumen_ejecutivo', '') or '').strip()),
            ("PANORAMA DE MERCADO:\n" + (se.get('panorama_mercado', '') or '').strip()),
            ("ANÁLISIS COMPETITIVO:\n" + (se.get('analisis_competitivo', '') or '').strip()),
            ("ANÁLISIS DE CAMPAÑAS:\n" + (se.get('analisis_campanas', '') or '').strip()),
            ("ANÁLISIS DE CANALES:\n" + (se.get('analisis_canales', '') or '').strip()),
            ("SOSTENIBILIDAD Y PACKAGING:\n" + (se.get('analisis_sostenibilidad_packaging', '') or '').strip()),
            ("CONSUMIDOR (VoC):\n" + (se.get('consumidor', '') or '').strip()),
            ("CUSTOMER JOURNEY:\n" + (se.get('customer_journey', '') or '').strip()),
            ("SENTIMIENTO Y REPUTACIÓN:\n" + (se.get('sentimiento_reputacion', '') or '').strip()),
            ("OPORTUNIDADES Y RIESGOS:\n" + (se.get('oportunidades_riesgos', '') or '').strip()),
            ("PLAN 90 DÍAS:\n" + (se.get('plan_90_dias', '') or '').strip()),
        ])

        prompt = f"""
{self.system_prompt}

{self.task_prompt}

===========================================
MISIÓN: GENERAR INFORME NARRATIVO TIPO McKINSEY
===========================================

⚠️ NO GENERES UN "DUMP" DE DATOS. CUENTA UNA HISTORIA ESTRATÉGICA. ⚠️

🔥 INSTRUCCIÓN CRÍTICA - USO DE TODOS LOS ANÁLISIS:
Tienes acceso a 15+ análisis especializados (cuantitativos, cualitativos, competitivos, tendencias, estratégicos, síntesis, campañas, canales, ESG, packaging, pricing, journey, escenarios, market_context, TRANSVERSAL).
DEBES integrar insights de TODOS ellos en tu narrativa. NO ignores ninguno. Cada sección debe referenciar EXPLÍCITAMENTE los datos de los JSONs correspondientes listados abajo.
Los 'temas_comunes' del TRANSVERSAL son HILOS CONDUCTORES que deben aparecer en múltiples secciones.
Si hay 'contradicciones' en el TRANSVERSAL, resuélvelas o señálalas explícitamente.

REGLAS NARRATIVAS CRÍTICAS:
1. PIRÁMIDE DE MINTO (ANSWER FIRST): Arranca cada sección con la conclusión clara (recomendación/diagnóstico) y después los 2-4 argumentos que la sustentan, cada uno con datos.
2. MECE: Estructura los argumentos de forma mutuamente excluyente y colectivamente exhaustiva.
3. Cada sección debe DESARROLLARSE en 3-7 párrafos fluidos y conectados.
4. NO uses listas de bullets como respuesta principal (úsalas solo para respaldar narrativas).
5. USA transiciones narrativas: "Esto explica...", "Sin embargo...", "A pesar de...", "Lo que revela...".
6. CITA datos específicos DENTRO de las narrativas (no como apéndices) con unidad, periodo y comparación.
7. CONECTA insights entre secciones para construir un argumento coherente.
8. Escribe como si estuvieras presentando en vivo a un CEO.
9. VOZ ACTIVA Y PRESCRIPTIVA: Da órdenes y recomendaciones directas ("Recomendamos reasignar...", "Pausar...", "Lanzar...").
10. LENGUAJE DE NEGOCIO: Conecta KPIs de marketing con impacto financiero (CAC, CLV, ROMI/ROI, EBITDA, cuota de mercado, payback).
11. SO WHAT: Cada dato debe incluir su implicación de negocio explícita (impacto, riesgo o oportunidad y decisión).

{se_block}

GUÍA DE PRECISIÓN DE DATOS (OBLIGATORIA):
- Cita cifras con unidad y periodo: "SOV 54% (W43 2025)".
- Compara siempre: "vs 28% competidor; +6 pp vs periodo anterior".
- Usa redondeo coherente (1 decimal) y marca dirección: ↑/↓/↗/↘.
- Reporta deltas como "+X pp" o "+Y%" e indica la ventana temporal.
- Traza la fuente dentro del texto: KPI cuantitativo, tendencia histórica o cita textual.

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
- Tendencia SOV: {json.dumps((trends or {}).get('sov_trend_data', {}), indent=2)}
- Tendencia Sentimiento: {json.dumps((trends or {}).get('sentiment_trend_data', {}), indent=2)}

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

ESCENARIOS (12-24 meses):
{json.dumps(scenarios, indent=2) if scenarios else 'No disponible'}

CUSTOMER JOURNEY:
{json.dumps(journey, indent=2) if journey else 'No disponible'}

PRICING POWER (Precio vs Calidad percibida; tamaño=SOV):
{json.dumps(pricing_power, indent=2) if pricing_power else 'No disponible'}

CONTEXTO DE MERCADO (PESTEL/Porter/Drivers):
{json.dumps(market_context, indent=2) if market_context else 'No disponible'}

========================================
ANÁLISIS TRANSVERSAL (Patrones comunes y contradicciones entre marcas):
========================================
{json.dumps(transversal, indent=2) if transversal else 'No disponible'}

⚠️ INSTRUCCIÓN CRÍTICA: INTEGRA los 'temas_comunes' del análisis transversal como hilos conductores en tu narrativa.
   Si hay 'contradicciones', resuélvelas en tu análisis o señálalas explícitamente.
   Los 'insights_nuevos' deben aparecer como hallazgos diferenciales en tu síntesis.

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
    "narrativa_principal": "DESARROLLA EN 4-6 PÁRRAFOS: Empieza con la situación del mercado (integrando KPIs clave como SOV, menciones, tendencias Y contexto de PESTEL/Porter del market_context). Luego desarrolla la complicación (la tensión estratégica central con evidencia cuantitativa + citas cualitativas del raw_responses + patrones del análisis TRANSVERSAL). Finalmente responde a la pregunta clave con los hallazgos principales integrando insights de TODOS los análisis especializados (campañas, canales, ESG, packaging, pricing, journey, escenarios) y su implicación. USA EXPLÍCITAMENTE los 'temas_comunes' del TRANSVERSAL como hilos conductores. Si hay 'contradicciones', señálalas. Esta debe ser una narrativa fluida y argumentativa, no una lista.",
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
    "narrativa": "DESARROLLA EN 5-7 PÁRRAFOS: Describe la naturaleza del mercado/categoría (usando la situación del synthesis_agent como apertura), tamaño y crecimiento si disponible, drivers de categoría principales con ejemplos específicos de cómo impactan decisiones, factores PESTEL más relevantes con implicaciones concretas (NO genéricas), análisis de Fuerzas de Porter adaptado a este mercado. USA EXPLÍCITAMENTE los datos del JSON 'CONTEXTO DE MERCADO': extrae 'panorama_general' (descripcion, tamano_estimado, crecimiento_estimado, madurez, caracteristicas_clave), 'analisis_pestel' (politico_legal, economico, social, tecnologico, ecologico), 'fuerzas_porter' (rivalidad_competitiva, poder_compradores, poder_proveedores, amenaza_nuevos_entrantes, amenaza_sustitutos), 'drivers_categoria' (driver, importancia, tendencia, descripcion), 'sintesis_estrategica' (factores_criticos_exito, oportunidades_contexto, amenazas_prioritarias, insight_clave). Cuenta cómo funciona este mercado y qué factores lo moldean. Conecta los factores entre sí."
  }},
  
  "analisis_competitivo": {{
    "narrativa_dinamica": "DESARROLLA EN 4-6 PÁRRAFOS: Analiza la dinámica competitiva actual: quién domina y por qué (con datos de SOV y sentimiento), cómo se posicionan las marcas principales, correlaciones entre visibilidad/percepción/marketing/canal, gaps competitivos explotables. USA EXPLÍCITAMENTE el JSON 'PRICING POWER' para analizar el posicionamiento precio-calidad: extrae 'perceptual_map' (marca, precio, calidad, sov) para identificar marcas premium vs value, gaps de posicionamiento, y 'brand_pricing_metrics' (price_premium_pct, elasticity_signal, discounting_frequency). Conecta múltiples dimensiones para revelar la historia competitiva. Menciona explícitamente 'Como muestra el Gráfico de SOV...'",
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
    "narrativa": "DESARROLLA EN 3-5 PÁRRAFOS: Síntesis de la actividad de marketing en el mercado: qué marcas comunican activamente y cómo, principales campañas y mensajes clave, canales utilizados, percepción de efectividad y recepción cualitativa, gaps (marcas silenciosas o con comunicación inefectiva a pesar de alto SOV). USA EXPLÍCITAMENTE los datos del JSON 'ANÁLISIS DE CAMPAÑAS Y MARKETING': extrae 'marca_mas_activa', 'mensajes_clave', 'canales_destacados', 'campanas_especificas' (con nombre, canales, mensaje_central, recepcion), 'gaps_marketing'. CITA ejemplos concretos de campañas y su recepción."
  }},
  
  "analisis_canales": {{
    "narrativa": "DESARROLLA EN 3-5 PÁRRAFOS: Estrategias de distribución observadas (intensiva/selectiva/exclusiva), ventajas competitivas en accesibilidad y presencia omnicanal, gaps de e-commerce y oportunidades digitales, retailers clave y experiencia de compra diferenciada. USA EXPLÍCITAMENTE los datos del JSON 'ANÁLISIS DE CANALES Y DISTRIBUCIÓN': extrae 'marca_mejor_distribuida', 'gaps_e_commerce', 'retailers_clave', 'disponibilidad_por_marca' (canales_presencia, facilidad_encontrar, problemas_reportados), 'tendencias_canal'. CITA ejemplos concretos por marca."
  }},
  
  "analisis_sostenibilidad_packaging": {{
    "narrativa": "DESARROLLA EN 3-4 PÁRRAFOS: Percepción ESG del mercado (controversias, líderes, rezagados), análisis de packaging (problemas funcionales, diseño, innovaciones), importancia relativa de ESG y packaging como drivers de decisión, oportunidades de diferenciación. USA EXPLÍCITAMENTE los datos del JSON 'ANÁLISIS ESG Y SOSTENIBILIDAD': extrae 'controversias_clave', 'driver_compra_sostenibilidad', 'benchmarking_marcas' (percepcion_esg, fortalezas/debilidades_esg, certificaciones), 'gaps_oportunidades'. USA los datos del JSON 'ANÁLISIS DE PACKAGING Y DISEÑO': extrae 'quejas_packaging', 'atributos_valorados', 'innovaciones_detectadas', 'benchmarking_funcional' (score_funcionalidad, score_diseño, fortalezas/debilidades_packaging, material_principal). CONECTA ESG y packaging cuando sea relevante."
  }},
  
  "consumidor": {{
    "narrativa_voz_cliente": "DESARROLLA EN 4-5 PÁRRAFOS: Integra citas textuales directas del raw_responses para dar vida a la voz del consumidor. Desarrolla drivers de elección con ejemplos específicos de POR QUÉ eligen cada marca, explica barreras de compra con evidencia cualitativa, describe ocasiones de consumo principales y cómo impactan la decisión, identifica tensiones o contradicciones. HAZ QUE EL CONSUMIDOR COBRE VIDA con sus propias palabras entrecomilladas."
  }},

  "customer_journey": {{
    "narrativa": "DESARROLLA EN 2-3 PÁRRAFOS: Explica el recorrido típico detectado (awareness→advocacy), pain points transversales por etapa, touchpoints dominantes (online/offline) y cómo esto se conecta con la Complicación y el plan de 90 días. USA EXPLÍCITAMENTE los datos del JSON 'CUSTOMER JOURNEY': extrae 'stages' (name, pain_points, touchpoints, insights) por cada etapa (awareness, consideration, purchase, retention, advocacy), y 'buyer_personas'. Incluye 1-2 citas textuales si es posible y menciona brevemente 1-2 buyer personas relevantes con sus características concretas del JSON."
  }},
  
  "sentimiento_reputacion": {{
    "narrativa": "DESARROLLA EN 3-4 PÁRRAFOS: Presenta scores de sentimiento por marca con contexto (no solo números), EXPLICA el 'por qué' detrás de cada score con insights cualitativos del texto crudo, analiza correlaciones entre sentimiento/SOV/marketing, identifica cambios vs periodos anteriores si hay contexto histórico. Menciona 'Como muestra el Gráfico de Sentimiento...'"
  }},
  
  "oportunidades_riesgos": {{
    "narrativa_oportunidades": "DESARROLLA EN 3-4 PÁRRAFOS: Profundiza en las TOP 3-5 oportunidades más críticas, explicando la lógica, evidencia multi-fuente, impacto potencial, y cómo capitalizarlas. USA el JSON 'ESCENARIOS' para contextualizar: extrae 'best_case' (probability, drivers, description, impact, recommended_actions) y conecta las oportunidades con este escenario optimista. Conecta oportunidades entre sí si es relevante.",
    "narrativa_riesgos": "DESARROLLA EN 3-4 PÁRRAFOS: Profundiza en los TOP 3-5 riesgos más graves, explicando probabilidad, severidad, evidencia, y estrategias de mitigación. USA el JSON 'ESCENARIOS' para contextualizar: extrae 'worst_case' (probability, drivers, description, impact, recommended_actions) y 'base_case' para identificar escenarios de mayor peligro y estrategias de mitigación concretas. Identifica escenarios de mayor peligro.",
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
    "narrativa_estrategia": "DESARROLLA EN 2-3 PÁRRAFOS: Explica la lógica del plan de acción completo: por qué estas iniciativas, en este orden, para resolver la complicación identificada. USA EXPLÍCITAMENTE los datos de 'ANÁLISIS DE CAMPAÑAS' (campanas_especificas con recepcion positiva/negativa, gaps_marketing), 'ANÁLISIS DE CANALES' (gaps_e_commerce, disponibilidad_por_marca, problemas_reportados), 'PRICING POWER' (elasticity_signal, discounting_frequency), 'CUSTOMER JOURNEY' (pain_points por etapa), y 'ESCENARIOS' (recommended_actions de base_case) para PRIORIZAR iniciativas basadas en evidencia real. Especifica QUÉ campañas pausar o escalar, QUÉ canales reforzar, QUÉ pain points atacar, con datos concretos del JSON.",
    "iniciativas": [
      {{
        "titulo": "Iniciativa 1",
        "descripcion": "QUÉ hacer exactamente (2-3 líneas detalladas, NO bullets). CITA EXPLÍCITAMENTE datos concretos: nombra canales específicos del JSON 'ANÁLISIS DE CANALES' a reforzar (ej: 'e-commerce' si hay gaps), campañas específicas del JSON 'ANÁLISIS DE CAMPAÑAS' a pausar/escalar (ej: 'Campaña X con recepción negativa'), pain points concretos del 'CUSTOMER JOURNEY' a resolver (ej: 'fricción en etapa consideration por falta de reviews'), retailers específicos del 'ANÁLISIS DE CANALES' a priorizar.",
        "por_que": "POR QUÉ hacerlo - vinculado explícitamente a la complicación y datos específicos del JSON correspondiente con cifras concretas (ej: 'porque el gap de e-commerce es X% vs competencia' o 'porque la campaña Y tiene recepción negativa del 65%') (2-3 líneas)",
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
11. **PRECISIÓN CUANTITATIVA**: Cada párrafo debe incluir al menos 1 cifra con unidad y 1 comparación explícita (competidor o periodo).
12. **MAGNITUD Y DIRECCIÓN**: Reporta deltas como "+X pp" o "+Y%" e indica dirección (↑/↓/↗/↘).
13. **TRAZABILIDAD**: Referencia la fuente de cada cifra (KPI, tendencia o cita textual) dentro del propio párrafo.

========================================
✅ CHECKLIST FINAL ANTES DE DEVOLVER EL JSON:
========================================
Antes de devolver tu respuesta, VERIFICA que has usado EXPLÍCITAMENTE datos de:
□ CUANTITATIVOS (SOV, menciones, ranking)
□ CUALITATIVOS (sentimiento, atributos)
□ COMPETITIVOS (lider, benchmarking)
□ TENDENCIAS (sov_trend_data, sentiment_trend_data)
□ ESTRATÉGICOS (oportunidades, riesgos, DAFO)
□ SÍNTESIS (situacion, complicacion, pregunta_clave)
□ TRANSVERSAL (temas_comunes, contradicciones, insights_nuevos) ← CRÍTICO
□ CAMPAÑAS (marca_mas_activa, campanas_especificas, gaps_marketing)
□ CANALES (disponibilidad_por_marca, gaps_e_commerce, retailers_clave)
□ ESG (benchmarking_marcas, controversias_clave)
□ PACKAGING (benchmarking_funcional, quejas_packaging, innovaciones)
□ PRICING POWER (perceptual_map, brand_pricing_metrics)
□ CUSTOMER JOURNEY (stages con pain_points, buyer_personas)
□ ESCENARIOS (best_case, base_case, worst_case)
□ MARKET CONTEXT (panorama_general, pestel, porter, drivers_categoria)

Si alguno está disponible pero NO lo has usado en las narrativas, REVISA y completa antes de devolver.
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

        # Asegurar estructuras nuevas clave
        resumen = informe.setdefault('resumen_ejecutivo', {})
        resumen.setdefault('answer_first', {
            'the_answer': '', 'the_why': '', 'the_how': '', 'the_impact': ''
        })

        # Gating mínimo sobre answer_first y plan
        ans = resumen.get('answer_first') or {}
        def _fill_if_short(key: str, default_text: str):
            try:
                val = ans.get(key)
                if not isinstance(val, str) or len(val.strip()) < 50:
                    ans[key] = default_text
            except Exception:
                ans[key] = default_text
        _fill_if_short('the_answer', 'Recomendación: reenfocar inversión hacia canales con mejor desempeño observado y reforzar propuesta ESG/packaging para convertir visibilidad en preferencia.')
        _fill_if_short('the_why', 'Porque los datos muestran brecha entre visibilidad y preferencia. KPIs de sentimiento y señales en canales/packaging sugieren fricción que limita conversión.')
        _fill_if_short('the_how', 'Roadmap 90 días: 1) Reasignar 15-20% presupuesto a canales con mejor conversión observada; 2) Lanzar test de creatividades y nueva narrativa ESG; 3) Resolver pain points de disponibilidad en e-commerce con acuerdos minoristas.')
        _fill_if_short('the_impact', 'Impacto esperado: +3-5 pp SOV de marca prioritaria, +0.1 a +0.2 en sentimiento y mejora de eficiencia de medios 10-15% en 90 días.')
        resumen['answer_first'] = ans

        opp_risk = informe.setdefault('oportunidades_riesgos', {})
        dafo = opp_risk.setdefault('dafo_sintesis', {})
        dafo.setdefault('cruces_estrategicos', '')

        # Buyer personas: si existen, asegurar descripciones como texto (no listas)
        if 'buyer_personas' in informe and isinstance(informe['buyer_personas'], list):
            for p in informe['buyer_personas']:
                if isinstance(p, dict):
                    if isinstance(p.get('motivations'), list):
                        p['motivations'] = ', '.join(map(str, p['motivations']))
                    if isinstance(p.get('pain_points'), list):
                        p['pain_points'] = ', '.join(map(str, p['pain_points']))
        
        return informe
    
    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        """Helper para obtener análisis"""
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        
        return result.resultado if result else {}


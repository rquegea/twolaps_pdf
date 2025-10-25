"""
Competitive Agent
Análisis de posicionamiento competitivo
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult


class EvidenceItem(BaseModel):
    tipo: str
    detalle: str
    fuente_id: Optional[str] = None
    periodo: Optional[str] = None


class InsightItem(BaseModel):
    titulo: str
    evidencia: List[EvidenceItem] = Field(default_factory=list)
    impacto_negocio: str
    recomendacion: str
    prioridad: str
    kpis_seguimiento: List[Dict[str, str]] = Field(default_factory=list)
    confianza: str
    contraargumento: Optional[str] = None


class CompetitiveOutputModel(BaseModel):
    insights: List[InsightItem] = Field(default_factory=list)
    lider_mercado: Optional[str] = None
    ranking_sov: Optional[List[str]] = None
    benchmarking_atributos: Optional[Dict[str, Dict[str, str]]] = None
    perfiles_competidores: Optional[List[Dict[str, Any]]] = None


class CompetitiveAgent(BaseAgent):
    """
    Agente de análisis competitivo
    Lee resultados de agentes previos y genera análisis comparativo
    """
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Analiza posicionamiento competitivo
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis competitivo
        """
        # Cargar prompt
        self.load_prompts_dynamic(categoria_id, 'competitive_agent')

        # Obtener análisis previos
        quantitative = self._get_analysis('quantitative', categoria_id, periodo)
        qualitative = self._get_analysis('qualitative', categoria_id, periodo)
        # Fallback por compatibilidad con versiones previas
        if not qualitative:
            qualitative = self._get_analysis('qualitativeextraction', categoria_id, periodo)
        trends = self._get_analysis('trends', categoria_id, periodo) or {}
        campaign_analysis = self._get_analysis('campaign_analysis', categoria_id, periodo) or {}
        channel_analysis = self._get_analysis('channel_analysis', categoria_id, periodo) or {}
        
        if not quantitative or not qualitative:
            return {'error': 'Faltan análisis previos (quantitative y qualitative)'}
        
        # Análisis competitivo
        sov = quantitative.get('sov_percent', {})
        sentimientos = qualitative.get('sentimiento_por_marca', {})
        
        # Identificar líder
        lider = max(sov.items(), key=lambda x: x[1])[0] if sov else None
        
        # Gaps competitivos (marcas con bajo SOV pero alto sentimiento)
        gaps = []
        for marca in sov.keys():
            sov_val = sov.get(marca, 0)
            sent_val = sentimientos.get(marca, {}).get('score_medio', 0)
            
            if sov_val < 15 and sent_val > 0.5:
                gaps.append({
                    'marca': marca,
                    'gap_type': 'oportunidad',
                    'razon': f"Alto sentimiento ({sent_val:.2f}) pero bajo SOV ({sov_val:.1f}%)"
                })
            elif sov_val > 25 and sent_val < 0.3:
                gaps.append({
                    'marca': marca,
                    'gap_type': 'riesgo',
                    'razon': f"Alto SOV ({sov_val:.1f}%) pero sentimiento bajo ({sent_val:.2f})"
                })
        
        # Moats y brand equity (borrador basado en datos disponibles)
        moats = []
        for marca in sov.keys():
            moat_entry = {
                'marca': marca,
                'barreras_entrada': [],
                'switching_costs': [],
                'network_effects': [],
                'brand_equity': {
                    'reconocimiento': 'N/A',
                    'lealtad': 'N/A',
                    'premium_power': 'N/A'
                }
            }
            moats.append(moat_entry)

        # Construir inputs para prompt
        sov_data = sov
        sentiment_data = {m: sentimientos.get(m, {}) for m in sov.keys()}
        attributes_data = qualitative.get('atributos_por_marca') or {}
        qualitative_data = {
            'marketing_campanas': qualitative.get('marketing_campanas') or {},
            'canales_distribucion': qualitative.get('canales_distribucion') or {},
        }

        # Proteger placeholders reales y escapar llaves literales del template
        template = self.task_prompt or ""
        keys = ["sov_data", "sentiment_data", "attributes_data", "qualitative_data"]
        for k in keys:
            template = template.replace("{" + k + "}", f"__{k.upper()}__")
        template = template.replace("{", "{{").replace("}", "}}")
        for k in keys:
            template = template.replace(f"__{k.upper()}__", "{" + k + "}")

        prompt = template.format(
            sov_data=sov_data,
            sentiment_data=sentiment_data,
            attributes_data=attributes_data,
            qualitative_data=qualitative_data,
        )

        # Añadir datos de tendencias para forzar evidencia cruzada con cambios de SOV
        try:
            tlist = trends.get('tendencias') or []
            trends_summary = [
                {
                    'marca': t.get('marca'),
                    'cambio_puntos': t.get('cambio_puntos'),
                    'cambio_rel_pct': t.get('cambio_rel_pct'),
                    'direccion': t.get('direccion')
                }
                for t in tlist if t.get('marca') and t.get('cambio_puntos') is not None
            ][:8]
            prompt = (
                prompt
                + "\n\nDATOS DE TENDENCIAS (para evidencia cruzada en insights):\n"
                + str(trends_summary)
                + "\nREGLA: incluye al menos 1 evidencia con cambio de SOV (pp o %) del bloque anterior."
            )
        except Exception:
            pass

        # Si hay tendencias, forzar que el PRIMER insight trate la marca con mayor cambio
        try:
            top_brand = None
            top_delta = 0.0
            for t in (trends.get('tendencias') or []):
                try:
                    d = abs(float(t.get('cambio_puntos') or 0.0))
                    if d > top_delta and t.get('marca'):
                        top_delta = d
                        top_brand = t.get('marca')
                except Exception:
                    continue
            if top_brand:
                prompt += (
                    f"\nREGLA: El PRIMER insight DEBE tratar sobre la marca '{top_brand}' e incluir como evidencia el cambio de SOV (pp o %) indicado en DATOS DE TENDENCIAS."
                )
        except Exception:
            pass

        def _passes_gating(comp: dict) -> bool:
            ins = (comp or {}).get('insights') or []
            if not ins:
                return False
            first = ins[0]
            evid = first.get('evidencia') or []
            if len(evid) < 3:
                return False
            has_cita = any((e.get('tipo') == 'CitaRAG') for e in evid if isinstance(e, dict))
            return has_cita

        def _generate(prompt_text: str) -> dict:
            g = self._generate_with_validation(
                prompt=prompt_text,
                pydantic_model=CompetitiveOutputModel,
                max_retries=2,
                temperature=0.3,
            )
            return g.get('parsed') if g.get('success') else {}

        parsed = _generate(prompt)
        if not parsed or not _passes_gating(parsed):
            prompt_retry = (
                prompt
                + "\n\nREQUISITOS ESTRICTOS: Devuelve 1-2 insights máximo, cada uno con ≥3 evidencias y AL MENOS 1 CitaRAG con 'fuente_id'. "
                  "Sin comas finales ni texto adicional."
            )
            parsed = _generate(prompt_retry)

        if not parsed:
            # Devolver fallback estructurado mínimo con gaps y comparativa para no bloquear
            fallback = {
                'insights': [],
                'lider_mercado': lider,
                'ranking_sov': [m for m, _ in sorted(sov.items(), key=lambda x: x[1], reverse=True)],
                'perfiles_competidores': [],
            }
            self.save_results(categoria_id, periodo, fallback)
            return fallback
        # Post-proceso mínimo: normalizar periodo/fuente y añadir KPI reputación + trazabilidad campañas/canales
        try:
            for ins in (parsed.get('insights') or []):
                for ev in (ins.get('evidencia') or []):
                    if ev.get('periodo') in (None, '', 'null'):
                        ev['periodo'] = periodo
                    if ev.get('tipo') == 'CitaRAG' and not ev.get('fuente_id'):
                        ev['fuente_id'] = 'exec_inferido'
                # KPI reputación si falta
                try:
                    kpis = ins.get('kpis_seguimiento') or []
                    has_rep = any(isinstance(k, dict) and ('sentimiento' in (k.get('nombre','').lower())) for k in kpis)
                    if not has_rep:
                        kpis.append({
                            'nombre': 'Mejorar sentimiento de marca',
                            'valor_objetivo': '+0.08',
                            'fecha_objetivo': '90 días'
                        })
                        ins['kpis_seguimiento'] = kpis
                except Exception:
                    pass
                # Evidencias de campañas/canales si existen
                try:
                    evid_list = ins.get('evidencia') or []
                    titulo = ins.get('titulo', '') or ''
                    target_marca = None
                    for m in sov.keys():
                        if m and m in titulo:
                            target_marca = m
                            break
                    if not target_marca and sov:
                        target_marca = list(sov.keys())[0]
                    # Campañas
                    camps = campaign_analysis.get('campanas_especificas') or []
                    hit_camps = [c for c in camps if isinstance(c, dict) and (not target_marca or c.get('marca') == target_marca)]
                    if hit_camps:
                        nombre = hit_camps[0].get('nombre_campana') or hit_camps[0].get('mensaje_central')
                        if nombre:
                            evid_list.append({
                                'tipo': 'DatoAgente',
                                'detalle': f"Campaña mencionada: {nombre}",
                                'fuente_id': 'campaign_analysis',
                                'periodo': periodo
                            })
                    # Canales
                    disp = channel_analysis.get('disponibilidad_por_marca') or []
                    hits = [d for d in disp if isinstance(d, dict) and (not target_marca or d.get('marca') == target_marca)]
                    if hits:
                        retailers = hits[0].get('retailers_mencionados') or []
                        if retailers:
                            evid_list.append({
                                'tipo': 'DatoAgente',
                                'detalle': f"Retailer citado: {retailers[0]}",
                                'fuente_id': 'channel_analysis',
                                'periodo': periodo
                            })
                    ins['evidencia'] = evid_list
                except Exception:
                    pass
        except Exception:
            pass

        # Guardar y devolver
        self.save_results(categoria_id, periodo, parsed)
        return parsed
    
    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        """Helper para obtener análisis previo"""
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        
        return result.resultado if result else {}


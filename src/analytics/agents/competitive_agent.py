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

        gen = self._generate_with_validation(
            prompt=prompt,
            pydantic_model=CompetitiveOutputModel,
            max_retries=2,
            temperature=0.3,
        )

        if not gen.get('success') or not gen.get('parsed'):
            # Devolver fallback estructurado mínimo con gaps y comparativa para no bloquear
            fallback = {
                'insights': [],
                'lider_mercado': lider,
                'ranking_sov': [m for m, _ in sorted(sov.items(), key=lambda x: x[1], reverse=True)],
                'perfiles_competidores': [],
            }
            self.save_results(categoria_id, periodo, fallback)
            return fallback

        parsed = gen['parsed']
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


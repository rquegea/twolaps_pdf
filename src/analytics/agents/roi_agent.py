"""
ROI Agent
Calcula ROI/ROAS/CPA y payback por campaña/canal con modo de datos parciales
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json
from src.analytics.agents.base_agent import BaseAgent


class ROIAgent(BaseAgent):
    """
    Agente de ROI de marketing. No llama a LLM: calcula métricas determinísticas a partir de inputs.
    Input esperado (persistido por otros agentes o configuración interna del periodo):
    {
      "por_canal": [
        {"canal": "Search", "gasto": 10000, "revenue_atr": 30000, "conversions": 500, "margen_pct": 0.4},
        ...
      ],
      "supuestos": ["..."]
    }
    """

    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.agent_name = 'roi'

    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        # Obtener inputs desde archivo JSON (data/roi/{mercado}/{categoria}/{periodo}.json) o AnalysisResult('roi_inputs')
        inputs = self._load_inputs_from_file(categoria_id, periodo)
        if not inputs:
            inputs = self._get_analysis('roi_inputs', categoria_id, periodo) or {}
        por_canal = inputs.get('por_canal', []) if isinstance(inputs, dict) else []
        supuestos = inputs.get('supuestos', []) if isinstance(inputs, dict) else []

        # Fallback: ejemplo si no hay inputs (Search/Social/Display)
        if not por_canal:
            por_canal = [
                {"canal": "Search", "gasto": 15000, "revenue_atr": 45000, "conversions": 900, "margen_pct": 0.45},
                {"canal": "Social", "gasto": 10000, "revenue_atr": 22000, "conversions": 400, "margen_pct": 0.40},
                {"canal": "Display", "gasto": 8000, "revenue_atr": 12000, "conversions": 150, "margen_pct": 0.35}
            ]
            supuestos = supuestos or [
                "Ejemplo de integración ROI con datos sintéticos",
                "Margen bruto asumido por canal basado en benchmark interno",
                "Atribución directa simplificada (last-touch)"
            ]

        resultados_canal = []
        total_gasto = 0.0
        total_revenue = 0.0
        total_conversions = 0
        total_margen = 0.0

        for item in por_canal:
            gasto = float(item.get('gasto', 0) or 0)
            revenue_atr = float(item.get('revenue_atr', 0) or 0)
            conversions = int(item.get('conversions', 0) or 0)
            margen_pct = float(item.get('margen_pct', 0.35) or 0.35)

            roas = (revenue_atr / gasto) if gasto > 0 else 0.0
            beneficio = revenue_atr * margen_pct - gasto
            roi_pct = (beneficio / gasto * 100) if gasto > 0 else 0.0
            cpa = (gasto / conversions) if conversions > 0 else None
            payback_meses = self._estimate_payback_months(gasto, revenue_atr * margen_pct)

            resultados_canal.append({
                'canal': item.get('canal', 'N/A'),
                'gasto': gasto,
                'revenue_atr': revenue_atr,
                'roas': roas,
                'roi_pct': roi_pct,
                'cpa': cpa,
                'payback_meses': payback_meses
            })

            total_gasto += gasto
            total_revenue += revenue_atr
            total_conversions += conversions
            total_margen += revenue_atr * margen_pct

        roas_total = (total_revenue / total_gasto) if total_gasto > 0 else 0.0
        beneficio_total = total_margen - total_gasto
        roi_total_pct = (beneficio_total / total_gasto * 100) if total_gasto > 0 else 0.0
        cpa_total = (total_gasto / total_conversions) if total_conversions > 0 else None
        payback_total_meses = self._estimate_payback_months(total_gasto, total_margen)

        resumen = {
            'roas': roas_total,
            'roi_pct': roi_total_pct,
            'cpa': cpa_total,
            'payback_meses': payback_total_meses
        }

        resultado = {
            'resumen': resumen,
            'por_canal': resultados_canal,
            'supuestos': supuestos,
            'periodo': periodo,
            'categoria_id': categoria_id
        }

        self.save_results(categoria_id, periodo, resultado)
        return resultado

    def _estimate_payback_months(self, inversion: float, beneficio_mensual: float) -> int:
        if beneficio_mensual <= 0:
            return -1
        meses = inversion / max(beneficio_mensual, 1e-6)
        return int(round(meses))

    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        from src.database.models import AnalysisResult
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        return result.resultado if result else {}

    def _load_inputs_from_file(self, categoria_id: int, periodo: str) -> Optional[Dict[str, Any]]:
        """
        Intenta leer inputs de ROI desde un archivo JSON en data/roi/{mercado}/{categoria}/{periodo}.json
        Valida un esquema mínimo y normaliza tipos.
        """
        try:
            # Resolver mercado y categoría
            from src.database.models import Categoria, Mercado
            categoria = self.session.query(Categoria).get(categoria_id)
            if not categoria:
                return None
            mercado = self.session.query(Mercado).get(categoria.mercado_id)
            market_name = (mercado.nombre or 'FMCG').replace(' ', '_')
            cat_name = (categoria.nombre or 'Categoria').replace(' ', '_')
            roi_path = Path(f"data/roi/{market_name}/{cat_name}/{periodo}.json")
            if not roi_path.exists():
                return None
            with roi_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
            # Validar esquema mínimo
            por_canal = data.get('por_canal')
            if not isinstance(por_canal, list):
                return None
            normalized = []
            for item in por_canal:
                if not isinstance(item, dict):
                    continue
                canal = str(item.get('canal', 'N/A'))
                gasto = float(item.get('gasto', 0) or 0)
                revenue_atr = float(item.get('revenue_atr', 0) or 0)
                conversions = int(item.get('conversions', 0) or 0)
                margen_pct = float(item.get('margen_pct', 0.35) or 0.35)
                if gasto < 0 or revenue_atr < 0 or conversions < 0 or not (0 <= margen_pct <= 1):
                    # Valores inválidos: descartar entrada
                    continue
                normalized.append({
                    'canal': canal,
                    'gasto': gasto,
                    'revenue_atr': revenue_atr,
                    'conversions': conversions,
                    'margen_pct': margen_pct
                })
            if not normalized:
                return None
            return {
                'por_canal': normalized,
                'supuestos': data.get('supuestos', []) if isinstance(data.get('supuestos'), list) else []
            }
        except Exception:
            return None



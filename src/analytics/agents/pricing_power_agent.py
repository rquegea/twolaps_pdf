"""
Pricing Power Agent
Analiza poder de pricing y produce datos para mapa perceptual
"""

import json
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.analytics.rag_manager import RAGManager
from src.query_executor.api_clients import OpenAIClient
from src.analytics.schemas import PricingPowerOutput


class PricingPowerAgent(BaseAgent):
    """
    Agente de pricing: price premium, elasticidad percibida y mapa perceptual
    """

    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = OpenAIClient()
        self.rag_manager = RAGManager(session)
        self.agent_name = 'pricing_power'
        self.top_k_fragments = 10

    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        self.load_prompts_dynamic(categoria_id, default_key='pricing_power_agent')

        analytical_query = (
            "precio, caro, barato, promociones, descuento, premium, relación calidad-precio,"
            " calidad percibida, posicionamiento precio, mapa perceptual"
        )

        fragments = self.rag_manager.search_query_executions_for_question(
            categoria_id=categoria_id,
            periodo=periodo,
            analytical_question=analytical_query,
            top_k=self.top_k_fragments
        )

        context = '\n\n---\n\n'.join([f["texto"] for f in fragments]) if fragments else ""
        prompt = self.task_prompt.format(contexto=context)

        gen = self._generate_with_validation(
            prompt=prompt,
            pydantic_model=PricingPowerOutput,
            max_retries=1,
            temperature=0.2,
            max_tokens=2500,
            provider="openai"
        )
        parsed = gen.get('parsed') if gen.get('success') else {"brand_pricing_metrics": [], "perceptual_map": []}

        # Si no hay puntos del mapa, intentar inferir algunos proxies desde quantitative/sentiment
        try:
            if not parsed.get('perceptual_map'):
                quant = self._get_analysis('quantitative', categoria_id, periodo)
                # Fallback: si no hay SOV en el rango, usar periodo previo (mensual)
                if not (quant or {}).get('sov_percent'):
                    prev_month = self._get_previous_periodo_generic(periodo)
                    if prev_month:
                        quant_prev = self._get_analysis('quantitative', categoria_id, prev_month)
                        if quant_prev:
                            quant = quant_prev
                sent = self._get_analysis('qualitative', categoria_id, periodo) or self._get_analysis('qualitativeextraction', categoria_id, periodo)
                sov = (quant or {}).get('sov_percent') or {}
                sent_by = (sent or {}).get('sentimiento_por_marca') or {}
                items = []
                for marca, share in list(sorted(sov.items(), key=lambda x: x[1], reverse=True))[:5]:
                    s = sent_by.get(marca) or {}
                    score = 0.0
                    try:
                        score = float(s.get('score_medio') or s.get('score') or 0.0)
                    except Exception:
                        score = 0.0
                    precio = min(max(50 + (share - (sum(sov.values())/max(len(sov),1))) * 0.8, 0), 100)
                    calidad = min(max(50 + score * 40, 0), 100)
                    items.append({"marca": marca, "precio": float(precio), "calidad": float(calidad), "sov": float(share)})
                if items:
                    parsed['perceptual_map'] = items
        except Exception:
            pass

        parsed['periodo'] = periodo
        parsed['categoria_id'] = categoria_id
        parsed['metadata'] = {"fragments_analyzed": len(fragments) if fragments else 0}

        self.save_results(categoria_id, periodo, parsed)
        return parsed

    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """Helper para obtener análisis previo"""
        try:
            from src.database.models import AnalysisResult
            result = self.session.query(AnalysisResult).filter_by(
                categoria_id=categoria_id,
                periodo=periodo,
                agente=agent_name
            ).first()
            return result.resultado if result else {}
        except Exception:
            return {}

    def _clean_json_response(self, response_text: str) -> str:
        response_text = response_text.strip()
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip().startswith('```'):
                    in_json = not in_json
                    continue
                if in_json:
                    json_lines.append(line)
            response_text = '\n'.join(json_lines).strip()
        if response_text and not response_text.startswith('{'):
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                response_text = response_text[start:end+1]
        return response_text



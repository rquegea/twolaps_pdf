"""
Customer Journey Agent
Genera customer journey map y buyer personas usando RAG
"""

import json
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.analytics.rag_manager import RAGManager
from src.query_executor.api_clients import OpenAIClient


class CustomerJourneyAgent(BaseAgent):
    """
    Agente de Customer Journey y Buyer Personas
    """

    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = OpenAIClient()
        self.rag_manager = RAGManager(session)
        self.agent_name = 'customer_journey'
        self.top_k_fragments = 12

    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        self.load_prompts_dynamic(categoria_id, default_key='customer_journey_agent')

        analytical_query = (
            "awareness, consideration, purchase, retention, advocacy, descubrimiento, evaluación, compra, repetición, recomendación,"
            " buyer journey, touchpoints, pain points, información previa a compra"
        )

        fragments = self.rag_manager.search_query_executions_for_question(
            categoria_id=categoria_id,
            periodo=periodo,
            analytical_question=analytical_query,
            top_k=self.top_k_fragments
        )

        context = '\n\n---\n\n'.join([f["texto"] for f in fragments]) if fragments else ""
        prompt = self.task_prompt.format(contexto=context)

        result = self.client.generate(prompt=prompt, temperature=0.3, max_tokens=3000, json_mode=True)
        response_text = self._clean_json_response(result.get('response_text', ''))
        try:
            parsed = json.loads(response_text)
        except Exception:
            parsed = {
                "stages": [],
                "buyer_personas": [],
                "metadata": {"fragments_analyzed": len(fragments) if fragments else 0}
            }

        parsed['periodo'] = periodo
        parsed['categoria_id'] = categoria_id
        meta = parsed.get('metadata', {})
        meta['fragments_analyzed'] = len(fragments) if fragments else 0
        parsed['metadata'] = meta

        self.save_results(categoria_id, periodo, parsed)
        return parsed

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



"""
Scenario Planning Agent
Genera escenarios best/base/worst con probabilidades y acciones
"""

import json
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.query_executor.api_clients import OpenAIClient
from src.analytics.schemas import EvidenceItem


class ScenarioPlanningAgent(BaseAgent):
    """
    Agente de planificación de escenarios (12-24 meses)
    """

    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = OpenAIClient()
        self.agent_name = 'scenario_planning'

    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        self.load_prompts_dynamic(categoria_id, default_key='scenario_planning_agent')

        # Inputs: usa strategic + trends como contexto si existen
        strategic = self._get_analysis('strategic', categoria_id, periodo)
        trends = self._get_analysis('trends', categoria_id, periodo)

        datos = {
            'strategic': strategic,
            'trends': trends
        }
        prompt = self.task_prompt.format(datos_estrategicos=json.dumps(datos))

        result = self.client.generate(prompt=prompt, temperature=0.3, max_tokens=2500, json_mode=True)
        response_text = self._clean_json_response(result.get('response_text', ''))
        try:
            parsed = json.loads(response_text)
        except Exception:
            parsed = {}

        # Gating: asegurar 3 escenarios con campos obligatorios
        defaults = {
            'probability': 0.33,
            'drivers': [],
            'description': '',
            'impact': '',
            'recommended_actions': []
        }
        for key in ['best_case', 'base_case', 'worst_case']:
            parsed[key] = {**defaults, **(parsed.get(key) or {})}

        parsed['periodo'] = periodo
        parsed['categoria_id'] = categoria_id
        self.save_results(categoria_id, periodo, parsed)
        return parsed

    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        from src.database.models import AnalysisResult
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        return result.resultado if result else {}

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



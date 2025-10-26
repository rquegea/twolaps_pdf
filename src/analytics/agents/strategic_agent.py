"""
Strategic Agent
Generación de oportunidades y riesgos estratégicos
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult
from src.query_executor.api_clients import OpenAIClient
from src.analytics.schemas import StrategicOutput


class StrategicAgent(BaseAgent):
    """
    Agente estratégico
    Genera oportunidades y riesgos basándose en análisis previos usando LLM
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = OpenAIClient()
        # Prompt se cargará dinámicamente
    
    def load_prompts(self):
        # Deprecated: usar load_prompts_dynamic
        pass
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Genera oportunidades y riesgos usando LLM con acceso a respuestas textuales
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con oportunidades y riesgos
        """
        # Cargar prompt por tipo de mercado
        self.load_prompts_dynamic(categoria_id, default_key='strategic_agent')

        # Leer análisis previos
        quantitative = self._get_analysis('quantitative', categoria_id, periodo)
        qualitative = self._get_analysis('qualitative', categoria_id, periodo)
        if not qualitative:
            qualitative = self._get_analysis('qualitativeextraction', categoria_id, periodo)
        competitive = self._get_analysis('competitive', categoria_id, periodo)
        trends = self._get_analysis('trends', categoria_id, periodo)
        # Datos adicionales FMCG usados por el prompt estratégico ampliado
        campaign = self._get_analysis('campaign_analysis', categoria_id, periodo)
        channel = self._get_analysis('channel_analysis', categoria_id, periodo)
        esg = self._get_analysis('esg_analysis', categoria_id, periodo)
        packaging = self._get_analysis('packaging_analysis', categoria_id, periodo)
        
        if not quantitative or not qualitative:
            return {'error': 'Faltan análisis previos'}
        
        # NUEVO: Obtener muestra estratificada de respuestas textuales (LIMITADA para evitar 429/TPM)
        raw_responses = self._get_stratified_sample(categoria_id, periodo, samples_per_group=1)
        # Limitar tamaño total del bloque de texto para reducir tokens
        if isinstance(raw_responses, str) and len(raw_responses) > 8000:
            raw_responses = raw_responses[:8000]
        
        # Construir inputs compactos para reducir tokens
        def _top_n_dict(d: Dict[str, Any], n: int = 10) -> Dict[str, Any]:
            if not isinstance(d, dict):
                return {}
            try:
                # Si son porcentajes por marca, ordenar por valor desc
                items = list(d.items())
                items.sort(key=lambda kv: (kv[1] if isinstance(kv[1], (int, float)) else 0), reverse=True)
                return {k: v for k, v in items[:n]}
            except Exception:
                return dict(list(d.items())[:n])

        def _trim_list(lst: Any, n: int = 5) -> Any:
            return (lst or [])[:n] if isinstance(lst, list) else []

        sov_compact = _top_n_dict(quantitative.get('sov_percent', {}), n=10)
        sentiment_compact = {}
        if isinstance(qualitative.get('sentimiento_por_marca'), dict):
            # Reducir a top 10 por score_medio si existe
            items = []
            for marca, data in qualitative['sentimiento_por_marca'].items():
                score = 0.0
                if isinstance(data, dict):
                    val = data.get('score_medio') or data.get('score')
                    try:
                        score = float(val)
                    except Exception:
                        score = 0.0
                items.append((marca, data, score))
            items.sort(key=lambda x: x[2], reverse=True)
            sentiment_compact = {m: d for m, d, _ in items[:10]}

        competitive_compact = {}
        if isinstance(competitive, dict):
            competitive_compact['lider_mercado'] = competitive.get('lider_mercado')
            if isinstance(competitive.get('insights'), list):
                competitive_compact['insights'] = _trim_list(competitive.get('insights'), n=3)

        trends_compact = _trim_list((trends or {}).get('tendencias', []), n=5)

        def _compact_agent_data(data: Any, insight_key: str = 'insights', n: int = 3) -> Dict[str, Any]:
            if not isinstance(data, dict):
                return {}
            compact = {}
            meta = data.get('metadata') or {}
            if meta:
                compact['metadata'] = meta
            if isinstance(data.get(insight_key), list):
                compact[insight_key] = _trim_list(data.get(insight_key), n)
            return compact or (data if len(json.dumps(data)) < 2000 else {})

        campaign_compact = _compact_agent_data(campaign, 'insights', 3)
        channel_compact = _compact_agent_data(channel, 'insights', 3)
        esg_compact = _compact_agent_data(esg, 'insights', 3)
        packaging_compact = _compact_agent_data(packaging, 'insights', 3)

        # Construir prompt con datos estructurados COMPACTOS y respuestas textuales
        prompt = self.task_prompt.format(
            sov_data=json.dumps(sov_compact, separators=(',', ':')),
            sentiment_data=json.dumps(sentiment_compact, separators=(',', ':')),
            competitive_data=json.dumps(competitive_compact, separators=(',', ':')),
            trends_data=json.dumps(trends_compact, separators=(',', ':')),
            raw_responses_sample=raw_responses,
            campaign_analysis_data=json.dumps(campaign_compact, separators=(',', ':')),
            channel_analysis_data=json.dumps(channel_compact, separators=(',', ':')),
            esg_analysis_data=json.dumps(esg_compact, separators=(',', ':')),
            packaging_analysis_data=json.dumps(packaging_compact, separators=(',', ':'))
        )
        
        # Llamar a LLM
        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.45,
                max_tokens=5000
            )

            # Limpiar y validar con Pydantic
            response_text = self._clean_json_response(result.get('response_text', ''))
            parsed_dict = {}
            try:
                parsed_obj = StrategicOutput.model_validate_json(response_text)  # type: ignore[attr-defined]
                parsed_dict = parsed_obj.model_dump()  # type: ignore[attr-defined]
            except Exception:
                try:
                    parsed_dict = json.loads(response_text)
                except Exception:
                    parsed_dict = {'oportunidades': [], 'riesgos': []}

            # Gating mínimo: ≥5 oportunidades y ≥5 riesgos, cada uno con algún texto
            opp = parsed_dict.get('oportunidades') or []
            rsk = parsed_dict.get('riesgos') or []
            if len(opp) < 5 or len(rsk) < 5:
                # Reforzar instrucción y reintentar de forma conservadora
                strict = (
                    prompt
                    + "\n\nREQUISITO ESTRICTO: Devuelve ≥5 oportunidades y ≥5 riesgos con descripciones y datos de soporte. SOLO JSON válido."
                )
                result2 = self.client.generate(prompt=strict, temperature=0.5, max_tokens=7000)
                response2 = self._clean_json_response(result2.get('response_text', ''))
                try:
                    parsed_obj2 = StrategicOutput.model_validate_json(response2)  # type: ignore[attr-defined]
                    parsed_dict = parsed_obj2.model_dump()  # type: ignore[attr-defined]
                except Exception:
                    try:
                        parsed_dict = json.loads(response2)
                    except Exception:
                        parsed_dict = parsed_dict  # mantener lo previo

            parsed_dict['periodo'] = periodo
            parsed_dict['categoria_id'] = categoria_id
            parsed_dict.setdefault('metadata', {})

            self.save_results(categoria_id, periodo, parsed_dict)
            return parsed_dict
            
        except Exception as e:
            self.logger.error(f"Error generando análisis estratégico: {e}", exc_info=True)
            return {'error': f'Error en análisis estratégico: {str(e)}'}

    def _clean_json_response(self, response_text: str) -> str:
        """
        Limpia la respuesta del LLM para extraer JSON válido, incluso si viene con markdown o texto.
        """
        if not isinstance(response_text, str):
            return '{}'
        txt = response_text.strip()
        # Extraer bloque entre ``` si existe
        if '```' in txt:
            lines = txt.split('\n')
            json_lines = []
            in_block = False
            for line in lines:
                striped = line.strip()
                if striped.startswith('```'):
                    if not in_block:
                        in_block = True
                        continue
                    else:
                        break
                if in_block:
                    json_lines.append(line)
            txt = '\n'.join(json_lines).strip()
        # Buscar primer '{' y último '}'
        start = txt.find('{')
        end = txt.rfind('}')
        if start != -1 and end != -1 and end > start:
            return txt[start:end+1]
        # No hay JSON detectable
        return '{}'
    
    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        """Helper para obtener análisis"""
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        
        return result.resultado if result else {}


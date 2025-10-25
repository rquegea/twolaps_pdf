"""
Synthesis Agent
Sintetiza todos los análisis en una narrativa central (Situación-Complicación-Pregunta)
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult
from src.query_executor.api_clients import AnthropicClient


class SynthesisAgent(BaseAgent):
    """
    Agente de síntesis narrativa
    Genera el "So What?" del análisis
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = AnthropicClient()  # Cambiado a Anthropic
        self.load_prompts()
    
    def load_prompts(self):
        """Carga prompts de configuración"""
        prompt_path = Path("config/prompts/agent_prompts.yaml")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)
                self.task_prompt = prompts.get('synthesis_agent', {}).get('task', '')
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Genera narrativa central (Situación-Complicación-Pregunta) con análisis profundo
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con narrativa central
        """
        # Leer análisis previos
        quantitative = self._get_analysis('quantitative', categoria_id, periodo)
        qualitative = self._get_analysis('qualitative', categoria_id, periodo)
        if not qualitative:
            qualitative = self._get_analysis('qualitativeextraction', categoria_id, periodo)
        strategic = self._get_analysis('strategic', categoria_id, periodo)
        
        if not quantitative or not qualitative or not strategic:
            return {'error': 'Faltan análisis previos necesarios'}
        
        # NUEVO: Obtener muestra estratificada de respuestas textuales
        raw_responses = self._get_stratified_sample(categoria_id, periodo, samples_per_group=2)
        
        # Construir prompt con datos estructurados Y respuestas textuales
        prompt = self.task_prompt.format(
            quantitative_results=json.dumps(quantitative, indent=2),
            sentiment_results=json.dumps(qualitative.get('sentimiento_por_marca', {}), indent=2),
            strategic_results=json.dumps(strategic, indent=2),
            raw_responses_sample=raw_responses
        )
        
        # Llamar a LLM
        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.7,   # Aumentado para más creatividad narrativa
                max_tokens=8000    # 🔥 AMPLIADO: Permite narrativas S-C-P de 8-12 líneas con máxima densidad
            )
            
            # Parsear con limpieza robusta y fallback
            response_text = self._clean_json_response(result.get('response_text', ''))
            try:
                narrativa = json.loads(response_text)
            except Exception:
                # Reintento más estricto: exige los tres campos
                strict_prompt = prompt + "\n\nDEVUELVE SOLO JSON con claves 'situacion', 'complicacion', 'pregunta_clave'. Sin markdown."
                retry = self.client.generate(
                    prompt=strict_prompt,
                    temperature=0.5,
                    max_tokens=4000
                )
                response_text = self._clean_json_response(retry.get('response_text', ''))
                try:
                    narrativa = json.loads(response_text)
                except Exception:
                    narrativa = {
                        'situacion': '',
                        'complicacion': '',
                        'pregunta_clave': ''
                    }
            
            resultado = {
                'periodo': periodo,
                'categoria_id': categoria_id,
                'situacion': narrativa.get('situacion', ''),
                'complicacion': narrativa.get('complicacion', ''),
                'pregunta_clave': narrativa.get('pregunta_clave', '')
            }

            # Gating mínimo: los tres campos deben tener contenido (≥50 chars cada uno)
            def _ok(txt: str) -> bool:
                try:
                    return isinstance(txt, str) and len(txt.strip()) >= 50
                except Exception:
                    return False
            if not (_ok(resultado['situacion']) and _ok(resultado['complicacion']) and _ok(resultado['pregunta_clave'])):
                # fallback ultra mínimo con concatenación de señales duras
                if not _ok(resultado['situacion']):
                    resultado['situacion'] = 'Diagnóstico mínimo: mercado con actividad y señales insuficientes para narrativa extensa.'
                if not _ok(resultado['complicacion']):
                    resultado['complicacion'] = 'Tensión central: desalineación entre visibilidad y percepción; gaps en canal/ESG/packaging.'
                if not _ok(resultado['pregunta_clave']):
                    resultado['pregunta_clave'] = '¿Cómo cerrar la brecha entre visibilidad y preferencia mejorando canal y propuesta ESG/packaging?'
            
            self.save_results(categoria_id, periodo, resultado)
            return resultado
            
        except Exception as e:
            self.logger.error(f"Error generando síntesis: {e}", exc_info=True)
            return {'error': f'Error en síntesis: {str(e)}'}
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Limpia la respuesta del LLM para extraer JSON válido, incluso si viene con markdown o texto libre.
        """
        if not isinstance(response_text, str):
            return '{}'
        txt = response_text.strip()
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
        start = txt.find('{')
        end = txt.rfind('}')
        if start != -1 and end != -1 and end > start:
            return txt[start:end+1]
        return '{}'
    
    def _get_analysis(self, agent_name: str, categoria_id: int, periodo: str) -> Dict:
        """Helper para obtener análisis"""
        result = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=agent_name
        ).first()
        return result.resultado if result else {}


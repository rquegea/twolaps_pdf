"""
Transversal Agent
Sintetiza patrones transversales entre resultados de agentes para detectar temas comunes y contradicciones
"""

import json
from typing import Dict, Any
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import AnalysisResult
from src.query_executor.api_clients import OpenAIClient


class TransversalAgent(BaseAgent):
    """Agente transversal para síntesis de patrones e inconsistencias"""

    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = OpenAIClient()
        self.agent_name = 'transversal'

    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """Lee AnalysisResult de múltiples agentes y sintetiza patrones/contradicciones"""
        # Cargar prompt por mercado si definimos variantes en YAML (opcional, fallback a un prompt fijo)
        self.load_prompts_dynamic(categoria_id, default_key='transversal_agent')

        # Reunir resultados clave
        agent_keys = [
            'quantitative', 'qualitative', 'competitive', 'trends',
            'campaign_analysis', 'channel_analysis', 'esg_analysis', 'packaging_analysis',
            'strategic'
        ]
        resultados = {}
        for ak in agent_keys:
            row = self.session.query(AnalysisResult).filter_by(
                categoria_id=categoria_id,
                periodo=periodo,
                agente=ak
            ).first()
            resultados[ak] = row.resultado if row else {}

        # Construir prompt mínimo si no hay YAML específico
        if not self.task_prompt:
            self.task_prompt = (
                "Eres un agente de síntesis transversal. Con los datos de múltiples agentes, "
                "identifica: (1) temas comunes consistentes entre Sentimiento, Competencia y Tendencias; "
                "(2) contradicciones entre Cuantitativo y Cualitativo; (3) insights no capturados por otros agentes.\n\n"
                "Devuelve únicamente un JSON válido con esta estructura:\n"
                '{"temas_comunes": [], "contradicciones": [], "insights_nuevos": []}'
            )

        prompt = self.task_prompt.format(
            quantitative=json.dumps(resultados.get('quantitative', {}), indent=2),
            qualitative=json.dumps(resultados.get('qualitative', {}), indent=2),
            competitive=json.dumps(resultados.get('competitive', {}), indent=2),
            trends=json.dumps(resultados.get('trends', {}), indent=2),
            campaign=json.dumps(resultados.get('campaign_analysis', {}), indent=2),
            channel=json.dumps(resultados.get('channel_analysis', {}), indent=2),
            esg=json.dumps(resultados.get('esg_analysis', {}), indent=2),
            packaging=json.dumps(resultados.get('packaging_analysis', {}), indent=2),
            strategic=json.dumps(resultados.get('strategic', {}), indent=2)
        )

        # Estructura por defecto SIEMPRE disponible
        default_data = {
            'temas_comunes': [],
            'contradicciones': [],
            'insights_nuevos': []
        }
        
        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2500,
                json_mode=True
            )
            response_text = (result.get('response_text') or '').strip()
            
            if not response_text:
                self.logger.warning("Transversal agent: respuesta vacía del LLM")
                self.save_results(categoria_id, periodo, default_data)
                return default_data
            
            # Limpiar respuesta por si tiene markdown o texto extra
            response_text = self._clean_json_response(response_text)
            
            # Limpieza ULTRA agresiva de comillas escapadas
            response_text = response_text.replace('\\"', '"').replace('\\\\', '\\')
            
            # Parsear JSON con manejo multi-capa
            data = None
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as e1:
                self.logger.warning(f"Intento 1 falló: {e1}. Intentando limpieza adicional...")
                # Intento 2: Limpiar más agresivamente
                try:
                    # Remover posibles comillas extras al inicio/final
                    cleaned = response_text.strip('"').strip("'")
                    data = json.loads(cleaned)
                except json.JSONDecodeError as e2:
                    self.logger.warning(f"Intento 2 falló: {e2}. Usando estructura por defecto.")
                    self.logger.debug(f"Respuesta problemática: {response_text[:500]}")
                    data = default_data.copy()
            
            # Si data no es dict, usar default
            if not isinstance(data, dict):
                self.logger.warning(f"Respuesta no es un diccionario: {type(data)}. Usando estructura por defecto.")
                data = default_data.copy()
            else:
                # Limpiar claves mal formadas de forma ULTRA AGRESIVA
                cleaned_data = {}
                for key, value in data.items():
                    try:
                        # Convertir key a string y limpiar TODO
                        clean_key = str(key).strip()
                        
                        # Remover comillas de todo tipo
                        for quote_char in ['"', "'", '`']:
                            clean_key = clean_key.strip(quote_char)
                        
                        # Remover espacios y caracteres especiales
                        clean_key = clean_key.strip()
                        
                        # Normalizar a claves conocidas usando fuzzy matching
                        clean_key_lower = clean_key.lower().replace(' ', '_').replace('-', '_')
                        
                        if 'tema' in clean_key_lower and 'comun' in clean_key_lower:
                            clean_key = 'temas_comunes'
                        elif 'contradicc' in clean_key_lower:
                            clean_key = 'contradicciones'
                        elif 'insight' in clean_key_lower or 'nuevo' in clean_key_lower:
                            clean_key = 'insights_nuevos'
                        elif clean_key_lower in ['temas_comunes', 'contradicciones', 'insights_nuevos']:
                            # Ya está bien
                            pass
                        else:
                            # Clave desconocida, intentar mapear
                            self.logger.debug(f"Clave desconocida ignorada: {key}")
                            continue
                        
                        cleaned_data[clean_key] = value
                    except Exception as e:
                        self.logger.warning(f"Error procesando clave {key}: {e}")
                        continue
                
                data = cleaned_data
            
            # Asegurar que existen TODAS las claves esperadas
            for required_key in ['temas_comunes', 'contradicciones', 'insights_nuevos']:
                if required_key not in data:
                    data[required_key] = []
                # Asegurar que el valor es una lista
                if not isinstance(data[required_key], list):
                    self.logger.warning(f"Clave {required_key} no es lista, convirtiendo...")
                    try:
                        # Si es string, intentar parsear como JSON
                        if isinstance(data[required_key], str):
                            data[required_key] = json.loads(data[required_key])
                        # Si es otro tipo, envolver en lista
                        elif data[required_key] is not None:
                            data[required_key] = [data[required_key]]
                        else:
                            data[required_key] = []
                    except (json.JSONDecodeError, TypeError, ValueError):
                        data[required_key] = []
            
        except Exception as e:
            self.logger.error(f"Error CRÍTICO en transversal agent: {e}", exc_info=True)
            data = default_data.copy()

        self.save_results(categoria_id, periodo, data)
        return data
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Limpia la respuesta del LLM para extraer JSON válido
        
        Args:
            response_text: Respuesta del LLM
        
        Returns:
            JSON limpio como string
        """
        response_text = response_text.strip()
        
        # Si tiene bloques de markdown con ```, extraer el contenido
        if response_text.startswith('```'):
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
        
        # Si aún no es JSON válido, intentar extraer el primer bloque JSON
        if response_text and not response_text.startswith('{'):
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                response_text = response_text[start:end+1]
        
        return response_text.strip()



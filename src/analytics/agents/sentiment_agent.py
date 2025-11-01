"""
Sentiment Agent
Análisis de sentimiento usando LLM
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field, RootModel
from collections import defaultdict
from sqlalchemy import extract
from src.analytics.agents.base_agent import BaseAgent
from src.database.models import Query, QueryExecution, Marca
from src.query_executor.api_clients import OpenAIClient


class SentimentAgent(BaseAgent):
    """
    Agente de análisis de sentimiento
    Usa LLM para clasificar sentimiento por marca y atributo
    """
    
    def __init__(self, session, version: str = "1.0.0"):
        super().__init__(session, version)
        self.client = OpenAIClient()
        self.load_prompts()
    
    def load_prompts(self):
        """Carga prompts de configuración"""
        prompt_path = Path("config/prompts/agent_prompts.yaml")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)
                self.task_prompt = prompts.get('sentiment_agent', {}).get('task', '')
        else:
            self.task_prompt = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Prompt por defecto si no hay config"""
        return """
        Analiza el sentimiento sobre las marcas en el siguiente texto.
        
        MARCAS A ANALIZAR: {marcas}
        
        TEXTO: {texto}
        
        Devuelve JSON:
        {{
          "marca": {{
            "score": float (-1 a 1),
            "tono": "positivo|neutral|negativo",
            "atributos": {{"sabor": score, "precio": score, "calidad": score}},
            "quote": "fragmento relevante"
          }}
        }}
        """
    
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Ejecuta análisis de sentimiento
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
        
        Returns:
            Dict con análisis de sentimiento
        """
        # Ventana temporal dinámica
        start, end, _ = self._parse_periodo(periodo)
        
        # 1. Obtener marcas
        marcas = self.session.query(Marca).filter_by(
            categoria_id=categoria_id
        ).all()
        
        if not marcas:
            return {'error': 'No hay marcas configuradas'}
        
        marca_nombres = [m.nombre for m in marcas]
        
        # 2. Obtener ejecuciones
        executions = self.session.query(QueryExecution).join(
            Query
        ).filter(
            Query.categoria_id == categoria_id,
            QueryExecution.timestamp >= start,
            QueryExecution.timestamp < end
        ).all()
        
        if not executions:
            return {'error': 'No hay datos para analizar'}
        
        # 3. Analizar sentimiento por respuesta (muestra) con validación Pydantic
        class MarcaSentiment(BaseModel):
            score: float
            atributos: Dict[str, float] = Field(default_factory=dict)

        class SentimentOutput(RootModel[Dict[str, MarcaSentiment]]):
            pass

        sample_size = min(10, len(executions))
        sampled_executions = executions[:sample_size]

        sentiments_by_marca = defaultdict(list)
        atributos_by_marca = defaultdict(lambda: defaultdict(list))

        allowed_attrs = [
            'calidad', 'precio', 'innovacion', 'servicio', 'reputacion', 'disponibilidad', 'diseño'
        ]

        for execution in sampled_executions:
            texto_src = (execution.respuesta_texto or '')[:800]
            marcas_csv = ', '.join(marca_nombres)
            attrs_csv = ', '.join(allowed_attrs)
            prompt = (
                "Eres un analista de sentimiento. Dado el TEXTO, estima el sentimiento por marca.\n\n"
                f"MARCAS: {marcas_csv}\n"
                f"ATRIBUTOS_PERMITIDOS: {attrs_csv}\n\n"
                "FORMATO JSON ESTRICTO (sin texto extra):\n"
                "{\n  \"Marca X\": {\"score\": 0.12, \"atributos\": {\"precio\": 0.3}},\n"
                "  \"Marca Y\": {\"score\": -0.20, \"atributos\": {}}\n}\n\n"
                "Reglas:\n- score en [-1,1]\n- atributos sólo de ATRIBUTOS_PERMITIDOS con valores en [-1,1]\n"
                "- Si una marca no aparece, inclúyela igualmente con score 0 y atributos {}.\n\n"
                f"TEXTO:\n{texto_src}"
            )
            gen = self._generate_with_validation(
                prompt=prompt,
                pydantic_model=SentimentOutput,
                max_retries=2,
                temperature=0.3,
                max_tokens=900,
            )
            if not gen.get('success') or not gen.get('parsed'):
                continue
            parsed = gen['parsed']
            if hasattr(parsed, 'model_dump'):
                data = parsed.model_dump()
            elif isinstance(parsed, dict):
                data = parsed
            else:
                try:
                    data = json.loads(parsed) if isinstance(parsed, str) else {}
                except Exception:
                    data = {}
            for marca, ms in data.items():
                if marca in marca_nombres:
                    sentiments_by_marca[marca].append(float(ms.get('score', 0)))
                    for attr, score in (ms.get('atributos') or {}).items():
                        try:
                            atributos_by_marca[marca][attr].append(float(score))
                        except Exception:
                            pass
        
        # 4. Agregar sentimientos
        sentimiento_agregado = {}
        for marca in marca_nombres:
            scores = sentiments_by_marca.get(marca, [0])
            sentimiento_agregado[marca] = {
                'score_medio': sum(scores) / len(scores) if scores else 0,
                'menciones_analizadas': len(scores),
                'distribucion': {
                    'positivo': len([s for s in scores if s > 0.3]),
                    'neutral': len([s for s in scores if -0.3 <= s <= 0.3]),
                    'negativo': len([s for s in scores if s < -0.3])
                }
            }
        
        # 5. Agregar atributos
        atributos_agregados = {}
        for marca in marca_nombres:
            atributos_agregados[marca] = {}
            for attr, scores in atributos_by_marca.get(marca, {}).items():
                atributos_agregados[marca][attr] = sum(scores) / len(scores) if scores else 0
        
        # 6. Generar insights con Plantilla Obligatoria usando prompt desde config
        try:
            # Construir contexto compacto
            metricas_compact = {
                "por_marca": sentimiento_agregado,
                "atributos_por_marca": atributos_agregados,
            }
            import json as _json
            metricas_json = _json.dumps(metricas_compact, ensure_ascii=False, indent=2)
            citas_list = []
            for ex in sampled_executions[:8]:
                txt = (ex.respuesta_texto or "").replace("\n", " ")[:200]
                citas_list.append(f"- exec_{ex.id}: \"{txt}\"")
            citas_txt = "\n".join(citas_list)

            # Cargar prompt desde config (dinámico por tipo de mercado si se desea)
            self.load_prompts()
            prompt_insights = (self.task_prompt or "").format(
                marcas=', '.join(marca_nombres),
                periodo=periodo,
                metricas_json=metricas_json,
                citas=citas_txt
            )

            # Modelos Pydantic para insights
            from typing import List, Literal

            class Evidencia(BaseModel):
                tipo: Literal['KPI','CitaRAG','DatoAgente']
                detalle: str
                fuente_id: Optional[str] = None
                periodo: Optional[str] = None

            class KPIItem(BaseModel):
                nombre: str
                valor_objetivo: str
                fecha_objetivo: str

            class Insight(BaseModel):
                titulo: str
                evidencia: List[Evidencia]
                impacto_negocio: str
                recomendacion: str
                prioridad: Literal['alta','media','baja']
                kpis_seguimiento: List[KPIItem]
                confianza: Literal['alta','media','baja']
                contraargumento: Optional[str] = None

            class SentimentInsights(BaseModel):
                insights: List[Insight]

            def _passes_gating(insights: list) -> bool:
                if not insights:
                    return False
                first = insights[0]
                evid = first.get('evidencia') or []
                if len(evid) < 3:
                    return False
                has_cita = any((e.get('tipo') == 'CitaRAG') for e in evid if isinstance(e, dict))
                return has_cita

            def _generate_insights(runtime_prompt: str) -> list:
                gen = self._generate_with_validation(
                    prompt=runtime_prompt,
                    pydantic_model=SentimentInsights,
                    max_retries=2,
                    temperature=0.2,
                    max_tokens=2500,  # Aumentado de 900 para evitar truncamiento
                )
                obj = gen.get('parsed') or {}
                return (obj.get('insights') if isinstance(obj, dict) else []) or []

            insights_list = _generate_insights(prompt_insights)
            if not _passes_gating(insights_list):
                # Reforzar prompt para cumplir gating explícitamente
                prompt_insights_retry = (
                    prompt_insights
                    + "\n\nREQUISITOS ESTRICTOS: Devuelve 1-2 insights como máximo, cada uno con ≥3 evidencias y AL MENOS 1 CitaRAG con 'fuente_id'. "
                      "Sin comas finales ni texto adicional."
                )
                insights_list = _generate_insights(prompt_insights_retry)
        except Exception:
            insights_list = []

        # 7. Resultado
        resultado = {
            'periodo': periodo,
            'categoria_id': categoria_id,
            'sentimiento_global': sum(
                s['score_medio'] for s in sentimiento_agregado.values()
            ) / len(sentimiento_agregado) if sentimiento_agregado else 0,
            'por_marca': sentimiento_agregado,
            'sentimiento_por_marca': sentimiento_agregado,
            'atributos_por_marca': atributos_agregados,
            'insights': insights_list,
            'metadata': {
                'executions_analizadas': sample_size,
                'total_executions': len(executions),
                'metodo': 'llm_sampling+validated'
            }
        }
        
        # Guardar
        self.save_results(categoria_id, periodo, resultado)
        
        return resultado


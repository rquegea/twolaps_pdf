"""
Base Agent
Clase base abstracta para todos los agentes de análisis
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from typing import Optional, Type
from pydantic import BaseModel, ValidationError
from pathlib import Path
import yaml
from datetime import datetime
from collections import defaultdict
import random
from sqlalchemy.orm import Session
from src.database.models import AnalysisResult
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BaseAgent(ABC):
    """
    Clase base para agentes de análisis
    """
    
    def __init__(self, session: Session, version: str = "1.0.0"):
        """
        Initialize agent
        
        Args:
            session: Sesión de SQLAlchemy
            version: Versión del agente
        """
        self.session = session
        self.version = version
        self.agent_name = self.__class__.__name__.replace('Agent', '').lower()
        # Logger específico del agente
        # Usamos el nombre de la clase para separar logs por agente
        self.logger = setup_logger(self.__class__.__name__)
        # Atributos comunes para prompts por mercado
        self.tipo_mercado = None
        self.task_prompt = ""
        self.system_prompt = ""
        # Carga de system prompt común
        self._load_system_prompt()
    
    @abstractmethod
    def analyze(self, categoria_id: int, periodo: str) -> Dict[str, Any]:
        """
        Ejecuta el análisis
        
        Args:
            categoria_id: ID de la categoría
            periodo: Periodo en formato YYYY-MM
        
        Returns:
            Dict con resultados del análisis
        """
        pass
    
    def save_results(
        self,
        categoria_id: int,
        periodo: str,
        resultado: Dict[str, Any]
    ) -> int:
        """
        Guarda los resultados del análisis en la base de datos
        
        Args:
            categoria_id: ID de la categoría
            periodo: Periodo
            resultado: Dict con resultados
        
        Returns:
            ID del AnalysisResult creado
        """
        # Verificar si ya existe un análisis para este periodo/agente
        existing = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            periodo=periodo,
            agente=self.agent_name
        ).first()
        
        if existing:
            # Actualizar existente
            existing.resultado = resultado
            existing.timestamp = datetime.utcnow()
            existing.version_agente = self.version
            self.session.flush()
            analysis_id = existing.id
        else:
            # Crear nuevo
            analysis = AnalysisResult(
                categoria_id=categoria_id,
                periodo=periodo,
                agente=self.agent_name,
                resultado=resultado,
                timestamp=datetime.utcnow(),
                version_agente=self.version
            )
            self.session.add(analysis)
            self.session.flush()
            analysis_id = analysis.id
        
        self.session.commit()
        
        logger.info(
            "analysis_saved",
            agent=self.agent_name,
            categoria_id=categoria_id,
            periodo=periodo,
            analysis_id=analysis_id
        )
        
        return analysis_id

    # =============================
    # Prompt Loading Helpers
    # =============================
    def _load_system_prompt(self) -> None:
        """Carga prompt de sistema base si existe."""
        system_path = Path("config/prompts/system_prompts.yaml")
        if system_path.exists():
            with open(system_path, 'r', encoding='utf-8') as f:
                system = yaml.safe_load(f)
                self.system_prompt = system.get('base_consultant_role', '')

    def load_prompts_dynamic(self, categoria_id: int, default_key: str) -> None:
        """
        Carga task_prompt dinámicamente según tipo_mercado.
        - Obtiene tipo_mercado vía join Categoria->Mercado
        - Selecciona prompts[default_key][tipo] o prompts[default_key]['default'] o prompts[default_key]['task']
        """
        from src.database.models import Categoria, Mercado
        # Resolver tipo de mercado
        categoria = self.session.query(Categoria).get(categoria_id)
        if not categoria:
            self.logger.warning("Categoría no encontrada para carga de prompt", categoria_id=categoria_id)
            return
        mercado = self.session.query(Mercado).get(categoria.mercado_id)
        self.tipo_mercado = getattr(mercado, 'tipo_mercado', None) or 'FMCG'

        prompt_path = Path("config/prompts/agent_prompts.yaml")
        if not prompt_path.exists():
            self.logger.warning("Archivo de prompts no encontrado", path=str(prompt_path))
            return
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompts_yaml = yaml.safe_load(f) or {}

        agent_block = prompts_yaml.get(default_key, {})
        # Compatibilidad: si hay 'task' al nivel raíz
        if 'task' in agent_block and isinstance(agent_block.get('task'), str):
            base_task = agent_block.get('task', '')
        else:
            base_task = ''

        # Variantes por tipo
        # Estructura esperada:
        # key: { default: { task: "..." }, fmcg: { task: "..." }, digital_saas: { task: "..." } }
        # Normalizamos claves a lower para matching robusto
        variant_task = None
        normalized = {str(k).lower(): v for k, v in agent_block.items() if isinstance(v, dict)}
        tipo_key = (self.tipo_mercado or '').lower()
        if tipo_key in normalized:
            variant_task = normalized[tipo_key].get('task')
        if not variant_task and 'default' in normalized:
            variant_task = normalized['default'].get('task')

        self.task_prompt = variant_task or base_task or self.task_prompt
    
    def get_previous_analysis(
        self,
        categoria_id: int,
        periodo: str
    ) -> Dict[str, Any]:
        """
        Obtiene análisis previo del mismo agente (si existe)
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo actual
        
        Returns:
            Dict con resultados o None
        """
        # TODO: Implementar lógica para obtener periodo anterior
        previous = self.session.query(AnalysisResult).filter_by(
            categoria_id=categoria_id,
            agente=self.agent_name
        ).filter(
            AnalysisResult.periodo < periodo
        ).order_by(
            AnalysisResult.periodo.desc()
        ).first()
        
        if previous:
            return previous.resultado
        
        return None
    
    # =============================
    # Period Helpers (daily/weekly/monthly)
    # =============================
    def _parse_periodo(self, periodo: str):
        """
        Convierte un periodo en ventana [start, end) y devuelve la granularidad.
        Soporta:
          - YYYY-MM-DD  -> 'daily'
          - YYYY-Www    -> 'weekly' (ISO semana, lunes-domingo)
          - YYYY-MM     -> 'monthly'
        """
        import re
        from datetime import datetime, timedelta
        p = (periodo or "").strip()
        # Rango arbitrario: YYYY-MM-DD..YYYY-MM-DD
        if '..' in p:
            start_s, end_s = p.split('..', 1)
            start = datetime.strptime(start_s.strip(), '%Y-%m-%d')
            end = datetime.strptime(end_s.strip(), '%Y-%m-%d') + timedelta(days=1)  # fin exclusivo
            return start, end, 'range'

        if re.match(r'^\d{4}-\d{2}-\d{2}$', p):  # diario
            start = datetime.strptime(p, '%Y-%m-%d')
            end = start + timedelta(days=1)
            return start, end, 'daily'
        if re.match(r'^\d{4}-W\d{2}$', p):       # semanal ISO
            y, w = p.split('-W')
            start = datetime.fromisocalendar(int(y), int(w), 1)  # lunes
            end = start + timedelta(days=7)
            return start, end, 'weekly'
        if re.match(r'^\d{4}-\d{2}$', p):        # mensual
            start = datetime.strptime(p, '%Y-%m')
            y, m = start.year, start.month
            end = (datetime(y+1, 1, 1) if m == 12 else datetime(y, m+1, 1))
            return start, end, 'monthly'
        raise ValueError(f"Formato de periodo no soportado: {periodo}")

    def _get_last_periods_generic(self, periodo: str, n: int = 6):
        """Devuelve últimos n periodos según granularidad del periodo dado (incluye actual)."""
        from datetime import timedelta
        start, _, gran = self._parse_periodo(periodo)
        periods = []
        for i in range(n-1, -1, -1):
            if gran == 'daily':
                d = start - timedelta(days=i)
                periods.append(d.strftime('%Y-%m-%d'))
            elif gran == 'weekly':
                d = start - timedelta(weeks=i)
                iso = d.isocalendar()
                periods.append(f"{iso.year}-W{iso.week:02d}")
            else:  # monthly
                y, m = start.year, start.month - i
                while m <= 0:
                    y -= 1
                    m += 12
                periods.append(f"{y}-{m:02d}")
        return periods

    def _get_previous_periodo_generic(self, periodo: str) -> str:
        seq = self._get_last_periods_generic(periodo, n=2)
        return seq[0] if len(seq) == 2 else None
    
    def _get_stratified_sample(self, categoria_id: int, periodo: str, samples_per_group: int = 2) -> str:
        """
        Obtiene muestra estratificada de respuestas textuales.
        Agrupa por (query_id, proveedor_ia) y toma N respuestas de cada grupo
        para garantizar representatividad y eliminar sesgo.
        
        Args:
            categoria_id: ID de categoría
            periodo: Periodo (YYYY-MM)
            samples_per_group: Número de respuestas a tomar de cada grupo (default: 2)
        
        Returns:
            String formateado con las respuestas textuales estratificadas
        """
        from src.database.models import Query, QueryExecution
        start, end, _ = self._parse_periodo(periodo)
        
        # Obtener TODAS las ejecuciones con respuesta_texto en ventana [start, end)
        executions = self.session.query(QueryExecution).join(
            Query
        ).filter(
            Query.categoria_id == categoria_id,
            QueryExecution.respuesta_texto.isnot(None),
            QueryExecution.timestamp >= start,
            QueryExecution.timestamp < end
        ).all()
        
        if not executions:
            return "No hay respuestas textuales disponibles para este periodo."
        
        # Agrupar por (query_id, proveedor_ia) para estratificación
        groups = defaultdict(list)
        for execution in executions:
            key = (execution.query_id, execution.proveedor_ia)
            groups[key].append(execution)
        
        # Seleccionar muestra estratificada
        sampled = []
        for group_executions in groups.values():
            # Tomar N aleatorias de cada grupo (o todas si hay menos de N)
            sample_size = min(samples_per_group, len(group_executions))
            sampled.extend(random.sample(group_executions, sample_size))
        
        # Log información de la estratificación
        self.logger.info(
            f"Muestreo estratificado: {len(sampled)} respuestas de {len(groups)} grupos (total: {len(executions)})",
            categoria_id=categoria_id,
            periodo=periodo
        )
        
        # Formatear respuestas
        formatted = []
        for i, execution in enumerate(sampled, 1):
            texto_truncado = execution.respuesta_texto[:1000] if execution.respuesta_texto else ""
            formatted.append(
                f"--- RESPUESTA {i} ---\n"
                f"Query: {execution.query.pregunta if execution.query else 'N/A'}\n"
                f"Proveedor: {execution.proveedor_ia}\n"
                f"Contenido: {texto_truncado}\n"
            )
        
        return "\n".join(formatted)

    # =============================
    # LLM Generation + Validation
    # =============================
    def _generate_with_validation(
        self,
        prompt: str,
        pydantic_model: Type[BaseModel],
        max_retries: int = 2,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        provider: str = "openai",
        llm_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera texto con LLM y valida contra un modelo Pydantic. Devuelve dict con claves:
          - parsed: dict (si éxito)
          - raw_response: str
          - success: bool
          - error: str|None
        """
        try:
            # Carga perezosa para evitar dependencias circulares
            from src.query_executor.poller import get_client
        except Exception as e:
            self.logger.error("No se pudo cargar cliente de LLM", error=str(e))
            return {"parsed": None, "raw_response": "", "success": False, "error": str(e)}

        client = None
        try:
            client = get_client(provider)
            # Si se especifica un modelo concreto y el cliente lo soporta
            if llm_model and hasattr(client, "model"):
                client.model = llm_model
        except Exception as e:
            self.logger.error("No se pudo inicializar cliente LLM", error=str(e))
            return {"parsed": None, "raw_response": "", "success": False, "error": str(e)}

        augmented_prompt = prompt
        last_error: Optional[str] = None

        for attempt in range(max_retries + 1):
            try:
                result = client.execute_query(
                    question=augmented_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                raw_text = result.get("response_text", "") or ""
                # Saneado: eliminar fences de markdown si el proveedor los añade
                rt = raw_text.strip()
                if rt.startswith("```"):
                    # Quitar primera línea con ``` o ```json
                    first_nl = rt.find('\n')
                    if first_nl != -1:
                        rt = rt[first_nl+1:]
                    # Quitar cierre ``` al final
                    if rt.endswith("```"):
                        rt = rt[:-3]
                raw_text = rt.strip()

                # Validación con Pydantic (compatibilidad v1/v2)
                parsed_obj = None
                try:
                    # Pydantic v2
                    parsed_obj = pydantic_model.model_validate_json(raw_text)  # type: ignore[attr-defined]
                except AttributeError:
                    # Pydantic v1
                    parsed_obj = pydantic_model.parse_raw(raw_text)  # type: ignore[attr-defined]

                # Serializar a dict (v1/v2)
                try:
                    parsed_dict = parsed_obj.model_dump()  # type: ignore[attr-defined]
                except Exception:
                    parsed_dict = parsed_obj.dict()  # type: ignore[attr-defined]

                return {
                    "parsed": parsed_dict,
                    "raw_response": raw_text,
                    "success": True,
                    "error": None,
                }

            except (ValidationError, ValueError) as ve:
                last_error = str(ve)
                self.logger.warning(
                    "validation_failed",
                    attempt=attempt,
                    error=last_error
                )
                # Reintentar con instrucción de corrección de formato
                augmented_prompt = (
                    prompt
                    + "\n\nERROR: La respuesta anterior no cumplió el formato JSON esperado. "
                      "DEVUELVE ÚNICAMENTE UN JSON VÁLIDO que cumpla la estructura requerida, sin texto adicional."
                )
                continue
            except Exception as e:
                last_error = str(e)
                self.logger.error("error_llm_generate", error=last_error)
                break

        return {
            "parsed": None,
            "raw_response": "",
            "success": False,
            "error": last_error or "unknown_error",
        }


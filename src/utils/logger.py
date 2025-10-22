"""
Logging System
Sistema de logging estructurado para TwoLaps
"""

import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
import structlog


def setup_logger(name: str = None, level: str = None) -> structlog.BoundLogger:
    """
    Configura y retorna un logger estructurado
    
    Args:
        name: Nombre del logger (típicamente __name__)
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger configurado
    """
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    
    # Configurar logging estándar
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Handler para archivo con rotación
    file_handler = RotatingFileHandler(
        "logs/twolaps.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(getattr(logging, level.upper()))
    
    # Configurar structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if sys.stdout.isatty() else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    
    logger = structlog.get_logger(name if name else "twolaps")
    
    return logger


def log_query_execution(
    logger: structlog.BoundLogger,
    query_id: int,
    provider: str,
    model: str,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
    latency_ms: int
):
    """
    Log de ejecución de query con métricas
    """
    logger.info(
        "query_executed",
        query_id=query_id,
        provider=provider,
        model=model,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        cost_usd=cost_usd,
        latency_ms=latency_ms
    )


def log_agent_analysis(
    logger: structlog.BoundLogger,
    agent_name: str,
    categoria_id: int,
    periodo: str,
    execution_time_seconds: float,
    result_summary: dict = None
):
    """
    Log de análisis de agente
    """
    logger.info(
        "agent_analysis_completed",
        agent=agent_name,
        categoria_id=categoria_id,
        periodo=periodo,
        execution_time_seconds=execution_time_seconds,
        result_summary=result_summary or {}
    )


def log_report_generation(
    logger: structlog.BoundLogger,
    report_id: int,
    categoria_id: int,
    categoria_nombre: str,
    periodo: str,
    pdf_path: str,
    pdf_size_mb: float,
    generation_time_seconds: float,
    agents_executed: dict = None,
    charts_generated: int = 0,
    total_pages: int = None
):
    """
    Log detallado de generación de reporte
    """
    logger.info(
        "report_generated",
        report_id=report_id,
        categoria_id=categoria_id,
        categoria=categoria_nombre,
        periodo=periodo,
        pdf_path=pdf_path,
        pdf_size_mb=round(pdf_size_mb, 2),
        generation_time_seconds=round(generation_time_seconds, 2),
        agents_executed=agents_executed or {},
        charts_generated=charts_generated,
        total_pages=total_pages,
        status="success"
    )


def log_error(
    logger: structlog.BoundLogger,
    component: str,
    error: Exception,
    context: dict = None
):
    """
    Log de error con contexto
    """
    logger.error(
        "error_occurred",
        component=component,
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {},
        exc_info=True
    )


# Logger global por defecto
default_logger = setup_logger("twolaps")


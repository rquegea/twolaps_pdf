#!/usr/bin/env python3
"""
Genera únicamente las gráficas (PNG) a partir de análisis ya existentes en BD,
sin invocar LLMs ni crear PDFs.

Uso:
  python scripts/generate_charts_only.py -c "FMCG/Champagnes" -p "2025-10" [--out DIR]
"""

import argparse
import base64
from pathlib import Path
from typing import Dict, Any

from src.database.connection import get_session
from src.database.models import Mercado, Categoria, AnalysisResult
from src.reporting.chart_generator import generate_all_charts


def _get_analysis(session, categoria_id: int, periodo: str, agente: str) -> Dict[str, Any]:
    row = session.query(AnalysisResult).filter_by(
        categoria_id=categoria_id, periodo=periodo, agente=agente
    ).first()
    return row.resultado if row else {}


def _to_data_uri_bytes(data_uri: str) -> bytes:
    if not data_uri or "," not in data_uri:
        return b""
    try:
        return base64.b64decode(data_uri.split(",", 1)[1])
    except Exception:
        return b""


def main():
    parser = argparse.ArgumentParser(description="Generar solo gráficas desde análisis existentes")
    parser.add_argument("-c", "--category", required=True, help="Mercado/Categoría (ej: FMCG/Champagnes)")
    parser.add_argument("-p", "--period", required=True, help="Periodo YYYY-MM (ej: 2025-10)")
    parser.add_argument("--out", help="Directorio de salida (opcional)")
    args = parser.parse_args()

    try:
        market_name, cat_name = args.category.split("/", 1)
    except ValueError:
        raise SystemExit("Formato inválido de categoría. Usa: Mercado/Categoría")

    with get_session() as session:
        mercado = session.query(Mercado).filter_by(nombre=market_name).first()
        if not mercado:
            raise SystemExit(f"Mercado '{market_name}' no encontrado")

        categoria = session.query(Categoria).filter_by(mercado_id=mercado.id, nombre=cat_name).first()
        if not categoria:
            raise SystemExit(f"Categoría '{args.category}' no encontrada")

        periodo = args.period

        # Análisis existentes (NO llama a LLM)
        quantitative = _get_analysis(session, categoria.id, periodo, "quantitative")
        qualitative = _get_analysis(session, categoria.id, periodo, "qualitative") or 
                      _get_analysis(session, categoria.id, periodo, "qualitativeextraction")
        channel = _get_analysis(session, categoria.id, periodo, "channel_analysis")
        strategic = _get_analysis(session, categoria.id, periodo, "strategic")
        esg = _get_analysis(session, categoria.id, periodo, "esg_analysis")

        # Construir report_data mínimo para los generadores de gráficos
        report_data: Dict[str, Any] = {}

        # 1) Competencia → SOV
        sov = quantitative.get("sov_percent") or quantitative.get("sov") or {}
        report_data["competencia"] = {
            "sov_data": sov if isinstance(sov, dict) else {},
            "sov_trend_data": {},  # Completar si tienes histórico
        }

        # 2) Sentimiento
        sentiment_data: Dict[str, Dict[str, float]] = {}
        sentiment_scores: Dict[str, float] = {}
        spm = (qualitative or {}).get("sentimiento_por_marca", {})
        if isinstance(spm, dict):
            for marca, payload in spm.items():
                dist = (payload or {}).get("distribucion") or {}
                if isinstance(dist, dict) and dist:
                    sentiment_data[marca] = {
                        "positivo": dist.get("positivo", 0),
                        "neutral": dist.get("neutral", 0),
                        "negativo": dist.get("negativo", 0),
                    }
                score = (payload or {}).get("score_medio")
                if isinstance(score, (int, float)):
                    sentiment_scores[marca] = float(score)
        report_data["sentimiento_reputacion"] = {
            "sentiment_data": sentiment_data,
            "sentiment_scores": sentiment_scores,
            "sentiment_trend_data": {},  # Completar si hay histórico
        }

        # 3) Atributos → radar
        report_data["atributos"] = {
            "por_marca": (qualitative or {}).get("atributos_por_marca", {})
        }

        # 4) Canales → barras agrupadas
        report_data["analisis_canales"] = {
            "presencia_por_marca": (channel or {}).get("presencia_por_marca", {})
        }

        # 5) Oportunidades/Riesgos → matrices
        report_data["oportunidades_riesgos"] = {
            "oportunidades": (strategic or {}).get("oportunidades", [])[:10],
            "riesgos": (strategic or {}).get("riesgos", [])[:10],
        }

        # 6) ESG → scatter (si hay scores por marca)
        esg_scores = {}
        if isinstance((esg or {}).get("scores_esg"), dict):
            esg_scores = esg["scores_esg"]
        report_data["analisis_sostenibilidad_packaging"] = {"scores_esg": esg_scores}

        # Generar gráficos (data URIs base64)
        charts = generate_all_charts(report_data)

        # Guardar PNGs
        out_dir = Path(args.out or f"data/reports/charts/{market_name}_{cat_name}_{periodo}")
        out_dir.mkdir(parents=True, exist_ok=True)

        saved = []
        for name, data_uri in (charts or {}).items():
            if not data_uri:
                continue
            png_bytes = _to_data_uri_bytes(data_uri)
            if not png_bytes:
                continue
            out_path = out_dir / f"{name}.png"
            with open(out_path, "wb") as f:
                f.write(png_bytes)
            saved.append(str(out_path))

        print(f"✅ Gráficos generados: {len(saved)}")
        for p in saved:
            print(f" - {p}")


if __name__ == "__main__":
    main()




#!/usr/bin/env python3
"""
Genera únicamente las gráficas (PNG) a partir de análisis ya existentes en BD,

Uso:
  python scripts/generate_charts_only.py -c "FMCG/Champagnes" -p "2025-10" [--out DIR]
"""

import sys
import os
import argparse
# Fix: Añadir la carpeta raíz del proyecto a sys.path para resolver 'src'
# Esto permite importar módulos como src.database.connection
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from typing import Dict, Any
import base64

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
        # Nota: La condición de fallo en la función original puede ser redundante, 
        # pero se mantiene la lógica de extracción de base64.
        if "," not in data_uri:
             return b""
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
        # Fix de sintaxis para la continuación de línea (usando paréntesis)
        qualitative = (
            _get_analysis(session, categoria.id, periodo, "qualitative") or 
            _get_analysis(session, categoria.id, periodo, "qualitativeextraction")
        )
        channel = _get_analysis(session, categoria.id, periodo, "channel_analysis")
        strategic = _get_analysis(session, categoria.id, periodo, "strategic")
        esg = _get_analysis(session, categoria.id, periodo, "esg_analysis")

        # Construir report_data mínimo para los generadores de gráficos
        report_data: Dict[str, Any] = {}

        # 1) Competencia → SOV (barras horizontales + pie + tendencia)
        sov = quantitative.get("sov_percent") or quantitative.get("sov") or {}
        
        # Construir trend data con un solo punto (funciona igual)
        sov_trend_data = {}
        if isinstance(sov, dict):
            for marca, valor in sov.items():
                sov_trend_data[marca] = [{"periodo": periodo, "sov": valor}]
        
        report_data["competencia"] = {
            "sov_data": sov if isinstance(sov, dict) else {},
            "sov_trend_data": sov_trend_data,
            "sov_waterfall": [],  # Opcional: agregar si tienes datos históricos
        }

        # 2) Sentimiento (barras apiladas + tendencia + scores)
        sentiment_data: Dict[str, Dict[str, float]] = {}
        sentiment_scores: Dict[str, float] = {}
        sentiment_trend_data: Dict[str, Any] = {}
        
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
                    # Construir trend data con un solo punto
                    sentiment_trend_data[marca] = [{"periodo": periodo, "score": float(score)}]
        
        report_data["sentimiento_reputacion"] = {
            "sentiment_data": sentiment_data,
            "sentiment_scores": sentiment_scores,
            "sentiment_trend_data": sentiment_trend_data,
        }

        # 3) Atributos → radar chart
        report_data["atributos"] = {
            "por_marca": (qualitative or {}).get("atributos_por_marca", {})
        }

        # 4) Canales → barras agrupadas
        report_data["analisis_canales"] = {
            "presencia_por_marca": (channel or {}).get("presencia_por_marca", {})
        }

        # 5) Oportunidades/Riesgos → matrices 2x2
        oportunidades_raw = (strategic or {}).get("oportunidades", [])
        riesgos_raw = (strategic or {}).get("riesgos", [])
        
        # Normalizar oportunidades a formato de dict si son strings
        oportunidades = []
        if isinstance(oportunidades_raw, list):
            for i, opp in enumerate(oportunidades_raw[:10]):
                if isinstance(opp, dict):
                    oportunidades.append(opp)
                elif isinstance(opp, str):
                    oportunidades.append({
                        "titulo": opp,
                        "impacto": "medio",
                        "esfuerzo": "medio"
                    })
        
        # Normalizar riesgos a formato de dict si son strings
        riesgos = []
        if isinstance(riesgos_raw, list):
            for i, risk in enumerate(riesgos_raw[:10]):
                if isinstance(risk, dict):
                    riesgos.append(risk)
                elif isinstance(risk, str):
                    riesgos.append({
                        "titulo": risk,
                        "probabilidad": "media",
                        "severidad": "media"
                    })
        
        report_data["oportunidades_riesgos"] = {
            "oportunidades": oportunidades,
            "riesgos": riesgos,
        }

        # 6) ESG → scatter plot (SOV vs ESG Score, tamaño=sentimiento)
        esg_scores = {}
        if isinstance((esg or {}).get("scores_esg"), dict):
            esg_scores = esg["scores_esg"]
        report_data["analisis_sostenibilidad_packaging"] = {"scores_esg": esg_scores}
        
        # 7) Plan de 90 días → timeline (Gantt)
        iniciativas_raw = (strategic or {}).get("plan_90_dias", {}).get("iniciativas", [])
        iniciativas = []
        if isinstance(iniciativas_raw, list):
            for i, init in enumerate(iniciativas_raw[:8]):
                if isinstance(init, dict):
                    iniciativas.append(init)
                elif isinstance(init, str):
                    # Asignar timeline progresivo
                    timeline = ["0-30 días", "30-60 días", "60-90 días"][i % 3]
                    iniciativas.append({
                        "titulo": init,
                        "timeline": timeline,
                        "prioridad": "media"
                    })
        
        report_data["plan_90_dias"] = {"iniciativas": iniciativas}
        
        # 8) Mapa perceptual (Precio vs Calidad, tamaño=SOV)
        # Construir datos sintéticos si no existen
        perceptual_brands = []
        if isinstance(sov, dict):
            for i, (marca, sov_val) in enumerate(list(sov.items())[:8]):
                # Valores sintéticos para demo (idealmente deberían venir de análisis)
                perceptual_brands.append({
                    "marca": marca,
                    "precio": 40 + (i * 8),  # Valores entre 40-100
                    "calidad": 50 + (i * 7),  # Valores entre 50-100
                    "sov": sov_val
                })
        
        report_data["pricing_power"] = {
            "perceptual_map": perceptual_brands
        }
        
        # 9) BCG Matrix (Market Share vs Growth Rate)
        # Derivar de SOV actual (growth = 0 si no hay histórico)
        bcg_metrics = {}
        if isinstance(sov, dict):
            for marca, share in sov.items():
                bcg_metrics[marca] = {
                    "market_share": float(share),
                    "growth_rate": 0.0,  # Sin histórico = 0% growth
                    "size": float(share)
                }
        
        report_data["bcg_metrics"] = bcg_metrics

        # Generar gráficos (data URIs base64)
        print(f"\n🎨 Generando gráficos para {market_name}/{cat_name} - {periodo}...")
        charts = generate_all_charts(report_data)

        # Guardar PNGs
        out_dir = Path(args.out or f"data/reports/charts/{market_name}_{cat_name}_{periodo}")
        out_dir.mkdir(parents=True, exist_ok=True)

        # Diccionario con nombres legibles de gráficos
        chart_names = {
            "sov_chart": "SOV - Barras Horizontales",
            "sov_pie_chart": "SOV - Gráfico de Pastel",
            "sov_trend_chart": "SOV - Evolución Temporal",
            "sentiment_chart": "Sentimiento - Barras Apiladas",
            "sentiment_trend_chart": "Sentimiento - Evolución Temporal",
            "opportunity_matrix": "Matriz de Oportunidades (Impacto vs Esfuerzo)",
            "risk_matrix": "Matriz de Riesgos (Probabilidad vs Severidad)",
            "attribute_radar": "Radar de Atributos por Marca",
            "channel_penetration": "Penetración por Canal",
            "esg_leadership": "Liderazgo ESG (SOV vs Score ESG)",
            "timeline_chart": "Timeline Plan 90 Días (Gantt)",
            "perceptual_map": "Mapa Perceptual (Precio vs Calidad)",
            "waterfall_chart": "Waterfall de Cambios en SOV",
            "bcg_matrix": "Matriz BCG (Share vs Growth)",
        }

        saved = []
        skipped = []
        
        for name, data_uri in (charts or {}).items():
            if not data_uri:
                skipped.append(name)
                continue
            png_bytes = _to_data_uri_bytes(data_uri)
            if not png_bytes:
                skipped.append(name)
                continue
            out_path = out_dir / f"{name}.png"
            with open(out_path, "wb") as f:
                f.write(png_bytes)
            saved.append((name, str(out_path)))

        # Resumen
        print(f"\n✅ Gráficos generados exitosamente: {len(saved)}/{len(chart_names)}")
        print(f"📁 Directorio: {out_dir}\n")
        
        if saved:
            print("📊 Gráficos creados:")
            for name, path in saved:
                display_name = chart_names.get(name, name)
                print(f"   ✓ {display_name}")
                print(f"     {path}")
        
        if skipped:
            print(f"\n⚠️  Gráficos omitidos (sin datos): {len(skipped)}")
            for name in skipped:
                display_name = chart_names.get(name, name)
                print(f"   - {display_name}")


if __name__ == "__main__":
    main()
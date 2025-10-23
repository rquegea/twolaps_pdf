#!/usr/bin/env python3
"""
Diagnóstico de datos guardados en BD para FMCG/Champagnes (periodo YYYY-MM).

Uso:
  python scripts/diagnostico_champagnes.py 2025-10
"""

import sys
import os
from typing import Any, Dict

# Añadir raíz del proyecto al path para poder importar 'src'
sys.path.insert(0, os.path.abspath('.'))

from src.database.connection import get_session
from src.database.models import Mercado, Categoria, AnalysisResult


def main():
    periodo = sys.argv[1] if len(sys.argv) > 1 else '2025-10'

    with get_session() as session:
        mercado = session.query(Mercado).filter_by(nombre='FMCG').first()
        if not mercado:
            print("✗ Mercado 'FMCG' no encontrado")
            return

        categoria = session.query(Categoria).filter_by(mercado_id=mercado.id, nombre='Champagnes').first()
        if not categoria:
            print("✗ Categoría 'Champagnes' no encontrada en FMCG")
            return

        print(f"✓ Categoría: FMCG/Champagnes (ID {categoria.id})")
        print(f"Periodo: {periodo}\n")

        analisis = session.query(AnalysisResult).filter_by(categoria_id=categoria.id, periodo=periodo).all()
        if not analisis:
            print("✗ No hay AnalysisResult para ese periodo")
            return

        # Índices rápidos por agente
        by_agent: Dict[str, Dict[str, Any]] = {}
        for a in analisis:
            by_agent[a.agente] = a.resultado or {}

        # Quantitative (SOV)
        q = by_agent.get('quantitative', {})
        sov = q.get('sov_percent') or q.get('sov') or {}
        print("[quantitative]")
        print(f"  - SOV marcas: {len(sov) if isinstance(sov, dict) else 0}")

        # Qualitative
        qual = by_agent.get('qualitative') or by_agent.get('qualitativeextraction') or {}
        spm = (qual or {}).get('sentimiento_por_marca', {})
        print("[qualitative]")
        print(f"  - Sentimiento por marca: {len(spm) if isinstance(spm, dict) else 0}")
        atributos = (qual or {}).get('atributos_por_marca', {})
        print(f"  - Atributos por marca: {len(atributos) if isinstance(atributos, dict) else 0}")

        # Canales
        ch = by_agent.get('channel_analysis', {})
        ppm = ch.get('presencia_por_marca')
        print("[channel_analysis]")
        print(f"  - presencia_por_marca: {'✓' if isinstance(ppm, dict) and len(ppm)>0 else '✗'}")

        # Strategic
        st = by_agent.get('strategic', {})
        print("[strategic]")
        ops = st.get('oportunidades', [])
        rsk = st.get('riesgos', [])
        plan = (st.get('plan_90_dias') or {}).get('iniciativas', []) if isinstance(st.get('plan_90_dias'), dict) else []

        def tipo_item(lst):
            if not lst:
                return '—'
            t = type(lst[0]).__name__
            if isinstance(lst[0], dict):
                return f"dict keys={list(lst[0].keys())}"
            return t

        print(f"  - Oportunidades: {len(ops)} (tipo: {tipo_item(ops)})")
        print(f"  - Riesgos: {len(rsk)} (tipo: {tipo_item(rsk)})")
        print(f"  - Plan 90 días, iniciativas: {len(plan)} (tipo: {tipo_item(plan)})")

        # ESG
        esg = by_agent.get('esg_analysis', {})
        print("[esg_analysis]")
        scores = esg.get('scores_esg')
        print(f"  - scores_esg: {'✓' if isinstance(scores, dict) and len(scores)>0 else '✗'}")


if __name__ == '__main__':
    main()



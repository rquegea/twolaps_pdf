"""
Competitor Discovery
Detección automática de posibles competidores/marcas en textos de respuestas.
"""

from __future__ import annotations

import json
import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from src.database.models import Marca, BrandCandidate, QueryExecution, Categoria
from src.query_executor.api_clients import OpenAIClient
from src.utils.logger import setup_logger


logger = setup_logger(__name__)


BRAND_NAME_REGEX = re.compile(r"\b([A-Z][A-Za-z0-9&'\-]+(?:\s+[A-Z][A-Za-z0-9&'\-]+){0,3})\b")


class LLMCompetitorDetector:
    """
    Detector basado en LLM con heurísticas de respaldo.
    """

    def __init__(self, session: Session):
        self.session = session
        self.client = OpenAIClient()

    def discover_from_text(self, categoria_id: int, texto: str) -> List[Dict[str, Any]]:
        """
        Retorna una lista de candidatos con estructura:
        {"nombre": str, "aliases": [..], "confianza": float}
        """
        if not texto:
            return []

        # Prompt compacto para extracción
        prompt = f"""
Identifica nombres de marcas/operadores del mercado FMCG en el texto.
Devuelve SOLO JSON con esta estructura estricta:
{{"candidatos": [{{"nombre": "...", "aliases": ["..."], "confianza": 0.0}}]}}

TEXTO:
{texto[:2000]}
"""

        candidates: List[Dict[str, Any]] = []

        try:
            res = self.client.generate(prompt=prompt, temperature=0.2, max_tokens=500)
            data = json.loads(res["response_text"]) if res.get("response_text") else {}
            for item in data.get("candidatos", []):
                nombre = str(item.get("nombre", "")).strip()
                if not nombre:
                    continue
                aliases = [a.strip() for a in item.get("aliases", []) if isinstance(a, str) and a.strip()]
                confianza = float(item.get("confianza", 0.5))
                candidates.append({"nombre": nombre, "aliases": aliases, "confianza": confianza})
        except Exception:
            # Fallback heurístico si el LLM falla
            candidates.extend(self._heuristic_extract(texto))

        # Filtrar existentes
        return self._filter_existing_brands(categoria_id, candidates)

    def _heuristic_extract(self, texto: str) -> List[Dict[str, Any]]:
        """Heurística simple basada en capitalización y longitud."""
        raw = set()
        for match in BRAND_NAME_REGEX.findall(texto or ""):
            name = match.strip()
            if len(name) < 3 or len(name) > 40:
                continue
            if any(tok.islower() for tok in name.split()):
                continue
            raw.add(name)
        return [{"nombre": n, "aliases": [n], "confianza": 0.4} for n in sorted(raw)]

    def _filter_existing_brands(self, categoria_id: int, candidates: List[Dict[str, Any]]):
        existing = self.session.query(Marca).filter_by(categoria_id=categoria_id).all()
        existing_names = set(m.nombre.lower() for m in existing)
        existing_aliases = set(a.lower() for m in existing for a in (m.aliases or []))

        filtered = []
        for c in candidates:
            name_l = c["nombre"].lower()
            if name_l in existing_names or name_l in existing_aliases:
                continue
            filtered.append(c)
        return filtered


def upsert_brand_candidates(
    session: Session,
    categoria_id: int,
    execution: QueryExecution,
    detected: List[Dict[str, Any]]
) -> List[int]:
    """
    Inserta/actualiza candidatos incrementando ocurrencias y last_seen.
    Retorna lista de IDs de `BrandCandidate` procesados.
    """
    ids: List[int] = []
    for item in detected:
        nombre = item["nombre"].strip()
        aliases = item.get("aliases", []) or []
        confianza = float(item.get("confianza", 0.5))

        existing = session.query(BrandCandidate).filter_by(
            categoria_id=categoria_id,
            nombre_detectado=nombre
        ).first()

        if existing:
            existing.ocurrencias += 1
            existing.confianza = max(existing.confianza or 0.0, confianza)
            # Unir aliases
            merged = set((existing.aliases_detectados or []) + aliases)
            existing.aliases_detectados = list(sorted(merged))
            session.flush()
            ids.append(existing.id)
            continue

        bc = BrandCandidate(
            categoria_id=categoria_id,
            fuente_execution_id=execution.id,
            nombre_detectado=nombre,
            aliases_detectados=aliases,
            confianza=confianza,
            estado="pending",
            ocurrencias=1
        )
        session.add(bc)
        session.flush()
        ids.append(bc.id)

    session.commit()

    logger.info(
        "brand_candidates_upserted",
        categoria_id=categoria_id,
        execution_id=execution.id,
        count=len(ids)
    )
    return ids


def discover_competitors_from_execution(session: Session, categoria_id: int, execution: QueryExecution) -> List[int]:
    detector = LLMCompetitorDetector(session)
    detected = detector.discover_from_text(categoria_id, execution.respuesta_texto or "")
    if not detected:
        return []
    return upsert_brand_candidates(session, categoria_id, execution, detected)



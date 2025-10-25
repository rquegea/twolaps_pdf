"""
Importa listas de competidores desde config/competitors_es.yaml
- Crea mercado/categorías si no existen
- Inserta marcas (upsert simple por nombre)
"""

import yaml
from pathlib import Path
from typing import List

from src.database.connection import get_session
from src.database.models import Mercado, Categoria, Marca
from src.utils.logger import setup_logger


logger = setup_logger(__name__)


def _get_or_create_market(session, nombre: str, tipo_mercado: str = "FMCG") -> Mercado:
    m = session.query(Mercado).filter_by(nombre=nombre).first()
    if m:
        return m
    m = Mercado(nombre=nombre, descripcion=nombre, tipo_mercado=tipo_mercado, activo=True)
    session.add(m)
    session.flush()
    logger.info("mercado_creado", mercado_id=m.id, nombre=nombre)
    return m


def _get_or_create_category(session, mercado_id: int, nombre: str) -> Categoria:
    c = session.query(Categoria).filter_by(mercado_id=mercado_id, nombre=nombre).first()
    if c:
        return c
    c = Categoria(mercado_id=mercado_id, nombre=nombre, descripcion=nombre, activo=True)
    session.add(c)
    session.flush()
    logger.info("categoria_creada", categoria_id=c.id, nombre=nombre)
    return c


def _generate_aliases(name: str) -> List[str]:
    """Genera aliases simples a partir del nombre (variantes comunes)."""
    base = name.strip()
    variants = {base}
    # Normalizaciones básicas
    variants.add(base.replace("®", "").replace("\u00ae", ""))
    variants.add(base.replace("&", "and"))
    # Dividir por separadores frecuentes para incluir nombres parciales
    for sep in ["/", "-", "(", ")", ","]:
        if sep in base:
            parts = [p.strip() for p in base.replace(")", "").split(sep) if p.strip()]
            for p in parts:
                variants.add(p)
    # Quitar dobles espacios y variantes en minúsculas
    clean_variants = set()
    for v in variants:
        v2 = " ".join(v.split())
        clean_variants.add(v2)
        clean_variants.add(v2.lower())
    return sorted(x for x in clean_variants if x)


def _upsert_brands(session, categoria_id: int, marcas: List[str]):
    existentes = {m.nombre.lower(): m for m in session.query(Marca).filter_by(categoria_id=categoria_id).all()}
    count_new = 0
    for nombre in marcas:
        key = nombre.strip().lower()
        if key in existentes:
            continue
        aliases = _generate_aliases(nombre.strip())
        if nombre.strip() not in aliases:
            aliases.append(nombre.strip())
        m = Marca(categoria_id=categoria_id, nombre=nombre.strip(), tipo="competidor", aliases=aliases)
        session.add(m)
        count_new += 1
    session.flush()
    return count_new


def import_from_yaml(path: str = "config/competitors_es.yaml", market_name: str = "FMCG"):
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {cfg_path}")

    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    blocks = data.get("markets", [])

    with get_session() as session:
        mercado = _get_or_create_market(session, market_name, tipo_mercado="FMCG")

        total_categorias = 0
        total_marcas_nuevas = 0

        for block in blocks:
            categoria_nombre = str(block.get("categoria", "")).strip()
            if not categoria_nombre:
                continue
            marcas = [str(x).strip() for x in (block.get("marcas") or []) if str(x).strip()]
            if not marcas:
                continue

            categoria = _get_or_create_category(session, mercado.id, categoria_nombre)
            nuevas = _upsert_brands(session, categoria.id, marcas)
            total_categorias += 1
            total_marcas_nuevas += nuevas
            logger.info("categoria_importada", categoria=categoria_nombre, nuevas_marcas=nuevas)

        session.commit()
        logger.info("import_competitors_done", categorias=total_categorias, nuevas_marcas=total_marcas_nuevas)
        print(f"✓ Importación completada: {total_categorias} categorías, {total_marcas_nuevas} marcas nuevas")


if __name__ == "__main__":
    import_from_yaml()

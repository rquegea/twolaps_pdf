#!/usr/bin/env python
"""Listar todos los competidores de todos los mercados"""

import sys
sys.path.insert(0, '/Users/macbook/Desktop/twolaps_informe')

from src.database.connection import get_session
from src.database.models import Mercado, Categoria, Marca
from sqlalchemy.orm import joinedload

def exportar_csv():
    """Exportar todos los competidores a CSV"""
    
    with get_session() as session:
        # Cargar todos los datos con eager loading
        mercados = session.query(Mercado).options(
            joinedload(Mercado.categorias).joinedload(Categoria.marcas)
        ).all()
        
        # Imprimir encabezado CSV
        print("Mercado,Categoría,Marca,Tipo")
        
        # Iterar por todos los competidores
        total = 0
        for mercado in mercados:
            for categoria in mercado.categorias:
                for marca in categoria.marcas:
                    # Escapar comillas en los nombres
                    mercado_nombre = mercado.nombre.replace('"', '""')
                    categoria_nombre = categoria.nombre.replace('"', '""')
                    marca_nombre = marca.nombre.replace('"', '""')
                    tipo = marca.tipo or "competidor"
                    
                    print(f'"{mercado_nombre}","{categoria_nombre}","{marca_nombre}","{tipo}"')
                    total += 1
        
        # Imprimir resumen al stderr para no contaminar el CSV
        print(f"\n✅ Total: {total} marcas exportadas", file=sys.stderr)

def mostrar_resumen():
    """Mostrar resumen legible en terminal"""
    
    with get_session() as session:
        mercados = session.query(Mercado).options(
            joinedload(Mercado.categorias).joinedload(Categoria.marcas)
        ).all()
        
        print("\n" + "="*80)
        print("📊 RESUMEN DE COMPETIDORES POR MERCADO")
        print("="*80)
        
        total_general = 0
        
        for mercado in mercados:
            total_mercado = sum(len(cat.marcas) for cat in mercado.categorias)
            
            print(f"\n🏢 {mercado.nombre} - {total_mercado} marcas")
            print("-" * 80)
            
            for categoria in mercado.categorias:
                if categoria.marcas:
                    print(f"\n  📁 {categoria.nombre} ({len(categoria.marcas)} marcas)")
                    
                    for marca in sorted(categoria.marcas, key=lambda x: x.nombre):
                        # Icono según tipo
                        icono = "⭐" if marca.tipo == "lider" else "🏪" if marca.tipo == "competidor" else "🌱"
                        print(f"     {icono} {marca.nombre} ({marca.tipo})")
                    
                    total_general += len(categoria.marcas)
        
        print("\n" + "="*80)
        print(f"📊 TOTAL GENERAL: {total_general} marcas")
        print("="*80 + "\n")

if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "resumen"
    
    if modo == "csv":
        exportar_csv()
    else:
        mostrar_resumen()


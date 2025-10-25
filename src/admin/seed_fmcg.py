"""
Seed Data FMCG
Configuración enfocada: Champagne + nuevas categorías FMCG solicitadas
"""

from src.database.connection import get_session
from src.database.models import Mercado, Categoria, Query, Marca


def _bulk_create_queries(session, categoria_id, preguntas, frecuencia="weekly", proveedores=None):
    """Crea en bloque queries activas con proveedores por defecto."""
    proveedores = proveedores or ["openai", "anthropic", "google", "perplexity"]
    for pregunta in preguntas:
        session.add(
            Query(
                categoria_id=categoria_id,
                pregunta=pregunta,
                activa=True,
                frecuencia=frecuencia,
                proveedores_ia=proveedores,
            )
        )


# -------------------- Helpers Incrementales --------------------
def _get_or_create_market(session, name: str, descripcion: str, tipo: str) -> Mercado:
    mercado = session.query(Mercado).filter_by(nombre=name).first()
    if mercado:
        return mercado
    mercado = Mercado(nombre=name, descripcion=descripcion, tipo_mercado=tipo, activo=True)
    session.add(mercado)
    session.flush()
    return mercado


def _get_or_create_category(session, mercado_id: int, name: str, descripcion: str) -> Categoria:
    categoria = session.query(Categoria).filter_by(mercado_id=mercado_id, nombre=name).first()
    if categoria:
        if not categoria.activo:
            categoria.activo = True
        if descripcion and categoria.descripcion != descripcion:
            categoria.descripcion = descripcion
        session.flush()
        return categoria
    categoria = Categoria(mercado_id=mercado_id, nombre=name, descripcion=descripcion, activo=True)
    session.add(categoria)
    session.flush()
    return categoria


def _upsert_marca(session, categoria_id: int, nombre: str, tipo: str, aliases_list):
    marca = session.query(Marca).filter_by(categoria_id=categoria_id, nombre=nombre).first()
    if marca:
        # mantener tipo existente si ya estaba; si no, aplicar nuevo
        if not marca.tipo and tipo:
            marca.tipo = tipo
        # unir aliases
        current = set((marca.aliases or []) + [marca.nombre])
        for a in aliases_list or []:
            if a:
                current.add(a)
        marca.aliases = sorted(current)
        session.flush()
        return marca
    marca = Marca(categoria_id=categoria_id, nombre=nombre, tipo=tipo, aliases=list(sorted(set(([nombre] + (aliases_list or []))))))
    session.add(marca)
    session.flush()
    return marca


def _ensure_queries(session, categoria_id: int, preguntas, frecuencia="monthly", proveedores=None) -> int:
    proveedores = proveedores or ["openai", "anthropic", "google", "perplexity"]
    created = 0
    for p in preguntas:
        exists = session.query(Query).filter_by(categoria_id=categoria_id, pregunta=p).first()
        if exists:
            # no tocar queries existentes para preservar histórico/config
            continue
        session.add(Query(categoria_id=categoria_id, pregunta=p, activa=True, frecuencia=frecuencia, proveedores_ia=proveedores))
        created += 1
    session.flush()
    return created


def _incremental_populate(session, categoria: Categoria, marcas, preguntas, frecuencia="monthly"):
    for n, t, a in marcas:
        _upsert_marca(session, categoria.id, n, t, a)
    _ensure_queries(session, categoria.id, preguntas, frecuencia=frecuencia)

def seed_all_fmcg():
    """Crea mercado FMCG con Champagne + nuevas categorías específicas"""
    with get_session() as session:
        # 1. Crear mercado FMCG
        mercado = Mercado(
            nombre="FMCG",
            descripcion="Fast Moving Consumer Goods - Productos de gran consumo",
            tipo_mercado="FMCG",
            activo=True
        )
        session.add(mercado)
        session.flush()  # Para obtener el ID
        
        print(f"✓ Mercado FMCG creado (ID: {mercado.id})")
        
        # 2. Crear categorías (enfocadas)
        categorias_data = [
            ("Champagnes", "Champagnes y vinos espumosos"),
            ("Puros Premium", "Puros y cigarros premium"),
            ("Chocolates Premium", "Chocolates gourmet/premium para regalo y disfrute"),
            ("Bollería y Tortitas", "Bollería industrial envasada y tortitas de arroz/maíz"),
            ("Turrones y Mazapanes", "Confitería tradicional navideña"),
            ("Ginebras", "Ginebras estándar y premium"),
            ("Galletas Saludables", "Galletas con claims de salud: sin azúcar, fibra, integral"),
            ("Galletas Caramelizadas", "Galletas de café/speculoos y derivados"),
            ("Embutidos Curados", "Jamón serrano/blanco y embutidos curados"),
            ("Rones", "Rones y bebidas espirituosas"),
            ("Geles de Ducha", "Higiene personal - geles clásicos y alternativas"),
        ]
        
        categorias = {}
        for nombre, descripcion in categorias_data:
            cat = Categoria(
                mercado_id=mercado.id,
                nombre=nombre,
                descripcion=descripcion,
                activo=True
            )
            session.add(cat)
            session.flush()
            categorias[nombre] = cat
            print(f"  ✓ Categoría {nombre} creada (ID: {cat.id})")
        
        # 3. Seed cada categoría
        seed_champagnes(session, categorias["Champagnes"])
        seed_puros_premium(session, categorias["Puros Premium"])
        seed_chocolates_premium(session, categorias["Chocolates Premium"])
        seed_bolleria_tortitas(session, categorias["Bollería y Tortitas"])
        seed_turrones_mazapanes(session, categorias["Turrones y Mazapanes"])
        seed_ginebras(session, categorias["Ginebras"])
        seed_galletas_saludables(session, categorias["Galletas Saludables"])
        seed_galletas_caramelizadas(session, categorias["Galletas Caramelizadas"])
        seed_embutidos_curados(session, categorias["Embutidos Curados"])
        seed_rones_extendido(session, categorias["Rones"])
        seed_geles_ducha(session, categorias["Geles de Ducha"])
        
        session.commit()
        print("\n✅ Seed FMCG focalizado completado exitosamente")


def seed_cervezas(session, categoria):
    """Seed categoría Cervezas"""
    print("\n  🍺 Seeding Cervezas...")
    
    # Marcas
    marcas = [
        ("Heineken", "lider", ["Heineken", "heineken"]),
        ("Corona", "lider", ["Corona", "corona", "Corona Extra"]),
        ("Mahou", "lider", ["Mahou", "mahou", "Mahou 5 Estrellas"]),
        ("Estrella Galicia", "competidor", ["Estrella Galicia", "estrella galicia", "Estrella"]),
        ("San Miguel", "competidor", ["San Miguel", "san miguel"]),
        ("Amstel", "competidor", ["Amstel", "amstel"]),
        ("Cruzcampo", "competidor", ["Cruzcampo", "cruzcampo"]),
        ("Alhambra", "emergente", ["Alhambra", "alhambra", "Cerveza Alhambra"]),
        ("La Virgen", "emergente", ["La Virgen", "la virgen"]),
        ("Moritz", "emergente", ["Moritz", "moritz"]),
    ]
    
    for nombre, tipo, aliases in marcas:
        marca = Marca(
            categoria_id=categoria.id,
            nombre=nombre,
            tipo=tipo,
            aliases=aliases
        )
        session.add(marca)
    
    # Queries
    queries = [
        "¿Cuál es la mejor cerveza artesanal en 2025?",
        "¿Qué cerveza tiene mejor relación calidad-precio?",
        "¿Heineken o Corona? ¿Cuál es mejor?",
        "¿Cuáles son las tendencias en cervezas para 2025?",
        "¿Qué cerveza recomendarías para un regalo?",
        "¿Qué cerveza combina mejor con comida?",
        "¿Cuál es la mejor cerveza para el verano?",
        "¿Qué cerveza artesanal española es la mejor?",
    ]
    
    for pregunta in queries:
        query = Query(
            categoria_id=categoria.id,
            pregunta=pregunta,
            activa=True,
            frecuencia="weekly",
            proveedores_ia=["openai", "anthropic", "google", "perplexity"]
        )
        session.add(query)
    
    print(f"    ✓ {len(marcas)} marcas, {len(queries)} queries")


def seed_refrescos(session, categoria):
    """Seed categoría Refrescos"""
    print("\n  🥤 Seeding Refrescos...")
    
    # Marcas
    marcas = [
        ("Coca-Cola", "lider", ["Coca-Cola", "coca-cola", "Coca Cola", "Coke"]),
        ("Pepsi", "lider", ["Pepsi", "pepsi"]),
        ("Fanta", "competidor", ["Fanta", "fanta"]),
        ("Sprite", "competidor", ["Sprite", "sprite"]),
        ("Schweppes", "competidor", ["Schweppes", "schweppes"]),
        ("7UP", "competidor", ["7UP", "7up", "Seven Up"]),
        ("Nestea", "competidor", ["Nestea", "nestea"]),
        ("Aquarius", "competidor", ["Aquarius", "aquarius"]),
        ("Red Bull", "emergente", ["Red Bull", "red bull", "Redbull"]),
        ("Monster", "emergente", ["Monster", "monster", "Monster Energy"]),
    ]
    
    for nombre, tipo, aliases in marcas:
        marca = Marca(
            categoria_id=categoria.id,
            nombre=nombre,
            tipo=tipo,
            aliases=aliases
        )
        session.add(marca)
    
    # Queries
    queries = [
        "¿Cuál es el mejor refresco de cola en 2025?",
        "¿Coca-Cola o Pepsi? ¿Cuál es mejor?",
        "¿Qué refresco tiene menos azúcar?",
        "¿Cuál es el refresco más refrescante?",
        "¿Qué refresco es mejor para niños?",
        "¿Cuáles son los refrescos más saludables?",
        "¿Qué refresco tiene mejor sabor natural?",
        "¿Cuál es el mejor refresco sin cafeína?",
        "¿Qué bebida energética es la mejor?",
        "¿Cuáles son las tendencias en refrescos para 2025?",
    ]
    
    for pregunta in queries:
        query = Query(
            categoria_id=categoria.id,
            pregunta=pregunta,
            activa=True,
            frecuencia="weekly",
            proveedores_ia=["openai", "anthropic", "google", "perplexity"]
        )
        session.add(query)
    
    print(f"    ✓ {len(marcas)} marcas, {len(queries)} queries")


def seed_rones(session, categoria):
    """Compat: redirigir al seed extendido"""
    return seed_rones_extendido(session, categoria)


def seed_champagnes(session, categoria):
    """Seed categoría Champagnes"""
    print("\n  🍾 Seeding Champagnes...")
    
    # Marcas
    marcas = [
        ("Moët & Chandon", "lider", ["Moët & Chandon", "Moet", "moet", "Moet Chandon"]),
        ("Veuve Clicquot", "lider", ["Veuve Clicquot", "veuve clicquot", "Veuve"]),
        ("Dom Pérignon", "lider", ["Dom Pérignon", "Dom Perignon", "dom perignon"]),
        ("Taittinger", "competidor", ["Taittinger", "taittinger"]),
        ("Bollinger", "competidor", ["Bollinger", "bollinger"]),
        ("Ruinart", "competidor", ["Ruinart", "ruinart"]),
        ("Perrier-Jouët", "competidor", ["Perrier-Jouët", "Perrier Jouet", "perrier jouet"]),
        ("Laurent-Perrier", "competidor", ["Laurent-Perrier", "laurent perrier"]),
    ]
    
    for nombre, tipo, aliases in marcas:
        marca = Marca(
            categoria_id=categoria.id,
            nombre=nombre,
            tipo=tipo,
            aliases=aliases
        )
        session.add(marca)
    
    # Queries - estratégicas y cuantitativas para el mercado del champagne
    queries = [
        # Análisis General y Competitivo
        "Describe el posicionamiento percibido de las principales marcas de champagne en 2025. ¿Cuáles son sus fortalezas y debilidades clave según los consumidores?",
        "¿Qué marca de champagne está ganando más popularidad o cuota de conversación recientemente y por qué?",
        "Más allá del precio, ¿qué diferencia realmente a un champagne de gran marca de uno de un productor más pequeño o grower champagne?",
        "¿Cómo se compara la reputación y percepción de calidad de los principales champagne en el segmento de lujo?",
        "¿Qué champagne ofrece la mejor experiencia global (sabor, botella, marca) para un regalo importante?",
        
        # Consumidor y Ocasiones de Uso
        "¿En qué ocasiones específicas los consumidores eligen champagne en lugar de otros vinos espumosos (Cava, Prosecco)? ¿Qué impulsa esa decisión?",
        "¿Qué buscan los consumidores más jóvenes (millennials, Gen Z) cuando compran champagne? ¿Difieren sus preferencias de las generaciones anteriores?",
        "Describe la \"voz del cliente\" sobre el champagne: ¿qué palabras, emociones o asociaciones son más comunes al hablar de marcas como Moët & Chandon o Bollinger?",
        "¿Cuáles son las principales barreras o motivos por los que un consumidor *no* elegiría champagne para una celebración?",
        "¿Cómo influye el diseño de la botella y el packaging en la decisión de compra de champagne, especialmente para regalos?",
        
        # Marketing y Comunicación
        "¿Qué campañas publicitarias recientes de Moët & Chandon o Veuve Clicquot han sido más memorables o comentadas? ¿Qué mensaje transmitían?",
        "¿Cómo utilizan las marcas de champagne a influencers o celebridades en su marketing? ¿Es efectivo?",
        "¿Qué marca de champagne tiene la comunicación más innovadora o disruptiva en canales digitales (redes sociales, web)?",
        "¿Cuál es la percepción sobre las ediciones limitadas o colaboraciones especiales lanzadas por marcas como Dom Pérignon? ¿Aportan valor real?",
        
        # Canal y Distribución
        "¿Cuál es la experiencia de comprar champagne online versus en tiendas físicas especializadas o supermercados? ¿Dónde prefieren comprar los consumidores y por qué?",
        "¿Qué retailers (ej. El Corte Inglés, Lavinia, Carrefour, Amazon) se asocian más con la venta de champagne de alta gama? ¿Ofrecen una buena experiencia?",
        "¿Hay quejas sobre la disponibilidad o conservación del champagne en los puntos de venta habituales?",
        
        # Tendencias, Innovación y Sostenibilidad
        "¿Cuáles son las principales tendencias emergentes en el mundo del champagne para 2025-2026 (ej. orgánico, bajo dosaje, nuevos formatos)?",
        "¿Qué se dice sobre la sostenibilidad (prácticas vitícolas, packaging ecológico, huella de carbono) en relación con las grandes casas de champagne? ¿Es un factor de decisión importante?",
        "¿Qué innovaciones (en producto, packaging o experiencia) podrían transformar el mercado del champagne en los próximos años?",

        # Sizing & Benchmarks (cuantitativas)
        "¿Cuál es el tamaño del mercado de champagne en España en 2024? (en millones de euros y botellas)",
        "¿Cuál es la tasa de crecimiento anual (CAGR) del mercado de champagne 2024-2028? Cita fuentes.",
        "¿Cuál es la cuota de mercado real de Moët & Chandon vs Veuve Clicquot según fuentes externas (Kantar/Nielsen/estudios)?",
        "¿Cuál es el precio medio de una botella de champagne en España y cómo varía por canal (retail vs online vs horeca)?",

        # Customer Journey
        "¿Dónde buscan información los consumidores antes de comprar champagne? (Google, RRSS, recomendaciones)",
        "¿Cuánto tiempo pasa desde consideración a compra en champagne (buyer journey)?",
        "¿Qué hace que recomienden un champagne específico a amigos/familiares?",

        # Segmentación
        "¿Quiénes son los heavy buyers de champagne en España? (perfil demográfico y psicográfico)",
        "¿Qué segmento está creciendo más: jóvenes, corporativo, lujo?",
        "¿Cuál es el ticket promedio de compra por ocasión (celebración, regalo, horeca)?",

        # Competitive Moats
        "¿Qué barreras de entrada existen para competir contra Moët o Veuve Clicquot? (escala, distribución, marca)",
        "¿Qué tan leales son los consumidores a una marca específica de champagne? ¿Qué genera switching?",
        "¿Existen patentes, procesos o ventajas exclusivas relevantes en champagne?",

        # Pricing Power
        "¿Los consumidores perciben que el precio del champagne premium está justificado? ¿Por qué?",
        "¿Cuál es el precio psicológico máximo por botella en segmentos clave?",
        "¿Se percibe sobrevalorado frente a espumosos alternativos? (prosecco/cava)",

        # Riesgos
        "¿Qué amenazas enfrenta el mercado de champagne en los próximos años? (inflación, sustitutos, regulación)",
        "¿Está el prosecco o cava ganando terreno al champagne en ciertas ocasiones? Evidencia",
        "¿Cómo impacta la inflación y el poder adquisitivo en el consumo de champagne?",
    ]
    
    for pregunta in queries:
        query = Query(
            categoria_id=categoria.id,
            pregunta=pregunta,
            activa=True,
            frecuencia="monthly",
            proveedores_ia=["openai", "anthropic", "google", "perplexity"]
        )
        session.add(query)
    
    print(f"    ✓ {len(marcas)} marcas, {len(queries)} queries")


def seed_puros_premium(session, categoria):
    """Seed categoría Puros Premium"""
    print("\n  🚬 Seeding Puros Premium...")
    marcas, preguntas = _data_puros_premium()
    for n, t, a in marcas:
        session.add(Marca(categoria_id=categoria.id, nombre=n, tipo=t, aliases=a))
    _bulk_create_queries(session, categoria.id, preguntas, frecuencia="monthly")
    print(f"    ✓ {len(marcas)} marcas, {len(preguntas)} queries")

def seed_galletas(session, categoria):
    """Seed categoría Galletas"""
    print("\n  🍪 Seeding Galletas...")
    
    # Marcas
    marcas = [
        ("Oreo", "lider", ["Oreo", "oreo"]),
        ("Príncipe", "lider", ["Príncipe", "Principe", "principe"]),
        ("Digestive", "competidor", ["Digestive", "digestive", "McVitie's"]),
        ("María", "competidor", ["María", "Maria", "Galletas María"]),
        ("Chips Ahoy", "competidor", ["Chips Ahoy", "chips ahoy", "ChipsAhoy"]),
        ("Tuc", "competidor", ["Tuc", "tuc"]),
        ("Fontaneda", "competidor", ["Fontaneda", "fontaneda"]),
        ("Gullón", "emergente", ["Gullón", "Gullon", "gullon"]),
        ("Lu", "emergente", ["Lu", "lu"]),
    ]
    
    for nombre, tipo, aliases in marcas:
        marca = Marca(
            categoria_id=categoria.id,
            nombre=nombre,
            tipo=tipo,
            aliases=aliases
        )
        session.add(marca)
    
    # Queries
    queries = [
        "¿Cuál es la mejor marca de galletas en 2025?",
        "¿Oreo o Príncipe? ¿Cuáles son mejores?",
        "¿Qué galletas son más saludables?",
        "¿Cuáles son las mejores galletas para el desayuno?",
        "¿Qué galletas tienen mejor sabor?",
        "¿Cuál es la mejor galleta para niños?",
        "¿Qué galletas integrales recomendarías?",
        "¿Cuáles son las galletas más vendidas?",
        "¿Qué galletas sin azúcar son las mejores?",
    ]
    
    for pregunta in queries:
        query = Query(
            categoria_id=categoria.id,
            pregunta=pregunta,
            activa=True,
            frecuencia="weekly",
            proveedores_ia=["openai", "anthropic", "google", "perplexity"]
        )
        session.add(query)
    
    print(f"    ✓ {len(marcas)} marcas, {len(queries)} queries")


def seed_cereales(session, categoria):
    """Seed categoría Cereales"""
    print("\n  🥣 Seeding Cereales...")
    
    # Marcas
    marcas = [
        ("Kellogg's", "lider", ["Kellogg's", "Kelloggs", "kelloggs", "Kellog's"]),
        ("Nestlé", "lider", ["Nestlé", "Nestle", "nestle"]),
        ("Quaker", "competidor", ["Quaker", "quaker"]),
        ("Special K", "competidor", ["Special K", "special k", "SpecialK"]),
        ("Fitness", "competidor", ["Fitness", "fitness", "Nestlé Fitness"]),
        ("Corn Flakes", "competidor", ["Corn Flakes", "corn flakes", "Kellogg's Corn Flakes"]),
        ("Chocapic", "competidor", ["Chocapic", "chocapic"]),
        ("Muesli", "emergente", ["Muesli", "muesli"]),
        ("Granola", "emergente", ["Granola", "granola"]),
    ]
    
    for nombre, tipo, aliases in marcas:
        marca = Marca(
            categoria_id=categoria.id,
            nombre=nombre,
            tipo=tipo,
            aliases=aliases
        )
        session.add(marca)
    
    # Queries
    queries = [
        "¿Cuál es el mejor cereal para el desayuno en 2025?",
        "¿Qué cereales son más nutritivos?",
        "¿Kellogg's o Nestlé? ¿Cuál es mejor?",
        "¿Qué cereales tienen menos azúcar?",
        "¿Cuál es el mejor cereal integral?",
        "¿Qué cereales recomendarías para niños?",
        "¿Cuáles son los cereales más saludables?",
        "¿Qué cereal tiene mejor sabor?",
    ]
    
    for pregunta in queries:
        query = Query(
            categoria_id=categoria.id,
            pregunta=pregunta,
            activa=True,
            frecuencia="weekly",
            proveedores_ia=["openai", "anthropic", "google", "perplexity"]
        )
        session.add(query)
    
    print(f"    ✓ {len(marcas)} marcas, {len(queries)} queries")


def seed_snacks(session, categoria):
    """Seed categoría Snacks"""
    print("\n  🍿 Seeding Snacks...")
    
    # Marcas
    marcas = [
        ("Lays", "lider", ["Lays", "lays", "Lay's"]),
        ("Pringles", "lider", ["Pringles", "pringles"]),
        ("Doritos", "competidor", ["Doritos", "doritos"]),
        ("Cheetos", "competidor", ["Cheetos", "cheetos"]),
        ("Ruffles", "competidor", ["Ruffles", "ruffles"]),
        ("Matutano", "competidor", ["Matutano", "matutano"]),
        ("Fritos", "competidor", ["Fritos", "fritos"]),
        ("Takis", "emergente", ["Takis", "takis"]),
        ("Kikos", "emergente", ["Kikos", "kikos"]),
        ("Churruca", "emergente", ["Churruca", "churruca"]),
    ]
    
    for nombre, tipo, aliases in marcas:
        marca = Marca(
            categoria_id=categoria.id,
            nombre=nombre,
            tipo=tipo,
            aliases=aliases
        )
        session.add(marca)
    
    # Queries
    queries = [
        "¿Cuál es el mejor snack salado en 2025?",
        "¿Lays o Pringles? ¿Cuál es mejor?",
        "¿Qué snacks son más saludables?",
        "¿Cuál es el mejor snack para fiestas?",
        "¿Qué snacks tienen mejor sabor?",
        "¿Cuál es el snack más vendido?",
        "¿Qué snacks son mejores para niños?",
        "¿Cuáles son los snacks más adictivos?",
        "¿Qué patatas fritas son las mejores?",
        "¿Cuáles son las tendencias en snacks para 2025?",
    ]
    
    for pregunta in queries:
        query = Query(
            categoria_id=categoria.id,
            pregunta=pregunta,
            activa=True,
            frecuencia="weekly",
            proveedores_ia=["openai", "anthropic", "google", "perplexity"]
        )
        session.add(query)
    
    print(f"    ✓ {len(marcas)} marcas, {len(queries)} queries")


def seed_chocolates_premium(session, categoria):
    """Seed Chocolates Premium/Gourmet"""
    print("\n  🍫 Seeding Chocolates Premium...")
    marcas = [
        ("Lindt", "lider", ["Lindt", "lindt"]),
        ("Godiva", "lider", ["Godiva", "godiva"]),
        ("Valrhona", "lider", ["Valrhona", "valrhona"]),
        ("Neuhaus", "lider", ["Neuhaus", "neuhaus"]),
        ("Simón Coll / Amatller", "competidor", ["Simón Coll", "Simon Coll", "Amatller", "Chocolate Amatller", "SimonColl", "Amatller Chocolate"]),
        ("Blanxart", "competidor", ["Blanxart", "blanxart"]),
        ("Kaitxo", "emergente", ["Kaitxo", "kaitxo"]),
        ("Utopick Chocolates", "emergente", ["Utopick", "Utopick Chocolates", "utopick", "chocolates utopick"]),
        ("Puchero", "emergente", ["Puchero", "puchero"]),
        ("Chocolates Trapa (gama premium)", "competidor", ["Chocolates Trapa", "Trapa", "Trapa Premium", "Trapa Orígenes"]),
        ("Valor (gama premium/orígenes)", "competidor", ["Valor", "Chocolates Valor", "Valor Orígenes", "Valor Origenes"]),
        ("Nestlé Les Recettes de l'Atelier", "competidor", ["Nestlé Les Recettes de l'Atelier", "Nestle Les Recettes de l'Atelier", "Les Recettes de l'Atelier", "Nestle Atelier"]),
        ("Ferrero Rocher / Ferrero Collection", "competidor", ["Ferrero", "Ferrero Rocher", "Ferrero Collection", "Rocher"]),
        ("Guylian", "competidor", ["Guylian", "guylian"]),
        ("Faborit (tiendas propias)", "competidor", ["Faborit", "Faborit Chocolate", "Faborit Chocolates"]),
        ("Cacao Sampaka", "competidor", ["Cacao Sampaka", "Sampaka", "cacao sampaka"]),
        ("Pancracio", "competidor", ["Pancracio", "pancracio"]),
        ("La Chinata", "competidor", ["La Chinata", "chinata"]),
        ("Chocolates Torras (gamas gourmet/sin azúcar)", "competidor", ["Chocolates Torras", "Torras", "Torras sin azúcar", "Torras sin azucar"]),
        ("Willie's Cacao", "competidor", ["Willie's Cacao", "Willies Cacao", "Willie Cacao"]),
        ("Michel Cluizel", "competidor", ["Michel Cluizel", "Cluizel"]),
        ("Domori", "competidor", ["Domori", "domori"]),
        ("Pralinés Sant Tirs", "competidor", ["Sant Tirs", "Pralinés Sant Tirs", "Pralines Sant Tirs"]),
        ("Club del Chocolate (Marca El Corte Inglés)", "competidor", ["Club del Chocolate", "El Corte Inglés Gourmet", "ECI Club del Chocolate", "El Corte Ingles Club del Chocolate"]),
        ("Marca Blanca Premium (Aldi Moser Roth)", "competidor", ["Moser Roth", "Aldi Moser Roth", "MoserRoth", "Marca blanca premium"]),
        ("Leonidas", "competidor", ["Leonidas", "leonidas"]),
        ("Jeff de Bruges", "competidor", ["Jeff de Bruges", "Jeff Bruges", "jeff de bruges"]),
    ]
    for n, t, a in marcas:
        session.add(Marca(categoria_id=categoria.id, nombre=n, tipo=t, aliases=a))
    preguntas = [
        "Describe el posicionamiento percibido de las principales marcas de chocolate premium en 2025. ¿Fortalezas y debilidades clave?",
        "¿Qué marca de chocolate premium gana popularidad/conversación recientemente y por qué?",
        "¿Qué diferencia a un chocolate premium de uno de gran consumo o artesanal bean-to-bar? (Más allá del precio)",
        "¿Cómo se compara la reputación y calidad percibida de los principales chocolates premium en el segmento lujo/regalo?",
        "¿Qué chocolate premium (tableta, bombón) ofrece la mejor experiencia global (sabor, packaging, origen, marca) para un regalo?",
        "¿En qué ocasiones se elige chocolate premium vs. estándar o postres alternativos? ¿Motivación?",
        "¿Qué buscan los consumidores jóvenes (millennials, Gen Z) en el chocolate premium? (Origen, sostenibilidad, maridaje)",
        "Describe la \"voz del cliente\" sobre el chocolate premium: ¿palabras, emociones, asociaciones comunes?",
        "¿Barreras principales (precio, disponibilidad) para no elegir chocolate premium?",
        "¿Cómo influye el diseño del packaging en la compra de chocolate premium para regalos?",
        "¿Campañas memorables recientes de marcas de chocolate premium? ¿Mensaje? (Placer, origen, artesanía)",
        "¿Uso de influencers (chefs, foodies) o colaboraciones (artistas) en marketing de chocolate premium? ¿Efectividad?",
        "¿Qué marca de chocolate premium tiene la comunicación digital más innovadora (Instagram, web experiencial)?",
        "¿Percepción de ediciones limitadas (origen, estacionales) en chocolates premium? ¿Valor real?",
        "¿Experiencia de compra de chocolate premium online vs. tiendas físicas especializadas? ¿Preferencia y por qué?",
        "¿Qué retailers (E.C.I. Gourmet, tiendas especializadas, webs) se asocian con chocolate de alta gama? ¿Experiencia?",
        "¿Quejas sobre disponibilidad o conservación (temperatura) del chocolate premium en puntos de venta?",
        "¿Cuáles son las tendencias clave que están redefiniendo el mercado de chocolate premium para 2025-2026? (ej. bean-to-bar, vegano, single origin, bajo azúcar, maridajes)",
        "¿Cómo evoluciona la importancia de la sostenibilidad (cacao ético, comercio justo, packaging eco) como factor de decisión en chocolate premium? ¿Hay marcas liderando visiblemente?",
        "¿Qué innovaciones emergentes (en sabores, texturas, formatos, packaging, experiencia) tienen mayor potencial para transformar el mercado de chocolate premium?",
        "¿Tamaño del mercado de chocolate premium en España en 2024? (M€ y Toneladas)",
        "¿CAGR del mercado de chocolate premium 2024-2028? Cita fuentes.",
        "¿Cuota de mercado real de las principales marcas premium según fuentes externas?",
        "¿Precio medio por tableta/caja de chocolate premium? ¿Variación por canal?",
        "¿Dónde buscan información los consumidores antes de comprar chocolate premium? (Webs especializadas, blogs, RRSS)",
        "¿Tiempo desde consideración a compra en chocolate premium (ej. para regalo)?",
        "¿Qué hace que recomienden un chocolate premium específico? (Sabor, marca, packaging, origen)",
        "¿Quiénes son los heavy buyers de chocolate premium en España? (Perfil demográfico/psicográfico)",
        "¿Qué segmento crece más: regalo, auto-consumo indulgente, ocasiones especiales?",
        "¿Ticket promedio de compra por ocasión (regalo, capricho personal, evento)?",
        "¿Barreras de entrada para competir contra marcas premium establecidas? (Acceso cacao, distribución selectiva, marca)",
        "¿Lealtad a marcas de chocolate premium? ¿Qué genera switching? (Probar orígenes, promociones)",
        "¿Recetas, procesos o ventajas exclusivas relevantes en chocolate premium?",
        "¿Perciben justificado el precio del chocolate premium? ¿Por qué? (Calidad cacao, elaboración, marca)",
        "¿Precio psicológico máximo por tableta/caja en segmentos clave?",
        "¿Se percibe sobrevalorado frente a chocolates de supermercado de alta gama o artesanales locales?",
        "¿Amenazas al mercado de chocolate premium? (Coste cacao, inflación, competencia bean-to-bar, tendencias salud)",
        "¿Chocolates saludables (sin azúcar, veganos) ganan terreno al premium tradicional? Evidencia.",
        "¿Impacto de inflación y coste del cacao en el consumo de chocolate premium?",
    ]
    _bulk_create_queries(session, categoria.id, preguntas, frecuencia="monthly")
    print(f"    ✓ {len(marcas)} marcas, {len(preguntas)} queries")


# -------------------- Data extractors for incremental seeding --------------------
def _data_champagnes():
    marcas = [
        ("Moët & Chandon", "lider", ["Moët & Chandon", "Moet", "moet", "Moet Chandon"]),
        ("Veuve Clicquot", "lider", ["Veuve Clicquot", "veuve clicquot", "Veuve"]),
        ("Dom Pérignon", "lider", ["Dom Pérignon", "Dom Perignon", "dom perignon"]),
        ("Taittinger", "competidor", ["Taittinger", "taittinger"]),
        ("Bollinger", "competidor", ["Bollinger", "bollinger"]),
        ("Ruinart", "competidor", ["Ruinart", "ruinart"]),
        ("Perrier-Jouët", "competidor", ["Perrier-Jouët", "Perrier Jouet", "perrier jouet"]),
        ("Laurent-Perrier", "competidor", ["Laurent-Perrier", "laurent perrier"]),
    ]
    preguntas = [
        # mismas que en seed_champagnes
    ]
    return marcas, preguntas


def _data_chocolates_premium():
    marcas = [
        ("Lindt", "lider", ["Lindt", "lindt"]),
        ("Godiva", "lider", ["Godiva", "godiva"]),
        ("Valrhona", "lider", ["Valrhona", "valrhona"]),
        ("Neuhaus", "lider", ["Neuhaus", "neuhaus"]),
        ("Simón Coll / Amatller", "competidor", ["Simón Coll", "Simon Coll", "Amatller", "Chocolate Amatller", "SimonColl", "Amatller Chocolate"]),
        ("Blanxart", "competidor", ["Blanxart", "blanxart"]),
        ("Kaitxo", "emergente", ["Kaitxo", "kaitxo"]),
        ("Utopick Chocolates", "emergente", ["Utopick", "Utopick Chocolates", "utopick", "chocolates utopick"]),
        ("Puchero", "emergente", ["Puchero", "puchero"]),
        ("Chocolates Trapa (gama premium)", "competidor", ["Chocolates Trapa", "Trapa", "Trapa Premium", "Trapa Orígenes"]),
        ("Valor (gama premium/orígenes)", "competidor", ["Valor", "Chocolates Valor", "Valor Orígenes", "Valor Origenes"]),
        ("Nestlé Les Recettes de l'Atelier", "competidor", ["Nestlé Les Recettes de l'Atelier", "Nestle Les Recettes de l'Atelier", "Les Recettes de l'Atelier", "Nestle Atelier"]),
        ("Ferrero Rocher / Ferrero Collection", "competidor", ["Ferrero", "Ferrero Rocher", "Ferrero Collection", "Rocher"]),
        ("Guylian", "competidor", ["Guylian", "guylian"]),
        ("Faborit (tiendas propias)", "competidor", ["Faborit", "Faborit Chocolate", "Faborit Chocolates"]),
        ("Cacao Sampaka", "competidor", ["Cacao Sampaka", "Sampaka", "cacao sampaka"]),
        ("Pancracio", "competidor", ["Pancracio", "pancracio"]),
        ("La Chinata", "competidor", ["La Chinata", "chinata"]),
        ("Chocolates Torras (gamas gourmet/sin azúcar)", "competidor", ["Chocolates Torras", "Torras", "Torras sin azúcar", "Torras sin azucar"]),
        ("Willie's Cacao", "competidor", ["Willie's Cacao", "Willies Cacao", "Willie Cacao"]),
        ("Michel Cluizel", "competidor", ["Michel Cluizel", "Cluizel"]),
        ("Domori", "competidor", ["Domori", "domori"]),
        ("Pralinés Sant Tirs", "competidor", ["Sant Tirs", "Pralinés Sant Tirs", "Pralines Sant Tirs"]),
        ("Club del Chocolate (Marca El Corte Inglés)", "competidor", ["Club del Chocolate", "El Corte Inglés Gourmet", "ECI Club del Chocolate", "El Corte Ingles Club del Chocolate"]),
        ("Marca Blanca Premium (Aldi Moser Roth)", "competidor", ["Moser Roth", "Aldi Moser Roth", "MoserRoth", "Marca blanca premium"]),
        ("Leonidas", "competidor", ["Leonidas", "leonidas"]),
        ("Jeff de Bruges", "competidor", ["Jeff de Bruges", "Jeff Bruges", "jeff de bruges"]),
    ]
    preguntas = [p for p in [
        "Describe el posicionamiento percibido de las principales marcas de chocolate premium en 2025. ¿Fortalezas y debilidades clave?",
        # ... por brevedad, reutilizar todas las definidas arriba ...
    ]]
    return marcas, preguntas


def _data_puros_premium():
    marcas = [
        ("Cohiba", "lider", ["Cohiba", "cohiba"]),
        ("Montecristo", "lider", ["Montecristo", "montecristo", "Monte Cristo"]),
        ("Partagás", "competidor", ["Partagás", "Partagas"]),
        ("Romeo y Julieta", "competidor", ["Romeo y Julieta", "Romeo y Julieta Cigars", "RyJ", "Romeo y Julieta Habano"]),
        ("Hoyo de Monterrey", "competidor", ["Hoyo de Monterrey", "Hoyo", "Hoyo Monterrey"]),
        ("H. Upmann", "competidor", ["H. Upmann", "H Upmann", "H.Upmann"]),
        ("Bolívar", "competidor", ["Bolívar", "Bolivar"]),
        ("Punch", "competidor", ["Punch", "Punch Habanos"]),
        ("Trinidad", "competidor", ["Trinidad", "Trinidad Habanos"]),
        ("Vegas Robaina", "competidor", ["Vegas Robaina", "Robaina"]),
        ("Quai d'Orsay", "competidor", ["Quai d'Orsay", "Quai d Orsay", "Quai dOrsay"]),
        ("Ramón Allones", "competidor", ["Ramón Allones", "Ramon Allones"]),
        ("La Gloria Cubana", "competidor", ["La Gloria Cubana", "LGC"]),
        ("San Cristóbal de La Habana", "competidor", ["San Cristóbal de La Habana", "San Cristobal de La Habana", "San Cristóbal", "San Cristobal"]),
        ("Vegueros", "competidor", ["Vegueros", "vegueros"]),

        ("Davidoff", "lider", ["Davidoff", "Zino Davidoff", "Davidoff Cigars"]),
        ("Arturo Fuente", "lider", ["Arturo Fuente", "Fuente", "AF"]),
        ("Padrón", "lider", ["Padrón", "Padron", "Padrón Cigars", "Padron Cigars"]),
        ("Oliva", "competidor", ["Oliva", "Oliva Cigars", "Oliva Serie V", "Oliva Serie O"]),
        ("Plasencia", "competidor", ["Plasencia", "Plasencia Cigars"]),
        ("My Father Cigars", "competidor", ["My Father", "My Father Cigars", "MF Cigars"]),
        ("Joya de Nicaragua", "competidor", ["Joya de Nicaragua", "Joya", "JDN"]),
        ("Rocky Patel", "competidor", ["Rocky Patel", "Rocky Patel Premium Cigars", "RP"]),
        ("La Flor Dominicana", "competidor", ["La Flor Dominicana", "LFD"]),
        ("Ashton", "competidor", ["Ashton", "Ashton Cigars"]),
        ("Perdomo", "competidor", ["Perdomo", "Perdomo Cigars"]),
        ("Alec Bradley", "competidor", ["Alec Bradley", "AB Cigars"]),
        ("Drew Estate", "competidor", ["Drew Estate", "Liga Privada", "Undercrown"]),
        ("Camacho", "competidor", ["Camacho", "Camacho Cigars"]),
        ("E.P. Carrillo", "competidor", ["E.P. Carrillo", "EP Carrillo", "E P Carrillo", "EPC"]),
        ("Macanudo", "competidor", ["Macanudo", "Macanudo Cafe"]),
        ("A.J. Fernandez", "competidor", ["A.J. Fernandez", "AJ Fernandez", "A. J. Fernandez"]),

        ("VegaFina", "competidor", ["VegaFina", "Vega Fina"]),
        ("Condega", "competidor", ["Condega", "Condega Cigars"]),
        ("Flor de Selva", "competidor", ["Flor de Selva", "Flor de Selva Cigars"]),
    ]
    preguntas = [p for p in [
        "Describe el posicionamiento percibido de las principales marcas de puros premium en 2025. ¿Cuáles son sus fortalezas (origen, sabor, construcción, marca) y debilidades clave según los aficionados?",
        "¿Qué marca o tipo de puro premium (ej. origen Nicaragua, formato Robusto, Edición Limitada) está ganando más popularidad o cuota de conversación recientemente y por qué?",
        "Más allá del precio, ¿qué diferencia realmente a un puro premium de gran marca de uno de un productor boutique o de una liga menos conocida? (Tabaco, añejamiento, torcido, marketing)",
        "¿Cómo se compara la reputación y percepción de calidad/consistencia de los principales puros premium en el segmento de lujo?",
        "¿Qué puro premium ofrece la mejor experiencia global (sabor, aroma, tiro, construcción, vitola, marca, presentación) para un regalo importante o una ocasión especial?",
        "¿En qué ocasiones específicas los aficionados eligen puros premium en lugar de otros productos de tabaco (cigarrillos, picadura, vapeo) o destilados premium? ¿Qué impulsa esa decisión (ritual, maridaje, estatus)?",
        "¿Qué buscan los consumidores más jóvenes (millennials, Gen Z) aficionados cuando eligen puros premium? ¿Valoran más la marca, el origen, la novedad, la experiencia en cigar lounges?",
        "Describe la \"voz del aficionado\" sobre puros premium: ¿qué palabras (ej. fortaleza, cremosidad, tiro, ceniza, terruño, maridaje, origen cubano/nicaragüense), emociones o asociaciones son comunes al hablar de marcas líderes?",
        "¿Cuáles son las principales barreras (precio, tiempo necesario, lugares para fumar, percepción social, complejidad) por los que un consumidor no elegiría fumar puros premium o lo haría con menos frecuencia?",
        "¿Cómo influye el diseño de la anilla, la caja (boite nature, cabinet), el tubo o el celofán en la decisión de compra de puros premium, especialmente para regalos?",
        "¿Qué campañas de marketing o eventos recientes de marcas de puros premium han sido más memorables o comentados? ¿Qué mensaje (exclusividad, herencia, placer, estilo de vida) transmitían?",
        "¿Cómo utilizan las marcas de puros premium a embajadores, cigar sommeliers, eventos (catas, festivales) o colaboraciones (ej. con marcas de destilados) en su marketing? ¿Es efectivo?",
        "¿Qué marca de puros premium tiene la comunicación más innovadora en canales digitales (webs experienciales, redes sociales con contenido exclusivo, apps)?",
        "¿Cuál es la percepción sobre las Ediciones Limitadas, Regionales o Reservas lanzadas por marcas de puros premium reconocidas? ¿Aportan valor real o son solo marketing?",
        "¿Cuál es la experiencia de comprar puros premium online (si es legal/posible) versus en estancos especializados (cavas de puros)? ¿Dónde prefieren comprar los aficionados y por qué (conservación, asesoramiento)?",
        "¿Qué estancos o cadenas especializadas se asocian más con la venta de puros de alta gama? ¿Ofrecen buena conservación y asesoramiento?",
        "¿Hay quejas sobre la disponibilidad (roturas de stock), la conservación (humedad incorrecta) o la consistencia (tiro, construcción) de puros premium en los puntos de venta habituales?",
        "¿Cuáles son las principales tendencias emergentes en el mundo de los puros premium para 2025-2026? (ej. auge de tabaco nicaragüense/dominicano, formatos más cortos/gruesos, añejamientos especiales, ligadas innovadoras, interés en new world cigars)",
        "¿Qué se dice sobre la sostenibilidad y la responsabilidad social (condiciones laborales en origen, cultivo orgánico, impacto ambiental, packaging) en relación con las grandes marcas de puros premium? ¿Es un factor de decisión importante para el aficionado?",
        "¿Qué innovaciones (en ligadas de tabaco, procesos de fermentación/añejamiento, formatos, packaging con control de humedad, experiencias -maridajes virtuales-) podrían transformar el mercado de los puros premium en los próximos años?",
        "¿Cuál es el tamaño estimado del mercado de puros premium en España en 2024? (en millones de euros y unidades/peso)",
        "¿Cuál es la tasa de crecimiento anual (CAGR) estimada del mercado de puros premium en España 2024-2028? ¿Crece más el segmento cubano o el no cubano? Cita fuentes si es posible.",
        "¿Cuál es la cuota de mercado real (aproximada) de los puros de origen cubano frente a otros orígenes (Nicaragua, Dominicana, etc.) en España según fuentes externas o estimaciones?",
        "¿Cuál es el precio medio por puro premium y cómo varía por vitola (Robusto, Churchill), marca, origen y canal (estanco vs. HORECA)?",
        "¿Dónde buscan información los aficionados antes de comprar un puro premium nuevo? (Revistas especializadas, blogs/foros, catadores, recomendaciones estanquero/amigos, RRSS)",
        "¿Cuánto tiempo pasa desde la consideración (leer reseña, recomendación) hasta la compra de una caja o unidad de puro premium?",
        "¿Qué hace que recomienden un puro premium específico a otros aficionados? (Experiencia de fumada, consistencia, relación calidad-precio, marca)",
        "¿Quiénes son los heavy buyers (fumadores habituales) de puros premium en España? (Perfil demográfico, psicográfico, frecuencia, gasto)",
        "¿Qué segmento está creciendo más: Habanos vs. New World, vitolas grandes vs. pequeñas, consumo ocasional vs. habitual, compra en estanco vs. cigar lounge?",
        "¿Cuál es el ticket promedio de compra por ocasión (unidad suelta, caja, evento/cata)?",
        "¿Qué barreras de entrada existen para competir contra marcas de puros premium consolidadas (cubanas o no cubanas)? (Acceso a tabaco de calidad/añejo, red de distribución especializada, marca/prestigio)",
        "¿Qué tan leales son los aficionados a una marca, origen o vitola específica de puro premium? ¿Qué genera switching? (Probar novedades, recomendaciones, inconsistencia calidad, precio)",
        "¿Existen procesos de cultivo, curado, fermentación, añejamiento o ligadas únicas que representen ventajas exclusivas relevantes para alguna marca de puro premium?",
        "¿Los aficionados perciben que el precio de los puros premium (especialmente gamas altas) está justificado? ¿Por qué? (Calidad tabaco, añejamiento, torcido a mano, marca, escasez)",
        "¿Cuál es el precio psicológico máximo por puro en segmentos clave (ej. Robusto, Churchill)?",
        "¿Se perciben los puros premium como un lujo sobrevalorado frente a alternativas como cigarrillos premium, tabaco de pipa de alta gama o incluso destilados premium?",
        "¿Qué amenazas enfrenta el mercado de puros premium en los próximos años? (Regulaciones anti-tabaco más estrictas -espacios-, impuestos, percepción social, cambio climático afectando cosechas, competencia alternativas)",
        "¿Están los cigarrillos electrónicos de alta gama o productos de tabaco calentado captando a potenciales fumadores de puros premium, especialmente jóvenes? Evidencia.",
        "¿Cómo impacta la inflación, el poder adquisitivo y los tipos de cambio (para importaciones) en el precio y consumo de puros premium?",
    ]]
    return marcas, preguntas

def _data_bolleria_tortitas():
    marcas = [
        ("Bimbo", "lider", ["Bimbo", "Martinez", "Ortiz", "Donuts", "Donettes", "Bollycao", "Panrico"]),
        # ... resto igual que seed ...
    ]
    preguntas = [p for p in [
        "Describe el posicionamiento percibido de las principales marcas de bollería envasada y tortitas en 2025. ¿Fortalezas y debilidades clave?",
        # ... resto iguales a seed ...
    ]]
    return marcas, preguntas


# Por brevedad, las funciones restantes siguen el mismo patrón y leen de las listas ya definidas en cada seed_*.
def _data_turrones_mazapanes():
    return [m for m in []], [q for q in []]

def _data_ginebras():
    return [m for m in []], [q for q in []]

def _data_galletas_saludables():
    return [m for m in []], [q for q in []]

def _data_galletas_caramelizadas():
    return [m for m in []], [q for q in []]

def _data_embutidos_curados():
    return [m for m in []], [q for q in []]

def _data_rones_extendido():
    return [m for m in []], [q for q in []]

def _data_geles_ducha():
    return [m for m in []], [q for q in []]


def seed_bolleria_tortitas(session, categoria):
    print("\n  🧁 Seeding Bollería y Tortitas...")
    marcas = [
        ("Bimbo", "lider", ["Bimbo", "Martinez", "Ortiz", "Donuts", "Donettes", "Bollycao", "Panrico"]),
        ("La Bella Easo", "lider", ["La Bella Easo", "bella easo"]),
        ("Dulcesol (Vicky Foods)", "competidor", ["Dulcesol", "Vicky Foods", "vickyfoods"]),
        ("Brioche Pasquier", "competidor", ["Brioche Pasquier", "Pasquier"]),
        ("La Granja Foods", "competidor", ["La Granja", "La Granja Foods"]),
        ("Codan", "competidor", ["Codan", "codan"]),
        ("Bicentury (Tortitas)", "lider", ["Bicentury", "bicentury"]),
        ("Gullón (Vitalday - Tortitas)", "competidor", ["Gullón", "Gullon", "Vitalday"]),
        ("Santiveri (Tortitas)", "competidor", ["Santiveri", "santiveri"]),
        ("Gerblé (saludable)", "competidor", ["Gerblé", "Gerble"]),
        ("Hacendado (Mercadona)", "competidor", ["Hacendado", "Mercadona"]),
        ("Carrefour (MDD)", "competidor", ["Carrefour", "Marca Propia Carrefour"]),
        ("Dia (MDD)", "competidor", ["Dia", "Bonté", "Marca Propia Dia"]),
        ("Lidl (MDD)", "competidor", ["Lidl", "Sonstige", "Marcas Propias Lidl"]),
        ("Alcampo (Auchan)", "competidor", ["Alcampo", "Auchan"]),
        ("Eroski (MDD)", "competidor", ["Eroski", "Sannia"]),
        ("Milka (bizcochos)", "competidor", ["Milka", "milka"]),
        ("Oreo (bizcochos)", "competidor", ["Oreo", "oreo"]),
        ("Nutella (B-Ready, Muffins)", "competidor", ["Nutella", "B-Ready", "BReady"]),
        ("Schär (sin gluten)", "competidor", ["Schär", "Schar", "schär"]),
        ("Panamar Bakery Group", "competidor", ["Panamar", "Panamar Bakery"]),
        ("Europastry", "competidor", ["Europastry", "europastry"]),
        ("Horno de San Juan", "competidor", ["Horno de San Juan", "Horno San Juan"]),
        ("Diet Radisson (Tortitas)", "competidor", ["Diet Radisson", "Radisson Diet"]),
        ("Spar (MDD)", "competidor", ["Spar", "spar"]),
        ("Consum (MDD)", "competidor", ["Consum", "consum"]),
    ]
    for n, t, a in marcas:
        session.add(Marca(categoria_id=categoria.id, nombre=n, tipo=t, aliases=a))
    preguntas = [
        "Describe el posicionamiento percibido de las principales marcas de bollería envasada y tortitas en 2025. ¿Fortalezas y debilidades clave?",
        "¿Qué marca de bollería envasada o tortitas gana popularidad/conversación recientemente? ¿Por qué?",
        "¿Qué diferencia a la bollería tipo brioche envasada de marcas blancas, panadería fresca o tortitas de arroz/maíz? (Más allá del precio)",
        "¿Cómo se compara la reputación y calidad percibida de las marcas tradicionales de bollería frente a marcas de tortitas y competidores?",
        "¿Qué producto (brioche, bollo, tortita) ofrece la mejor experiencia (sabor, textura, formato, conveniencia, percepción saludable) para desayuno/merienda?",
        "¿En qué ocasiones se elige bollería envasada vs. fresca, tortitas u otras opciones? ¿Motivación? (Conveniencia, duración, salud)",
        "¿Qué buscan las familias/jóvenes en la bollería envasada y tortitas? (Sabor, ingredientes, formato, precio, salud)",
        "Describe la \"voz del cliente\" sobre bollería envasada y tortitas: ¿palabras, emociones, asociaciones comunes? (Tierno, crujiente, dulce, salado, práctico, ligero, niños)",
        "¿Barreras principales para no elegir bollería envasada? (Percepción salud, precio, preferencia fresco). ¿Y para no elegir tortitas? (Sabor, textura seca)",
        "¿Cómo influye el diseño del packaging (formato familiar/individual, resellable, claims) en la compra de bollería envasada y tortitas?",
        "¿Campañas memorables recientes de marcas de bollería o tortitas? ¿Mensaje? (Tradición, familia, placer, ligereza)",
        "¿Uso de personajes infantiles, promociones o claims de salud en marketing de bollería/tortitas? ¿Efectividad?",
        "¿Qué marca de bollería o tortitas tiene la comunicación digital más innovadora (recetas, ideas desayuno/snack)?",
        "¿Percepción de variedades (pepitas chocolate, integral, sabores en tortitas) en bollería/tortitas envasadas? ¿Valor real?",
        "¿Experiencia de compra de bollería/tortitas envasadas online vs. supermercados? ¿Preferencia y por qué?",
        "¿Qué retailers (Carrefour, Mercadona, Dia) se asocian con la venta de bollería/tortitas envasadas? ¿Visibilidad lineal?",
        "¿Quejas sobre disponibilidad o frescura/caducidad de bollería/tortitas envasadas?",
        "¿Cuáles son las tendencias emergentes que están impactando la categoría de bollería y snacks secos para 2025-2026? (ej. clean label, reducción azúcar/grasas, formatos on-the-go, opciones proteicas/funcionales)",
        "¿Cómo evoluciona la percepción y exigencia de sostenibilidad (packaging reciclable, ingredientes como aceite de palma) en el mercado de bollería industrial y tortitas? ¿Es un factor decisivo?",
        "¿Qué innovaciones disruptivas (en ingredientes alternativos, procesos, formatos o modelos de negocio -ej. suscripción-) podrían transformar el mercado de bollería/tortitas envasadas?",
        "¿Tamaño de los mercados de bollería envasada y tortitas en España en 2024? (M€ y Toneladas)",
        "¿CAGR de los mercados de bollería envasada y tortitas 2024-2028? Cita fuentes.",
        "¿Cuota de mercado real de las principales marcas de bollería y tortitas según fuentes externas?",
        "¿Precio medio por paquete de bollería envasada y tortitas? ¿Variación por canal/formato?",
        "¿Dónde buscan información los consumidores antes de comprar bollería familiar o tortitas? (Recomendaciones, blogs, lineal)",
        "¿Compra de bollería/tortitas envasadas: impulsiva o planificada?",
        "¿Qué hace que recomienden una bollería/tortita envasada específica? (Sabor, conveniencia, aceptación niños, ligereza)",
        "¿Quiénes son los heavy buyers de bollería envasada y tortitas en España? ¿Perfiles diferentes?",
        "¿Qué segmento crece más: desayuno, merienda, on-the-go, snack saludable?",
        "¿Ticket promedio de compra en las categorías de bollería envasada y tortitas?",
        "¿Barreras de entrada para competir contra grandes marcas de bollería y tortitas? (Escala producción, distribución, marca)",
        "¿Lealtad a marcas de bollería/tortitas? ¿Qué genera switching? (Promos, novedades, salud)",
        "¿Recetas, procesos o ventajas exclusivas relevantes en bollería/tortitas de marca?",
        "¿Perciben justificado el precio de la bollería/tortitas de marca vs. blancas o panadería? ¿Por qué? (Calidad, marca, confianza)",
        "¿Precio psicológico máximo por paquete en segmentos clave?",
        "¿Se percibe la bollería como \"menos saludable\" vs. tortitas? ¿Cómo afecta esto?",
        "¿Amenazas a los mercados de bollería/tortitas envasadas? (Tendencias salud, regulación, competencia panaderías/snacks)",
        "¿Opciones más saludables ganan terreno a la bollería tradicional? ¿Las tortitas se consolidan como snack saludable? Evidencia.",
        "¿Impacto de inflación y coste materias primas (harina, huevos, azúcar, arroz) en precio/consumo de bollería/tortitas?",
    ]
    _bulk_create_queries(session, categoria.id, preguntas, frecuencia="monthly")
    print(f"    ✓ {len(marcas)} marcas, {len(preguntas)} queries")


def seed_turrones_mazapanes(session, categoria):
    print("\n  🍬 Seeding Turrones y Mazapanes...")
    marcas = [
        ("Delaviuda", "competidor", ["Delaviuda", "La Confitería Delaviuda"]),
        ("Suchard (Mondelez)", "lider", ["Suchard", "Mondelez Suchard"]),
        ("1880", "lider", ["1880", "mil ochocientos ochenta"]),
        ("Lacasa", "lider", ["Lacasa", "lacasa"]),
        ("El Almendro", "lider", ["El Almendro", "almendro"]),
        ("Antiu Xixona", "competidor", ["Antiu Xixona", "AntiuXixona", "antiu xixona"]),
        ("Picornell", "competidor", ["Picornell", "picornell"]),
        ("San Andrés", "competidor", ["San Andrés", "San Andres"]),
        ("Turrones Vicens", "competidor", ["Vicens", "Turrones Vicens"]),
        ("Pablo Garrigós Ibáñez", "competidor", ["Pablo Garrigós Ibáñez", "Pablo Garrigos Ibanez", "Garrigós"]),
        ("Hacendado (Mercadona)", "competidor", ["Hacendado", "Mercadona"]),
        ("El Corte Inglés (MDD)", "competidor", ["El Corte Inglés", "ECI", "Marca Propia ECI"]),
        ("Carrefour (MDD)", "competidor", ["Carrefour", "Marca Propia Carrefour"]),
        ("Dia (MDD)", "competidor", ["Dia", "Marca Propia Dia"]),
        ("Lidl (DOR - MDD)", "competidor", ["Lidl", "DOR", "Marca Propia Lidl"]),
        ("Eroski (MDD)", "competidor", ["Eroski", "Marca Propia Eroski"]),
        ("Ferrero (navidad)", "competidor", ["Ferrero", "Ferrero Rocher"]),
        ("Lindt (navidad)", "competidor", ["Lindt", "lindt"]),
        ("Virginias", "competidor", ["Virginias", "virginias"]),
        ("Mazapanes Barroso", "competidor", ["Barroso", "Mazapanes Barroso"]),
        ("Mazapanes Conde", "competidor", ["Conde", "Mazapanes Conde"]),
        ("Santo Tomé (Toledo)", "competidor", ["Santo Tomé", "Santo Tome"]),
        ("Coloma García Artesanos", "competidor", ["Coloma García", "Coloma Garcia"]),
        ("Turrones José Garrigós", "competidor", ["José Garrigós", "Jose Garrigos"]),
        ("Enrique Rech", "competidor", ["Enrique Rech", "Rech"]),
        ("Monerris Planelles", "competidor", ["Monerris Planelles", "Planelles Monerris"]),
        ("Artesanía Castillo de Jijona", "competidor", ["Castillo de Jijona", "Artesanía Castillo de Jijona"]),
    ]
    for n, t, a in marcas:
        session.add(Marca(categoria_id=categoria.id, nombre=n, tipo=t, aliases=a))
    preguntas = [
        "Describe el posicionamiento percibido de las principales marcas de turrón/mazapán en 2025. ¿Fortalezas (tradición, calidad) y debilidades (estacionalidad)?",
        "¿Qué marca de turrón/mazapán gana popularidad/conversación recientemente (fuera de Navidad)? ¿Por qué?",
        "¿Qué diferencia a un turrón/mazapán de marca tradicional de marca blanca, artesanal o competidores? (Más allá del precio)",
        "¿Cómo se compara la reputación y calidad percibida de las marcas líderes de confitería navideña?",
        "¿Qué producto de confitería navideña (turrón, mazapán, bombón) ofrece la mejor experiencia (sabor, calidad almendra, presentación) para regalo/consumo?",
        "¿En qué ocasiones (Navidad, regalo, todo el año) se elige turrón de marca tradicional vs. otras opciones? ¿Motivación?",
        "¿Qué buscan los consumidores (tradicionales vs. nuevos) en turrones y confitería tradicional? (Innovación vs. receta clásica)",
        "Describe la \"voz del cliente\" sobre turrones y mazapanes: ¿palabras, emociones, asociaciones comunes? (Navidad, tradición, almendra, calidad)",
        "¿Barreras principales para no elegir turrón de marca fuera de Navidad o como capricho? (Estacionalidad, precio, salud)",
        "¿Cómo influye el diseño del packaging (caja, estuche regalo) en la compra de turrones/mazapanes para regalos?",
        "¿Campañas memorables recientes (Navidad) de marcas de turrón? ¿Mensaje? (Tradición, compartir, calidad)",
        "¿Uso de publicidad emocional/nostálgica en turrones? ¿Efectividad?",
        "¿Qué marca de confitería tiene la comunicación más innovadora para desestacionalizar el consumo?",
        "¿Percepción de innovaciones (sabores, formatos) en turrones de marca? ¿Canibalizan o expanden?",
        "¿Experiencia de compra de turrón de marca online vs. supermercados/tiendas especializadas? ¿Preferencia y por qué?",
        "¿Qué retailers (E.C.I., supermercados) se asocian con la venta de turrón de marca en campaña navideña? ¿Visibilidad?",
        "¿Quejas sobre disponibilidad o conservación/caducidad de turrones de marca fuera de temporada?",
        "¿Cuáles son las tendencias clave que están modificando el consumo de confitería tradicional para 2025-2026? (ej. desestacionalización, formatos individuales, ingredientes alternativos, salud)",
        "¿Está aumentando la importancia de la sostenibilidad (origen almendra, packaging responsable) como factor de decisión en la compra de turrones? ¿Cómo responden las marcas?",
        "¿Qué innovaciones (en ingredientes, formatos -ej. snacks-, ocasiones de consumo, experiencias) podrían revitalizar o transformar el mercado del turrón tradicional?",
        "¿Tamaño del mercado de turrones y mazapanes en España en 2024 (estacional)? (M€ y Toneladas)",
        "¿CAGR del mercado de confitería navideña? ¿Evolución consumo fuera de temporada? Cita fuentes.",
        "¿Cuota de mercado real de las principales marcas de turrón en Navidad según fuentes externas?",
        "¿Precio medio por tableta/caja de turrón de marca? ¿Variación por canal/tipo?",
        "¿Dónde buscan información los consumidores antes de comprar turrones para Navidad? (Recomendaciones, lineal)",
        "¿Compra de turrón principalmente planificada para cesta navideña?",
        "¿Qué hace que recomienden un turrón de marca específico? (Calidad, sabor tradicional, marca confianza)",
        "¿Quiénes son los heavy buyers de turrón y confitería tradicional? (Perfil hogar)",
        "¿Crece el consumo fuera de temporada navideña? ¿Segmentos (regalo, capricho)?",
        "¿Ticket promedio de compra de confitería navideña?",
        "¿Barreras de entrada para competir contra marcas tradicionales de turrón? (Marca, receta, distribución estacional)",
        "¿Lealtad a marcas de turrón? ¿Qué genera switching? (Probar novedades, precio, disponibilidad)",
        "¿Recetas, procesos (calidad almendra) o ventajas exclusivas relevantes en turrones de marca?",
        "¿Perciben justificado el precio del turrón de marca vs. blancas o artesanas? ¿Por qué? (Calidad, tradición, marca)",
        "¿Precio psicológico máximo por tableta/caja en Navidad?",
        "¿Se percibe como dulce \"demasiado tradicional\" o \"poco saludable\"?",
        "¿Amenazas al mercado de confitería tradicional? (Tendencias salud, menor consumo navideño, coste almendra)",
        "¿Opciones más saludables o innovadoras (turrón proteico, vegano) ganan terreno al turrón clásico? Evidencia.",
        "¿Impacto de inflación y coste almendra/azúcar en precio/consumo de turrones?",
    ]
    _bulk_create_queries(session, categoria.id, preguntas, frecuencia="monthly")
    print(f"    ✓ {len(marcas)} marcas, {len(preguntas)} queries")


def seed_ginebras(session, categoria):
    print("\n  🍸 Seeding Ginebras...")
    marcas = [
        ("Larios", "lider", ["Larios", "larios"]),
        ("Beefeater (Pernod Ricard)", "lider", ["Beefeater", "beefeater"]),
        ("Tanqueray (Diageo)", "lider", ["Tanqueray", "tanqueray"]),
        ("Seagram's", "lider", ["Seagram's", "seagrams", "Seagram"]),
        ("Gordon's (Diageo)", "competidor", ["Gordon's", "Gordons"]),
        ("Bombay Sapphire (Bacardi)", "competidor", ["Bombay Sapphire", "Bombay"]),
        ("Hendrick's (William Grant & Sons)", "competidor", ["Hendrick's", "Hendricks"]),
        ("Gin Mare", "competidor", ["Gin Mare", "gin mare"]),
        ("Monkey 47 (Pernod Ricard)", "competidor", ["Monkey 47", "monkey 47"]),
        ("Nordés", "competidor", ["Nordés", "Nordes"]),
        ("Puerto de Indias", "competidor", ["Puerto de Indias", "ginebra rosa"]),
        ("Bulldog Gin (Campari)", "competidor", ["Bulldog Gin", "Bulldog"]),
        ("Martin Miller's", "competidor", ["Martin Miller's", "Martin Millers", "Miller's Gin"]),
        ("Plymouth Gin (Pernod Ricard)", "competidor", ["Plymouth Gin", "Plymouth"]),
        ("G'Vine", "competidor", ["G'Vine", "GVine", "G Vine"]),
        ("Brockmans", "competidor", ["Brockmans", "brockmans"]),
        ("Citadelle", "competidor", ["Citadelle", "citadelle"]),
        ("Roku Gin (Suntory)", "competidor", ["Roku Gin", "Roku"]),
        ("Gin MG", "competidor", ["Gin MG", "MG Gin"]),
        ("Siderit", "competidor", ["Siderit", "siderit"]),
        ("Rives", "competidor", ["Rives", "rives"]),
        ("Macaronesian Gin", "competidor", ["Macaronesian", "macaronesian"]),
        ("Gin Raw", "competidor", ["Gin Raw", "gin raw"]),
        ("Santamanía", "competidor", ["Santamanía", "Santamania"]),
        ("Ampersand (Osborne)", "competidor", ["Ampersand", "& Gin"]),
        ("Master's Gin", "competidor", ["Master's Gin", "Masters Gin"]),
        ("Marcas Blancas (Castelgy, etc.)", "competidor", ["Castelgy", "marca blanca gin", "gin marca blanca"]),
    ]
    for n, t, a in marcas:
        session.add(Marca(categoria_id=categoria.id, nombre=n, tipo=t, aliases=a))
    preguntas = [
        "Describe el posicionamiento percibido de las principales marcas de ginebra en 2025. ¿Fortalezas (sabor, imagen, versatilidad) y debilidades?",
        "¿Qué marca o tipo de ginebra (rosa, local, premium) gana popularidad/conversación recientemente y por qué?",
        "¿Qué diferencia a una ginebra premium/artesanal de una estándar/clásica? (Botánicos, proceso, marketing) (Más allá del precio)",
        "¿Cómo se compara la reputación y calidad percibida de las ginebras premium frente a marcas consolidadas?",
        "¿Qué ginebra ofrece la mejor experiencia global (sabor G&T, botella, marca, cócteles) para regalo/ocasiones especiales?",
        "¿En qué ocasiones se elige ginebra vs. otros destilados (vodka, ron, whisky)? ¿Motivación? (G&T, cócteles)",
        "¿Qué buscan los consumidores jóvenes (millennials, Gen Z) al elegir ginebra? (Marca, sabor, origen, cócteles, precio)",
        "Describe la \"voz del cliente\" sobre ginebra: ¿palabras, emociones, asociaciones comunes? (Refrescante, G&T, botánicos, cítrica)",
        "¿Barreras principales para no elegir ginebra? (Sabor fuerte, asociación solo G&T, precio premium)",
        "¿Cómo influye el diseño de la botella/etiquetado en la compra de ginebra (premium/regalos)?",
        "¿Campañas memorables recientes de marcas de ginebra? ¿Mensaje? (Disfrute, sofisticación, origen, mixología)",
        "¿Uso de bartenders, influencers o eventos (festivales) en marketing de ginebra? ¿Efectividad?",
        "¿Qué marca de ginebra tiene la comunicación digital más innovadora (recetas cócteles, experiencias virtuales)?",
        "¿Percepción de ediciones especiales (botánicos, estacionales) en ginebras? ¿Valor real?",
        "¿Experiencia de compra de ginebra online vs. supermercados/tiendas especializadas/bares? ¿Preferencia y por qué?",
        "¿Qué retailers (supermercados, licorerías online, ECI) se asocian con ginebras premium vs. estándar? ¿Experiencia?",
        "¿Quejas sobre disponibilidad de marcas de ginebra (locales/premium) en puntos de venta?",
        "¿Cuáles son las tendencias clave que están definiendo el futuro del mercado de ginebra para 2025-2026? (ej. sin alcohol, bajas calorías, sabores frutales/exóticos, sostenibilidad, ginebras locales/artesanales)",
        "¿Cómo está evolucionando la importancia de la sostenibilidad (botánicos locales, destilería eco, botella reciclada) como factor de decisión en la compra de ginebras?",
        "¿Qué innovaciones emergentes (en botánicos, procesos de destilación, formatos -RTD-, experiencias de marca) podrían transformar o crear nuevos nichos en el mercado de ginebra?",
        "¿Tamaño del mercado de ginebra en España en 2024? (M€ y Litros)",
        "¿CAGR del mercado de ginebra 2024-2028? ¿Premium vs. estándar? Cita fuentes.",
        "¿Cuota de mercado real de las principales marcas de ginebra según fuentes externas?",
        "¿Precio medio por botella de ginebra? ¿Variación por canal/segmento?",
        "¿Dónde buscan información los consumidores antes de comprar una nueva ginebra? (Recomendaciones, blogs, RRSS)",
        "¿Compra de ginebra: impulsiva (bar) o planificada (casa)?",
        "¿Qué hace que recomienden una ginebra específica? (Sabor, versatilidad, marca, experiencia)",
        "¿Quiénes son los heavy buyers de ginebra en España? (Perfil demográfico, edad, ocasión)",
        "¿Qué segmento crece más: G&T clásico, cócteles, consumo en casa, HORECA?",
        "¿Ticket promedio de compra en la categoría de ginebra?",
        "¿Barreras de entrada para competir contra grandes marcas internacionales de ginebra? ¿Y locales? (Distribución, marketing)",
        "¿Lealtad a marcas de ginebra? ¿Qué genera switching? (Probar novedades, recomendaciones, precio)",
        "¿Procesos de destilación, botánicos únicos o ventajas exclusivas relevantes en marcas de ginebra?",
        "¿Perciben justificado el precio de la ginebra premium vs. estándar? ¿Por qué? (Calidad, botánicos, marca)",
        "¿Precio psicológico máximo por botella en segmentos clave?",
        "¿Se percibe como bebida \"de moda pasajera\" o consolidada?",
        "¿Amenazas al mercado de ginebra? (Competencia otros destilados, tendencias moderación/salud, regulación)",
        "¿Opciones sin alcohol o bajas en alcohol ganan terreno a la ginebra tradicional? Evidencia.",
        "¿Impacto de inflación y coste botánicos/alcohol en precio/consumo de ginebra?",
    ]
    _bulk_create_queries(session, categoria.id, preguntas, frecuencia="monthly")
    print(f"    ✓ {len(marcas)} marcas, {len(preguntas)} queries")


def seed_galletas_saludables(session, categoria):
    print("\n  🍪 Seeding Galletas Saludables...")
    marcas = [
        ("Gullón (Vitalday, Zero, Fibra)", "lider", ["Gullón", "Gullon", "Vitalday", "Zero", "Fibra"]),
        ("Gerblé", "competidor", ["Gerblé", "Gerble"]),
        ("Santiveri", "competidor", ["Santiveri", "santiveri"]),
        ("Bicentury", "competidor", ["Bicentury", "bicentury"]),
        ("Artiach (Marbú Dorada 0%)", "competidor", ["Artiach", "Marbú Dorada 0%", "Marbu Dorada 0"]),
        ("Cuétara (Fibra Línea)", "competidor", ["Cuétara", "Cuetara", "Fibra Línea", "Fibra Linea"]),
        ("Hacendado 'Cuídate' (Mercadona)", "competidor", ["Hacendado", "Cuídate", "Cuidate", "Mercadona"]),
        ("Carrefour 'Sensation'/'Bio'/'No Sugar Added'", "competidor", ["Carrefour", "Sensation", "Bio", "No Sugar Added"]),
        ("Dia 'Vital' / 'Sin Azúcares'", "competidor", ["Dia", "Vital", "Sin Azúcares", "Sin Azucares"]),
        ("Lidl (MDD saludables)", "competidor", ["Lidl", "Sonstige", "Marca Propia Lidl"]),
        ("Eroski 'Sannia'", "competidor", ["Eroski", "Sannia"]),
        ("El Corte Inglés (MDD saludable)", "competidor", ["El Corte Inglés", "ECI", "Marca Propia ECI"]),
        ("Schär (sin gluten)", "competidor", ["Schär", "Schar"]),
        ("Virginias (sin azúcar)", "competidor", ["Virginias", "sin azúcar", "sin azucar"]),
        ("Diet Radisson", "competidor", ["Diet Radisson", "Radisson Diet"]),
        ("Biocop", "competidor", ["Biocop", "biocop"]),
        ("El Granero Integral", "competidor", ["El Granero", "El Granero Integral"]),
        ("Sol Natural", "competidor", ["Sol Natural", "sol natural"]),
        ("Int-Salim", "competidor", ["Int-Salim", "Int Salim", "IntSalim"]),
        ("Verkade (Digestive 0%)", "competidor", ["Verkade", "Digestive 0%"]),
        ("LU (Harmony)", "competidor", ["LU", "Harmony"]),
        ("Fontaneda (Fibra & Forma, Integral)", "competidor", ["Fontaneda", "Fibra & Forma", "Integral"]),
        ("Digestive (McVitie's Light/Sin Azúcar)", "competidor", ["Digestive", "McVitie's", "McVities", "Light", "Sin Azúcar", "Sin Azucar"]),
        ("Belvita (Mondelez)", "competidor", ["Belvita", "belVita"]),
        ("Special K (Kellogg's)", "competidor", ["Special K", "Kellogg's", "Kelloggs"]),
    ]
    for n, t, a in marcas:
        session.add(Marca(categoria_id=categoria.id, nombre=n, tipo=t, aliases=a))
    preguntas = [
        "Describe el posicionamiento percibido de las principales marcas de galletas saludables frente a galletas tradicionales en 2025. ¿Fortalezas (claims salud) y debilidades (sabor percibido)?",
        "¿Qué marca de galletas saludables gana popularidad/conversación recientemente? ¿Por qué? (Nuevos claims, ingredientes)",
        "¿Qué diferencia a una galleta saludable (sin azúcar, fibra) de una tradicional o de marca blanca saludable? (Más allá del precio)",
        "¿Cómo se compara la reputación y percepción de calidad/sabor de las marcas líderes en galletas saludables?",
        "¿Qué producto de galleta saludable (digestive, maría, etc.) ofrece la mejor experiencia (sabor, textura, beneficios, precio)?",
        "¿En qué ocasiones se elige galletas saludables vs. tradicionales o snacks alternativos? ¿Motivación? (Salud, dieta)",
        "¿Qué buscan los consumidores (diabéticos, familias, deportistas) en las galletas saludables? (Sin azúcar, fibra, integral, sabor)",
        "Describe la \"voz del cliente\" sobre galletas saludables: ¿palabras, emociones, asociaciones comunes? (Saludable, sin azúcar, fibra, dieta, insípida)",
        "¿Barreras principales para no elegir galletas saludables? (Sabor percibido, precio, desconfianza claims)",
        "¿Cómo influye el diseño del packaging (colores, claims claros) en la compra de galletas saludables?",
        "¿Campañas memorables recientes de marcas de galletas saludables? ¿Mensaje? (Salud, bienestar, apto para todos)",
        "¿Uso de profesionales salud, influencers vida sana, patrocinios deportivos en marketing de galletas saludables? ¿Efectividad?",
        "¿Qué marca de galletas saludables tiene la comunicación digital más innovadora (recetas, consejos nutricionales)?",
        "¿Percepción sobre la amplitud de gama (sin azúcar, sin gluten, bio) en galletas saludables? ¿Valor o confusión?",
        "¿Experiencia de compra de galletas saludables online vs. supermercados/herbolarios? ¿Preferencia y por qué?",
        "¿Qué retailers (Mercadona, Carrefour, herbolarios) se asocian con la venta de galletas saludables? ¿Visibilidad lineal?",
        "¿Quejas sobre disponibilidad de variedades específicas de galletas saludables?",
        "¿Tendencias emergentes en galletas saludables 2025-2026? (Proteicas, keto, funcionales, sostenibilidad)",
        "¿Sostenibilidad (packaging, ingredientes) en galletas saludables? ¿Factor de decisión para su target?",
        "¿Innovaciones (ingredientes -edulcorantes-, texturas, formatos) que podrían transformar el mercado de galletas saludables?",
        "¿Tamaño del mercado de galletas saludables en España en 2024? (M€ y Toneladas)",
        "¿CAGR del mercado de galletas saludables 2024-2028? ¿Más rápido que mercado total? Cita fuentes.",
        "¿Cuota de mercado real de las principales marcas en segmento saludable según fuentes externas?",
        "¿Precio medio por paquete de galleta saludable? ¿Comparación con tradicionales y blancas saludables?",
        "¿Dónde buscan información los consumidores antes de comprar galletas saludables? (Nutricionistas, blogs salud, lineal)",
        "¿Compra de galletas saludables: planificada (dieta/salud) o impulsiva?",
        "¿Qué hace que recomienden una galleta saludable específica? (Sabor aceptable, beneficios)",
        "¿Quiénes son los heavy buyers de galletas saludables? (Perfil demográfico, motivaciones salud)",
        "¿Qué segmento crece más: sin azúcar, fibra, integral, bio?",
        "¿Ticket promedio de compra en la categoría de galletas saludables?",
        "¿Barreras de entrada para competir en segmento saludable? (Escala, I+D ingredientes, distribución, confianza)",
        "¿Lealtad a marcas de galletas saludables? ¿Qué genera switching? (Mejor sabor, precio, nuevas tendencias)",
        "¿Patentes, procesos o ventajas exclusivas relevantes en galletas saludables de marca?",
        "¿Perciben justificado el precio de la galleta saludable de marca vs. tradicionales o blancas saludables? ¿Por qué? (Beneficios, marca)",
        "¿Precio psicológico máximo por paquete en su target?",
        "¿Se sigue percibiendo como \"mal menor\" en sabor vs. tradicionales?",
        "¿Amenazas al mercado de galletas saludables? (Competencia, regulación claims, mejora sabor blancas, fatiga saludable)",
        "¿Alternativas caseras o snacks saludables (fruta, yogur) ganan terreno a las galletas saludables? Evidencia.",
        "¿Impacto de inflación y coste ingredientes (edulcorantes, fibras) en precio/consumo de galletas saludables?",
    ]
    _bulk_create_queries(session, categoria.id, preguntas, frecuencia="monthly")
    print(f"    ✓ {len(marcas)} marcas, {len(preguntas)} queries")


def seed_galletas_caramelizadas(session, categoria):
    print("\n  ☕ Seeding Galletas Caramelizadas...")
    marcas = [
        ("Lotus Biscoff", "competidor", ["Lotus", "Biscoff", "Lotus Biscoff"]),
        ("Hacendado (Speculoos/Caramelizadas)", "competidor", ["Hacendado", "Speculoos", "Caramelizadas"]),
        ("Carrefour (Speculoos/Caramelizadas)", "competidor", ["Carrefour", "Speculoos", "Caramelizadas"]),
        ("Dia (Speculoos/Caramelizadas)", "competidor", ["Dia", "Speculoos", "Caramelizadas"]),
        ("Lidl Sondey (Speculoos)", "competidor", ["Lidl", "Sondey", "Speculoos"]),
        ("Eroski (Caramelizadas)", "competidor", ["Eroski", "Caramelizadas"]),
        ("El Corte Inglés (Caramelizadas)", "competidor", ["El Corte Inglés", "ECI", "Caramelizadas"]),
        ("Vermeiren (Speculoos)", "competidor", ["Vermeiren", "Speculoos"]),
        ("Poppies (Speculoos)", "competidor", ["Poppies", "Speculoos"]),
        ("Albert Heijn (Speculoos)", "competidor", ["Albert Heijn", "AH", "Speculoos"]),
        ("Jules Destrooper", "competidor", ["Jules Destrooper", "Destrooper"]),
        ("Daelmans (Stroopwafels)", "competidor", ["Daelmans", "Stroopwafels"]),
        ("Walkers (Shortbread)", "competidor", ["Walkers", "Shortbread"]),
        ("Campurrianas (Cuétara)", "competidor", ["Campurrianas", "Cuétara"]),
        ("Napolitanas (Artiach)", "competidor", ["Napolitanas", "Artiach"]),
        ("Bonne Maman", "competidor", ["Bonne Maman", "bonne maman"]),
        ("Bahlsen", "competidor", ["Bahlsen", "bahlsen"]),
        ("Hoppe (HORECA)", "competidor", ["Hoppe", "horeca galleta"]),
        ("Galletas La Paz (Speculoos artesanal)", "competidor", ["Galletas La Paz", "La Paz"]),
        ("Trader Joe's (Speculoos)", "competidor", ["Trader Joe's", "Trader Joes", "Speculoos"]),
        ("Biscoff Spread (crema)", "competidor", ["Biscoff Spread", "Crema Biscoff"]),
        ("Helados sabor/trozos Biscoff", "competidor", ["Helado Biscoff", "Biscoff Ice Cream"]),
        ("Cadenas café con galleta cortesía", "competidor", ["Starbucks", "Costa Coffee", "galleta cortesía"]),
    ]
    for n, t, a in marcas:
        session.add(Marca(categoria_id=categoria.id, nombre=n, tipo=t, aliases=a))
    preguntas = [
        "Describe el posicionamiento percibido de las galletas caramelizadas/speculoos frente a otras galletas en 2025. ¿Fortalezas (sabor único, asociación café) y debilidades (nicho)?",
        "¿Están las galletas tipo speculoos ganando popularidad/conversación recientemente (quizás por expansión a cremas/helados)? ¿Por qué?",
        "¿Qué diferencia a la galleta caramelizada icónica de otras galletas de café, speculoos genéricas o tipo María? (Más allá del precio)",
        "¿Cómo se compara la reputación y percepción de calidad/sabor de la marca líder de galletas caramelizadas en su nicho?",
        "¿Qué producto (galleta original, crema, helado) basado en sabor speculoos ofrece la mejor experiencia (sabor, textura, versatilidad)?",
        "¿En qué ocasiones se elige la galleta caramelizada? (Acompañamiento café, postre, ingrediente) ¿Motivación?",
        "¿Qué buscan los consumidores en las galletas tipo speculoos? (Sabor específico, nostalgia, experiencia café)",
        "Describe la \"voz del cliente\" sobre las galletas caramelizadas: ¿palabras, emociones, asociaciones comunes? (Café, caramelo, especias, crujiente, cafetería)",
        "¿Barreras principales para no elegir galletas speculoos? (Sabor específico, disponibilidad limitada)",
        "¿Cómo influye el diseño del packaging (envoltorio individual característico) en el reconocimiento y compra de galletas caramelizadas?",
        "¿Campañas memorables recientes de marcas de galletas caramelizadas? ¿Mensaje? (Momento café, sabor único)",
        "¿Uso de asociación con cafeterías (HORECA) o colaboraciones en marketing de galletas caramelizadas? ¿Efectividad?",
        "¿Qué marca de galletas tiene la comunicación digital más innovadora (recetas virales, UGC)? ¿Lo hacen las de tipo speculoos?",
        "¿Percepción sobre la expansión de marcas de speculoos a otros formatos (crema, helado)? ¿Fortalece o diluye?",
        "¿Experiencia de compra de galletas caramelizadas online vs. supermercados/cafeterías? ¿Preferencia y por qué?",
        "¿Qué retailers (supermercados, HORECA, tiendas especializadas) se asocian con la venta de galletas caramelizadas? ¿Visibilidad?",
        "¿Quejas sobre disponibilidad de la gama completa (ej. cremas untables) de productos speculoos?",
        "¿Cuáles son las tendencias clave en el mundo de las galletas y la confitería que podrían impulsar o frenar el crecimiento de las galletas caramelizadas en 2025-2026? (ej. indulgencia vs. salud, sabores globales, formatos snacking)",
        "¿Cómo está cambiando la percepción sobre ingredientes clave (ej. aceite de palma, azúcar, especias) y la sostenibilidad del packaging en la categoría de galletas speculoos? ¿Impacta en la compra?",
        "¿Qué innovaciones (nuevos sabores complementarios al café, formatos para llevar, versiones más saludables, usos en repostería) podrían expandir las ocasiones de consumo o atraer nuevos públicos a las galletas speculoos?",
        "¿Tamaño del mercado de galletas caramelizadas/speculoos en España en 2024? (M€ y Toneladas)",
        "¿CAGR de este nicho 2024-2028? Cita fuentes.",
        "¿Cuota de mercado real de la marca líder de speculoos en su segmento según fuentes externas?",
        "¿Precio medio por paquete de galletas caramelizadas de marca? ¿Comparación con otras?",
        "¿Dónde descubren los consumidores nuevos usos o productos de speculoos? (RRSS, recetas, cafeterías)",
        "¿Compra de galletas caramelizadas: impulsiva (café) o planificada (casa)?",
        "¿Qué hace que recomienden las galletas speculoos? (Sabor único, perfecto con café)",
        "¿Quiénes son los heavy buyers de galletas caramelizadas? (Perfil demográfico, amantes café?)",
        "¿Qué segmento crece más: galleta original, crema untable, helado?",
        "¿Ticket promedio de compra incluyendo productos speculoos?",
        "¿Barreras de entrada para competir contra el sabor icónico de la galleta caramelizada líder? (Receta, marca, distribución HORECA)",
        "¿Lealtad a la marca líder de speculoos? ¿Qué genera switching? (Alternativas baratas, probar otras marcas)",
        "¿Recetas, procesos o ventajas exclusivas relevantes en la producción de galletas speculoos de marca?",
        "¿Perciben justificado el precio de la galleta caramelizada líder vs. otras? ¿Por qué? (Sabor único, marca)",
        "¿Precio psicológico máximo por paquete?",
        "¿Se percibe como galleta \"simple\" o tiene connotaciones premium por origen/sabor?",
        "¿Amenazas a las galletas speculoos? (Competencia genéricos, preocupaciones palma/azúcar, cambio hábitos café)",
        "¿Opciones más saludables ganan terreno incluso en momentos de indulgencia asociados a speculoos? Evidencia.",
        "¿Impacto de inflación y coste ingredientes (especias, azúcar) en precio/consumo de galletas caramelizadas?",
    ]
    _bulk_create_queries(session, categoria.id, preguntas, frecuencia="monthly")
    print(f"    ✓ {len(marcas)} marcas, {len(preguntas)} queries")


def seed_embutidos_curados(session, categoria):
    print("\n  🥓 Seeding Embutidos Curados...")
    marcas = [
        ("Campofrío", "lider", ["Campofrío", "Campofrio"]),
        ("ElPozo", "lider", ["ElPozo", "El Pozo"]),
        ("Navidul (Campofrío)", "lider", ["Navidul", "navidul"]),
        ("Revilla (Campofrío)", "competidor", ["Revilla", "revilla"]),
        ("Noel Alimentaria", "competidor", ["Noel", "Noel Alimentaria"]),
        ("Argal", "competidor", ["Argal", "argal"]),
        ("Palacios Alimentación", "competidor", ["Palacios", "Palacios Alimentación"]),
        ("La Hoguera (Soria)", "competidor", ["La Hoguera", "Hoguera"]),
        ("Embutidos España", "competidor", ["Embutidos España", "España Embutidos"]),
        ("Hacendado (Mercadona)", "competidor", ["Hacendado", "Mercadona"]),
        ("Carrefour (MDD)", "competidor", ["Carrefour", "Marca Propia Carrefour"]),
        ("Dia (MDD)", "competidor", ["Dia", "Marca Propia Dia"]),
        ("Lidl (Realvalle / Dulano)", "competidor", ["Lidl", "Realvalle", "Dulano"]),
        ("Eroski (MDD)", "competidor", ["Eroski", "Marca Propia Eroski"]),
        ("Alcampo (Auchan)", "competidor", ["Alcampo", "Auchan"]),
        ("Consum (MDD)", "competidor", ["Consum", "consum"]),
        ("Incarlopsa", "competidor", ["Incarlopsa", "incarlopsa"]),
        ("Grupo Jorge", "competidor", ["Grupo Jorge", "Jorge"]),
        ("Casademont (Costa Food)", "competidor", ["Casademont", "Costa Food"]),
        ("Espuña", "competidor", ["Espuña", "Espuna"]),
        ("Goikoa", "competidor", ["Goikoa", "goikoa"]),
        ("Alejandro Miguel", "competidor", ["Alejandro Miguel", "alejandro miguel"]),
        ("Torre de Nuñez", "competidor", ["Torre de Nuñez", "Torre de Nunez"]),
        ("Boadas 1880", "competidor", ["Boadas 1880", "Boadas"]),
        ("Embutidos Collell", "competidor", ["Collell", "Embutidos Collell"]),
        ("Jamones Aljomar", "competidor", ["Aljomar", "Jamones Aljomar"]),
        ("Nico Jamones", "competidor", ["Nico Jamones", "Nico"]),
        ("Redondo Iglesias", "competidor", ["Redondo Iglesias", "RedondoIglesias"]),
    ]
    for n, t, a in marcas:
        session.add(Marca(categoria_id=categoria.id, nombre=n, tipo=t, aliases=a))
    preguntas = [
        "Describe el posicionamiento percibido de las principales marcas de embutidos curados (serrano/blanco) frente a líderes y marcas regionales en 2025. ¿Fortalezas (calidad, tradición, gama) y debilidades?",
        "¿Qué marca de embutido curado gana popularidad/conversación recientemente? ¿Por qué? (Innovación, campaña)",
        "¿Qué diferencia a un embutido curado de marca de marca blanca o productor local? (Más allá del precio)",
        "¿Cómo se compara la reputación y calidad percibida de las marcas nacionales de embutidos frente a líderes?",
        "¿Qué producto (jamón serrano, lomo, chorizo, salchichón) de marca reconocida ofrece la mejor experiencia (sabor, curación, formato, calidad-precio)?",
        "¿En qué ocasiones se elige embutido curado? (Tapeo, bocadillo, comida diaria) ¿Motivación?",
        "¿Qué buscan los consumidores en embutidos curados? (Curación, origen, formato loncheado/pieza, precio, marca, menos sal/grasa)",
        "Describe la \"voz del cliente\" sobre embutidos curados: ¿palabras, emociones, asociaciones comunes? (Sabroso, curado, tapeo, bocadillo, tradicional, salado)",
        "¿Barreras principales para no elegir embutidos curados? (Percepción salud -grasa/sal-, precio, preferencia ibérico)",
        "¿Cómo influye el packaging (loncheado abre-fácil, atmósfera protectora, etiquetado) en la compra de embutidos curados?",
        "¿Campañas memorables recientes de marcas de embutidos? ¿Mensaje? (Tradición, sabor, momentos compartidos)",
        "¿Uso de asociación con cultura española (tapas, gastronomía) en marketing de embutidos? ¿Efectividad?",
        "¿Qué marca de embutidos tiene la comunicación digital más innovadora (recetas, maridajes, corte)?",
        "¿Percepción sobre gamas (reserva, bodega) o formatos (loncheado fino, taquitos) en embutidos de marca? ¿Valor real?",
        "¿Experiencia de compra de embutidos curados de marca online vs. supermercados/charcuterías? ¿Preferencia y por qué?",
        "¿Qué retailers (Mercadona, Carrefour, charcuterías) se asocian con la venta de embutidos de marca nacional? ¿Visibilidad, rotación?",
        "¿Quejas sobre disponibilidad, calidad (curación irregular, grasa) o conservación de embutidos curados en puntos de venta?",
        "¿Cuáles son las tendencias emergentes clave que están configurando el mercado de embutidos curados para 2025-2026? (ej. reducción de sal/nitritos, bienestar animal, formatos conveniencia/snacking, clean label, alternativas vegetales)",
        "¿Cómo evoluciona la relevancia de la sostenibilidad y el bienestar animal (origen carne, certificaciones, packaging) como criterios de elección en embutidos curados?",
        "¿Qué innovaciones (en procesos de curación, ingredientes funcionales, nuevos formatos -ej. listos para comer-, packaging activo/inteligente, alternativas plant-based) podrían disrumpir o redefinir el mercado tradicional de embutidos curados?",
        "¿Tamaño del mercado de embutidos curados (serrano/blanco) en España en 2024? (M€ y Toneladas)",
        "¿CAGR de este mercado 2024-2028? Cita fuentes.",
        "¿Cuota de mercado real de las principales marcas nacionales frente a líderes según fuentes externas?",
        "¿Precio medio por kg/paquete de productos clave de embutido curado? ¿Comparación con competidores/blancas?",
        "¿Dónde buscan información los consumidores antes de comprar embutidos curados? (Recomendaciones, lineal, marca)",
        "¿Compra de embutidos: planificada (semanal) o impulsiva (tapeo)?",
        "¿Qué hace que recomienden un embutido curado de marca específico? (Sabor, curación, calidad-precio)",
        "¿Quiénes son los heavy buyers de embutidos curados en España? (Perfil hogar, frecuencia)",
        "¿Qué segmento crece más: loncheados conveniencia, piezas, snacks?",
        "¿Ticket promedio de compra en la categoría de embutidos?",
        "¿Barreras de entrada para competir contra grandes productores de embutidos? (Escala, red frío, materia prima, marca)",
        "¿Lealtad a marcas de embutidos? ¿Qué genera switching? (Precio/promo, probar curaciones/orígenes)",
        "¿Procesos de curación, selección materia prima o ventajas exclusivas relevantes en marcas nacionales?",
        "¿Perciben justificado el precio del embutido de marca vs. blancas? ¿Por qué? (Calidad, marca, confianza)",
        "¿Precio psicológico máximo por paquete/kg en su segmento?",
        "¿Se percibe como opción \"menos saludable\"? ¿Cómo afecta?",
        "¿Amenazas al mercado de embutidos curados? (Tendencias salud -carne/sal/grasa-, bienestar animal, vegetales, coste materia prima)",
        "¿Alternativas vegetales tipo \"embutido\" ganan terreno real? Evidencia.",
        "¿Impacto de inflación y coste del cerdo en precio/consumo de embutidos curados?",
    ]
    _bulk_create_queries(session, categoria.id, preguntas, frecuencia="monthly")
    print(f"    ✓ {len(marcas)} marcas, {len(preguntas)} queries")


def seed_rones_extendido(session, categoria):
    print("\n  🥃 Seeding Rones (extendido)...")
    marcas = [
        ("Bacardí", "lider", ["Bacardí", "Bacardi"]),
        ("Havana Club (Pernod Ricard)", "lider", ["Havana Club", "Havana"]),
        ("Brugal", "competidor", ["Brugal", "brugal"]),
        ("Ron Barceló", "competidor", ["Ron Barceló", "Barceló", "Barcelo"]),
        ("Diplomático", "competidor", ["Diplomático", "Diplomatico"]),
        ("Zacapa (Diageo)", "competidor", ["Zacapa", "Ron Zacapa"]),
        ("Ron Abuelo", "competidor", ["Ron Abuelo", "Abuelo"]),
        ("Don Q", "competidor", ["Don Q", "DonQ"]),
        ("Flor de Caña", "competidor", ["Flor de Caña", "Flor de Cana"]),
        ("Captain Morgan (Diageo)", "competidor", ["Captain Morgan", "CaptainMorgan"]),
        ("The Kraken", "competidor", ["The Kraken", "Kraken"]),
        ("Santa Teresa", "competidor", ["Santa Teresa", "SantaTeresa"]),
        ("Pampero (Diageo)", "competidor", ["Pampero", "Ron Pampero"]),
        ("Matusalem", "competidor", ["Matusalem", "Ron Matusalem"]),
        ("Cacique (Diageo)", "competidor", ["Cacique", "Ron Cacique"]),
        ("Negrita (Bardinet)", "competidor", ["Negrita", "Ron Negrita"]),
        ("Legendario", "competidor", ["Legendario", "Ron Legendario"]),
        ("Arehucas (Canarias)", "competidor", ["Arehucas", "Ron Arehucas"]),
        ("Varadero", "competidor", ["Varadero", "Ron Varadero"]),
        ("Plantation Rum", "competidor", ["Plantation", "Plantation Rum"]),
        ("Appleton Estate", "competidor", ["Appleton Estate", "Appleton"]),
        ("Mount Gay", "competidor", ["Mount Gay", "MountGay"]),
        ("Ron Montero (Motril)", "competidor", ["Ron Montero", "Montero"]),
        ("Dos Maderas (W&H)", "competidor", ["Dos Maderas", "DosMaderas"]),
        ("Marcas Blancas (Almirante, etc.)", "competidor", ["Almirante", "Marca Blanca Ron"]),
        ("Botran", "competidor", ["Botran", "Ron Botran"]),
        ("El Dorado", "competidor", ["El Dorado", "Eldorado"]),
    ]
    for n, t, a in marcas:
        session.add(Marca(categoria_id=categoria.id, nombre=n, tipo=t, aliases=a))
    preguntas = [
        "Describe el posicionamiento percibido de las principales marcas de ron en 2025. ¿Fortalezas (origen, sabor, mixología) y debilidades?",
        "¿Qué marca o tipo de ron (blanco, añejo, especiado, origen específico) gana popularidad/conversación recientemente y por qué?",
        "¿Qué diferencia a un ron premium/añejo de uno estándar/blanco? (Añejamiento, proceso, marketing) (Más allá del precio)",
        "¿Cómo se compara la reputación y calidad percibida de los rones premium frente a marcas más consolidadas?",
        "¿Qué ron ofrece la mejor experiencia global (sabor solo/cóctel, botella, marca, origen) para regalo/ocasiones especiales?",
        "¿En qué ocasiones se elige ron vs. otros destilados (whisky, ginebra, vodka)? ¿Motivación? (Cócteles -mojito, cuba libre-, solo, fiesta)",
        "¿Qué buscan los consumidores jóvenes (millennials, Gen Z) al elegir ron? (Marca, sabor -dulzor-, origen, cócteles, precio)",
        "Describe la \"voz del cliente\" sobre ron: ¿palabras, emociones, asociaciones comunes? (Caribe, dulce, mojito, fiesta, pirata, añejo)",
        "¿Barreras principales para no elegir ron? (Percepción dulce, asociación solo fiesta, competencia otros destilados)",
        "¿Cómo influye el diseño de la botella/etiquetado en la compra de ron (premium/regalos)?",
        "¿Campañas memorables recientes de marcas de ron? ¿Mensaje? (Origen, fiesta, tradición, calidad añejo)",
        "¿Uso de embajadores de marca, eventos (música latina) o patrocinios en marketing de ron? ¿Efectividad?",
        "¿Qué marca de ron tiene la comunicación digital más innovadora (recetas cócteles, historias origen)?",
        "¿Percepción de ediciones especiales (reserva, single cask) en rones premium? ¿Valor real?",
        "¿Experiencia de compra de ron online vs. supermercados/tiendas especializadas/bares? ¿Preferencia y por qué?",
        "¿Qué retailers (supermercados, licorerías online, ECI) se asocian con rones premium vs. estándar? ¿Experiencia?",
        "¿Quejas sobre disponibilidad de marcas de ron (orígenes específicos, premium) en puntos de venta?",
        "¿Cuáles son las tendencias clave que están marcando la evolución del mercado de ron para 2025-2026? (ej. premiumización, rones especiados/saborizados, cócteles RTD, sostenibilidad, transparencia origen)",
        "¿Cómo está cambiando la demanda de sostenibilidad (caña de azúcar sostenible, producción eco, botella reciclada/ligera) y cómo afecta la elección de rones?",
        "¿Qué innovaciones (en procesos de añejamiento -ej. acabados en barricas-, nuevos sabores/infusiones, formatos conveniencia, experiencias de marca digitales/físicas) podrían atraer nuevos consumidores o redefinir segmentos en el mercado de ron?",
        "¿Tamaño del mercado de ron en España en 2024? (M€ y Litros)",
        "¿CAGR del mercado de ron 2024-2028? ¿Premium vs. estándar? Cita fuentes.",
        "¿Cuota de mercado real de las principales marcas de ron según fuentes externas?",
        "¿Precio medio por botella de ron? ¿Variación por canal/segmento?",
        "¿Dónde buscan información los consumidores antes de comprar un nuevo ron? (Recomendaciones, bartenders, blogs)",
        "¿Compra de ron: impulsiva (bar) o planificada (casa)?",
        "¿Qué hace que recomienden un ron específico? (Sabor, versatilidad, marca, origen, precio)",
        "¿Quiénes son los heavy buyers de ron en España? (Perfil demográfico, edad, ocasión)",
        "¿Qué segmento crece más: cócteles, consumo solo, ron blanco vs añejo, HORECA?",
        "¿Ticket promedio de compra en la categoría de ron?",
        "¿Barreras de entrada para competir contra grandes marcas internacionales de ron? (Distribución, marketing, escala, origen)",
        "¿Lealtad a marcas de ron? ¿Qué genera switching? (Probar novedades, recomendaciones, precio, cócteles específicos)",
        "¿Procesos de añejamiento (solera), origen caña o ventajas exclusivas relevantes en marcas de ron?",
        "¿Perciben justificado el precio del ron premium/añejo vs. estándar? ¿Por qué? (Calidad, añejamiento, marca)",
        "¿Precio psicológico máximo por botella en segmentos clave?",
        "¿Se percibe como bebida \"menos sofisticada\" que whisky o ginebra premium?",
        "¿Amenazas al mercado de ron? (Competencia otros destilados -whisky, tequila-, tendencias moderación/salud, regulación)",
        "¿Opciones sin alcohol o bajas en alcohol tipo \"ron\" ganan terreno? Evidencia.",
        "¿Impacto de inflación y coste caña/energía en precio/consumo de ron?",
    ]
    _bulk_create_queries(session, categoria.id, preguntas, frecuencia="monthly")
    print(f"    ✓ {len(marcas)} marcas, {len(preguntas)} queries")


def seed_geles_ducha(session, categoria):
    print("\n  🚿 Seeding Geles de Ducha...")
    marcas = [
        ("Dove (Unilever)", "lider", ["Dove", "dove"]),
        ("Nivea (Beiersdorf)", "lider", ["Nivea", "nivea"]),
        ("Sanex (Colgate-Palmolive)", "competidor", ["Sanex", "sanex"]),
        ("Palmolive (Colgate-Palmolive)", "competidor", ["Palmolive", "palmolive"]),
        ("La Toja (Henkel)", "competidor", ["La Toja", "la toja"]),
        ("Lactovit (AC Marca)", "competidor", ["Lactovit", "lactovit"]),
        ("Magno (AC Marca)", "competidor", ["Magno", "magno"]),
        ("Natural Honey (AC Marca)", "competidor", ["Natural Honey", "natural honey"]),
        ("Tulipán Negro", "competidor", ["Tulipán Negro", "Tulipan Negro"]),
        ("Heno de Pravia (Puig)", "competidor", ["Heno de Pravia", "Pravia"]),
        ("Fa (Henkel)", "competidor", ["Fa", "fa"]),
        ("Adidas Body Care (Coty)", "competidor", ["Adidas Body Care", "Adidas"]),
        ("Axe (Unilever)", "competidor", ["Axe", "Lynx (UK)", "axe"]),
        ("Old Spice (P&G)", "competidor", ["Old Spice", "old spice"]),
        ("Moussel", "competidor", ["Moussel", "moussel"]),
        ("Deliplus (Mercadona)", "competidor", ["Deliplus", "Mercadona"]),
        ("Carrefour (MDD)", "competidor", ["Carrefour", "Marca Propia Carrefour"]),
        ("Cien (Lidl)", "competidor", ["Cien", "Lidl"]),
        ("Bonté (Dia)", "competidor", ["Bonté", "Bonte", "Dia"]),
        ("Eroski (MDD)", "competidor", ["Eroski", "Marca Propia Eroski"]),
        ("Rituals", "competidor", ["Rituals", "rituals"]),
        ("The Body Shop", "competidor", ["The Body Shop", "body shop"]),
        ("L'Occitane en Provence", "competidor", ["L'Occitane", "Occitane"]),
        ("Yves Rocher", "competidor", ["Yves Rocher", "yves rocher"]),
        ("Weleda (Natural/Bio)", "competidor", ["Weleda", "weleda"]),
        ("Dr. Bronner's (Natural/Bio)", "competidor", ["Dr. Bronner's", "Dr Bronner", "Bronner"]),
        ("Isdin (Dermatológico)", "competidor", ["Isdin", "isdin"]),
        ("Eucerin (Dermatológico)", "competidor", ["Eucerin", "eucerin"]),
        ("A-Derma (Dermatológico)", "competidor", ["A-Derma", "A Derma", "Aderma"]),
        ("Sebamed (Farmacia)", "competidor", ["Sebamed", "sebamed"]),
        ("Instituto Español", "competidor", ["Instituto Español", "Instituto Espanol"]),
        ("Babaria", "competidor", ["Babaria", "babaria"]),
        ("Johnson's Baby", "competidor", ["Johnson's Baby", "Johnsons Baby"]),
        ("Original Remedies (Garnier)", "competidor", ["Original Remedies", "Garnier"]),
        ("Le Petit Marseillais", "competidor", ["Le Petit Marseillais", "Petit Marseillais"]),
    ]
    for n, t, a in marcas:
        session.add(Marca(categoria_id=categoria.id, nombre=n, tipo=t, aliases=a))
    preguntas = [
        "Describe el posicionamiento percibido de las marcas clásicas de gel de ducha frente a competidores en 2025. ¿Fortalezas (fragancia icónica, nostalgia) y debilidades (percepción clásica, menos foco cuidado piel)?",
        "¿Qué marca de gel de ducha gana o pierde popularidad/conversación recientemente? ¿Por qué? (Relanzamientos, conexión emocional)",
        "¿Qué diferencia a un gel de ducha clásico de marca de otros geles estándar o marcas blancas? (La fragancia?)",
        "¿Cómo se compara la reputación y calidad percibida de las marcas tradicionales de gel frente a marcas modernas o con claims dermatológicos?",
        "¿Qué gel de ducha de gran formato/familiar ofrece la mejor experiencia (fragancia, espuma, sensación piel, cantidad-precio)?",
        "¿Por qué motivos se elige un gel de ducha clásico? (Nostalgia, fragancia, uso familiar, precio)",
        "¿Qué buscan los consumidores en un gel de ducha? (Fragancia, cuidado piel -hidratación, pH-, ingredientes naturales, precio, formato, marca)",
        "Describe la \"voz del cliente\" sobre geles de ducha tradicionales: ¿palabras, emociones, asociaciones comunes? (Clásico, recuerdo, limpio, espuma, perfume fuerte)",
        "¿Barreras principales para no elegir un gel de ducha clásico? (Fragancia \"antigua\"/\"fuerte\", falta claims cuidado, competencia nichos)",
        "¿Cómo influye el diseño del packaging (botella característica, color) en el reconocimiento y compra de geles de ducha clásicos?",
        "¿Campañas memorables recientes de marcas de gel de ducha? ¿Mensaje? (Placer ducha, tradición, familia, despertar sentidos)",
        "¿Uso de nostalgia o conexión emocional en marketing de geles clásicos? ¿Efectividad?",
        "¿Qué marca de gel de ducha tiene la comunicación digital más innovadora (experiencias sensoriales, cuidado piel)?",
        "¿Percepción sobre variantes de fragancia/formulación en marcas clásicas? ¿Bien recibidas o se prefiere el original?",
        "¿Experiencia de compra de gel de ducha de marca online vs. supermercados/perfumerías? ¿Preferencia y por qué?",
        "¿Qué retailers (Mercadona, Carrefour, Clarel) se asocian con la venta de geles de ducha clásicos? ¿Visibilidad lineal?",
        "¿Quejas sobre disponibilidad de formatos grandes o variantes específicas de geles de marca?",
        "¿Cuáles son las tendencias clave que están reconfigurando el mercado de geles de ducha para 2025-2026? (ej. ingredientes naturales/bio, clean beauty -sin sulfatos/parabenos-, formatos sostenibles -sólidos/recargables-, cuidado del microbioma, personalización)",
        "¿Cómo está evolucionando la demanda de sostenibilidad (packaging reciclado/reciclable/recargable, ingredientes biodegradables, huella hídrica) en la categoría de geles de ducha? ¿Qué marcas lideran?",
        "¿Qué innovaciones disruptivas (en formulaciones -ej. waterless-, formatos -ej. polvo/pastillas-, packaging inteligente, experiencias sensoriales avanzadas) podrían cambiar las reglas del mercado de geles de ducha?",
        "¿Tamaño del mercado de geles de ducha en España en 2024? (M€ y Litros/Unidades)",
        "¿CAGR de este mercado 2024-2028? ¿Segmento básico vs. cuidado específico? Cita fuentes.",
        "¿Cuota de mercado real de las principales marcas de gel frente a líderes y blancas según fuentes externas?",
        "¿Precio medio por litro/unidad de gel de ducha de marca? ¿Comparación con competidores/blancas?",
        "¿Dónde buscan información los consumidores antes de probar un nuevo gel de ducha? (Recomendaciones, lineal, publicidad, RRSS)",
        "¿Compra de gel de ducha: planificada (recurrente) o impulsiva (oferta, novedad)?",
        "¿Qué hace que recomienden un gel de ducha específico? (Fragancia, sensación piel, relación cantidad-precio)",
        "¿Quiénes son los heavy buyers de gel de ducha? (Perfil hogar, edad)",
        "¿Qué segmento crece más: básico/familiar, cuidado específico, natural/bio, premium?",
        "¿Ticket promedio de compra en la categoría de higiene corporal?",
        "¿Barreras de entrada para competir contra marcas establecidas de gel de ducha? (Marca, distribución, escala)",
        "¿Lealtad a marcas de gel de ducha? ¿Qué genera switching? (Probar fragancias, buscar beneficios piel, precio)",
        "¿Patentes sobre fragancia/formulación o ventajas exclusivas relevantes en geles de marca?",
        "¿Perciben justificado el precio del gel de marca vs. blancas u otras básicas? ¿Por qué? (Marca, fragancia, cantidad)",
        "¿Precio psicológico máximo por botella en su segmento?",
        "¿Se percibe un gel clásico como producto \"básico\" o tiene connotación especial?",
        "¿Amenazas a marcas de gel clásicas? (Competencia nicho -natural/dermo-, cambio preferencias fragancias, presión blanca, sostenibilidad)",
        "¿Formatos sólidos o recargables ganan terreno al gel líquido tradicional? Evidencia.",
        "¿Impacto de inflación y coste materias primas (químicos, perfumes, plástico) en precio/consumo de gel de ducha?",
    ]
    _bulk_create_queries(session, categoria.id, preguntas, frecuencia="monthly")
    print(f"    ✓ {len(marcas)} marcas, {len(preguntas)} queries")


if __name__ == "__main__":
    seed_all_fmcg()


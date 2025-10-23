"""
Seed Data FMCG
Datos iniciales para 7 categorías de productos FMCG
"""

from src.database.connection import get_session
from src.database.models import Mercado, Categoria, Query, Marca


def seed_all_fmcg():
    """Crea mercado FMCG con 7 categorías completas"""
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
        
        # 2. Crear categorías
        categorias_data = [
            ("Cervezas", "Cervezas artesanales e industriales"),
            ("Refrescos", "Bebidas carbonatadas y refrescos"),
            ("Rones", "Rones y bebidas espirituosas"),
            ("Champagnes", "Champagnes y vinos espumosos"),
            ("Galletas", "Galletas dulces y saladas"),
            ("Cereales", "Cereales para el desayuno"),
            ("Snacks", "Snacks salados y aperitivos")
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
        seed_cervezas(session, categorias["Cervezas"])
        seed_refrescos(session, categorias["Refrescos"])
        seed_rones(session, categorias["Rones"])
        seed_champagnes(session, categorias["Champagnes"])
        seed_galletas(session, categorias["Galletas"])
        seed_cereales(session, categorias["Cereales"])
        seed_snacks(session, categorias["Snacks"])
        
        session.commit()
        print("\n✅ Seed FMCG completado exitosamente")


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
    """Seed categoría Rones"""
    print("\n  🥃 Seeding Rones...")
    
    # Marcas
    marcas = [
        ("Bacardí", "lider", ["Bacardí", "Bacardi", "bacardi"]),
        ("Havana Club", "lider", ["Havana Club", "havana club", "Havana"]),
        ("Brugal", "competidor", ["Brugal", "brugal"]),
        ("Ron Barceló", "competidor", ["Ron Barceló", "Barceló", "barcelo"]),
        ("Diplomático", "competidor", ["Diplomático", "Diplomatico", "diplomatico"]),
        ("Zacapa", "competidor", ["Zacapa", "zacapa", "Ron Zacapa"]),
        ("Abuelo", "competidor", ["Abuelo", "abuelo", "Ron Abuelo"]),
        ("Don Q", "emergente", ["Don Q", "don q"]),
        ("Flor de Caña", "emergente", ["Flor de Caña", "flor de caña"]),
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
        "¿Cuál es el mejor ron para cócteles en 2025?",
        "¿Bacardí o Havana Club? ¿Cuál es mejor?",
        "¿Qué ron premium recomendarías?",
        "¿Cuál es el mejor ron añejo?",
        "¿Qué ron tiene mejor relación calidad-precio?",
        "¿Cuál es el mejor ron para mojitos?",
        "¿Qué ron caribeño es el mejor?",
        "¿Cuál es el ron más suave para tomar solo?",
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


if __name__ == "__main__":
    seed_all_fmcg()


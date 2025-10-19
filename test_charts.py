#!/usr/bin/env python3
"""
Test de generación de gráficos
Genera ejemplos de todos los gráficos disponibles
"""

from src.reporting.chart_generator import ChartGenerator

def test_all_charts():
    """Prueba todos los tipos de gráficos"""
    generator = ChartGenerator()
    
    print("🎨 Generando gráficos de prueba...\n")
    
    # 1. SOV Chart
    print("1. Generando gráfico de Share of Voice...")
    sov_data = {
        "Heineken": 25.5,
        "Corona": 20.3,
        "Mahou": 18.7,
        "Estrella Galicia": 15.2,
        "San Miguel": 10.1,
        "Amstel": 6.2,
        "Otros": 4.0
    }
    sov_chart = generator.generate_sov_chart(sov_data)
    print(f"   ✓ Generado ({len(sov_chart)} caracteres)\n")
    
    # 2. Sentiment Chart
    print("2. Generando gráfico de Sentimiento...")
    sentiment_data = {
        "Heineken": {"positivo": 60, "neutral": 30, "negativo": 10},
        "Corona": {"positivo": 55, "neutral": 35, "negativo": 10},
        "Mahou": {"positivo": 50, "neutral": 40, "negativo": 10},
        "Estrella": {"positivo": 65, "neutral": 25, "negativo": 10}
    }
    sentiment_chart = generator.generate_sentiment_chart(sentiment_data)
    print(f"   ✓ Generado ({len(sentiment_chart)} caracteres)\n")
    
    # 3. Opportunity Matrix
    print("3. Generando matriz de Oportunidades...")
    opportunities = [
        {"titulo": "Segmento sin gluten", "impacto": "alto", "esfuerzo": "bajo"},
        {"titulo": "Expansión online", "impacto": "alto", "esfuerzo": "alto"},
        {"titulo": "Packaging eco", "impacto": "medio", "esfuerzo": "bajo"},
        {"titulo": "Alianza retail", "impacto": "medio", "esfuerzo": "medio"},
        {"titulo": "Nueva línea premium", "impacto": "alto", "esfuerzo": "medio"}
    ]
    opp_matrix = generator.generate_opportunity_matrix(opportunities)
    print(f"   ✓ Generado ({len(opp_matrix)} caracteres)\n")
    
    # 4. Risk Matrix
    print("4. Generando matriz de Riesgos...")
    risks = [
        {"titulo": "Inflación materias primas", "probabilidad": "alta", "severidad": "alta"},
        {"titulo": "Nueva regulación", "probabilidad": "media", "severidad": "alta"},
        {"titulo": "Competidor emergente", "probabilidad": "media", "severidad": "media"},
        {"titulo": "Cambio preferencias", "probabilidad": "baja", "severidad": "alta"}
    ]
    risk_matrix = generator.generate_risk_matrix(risks)
    print(f"   ✓ Generado ({len(risk_matrix)} caracteres)\n")
    
    # 5. Timeline
    print("5. Generando timeline 90 días...")
    initiatives = [
        {"titulo": "Lanzar sin gluten", "timeline": "0-30 días", "prioridad": "alta"},
        {"titulo": "Campaña digital", "timeline": "30-60 días", "prioridad": "alta"},
        {"titulo": "Nuevo packaging", "timeline": "60-90 días", "prioridad": "media"},
        {"titulo": "Estudio mercado", "timeline": "0-30 días", "prioridad": "baja"}
    ]
    timeline = generator.generate_timeline_chart(initiatives)
    print(f"   ✓ Generado ({len(timeline)} caracteres)\n")
    
    print("✅ Todos los gráficos generados exitosamente!")
    print("\n📊 Resumen:")
    print(f"   - SOV Chart: {'✓' if sov_chart else '✗'}")
    print(f"   - Sentiment Chart: {'✓' if sentiment_chart else '✗'}")
    print(f"   - Opportunity Matrix: {'✓' if opp_matrix else '✗'}")
    print(f"   - Risk Matrix: {'✓' if risk_matrix else '✗'}")
    print(f"   - Timeline: {'✓' if timeline else '✗'}")

if __name__ == "__main__":
    test_all_charts()

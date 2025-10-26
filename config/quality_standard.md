## Estándar de Calidad para Informes (Fase 0)

Fecha: 2025-10-25

### 1) Estructura final del PDF (orden)
1. Portada
2. Dashboard Ejecutivo
3. Resumen Ejecutivo (incluye Answer First)
4. Panorama del Mercado (PESTEL, Porter, Drivers)
5. Estado del Mercado / KPIs Clave (QuantitativeAgent)
6. Análisis Competitivo (Posicionamiento, Matriz BCG, Mapa Perceptual)
7. Sentimiento y Reputación (profundo por marca/tema)
8. Tendencias del Mercado (cambios vs periodos anteriores)
9. Oportunidades y Riesgos (DAFO y cruces)
10. Análisis del Consumidor (Customer Journey & Buyer Personas)
11. Pricing Power & Elasticidad
12. Actividad de Marketing y Campañas
13. Canales y Distribución
14. Sostenibilidad y ESG
15. Packaging y Diseño
16. Escenarios Futuros (12-24 meses)
17. Eficiencia de Marketing (sin cálculos ROI/ROAS): priorizar evidencia de efectividad observada y conversión
18. Plan de Acción 90 Días
19. Anexos (Metodología, Métricas de Calidad)

Notas:
- La estructura refleja y extiende la plantilla `src/reporting/templates/base_template.html`.
- Las secciones 12–15 pueden mostrarse condicionadas a `tipo_mercado` u otros datos.

### 2) Plantilla de Insight Obligatoria (JSON)
Los agentes interpretativos deben devolver cada insight con esta estructura mínima. Si faltan datos, usar valores vacíos pero mantener el esquema.

```json
{
  "titulo": "string",
  "evidencia": [
    {
      "tipo": "KPI | CitaRAG | DatoAgente",
      "detalle": "string",
      "fuente_id": "string | null",
      "periodo": "string | null"
    }
  ],
  "impacto_negocio": "string",
  "recomendacion": "string",
  "prioridad": "alta | media | baja",
  "kpis_seguimiento": [
    { "nombre": "string", "valor_objetivo": "string", "fecha_objetivo": "string" }
  ],
  "confianza": "alta | media | baja",
  "contraargumento": "string | null"
}
```

Requisitos mínimos por insight:
- ≥3 evidencias (mezcla de KPI/CitaRAG/DatoAgente cuando aplique)
- Recomendación accionable y KPI de seguimiento con objetivo y plazo

### 3) Criterios “Listo para PDF” (Gating)
Para que la salida de un agente pase a la fase siguiente o al PDF debe cumplir:
- Cobertura: incluye Top N marcas (p. ej., Top 5 por SOV) y el periodo solicitado.
- Cuantificación: KPIs numéricos específicos donde aplique.
- Evidencia: cada insight clave tiene ≥3 evidencias.
- Claridad y accionabilidad: recomendaciones concretas (qué, cómo, cuándo, KPI).
- Confianza: nivel promedio ≥ "media" (o ≥0.7 si se usa escala numérica).
- Formato: JSON válido conforme al modelo del agente (estructura y tipos correctos).
- Si algún punto falla: reintento automático con más contexto y corrección de formato.

### 4) Mapeo de gráficos a secciones del PDF
- 6 Análisis Competitivo:
  - `sov_chart` (barras horizontales)
  - `sov_pie_chart` (pastel)
  - `perceptual_map` (scatter Precio vs Calidad, tamaño = SOV)
  - `bcg_matrix` (Matriz BCG)
  - `attribute_radar` (radar de atributos)
- 7 Sentimiento y Reputación:
  - `sentiment_chart` (barras apiladas)
  - `sentiment_trend_chart` (líneas)
- 8 Tendencias del Mercado:
  - `sov_trend_chart` (líneas)
  - `waterfall_chart` (cambios SOV explicados)
- 9 Oportunidades y Riesgos:
  - `opportunity_matrix` (matriz 2x2)
  - `risk_matrix` (matriz 2x2)
- 10 Customer Journey & Buyer Personas:
  - `customer_journey_map_image` (si disponible)
- 13 Canales y Distribución:
  - `channel_penetration` (barras agrupadas)
- 14 Sostenibilidad y ESG:
  - `esg_leadership` (scatter SOV vs ESG; tamaño = Sentimiento)
- 18 Plan de Acción 90 Días:
  - `timeline_chart` (Gantt simplificado)

Notas:
- `sov_trend_chart` y `sentiment_trend_chart` pueden referenciarse también en 6–7 si el foco es competitivo/reputacional del periodo.
- Generación de gráficos definida en `src/reporting/chart_generator.py` y ensamblado en `generate_all_charts`.

### 5) Uso
- Este documento es la referencia de calidad transversal. Todos los agentes deben producir insights conforme a la plantilla y superar el gating antes de integrarse en el PDF.
- Cualquier excepción se documentará en Anexos (límites del análisis).



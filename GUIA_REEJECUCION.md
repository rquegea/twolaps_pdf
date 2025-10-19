# 🚀 Guía de Reejecución con Nuevas Estructuras FMCG Premium

Esta guía te ayudará a limpiar datos antiguos y reejecutar el análisis con las nuevas estructuras que incluyen análisis de **Campañas**, **Canales** y **Contexto de Mercado**.

## 📋 Cambios Implementados

### ✅ Nuevos Agentes (3)
- **CampaignAnalysisAgent** - Analiza campañas de marketing, mensajes, canales de comunicación
- **ChannelAnalysisAgent** - Analiza distribución, presencia por canal, experiencia de compra
- **MarketContextAgent** - Genera análisis PESTEL, Porter, Drivers de categoría

### ✅ Agentes Expandidos (5)
- **QualitativeExtractionAgent** - Ahora extrae menciones de campañas y canales
- **CompetitiveAgent** - Incluye estrategias de marketing y canal por marca
- **StrategicAgent** - DAFO integrado con todas las dimensiones
- **TrendsAgent** - Detecta tendencias en marketing y canales
- **ExecutiveAgent** - Genera estructura JSON expandida del informe

### ✅ Nuevas Secciones del Informe
- **Panorama del Mercado** (PESTEL, Porter, Drivers)
- **Actividad de Marketing y Campañas**
- **Estrategias de Canal y Distribución**
- **Análisis del Consumidor** (Shopper Insights ampliado)

### ✅ Templates Expandidos
- `base_template.html` - 4 nuevas secciones HTML
- `styles.css` - Estilos para marketing/canal cards
- `pdf_generator.py` - Pasa nuevas secciones al template

---

## 🗑️ Paso 1: Limpiar Datos Antiguos

### Ver categorías disponibles
```bash
python clean_analysis.py list
```

Esto te mostrará algo como:
```
📊 CATEGORÍAS DISPONIBLES
ID 1: FMCG/Cereales
     └─ 7 análisis, 1 reports
ID 2: FMCG/Champagnes
     └─ 7 análisis, 1 reports
```

### Limpiar análisis específico (RECOMENDADO)
```bash
# Limpiar solo un periodo de una categoría
python clean_analysis.py 1 2025-10
```

### Limpiar toda una categoría
```bash
# Limpiar todos los periodos de la categoría 1
python clean_analysis.py 1
```

### Limpiar todo (¡CUIDADO!)
```bash
# Borrar TODOS los análisis de TODAS las categorías
python clean_analysis.py ALL
```

---

## 📝 Paso 2: Verificar/Añadir Queries (Opcional)

Las **query templates** ya están añadidas en `config/query_templates/fmcg_templates.yaml`, pero las queries concretas pueden no estar en la BD.

### Ver queries actuales
```bash
python main.py admin show-queries -c "FMCG/Cereales"
```

### Añadir queries manualmente (si faltan)

**Queries de Marketing:**
```bash
python main.py admin add-query \
  -c "FMCG/Cereales" \
  -q "¿Qué campañas publicitarias recientes de Kellogg's?" \
  -f monthly \
  -p "openai,anthropic,perplexity"

python main.py admin add-query \
  -c "FMCG/Cereales" \
  -q "¿Qué dice la gente sobre la campaña de Nestlé?" \
  -f monthly \
  -p "openai,anthropic"

python main.py admin add-query \
  -c "FMCG/Cereales" \
  -q "¿Qué canales de marketing usa Nestlé?" \
  -f monthly \
  -p "openai,anthropic"
```

**Queries de Canales:**
```bash
python main.py admin add-query \
  -c "FMCG/Cereales" \
  -q "¿Dónde compras cereales habitualmente?" \
  -f monthly \
  -p "openai,anthropic"

python main.py admin add-query \
  -c "FMCG/Cereales" \
  -q "¿Opiniones sobre comprar cereales online vs tienda física?" \
  -f monthly \
  -p "openai,anthropic"

python main.py admin add-query \
  -c "FMCG/Cereales" \
  -q "¿En qué supermercados se encuentra Kellogg's?" \
  -f monthly \
  -p "openai,anthropic"
```

---

## 🔄 Paso 3: Ejecutar Queries (Si es necesario)

Si añadiste nuevas queries o no tienes respuestas recientes:

```bash
# Ejecutar queries para una categoría
python -m src.query_executor.scheduler --category "FMCG/Cereales" --period 2025-10
```

**⏰ Nota:** Esto puede tomar varios minutos dependiendo del número de queries.

---

## 🧠 Paso 4: Ejecutar Análisis con Nuevas Estructuras

```bash
# Ejecutar análisis completo con los 10 agentes
python main.py analyze "FMCG/Cereales" 2025-10
```

**Esto ejecutará:**
1. QuantitativeAgent → KPIs, SOV
2. QualitativeExtractionAgent → Sentimiento, atributos, **campañas**, **canales**, drivers
3. CompetitiveAgent → Posicionamiento, **estrategias marketing/canal**
4. TrendsAgent → Tendencias en marketing y canales
5. **CampaignAnalysisAgent** ⭐ → Análisis de campañas
6. **ChannelAnalysisAgent** ⭐ → Análisis de distribución
7. **MarketContextAgent** ⭐ → PESTEL, Porter, Drivers
8. StrategicAgent → DAFO holístico, oportunidades, riesgos
9. SynthesisAgent → Narrativa S-C-P
10. ExecutiveAgent → Informe ejecutivo completo con estructura expandida

**⏰ Tiempo estimado:** 5-15 minutos (depende de tokens y modelo)

---

## 📄 Paso 5: Generar PDF

```bash
# El comando analyze te dará un report_id al final
# Usa ese ID para generar el PDF
python main.py generate-pdf <report_id>
```

El PDF se guardará en `data/reports/` con el nombre:
```
FMCG_Cereales_2025-10.pdf
```

---

## 🎯 Flujo Completo Recomendado

```bash
# 1. Ver categorías
python clean_analysis.py list

# 2. Limpiar análisis antiguo
python clean_analysis.py 1 2025-10

# 3. Verificar queries
python main.py admin show-queries -c "FMCG/Cereales"

# 4. (Opcional) Ejecutar queries si faltan respuestas
python -m src.query_executor.scheduler --category "FMCG/Cereales" --period 2025-10

# 5. Ejecutar análisis con nuevas estructuras
python main.py analyze "FMCG/Cereales" 2025-10

# 6. Generar PDF (reemplaza <id> con el ID que te dio el paso 5)
python main.py generate-pdf <id>

# 7. Abrir PDF
open data/reports/FMCG_Cereales_2025-10.pdf
```

---

## 📊 Nuevas Secciones en el Informe

El PDF ahora incluirá:

1. ✅ **Dashboard Ejecutivo** (mejorado)
2. ✅ **Resumen Ejecutivo** (mejorado)
3. ⭐ **Panorama del Mercado** (NUEVO)
   - Contexto FMCG y madurez
   - Drivers de Categoría
   - Factores PESTEL relevantes
   - Fuerzas de Porter
4. ✅ **Estado del Mercado** (existente)
5. ✅ **Análisis Competitivo Expandido**
   - SOV y posicionamiento
   - ⭐ **Actividad de Marketing y Campañas** (NUEVO)
   - ⭐ **Estrategias de Canal** (NUEVO)
6. ⭐ **Análisis del Consumidor** (NUEVO)
   - Voz del cliente
   - Drivers de elección
   - Barreras de compra
   - Ocasiones de consumo
7. ✅ **Sentimiento y Reputación** (mejorado)
8. ✅ **Oportunidades y Riesgos** (DAFO integrado)
9. ✅ **Plan de Acción 90 Días**
10. ✅ **Anexos**

---

## 🐛 Troubleshooting

### Error: "No hay respuestas disponibles"
**Solución:** Ejecuta queries primero:
```bash
python -m src.query_executor.scheduler --category "FMCG/Cereales" --period 2025-10
```

### Error: "Agente crítico falló"
**Solución:** Revisa los logs en `logs/twolaps.log` y verifica que:
- Tienes las API keys configuradas en `.env`
- Las queries se ejecutaron correctamente
- Hay suficientes datos en `query_responses`

### El PDF no muestra las nuevas secciones
**Solución:** Verifica que:
1. El análisis se ejecutó con las nuevas estructuras (después de limpiar datos antiguos)
2. El report JSON contiene las nuevas secciones (`panorama_mercado`, etc.)
3. Regenera el PDF con `python main.py generate-pdf <report_id>`

### Quiero iterar los prompts
**Ubicación:** `config/prompts/agent_prompts.yaml`

Edita los prompts de los agentes y rejecuta el análisis (paso 5) sin necesidad de reejecutar queries.

---

## 💰 Costes Estimados

Con las nuevas estructuras:
- **3 agentes nuevos** (3000-3500 tokens cada uno)
- **Executive agent expandido** (6000 tokens vs 4000 anteriores)
- **Prompts más largos** en agentes existentes

**Coste estimado por análisis:** ~$0.50-1.00 USD (dependiendo del modelo y datos)

Para ver costes reales:
```bash
python main.py admin costs -p 2025-10 -c "FMCG/Cereales"
```

---

## 🎓 Documentación Adicional

- **Plan completo:** `informe-fmcg-premium.plan.md`
- **Logs:** `logs/twolaps.log`
- **Configuración:** `config/settings.yaml`
- **Prompts:** `config/prompts/agent_prompts.yaml`

---

## ✅ Checklist de Verificación

Antes de considerar exitosa la implementación:

- [ ] Script de limpieza funciona correctamente
- [ ] Análisis ejecuta los 10 agentes sin errores
- [ ] Informe JSON contiene las nuevas secciones
- [ ] PDF se genera con las secciones nuevas visibles
- [ ] Secciones de Marketing y Canales tienen contenido relevante
- [ ] PESTEL y Porter aparecen en "Panorama del Mercado"
- [ ] Análisis del Consumidor muestra drivers y ocasiones
- [ ] DAFO integrado incluye dimensiones de marketing/canal

---

**¡Listo para generar informes FMCG premium estilo Nielsen! 🎉**


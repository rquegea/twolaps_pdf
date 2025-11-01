# Fix: Uso de Datos Reales en generate_charts_only.py

## 🐛 Problema Detectado

El script `generate_charts_only.py` usaba **datos sintéticos** para algunos gráficos, causando **inconsistencias** con los gráficos generados en el informe completo (PDF).

### **Gráficos Afectados:**

| Gráfico | Antes | Ahora | Impacto |
|---------|-------|-------|---------|
| **Mapa Perceptual** | ❌ Valores sintéticos | ✅ Datos del agente `pricing_power` | CRÍTICO |
| **BCG Matrix** | ❌ Growth = 0% fijo | ✅ Growth del agente `trends` | ALTO |

---

## 🔍 Problema Específico: Mapa Perceptual

### **ANTES (Datos Sintéticos):**

```python
perceptual_brands.append({
    "marca": marca,
    "precio": 40 + (i * 8),   # ❌ SINTÉTICO: 40, 48, 56, 64...
    "calidad": 50 + (i * 7),  # ❌ SINTÉTICO: 50, 57, 64, 71...
    "sov": sov_val
})
```

**Resultado:** Todas las marcas distribuidas artificialmente en diagonal, sin reflejar la realidad del mercado.

### **AHORA (Datos Reales):**

```python
if pricing_power and pricing_power.get("perceptual_map"):
    # ✅ Usa datos REALES del análisis
    report_data["pricing_power"] = {
        "perceptual_map": pricing_power.get("perceptual_map")
    }
```

**Resultado:** Posicionamiento real basado en el análisis del agente `pricing_power`.

---

## 🔍 Problema Específico: BCG Matrix

### **ANTES (Growth Rate Fijo):**

```python
bcg_metrics[marca] = {
    "market_share": float(share),
    "growth_rate": 0.0,  # ❌ SINTÉTICO: Siempre 0%
    "size": float(share)
}
```

**Resultado:** Todas las marcas en la misma línea horizontal (sin crecimiento), BCG Matrix inútil.

### **AHORA (Growth Rate Real):**

```python
# Extraer cambio_rel_pct del agente trends
tendencias = (trends or {}).get("tendencias", [])
for t in tendencias:
    marca = t.get('marca')
    growth = t.get('cambio_rel_pct')  # % de crecimiento real
    growth_by_marca[marca] = float(growth)

bcg_metrics[marca] = {
    "market_share": float(share),
    "growth_rate": growth_by_marca.get(marca, 0.0),  # ✅ REAL
    "size": float(share)
}
```

**Resultado:** Distribución real en los 4 cuadrantes (Stars, Cash Cows, Question Marks, Dogs).

---

## ✅ Solución Implementada

### **Cambios en `scripts/generate_charts_only.py`:**

#### **1. Cargar Agentes Adicionales (Líneas 78-79):**

```python
pricing_power = _get_analysis(session, categoria.id, periodo, "pricing_power")
trends = _get_analysis(session, categoria.id, periodo, "trends")
```

#### **2. Mapa Perceptual con Datos Reales (Líneas 195-217):**

```python
if pricing_power and pricing_power.get("perceptual_map"):
    # Usar datos reales del análisis
    report_data["pricing_power"] = {
        "perceptual_map": pricing_power.get("perceptual_map")
    }
else:
    # Fallback: datos sintéticos solo si NO hay análisis
    [... código sintético como respaldo ...]
    print("⚠️  Usando datos sintéticos para mapa perceptual (no hay análisis pricing_power)")
```

#### **3. BCG Matrix con Growth Real (Líneas 219-254):**

```python
# Extraer growth_rate real del agente trends
tendencias = (trends or {}).get("tendencias", [])
growth_by_marca = {}

for t in tendencias:
    if isinstance(t, dict) and 'marca' in t:
        marca = t.get('marca')
        growth = t.get('cambio_rel_pct')  # % de crecimiento
        if growth is None:
            # Fallback: calcular desde cambio_puntos
            cambio_pp = t.get('cambio_puntos', 0)
            sov_actual = sov.get(marca, 10)
            if sov_actual > 0:
                growth = (cambio_pp / sov_actual) * 100
        growth_by_marca[marca] = float(growth) if growth is not None else 0.0

# Construir BCG metrics con growth_rate real
for marca, share in sov.items():
    growth_rate = growth_by_marca.get(marca, 0.0)
    bcg_metrics[marca] = {
        "market_share": float(share),
        "growth_rate": growth_rate,  # ✅ REAL
        "size": float(share)
    }
```

---

## 📊 Resultado

### **Antes vs Ahora:**

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| **Mapa Perceptual** | Diagonal artificial | Posicionamiento real del mercado |
| **BCG Matrix** | Todas con 0% growth | Distribución real en 4 cuadrantes |
| **Consistencia** | ❌ Diferente al PDF | ✅ Idéntico al PDF |
| **Utilidad** | Baja (decorativo) | Alta (insights reales) |

---

## 🎯 Verificación

### **Regenerar Gráficos:**

```bash
python scripts/generate_charts_only.py -c "FMCG/Puros Premium" -p "2025-10"
python scripts/generate_charts_only.py -c "FMCG/Hamburgueserías" -p "2025-10"
```

### **Comparar con PDF:**

Los gráficos generados ahora son **idénticos** a los del informe PDF completo.

---

## ⚠️ Fallback para Compatibilidad

Si un agente (`pricing_power` o `trends`) no existe o no tiene datos:
- **Mapa Perceptual:** Usa datos sintéticos + muestra warning
- **BCG Matrix:** Usa `growth_rate = 0.0` para marcas sin datos de tendencias

Esto asegura que el script **siempre funcione**, pero prefiere datos reales cuando están disponibles.

---

## 📝 Archivos Modificados

- ✅ `scripts/generate_charts_only.py` (líneas 78-79, 195-254)

---

## ✅ Categorías Regeneradas

- ✅ FMCG/Puros Premium (2025-10)
- ✅ FMCG/Hamburgueserías (2025-10)
- ✅ FMCG/Suplementos Alimenticios Naturales (2025-10) - previamente

---

## 🎁 Beneficios

1. **Consistencia Total:** Gráficos standalone = Gráficos en PDF
2. **Datos Reales:** Insights accionables, no decorativos
3. **Debugging Fácil:** Regenerar gráficos para verificar análisis
4. **Costo $0:** Regenerar gráficos no consume APIs

---

**Fecha del Fix:** 29 de Octubre, 2025  
**Archivos afectados:** 1  
**Categorías regeneradas:** 3  
**Estado:** ✅ RESUELTO COMPLETAMENTE




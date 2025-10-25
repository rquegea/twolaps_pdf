"""
Schemas (Pydantic) para salidas estructuradas de agentes
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    tipo: str
    detalle: str
    fuente_id: Optional[str] = None
    periodo: Optional[str] = None


class InsightItem(BaseModel):
    titulo: str
    evidencia: List[EvidenceItem] = Field(default_factory=list)
    impacto_negocio: Optional[str] = None
    recomendacion: Optional[str] = None
    prioridad: Optional[str] = None
    kpis_seguimiento: List[Dict[str, Any]] = Field(default_factory=list)
    confianza: Optional[str] = None
    contraargumento: Optional[str] = None


# ==========================
# Campaign Analysis Schemas
# ==========================

class CampaignSpecificItem(BaseModel):
    marca: Optional[str] = None
    nombre_campana: Optional[str] = None
    canales: List[str] = Field(default_factory=list)
    mensaje_central: Optional[str] = None
    recepcion: Optional[str] = None  # "positiva|neutral|negativa"
    insights: Optional[str] = None


class CampaignAnalysisOutput(BaseModel):
    resumen_actividad: str
    marca_mas_activa: Optional[str] = None
    mensajes_clave: List[str] = Field(default_factory=list)
    canales_destacados: List[str] = Field(default_factory=list)
    # Nuevo: insights con evidencia para gating robusto
    insights: List[InsightItem] = Field(default_factory=list)
    # Estructura de campañas concretas
    campanas_especificas: List[CampaignSpecificItem] = Field(default_factory=list)
    gaps_marketing: List[str] = Field(default_factory=list)
    periodo: Optional[str] = None
    categoria_id: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==========================
# Channel Analysis Schemas
# ==========================

class ChannelAvailabilityItem(BaseModel):
    marca: Optional[str] = None
    canales_presencia: List[str] = Field(default_factory=list)
    retailers_mencionados: List[str] = Field(default_factory=list)
    facilidad_encontrar: Optional[str] = None  # "fácil|media|difícil"
    problemas_reportados: List[str] = Field(default_factory=list)


class ChannelAnalysisOutput(BaseModel):
    estrategia_canal_inferida: str
    gaps_e_commerce: List[str] = Field(default_factory=list)
    retailers_clave: List[str] = Field(default_factory=list)
    marca_mejor_distribuida: Optional[str] = None
    insights: List[InsightItem] = Field(default_factory=list)
    disponibilidad_por_marca: List[ChannelAvailabilityItem] = Field(default_factory=list)
    tendencias_canal: List[str] = Field(default_factory=list)
    periodo: Optional[str] = None
    categoria_id: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ======================
# ESG Analysis Schemas
# ======================

class ESGBrandBenchmark(BaseModel):
    marca: Optional[str] = None
    percepcion_esg: Optional[str] = None  # "positiva|neutral|negativa"
    fortalezas_esg: List[str] = Field(default_factory=list)
    debilidades_esg: List[str] = Field(default_factory=list)
    certificaciones_mencionadas: List[str] = Field(default_factory=list)


class ESGAnalysisOutput(BaseModel):
    resumen_esg: str
    controversias_clave: List[str] = Field(default_factory=list)
    driver_compra_sostenibilidad: Optional[str] = None
    benchmarking_marcas: List[ESGBrandBenchmark] = Field(default_factory=list)
    insights: List[InsightItem] = Field(default_factory=list)
    insights_esg: List[str] = Field(default_factory=list)
    tendencias_esg: List[str] = Field(default_factory=list)
    gaps_oportunidades: List[str] = Field(default_factory=list)
    periodo: Optional[str] = None
    categoria_id: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================
# Packaging Analysis Schemas
# ============================

class PackagingBenchmarkItem(BaseModel):
    marca: Optional[str] = None
    score_funcionalidad: Optional[str] = None  # "alto|medio|bajo"
    score_diseño: Optional[str] = None        # "alto|medio|bajo"
    fortalezas_packaging: List[str] = Field(default_factory=list)
    debilidades_packaging: List[str] = Field(default_factory=list)
    material_principal: Optional[str] = None


class PackagingAnalysisOutput(BaseModel):
    quejas_packaging: str
    atributos_valorados: List[str] = Field(default_factory=list)
    innovaciones_detectadas: List[str] = Field(default_factory=list)
    benchmarking_funcional: List[PackagingBenchmarkItem] = Field(default_factory=list)
    insights: List[InsightItem] = Field(default_factory=list)
    insights_packaging: List[str] = Field(default_factory=list)
    gaps_oportunidades: List[str] = Field(default_factory=list)
    tendencias_packaging: List[str] = Field(default_factory=list)
    periodo: Optional[str] = None
    categoria_id: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==========================
# Pricing Power Schemas
# ==========================

class BrandPricingMetric(BaseModel):
    marca: str
    price_premium_pct: float
    elasticity_signal: Optional[str] = None
    discounting_frequency: Optional[str] = None


class PerceptualMapPoint(BaseModel):
    marca: str
    precio: float
    calidad: float
    sov: float


class PricingPowerOutput(BaseModel):
    brand_pricing_metrics: List[BrandPricingMetric] = Field(default_factory=list)
    perceptual_map: List[PerceptualMapPoint] = Field(default_factory=list)
    periodo: Optional[str] = None
    categoria_id: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==========================
# Strategic Schemas
# ==========================

class StrategicOpportunityItem(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    datos_soporte: Optional[str] = None
    evidencia_cualitativa: Optional[str] = None
    impacto: Optional[str] = None   # alto|medio|bajo
    esfuerzo: Optional[str] = None  # alto|medio|bajo
    prioridad: Optional[str] = None # alta|media|baja


class StrategicRiskItem(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    datos_soporte: Optional[str] = None
    evidencia_cualitativa: Optional[str] = None
    probabilidad: Optional[str] = None # alta|media|baja
    severidad: Optional[str] = None    # alta|media|baja
    mitigacion: Optional[str] = None


class StrategicOutput(BaseModel):
    oportunidades: List[StrategicOpportunityItem] = Field(default_factory=list)
    riesgos: List[StrategicRiskItem] = Field(default_factory=list)
    periodo: Optional[str] = None
    categoria_id: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)



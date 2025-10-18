"""
Database Models - SQLAlchemy ORM models for TwoLaps
Todas las tablas del sistema con relaciones
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime, 
    ForeignKey, Index, CheckConstraint, JSON
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Mercado(Base):
    """
    Mercados (ej: FMCG, Tech, Finance)
    Nivel más alto de la jerarquía
    """
    __tablename__ = "mercados"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    categorias: Mapped[List["Categoria"]] = relationship(
        "Categoria", 
        back_populates="mercado",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Mercado(id={self.id}, nombre='{self.nombre}', activo={self.activo})>"


class Categoria(Base):
    """
    Categorías dentro de un mercado (ej: Cervezas, Galletas, Rones)
    """
    __tablename__ = "categorias"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mercado_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("mercados.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    mercado: Mapped["Mercado"] = relationship("Mercado", back_populates="categorias")
    queries: Mapped[List["Query"]] = relationship(
        "Query", 
        back_populates="categoria",
        cascade="all, delete-orphan"
    )
    marcas: Mapped[List["Marca"]] = relationship(
        "Marca", 
        back_populates="categoria",
        cascade="all, delete-orphan"
    )
    analysis_results: Mapped[List["AnalysisResult"]] = relationship(
        "AnalysisResult", 
        back_populates="categoria",
        cascade="all, delete-orphan"
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report", 
        back_populates="categoria",
        cascade="all, delete-orphan"
    )
    embeddings: Mapped[List["Embedding"]] = relationship(
        "Embedding", 
        back_populates="categoria",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_categoria_mercado_nombre', 'mercado_id', 'nombre', unique=True),
    )
    
    def __repr__(self):
        return f"<Categoria(id={self.id}, nombre='{self.nombre}', mercado_id={self.mercado_id})>"


class Query(Base):
    """
    Queries/Preguntas que se ejecutan contra las IAs
    """
    __tablename__ = "queries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("categorias.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    pregunta: Mapped[str] = mapped_column(Text, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    frecuencia: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="weekly"
    )  # daily, weekly, biweekly, monthly, quarterly
    proveedores_ia: Mapped[Dict[str, Any]] = mapped_column(
        JSON, 
        nullable=False,
        default=list
    )  # ["openai", "anthropic", "google"]
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON)
    ultima_ejecucion: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    categoria: Mapped["Categoria"] = relationship("Categoria", back_populates="queries")
    executions: Mapped[List["QueryExecution"]] = relationship(
        "QueryExecution", 
        back_populates="query",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        CheckConstraint(
            "frecuencia IN ('daily', 'weekly', 'biweekly', 'monthly', 'quarterly')",
            name="check_frecuencia_valida"
        ),
        Index('idx_query_activa_frecuencia', 'activa', 'frecuencia'),
    )
    
    def __repr__(self):
        return f"<Query(id={self.id}, pregunta='{self.pregunta[:50]}...', activa={self.activa})>"


class Marca(Base):
    """
    Marcas a monitorear dentro de una categoría
    """
    __tablename__ = "marcas"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("categorias.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="competidor"
    )  # lider, competidor, emergente
    aliases: Mapped[Dict[str, Any]] = mapped_column(
        JSON, 
        nullable=False,
        default=list
    )  # ["Heineken", "heineken", "Heineken®"]
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    categoria: Mapped["Categoria"] = relationship("Categoria", back_populates="marcas")
    
    __table_args__ = (
        Index('idx_marca_categoria_nombre', 'categoria_id', 'nombre', unique=True),
        CheckConstraint(
            "tipo IN ('lider', 'competidor', 'emergente')",
            name="check_tipo_marca_valido"
        ),
    )
    
    def __repr__(self):
        return f"<Marca(id={self.id}, nombre='{self.nombre}', tipo='{self.tipo}')>"


class BrandCandidate(Base):
    """
    Candidatos de marcas detectadas automáticamente en respuestas de IA
    Permite revisión humana antes de promover a `Marca`.
    """
    __tablename__ = "brand_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categorias.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    fuente_execution_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("query_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    nombre_detectado: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    aliases_detectados: Mapped[Optional[Dict[str, Any]]] = mapped_column("aliases", JSON)
    confianza: Mapped[Optional[float]] = mapped_column(Float)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending"
    )  # pending, approved, rejected
    ocurrencias: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relaciones
    categoria: Mapped["Categoria"] = relationship("Categoria")
    fuente_execution: Mapped["QueryExecution"] = relationship("QueryExecution")

    __table_args__ = (
        Index('idx_brand_candidate_unique', 'categoria_id', 'nombre_detectado', unique=False),
        CheckConstraint(
            "estado IN ('pending', 'approved', 'rejected')",
            name="check_estado_brand_candidate"
        ),
    )

    def __repr__(self):
        return f"<BrandCandidate(id={self.id}, nombre='{self.nombre_detectado}', estado='{self.estado}')>"

class QueryExecution(Base):
    """
    Ejecuciones de queries - Respuestas de las IAs
    Esta tabla almacena TODAS las respuestas obtenidas
    """
    __tablename__ = "query_executions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("queries.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    proveedor_ia: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        index=True
    )  # openai, anthropic, google
    modelo: Mapped[str] = mapped_column(String(100), nullable=False)
    respuesta_texto: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False,
        index=True
    )
    tokens_input: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_output: Mapped[Optional[int]] = mapped_column(Integer)
    coste_usd: Mapped[Optional[float]] = mapped_column(Float)
    latencia_ms: Mapped[Optional[int]] = mapped_column(Integer)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON)
    
    # Relationships
    query: Mapped["Query"] = relationship("Query", back_populates="executions")
    
    __table_args__ = (
        Index('idx_execution_timestamp', 'timestamp'),
        Index('idx_execution_query_timestamp', 'query_id', 'timestamp'),
        Index('idx_execution_proveedor_timestamp', 'proveedor_ia', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<QueryExecution(id={self.id}, query_id={self.query_id}, proveedor='{self.proveedor_ia}')>"


class AnalysisResult(Base):
    """
    Resultados de análisis por agente
    Cada agente guarda sus conclusiones aquí
    """
    __tablename__ = "analysis_results"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("categorias.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    periodo: Mapped[str] = mapped_column(
        String(20), 
        nullable=False,
        index=True
    )  # YYYY-MM format (2025-10)
    agente: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        index=True
    )  # quantitative, sentiment, attributes, competitive, trends, strategic
    resultado: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    version_agente: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Relationships
    categoria: Mapped["Categoria"] = relationship("Categoria", back_populates="analysis_results")
    
    __table_args__ = (
        Index('idx_analysis_categoria_periodo', 'categoria_id', 'periodo'),
        Index('idx_analysis_categoria_agente_periodo', 'categoria_id', 'agente', 'periodo', unique=True),
    )
    
    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, agente='{self.agente}', periodo='{self.periodo}')>"


class Report(Base):
    """
    Informes finales generados
    """
    __tablename__ = "reports"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("categorias.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    periodo: Mapped[str] = mapped_column(
        String(20), 
        nullable=False,
        index=True
    )  # YYYY-MM
    estado: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="draft"
    )  # draft, review, published
    contenido: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500))
    generado_por: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    metricas_calidad: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Relationships
    categoria: Mapped["Categoria"] = relationship("Categoria", back_populates="reports")
    
    __table_args__ = (
        Index('idx_report_categoria_periodo', 'categoria_id', 'periodo', unique=True),
        CheckConstraint(
            "estado IN ('draft', 'review', 'published')",
            name="check_estado_report_valido"
        ),
    )
    
    def __repr__(self):
        return f"<Report(id={self.id}, periodo='{self.periodo}', estado='{self.estado}')>"


class Embedding(Base):
    """
    Embeddings para RAG (búsqueda de contexto histórico)
    Usa pgvector para búsqueda de similitud
    """
    __tablename__ = "embeddings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("categorias.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    periodo: Mapped[str] = mapped_column(
        String(20), 
        nullable=False,
        index=True
    )
    tipo: Mapped[str] = mapped_column(
        String(50), 
        nullable=False
    )  # query_execution, analysis_result, report
    referencia_id: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[Any] = mapped_column(Vector(1536))  # OpenAI embedding dimension
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    categoria: Mapped["Categoria"] = relationship("Categoria", back_populates="embeddings")
    
    __table_args__ = (
        Index('idx_embedding_categoria_periodo', 'categoria_id', 'periodo'),
        Index('idx_embedding_tipo_referencia', 'tipo', 'referencia_id'),
    )
    
    def __repr__(self):
        return f"<Embedding(id={self.id}, tipo='{self.tipo}', periodo='{self.periodo}')>"


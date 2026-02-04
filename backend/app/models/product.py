"""
Modelo unificado de Produto para múltiplos marketplaces.
Design: Domain-Driven Design com suporte a extensões futuras.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
import hashlib


class Marketplace(str, Enum):
    """Marketplaces suportados."""
    SHOPEE = "shopee"
    ALIEXPRESS = "aliexpress"
    SHEIN = "shein"
    AMAZON = "amazon"
    CUSTOM = "custom"


class ProductPrice(BaseModel):
    """Informações de preço com moeda e desconto."""
    amount: float = Field(..., gt=0, description="Preço em unidades da moeda")
    currency: str = Field(default="BRL", description="Código da moeda ISO 4217")
    original_amount: Optional[float] = Field(default=None, description="Preço original antes desconto")
    discount_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    
    @property
    def discount_amount(self) -> Optional[float]:
        """Calcula diferença de preço se houver desconto."""
        if self.original_amount and self.original_amount > self.amount:
            return self.original_amount - self.amount
        return None


class ProductImage(BaseModel):
    """Metadados de imagem do produto."""
    url: str = Field(..., description="URL da imagem")
    alt_text: Optional[str] = None
    is_primary: bool = Field(default=False, description="Imagem principal/destaque")
    position: int = Field(default=0, description="Ordem na galeria")


class ProductAttribute(BaseModel):
    """Atributo genérico (cor, tamanho, etc)."""
    name: str
    value: str
    category: Optional[str] = None  # "color", "size", "material", etc


class ProductMetadata(BaseModel):
    """Metadados de origem e tracking."""
    marketplace: Marketplace
    marketplace_id: str = Field(..., description="ID único no marketplace")
    source_url: str = Field(..., description="URL original")
    scrape_timestamp: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    scrape_hash: Optional[str] = None  # hash para detectar mudanças
    
    def compute_hash(self, content: str) -> str:
        """Computa hash SHA256 do conteúdo."""
        return hashlib.sha256(content.encode()).hexdigest()


class Product(BaseModel):
    """
    Modelo unificado de Produto com suporte multi-marketplace.
    """
    # Identifikação
    id: Optional[str] = None
    name: str = Field(..., min_length=5, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    
    # Preço e Disponibilidade
    price: ProductPrice
    stock: Optional[int] = Field(default=None, ge=0, description="Quantidade disponível")
    is_available: bool = Field(default=True)
    
    # Imagens
    images: List[ProductImage] = Field(default_factory=list)
    
    # Atributos e Características
    attributes: List[ProductAttribute] = Field(default_factory=list, description="Variações/specs")
    features: List[str] = Field(default_factory=list, description="Características principais")
    categories: List[str] = Field(default_factory=list, description="Categorias hierárquicas")
    
    # Rating e Reviews
    rating: Optional[float] = Field(None, ge=0, le=5, description="Nota média")
    review_count: int = Field(default=0)
    seller_rating: Optional[float] = Field(None, ge=0, le=5)
    seller_name: Optional[str] = None
    
    # Metadata
    metadata: ProductMetadata
    
    # Dados para IA/ML
    raw_data: Optional[Dict[str, Any]] = Field(default=None, description="Dados brutos do scraper")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
    
    @validator('price')
    def validate_price(cls, v: ProductPrice):
        """Valida consistência de preço."""
        if v.original_amount and v.original_amount < v.amount:
            raise ValueError("Preço original não pode ser menor que preço atual")
        return v
    
    @property
    def cache_key(self) -> str:
        """Chave única para cache Redis."""
        return f"product:{self.metadata.marketplace}:{self.metadata.marketplace_id}"
    
    @property
    def display_name(self) -> str:
        """Nome formatado para exibição."""
        return f"{self.name[:100]}..." if len(self.name) > 100 else self.name


class ProductCreateRequest(BaseModel):
    """Request para criar/atualizar produto (entrada)."""
    url: str = Field(..., description="URL do produto")
    marketplace: Marketplace


class ProductResponse(BaseModel):
    """Response com dados do produto para API."""
    id: str
    name: str
    price: ProductPrice
    images: List[ProductImage]
    rating: Optional[float]
    review_count: int
    marketplace: Marketplace
    source_url: str
    seller_name: Optional[str]


class BulkProductResponse(BaseModel):
    """Response para busca de múltiplos produtos."""
    total: int
    products: List[ProductResponse]
    cache_hit: bool = Field(default=False, description="Se dados vieram de cache")

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
import hashlib

class Marketplace(str, Enum):
    SHOPEE = "shopee"
    ALIEXPRESS = "aliexpress"
    SHEIN = "shein"
    AMAZON = "amazon"
    CUSTOM = "custom"

class ProductPrice(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(default="BRL")
    original_amount: Optional[float] = Field(default=None)
    discount_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    
    @property
    def discount_amount(self) -> Optional[float]:
        if self.original_amount and self.original_amount > self.amount:
            return self.original_amount - self.amount
        return None

class ProductImage(BaseModel):
    url: str
    alt_text: Optional[str] = None
    is_primary: bool = Field(default=False)
    position: int = Field(default=0)

class ProductAttribute(BaseModel):
    name: str
    value: str
    category: Optional[str] = None

class ProductMetadata(BaseModel):
    marketplace: Marketplace
    marketplace_id: str
    source_url: str
    scrape_timestamp: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    scrape_hash: Optional[str] = None
    
    def compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

class Product(BaseModel):
    # Nova Configuração Pydantic v2
    model_config = ConfigDict(
        protected_namespaces=(),
        json_encoders={datetime: lambda v: v.isoformat()}
    )

    id: Optional[str] = None
    name: str = Field(..., min_length=5, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    price: ProductPrice
    stock: Optional[int] = Field(default=None, ge=0)
    is_available: bool = Field(default=True)
    images: List[ProductImage] = Field(default_factory=list)
    attributes: List[ProductAttribute] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: int = Field(default=0)
    seller_rating: Optional[float] = Field(None, ge=0, le=5)
    seller_name: Optional[str] = None
    metadata: ProductMetadata
    raw_data: Optional[Dict[str, Any]] = None

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: ProductPrice):
        if v.original_amount and v.original_amount < v.amount:
            raise ValueError("Preço original não pode ser menor que preço atual")
        return v
    
    @property
    def cache_key(self) -> str:
        return f"product:{self.metadata.marketplace}:{self.metadata.marketplace_id}"

class ProductCreateRequest(BaseModel):
    url: str
    marketplace: Marketplace

class ProductResponse(BaseModel):
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
    total: int
    products: List[ProductResponse]
    cache_hit: bool = False
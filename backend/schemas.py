"""
Database Schemas for the Fashion E-commerce Platform
Each Pydantic model represents a MongoDB collection (collection name = class name lowercased).
"""
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr

# Core users
class User(BaseModel):
    email: EmailStr
    password_hash: str
    name: str
    role: str = Field(default="buyer", description="buyer | seller | admin")
    avatar: Optional[str] = None
    phone: Optional[str] = None
    addresses: List[dict] = Field(default_factory=list)
    is_active: bool = True

# Products
class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(ge=0)
    category: str
    images: List[str] = Field(default_factory=list)
    rating: float = 4.7
    reviews: int = 0
    stock: int = 0
    colors: List[str] = Field(default_factory=list)
    sizes: List[str] = Field(default_factory=list)
    seller_id: Optional[str] = None
    sale_price: Optional[float] = None
    tags: List[str] = Field(default_factory=list)

# Wishlist
class Wishlist(BaseModel):
    user_id: str
    product_id: str

# Cart items
class Cart(BaseModel):
    user_id: str
    items: List[dict] = Field(default_factory=list)

# Orders
class Order(BaseModel):
    user_id: str
    items: List[dict]  # [{product_id, qty, price}]
    total: float
    status: str = Field(default="new", description="new|paid|shipped|completed|cancelled")
    payment_method: str = Field(default="cod")
    address: dict

# Chat messages
class Chat(BaseModel):
    room_id: str  # could be f"{buyer_id}:{seller_id}"
    sender_id: str
    message: str
    role: str = Field(default="user")  # user|assistant


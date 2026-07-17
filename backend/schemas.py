"""Stockei - Pydantic schemas das APIs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- Users ----------
class UserOut(ORMModel):
    id: int
    email: str
    name: str
    role: str
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None


# ---------- Customers ----------
class CustomerIn(BaseModel):
    name: str
    cnpj: str
    email: EmailStr
    phone: str = ""
    plan: str = "pilot"


class CustomerOut(ORMModel):
    id: int
    name: str
    cnpj: str
    email: str
    phone: str
    plan: str
    status: str
    created_at: datetime


# ---------- Stores ----------
class StoreIn(BaseModel):
    customer_id: int
    name: str
    address: str = ""
    city: str = ""
    state: str = ""


class StoreOut(ORMModel):
    id: int
    customer_id: int
    name: str
    address: str
    city: str
    state: str
    created_at: datetime


# ---------- Cameras ----------
class CameraIn(BaseModel):
    store_id: int
    name: str
    location: str = ""


class CameraOut(ORMModel):
    id: int
    store_id: int
    name: str
    location: str
    status: str
    last_seen: datetime | None
    created_at: datetime


# ---------- Products ----------
class ProductIn(BaseModel):
    store_id: int
    sku: str
    name: str
    category: str = ""
    price: float = 0.0


class ProductOut(ORMModel):
    id: int
    store_id: int
    sku: str
    name: str
    category: str
    price: float
    brand: str = ""
    size_value: float | None = None
    size_unit: str = ""
    name_raw: str = ""
    source: str = "manual"
    created_at: datetime


# ---------- Inventory ----------
class InventoryOut(ORMModel):
    id: int
    product_id: int
    quantity: int
    last_count: int
    last_counted_at: datetime | None
    expiry_date: datetime | None = None


class CountRequest(BaseModel):
    product_id: int
    quantity: int


# ---------- Movements ----------
class MovementIn(BaseModel):
    product_id: int
    quantity: int
    type: str = Field(pattern="^(in|out|adjustment)$")


class MovementOut(ORMModel):
    id: int
    product_id: int
    quantity: int
    type: str
    user_id: int | None
    timestamp: datetime

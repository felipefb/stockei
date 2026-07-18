"""
Stockei - SQLAlchemy models
Schema completo do banco (ver docs/marco1/database_documentation.md).
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="operator")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    cnpj: Mapped[str] = mapped_column(String(18), unique=True)
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(20), default="")
    plan: Mapped[str] = mapped_column(String(50), default="pilot")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stores: Mapped[list["Store"]] = relationship(back_populates="customer")


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(255), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    state: Mapped[str] = mapped_column(String(2), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped[Customer] = relationship(back_populates="stores")
    cameras: Mapped[list["Camera"]] = relationship(back_populates="store")
    products: Mapped[list["Product"]] = relationship(back_populates="store")


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="offline")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    store: Mapped[Store] = relationship(back_populates="cameras")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (Index("ix_products_store_sku", "store_id", "sku", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    sku: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(100), default="")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    # Campos normalizados (preenchidos pelo backend/normalizer.py)
    brand: Mapped[str] = mapped_column(String(100), default="")
    size_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    size_unit: Mapped[str] = mapped_column(String(10), default="")
    name_raw: Mapped[str] = mapped_column(String(500), default="")
    source: Mapped[str] = mapped_column(String(30), default="manual")  # manual|gtin|ocr
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    store: Mapped[Store] = relationship(back_populates="products")
    inventory: Mapped["Inventory"] = relationship(back_populates="product", uselist=False)


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), unique=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    last_count: Mapped[int] = mapped_column(Integer, default=0)
    last_counted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    product: Mapped[Product] = relationship(back_populates="inventory")


class Movement(Base):
    __tablename__ = "movements"
    __table_args__ = (Index("ix_movements_product_ts", "product_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20))  # in | out | adjustment
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class InventorySession(Base):
    """Evento de inventário: abrir → contar → aprovar (gera ajustes) ou descartar."""

    __tablename__ = "inventory_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|approved|discarded
    accuracy_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    counts: Mapped[list["InventoryCount"]] = relationship(back_populates="session")


class InventoryCount(Base):
    """Contagem de um produto dentro de uma sessão (expected vs counted)."""

    __tablename__ = "inventory_counts"
    __table_args__ = (Index("ix_invcount_session_product", "session_id", "product_id",
                            unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("inventory_sessions.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    expected: Mapped[int] = mapped_column(Integer, default=0)
    counted: Mapped[int] = mapped_column(Integer, default=0)
    counted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped[InventorySession] = relationship(back_populates="counts")


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    face_encoding: Mapped[str] = mapped_column(Text, default="")
    role: Mapped[str] = mapped_column(String(50), default="employee")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MovementTracking(Base):
    __tablename__ = "movement_tracking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movement_id: Mapped[int] = mapped_column(ForeignKey("movements.id"), index=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

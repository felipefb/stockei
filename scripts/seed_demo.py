"""
Stockei - Popula o banco com dados realistas para a apresentação.
Uso: python scripts/seed_demo.py  (com o servidor parado ou rodando — usa o banco direto)
"""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import models
from backend.database import Base, SessionLocal, engine
from backend.normalizer import normalize_product

PRODUCTS = [
    # (ean, texto cru, preço, estoque)
    ("7898625211122", "Vigor Grego Tradicional Iogurte 90 g", 4.99, 24),
    ("7894900011517", "REFRIGERANTE COCA-COLA ORIGINAL GARRAFA 2L", 9.99, 36),
    ("7891000100103", "Nestle Leite Moca Lata 395 g", 8.49, 18),
    ("7891149104403", "Cerveja Heineken Long Neck 330 ml", 6.99, 48),
    ("7891910000197", "Acucar Uniao Refinado 1 kg", 5.29, 30),
    ("7896036090244", "Arroz Tio Joao Branco 5 kg", 27.90, 12),
    ("7891024134702", "Colgate Creme Dental Total 12 90 g", 7.99, 40),
    ("7891150056465", "Omo Sabao em Po Lavagem Perfeita 1,6 kg", 21.90, 8),
    ("7896098900217", "Cafe Pilao Torrado e Moido 500 g", 18.90, 15),
    ("7891991010023", "Guarana Antarctica Refrigerante 2 l", 8.49, 4),   # alerta
    ("7896004400013", "Leite Italac Integral 1 l", 4.79, 3),             # alerta
    ("6937232308298", "Lenyes Porta Cartao Magnetico Fibra de Aramida", 49.90, 2),  # alerta
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(models.User).first()
        store = db.query(models.Store).first()
        if store is None:
            customer = models.Customer(name="Mercado Demo", cnpj="00.000.000/0001-00",
                                       email="demo@stockei.com.br")
            db.add(customer)
            db.flush()
            store = models.Store(customer_id=customer.id, name="Loja Centro",
                                 city="São Paulo", state="SP")
            db.add(store)
            db.flush()

        created = 0
        for ean, raw, price, qty in PRODUCTS:
            if db.query(models.Product).filter(models.Product.sku == ean).first():
                continue
            n = normalize_product(raw)
            product = models.Product(
                store_id=store.id, sku=ean, name=n["display_name"],
                brand=n["brand"] or "", category=n["category"] or "",
                size_value=n["size_value"], size_unit=n["size_unit"] or "",
                name_raw=raw, source="gtin", price=price,
            )
            db.add(product)
            db.flush()
            db.add(models.Inventory(product_id=product.id, quantity=qty,
                                    last_count=qty, last_counted_at=datetime.utcnow()))
            # histórico de movimentações dos últimos 7 dias
            for _ in range(random.randint(2, 5)):
                db.add(models.Movement(
                    product_id=product.id,
                    quantity=random.randint(1, 6),
                    type=random.choice(["in", "out", "out"]),
                    user_id=user.id if user else None,
                    timestamp=datetime.utcnow() - timedelta(
                        days=random.randint(0, 7), hours=random.randint(0, 12)),
                ))
            created += 1
        db.commit()
        total = db.query(models.Product).count()
        print(f"Seed concluído: {created} produtos novos ({total} no catálogo).")
    finally:
        db.close()


if __name__ == "__main__":
    main()

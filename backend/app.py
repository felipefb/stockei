"""
Stockei - API principal (FastAPI)
Rodar: uvicorn backend.app:app --reload
Docs:  http://localhost:8000/docs
"""

import logging
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import Base, engine, get_db
from backend.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stockei.api")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Stockei API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringir ao domínio do portal em produção
    allow_methods=["*"],
    allow_headers=["*"],
)

_bearer = HTTPBearer(auto_error=False)

# Fluxo de frames (captura -> fila -> YOLOv8 -> WebSocket)
from backend.frame_processing_api import mount as _mount_frames  # noqa: E402

_mount_frames(app)

# Portal e frontend estáticos (demo local)
import pathlib  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402

_ROOT = pathlib.Path(__file__).resolve().parent.parent
for _dir in ("portal", "frontend"):
    _path = _ROOT / _dir
    if _path.is_dir():
        app.mount(f"/{_dir}", StaticFiles(directory=_path, html=True), name=_dir)

# Rate limiting simples em memória (produção: Redis)
_RATE_LIMIT = 100  # req/min por IP
_rate_state: dict[str, list[float]] = {}


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    import time

    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = [t for t in _rate_state.get(ip, []) if now - t < 60]
    if len(window) >= _RATE_LIMIT:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    window.append(now)
    _rate_state[ip] = window
    return await call_next(request)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ---------- Health ----------
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ---------- Auth ----------
@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(body: schemas.UserRegister, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(
        email=body.email, password_hash=hash_password(body.password), name=body.name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User registered: %s", user.email)
    return user


@app.post("/auth/login", response_model=schemas.TokenPair)
def login(body: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return schemas.TokenPair(
        access_token=create_token(str(user.id), "access"),
        refresh_token=create_token(str(user.id), "refresh"),
    )


@app.post("/auth/refresh", response_model=schemas.TokenPair)
def refresh(body: schemas.RefreshRequest):
    payload = decode_token(body.refresh_token, expected_type="refresh")
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return schemas.TokenPair(
        access_token=create_token(payload["sub"], "access"),
        refresh_token=create_token(payload["sub"], "refresh"),
    )


@app.post("/auth/logout", status_code=204)
def logout(user: models.User = Depends(get_current_user)):
    # JWT stateless: logout é responsabilidade do cliente (descartar tokens).
    # Produção: blocklist de tokens em Redis.
    return None


# ---------- Users ----------
@app.get("/users/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@app.put("/users/me", response_model=schemas.UserOut)
def update_me(
    body: schemas.UserUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.name is not None:
        user.name = body.name
    db.commit()
    db.refresh(user)
    return user


@app.get("/users/{user_id}", response_model=schemas.UserOut)
def get_user(
    user_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---------- CRUD genérico ----------
def _get_or_404(db: Session, model, obj_id: int):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return obj


# Customers
@app.get("/customers", response_model=list[schemas.CustomerOut])
def list_customers(
    _: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(models.Customer).all()


@app.post("/customers", response_model=schemas.CustomerOut, status_code=201)
def create_customer(
    body: schemas.CustomerIn,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if db.query(models.Customer).filter(models.Customer.cnpj == body.cnpj).first():
        raise HTTPException(status_code=409, detail="CNPJ already registered")
    customer = models.Customer(**body.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@app.get("/customers/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(
    customer_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_or_404(db, models.Customer, customer_id)


@app.put("/customers/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(
    customer_id: int,
    body: schemas.CustomerIn,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = _get_or_404(db, models.Customer, customer_id)
    for key, value in body.model_dump().items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


@app.delete("/customers/{customer_id}", status_code=204)
def delete_customer(
    customer_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = _get_or_404(db, models.Customer, customer_id)
    db.delete(customer)
    db.commit()
    return None


# Stores
@app.get("/stores", response_model=list[schemas.StoreOut])
def list_stores(_: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.Store).all()


@app.post("/stores", response_model=schemas.StoreOut, status_code=201)
def create_store(
    body: schemas.StoreIn,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_or_404(db, models.Customer, body.customer_id)
    store = models.Store(**body.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@app.get("/stores/{store_id}", response_model=schemas.StoreOut)
def get_store(
    store_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_or_404(db, models.Store, store_id)


@app.put("/stores/{store_id}", response_model=schemas.StoreOut)
def update_store(
    store_id: int,
    body: schemas.StoreIn,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_or_404(db, models.Store, store_id)
    for key, value in body.model_dump().items():
        setattr(store, key, value)
    db.commit()
    db.refresh(store)
    return store


# Cameras
@app.get("/cameras", response_model=list[schemas.CameraOut])
def list_cameras(_: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.Camera).all()


@app.post("/cameras", response_model=schemas.CameraOut, status_code=201)
def create_camera(
    body: schemas.CameraIn,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_or_404(db, models.Store, body.store_id)
    camera = models.Camera(**body.model_dump())
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@app.get("/cameras/{camera_id}", response_model=schemas.CameraOut)
def get_camera(
    camera_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_or_404(db, models.Camera, camera_id)


@app.put("/cameras/{camera_id}", response_model=schemas.CameraOut)
def update_camera(
    camera_id: int,
    body: schemas.CameraIn,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    camera = _get_or_404(db, models.Camera, camera_id)
    for key, value in body.model_dump().items():
        setattr(camera, key, value)
    db.commit()
    db.refresh(camera)
    return camera


# Products
@app.get("/products", response_model=list[schemas.ProductOut])
def list_products(
    _: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(models.Product).all()


@app.post("/products", response_model=schemas.ProductOut, status_code=201)
def create_product(
    body: schemas.ProductIn,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_or_404(db, models.Store, body.store_id)
    product = models.Product(**body.model_dump())
    db.add(product)
    db.flush()
    db.add(models.Inventory(product_id=product.id, quantity=0))
    db.commit()
    db.refresh(product)
    return product


@app.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(
    product_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_or_404(db, models.Product, product_id)


@app.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    body: schemas.ProductIn,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = _get_or_404(db, models.Product, product_id)
    for key, value in body.model_dump().items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


# Inventory
@app.get("/inventory", response_model=list[schemas.InventoryOut])
def list_inventory(
    _: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(models.Inventory).all()


@app.post("/inventory/count", response_model=schemas.InventoryOut)
def count_inventory(
    body: schemas.CountRequest,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inv = (
        db.query(models.Inventory)
        .filter(models.Inventory.product_id == body.product_id)
        .first()
    )
    if inv is None:
        raise HTTPException(status_code=404, detail="Inventory not found")
    inv.last_count = inv.quantity
    inv.quantity = body.quantity
    inv.last_counted_at = datetime.utcnow()
    db.commit()
    db.refresh(inv)
    return inv


@app.get("/inventory/count/{inventory_id}", response_model=schemas.InventoryOut)
def get_count(
    inventory_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_or_404(db, models.Inventory, inventory_id)


# Movements
@app.get("/movements", response_model=list[schemas.MovementOut])
def list_movements(
    _: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(models.Movement).order_by(models.Movement.timestamp.desc()).limit(100).all()


@app.post("/movements", response_model=schemas.MovementOut, status_code=201)
def create_movement(
    body: schemas.MovementIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_or_404(db, models.Product, body.product_id)
    movement = models.Movement(**body.model_dump(), user_id=user.id)
    db.add(movement)
    inv = (
        db.query(models.Inventory)
        .filter(models.Inventory.product_id == body.product_id)
        .first()
    )
    if inv is not None:
        delta = body.quantity if body.type == "in" else -body.quantity
        if body.type == "adjustment":
            inv.quantity = body.quantity
        else:
            inv.quantity = max(0, inv.quantity + delta)
    db.commit()
    db.refresh(movement)
    return movement

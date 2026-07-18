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
_RATE_LIMIT = 600  # req/min por IP (streaming de camera: 3-5 FPS = 180-300 req/min)
_RATE_EXEMPT = ("/process-frame", "/ws/")  # fluxo continuo de frames não conta
_rate_state: dict[str, list[float]] = {}


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    import time

    if request.url.path.startswith(_RATE_EXEMPT):
        return await call_next(request)

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


# ---------- Identificação por código de barras (EAN) ----------
def _demo_store(db: Session, user: models.User) -> models.Store:
    """Garante cliente/loja demo para cadastros feitos pelo scanner do portal."""
    store = db.query(models.Store).first()
    if store is None:
        customer = models.Customer(
            name="Demo", cnpj=f"demo-{user.id}", email=user.email
        )
        db.add(customer)
        db.flush()
        store = models.Store(customer_id=customer.id, name="Loja Demo")
        db.add(store)
        db.flush()
    return store


@app.get("/identify/{ean}")
def identify(
    ean: str,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Identifica produto pelo código de barras (sku=EAN) com estoque atual."""
    product = db.query(models.Product).filter(models.Product.sku == ean).first()
    if product is None:
        from backend.product_lookup import lookup_ean

        suggestion = lookup_ean(ean)
        return {
            "found": False,
            "ean": ean,
            "suggested_name": suggestion["name"] if suggestion else None,
            "suggestion_source": suggestion["source"] if suggestion else None,
        }
    inv = (
        db.query(models.Inventory)
        .filter(models.Inventory.product_id == product.id)
        .first()
    )
    return {
        "found": True,
        "ean": ean,
        "product": schemas.ProductOut.model_validate(product).model_dump(),
        "quantity": inv.quantity if inv else 0,
    }


class RegisterByEan(schemas.BaseModel):
    name: str
    source: str = "manual"  # manual | gtin | ocr
    store_id: int | None = None  # loja destino; None = loja demo


@app.post("/identify/{ean}/register", status_code=201)
def register_by_ean(
    ean: str,
    body: RegisterByEan,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cadastra produto novo a partir do EAN escaneado, com dados normalizados."""
    if db.query(models.Product).filter(models.Product.sku == ean).first():
        raise HTTPException(status_code=409, detail="EAN already registered")
    if body.store_id is not None:
        store = _get_or_404(db, models.Store, body.store_id)
    else:
        store = _demo_store(db, user)

    from backend.normalizer import normalize_product

    norm = normalize_product(body.name)
    product = models.Product(
        store_id=store.id,
        sku=ean,
        name=norm["display_name"],
        brand=norm["brand"] or "",
        category=norm["category"] or "",
        size_value=norm["size_value"],
        size_unit=norm["size_unit"] or "",
        name_raw=norm["name_raw"],
        source=body.source,
    )
    db.add(product)
    db.flush()
    db.add(models.Inventory(product_id=product.id, quantity=0))
    db.commit()
    db.refresh(product)
    return {"found": True, "ean": ean,
            "product": schemas.ProductOut.model_validate(product).model_dump(),
            "quantity": 0}


from fastapi import File, UploadFile  # noqa: E402


@app.post("/identify/suggest-from-image")
async def suggest_from_image(
    frame: UploadFile = File(...),
    _: models.User = Depends(get_current_user),
):
    """Lê a embalagem no frame (OCR local) e sugere a descrição do produto."""
    data = await frame.read()
    try:
        from backend.vision_identify import read_package

        return read_package(data)
    except Exception as exc:
        logger.warning("vision indisponível: %s", exc)
        return {"suggested_name": None, "texts": [], "error": str(exc)}


@app.post("/identify/scan-frame")
async def scan_frame(
    frame: UploadFile = File(...),
    _: models.User = Depends(get_current_user),
):
    """
    Escaneamento unificado: UMA passada de OCR no frame extrai ao mesmo tempo
    a sugestão de nome do produto e a data de validade (aceita datas vencidas,
    sinalizadas com expired=true). O código de barras é lido no cliente.
    """
    from backend.vision_identify import read_package
    from ml.date_validation import extract_date

    from backend.vision_identify import enhance_for_ocr

    def _find_expiry(texts):
        for t in texts:
            result = extract_date(t["text"])
            if result["date"]:  # data plausível (válida OU vencida)
                is_expired = result.get("error") == "Produto vencido"
                if result["valid"] or is_expired:
                    return {"date": result["date"], "expired": is_expired,
                            "source_text": t["text"]}
        return None

    data = await frame.read()
    try:
        package = read_package(data)
    except Exception as exc:
        logger.warning("OCR indisponível: %s", exc)
        return {"suggested_name": None, "expiry": None, "error": str(exc)}

    expiry = _find_expiry(package["texts"])

    # datas de jato de tinta/baixo contraste: segunda passada com realce
    if expiry is None:
        try:
            enhanced = read_package(enhance_for_ocr(data))
            expiry = _find_expiry(enhanced["texts"])
        except Exception as exc:
            logger.debug("passada com realce falhou: %s", exc)

    return {"suggested_name": package["suggested_name"], "expiry": expiry}


@app.post("/identify/expiry-from-image")
async def expiry_from_image(
    frame: UploadFile = File(...),
    _: models.User = Depends(get_current_user),
):
    """Lê a data de validade da embalagem no frame (OCR local RapidOCR)."""
    from backend.vision_identify import read_package
    from ml.date_validation import extract_date

    data = await frame.read()
    try:
        texts = read_package(data)["texts"]
    except Exception as exc:
        logger.warning("OCR indisponível: %s", exc)
        return {"valid": False, "error": f"OCR indisponível: {exc}"}

    # tenta extrair uma data válida de qualquer texto lido
    best = None
    for t in texts:
        result = extract_date(t["text"])
        if result["valid"]:
            return {**result, "source_text": t["text"]}
        if result["raw"] and best is None:
            best = {**result, "source_text": t["text"]}
    return best or {"valid": False, "date": None, "raw": "",
                    "error": "Nenhuma data encontrada", "suggestions": []}


class SetExpiry(schemas.BaseModel):
    expiry_date: str  # ISO: YYYY-MM-DD


@app.post("/identify/{ean}/expiry")
def set_expiry(
    ean: str,
    body: SetExpiry,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Grava a data de validade do lote atual no inventário do produto."""
    product = db.query(models.Product).filter(models.Product.sku == ean).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    inv = (
        db.query(models.Inventory)
        .filter(models.Inventory.product_id == product.id)
        .first()
    )
    if inv is None:
        inv = models.Inventory(product_id=product.id, quantity=0)
        db.add(inv)
    try:
        inv.expiry_date = datetime.fromisoformat(body.expiry_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Data inválida (use YYYY-MM-DD)")
    db.commit()
    days_left = (inv.expiry_date.date() - datetime.utcnow().date()).days
    return {"ean": ean, "product_name": product.name,
            "expiry_date": inv.expiry_date.date().isoformat(), "days_left": days_left}


@app.post("/identify/ai-suggest")
async def ai_suggest(
    frame: UploadFile = File(...),
    _: models.User = Depends(get_current_user),
):
    """Identificação por IA multimodal (sob demanda; respeita teto diário)."""
    from backend.ai_identify import AILimitReached, identify_package, usage_stats

    data = await frame.read()
    try:
        result = identify_package(data)
        return {**result, "usage": usage_stats()}
    except AILimitReached as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception as exc:
        logger.warning("IA indisponível: %s", exc)
        raise HTTPException(status_code=503, detail=f"IA indisponível: {exc}")


@app.get("/ai/usage")
def ai_usage(_: models.User = Depends(get_current_user)):
    """Contador de uso e custo estimado da identificação por IA."""
    from backend.ai_identify import usage_stats

    return usage_stats()


class StockIn(schemas.BaseModel):
    quantity: int = 1


@app.post("/identify/{ean}/stock-in")
def stock_in_by_ean(
    ean: str,
    body: StockIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirma entrada em estoque do produto escaneado."""
    product = db.query(models.Product).filter(models.Product.sku == ean).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db.add(models.Movement(product_id=product.id, quantity=body.quantity,
                           type="in", user_id=user.id))
    inv = (
        db.query(models.Inventory)
        .filter(models.Inventory.product_id == product.id)
        .first()
    )
    if inv is None:
        inv = models.Inventory(product_id=product.id, quantity=0)
        db.add(inv)
    inv.quantity += body.quantity
    db.commit()
    return {"ean": ean, "product_name": product.name, "quantity": inv.quantity}


# ---------- Sessões de Inventário (P16) ----------
class SessionCreate(schemas.BaseModel):
    store_id: int


class CountIn(schemas.BaseModel):
    ean: str
    counted: int


def _session_detail(db: Session, sess: models.InventorySession) -> dict:
    items = []
    divergent = 0
    for c in sess.counts:
        product = db.get(models.Product, c.product_id)
        diff = c.counted - c.expected
        divergent += diff != 0
        items.append({
            "product_id": c.product_id, "name": product.name if product else "?",
            "sku": product.sku if product else "", "expected": c.expected,
            "counted": c.counted, "diff": diff,
        })
    total = len(items)
    return {
        "id": sess.id, "store_id": sess.store_id, "status": sess.status,
        "created_at": sess.created_at.isoformat(),
        "closed_at": sess.closed_at.isoformat() if sess.closed_at else None,
        "accuracy_pct": sess.accuracy_pct,
        "items": sorted(items, key=lambda i: (i["diff"] == 0, i["name"])),
        "total_items": total, "divergent_items": divergent,
    }


@app.get("/inventory/sessions")
def list_sessions(
    store_id: int | None = None,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.InventorySession).order_by(models.InventorySession.id.desc())
    if store_id is not None:
        q = q.filter(models.InventorySession.store_id == store_id)
    return [
        {"id": s.id, "store_id": s.store_id, "status": s.status,
         "created_at": s.created_at.isoformat(), "accuracy_pct": s.accuracy_pct,
         "items": len(s.counts)}
        for s in q.limit(50).all()
    ]


@app.post("/inventory/sessions", status_code=201)
def open_session(
    body: SessionCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_or_404(db, models.Store, body.store_id)
    open_exists = (
        db.query(models.InventorySession)
        .filter(models.InventorySession.store_id == body.store_id,
                models.InventorySession.status == "open")
        .first()
    )
    if open_exists:
        raise HTTPException(status_code=409,
                            detail=f"Sessão {open_exists.id} já está aberta nesta loja")
    sess = models.InventorySession(store_id=body.store_id, user_id=user.id)
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return _session_detail(db, sess)


@app.get("/inventory/sessions/{session_id}")
def get_session(
    session_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _session_detail(db, _get_or_404(db, models.InventorySession, session_id))


@app.post("/inventory/sessions/{session_id}/counts")
def record_count(
    session_id: int,
    body: CountIn,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sess = _get_or_404(db, models.InventorySession, session_id)
    if sess.status != "open":
        raise HTTPException(status_code=409, detail="Sessão não está aberta")
    product = (
        db.query(models.Product)
        .filter(models.Product.sku == body.ean,
                models.Product.store_id == sess.store_id)
        .first()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado nesta loja")
    inv = (
        db.query(models.Inventory)
        .filter(models.Inventory.product_id == product.id)
        .first()
    )
    expected = inv.quantity if inv else 0

    count = (
        db.query(models.InventoryCount)
        .filter(models.InventoryCount.session_id == sess.id,
                models.InventoryCount.product_id == product.id)
        .first()
    )
    if count is None:
        count = models.InventoryCount(session_id=sess.id, product_id=product.id)
        db.add(count)
    count.expected = expected
    count.counted = body.counted
    count.counted_at = datetime.utcnow()
    db.commit()
    return {"product": product.name, "expected": expected,
            "counted": body.counted, "diff": body.counted - expected}


@app.post("/inventory/sessions/{session_id}/approve")
def approve_session(
    session_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aprova a sessão: gera ajustes para as divergências e fecha com acuracidade."""
    sess = _get_or_404(db, models.InventorySession, session_id)
    if sess.status != "open":
        raise HTTPException(status_code=409, detail="Sessão não está aberta")
    if not sess.counts:
        raise HTTPException(status_code=422, detail="Sessão sem contagens")

    adjustments = 0
    for c in sess.counts:
        if c.counted == c.expected:
            continue
        db.add(models.Movement(product_id=c.product_id, quantity=c.counted,
                               type="adjustment", user_id=user.id))
        inv = (
            db.query(models.Inventory)
            .filter(models.Inventory.product_id == c.product_id)
            .first()
        )
        if inv is None:
            inv = models.Inventory(product_id=c.product_id)
            db.add(inv)
        inv.last_count = inv.quantity
        inv.quantity = c.counted
        inv.last_counted_at = datetime.utcnow()
        adjustments += 1

    sess.status = "approved"
    sess.closed_at = datetime.utcnow()
    sess.accuracy_pct = round(100 * (len(sess.counts) - adjustments) / len(sess.counts), 1)
    db.commit()
    return {"session_id": sess.id, "adjustments": adjustments,
            "accuracy_pct": sess.accuracy_pct}


@app.post("/inventory/sessions/{session_id}/discard")
def discard_session(
    session_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sess = _get_or_404(db, models.InventorySession, session_id)
    if sess.status != "open":
        raise HTTPException(status_code=409, detail="Sessão não está aberta")
    sess.status = "discarded"
    sess.closed_at = datetime.utcnow()
    db.commit()
    return {"session_id": sess.id, "status": sess.status}


@app.get("/inventory/position")
def inventory_position(
    date: str | None = None,
    store_id: int | None = None,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Posição de estoque na data (fim do dia), reconstruída pelo replay dos
    movimentos (in soma, out subtrai, adjustment define o valor absoluto).
    Sem data, retorna a posição atual.
    """
    products_q = db.query(models.Product)
    if store_id is not None:
        products_q = products_q.filter(models.Product.store_id == store_id)
    products = products_q.all()

    if date is None:
        cutoff = None
    else:
        try:
            cutoff = datetime.fromisoformat(date).replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=422, detail="Data inválida (use YYYY-MM-DD)")

    rows = []
    for product in products:
        if cutoff is None:
            inv = (
                db.query(models.Inventory)
                .filter(models.Inventory.product_id == product.id)
                .first()
            )
            qty = inv.quantity if inv else 0
        else:
            qty = 0
            movements = (
                db.query(models.Movement)
                .filter(models.Movement.product_id == product.id,
                        models.Movement.timestamp <= cutoff)
                .order_by(models.Movement.timestamp)
                .all()
            )
            for m in movements:
                if m.type == "in":
                    qty += m.quantity
                elif m.type == "out":
                    qty = max(0, qty - m.quantity)
                else:  # adjustment define valor absoluto
                    qty = m.quantity
        rows.append({"sku": product.sku, "name": product.name, "quantity": qty,
                     "value": round(qty * (product.price or 0), 2)})

    return {"date": date or "atual", "store_id": store_id,
            "total_units": sum(r["quantity"] for r in rows),
            "total_value": round(sum(r["value"] for r in rows), 2),
            "items": sorted(rows, key=lambda r: -r["value"])}


# ---------- Export ----------
@app.get("/inventory/export.csv")
def export_inventory_csv(
    store_id: int | None = None,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exporta o inventário em CSV (Excel-friendly, ; como separador)."""
    import csv
    import io

    from fastapi.responses import StreamingResponse

    query = (
        db.query(models.Product, models.Inventory, models.Store)
        .outerjoin(models.Inventory, models.Inventory.product_id == models.Product.id)
        .join(models.Store, models.Store.id == models.Product.store_id)
    )
    if store_id is not None:
        query = query.filter(models.Product.store_id == store_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow([
        "loja", "ean", "produto", "marca", "categoria", "tamanho", "unidade",
        "preco", "quantidade", "valor_total", "ultima_contagem_em",
    ])
    for product, inv, store in query.all():
        qty = inv.quantity if inv else 0
        writer.writerow([
            store.name, product.sku, product.name, product.brand, product.category,
            product.size_value if product.size_value is not None else "",
            product.size_unit,
            f"{product.price:.2f}".replace(".", ","),
            qty,
            f"{qty * (product.price or 0):.2f}".replace(".", ","),
            inv.last_counted_at.isoformat() if inv and inv.last_counted_at else "",
        ])

    buffer.seek(0)
    filename = f"stockei_inventario_{datetime.utcnow():%Y%m%d}.csv"
    return StreamingResponse(
        iter(["﻿" + buffer.getvalue()]),  # BOM para acentos no Excel
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------- Dashboard ----------
LOW_STOCK_THRESHOLD = 5


@app.get("/dashboard/summary")
def dashboard_summary(
    store_id: int | None = None,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resumo executivo do estoque: valor, categorias, alertas e movimentações."""
    products_q = (
        db.query(models.Product, models.Inventory)
        .outerjoin(models.Inventory, models.Inventory.product_id == models.Product.id)
    )
    if store_id is not None:
        products_q = products_q.filter(models.Product.store_id == store_id)
    rows = products_q.all()

    total_units = 0
    stock_value = 0.0
    low_stock = []
    by_category: dict[str, dict] = {}
    for product, inv in rows:
        qty = inv.quantity if inv else 0
        total_units += qty
        stock_value += qty * (product.price or 0)
        if qty < LOW_STOCK_THRESHOLD:
            low_stock.append({"name": product.name, "quantity": qty, "sku": product.sku})
        cat = product.category or "Sem categoria"
        agg = by_category.setdefault(cat, {"category": cat, "units": 0, "value": 0.0})
        agg["units"] += qty
        agg["value"] = round(agg["value"] + qty * (product.price or 0), 2)

    recent_q = (
        db.query(models.Movement, models.Product)
        .join(models.Product, models.Product.id == models.Movement.product_id)
    )
    if store_id is not None:
        recent_q = recent_q.filter(models.Product.store_id == store_id)
    recent = recent_q.order_by(models.Movement.timestamp.desc()).limit(10).all()

    # validade: vencidos e vencendo em ate 30 dias
    today = datetime.utcnow().date()
    expiring = []
    for product, inv in rows:
        if inv is None or inv.expiry_date is None or (inv.quantity or 0) == 0:
            continue
        days_left = (inv.expiry_date.date() - today).days
        if days_left <= 30:
            expiring.append({
                "name": product.name, "sku": product.sku,
                "quantity": inv.quantity,
                "value": round(inv.quantity * (product.price or 0), 2),
                "expiry_date": inv.expiry_date.date().isoformat(),
                "days_left": days_left,
            })
    expiring.sort(key=lambda i: i["days_left"])

    return {
        "total_products": len(rows),
        "total_units": total_units,
        "stock_value": round(stock_value, 2),
        "expiring": expiring[:10],
        "expiring_value": round(sum(i["value"] for i in expiring), 2),
        "low_stock": sorted(low_stock, key=lambda i: i["quantity"])[:10],
        "by_category": sorted(by_category.values(), key=lambda c: -c["units"]),
        "recent_movements": [
            {
                "product": product.name,
                "type": movement.type,
                "quantity": movement.quantity,
                "timestamp": movement.timestamp.isoformat(),
            }
            for movement, product in recent
        ],
    }


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

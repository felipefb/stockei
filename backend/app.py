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

# imagens coletadas para curadoria do dataset (ml/image_scraper.py)
_SCRAPED = _ROOT / "ml" / "dataset" / "scraped"
_SCRAPED.mkdir(parents=True, exist_ok=True)
app.mount("/scraped", StaticFiles(directory=_SCRAPED), name="scraped")

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


# Estoque mínimo padrão por categoria (giro típico do varejo de bairro)
MIN_STOCK_BY_CATEGORY = {
    "Bebidas": 12, "Laticínios": 8, "Mercearia": 10,
    "Higiene": 6, "Limpeza": 6, "Medicamentos": 10, "Acessórios": 3,
}
DEFAULT_MIN_STOCK = 5


class RegisterByEan(schemas.BaseModel):
    name: str
    source: str = "manual"  # manual | gtin | ocr
    store_id: int | None = None  # loja destino; None = loja demo
    price: float = 0.0
    min_stock: int | None = None  # None = padrão inteligente por categoria


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
        price=body.price or 0.0,
    )
    db.add(product)
    db.flush()
    min_stock = body.min_stock if body.min_stock is not None else \
        MIN_STOCK_BY_CATEGORY.get(norm["category"] or "", DEFAULT_MIN_STOCK)
    db.add(models.Inventory(product_id=product.id, quantity=0, min_stock=min_stock))
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
    mode: str | None = None,
    _: models.User = Depends(get_current_user),
):
    """
    Escaneamento unificado: UMA passada de OCR no frame extrai ao mesmo tempo
    a sugestão de nome do produto e a data de validade (aceita datas vencidas,
    sinalizadas com expired=true). O código de barras é lido no cliente; o
    zxing-cpp do servidor cobre os que o navegador não decodifica.
    mode=barcode: só decodifica o código (sem OCR — barato para o loop ocioso).
    """
    from backend.vision_identify import enhance_for_ocr, read_package
    from ml.date_validation import extract_best_expiry

    def _decode_barcode(image_bytes):
        """Fallback de servidor: zxing-cpp decodifica quando o navegador falha."""
        try:
            import io as _io

            import zxingcpp
            from PIL import Image

            img = Image.open(_io.BytesIO(image_bytes)).convert("RGB")
            for r in zxingcpp.read_barcodes(img):
                text = r.text.strip()
                if text and len(text) >= 8 and text.isdigit():
                    return text
        except Exception as exc:
            logger.debug("zxing indisponível: %s", exc)
        return None

    def _find_expiry(texts):
        # Junta os textos numa linha só para o classificador enxergar o rótulo
        # (V/VAL) mesmo quando o OCR quebra "VAL 05/26" em blocos separados;
        # também roda por bloco como reforço.
        joined = " ".join(t["text"] for t in texts)
        for candidate in (joined, *[t["text"] for t in texts]):
            result = extract_best_expiry(candidate)
            if result["date"]:  # data plausível (válida OU vencida)
                is_expired = result.get("error") == "Produto vencido"
                if result["valid"] or is_expired:
                    return {"date": result["date"], "expired": is_expired,
                            "source_text": result["raw"]}
        return None

    data = await frame.read()

    if mode == "barcode":  # loop ocioso procurando código: pula o OCR
        ean = _decode_barcode(data)
        if ean is None:
            try:
                ean = _decode_barcode(enhance_for_ocr(data))
            except Exception:
                pass
        return {"suggested_name": None, "expiry": None, "ean": ean}

    try:
        package = read_package(data)
    except Exception as exc:
        logger.warning("OCR indisponível: %s", exc)
        return {"suggested_name": None, "expiry": None, "error": str(exc)}

    expiry = _find_expiry(package["texts"])
    ean = _decode_barcode(data)

    # datas de jato de tinta/baixo contraste: segunda passada com realce
    if expiry is None or ean is None:
        try:
            enhanced_bytes = enhance_for_ocr(data)
            if expiry is None:
                expiry = _find_expiry(read_package(enhanced_bytes)["texts"])
            if ean is None:
                ean = _decode_barcode(enhanced_bytes)
        except Exception as exc:
            logger.debug("passada com realce falhou: %s", exc)

    return {"suggested_name": package["suggested_name"], "expiry": expiry, "ean": ean}


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


@app.post("/identify/expiry-ai")
async def expiry_ai(
    frame: UploadFile = File(...),
    _: models.User = Depends(get_current_user),
):
    """Leitura de validade por IA multimodal — fallback quando o OCR local falha
    (sob demanda, respeita o mesmo teto diário da identificação)."""
    from backend.ai_identify import AILimitReached, read_expiry, usage_stats

    data = await frame.read()
    try:
        result = read_expiry(data)
    except AILimitReached as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception as exc:
        logger.warning("IA indisponível: %s", exc)
        raise HTTPException(status_code=503, detail=f"IA indisponível: {exc}")

    expiry = None
    if result.get("expiry_date"):
        try:
            parsed = datetime.fromisoformat(result["expiry_date"])
            expiry = {"date": parsed.date().isoformat(),
                      "expired": parsed.date() < datetime.utcnow().date(),
                      "source_text": result.get("raw_text") or "IA"}
        except ValueError:
            logger.warning("IA devolveu data não-ISO: %r", result["expiry_date"])
    return {"expiry": expiry, "confidence": result.get("confidence"),
            "usage": usage_stats()}


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


# ---------- Conferência de Recebimento — NF-e vs câmera (P10) ----------
def _receiving_detail(db: Session, sess: models.ReceivingSession) -> dict:
    items = []
    for it in sess.items:
        registered = (
            db.query(models.Product).filter(models.Product.sku == it.ean).first()
            is not None if it.ean else False
        )
        items.append({
            "id": it.id, "ean": it.ean, "description": it.description,
            "expected_qty": it.expected_qty, "checked_qty": it.checked_qty,
            "unit_cost": it.unit_cost, "status": it.item_status,
            "registered": registered,
        })
    order = {"pendente": 0, "divergente": 1, "excedente": 2, "conferido": 3}
    items.sort(key=lambda i: (order.get(i["status"], 9), i["description"]))
    done = sum(i["status"] != "pendente" for i in items)
    return {
        "id": sess.id, "store_id": sess.store_id, "status": sess.status,
        "nfe_key": sess.nfe_key, "supplier": sess.supplier,
        "issued_at": sess.issued_at.isoformat() if sess.issued_at else None,
        "created_at": sess.created_at.isoformat(),
        "closed_at": sess.closed_at.isoformat() if sess.closed_at else None,
        "items": items, "total_items": len(items), "checked_items": done,
        "total_value": round(sum(i["expected_qty"] * i["unit_cost"] for i in items), 2),
    }


@app.post("/receiving/upload-xml", status_code=201)
async def receiving_upload_xml(
    xml: UploadFile = File(...),
    store_id: int | None = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Importa o XML da NF-e de entrada e abre a conferência de recebimento."""
    from backend.nfe_parser import NFEParseError, parse_nfe

    data = await xml.read()
    try:
        nfe = parse_nfe(data)
    except NFEParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if store_id is not None:
        store = _get_or_404(db, models.Store, store_id)
    else:
        store = _demo_store(db, user)

    if nfe["key"]:
        duplicate = (
            db.query(models.ReceivingSession)
            .filter(models.ReceivingSession.nfe_key == nfe["key"],
                    models.ReceivingSession.status != "discarded")
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail=f"NF-e já importada na conferência {duplicate.id}")

    sess = models.ReceivingSession(
        store_id=store.id, user_id=user.id, nfe_key=nfe["key"],
        supplier=nfe["supplier"], issued_at=nfe["issued_at"],
    )
    db.add(sess)
    db.flush()
    for item in nfe["items"]:
        db.add(models.ReceivingItem(
            session_id=sess.id, ean=item["ean"], description=item["description"],
            expected_qty=item["qty"], unit_cost=item["unit_cost"],
        ))
    db.commit()
    db.refresh(sess)
    return _receiving_detail(db, sess)


@app.get("/receiving")
def list_receiving(
    store_id: int | None = None,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.ReceivingSession).order_by(models.ReceivingSession.id.desc())
    if store_id is not None:
        q = q.filter(models.ReceivingSession.store_id == store_id)
    return [
        {"id": s.id, "supplier": s.supplier, "status": s.status,
         "created_at": s.created_at.isoformat(), "items": len(s.items),
         "checked": sum(i.item_status != "pendente" for i in s.items)}
        for s in q.limit(50).all()
    ]


@app.get("/receiving/{session_id}")
def get_receiving(
    session_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _receiving_detail(db, _get_or_404(db, models.ReceivingSession, session_id))


class ReceivingCheck(schemas.BaseModel):
    ean: str
    qty: float = 1


@app.post("/receiving/{session_id}/check")
def receiving_check(
    session_id: int,
    body: ReceivingCheck,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dá baixa no checklist pelo EAN escaneado (soma qty ao conferido)."""
    sess = _get_or_404(db, models.ReceivingSession, session_id)
    if sess.status != "open":
        raise HTTPException(status_code=409, detail="Conferência não está aberta")
    item = (
        db.query(models.ReceivingItem)
        .filter(models.ReceivingItem.session_id == sess.id,
                models.ReceivingItem.ean == body.ean)
        .first()
    )
    if item is None:  # veio na entrega mas não está na nota
        item = models.ReceivingItem(
            session_id=sess.id, ean=body.ean, description=f"Excedente {body.ean}",
            expected_qty=0, checked_qty=0, item_status="excedente",
        )
        db.add(item)
    item.checked_qty += body.qty
    if item.expected_qty > 0:
        item.item_status = ("conferido" if item.checked_qty == item.expected_qty
                            else "divergente")
    db.commit()
    return {"ean": item.ean, "description": item.description,
            "expected_qty": item.expected_qty, "checked_qty": item.checked_qty,
            "status": item.item_status}


@app.post("/receiving/{session_id}/close")
def receiving_close(
    session_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fecha a conferência: o que foi CONFERIDO entra no estoque (movimento in),
    o custo da nota atualiza o cost_price (alimenta o Smart Pricing) e produtos
    desconhecidos são cadastrados automaticamente a partir da descrição da nota.
    """
    from backend.normalizer import normalize_product

    sess = _get_or_404(db, models.ReceivingSession, session_id)
    if sess.status != "open":
        raise HTTPException(status_code=409, detail="Conferência não está aberta")

    entered = 0
    registered = []
    divergences = []
    for it in sess.items:
        if it.expected_qty > 0 and it.checked_qty != it.expected_qty:
            divergences.append({
                "ean": it.ean, "description": it.description,
                "expected_qty": it.expected_qty, "checked_qty": it.checked_qty,
                "status": "faltou" if it.checked_qty < it.expected_qty else "sobrou",
            })
        if it.expected_qty > 0 and it.checked_qty == 0:
            it.item_status = "divergente"
        qty = int(it.checked_qty)
        if qty <= 0:
            continue
        product = None
        inv = None
        if it.ean:
            product = (
                db.query(models.Product).filter(models.Product.sku == it.ean).first()
            )
        if product is None and it.ean:
            norm = normalize_product(it.description)
            product = models.Product(
                store_id=sess.store_id, sku=it.ean, name=norm["display_name"],
                brand=norm["brand"] or "", category=norm["category"] or "",
                size_value=norm["size_value"], size_unit=norm["size_unit"] or "",
                name_raw=norm["name_raw"], source="nfe",
            )
            db.add(product)
            db.flush()
            min_stock = MIN_STOCK_BY_CATEGORY.get(norm["category"] or "",
                                                  DEFAULT_MIN_STOCK)
            inv = models.Inventory(product_id=product.id, quantity=0,
                                   min_stock=min_stock)
            db.add(inv)
            registered.append({"ean": it.ean, "name": product.name})
        if product is None:
            continue  # item sem EAN: não movimenta estoque automaticamente
        if it.unit_cost > 0:
            product.cost_price = it.unit_cost
        db.add(models.Movement(product_id=product.id, quantity=qty, type="in",
                               unit_value=it.unit_cost, user_id=user.id,
                               note=f"NF-e {sess.nfe_key[-8:] if sess.nfe_key else sess.id}"))
        if inv is None:
            inv = (
                db.query(models.Inventory)
                .filter(models.Inventory.product_id == product.id)
                .first()
            )
        if inv is None:
            inv = models.Inventory(product_id=product.id, quantity=0)
            db.add(inv)
        inv.quantity += qty
        entered += qty

    sess.status = "closed"
    sess.closed_at = datetime.utcnow()
    db.commit()
    return {"session_id": sess.id, "entered_units": entered,
            "auto_registered": registered, "divergences": divergences}


@app.post("/receiving/{session_id}/discard")
def receiving_discard(
    session_id: int,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sess = _get_or_404(db, models.ReceivingSession, session_id)
    if sess.status != "open":
        raise HTTPException(status_code=409, detail="Conferência não está aberta")
    sess.status = "discarded"
    sess.closed_at = datetime.utcnow()
    db.commit()
    return {"session_id": sess.id, "status": sess.status}


# ---------- Perdas e Quebras (P11) ----------
LOSS_REASONS = ("vencimento", "avaria", "furto", "erro_cadastro", "consumo_interno")


class LossIn(schemas.BaseModel):
    ean: str
    quantity: int = 1
    reason: str
    note: str = ""


@app.post("/losses", status_code=201)
def register_loss(
    body: LossIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registra perda: baixa o estoque e valoriza pelo preço de venda atual."""
    if body.reason not in LOSS_REASONS:
        raise HTTPException(
            status_code=422,
            detail=f"Motivo inválido. Use um de: {', '.join(LOSS_REASONS)}")
    if body.quantity <= 0:
        raise HTTPException(status_code=422, detail="Quantidade deve ser positiva")
    product = db.query(models.Product).filter(models.Product.sku == body.ean).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    db.add(models.Movement(product_id=product.id, quantity=body.quantity,
                           type="loss", reason=body.reason, note=body.note,
                           unit_value=product.price or 0, user_id=user.id))
    inv = (
        db.query(models.Inventory)
        .filter(models.Inventory.product_id == product.id)
        .first()
    )
    if inv is not None:
        inv.quantity = max(0, inv.quantity - body.quantity)
        if body.reason == "vencimento" and inv.quantity == 0:
            inv.expiry_date = None  # lote vencido saiu inteiro: limpa o alerta
    db.commit()
    value = round(body.quantity * (product.price or 0), 2)
    return {"ean": body.ean, "product_name": product.name,
            "quantity": body.quantity, "reason": body.reason,
            "value": value, "stock_after": inv.quantity if inv else 0}


@app.get("/losses/report")
def losses_report(
    days: int = 30,
    store_id: int | None = None,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Perdas do período: total em R$, por motivo e por produto + índice de perdas."""
    from datetime import timedelta

    since = datetime.utcnow() - timedelta(days=days)
    q = (
        db.query(models.Movement, models.Product)
        .join(models.Product, models.Product.id == models.Movement.product_id)
        .filter(models.Movement.type == "loss", models.Movement.timestamp >= since)
    )
    if store_id is not None:
        q = q.filter(models.Product.store_id == store_id)

    total_value = 0.0
    total_units = 0
    by_reason: dict[str, dict] = {}
    by_product: dict[str, dict] = {}
    for mv, product in q.all():
        value = round(mv.quantity * (mv.unit_value or product.price or 0), 2)
        total_value += value
        total_units += mv.quantity
        r = by_reason.setdefault(mv.reason or "sem_motivo",
                                 {"reason": mv.reason or "sem_motivo",
                                  "units": 0, "value": 0.0})
        r["units"] += mv.quantity
        r["value"] = round(r["value"] + value, 2)
        p = by_product.setdefault(product.sku, {
            "sku": product.sku, "name": product.name, "units": 0, "value": 0.0})
        p["units"] += mv.quantity
        p["value"] = round(p["value"] + value, 2)

    # índice de perdas: % sobre o valor do estoque atual (meta varejo: < 2%)
    inv_q = (
        db.query(models.Product, models.Inventory)
        .outerjoin(models.Inventory, models.Inventory.product_id == models.Product.id)
    )
    if store_id is not None:
        inv_q = inv_q.filter(models.Product.store_id == store_id)
    stock_value = sum((inv.quantity if inv else 0) * (prod.price or 0)
                      for prod, inv in inv_q.all())
    loss_pct = round(100 * total_value / stock_value, 2) if stock_value else None

    return {
        "days": days, "total_value": round(total_value, 2),
        "total_units": total_units, "loss_pct_of_stock": loss_pct,
        "target_pct": 2.0,
        "by_reason": sorted(by_reason.values(), key=lambda r: -r["value"]),
        "by_product": sorted(by_product.values(), key=lambda p: -p["value"])[:20],
    }


# ---------- Precificação Inteligente (P5) ----------
@app.get("/pricing/suggestions")
def pricing_suggestions(
    store_id: int | None = None,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sugestões de preço: desconto por validade próxima e recomposição de margem."""
    from backend.pricing import expiry_suggestion, margin_suggestion

    q = (
        db.query(models.Product, models.Inventory)
        .outerjoin(models.Inventory, models.Inventory.product_id == models.Product.id)
    )
    if store_id is not None:
        q = q.filter(models.Product.store_id == store_id)

    suggestions = []
    for product, inv in q.all():
        base = {"sku": product.sku, "name": product.name}
        s = expiry_suggestion(product, inv)
        if s:  # validade tem prioridade: dinheiro parado prestes a virar perda
            suggestions.append({**base, **s})
            continue
        s = margin_suggestion(product)
        if s:
            suggestions.append({**base, **s})

    order = {"validade": 0, "margem": 1}
    suggestions.sort(key=lambda s: (order[s["type"]], s.get("days_left", 999)))
    return {"suggestions": suggestions, "count": len(suggestions)}


class ApplyPrice(schemas.BaseModel):
    price: float


@app.post("/pricing/{ean}/apply")
def apply_price(
    ean: str,
    body: ApplyPrice,
    _: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aplica o preço sugerido (ou digitado) — decisão sempre do lojista."""
    if body.price < 0:
        raise HTTPException(status_code=422, detail="Preço inválido")
    product = db.query(models.Product).filter(models.Product.sku == ean).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product.price = round(body.price, 2)
    db.commit()
    return {"ean": ean, "name": product.name, "price": product.price}


# ---------- Curadoria do dataset (double-check humano) ----------
class CurateIn(schemas.BaseModel):
    file: str
    keep: bool
    true_date: str | None = None  # gabarito ISO YYYY-MM-DD quando houver data


@app.get("/dataset/pending")
def dataset_pending(_: models.User = Depends(get_current_user)):
    """Imagens coletadas aguardando curadoria."""
    import json as _json

    manifest_path = _SCRAPED / "manifest.json"
    if not manifest_path.exists():
        return {"pending": [], "kept": 0, "discarded": 0}
    manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
    pending = [{"file": k, "query": v.get("query", "")}
               for k, v in manifest.items() if v.get("status") == "pending"]
    return {
        "pending": pending[:200],
        "kept": sum(v.get("status") == "kept" for v in manifest.values()),
        "discarded": sum(v.get("status") == "discarded" for v in manifest.values()),
    }


@app.post("/dataset/curate")
def dataset_curate(
    body: CurateIn,
    _: models.User = Depends(get_current_user),
):
    """Registra o veredito humano: aprova (com gabarito) ou descarta."""
    import json as _json

    manifest_path = _SCRAPED / "manifest.json"
    manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
    if body.file not in manifest:
        raise HTTPException(status_code=404, detail="Imagem não está no manifest")
    entry = manifest[body.file]
    entry["status"] = "kept" if body.keep else "discarded"
    if body.true_date:
        try:
            datetime.fromisoformat(body.true_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Gabarito inválido (YYYY-MM-DD)")
        entry["true_date"] = body.true_date
    manifest_path.write_text(_json.dumps(manifest, indent=1), encoding="utf-8")

    if not body.keep:  # descartada sai do disco
        (_SCRAPED / body.file).unlink(missing_ok=True)
    return {"file": body.file, "status": entry["status"]}


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
        "preco", "quantidade", "estoque_minimo", "valor_total", "ultima_contagem_em",
    ])
    for product, inv, store in query.all():
        qty = inv.quantity if inv else 0
        writer.writerow([
            store.name, product.sku, product.name, product.brand, product.category,
            product.size_value if product.size_value is not None else "",
            product.size_unit,
            f"{product.price:.2f}".replace(".", ","),
            qty,
            inv.min_stock if inv else 5,
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
        # alerta respeita o estoque mínimo definido POR PRODUTO
        min_stock = inv.min_stock if inv else LOW_STOCK_THRESHOLD
        if qty < min_stock:
            low_stock.append({"name": product.name, "quantity": qty,
                              "min_stock": min_stock, "sku": product.sku})
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

    # perdas dos últimos 30 dias (P11) — o número que o dono sente no bolso
    from datetime import timedelta

    loss_q = (
        db.query(models.Movement, models.Product)
        .join(models.Product, models.Product.id == models.Movement.product_id)
        .filter(models.Movement.type == "loss",
                models.Movement.timestamp >= datetime.utcnow() - timedelta(days=30))
    )
    if store_id is not None:
        loss_q = loss_q.filter(models.Product.store_id == store_id)
    losses_30d = round(sum(
        mv.quantity * (mv.unit_value or product.price or 0)
        for mv, product in loss_q.all()), 2)

    return {
        "losses_30d": losses_30d,
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

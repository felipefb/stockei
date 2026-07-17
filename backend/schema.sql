-- Stockei - Schema PostgreSQL (referência; fonte de verdade: backend/models.py + Alembic)

CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name          VARCHAR(255) NOT NULL,
    role          VARCHAR(50)  NOT NULL DEFAULT 'operator',
    created_at    TIMESTAMP NOT NULL DEFAULT now(),
    updated_at    TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE customers (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    cnpj       VARCHAR(18) NOT NULL UNIQUE,
    email      VARCHAR(255) NOT NULL,
    phone      VARCHAR(20) NOT NULL DEFAULT '',
    plan       VARCHAR(50) NOT NULL DEFAULT 'pilot',
    status     VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE stores (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    name        VARCHAR(255) NOT NULL,
    address     VARCHAR(255) NOT NULL DEFAULT '',
    city        VARCHAR(100) NOT NULL DEFAULT '',
    state       VARCHAR(2) NOT NULL DEFAULT '',
    created_at  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_stores_customer_id ON stores(customer_id);

CREATE TABLE cameras (
    id         SERIAL PRIMARY KEY,
    store_id   INTEGER NOT NULL REFERENCES stores(id),
    name       VARCHAR(255) NOT NULL,
    location   VARCHAR(255) NOT NULL DEFAULT '',
    status     VARCHAR(20) NOT NULL DEFAULT 'offline',
    last_seen  TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_cameras_store_id ON cameras(store_id);

CREATE TABLE products (
    id         SERIAL PRIMARY KEY,
    store_id   INTEGER NOT NULL REFERENCES stores(id),
    sku        VARCHAR(64) NOT NULL,
    name       VARCHAR(255) NOT NULL,
    category   VARCHAR(100) NOT NULL DEFAULT '',
    price      DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (store_id, sku)
);
CREATE INDEX ix_products_name ON products(name);

CREATE TABLE inventory (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL UNIQUE REFERENCES products(id),
    quantity        INTEGER NOT NULL DEFAULT 0,
    last_count      INTEGER NOT NULL DEFAULT 0,
    last_counted_at TIMESTAMP
);

CREATE TABLE movements (
    id         SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL,
    type       VARCHAR(20) NOT NULL,
    user_id    INTEGER REFERENCES users(id),
    timestamp  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_movements_product_ts ON movements(product_id, timestamp);
CREATE INDEX ix_movements_timestamp ON movements(timestamp);

CREATE TABLE people (
    id            SERIAL PRIMARY KEY,
    store_id      INTEGER NOT NULL REFERENCES stores(id),
    name          VARCHAR(255) NOT NULL,
    face_encoding TEXT NOT NULL DEFAULT '',
    role          VARCHAR(50) NOT NULL DEFAULT 'employee',
    created_at    TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_people_store_id ON people(store_id);

CREATE TABLE movement_tracking (
    id          SERIAL PRIMARY KEY,
    movement_id INTEGER NOT NULL REFERENCES movements(id),
    person_id   INTEGER REFERENCES people(id),
    timestamp   TIMESTAMP NOT NULL DEFAULT now(),
    confidence  DOUBLE PRECISION NOT NULL DEFAULT 0
);
CREATE INDEX ix_movement_tracking_movement_id ON movement_tracking(movement_id);
CREATE INDEX ix_movement_tracking_timestamp ON movement_tracking(timestamp);

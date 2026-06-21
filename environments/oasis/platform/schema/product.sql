CREATE TABLE IF NOT EXISTS product (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    description TEXT DEFAULT '',
    price REAL DEFAULT 0.0,
    sales INTEGER DEFAULT 0
);

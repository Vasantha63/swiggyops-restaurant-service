from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import PlainTextResponse
import sqlite3
import uvicorn

app = FastAPI(title="SwiggyOps Restaurant Service")

# Prometheus metrics
request_counter = Counter("restaurant_requests_total", "Total requests", ["method", "endpoint"])
request_latency = Histogram("restaurant_request_latency_seconds", "Request latency")

# Database setup
def get_db():
    conn = sqlite3.connect("restaurants.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cuisine TEXT NOT NULL,
            rating REAL DEFAULT 0.0,
            is_open INTEGER DEFAULT 1,
            city TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT,
            is_available INTEGER DEFAULT 1
        )
    """)
    # Sample data
    conn.execute("INSERT OR IGNORE INTO restaurants (id, name, cuisine, rating, city) VALUES (1, 'Biryani House', 'Indian', 4.5, 'Hyderabad')")
    conn.execute("INSERT OR IGNORE INTO restaurants (id, name, cuisine, rating, city) VALUES (2, 'Pizza Palace', 'Italian', 4.2, 'Hyderabad')")
    conn.execute("INSERT OR IGNORE INTO menu_items (id, restaurant_id, name, price, category) VALUES (1, 1, 'Chicken Biryani', 180, 'Main Course')")
    conn.execute("INSERT OR IGNORE INTO menu_items (id, restaurant_id, name, price, category) VALUES (2, 1, 'Mutton Biryani', 220, 'Main Course')")
    conn.execute("INSERT OR IGNORE INTO menu_items (id, restaurant_id, name, price, category) VALUES (3, 2, 'Margherita Pizza', 299, 'Pizza')")
    conn.commit()
    conn.close()

init_db()

# Models
class Restaurant(BaseModel):
    name: str
    cuisine: str
    rating: Optional[float] = 0.0
    is_open: Optional[int] = 1
    city: str

class MenuItem(BaseModel):
    restaurant_id: int
    name: str
    price: float
    category: Optional[str] = None
    is_available: Optional[int] = 1

# Restaurant Routes
@app.get("/restaurants")
def get_restaurants():
    request_counter.labels(method="GET", endpoint="/restaurants").inc()
    conn = get_db()
    restaurants = conn.execute("SELECT * FROM restaurants").fetchall()
    conn.close()
    return [dict(r) for r in restaurants]

@app.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: int):
    request_counter.labels(method="GET", endpoint="/restaurants/id").inc()
    conn = get_db()
    restaurant = conn.execute("SELECT * FROM restaurants WHERE id=?", (restaurant_id,)).fetchone()
    conn.close()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return dict(restaurant)

@app.post("/restaurants")
def create_restaurant(restaurant: Restaurant):
    request_counter.labels(method="POST", endpoint="/restaurants").inc()
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO restaurants (name, cuisine, rating, is_open, city) VALUES (?, ?, ?, ?, ?)",
        (restaurant.name, restaurant.cuisine, restaurant.rating, restaurant.is_open, restaurant.city)
    )
    conn.commit()
    conn.close()
    return {"id": cursor.lastrowid, "message": "Restaurant created!"}

# Menu Routes
@app.get("/restaurants/{restaurant_id}/menu")
def get_menu(restaurant_id: int):
    request_counter.labels(method="GET", endpoint="/menu").inc()
    conn = get_db()
    items = conn.execute("SELECT * FROM menu_items WHERE restaurant_id=?", (restaurant_id,)).fetchall()
    conn.close()
    return [dict(i) for i in items]

@app.post("/menu")
def add_menu_item(item: MenuItem):
    request_counter.labels(method="POST", endpoint="/menu").inc()
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO menu_items (restaurant_id, name, price, category, is_available) VALUES (?, ?, ?, ?, ?)",
        (item.restaurant_id, item.name, item.price, item.category, item.is_available)
    )
    conn.commit()
    conn.close()
    return {"id": cursor.lastrowid, "message": "Menu item added!"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "restaurant-service"}

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return generate_latest()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
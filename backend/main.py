import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from database import db, create_document, get_documents
from schemas import User as UserSchema, Product as ProductSchema, Wishlist as WishlistSchema, Cart as CartSchema, Order as OrderSchema, Chat as ChatSchema
import hashlib
from bson import ObjectId

app = FastAPI(title="VibeFashion API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "VibeFashion Backend"}


@app.get("/test")
def test_database():
    from database import db as _db
    ok = _db is not None
    return {
        "backend": "✅ Running",
        "database": "✅ Connected" if ok else "❌ Not Connected",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": os.getenv("DATABASE_NAME") or "-",
        "collections": (list(_db.list_collection_names()) if ok else []),
    }


# ========== AUTH ==========
class RegisterPayload(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginPayload(BaseModel):
    email: EmailStr
    password: str


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


@app.post("/api/auth/register")
def register(body: RegisterPayload):
    if db is None:
        raise HTTPException(500, "Database not configured")
    # check exists
    existing = db["user"].find_one({"email": body.email})
    if existing:
        raise HTTPException(400, "Email already registered")
    user = UserSchema(email=body.email, password_hash=_hash(body.password), name=body.name)
    uid = create_document("user", user)
    return {"user_id": uid, "email": body.email, "name": body.name}


@app.post("/api/auth/login")
def login(body: LoginPayload):
    if db is None:
        raise HTTPException(500, "Database not configured")
    u = db["user"].find_one({"email": body.email})
    if not u:
        raise HTTPException(401, "Invalid credentials")
    if u.get("password_hash") != _hash(body.password):
        raise HTTPException(401, "Invalid credentials")
    return {"user_id": str(u.get("_id")), "email": u.get("email"), "name": u.get("name"), "role": u.get("role", "buyer")}


# ========== PRODUCTS ==========
class CreateProductPayload(ProductSchema):
    pass

@app.get("/api/products")
def list_products(q: Optional[str] = None, category: Optional[str] = None, limit: int = 24):
    if db is None:
        raise HTTPException(500, "Database not configured")
    filt = {}
    if q:
        filt["title"] = {"$regex": q, "$options": "i"}
    if category:
        filt["category"] = {"$regex": f"^{category}$", "$options": "i"}
    docs = db["product"].find(filt).limit(limit)
    res = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        res.append(d)
    return {"items": res}

@app.post("/api/products")
def create_product(body: CreateProductPayload):
    pid = create_document("product", body)
    return {"product_id": pid}

@app.post("/api/seed-products")
def seed_products():
    if db is None:
        raise HTTPException(500, "Database not configured")
    sample = [
        ProductSchema(
            title="Oversized Tee Minimal",
            description="Kaos oversized bahan cotton combed 24s, nyaman dan adem.",
            price=129000,
            sale_price=99000,
            category="Wanita",
            images=[
                "https://images.unsplash.com/photo-1487099174927-da3cd6408862?auto=format&fit=crop&w=1200&q=80"
            ],
            rating=4.6,
            reviews=128,
            stock=100,
            colors=["black","white","cream"],
            sizes=["S","M","L","XL"],
        ),
        ProductSchema(
            title="Cardigan Rajut Pastel",
            description="Cardigan rajut halus dengan palet pastel.",
            price=199000,
            category="Pria",
            images=[
                "https://images.unsplash.com/photo-1693592401248-c9544518318a?auto=format&fit=crop&w=1200&q=80"
            ],
            rating=4.8,
            reviews=342,
            stock=55,
            colors=["sage","rose","sky"],
            sizes=["S","M","L"],
        ),
        ProductSchema(
            title="Sneakers Putih Clean",
            description="Sneakers putih serbaguna dengan desain minimal.",
            price=359000,
            category="Unisex",
            images=[
                "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=1200&q=80"
            ],
            rating=4.7,
            reviews=521,
            stock=80,
            sizes=["38","39","40","41","42"],
        ),
        ProductSchema(
            title="Tote Bag Kanvas",
            description="Tote bag kanvas tebal untuk harian.",
            price=99000,
            category="Aksesoris",
            images=[
                "https://images.unsplash.com/photo-1511988617509-a57c8a288659?auto=format&fit=crop&w=1200&q=80"
            ],
            rating=4.5,
            reviews=213,
            stock=120,
        ),
    ]
    for p in sample:
        db["product"].insert_one({**p.model_dump(), "created_at": None, "updated_at": None})
    return {"seeded": len(sample)}


# ========== WISHLIST ==========
class WishlistPayload(BaseModel):
    user_id: str
    product_id: str

@app.get("/api/wishlist")
def get_wishlist(user_id: str):
    items = get_documents("wishlist", {"user_id": user_id})
    for i in items:
        i["id"] = str(i.pop("_id"))
    return {"items": items}

@app.post("/api/wishlist")
def add_wishlist(body: WishlistPayload):
    wid = create_document("wishlist", WishlistSchema(**body.model_dump()))
    return {"wishlist_id": wid}


# ========== CART ==========
class CartItemPayload(BaseModel):
    user_id: str
    product_id: str
    qty: int = 1

@app.get("/api/cart")
def get_cart(user_id: str):
    cart = db["cart"].find_one({"user_id": user_id})
    if not cart:
        cart = {"user_id": user_id, "items": []}
        db["cart"].insert_one(cart)
    cart["id"] = str(cart.pop("_id")) if cart.get("_id") else None
    return cart

@app.post("/api/cart")
def add_to_cart(body: CartItemPayload):
    c = db["cart"].find_one({"user_id": body.user_id})
    if not c:
        c = {"user_id": body.user_id, "items": []}
    # upsert product
    found = False
    for it in c["items"]:
        if it["product_id"] == body.product_id:
            it["qty"] += body.qty
            found = True
            break
    if not found:
        c["items"].append({"product_id": body.product_id, "qty": body.qty})
    db["cart"].update_one({"user_id": body.user_id}, {"$set": c}, upsert=True)
    return {"ok": True}


# ========== ORDERS ==========
class CreateOrderPayload(BaseModel):
    user_id: str
    items: List[dict]
    total: float
    payment_method: str = "cod"
    address: dict

@app.post("/api/orders")
def create_order(body: CreateOrderPayload):
    order = OrderSchema(
        user_id=body.user_id,
        items=body.items,
        total=body.total,
        payment_method=body.payment_method,
        address=body.address,
    )
    oid = create_document("order", order)
    # empty cart
    db["cart"].update_one({"user_id": body.user_id}, {"$set": {"items": []}}, upsert=True)
    return {"order_id": oid, "status": "new"}


# ========== CHAT ==========
class ChatSendPayload(BaseModel):
    room_id: str
    sender_id: str
    message: str

@app.get("/api/chat/{room_id}")
def get_chat(room_id: str, limit: int = 50):
    msgs = db["chat"].find({"room_id": room_id}).sort("created_at", -1).limit(limit)
    res = []
    for m in msgs:
        m["id"] = str(m.pop("_id"))
        res.append(m)
    return {"messages": list(reversed(res))}

@app.post("/api/chat")
def send_chat(body: ChatSendPayload):
    msg = ChatSchema(room_id=body.room_id, sender_id=body.sender_id, message=body.message)
    mid = create_document("chat", msg)
    return {"message_id": mid}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

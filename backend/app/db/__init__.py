from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import MONGO_URI

db = None
if MONGO_URI:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.get_default_database()
else:
    # For tests or missing config fallback to None
    db = None

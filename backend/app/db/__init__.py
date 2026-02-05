import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
# O nome do banco pode ser extraído da URI ou definido aqui
DB_NAME = "infinity_ads" 

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
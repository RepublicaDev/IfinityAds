import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "./firebase-key.json")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
HEYGEN_API_URL = os.getenv("HEYGEN_API_URL")
QWEN_API_ENDPOINT = os.getenv("QWEN_API_ENDPOINT")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")

import firebase_admin
from firebase_admin import credentials, auth, firestore
from app.core.config import FIREBASE_KEY_PATH, FIREBASE_JSON_CONTENT
import json
import logging

logger = logging.getLogger(__name__)

def initialize_firebase():
    """Inicializa o SDK do Firebase Admin."""
    try:
        if not firebase_admin._apps:
            # Prioriza o conteúdo da variável de ambiente (Render)
            if FIREBASE_JSON_CONTENT:
                cred_dict = json.loads(FIREBASE_JSON_CONTENT)
                cred = credentials.Certificate(cred_dict)
                logger.info("🔥 Firebase inicializado via variável de ambiente.")
            else:
                # Usa o arquivo físico (Local)
                cred = credentials.Certificate(FIREBASE_KEY_PATH)
                logger.info(f"🔥 Firebase inicializado via arquivo: {FIREBASE_KEY_PATH}")
            
            firebase_admin.initialize_app(cred)
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar Firebase: {e}")
        raise e

# Exporta o cliente do Firestore para uso nos services
db = firestore.client() if firebase_admin._apps else None
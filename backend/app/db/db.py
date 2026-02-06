import os
import logging
from typing import Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        # Usamos Any para evitar o erro "Variável não permitida na expressão de tipo"
        self.client: Any = None
        self._db: Any = None

    async def connect(self):
        """Inicializa a conexão com o MongoDB."""
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/ifinityads")
        try:
            # Inicialização direta
            self.client = AsyncIOMotorClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000
            )
            
            # Extrai o nome do banco
            db_name = mongo_uri.split("/")[-1].split("?")[0] or "ifinityads"
            self._db = self.client[db_name]
            
            # Teste de conexão
            await self.client.admin.command('ping')
            logger.info(f"✅ MongoDB conectado: {db_name}")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar no MongoDB: {e}")
            raise e

    async def close(self):
        """Fecha a conexão."""
        if self.client is not None:
            self.client.close()
            logger.info("MongoDB desconectado.")

    @property
    def database(self) -> Any:
        """Retorna a instância do banco de dados."""
        if self._db is None:
            raise RuntimeError("Database não inicializado. Chame connect() primeiro.")
        return self._db

# Instância única
db_wrapper = Database()
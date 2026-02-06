import httpx
import os
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class DIDService:
    def __init__(self):
        # D-ID requer a chave em formato Basic Auth. 
        # Geralmente é 'api_key:secret' ou apenas a chave codificada.
        self.api_key = os.getenv("DID_API_KEY", "")
        self.url = "https://api.d-id.com/talks"
        self.headers = {
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json",
            "accept": "application/json"
        }

    async def create_talk(self, image_url: str, text: str) -> Dict[str, Any]:
        """Solicita a criação de um vídeo de avatar falando."""
        if not self.api_key:
            raise ValueError("DID_API_KEY não configurada nas variáveis de ambiente.")

        payload = {
            "script": {
                "type": "text",
                "subtitles": "false",
                "provider": {"type": "microsoft", "voice_id": "pt-BR-AntonioNeural"},
                "ssml": "false",
                "input": text
            },
            "config": {"fluent": "false", "pad_audio": "0.0"},
            "source_url": image_url
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = cast(Dict[str, Any], response.json())
            logger.info(f"D-ID Talk criado com sucesso: {data.get('id')}")
            return data

    async def get_talk(self, talk_id: str) -> Dict[str, Any]:
        """Consulta o status e o resultado de um vídeo (Polling)."""
        url = f"{self.url}/{talk_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())

from typing import cast # Import necessário para o Pylance
import httpx
import os
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class DIDService:
    def __init__(self):
        self.api_key = os.getenv("DID_API_KEY", "")
        self.url = "https://api.d-id.com/talks"
        # D-ID usa Basic Auth com a chave da API
        self.headers = {
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json",
            "accept": "application/json"
        }

    async def create_talk(self, image_url: str, text: str) -> Optional[Dict[str, Any]]:
        """Solicita a criação de um vídeo de avatar falando."""
        if not self.api_key:
            logger.error("Chave de API do D-ID não configurada.")
            return None

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

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.url, json=payload, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                logger.info(f"D-ID Talk criado: {data.get('id')}")
                return data
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro na API D-ID ({e.response.status_code}): {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao chamar D-ID: {e}")
            raise
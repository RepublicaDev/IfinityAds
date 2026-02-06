import httpx
import os

class DIDService:
    def __init__(self):
        self.api_key = os.getenv("DID_API_KEY")
        self.url = "https://api.d-id.com/talks"
        self.headers = {
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json"
        }

    async def create_talk(self, image_url: str, text: str):
        payload = {
            "script": {
                "type": "text",
                "input": text,
                "provider": {"type": "microsoft", "voice_id": "pt-BR-AntonioNeural"}
            },
            "source_url": image_url
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(self.url, json=payload, headers=self.headers)
            return r.json() # Retorna o ID do vídeo para monitorar
import httpx
from app.core.config import HEYGEN_API_KEY, HEYGEN_API_URL

class HeyGenClient:
    def __init__(self):
        self.api_key = HEYGEN_API_KEY
        self.url = HEYGEN_API_URL

    async def render_video(self, script: str, voice_style: str = "commercial", avatar: str = "human") -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {"script": script, "voice_style": voice_style, "avatar": avatar}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(self.url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

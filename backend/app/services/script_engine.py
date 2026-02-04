import os
import httpx
from app.core.config import QWEN_API_ENDPOINT, QWEN_API_KEY

class ScriptEngine:
    def __init__(self, model="qwen-3"):
        self.model = model

    def build_prompt(self, product: dict, yt_insights: dict, style: str = "charismatic_fomo") -> str:
        evidences = yt_insights.get("evidence", [])
        prompt = (
            f"Crie um anúncio de 15-30s com tom {style} para o produto abaixo.\n"
            f"Produto: {product.get('title')}\n"
            f"Preço: {product.get('price')}\n"
            f"Características: {', '.join(product.get('features', []))}\n"
            f"Relatos reais dos usuários (evidências): {evidences}\n"
            "Regras: Não inventar informações. Usar evidências para confirmar benefícios e mitigar dúvidas. Usar FOMO e CTA claro."
        )
        return prompt

    async def call_llm(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {QWEN_API_KEY}"} if QWEN_API_KEY else {}
        payload = {"model": self.model, "prompt": prompt, "max_tokens": 300}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(QWEN_API_ENDPOINT, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("text") or data.get("output") or data.get("result") or str(data)

    async def generate(self, product: dict, yt_insights: dict, style: str = "charismatic_fomo") -> str:
        prompt = self.build_prompt(product, yt_insights, style)
        try:
            return await self.call_llm(prompt)
        except Exception:
            # deterministic fallback
            return f"Experimente {product.get('title')}! {product.get('features', [''])[0]}"

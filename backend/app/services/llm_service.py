from groq import AsyncGroq
import os

class LLMService:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"

    async def generate_ad_script(self, product_data: dict, style: str):
        prompt = f"Crie um roteiro de anúncio {style} para o produto: {product_data['name']}"
        
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return completion.choices[0].message.content
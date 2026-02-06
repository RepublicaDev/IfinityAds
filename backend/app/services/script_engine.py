class ScriptEngine:
    # ... build_prompt ...
    def build_prompt(self, product_data: dict, yt_insights: dict, style: str = "charismatic_fomo") -> str:
        # Garante que pega 'name' que é o campo do seu modelo
        name = product_data.get('name') or product_data.get('title') or "Produto"
        price = product_data.get('price', {}).get('amount') if isinstance(product_data.get('price'), dict) else product_data.get('price')
        
        evidences = yt_insights.get("positive_aspects", [])
        
        prompt = (
            f"Crie um anúncio de 15-30s com tom {style}.\n"
            f"Produto: {name}\n"
            f"Preço: {price}\n"
            f"Depoimentos: {', '.join(evidences[:3])}\n"
            "Gere um script focado em conversão."
        )
        return prompt
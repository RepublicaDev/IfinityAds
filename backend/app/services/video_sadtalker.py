import replicate
import os
from typing import Any

class SadTalkerService:
    def __init__(self):
        token = os.getenv("REPLICATE_API_TOKEN")
        if not token:
            raise ValueError("REPLICATE_API_TOKEN não configurada no .env")
        # Definir no os.environ garante que o cliente do Replicate encontre a chave
        os.environ["REPLICATE_API_TOKEN"] = token

    async def generate_video(self, image_path: str, audio_path: str) -> str:
        """
        Gera vídeo usando imagem e áudio.
        """
        try:
            # Replicate run é síncrono por padrão, mas o client pode ser usado de forma async 
            # se necessário. Para este exemplo, manteremos a chamada direta.
            output = replicate.run(
                "vinthony/sadtalker:3aa3dac93530283351f0888871628e1d9967ed5ddfad9ca9048a39027420213d",
                input={
                    "source_image": open(image_path, "rb"),
                    "driven_audio": open(audio_path, "rb"),
                    "still": True,
                    "preprocess": "full"
                }
            )
            return str(output)
        except Exception as e:
            raise RuntimeError(f"Erro no Replicate/SadTalker: {e}")
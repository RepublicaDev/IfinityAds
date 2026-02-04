from youtube_transcript_api import YouTubeTranscriptApi
import asyncio
import re
from typing import Dict

class YouTubeAnalyzer:
    def __init__(self):
        self.patterns = [
            r"(o ponto negativo é[\s\S]*?)(?:\.|\n|$)",
            r"(o que eu mais gostei foi[\s\S]*?)(?:\.|\n|$)",
            r"(recomendo[\s\S]*?)(?:\.|\n|$)",
            r"(não gostei[\s\S]*?)(?:\.|\n|$)",
        ]

    async def fetch_transcript(self, video_id: str) -> str:
        return await asyncio.to_thread(lambda: " ".join([s["text"] for s in YouTubeTranscriptApi.get_transcript(video_id)]))

    def extract_insights(self, transcript: str) -> Dict:
        matches = []
        for p in self.patterns:
            matches += re.findall(p, transcript, flags=re.IGNORECASE)
        positives = [m for m in matches if re.search(r"gostei|recomendo|bom|ótimo|excelente", m, flags=re.I)]
        negatives = [m for m in matches if re.search(r"não gostei|ponto negativo|ruim|problema", m, flags=re.I)]
        return {"raw": transcript, "positives": positives, "negatives": negatives, "evidence": matches}

    async def analyze(self, youtube_url: str) -> Dict:
        video_id = youtube_url.split("v=")[-1].split("&")[0]
        transcript = await self.fetch_transcript(video_id)
        return self.extract_insights(transcript)

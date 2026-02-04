from pydantic import BaseModel, Field
from typing import List, Optional

class AdCreate(BaseModel):
    product_url: str
    youtube_url: Optional[str]
    style: Optional[str] = "charismatic_fomo"

class AdDocument(BaseModel):
    job_id: str
    user_id: str
    product: dict
    yt_insights: dict
    script: Optional[str]
    video_result: Optional[dict]
    status: str = Field(default="queued")

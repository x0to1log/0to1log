from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class Post(BaseModel):
    id: str
    slug_en: str
    slug_ko: str
    title_en: str
    title_ko: str
    summary_en: Optional[str] = None
    summary_ko: Optional[str] = None
    status: str = "draft"
    created_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

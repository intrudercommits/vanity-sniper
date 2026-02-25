from pydantic import BaseModel
from typing import Dict, Optional
import json
import os


class Config(BaseModel):
    token: str
    password: str
    mode: str = "lookup"
    vanities: Dict[str, str]
    search_length: int = 3
    webhook_url: Optional[str] = None


def load_config() -> Config:
    if not os.path.exists("data/config.json"):
        raise FileNotFoundError(f"Config file not found")
    
    with open("data/config.json", "r") as f:
        config_data = json.load(f)
    
    return Config(**config_data)
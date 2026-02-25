from __future__ import annotations

import datetime
from typing import Optional

import aiohttp

try:
    from pydantic import BaseModel
except ImportError:
    import os
    os.system("pip install pydantic --quiet")
    from pydantic import BaseModel

from .logger import log


class WebhookField(BaseModel):
    name: str
    value: str
    inline: bool = True


class WebhookEmbed(BaseModel):
    title: str
    description: str
    color: int
    fields: list[WebhookField] = []
    footer_text: str = "Vanity Sniper"
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "color": self.color,
            "fields": [f.model_dump() for f in self.fields],
            "footer": {"text": self.footer_text},
            "timestamp": self.timestamp or datetime.datetime.utcnow().isoformat(),
        }


class WebhookPayload(BaseModel):
    embeds: list[WebhookEmbed]

    def to_dict(self) -> dict:
        return {"embeds": [e.to_dict() for e in self.embeds]}



async def send_webhook(
    webhook_url: str,
    vanity: str,
    guild_id: str,
    latency_ms: float,
    *,
    retries: int = 3,
) -> None:
    if not webhook_url:
        return

    payload = WebhookPayload(
        embeds=[
            WebhookEmbed(
                title="Sniped!",
                description=f"Successfully claimed **discord.gg/{vanity}**",
                color=0x9ad1d9,
                fields=[
                    WebhookField(name="Vanity",        value=f"`{vanity}`"),
                    WebhookField(name="Guild ID",       value=f"`{guild_id}`"),
                    WebhookField(name="Claim Latency",  value=f"`{latency_ms:.2f} ms`"),
                ],
            )
        ]
    )

    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload.to_dict()) as resp:
                    if resp.status in (200, 204):
                        log("SUCCESS", f"Webhook sent (attempt {attempt}).")
                        return
                    log("WARNING", f"Webhook HTTP {resp.status} on attempt {attempt}.")
        except Exception as exc:
            log("ERROR", f"Webhook error (attempt {attempt}): {exc}")

    log("ERROR", "All webhook attempts failed.")

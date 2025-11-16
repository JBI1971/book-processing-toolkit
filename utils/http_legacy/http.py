from __future__ import annotations
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class TransientHTTPError(Exception): ...

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    retry=retry_if_exception_type(TransientHTTPError),
)
def get_text(url: str, *, timeout: float = 15.0, headers: dict | None = None) -> str:
    try:
        r = httpx.get(url, timeout=timeout, headers=headers)
        if r.status_code >= 500:
            raise TransientHTTPError(f"Server error {r.status_code}")
        r.raise_for_status()
        return r.text
    except httpx.ConnectError as e:
        raise TransientHTTPError(str(e)) from e

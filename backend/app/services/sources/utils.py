import re
from datetime import UTC, datetime

from bs4 import BeautifulSoup


def clean_html(text: str | None) -> str:
    """Strip HTML markup and collapse excess whitespace into clean plain text."""
    if not text:
        return ""
    try:
        soup = BeautifulSoup(text, "html.parser")
        plain = soup.get_text(separator=" ", strip=True)
        return re.sub(r"\s+", " ", plain).strip()
    except Exception:
        # Fallback to regex-based tag removal
        stripped = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", stripped).strip()


def parse_iso_datetime(val: str | None) -> datetime | None:
    """Parse common ISO-8601 or RFC-2822 timestamps into UTC-aware datetimes."""
    if not val:
        return None
    try:
        clean = val.replace("Z", "+00:00")
        if "." in clean:
            base, frac = clean.split(".", 1)
            frac = frac[:6]
            clean = f"{base}.{frac}"
        dt = datetime.fromisoformat(clean)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None

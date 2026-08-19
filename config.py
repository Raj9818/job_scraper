import os
import random

from dotenv import load_dotenv


load_dotenv()


# =========================================================
# Helpers
# =========================================================

def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is missing."
        )

    return value


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None or value == "":
        return default

    try:
        return int(value)

    except ValueError:
        raise RuntimeError(
            f"Environment variable '{name}' must be an integer."
        )


def get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None or value == "":
        return default

    try:
        return float(value)

    except ValueError:
        raise RuntimeError(
            f"Environment variable '{name}' must be a number."
        )


# =========================================================
# Database
# =========================================================

DB_URL = get_required_env("DB_URL")


# =========================================================
# Source
# =========================================================

NAUKRI_BASE_URL = get_required_env(
    "NAUKRI_BASE_URL"
).rstrip("/")


# =========================================================
# Search configuration
# =========================================================

KEYWORD = get_required_env("KEYWORD")

LOCATION = os.getenv(
    "LOCATION",
    ""
)

MAX_PAGES = get_int_env(
    "MAX_PAGES",
    1
)

URLS_LIMIT = get_int_env(
    "URLS_LIMIT",
    20
)


# =========================================================
# Pacing
# =========================================================

MIN_DELAY = get_float_env(
    "MIN_DELAY",
    2.5
)

MAX_DELAY = get_float_env(
    "MAX_DELAY",
    7.0
)


# =========================================================
# Identity rotation
# =========================================================

REQUESTS_PER_IDENTITY = get_int_env(
    "REQUESTS_PER_IDENTITY",
    15
)


# =========================================================
# Circuit breaker
# =========================================================

MAX_CONSECUTIVE_FAILURES = get_int_env(
    "MAX_CONSECUTIVE_FAILURES",
    4
)

CIRCUIT_BREAK_COOLDOWN_SEC = get_int_env(
    "CIRCUIT_BREAK_COOLDOWN_SEC",
    900
)


# =========================================================
# Proxy pool
# =========================================================

PROXY_POOL = [
    proxy.strip()
    for proxy in os.getenv(
        "PROXY_POOL",
        ""
    ).split(",")
    if proxy.strip()
]


def get_proxy():
    if not PROXY_POOL:
        return None

    return random.choice(PROXY_POOL)


# =========================================================
# Selector version
# =========================================================

NAUKRI_SELECTOR_VERSION = os.getenv(
    "NAUKRI_SELECTOR_VERSION",
    "v1"
)


# =========================================================
# Naukri selectors
# =========================================================

NAUKRI_SELECTORS = {
    "v1": {
        "job_card": "div.cust-job-tuple",
        "title": "a.title",
        "company": "a.comp-name",
        "location": "span.locWdth",
        "experience": "span.expwdth",
        "link_attr": "href",
    }
}
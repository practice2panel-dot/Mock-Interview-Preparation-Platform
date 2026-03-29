"""
CORS allowed origins for Flask-CORS.

Configure production via environment variables:
  FRONTEND_URL      — primary frontend origin (e.g. https://your-app.vercel.app)
  CORS_ORIGINS      — optional comma-separated extra origins (e.g. preview deploys)

Local dev defaults include localhost:3000 unless overridden.
"""
import os


def get_allowed_origins():
    """Return a list of origins (no trailing slashes) for CORS."""
    seen = set()
    origins = []

    def add(origin):
        if not origin:
            return
        o = origin.strip().rstrip("/")
        if not o or o in seen:
            return
        seen.add(o)
        origins.append(o)

    # Explicit list: CORS_ORIGINS=https://a.com,https://b.com
    raw_extra = os.getenv("CORS_ORIGINS", "").strip()
    if raw_extra:
        for part in raw_extra.split(","):
            add(part)

    # Single frontend URL (Render + Vercel typical setup)
    add(os.getenv("FRONTEND_URL", "").strip())

    # Local development defaults when nothing else is set
    if not origins:
        add("http://localhost:3000")
        add("http://127.0.0.1:3000")
    else:
        # Still allow local dev when FRONTEND_URL is set (optional convenience)
        if os.getenv("ALLOW_LOCALHOST_CORS", "").lower() in ("1", "true", "yes"):
            add("http://localhost:3000")
            add("http://127.0.0.1:3000")

    return origins

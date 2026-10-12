# ── InsightFlow backend ─────────────────────────────────────────────────────
# Used by Render (render.yaml), Railway, Fly.io and any Docker host.
#
# IMPORTANT layout note: app/seed.py resolves the dataset with
#     ROOT = Path(__file__).resolve().parents[2]
#     OFFICIAL_CSV = ROOT / "sample_data" / "official_dataset.csv"
# so the image MUST mirror the repository tree (backend/ + sample_data/ as
# siblings). Flattening app/ to the workdir root makes parents[2] point at "/"
# and the seed silently finds nothing → an empty database.
#
# Build from the *repository root*:
#     docker build -f backend/Dockerfile -t insightflow-api .
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_URL=sqlite:///./insightflow.db \
    PORT=8000

WORKDIR /srv

# Dependencies first so the layer caches across code-only changes.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Mirror the repo layout that seed.py's parents[2] lookup expects.
COPY backend/app ./backend/app
COPY sample_data ./sample_data

WORKDIR /srv/backend
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]


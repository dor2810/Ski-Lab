# Backend API only (ski_optimizer/) -- the frontend is static, deployed
# separately to Firebase Hosting (see firebase.json). Built for Cloud
# Run: reads $PORT (Cloud Run sets this; 8080 is the default/fallback
# for running the image anywhere else, e.g. `docker run -p 8080:8080`).
FROM python:3.12-slim

WORKDIR /app

# Installed before copying the rest of the source so this layer only
# rebuilds when requirements.txt actually changes, not on every code
# edit -- meaningfully faster iterative builds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ski_optimizer/ ski_optimizer/
COPY data/ data/

# DATABASE_URL comes from the Cloud Run service env (Neon Postgres as
# of 2026-08-29 -- the Litestream/SQLite stopgap layer that lived here
# is gone; see git history for its rationale and NEXT_STEPS.md for the
# cutover). The sqlite default below only serves bare local runs.
ENV DATABASE_URL=sqlite:///./ski_lab.db

ENV PORT=8080
EXPOSE 8080

# Shell form so $PORT gets substituted -- Cloud Run injects the port.
CMD uvicorn ski_optimizer.api.main:app --host 0.0.0.0 --port $PORT

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

ENV PORT=8080
EXPOSE 8080

# Shell form (not exec/JSON form) so $PORT actually gets substituted --
# Cloud Run injects a real port number at container start, not always 8080.
CMD uvicorn ski_optimizer.api.main:app --host 0.0.0.0 --port $PORT

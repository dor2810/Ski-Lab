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

# Litestream: SQLite streaming replication to GCS, so user accounts
# survive deploys/restarts on Cloud Run's ephemeral filesystem -- see
# litestream.yml for the full rationale and the max-instances=1
# constraint it imposes. Pinned version.
ADD https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.deb /tmp/litestream.deb
RUN dpkg -i /tmp/litestream.deb && rm /tmp/litestream.deb

COPY ski_optimizer/ ski_optimizer/
COPY data/ data/
COPY litestream.yml /etc/litestream.yml
COPY run.sh /run.sh
RUN chmod +x /run.sh

# The API reads DATABASE_URL (db/database.py); /data is where run.sh
# restores the replica to and litestream watches. Four slashes =
# absolute path.
ENV DATABASE_URL=sqlite:////data/ski_lab.db

ENV PORT=8080
EXPOSE 8080

# run.sh: litestream restore (if a replica exists), then litestream
# replicate -exec uvicorn -- $PORT substitution happens inside the
# script.
CMD ["/run.sh"]

#!/bin/sh
# Container entrypoint: restore the SQLite database from its GCS
# replica (if one exists), then run the API under Litestream so every
# write streams back to GCS. See litestream.yml for the full rationale.
set -e

mkdir -p /data

# -if-replica-exists: first boot ever (no replica yet) starts with a
# fresh, empty database instead of failing.
# -if-db-not-exists: never clobber a database that's already present
# locally (defensive; on Cloud Run the filesystem starts empty anyway).
litestream restore -if-replica-exists -if-db-not-exists /data/ski_lab.db

# exec so uvicorn's signals flow through litestream (it forwards
# SIGTERM to the child and flushes the replica before exiting -- the
# reason a deploy no longer loses the last seconds of writes).
exec litestream replicate -exec "uvicorn ski_optimizer.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"

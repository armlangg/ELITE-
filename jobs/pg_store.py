"""PostgreSQL job store — remplace FileJobStore en production.
Même interface que FileJobStore, migration transparente.
"""
import json
import logging
from typing import Optional, Iterable
import psycopg2
import psycopg2.extras
from .models import Job, JobStatus
from .store import JobStore

log = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS elite_jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',
    payload JSONB NOT NULL DEFAULT '{}',
    result JSONB,
    error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);
"""

class PgJobStore(JobStore):
    """PostgreSQL-backed job store. Thread-safe via connection per operation."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._init_table()

    def _connect(self):
        return psycopg2.connect(self.database_url, cursor_factory=psycopg2.extras.RealDictCursor)

    def _init_table(self):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_TABLE)
            conn.commit()
        log.info("pg_store.table_ready")

    def create(self, job: Job) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO elite_jobs (id, status, payload, result, error, created_at, started_at, finished_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (job.id, job.status.value, json.dumps(job.payload), json.dumps(job.result) if job.result else None, job.error, job.created_at, job.started_at, job.finished_at)
                )
            conn.commit()

    def get(self, job_id: str) -> Optional[Job]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM elite_jobs WHERE id = %s", (job_id,))
                row = cur.fetchone()
        if not row:
            return None
        return self._row_to_job(row)

    def update(self, job: Job) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE elite_jobs SET status=%s, result=%s, error=%s, started_at=%s, finished_at=%s WHERE id=%s",
                    (job.status.value, json.dumps(job.result) if job.result else None, job.error, job.started_at, job.finished_at, job.id)
                )
            conn.commit()

    def list_by_status(self, status: JobStatus) -> Iterable[Job]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM elite_jobs WHERE status = %s", (status.value,))
                rows = cur.fetchall()
        return [self._row_to_job(r) for r in rows]

    def _row_to_job(self, row) -> Job:
        return Job(
            id=row['id'],
            status=JobStatus(row['status']),
            payload=row['payload'] if isinstance(row['payload'], dict) else json.loads(row['payload']),
            result=row['result'] if isinstance(row['result'], (dict, list)) else (json.loads(row['result']) if row['result'] else None),
            error=row['error'],
            created_at=row['created_at'],
            started_at=row['started_at'],
            finished_at=row['finished_at'],
        )

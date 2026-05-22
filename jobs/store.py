"""Couche de persistance des Jobs.

JobStore est une interface abstraite. Aujourd'hui une seule implémentation
(FileJobStore, écrit du JSON sur disque). Demain on ajoute RedisJobStore avec
exactement la même interface — le reste du code ne change pas.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Iterable
import json
import threading

from .models import Job, JobStatus


class JobStore(ABC):
    @abstractmethod
    def create(self, job: Job) -> None: ...

    @abstractmethod
    def get(self, job_id: str) -> Optional[Job]: ...

    @abstractmethod
    def update(self, job: Job) -> None: ...

    @abstractmethod
    def list_by_status(self, status: JobStatus) -> Iterable[Job]: ...


class FileJobStore(JobStore):
    """Stockage fichier. Un fichier JSON par job.
    Écriture atomique via tmp + rename pour éviter les lectures partielles.
    Thread-safe via lock."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, job_id: str) -> Path:
        return self.base_dir / f"{job_id}.json"

    def create(self, job: Job) -> None:
        with self._lock:
            self._write(job)

    def get(self, job_id: str) -> Optional[Job]:
        path = self._path(job_id)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                return Job.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def update(self, job: Job) -> None:
        with self._lock:
            self._write(job)

    def list_by_status(self, status: JobStatus) -> Iterable[Job]:
        for path in self.base_dir.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8") as f:
                    job = Job.from_dict(json.load(f))
                if job.status == status:
                    yield job
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    def _write(self, job: Job) -> None:
        path = self._path(job.id)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(job.to_dict(), f, ensure_ascii=False, indent=2)
        tmp.replace(path)

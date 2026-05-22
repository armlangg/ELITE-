"""Worker d'exécution des Jobs.

Un seul thread, une queue interne, traitement séquentiel (1 job à la fois).
Le handler est injecté — le worker ne sait rien du contenu métier.

Migration future vers RQ/Celery : remplacer la classe sans toucher app.py."""
from datetime import datetime, timezone
from typing import Callable
import logging
import queue
import threading

from .models import Job, JobStatus
from .store import JobStore

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobWorker:
    def __init__(self, store: JobStore, handler: Callable[[Job], dict]):
        self.store = store
        self.handler = handler
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True, name="JobWorker")
        self._stop = threading.Event()

    def start(self) -> None:
        self._recover_orphans()
        self._thread.start()
        log.info("worker.started")

    def submit(self, job: Job) -> None:
        """Crée le job en stockage et le pousse dans la queue."""
        self.store.create(job)
        self._queue.put(job.id)
        log.info("job.submitted id=%s", job.id)

    def _recover_orphans(self) -> None:
        """Au démarrage, on inspecte les jobs en PROCESSING : ils sont orphelins
        (le process précédent a été tué). On les passe en ERROR pour que Make.com
        puisse retry proprement plutôt que de poll dans le vide.
        Les jobs PENDING sont re-enqueue."""
        for job in list(self.store.list_by_status(JobStatus.PROCESSING)):
            job.status = JobStatus.ERROR
            job.error = "Worker restarted while job was processing"
            job.finished_at = _now_iso()
            self.store.update(job)
            log.warning("job.recovered_as_error id=%s", job.id)

        for job in list(self.store.list_by_status(JobStatus.PENDING)):
            self._queue.put(job.id)
            log.info("job.recovered_as_pending id=%s", job.id)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                job_id = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            self._process(job_id)

    def _process(self, job_id: str) -> None:
        job = self.store.get(job_id)
        if not job:
            log.error("job.not_found id=%s", job_id)
            return

        job.status = JobStatus.PROCESSING
        job.started_at = _now_iso()
        self.store.update(job)
        log.info("job.processing id=%s", job_id)

        try:
            result = self.handler(job)
            job.result = result
            job.status = JobStatus.DONE
            log.info("job.done id=%s", job_id)
        except Exception as e:
            job.error = f"{type(e).__name__}: {e}"
            job.status = JobStatus.ERROR
            log.exception("job.error id=%s", job_id)
        finally:
            job.finished_at = _now_iso()
            self.store.update(job)

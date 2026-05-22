"""Serveur Flask ELITE — endpoints d'analyse asynchrone.

Architecture :
  POST /analyze       -> crée un job, répond 202 avec job_id
  GET  /status/<id>   -> état du job (pending/processing/done/error)
  GET  /result/<id>   -> résultat final (si done)
  GET  /health        -> healthcheck

Le traitement est asynchrone via un JobWorker single-threaded.
Aucune logique métier dans ce fichier : juste du routing + composition.
"""
import logging
import sys

from flask import Flask, request, jsonify

from config import Config
from jobs.models import Job, JobStatus
from jobs.store import FileJobStore
from jobs.worker import JobWorker
from analysis.downloader import VideoDownloader
from analysis.gemini import GeminiAnalyzer


# --- Flask (défini en premier pour que Gunicorn le trouve même si l'init plante) ---
app = Flask(__name__)

# --- Logging ---
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("elite")

# --- Composition root : on instancie ici, on injecte partout ---
store = FileJobStore(Config.JOBS_DIR)
downloader = VideoDownloader(Config.DOWNLOAD_DIR, timeout_sec=Config.DOWNLOAD_TIMEOUT_SEC)
analyzer = GeminiAnalyzer(api_key=Config.GEMINI_API_KEY, model=Config.GEMINI_MODEL)


def handle_job(job: Job) -> dict:
    """Pipeline d'analyse. Appelé par le worker dans son thread.
    Téléchargement -> analyse Gemini -> nettoyage."""
    url = job.payload["url"]
    opponent = job.payload["opponent_name"]

    video_path = downloader.download(url)
    try:
        return analyzer.analyze_video(video_path, opponent)
    finally:
        video_path.unlink(missing_ok=True)


worker = JobWorker(store=store, handler=handle_job)
worker.start()


@app.get("/health")
def health():
    return jsonify(status="ok"), 200


@app.post("/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    opponent = data.get("opponent_name")

    if not url or not opponent:
        return jsonify(error="Fields 'url' and 'opponent_name' are required"), 400

    job = Job(payload={"url": url, "opponent_name": opponent})
    worker.submit(job)

    return jsonify(job_id=job.id, status=job.status.value), 202


@app.get("/status/<job_id>")
def status(job_id: str):
    job = store.get(job_id)
    if not job:
        return jsonify(error="job not found"), 404
    return jsonify(
        job_id=job.id,
        status=job.status.value,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=job.error,
    ), 200


@app.get("/result/<job_id>")
def result(job_id: str):
    job = store.get(job_id)
    if not job:
        return jsonify(error="job not found"), 404
    if job.status != JobStatus.DONE:
        return jsonify(
            error=f"job not done (status: {job.status.value})",
            status=job.status.value,
        ), 409
    return jsonify(job_id=job.id, result=job.result), 200

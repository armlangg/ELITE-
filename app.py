"""Serveur Flask ELITE — endpoints d'analyse asynchrone."""
import logging
import sys
import uuid

from flask import Flask, request, jsonify
from flask_cors import CORS

from config import Config
from jobs.models import Job, JobStatus
from jobs.store import FileJobStore
from jobs.worker import JobWorker
from analysis.downloader import VideoDownloader
from analysis.gemini import GeminiAnalyzer
from analysis.claude_client import ClaudeClient
from analysis.search_engine import SearchEngine

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("elite")

if Config.YOUTUBE_COOKIES:
    Config.COOKIES_FILE.write_text(Config.YOUTUBE_COOKIES, encoding="utf-8")
    log.info("cookies.written path=%s", Config.COOKIES_FILE)

store = FileJobStore(Config.JOBS_DIR)
downloader = VideoDownloader(
    Config.DOWNLOAD_DIR,
    cookies_file=Config.COOKIES_FILE if Config.YOUTUBE_COOKIES else None,
    timeout_sec=Config.DOWNLOAD_TIMEOUT_SEC,
)
analyzer = GeminiAnalyzer(api_key=Config.GEMINI_API_KEY, model=Config.GEMINI_MODEL)
claude = ClaudeClient(api_key=Config.CLAUDE_API_KEY, model=Config.CLAUDE_MODEL) if Config.CLAUDE_API_KEY else None
search = SearchEngine(
    youtube_api_key=Config.YOUTUBE_API_KEY,
    google_api_key=Config.GOOGLE_SEARCH_API_KEY,
    google_cx=Config.GOOGLE_SEARCH_ENGINE_ID,
) if Config.YOUTUBE_API_KEY else None


def handle_job(job: Job) -> dict:
    opponent = job.payload["opponent_name"]
    video_path = Config.DOWNLOAD_DIR / job.payload["video_filename"]

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    try:
        if downloader.ffmpeg:
            video_path = downloader._convert_to_h264(video_path)

        # Étape 1 : analyse vidéo Gemini
        gemini_result = analyzer.analyze_video(video_path, opponent)
        gemini_analysis = gemini_result["analysis"]

        # Étape 2 : game plan Claude
        if claude:
            game_plan = claude.generate_game_plan(opponent, gemini_analysis)
            return {
                "opponent": opponent,
                "gemini_analysis": gemini_analysis,
                "game_plan": game_plan,
            }
        else:
            log.warning("claude.not_configured — returning gemini only")
            return gemini_result

    finally:
        video_path.unlink(missing_ok=True)


worker = JobWorker(store=store, handler=handle_job)
worker.start()


@app.post("/analyze-url")
def analyze_url():
    """Test endpoint : analyse directe via URL YouTube."""
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    opponent = data.get("opponent_name")

    if not url or not opponent:
        return jsonify(error="Fields 'url' and 'opponent_name' are required"), 400

    def handle_url_job(job: Job) -> dict:
        gemini_result = analyzer.analyze_video(job.payload["url"], job.payload["opponent_name"])
        if claude:
            game_plan = claude.generate_game_plan(job.payload["opponent_name"], gemini_result["analysis"])
            return {"opponent": job.payload["opponent_name"], "gemini_analysis": gemini_result["analysis"], "game_plan": game_plan}
        return gemini_result

    job = Job(payload={"url": url, "opponent_name": opponent})
    # Use inline worker for URL jobs
    from jobs.worker import JobWorker
    url_worker = JobWorker(store=store, handler=handle_url_job)
    store.create(job)
    import threading
    def run():
        url_worker._process(job.id)
    threading.Thread(target=run, daemon=True).start()

    return jsonify(job_id=job.id, status=job.status.value), 202


@app.get("/search/<boxer_name>")
def search_boxer(boxer_name: str):
    """Recherche exhaustive de sources sur un boxeur."""
    if not search:
        return jsonify(error="Search APIs not configured"), 503
    try:
        sources = search.search_boxer(boxer_name, max_results=30)
        return jsonify(
            boxer=boxer_name,
            total=len(sources),
            sources=[s.to_dict() for s in sources],
        ), 200
    except Exception as e:
        log.exception("search.error boxer=%s", boxer_name)
        return jsonify(error=str(e)), 500


@app.get("/health")
def health():
    return jsonify(status="ok"), 200


@app.post("/upload")
def upload():
    opponent = request.form.get("opponent_name")
    if not opponent:
        return jsonify(error="Field 'opponent_name' is required"), 400

    if "video" not in request.files:
        return jsonify(error="Field 'video' (file) is required"), 400

    file = request.files["video"]
    if not file.filename:
        return jsonify(error="Empty filename"), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "mp4"
    filename = f"{uuid.uuid4()}.{ext}"
    save_path = Config.DOWNLOAD_DIR / filename
    Config.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file.save(str(save_path))
    log.info("upload.saved path=%s size=%d", save_path, save_path.stat().st_size)

    job = Job(payload={"opponent_name": opponent, "video_filename": filename})
    worker.submit(job)

    return jsonify(job_id=job.id, status=job.status.value), 202


@app.post("/analyze")
def analyze():
    return jsonify(error="YouTube download temporarily disabled. Use /upload instead."), 503


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

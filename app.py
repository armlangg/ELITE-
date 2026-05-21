from flask import Flask, request, jsonify
import yt_dlp
from google import genai
import os
import tempfile

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

PROMPT_ANALYSE = """Tu es un analyste tactique expert en boxe anglaise professionnelle.
Analyse cette video et produis une analyse tactique complete selon cette structure :

0. ANALYSE DE LA SOURCE ET FIABILITE DU MATERIEL
- Type de contenu identifie
- Coefficient de fiabilite applique (%)
- Risque d intox : oui / possible / non

1. PROFIL GENERAL
- Style de boxe, garde, distance preferee

2. ANALYSE SPATIALE
- Zones offensives, defensives, coups recus, deplacements

3. STATISTIQUES OFFENSIVES
- Frequence, efficacite, distance, signal avant-coureur par coup

4. COMBINAISONS FAVORITES
- Top 5 avec sequence, declencheur, frequence, efficacite

5. ANALYSE DEFENSIVE
C01 a C20 : defense principale, secondaire, contre, expositions, taux succes, vulnerabilite, confiance

6. FAIBLESSES STRUCTURELLES
Par priorite : description, situation, exploitation

7. CONDITIONNEMENT
Evolution par round, fatigue, fin de round, resistance

8. PSYCHOLOGIE
Pression, encaissement, difficulte, frustration

Reponds en francais. Precis, factuel, quantifie."""


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    urls_raw = data.get("urls", "")
    adversaire = data.get("adversaire", "Inconnu")

    if isinstance(urls_raw, list):
        urls = urls_raw
    else:
        urls = [u.strip() for u in urls_raw.split(",") if u.strip()]

    if not urls:
        return jsonify({"error": "Aucune URL fournie"}), 400

    analyses = []

    for url in urls:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts = {
                    "format": "worst[ext=mp4]/worst/best[filesize<50M]",
                    "merge_output_format": "mp4",
                    "outtmpl": tmpdir + "/video.%(ext)s",
                    "quiet": True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                video_files = [f for f in os.listdir(tmpdir) if f.startswith("video")]
                if not video_files:
                    analyses.append({"url": url, "error": "Telechargement echoue"})
                    continue

                video_path = os.path.join(tmpdir, video_files[0])

                uploaded_file = client.files.upload(file=video_path)

                while uploaded_file.state.name == "PROCESSING":
                    import time
                    time.sleep(5)
                    uploaded_file = client.files.get(name=uploaded_file.name)

                if uploaded_file.state.name == "FAILED":
                    analyses.append({"url": url, "error": "Traitement Gemini echoue"})
                    continue

                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[uploaded_file, PROMPT_ANALYSE]
                )

                analyses.append({
                    "url": url,
                    "analyse": response.text
                })

                client.files.delete(name=uploaded_file.name)

        except Exception as e:
            analyses.append({"url": url, "error": str(e)})

    return jsonify({
        "adversaire": adversaire,
        "nombre_videos": len(urls),
        "analyses": analyses
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

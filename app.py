from flask import Flask, request, jsonify
import yt_dlp
from google import genai
import os
import tempfile
import time

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

PROMPT_ANALYSE = """Tu es un analyste tactique expert en boxe anglaise professionnelle.
Analyse cette video et produis une analyse tactique complete selon cette structure :

0. ANALYSE DE LA SOURCE ET FIABILITE DU MATERIEL
- Type de contenu identifie
- Qui a diffuse ce contenu
- Signes de mise en scene ou selection deliberee
- Coefficient de fiabilite applique (%)
- Risque d intox : oui / possible / non

1. PROFIL GENERAL
- Style de boxe
- Garde et points de vulnerabilite
- Distance preferee

2. ANALYSE SPATIALE
- Zones du ring en phase offensive
- Zones du ring en phase defensive
- Zones ou il a recu le plus de coups
- Deplacements apres encaissement

3. STATISTIQUES OFFENSIVES
Pour chaque coup (jab, direct droit, crochet gauche/droit, uppercut gauche/droit, corps) :
- Frequence, efficacite, distance, signal avant-coureur

4. COMBINAISONS FAVORITES
Les 3 a 5 plus recurrentes avec sequence, declencheur, frequence, efficacite

5. ANALYSE DEFENSIVE
Pour chaque combinaison : defense principale, defense secondaire, contre-attaque, expositions observees, taux de succes, vulnerabilite, niveau de confiance
C01-1 / C02-2 / C03-3
C04-1-2 / C05-1-3 / C06-2-3 / C07-1-1 / C08-3-2 / C09-1-B / C10-2-B
C11-1-2-3 / C12-1-1-2 / C13-1-2-B / C14-1-3-2 / C15-1-2-5 / C16-3-2-3 / C17-1-B-3 / C18-2-3-2 / C19-1-2-6 / C20-5-2-3

6. FAIBLESSES STRUCTURELLES
Par ordre de priorite : description, situation, exploitation concrete

7. CONDITIONNEMENT ET ENDURANCE
Evolution par round, premiers signes de fatigue, comportement fin de round, resistance

8. ELEMENTS PSYCHOLOGIQUES
Reaction a la pression, apres encaissement, en difficulte, frustration

Reponds en francais. Sois precis, factuel, quantifie."""


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    urls = data.get("urls", [])
    adversaire = data.get("adversaire", "Inconnu")

    if not urls:
        return jsonify({"error": "Aucune URL fournie"}), 400

    analyses = []

    for url in urls:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts = {
                    "format": "best[ext=mp4][filesize<200M]/best[filesize<200M]",
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

                video_file = genai.upload_file(
                    path=video_path,
                    display_name=adversaire
                )

                while video_file.state.name == "PROCESSING":
                    time.sleep(5)
                    video_file = genai.get_file(video_file.name)

                if video_file.state.name == "FAILED":
                    analyses.append({"url": url, "error": "Traitement Gemini echoue"})
                    continue

                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content([video_file, PROMPT_ANALYSE])

                analyses.append({
                    "url": url,
                    "analyse": response.text
                })

                genai.delete_file(video_file.name)

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

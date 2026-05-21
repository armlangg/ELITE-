from flask import Flask, request, jsonify
import yt_dlp
import google.generativeai as genai
import os
import tempfile
import time

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

PROMPT_ANALYSE = """
Tu es un analyste tactique expert en boxe anglaise professionnelle.
Analyse cette vidéo et produis une analyse tactique complète selon cette structure :

0. ANALYSE DE LA SOURCE ET FIABILITÉ DU MATÉRIEL
- Type de contenu identifié
- Qui a diffusé ce contenu
- Signes de mise en scène ou sélection délibérée
- Coefficient de fiabilité appliqué (%)
- Risque d'intox : oui / possible / non

1. PROFIL GÉNÉRAL
- Style de boxe
- Garde et points de vulnérabilité
- Distance préférée

2. ANALYSE SPATIALE
- Zones du ring en phase offensive
- Zones du ring en phase défensive
- Zones où il a reçu le plus de coups
- Déplacements après encaissement

3. STATISTIQUES OFFENSIVES
Pour chaque coup (jab, direct droit, crochet gauche/droit, uppercut gauche/droit, corps) :
- Fréquence, efficacité, distance, signal avant-coureur

4. COMBINAISONS FAVORITES
Les 3 à 5 plus récurrentes avec séquence, déclencheur, fréquence, efficacité

5. ANALYSE DÉFENSIVE — RÉPONSE AUX COMBINAISONS
Légende : 1=Jab / 2=Direct droit / 3=Crochet gauche / 4=Crochet droit / 5=Uppercut gauche / 6=Uppercut droit / B=Corps

Pour chaque combinaison : défense principale, défense secondaire, contre-attaque, expositions observées, taux de succès, vulnérabilité, niveau de confiance

C01-1 / C02-2 / C03-3
C04-1-2 / C05-1-3 / C06-2-3 / C07-1-1 / C08-3-2 / C09-1-B / C10-2-B
C11-1-2-3 / C12-1-1-2 / C13-1-2-B / C14-1-3-2 / C15-1-2-5 / C16-3-2-3 / C17-1-B-3 / C18-2-3-2 / C19-1-2-6 / C20-5-2-3

Synthèse défensive : 3 combinaisons cibles, 3 combinaisons verrouillées, pattern dominant, angle délaissé, meilleur moment pour attaquer

6. FAIBLESSES STRUCTURELLES
Par ordre de priorité : description, situation, exploitation concrète

7. CONDITIONNEMENT ET ENDURANCE
- Évolution par round, premiers signes de fatigue, comportement fin de round, résistance

8. ÉLÉMENTS PSYCHOLOGIQUES
- Réaction à la pression, après encaissement, en difficulté, frustration

Réponds en français. Sois précis, factuel, quantifié. Signale clairement les observations à faible confiance.
"""

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
                    "outtmpl": f"{tmpdir}/video.%(ext)s",
                    "quiet": True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                video_files = [f for f in os.listdir(tmpdir) if f.startswith("video")]
                if not video_files:
                    analyses.append({"url": url, "error": "Téléchargement échoué"})
                    continue

                video_path = os.path.join(tmpdir, video_files[0])

                video_file = genai.upload_file(
                    path=video_path,
                    display_name=f"{adversaire}_{url[-20:]}"
                )

                while video_file.state.name == "PROCESSING":
                    time.sleep(5)
                    video_file = genai.get_file(video_file.name)

                if video_file.state.n

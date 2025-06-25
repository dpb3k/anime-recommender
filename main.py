from flask import Flask, request, jsonify
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib
from huggingface_hub import hf_hub_download
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis

app = Flask(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ["REDIS_URL"],
    app=app,
    default_limits=["100 per day", "10 per minute"]
)

@app.route("/recommend")
def recommend():
    query = request.args.get("anime")
    if not query:
        return jsonify({"error": "No anime provided"}), 400

    # 👇 Lazy load everything INSIDE the route
    anime_df = pd.read_csv("anime.csv").dropna(subset=["genre"])
    ratings_df = pd.read_csv("rating.csv")
    ratings_df = ratings_df[ratings_df["rating"] > 0]

    tfidf = TfidfVectorizer(stop_words="english")
    genre_matrix = tfidf.fit_transform(anime_df["genre"])

    anime_id_to_index = {aid: idx for idx, aid in enumerate(anime_df["anime_id"])}
    anime_name_to_id = dict(zip(anime_df["name"], anime_df["anime_id"]))

    hf_token = os.environ.get("HF_TOKEN")
    model_path = hf_hub_download(repo_id="tyfulks/animerec", filename="svd_model.pkl", token=hf_token)
    svd_model = joblib.load(model_path)

    if query not in anime_name_to_id:
        return jsonify({"error": "Anime not found"}), 404

    target_id = anime_name_to_id[query]
    target_idx = anime_id_to_index[target_id]

    # Similarity + predictions
    content_scores = cosine_similarity(genre_matrix[target_idx], genre_matrix).flatten()
    content_indices = content_scores.argsort()[::-1][1:21]

    svd_scores = []
    for idx in content_indices:
        aid = anime_df.iloc[idx]["anime_id"]
        pred = svd_model.predict(uid=999999, iid=aid).est
        svd_scores.append((idx, pred))

    final_scores = sorted(svd_scores, key=lambda x: x[1], reverse=True)[:5]
    recommendations = []
    selected_rows = anime_df.iloc[[idx for idx, _ in final_scores]]

    for row, (_, score) in zip(selected_rows.itertuples(index=False), final_scores):
        recommendations.append({
            "title": row.name,
            "genre": row.genre,
            "rating": row.rating,
            "score": round(score, 2)
        })

    return jsonify(recommendations)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

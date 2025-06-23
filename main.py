import pandas as pd
from flask import Flask, request, jsonify
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from surprise import SVD, Dataset, Reader


# Load anime metadata
anime_df = pd.read_csv(r"anime.csv").dropna(subset=["genre"])
ratings_df = pd.read_csv(r"rating.csv")
ratings_df = ratings_df[ratings_df["rating"] > 0]

# Setup TF-IDF for genres
tfidf = TfidfVectorizer(stop_words="english")
genre_matrix = tfidf.fit_transform(anime_df["genre"])

# Build Surprise SVD model
reader = Reader(rating_scale=(1, 10))
data = Dataset.load_from_df(ratings_df[["user_id", "anime_id", "rating"]], reader)
trainset = data.build_full_trainset()
import joblib
svd_model = joblib.load("svd_model.pkl")


# Create anime_id <-> index mappings
anime_id_to_index = {aid: idx for idx, aid in enumerate(anime_df["anime_id"])}
anime_name_to_id = dict(zip(anime_df["name"], anime_df["anime_id"]))

app = Flask(__name__)

@app.route("/recommend")
def recommend():
    query = request.args.get("anime")
    if not query or query not in anime_name_to_id:
        return jsonify({"error": "Anime not found"}), 404

    target_id = anime_name_to_id[query]
    target_idx = anime_id_to_index.get(target_id)

    # Content-based filtering: cosine similarity on genre
    content_scores = cosine_similarity(genre_matrix[target_idx], genre_matrix).flatten()
    content_indices = content_scores.argsort()[::-1][1:21]

    # Collaborative filtering: SVD prediction for virtual user
    svd_scores = []
    for idx in content_indices:
        aid = anime_df.iloc[idx]["anime_id"]
        pred = svd_model.predict(uid=999999, iid=aid).est
        svd_scores.append((idx, pred))

    # Sort final hybrid score (combine content + collaborative)
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
    app.run(host="0.0.0.0", port=5000, debug=True)


from pathlib import Path
import re
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter

import numpy as np
import pandas as pd
import joblib


class RecommenderEngine:
    _instance: Optional["RecommenderEngine"] = None

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent.parent
        self.base_dir = Path(base_dir)

        # Paths
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "outputs" / "models"

        # State
        self.movies_df: pd.DataFrame = pd.DataFrame()
        self.ratings_df: pd.DataFrame = pd.DataFrame()
        self.train_ratings_df: pd.DataFrame = pd.DataFrame()
        self.tags_by_movie: Dict[int, List[str]] = {}
        self.all_genres: List[str] = []

        # Model & Latent mappings
        self.model = None
        self.trainset = None
        self.raw_to_inner_item: Dict[int, int] = {}
        self.inner_to_raw_item: Dict[int, int] = {}
        self.raw_to_inner_user: Dict[int, int] = {}
        self.inner_to_raw_user: Dict[int, int] = {}
        self.qi_normalized: Optional[np.ndarray] = None
        self.movie_lookup: Dict[int, Dict[str, Any]] = {}

        self._load()

    @classmethod
    def get_instance(cls, base_dir: Optional[Path] = None) -> "RecommenderEngine":
        if cls._instance is None:
            cls._instance = cls(base_dir=base_dir)
        return cls._instance

    def _load(self):
        # 1. Load CSVs
        movies_csv = self.data_dir / "movies.csv"
        links_csv = self.data_dir / "links.csv"
        ratings_csv = self.data_dir / "ratings.csv"
        tags_csv = self.data_dir / "tags.csv"
        train_csv = self.data_dir / "processed" / "train_ratings.csv"

        movies = pd.read_csv(movies_csv)
        links = pd.read_csv(links_csv) if links_csv.exists() else pd.DataFrame(columns=["movieId", "imdbId"])
        ratings = pd.read_csv(ratings_csv)
        train_ratings = pd.read_csv(train_csv) if train_csv.exists() else ratings

        # Tags processing
        if tags_csv.exists():
            tags_df = pd.read_csv(tags_csv)
            tags_grouped = tags_df.groupby("movieId")["tag"].apply(
                lambda s: list(dict.fromkeys(s.dropna().astype(str).str.strip().str.lower()))[:10]
            ).to_dict()
            self.tags_by_movie = tags_grouped
        else:
            self.tags_by_movie = {}

        # Ratings stats per movie
        stats = ratings.groupby("movieId").agg(
            vote_count=("rating", "count"),
            vote_avg=("rating", "mean")
        ).reset_index()

        # Merge movies with links and stats
        merged = movies.merge(links, on="movieId", how="left").merge(stats, on="movieId", how="left")
        merged["vote_count"] = merged["vote_count"].fillna(0).astype(int)
        merged["vote_avg"] = merged["vote_avg"].fillna(0.0).round(2)

        # Extract year
        merged["year"] = merged["title"].str.extract(r"\((\d{4})\)").astype(float).astype("Int64")

        # Clean IMDb Id and Url
        def format_imdb(val):
            if pd.isna(val) or val == "":
                return None, None
            try:
                padded = f"tt{int(val):07d}"
                return padded, f"https://www.imdb.com/title/{padded}/"
            except Exception:
                return None, None

        imdb_data = [format_imdb(x) for x in merged["imdbId"]]
        merged["formatted_imdbId"] = [x[0] for x in imdb_data]
        merged["imdb_url"] = [x[1] for x in imdb_data]

        # Parse genres as list
        merged["genres_list"] = merged["genres"].apply(
            lambda g: [x.strip() for x in str(g).split("|") if x.strip() and x.strip() != "(no genres listed)"]
        )

        all_unique_genres = set()
        for glist in merged["genres_list"]:
            all_unique_genres.update(glist)
        self.all_genres = sorted(list(all_unique_genres))

        self.movies_df = merged
        self.ratings_df = ratings
        self.train_ratings_df = train_ratings

        # Fast dictionary lookup by movieId
        self.movie_lookup = {}
        for _, row in merged.iterrows():
            mid = int(row["movieId"])
            self.movie_lookup[mid] = {
                "movieId": mid,
                "title": row["title"],
                "year": int(row["year"]) if pd.notna(row["year"]) else None,
                "genres": row["genres_list"],
                "vote_count": int(row["vote_count"]),
                "vote_avg": float(row["vote_avg"]),
                "imdbId": row["formatted_imdbId"],
                "imdbUrl": row["imdb_url"],
                "tags": self.tags_by_movie.get(mid, [])
            }

        # 2. Load SVD Model
        model_path = self.models_dir / "svd_model.pkl"
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found at {model_path}")
        self.model = joblib.load(model_path)
        self.trainset = self.model.trainset

        # Build inner <-> raw mapping dictionaries
        self.raw_to_inner_item = {self.trainset.to_raw_iid(i): i for i in self.trainset.all_items()}
        self.inner_to_raw_item = {i: self.trainset.to_raw_iid(i) for i in self.trainset.all_items()}

        self.raw_to_inner_user = {self.trainset.to_raw_uid(u): u for u in self.trainset.all_users()}
        self.inner_to_raw_user = {u: self.trainset.to_raw_uid(u) for u in self.trainset.all_users()}

        # Pre-normalize qi for ultra-fast cosine similarity (matrix-vector dot product)
        qi = self.model.qi
        norms = np.linalg.norm(qi, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        self.qi_normalized = qi / norms

    # ─────────────────────────────────────────────────────────────
    # Search & Inspection
    # ─────────────────────────────────────────────────────────────
    def search_movies(
        self,
        query: str = "",
        limit: int = 20,
        genre: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        df = self.movies_df
        if genre and genre in self.all_genres:
            df = df[df["genres_list"].apply(lambda glist: genre in glist)]

        if query:
            clean_q = re.escape(query.strip())
            df = df[df["title"].str.contains(clean_q, case=False, na=False)]

        # Sort by popularity (vote_count descending)
        df = df.sort_values("vote_count", ascending=False).head(limit)

        results = []
        for mid in df["movieId"]:
            results.append(self.movie_lookup[int(mid)])
        return results

    def get_movie_detail(self, movie_id: int) -> Optional[Dict[str, Any]]:
        if movie_id not in self.movie_lookup:
            return None
        info = dict(self.movie_lookup[movie_id])
        info["similarMovies"] = self.get_similar_movies(movie_id, n=6)
        return info

    def get_similar_movies(self, movie_id: int, n: int = 10) -> List[Dict[str, Any]]:
        if movie_id not in self.raw_to_inner_item:
            return []

        inner_idx = self.raw_to_inner_item[movie_id]
        target_vec = self.qi_normalized[inner_idx]

        # Cosine similarity against all items in trainset
        sims = self.qi_normalized @ target_vec

        # Exclude the movie itself
        sims[inner_idx] = -1.0

        top_indices = np.argsort(sims)[::-1][:n]
        results = []
        for idx in top_indices:
            raw_mid = self.inner_to_raw_item[int(idx)]
            if raw_mid in self.movie_lookup:
                item = dict(self.movie_lookup[raw_mid])
                item["similarity"] = round(float(sims[idx]), 3)
                results.append(item)
        return results

    # ─────────────────────────────────────────────────────────────
    # User Profile & Existing User Recommendations
    # ─────────────────────────────────────────────────────────────
    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        user_ratings = self.train_ratings_df[self.train_ratings_df["userId"] == user_id]
        if user_ratings.empty:
            return None

        merged = user_ratings.merge(self.movies_df, on="movieId")
        top_rated_df = merged.sort_values("rating", ascending=False).head(10)

        top_rated = []
        for _, row in top_rated_df.iterrows():
            mid = int(row["movieId"])
            if mid in self.movie_lookup:
                item = dict(self.movie_lookup[mid])
                item["vote_avg"] = float(row["rating"])  # user's rating
                top_rated.append(item)

        # Genre breakdown
        genre_counter = Counter()
        for glist in merged["genres_list"]:
            genre_counter.update(glist)

        return {
            "userId": user_id,
            "ratingsCount": int(len(user_ratings)),
            "avgRating": round(float(user_ratings["rating"].mean()), 2),
            "topRated": top_rated,
            "genreDistribution": dict(genre_counter.most_common(12))
        }

    def get_user_recommendations(
        self,
        user_id: int,
        n: int = 10,
        genre: Optional[str] = None,
        min_ratings: int = 0
    ) -> List[Dict[str, Any]]:
        # Check if user exists in trainset
        if user_id not in self.raw_to_inner_user:
            # Fallback to cold-start empty or popular
            return []

        inner_uid = self.raw_to_inner_user[user_id]
        pu = self.model.pu[inner_uid]
        bu = self.model.bu[inner_uid]
        mu = self.trainset.global_mean

        # User's already rated movies
        seen_movies = set(self.train_ratings_df[self.train_ratings_df["userId"] == user_id]["movieId"])

        # Predict ratings for all candidate movies
        scores = mu + bu + self.model.bi + self.model.qi @ pu

        # Candidate filtering
        candidates = []
        for inner_iid in range(self.trainset.n_items):
            raw_mid = self.inner_to_raw_item[inner_iid]
            if raw_mid in seen_movies:
                continue
            if raw_mid not in self.movie_lookup:
                continue

            info = self.movie_lookup[raw_mid]
            if genre and genre not in info["genres"]:
                continue
            if info["vote_count"] < min_ratings:
                continue

            score = float(scores[inner_iid])
            candidates.append((raw_mid, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:n]

        results = []
        for raw_mid, pred_score in top_candidates:
            item = dict(self.movie_lookup[raw_mid])
            item["predictedRating"] = round(min(5.0, max(0.5, pred_score)), 2)
            results.append(item)

        return results

    # ─────────────────────────────────────────────────────────────
    # Guest / Cold Start Recommendations (Mathematical Folding-in)
    # ─────────────────────────────────────────────────────────────
    def get_guest_recommendations(
        self,
        ratings: List[Tuple[int, float]],
        n: int = 10,
        genre: Optional[str] = None,
        min_ratings: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Solves the Cold-Start problem on the fly:
        Estimates the guest's latent vector p_guest via Ridge Regression on items already in the SVD space:
        min_p sum_i (r_i - (mu + b_i + q_i^T p))^2 + lambda * ||p||^2
        """
        valid_items = []
        valid_ratings = []
        seen_mids = set()

        for mid, r in ratings:
            seen_mids.add(mid)
            if mid in self.raw_to_inner_item:
                valid_items.append(self.raw_to_inner_item[mid])
                valid_ratings.append(float(r))

        mu = self.trainset.global_mean

        if len(valid_items) == 0:
            # Fallback to popular high-rated movies
            df = self.movies_df[~self.movies_df["movieId"].isin(seen_mids)]
            if genre:
                df = df[df["genres_list"].apply(lambda glist: genre in glist)]
            df = df[df["vote_count"] >= max(min_ratings, 20)].sort_values("vote_avg", ascending=False).head(n)
            results = []
            for mid in df["movieId"]:
                item = dict(self.movie_lookup[int(mid)])
                item["predictedRating"] = item["vote_avg"]
                results.append(item)
            return results

        Q = self.model.qi[valid_items]
        b = self.model.bi[valid_items]
        y = np.array(valid_ratings) - (mu + b)

        # Ridge Regression closed-form solution
        reg = 0.05
        dim = self.model.qi.shape[1]
        p_guest = np.linalg.solve(Q.T @ Q + reg * np.eye(dim), Q.T @ y)

        # Predict for all movies in trainset
        scores = mu + self.model.bi + self.model.qi @ p_guest

        candidates = []
        for inner_iid in range(self.trainset.n_items):
            raw_mid = self.inner_to_raw_item[inner_iid]
            if raw_mid in seen_mids:
                continue
            if raw_mid not in self.movie_lookup:
                continue

            info = self.movie_lookup[raw_mid]
            if genre and genre not in info["genres"]:
                continue
            if info["vote_count"] < min_ratings:
                continue

            score = float(scores[inner_iid])
            candidates.append((raw_mid, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:n]

        results = []
        for raw_mid, pred_score in top_candidates:
            item = dict(self.movie_lookup[raw_mid])
            item["predictedRating"] = round(min(5.0, max(0.5, pred_score)), 2)
            results.append(item)

        return results

    # ─────────────────────────────────────────────────────────────
    # System Statistics & Metadata
    # ─────────────────────────────────────────────────────────────
    def get_stats(self) -> Dict[str, Any]:
        total_movies = int(len(self.movies_df))
        total_ratings = int(len(self.ratings_df))
        total_users = int(self.ratings_df["userId"].nunique())
        total_possible = total_users * total_movies
        sparsity = round((1.0 - (total_ratings / total_possible)) * 100, 2)

        return {
            "totalMovies": total_movies,
            "totalRatings": total_ratings,
            "totalUsers": total_users,
            "sparsityPercent": sparsity,
            "modelType": "SVD (Singular Value Decomposition / Funk SVD)",
            "modelRMSE": 0.8806,
            "modelMAE": 0.6742,
            "latentDimensions": int(self.model.qi.shape[1])
        }

    def get_sample_users(self, count: int = 50) -> List[int]:
        return sorted([int(u) for u in self.train_ratings_df["userId"].unique()[:count]])

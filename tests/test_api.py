import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure recommender-system is on sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["movies_count"] > 9000


def test_stats():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["totalMovies"] > 9000
    assert data["totalUsers"] == 610
    assert data["latentDimensions"] == 50
    assert data["modelRMSE"] == 0.8806


def test_genres():
    response = client.get("/api/genres")
    assert response.status_code == 200
    genres = response.json()
    assert "Action" in genres
    assert "Comedy" in genres
    assert "Sci-Fi" in genres


def test_search_movies():
    response = client.get("/api/movies/search?q=matrix&limit=5")
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0
    assert any("Matrix" in m["title"] for m in results)
    assert "imdbUrl" in results[0]


def test_movie_detail_and_similar():
    # Movie 1 is Toy Story (1995)
    response = client.get("/api/movies/1")
    assert response.status_code == 200
    detail = response.json()
    assert detail["movieId"] == 1
    assert "Toy Story" in detail["title"]
    assert len(detail["similarMovies"]) > 0

    # Test direct similar endpoint
    sim_res = client.get("/api/movies/1/similar?n=5")
    assert sim_res.status_code == 200
    similar = sim_res.json()
    assert len(similar) == 5
    assert all("similarity" in s for s in similar)


def test_user_profile_and_recommendations():
    # User 1
    profile_res = client.get("/api/users/1/profile")
    assert profile_res.status_code == 200
    profile = profile_res.json()
    assert profile["userId"] == 1
    assert profile["ratingsCount"] > 0
    assert len(profile["topRated"]) > 0

    # User 1 recommendations
    recs_res = client.get("/api/users/1/recommendations?n=5")
    assert recs_res.status_code == 200
    recs = recs_res.json()
    assert recs["count"] == 5
    assert all("predictedRating" in m for m in recs["recommendations"])


def test_guest_recommendations_cold_start():
    # Test cold start with Matrix (2571) and Pulp Fiction (296)
    payload = {
        "ratings": [
            {"movieId": 2571, "rating": 5.0},
            {"movieId": 296, "rating": 4.5}
        ],
        "n": 6,
        "genre": None,
        "min_ratings": 10
    }
    response = client.post("/api/recommendations/guest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 6
    recs = data["recommendations"]
    assert len(recs) == 6
    # Rated movies shouldn't be re-recommended
    rec_ids = [m["movieId"] for m in recs]
    assert 2571 not in rec_ids
    assert 296 not in rec_ids
    assert all(m["predictedRating"] > 0 for m in recs)


def test_frontend_serving():
    response = client.get("/")
    assert response.status_code == 200
    assert "CinéMatch" in response.text

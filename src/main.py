import os
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .engine import RecommenderEngine
from .schemas import (
    MovieSummary,
    MovieDetail,
    GuestRecommendationRequest,
    UserProfileResponse,
    RecommendationResponse,
    SystemStatsResponse,
)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload the recommender engine at startup
    RecommenderEngine.get_instance(base_dir=BASE_DIR)
    yield


app = FastAPI(
    title="CinéMatch API - Movie Recommender System",
    description=(
        "Production-ready Movie Recommender System API powered by SVD Matrix Factorization, "
        "collaborative filtering, and real-time visitor personalization (solving cold start). "
        "Trained on the MovieLens 100k dataset."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for external frontends (e.g. Next.js, React, Mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_engine() -> RecommenderEngine:
    return RecommenderEngine.get_instance(base_dir=BASE_DIR)


# ─────────────────────────────────────────────────────────────
# Health & Stats
# ─────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
def health_check():
    engine = get_engine()
    return {
        "status": "healthy",
        "model_loaded": engine.model is not None,
        "movies_count": len(engine.movies_df),
        "version": "1.0.0"
    }


@app.get("/api/stats", response_model=SystemStatsResponse, tags=["System"])
def get_system_stats():
    """Retourne les métriques de modélisation (RMSE, MAE) et du dataset MovieLens."""
    return get_engine().get_stats()


@app.get("/api/genres", response_model=List[str], tags=["Movies"])
def get_genres():
    """Retourne la liste de tous les genres cinématographiques disponibles."""
    return get_engine().all_genres


# ─────────────────────────────────────────────────────────────
# Movies & Search
# ─────────────────────────────────────────────────────────────
@app.get("/api/movies/search", response_model=List[MovieSummary], tags=["Movies"])
def search_movies(
    q: str = Query("", description="Terme de recherche dans le titre du film"),
    limit: int = Query(20, ge=1, le=100, description="Nombre maximum de résultats"),
    genre: Optional[str] = Query(None, description="Filtrer par genre exact")
):
    """Recherche des films par titre avec tri par popularité historique."""
    return get_engine().search_movies(query=q, limit=limit, genre=genre)


@app.get("/api/movies/{movie_id}", response_model=MovieDetail, tags=["Movies"])
def get_movie_detail(movie_id: int):
    """Retourne les détails complets d'un film, ses tags et ses films similaires."""
    movie = get_engine().get_movie_detail(movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film avec l'ID {movie_id} introuvable."
        )
    return movie


@app.get("/api/movies/{movie_id}/similar", response_model=List[MovieSummary], tags=["Movies"])
def get_similar_movies(
    movie_id: int,
    n: int = Query(10, ge=1, le=50, description="Nombre de films similaires")
):
    """
    Calcule les films les plus proches dans l'espace latent SVD (similarité cosinus des facteurs qi).
    Deux films sont proches si les utilisateurs ayant aimé l'un apprécient aussi l'autre.
    """
    engine = get_engine()
    if movie_id not in engine.movie_lookup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film avec l'ID {movie_id} introuvable."
        )
    return engine.get_similar_movies(movie_id, n=n)


# ─────────────────────────────────────────────────────────────
# Users & Recommendations
# ─────────────────────────────────────────────────────────────
@app.get("/api/users", response_model=List[int], tags=["Users"])
def get_sample_users(count: int = Query(50, ge=5, le=610)):
    """Retourne une liste d'IDs d'utilisateurs disponibles pour exploration."""
    return get_engine().get_sample_users(count=count)


@app.get("/api/users/{user_id}/profile", response_model=UserProfileResponse, tags=["Users"])
def get_user_profile(user_id: int):
    """Retourne l'historique de visionnage et la distribution des genres d'un utilisateur."""
    profile = get_engine().get_user_profile(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utilisateur {user_id} introuvable dans le jeu d'entraînement."
        )
    return profile


@app.get("/api/users/{user_id}/recommendations", response_model=RecommendationResponse, tags=["Recommendations"])
def get_user_recommendations(
    user_id: int,
    n: int = Query(10, ge=1, le=50, description="Nombre de recommandations"),
    genre: Optional[str] = Query(None, description="Filtrer par genre"),
    min_ratings: int = Query(0, ge=0, description="Seuil d'évaluations minimales du film")
):
    """Génère les meilleures recommandations personnalisées pour un utilisateur existant."""
    engine = get_engine()
    if user_id not in engine.raw_to_inner_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utilisateur {user_id} non trouvé dans les profils entraînés."
        )

    recs = engine.get_user_recommendations(
        user_id=user_id,
        n=n,
        genre=genre,
        min_ratings=min_ratings
    )
    return RecommendationResponse(
        count=len(recs),
        target=f"Utilisateur #{user_id}",
        recommendations=recs
    )


@app.post("/api/recommendations/guest", response_model=RecommendationResponse, tags=["Recommendations"])
def get_guest_recommendations(request: GuestRecommendationRequest):
    """
    Génère des recommandations personnalisées en temps réel pour un NOUVEL utilisateur (visiteur).
    Résout le problème du Cold-Start via 'folding-in' par régression Ridge sur les facteurs latents SVD.
    """
    ratings_tuples = [(item.movieId, item.rating) for item in request.ratings]
    recs = get_engine().get_guest_recommendations(
        ratings=ratings_tuples,
        n=request.n,
        genre=request.genre,
        min_ratings=request.min_ratings
    )
    return RecommendationResponse(
        count=len(recs),
        target="Invité (Profil dynamique en temps réel)",
        recommendations=recs
    )


# ─────────────────────────────────────────────────────────────
# Static Frontend Serving
# ─────────────────────────────────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        return FileResponse(STATIC_DIR / "index.html")

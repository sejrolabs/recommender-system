from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class MovieSummary(BaseModel):
    movieId: int = Field(..., description="ID unique du film")
    title: str = Field(..., description="Titre complet du film")
    year: Optional[int] = Field(None, description="Année de sortie extraite du titre")
    genres: List[str] = Field(default_factory=list, description="Liste des genres")
    vote_count: int = Field(0, description="Nombre total d'évaluations dans le dataset")
    vote_avg: float = Field(0.0, description="Note moyenne historique")
    imdbId: Optional[str] = Field(None, description="Identifiant IMDb formaté")
    imdbUrl: Optional[str] = Field(None, description="Lien direct vers la page IMDb")
    predictedRating: Optional[float] = Field(None, description="Note prédite par le modèle SVD (sur 5)")
    similarity: Optional[float] = Field(None, description="Score de similarité cosinus (de -1 à 1)")


class MovieDetail(MovieSummary):
    tags: List[str] = Field(default_factory=list, description="Tags associés par la communauté")
    similarMovies: List[MovieSummary] = Field(default_factory=list, description="Films les plus similaires")


class RatingInput(BaseModel):
    movieId: int = Field(..., description="ID du film noté")
    rating: float = Field(..., ge=0.5, le=5.0, description="Note attribuée entre 0.5 et 5.0")


class GuestRecommendationRequest(BaseModel):
    ratings: List[RatingInput] = Field(..., min_length=1, description="Liste des films notés par le visiteur")
    n: int = Field(10, ge=1, le=50, description="Nombre de recommandations souhaitées")
    genre: Optional[str] = Field(None, description="Filtrer par genre optionnel")
    min_ratings: int = Field(0, ge=0, description="Seuil minimal d'évaluations historiques du film")


class UserProfileResponse(BaseModel):
    userId: int
    ratingsCount: int
    avgRating: float
    topRated: List[MovieSummary]
    genreDistribution: Dict[str, int]


class RecommendationResponse(BaseModel):
    count: int
    target: str = Field(..., description="Description de la cible (User ID ou Invité)")
    recommendations: List[MovieSummary]


class SystemStatsResponse(BaseModel):
    totalMovies: int
    totalRatings: int
    totalUsers: int
    sparsityPercent: float
    modelType: str
    modelRMSE: float
    modelMAE: float
    latentDimensions: int

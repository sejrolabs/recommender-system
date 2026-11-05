---
title: CinéMatch — Movie Recommender System (SVD)
emoji: 🎬
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
license: mit
short_description: Système de recommandation de films par factorisation matricielle SVD (MovieLens)
---

# 🎬 CinéMatch — Système de Recommandation de Films

Application interactive basée sur la **factorisation matricielle SVD** (Funk SVD), entraînée sur le dataset MovieLens 100k.

## Fonctionnalités

- **Mode Visiteur** : notez quelques films → recommandations personnalisées en temps réel (Cold Start résolu par *folding-in* Ridge Regression sur les facteurs latents)
- **Profils utilisateurs** : explorez les 610 profils réels du dataset MovieLens
- **Films similaires** : similarité cosinus dans l'espace latent SVD ($q_i \in \mathbb{R}^{50}$)
- **Métriques** : tableau comparatif des modèles et visualisation mathématique du SVD

## Stack

- **Backend** : FastAPI + Python 3.11
- **Modèle** : SVD (scikit-surprise), RMSE = 0.8806
- **Frontend** : HTML/CSS/JS (Tailwind CSS)
- **Dataset** : [MovieLens ml-latest-small](https://grouplens.org/datasets/movielens/)

## Code source

👉 [GitHub Repository](https://github.com/sejrolabs/recommender-system)

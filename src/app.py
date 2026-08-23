# NOTE : ce script est situé dans src/, mais les chemins ci-dessous sont relatifs
# au dossier RACINE du projet — car Streamlit référence le dossier depuis lequel
# la commande est lancée, pas l'emplacement du fichier .py.
# À lancer depuis la RACINE du projet avec : streamlit run src/app.py
import streamlit as st
import pandas as pd
import numpy as np
import joblib
from collections import Counter

# ─────────────────────────────────────────────
# Configuration de la page
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Système de recommandation de films",
    page_icon="🎬",
    layout="wide"
)

# ─────────────────────────────────────────────
# Chargement des données et du modèle (mis en cache)
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    train_ratings = pd.read_csv('data/processed/train_ratings.csv')
    movies = pd.read_csv('data/movies.csv')
    return train_ratings, movies

@st.cache_resource
def load_model():
    return joblib.load('outputs/models/svd_model.pkl')

train_ratings, movies = load_data()
svd_model = load_model()

# ─────────────────────────────────────────────
# Fonction de recommandation pour un utilisateur (identique au notebook)
# ─────────────────────────────────────────────
def get_top_n_recommendations(user_id, n=10):
    all_movie_ids = movies['movieId'].unique()
    seen_movies = train_ratings[train_ratings['userId'] == user_id]['movieId'].unique()
    unseen_movies = [m for m in all_movie_ids if m not in seen_movies]

    predictions = []
    for movie_id in unseen_movies:
        pred = svd_model.predict(user_id, movie_id)
        predictions.append((movie_id, pred.est))

    predictions.sort(key=lambda x: x[1], reverse=True)
    top_n = predictions[:n]

    result = []
    for movie_id, pred_rating in top_n:
        title = movies[movies['movieId'] == movie_id]['title'].values[0]
        genres = movies[movies['movieId'] == movie_id]['genres'].values[0]
        result.append({
            'Film': title,
            'Genres': genres.replace('|', ', '),
            'Note prédite': round(pred_rating, 2)
        })

    return pd.DataFrame(result)

# ─────────────────────────────────────────────
# Fonctions pour la recherche de films similaires
# On réutilise les facteurs latents appris par le SVD (svd_model.qi) :
# deux films sont similaires si leurs vecteurs de facteurs latents sont proches
# (similarité cosinus), sans avoir besoin de reconstruire une matrice de similarité séparée.
# ─────────────────────────────────────────────
def search_movies(query, max_results=15):
    if not query:
        return pd.DataFrame()
    mask = movies['title'].str.contains(query, case=False, na=False, regex=False)
    return movies[mask].head(max_results)

@st.cache_resource
def get_item_factors():
    """Extrait les facteurs latents (qi) du modèle SVD, indexés par movieId réel."""
    trainset = svd_model.trainset
    item_factors = {}
    for inner_id in trainset.all_items():
        raw_id = trainset.to_raw_iid(inner_id)
        item_factors[raw_id] = svd_model.qi[inner_id]
    return item_factors

def get_similar_movies(movie_id, n=10):
    item_factors = get_item_factors()

    if movie_id not in item_factors:
        return pd.DataFrame()

    target_vector = item_factors[movie_id].reshape(1, -1)
    all_ids = list(item_factors.keys())
    all_vectors = np.array([item_factors[mid] for mid in all_ids])

    norms = np.linalg.norm(all_vectors, axis=1) * np.linalg.norm(target_vector)
    norms[norms == 0] = 1e-10
    similarities = (all_vectors @ target_vector.T).flatten() / norms

    sim_df = pd.DataFrame({'movieId': all_ids, 'similarity': similarities})
    sim_df = sim_df[sim_df['movieId'] != movie_id]
    sim_df = sim_df.sort_values('similarity', ascending=False).head(n)

    sim_df = sim_df.merge(movies, on='movieId')
    sim_df['Genres'] = sim_df['genres'].str.replace('|', ', ')
    sim_df['Similarité'] = sim_df['similarity'].round(3)
    return sim_df[['title', 'Genres', 'Similarité']].rename(columns={'title': 'Film'})

# ─────────────────────────────────────────────
# En-tête
# ─────────────────────────────────────────────
st.title("🎬 Système de recommandation de films")
st.markdown(
    "Démo interactive d'un système de recommandation basé sur la **factorisation matricielle (SVD)**, "
    "entraîné sur le dataset [MovieLens](https://grouplens.org/datasets/movielens/)."
)
st.divider()

# ─────────────────────────────────────────────
# Deux onglets
# ─────────────────────────────────────────────
tab1, tab2 = st.tabs(["🍿 Recommandations personnalisées", "🔍 Recherche de films similaires"])

# ═══════════════════════════════════════════════════════════
# ONGLET 1 — Recommandations personnalisées par utilisateur
# ═══════════════════════════════════════════════════════════
with tab1:
    col1, col2 = st.columns([1, 2])

    with col1:
        user_ids = sorted(train_ratings['userId'].unique())
        selected_user = st.selectbox("Choisir un utilisateur", user_ids)

        n_recommendations = st.slider("Nombre de recommandations", min_value=5, max_value=20, value=10)

        st.metric("Films déjà notés par cet utilisateur", len(train_ratings[train_ratings['userId'] == selected_user]))

    with col2:
        st.subheader(f"⭐ Films préférés de l'utilisateur {selected_user}")

        user_history = train_ratings[train_ratings['userId'] == selected_user].merge(movies, on='movieId')
        user_history = user_history.sort_values('rating', ascending=False)[['title', 'genres', 'rating']].head(5)
        user_history.columns = ['Film', 'Genres', 'Note donnée']
        user_history['Genres'] = user_history['Genres'].str.replace('|', ', ')

        st.dataframe(user_history, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader(f"🍿 Top {n_recommendations} recommandations pour l'utilisateur {selected_user}")

    with st.spinner("Calcul des recommandations en cours..."):
        recommendations = get_top_n_recommendations(selected_user, n=n_recommendations)

    st.dataframe(recommendations, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("📊 Répartition des genres recommandés")

    genre_counter = Counter()
    for genres_str in recommendations['Genres']:
        genre_counter.update([g.strip() for g in genres_str.split(',')])

    genre_df = pd.DataFrame(genre_counter.most_common(), columns=['Genre', 'Nombre'])
    st.bar_chart(genre_df.set_index('Genre'))

# ═══════════════════════════════════════════════════════════
# ONGLET 2 — Recherche de films et films similaires
# ═══════════════════════════════════════════════════════════
with tab2:
    st.subheader("🔍 Rechercher un film")

    query = st.text_input("Tapez le titre d'un film (ou une partie du titre)", placeholder="Ex : Matrix, Toy Story, Batman...")

    if query:
        search_results = search_movies(query)

        if search_results.empty:
            st.warning("Aucun film trouvé pour cette recherche.")
        else:
            movie_options = {
                f"{row['title']} — {row['genres'].replace('|', ', ')}": row['movieId']
                for _, row in search_results.iterrows()
            }
            selected_label = st.selectbox("Sélectionnez le film exact", list(movie_options.keys()))
            selected_movie_id = movie_options[selected_label]

            n_similar = st.slider("Nombre de films similaires à afficher", min_value=5, max_value=20, value=10)

            st.divider()
            st.subheader(f"🎯 Films similaires à « {selected_label.split(' — ')[0]} »")
            st.caption(
                "Similarité calculée à partir des facteurs latents appris par le modèle SVD : "
                "deux films sont considérés comme similaires si les utilisateurs qui les apprécient "
                "ont des profils de goûts proches, pas seulement s'ils partagent les mêmes genres."
            )

            with st.spinner("Recherche de films similaires..."):
                similar_movies = get_similar_movies(selected_movie_id, n=n_similar)

            if similar_movies.empty:
                st.info("Ce film ne fait pas partie du jeu d'entraînement du modèle (trop peu de notes), impossible de calculer des films similaires.")
            else:
                st.dataframe(similar_movies, use_container_width=True, hide_index=True)
    else:
        st.info("👆 Commencez à taper le nom d'un film pour voir des suggestions similaires.")

# ─────────────────────────────────────────────
# Pied de page
# ─────────────────────────────────────────────
st.divider()
st.caption(
    "Projet réalisé par [sejrolabs](https://github.com/sejrolabs) — "
    "Code source disponible sur [GitHub](https://github.com/sejrolabs/recommender-system)"
)
# 🎬 Système de recommandation de films

Système de recommandation de films combinant **filtrage collaboratif** et **factorisation matricielle (SVD)**, entraîné sur le dataset **MovieLens**, avec une application interactive **Streamlit** pour explorer les résultats.

## 📌 Contexte

Ce projet a pour objectif de recommander des films à des utilisateurs à partir de leur historique de notes, en comparant plusieurs approches classiques de systèmes de recommandation — des plus simples (baseline) aux plus avancées (SVD, technique ayant remporté le Netflix Prize). Il illustre en particulier la gestion de matrices **creuses (sparse)**, un enjeu central de ce type de problème.

## 📊 Dataset

- **Source** : [MovieLens (ml-latest-small)](https://grouplens.org/datasets/movielens/)
- **Volume** : 610 utilisateurs, 9 724 films, 100 836 notes
- **Sparsité de la matrice utilisateur-film** : 98.30% des cases sont vides — seulement 1.70% des combinaisons (utilisateur, film) possibles ont été notées

## 🛠️ Méthodologie

| Notebook | Contenu |
|----------|---------|
| `01_exploration.ipynb` | Distribution des notes, analyse de la sparsité, répartition par genre |
| `02_preprocessing.ipynb` | Split train/test **stratifié par utilisateur** (garantit que chaque utilisateur est représenté dans les deux ensembles) |
| `03_modeling.ipynb` | Comparaison de 3 approches : baseline, filtrage collaboratif, SVD |
| `04_recommendations.ipynb` | Génération de recommandations concrètes et évaluation Precision@K |

### Un split adapté au problème

Un split aléatoire classique risquerait d'exclure certains utilisateurs du train set. Ce projet utilise un split **par utilisateur** : pour chaque utilisateur, 80% de ses notes vont en train et 20% en test — garantissant que les 610 utilisateurs sont représentés dans les deux ensembles.

## 📈 Résultats

### Comparaison des approches (RMSE sur les notes prédites)

| Approche | RMSE | MAE |
|----------|------|-----|
| Baseline (moyenne par film) | 0.9856 | 0.7584 |
| Filtrage collaboratif (item-based, similarité cosinus) | 0.9048 | 0.6899 |
| **SVD (factorisation matricielle)** | **0.8806** | **0.6742** |

Le modèle **SVD** obtient les meilleurs résultats, confirmant l'intérêt de la factorisation matricielle par rapport à des approches plus simples — chaque niveau de complexité supplémentaire apporte un gain réel et mesurable.

### Évaluation Precision@10

**Precision@10 moyenne : 0.0306** (sur 10 films recommandés, ~0.3 correspondent à un film que l'utilisateur a noté ≥ 4 dans le test set).

⚠️ **Ce chiffre doit être interprété avec son contexte**, pas pris isolément :
- Chaque utilisateur n'a souvent que 2 à 5 films "aimés" (note ≥ 4) dans l'ensemble de test — le score maximum atteignable est donc mathématiquement plafonné bien en dessous de 1.0
- L'espace de films candidats est très large (~9 700 films pour seulement 10 recommandations)
- Ce type de score (0.02 à 0.10) est cohérent avec ce qui est couramment rapporté dans la littérature sur MovieLens avec ce protocole d'évaluation

Le **RMSE** reste donc la métrique la plus fiable pour juger la qualité globale du modèle dans ce projet ; le Precision@10 est présenté ici en toute transparence, avec ses limites plutôt que comme un score à maximiser isolément.

## 🖥️ Application interactive (Streamlit)

Une démo interactive permet d'explorer le modèle sans toucher au code :

- **Onglet 1 — Recommandations personnalisées** : sélection d'un utilisateur, visualisation de ses films préférés, génération de ses N meilleures recommandations avec répartition des genres
- **Onglet 2 — Recherche de films similaires** : recherche par titre, puis affichage des films les plus proches selon les **facteurs latents appris par le SVD** (similarité de goûts entre utilisateurs, pas seulement de genres)

### Lancer l'application en local

```bash
pip install -r requirements.txt
streamlit run src/app.py
```

*(commande à lancer depuis la racine du projet)*

## 🚀 Comment reproduire ce projet

```bash
git clone https://github.com/sejrolabs/recommender-system.git
cd recommender-system

pip install -r requirements.txt

# Télécharger movies.csv, ratings.csv, tags.csv, links.csv depuis MovieLens
# et les placer dans data/

# Exécuter les notebooks dans l'ordre (01 → 04)
streamlit run src/app.py
```

## 📦 Stack technique

- **Langage** : Python 3.11
- **Manipulation de données** : pandas, numpy
- **Machine Learning** : scikit-learn, scikit-surprise (SVD)
- **Application interactive** : Streamlit
- **Visualisation** : matplotlib, seaborn

## 🔍 Limites et pistes d'amélioration

- Le filtrage collaboratif item-based a été évalué sur un échantillon (raisons de temps de calcul) — une implémentation optimisée permettrait une évaluation complète
- Le **cold start** (nouveaux utilisateurs/films sans historique) n'est pas géré — une approche hybride (contenu + collaboratif) serait nécessaire en production
- Le fichier `tags.csv` n'a pas été exploité — il pourrait enrichir un système hybride basé sur le contenu
- Une validation croisée (plutôt qu'un split unique) renforcerait la robustesse des comparaisons de RMSE
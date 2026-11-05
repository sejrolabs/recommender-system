"""
Script de lancement pour le serveur FastAPI CinéMatch.

Lancement local :
    python run_server.py

Ou directement avec uvicorn :
    uvicorn src.main:app --reload --port 8000
"""

import sys
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=" * 60)
    print("🎬 Démarrage du serveur CinéMatch (FastAPI + SVD Recommender)")
    print("=" * 60)
    print(f"📍 Application web : http://127.0.0.1:{port}")
    print(f"📖 Swagger API     : http://127.0.0.1:{port}/docs")
    print("=" * 60)
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=True)

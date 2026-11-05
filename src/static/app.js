// CinéMatch Frontend Application

// State
let allGenres = [];
let guestRatings = [
  { movieId: 2571, title: "Matrix, The (1999)", rating: 5.0, genres: ["Action", "Sci-Fi"] },
  { movieId: 296, title: "Pulp Fiction (1994)", rating: 4.5, genres: ["Comedy", "Crime", "Drama"] }
];
let searchDebounceTimer = null;
let guestRecsDebounceTimer = null;

const POPULAR_STARTERS = [
  { movieId: 2571, title: "Matrix, The (1999)", rating: 5.0 },
  { movieId: 296, title: "Pulp Fiction (1994)", rating: 4.5 },
  { movieId: 1, title: "Toy Story (1995)", rating: 4.0 },
  { movieId: 260, title: "Star Wars: Episode IV (1977)", rating: 4.5 },
  { movieId: 318, title: "Shawshank Redemption, The (1994)", rating: 5.0 },
  { movieId: 589, title: "Terminator 2: Judgment Day (1991)", rating: 4.5 },
  { movieId: 2959, title: "Fight Club (1999)", rating: 4.5 },
  { movieId: 356, title: "Forrest Gump (1994)", rating: 4.0 }
];

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
  await loadGenres();
  renderQuickStarters();
  renderGuestRatedList();
  triggerGuestRecs();
  loadSampleUsers();
  loadStats();
});

// ─────────────────────────────────────────────────────────────
// Navigation & Tab Switching
// ─────────────────────────────────────────────────────────────
function switchTab(tabId) {
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.add("hidden"));
  document.getElementById(tabId).classList.remove("hidden");

  // Update navbar styles
  const btnMap = {
    "tab-guest": "nav-btn-guest",
    "tab-users": "nav-btn-users",
    "tab-similar": "nav-btn-similar",
    "tab-metrics": "nav-btn-metrics"
  };

  Object.entries(btnMap).forEach(([pane, btnId]) => {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    if (pane === tabId) {
      btn.className = "px-3.5 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all bg-indigo-600 text-white shadow-md shadow-indigo-600/30";
    } else {
      btn.className = "px-3.5 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all text-slate-400 hover:text-white hover:bg-slate-800/60";
    }
  });

  if (window.lucide) lucide.createIcons();
}

// ─────────────────────────────────────────────────────────────
// Genres & Metadata
// ─────────────────────────────────────────────────────────────
async function loadGenres() {
  try {
    const res = await fetch("/api/genres");
    if (res.ok) {
      allGenres = await res.json();
      const guestFilter = document.getElementById("guest-genre-filter");
      guestFilter.innerHTML = '<option value="">Tous les genres</option>';
      allGenres.forEach(g => {
        guestFilter.innerHTML += `<option value="${g}">${g}</option>`;
      });
    }
  } catch (err) {
    console.error("Erreur chargement genres:", err);
  }
}

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    if (res.ok) {
      const data = await res.json();
      document.getElementById("metric-movies").innerText = Number(data.totalMovies).toLocaleString();
      document.getElementById("metric-users").innerText = Number(data.totalUsers).toLocaleString();
      document.getElementById("metric-ratings").innerText = Number(data.totalRatings).toLocaleString();
      document.getElementById("metric-sparsity").innerText = data.sparsityPercent + "%";
    }
  } catch (err) {
    console.error("Erreur chargement stats:", err);
  }
}

// ─────────────────────────────────────────────────────────────
// Mode Invité (Cold Start Real-time Recommendations)
// ─────────────────────────────────────────────────────────────
function renderQuickStarters() {
  const container = document.getElementById("quick-starters-list");
  if (!container) return;
  container.innerHTML = "";

  POPULAR_STARTERS.forEach(m => {
    const isRated = guestRatings.some(r => r.movieId === m.movieId);
    const pill = document.createElement("button");
    pill.className = `px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
      isRated 
        ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 cursor-default" 
        : "bg-slate-800/80 hover:bg-indigo-600 hover:text-white text-slate-300 border border-slate-700/60"
    }`;
    pill.innerHTML = `<span>${m.title.split("(")[0]}</span> ${isRated ? '<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i>' : '<i data-lucide="plus" class="w-3 h-3"></i>'}`;
    if (!isRated) {
      pill.onclick = () => addGuestRating(m.movieId, m.title, m.rating);
    }
    container.appendChild(pill);
  });
  if (window.lucide) lucide.createIcons();
}

function handleGuestSearch(query) {
  clearTimeout(searchDebounceTimer);
  const resultsContainer = document.getElementById("guest-search-results");
  
  if (!query || query.trim().length < 2) {
    resultsContainer.classList.add("hidden");
    resultsContainer.innerHTML = "";
    return;
  }

  searchDebounceTimer = setTimeout(async () => {
    try {
      const res = await fetch(`/api/movies/search?q=${encodeURIComponent(query)}&limit=8`);
      if (res.ok) {
        const movies = await res.json();
        renderGuestSearchResults(movies);
      }
    } catch (err) {
      console.error("Erreur recherche:", err);
    }
  }, 250);
}

function renderGuestSearchResults(movies) {
  const container = document.getElementById("guest-search-results");
  container.innerHTML = "";

  if (movies.length === 0) {
    container.innerHTML = `<div class="p-3 text-xs text-slate-400 bg-slate-900/90 rounded-xl border border-slate-800">Aucun film trouvé.</div>`;
    container.classList.remove("hidden");
    return;
  }

  movies.forEach(m => {
    const isRated = guestRatings.some(r => r.movieId === m.movieId);
    const item = document.createElement("div");
    item.className = "p-3 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-800 flex items-center justify-between gap-3 transition-colors";
    
    item.innerHTML = `
      <div class="min-w-0 flex-1">
        <p class="text-xs font-semibold text-white truncate">${m.title}</p>
        <div class="flex items-center gap-2 mt-0.5 text-[10px] text-slate-400">
          <span>${m.year || "N/A"}</span>
          <span>•</span>
          <span class="truncate">${m.genres.slice(0, 2).join(", ")}</span>
          <span>•</span>
          <span>⭐ ${m.vote_avg} (${m.vote_count} votes)</span>
        </div>
      </div>
      <div>
        ${isRated ? `
          <span class="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-md border border-emerald-500/20 flex items-center gap-1">
            <i data-lucide="check" class="w-3 h-3"></i> Noté
          </span>
        ` : `
          <button onclick="addGuestRating(${m.movieId}, '${escapeQuotes(m.title)}', 5.0)" class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1 shadow-sm transition-all">
            <i data-lucide="plus" class="w-3.5 h-3.5"></i> Noter
          </button>
        `}
      </div>
    `;
    container.appendChild(item);
  });

  container.classList.remove("hidden");
  if (window.lucide) lucide.createIcons();
}

function addGuestRating(movieId, title, rating = 5.0, genres = []) {
  if (guestRatings.some(r => r.movieId === movieId)) return;
  guestRatings.push({ movieId, title, rating, genres });
  
  // Clear search
  const searchInput = document.getElementById("guest-movie-search");
  if (searchInput) searchInput.value = "";
  document.getElementById("guest-search-results").classList.add("hidden");

  renderQuickStarters();
  renderGuestRatedList();
  triggerGuestRecs();
}

function removeGuestRating(movieId) {
  guestRatings = guestRatings.filter(r => r.movieId !== movieId);
  renderQuickStarters();
  renderGuestRatedList();
  triggerGuestRecs();
}

function updateGuestRatingValue(movieId, newRating) {
  const item = guestRatings.find(r => r.movieId === movieId);
  if (item) {
    item.rating = parseFloat(newRating);
    triggerGuestRecs();
  }
}

function clearGuestRatings() {
  guestRatings = [];
  renderQuickStarters();
  renderGuestRatedList();
  triggerGuestRecs();
}

function renderGuestRatedList() {
  const countEl = document.getElementById("guest-rated-count");
  const emptyEl = document.getElementById("guest-empty-ratings");
  const listEl = document.getElementById("guest-rated-list");
  const clearBtn = document.getElementById("btn-clear-ratings");

  countEl.innerText = guestRatings.length;

  if (guestRatings.length === 0) {
    emptyEl.classList.remove("hidden");
    listEl.classList.add("hidden");
    clearBtn.classList.add("hidden");
    listEl.innerHTML = "";
    return;
  }

  emptyEl.classList.add("hidden");
  listEl.classList.remove("hidden");
  clearBtn.classList.remove("hidden");
  listEl.innerHTML = "";

  guestRatings.forEach(r => {
    const item = document.createElement("div");
    item.className = "p-2.5 bg-slate-900/90 rounded-xl border border-slate-800 flex items-center justify-between gap-3 text-xs";
    
    // Star selector HTML
    const starOptions = [1, 2, 3, 4, 5].map(val => `
      <button onclick="updateGuestRatingValue(${r.movieId}, ${val})" class="star-btn ${r.rating >= val ? 'text-amber-400' : 'text-slate-600'} hover:text-amber-300">
        ★
      </button>
    `).join("");

    item.innerHTML = `
      <div class="min-w-0 flex-1">
        <span class="font-semibold text-slate-200 block truncate">${r.title}</span>
        <div class="flex items-center gap-1.5 mt-0.5 text-[11px] text-slate-400">
          <span>Note : <strong class="text-amber-400">${r.rating}/5</strong></span>
          <div class="inline-flex gap-0.5 ml-2 text-sm">${starOptions}</div>
        </div>
      </div>
      <button onclick="removeGuestRating(${r.movieId})" class="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors" title="Retirer">
        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
      </button>
    `;
    listEl.appendChild(item);
  });

  if (window.lucide) lucide.createIcons();
}

function triggerGuestRecs() {
  clearTimeout(guestRecsDebounceTimer);
  guestRecsDebounceTimer = setTimeout(async () => {
    await fetchAndRenderGuestRecs();
  }, 200);
}

async function fetchAndRenderGuestRecs() {
  const grid = document.getElementById("guest-recs-grid");
  const indicator = document.getElementById("guest-status-indicator");
  const genre = document.getElementById("guest-genre-filter").value;
  const count = parseInt(document.getElementById("guest-count-slider").value) || 10;
  const minVotes = parseInt(document.getElementById("guest-minvotes-slider").value) || 0;

  indicator.innerHTML = `<span class="inline-flex items-center gap-1 text-indigo-400"><i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i> Calcul en cours...</span>`;
  if (window.lucide) lucide.createIcons();

  try {
    const payload = {
      ratings: guestRatings.map(r => ({ movieId: r.movieId, rating: r.rating })),
      n: count,
      genre: genre || null,
      min_ratings: minVotes
    };

    const res = await fetch("/api/recommendations/guest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const data = await res.json();
      indicator.innerHTML = `<span class="text-emerald-400 flex items-center gap-1"><i data-lucide="check" class="w-3.5 h-3.5"></i> ${data.count} recommandations générées</span>`;
      renderMovieCards(grid, data.recommendations, true);
    } else {
      indicator.innerHTML = `<span class="text-rose-400">Erreur lors de la recommandation</span>`;
    }
  } catch (err) {
    console.error("Erreur recommandation invité:", err);
    indicator.innerHTML = `<span class="text-rose-400">Erreur serveur</span>`;
  }
  if (window.lucide) lucide.createIcons();
}

// ─────────────────────────────────────────────────────────────
// Mode Profils Utilisateurs (1-610)
// ─────────────────────────────────────────────────────────────
async function loadSampleUsers() {
  try {
    const res = await fetch("/api/users?count=100");
    if (res.ok) {
      const users = await res.json();
      const selector = document.getElementById("user-selector");
      selector.innerHTML = "";
      users.forEach(uid => {
        selector.innerHTML += `<option value="${uid}">Utilisateur #${uid}</option>`;
      });
      if (users.length > 0) {
        loadUserProfile(users[0]);
      }
    }
  } catch (err) {
    console.error("Erreur chargement utilisateurs:", err);
  }
}

async function loadUserProfile(userId) {
  try {
    // 1. Profile history
    const resProfile = await fetch(`/api/users/${userId}/profile`);
    if (resProfile.ok) {
      const profile = await resProfile.json();
      document.getElementById("user-stat-count").innerText = profile.ratingsCount;
      document.getElementById("user-stat-avg").innerText = profile.avgRating;
      
      // Genre breakdown bars
      renderUserGenreBars(profile.genreDistribution);

      // Top history
      const historyContainer = document.getElementById("user-top-history");
      historyContainer.innerHTML = "";
      profile.topRated.forEach(m => {
        const item = document.createElement("div");
        item.className = "p-2.5 bg-slate-900/70 rounded-xl border border-slate-800 flex items-center justify-between gap-3 text-xs";
        item.innerHTML = `
          <div class="min-w-0 flex-1 truncate">
            <span class="font-semibold text-white truncate block">${m.title}</span>
            <span class="text-[10px] text-slate-400">${m.genres.join(", ")}</span>
          </div>
          <span class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 font-bold border border-amber-500/20">
            ★ ${m.vote_avg}
          </span>
        `;
        historyContainer.appendChild(item);
      });
    }

    // 2. Recommendations for this user
    const resRecs = await fetch(`/api/users/${userId}/recommendations?n=10`);
    if (resRecs.ok) {
      const recsData = await resRecs.json();
      const grid = document.getElementById("user-recs-grid");
      renderMovieCards(grid, recsData.recommendations, true);
    }
  } catch (err) {
    console.error("Erreur profil utilisateur:", err);
  }
}

function renderUserGenreBars(genreDist) {
  const container = document.getElementById("user-genre-bars");
  container.innerHTML = "";
  const maxCount = Math.max(...Object.values(genreDist), 1);

  Object.entries(genreDist).slice(0, 6).forEach(([genre, count]) => {
    const percent = Math.round((count / maxCount) * 100);
    const row = document.createElement("div");
    row.className = "space-y-1";
    row.innerHTML = `
      <div class="flex justify-between text-xs">
        <span class="text-slate-300">${genre}</span>
        <span class="text-slate-400 text-[10px]">${count} film${count > 1 ? 's' : ''}</span>
      </div>
      <div class="w-full bg-slate-800/80 rounded-full h-1.5 overflow-hidden">
        <div class="bg-indigo-500 h-1.5 rounded-full" style="width: ${percent}%"></div>
      </div>
    `;
    container.appendChild(row);
  });
}

// ─────────────────────────────────────────────────────────────
// Mode Films Similaires (Facteurs Latents SVD)
// ─────────────────────────────────────────────────────────────
function handleSimilarSearch(query) {
  clearTimeout(searchDebounceTimer);
  const container = document.getElementById("similar-search-results");
  
  if (!query || query.trim().length < 2) {
    container.classList.add("hidden");
    container.innerHTML = "";
    return;
  }

  searchDebounceTimer = setTimeout(async () => {
    try {
      const res = await fetch(`/api/movies/search?q=${encodeURIComponent(query)}&limit=6`);
      if (res.ok) {
        const movies = await res.json();
        container.innerHTML = "";
        if (movies.length === 0) {
          container.innerHTML = `<div class="p-3 text-xs text-slate-400">Aucun film trouvé.</div>`;
        } else {
          movies.forEach(m => {
            const item = document.createElement("div");
            item.className = "p-3 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 flex items-center justify-between cursor-pointer transition-colors";
            item.onclick = () => selectSimilarTarget(m.movieId);
            item.innerHTML = `
              <div>
                <p class="text-xs font-semibold text-white">${m.title}</p>
                <p class="text-[10px] text-slate-400">${m.year || ''} • ${m.genres.join(", ")}</p>
              </div>
              <span class="text-xs text-indigo-400 font-medium flex items-center gap-1">
                Explorer <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
              </span>
            `;
            container.appendChild(item);
          });
        }
        container.classList.remove("hidden");
        if (window.lucide) lucide.createIcons();
      }
    } catch (err) {
      console.error("Erreur similar search:", err);
    }
  }, 250);
}

async function selectSimilarTarget(movieId) {
  document.getElementById("similar-search-results").classList.add("hidden");
  document.getElementById("similar-movie-search").value = "";

  try {
    const res = await fetch(`/api/movies/${movieId}`);
    if (res.ok) {
      const movie = await res.json();
      
      const targetCard = document.getElementById("similar-target-card");
      targetCard.innerHTML = `
        <div class="space-y-1.5">
          <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[11px] font-semibold">
            Film cible analysé
          </div>
          <h3 class="text-xl font-bold text-white">${movie.title}</h3>
          <div class="flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span>Sortie : <strong>${movie.year || "N/A"}</strong></span>
            <span>•</span>
            <span>⭐ ${movie.vote_avg} (${movie.vote_count} avis)</span>
            ${movie.tags.length > 0 ? `<span>•</span> <span>Tags: ${movie.tags.slice(0, 3).join(", ")}</span>` : ''}
          </div>
          <div class="flex flex-wrap gap-1 mt-1">
            ${movie.genres.map(g => `<span class="px-2 py-0.5 rounded text-[10px] font-medium badge-genre">${g}</span>`).join("")}
          </div>
        </div>
        ${movie.imdbUrl ? `
          <a href="${movie.imdbUrl}" target="_blank" class="px-4 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-semibold flex items-center gap-2 transition-colors self-start sm:self-center">
            <i data-lucide="external-link" class="w-4 h-4"></i>
            Voir sur IMDb
          </a>
        ` : ''}
      `;

      const grid = document.getElementById("similar-movies-grid");
      renderMovieCards(grid, movie.similarMovies, false);

      document.getElementById("similar-section-output").classList.remove("hidden");
      if (window.lucide) lucide.createIcons();
    }
  } catch (err) {
    console.error("Erreur sélection film similaire:", err);
  }
}

// ─────────────────────────────────────────────────────────────
// Utility: Render Movie Cards
// ─────────────────────────────────────────────────────────────
function renderMovieCards(container, movies, isPredicted = true) {
  container.innerHTML = "";

  if (!movies || movies.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-8 text-center text-slate-400 text-xs bg-slate-900/60 rounded-xl border border-slate-800">
        Aucun film correspondant aux critères.
      </div>
    `;
    return;
  }

  movies.forEach(m => {
    const card = document.createElement("div");
    card.className = "movie-card glass-panel p-4 rounded-2xl flex flex-col justify-between gap-3 relative overflow-hidden group";

    const genreBadges = m.genres.slice(0, 3).map(g => {
      let badgeClass = "badge-genre";
      const gl = g.toLowerCase();
      if (gl.includes("action") || gl.includes("thriller")) badgeClass = "badge-action";
      else if (gl.includes("sci-fi")) badgeClass = "badge-scifi";
      else if (gl.includes("comedy")) badgeClass = "badge-comedy";
      else if (gl.includes("drama")) badgeClass = "badge-drama";
      return `<span class="px-2 py-0.5 rounded text-[10px] font-medium ${badgeClass}">${g}</span>`;
    }).join("");

    let scoreBadge = "";
    if (isPredicted && m.predictedRating !== undefined) {
      scoreBadge = `
        <div class="flex items-center gap-1 px-2.5 py-1 rounded-xl bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 text-amber-300 font-bold text-xs shadow-sm">
          <span>★</span>
          <span>${m.predictedRating}</span>
          <span class="text-[9px] text-amber-400/70 font-normal">prédit</span>
        </div>
      `;
    } else if (m.similarity !== undefined) {
      const pct = Math.round(m.similarity * 100);
      scoreBadge = `
        <div class="flex items-center gap-1 px-2.5 py-1 rounded-xl bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 font-bold text-xs">
          <span>${pct}%</span>
          <span class="text-[9px] text-indigo-300/70 font-normal">proche</span>
        </div>
      `;
    }

    card.innerHTML = `
      <div>
        <div class="flex items-start justify-between gap-2 mb-2">
          <span class="text-xs font-semibold text-slate-400">${m.year || "N/A"}</span>
          ${scoreBadge}
        </div>
        <h4 class="text-sm font-bold text-white group-hover:text-indigo-300 transition-colors line-clamp-2 leading-snug">
          ${m.title}
        </h4>
        <div class="flex flex-wrap gap-1 mt-2">
          ${genreBadges}
        </div>
      </div>

      <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
        <span class="text-[10px] text-slate-500">
          ⭐ ${m.vote_avg} (${m.vote_count} votes)
        </span>
        <div class="flex items-center gap-2">
          <button onclick="exploreSimilarFromCard(${m.movieId})" class="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium" title="Explorer les films similaires">
            Similaires
          </button>
          ${m.imdbUrl ? `
            <a href="${m.imdbUrl}" target="_blank" class="p-1 text-slate-400 hover:text-amber-400 transition-colors" title="Fiche IMDb">
              <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
            </a>
          ` : ''}
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  if (window.lucide) lucide.createIcons();
}

function exploreSimilarFromCard(movieId) {
  switchTab("tab-similar");
  selectSimilarTarget(movieId);
}

function escapeQuotes(str) {
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

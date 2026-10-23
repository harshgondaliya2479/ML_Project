/**
 * CineMind AI - Client Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initStats();
  initKnowledgeTab();
  initKnnMovieTab();
  initKnnUserTab();
  initSvdMovieTab();
  initComparisonTab();
  initDnnUserTab();
});

/* ==========================================================================
   Tab Navigation
   ========================================================================== */
function initTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  const panels = document.querySelectorAll('.tab-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.dataset.tab;

      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetPanel = document.getElementById(`tab-${targetId}`);
      if (targetPanel) {
        targetPanel.classList.add('active');
      }
    });
  });
}

/* ==========================================================================
   Dataset Stats
   ========================================================================== */
async function initStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    document.getElementById('statRatings').textContent = Number(data.total_ratings).toLocaleString();
    document.getElementById('statUsers').textContent = Number(data.total_users).toLocaleString();
    document.getElementById('statMovies').textContent = Number(data.total_movies).toLocaleString();
    document.getElementById('statGenres').textContent = data.total_genres;

    // Populate genre selector
    const genreSelect = document.getElementById('genreSelect');
    if (genreSelect && data.genres) {
      genreSelect.innerHTML = '<option value="All">All Genres</option>';
      data.genres.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g;
        opt.textContent = g;
        genreSelect.appendChild(opt);
      });
    }
  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

/* ==========================================================================
   TAB 1: Knowledge Discovery
   ========================================================================== */
function initKnowledgeTab() {
  const genreSelect = document.getElementById('genreSelect');
  if (genreSelect) {
    genreSelect.addEventListener('change', () => {
      loadKnowledgeData(genreSelect.value);
    });
  }
  loadKnowledgeData('All');
}

async function loadKnowledgeData(genre) {
  const topPopEl = document.getElementById('knowledgeTopPopular');
  const mostPopEl = document.getElementById('knowledgeMostPopular');
  const topRatedEl = document.getElementById('knowledgeTopRated');
  const criteriaText = document.getElementById('criteriaText');

  topPopEl.innerHTML = '<div class="skeleton-loader">Loading recommendations...</div>';
  mostPopEl.innerHTML = '<div class="skeleton-loader">Loading recommendations...</div>';
  topRatedEl.innerHTML = '<div class="skeleton-loader">Loading recommendations...</div>';

  try {
    const res = await fetch(`/api/knowledge?genre=${encodeURIComponent(genre)}`);
    const data = await res.json();

    if (data.criteria && criteriaText) {
      criteriaText.textContent = `Filtered with min ${data.criteria.min_viewers_used} viewers & ★ ${data.criteria.min_rating_used}+ rating`;
    }

    renderSimpleList(topPopEl, data.top_popular_rated);
    renderSimpleList(mostPopEl, data.most_popular);
    renderSimpleList(topRatedEl, data.top_rated);
  } catch (err) {
    console.error('Failed to load knowledge recs:', err);
  }
}

function renderSimpleList(container, movies) {
  if (!movies || movies.length === 0) {
    container.innerHTML = '<div class="skeleton-loader">No movies found</div>';
    return;
  }

  container.innerHTML = movies.map((m, idx) => `
    <div class="movie-item-row">
      <div class="movie-rank">${idx + 1}</div>
      <div class="movie-item-info">
        <div class="movie-item-title" title="${escapeHtml(m.title)}">${escapeHtml(m.title)}</div>
        <div class="movie-item-meta">
          ${(m.genres || []).slice(0, 3).map(g => `<span class="movie-genre-tag">${escapeHtml(g)}</span>`).join('')}
        </div>
      </div>
      <div class="movie-item-stats">
        <div class="rating-pill">★ ${m.avg_rating}</div>
        <div class="views-pill">${m.watch_count} views</div>
      </div>
    </div>
  `).join('');
}

/* ==========================================================================
   TAB 2: Item-Based KNN
   ========================================================================== */
function initKnnMovieTab() {
  const input = document.getElementById('knnMovieInput');
  const dropdown = document.getElementById('knnMovieSuggestions');
  const btnSearch = document.getElementById('btnKnnMovieSearch');

  setupAutocomplete(input, dropdown, (selectedMovie) => {
    input.value = selectedMovie;
    runKnnMovieSearch(selectedMovie);
  });

  if (btnSearch) {
    btnSearch.addEventListener('click', () => {
      runKnnMovieSearch(input.value.trim());
    });
  }

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      runKnnMovieSearch(input.value.trim());
      dropdown.style.display = 'none';
    }
  });

  // Quick Chips
  document.querySelectorAll('.chip[data-movie]').forEach(chip => {
    chip.addEventListener('click', () => {
      const m = chip.dataset.movie;
      input.value = m;
      runKnnMovieSearch(m);
    });
  });

  // Initial search
  runKnnMovieSearch('Star Wars (1977)');
}

async function runKnnMovieSearch(movieName) {
  if (!movieName) return;
  const container = document.getElementById('knnMovieResults');
  const titleEl = document.getElementById('knnMovieResultTitle');

  titleEl.innerHTML = `Similar Movies to: <span class="highlight">${escapeHtml(movieName)}</span>`;
  container.innerHTML = '<div class="skeleton-loader">Computing K-Nearest Neighbors...</div>';

  try {
    const res = await fetch(`/api/knn/movie?movie=${encodeURIComponent(movieName)}&top_n=12`);
    const data = await res.json();

    if (data.error) {
      let suggestionsHtml = '';
      if (data.suggestions && data.suggestions.length > 0) {
        suggestionsHtml = `
          <div style="margin-top: 1rem;">
            <p style="color: var(--text-muted); margin-bottom: 0.5rem;">Did you mean one of these?</p>
            <div class="quick-chips">
              ${data.suggestions.map(s => `<button class="chip suggestion-chip" data-movie="${escapeHtml(s)}">${escapeHtml(s)}</button>`).join('')}
            </div>
          </div>
        `;
      }
      container.innerHTML = `
        <div class="panel-card" style="grid-column: 1 / -1; text-align: center; padding: 2.5rem;">
          <p style="color: #f87171; font-weight: 600; font-size: 1.1rem;">⚠️ ${data.error}</p>
          ${suggestionsHtml}
        </div>
      `;
      // Attach click listeners to suggestions
      container.querySelectorAll('.suggestion-chip').forEach(c => {
        c.addEventListener('click', () => {
          document.getElementById('knnMovieInput').value = c.dataset.movie;
          runKnnMovieSearch(c.dataset.movie);
        });
      });
      return;
    }

    renderMovieCards(container, data.recommendations, 'similarity', 'Similarity');
  } catch (err) {
    container.innerHTML = `<div class="skeleton-loader" style="color:#f87171;">Failed to compute recommendations</div>`;
  }
}

/* ==========================================================================
   TAB 3: User-Based KNN
   ========================================================================== */
function initKnnUserTab() {
  const userIdInput = document.getElementById('knnUserId');
  const simUsersInput = document.getElementById('knnSimilarCount');
  const movieCountInput = document.getElementById('knnMovieCount');
  const btnGenerate = document.getElementById('btnKnnUserGenerate');
  const btnRandom = document.getElementById('btnRandomUser');

  if (btnGenerate) {
    btnGenerate.addEventListener('click', () => {
      runKnnUserSearch(
        parseInt(userIdInput.value) || 307,
        parseInt(simUsersInput.value) || 15,
        parseInt(movieCountInput.value) || 12
      );
    });
  }

  if (btnRandom) {
    btnRandom.addEventListener('click', () => {
      const randId = Math.floor(Math.random() * 943) + 1;
      userIdInput.value = randId;
      runKnnUserSearch(
        randId,
        parseInt(simUsersInput.value) || 15,
        parseInt(movieCountInput.value) || 12
      );
    });
  }

  // Initial run
  runKnnUserSearch(307, 15, 12);
}

async function runKnnUserSearch(userId, similarUsers, movieCount) {
  const historyList = document.getElementById('userHistoryList');
  const peersList = document.getElementById('similarPeersList');
  const resultsGrid = document.getElementById('knnUserResults');

  historyList.innerHTML = '<div class="skeleton-loader">Loading watch history...</div>';
  peersList.innerHTML = '<div class="skeleton-loader">Finding peers...</div>';
  resultsGrid.innerHTML = '<div class="skeleton-loader">Aggregating peer ratings...</div>';

  try {
    const res = await fetch(`/api/knn/user?user_id=${userId}&similar_users=${similarUsers}&n_movies=${movieCount}`);
    const data = await res.json();

    if (data.error) {
      resultsGrid.innerHTML = `<div class="panel-card" style="grid-column: 1 / -1; color: #f87171;">${data.error}</div>`;
      return;
    }

    // Render history
    historyList.innerHTML = (data.user_history || []).map(h => `
      <div class="history-item">
        <span title="${escapeHtml(h.title)}">${escapeHtml(h.title)}</span>
        <span class="rating-pill">★ ${h.rating}</span>
      </div>
    `).join('');

    // Render peers
    peersList.innerHTML = (data.similar_peers || []).map(p => `
      <div class="peer-chip">User ${p.user_id} <span style="opacity:0.7;">(dist: ${p.distance})</span></div>
    `).join('');

    // Render recommendations
    renderMovieCards(resultsGrid, data.recommendations, 'predicted_score', 'Weighted Score');
  } catch (err) {
    resultsGrid.innerHTML = `<div class="skeleton-loader" style="color:#f87171;">Error loading recommendations</div>`;
  }
}

/* ==========================================================================
   TAB 4: SVD Matrix Factorization
   ========================================================================== */
function initSvdMovieTab() {
  const input = document.getElementById('svdMovieInput');
  const dropdown = document.getElementById('svdMovieSuggestions');
  const btnSearch = document.getElementById('btnSvdMovieSearch');

  setupAutocomplete(input, dropdown, (selectedMovie) => {
    input.value = selectedMovie;
    runSvdMovieSearch(selectedMovie);
  });

  if (btnSearch) {
    btnSearch.addEventListener('click', () => {
      runSvdMovieSearch(input.value.trim());
    });
  }

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      runSvdMovieSearch(input.value.trim());
      dropdown.style.display = 'none';
    }
  });

  // Quick Chips
  document.querySelectorAll('.chip[data-svd-movie]').forEach(chip => {
    chip.addEventListener('click', () => {
      const m = chip.dataset.svdMovie;
      input.value = m;
      runSvdMovieSearch(m);
    });
  });

  // Initial search
  runSvdMovieSearch('Star Wars (1977)');
}

async function runSvdMovieSearch(movieName) {
  if (!movieName) return;
  const container = document.getElementById('svdMovieResults');
  const titleEl = document.getElementById('svdMovieResultTitle');

  titleEl.innerHTML = `Latent Similar Movies for: <span class="highlight">${escapeHtml(movieName)}</span>`;
  container.innerHTML = '<div class="skeleton-loader">Computing SVD Latent Projections...</div>';

  try {
    const res = await fetch(`/api/svd/movie?movie=${encodeURIComponent(movieName)}&top_n=12`);
    const data = await res.json();

    if (data.error) {
      container.innerHTML = `<div class="panel-card" style="grid-column: 1 / -1; color: #f87171;">${data.error}</div>`;
      return;
    }

    renderMovieCards(container, data.recommendations, 'similarity', 'Latent Match');
  } catch (err) {
    container.innerHTML = `<div class="skeleton-loader" style="color:#f87171;">Failed to compute SVD recommendations</div>`;
  }
}

/* ==========================================================================
   TAB 5: Model Comparison
   ========================================================================== */
function initComparisonTab() {
  const input = document.getElementById('compareMovieInput');
  const dropdown = document.getElementById('compareSuggestions');
  const btn = document.getElementById('btnCompareSearch');

  setupAutocomplete(input, dropdown, (m) => {
    input.value = m;
    runComparison(m);
  });

  if (btn) {
    btn.addEventListener('click', () => {
      runComparison(input.value.trim());
    });
  }

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      runComparison(input.value.trim());
      dropdown.style.display = 'none';
    }
  });

  runComparison('Star Wars (1977)');
}

async function runComparison(movie) {
  if (!movie) return;
  const knnContainer = document.getElementById('compareKnnResults');
  const svdContainer = document.getElementById('compareSvdResults');

  knnContainer.innerHTML = '<div class="skeleton-loader">Running KNN...</div>';
  svdContainer.innerHTML = '<div class="skeleton-loader">Running SVD...</div>';

  try {
    const res = await fetch(`/api/compare/movie?movie=${encodeURIComponent(movie)}&top_n=8`);
    const data = await res.json();

    renderMovieCards(knnContainer, data.knn.recommendations, 'similarity', 'Overlap Match');
    renderMovieCards(svdContainer, data.svd.recommendations, 'similarity', 'Latent Match');
  } catch (err) {
    console.error('Comparison error:', err);
  }
}

/* ==========================================================================
   TAB 6: Neural / Latent User Scoring
   ========================================================================== */
function initDnnUserTab() {
  const userIdInput = document.getElementById('dnnUserId');
  const countInput = document.getElementById('dnnMovieCount');
  const btn = document.getElementById('btnDnnUserGenerate');

  if (btn) {
    btn.addEventListener('click', () => {
      runDnnUserSearch(parseInt(userIdInput.value) || 307, parseInt(countInput.value) || 12);
    });
  }

  runDnnUserSearch(307, 12);
}

async function runDnnUserSearch(userId, count) {
  const container = document.getElementById('dnnUserResults');
  const titleEl = document.getElementById('dnnUserResultTitle');

  titleEl.innerHTML = `Predicted Movies for User <span class="highlight">${userId}</span>`;
  container.innerHTML = '<div class="skeleton-loader">Predicting ratings for unseen movies...</div>';

  try {
    const res = await fetch(`/api/dnn/user?user_id=${userId}&n_movies=${count}`);
    const data = await res.json();

    if (data.error) {
      container.innerHTML = `<div class="panel-card" style="grid-column: 1 / -1; color: #f87171;">${data.error}</div>`;
      return;
    }

    renderMovieCards(container, data.recommendations, 'predicted_rating', 'Predicted Rating');
  } catch (err) {
    container.innerHTML = `<div class="skeleton-loader" style="color:#f87171;">Failed to predict ratings</div>`;
  }
}

/* ==========================================================================
   Helper: Card Grid Renderer
   ========================================================================== */
function renderMovieCards(container, movies, scoreKey, scoreLabel) {
  if (!movies || movies.length === 0) {
    container.innerHTML = '<div class="skeleton-loader">No recommendations found</div>';
    return;
  }

  container.innerHTML = movies.map((m, idx) => {
    let scoreVal = m[scoreKey] !== undefined ? m[scoreKey] : '';
    let progressPercent = 0;

    if (scoreKey === 'similarity') {
      progressPercent = Math.min(100, Math.max(0, scoreVal));
      scoreVal = `${scoreVal}%`;
    } else if (scoreKey === 'predicted_rating') {
      progressPercent = Math.min(100, Math.max(0, (scoreVal / 5) * 100));
      scoreVal = `★ ${scoreVal}`;
    } else if (scoreKey === 'predicted_score') {
      progressPercent = Math.min(100, Math.max(0, scoreVal * 12));
    }

    return `
      <div class="movie-card">
        <div>
          <div class="movie-card-header">
            <span class="movie-rank">${idx + 1}</span>
            <span class="rating-pill">★ ${m.avg_rating}</span>
          </div>

          <h4 class="movie-card-title">${escapeHtml(m.title)}</h4>

          <div class="movie-card-genres">
            ${(m.genres || []).slice(0, 3).map(g => `<span class="movie-genre-tag">${escapeHtml(g)}</span>`).join('')}
          </div>
        </div>

        <div>
          <div class="match-bar-wrapper">
            <div class="match-bar-info">
              <span>${scoreLabel}</span>
              <span class="match-bar-val">${scoreVal}</span>
            </div>
            <div class="match-progress">
              <div class="match-progress-fill" style="width: ${progressPercent}%"></div>
            </div>
          </div>

          <div class="movie-card-footer">
            <span class="views-pill">${m.watch_count} ratings</span>
            <span style="font-size: 0.72rem; color: var(--accent-cyan);">MovieLens</span>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

/* ==========================================================================
   Helper: Autocomplete
   ========================================================================== */
function setupAutocomplete(inputEl, dropdownEl, onSelect) {
  let debounceTimeout = null;

  inputEl.addEventListener('input', () => {
    clearTimeout(debounceTimeout);
    const q = inputEl.value.trim();
    if (q.length < 2) {
      dropdownEl.style.display = 'none';
      return;
    }

    debounceTimeout = setTimeout(async () => {
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&limit=8`);
        const data = await res.json();
        if (data.suggestions && data.suggestions.length > 0) {
          dropdownEl.innerHTML = data.suggestions.map(s => `
            <div class="autocomplete-item" data-value="${escapeHtml(s)}">${escapeHtml(s)}</div>
          `).join('');
          dropdownEl.style.display = 'block';

          dropdownEl.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => {
              onSelect(item.dataset.value);
              dropdownEl.style.display = 'none';
            });
          });
        } else {
          dropdownEl.style.display = 'none';
        }
      } catch (e) {
        dropdownEl.style.display = 'none';
      }
    }, 200);
  });

  document.addEventListener('click', (e) => {
    if (!inputEl.contains(e.target) && !dropdownEl.contains(e.target)) {
      dropdownEl.style.display = 'none';
    }
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

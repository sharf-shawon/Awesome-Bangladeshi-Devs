(() => {
  const state = {
    manifest: null,
    summary: null,
    charts: null,
    pages: [],
    developers: new Map(),
    index: [],
    filtered: [],
    rendered: 0,
    pageSize: 30,
  };

  const el = (id) => document.getElementById(id);

  const escapeHtml = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));

  const qs = new URLSearchParams(location.search);
  ["q","location","language","skill","sort","minStars","minForks"].forEach((k) => {
    if (qs.has(k) && el(k)) el(k).value = qs.get(k);
  });

  const saveQuery = () => {
    const params = new URLSearchParams();
    ["q","location","language","skill","sort","minStars","minForks"].forEach((k) => {
      const v = el(k)?.value?.trim();
      if (v) params.set(k, v);
    });
    history.replaceState(null, "", `${location.pathname}?${params.toString()}`);
  };

  const fetchJson = (p) => fetch(p, { cache: "no-store" }).then((r) => r.json());

  const loadManifest = async () => {
    state.manifest = await fetchJson('/data/web/manifest.json');
    state.summary = await fetchJson(`/data/web/${state.manifest.stats_summary}`);
    state.charts = await fetchJson(`/data/web/${state.manifest.charts}`);
    state.index = (await fetchJson(`/data/web/${state.manifest.search_index}`)).items || [];
    el('meta').textContent = `Last updated: ${state.summary.generated_at || 'N/A'} · Developers: ${state.summary.total_developers || 0}`;
    renderCharts();
    await ensurePage(1);
    applyFilters();
  };

  const ensurePage = async (num) => {
    if (state.pages[num]) return;
    const file = state.manifest.directory_index[num - 1];
    if (!file) return;
    const payload = await fetchJson(`/data/web/${file}`);
    state.pages[num] = payload.developers || [];
    for (const d of state.pages[num]) state.developers.set(d.login, d);
  };

  const sortedIds = async () => {
    const sortBy = el('sort').value || 'activity';
    const data = await fetchJson(`/data/web/${state.manifest.sorted_indexes}`);
    return data[sortBy] || [];
  };

  const matches = (idx) => {
    const q = el('q').value.trim().toLowerCase();
    const location = el('location').value.trim().toLowerCase();
    const language = el('language').value.trim().toLowerCase();
    const skill = el('skill').value.trim().toLowerCase();
    const minStars = Number(el('minStars').value || 0);
    const minForks = Number(el('minForks').value || 0);

    if (q && !(idx.tokens || []).some((t) => t.includes(q))) return false;
    if (location && !String(idx.location || '').toLowerCase().includes(location)) return false;
    if (language && !(idx.languages || []).some((l) => l.toLowerCase().includes(language))) return false;
    if (skill) {
      const pool = [...(idx.skills || []), ...(idx.expertise_tags || [])].map((x) => String(x).toLowerCase());
      if (!pool.some((x) => x.includes(skill))) return false;
    }
    if ((idx.stars || 0) < minStars) return false;
    if ((idx.forks || 0) < minForks) return false;
    return true;
  };

  const hydrateFor = async (logins) => {
    const need = logins.filter((l) => !state.developers.has(l));
    let n = 1;
    while (need.length && state.manifest.directory_index[n - 1]) {
      await ensurePage(n++);
      for (let i = need.length - 1; i >= 0; i--) if (state.developers.has(need[i])) need.splice(i, 1);
    }
  };

  const applyFilters = async () => {
    saveQuery();
    const order = await sortedIds();
    const byId = new Map(state.index.map((i) => [i.id, i]));
    state.filtered = order.filter((id) => byId.has(id)).map((id) => byId.get(id)).filter(matches).map((i) => i.id);
    state.rendered = 0;
    el('results').innerHTML = '';
    el('count').textContent = `${state.filtered.length} matching developers`;
    await renderMore();
  };

  const card = (d) => {
    const skills = (d.skills || []).slice(0, 6).join(', ') || 'N/A';
    const langs = (d.primary_languages || d.languages || []).slice(0, 5).join(', ') || 'N/A';
    const repos = (d.top_repositories || []).slice(0, 3)
      .map((r) => `<li><a href="${escapeHtml(r.url || '#')}" rel="noopener">${escapeHtml(r.name || 'repo')}</a> ⭐${r.stargazers_count || 0}</li>`)
      .join('');
    return `<article class="card"><h3><a href="/developers/${encodeURIComponent(d.login)}/">${escapeHtml(d.login)}</a></h3>
      <p class="muted">${escapeHtml(d.name || '')} · ${escapeHtml(d.location || 'Unknown')}</p>
      <p>Followers: ${d.followers || 0} · Stars: ${d.recent_repo_stars_sum || 0} · Forks: ${d.repo_forks_sum || 0}</p>
      <p>Languages: ${escapeHtml(langs)}</p>
      <p>Skills: ${escapeHtml(skills)}</p>
      <ul>${repos || '<li>No repo summary</li>'}</ul></article>`;
  };

  const renderMore = async () => {
    const next = state.filtered.slice(state.rendered, state.rendered + state.pageSize);
    await hydrateFor(next);
    const html = next.map((id) => state.developers.get(id)).filter(Boolean).map(card).join('');
    el('results').insertAdjacentHTML('beforeend', html);
    state.rendered += next.length;
    el('loadMore').style.display = state.rendered < state.filtered.length ? 'block' : 'none';
  };

  const renderList = (target, items, fmt) => {
    const root = el(target);
    root.innerHTML = (items || []).map(fmt).join('') || '<li>No data available.</li>';
  };

  const renderCharts = () => {
    renderList('timeline', state.charts.timeline, (x) => `<li>${escapeHtml(x.date)}: ${x.total_contributions} contributions, ${x.developers} developers</li>`);
    renderList('topLanguages', state.summary.language_leaderboard, (x) => `<li>${escapeHtml(x.language)} (${x.developers} developers)</li>`);
    renderList('topLocations', state.summary.location_leaderboard, (x) => `<li>${escapeHtml(x.location)} (${x.developers} developers)</li>`);
    renderList('risingRepos', state.charts.rising_repositories, (x) => `<li><a href="${escapeHtml(x.url || '#')}" rel="noopener">${escapeHtml(x.repository)}</a> +${x.stars_growth} stars</li>`);
  };

  el('filters').addEventListener('input', () => applyFilters());
  el('loadMore').addEventListener('click', () => renderMore());

  loadManifest().catch((e) => {
    console.error(e);
    el('meta').textContent = 'Failed to load live data bundle.';
  });
})();

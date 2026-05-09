(() => {
  const state = {
    manifest: null,
    summary: null,
    charts: null,
    index: [],
    sorted: null,
    developersByLogin: new Map(),
    projects: [],
    devFiltered: [],
    projectFiltered: [],
    devRendered: 0,
    projectRendered: 0,
    pageSize: 30,
  };

  const page = document.body?.dataset?.page || "default";
  const byId = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const base = (window.SITE_BASE_URL || "").replace(/\/$/, "");
  const sitePath = (path) => `${base}${path.startsWith("/") ? path : `/${path}`}`;

  const fetchJson = async (path, options = {}) => {
    const url = /^https?:\/\//i.test(path) ? path : sitePath(path);
    const res = await fetch(url, { cache: options.cache || "default" });
    if (!res.ok) throw new Error(`Failed loading ${path}: ${res.status}`);
    return res.json();
  };

  const withVersion = (path) => {
    const v = state.manifest?.version;
    return v ? `${path}?v=${encodeURIComponent(v)}` : path;
  };

  const formatDate = (v) => {
    if (!v) return "N/A";
    const d = new Date(v);
    return Number.isNaN(d.getTime()) ? v : d.toLocaleDateString();
  };

  const debounce = (fn, ms = 140) => {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  };

  const createChart = (id, cfg) => {
    if (typeof Chart === "undefined") return;
    const el = byId(id);
    if (!el) return;
    new Chart(el, cfg);
  };

  const loadCore = async () => {
    state.manifest = await fetchJson("/data/web/manifest.json", { cache: "no-cache" });
    state.summary = await fetchJson(withVersion(`/data/web/${state.manifest.stats_summary}`));
    state.charts = await fetchJson(withVersion(`/data/web/${state.manifest.charts}`));
    state.index = (await fetchJson(withVersion(`/data/web/${state.manifest.search_index}`))).items || [];
    state.sorted = await fetchJson(withVersion(`/data/web/${state.manifest.sorted_indexes}`));
    const projectsPath = state.manifest.projects_index || "projects-index.json";
    state.projects = (await fetchJson(withVersion(`/data/web/${projectsPath}`))).items || [];
  };

  const hydrateProjectsFallback = async () => {
    if (state.projects.length) return;
    const owners = (state.summary?.top_followers || []).slice(0, 12);
    const map = new Map();
    await Promise.all(
      owners.map(async (owner) => {
        try {
          const repos = await fetchJson(`https://api.github.com/users/${encodeURIComponent(owner)}/repos?per_page=12&sort=updated`);
          for (const repo of repos || []) {
            const key = String(repo.full_name || repo.name || "").toLowerCase();
            if (!key) continue;
            const prev = map.get(key);
            const candidate = {
              id: key,
              name: repo.name,
              full_name: repo.full_name || repo.name,
              url: repo.html_url,
              description: repo.description,
              language: repo.language,
              stargazers_count: Number(repo.stargazers_count || 0),
              forks_count: Number(repo.forks_count || 0),
              updated_at: repo.updated_at,
              pushed_at: repo.pushed_at,
              topics: repo.topics || [],
              owner,
              archived: !!repo.archived,
              is_fork: !!repo.fork,
            };
            if (!prev || candidate.stargazers_count > prev.stargazers_count) map.set(key, candidate);
          }
        } catch (_) {}
      })
    );
    state.projects = [...map.values()].sort((a, b) => b.stargazers_count - a.stargazers_count);
  };

  const hydrateDevelopersMap = async () => {
    const files = state.manifest.directory_index || [];
    for (const file of files) {
      const payload = await fetchJson(withVersion(`/data/web/${file}`));
      for (const dev of payload.developers || []) {
        if (dev?.login) state.developersByLogin.set(dev.login, dev);
      }
    }
  };

  const renderHome = () => {
    const meta = byId("meta");
    if (meta) meta.textContent = `Last updated: ${state.summary.generated_at || "N/A"} · Developers: ${state.summary.total_developers || 0}`;

    const langCount = (state.summary.language_leaderboard || []).length;
    const locCount = (state.summary.location_leaderboard || []).length;

    byId("kpiDevelopers") && (byId("kpiDevelopers").textContent = String(state.summary.total_developers || 0));
    byId("kpiLanguages") && (byId("kpiLanguages").textContent = String(langCount));
    byId("kpiLocations") && (byId("kpiLocations").textContent = String(locCount));
    byId("kpiRepos") && (byId("kpiRepos").textContent = String(state.projects.length));

    createChart("timelineChart", {
      type: "line",
      data: {
        labels: (state.charts.timeline || []).map((x) => x.date),
        datasets: [{ label: "Contributions", data: (state.charts.timeline || []).map((x) => x.total_contributions), borderColor: "#0284c7", backgroundColor: "rgba(2,132,199,.14)", fill: true, tension: .25 }],
      },
      options: { responsive: true, maintainAspectRatio: false },
    });

    createChart("languageChart", {
      type: "bar",
      data: {
        labels: (state.summary.language_leaderboard || []).slice(0, 8).map((x) => x.language),
        datasets: [{ label: "Developers", data: (state.summary.language_leaderboard || []).slice(0, 8).map((x) => x.developers), backgroundColor: "#0ea5e9" }],
      },
      options: { responsive: true, maintainAspectRatio: false },
    });

    createChart("locationChart", {
      type: "doughnut",
      data: {
        labels: (state.summary.location_leaderboard || []).slice(0, 6).map((x) => x.location),
        datasets: [{ data: (state.summary.location_leaderboard || []).slice(0, 6).map((x) => x.developers), backgroundColor: ["#0ea5e9", "#38bdf8", "#7dd3fc", "#0284c7", "#0369a1", "#0891b2"] }],
      },
      options: { responsive: true, maintainAspectRatio: false },
    });

    const rising = byId("risingRepos");
    if (rising) {
      rising.innerHTML = (state.charts.rising_repositories || []).slice(0, 10).map((r) => `<li><a href="${esc(r.url || "#")}" rel="noopener">${esc(r.repository || "Repository")}</a> (+${Number(r.stars_growth || 0)} stars)</li>`).join("") || "<li>No data available.</li>";
    }
  };

  const devCard = (dev) => {
    const repos = (dev.top_repositories || []).slice(0, 4).map((r) => `<li><a href="${esc(r.url || "#")}" rel="noopener">${esc(r.name || "repo")}</a> ⭐${Number(r.stargazers_count || 0)} · 🍴${Number(r.forks_count || 0)}</li>`).join("") || "<li>No repository data.</li>";
    const languages = (dev.primary_languages || dev.languages || []).slice(0, 5).join(", ") || "N/A";
    const skills = (dev.skills || []).slice(0, 6).join(", ") || "N/A";
    return `<article class="card">
      <h3><a href="${sitePath(`/developers/${encodeURIComponent(dev.login)}/`)}">${esc(dev.login)}</a></h3>
      <p class="meta">${esc(dev.name || "")} · ${esc(dev.location || "Unknown")}</p>
      <p>Followers: ${Number(dev.followers || 0)} · Stars: ${Number(dev.recent_repo_stars_sum || 0)} · Forks: ${Number(dev.repo_forks_sum || 0)}</p>
      <p>Languages: ${esc(languages)}</p>
      <p>Skills: ${esc(skills)}</p>
      <ul>${repos}</ul>
    </article>`;
  };

  const projectCard = (repo) => {
    const desc = esc(repo.description || "No description provided.");
    const topics = (repo.topics || []).slice(0, 7).map((t) => `<code>${esc(t)}</code>`).join(" ");
    return `<article class="card">
      <h3><a href="${esc(repo.url || "#")}" rel="noopener">${esc(repo.full_name || repo.name || "repository")}</a></h3>
      <p class="meta">Owner: <a href="${sitePath(`/developers/${encodeURIComponent(repo.owner || "")}/`)}">${esc(repo.owner || "Unknown")}</a> · ${esc(repo.language || "Unknown")}</p>
      <p>${desc}</p>
      <p>⭐ ${Number(repo.stargazers_count || 0)} · 🍴 ${Number(repo.forks_count || 0)} · Updated: ${esc(formatDate(repo.updated_at || repo.pushed_at))}</p>
      ${topics ? `<p>${topics}</p>` : ""}
    </article>`;
  };

  const devMatches = (idx) => {
    const q = byId("q")?.value?.trim().toLowerCase() || "";
    const location = byId("location")?.value?.trim().toLowerCase() || "";
    const language = byId("language")?.value?.trim().toLowerCase() || "";
    const skill = byId("skill")?.value?.trim().toLowerCase() || "";
    const minStars = Number(byId("minStars")?.value || 0);
    const minForks = Number(byId("minForks")?.value || 0);

    if (q && !(idx.tokens || []).some((t) => String(t).includes(q))) return false;
    if (location && !String(idx.location || "").toLowerCase().includes(location)) return false;
    if (language && !(idx.languages || []).some((l) => String(l).toLowerCase().includes(language))) return false;
    if (skill && ![...(idx.skills || []), ...(idx.expertise_tags || [])].some((s) => String(s).toLowerCase().includes(skill))) return false;
    if (Number(idx.stars || 0) < minStars) return false;
    if (Number(idx.forks || 0) < minForks) return false;
    return true;
  };

  const applyDeveloperFilters = () => {
    const sortBy = byId("sort")?.value || "activity";
    const order = (state.sorted?.[sortBy] || []).filter(Boolean);
    const idxMap = new Map(state.index.map((x) => [x.id, x]));
    state.devFiltered = order.map((id) => idxMap.get(id)).filter(Boolean).filter(devMatches).map((x) => x.id);
    state.devRendered = 0;
    byId("results").innerHTML = "";
    byId("count").textContent = `${state.devFiltered.length} matching developers`;
    renderMoreDevelopers();
  };

  const renderMoreDevelopers = () => {
    const batch = state.devFiltered.slice(state.devRendered, state.devRendered + state.pageSize).map((login) => state.developersByLogin.get(login)).filter(Boolean);
    byId("results").insertAdjacentHTML("beforeend", batch.map(devCard).join(""));
    state.devRendered += batch.length;
    byId("loadMore").style.display = state.devRendered < state.devFiltered.length ? "inline-block" : "none";
  };

  const projectMatches = (repo) => {
    const q = byId("pq")?.value?.trim().toLowerCase() || "";
    const language = byId("planguage")?.value?.trim().toLowerCase() || "";
    const owner = byId("powner")?.value?.trim().toLowerCase() || "";
    const minStars = Number(byId("pminStars")?.value || 0);
    const minForks = Number(byId("pminForks")?.value || 0);

    if (q) {
      const pool = [repo.name, repo.full_name, repo.description, repo.owner, ...(repo.topics || [])].map((x) => String(x || "").toLowerCase());
      if (!pool.some((x) => x.includes(q))) return false;
    }
    if (language && !String(repo.language || "").toLowerCase().includes(language)) return false;
    if (owner && !String(repo.owner || "").toLowerCase().includes(owner)) return false;
    if (Number(repo.stargazers_count || 0) < minStars) return false;
    if (Number(repo.forks_count || 0) < minForks) return false;
    return true;
  };

  const projectSort = (sortBy) => {
    const list = [...state.projects];
    const collator = new Intl.Collator(undefined, { sensitivity: "base" });
    if (sortBy === "name") return list.sort((a, b) => collator.compare(a.full_name || a.name || "", b.full_name || b.name || ""));
    if (sortBy === "updated") return list.sort((a, b) => String(b.updated_at || b.pushed_at || "").localeCompare(String(a.updated_at || a.pushed_at || "")));
    if (sortBy === "forks") return list.sort((a, b) => Number(b.forks_count || 0) - Number(a.forks_count || 0));
    return list.sort((a, b) => Number(b.stargazers_count || 0) - Number(a.stargazers_count || 0));
  };

  const applyProjectFilters = () => {
    const ordered = projectSort(byId("psort")?.value || "stars");
    state.projectFiltered = ordered.filter(projectMatches);
    state.projectRendered = 0;
    byId("projectResults").innerHTML = "";
    byId("projectCount").textContent = `${state.projectFiltered.length} matching projects`;
    renderMoreProjects();
  };

  const renderMoreProjects = () => {
    const batch = state.projectFiltered.slice(state.projectRendered, state.projectRendered + state.pageSize);
    byId("projectResults").insertAdjacentHTML("beforeend", batch.map(projectCard).join(""));
    state.projectRendered += batch.length;
    byId("projectLoadMore").style.display = state.projectRendered < state.projectFiltered.length ? "inline-block" : "none";
  };

  const initDevelopersPage = async () => {
    await hydrateDevelopersMap();
    const apply = debounce(applyDeveloperFilters, 120);
    byId("devFilters")?.addEventListener("input", apply);
    byId("loadMore")?.addEventListener("click", renderMoreDevelopers);
    applyDeveloperFilters();
  };

  const initProjectsPage = () => {
    const apply = debounce(applyProjectFilters, 120);
    byId("projectFilters")?.addEventListener("input", apply);
    byId("projectLoadMore")?.addEventListener("click", renderMoreProjects);
    applyProjectFilters();
  };

  (async () => {
    try {
      await loadCore();
      if (page === "home") renderHome();
      if (page === "developers") await initDevelopersPage();
      if (page === "projects") {
        await hydrateProjectsFallback();
        initProjectsPage();
      }
    } catch (err) {
      console.error(err);
      const meta = byId("meta");
      if (meta) meta.textContent = "Failed to load live site data.";
    }
  })();
})();

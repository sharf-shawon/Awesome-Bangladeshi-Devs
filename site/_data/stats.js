export default async function() {
  const { default: getEnriched } = await import("./enriched.js");
  const enriched = getEnriched();
  
  if (!enriched.length) return { total_devs: 0 };

  const stats = {
    total_devs: enriched.length,
    total_stars: 0,
    total_followers: 0,
    total_repos: 0,
    join_years: {},
    companies: {},
    topics: {},
    top_repos: [],
    languages: {},
    last_updated: ""
  };

  const all_repos = [];

  enriched.forEach(dev => {
    stats.total_stars += (dev.total_stars || 0);
    stats.total_followers += (dev.followers || 0);
    stats.total_repos += (dev.public_repos || 0);

    // Join Years
    if (dev.created_at) {
      const year = dev.created_at.substring(0, 4);
      stats.join_years[year] = (stats.join_years[year] || 0) + 1;
    }

    // Organizations / Companies
    if (dev.company) {
      const org = dev.company.trim().replace(/^@/, "").toLowerCase();
      if (org) {
        stats.companies[org] = (stats.companies[org] || 0) + 1;
      }
    }

    // Languages
    if (dev.all_languages) {
      dev.all_languages.forEach(l => {
        if (l) stats.languages[l] = (stats.languages[l] || 0) + 1;
      });
    }

    // Repos & Topics
    const repos = dev.featured_repos || dev.top_repos || [];
    repos.forEach(repo => {
      all_repos.push({
        name: repo.name,
        owner: dev.github_username,
        stars: repo.stargazerCount || repo.stars || 0,
        url: repo.url,
        description: repo.description,
        language: repo.primaryLanguage || repo.language
      });

      if (repo.topics) {
        repo.topics.forEach(t => {
          const topic = t.toLowerCase();
          // Filter out some noise
          if (topic !== dev.github_username.toLowerCase() && topic.length > 2) {
            stats.topics[topic] = (stats.topics[topic] || 0) + 1;
          }
        });
      }
    });

    const at = dev.enriched_at || dev.last_repo_fetched_at || "";
    if (at > stats.last_updated) stats.last_updated = at;
  });

  // Sort and Slice
  stats.top_repos = all_repos.sort((a, b) => b.stars - a.stars).slice(0, 10);
  
  stats.top_companies = Object.entries(stats.companies)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, count]) => ({ name, count }));

  stats.top_topics = Object.entries(stats.topics)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([name, count]) => ({ name, count }));

  stats.sorted_join_years = Object.entries(stats.join_years)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([year, count]) => ({ year, count }));

  const topLangEntry = Object.entries(stats.languages).sort((a, b) => b[1] - a[1])[0];
  stats.top_language = topLangEntry ? topLangEntry[0] : "N/A";

  return stats;
}

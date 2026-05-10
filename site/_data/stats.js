const enriched = require("./enriched.js")();

module.exports = function() {
  const langCounts = {};
  const topicCounts = {};
  const locations = {};
  let totalStars = 0;
  let totalRepos = 0;
  let totalActivity = 0;

  enriched.forEach(user => {
    // Languages
    user.top_languages.forEach(lang => {
      langCounts[lang] = (langCounts[lang] || 0) + 1;
    });

    // Topics
    if (user.top_topics) {
      user.top_topics.forEach(topic => {
        topicCounts[topic] = (topicCounts[topic] || 0) + 1;
      });
    }

    // Locations (normalized)
    if (user.location) {
        let loc = user.location.split(',').pop().trim();
        if (loc.toLowerCase().includes('bangladesh') || loc.toLowerCase() === 'bd') loc = 'Bangladesh';
        locations[loc] = (locations[loc] || 0) + 1;
    }

    // Totals
    totalActivity += (user.activity_score || 0);
    totalRepos += (user.public_repos || 0);
    
    if (user.featured_repos) {
        user.featured_repos.forEach(repo => {
            totalStars += (repo.stargazerCount || 0);
        });
    }
  });

  const sortedLangs = Object.entries(langCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({
      name,
      count,
      percentage: ((count / enriched.length) * 100).toFixed(1)
    }));

  const sortedTopics = Object.entries(topicCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([name, count]) => ({ name, count }));

  const sortedLocations = Object.entries(locations)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, count]) => ({ name, count }));

  return {
    topLanguages: sortedLangs.slice(0, 15),
    topTopics: sortedTopics,
    topLocations: sortedLocations,
    totalUsers: enriched.length,
    totalStars: totalStars.toLocaleString(),
    totalRepos: totalRepos.toLocaleString(),
    avgActivity: (totalActivity / enriched.length).toFixed(1),
    mostActive: [...enriched].sort((a, b) => b.activity_score - a.activity_score).slice(0, 12)
  };
};

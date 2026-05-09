const enriched = require("./enriched.js")();

module.exports = function() {
  const langCounts = {};
  enriched.forEach(user => {
    user.top_languages.forEach(lang => {
      langCounts[lang] = (langCounts[lang] || 0) + 1;
    });
  });

  const sortedLangs = Object.entries(langCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({
      name,
      count,
      percentage: ((count / enriched.length) * 100).toFixed(1)
    }));

  return {
    topLanguages: sortedLangs.slice(0, 15),
    totalUsers: enriched.length,
    mostActive: [...enriched].sort((a, b) => b.activity_score - a.activity_score).slice(0, 6)
  };
};

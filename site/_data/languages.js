const enriched = require("./enriched.js")();

module.exports = function() {
  const languages = new Set();
  enriched.forEach(user => {
    user.top_languages.forEach(lang => {
      languages.add(lang);
    });
  });
  // Filter for common languages to avoid noise
  const commonLanguages = ["Python", "JavaScript", "TypeScript", "Go", "Rust", "PHP", "Java", "C++", "C#", "Ruby", "Swift", "Kotlin", "Dart", "HTML", "CSS"];
  return Array.from(languages).filter(l => commonLanguages.includes(l));
};

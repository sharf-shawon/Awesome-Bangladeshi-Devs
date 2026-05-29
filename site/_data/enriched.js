import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

export default function() {
  try {
    const raw = readFileSync(join(__dirname, "../../data/users-enriched.json"), "utf8");
    const data = JSON.parse(raw);
    
    // Normalize data
    return data.map(user => {
      const u = { ...user };
      
      // Use github_username as primary username field
      u.github_username = u.github_username || u.username;
      
      // Normalize repos
      u.top_repos = u.top_repos || u.featured_repos || [];
      u.top_repos = u.top_repos.map(repo => ({
        ...repo,
        stars: repo.stars !== undefined ? repo.stars : repo.stargazerCount,
        forks: repo.forks !== undefined ? repo.forks : repo.forkCount,
        language: repo.language || repo.primaryLanguage
      }));
      
      // Normalize languages
      u.all_languages = u.all_languages || u.top_languages || [];
      if (!u.top_language && u.all_languages.length > 0) {
        u.top_language = u.all_languages[0];
      }
      
      // Normalize stars
      if (u.total_stars === undefined) {
        u.total_stars = u.top_repos.reduce((s, r) => s + (r.stars || 0), 0);
      }
      
      // Normalize website
      u.website_url = u.website_url || u.blog;
      
      // Normalize enriched_at
      u.enriched_at = u.enriched_at || u.last_repo_fetched_at;
      
      return u;
    });
  } catch (e) {
    console.error("Error loading enriched data:", e);
    return [];
  }
}

# Contributing to Awesome Bangladeshi Developers

Thank you for your interest in contributing to the most comprehensive directory of Bangladeshi GitHub developers! By joining this list, you're helping to showcase the talent and impact of the Bangladeshi open-source community to the world.

This project is designed to be a data-driven resource for finding the top developers, rising stars, and active contributors from Bangladesh.

## 🚀 Adding a Developer

Adding someone (including yourself) is fully automated. You don't need to edit any files manually.

1. **Open an Issue:** Go to the [Issues](https://github.com/sharf-shawon/Awesome-Bangladeshi-Devs/issues/new/choose) page.
2. **Select Template:** Choose the **"Add Developer to Awesome List"** template.
3. **Fill the Form:**
   * **GitHub Username:** Exact username (e.g., `johndoe`).
   * **Profile URL:** Link to the profile.
   * **Location:** Must contain a valid location alias (e.g., `Dhaka`, `Bangladesh`, `Sylhet`, etc.).
4. **Submit:** Once submitted, our automation will:
   * Validate the information.
   * Fetch real-time statistics (followers, stars, etc.).
   * Add the developer to the list and regenerate the README automatically.

## 🗑️ Removing a Developer

1. **Open an Issue:** Select the **"Remove Developer from Awesome List"** template.
2. **Self-Removal:** If you are removing your own profile, check the **"Self-Removal Confirmation"** box. The automation will process this immediately.
3. **Third-Party Removal:** If you are reporting an ineligible profile, a maintainer will review the request manually.

## 📊 How the Ranking Works

The **Overall Score** is calculated using a 90-day activity lookback. We use a weighted formula to ensure fairness across different types of contributions:

| Metric | Weight | Description |
| :--- | :--- | :--- |
| **Contributions** | 35% | Total activity (commits, PRs, issues, etc.) |
| **Followers** | 20% | Total number of GitHub followers |
| **Pull Requests** | 10% | Number of PRs opened in the last 90 days |
| **Stars** | 10% | Total stars received on repositories |
| **Public Repos** | 10% | Total number of public repositories |
| **Others** | 15% | Commits (5%), Issues (5%), and Reviews (5%) |

*Note: All stats are normalized across the entire community to calculate the final composite score.*

## 🛠️ Technical Details

This repository uses a fully automated CI/CD pipeline:
- **Daily Scans:** Automatically updates statistics for all listed developers.
- **Monthly Archives:** A snapshot of the top developers is released at the end of every month.
- **Validation:** Every change is linted for "Awesome" compliance and schema integrity.

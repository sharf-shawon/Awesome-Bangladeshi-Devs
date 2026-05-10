let fuse;
let allUsers = [];
let filteredUsers = [];
const itemsPerPage = 24;
let isLoading = false;

const searchInput = document.getElementById('search-input');
const devGrid = document.getElementById('dev-grid');
const noResults = document.getElementById('no-results');
const resultsCount = document.getElementById('search-results-count');
const quickFilters = document.querySelectorAll('#quick-filters button');
const totalCountDisplay = document.getElementById('total-count');
const infiniteScrollStatus = document.getElementById('infinite-scroll-status');

// Advanced Filter Elements
const toggleAdvanced = document.getElementById('toggle-advanced');
const advancedPanel = document.getElementById('advanced-search-panel');
const sortBySelect = document.getElementById('sort-by');
const minFollowersInput = document.getElementById('min-followers');
const langFilterInput = document.getElementById('lang-filter');

async function initSearch() {
    try {
        const response = await fetch(`${window.pathPrefix || '/'}data/users-enriched.json`);
        allUsers = await response.json();
        
        const fuseData = allUsers.map(user => ({
            id: user.username,
            name: user.name,
            bio: user.bio,
            langs: user.top_languages,
            topics: user.top_topics,
            score: user.activity_score,
            followers: user.followers,
            repos: user.public_repos
        }));

        const options = {
            keys: [
                { name: 'id', weight: 1.0 },
                { name: 'name', weight: 0.8 },
                { name: 'langs', weight: 0.6 },
                { name: 'topics', weight: 0.5 },
                { name: 'bio', weight: 0.3 }
            ],
            threshold: 0.3,
            useExtendedSearch: true,
            ignoreLocation: true, // Search everywhere in the string
            findAllMatches: true,
            includeScore: true
        };

        fuse = new Fuse(fuseData, options);
        
        // Initial state: show all users sorted by activity score
        performSearch(new URLSearchParams(window.location.search).get('q') || '');

    } catch (error) {
        console.error('Error initializing search:', error);
    }
}

function performSearch(query) {
    if (!fuse) return;

    // Update URL
    const url = new URL(window.location);
    if (query) url.searchParams.set('q', query);
    else url.searchParams.delete('q');
    window.history.replaceState({}, '', url);

    if (!query) {
        // Just wrap the items to match Fuse structure
        filteredUsers = allUsers.map(user => ({
            item: {
                id: user.username,
                name: user.name,
                bio: user.bio,
                langs: user.top_languages,
                score: user.activity_score,
                followers: user.followers,
                repos: user.public_repos
            }
        }));
    } else {
        // Multi-word support: Fuse handles "word1 word2" by default, 
        // but we can ensure it by splitting if needed. 
        // With useExtendedSearch: true, it handles complex queries.
        filteredUsers = fuse.search(query);
    }

    sortAndFilter();
}

function sortAndFilter() {
    let results = [...filteredUsers];

    // Apply Filters
    const minFollowers = parseInt(minFollowersInput?.value) || 0;
    const langFilter = langFilterInput?.value?.toLowerCase().trim() || '';

    results = results.filter(r => {
        const item = r.item || r;
        if (item.followers < minFollowers) return false;
        if (langFilter && !item.langs?.some(l => l.toLowerCase().includes(langFilter))) return false;
        return true;
    });

    // Apply Sorting
    const sortBy = sortBySelect?.value || 'activity_score';
    
    results.sort((a, b) => {
        const itemA = a.item || a;
        const itemB = b.item || b;

        // If explicitly requested Name sort
        if (sortBy === 'name') {
            return (itemA.name || '').localeCompare(itemB.name || '');
        }

        // If we are searching (query exists) and sorting by activity_score, 
        // we might want to prioritize relevance. 
        // BUT user said sorting is broken, so let's be strict.
        
        if (sortBy === 'relevance' && a.score !== undefined && b.score !== undefined) {
            return a.score - b.score; // Fuse score: lower is better
        }

        // Standard numeric sorts
        const valA = itemA[sortBy] || 0;
        const valB = itemB[sortBy] || 0;
        return valB - valA;
    });

    devGrid.innerHTML = ''; // Reset grid
    if (results.length === 0) {
        noResults.classList.remove('hidden');
        resultsCount.textContent = '0 results';
        if (totalCountDisplay) totalCountDisplay.textContent = '0';
        return;
    }

    noResults.classList.add('hidden');
    resultsCount.textContent = `${results.length} results`;
    if (totalCountDisplay) totalCountDisplay.textContent = results.length.toLocaleString();

    loadMore(results);
}

function loadMore(results) {
    const fragment = document.createDocumentFragment();
    const currentCount = devGrid.children.length;
    const toDisplay = results.slice(currentCount, currentCount + itemsPerPage);
    
    toDisplay.forEach(result => {
        const user = result.item || result;
        const card = document.createElement('div');
        card.className = 'dev-card border dark:border-gray-800 p-6 rounded-2xl hover:shadow-lg transition-all group';
        card.innerHTML = `
            <div class="flex items-center gap-4 mb-4">
                <img src="https://github.com/${user.id}.png" alt="${user.name}" class="w-16 h-16 rounded-full group-hover:scale-110 transition-transform" onerror="this.src='https://github.com/identicons/${user.id}.png'">
                <div>
                    <h3 class="font-bold text-lg"><a href="${window.pathPrefix || '/'}dev/${user.id.toLowerCase()}/" class="hover:text-blue-500">${user.name || user.id}</a></h3>
                    <p class="text-sm text-gray-500">@${user.id}</p>
                </div>
            </div>
            <p class="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2 h-10">${user.bio || "No bio available."}</p>
            <div class="flex flex-wrap gap-1 mb-4 h-12 overflow-hidden">
                ${(user.langs || []).slice(0, 3).map(lang => `<span class="text-xs px-2 py-1 bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-300 rounded">${lang}</span>`).join('')}
            </div>
            <div class="flex justify-between items-center text-xs text-gray-400 border-t dark:border-gray-800 pt-4">
                <span>⭐ ${user.followers || 0} followers</span>
                <span class="font-bold text-green-500">${Math.round(user.score || 0)} activity</span>
            </div>
        `;
        fragment.appendChild(card);
    });

    devGrid.appendChild(fragment);
    
    if (devGrid.children.length >= results.length) {
        infiniteScrollStatus.style.display = 'none';
    } else {
        infiniteScrollStatus.style.display = 'block';
    }
    
    isLoading = false;
}

// Infinite Scroll
window.addEventListener('scroll', () => {
    if (isLoading) return;
    
    const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
    if (scrollTop + clientHeight >= scrollHeight - 800) {
        const results = applySearchAndFiltersLocal(); // Helper to get current set
        if (devGrid.children.length < results.length) {
            isLoading = true;
            loadMore(results);
        }
    }
});

function applySearchAndFiltersLocal() {
    // This is essentially sortAndFilter but returns the result instead of rendering
    let results = [...filteredUsers];
    const minFollowers = parseInt(minFollowersInput?.value) || 0;
    const langFilter = langFilterInput?.value?.toLowerCase().trim() || '';

    results = results.filter(r => {
        const item = r.item || r;
        if (item.followers < minFollowers) return false;
        if (langFilter && !item.langs?.some(l => l.toLowerCase().includes(langFilter))) return false;
        return true;
    });

    const sortBy = sortBySelect?.value || 'activity_score';
    results.sort((a, b) => {
        const itemA = a.item || a;
        const itemB = b.item || b;
        if (sortBy === 'name') return (itemA.name || '').localeCompare(itemB.name || '');
        if (sortBy === 'relevance' && a.score !== undefined) return a.score - b.score;
        const valA = itemA[sortBy] || 0;
        const valB = itemB[sortBy] || 0;
        return valB - valA;
    });
    return results;
}

// Event Listeners
if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        performSearch(e.target.value);
    });
}

quickFilters.forEach(button => {
    button.addEventListener('click', () => {
        const filter = button.getAttribute('data-filter');
        searchInput.value = filter;
        performSearch(filter);
    });
});

toggleAdvanced?.addEventListener('click', () => {
    advancedPanel.classList.toggle('hidden');
});

[sortBySelect, minFollowersInput, langFilterInput].forEach(el => {
    el?.addEventListener('input', sortAndFilter);
});

// Developer Profile Repository Logic
const reposContainer = document.getElementById('repos-container');
const repoSearchInput = document.getElementById('repo-search');
const repoSortSelect = document.getElementById('repo-sort');
const loadMoreReposBtn = document.getElementById('load-more-repos');

let allRepos = [];

function initRepos() {
    if (!reposContainer) return;
    
    const initialRepos = Array.from(reposContainer.querySelectorAll('.repo-card')).map(card => ({
        html: card.outerHTML,
        name: card.getAttribute('data-name'),
        stars: parseInt(card.getAttribute('data-stars')),
        updated: card.getAttribute('data-updated'),
        visible: true
    }));
    
    allRepos = initialRepos;
    
    repoSearchInput?.addEventListener('input', filterRepos);
    repoSortSelect?.addEventListener('input', filterRepos);
    loadMoreReposBtn?.addEventListener('click', loadMoreFromGitHub);
}

function filterRepos() {
    const query = repoSearchInput.value.toLowerCase();
    const sortBy = repoSortSelect.value;
    
    allRepos.forEach(repo => {
        repo.visible = repo.name.includes(query);
    });
    
    const sorted = [...allRepos].filter(r => r.visible).sort((a, b) => {
        if (sortBy === 'stars') return b.stars - a.stars;
        if (sortBy === 'updated') return new Date(b.updated) - new Date(a.updated);
        if (sortBy === 'name') return a.name.localeCompare(b.name);
        return 0;
    });
    
    reposContainer.innerHTML = sorted.map(r => r.html).join('');
    
    if (sorted.length === 0) {
        reposContainer.innerHTML = '<div class="col-span-full py-12 text-center text-gray-500">No repositories found.</div>';
    }
}

async function loadMoreFromGitHub() {
    const username = reposContainer.getAttribute('data-username');
    if (!username) return;
    
    loadMoreReposBtn.disabled = true;
    loadMoreReposBtn.textContent = 'Loading...';
    
    try {
        const response = await fetch(`https://api.github.com/users/${username}/repos?sort=updated&per_page=100`);
        const githubRepos = await response.json();
        
        if (!Array.isArray(githubRepos)) throw new Error('Invalid response');
        
        const existingNames = new Set(allRepos.map(r => r.name));
        const newRepos = githubRepos.filter(r => !existingNames.has(r.name.toLowerCase()));
        
        newRepos.forEach(repo => {
            const repoData = {
                name: repo.name.toLowerCase(),
                stars: repo.stargazers_count,
                updated: repo.pushed_at,
                visible: true,
                html: `
                    <div class="repo-card border dark:border-gray-800 p-6 rounded-xl hover:shadow-md transition-shadow" data-stars="${repo.stargazers_count}" data-name="${repo.name.toLowerCase()}" data-updated="${repo.pushed_at}">
                        <div class="flex justify-between items-start mb-4">
                            <h3 class="text-xl font-bold"><a href="${repo.html_url}" class="hover:text-blue-500">${repo.name}</a></h3>
                            <span class="text-sm text-gray-500">⭐ ${repo.stargazers_count}</span>
                        </div>
                        <p class="text-gray-600 dark:text-gray-400 mb-4 line-clamp-2 h-12">${repo.description || "No description provided."}</p>
                        <div class="flex justify-between items-center text-sm">
                            <span class="font-medium text-blue-500">${repo.language || "Plain Text"}</span>
                            <span class="text-gray-400">Updated ${new Date(repo.pushed_at).toLocaleDateString()}</span>
                        </div>
                    </div>
                `
            };
            allRepos.push(repoData);
        });
        
        filterRepos();
        loadMoreReposBtn.parentElement.classList.add('hidden');
    } catch (error) {
        console.error('Error loading repos:', error);
        loadMoreReposBtn.textContent = 'Error loading. Try again?';
        loadMoreReposBtn.disabled = false;
    }
}

// Initialize
if (devGrid) {
    initSearch();
}
initRepos();

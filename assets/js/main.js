let fuse;
const searchInput = document.getElementById('search-input');
const devGrid = document.getElementById('dev-grid');
const noResults = document.getElementById('no-results');
const resultsCount = document.getElementById('search-results-count');
const quickFilters = document.querySelectorAll('#quick-filters button');

async function initSearch() {
    try {
        const response = await fetch('/data/search-index.json');
        const data = await response.json();

        const options = {
            keys: [
                { name: 'id', weight: 1.0 },
                { name: 'name', weight: 0.9 },
                { name: 'langs', weight: 0.7 },
                { name: 'topics', weight: 0.7 },
                { name: 'aliases', weight: 0.7 },
                { name: 'r_names', weight: 0.5 },
                { name: 'bio', weight: 0.3 },
                { name: 'r_desc', weight: 0.3 }
            ],
            threshold: 0.3,
            includeScore: true
        };

        fuse = new Fuse(data, options);

        // Check URL for initial search
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('q');
        if (query) {
            searchInput.value = query;
            performSearch(query);
        }
    } catch (error) {
        console.error('Failed to initialize search:', error);
    }
}

function performSearch(query) {
    if (!fuse) return;

    // Update URL without reloading
    const url = new URL(window.location);
    if (query) {
        url.searchParams.set('q', query);
    } else {
        url.searchParams.delete('q');
    }
    window.history.replaceState({}, '', url);

    if (!query) {
        // If empty, we could show the default top developers
        // For now, let's just reload the page or reset the view
        location.reload(); 
        return;
    }

    const results = fuse.search(query);
    
    // Sort results by a combination of Fuse score and our activity score/followers
    results.sort((a, b) => {
        const scoreA = (1 - a.score) * 0.6 + (a.item.score / 1000) * 0.4;
        const scoreB = (1 - b.score) * 0.6 + (b.item.score / 1000) * 0.4;
        return scoreB - scoreA;
    });

    renderResults(results);
}

function renderResults(results) {
    devGrid.innerHTML = '';
    
    if (results.length === 0) {
        noResults.classList.remove('hidden');
        resultsCount.textContent = '0 results';
        return;
    }

    noResults.classList.add('hidden');
    resultsCount.textContent = `${results.length} results`;

    results.slice(0, 48).forEach(result => {
        const user = result.item;
        const card = document.createElement('div');
        card.className = 'dev-card border dark:border-gray-800 p-6 rounded-2xl hover:shadow-lg transition-all group';
        card.innerHTML = `
            <div class="flex items-center gap-4 mb-4">
                <img src="https://github.com/${user.id}.png" alt="${user.name}" class="w-16 h-16 rounded-full group-hover:scale-110 transition-transform">
                <div>
                    <h3 class="font-bold text-lg"><a href="/dev/${user.id.toLowerCase()}/" class="hover:text-blue-500">${user.name}</a></h3>
                    <p class="text-sm text-gray-500">@${user.id}</p>
                </div>
            </div>
            <p class="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2 h-10">${user.bio || "No bio available."}</p>
            <div class="flex flex-wrap gap-1 mb-4 h-12 overflow-hidden">
                ${user.langs.slice(0, 3).map(lang => `<span class="text-xs px-2 py-1 bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-300 rounded">${lang}</span>`).join('')}
            </div>
            <div class="flex justify-between items-center text-xs text-gray-400 border-t dark:border-gray-800 pt-4">
                <span>⭐ ${user.followers} followers</span>
                <span class="font-bold text-green-500">${user.score} activity</span>
            </div>
        `;
        devGrid.appendChild(card);
    });
}

if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        performSearch(e.target.value);
    });
    
    initSearch();
}

quickFilters.forEach(button => {
    button.addEventListener('click', () => {
        const filter = button.getAttribute('data-filter');
        searchInput.value = filter;
        performSearch(filter);
    });
});

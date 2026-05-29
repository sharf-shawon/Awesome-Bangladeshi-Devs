document.addEventListener('DOMContentLoaded', async () => {
    const searchInput = document.getElementById('project-search');
    const sortSelect = document.getElementById('project-sort');
    const langFilters = document.getElementById('language-filters');
    const clearFilters = document.getElementById('clear-filters');
    const resultsGrid = document.getElementById('projects-grid');
    const resultsInfo = document.getElementById('project-results-info');
    const resultsCount = document.getElementById('project-count');
    const noResults = document.getElementById('no-results');
    const sentinel = document.getElementById('load-more-sentinel');
    const loadingSpinner = document.getElementById('loading-spinner');

    let projects = [];
    let currentResults = [];
    let selectedLang = null;
    let fuse = null;
    
    // Batch rendering state
    const BATCH_SIZE = 50;
    let currentIndex = 0;

    try {
        const response = await fetch('/data/projects.json');
        projects = await response.json();
        
        // Initialize Fuse.js
        fuse = new Fuse(projects, {
            keys: ['n', 'd', 'o'],
            threshold: 0.3
        });

        // Initialize Language Filters
        const langs = [...new Set(projects.map(p => p.l).filter(Boolean))].sort();
        renderFilters(langs);
        
        // Setup Infinite Scroll
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                renderNextBatch();
            }
        }, { rootMargin: '200px' });
        
        observer.observe(sentinel);

        // Initial Search/Sort/Filter trigger
        updateDisplay();

    } catch (e) {
        console.error('Error loading projects:', e);
    }

    function renderFilters(langs) {
        langFilters.innerHTML = langs.map(lang => `
            <button class="lang-chip px-3 py-1 rounded-full text-sm font-medium border border-gray-200 dark:border-gray-700 hover:border-primary transition-all" data-lang="${lang}">
                ${lang}
            </button>
        `).join('');

        langFilters.addEventListener('click', (e) => {
            const chip = e.target.closest('.lang-chip');
            if (!chip) return;
            
            const lang = chip.dataset.lang;
            selectedLang = (selectedLang === lang) ? null : lang;
            updateFiltersUI();
            updateDisplay();
        });
    }

    function updateFiltersUI() {
        document.querySelectorAll('.lang-chip').forEach(chip => {
            if (chip.dataset.lang === selectedLang) {
                chip.classList.add('bg-primary', 'text-white', 'border-primary');
            } else {
                chip.classList.remove('bg-primary', 'text-white', 'border-primary');
            }
        });
        clearFilters.classList.toggle('hidden', !selectedLang);
    }

    function updateDisplay() {
        const query = searchInput.value.trim();
        let results = query ? fuse.search(query).map(r => r.item) : [...projects];

        if (selectedLang) {
            results = results.filter(p => p.l === selectedLang);
        }

        const sortBy = sortSelect.value;
        results.sort((a, b) => {
            if (sortBy === 'stars') return b.s - a.s;
            if (sortBy === 'forks') return b.f - a.f;
            if (sortBy === 'name') return a.n.localeCompare(b.n);
            return 0;
        });

        currentResults = results;
        currentIndex = 0;
        resultsGrid.innerHTML = ''; // Clear for new results
        
        resultsInfo.classList.remove('hidden');
        resultsCount.textContent = results.length;
        noResults.classList.toggle('hidden', results.length > 0);
        
        renderNextBatch();
    }

    function renderNextBatch() {
        if (currentIndex >= currentResults.length) {
            loadingSpinner.classList.add('hidden');
            return;
        }

        loadingSpinner.classList.remove('hidden');
        const nextBatch = currentResults.slice(currentIndex, currentIndex + BATCH_SIZE);
        
        const fragment = document.createDocumentFragment();
        nextBatch.forEach(repo => {
            const card = document.createElement('div');
            card.className = "group p-6 rounded-2xl border border-gray-200 dark:border-gray-700 hover:border-primary bg-white dark:bg-slate-800 transition-all hover:shadow-lg flex flex-col justify-between";
            card.innerHTML = `
                <div>
                    <div class="flex items-center gap-2 mb-4">
                        <a href="/dev/${repo.o.toLowerCase()}/" class="flex items-center gap-2 hover:text-primary transition-colors">
                            <img src="${repo.a}" alt="${repo.o}" class="w-6 h-6 rounded-full">
                            <span class="text-sm font-medium text-gray-500 group-hover:text-primary">@${repo.o}</span>
                        </a>
                    </div>
                    <h2 class="text-xl font-bold group-hover:text-primary transition-colors mb-2 break-all">
                        <a href="${repo.u}" target="_blank" rel="noopener noreferrer">${repo.n}</a>
                    </h2>
                    <p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-3 mb-4">${repo.d || "No description provided."}</p>
                </div>
                <div class="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-700">
                    <div class="flex items-center gap-4 text-sm font-medium">
                        <span class="flex items-center gap-1">★ ${repo.s}</span>
                        <span class="flex items-center gap-1">⑂ ${repo.f}</span>
                    </div>
                    ${repo.l ? `<span class="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs font-bold rounded-md">${repo.l}</span>` : ''}
                </div>
            `;
            fragment.appendChild(card);
        });

        resultsGrid.appendChild(fragment);
        currentIndex += BATCH_SIZE;
        
        if (currentIndex >= currentResults.length) {
            loadingSpinner.classList.add('hidden');
        }
    }

    searchInput.addEventListener('input', updateDisplay);
    sortSelect.addEventListener('change', updateDisplay);
    clearFilters.addEventListener('click', () => {
        selectedLang = null;
        updateFiltersUI();
        updateDisplay();
    });
});

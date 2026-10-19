let currentFundsData = [];
let currentSubcategory = "Flexi Cap Fund";
let rollingChartInstance = null;
let activeRollingSeries = [];
let modalReturnFocus = null;
let toastTimer = null;
let lastForceRefresh = false;

// DOM Elements
const categoryInput = document.getElementById("categoryInput");
const subcategoriesList = document.getElementById("subcategoriesList");
const forceRefreshCheckbox = document.getElementById("forceRefresh");
const searchBtn = document.getElementById("searchBtn");
const btnIcon = document.getElementById("btnIcon");
const btnText = document.getElementById("btnText");

const kpiSection = document.getElementById("kpiSection");
const kpiQualifying = document.getElementById("kpiQualifying");
const kpiTopRating = document.getElementById("kpiTopRating");
const kpiTopFund = document.getElementById("kpiTopFund");
const kpiAvgRolling = document.getElementById("kpiAvgRolling");
const kpiAvgTer = document.getElementById("kpiAvgTer");
const kpiCacheStatus = document.getElementById("kpiCacheStatus");
const kpiCacheTime = document.getElementById("kpiCacheTime");

const tableSection = document.getElementById("tableSection");
const fundsTableBody = document.getElementById("fundsTableBody");
const tableFilterInput = document.getElementById("tableFilterInput");
const tableSortSelect = document.getElementById("tableSortSelect");
const exportCsvBtn = document.getElementById("exportCsvBtn");

const loadingOverlay = document.getElementById("loadingOverlay");
const loadingTitle = document.getElementById("loadingTitle");
const loadingDesc = document.getElementById("loadingDesc");
const emptyState = document.getElementById("emptyState");
const errorState = document.getElementById("errorState");
const errorMessage = document.getElementById("errorMessage");
const researchResults = document.getElementById("researchResults");
const resultsTitle = document.getElementById("resultsTitle");
const resultCount = document.getElementById("resultCount");
const summaryStatus = document.getElementById("summaryStatus");
const pageContent = document.getElementById("pageContent");

// Modal Elements
const fundModal = document.getElementById("fundModal");
const modalDialog = document.getElementById("modalDialog");
const modalCloseBtnTop = document.getElementById("modalCloseBtnTop");
const modalCloseBtnBottom = document.getElementById("modalCloseBtnBottom");
const toast = document.getElementById("toast");
const toastText = document.getElementById("toastText");

// Initialize on load
document.addEventListener("DOMContentLoaded", () => {
    loadSubcategories();
    setupEventHandlers();
    // Run initial search for Flexi Cap Fund
    runResearch("Flexi Cap Fund", false);
});

// Load subcategories for datalist
async function loadSubcategories() {
    try {
        const res = await fetch("/api/subcategories");
        const data = await res.json();
        if (data.subcategories && Array.isArray(data.subcategories)) {
            subcategoriesList.innerHTML = "";
            data.subcategories.forEach(sub => {
                const opt = document.createElement("option");
                opt.value = sub;
                subcategoriesList.appendChild(opt);
            });
        }
    } catch (err) {
        console.error("Failed to load subcategories:", err);
    }
}

// Setup Event Handlers
function setupEventHandlers() {
    // Search Button
    searchBtn.addEventListener("click", () => {
        const cat = categoryInput.value.trim() || "Flexi Cap Fund";
        const force = forceRefreshCheckbox.checked;
        runResearch(cat, force);
    });

    // Enter key in input
    categoryInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            const cat = categoryInput.value.trim() || "Flexi Cap Fund";
            const force = forceRefreshCheckbox.checked;
            runResearch(cat, force);
        }
    });

    // Preset chips
    document.querySelectorAll(".preset-chip").forEach(chip => {
        chip.setAttribute("aria-pressed", String(chip.classList.contains("active")));
        chip.addEventListener("click", () => {
            const cat = chip.getAttribute("data-cat");
            categoryInput.value = cat;
            runResearch(cat, false);
        });
    });

    // Client-side filtering & sorting
    tableFilterInput.addEventListener("input", renderTable);
    tableSortSelect.addEventListener("change", renderTable);
    exportCsvBtn.addEventListener("click", exportTableToCSV);
    document.getElementById("retryBtn").addEventListener("click", () => {
        runResearch(currentSubcategory, lastForceRefresh);
    });
    document.getElementById("chooseCategoryBtn").addEventListener("click", () => {
        categoryInput.focus();
        categoryInput.select();
    });

    // Modal Tabs
    const tabs = [...document.querySelectorAll(".modal-tab-btn")];
    tabs.forEach((btn, index) => {
        btn.addEventListener("click", () => activateModalTab(btn));
        btn.addEventListener("keydown", (event) => {
            let target;
            if (event.key === "ArrowRight") target = tabs[(index + 1) % tabs.length];
            if (event.key === "ArrowLeft") target = tabs[(index + tabs.length - 1) % tabs.length];
            if (event.key === "Home") target = tabs[0];
            if (event.key === "End") target = tabs[tabs.length - 1];
            if (!target) return;
            event.preventDefault();
            activateModalTab(target);
            target.focus({ preventScroll: true });
        });
    });

    // STRICT NON-CLOSABLE BACKDROP IMPLEMENTATION:
    // Clicking on backdrop (outside modal-dialog) does NOT close the modal!
    fundModal.addEventListener("click", (e) => {
        if (e.target === fundModal) {
            e.stopPropagation();
            triggerBackdropLockedNotice();
        }
    });

    // Only Close Buttons can dismiss modal
    modalCloseBtnTop.addEventListener("click", closeModal);
    modalCloseBtnBottom.addEventListener("click", closeModal);

    // Disable ESC key closing as well to prevent accidental dismissals
    document.addEventListener("keydown", (e) => {
        if (fundModal.style.display !== "flex") return;
        if (e.key === "Escape") {
            e.preventDefault();
            triggerBackdropLockedNotice();
        }
        if (e.key === "Tab") {
            const focusable = [...modalDialog.querySelectorAll('button:not(:disabled), [tabindex="0"]')]
                .filter(element => element.getClientRects().length);
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
    });
}

function activateModalTab(button) {
    document.querySelectorAll(".modal-tab-btn").forEach(tab => {
        const selected = tab === button;
        tab.classList.toggle("active", selected);
        tab.setAttribute("aria-selected", String(selected));
        tab.tabIndex = selected ? 0 : -1;
    });
    document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.toggle("active", pane.id === button.dataset.tab);
    });
    if (button.dataset.tab === "tab-chart" && !rollingChartInstance) {
        renderRollingChart(activeRollingSeries);
    }
}

function triggerBackdropLockedNotice() {
    modalDialog.classList.add("shake");
    showToast("Analysis stays open. Use Close to return to the results.");
}

function showToast(message) {
    toastText.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
        modalDialog.classList.remove("shake");
    }, 5000);
}

function closeModal() {
    fundModal.style.display = "none";
    document.body.classList.remove("modal-open");
    pageContent.inert = false;
    modalDialog.classList.remove("shake");
    toast.classList.remove("show");
    clearTimeout(toastTimer);
    if (rollingChartInstance) {
        rollingChartInstance.destroy();
        rollingChartInstance = null;
    }
    if (modalReturnFocus && modalReturnFocus.isConnected) {
        modalReturnFocus.focus({ preventScroll: true });
    }
}

// Fetch Research Data
async function runResearch(subcategory, forceRefresh) {
    if (searchBtn.disabled) return;
    currentSubcategory = subcategory;
    lastForceRefresh = forceRefresh;
    resultsTitle.textContent = subcategory;
    document.querySelectorAll(".preset-chip").forEach(chip => {
        const selected = chip.dataset.cat === subcategory;
        chip.classList.toggle("active", selected);
        chip.setAttribute("aria-pressed", String(selected));
    });
    
    // UI state: loading
    setLoadingState(true, subcategory);

    try {
        const response = await fetch("/api/research", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                subcategory: subcategory,
                force_refresh: forceRefresh
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Failed to fetch research results");
        }

        const data = await response.json();
        currentFundsData = data.funds || [];
        searchBtn.dataset.state = "success";

        renderKPIs(data.summary);
        renderTable();

        if (currentFundsData.length === 0) {
            emptyState.style.display = "block";
            tableSection.style.display = "none";
        } else {
            emptyState.style.display = "none";
            tableSection.style.display = "block";
        }
    } catch (err) {
        console.error("Research error:", err);
        currentFundsData = [];
        errorMessage.textContent = `${err.message}. Retry research, or choose another category.`;
        errorState.hidden = false;
        resultCount.textContent = "Research unavailable";
        searchBtn.dataset.state = "error";
    } finally {
        setLoadingState(false, subcategory);
    }
}

function setLoadingState(isLoading, subcategory) {
    researchResults.setAttribute("aria-busy", String(isLoading));
    searchBtn.setAttribute("aria-busy", String(isLoading));
    document.querySelectorAll(".preset-chip").forEach(chip => { chip.disabled = isLoading; });
    if (isLoading) {
        searchBtn.disabled = true;
        searchBtn.dataset.state = "loading";
        btnIcon.textContent = "";
        btnText.textContent = "Analyzing…";
        resultCount.textContent = "";
        summaryStatus.hidden = true;
        errorState.hidden = true;
        loadingOverlay.style.display = "block";
        loadingTitle.textContent = `Analyzing ${subcategory}…`;
        loadingDesc.textContent = "Fetching daily NAV history and calculating 5-year rolling returns. Live research can take a few minutes.";
        tableSection.style.display = "none";
        kpiSection.style.display = "none";
        emptyState.style.display = "none";
    } else {
        searchBtn.disabled = false;
        btnIcon.textContent = "↗";
        btnText.textContent = "Analyze category";
        loadingOverlay.style.display = "none";
    }
}

// Render KPI Cards
function renderKPIs(summary) {
    if (!summary) return;
    kpiSection.style.display = "grid";
    summaryStatus.hidden = false;

    kpiQualifying.replaceChildren(document.createTextNode(String(summary.qualifying_funds_9y)));
    const total = document.createElement("small");
    total.textContent = ` / ${summary.total_funds_searched}`;
    kpiQualifying.appendChild(total);
    kpiTopRating.textContent = currentFundsData.length ? `${summary.category_top_rating} / 10` : "—";
    
    // Format top fund name cleanly
    kpiTopFund.textContent = summary.category_top_rated_fund || "No eligible funds";

    kpiAvgRolling.textContent = currentFundsData.length ? `${summary.category_avg_rolling_mean}%` : "—";
    kpiAvgTer.textContent = currentFundsData.length ? `${summary.category_avg_ter}%` : "—";

    kpiCacheStatus.textContent = summary.is_cached ? "Cached research" : "Live research";
    kpiCacheTime.textContent = `Updated: ${summary.last_updated}`;
}

// Filter and Sort Table
function getFilteredAndSortedFunds() {
    let list = [...currentFundsData];
    const query = tableFilterInput.value.trim().toLowerCase();

    if (query) {
        list = list.filter(f => 
            f.fund_name.toLowerCase().includes(query) || 
            (f.amc_name && f.amc_name.toLowerCase().includes(query)) ||
            (f.fund_manager && f.fund_manager.toLowerCase().includes(query))
        );
    }

    const sortType = tableSortSelect.value;
    list.sort((a, b) => {
        switch (sortType) {
            case "rating_desc":
                return b.rating - a.rating || b.rolling_stats.mean - a.rolling_stats.mean;
            case "rolling_mean_desc":
                return b.rolling_stats.mean - a.rolling_stats.mean;
            case "rolling_min_desc":
                return b.rolling_stats.min_return - a.rolling_stats.min_return;
            case "ter_asc":
                return a.expense_ratio - b.expense_ratio;
            case "aum_desc":
                return b.aum - a.aum;
            case "pre_5y_desc":
                return (b.precalculated_5y || 0) - (a.precalculated_5y || 0);
            default:
                return b.rating - a.rating;
        }
    });

    return list;
}

// Render Table Rows
function renderTable() {
    const funds = getFilteredAndSortedFunds();
    resultCount.textContent = `${funds.length} of ${currentFundsData.length} funds shown`;
    exportCsvBtn.disabled = funds.length === 0;
    fundsTableBody.innerHTML = "";

    if (funds.length === 0) {
        fundsTableBody.innerHTML = `
            <tr>
                <td colspan="12" class="no-results-cell">
                    <p>No funds match this filter. Try a different name or clear the filter.</p>
                    <button type="button" class="btn-secondary" id="clearFilterBtn">Clear filter</button>
                </td>
            </tr>
        `;
        document.getElementById("clearFilterBtn").addEventListener("click", () => {
            tableFilterInput.value = "";
            renderTable();
            tableFilterInput.focus();
        });
        return;
    }

    funds.forEach((fund, index) => {
        const tr = document.createElement("tr");

        // Rank badge styling
        let rankClass = "rank-badge";
        if (index === 0) rankClass += " rank-top-1";
        else if (index === 1) rankClass += " rank-top-2";
        else if (index === 2) rankClass += " rank-top-3";

        // Rating pill styling
        let ratingClass = "rating-badge ";
        if (fund.rating >= 8.5) ratingClass += "rating-high";
        else if (fund.rating >= 7.5) ratingClass += "rating-good";
        else if (fund.rating >= 6.0) ratingClass += "rating-medium";
        else ratingClass += "rating-low";

        // Trailing 5Y text
        const trailing5yText = fund.precalculated_5y !== null ? `${fund.precalculated_5y}%` : "N/A";
        
        // Min SIP formatted
        const minSipText = fund.min_sip_amount != null ? `₹${Number(fund.min_sip_amount).toLocaleString("en-IN")}` : "N/A";

        tr.innerHTML = `
            <td class="rank-cell">
                <span class="${rankClass}">#${index + 1}</span>
            </td>
            <td class="rating-cell">
                <div class="${ratingClass}">
                    ${fund.rating.toFixed(1)} <span class="rating-max">/10</span>
                </div>
            </td>
            <td class="fund-name-cell">
                <div class="fund-title" title="${fund.fund_name}">${fund.fund_name}</div>
                <div class="fund-meta">${fund.amc_name || "Mutual Fund"} • Code: ${fund.scode}</div>
            </td>
            <td>
                <div style="font-weight: 500;">${fund.inception_date}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">${fund.age_years} yrs</div>
            </td>
            <td>
                <div class="stat-numeric">₹${Number(fund.aum).toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr</div>
            </td>
            <td>
                <div class="stat-numeric">
                    ${fund.expense_ratio}%
                </div>
            </td>
            <td>
                <div class="stat-numeric ${fund.rolling_stats.mean < 0 ? 'text-negative' : 'text-positive'}">
                    ${fund.rolling_stats.mean}%
                </div>
            </td>
            <td>
                <div class="stat-numeric">
                    ${fund.rolling_stats.median}%
                </div>
            </td>
            <td>
                <div class="stat-numeric">
                    ${fund.rolling_stats.std_dev}%
                </div>
            </td>
            <td>
                <div class="stat-numeric">
                    ${trailing5yText}
                </div>
            </td>
            <td>
                <div class="stat-numeric">
                    ${minSipText}
                </div>
            </td>
            <td class="action-cell">
                <button class="btn-inspect" data-scode="${fund.scode}">View analysis ↗</button>
            </td>
        `;

        // Click row opens modal
        tr.addEventListener("click", () => openFundModal(fund, tr.querySelector(".btn-inspect")));
        const btnInspect = tr.querySelector(".btn-inspect");
        btnInspect.setAttribute("aria-label", `View analysis for ${fund.fund_name}`);
        const headers = document.querySelectorAll("#fundsTable thead th");
        [...tr.cells].forEach((cell, cellIndex) => {
            cell.dataset.label = headers[cellIndex].textContent;
        });
        btnInspect.addEventListener("click", (e) => {
            e.stopPropagation();
            openFundModal(fund, btnInspect);
        });

        fundsTableBody.appendChild(tr);
    });
}

// Open Fund Modal and populate all tabs
function openFundModal(fund, trigger) {
    if (!fund) return;
    modalReturnFocus = trigger || document.activeElement;

    // Header info
    document.getElementById("modalFundName").textContent = fund.fund_name;
    document.getElementById("modalSubcategoryAndAmc").textContent = `${fund.amc_name || 'AMC'} • ${fund.subcategory_name} • Code: ${fund.scode}`;
    
    // Rating badge in modal
    const modalRatingBadge = document.getElementById("modalRatingBadge");
    modalRatingBadge.className = "rating-badge " + (fund.rating >= 8.5 ? "rating-high" : (fund.rating >= 7.5 ? "rating-good" : (fund.rating >= 6.0 ? "rating-medium" : "rating-low")));
    modalRatingBadge.innerHTML = `${fund.rating.toFixed(1)} <span class="rating-max">/ 10</span>`;

    document.getElementById("modalTierLabel").textContent = fund.rating_breakdown.rating_label;
    document.getElementById("modalInceptionBadge").textContent = `${fund.age_years} Yrs Track Record (${fund.inception_date})`;

    // Key stats
    document.getElementById("modalAum").textContent = `₹${Number(fund.aum).toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`;
    document.getElementById("modalTer").textContent = `${fund.expense_ratio}%`;
    document.getElementById("modalMinSip").textContent = fund.min_sip_amount != null ? `₹${Number(fund.min_sip_amount).toLocaleString("en-IN")}` : "N/A";
    document.getElementById("modalBenchmark").textContent = fund.benchmark || "Not provided";
    document.getElementById("modalManager").textContent = fund.fund_manager || "N/A";
    document.getElementById("modalNav").textContent = fund.latest_nav ? `₹${Number(fund.latest_nav).toFixed(2)}` : "N/A";

    // Tab 1: Tabular returns
    // Precalculated
    document.getElementById("ret1m").textContent = fund.precalculated_1m !== null ? `${fund.precalculated_1m}%` : "N/A";
    document.getElementById("ret3m").textContent = fund.precalculated_3m !== null ? `${fund.precalculated_3m}%` : "N/A";
    document.getElementById("ret6m").textContent = fund.precalculated_6m !== null ? `${fund.precalculated_6m}%` : "N/A";
    document.getElementById("ret1y").textContent = fund.precalculated_1y !== null ? `${fund.precalculated_1y}%` : "N/A";
    document.getElementById("ret3y").textContent = fund.precalculated_3y !== null ? `${fund.precalculated_3y}%` : "N/A";
    document.getElementById("ret5y").textContent = fund.precalculated_5y !== null ? `${fund.precalculated_5y}%` : "N/A";
    document.getElementById("ret3yAbs").textContent = fund.precalculated_3y_abs !== null ? `${fund.precalculated_3y_abs}%` : "N/A";
    document.getElementById("ret5yAbs").textContent = fund.precalculated_5y_abs !== null ? `${fund.precalculated_5y_abs}%` : "N/A";

    // Rolling returns
    const roll = fund.rolling_stats;
    document.getElementById("rollMean").textContent = `${roll.mean}%`;
    document.getElementById("rollMedian").textContent = `${roll.median}%`;
    document.getElementById("rollMin").textContent = `${roll.min_return}%`;
    document.getElementById("rollMax").textContent = `${roll.max_return}%`;
    document.getElementById("rollStd").textContent = `${roll.std_dev}%`;
    document.getElementById("rollP10").textContent = `${roll.prob_above_10}%`;
    document.getElementById("rollP12").textContent = `${roll.prob_above_12}%`;
    document.getElementById("rollP15").textContent = `${roll.prob_above_15}%`;
    document.getElementById("rollNeg").textContent = `${roll.prob_negative}%`;
    document.getElementById("rollObsCount").textContent = `${roll.observation_count} windows`;
    ["ret5y", "rollMean", "rollMin"].forEach(id => {
        const element = document.getElementById(id);
        const value = Number.parseFloat(element.textContent);
        element.classList.toggle("text-negative", value < 0);
        element.classList.toggle("text-positive", value >= 0);
    });

    // Tab 3: Scorecard breakdown
    const rb = fund.rating_breakdown;
    document.getElementById("scoreRolling").textContent = `${rb.rolling_return_score.toFixed(2)} / 3.5`;
    document.getElementById("scoreTer").textContent = `${rb.expense_ratio_score.toFixed(2)} / 2.0`;
    document.getElementById("scoreConsistency").textContent = `${rb.consistency_score.toFixed(2)} / 1.5`;
    document.getElementById("scoreAum").textContent = `${rb.aum_score.toFixed(2)} / 1.0`;
    document.getElementById("scoreHistorical").textContent = `${rb.historical_return_score.toFixed(2)} / 2.0`;

    // Build the chart only once its tab has a measurable layout.
    activeRollingSeries = roll.rolling_series || [];

    // Set first tab active
    const firstTab = document.getElementById("returnsTab");
    activateModalTab(firstTab);
    fundModal.dispatchEvent(new CustomEvent("fund-analysis-open", { detail: fund }));
    document.querySelector(".modal-body").scrollTop = 0;

    // Display modal
    fundModal.style.display = "flex";
    document.body.classList.add("modal-open");
    pageContent.inert = true;
    firstTab.focus({ preventScroll: true });
}

// Render 5-Year Rolling Returns Chart with Chart.js
function renderRollingChart(series) {
    const canvas = document.getElementById("rollingChartCanvas");
    if (!canvas) return;
    const chartStatus = document.getElementById("chartStatus");
    const chartFrame = document.getElementById("chartFrame");

    if (rollingChartInstance) {
        rollingChartInstance.destroy();
        rollingChartInstance = null;
    }

    if (!series || series.length === 0 || typeof Chart === "undefined") {
        chartFrame.hidden = true;
        chartStatus.hidden = false;
        chartStatus.textContent = !series || series.length === 0
            ? "No rolling time series is available for this fund. Summary metrics are in Returns."
            : "The chart library could not load. Reload the page to retry; summary metrics are in Returns.";
        return;
    }
    chartFrame.hidden = false;
    chartStatus.hidden = true;

    const labels = series.map(p => p.date);
    const dataVals = series.map(p => p.cagr);

    const ctx = canvas.getContext("2d");
    const styles = getComputedStyle(document.documentElement);
    const token = name => styles.getPropertyValue(name).trim();

    rollingChartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "5-Year Rolling Return CAGR (%)",
                    data: dataVals,
                    borderColor: token("--color-accent"),
                    borderWidth: 2,
                    backgroundColor: token("--color-chart-fill"),
                    fill: true,
                    tension: 0.2,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: token("--color-accent")
                },
                {
                    label: "12% reference hurdle",
                    data: labels.map(() => 12.0),
                    borderColor: token("--color-secondary"),
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: "0% Breakeven Line",
                    data: labels.map(() => 0.0),
                    borderColor: token("--color-negative"),
                    borderWidth: 1,
                    borderDash: [3, 3],
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: {
                mode: "index",
                intersect: false
            },
            plugins: {
                legend: {
                    labels: {
                        color: token("--color-secondary"),
                        font: { family: token("--font-body"), size: 12 },
                        usePointStyle: true,
                        boxWidth: 8
                    }
                },
                tooltip: {
                    backgroundColor: token("--color-paper-2"),
                    titleColor: token("--color-ink"),
                    bodyColor: token("--color-secondary"),
                    borderColor: token("--color-rule"),
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}% CAGR`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: token("--color-rule") },
                    ticks: {
                        color: token("--color-muted"),
                        maxTicksLimit: 8,
                        font: { family: token("--font-body"), size: 12 }
                    }
                },
                y: {
                    grid: { color: token("--color-rule") },
                    ticks: {
                        color: token("--color-secondary"),
                        font: { family: token("--font-body"), size: 12 },
                        callback: function(value) {
                            return value + "%";
                        }
                    }
                }
            }
        }
    });
}

// Export Table Data to CSV
function exportTableToCSV() {
    const funds = getFilteredAndSortedFunds();
    if (funds.length === 0) {
        showToast("No funds to export. Clear the filter or analyze another category.");
        return;
    }

    const headers = [
        "Rank",
        "Rating (out of 10)",
        "Scheme Name",
        "AMC",
        "Code",
        "Inception Date",
        "Age (Years)",
        "AUM (Cr)",
        "Expense Ratio (%)",
        "Min SIP Amount (INR)",
        "5Y Rolling Avg Return (%)",
        "5Y Rolling Median Return (%)",
        "5Y Rolling Min Return (%)",
        "5Y Rolling Max Return (%)",
        "5Y Rolling Std Dev (%)",
        "Prob > 10% CAGR (%)",
        "Prob > 12% CAGR (%)",
        "Prob > 15% CAGR (%)",
        "Precalculated 5Y Return (%)",
        "Benchmark"
    ];

    const rows = funds.map((f, i) => [
        i + 1,
        f.rating,
        `"${f.fund_name.replace(/"/g, '""')}"`,
        `"${(f.amc_name || '').replace(/"/g, '""')}"`,
        f.scode,
        f.inception_date,
        f.age_years,
        f.aum,
        f.expense_ratio,
        f.min_sip_amount,
        f.rolling_stats.mean,
        f.rolling_stats.median,
        f.rolling_stats.min_return,
        f.rolling_stats.max_return,
        f.rolling_stats.std_dev,
        f.rolling_stats.prob_above_10,
        f.rolling_stats.prob_above_12,
        f.rolling_stats.prob_above_15,
        f.precalculated_5y !== null ? f.precalculated_5y : "",
        `"${(f.benchmark || '').replace(/"/g, '""')}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `mutual_funds_${currentSubcategory.toLowerCase().replace(/\s+/g, '_')}_research.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

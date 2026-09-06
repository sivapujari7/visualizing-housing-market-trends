// Global state to hold Chart.js instances for dynamic updates
let charts = {
    salesByRenovation: null,
    ageByRenovation: null,
    ageByFeatures: null
};

// Current grouping for the features chart
let activeFeatureGroup = 'bedrooms';

document.addEventListener('DOMContentLoaded', () => {
    // Check if we are on the dashboard page
    const dashboardElement = document.getElementById('dashboard-view');
    if (dashboardElement) {
        initDashboard();
    }
});

function initDashboard() {
    // 1. Setup Toggle View (Tableau vs Fallback Dashboard)
    const btnTableau = document.getElementById('btn-tableau-view');
    const btnFallback = document.getElementById('btn-fallback-view');
    const tableauContainer = document.getElementById('tableau-container');
    const fallbackContainer = document.getElementById('fallback-container');
    const filterSection = document.getElementById('filter-section');

    if (btnTableau && btnFallback) {
        btnTableau.addEventListener('click', () => {
            btnTableau.classList.add('active');
            btnFallback.classList.remove('active');
            tableauContainer.style.display = 'block';
            fallbackContainer.style.display = 'none';
            filterSection.style.display = 'none'; // Tableau has its own internal filters
        });

        btnFallback.addEventListener('click', () => {
            btnFallback.classList.add('active');
            btnTableau.classList.remove('active');
            tableauContainer.style.display = 'none';
            fallbackContainer.style.display = 'block';
            filterSection.style.display = 'block'; // Show filters for Chart.js
            updateDashboardData(); // Initial load for fallback visualizer
        });
    }

    // 2. Setup Filter Event Listeners
    const filterIds = ['filter-bedrooms', 'filter-bathrooms', 'filter-floors', 'filter-house-age', 'filter-renovation-status', 'filter-sale-price'];
    filterIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                updateDashboardData();
            });
        }
    });

    // 3. Feature Grouping Buttons (Chart 3)
    const btnBedrooms = document.getElementById('btn-group-bedrooms');
    const btnBathrooms = document.getElementById('btn-group-bathrooms');
    const btnFloors = document.getElementById('btn-group-floors');

    if (btnBedrooms && btnBathrooms && btnFloors) {
        const setGroupActive = (btn, group) => {
            [btnBedrooms, btnBathrooms, btnFloors].forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeFeatureGroup = group;
            fetchFeatureAgeData();
        };

        btnBedrooms.addEventListener('click', () => setGroupActive(btnBedrooms, 'bedrooms'));
        btnBathrooms.addEventListener('click', () => setGroupActive(btnBathrooms, 'bathrooms'));
        btnFloors.addEventListener('click', () => setGroupActive(btnFloors, 'floors'));
    }

    // Default: Initial load is Tableau Dashboard view
    if (tableauContainer && fallbackContainer && filterSection) {
        tableauContainer.style.display = 'block';
        fallbackContainer.style.display = 'none';
        filterSection.style.display = 'none';
    }
}

// Gather all currently selected filter parameters as a query string
function getFilterQueryParams() {
    const bedrooms = document.getElementById('filter-bedrooms')?.value || 'All';
    const bathrooms = document.getElementById('filter-bathrooms')?.value || 'All';
    const floors = document.getElementById('filter-floors')?.value || 'All';
    const houseAge = document.getElementById('filter-house-age')?.value || 'All';
    const renStatus = document.getElementById('filter-renovation-status')?.value || 'All';
    const salePrice = document.getElementById('filter-sale-price')?.value || 'All';

    return `bedrooms=${encodeURIComponent(bedrooms)}&bathrooms=${encodeURIComponent(bathrooms)}&floors=${encodeURIComponent(floors)}&house_age=${encodeURIComponent(houseAge)}&renovation_status=${encodeURIComponent(renStatus)}&sale_price=${encodeURIComponent(salePrice)}`;
}

// Fetch data from Flask API endpoints and reload all widgets
function updateDashboardData() {
    const params = getFilterQueryParams();
    
    // Load KPIs
    fetch(`/api/kpis?${params}`)
        .then(res => res.json())
        .then(payload => {
            if (payload.success) {
                updateKPIs(payload.data);
            }
        })
        .catch(err => console.error("Error loading KPIs:", err));

    // Load Chart 1: Total Sales by Years Since Renovation
    fetch(`/api/charts/sales_by_renovation?${params}`)
        .then(res => res.json())
        .then(payload => {
            if (payload.success) {
                renderSalesByRenovationChart(payload.data);
            }
        })
        .catch(err => console.error("Error loading Chart 1:", err));

    // Load Chart 2: House Age distribution by Renovation Status
    fetch(`/api/charts/age_by_renovation?${params}`)
        .then(res => res.json())
        .then(payload => {
            if (payload.success) {
                renderAgeByRenovationChart(payload.data);
            }
        })
        .catch(err => console.error("Error loading Chart 2:", err));

    // Load Chart 3: House Age grouped by Features (Bedrooms, Bathrooms, Floors)
    fetchFeatureAgeData();
}

function fetchFeatureAgeData() {
    const params = getFilterQueryParams();
    fetch(`/api/charts/age_by_features?${params}`)
        .then(res => res.json())
        .then(payload => {
            if (payload.success) {
                renderAgeByFeaturesChart(payload.data);
            }
        })
        .catch(err => console.error("Error loading Chart 3:", err));
}

// Formats number to currency style
function formatCurrency(val) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0
    }).format(val);
}

// Formats number to compact decimal/count format
function formatNumber(val) {
    return new Intl.NumberFormat('en-US').format(val);
}

// Update the DOM text content of the KPI cards
function updateKPIs(data) {
    const totalHousesEl = document.getElementById('kpi-total-houses');
    const avgPriceEl = document.getElementById('kpi-avg-price');
    const basementAreaEl = document.getElementById('kpi-basement-area');
    const priceSqftEl = document.getElementById('kpi-price-sqft');

    if (totalHousesEl) totalHousesEl.textContent = formatNumber(data.total_houses);
    if (avgPriceEl) avgPriceEl.textContent = formatCurrency(data.avg_price);
    if (basementAreaEl) basementAreaEl.textContent = formatNumber(data.total_basement_area) + " sqft";
    if (priceSqftEl) priceSqftEl.textContent = formatCurrency(data.avg_price_per_sqft) + "/sqft";
}

// ---------------- CHART RENDERING FUNCTIONS ----------------

function renderSalesByRenovationChart(data) {
    const ctx = document.getElementById('chart-sales-renovation')?.getContext('2d');
    if (!ctx) return;

    if (charts.salesByRenovation) {
        charts.salesByRenovation.destroy();
    }

    const labels = data.map(item => item.bin);
    const totalSales = data.map(item => item.total_sales);
    const houseCounts = data.map(item => item.count);

    charts.salesByRenovation = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Sales Volume ($)',
                    data: totalSales,
                    backgroundColor: 'rgba(99, 102, 241, 0.7)',
                    borderColor: 'rgb(99, 102, 241)',
                    borderWidth: 1.5,
                    borderRadius: 6,
                    yAxisID: 'y'
                },
                {
                    label: 'House Count',
                    data: houseCounts,
                    type: 'line',
                    borderColor: 'rgb(244, 63, 94)',
                    backgroundColor: 'rgba(244, 63, 94, 0.2)',
                    borderWidth: 3,
                    pointBackgroundColor: 'rgb(244, 63, 94)',
                    yAxisID: 'y1',
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#9ca3af', font: { family: 'Inter' } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.datasetIndex === 0) {
                                label += formatCurrency(context.parsed.y);
                            } else {
                                label += formatNumber(context.parsed.y) + ' houses';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af', font: { family: 'Inter' } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { 
                        color: '#9ca3af', 
                        font: { family: 'Inter' },
                        callback: function(value) {
                            return '$' + (value / 1e6).toFixed(1) + 'M';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Total Sales Volume',
                        color: '#9ca3af'
                    }
                },
                y1: {
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#9ca3af', font: { family: 'Inter' } },
                    title: {
                        display: true,
                        text: 'House Count',
                        color: '#9ca3af'
                    }
                }
            }
        }
    });
}

function renderAgeByRenovationChart(data) {
    const ctx = document.getElementById('chart-age-renovation')?.getContext('2d');
    if (!ctx) return;

    if (charts.ageByRenovation) {
        charts.ageByRenovation.destroy();
    }

    const labels = data.map(item => item.status);
    const counts = data.map(item => item.count);
    const avgAges = data.map(item => item.avg_age);

    charts.ageByRenovation = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: [
                    'rgba(168, 85, 247, 0.7)',  // Renovated
                    'rgba(99, 102, 241, 0.5)'   // Not Renovated
                ],
                borderColor: [
                    'rgb(168, 85, 247)',
                    'rgb(99, 102, 241)'
                ],
                borderWidth: 1.5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#9ca3af', font: { family: 'Inter' } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const index = context.dataIndex;
                            const count = counts[index];
                            const age = avgAges[index];
                            const label = labels[index];
                            return `${label}: ${formatNumber(count)} houses (Avg Age: ${age} yrs)`;
                        }
                    }
                }
            }
        }
    });
}

function renderAgeByFeaturesChart(data) {
    const ctx = document.getElementById('chart-age-features')?.getContext('2d');
    if (!ctx || !data || Object.keys(data).length === 0) return;

    if (charts.ageByFeatures) {
        charts.ageByFeatures.destroy();
    }

    const activeData = data[activeFeatureGroup];
    const labels = Object.keys(activeData);
    const avgAges = labels.map(label => activeData[label].avg_age);
    const houseCounts = labels.map(label => activeData[label].count);

    let barColor = 'rgba(168, 85, 247, 0.7)';
    let borderColor = 'rgb(168, 85, 247)';
    let groupTitle = 'Bedrooms';
    
    if (activeFeatureGroup === 'bathrooms') {
        barColor = 'rgba(244, 63, 94, 0.7)';
        borderColor = 'rgb(244, 63, 94)';
        groupTitle = 'Bathrooms';
    } else if (activeFeatureGroup === 'floors') {
        barColor = 'rgba(16, 185, 129, 0.7)';
        borderColor = 'rgb(16, 185, 129)';
        groupTitle = 'Floors';
    }

    charts.ageByFeatures = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: `Average House Age (Years)`,
                data: avgAges,
                backgroundColor: barColor,
                borderColor: borderColor,
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#9ca3af', font: { family: 'Inter' } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = labels[context.dataIndex];
                            const age = avgAges[context.dataIndex];
                            const count = houseCounts[context.dataIndex];
                            return `Group [${label}] -> Avg Age: ${age} yrs (Sample Size: ${formatNumber(count)})`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af', font: { family: 'Inter' } },
                    title: {
                        display: true,
                        text: `Property Feature: ${groupTitle}`,
                        color: '#9ca3af'
                    }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af', font: { family: 'Inter' } },
                    title: {
                        display: true,
                        text: 'Average Age (Years)',
                        color: '#9ca3af'
                    }
                }
            }
        }
    });
}

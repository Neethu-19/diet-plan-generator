// API Configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';

// DOM Elements
const form = document.getElementById('progress-form');
const adherenceSlider = document.getElementById('adherence');
const adherenceValue = document.getElementById('adherence-value');
const loading = document.getElementById('loading');
const errorDiv = document.getElementById('error');
const successDiv = document.getElementById('success');
const analysisContainer = document.getElementById('analysis-container');
const logsContainer = document.getElementById('logs-container');

// Set today's date as default
document.getElementById('date').valueAsDate = new Date();

// Update adherence display
adherenceSlider.addEventListener('input', (e) => {
    const value = parseFloat(e.target.value);
    adherenceValue.textContent = value.toFixed(2);
});

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await logProgress();
});

async function logProgress() {
    hideMessages();
    loading.classList.remove('hidden');
    
    try {
        const formData = new FormData(form);
        
        const request = {
            user_id: formData.get('user_id'),
            date: formData.get('date'),
            actual_weight_kg: parseFloat(formData.get('actual_weight_kg')),
            adherence_score: parseFloat(formData.get('adherence_score')),
            notes: formData.get('notes') || null,
            energy_level: formData.get('energy_level') ? parseInt(formData.get('energy_level')) : null,
            hunger_level: formData.get('hunger_level') ? parseInt(formData.get('hunger_level')) : null
        };
        
        const response = await fetch(`${API_BASE_URL}/log-progress`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to log progress');
        }
        
        const data = await response.json();
        
        loading.classList.add('hidden');
        showSuccess('Progress logged successfully! 🎉');
        
        // Reset form but keep user_id
        const userId = formData.get('user_id');
        form.reset();
        document.getElementById('user_id').value = userId;
        document.getElementById('date').valueAsDate = new Date();
        adherenceSlider.value = 0.8;
        adherenceValue.textContent = '0.80';
        
        // Suggest viewing analysis
        setTimeout(() => {
            if (confirm('Would you like to view your progress analysis?')) {
                document.getElementById('history-user-id').value = userId;
                showTab('history');
                loadHistory();
            }
        }, 1000);
        
    } catch (error) {
        console.error('Error:', error);
        loading.classList.add('hidden');
        showError(error.message);
    }
}


async function loadHistory() {
    const userId = document.getElementById('history-user-id').value;
    
    if (!userId) {
        showError('Please enter a user ID');
        return;
    }
    
    hideMessages();
    loading.classList.remove('hidden');
    analysisContainer.innerHTML = '';
    logsContainer.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE_URL}/progress/${userId}?days=30&analyze=true`);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to load progress history');
        }
        
        const data = await response.json();
        
        loading.classList.add('hidden');
        
        // Display analysis if available
        if (data.analysis) {
            displayAnalysis(data.analysis);
        } else {
            analysisContainer.innerHTML = `
                <div class="empty-state">
                    <h3>Not enough data for analysis</h3>
                    <p>Log at least 2 days of progress to see analysis</p>
                </div>
            `;
        }
        
        // Display logs
        if (data.logs && data.logs.length > 0) {
            displayLogs(data.logs);
        } else {
            logsContainer.innerHTML = `
                <div class="empty-state">
                    <h3>No progress logs yet</h3>
                    <p>Start logging your daily progress to track your journey</p>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Error:', error);
        loading.classList.add('hidden');
        showError(error.message);
    }
}

function displayAnalysis(analysis) {
    const statusClass = `status-${analysis.progress_status.replace('_', '-')}`;
    
    let adjustmentHTML = '';
    if (analysis.calorie_adjustment_needed) {
        const changeSign = analysis.suggested_calorie_change > 0 ? '+' : '';
        adjustmentHTML = `
            <div class="adjustment-box">
                <h3>🔧 Calorie Adjustment Recommended</h3>
                <p style="margin: 10px 0;">Based on your progress, we recommend adjusting your daily calorie target:</p>
                <div class="adjustment-value">${changeSign}${analysis.suggested_calorie_change} kcal/day</div>
                <p style="margin: 10px 0;">New target: <strong>${analysis.new_target_kcal} kcal/day</strong></p>
                <button onclick="applyAdjustment('${analysis.user_id}')" style="margin-top: 15px; width: auto; padding: 10px 20px;">
                    Apply Adjustment
                </button>
            </div>
        `;
    }
    
    analysisContainer.innerHTML = `
        <div class="analysis-card">
            <h2>📊 Progress Analysis</h2>
            <p style="opacity: 0.9; margin-top: 5px;">${analysis.analysis_period_days} days | ${analysis.num_logs} logs</p>
            
            <div class="analysis-grid">
                <div class="analysis-item">
                    <div class="analysis-value">${analysis.starting_weight} kg</div>
                    <div class="analysis-label">Starting Weight</div>
                </div>
                <div class="analysis-item">
                    <div class="analysis-value">${analysis.current_weight} kg</div>
                    <div class="analysis-label">Current Weight</div>
                </div>
                <div class="analysis-item">
                    <div class="analysis-value">${analysis.total_weight_change > 0 ? '+' : ''}${analysis.total_weight_change.toFixed(1)} kg</div>
                    <div class="analysis-label">Total Change</div>
                </div>
                <div class="analysis-item">
                    <div class="analysis-value">${(analysis.average_adherence * 100).toFixed(0)}%</div>
                    <div class="analysis-label">Avg Adherence</div>
                </div>
            </div>
            
            <div class="analysis-grid" style="margin-top: 20px;">
                <div class="analysis-item">
                    <div class="analysis-value">${analysis.actual_rate_kg_per_week.toFixed(2)}</div>
                    <div class="analysis-label">Actual Rate (kg/week)</div>
                </div>
                <div class="analysis-item">
                    <div class="analysis-value">${analysis.goal_rate_kg_per_week.toFixed(2)}</div>
                    <div class="analysis-label">Goal Rate (kg/week)</div>
                </div>
                <div class="analysis-item">
                    <div class="analysis-value">${analysis.adherence_trend}</div>
                    <div class="analysis-label">Adherence Trend</div>
                </div>
                <div class="analysis-item">
                    <span class="status-badge ${statusClass}">${analysis.progress_status.replace('_', ' ').toUpperCase()}</span>
                </div>
            </div>
            
            <div class="recommendation-box">
                <h3 style="margin-bottom: 10px;">💡 Recommendation</h3>
                <p>${analysis.recommendation}</p>
            </div>
        </div>
        
        ${adjustmentHTML}
    `;
}

function displayLogs(logs) {
    logsContainer.innerHTML = '<h3 style="margin: 30px 0 20px 0;">Progress History</h3>';
    
    logs.reverse().forEach(log => {
        const adherencePercent = (log.adherence_score * 100).toFixed(0);
        
        logsContainer.innerHTML += `
            <div class="log-entry">
                <div>
                    <div class="log-date">${log.log_date}</div>
                    <div class="log-details">
                        Weight: ${log.actual_weight_kg} kg | 
                        Adherence: ${adherencePercent}%
                        ${log.energy_level ? ` | Energy: ${log.energy_level}/5` : ''}
                        ${log.hunger_level ? ` | Hunger: ${log.hunger_level}/5` : ''}
                    </div>
                    ${log.notes ? `<div class="log-details" style="margin-top: 5px; font-style: italic;">"${log.notes}"</div>` : ''}
                </div>
                <div>
                    <div class="adherence-bar">
                        <div class="adherence-fill" style="width: ${adherencePercent}%"></div>
                    </div>
                </div>
            </div>
        `;
    });
}

async function applyAdjustment(userId) {
    if (!confirm('Apply the recommended calorie adjustment? This will affect future meal plans.')) {
        return;
    }
    
    hideMessages();
    loading.classList.remove('hidden');
    
    try {
        const response = await fetch(`${API_BASE_URL}/analyze-progress/${userId}?days=30&apply_adjustment=true`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to apply adjustment');
        }
        
        const data = await response.json();
        
        loading.classList.add('hidden');
        showSuccess('Calorie adjustment applied successfully! Future meal plans will use the new target.');
        
        // Reload history to show updated state
        setTimeout(() => loadHistory(), 2000);
        
    } catch (error) {
        console.error('Error:', error);
        loading.classList.add('hidden');
        showError(error.message);
    }
}

function showTab(tabName) {
    // Update tabs
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Update sections
    const sections = document.querySelectorAll('.section');
    sections.forEach(section => section.classList.remove('active'));
    
    if (tabName === 'log') {
        tabs[0].classList.add('active');
        document.getElementById('log-section').classList.add('active');
    } else {
        tabs[1].classList.add('active');
        document.getElementById('history-section').classList.add('active');
    }
}

function showError(message) {
    errorDiv.textContent = `Error: ${message}`;
    errorDiv.classList.remove('hidden');
    setTimeout(() => errorDiv.classList.add('hidden'), 5000);
}

function showSuccess(message) {
    successDiv.textContent = message;
    successDiv.classList.remove('hidden');
    setTimeout(() => successDiv.classList.add('hidden'), 5000);
}

function hideMessages() {
    errorDiv.classList.add('hidden');
    successDiv.classList.add('hidden');
}

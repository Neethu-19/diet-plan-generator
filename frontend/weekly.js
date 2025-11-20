// API Configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';

// State
let currentWeeklyPlan = null;
let currentUserId = null;

// DOM Elements
const form = document.getElementById('weekly-form');
const formSection = document.getElementById('form-section');
const loading = document.getElementById('loading');
const errorDiv = document.getElementById('error');
const planSection = document.getElementById('plan-section');
const viewTab = document.getElementById('view-tab');

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await generateWeeklyPlan();
});

async function generateWeeklyPlan() {
    hideError();
    formSection.classList.add('hidden');
    loading.classList.remove('hidden');
    
    try {
        const formData = new FormData(form);
        
        const userProfile = {
            user_id: formData.get('user_id'),
            age: parseInt(formData.get('age')),
            sex: formData.get('sex'),
            weight_kg: parseFloat(formData.get('weight_kg')),
            height_cm: parseFloat(formData.get('height_cm')),
            activity_level: 'moderate',
            goal: formData.get('goal'),
            goal_rate_kg_per_week: 0.0,
            diet_pref: formData.get('diet_pref'),
            allergies: formData.get('allergies') ? formData.get('allergies').split(',').map(a => a.trim()) : [],
            wake_time: formData.get('wake_time') + ':00',
            lunch_time: formData.get('lunch_time') + ':00',
            dinner_time: formData.get('dinner_time') + ':00',
            cooking_skill: parseInt(formData.get('cooking_skill')),
            budget_per_week: null
        };
        
        const activityPattern = {
            monday: formData.get('activity_monday'),
            tuesday: formData.get('activity_tuesday'),
            wednesday: formData.get('activity_wednesday'),
            thursday: formData.get('activity_thursday'),
            friday: formData.get('activity_friday'),
            saturday: formData.get('activity_saturday'),
            sunday: formData.get('activity_sunday')
        };
        
        // Get target audience and tips preference
        const targetAudience = formData.get('target_audience') || 'general';
        const includeTips = formData.get('include_tips') === 'on';
        
        const response = await fetch(`${API_BASE_URL}/generate-weekly-plan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_profile: userProfile,
                activity_pattern: activityPattern,
                max_recipe_repeats: parseInt(formData.get('max_recipe_repeats')),
                target_audience: targetAudience,
                include_tips: includeTips
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate weekly plan');
        }
        
        const data = await response.json();
        console.log('Received weekly plan data:', data);
        console.log('Daily plans:', data.daily_plans);
        currentWeeklyPlan = data;
        currentUserId = userProfile.user_id;
        
        loading.classList.add('hidden');
        displayWeeklyPlan(data);
        viewTab.style.display = 'block';
        showTab('view');
        
    } catch (error) {
        console.error('Error:', error);
        loading.classList.add('hidden');
        formSection.classList.remove('hidden');
        showError(error.message);
    }
}

function displayWeeklyPlan(plan) {
    console.log('Displaying plan:', plan);
    console.log('Number of daily plans:', plan.daily_plans ? plan.daily_plans.length : 0);
    
    planSection.innerHTML = '';
    
    // Check if plan has data
    if (!plan || !plan.daily_plans || plan.daily_plans.length === 0) {
        planSection.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <h2 style="color: #666; margin-bottom: 20px;">No meal plan generated yet</h2>
                <p style="color: #999; margin-bottom: 30px;">Click "Create Plan" tab to generate your 7-day meal plan</p>
                <button onclick="showTab('form')">Go to Create Plan</button>
            </div>
        `;
        planSection.classList.remove('hidden');
        return;
    }
    
    // Weekly Summary
    const stats = plan.weekly_stats || {};
    const summaryHTML = `
        <div class="weekly-summary">
            <h2>📊 Weekly Summary</h2>
            <p style="opacity: 0.9; margin-top: 5px;">Week: ${plan.start_date} to ${plan.end_date}</p>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value">${Math.round(stats.total_kcal || 0)}</div>
                    <div class="summary-label">Total Calories</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${Math.round(stats.avg_daily_kcal || 0)}</div>
                    <div class="summary-label">Avg Daily Calories</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${stats.unique_recipes || 0}</div>
                    <div class="summary-label">Unique Recipes</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${((plan.variety_score || 0) * 100).toFixed(0)}%</div>
                    <div class="summary-label">Variety Score</div>
                </div>
            </div>
        </div>
    `;
    
    planSection.innerHTML += summaryHTML;
    
    // Display enhanced presentation if available
    if (plan.enhanced_presentation) {
        displayEnhancedPresentation(plan.enhanced_presentation);
    }
    
    // Daily Plans
    plan.daily_plans.forEach((day, index) => {
        const dayHTML = createDayCard(day, index, plan.week_plan_id);
        planSection.innerHTML += dayHTML;
    });
    
    // Action Buttons
    planSection.innerHTML += `
        <div class="action-buttons">
            <button onclick="startOver()">Create New Plan</button>
            <button class="btn-secondary" onclick="showTab('form')">Edit Profile</button>
        </div>
    `;
    
    planSection.classList.remove('hidden');
}

function createDayCard(day, index, weekPlanId) {
    console.log(`Creating day card for day ${day.day_index}:`, day);
    console.log(`Number of meals: ${day.meals ? day.meals.length : 0}`);
    
    const meals = day.meals || [];
    const totals = day.total_nutrition || {};
    const targets = day.adjusted_targets || {};
    
    const mealsHTML = meals.map(meal => `
        <div class="meal-item">
            <div class="meal-type-badge">${meal.meal_type}</div>
            <div class="meal-title">${meal.recipe_title}</div>
            <div class="meal-nutrition">
                ${Math.round(meal.total_nutrition.kcal)} kcal | 
                P: ${Math.round(meal.total_nutrition.protein_g)}g | 
                C: ${Math.round(meal.total_nutrition.carbs_g)}g | 
                F: ${Math.round(meal.total_nutrition.fat_g)}g
            </div>
            <div class="collapsible" id="meal-details-${day.day_index}-${meal.meal_type}">
                <p style="margin-top: 10px; font-size: 13px;"><strong>Servings:</strong> ${meal.servings}</p>
                <p style="font-size: 13px; margin-top: 5px;"><strong>Ingredients:</strong></p>
                <ul class="ingredients-list">
                    ${meal.ingredients.slice(0, 8).map(ing => `<li>${ing}</li>`).join('')}
                    ${meal.ingredients.length > 8 ? `<li>...and ${meal.ingredients.length - 8} more</li>` : ''}
                </ul>
            </div>
            <button class="expand-btn" onclick="toggleDetails('meal-details-${day.day_index}-${meal.meal_type}')">
                Show Details
            </button>
        </div>
    `).join('');
    
    return `
        <div class="day-card">
            <div class="day-header">
                <div>
                    <div class="day-title">Day ${day.day_index + 1}: ${day.day_name}</div>
                    <div class="day-date">${day.date}</div>
                </div>
                <div>
                    <span class="activity-badge">${day.activity_level}</span>
                </div>
            </div>
            
            <div class="nutrition-bar">
                <div class="nutrition-stat">
                    <div class="nutrition-stat-value">${Math.round(totals.kcal || 0)}</div>
                    <div class="nutrition-stat-label">Calories (Target: ${Math.round(targets.target_kcal || 0)})</div>
                </div>
                <div class="nutrition-stat">
                    <div class="nutrition-stat-value">${Math.round(totals.protein_g || 0)}g</div>
                    <div class="nutrition-stat-label">Protein (Target: ${Math.round(targets.protein_g || 0)}g)</div>
                </div>
                <div class="nutrition-stat">
                    <div class="nutrition-stat-value">${Math.round(totals.carbs_g || 0)}g</div>
                    <div class="nutrition-stat-label">Carbs (Target: ${Math.round(targets.carbs_g || 0)}g)</div>
                </div>
                <div class="nutrition-stat">
                    <div class="nutrition-stat-value">${Math.round(totals.fat_g || 0)}g</div>
                    <div class="nutrition-stat-label">Fat (Target: ${Math.round(targets.fat_g || 0)}g)</div>
                </div>
            </div>
            
            ${mealsHTML}
            
            <div class="action-buttons">
                <button class="btn-small btn-secondary" onclick="regenerateDay('${weekPlanId}', ${day.day_index})">
                    🔄 Regenerate This Day
                </button>
            </div>
        </div>
    `;
}

async function regenerateDay(weekPlanId, dayIndex) {
    if (!currentUserId) {
        showError('User ID not found. Please create a new plan.');
        return;
    }
    
    if (!confirm(`Regenerate meals for Day ${dayIndex + 1}?`)) {
        return;
    }
    
    loading.classList.remove('hidden');
    planSection.classList.add('hidden');
    
    try {
        const formData = new FormData(form);
        const userProfile = {
            user_id: currentUserId,
            age: parseInt(formData.get('age')),
            sex: formData.get('sex'),
            weight_kg: parseFloat(formData.get('weight_kg')),
            height_cm: parseFloat(formData.get('height_cm')),
            activity_level: 'moderate',
            goal: formData.get('goal'),
            goal_rate_kg_per_week: 0.0,
            diet_pref: formData.get('diet_pref'),
            allergies: formData.get('allergies') ? formData.get('allergies').split(',').map(a => a.trim()) : [],
            wake_time: formData.get('wake_time') + ':00',
            lunch_time: formData.get('lunch_time') + ':00',
            dinner_time: formData.get('dinner_time') + ':00',
            cooking_skill: parseInt(formData.get('cooking_skill')),
            budget_per_week: null
        };
        
        const response = await fetch(`${API_BASE_URL}/regenerate-day`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                week_plan_id: weekPlanId,
                day_index: dayIndex,
                user_profile: userProfile
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to regenerate day');
        }
        
        const data = await response.json();
        currentWeeklyPlan = data;
        
        loading.classList.add('hidden');
        displayWeeklyPlan(data);
        
    } catch (error) {
        console.error('Error:', error);
        loading.classList.add('hidden');
        planSection.classList.remove('hidden');
        showError(error.message);
    }
}

function toggleDetails(elementId) {
    const element = document.getElementById(elementId);
    const button = event.target;
    
    if (element.classList.contains('expanded')) {
        element.classList.remove('expanded');
        button.textContent = 'Show Details';
    } else {
        element.classList.add('expanded');
        button.textContent = 'Hide Details';
    }
}

function showTab(tabName) {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    if (tabName === 'form') {
        formSection.classList.remove('hidden');
        planSection.classList.add('hidden');
        tabs[0].classList.add('active');
    } else {
        formSection.classList.add('hidden');
        planSection.classList.remove('hidden');
        tabs[1].classList.add('active');
    }
}

function startOver() {
    planSection.classList.add('hidden');
    formSection.classList.remove('hidden');
    hideError();
    currentWeeklyPlan = null;
    currentUserId = null;
    viewTab.style.display = 'none';
    showTab('form');
}

function showError(message) {
    errorDiv.textContent = `Error: ${message}`;
    errorDiv.classList.remove('hidden');
}

function hideError() {
    errorDiv.classList.add('hidden');
}

// Display enhanced presentation
function displayEnhancedPresentation(presentation) {
    if (!presentation) return;
    
    // Add summary
    const summaryHTML = `
        <div class="meal-plan-summary">
            ${presentation.summary}
        </div>
    `;
    planSection.innerHTML += summaryHTML;
    
    // Add sections (excluding nutrition overview for now, we'll show it separately)
    presentation.sections.forEach(section => {
        if (section.title.includes('Nutrition Overview')) return;
        
        let sectionHTML = `
            <div class="meal-section">
                <h3 class="section-title">${section.title}</h3>
                <div class="section-body">
                    ${markdownToHtml(section.body_markdown)}
                </div>
        `;
        
        // Add tips if present
        if (section.tips && section.tips.length > 0) {
            sectionHTML += `
                <div class="section-tips">
                    <ul class="tips-list">
                        ${section.tips.map(tip => `<li>${tip}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        sectionHTML += '</div>';
        planSection.innerHTML += sectionHTML;
    });
    
    // Add audience notes
    if (presentation.target_audience_notes) {
        const notesHTML = `
            <div class="audience-notes">
                ${presentation.target_audience_notes}
            </div>
        `;
        planSection.innerHTML += notesHTML;
    }
}

// Simple markdown to HTML converter
function markdownToHtml(markdown) {
    let html = markdown;
    
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Lists
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';
    
    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, '');
    html = html.replace(/<p>\s*<ul>/g, '<ul>');
    html = html.replace(/<\/ul>\s*<\/p>/g, '</ul>');
    
    return html;
}

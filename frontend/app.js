// API Configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';

// DOM Elements
const form = document.getElementById('profile-form');
const onboardingForm = document.getElementById('onboarding-form');
const loading = document.getElementById('loading');
const errorDiv = document.getElementById('error');
const mealPlanDiv = document.getElementById('meal-plan');
const submitBtn = document.getElementById('submit-btn');

// State
let currentMealPlan = null;

// Form submission handler
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Hide previous results
    errorDiv.classList.add('hidden');
    mealPlanDiv.classList.add('hidden');
    
    // Show loading
    onboardingForm.classList.add('hidden');
    loading.classList.remove('hidden');
    
    try {
        // Collect form data
        const formData = new FormData(form);
        const userProfile = {
            user_id: generateUserId(),
            age: parseInt(formData.get('age')),
            sex: formData.get('sex'),
            weight_kg: parseFloat(formData.get('weight_kg')),
            height_cm: parseFloat(formData.get('height_cm')),
            activity_level: formData.get('activity_level'),
            goal: formData.get('goal'),
            goal_rate_kg_per_week: parseFloat(formData.get('goal_rate_kg_per_week')),
            diet_pref: formData.get('diet_pref'),
            allergies: formData.get('allergies') ? formData.get('allergies').split(',').map(a => a.trim()) : [],
            wake_time: formData.get('wake_time') + ':00',
            lunch_time: formData.get('lunch_time') + ':00',
            dinner_time: formData.get('dinner_time') + ':00',
            cooking_skill: parseInt(formData.get('cooking_skill')),
            budget_per_week: null
        };
        
        // Get target audience and tips preference
        const targetAudience = formData.get('target_audience') || 'general';
        const includeTips = formData.get('include_tips') === 'on';
        
        // Call API
        const response = await fetch(`${API_BASE_URL}/generate-plan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_profile: userProfile,
                target_audience: targetAudience,
                include_tips: includeTips
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate meal plan');
        }
        
        const data = await response.json();
        currentMealPlan = data.meal_plan;
        
        // Hide loading
        loading.classList.add('hidden');
        
        // Display meal plan with enhanced presentation
        displayMealPlan(currentMealPlan, data.enhanced_presentation);
        
    } catch (error) {
        console.error('Error:', error);
        loading.classList.add('hidden');
        onboardingForm.classList.remove('hidden');
        showError(error.message);
    }
});

// Display meal plan
function displayMealPlan(mealPlan, enhancedPresentation = null) {
    console.log('Displaying meal plan:', mealPlan);
    
    if (!mealPlan || !mealPlan.meals || mealPlan.meals.length === 0) {
        showError('No meal plan data received. Please try again.');
        onboardingForm.classList.remove('hidden');
        return;
    }
    
    mealPlanDiv.innerHTML = '';
    
    // Display enhanced presentation if available
    if (enhancedPresentation) {
        displayEnhancedPresentation(enhancedPresentation);
    }
    
    // Nutrition summary
    const summaryHTML = `
        <div class="nutrition-summary">
            <h2>Daily Nutrition Summary</h2>
            <div class="nutrition-grid">
                <div class="nutrition-item">
                    <div class="nutrition-value">${Math.round(mealPlan.total_nutrition.kcal)}</div>
                    <div class="nutrition-label">Calories</div>
                </div>
                <div class="nutrition-item">
                    <div class="nutrition-value">${Math.round(mealPlan.total_nutrition.protein_g)}g</div>
                    <div class="nutrition-label">Protein</div>
                </div>
                <div class="nutrition-item">
                    <div class="nutrition-value">${Math.round(mealPlan.total_nutrition.carbs_g)}g</div>
                    <div class="nutrition-label">Carbs</div>
                </div>
                <div class="nutrition-item">
                    <div class="nutrition-value">${Math.round(mealPlan.total_nutrition.fat_g)}g</div>
                    <div class="nutrition-label">Fat</div>
                </div>
            </div>
        </div>
    `;
    
    mealPlanDiv.innerHTML += summaryHTML;
    
    // Timeline View
    const timelineHTML = createTimelineView(mealPlan.meals);
    mealPlanDiv.innerHTML += timelineHTML;
    
    // Charts
    const chartsHTML = `
        <div class="charts-container">
            <div class="chart-card">
                <h3>📊 Macro Distribution</h3>
                <canvas id="macroChart" width="300" height="300"></canvas>
            </div>
            <div class="chart-card">
                <h3>🔥 Calories by Meal</h3>
                <canvas id="caloriesChart" width="300" height="300"></canvas>
            </div>
        </div>
    `;
    mealPlanDiv.innerHTML += chartsHTML;
    
    // Export Buttons
    const exportHTML = `
        <div class="export-buttons">
            <button class="export-btn" onclick="exportToPDF()">
                📄 Export as PDF
            </button>
            <button class="export-btn" onclick="printPlan()">
                🖨️ Print Plan
            </button>
            <button class="export-btn" onclick="shareLink()">
                🔗 Copy Link
            </button>
        </div>
    `;
    mealPlanDiv.innerHTML += exportHTML;
    
    // Meals
    mealPlan.meals.forEach(meal => {
        const mealHTML = `
            <div class="meal-card" data-recipe-id="${meal.recipe_id}">
                <div class="meal-header">
                    <div class="meal-type">${meal.meal_type}</div>
                    <button class="swap-btn" onclick="swapMeal('${meal.meal_type}')">Swap</button>
                </div>
                <h3>${meal.recipe_title}</h3>
                <p><strong>Portion:</strong> ${meal.portion_size}</p>
                <p><strong>Nutrition:</strong> ${Math.round(meal.kcal)} kcal | 
                   ${Math.round(meal.protein_g)}g protein | 
                   ${Math.round(meal.carbs_g)}g carbs | 
                   ${Math.round(meal.fat_g)}g fat</p>
                <p><strong>Ingredients:</strong></p>
                <ul class="ingredients-list">
                    ${meal.ingredients.slice(0, 5).map(ing => `<li>${ing}</li>`).join('')}
                    ${meal.ingredients.length > 5 ? `<li>...and ${meal.ingredients.length - 5} more</li>` : ''}
                </ul>
                <p><strong>Instructions:</strong></p>
                <p>${meal.instructions.substring(0, 200)}${meal.instructions.length > 200 ? '...' : ''}</p>
                <div class="feedback-buttons">
                    <button class="feedback-btn like-btn" data-recipe-id="${meal.recipe_id}" onclick="handleFeedback('${meal.recipe_id}', '${meal.recipe_title.replace(/'/g, "\\'")}', true)">
                        👍 Like
                    </button>
                    <button class="feedback-btn dislike-btn" data-recipe-id="${meal.recipe_id}" onclick="handleFeedback('${meal.recipe_id}', '${meal.recipe_title.replace(/'/g, "\\'")}', false)">
                        👎 Dislike
                    </button>
                </div>
                <button class="regenerate-btn" onclick="regenerateMeal('${meal.meal_type}', '${meal.recipe_id}')">
                    🔄 Try Another Recipe
                </button>
            </div>
        `;
        mealPlanDiv.innerHTML += mealHTML;
    });
    
    // Load existing feedback to update button states
    if (typeof loadExistingFeedback === 'function') {
        setTimeout(loadExistingFeedback, 500);
    }
    
    // Add new plan button
    mealPlanDiv.innerHTML += `
        <button onclick="startOver()" style="margin-top: 20px;">Generate New Plan</button>
    `;
    
    mealPlanDiv.classList.remove('hidden');
    
    // Generate charts after DOM is ready
    setTimeout(() => {
        createMacroChart(mealPlan.total_nutrition);
        createCaloriesChart(mealPlan.meals);
    }, 100);
}

// Swap meal (placeholder)
function swapMeal(mealType) {
    alert(`Meal swap functionality for ${mealType} will be available once database integration is complete.`);
}

// Start over
function startOver() {
    mealPlanDiv.classList.add('hidden');
    errorDiv.classList.add('hidden');
    onboardingForm.classList.remove('hidden');
    form.reset();
    currentMealPlan = null;
}

// Show error
function showError(message) {
    errorDiv.textContent = `Error: ${message}`;
    errorDiv.classList.remove('hidden');
}

// Generate user ID
function generateUserId() {
    return 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
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
    mealPlanDiv.innerHTML += summaryHTML;
    
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
        mealPlanDiv.innerHTML += sectionHTML;
    });
    
    // Add audience notes
    if (presentation.target_audience_notes) {
        const notesHTML = `
            <div class="audience-notes">
                ${presentation.target_audience_notes}
            </div>
        `;
        mealPlanDiv.innerHTML += notesHTML;
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


// Create timeline view
function createTimelineView(meals) {
    const mealTimes = {
        'breakfast': { time: '7:00 AM', position: 15, emoji: '🌅' },
        'lunch': { time: '12:00 PM', position: 45, emoji: '🌞' },
        'dinner': { time: '7:00 PM', position: 75, emoji: '🌙' },
        'snack': { time: '3:00 PM', position: 60, emoji: '🍎' }
    };
    
    let timelineHTML = `
        <div class="timeline-container">
            <h3>📅 Your Meal Schedule</h3>
            <div class="timeline">
                <div class="timeline-line"></div>
    `;
    
    meals.forEach(meal => {
        const mealType = meal.meal_type.toLowerCase();
        const timeInfo = mealTimes[mealType] || { time: '12:00 PM', position: 50, emoji: '🍽️' };
        
        timelineHTML += `
            <div class="timeline-meal" style="left: ${timeInfo.position}%">
                <div class="timeline-dot"></div>
                <div class="timeline-label">${timeInfo.emoji} ${meal.meal_type}</div>
                <div class="timeline-time">${timeInfo.time}</div>
            </div>
        `;
    });
    
    timelineHTML += `
            </div>
        </div>
    `;
    
    return timelineHTML;
}

// Create macro pie chart
function createMacroChart(nutrition) {
    const ctx = document.getElementById('macroChart');
    if (!ctx) return;
    
    const protein = Math.round(nutrition.protein_g);
    const carbs = Math.round(nutrition.carbs_g);
    const fat = Math.round(nutrition.fat_g);
    
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Protein', 'Carbs', 'Fat'],
            datasets: [{
                data: [protein, carbs, fat],
                backgroundColor: [
                    '#FF6384',
                    '#36A2EB',
                    '#FFCE56'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value}g (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Create calories bar chart
function createCaloriesChart(meals) {
    const ctx = document.getElementById('caloriesChart');
    if (!ctx) return;
    
    const labels = meals.map(m => m.meal_type);
    const data = meals.map(m => Math.round(m.kcal));
    const colors = ['#FF9F40', '#4BC0C0', '#9966FF', '#FF6384'];
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Calories',
                data: data,
                backgroundColor: colors.slice(0, meals.length),
                borderWidth: 0,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y} kcal`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + ' kcal';
                        }
                    }
                }
            }
        }
    });
}

// Regenerate a single meal
async function regenerateMeal(mealType, currentRecipeId) {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '🔄 Regenerating...';
    
    try {
        // For now, show a message that this requires the swap endpoint
        alert(`Meal regeneration for ${mealType} will be available once the swap endpoint is fully implemented. For now, you can generate a new complete plan.`);
        
        // TODO: Implement when swap endpoint is ready
        // const response = await fetch(`${API_BASE_URL}/swap`, {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify({
        //         plan_id: currentMealPlan.plan_id,
        //         meal_type: mealType,
        //         exclude_recipes: [currentRecipeId]
        //     })
        // });
        
    } catch (error) {
        console.error('Error regenerating meal:', error);
        alert('Failed to regenerate meal. Please try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Export to PDF
function exportToPDF() {
    alert('PDF export will be implemented with jsPDF library. For now, use Print instead.');
    // TODO: Implement with jsPDF
}

// Print plan
function printPlan() {
    window.print();
}

// Share link
function shareLink() {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
        alert('Link copied to clipboard!');
    }).catch(() => {
        alert('Failed to copy link. Please copy manually: ' + url);
    });
}

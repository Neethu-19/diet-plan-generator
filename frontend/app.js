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
        
        // Call API
        const response = await fetch(`${API_BASE_URL}/generate-plan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_profile: userProfile
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
        
        // Display meal plan
        displayMealPlan(currentMealPlan);
        
    } catch (error) {
        console.error('Error:', error);
        loading.classList.add('hidden');
        onboardingForm.classList.remove('hidden');
        showError(error.message);
    }
});

// Display meal plan
function displayMealPlan(mealPlan) {
    mealPlanDiv.innerHTML = '';
    
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
    
    // Meals
    mealPlan.meals.forEach(meal => {
        const mealHTML = `
            <div class="meal-card">
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
            </div>
        `;
        mealPlanDiv.innerHTML += mealHTML;
    });
    
    // Add new plan button
    mealPlanDiv.innerHTML += `
        <button onclick="startOver()" style="margin-top: 20px;">Generate New Plan</button>
    `;
    
    mealPlanDiv.classList.remove('hidden');
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

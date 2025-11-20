/**
 * Preferences and Feedback Management
 */

const API_BASE = 'http://localhost:8000';
const USER_ID = 'user_123'; // In production, get from authentication

/**
 * Submit feedback for a recipe
 */
async function submitFeedback(recipeId, liked) {
    try {
        const response = await fetch(`${API_BASE}/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: USER_ID,
                recipe_id: recipeId,
                liked: liked
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to submit feedback');
        }
        
        const data = await response.json();
        console.log('Feedback submitted:', data);
        return data;
    } catch (error) {
        console.error('Error submitting feedback:', error);
        throw error;
    }
}

/**
 * Add feedback buttons to a meal card
 */
function addFeedbackButtons(mealElement, recipeId, recipeName) {
    // Check if buttons already exist
    if (mealElement.querySelector('.feedback-buttons')) {
        return;
    }
    
    const feedbackDiv = document.createElement('div');
    feedbackDiv.className = 'feedback-buttons';
    feedbackDiv.innerHTML = `
        <button class="feedback-btn like-btn" data-recipe-id="${recipeId}" onclick="handleFeedback('${recipeId}', '${recipeName}', true)">
            👍 Like
        </button>
        <button class="feedback-btn dislike-btn" data-recipe-id="${recipeId}" onclick="handleFeedback('${recipeId}', '${recipeName}', false)">
            👎 Dislike
        </button>
    `;
    
    mealElement.appendChild(feedbackDiv);
}

/**
 * Handle feedback button click
 */
async function handleFeedback(recipeId, recipeName, liked) {
    const likeBtn = document.querySelector(`.like-btn[data-recipe-id="${recipeId}"]`);
    const dislikeBtn = document.querySelector(`.dislike-btn[data-recipe-id="${recipeId}"]`);
    
    // Disable buttons while submitting
    likeBtn.disabled = true;
    dislikeBtn.disabled = true;
    
    try {
        await submitFeedback(recipeId, liked);
        
        // Update button states
        if (liked) {
            likeBtn.classList.add('liked');
            dislikeBtn.classList.remove('disliked');
            likeBtn.textContent = '👍 Liked!';
            dislikeBtn.textContent = '👎 Dislike';
        } else {
            dislikeBtn.classList.add('disliked');
            likeBtn.classList.remove('liked');
            dislikeBtn.textContent = '👎 Disliked!';
            likeBtn.textContent = '👍 Like';
        }
        
        // Show success message
        showFeedbackMessage(`Feedback saved for ${recipeName}`, 'success');
    } catch (error) {
        showFeedbackMessage('Error saving feedback. Please try again.', 'error');
    } finally {
        // Re-enable buttons
        likeBtn.disabled = false;
        dislikeBtn.disabled = false;
    }
}

/**
 * Show feedback message
 */
function showFeedbackMessage(message, type) {
    // Remove existing message if any
    const existingMessage = document.querySelector('.feedback-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `feedback-message ${type}`;
    messageDiv.textContent = message;
    messageDiv.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 8px;
        background: ${type === 'success' ? '#4caf50' : '#f44336'};
        color: white;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(messageDiv);
    
    // Remove after 3 seconds
    setTimeout(() => {
        messageDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => messageDiv.remove(), 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

/**
 * Load user's existing feedback and update button states
 */
async function loadExistingFeedback() {
    try {
        const response = await fetch(`${API_BASE}/feedback/${USER_ID}`);
        if (!response.ok) return;
        
        const data = await response.json();
        
        // Update button states for liked recipes
        data.liked_recipes.forEach(recipeId => {
            const likeBtn = document.querySelector(`.like-btn[data-recipe-id="${recipeId}"]`);
            const dislikeBtn = document.querySelector(`.dislike-btn[data-recipe-id="${recipeId}"]`);
            if (likeBtn) {
                likeBtn.classList.add('liked');
                likeBtn.textContent = '👍 Liked!';
            }
            if (dislikeBtn) {
                dislikeBtn.classList.remove('disliked');
                dislikeBtn.textContent = '👎 Dislike';
            }
        });
        
        // Update button states for disliked recipes
        data.disliked_recipes.forEach(recipeId => {
            const likeBtn = document.querySelector(`.like-btn[data-recipe-id="${recipeId}"]`);
            const dislikeBtn = document.querySelector(`.dislike-btn[data-recipe-id="${recipeId}"]`);
            if (dislikeBtn) {
                dislikeBtn.classList.add('disliked');
                dislikeBtn.textContent = '👎 Disliked!';
            }
            if (likeBtn) {
                likeBtn.classList.remove('liked');
                likeBtn.textContent = '👍 Like';
            }
        });
    } catch (error) {
        console.error('Error loading existing feedback:', error);
    }
}

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        submitFeedback,
        addFeedbackButtons,
        handleFeedback,
        loadExistingFeedback
    };
}

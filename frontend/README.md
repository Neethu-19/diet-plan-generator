# Frontend for Diet Planner

## 🎯 Unified Interface with 3 Interactive Features

The frontend now has a unified navigation system connecting all three main features:

### 1. Home Dashboard (`index.html`)
- Landing page with feature overview
- Quick navigation to all features
- Responsive design with feature cards

**Access:** http://localhost:3000/index.html

### 2. Daily Meal Plan (`daily.html`)
- Generate a personalized meal plan for one day
- Simple form with user profile
- View meals with nutrition information
- Quick single-day planning

**Access:** http://localhost:3000/daily.html

### 3. Weekly Meal Plan (`weekly.html`) ⭐ POPULAR
- Generate complete 7-day meal plans
- Set different activity levels for each day
- Recipe variety control (no repeats!)
- Activity-based macro adjustments
- View weekly nutrition summary
- Regenerate specific days
- Expandable meal details

**Access:** http://localhost:3000/weekly.html

### 4. Progress Tracker (`progress.html`) 🆕 NEW!
- Log daily weight and adherence
- Automatic progress analysis
- Adaptive calorie adjustments
- View progress history and trends
- Get personalized recommendations

**Access:** http://localhost:3000/progress.html

## 🚀 How to Run

1. **Start the API server:**
   ```bash
   python start_server.py
   ```

2. **Start the frontend server:**
   ```bash
   cd frontend
   python -m http.server 3000
   ```

3. **Open your browser:**
   ```
   http://localhost:3000
   ```

## 🔗 Navigation

All pages have a unified navigation bar:
- **Home** - Main dashboard
- **Daily Plan** - Single-day meal planning
- **Weekly Plan** - 7-day meal planning
- **Progress Tracker** - Track and adapt

## ✨ Features

### Daily Meal Planner:
✅ Quick single-day plans
✅ Personalized nutrition targets
✅ Recipe recommendations
✅ Dietary preference support

### Weekly Meal Planner:
✅ Complete 7-day meal plans
✅ Custom activity levels per day
✅ Recipe variety tracking (max repeats: 1)
✅ Activity-based nutrition adjustments
✅ Weekly nutrition summary
✅ Regenerate individual days
✅ Expandable meal details

### Progress Tracker:
✅ Daily progress logging
✅ Weight and adherence tracking
✅ Automatic progress analysis
✅ Adaptive calorie adjustments
✅ Progress history visualization
✅ Personalized recommendations
✅ Energy and hunger level tracking

## 🔄 Integration Flow

1. **Generate Weekly Plan** → Get 7 days of meals
2. **Log Progress Daily** → Track weight and adherence
3. **System Analyzes** → Detects if progress is on track
4. **Auto-Adjust Calories** → Future plans use adjusted targets
5. **Regenerate Plans** → New plans reflect your progress

## 📱 Responsive Design

- Works on desktop, tablet, and mobile
- Adaptive layouts
- Touch-friendly interfaces
- Mobile-optimized navigation

## 🎨 Tech Stack

- Pure HTML/CSS/JavaScript (no frameworks)
- Fetch API for backend communication
- CSS Grid & Flexbox layouts
- Modern gradient design
- Smooth animations and transitions

## 🔧 API Integration

All features connect to the backend API:
- `POST /api/v1/generate-plan` - Daily plans
- `POST /api/v1/generate-weekly-plan` - Weekly plans
- `POST /api/v1/log-progress` - Progress logging
- `GET /api/v1/progress/{user_id}` - Progress history
- `POST /api/v1/analyze-progress/{user_id}` - Apply adjustments

## 📊 User Workflow

```
1. Start → Home Dashboard
2. Choose Feature:
   a. Daily Plan → Quick meal plan for today
   b. Weekly Plan → Plan entire week
   c. Progress Tracker → Log and analyze
3. Generate/Log → Get results
4. Track Progress → System adapts
5. Repeat → Continuous optimization
```

## 🎯 Next Steps

After opening http://localhost:3000:
1. Explore the home dashboard
2. Try generating a weekly plan
3. Log some progress data
4. See the adaptive system in action!

Enjoy your personalized, adaptive meal planning experience! 🥗📅📊

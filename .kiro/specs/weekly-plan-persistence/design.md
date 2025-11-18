# Design Document: Weekly Plan Persistence

## Overview

This design extends the existing weekly meal planning system with database persistence capabilities. The system will store 7-day meal plans in a relational database, enabling users to retrieve plans by date, view specific days (Today/Tomorrow/Full Week), and regenerate individual meals or entire days while maintaining recipe variety constraints.

The design follows the existing repository pattern and integrates seamlessly with the current `WeeklyPlanner` service, adding a persistence layer without disrupting the core planning logic.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│  /generate-weekly-plan  /get-weekly-plan  /regenerate-day   │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  Service Layer                               │
│  WeeklyPlanner (existing) + WeeklyPlanRepository (new)      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  Data Layer                                  │
│  weekly_plans  │  daily_plans  │  plan_meals                │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Plan Generation**: API → WeeklyPlanner → WeeklyPlanRepository → Database
2. **Plan Retrieval**: API → WeeklyPlanRepository → Database → API
3. **Day Regeneration**: API → WeeklyPlanner → WeeklyPlanRepository → Database

## Components and Interfaces

### 1. Database Models

#### WeeklyPlanModel
```python
class WeeklyPlanModel(Base):
    """Weekly meal plan table."""
    __tablename__ = "weekly_plans"
    
    week_plan_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    activity_pattern = Column(JSON, nullable=False)  # {day_name: activity_level}
    variety_score = Column(Float, nullable=False)
    max_recipe_repeats = Column(Integer, default=2)
    variety_preference = Column(Float, default=0.8)
    is_archived = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("UserProfileModel", back_populates="weekly_plans")
    daily_plans = relationship("DailyPlanModel", back_populates="weekly_plan", cascade="all, delete-orphan")
```

#### DailyPlanModel
```python
class DailyPlanModel(Base):
    """Daily meal plan within a weekly plan."""
    __tablename__ = "daily_plans"
    
    day_plan_id = Column(String, primary_key=True, index=True)
    week_plan_id = Column(String, ForeignKey("weekly_plans.week_plan_id"), nullable=False, index=True)
    day_index = Column(Integer, nullable=False)  # 0-6
    date = Column(Date, nullable=False, index=True)
    day_name = Column(String, nullable=False)  # monday, tuesday, etc.
    activity_level = Column(String, nullable=False)
    
    # Adjusted nutrition targets
    target_kcal = Column(Float, nullable=False)
    target_protein_g = Column(Float, nullable=False)
    target_carbs_g = Column(Float, nullable=False)
    target_fat_g = Column(Float, nullable=False)
    
    # Actual nutrition totals
    total_kcal = Column(Float, nullable=False)
    total_protein_g = Column(Float, nullable=False)
    total_carbs_g = Column(Float, nullable=False)
    total_fat_g = Column(Float, nullable=False)
    
    nutrition_provenance = Column(String, nullable=False)
    plan_version = Column(String, nullable=False)
    sources = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    weekly_plan = relationship("WeeklyPlanModel", back_populates="daily_plans")
    meals = relationship("PlanMealModel", back_populates="daily_plan", cascade="all, delete-orphan")
```

#### PlanMealModel
```python
class PlanMealModel(Base):
    """Individual meal within a daily plan."""
    __tablename__ = "plan_meals"
    
    meal_id = Column(String, primary_key=True, index=True)
    day_plan_id = Column(String, ForeignKey("daily_plans.day_plan_id"), nullable=False, index=True)
    meal_type = Column(String, nullable=False)  # breakfast, lunch, dinner, snacks
    sequence = Column(Integer, nullable=False)  # Order within the day
    
    recipe_id = Column(String, nullable=False, index=True)
    recipe_title = Column(String, nullable=False)
    servings = Column(Float, nullable=False)
    
    # Nutrition per serving
    kcal_per_serving = Column(Float, nullable=False)
    protein_g_per_serving = Column(Float, nullable=False)
    carbs_g_per_serving = Column(Float, nullable=False)
    fat_g_per_serving = Column(Float, nullable=False)
    
    # Total nutrition (servings * per_serving)
    total_kcal = Column(Float, nullable=False)
    total_protein_g = Column(Float, nullable=False)
    total_carbs_g = Column(Float, nullable=False)
    total_fat_g = Column(Float, nullable=False)
    
    ingredients = Column(JSON, default=list)
    instructions = Column(Text, nullable=True)
    prep_time_min = Column(Integer, nullable=True)
    cook_time_min = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    daily_plan = relationship("DailyPlanModel", back_populates="meals")
```

### 2. Repository Layer

#### WeeklyPlanRepository

```python
class WeeklyPlanRepository:
    """Repository for weekly meal plan operations."""
    
    def create_weekly_plan(self, weekly_plan_dict: Dict) -> WeeklyPlanModel:
        """Store a complete weekly plan with all daily plans and meals."""
        
    def get_weekly_plan(self, week_plan_id: str) -> Optional[WeeklyPlanModel]:
        """Retrieve a weekly plan by ID with all related data."""
        
    def get_weekly_plan_by_date(self, user_id: str, date: date) -> Optional[WeeklyPlanModel]:
        """Find the weekly plan containing a specific date."""
        
    def get_user_weekly_plans(self, user_id: str, limit: int = 10, include_archived: bool = False) -> List[WeeklyPlanModel]:
        """Get all weekly plans for a user."""
        
    def update_daily_plan(self, day_plan_id: str, updated_meals: List[Dict]) -> Optional[DailyPlanModel]:
        """Update a specific day's meals."""
        
    def archive_weekly_plan(self, week_plan_id: str) -> bool:
        """Soft delete a weekly plan."""
        
    def delete_weekly_plan(self, week_plan_id: str) -> bool:
        """Permanently delete a weekly plan."""
        
    def get_daily_plan(self, week_plan_id: str, day_index: int) -> Optional[DailyPlanModel]:
        """Get a specific day from a weekly plan."""
        
    def get_today_plan(self, user_id: str) -> Optional[DailyPlanModel]:
        """Get today's meal plan for a user."""
        
    def get_tomorrow_plan(self, user_id: str) -> Optional[DailyPlanModel]:
        """Get tomorrow's meal plan for a user."""
```

### 3. Service Layer Updates

#### WeeklyPlanner Enhancements

The existing `WeeklyPlanner` service will be enhanced with persistence methods:

```python
class WeeklyPlanner:
    def __init__(self, db_session: Optional[Session] = None):
        self.nutrition_engine = NutritionEngine()
        self.rag_module = RAGModule()
        self.daily_planner = SimplePlanner()
        self.validator = Validator()
        self.repository = WeeklyPlanRepository(db_session) if db_session else None
    
    def generate_and_save_weekly_plan(self, request: WeeklyPlanRequest) -> Dict:
        """Generate weekly plan and save to database."""
        # Generate plan (existing logic)
        weekly_plan = self.generate_weekly_plan(request)
        
        # Save to database if repository available
        if self.repository:
            self.repository.create_weekly_plan(weekly_plan)
        
        return weekly_plan
    
    def regenerate_and_update_day(self, week_plan_id: str, day_index: int, constraints: Optional[Dict] = None) -> Dict:
        """Regenerate a day and update in database."""
        # Load existing plan
        db_plan = self.repository.get_weekly_plan(week_plan_id)
        
        # Convert to dict format
        weekly_plan = self._model_to_dict(db_plan)
        
        # Regenerate day (existing logic)
        updated_plan = self.regenerate_day(weekly_plan, day_index, constraints)
        
        # Update in database
        self.repository.update_daily_plan(
            updated_plan['daily_plans'][day_index]['day_plan_id'],
            updated_plan['daily_plans'][day_index]['meals']
        )
        
        return updated_plan
```

### 4. API Endpoints

#### Enhanced Endpoints

```python
@router.post("/generate-weekly-plan", response_model=WeeklyPlanResponse)
async def generate_weekly_plan(request: WeeklyPlanRequest, db: Session = Depends(get_db)):
    """Generate and save a 7-day meal plan."""
    planner = WeeklyPlanner(db_session=db)
    weekly_plan = planner.generate_and_save_weekly_plan(request)
    return WeeklyPlanResponse(weekly_plan=weekly_plan)

@router.get("/weekly-plan/{week_plan_id}", response_model=WeeklyPlanResponse)
async def get_weekly_plan(week_plan_id: str, db: Session = Depends(get_db)):
    """Retrieve a weekly plan by ID."""
    repository = WeeklyPlanRepository(db)
    db_plan = repository.get_weekly_plan(week_plan_id)
    if not db_plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    return WeeklyPlanResponse(weekly_plan=_model_to_dict(db_plan))

@router.get("/weekly-plan/today/{user_id}", response_model=DailyPlanResponse)
async def get_today_plan(user_id: str, db: Session = Depends(get_db)):
    """Get today's meal plan."""
    repository = WeeklyPlanRepository(db)
    daily_plan = repository.get_today_plan(user_id)
    if not daily_plan:
        raise HTTPException(status_code=404, detail="No active plan for today")
    return DailyPlanResponse(daily_plan=_model_to_dict(daily_plan))

@router.get("/weekly-plan/tomorrow/{user_id}", response_model=DailyPlanResponse)
async def get_tomorrow_plan(user_id: str, db: Session = Depends(get_db)):
    """Get tomorrow's meal plan."""
    repository = WeeklyPlanRepository(db)
    daily_plan = repository.get_tomorrow_plan(user_id)
    if not daily_plan:
        raise HTTPException(status_code=404, detail="No active plan for tomorrow")
    return DailyPlanResponse(daily_plan=_model_to_dict(daily_plan))

@router.post("/regenerate-day", response_model=WeeklyPlanResponse)
async def regenerate_day(request: RegenerateDayRequest, db: Session = Depends(get_db)):
    """Regenerate a specific day in a weekly plan."""
    planner = WeeklyPlanner(db_session=db)
    updated_plan = planner.regenerate_and_update_day(
        request.week_plan_id,
        request.day_index,
        request.constraints
    )
    return WeeklyPlanResponse(weekly_plan=updated_plan)

@router.delete("/weekly-plan/{week_plan_id}")
async def delete_weekly_plan(week_plan_id: str, archive_only: bool = True, db: Session = Depends(get_db)):
    """Delete or archive a weekly plan."""
    repository = WeeklyPlanRepository(db)
    
    if archive_only:
        success = repository.archive_weekly_plan(week_plan_id)
    else:
        success = repository.delete_weekly_plan(week_plan_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    
    return {"status": "success", "archived": archive_only}

@router.get("/weekly-plans/{user_id}", response_model=List[WeeklyPlanSummary])
async def get_user_weekly_plans(
    user_id: str,
    limit: int = 10,
    include_archived: bool = False,
    db: Session = Depends(get_db)
):
    """Get all weekly plans for a user."""
    repository = WeeklyPlanRepository(db)
    plans = repository.get_user_weekly_plans(user_id, limit, include_archived)
    return [_model_to_summary(plan) for plan in plans]
```

## Data Models

### Database Schema Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      user_profiles                           │
│  user_id (PK)  │  age  │  sex  │  weight_kg  │  ...        │
└────────────┬────────────────────────────────────────────────┘
             │
             │ 1:N
             │
┌────────────▼────────────────────────────────────────────────┐
│                      weekly_plans                            │
│  week_plan_id (PK)  │  user_id (FK)  │  start_date         │
│  end_date  │  activity_pattern  │  variety_score           │
│  is_archived  │  created_at  │  updated_at                  │
└────────────┬────────────────────────────────────────────────┘
             │
             │ 1:7
             │
┌────────────▼────────────────────────────────────────────────┐
│                      daily_plans                             │
│  day_plan_id (PK)  │  week_plan_id (FK)  │  day_index      │
│  date  │  day_name  │  activity_level  │  target_kcal      │
│  total_kcal  │  nutrition_provenance  │  ...               │
└────────────┬────────────────────────────────────────────────┘
             │
             │ 1:N
             │
┌────────────▼────────────────────────────────────────────────┐
│                      plan_meals                              │
│  meal_id (PK)  │  day_plan_id (FK)  │  meal_type           │
│  recipe_id  │  recipe_title  │  servings  │  total_kcal    │
│  ingredients  │  instructions  │  ...                       │
└─────────────────────────────────────────────────────────────┘
```

### Indexes

For optimal query performance:

```sql
-- Weekly plans
CREATE INDEX idx_weekly_plans_user_date ON weekly_plans(user_id, start_date DESC);
CREATE INDEX idx_weekly_plans_archived ON weekly_plans(is_archived);

-- Daily plans
CREATE INDEX idx_daily_plans_week ON daily_plans(week_plan_id);
CREATE INDEX idx_daily_plans_date ON daily_plans(date);

-- Plan meals
CREATE INDEX idx_plan_meals_day ON plan_meals(day_plan_id);
CREATE INDEX idx_plan_meals_recipe ON plan_meals(recipe_id);
```

## Error Handling

### Error Scenarios

1. **Plan Not Found**
   - Status: 404
   - Message: "Weekly plan not found"
   - Action: Return error response

2. **No Active Plan for Date**
   - Status: 404
   - Message: "No active meal plan for [date]"
   - Action: Suggest generating a new plan

3. **Invalid Day Index**
   - Status: 400
   - Message: "Day index must be between 0 and 6"
   - Action: Return validation error

4. **Database Connection Error**
   - Status: 503
   - Message: "Database temporarily unavailable"
   - Action: Retry logic, fallback to in-memory generation

5. **Concurrent Modification**
   - Status: 409
   - Message: "Plan was modified by another request"
   - Action: Reload and retry

### Error Handling Strategy

```python
try:
    weekly_plan = planner.generate_and_save_weekly_plan(request)
except IntegrityError as e:
    logger.error(f"Database integrity error: {e}")
    raise HTTPException(status_code=409, detail="Plan already exists or constraint violation")
except OperationalError as e:
    logger.error(f"Database operational error: {e}")
    raise HTTPException(status_code=503, detail="Database temporarily unavailable")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Failed to generate weekly plan")
```

## Testing Strategy

### Unit Tests

1. **Repository Tests**
   - Test CRUD operations for weekly plans
   - Test date-based queries (today, tomorrow, date range)
   - Test archiving and deletion
   - Test cascade deletes

2. **Service Tests**
   - Test plan generation with persistence
   - Test day regeneration with database updates
   - Test recipe variety tracking across database loads

3. **Model Tests**
   - Test model relationships
   - Test JSON serialization/deserialization
   - Test constraint validations

### Integration Tests

1. **End-to-End Flow**
   - Generate weekly plan → Save → Retrieve → Verify
   - Regenerate day → Update → Retrieve → Verify
   - Archive plan → Verify not in active queries

2. **Date-Based Queries**
   - Create plan for current week
   - Query today's plan
   - Query tomorrow's plan
   - Query full week

3. **Multi-User Scenarios**
   - Multiple users with overlapping dates
   - Verify user isolation
   - Test concurrent plan generation

### Performance Tests

1. **Query Performance**
   - Measure retrieval time for weekly plans
   - Test index effectiveness
   - Benchmark complex joins

2. **Bulk Operations**
   - Generate multiple weekly plans
   - Test pagination for user plan lists

## Migration Strategy

### Alembic Migration

```python
"""Add weekly plan tables

Revision ID: 002_weekly_plans
Revises: 001_initial
Create Date: 2024-01-15
"""

def upgrade():
    # Create weekly_plans table
    op.create_table(
        'weekly_plans',
        sa.Column('week_plan_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('activity_pattern', sa.JSON(), nullable=False),
        sa.Column('variety_score', sa.Float(), nullable=False),
        sa.Column('max_recipe_repeats', sa.Integer(), nullable=False),
        sa.Column('variety_preference', sa.Float(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('week_plan_id'),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.user_id'])
    )
    
    # Create indexes
    op.create_index('idx_weekly_plans_user_date', 'weekly_plans', ['user_id', 'start_date'])
    op.create_index('idx_weekly_plans_archived', 'weekly_plans', ['is_archived'])
    
    # Create daily_plans table
    op.create_table(
        'daily_plans',
        sa.Column('day_plan_id', sa.String(), nullable=False),
        sa.Column('week_plan_id', sa.String(), nullable=False),
        sa.Column('day_index', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('day_name', sa.String(), nullable=False),
        sa.Column('activity_level', sa.String(), nullable=False),
        sa.Column('target_kcal', sa.Float(), nullable=False),
        sa.Column('target_protein_g', sa.Float(), nullable=False),
        sa.Column('target_carbs_g', sa.Float(), nullable=False),
        sa.Column('target_fat_g', sa.Float(), nullable=False),
        sa.Column('total_kcal', sa.Float(), nullable=False),
        sa.Column('total_protein_g', sa.Float(), nullable=False),
        sa.Column('total_carbs_g', sa.Float(), nullable=False),
        sa.Column('total_fat_g', sa.Float(), nullable=False),
        sa.Column('nutrition_provenance', sa.String(), nullable=False),
        sa.Column('plan_version', sa.String(), nullable=False),
        sa.Column('sources', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('day_plan_id'),
        sa.ForeignKeyConstraint(['week_plan_id'], ['weekly_plans.week_plan_id'], ondelete='CASCADE')
    )
    
    # Create indexes
    op.create_index('idx_daily_plans_week', 'daily_plans', ['week_plan_id'])
    op.create_index('idx_daily_plans_date', 'daily_plans', ['date'])
    
    # Create plan_meals table
    op.create_table(
        'plan_meals',
        sa.Column('meal_id', sa.String(), nullable=False),
        sa.Column('day_plan_id', sa.String(), nullable=False),
        sa.Column('meal_type', sa.String(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.String(), nullable=False),
        sa.Column('recipe_title', sa.String(), nullable=False),
        sa.Column('servings', sa.Float(), nullable=False),
        sa.Column('kcal_per_serving', sa.Float(), nullable=False),
        sa.Column('protein_g_per_serving', sa.Float(), nullable=False),
        sa.Column('carbs_g_per_serving', sa.Float(), nullable=False),
        sa.Column('fat_g_per_serving', sa.Float(), nullable=False),
        sa.Column('total_kcal', sa.Float(), nullable=False),
        sa.Column('total_protein_g', sa.Float(), nullable=False),
        sa.Column('total_carbs_g', sa.Float(), nullable=False),
        sa.Column('total_fat_g', sa.Float(), nullable=False),
        sa.Column('ingredients', sa.JSON(), nullable=False),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('prep_time_min', sa.Integer(), nullable=True),
        sa.Column('cook_time_min', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('meal_id'),
        sa.ForeignKeyConstraint(['day_plan_id'], ['daily_plans.day_plan_id'], ondelete='CASCADE')
    )
    
    # Create indexes
    op.create_index('idx_plan_meals_day', 'plan_meals', ['day_plan_id'])
    op.create_index('idx_plan_meals_recipe', 'plan_meals', ['recipe_id'])

def downgrade():
    op.drop_table('plan_meals')
    op.drop_table('daily_plans')
    op.drop_table('weekly_plans')
```

## Implementation Notes

### Backward Compatibility

- Existing `WeeklyPlanner` functionality remains unchanged
- Database persistence is optional (repository can be None)
- API endpoints maintain existing response formats

### Performance Considerations

1. **Lazy Loading**: Use SQLAlchemy lazy loading for relationships to avoid N+1 queries
2. **Batch Inserts**: Insert all meals for a day in a single transaction
3. **Connection Pooling**: Reuse database connections via SQLAlchemy pool
4. **Caching**: Consider Redis cache for frequently accessed plans (today/tomorrow)

### Security Considerations

1. **User Isolation**: Always filter queries by user_id
2. **Input Validation**: Validate all date inputs and day indexes
3. **SQL Injection**: Use parameterized queries (handled by SQLAlchemy)
4. **Authorization**: Verify user owns the plan before modifications

### Scalability

1. **Partitioning**: Consider date-based partitioning for large datasets
2. **Archiving**: Automatically archive plans older than 30 days
3. **Cleanup**: Background job to delete archived plans older than 90 days
4. **Read Replicas**: Use read replicas for retrieval queries

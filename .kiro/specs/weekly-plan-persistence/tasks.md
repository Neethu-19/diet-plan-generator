# Implementation Plan

- [x] 1. Create database models for weekly plan persistence
  - Add WeeklyPlanModel, DailyPlanModel, and PlanMealModel to src/data/models.py
  - Define relationships between models with cascade deletes
  - Add is_archived field for soft deletion support
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 6.1, 7.2_

- [x] 2. Create Alembic migration for weekly plan tables
  - [x] 2.1 Generate new migration file for weekly plan schema
    - Create migration file using alembic revision command
    - Define upgrade() function to create weekly_plans, daily_plans, and plan_meals tables
    - Define downgrade() function to drop tables in reverse order
    - _Requirements: 8.1, 8.2, 8.3, 8.5_

  - [x] 2.2 Add database indexes for query optimization
    - Create composite index on (user_id, start_date) for weekly_plans
    - Create index on is_archived for filtering active plans
    - Create indexes on week_plan_id and date for daily_plans
    - Create indexes on day_plan_id and recipe_id for plan_meals
    - _Requirements: 8.4_

- [x] 3. Implement WeeklyPlanRepository with CRUD operations
  - [x] 3.1 Implement create_weekly_plan method
    - Accept weekly plan dictionary from WeeklyPlanner service
    - Create WeeklyPlanModel instance with metadata
    - Create DailyPlanModel instances for all 7 days
    - Create PlanMealModel instances for all meals
    - Use single transaction for atomicity
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 3.2 Implement retrieval methods
    - Implement get_weekly_plan(week_plan_id) with eager loading
    - Implement get_weekly_plan_by_date(user_id, date) to find plan containing date
    - Implement get_user_weekly_plans(user_id, limit, include_archived) with pagination
    - Implement get_daily_plan(week_plan_id, day_index) for specific day retrieval
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 3.3 Implement today and tomorrow retrieval methods
    - Implement get_today_plan(user_id) using current date
    - Implement get_tomorrow_plan(user_id) using current date + 1 day
    - Handle timezone considerations for date calculations
    - Return None if no active plan exists for the date
    - _Requirements: 2.1, 2.2, 2.5_

  - [x] 3.4 Implement update and deletion methods
    - Implement update_daily_plan(day_plan_id, updated_meals) for day regeneration
    - Implement archive_weekly_plan(week_plan_id) for soft deletion
    - Implement delete_weekly_plan(week_plan_id) for permanent deletion
    - Add validation to prevent deletion of active plans
    - _Requirements: 3.4, 7.1, 7.2, 7.5_

- [x] 4. Enhance WeeklyPlanner service with persistence
  - [x] 4.1 Add repository integration to WeeklyPlanner
    - Add optional db_session parameter to __init__
    - Initialize WeeklyPlanRepository if session provided
    - Maintain backward compatibility when repository is None
    - _Requirements: 1.1_

  - [x] 4.2 Implement generate_and_save_weekly_plan method
    - Call existing generate_weekly_plan method
    - Save result to database using repository.create_weekly_plan
    - Handle database errors gracefully
    - Return the generated plan dictionary
    - _Requirements: 1.1, 1.5_

  - [x] 4.3 Implement regenerate_and_update_day method
    - Load existing weekly plan from database
    - Convert database models to dictionary format
    - Call existing regenerate_day method with loaded plan
    - Update database with regenerated day data
    - Recalculate and update variety score
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 4.4 Add helper methods for model conversion
    - Implement _model_to_dict to convert SQLAlchemy models to dictionaries
    - Implement _dict_to_model for reverse conversion if needed
    - Handle nested relationships (weekly → daily → meals)
    - _Requirements: 2.3, 2.4_

- [x] 5. Update API endpoints for weekly plan persistence
  - [x] 5.1 Update generate-weekly-plan endpoint
    - Add db: Session = Depends(get_db) parameter
    - Pass db_session to WeeklyPlanner constructor
    - Call generate_and_save_weekly_plan instead of generate_weekly_plan
    - Handle database errors with appropriate HTTP status codes
    - _Requirements: 1.1, 1.5_

  - [x] 5.2 Implement get-weekly-plan endpoint
    - Create GET /api/v1/weekly-plan/{week_plan_id} endpoint
    - Use WeeklyPlanRepository to retrieve plan
    - Return 404 if plan not found
    - Convert model to response format
    - _Requirements: 6.1, 6.4_

  - [x] 5.3 Implement today and tomorrow endpoints
    - Create GET /api/v1/weekly-plan/today/{user_id} endpoint
    - Create GET /api/v1/weekly-plan/tomorrow/{user_id} endpoint
    - Return 404 with helpful message if no active plan exists
    - Include nutrition summaries in response
    - _Requirements: 2.1, 2.2, 2.4, 2.5_

  - [x] 5.4 Implement full week view endpoint
    - Create GET /api/v1/weekly-plan/week/{user_id} endpoint
    - Accept optional date parameter (defaults to current date)
    - Return all 7 daily plans with complete meal details
    - Include weekly summary statistics
    - _Requirements: 2.3, 2.4_

  - [x] 5.5 Update regenerate-day endpoint
    - Modify to use regenerate_and_update_day method
    - Remove placeholder 501 response
    - Add proper error handling for database operations
    - Return updated weekly plan
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 5.6 Implement plan management endpoints
    - Create GET /api/v1/weekly-plans/{user_id} for listing user plans
    - Create DELETE /api/v1/weekly-plan/{week_plan_id} with archive_only parameter
    - Add query parameters for pagination and filtering
    - Implement proper authorization checks
    - _Requirements: 6.3, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 6. Add response models for new endpoints
  - Add DailyPlanResponse model to schemas.py
  - Add WeeklyPlanSummary model for list views
  - Add pagination models if needed
  - Update existing models to support database fields
  - _Requirements: 2.1, 2.2, 2.3, 6.3_

- [x] 7. Update UserProfileModel with weekly_plans relationship
  - Add weekly_plans relationship to UserProfileModel in models.py
  - Ensure cascade behavior is appropriate
  - _Requirements: 1.1_

- [ ]* 8. Create integration test for weekly plan persistence
  - [ ]* 8.1 Test complete weekly plan lifecycle
    - Generate weekly plan and verify database storage
    - Retrieve plan by ID and verify all data
    - Query today's plan and verify correct day returned
    - Query tomorrow's plan and verify correct day returned
    - _Requirements: 1.1, 1.5, 2.1, 2.2, 6.1_

  - [ ]* 8.2 Test day regeneration workflow
    - Generate initial weekly plan
    - Regenerate a specific day
    - Verify updated meals in database
    - Verify variety score recalculation
    - Verify other days remain unchanged
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 8.3 Test recipe variety constraints
    - Generate weekly plan with max_recipe_repeats=2
    - Verify no recipe appears more than 2 times
    - Regenerate a day and verify variety constraints still hold
    - Test variety score calculation
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 8.4 Test activity-based macro adjustments
    - Generate plan with varied activity pattern
    - Verify rest day has lower calories and carbs
    - Verify active day has higher calories and carbs
    - Verify protein and fat adjustments are correct
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 8.5 Test plan archiving and deletion
    - Create and archive a weekly plan
    - Verify archived plan not in default queries
    - Retrieve archived plan with include_archived=True
    - Test permanent deletion
    - Verify cascade deletes work correctly
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 9. Create test script for end-to-end weekly plan workflow
  - Create test_weekly_persistence.py script
  - Test plan generation and storage
  - Test retrieval by various methods (ID, date, today, tomorrow)
  - Test day regeneration
  - Test plan listing and filtering
  - Test archiving and deletion
  - _Requirements: 1.1, 2.1, 2.2, 2.3, 3.1, 6.1, 7.1_

- [ ]* 10. Update documentation
  - Update API documentation with new endpoints
  - Add examples for weekly plan persistence
  - Document database schema and relationships
  - Add migration instructions to README
  - _Requirements: All_

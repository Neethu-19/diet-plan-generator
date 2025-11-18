import json

# Load basic recipes
with open('data/basic_recipes.json', 'r') as f:
    existing = json.load(f)

# Load new recipes
with open('data/more_recipes.json', 'r') as f:
    new_recipes = json.load(f)

# Combine
all_recipes = existing + new_recipes

# Save
with open('data/sample_recipes.json', 'w') as f:
    json.dump(all_recipes, f, indent=2)

print(f"✅ Merged {len(existing)} existing + {len(new_recipes)} new = {len(all_recipes)} total recipes")

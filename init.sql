-- Database initialization script for Recipe Collection Application
-- Creates isolated databases for each microservice to enforce the Database-per-Service pattern

-- Create recipes database if not exists
SELECT 'CREATE DATABASE recipes_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'recipes_db')\gexec

-- Create ingredients database if not exists
SELECT 'CREATE DATABASE ingredients_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ingredients_db')\gexec

-- Connect to recipes_db and create tables
\c recipes_db;

CREATE TABLE IF NOT EXISTS recipes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    instructions TEXT NOT NULL,
    prep_time INTEGER NOT NULL DEFAULT 0,  -- In minutes
    cook_time INTEGER NOT NULL DEFAULT 0,  -- In minutes
    servings INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_recipes_category ON recipes(category);
CREATE INDEX IF NOT EXISTS idx_recipes_name ON recipes(name);

-- Seed Initial Dummy Data for Recipes
INSERT INTO recipes (id, name, category, description, instructions, prep_time, cook_time, servings) VALUES
(1, 'Classic Spaghetti Carbonara', 'Italian', 'Authentic Roman carbonara made with guanciale, egg yolks, and Pecorino Romano.', '1. Boil pasta al dente.\n2. Render guanciale until crispy in a pan.\n3. Whisk egg yolks, whole egg, and grated Pecorino.\n4. Toss hot pasta in pan off heat, pour egg mixture and toss vigorously to form a creamy sauce.\n5. Finish with cracked black pepper.', 10, 15, 4),
(2, 'Street-Style Chicken Tacos', 'Mexican', 'Juicy grilled citrus-marinated chicken served on warm corn tortillas with salsa verde and cilantro.', '1. Marinate chicken thighs in lime juice, garlic, cumin, and chili powder.\n2. Grill chicken over medium-high heat until charred and cooked through.\n3. Rest and dice into cubes.\n4. Warm corn tortillas and assemble with diced onion, cilantro, and salsa verde.', 25, 15, 4),
(3, 'Thai Green Chicken Curry', 'Asian', 'Fragrant and creamy green curry with tender chicken, bamboo shoots, and Thai basil.', '1. Fry green curry paste in coconut cream until aromatic.\n2. Add sliced chicken breast and cook until sealed.\n3. Pour in coconut milk, bamboo shoots, fish sauce, and palm sugar.\n4. Simmer for 10 minutes and stir in fresh Thai basil leaves.', 15, 20, 4),
(4, 'Mediterranean Greek Salad', 'Mediterranean', 'Crisp and refreshing salad with vine tomatoes, cucumbers, Kalamata olives, and Greek feta.', '1. Chop ripe tomatoes and cucumbers into chunks.\n2. Thinly slice red onion and toss with Kalamata olives.\n3. Place a whole block of Greek feta on top.\n4. Drizzle with extra virgin olive oil, red wine vinegar, and oregano.', 15, 0, 2),
(5, 'Classic New York Cheesecake', 'Dessert', 'Rich, velvety baked cheesecake with a buttery graham cracker crust.', '1. Mix graham cracker crumbs with melted butter and press into springform pan.\n2. Beat cream cheese with sugar, eggs, vanilla, and sour cream until smooth.\n3. Pour over crust and bake at 325°F in a water bath for 60 minutes.\n4. Cool in oven and chill in refrigerator for 4 hours.', 30, 60, 8),
(6, 'All-American Smash Burgers', 'American', 'Double patty smash burgers with crispy lace edges, melted American cheese, and special sauce.', '1. Portion ground beef into loose balls.\n2. Smash flat onto a screaming hot cast-iron griddle.\n3. Season with salt and pepper; flip after 2 mins and melt cheese on top.\n4. Stack double patties onto toasted brioche buns with pickles and burger sauce.', 15, 10, 4),
(7, 'Spicy Dan Dan Noodles', 'Asian', 'Sichuan street-style wheat noodles coated in a fiery, nutty sesame-chili sauce topped with pork.', '1. Fry minced pork with Shaoxing wine and sweet bean paste.\n2. Whisk Sichuan chili oil, sesame paste, soy sauce, and Chinkiang vinegar in serving bowls.\n3. Boil fresh noodles, drain, and transfer into sauce bowls with noodle broth.\n4. Top with seasoned pork, crushed roasted peanuts, and scallions.', 15, 15, 3),
(8, 'Classic French Chocolate Mousse', 'Dessert', 'Airy, dark chocolate mousse made with rich 70% bittersweet chocolate and whipped cream.', '1. Melt dark chocolate and butter over a gentle water bath.\n2. Whisk egg yolks into the cooled chocolate.\n3. Whip egg whites with sugar until stiff peaks form.\n4. Gently fold egg whites into chocolate mixture.\n5. Spoon into ramekins and refrigerate for 4 hours.', 25, 5, 6)
ON CONFLICT (id) DO NOTHING;

SELECT setval('recipes_id_seq', (SELECT MAX(id) FROM recipes));

-- Connect to ingredients_db and create tables
\c ingredients_db;

CREATE TABLE IF NOT EXISTS ingredients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    quantity NUMERIC(10, 2) NOT NULL DEFAULT 1.00,
    recipe_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ingredients_recipe_id ON ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_ingredients_name ON ingredients(name);

-- Seed Initial Dummy Data for Ingredients
INSERT INTO ingredients (id, name, unit, quantity, recipe_id) VALUES
-- Recipe 1: Carbonara
(1, 'Spaghetti', 'grams', 400.00, 1),
(2, 'Guanciale or Pancetta', 'grams', 150.00, 1),
(3, 'Egg yolks', 'pieces', 4.00, 1),
(4, 'Whole egg', 'piece', 1.00, 1),
(5, 'Pecorino Romano cheese', 'grams', 80.00, 1),
(6, 'Coarsely ground black pepper', 'tablespoon', 1.00, 1),
-- Recipe 2: Chicken Tacos
(7, 'Boneless chicken thighs', 'grams', 700.00, 2),
(8, 'Corn tortillas', 'pieces', 12.00, 2),
(9, 'Limes', 'pieces', 3.00, 2),
(10, 'Fresh cilantro', 'bunch', 1.00, 2),
(11, 'White onion', 'medium', 1.00, 2),
(12, 'Salsa verde', 'ml', 150.00, 2),
-- Recipe 3: Thai Green Curry
(13, 'Chicken breast', 'grams', 500.00, 3),
(14, 'Coconut milk', 'ml', 400.00, 3),
(15, 'Thai green curry paste', 'tablespoons', 3.00, 3),
(16, 'Bamboo shoots', 'grams', 100.00, 3),
(17, 'Thai basil leaves', 'cup', 1.00, 3),
(18, 'Fish sauce', 'tablespoons', 2.00, 3),
-- Recipe 4: Greek Salad
(19, 'Ripe vine tomatoes', 'pieces', 4.00, 4),
(20, 'English cucumber', 'piece', 1.00, 4),
(21, 'Kalamata olives', 'grams', 100.00, 4),
(22, 'Greek Feta cheese block', 'grams', 200.00, 4),
(23, 'Extra virgin olive oil', 'tablespoons', 4.00, 4),
(24, 'Dried oregano', 'tablespoon', 1.00, 4),
-- Recipe 5: Cheesecake
(25, 'Cream cheese (softened)', 'grams', 680.00, 5),
(26, 'Graham cracker crumbs', 'grams', 150.00, 5),
(27, 'Granulated sugar', 'grams', 200.00, 5),
(28, 'Large eggs', 'pieces', 3.00, 5),
(29, 'Sour cream', 'ml', 120.00, 5),
-- Recipe 6: Smash Burgers
(30, 'Ground beef (80/20)', 'grams', 450.00, 6),
(31, 'Brioche burger buns', 'pieces', 4.00, 6),
(32, 'American cheese slices', 'slices', 8.00, 6),
(33, 'Dill pickle chips', 'slices', 12.00, 6),
(34, 'Burger sauce', 'tablespoons', 4.00, 6),
-- Recipe 7: Dan Dan Noodles
(35, 'Fresh wheat noodles', 'grams', 300.00, 7),
(37, 'Sichuan chili oil', 'tablespoons', 3.00, 7),
(38, 'Chinese sesame paste', 'tablespoons', 2.00, 7),
(39, 'Roasted peanuts', 'grams', 30.00, 7),
-- Recipe 8: Chocolate Mousse
(40, 'Bittersweet chocolate (70%)', 'grams', 200.00, 8),
(41, 'Unsalted butter', 'grams', 30.00, 8),
(42, 'Large eggs (separated)', 'pieces', 4.00, 8),
(43, 'Heavy whipping cream', 'ml', 100.00, 8)
ON CONFLICT (id) DO NOTHING;

SELECT setval('ingredients_id_seq', (SELECT MAX(id) FROM ingredients));

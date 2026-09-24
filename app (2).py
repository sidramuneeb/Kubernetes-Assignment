import logging
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flasgger import Swagger
from sqlalchemy import text

from config import Config
from models import db, Recipe

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("recipes-service")

# Initialize Flask app
app = Flask(__name__, static_folder="static")
app.config.from_object(Config)

db.init_app(app)
CORS(app)
Swagger(app)

# Auto-create tables on startup if not already created
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        logger.warning(f"Database init warning: {e}")


# --- Web UI ---
@app.route("/")
@app.route("/dashboard")
def index():
    return send_from_directory(app.static_folder, "index.html")


# --- Health Check (Kubernetes Probes) ---
@app.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "healthy", "service": Config.SERVICE_NAME}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


# --- Recipes REST API ---
@app.route("/api/recipes", methods=["GET"])
def get_recipes():
    """List all recipes with optional filtering by category or search term."""
    category = request.args.get("category")
    search = request.args.get("search")
    limit = min(int(request.args.get("limit", 20)), 100)
    offset = int(request.args.get("offset", 0))

    query = Recipe.query
    if category:
        query = query.filter(Recipe.category.ilike(f"%{category.strip()}%"))
    if search:
        term = f"%{search.strip()}%"
        query = query.filter((Recipe.name.ilike(term)) | (Recipe.description.ilike(term)))

    total = query.count()
    recipes = query.order_by(Recipe.id.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "total": total,
        "recipes": [r.to_dict() for r in recipes]
    }), 200


@app.route("/api/recipes/<int:recipe_id>", methods=["GET"])
def get_recipe(recipe_id):
    """Get a single recipe with ingredients fetched from the Ingredients microservice."""
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        return jsonify({"error": f"Recipe {recipe_id} not found"}), 404

    # Inter-service call: fetch ingredients for this recipe unless explicitly disabled
    include_ingredients = request.args.get("include_ingredients", "true").lower() in ("true", "1", "yes")
    ingredients = []
    if include_ingredients:
        try:
            url = f"{Config.INGREDIENTS_SERVICE_URL}/api/ingredients?recipe_id={recipe_id}"
            resp = requests.get(url, timeout=Config.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                ingredients = resp.json().get("ingredients", [])
        except Exception as e:
            logger.warning(f"Could not reach ingredients service: {e}")

    return jsonify(recipe.to_dict(include_ingredients=include_ingredients, ingredients=ingredients)), 200


@app.route("/api/recipes", methods=["POST"])
def create_recipe():
    """Create a new recipe."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    category = data.get("category", "").strip()
    instructions = data.get("instructions", "").strip()

    if not name or not category or not instructions:
        return jsonify({"error": "name, category, and instructions are required"}), 400

    recipe = Recipe(
        name=name,
        category=category,
        description=data.get("description", "").strip(),
        instructions=instructions,
        prep_time=int(data.get("prep_time", 0)),
        cook_time=int(data.get("cook_time", 0)),
        servings=int(data.get("servings", 1))
    )

    db.session.add(recipe)
    db.session.commit()
    return jsonify({"message": "Recipe created", "recipe": recipe.to_dict()}), 201


@app.route("/api/recipes/<int:recipe_id>", methods=["PUT"])
def update_recipe(recipe_id):
    """Update an existing recipe."""
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        return jsonify({"error": f"Recipe {recipe_id} not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        recipe.name = data["name"].strip()
    if "category" in data:
        recipe.category = data["category"].strip()
    if "description" in data:
        recipe.description = data["description"].strip()
    if "instructions" in data:
        recipe.instructions = data["instructions"].strip()
    if "prep_time" in data:
        recipe.prep_time = int(data["prep_time"])
    if "cook_time" in data:
        recipe.cook_time = int(data["cook_time"])
    if "servings" in data:
        recipe.servings = int(data["servings"])

    db.session.commit()
    return jsonify({"message": "Recipe updated", "recipe": recipe.to_dict()}), 200


@app.route("/api/recipes/<int:recipe_id>", methods=["DELETE"])
def delete_recipe(recipe_id):
    """Delete a recipe and tell the ingredients microservice to delete its ingredients."""
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        return jsonify({"error": f"Recipe {recipe_id} not found"}), 404

    db.session.delete(recipe)
    db.session.commit()

    # Cascade deletion to ingredients service
    try:
        url = f"{Config.INGREDIENTS_SERVICE_URL}/api/ingredients/by-recipe/{recipe_id}"
        requests.delete(url, timeout=Config.REQUEST_TIMEOUT)
    except Exception as e:
        logger.warning(f"Failed to cascade delete ingredients: {e}")

    return jsonify({"message": f"Recipe {recipe_id} deleted"}), 200


# --- Reverse-Proxy Helpers for UI ---
@app.route("/api/ingredients", methods=["GET", "POST"])
def proxy_ingredients():
    url = f"{Config.INGREDIENTS_SERVICE_URL}/api/ingredients"
    try:
        if request.method == "POST":
            res = requests.post(url, json=request.get_json(silent=True), timeout=Config.REQUEST_TIMEOUT)
        else:
            res = requests.get(url, params=request.args, timeout=Config.REQUEST_TIMEOUT)
        return (res.content, res.status_code, [("Content-Type", "application/json")])
    except Exception as e:
        return jsonify({"error": "Ingredients service unreachable", "details": str(e)}), 503


@app.route("/api/ingredients/<int:ingredient_id>", methods=["DELETE"])
def proxy_delete_ingredient(ingredient_id):
    url = f"{Config.INGREDIENTS_SERVICE_URL}/api/ingredients/{ingredient_id}"
    try:
        res = requests.delete(url, timeout=Config.REQUEST_TIMEOUT)
        return (res.content, res.status_code, [("Content-Type", "application/json")])
    except Exception as e:
        return jsonify({"error": "Ingredients service unreachable", "details": str(e)}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)

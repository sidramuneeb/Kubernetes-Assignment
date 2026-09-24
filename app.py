import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from flasgger import Swagger
from sqlalchemy import text

from config import Config
from models import db, Ingredient

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingredients-service")

# Initialize Flask app
app = Flask(__name__)
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


# --- Health Check (Kubernetes Probes) ---
@app.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "healthy", "service": Config.SERVICE_NAME}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


# --- Ingredients REST API ---
@app.route("/api/ingredients", methods=["GET"])
def get_ingredients():
    """List ingredients with optional filtering by recipe_id or search keyword."""
    recipe_id = request.args.get("recipe_id")
    search = request.args.get("search")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))

    query = Ingredient.query
    if recipe_id:
        try:
            query = query.filter(Ingredient.recipe_id == int(recipe_id))
        except ValueError:
            return jsonify({"error": "recipe_id must be an integer"}), 400

    if search:
        query = query.filter(Ingredient.name.ilike(f"%{search.strip()}%"))

    total = query.count()
    ingredients = query.order_by(Ingredient.id.asc()).offset(offset).limit(limit).all()

    return jsonify({
        "total": total,
        "ingredients": [i.to_dict() for i in ingredients]
    }), 200


@app.route("/api/ingredients/<int:ingredient_id>", methods=["GET"])
def get_ingredient(ingredient_id):
    """Get a single ingredient by ID."""
    ingredient = Ingredient.query.get(ingredient_id)
    if not ingredient:
        return jsonify({"error": f"Ingredient {ingredient_id} not found"}), 404
    return jsonify(ingredient.to_dict()), 200


@app.route("/api/ingredients", methods=["POST"])
def create_ingredient():
    """Create a new ingredient, validating that the target recipe exists in the Recipes service."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    unit = data.get("unit", "").strip()
    quantity = data.get("quantity")
    recipe_id = data.get("recipe_id")

    if not name or not unit or quantity is None or recipe_id is None:
        return jsonify({"error": "name, unit, quantity, and recipe_id are required"}), 400

    try:
        quantity = float(quantity)
        recipe_id = int(recipe_id)
    except (ValueError, TypeError):
        return jsonify({"error": "quantity must be a number and recipe_id an integer"}), 400

    # Inter-service call: check if recipe exists in recipes-service (skip fetching ingredients to prevent circular HTTP calls)
    try:
        url = f"{Config.RECIPES_SERVICE_URL}/api/recipes/{recipe_id}?include_ingredients=false"
        resp = requests.get(url, timeout=Config.REQUEST_TIMEOUT)
        if resp.status_code == 404:
            return jsonify({"error": f"Recipe {recipe_id} does not exist"}), 400
    except Exception as e:
        logger.warning(f"Could not reach recipes service for validation: {e}")

    ingredient = Ingredient(name=name, unit=unit, quantity=quantity, recipe_id=recipe_id)
    db.session.add(ingredient)
    db.session.commit()

    return jsonify({"message": "Ingredient created", "ingredient": ingredient.to_dict()}), 201


@app.route("/api/ingredients/<int:ingredient_id>", methods=["PUT"])
def update_ingredient(ingredient_id):
    """Update an existing ingredient."""
    ingredient = Ingredient.query.get(ingredient_id)
    if not ingredient:
        return jsonify({"error": f"Ingredient {ingredient_id} not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        ingredient.name = data["name"].strip()
    if "unit" in data:
        ingredient.unit = data["unit"].strip()
    if "quantity" in data:
        ingredient.quantity = float(data["quantity"])
    if "recipe_id" in data:
        ingredient.recipe_id = int(data["recipe_id"])

    db.session.commit()
    return jsonify({"message": "Ingredient updated", "ingredient": ingredient.to_dict()}), 200


@app.route("/api/ingredients/<int:ingredient_id>", methods=["DELETE"])
def delete_ingredient(ingredient_id):
    """Delete a single ingredient."""
    ingredient = Ingredient.query.get(ingredient_id)
    if not ingredient:
        return jsonify({"error": f"Ingredient {ingredient_id} not found"}), 404

    db.session.delete(ingredient)
    db.session.commit()
    return jsonify({"message": f"Ingredient {ingredient_id} deleted"}), 200


@app.route("/api/ingredients/by-recipe/<int:recipe_id>", methods=["DELETE"])
def delete_ingredients_by_recipe(recipe_id):
    """Delete all ingredients for a specific recipe (cascade helper)."""
    count = Ingredient.query.filter(Ingredient.recipe_id == recipe_id).delete()
    db.session.commit()
    return jsonify({"message": f"Deleted {count} ingredients for recipe {recipe_id}"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Ingredient(db.Model):
    __tablename__ = "ingredients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    recipe_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "unit": self.unit,
            "quantity": float(self.quantity),
            "recipe_id": self.recipe_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

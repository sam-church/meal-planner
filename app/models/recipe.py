from app.database import db

class Recipe(db.Model):
    __tablename__ = 'recipes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    source_url = db.Column(db.Text)
    source_api_id = db.Column(db.Text)
    base_servings = db.Column(db.Integer, nullable=False, default=2)
    ingredients = db.Column(db.JSON, default=list)
    cook_method = db.Column(db.JSON, default=list)
    prep_time_mins = db.Column(db.Integer)
    cook_time_mins = db.Column(db.Integer)
    makes_leftovers = db.Column(db.Boolean, default=False)
    nutrition = db.Column(db.JSON)
    tags = db.Column(db.JSON, default=list)
    notes = db.Column(db.Text)
    last_used_date = db.Column(db.Date)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'source_url': self.source_url,
            'source_api_id': self.source_api_id,
            'base_servings': self.base_servings,
            'ingredients': self.ingredients or [],
            'cook_method': self.cook_method or [],
            'prep_time_mins': self.prep_time_mins,
            'cook_time_mins': self.cook_time_mins,
            'makes_leftovers': self.makes_leftovers,
            'nutrition': self.nutrition,
            'tags': self.tags or [],
            'notes': self.notes,
            'last_used_date': self.last_used_date.isoformat() if self.last_used_date else None,
        }

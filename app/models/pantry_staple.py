from app.database import db

class PantryStaple(db.Model):
    __tablename__ = 'pantry_staples'
    id = db.Column(db.Integer, primary_key=True)
    ingredient_name = db.Column(db.Text, nullable=False, unique=True)
    category = db.Column(db.Text, default='other')

    def to_dict(self):
        return {'id': self.id, 'ingredient_name': self.ingredient_name, 'category': self.category}

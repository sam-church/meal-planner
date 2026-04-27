from app.database import db

class ShoppingList(db.Model):
    __tablename__ = 'shopping_lists'
    id = db.Column(db.Integer, primary_key=True)
    week_plan_id = db.Column(db.Integer, db.ForeignKey('week_plans.id'), nullable=False)
    items = db.Column(db.JSON, default=dict)
    generated_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'week_plan_id': self.week_plan_id,
            'items': self.items or {},
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
        }

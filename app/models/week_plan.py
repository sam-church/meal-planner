from app.database import db

class WeekPlan(db.Model):
    __tablename__ = 'week_plans'
    id = db.Column(db.Integer, primary_key=True)
    week_start_date = db.Column(db.Date, nullable=False)
    slots = db.Column(db.JSON, default=dict)
    calendar_synced = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'week_start_date': self.week_start_date.isoformat() if self.week_start_date else None,
            'slots': self.slots or {},
            'calendar_synced': self.calendar_synced,
            'notes': self.notes,
        }

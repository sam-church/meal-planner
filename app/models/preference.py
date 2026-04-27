from app.database import db

class Preference(db.Model):
    __tablename__ = 'preferences'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Text, nullable=False)
    value = db.Column(db.Text, nullable=False)
    scope = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'type': self.type, 'value': self.value, 'scope': self.scope}

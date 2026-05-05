import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DATA_DIR, 'meal_planner.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

LUNCH_START = "11:30"
DINNER_START = "18:00"
SUNDAY_PREP_START = "14:00"
CALENDAR_NAME = "Triple F"
CALENDAR_TIMEZONE = "America/New_York"
SPOONACULAR_API_KEY = os.environ.get("SPOONACULAR_API_KEY", "")

SLOT_KEYS = [
    'mon_lunch', 'mon_dinner',
    'tue_lunch', 'tue_dinner',
    'wed_lunch', 'wed_dinner',
    'thu_lunch', 'thu_dinner',
    'fri_lunch', 'fri_dinner',
    'sunday_prep',
]

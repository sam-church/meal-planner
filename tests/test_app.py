def test_app_creates(app):
    assert app is not None

def test_db_tables_exist(app):
    with app.app_context():
        from app.database import db
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        assert 'recipes' in tables
        assert 'week_plans' in tables
        assert 'shopping_lists' in tables
        assert 'pantry_staples' in tables
        assert 'preferences' in tables

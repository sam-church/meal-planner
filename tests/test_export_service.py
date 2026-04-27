from datetime import date
from app.services.export_service import render_markdown


class MockWeekPlan:
    def __init__(self, week_start_date):
        self.week_start_date = week_start_date


class MockShoppingList:
    def __init__(self, items):
        self.items = items


def test_render_markdown_basic():
    wp = MockWeekPlan(date(2026, 4, 28))
    sl = MockShoppingList({
        'chicken breast': {'quantity': 1.5, 'unit': 'lbs', 'category': 'protein', 'checked': False, 'is_staple': False},
        'spinach': {'quantity': 2.0, 'unit': 'cups', 'category': 'produce', 'checked': False, 'is_staple': False},
    })
    result = render_markdown(sl, wp)
    assert '# Shopping List — Week of Apr 28, 2026' in result
    assert '## Produce' in result
    assert '## Protein' in result
    assert '- [ ] spinach — 2.0 cups' in result
    assert '- [ ] chicken breast — 1.5 lbs' in result
    # Produce should appear before Protein
    assert result.index('## Produce') < result.index('## Protein')


def test_render_markdown_empty():
    wp = MockWeekPlan(date(2026, 4, 28))
    sl = MockShoppingList({})
    result = render_markdown(sl, wp)
    assert '# Shopping List' in result
    assert '## Produce' not in result

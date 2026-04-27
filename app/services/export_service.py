CATEGORY_ORDER = ['produce', 'protein', 'dairy', 'pantry', 'other']


def render_markdown(shopping_list, week_plan):
    """Return Obsidian-ready markdown shopping list string."""
    week_start = week_plan.week_start_date
    if hasattr(week_start, 'strftime'):
        date_str = week_start.strftime('%b %-d, %Y')
    else:
        date_str = str(week_start)

    lines = [f'# Shopping List — Week of {date_str}', '']
    items = shopping_list.items or {}

    by_category = {}
    for name, data in items.items():
        cat = data.get('category', 'other') or 'other'
        by_category.setdefault(cat, []).append((name, data))

    all_cats = list(CATEGORY_ORDER)
    for cat in by_category:
        if cat not in all_cats:
            all_cats.append(cat)

    for cat in all_cats:
        if cat not in by_category:
            continue
        lines.append(f'## {cat.capitalize()}')
        for name, data in sorted(by_category[cat]):
            qty = data.get('quantity', '')
            unit = data.get('unit', '') or ''
            if qty and unit:
                lines.append(f'- [ ] {name} — {float(qty):.1f} {unit}')
            elif qty:
                lines.append(f'- [ ] {name} — {float(qty):.1f}')
            else:
                lines.append(f'- [ ] {name}')
        lines.append('')

    return '\n'.join(lines)

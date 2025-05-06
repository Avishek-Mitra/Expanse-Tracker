def get_color(category):
    """Return a color for a given category."""
    colors = {
        'Food': '#84cc16',
        'Transportation': '#3b82f6',
        'Entertainment': '#8b5cf6',
        'Utilities': '#f97316',
        'Housing': '#ef4444',
        'Healthcare': '#06b6d4',
        'Personal': '#ec4899',
        'Education': '#14b8a6',
        'Other': '#6b7280',
    }
    return colors.get(category, '#6b7280')
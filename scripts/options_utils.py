"""
Shared utilities for options-related calculations.
"""


def determine_strike_increment(price):
    """Determine strike increment based on underlying price."""
    if price < 50:
        return 2.5
    if price < 200:
        return 5.0
    return 10.0


def round_to_increment(price, increment):
    """Round price to nearest strike increment."""
    if increment <= 0:
        return price
    return round(round(price / increment) * increment, 2)

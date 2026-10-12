"""Explicit approval of the real review, only for disposable test data."""
from colegio.restore import preview_restore, restore


def approved_restore(backup,directory):
    review=preview_restore(backup,directory)
    return restore(backup,directory,preview_hash=review['preview_hash'],confirmation=review['confirmation'],
                   emergency_floors=review['floors'] if review['requires_floor_review'] else None)

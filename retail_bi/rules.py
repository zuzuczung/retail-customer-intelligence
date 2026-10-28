"""Pure business rules shared with independent source controls."""
from decimal import Decimal
import re

PRODUCT_CODE = re.compile(r'^[0-9]{5}[A-Za-z]*$')


def classify(invoice, stock, quantity, price):
    if not PRODUCT_CODE.fullmatch(str(stock)):
        return 'non_merchandise'
    if price <= 0:
        return 'invalid_price'
    if quantity > 0 and not str(invoice).upper().startswith('C'):
        return 'sale'
    if quantity < 0:
        return 'negative_adjustment'
    return 'other'


def rfm_scores(recency, frequency, monetary):
    r = 5 if recency <= 30 else 4 if recency <= 60 else 3 if recency <= 90 else 2 if recency <= 180 else 1
    f = 5 if frequency >= 10 else 4 if frequency >= 6 else 3 if frequency >= 3 else 2 if frequency >= 2 else 1
    m = 5 if monetary >= Decimal('5000') else 4 if monetary >= Decimal('2000') else 3 if monetary >= Decimal('1000') else 2 if monetary >= Decimal('500') else 1
    return r, f, m

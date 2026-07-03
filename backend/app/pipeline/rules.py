"""Rule-based categorization dictionary.

An ordered list of keyword/regex rules mapping cleaned descriptions to canonical categories.
Order encodes **precedence**: the first matching rule wins, so more specific rules (e.g.
"AMAZON PRIME" → Subscriptions) are placed before broader ones ("AMAZON" → Shopping). Patterns
use word boundaries to avoid substring false positives (e.g. "RENT" must not match "RENTAL").

These rules are India-centric and intentionally fast/free — they handle the bulk of real
statements before the optional LLM fallback (Phase 9) touches anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.constants import CANONICAL_CATEGORY_SET
from app.models.schemas import Direction


@dataclass(frozen=True)
class Rule:
    pattern: re.Pattern[str]
    category: str
    confidence: float
    direction: Optional[Direction] = None  # if set, only matches this transaction direction


def _r(keywords: str, category: str, confidence: float = 0.9, direction: Optional[Direction] = None) -> Rule:
    """Build a case-insensitive, word-boundary rule from a regex alternation string."""
    return Rule(re.compile(rf"\b(?:{keywords})\b", re.IGNORECASE), category, confidence, direction)


# Ordered most-specific → most-general. First match wins.
RULES: list[Rule] = [
    # --- Subscriptions (brand-specific; must precede Shopping for AMAZON PRIME) ---
    _r(r"NETFLIX|HOTSTAR|DISNEY|SPOTIFY|GAANA|JIOSAAVN|SONYLIV|ZEE5|VOOT|AUDIBLE|"
       r"YOUTUBE\s+PREMIUM|AMAZON\s+PRIME|PRIME\s+VIDEO|APPLE\.COM/BILL|SUBSCRIPTION",
       "Subscriptions", 0.95),

    # --- EMI / loans (note: the word "EMI" is often stripped during cleaning, so match LOAN) ---
    _r(r"EMI|LOAN|HOME\s+LOAN|CAR\s+LOAN|PERSONAL\s+LOAN|BAJAJ\s+FIN|NACH",
       "EMI", 0.9),

    # --- Rent (word boundary keeps "RENTAL" out) ---
    _r(r"RENT|HOUSE\s+RENT", "Rent", 0.9),

    # --- Investments ---
    _r(r"SIP|MUTUAL\s+FUND|ZERODHA|GROWW|UPSTOX|KUVERA|SMALLCASE|NPS|PPF|ELSS|"
       r"COIN|INDMONEY|BROKING",
       "Investments", 0.9),

    # --- Salary (income — credits only) ---
    _r(r"SALARY|PAYROLL|STIPEND", "Salary", 0.95, direction="credit"),

    # --- Food (incl. groceries & quick-commerce) ---
    _r(r"SWIGGY|ZOMATO|RESTAURANT|DOMINOS|MCDONALD|KFC|PIZZA|BURGER|CAFE|STARBUCKS|"
       r"FRESHMENU|EATCLUB|BIGBASKET|BLINKIT|ZEPTO|GROFERS|DUNZO|INSTAMART",
       "Food", 0.9),

    # --- Travel (cabs, trains, flights, fuel, tolls) ---
    _r(r"UBER|OLA|RAPIDO|IRCTC|REDBUS|MAKEMYTRIP|GOIBIBO|YATRA|INDIGO|VISTARA|"
       r"AIR\s*INDIA|SPICEJET|FUEL|PETROL|DIESEL|INDIAN\s+OIL|BHARAT\s+PETROLEUM|"
       r"HPCL|IOCL|FASTAG|TOLL|METRO|PARKING|OLACABS",
       "Travel", 0.9),

    # --- Bills & utilities (incl. insurance & telecom) ---
    _r(r"ELECTRICITY|BESCOM|BSES|TATA\s+POWER|ADANI\s+ELECTRICITY|RECHARGE|AIRTEL|"
       r"JIO|VODAFONE|\bVI\b|BSNL|BROADBAND|DTH|GAS\s+BILL|WATER\s+BILL|POSTPAID|"
       r"PREPAID|INSURANCE|\bLIC\b|PREMIUM|UTILITY",
       "Bills", 0.85),

    # --- Shopping (general retail / e-commerce) ---
    _r(r"AMAZON|FLIPKART|MYNTRA|AJIO|MEESHO|NYKAA|RELIANCE\s+DIGITAL|CROMA|IKEA|"
       r"DECATHLON|LIFESTYLE|SHOPPERS\s+STOP|TATA\s+CLIQ|SNAPDEAL|DMART|RELIANCE\s+TRENDS",
       "Shopping", 0.85),
]


def match_category(description_clean: str, direction: Direction) -> Optional[tuple[str, float]]:
    """Return (category, confidence) for the first matching rule, or None if none match."""
    if not description_clean:
        return None
    for rule in RULES:
        if rule.direction is not None and rule.direction != direction:
            continue
        if rule.pattern.search(description_clean):
            return rule.category, rule.confidence
    return None


def _assert_rules_canonical() -> None:
    """Guard: every rule must map to a canonical category (fails fast at import time)."""
    for rule in RULES:
        if rule.category not in CANONICAL_CATEGORY_SET:
            raise ValueError(f"Rule maps to non-canonical category: {rule.category!r}")


_assert_rules_canonical()

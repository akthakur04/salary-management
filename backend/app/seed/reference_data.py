"""ACME's job architecture, reference FX rates and pay bands for the demo data set.

Figures are synthetic but internally consistent: bands are a family's US midpoint,
scaled by level and by a country pay factor, then converted to local currency at
the reference rate. Two India bands are pinned to the figures in the UI design so
the demo scenario ("promote Ravi Kumar to L4 with a 12% raise") lands below the
new band, as designed.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.bands import PayBand
from app.domain.components import ComponentType
from app.domain.money import Money, round_half_even
from app.domain.role_defaults import RoleDefaultComponent

RATE_SET = "2026-reference"


@dataclass(frozen=True, slots=True)
class CountrySpec:
    code: str
    name: str
    currency: str
    usd_per_unit: Decimal
    pay_factor: Decimal
    headcount_weight: int


COUNTRIES = (
    CountrySpec("US", "United States", "USD", Decimal("1"), Decimal("1.00"), 2140),
    CountrySpec("IN", "India", "INR", Decimal("0.012"), Decimal("0.25"), 2592),
    CountrySpec("GB", "United Kingdom", "GBP", Decimal("1.27"), Decimal("0.68"), 1120),
    CountrySpec("BR", "Brazil", "BRL", Decimal("0.18"), Decimal("0.27"), 1060),
    CountrySpec("DE", "Germany", "EUR", Decimal("1.08"), Decimal("0.72"), 980),
    CountrySpec("CA", "Canada", "CAD", Decimal("0.73"), Decimal("0.78"), 610),
    CountrySpec("AU", "Australia", "AUD", Decimal("0.65"), Decimal("0.75"), 540),
    CountrySpec("SG", "Singapore", "SGD", Decimal("0.74"), Decimal("0.62"), 470),
)


@dataclass(frozen=True, slots=True)
class FamilySpec:
    name: str
    department: str
    us_l3_midpoint: int
    commissioned: bool = False


DEPARTMENT_WEIGHTS = {
    "Engineering": 34,
    "Sales": 16,
    "Customer Support": 15,
    "Marketing": 8,
    "Data": 7,
    "Product": 6,
    "Finance": 5,
    "People": 4,
}

FAMILIES = (
    FamilySpec("Software Engineer", "Engineering", 130_000),
    FamilySpec("QA Engineer", "Engineering", 105_000),
    FamilySpec("DevOps Engineer", "Engineering", 125_000),
    FamilySpec("Security Engineer", "Engineering", 135_000),
    FamilySpec("Mobile Engineer", "Engineering", 125_000),
    FamilySpec("Engineering Manager", "Engineering", 150_000),
    FamilySpec("Product Manager", "Product", 135_000),
    FamilySpec("Product Designer", "Product", 115_000),
    FamilySpec("UX Researcher", "Product", 110_000),
    FamilySpec("Data Analyst", "Data", 100_000),
    FamilySpec("Data Engineer", "Data", 125_000),
    FamilySpec("Data Scientist", "Data", 135_000),
    FamilySpec("Account Executive", "Sales", 85_000, commissioned=True),
    FamilySpec("Sales Development Rep", "Sales", 60_000, commissioned=True),
    FamilySpec("Sales Manager", "Sales", 110_000, commissioned=True),
    FamilySpec("Solutions Engineer", "Sales", 120_000),
    FamilySpec("Support Specialist", "Customer Support", 55_000),
    FamilySpec("Customer Success Manager", "Customer Support", 80_000),
    FamilySpec("Marketing Manager", "Marketing", 105_000),
    FamilySpec("Content Strategist", "Marketing", 85_000),
    FamilySpec("Growth Marketer", "Marketing", 95_000),
    FamilySpec("Financial Analyst", "Finance", 95_000),
    FamilySpec("Accountant", "Finance", 85_000),
    FamilySpec("HR Business Partner", "People", 95_000),
    FamilySpec("Recruiter", "People", 80_000),
)

LEVELS = (1, 2, 3, 4, 5)
LEVEL_WEIGHTS = (23, 29, 24, 16, 8)
LEVEL_MULTIPLIER = {
    1: Decimal("0.60"),
    2: Decimal("0.80"),
    3: Decimal("1.00"),
    4: Decimal("1.25"),
    5: Decimal("1.55"),
}
BAND_SPREAD = Decimal("0.18")
BONUS_PERCENT_BY_LEVEL = {3: Decimal("10"), 4: Decimal("15"), 5: Decimal("20")}
COMMISSION_PERCENT_BY_LEVEL = {
    1: Decimal("30"),
    2: Decimal("35"),
    3: Decimal("40"),
    4: Decimal("45"),
    5: Decimal("50"),
}

_PINNED_BANDS_INR = {
    ("Software Engineer", 3): (22_00_000, 27_00_000, 32_00_000),
    ("Software Engineer", 4): (28_00_000, 33_00_000, 38_00_000),
}


def role_defaults(family: FamilySpec, level: int) -> tuple[RoleDefaultComponent, ...]:
    """Sales roles carry commission at every level; others get a bonus from L3."""
    if family.commissioned:
        return (
            RoleDefaultComponent(
                ComponentType.COMMISSION, COMMISSION_PERCENT_BY_LEVEL[level], "Sales commission"
            ),
        )
    if level in BONUS_PERCENT_BY_LEVEL:
        return (
            RoleDefaultComponent(
                ComponentType.BONUS, BONUS_PERCENT_BY_LEVEL[level], "Annual bonus"
            ),
        )
    return ()


def pay_band(family: FamilySpec, level: int, country: CountrySpec) -> PayBand:
    if country.code == "IN" and (family.name, level) in _PINNED_BANDS_INR:
        minimum, midpoint, maximum = _PINNED_BANDS_INR[(family.name, level)]
        return PayBand(_local(minimum, "INR"), _local(midpoint, "INR"), _local(maximum, "INR"))

    usd_midpoint = family.us_l3_midpoint * LEVEL_MULTIPLIER[level] * country.pay_factor
    local_midpoint = usd_midpoint / country.usd_per_unit
    return PayBand(
        _local_rounded(local_midpoint * (1 - BAND_SPREAD), country.currency),
        _local_rounded(local_midpoint, country.currency),
        _local_rounded(local_midpoint * (1 + BAND_SPREAD), country.currency),
    )


def round_to_thousand(local_units: Decimal) -> int:
    """Whole thousands of local currency, as pay is usually quoted."""
    return round_half_even(local_units / 1000) * 1000


def _local(units: int, currency: str) -> Money:
    return Money(units * 100, currency)


def _local_rounded(local_units: Decimal, currency: str) -> Money:
    return _local(round_to_thousand(local_units), currency)

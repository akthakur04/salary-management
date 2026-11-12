"""Business-rule violations raised by the domain.

Each error has a stable `code` that the API returns to clients, and keyword
`details` that say which values broke the rule. The API layer maps them to
HTTP statuses, so the domain stays free of HTTP concerns.
"""

from typing import ClassVar


class DomainError(Exception):
    code: ClassVar[str] = "DOMAIN_RULE_VIOLATED"

    def __init__(self, message: str, **details: object) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class InvalidAmountError(DomainError):
    code = "INVALID_AMOUNT"


class InvalidCurrencyError(DomainError):
    code = "INVALID_CURRENCY"


class CurrencyMismatchError(DomainError):
    code = "CURRENCY_MISMATCH"


class CurrencyCountryMismatchError(DomainError):
    code = "CURRENCY_COUNTRY_MISMATCH"


class InvalidPercentageError(DomainError):
    code = "INVALID_PERCENTAGE"


class InvalidComponentError(DomainError):
    code = "INVALID_COMPONENT"


class MissingPayoutDateError(DomainError):
    code = "MISSING_PAYOUT_DATE"


class InvalidPayBandError(DomainError):
    code = "INVALID_PAY_BAND"


class InvalidFteError(DomainError):
    code = "INVALID_FTE"


class MissingFxRateError(DomainError):
    code = "MISSING_FX_RATE"


class InvalidFxRateError(DomainError):
    code = "INVALID_FX_RATE"


class InvalidEffectivePeriodError(DomainError):
    code = "INVALID_EFFECTIVE_PERIOD"


class OverlappingVersionError(DomainError):
    code = "OVERLAPPING_VERSION"


class InvalidChangeReasonError(DomainError):
    code = "INVALID_CHANGE_REASON"


class InvalidEmployeeIdentityError(DomainError):
    code = "INVALID_EMPLOYEE_IDENTITY"


class DuplicateEmployeeError(DomainError):
    code = "DUPLICATE_EMPLOYEE"

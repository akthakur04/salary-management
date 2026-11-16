"""Employee code and work email: normalised, and unique across the organisation.

The database also enforces uniqueness with unique indexes; this check gives a
clear error before the insert is attempted.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.errors import DuplicateEmployeeError, InvalidEmployeeIdentityError

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@dataclass(frozen=True, slots=True)
class EmployeeIdentity:
    employee_code: str
    email: str

    def __post_init__(self) -> None:
        code = self.employee_code.strip().upper()
        email = self.email.strip().lower()
        if not code:
            raise InvalidEmployeeIdentityError("Employee code can't be blank.")
        if not _EMAIL.fullmatch(email):
            raise InvalidEmployeeIdentityError(
                "Enter a work email such as name@company.com.", email=email
            )
        object.__setattr__(self, "employee_code", code)
        object.__setattr__(self, "email", email)


def ensure_unique_identity(
    candidate: EmployeeIdentity, existing: Iterable[EmployeeIdentity]
) -> None:
    for other in existing:
        if other.employee_code == candidate.employee_code:
            raise DuplicateEmployeeError(
                "Another employee already has this employee code.",
                field="employee_code",
                value=candidate.employee_code,
            )
        if other.email == candidate.email:
            raise DuplicateEmployeeError(
                "Another employee already uses this email.",
                field="email",
                value=candidate.email,
            )

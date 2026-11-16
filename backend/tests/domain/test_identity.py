import pytest

from app.domain.errors import DuplicateEmployeeError, InvalidEmployeeIdentityError
from app.domain.identity import EmployeeIdentity, ensure_unique_identity

EXISTING = [
    EmployeeIdentity("EMP-04821", "ravi.kumar@acme.example"),
    EmployeeIdentity("EMP-01177", "ananya.sharma@acme.example"),
]


def test_identity_is_normalised_for_comparison() -> None:
    identity = EmployeeIdentity(" emp-04821 ", " Ravi.Kumar@ACME.example ")

    assert identity.employee_code == "EMP-04821"
    assert identity.email == "ravi.kumar@acme.example"


def test_duplicate_employee_code_is_rejected() -> None:
    with pytest.raises(DuplicateEmployeeError) as raised:
        ensure_unique_identity(EmployeeIdentity("emp-04821", "new.person@acme.example"), EXISTING)

    assert raised.value.details == {"field": "employee_code", "value": "EMP-04821"}


def test_duplicate_email_is_rejected_ignoring_case() -> None:
    with pytest.raises(DuplicateEmployeeError) as raised:
        ensure_unique_identity(EmployeeIdentity("EMP-09999", "RAVI.KUMAR@acme.example"), EXISTING)

    assert raised.value.details == {"field": "email", "value": "ravi.kumar@acme.example"}


def test_unique_identity_is_accepted() -> None:
    ensure_unique_identity(EmployeeIdentity("EMP-09999", "new.person@acme.example"), EXISTING)


@pytest.mark.parametrize(
    ("code", "email"),
    [
        ("", "someone@acme.example"),
        ("EMP-1", "not-an-email"),
        ("EMP-1", "two@@acme.example"),
        ("EMP-1", "no-domain@"),
    ],
)
def test_blank_code_or_malformed_email_is_rejected(code: str, email: str) -> None:
    with pytest.raises(InvalidEmployeeIdentityError):
        EmployeeIdentity(code, email)

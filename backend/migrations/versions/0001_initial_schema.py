"""Initial schema: reference data, employees and compensation history.

Revision ID: 0001
Revises:

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models.types import ExactDecimal

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "country",
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_country")),
    )
    op.create_table(
        "department",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_department")),
        sa.UniqueConstraint("name", name=op.f("uq_department_name")),
    )
    op.create_table(
        "employee",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column(
            "employment_type",
            sa.Enum(
                "full_time",
                "part_time",
                "contractor",
                name="employment_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("fte", ExactDecimal(3, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "on_leave",
                "terminated",
                name="employment_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("termination_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee")),
        sa.UniqueConstraint("email", name=op.f("uq_employee_email")),
        sa.UniqueConstraint("employee_code", name=op.f("uq_employee_employee_code")),
    )
    with op.batch_alter_table("employee", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_employee_employment_type"), ["employment_type"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_employee_name"), ["name"], unique=False)
        batch_op.create_index(batch_op.f("ix_employee_status"), ["status"], unique=False)

    op.create_table(
        "fx_rate",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rate_set", sa.String(length=40), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("usd_per_unit", ExactDecimal(18, 10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fx_rate")),
        sa.UniqueConstraint("rate_set", "currency", name=op.f("uq_fx_rate_rate_set_currency")),
    )
    with op.batch_alter_table("fx_rate", schema=None) as batch_op:
        batch_op.create_index(
            "ix_fx_rate_is_active_currency", ["is_active", "currency"], unique=False
        )

    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("family", sa.String(length=80), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.CheckConstraint("level BETWEEN 1 AND 5", name=op.f("ck_role_level_range")),
        sa.ForeignKeyConstraint(
            ["department_id"], ["department.id"], name=op.f("fk_role_department_id_department")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role")),
        sa.UniqueConstraint("family", "level", name=op.f("uq_role_family_level")),
    )
    with op.batch_alter_table("role", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_role_department_id"), ["department_id"], unique=False)

    op.create_table(
        "compensation_version",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "reason",
            sa.Enum(
                "hire",
                "promotion",
                "merit",
                "market_adjustment",
                "transfer",
                "correction",
                name="change_reason",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("base_annual_minor", sa.BigInteger(), nullable=False),
        sa.Column("fixed_cash_minor", sa.BigInteger(), nullable=False),
        sa.Column("target_variable_minor", sa.BigInteger(), nullable=False),
        sa.Column("ttc_minor", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "base_annual_minor > 0", name=op.f("ck_compensation_version_base_positive")
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name=op.f("ck_compensation_version_period_order"),
        ),
        sa.ForeignKeyConstraint(
            ["country_code"],
            ["country.code"],
            name=op.f("fk_compensation_version_country_code_country"),
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name=op.f("fk_compensation_version_employee_id_employee"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["role.id"], name=op.f("fk_compensation_version_role_id_role")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_compensation_version")),
    )
    with op.batch_alter_table("compensation_version", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_compensation_version_country_code"), ["country_code"], unique=False
        )
        batch_op.create_index(
            "ix_compensation_version_employee_id_effective_from",
            ["employee_id", "effective_from"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_compensation_version_role_id"), ["role_id"], unique=False
        )
        batch_op.create_index(
            "uq_compensation_version_one_open_per_employee",
            ["employee_id"],
            unique=True,
            sqlite_where=sa.text("effective_to IS NULL"),
            postgresql_where=sa.text("effective_to IS NULL"),
        )

    op.create_table(
        "pay_band",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("min_minor", sa.BigInteger(), nullable=False),
        sa.Column("mid_minor", sa.BigInteger(), nullable=False),
        sa.Column("max_minor", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "min_minor > 0 AND min_minor <= mid_minor AND mid_minor <= max_minor",
            name=op.f("ck_pay_band_ordered"),
        ),
        sa.ForeignKeyConstraint(
            ["country_code"], ["country.code"], name=op.f("fk_pay_band_country_code_country")
        ),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"], name=op.f("fk_pay_band_role_id_role")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pay_band")),
        sa.UniqueConstraint(
            "role_id", "country_code", name=op.f("uq_pay_band_role_id_country_code")
        ),
    )
    op.create_table(
        "role_default_component",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "allowance",
                "bonus",
                "commission",
                "one_time",
                name="component_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("percent", ExactDecimal(5, 2), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"], ["role.id"], name=op.f("fk_role_default_component_role_id_role")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_default_component")),
    )
    with op.batch_alter_table("role_default_component", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_role_default_component_role_id"), ["role_id"], unique=False
        )

    op.create_table(
        "compensation_component",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "allowance",
                "bonus",
                "commission",
                "one_time",
                name="component_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "basis",
            sa.Enum(
                "fixed_amount",
                "percent_of_base",
                name="component_basis",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "frequency",
            sa.Enum(
                "monthly",
                "annual",
                "once",
                name="frequency",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=True),
        sa.Column("percent", ExactDecimal(5, 2), nullable=True),
        sa.Column("payout_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["compensation_version.id"],
            name=op.f("fk_compensation_component_version_id_compensation_version"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_compensation_component")),
    )
    with op.batch_alter_table("compensation_component", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_compensation_component_version_id"), ["version_id"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("compensation_component", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_compensation_component_version_id"))

    op.drop_table("compensation_component")
    with op.batch_alter_table("role_default_component", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_role_default_component_role_id"))

    op.drop_table("role_default_component")
    op.drop_table("pay_band")
    with op.batch_alter_table("compensation_version", schema=None) as batch_op:
        batch_op.drop_index(
            "uq_compensation_version_one_open_per_employee",
            sqlite_where=sa.text("effective_to IS NULL"),
            postgresql_where=sa.text("effective_to IS NULL"),
        )
        batch_op.drop_index(batch_op.f("ix_compensation_version_role_id"))
        batch_op.drop_index("ix_compensation_version_employee_id_effective_from")
        batch_op.drop_index(batch_op.f("ix_compensation_version_country_code"))

    op.drop_table("compensation_version")
    with op.batch_alter_table("role", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_role_department_id"))

    op.drop_table("role")
    with op.batch_alter_table("fx_rate", schema=None) as batch_op:
        batch_op.drop_index("ix_fx_rate_is_active_currency")

    op.drop_table("fx_rate")
    with op.batch_alter_table("employee", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_employee_status"))
        batch_op.drop_index(batch_op.f("ix_employee_name"))
        batch_op.drop_index(batch_op.f("ix_employee_employment_type"))

    op.drop_table("employee")
    op.drop_table("department")
    op.drop_table("country")

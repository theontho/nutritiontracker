"""Add the remaining Cronometer nutrient catalog fields.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-02
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

NUTRIENT_COLUMNS = (
    "water_g",
    "ash_g",
    "alcohol_g",
    "beta_hydroxybutyrate_g",
    "oxalate_mg",
    "phytate_mg",
    "net_carbs_g",
    "starch_g",
    "allulose_g",
    "fructose_g",
    "galactose_g",
    "glucose_g",
    "lactose_g",
    "maltose_g",
    "sucrose_g",
    "sugar_alcohol_g",
    "omega_3_g",
    "alpha_linolenic_acid_g",
    "dha_g",
    "epa_g",
    "omega_6_g",
    "arachidonic_acid_g",
    "linoleic_acid_g",
    "insoluble_fiber_g",
    "soluble_fiber_g",
    "phytosterol_mg",
    "fluoride_ug",
    "molybdenum_ug",
    "menaquinone_7_ug",
    "alanine_g",
    "arginine_g",
    "aspartic_acid_g",
    "cystine_g",
    "glutamic_acid_g",
    "glycine_g",
    "histidine_g",
    "hydroxyproline_g",
    "isoleucine_g",
    "leucine_g",
    "lysine_g",
    "methionine_g",
    "phenylalanine_g",
    "proline_g",
    "serine_g",
    "threonine_g",
    "tryptophan_g",
    "tyrosine_g",
    "valine_g",
)


def upgrade() -> None:
    for column in NUTRIENT_COLUMNS:
        op.execute(f"ALTER TABLE foods ADD COLUMN {column} REAL")


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for this migration")

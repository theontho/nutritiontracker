"""Add detailed USDA fatty acids and source-native nutrient values.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-04
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

NUTRIENT_COLUMNS = (
    "energy_kj",
    "betaine_mg",
    "vitamin_a_iu",
    "vitamin_d_iu",
    "butyric_acid_g",
    "caproic_acid_g",
    "caprylic_acid_g",
    "capric_acid_g",
    "lauric_acid_g",
    "myristic_acid_g",
    "pentadecylic_acid_g",
    "palmitic_acid_g",
    "margaric_acid_g",
    "stearic_acid_g",
    "arachidic_acid_g",
    "behenic_acid_g",
    "lignoceric_acid_g",
    "myristoleic_acid_g",
    "pentadecenoic_acid_g",
    "palmitoleic_acid_g",
    "sapienic_acid_g",
    "heptadecenoic_acid_g",
    "oleic_acid_g",
    "oleic_acid_cis_g",
    "gondoic_acid_g",
    "docosenoic_acid_g",
    "erucic_acid_g",
    "nervonic_acid_g",
    "pufa_18_2_g",
    "conjugated_linoleic_acid_g",
    "pufa_18_3_g",
    "gamma_linolenic_acid_g",
    "pufa_18_3i_g",
    "stearidonic_acid_g",
    "eicosadienoic_acid_g",
    "pufa_20_3_g",
    "eicosatrienoic_acid_g",
    "dihomo_gamma_linolenic_acid_g",
    "adrenic_acid_g",
    "dpa_g",
    "trans_monoenoic_fat_g",
    "trans_palmitoleic_acid_g",
    "trans_oleic_acid_g",
    "trans_erucic_acid_g",
    "trans_linoleic_acid_g",
    "trans_polyenoic_fat_g",
    "theobromine_mg",
)


def upgrade() -> None:
    for column in NUTRIENT_COLUMNS:
        op.execute(f"ALTER TABLE foods ADD COLUMN {column} REAL")


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for this migration")

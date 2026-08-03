"""Add independently reported vitamin and choline forms.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-02
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

NUTRIENT_FORM_COLUMNS = (
    "retinol_ug",
    "beta_carotene_ug",
    "cis_beta_carotene_ug",
    "trans_beta_carotene_ug",
    "alpha_carotene_ug",
    "gamma_carotene_ug",
    "beta_cryptoxanthin_ug",
    "alpha_cryptoxanthin_ug",
    "lycopene_ug",
    "cis_lycopene_ug",
    "trans_lycopene_ug",
    "lutein_ug",
    "lutein_zeaxanthin_ug",
    "cis_lutein_zeaxanthin_ug",
    "vitamin_d2_ug",
    "vitamin_d3_ug",
    "vitamin_d3_25_hydroxy_ug",
    "vitamin_d4_ug",
    "beta_tocopherol_mg",
    "gamma_tocopherol_mg",
    "delta_tocopherol_mg",
    "alpha_tocotrienol_mg",
    "beta_tocotrienol_mg",
    "gamma_tocotrienol_mg",
    "delta_tocotrienol_mg",
    "dihydrophylloquinone_ug",
    "menaquinone_4_ug",
    "folate_food_ug",
    "folate_dfe_ug",
    "folate_5_mthf_ug",
    "folate_10_formyl_ug",
    "folate_5_formyl_ug",
    "vitamin_b12_added_ug",
    "choline_free_mg",
    "choline_phosphocholine_mg",
    "choline_phosphatidylcholine_mg",
    "choline_glycerophosphocholine_mg",
    "choline_sphingomyelin_mg",
)


def upgrade() -> None:
    for column in NUTRIENT_FORM_COLUMNS:
        op.execute(f"ALTER TABLE foods ADD COLUMN {column} REAL")


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for this migration")

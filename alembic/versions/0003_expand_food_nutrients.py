"""Expand food nutrition coverage.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-01
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


NEW_NUTRIENT_COLUMNS = (
    "added_sugar_g",
    "trans_fat_g",
    "monounsaturated_fat_g",
    "polyunsaturated_fat_g",
    "cholesterol_mg",
    "caffeine_mg",
    "copper_mg",
    "manganese_mg",
    "selenium_ug",
    "chromium_ug",
    "iodine_ug",
    "vitamin_e_mg",
    "vitamin_k_ug",
    "thiamin_mg",
    "riboflavin_mg",
    "pantothenic_acid_mg",
    "biotin_ug",
    "folate_ug",
    "folic_acid_ug",
    "choline_mg",
)


def upgrade() -> None:
    for column in NEW_NUTRIENT_COLUMNS:
        op.execute(f"ALTER TABLE foods ADD COLUMN {column} REAL DEFAULT 0")


def downgrade() -> None:
    raise NotImplementedError("downgrade not supported for this migration")

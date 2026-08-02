from collections.abc import Sequence

from app.models.food import NutrientsPer100
from app.repositories.foods import FoodRepository
from app.sources import FOOD_SOURCES, resolve_source_filter, source_tier

NUTRIENT_FIELDS = list(NutrientsPer100.model_fields.keys())

RELEVANCE_KEY = "relevance"

# What one quality tier is worth, expressed in bm25 units, when ordering
# results overall.
#
# Two effects had to be balanced. SQLite's bm25 ties heavily ("acai berry"
# returns four foods at exactly -16.486), and those ties used to be broken by
# rowid, so an Open Food Facts row of placeholder zeros could outrank the same
# food from a research-grade source purely by insertion order. bm25 also
# rewards short documents, and label data supplies far more terse names than
# reference data does, so "Butterfinger" outscored "Butter, salted".
#
# Tuned against real queries on the full catalogue. At 0.25 the label rows
# still won ("butter" returned Butterfinger); at 3.0 generic reference foods
# began displacing exact brand matches ("clif bar", "kombucha"). At 2.0 every
# brand query tested still returns its exact match first while generic queries
# return measured composition data — which is the behaviour a nutrition tracker
# wants.
SOURCE_TIER_WEIGHT = 2.0

# Re-ranking can only promote foods that were actually retrieved, so search a
# window well past the requested page before reordering it.
CANDIDATE_POOL = 100
MAX_CANDIDATE_POOL = 1000

# Sources that publish measured composition data rather than transcribed
# nutrition labels.
REFERENCE_TIER_MAX = 3
REFERENCE_SOURCES: tuple[str, ...] = tuple(
    source.code for source in FOOD_SOURCES if source.tier <= REFERENCE_TIER_MAX
)

# Keeps an unregistered source sorting after every registered one without
# pushing it so far down that it disappears from results entirely.
_UNREGISTERED_TIER = max(source.tier for source in FOOD_SOURCES) + 1


def _known_nutrients(food: dict) -> int:
    """How many nutrients the source actually reports (NULL means unknown)."""
    return sum(1 for f in NUTRIENT_FIELDS if food.get(f) is not None)


def _reported_nutrients(food: dict) -> int:
    return sum(1 for f in NUTRIENT_FIELDS if (food.get(f) or 0) > 0)


def _ranking_tier(food: dict) -> int:
    return min(source_tier(food.get("source")), _UNREGISTERED_TIER)


def _quality_rank(food: dict) -> tuple[int, int, int]:
    """Sort key for picking a winner among duplicates — lower is better.

    Source tier leads: a research-grade dataset beats label data even when the
    label happens to list more numbers. Nutrient counts only break ties within
    a tier.
    """
    return (
        source_tier(food.get("source")),
        -_known_nutrients(food),
        -_reported_nutrients(food),
    )


def _relevance_rank(food: dict) -> tuple[float, int]:
    """Overall sort key — text relevance adjusted by source quality.

    bm25 is negative and lower is better, so adding a per-tier penalty demotes
    weaker sources. Foods that still tie fall back to the more complete
    nutrient profile.
    """
    relevance = food.get(RELEVANCE_KEY)
    if relevance is None:
        relevance = 0.0
    return (
        relevance + SOURCE_TIER_WEIGHT * _ranking_tier(food),
        -_known_nutrients(food),
    )


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().strip().split())


class FoodSearchService:
    def __init__(self, repo: FoodRepository):
        self.repo = repo

    def search(
        self, query: str, *, source: str | None = None, user_id: int | None = None,
        limit: int = 20, offset: int = 0,
    ) -> list[dict]:
        # Retrieve a window by text relevance, then reorder it by relevance and
        # source quality together. Paging is applied last, after dedup, so a
        # page is not silently short when duplicates collapse.
        pool = min(MAX_CANDIDATE_POOL, max(CANDIDATE_POOL, (offset + limit) * 3))
        sources = resolve_source_filter(source)
        candidates = self.repo.search(
            query, sources=sources, user_id=user_id, limit=pool, offset=0
        )
        candidates += self._reference_candidates(
            query, sources=sources, user_id=user_id, limit=pool
        )
        by_id = {food["id"]: food for food in candidates}
        ranked = sorted(by_id.values(), key=_relevance_rank)
        page = self._deduplicate(ranked)[offset : offset + limit]
        for food in page:
            food.pop(RELEVANCE_KEY, None)
        return page

    def _reference_candidates(
        self, query: str, *, sources: Sequence[str] | None,
        user_id: int | None, limit: int,
    ) -> list[dict]:
        """A second retrieval pass restricted to measured-composition sources.

        Label data outnumbers reference data roughly fifty to one, so a window
        ordered by text relevance alone can fill entirely with branded rows:
        searching "salmon" reached position 489 before the first non-label
        food. Re-ranking cannot promote a food it never retrieved, so the
        reference sources get a pass of their own and always reach the ranker.
        """
        wanted = REFERENCE_SOURCES
        if sources is not None:
            wanted = tuple(code for code in sources if code in REFERENCE_SOURCES)
        if not wanted:
            return []
        return self.repo.search(
            query, sources=wanted, user_id=user_id, limit=limit, offset=0
        )

    def _deduplicate(self, foods: list[dict]) -> list[dict]:
        seen_barcodes: dict[str, int] = {}
        seen_names: dict[str, int] = {}
        result: list[dict] = []

        for food in foods:
            barcode = food.get("barcode")
            norm_name = _normalize_name(food.get("name", ""))
            dup_idx = None

            if barcode and barcode in seen_barcodes:
                dup_idx = seen_barcodes[barcode]
            elif norm_name in seen_names:
                dup_idx = seen_names[norm_name]

            if dup_idx is not None:
                existing = result[dup_idx]
                if _quality_rank(food) < _quality_rank(existing):
                    result[dup_idx] = food
                continue

            idx = len(result)
            if barcode:
                seen_barcodes[barcode] = idx
            seen_names[norm_name] = idx
            result.append(food)

        return result

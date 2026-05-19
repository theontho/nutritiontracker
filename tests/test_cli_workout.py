from click.testing import CliRunner
from unittest.mock import patch

runner = CliRunner()


def test_parse_shorthand_lb():
    from app.cli.workout import _parse_set
    result = _parse_set("135x8")
    assert result == {"weight": 135.0, "weight_unit": "lb", "reps": 8.0}


def test_parse_shorthand_kg():
    from app.cli.workout import _parse_set
    result = _parse_set("60kgx5")
    assert result == {"weight": 60.0, "weight_unit": "kg", "reps": 5.0}


def test_parse_timed():
    from app.cli.workout import _parse_set
    result = _parse_set("60s")
    assert result == {"duration_seconds": 60, "reps": None}


def test_workout_group_exists():
    from app.cli.workout import workout
    assert workout is not None


def test_workout_today_calls_api():
    from app.cli.workout import workout
    with patch("app.cli.workout._get") as mock_get:
        mock_get.return_value = []
        result = runner.invoke(workout, ["today"])
    assert result.exit_code == 0

from unittest.mock import patch

import httpx
from click.testing import CliRunner

from app.cli.client import APIClient
from app.cli.main import cli
from app.cli.nutrition import POUNDS_PER_KILOGRAM

runner = CliRunner()


def test_cli_exposes_nutrition_commands():
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "foods" in result.output
    assert "diary" in result.output
    assert "query" in result.output
    assert "stats" in result.output
    assert "weight" in result.output


def test_food_search_calls_api_and_formats_results():
    food = {
        "id": 12,
        "name": "Chicken breast",
        "brand": None,
        "source": "usda_foundation",
        "calories_kcal": 165,
        "protein_g": 31,
        "carbs_g": 0,
        "fat_g": 3.6,
    }
    with patch("app.cli.client.APIClient.request", return_value=[food]) as request:
        result = runner.invoke(cli, ["foods", "search", "chicken"])

    assert result.exit_code == 0
    assert "[12] Chicken breast" in result.output
    assert "165 kcal | P 31g C 0g F 3.6g" in result.output
    request.assert_called_once_with(
        "GET",
        "/foods/search",
        params={"q": "chicken", "source": "all", "limit": 10, "offset": 0},
    )


def test_json_option_emits_machine_readable_output():
    with patch(
        "app.cli.client.APIClient.request",
        return_value={"status": "ok", "version": "0.1.0"},
    ):
        result = runner.invoke(cli, ["--json", "health"])

    assert result.exit_code == 0
    assert '"status": "ok"' in result.output


def test_api_client_sends_bearer_token():
    response = httpx.Response(
        200,
        json={"status": "ok"},
        request=httpx.Request("GET", "https://example.test/health"),
    )
    with patch("app.cli.client.httpx.request", return_value=response) as request:
        APIClient("https://example.test", "secret").request("GET", "/health")

    assert request.call_args.kwargs["headers"] == {"Authorization": "Bearer secret"}


def test_api_errors_are_reported_without_traceback():
    response = httpx.Response(
        401,
        json={"detail": "Invalid bearer token"},
        request=httpx.Request("GET", "https://example.test/health"),
    )
    with patch("app.cli.client.httpx.request", return_value=response):
        result = runner.invoke(cli, ["health"])

    assert result.exit_code == 1
    assert "API request failed (401): Invalid bearer token" in result.output
    assert "Traceback" not in result.output


def test_diary_add_posts_entry():
    entry = {
        "food_name": "Chicken breast",
        "amount": 100,
        "unit": "g",
        "nutrients_total": {
            "calories_kcal": 165,
            "protein_g": 31,
            "carbs_g": 0,
            "fat_g": 3.6,
        },
    }
    with patch("app.cli.client.APIClient.request", return_value=entry) as request:
        result = runner.invoke(
            cli,
            [
                "diary",
                "add",
                "12",
                "100",
                "g",
                "--meal",
                "lunch",
                "--date",
                "2026-08-02",
            ],
        )

    assert result.exit_code == 0
    assert "Logged Chicken breast to lunch" in result.output
    request.assert_called_once_with(
        "POST",
        "/diary/2026-08-02/entries",
        json={
            "food_id": 12,
            "amount": 100.0,
            "unit": "g",
            "meal_type": "lunch",
        },
    )


def test_diary_search_queries_food_history():
    entry = {
        "id": 4,
        "date": "2026-08-01",
        "meal_type": "lunch",
        "food_name": "Chicken breast",
        "amount": 100,
        "unit": "g",
        "nutrients_total": {
            "calories_kcal": 165,
            "protein_g": 31,
            "carbs_g": 0,
            "fat_g": 3.6,
        },
    }
    with patch("app.cli.client.APIClient.request", return_value=[entry]) as request:
        result = runner.invoke(cli, ["diary", "search", "chicken"])

    assert result.exit_code == 0
    assert "2026-08-01 lunch: Chicken breast" in result.output
    request.assert_called_once_with("GET", "/diary/search", params={"q": "chicken"})


def test_query_supports_repeated_parameters_and_outputs_json():
    with patch(
        "app.cli.client.APIClient.request",
        return_value=[{"id": 1, "name": "oats"}],
    ) as request:
        result = runner.invoke(
            cli,
            [
                "query",
                "/kitchen/inventory",
                "--param",
                "q=oats",
                "--param",
                "status=have",
            ],
        )

    assert result.exit_code == 0
    assert '"name": "oats"' in result.output
    request.assert_called_once_with(
        "GET",
        "/kitchen/inventory",
        params=[("q", "oats"), ("status", "have")],
    )


def test_query_rejects_embedded_query_string():
    with patch("app.cli.client.APIClient.request") as request:
        result = runner.invoke(cli, ["query", "/events?limit=10"])

    assert result.exit_code == 2
    assert "use --param KEY=VALUE" in result.output
    request.assert_not_called()


def test_stats_rejects_reversed_range_without_api_call():
    with patch("app.cli.client.APIClient.request") as request:
        result = runner.invoke(cli, ["stats", "range", "2026-08-03", "2026-08-02"])

    assert result.exit_code == 2
    assert "START must not be after END" in result.output
    request.assert_not_called()


def test_weight_add_converts_pounds_to_kilograms():
    response = {"id": 7, "date": "2026-08-02", "weight_kg": 81.6466}
    with patch("app.cli.client.APIClient.request", return_value=response) as request:
        result = runner.invoke(
            cli,
            [
                "weight",
                "add",
                "180",
                "--unit",
                "lb",
                "--date",
                "2026-08-02",
            ],
        )

    assert result.exit_code == 0
    body = request.call_args.kwargs["json"]
    assert body["weight_kg"] == 180 / POUNDS_PER_KILOGRAM
    assert "81.6 kg" in result.output


def test_weight_list_requires_both_range_bounds():
    with patch("app.cli.client.APIClient.request") as request:
        result = runner.invoke(cli, ["weight", "list", "--start", "2026-08-01"])

    assert result.exit_code == 2
    assert "--start and --end must be used together" in result.output
    request.assert_not_called()

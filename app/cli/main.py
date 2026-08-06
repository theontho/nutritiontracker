from pathlib import Path

import click

from app.cli.client import (
    DEFAULT_BASE_URL,
    DEFAULT_CONFIG_PATH,
    APIClient,
    CLIContext,
    load_local_config,
)
from app.cli.exercises import exercises
from app.cli.nutrition import api_request, diary, foods, health, query, stats, weight
from app.cli.resources import activity, events, journal, kitchen, recipes, users
from app.cli.workout import workout


@click.group()
@click.option(
    "--base-url",
    envvar="NT_BASE_URL",
    show_default=DEFAULT_BASE_URL,
    help="Nutrition Tracker API URL.",
)
@click.option(
    "--token",
    envvar="NT_BEARER_TOKEN",
    help="Nutrition Tracker bearer token.",
)
@click.option(
    "--config",
    "config_path",
    envvar="NT_CONFIG",
    type=click.Path(path_type=Path, dir_okay=False),
    default=DEFAULT_CONFIG_PATH,
    show_default=True,
    help="JSON config containing base_url and a loopback token.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Emit JSON for scripting.",
)
@click.version_option(package_name="nutritiontracker")
@click.pass_context
def cli(
    click_context: click.Context,
    base_url: str | None,
    token: str | None,
    config_path: Path,
    json_output: bool,
) -> None:
    """Nutrition + workout tracking CLI."""
    local_config = load_local_config(config_path)
    click_context.obj = CLIContext(
        client=APIClient(
            base_url=base_url or local_config.base_url or DEFAULT_BASE_URL,
            token=token or local_config.token,
        ),
        json_output=json_output,
    )


cli.add_command(activity)
cli.add_command(diary)
cli.add_command(exercises)
cli.add_command(events)
cli.add_command(foods)
cli.add_command(health)
cli.add_command(journal)
cli.add_command(kitchen)
cli.add_command(query)
cli.add_command(recipes)
cli.add_command(api_request)
cli.add_command(stats)
cli.add_command(users)
cli.add_command(weight)
cli.add_command(workout)

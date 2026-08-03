import click

from app.cli.client import DEFAULT_BASE_URL, APIClient, CLIContext
from app.cli.exercises import exercises
from app.cli.nutrition import diary, foods, health, query, stats, weight
from app.cli.workout import workout


@click.group()
@click.option(
    "--base-url",
    envvar="NT_BASE_URL",
    default=DEFAULT_BASE_URL,
    show_default=True,
    help="Nutrition Tracker API URL.",
)
@click.option(
    "--token",
    envvar="NT_BEARER_TOKEN",
    help="Nutrition Tracker bearer token.",
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
    base_url: str,
    token: str | None,
    json_output: bool,
) -> None:
    """Nutrition + workout tracking CLI."""
    click_context.obj = CLIContext(
        client=APIClient(base_url=base_url, token=token),
        json_output=json_output,
    )


cli.add_command(diary)
cli.add_command(exercises)
cli.add_command(foods)
cli.add_command(health)
cli.add_command(query)
cli.add_command(stats)
cli.add_command(weight)
cli.add_command(workout)

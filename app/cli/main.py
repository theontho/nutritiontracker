import click
from app.cli.exercises import exercises
from app.cli.workout import workout


@click.group()
def cli():
    """Nutrition + workout tracking CLI."""
    pass


cli.add_command(exercises)
cli.add_command(workout)

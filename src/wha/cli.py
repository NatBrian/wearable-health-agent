"""CLI entry point for WHA."""

import typer

app = typer.Typer(name="wha", help="Wearable Health Early Warning Agent CLI")


@app.callback()
def main() -> None:
    """Wearable Health Early Warning Agent."""


if __name__ == "__main__":
    app()

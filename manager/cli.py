import typer
from manager import core

app = typer.Typer()

@app.command()
def init(path: str = typer.Argument(..., help="Path to initialize new registry")):
    """Initialize a new project registry"""
    core.initialize_registry(path)

if __name__ == "__main__":
    app()

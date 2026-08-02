from rich.console import Console
from rich.theme import Theme

custom_theme = Theme(
    {
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold blue",
        "status": "bold cyan",
        "time": "bold magenta",
    }
)
console = Console(theme=custom_theme, legacy_windows=False)

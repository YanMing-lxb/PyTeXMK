"""Thin forwarder: `python -m pytexmk` keeps equivalent to `pytexmk.cli.__main__.main()`."""
from .cli.__main__ import main

if __name__ == "__main__":
    main()

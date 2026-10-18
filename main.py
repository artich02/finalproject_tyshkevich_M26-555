import sys

from valutatrade_hub.cli.interface import CommandLineInterface

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    cli = CommandLineInterface()
    cli.run()


if __name__ == "__main__":
    main()
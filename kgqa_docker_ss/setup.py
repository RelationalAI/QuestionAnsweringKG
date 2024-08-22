import argparse
import importlib


def _parse_flag_argument(arg):
    key, value = arg.split("=")
    return key, value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="kgqa-setup")
    parser.add_argument("script")
    parser.add_argument(
        "-O",
        "--option",
        type=_parse_flag_argument,
        nargs="*",
        action="append",
        help="set script specific options.",
    )

    args = parser.parse_args()
    options = dict()
    if args.option:
        for key, value in [x[0] for x in args.option]:
            options[key] = value

    module = importlib.import_module(f"{args.script}")
    module.accept(options)

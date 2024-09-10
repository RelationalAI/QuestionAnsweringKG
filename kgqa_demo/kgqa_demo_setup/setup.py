import argparse
import importlib


def _parse_flag_argument(arg):
    key, value = arg.split("=")
    return key, value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="kgqa-setup")
    parser.add_argument("script", help="The script to run (without .py extension)")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to the configuration file (e.g., ./config.json)."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Directory where the output files will be saved."
    )
    parser.add_argument(
        "-O",
        "--option",
        type=_parse_flag_argument,
        nargs="*",
        help="Set script-specific options in key=value format.",
    )
    
    args = parser.parse_args()
    options = {}
    if args.option:
        for key, value in args.option:
            options[key] = value

    # Adding config and output_dir to the options dictionary
    options['config'] = args.config
    options['output_dir'] = args.output_dir
    module = importlib.import_module(args.script)
    module.main(options)

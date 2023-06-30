import asyncio
import os
import argparse
import importlib.util
import inspect


def load_script_module(script_name):
    # Get the path to the 'scripts' folder relative to 'run_script.py'
    scripts_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')

    # Construct the script file path
    script_path = os.path.join(scripts_folder, script_name + '.py')

    # Check if the script file exists
    if not os.path.isfile(script_path):
        print(f"Error: No script '{script_name}' defined in the 'scripts' folder.")
        exit(1)

    # Import the script as a module
    spec = importlib.util.spec_from_file_location(script_name, script_path)
    script_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script_module)

    return script_module


def main():
    parser = argparse.ArgumentParser(description='Run a script from the scripts folder')

    parser.add_argument('script', help='Name of the script to run (without the .py extension)')
    parser.add_argument('script_args', nargs=argparse.REMAINDER, help='Arguments to pass to the script')

    args = parser.parse_args()

    script_module = load_script_module(args.script)

    # Script module must have a 'main' function to be run
    if not hasattr(script_module, 'main') or not callable(script_module.main):
        print(f'Error: "{args.script}" module does not define a `main` function.')
        exit(1)

    # If the script defines a 'parse_args' function, parse the additional command line arguments using that and
    # pass the result to the script's 'main' function.
    if hasattr(script_module, 'parse_args') and callable(script_module.parse_args):
        script_parser = script_module.parse_args()
        script_args = script_parser.parse_args(args.script_args)
        def run_script(): return script_module.main(script_args)
    else:
        # If no parse_args function defined, call the script's 'main' function directly with no arguments
        def run_script(): return script_module.main()

    if inspect.iscoroutinefunction(script_module.main):
        asyncio.run(run_script())
    else:
        run_script()


if __name__ == "__main__":
    main()

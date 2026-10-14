# ScriptMonkey launcher. Start this file, not scriptmonkey_app.py directly.
from lib.scriptmonkey_diagnostics import install_logging
install_logging()
from scriptmonkey_app import main

if __name__ == "__main__":
    main()

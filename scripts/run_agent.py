# C:\Users\rossd\Downloads\RossNetAgents\scripts\run_agent.py

import argparse  # For command-line arguments
import asyncio
import importlib
import importlib.util
import logging
import os
import re
import sys

# --- Adjust Python Path ---
# Add the project root directory (RossNetAgents) to the Python path
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # RossNetAgents directory
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"[RunAgent] Added {project_root} to sys.path")

    # Explicitly load .env file from project root *before* agent imports
    dotenv_path = os.path.join(project_root, ".env")
    if os.path.exists(dotenv_path):
        try:
            # Attempt to import and use python-dotenv
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=dotenv_path, override=True)
            print(f"[RunAgent] Loaded environment variables from: {dotenv_path}")
            # Optional check: Verify if key is loaded
            # if 'OPENAI_API_KEY' not in os.environ:
            #      print("[RunAgent] WARNING: OPENAI_API_KEY not found after loading .env")
        except ImportError:
            print(
                "[RunAgent] Warning: 'python-dotenv' not installed. Cannot load .env file "
                "explicitly. Relying on automatic loading by libraries.",
            )
        except Exception as load_e:
            print(f"[RunAgent] Error loading .env file: {load_e}")
    else:
        print(
            "[RunAgent] Note: .env file not found at "
            f"{dotenv_path}, environment variables should be set manually if needed.",
        )

except Exception as e:
    print(f"[RunAgent] Error adjusting sys.path or loading .env: {e}")
    sys.exit(1)

# --- Basic Logging Config ---
# Agent-specific logging will be configured within the agent's main module
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("RunAgentScript")

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="Run a specific RossNet Agent.")
# Allow only trusted agent module prefixes; extend if additional namespaces are needed.
ALLOWED_AGENT_PREFIXES = ("agents.", "workers.")

# Modules must be dot-separated identifiers (no whitespace, no path traversal characters).
MODULE_PATH_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+$")


def validate_module_path(module_path: str) -> str:
    """Validate the supplied module path against a strict allow-list and pattern."""
    if not MODULE_PATH_PATTERN.fullmatch(module_path):
        raise ValueError("Module path must be a dot-separated Python identifier (e.g., agents.example.main).")

    if not any(module_path.startswith(prefix) for prefix in ALLOWED_AGENT_PREFIXES):
        allowed = ", ".join(ALLOWED_AGENT_PREFIXES)
        raise ValueError(f"Module path must begin with one of the allowed prefixes: {allowed}.")

    spec = importlib.util.find_spec(module_path)
    if spec is None or spec.origin is None:
        raise ValueError(f"Unable to locate module '{module_path}' within the project.")

    normalized_origin = os.path.abspath(spec.origin)
    if not normalized_origin.startswith(project_root):  # type: ignore[name-defined]
        raise ValueError(f"Module '{module_path}' resolves outside of the project tree and will not be loaded.")

    return module_path


parser.add_argument(
    "agent_module_path",
    help=("The full module path to the agent's main module (e.g., agents.planning.planner_agent.main)"),
)

raw_args = parser.parse_args()

try:
    args = argparse.Namespace(agent_module_path=validate_module_path(raw_args.agent_module_path))
except ValueError as err:
    parser.error(str(err))


# --- Dynamically Import and Run Agent ---
async def start_agent(module_path: str):
    """Dynamically imports and runs the main() function of the specified agent module."""
    try:
        logger.info(f"Attempting to import agent module: {module_path}")
        # Dynamically import the module
        agent_module = importlib.import_module(module_path)
        logger.info(f"Successfully imported {module_path}")

        # Check if the module has an async main() function
        if hasattr(agent_module, "main") and asyncio.iscoroutinefunction(agent_module.main):
            logger.info(f"Found async main() function in {module_path}. Executing...")
            # Execute the agent's main function
            await agent_module.main()
            logger.info(f"Agent module {module_path} main() finished.")
        else:
            logger.error(f"Module {module_path} does not have a callable async main() function.")

    except ImportError as e:
        # This is where the Langchain import error would likely be caught now
        logger.critical(
            f"Failed to import agent module {module_path} or its dependencies: {e}",
            exc_info=True,
        )
        logger.critical(
            "Ensure the module path is correct and all dependencies (like langchain-openai) are installed in the venv.",
        )
    except AttributeError as e:
        logger.critical(f"Error accessing main() function in {module_path}: {e}", exc_info=True)
    except Exception as e:
        logger.critical(
            f"An unexpected error occurred while running agent {module_path}: {e}",
            exc_info=True,
        )


# --- Script Execution ---
if __name__ == "__main__":
    logger.info(f"Attempting to run agent: {args.agent_module_path}")
    try:
        asyncio.run(start_agent(args.agent_module_path))
    except KeyboardInterrupt:
        logger.info("RunAgent script interrupted by user.")
    except Exception as e:
        logger.critical(f"RunAgent script failed: {e}", exc_info=True)
    finally:
        logger.info(f"RunAgent script finished for module: {args.agent_module_path}")

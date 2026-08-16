import os
import sqlite3
import importlib.util
from core.database import DB_PATH
from core.ui import console

SKILLS_DIR = "skills"

# Ensure skills directory exists
if not os.path.exists(SKILLS_DIR):
    os.makedirs(SKILLS_DIR)

def register_skill(name: str, description: str, code: str):
    """Write skill code to file and record it in database"""
    filename = f"{name.lower().replace(' ', '_')}.py"
    filepath = os.path.join(SKILLS_DIR, filename)
    
    try:
        # Save code to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
            
        # Log in SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        import time
        cursor.execute(
            """INSERT INTO skills (timestamp, name, description, filepath)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
               timestamp=excluded.timestamp, description=excluded.description, filepath=excluded.filepath""",
            (time.time(), name, description, filepath)
        )
        conn.commit()
        conn.close()
        console.print(f"[bold green]System:[/] Skill '{name}' successfully compiled and registered.")
    except Exception as e:
        console.print(f"[bold red]Skill Registration Error:[/] {e}")

def execute_skill(name: str) -> str:
    """Dynamically load and run a skill's run() function"""
    # If the LLM tries to append parameters inside the execute tag (e.g. get_weather|Badulla), extract the actual skill name
    if "|" in name:
        name = name.split("|")[0].strip()
    elif ":" in name:
        name = name.split(":")[0].strip()

    filename = f"{name.lower().replace(' ', '_')}.py"
    filepath = os.path.join(SKILLS_DIR, filename)
    
    if not os.path.exists(filepath):
        return f"Error: Skill '{name}' file not found."
        
    try:
        spec = importlib.util.spec_from_file_location(name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'run'):
            # Run the skill. We can run it synchronously or check if it's a coroutine.
            import inspect
            if inspect.iscoroutinefunction(module.run):
                # If it's a coroutine, we run it in the loop
                import asyncio
                result = asyncio.run(module.run())
            else:
                result = module.run()
            return str(result)
        else:
            return f"Error: Skill '{name}' does not define a run() function."
    except Exception as e:
        console.print(f"[bold red]Skill Execution Error ({name}):[/] {e}")
        return f"Error running skill '{name}': {e}"

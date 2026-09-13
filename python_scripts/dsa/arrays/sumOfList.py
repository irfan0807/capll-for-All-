from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).parents[1] / "sumOfList.py"), run_name="__main__")

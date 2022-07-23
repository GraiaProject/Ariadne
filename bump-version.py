import pathlib
import re
import sys

tag_name = sys.argv[1]
init_file = pathlib.Path("./src/graia/ariadne/__init__.py")
code = init_file.read_text(encoding="utf-8")
code = re.sub(r"__version__ = \".+?\"", f'__version__ = "{tag_name}"', code)
init_file.write_text(code, "utf-8")

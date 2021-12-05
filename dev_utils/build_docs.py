import os
import shutil
import subprocess

os.chdir(os.path.join(__file__, "..", ".."))
subprocess.run(["black", "."])
subprocess.run(["isort", "."])
try:
    shutil.rmtree(os.path.abspath(os.path.join(".", "docs")))
except FileNotFoundError:
    pass
os.chdir(os.path.abspath(os.path.join(__file__, "..", "..", "src", "graia")))
subprocess.run(
    [
        "pdoc",
        "--html",
        "ariadne",
        "--force",
        "-o",
        "./../..",
        "--config",
        "lunr_search={'fuzziness': 1, 'index_docstrings': True}",
    ]
)
os.chdir(os.path.abspath(os.path.join(__file__, "..", "..")))
os.rename("ariadne", "docs")
opt = input("Confirm to publish?")
if not opt.lower().startswith("y"):
    exit(0)
subprocess.run(["poetry", "publish", "--build"])

import subprocess
import os
import shutil

shutil.rmtree(os.path.abspath(os.path.join(__file__, "..", "..", "docs")))
os.chdir(os.path.abspath(os.path.join(__file__, "..", "..", "src", "graia")))
subprocess.run(["pdoc", "--html", "ariadne", "-o", "./../.."])
os.chdir(os.path.abspath(os.path.join(__file__, "..", "..")))
os.rename("ariadne", "docs")
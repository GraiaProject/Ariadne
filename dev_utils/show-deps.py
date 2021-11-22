import os
import subprocess
import time

os.chdir(os.path.join(__file__, "..", ".."))
subprocess.run(["pydeps", "src/graia/ariadne", "--show-dot", "--cluster"])
time.sleep(5.0)  # wait for browser to load & cache
os.remove("./ariadne.svg")

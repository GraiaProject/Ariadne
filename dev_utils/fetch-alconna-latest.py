import os
import io
import requests
import zipfile
import shutil
import tempfile

os.chdir(os.path.join(__file__, "..", ".."))

ALCONNA_DOWNLOAD_URL = "https://github.com/RF-Tar-Railt/Cesloi-Alconna/archive/refs/heads/main.zip"

zipped_main = requests.get(ALCONNA_DOWNLOAD_URL).content

print(len(zipped_main))

temp_dir = tempfile.mkdtemp()

print(temp_dir)

zip_f = zipfile.ZipFile(io.BytesIO(zipped_main), "r")
zip_f.extractall(temp_dir)

shutil.move(
    os.path.join(temp_dir, "Cesloi-Alconna-main/alconna"),
    "./src/graia/ariadne/message/parser/alconna/alconna",
)

shutil.rmtree(temp_dir)

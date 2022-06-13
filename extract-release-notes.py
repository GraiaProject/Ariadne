import sys
from itertools import dropwhile

tag_name = sys.argv[1].removeprefix("v")

with open("./CHANGELOG.md", encoding="utf-8") as f:
    changelog_text = f.read()

with open("./release-notes.md", encoding="utf-8", mode="w") as f:
    for line in dropwhile(lambda x: x != "## 未发布的更新", changelog_text.splitlines()):
        if line == "## 未发布的更新":
            continue
        if line.split(" ") and line.split(" ")[0] == "##":
            break
        print(line, file=f)

with open("./CHANGELOG.md", encoding="utf-8", mode="w") as f:
    f.write(changelog_text.replace("## 未发布的更新", f"## 未发布的更新\n\n## {tag_name}"))

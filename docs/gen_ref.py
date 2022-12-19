"""Generate the code reference pages and navigation."""
import sys
from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

fe = mkdocs_gen_files.FilesEditor.current()

root = Path(__file__).parent.parent

src = (root / "src").resolve()

sys.path.append(src.as_posix())

for path in sorted(Path(src, "graia").glob("**/*.py")):
    module_path = path.relative_to(src).with_suffix("")
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = path.relative_to(src / "graia" / "ariadne").with_suffix(".md")

    parts = list(module_path.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1] == "__main__" or parts[-1].startswith("_"):
        continue
    nav[parts] = full_doc_path

    with fe.open(full_doc_path, "w") as f:
        pass

    fe.set_edit_path(full_doc_path, path)

with fe.open("NAV.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())

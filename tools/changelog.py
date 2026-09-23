"""Prints the release notes of one version: its CHANGELOG.md section plus a
short guide to the release files.

    python tools/changelog.py 1.2.0
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = """
### Which file do I need?

| Browser | File |
|---|---|
| LibreWolf (and other builds that allow unsigned extensions) | `pip-crop-{v}.xpi` |
| Firefox (release) on Windows | `pip-crop-{v}-firefox-autoconfig.zip` |

Installation steps are in the {readme}.
`SHA256SUMS.txt` has the checksums; `updates.json` is the update manifest that
installed copies check for new versions.
"""


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    version = sys.argv[1]
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        text = f.read()
    m = re.search(rf"^## \[?{re.escape(version)}\]?[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m or not m.group(1).strip():
        sys.exit(f"changelog.py: CHANGELOG.md has no section for {version}")
    repo = os.environ.get("GITHUB_REPOSITORY")
    readme = f"[installation guide](https://github.com/{repo}/blob/main/docs/installation.md)" if repo else "installation guide (docs/installation.md)"
    print(m.group(1).strip() + "\n" + FILES.format(v=version, readme=readme))


if __name__ == "__main__":
    main()

"""Builds the distributable files from the sources.

    python tools/build.py [--repo OWNER/NAME] [--expect-version X.Y.Z]

Output in dist/:

  extension/                               unpacked extension (linting, about:debugging)
  pip-crop-<version>.xpi                   WebExtension Experiment: LibreWolf and other
                                           builds that allow unsigned extensions
  firefox-autoconfig/                      AutoConfig files + installer (Firefox release)
  pip-crop-<version>-firefox-autoconfig.zip
  updates.json                             self-hosted update manifest (only with --repo)
  SHA256SUMS.txt

--repo (default: $GITHUB_REPOSITORY) adds homepage_url and an update_url pointing
at the latest GitHub release, so installed copies update themselves from there.
Archives are reproducible: the same sources give the same bytes.
"""
import argparse, hashlib, json, os, re, shutil, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
NAME = "pip-crop"
MARKER = "/* @@PIPCROP_MODULE@@ */"
ZIP_DATE = (2020, 1, 1, 0, 0, 0)


def fail(msg):
    sys.exit(f"build.py: {msg}")


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def zip_dir(src, out):
    """Zip a folder with sorted entries, fixed dates and permissions."""
    files = []
    for base, dirs, names in os.walk(src):
        dirs.sort()
        files += [os.path.join(base, n) for n in sorted(names)]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            info = zipfile.ZipInfo(os.path.relpath(path, src).replace(os.sep, "/"), ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3  # Unix, whatever OS builds it
            info.external_attr = 0o644 << 16
            with open(path, "rb") as f:
                z.writestr(info, f.read())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"),
                    help="GitHub OWNER/NAME for homepage and self-hosted updates")
    ap.add_argument("--expect-version", help="fail unless the sources have this version (release tags)")
    args = ap.parse_args()

    manifest = json.loads(read("extension", "manifest.json"))
    version = manifest["version"]
    gecko = manifest["browser_specific_settings"]["gecko"]
    module = read("src", "pipcrop.js")
    m = re.search(r'^\s*version: "([^"]+)",$', module, re.M)
    if not m or m.group(1) != version:
        fail(f"version mismatch: extension/manifest.json has {version}, "
             f"src/pipcrop.js has {m.group(1) if m else 'none'}")
    if args.expect_version and args.expect_version != version:
        fail(f"expected version {args.expect_version}, the sources are {version}")
    wrapper = read("extension", "api-wrapper.js")
    if MARKER not in wrapper:
        fail(f"{MARKER} missing from extension/api-wrapper.js")

    if args.repo:
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo):
            fail(f"--repo must be OWNER/NAME, got {args.repo!r}")
        manifest["homepage_url"] = f"https://github.com/{args.repo}"
        gecko["update_url"] = f"https://github.com/{args.repo}/releases/latest/download/updates.json"

    if os.path.isdir(DIST):
        shutil.rmtree(DIST)

    # The extension: the whole module is inlined into the experiment's api.js.
    ext = os.path.join(DIST, "extension")
    write(os.path.join(ext, "manifest.json"), json.dumps(manifest, indent=2) + "\n")
    write(os.path.join(ext, "schema.json"), read("extension", "schema.json"))
    write(os.path.join(ext, "api.js"), wrapper.replace(MARKER, module.replace("\n", "\n  ").rstrip()))
    write(os.path.join(ext, "icons", "pip-crop.svg"), read("assets", "logo.svg"))
    xpi_name = f"{NAME}-{version}.xpi"
    xpi = os.path.join(DIST, xpi_name)
    zip_dir(ext, xpi)

    # Firefox release: AutoConfig files, the module and the installer.
    ac = os.path.join(DIST, "firefox-autoconfig")
    shutil.copytree(os.path.join(ROOT, "firefox-autoconfig"), ac)
    write(os.path.join(ac, "pipcrop.js"), module)
    ac_zip = os.path.join(DIST, f"{NAME}-{version}-firefox-autoconfig.zip")
    zip_dir(ac, ac_zip)

    assets = [xpi, ac_zip]
    if args.repo:
        updates = {"addons": {gecko["id"]: {"updates": [{
            "version": version,
            "update_link": f"https://github.com/{args.repo}/releases/download/v{version}/{xpi_name}",
            "update_hash": "sha256:" + sha256(xpi),
            "applications": {"gecko": {"strict_min_version": gecko["strict_min_version"]}},
        }]}}}
        path = os.path.join(DIST, "updates.json")
        write(path, json.dumps(updates, indent=2) + "\n")
        assets.append(path)
    sums = "".join(f"{sha256(p)}  {os.path.basename(p)}\n" for p in assets)
    write(os.path.join(DIST, "SHA256SUMS.txt"), sums)

    for p in assets:
        print(f"built {os.path.relpath(p, ROOT)} ({os.path.getsize(p)} bytes)")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"version={version}\n")


if __name__ == "__main__":
    main()

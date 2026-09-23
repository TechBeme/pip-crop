"""Runs Mozilla's add-on linter (web-ext lint, the same linter as
addons.mozilla.org) on the built extension.

    python tools/lint.py [dist/extension]

It always reports one error for PiP Crop, MANIFEST_FIELD_PRIVILEGED:
experiment_apis is only allowed in add-ons that Mozilla signs as privileged.
That is why PiP Crop cannot be listed on addons.mozilla.org, so that error is
expected. Any other error or warning fails; notices are printed only.
"""
import json, shutil, subprocess, sys

EXPECTED = {"MANIFEST_FIELD_PRIVILEGED"}
WEB_EXT = "web-ext@8"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "dist/extension"
    npx = shutil.which("npx")
    if not npx:
        sys.exit("lint.py: npx not found (install Node.js)")
    # --self-hosted: the add-on is distributed from GitHub releases and has an
    # update_url, which is only disallowed for add-ons hosted on AMO.
    run = subprocess.run([npx, "--yes", WEB_EXT, "lint", "--source-dir", src, "--output", "json",
                          "--self-hosted", "--no-config-discovery"],
                         capture_output=True, text=True, encoding="utf-8")
    out = run.stdout
    try:
        report = json.loads(out[out.index("{"):])
    except ValueError:
        sys.exit(f"lint.py: could not read the linter output\n{out}\n{run.stderr}")
    unexpected = []
    for kind in ("errors", "warnings", "notices"):
        for msg in report.get(kind, []):
            known = kind == "errors" and msg["code"] in EXPECTED
            tag = "expected" if known else kind[:-1]
            print(f"[{tag}] {msg['code']}: {msg['message']} ({msg.get('file', '')})")
            if kind != "notices" and not known:
                unexpected.append(msg["code"])
    if unexpected:
        sys.exit(f"lint.py: {len(unexpected)} unexpected problem(s): {', '.join(unexpected)}")
    print(f"lint ok ({report['summary']})")


if __name__ == "__main__":
    main()

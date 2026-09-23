# Contributing to PiP Crop

Thanks for helping improve PiP Crop. Contributions can include bug fixes, support for more platforms (Linux and macOS), gesture and UX improvements, documentation, translations and tests.

## Before you start

- Search existing issues and pull requests.
- Open an issue before a large change to how the crop or the gesture works.
- Never include personal browsing data, private videos or screenshots of other windows in issues or pull requests.
- Keep all logic in [`src/pipcrop.js`](src/pipcrop.js); the extension and the AutoConfig loader are thin wrappers around it.

## Local setup

```bash
git clone https://github.com/TechBeme/pip-crop.git
cd pip-crop
python tools/build.py
```

Install `dist/pip-crop-<version>.xpi` in LibreWolf (see [docs/installation.md](docs/installation.md)), or load `dist/extension/manifest.json` temporarily from `about:debugging`.

## Quality checks

Run the same checks as CI before opening a pull request:

```bash
python tools/build.py
python tools/lint.py
node --check src/pipcrop.js
```

`tools/lint.py` runs Mozilla's add-on linter and needs Node.js. It always reports one expected error, `MANIFEST_FIELD_PRIVILEGED`, because WebExtension Experiments are privileged.

For changes to the crop or the gesture, run the end-to-end tests on Windows ([tests/README.md](tests/README.md)), at least `tests/e2e/t_sim.py`, `t_clamp.py` and `t_armed.py`, and say which browser and display scale you tested. A successful build alone does not prove that a real PiP window crops correctly.

## Pull requests

1. Keep the change focused.
2. Explain the user-facing behavior and the implementation choice.
3. List the browsers, versions and display scales you tested, and anything you could not test.
4. Update the documentation when behavior, settings or installation change.
5. Add a line to [CHANGELOG.md](CHANGELOG.md) for the next release.

## Releasing

1. Update the version in `extension/manifest.json` and in `src/pipcrop.js` (`version:`), and add a section for it to `CHANGELOG.md`.
2. Commit, then tag and push the tag:
   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```

The [CI workflow](.github/workflows/ci.yml) checks that the tag matches the version, builds and lints the add-on and publishes a GitHub release with the `.xpi`, the Firefox AutoConfig zip, `updates.json` and checksums. Installed copies update themselves from `updates.json`.

## Commit style

Use clear imperative commits, for example:

```text
feat: crop from the top-left corner
fix: keep the window inside the screen after a crop
docs: explain AutoConfig with an existing userChrome.js loader
```

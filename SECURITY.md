# Security policy

## Supported versions

Security fixes are applied to the latest release and the default branch.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability reporting for this repository:

https://github.com/TechBeme/pip-crop/security/advisories/new

Include the affected file or component, the browser and version, reproduction steps, the potential impact and any suggested mitigation. Do not include personal browsing data or private videos.

## Privileged code

PiP Crop runs with the browser's full privileges, like every WebExtension Experiment and AutoConfig script. It only touches Picture-in-Picture player windows, makes no network requests of its own and collects no data. Install it only from this repository's releases, or build it from source code you have reviewed.

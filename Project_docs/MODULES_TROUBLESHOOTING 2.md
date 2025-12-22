## Module startup failures (sentinel-presidio / sentinel-toxicity) — Troubleshooting Notes ✅

Symptoms observed:
- `Failed to start module: Failed to start sentinel-presidio` and `sentinel-toxicity` seen in UI when enabling modules.
- Cloud Run logs show:
  - For Presidio: `ValueError: numpy.dtype size changed, may indicate binary incompatibility. Expected 96 ... got 88` (import-time crash from compiled spacy/thinc extensions).
  - For Toxicity: model download attempts at runtime and "Error loading model: We couldn't connect to 'https://huggingface.co' ..." followed by model init failure or long cold-start downloads.

Root causes:
1. Binary dependency mismatches (NumPy vs compiled C extensions from `spacy`/`thinc`/`presidio`) — caused import-time crashes and crash loops.
2. Large ML model downloads during runtime (Hugging Face / Detoxify) — network timeouts or lack of cached files caused the container to retry on start.

Remediations implemented:
- Dockerfiles for `presidio_service` and `toxicity_service` were updated to:
  - Upgrade `pip`, `setuptools`, and `wheel` before installs.
  - Pin `numpy` to a stable 1.x version (`1.25.3`) and install packages with `--prefer-binary` to ensure wheel usage.
  - Run `pip check` during build to fail early on incompatible dependencies.
  - For `toxicity`, pre-download the Detoxify model at build time and verify cache contents (`HF_HOME`).
  - For `presidio`, download the spaCy model at build time and include a small runtime sanity check during image build.

Operational recommendations (next steps):
- Rebuild and push the module images (use `./scripts/deploy.sh toxicity` and `./scripts/deploy.sh presidio`). The build logs will show `pip check` results and model cache verification.
- Confirm service logs after deployment. If the import-time NumPy error persists, try the following, iterating until successful:
  - Try a different pinned NumPy version (e.g., `1.24.x` or `1.25.x`) and rebuild until `pip check` passes.
  - Ensure build environment and runtime are both using linux/amd64 (our deploy script forces this).
- If Detoxify still downloads models at runtime, confirm the build step's pre-download succeeded (there will be files in `/app/.cache/huggingface` during build); if builds run in a network-restricted environment, use a CI step with network access or pre-stage the model files in a Cloud Storage bucket and copy them in the image build.

Quick verification after redeploy:
- Toxicity: GET /health should return `{"status":"ok","model_loaded":true}`
- Presidio: GET /health should return `{"status":"ok","activated":true}` after `/activate` is called or the container starts successfully

Notes for production hardening:
- Bake model artifacts into container images (or add a controlled initialization job that downloads into a shared cache) to avoid Cloud Run cold-start downloads.
- Add stricter startup behavior: make services fail-fast when model initialization fails (exit non-zero or raise an exception during startup) so Cloud Run marks the revision unhealthy and operators get immediate feedback.
- Add `pip check` and dependency validation into CI to catch binary incompatibilities before image publish.

If you want, I can:
- Open a PR with the Dockerfile changes (already modified locally), and add an automated test that builds images in CI and verifies `/health` endpoints.
- Try rebuilding the two modules now and tail their logs to confirm the fix.

# MDC-NG helpers

These command-line helpers operate the existing remote MDC-NG Docker service; they are not the Docker image or stack definition.

- `smdc.bash` submits a disposable FC2 placeholder to MDC-NG, waits for metadata processing, and prints the resulting NFO fields.
- `sfc2.bash` queries FC2CMADB through FlareSolverr as the fallback used by `smdc.bash`.

The scripts default to the existing host/container values configured in their source. Override `MDC_SSH`, `MDC_CONTAINER`, `MDC_WAIT_SECONDS`, `MDC_POLL_SECONDS`, and `MDC_PROGRESS_SECONDS` for `smdc.bash`; override `FLARE_SSH` and `FLARE_URL` for `sfc2.bash`.

Requirements: Bash, `jq`, `python3`, `ssh`, `ffmpeg`; the fallback additionally requires network access to FlareSolverr and FC2CMADB.

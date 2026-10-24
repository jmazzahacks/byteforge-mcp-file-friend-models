# File Friend models — development guide

Independent models repository in the File Friend multi-repository workspace. Follow ByteForge python-lib-setup. Import package: `byteforge_mcp_file_friend_models`; no runtime dependencies beyond Python 3.13's standard library.

Keep wire contracts stable. No server, client, database or Flask imports. Root virtual environment at `bin/activate`; preserve `.gitignore` when recreating it. Tests must run against the installed wheel and must not load the parent PostgreSQL fixture.

This is the first extraction checkpoint; the parent legacy module remains unchanged until consumer migration. Jason approved MIT licensing and public GitHub repositories under `jmazzahacks` on 2026-10-24. Never modify another agent's code or infrastructure.

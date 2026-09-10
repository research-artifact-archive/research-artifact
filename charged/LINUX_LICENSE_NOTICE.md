# Linux-derived source license

The files under `evidence/RESUMED_20260910_1617/linux_dentry_01/implementation01/`, `implementation02/` and `implementation03/` are Linux kernel modifications or KUnit integration files. They are provided under GPL version2 only, as indicated by their SPDX notices and this directory-level notice. The accompanying `GPL-2.0` text is copied unchanged from Linux v6.12 `LICENSES/preferred/GPL-2.0`.

The original `fs/d_path.c` is from Linux commit `adc218676eef25575469234709c2d87185ca223a` and retains its original SPDX notice. Authored changes factor and instrument its traversal for KUnit, add alternative test-only policies and fixtures, and later add global sequence attribution. `d_path.patch` records the original source change; `implementation03/attribution.patch` records the additional attribution instrumentation. The source manifests and execution receipts identify exact bytes.

The repository's general MIT license does not replace these GPL terms. No Linux binary, full Linux source archive or upstream runtime is redistributed here. The optional reproduction command acquires the exact public source archive and builds it in its own container. Other artifact code and documents retain their existing license scopes.

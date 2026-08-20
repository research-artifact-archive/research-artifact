# Public-evidence sanitization

All shipped text evidence was scanned after replacing the authors' absolute
workspace and home prefixes with the literal tokens `<LOCAL_WORKSPACE>` and
`<LOCAL_USER_HOME>`. This includes raw CSV, summaries, manifests, environment
records, command lines, Java/PRISM logs, and handoff evidence. No decision,
timing, memory, state, edge, certificate, model hash, or outcome field was
deliberately changed; only path-bearing text was tokenized.

Pre-sanitization inventories and private source/hash crosswalks are excluded
from this public directory. Otherwise an attacker could try candidate path
prefixes until a historical hash matches. Whole-file references affected by
tokenization are rebound to the sanitized public bytes when that file is
included; private historical seals with no public counterpart use the literal
`<PRIVATE_PRE_SANITIZATION_HASH_OMITTED>`. Campaign/runtime and input hashes
that do not crosswalk a private path remain as scientific provenance.

The root `SHA256SUMS` is the authoritative integrity inventory for this public
directory. The verifier independently checks the public hash bindings and
omission tokens, and rejects public pre-sanitization inventories, personal
home-directory paths, common credential forms, symlinks, and files at the
GitHub 100 MB hard limit.

#!/bin/bash
set -eu

PRE_COMMIT=.git/hooks/pre-commit

cat <<-EOF > ${PRE_COMMIT}
	rye fmt --check
EOF
chmod +x ${PRE_COMMIT}

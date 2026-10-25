#!/usr/bin/env fish
# Upgrade all dependencies to their latest versions, then raise the ">=" lower bounds
# in pyproject.toml (dependencies and dependency groups) to match the locked versions.

cd (status dirname); or exit 1

uv lock --upgrade; or exit 1

# Direct deps as "name version" pairs, e.g. "django 6.1.1"
for pair in (uv tree --depth 1 --frozen | string replace -rf '.*── (\S+) v(\S+).*' '$1 $2')
    echo $pair | read -l name ver; or exit 1
    # Package names are case-insensitive and treat -, _ and . as equivalent
    set -l pattern (string replace -ra '[-_.]' '[-_.]' -- $name)
    sed -E -i "s/\"($pattern)(\[[^]]*\])?>=[^\",;]*/\"\1\2>=$ver/I" pyproject.toml
end

# Re-lock so uv.lock picks up the new specifiers, then update the environment
uv lock; and uv sync; or exit 1

git --no-pager diff --stat -- pyproject.toml uv.lock

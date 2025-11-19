#!/bin/bash
# bump_ynca_version.sh
# Usage: ./bump_ynca_version.sh <new_version>
# Example: ./bump_ynca_version.sh 5.22.0


set -e

# Determine the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Get the previous version from pyproject.toml
PREV_VERSION=$(grep -oP 'ynca==\K[0-9.]+' "$SCRIPT_DIR/pyproject.toml" | head -n1)

if [ $# -ne 1 ]; then
  echo "Usage: $0 <new_version>"
  echo "Current version is: $PREV_VERSION"
  exit 1
fi

NEW_VERSION="$1"

# Function to compare versions (returns 0 if $1 > $2)
version_gt() {
  [ "$1" = "$2" ] && return 1
  local IFS=.
  local i ver1=($1) ver2=($2)
  # Fill empty fields in ver1 with zeros
  for ((i=${#ver1[@]}; i<${#ver2[@]}; i++)); do
    ver1[i]=0
  done
  # Fill empty fields in ver2 with zeros
  for ((i=${#ver2[@]}; i<${#ver1[@]}; i++)); do
    ver2[i]=0
  done
  for ((i=0; i<${#ver1[@]}; i++)); do
    if ((10#${ver1[i]} > 10#${ver2[i]})); then
      return 0
    elif ((10#${ver1[i]} < 10#${ver2[i]})); then
      return 1
    fi
  done
  return 1
}

# Check if new version is higher than previous
if ! version_gt "$NEW_VERSION" "$PREV_VERSION"; then
  echo "Error: New version ($NEW_VERSION) is not higher than previous version ($PREV_VERSION)."
  exit 1
fi


# Update dependency on ynca in yamaha_ynca/pyproject.toml
sed -i "s/ynca==[0-9.]*/ynca==$NEW_VERSION/" "$SCRIPT_DIR/pyproject.toml"

# Update version in yamaha_ynca/manifest.json
sed -i "s/ynca==[0-9.]*/ynca==$NEW_VERSION/" "$SCRIPT_DIR/custom_components/yamaha_ynca/manifest.json"

echo "Version bumped to $NEW_VERSION in pyproject.toml and manifest.json files."

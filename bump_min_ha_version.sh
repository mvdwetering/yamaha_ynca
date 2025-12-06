#!/bin/bash
# bump_min_ha_version.sh
# Usage: ./bump_min_ha_version.sh <ha_version> [pytest_homeassistant_version]
# Example: ./bump_min_ha_version.sh 2025.3.0
# Example: ./bump_min_ha_version.sh 2025.3.0 0.13.215


set -e

# Determine the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Get the previous version from hacs.json
PREV_VERSION=$(grep -oP '"homeassistant":\s*"\K[0-9.]+' "$SCRIPT_DIR/hacs.json" | head -n1)

if [ $# -ne 2 ]; then
  echo "Usage: $0 <ha_version> <pytest_homeassistant_version>"
  echo "Current minimum HA version is: $PREV_VERSION"
  
  # Get current pytest-homeassistant-custom-component version
  CURRENT_PYTEST=$(grep -oP 'pytest-homeassistant-custom-component==\K[0-9.]+' "$SCRIPT_DIR/pyproject.toml" | head -n1)
  echo "Current pytest-homeassistant-custom-component version is: $CURRENT_PYTEST"
  exit 1
fi

NEW_VERSION="$1"
PYTEST_HA_VERSION="$2"

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

# Update homeassistant version in hacs.json
sed -i "s/\"homeassistant\": \"[0-9.]*\"/\"homeassistant\": \"$NEW_VERSION\"/" "$SCRIPT_DIR/hacs.json"

# Update homeassistant-stubs in pyproject.toml
sed -i "s/homeassistant-stubs==[0-9.]*/homeassistant-stubs==$NEW_VERSION/" "$SCRIPT_DIR/pyproject.toml"

# Update pytest-homeassistant-custom-component
sed -i "s/pytest-homeassistant-custom-component==[0-9.]*/pytest-homeassistant-custom-component==$PYTEST_HA_VERSION/" "$SCRIPT_DIR/pyproject.toml"

echo "Minimum HA version bumped to $NEW_VERSION in hacs.json and pyproject.toml files."
echo "pytest-homeassistant-custom-component updated to $PYTEST_HA_VERSION."

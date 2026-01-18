#!/bin/bash
# bump_min_ha_version.sh
# Usage: ./bump_min_ha_version.sh <ha_version>
# Example: ./bump_min_ha_version.sh 2025.3.0


set -e

# Determine the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"


CURRENT_HA_VERSION=$(grep -oP 'homeassistant==\K[0-9.]+' "$SCRIPT_DIR/pyproject.toml" | head -n1)

if [ $# -ne 1 ]; then
  echo "Usage: $0 <ha_version>"
  echo "Current minimum Home Assistant version is: $CURRENT_HA_VERSION"
  exit 1
fi

NEW_VERSION="$1"

# Update homeassistant version in hacs.json
sed -i "s/\"homeassistant\": \"[0-9.]*\"/\"homeassistant\": \"$NEW_VERSION\"/" "$SCRIPT_DIR/hacs.json"

# Update homeassistant version in pyproject.toml
sed -i "s/homeassistant==[0-9.]*/homeassistant==$NEW_VERSION/" "$SCRIPT_DIR/pyproject.toml"

# Update minimum HA version in README.md
sed -i "s/Minimum required Home Assistant version is: [0-9.]*/Minimum required Home Assistant version is: $NEW_VERSION/" "$SCRIPT_DIR/README.md"

echo "Minimum HA version bumped from $CURRENT_HA_VERSION to $NEW_VERSION in hacs.json, pyproject.toml, and README.md files."

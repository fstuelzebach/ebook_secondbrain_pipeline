#!/bin/bash

# -----------------------------
# CONFIG
# -----------------------------
OLD_NAME="ibooks_notion_pipeline"         # Current folder/project name
NEW_NAME="$1"                             # New project name, passed as argument
GITHUB_USERNAME="fstuelzebach"       # Your GitHub username

if [ -z "$NEW_NAME" ]; then
    echo "Usage: ./rename_project.sh <new_project_name>"
    exit 1
fi

# -----------------------------
# Step 1: Rename local folder
# -----------------------------
CURRENT_DIR=$(pwd)
PARENT_DIR=$(dirname "$CURRENT_DIR")

if [[ "$(basename "$CURRENT_DIR")" != "$OLD_NAME" ]]; then
    echo "Error: You must run this script from the $OLD_NAME folder"
    exit 1
fi

cd "$PARENT_DIR"
mv "$OLD_NAME" "$NEW_NAME"
cd "$NEW_NAME"
echo "✅ Folder renamed to $NEW_NAME"

# -----------------------------
# Step 2: Update pyproject.toml
# -----------------------------
if [ -f "pyproject.toml" ]; then
    sed -i '' "s/name = \"$OLD_NAME\"/name = \"$NEW_NAME\"/" pyproject.toml
    echo "✅ pyproject.toml updated"
fi

# -----------------------------
# Step 3: Update setup.py
# -----------------------------
if [ -f "setup.py" ]; then
    sed -i '' "s/name=['\"]$OLD_NAME['\"]/name='$NEW_NAME'/" setup.py
    echo "✅ setup.py updated"
fi

# -----------------------------
# Step 4: Update Git remote
# -----------------------------
if git rev-parse --git-dir > /dev/null 2>&1; then
    NEW_REMOTE_URL="https://github.com/$GITHUB_USERNAME/$NEW_NAME.git"
    git remote set-url origin "$NEW_REMOTE_URL"
    echo "✅ Git remote updated to $NEW_REMOTE_URL"
else
    echo "⚠️ No git repository found. Skipping git remote update."
fi

echo "🎉 Project rename complete!"

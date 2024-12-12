#!/bin/bash
set -ex

REPO_DIR="/mnt/repos"
EXTRA_ADDONS_DIR="/mnt/project-addons"
SSH_DIR="/root/.ssh"
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no"

# Ensure the SSH directory exists and is properly set up
mkdir -p $SSH_DIR
if [[ -f /mnt/secrets/ssh-privatekey ]]; then
  cp /mnt/secrets/ssh-privatekey $SSH_DIR/privatekey
  chmod 600 $SSH_DIR/privatekey
  eval "$(ssh-agent -s)"
  ssh-add $SSH_DIR/privatekey
fi

# Clear the /mnt/extra-addons directory
rm -rf $EXTRA_ADDONS_DIR/*
mkdir -p $EXTRA_ADDONS_DIR

# Function to clone or update a repository
clone_or_update_repo() {
  local repo_url="$1"
  local branch="$2"
  local commit="$3"
  local target_dir="$4"
  local username="$5"
  local password="$6"

  if [ -d "$target_dir/.git" ]; then
    echo "Repository $repo_url already exists. Fetching latest changes."
    cd "$target_dir"
    git fetch origin "$branch"
    if [ -n "$commit" ]; then
      git reset --hard --recurse-submodules "$commit"
    else
      git reset --hard --recurse-submodules origin/$branch
    fi
  else
    if [ -n "$username" ] && [ -n "$password" ]; then
      echo "Using password authentication for cloning repository $repo_url."
      repo_url_with_auth="https://$username:$password@${repo_url#https://}"
      git clone --recurse-submodules -b "$branch" "$repo_url_with_auth" "$target_dir"
    else
      echo "Using SSH or default authentication for cloning repository $repo_url."
      git clone --recurse-submodules -b "$branch" "$repo_url" "$target_dir"
    fi
    cd "$target_dir"
    if [ -n "$commit" ]; then
      git reset --hard --recurse-submodules "$commit"
    fi
  fi
}

# Iterate over addon repositories
for repo_config in /mnt/config/addon-repos/*.json; do
  REPO_NAME=$(jq -r '.name' "$repo_config")
  REPO_URL=$(jq -r '.url' "$repo_config")
  BRANCH=$(jq -r '.branch' "$repo_config")
  COMMIT=$(jq -r '.commit // empty' "$repo_config")
  SSH_SECRET_NAME=$(jq -r '.ssh-auth.secretName // empty' "$repo_config")
  USERNAME=$(jq -r '.passwordAuth.username // empty' "$repo_config")
  PASSWORD=$(jq -r '.passwordAuth.password // empty' "$repo_config")

  TARGET_DIR="$REPO_DIR/$REPO_NAME"

  # Configure SSH key if a specific secret is defined
  if [ -n "$SSH_SECRET_NAME" ]; then
    SECRET_KEY_PATH="/mnt/secrets/$SSH_SECRET_NAME"
    if [ -f "$SECRET_KEY_PATH" ]; then
      cp "$SECRET_KEY_PATH" $SSH_DIR/privatekey
      chmod 600 $SSH_DIR/privatekey
      ssh-add $SSH_DIR/privatekey
    fi
  fi

  # Clone or update the repository
  clone_or_update_repo "$REPO_URL" "$BRANCH" "$COMMIT" "$TARGET_DIR" "$USERNAME" "$PASSWORD"

  # Create symlinks for active addons
  ACTIVE_ADDONS=$(jq -r '.activeAddons[]?.name' "$repo_config")
  for addon in $ACTIVE_ADDONS; do
    ln -sfn "$TARGET_DIR/$addon" "$EXTRA_ADDONS_DIR/$addon"
  done

  # Reset SSH key to default after processing each repo
  if [ -f /mnt/secrets/ssh-privatekey ]; then
    cp /mnt/secrets/ssh-privatekey $SSH_DIR/privatekey
    chmod 600 $SSH_DIR/privatekey
    eval "$(ssh-agent -s)"
    ssh-add $SSH_DIR/privatekey
  fi

done


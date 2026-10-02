#!/bin/bash
# Remove the launchd agent and MDTab.app. Does not touch the repository itself.
set -u
LABEL="com.tdual.mdtab"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$HOME/Applications/MDTab.app"
echo "removed. If MDTab was your default .md app, pick another one from Finder > Get Info > Open with."

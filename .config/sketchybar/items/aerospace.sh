#!/bin/bash

aerospace=(
  icon.width=0
  label.width=0
  script="$PLUGIN_DIR/aerospace.sh"
  icon.font="$FONT:Bold:16.0"
  display=active
)

sketchybar --add event aerospace_workspace_change            \
           --add item aerospace left               \
           --set aerospace "${aerospace[@]}"           \
           --subscribe aerospace aerospace_workspace_change      \
                             mouse.clicked

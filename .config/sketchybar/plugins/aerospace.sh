#!/bin/bash

workspace_change() {
  source "$CONFIG_DIR/colors.sh"
  source "$CONFIG_DIR/icons.sh"

  WORKSPACE=$(aerospace list-workspaces --focused)
  MODE=$(aerospace list-windows --focused --format "%{window-id} %{app-name}")
  
  COLOR=$BAR_BORDER_COLOR
  ICON=""
  LABEL=""

  if [ -z "$MODE" ]; then
    ICON=""
    COLOR=$BAR_BORDER_COLOR
  else
    ICON="󱂬"
    LABEL="$WORKSPACE"
    COLOR=$BLUE
  fi

  args=(--bar border_color=$COLOR --animate sin 10 --set $NAME icon.color=$COLOR)

  [ -z "$LABEL" ] && args+=(label.width=0) \
                  || args+=(label="$LABEL" label.width=60)

  [ -z "$ICON" ] && args+=(icon.width=0) \
                 || args+=(icon="$ICON" icon.width=30)

  sketchybar -m "${args[@]}"
}


mouse_clicked() {
  aerospace layout toggle floating tiling
  workspace_change
}

case "$SENDER" in
  "mouse.clicked") mouse_clicked
  ;;
  "aerospace_workspace_change") workspace_change 
  ;;
esac

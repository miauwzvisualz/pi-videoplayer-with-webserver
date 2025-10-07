#!/bin/bash
# Video Player Slicing Configuration
# Edit these values to adjust the video slicing

# Slice 1 - First section to extract
# Format: width:height:x_position:y_position
SLICE1_WIDTH=1792
SLICE1_HEIGHT=64
SLICE1_X=0
SLICE1_Y=0

# Slice 2 - Second section to extract
SLICE2_WIDTH=1280
SLICE2_HEIGHT=64
SLICE2_X=1792
SLICE2_Y=0

# Output arrangement (vstack = vertical, hstack = horizontal)
ARRANGEMENT="vstack"

# Build the FFmpeg filter_complex string
# This crops two sections and stacks them
# Note: vstack requires same width, so we pad the second slice
SLICE1="${SLICE1_WIDTH}:${SLICE1_HEIGHT}:${SLICE1_X}:${SLICE1_Y}"
SLICE2="${SLICE2_WIDTH}:${SLICE2_HEIGHT}:${SLICE2_X}:${SLICE2_Y}"

if [ "$ARRANGEMENT" = "vstack" ]; then
    # For vertical stacking, pad shorter width to match longer (left-aligned)
    if [ $SLICE1_WIDTH -gt $SLICE2_WIDTH ]; then
        VIDEO_FILTER="[0:v]crop=${SLICE1}[top];[0:v]crop=${SLICE2},pad=${SLICE1_WIDTH}:${SLICE2_HEIGHT}:0:0[bottom];[top][bottom]vstack"
    elif [ $SLICE2_WIDTH -gt $SLICE1_WIDTH ]; then
        VIDEO_FILTER="[0:v]crop=${SLICE1},pad=${SLICE2_WIDTH}:${SLICE1_HEIGHT}:0:0[top];[0:v]crop=${SLICE2}[bottom];[top][bottom]vstack"
    else
        VIDEO_FILTER="[0:v]crop=${SLICE1}[top];[0:v]crop=${SLICE2}[bottom];[top][bottom]vstack"
    fi
else
    # Horizontal stacking doesn't need width adjustment
    VIDEO_FILTER="[0:v]crop=${SLICE1}[top];[0:v]crop=${SLICE2}[bottom];[top][bottom]hstack"
fi

export VIDEO_FILTER

#!/bin/bash

# Claude Code Notification Hook - Alert for Questions/Approvals
# Plays a sound and shows a desktop notification when Claude needs input

# Play a different sound than the completion sound to distinguish
# Using "Ping" for attention-getting notification vs "Glass" for completion
afplay /System/Library/Sounds/Ping.aiff

# Send desktop notification (macOS)
osascript -e 'display notification "Claude Code needs your input" with title "Claude Code" sound name "Ping"'

# Alternative notification methods (uncomment to use):

# Option 1: Text-to-speech announcement
# say "Claude Code needs your attention"

# Option 2: More specific text-to-speech based on context
# say "Claude is asking for approval"

# Option 3: Terminal bell (simple beep)
# echo -e "\a"

# Option 4: Custom sound for questions/approvals
# afplay "/path/to/your/question-sound.mp3"

# Option 5: Multiple pings for urgency
# afplay /System/Library/Sounds/Ping.aiff
# sleep 0.3
# afplay /System/Library/Sounds/Ping.aiff

# Option 6: Urgent system sounds for important approvals
# afplay /System/Library/Sounds/Sosumi.aiff  # Classic urgent Mac sound
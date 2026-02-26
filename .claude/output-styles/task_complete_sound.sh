#!/bin/bash

# Claude Code Stop Hook - Play completion sound
# Plays a system sound when Claude finishes a task

# Option 1: Play system sound (Glass, Ping, Purr, Sosumi, etc.)
afplay /System/Library/Sounds/Glass.aiff

# Option 2: Alternative system sounds you can use:
# afplay /System/Library/Sounds/Ping.aiff
# afplay /System/Library/Sounds/Purr.aiff  
# afplay /System/Library/Sounds/Sosumi.aiff

# Option 3: Text-to-speech notification (uncomment to use)
# say "Task completed"

# Option 4: Custom sound file (uncomment and update path)
# afplay "/path/to/your/custom/sound.mp3"
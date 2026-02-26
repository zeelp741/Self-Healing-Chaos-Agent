# Restart Dev Server

Restart the Vite development server for ZeelOS.

## Task

1. First, check if there's an existing Vite dev server running by looking for the process
2. If a Vite process exists, kill it gracefully
3. Start a new dev server in the background using `npm run dev`
4. Confirm the server has started successfully

## Commands to Run

```bash
# Kill existing vite process if running
pkill -f "vite" 2>/dev/null || true

# Start the dev server in the background
npm run dev
```

## Notes
- Run the dev server in the background so it doesn't block further Claude interactions
- The server runs on the default Vite port (usually 5173)
- If there are build errors, report them to the user

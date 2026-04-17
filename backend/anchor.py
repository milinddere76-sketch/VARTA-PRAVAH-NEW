import os

# State persistence for 24/7 anchor rotation consistency
STATE_FILE = "/app/anchor_state.txt"

def get_next_anchor():
    """
    Returns the next anchor gender based on persistent state.
    Used to maintain rotation even across worker restarts.
    """
    # 1. Initialize if missing (Default to Female)
    if not os.path.exists(STATE_FILE):
        print("📂 [ANCHOR] Initializing state file (Default: Female)")
        try:
            with open(STATE_FILE, "w") as f:
                f.write("female")
            return "female"
        except:
            return "female" # Fallback if disk is read-only

    # 2. Read Current State
    try:
        with open(STATE_FILE, "r") as f:
            current = f.read().strip().lower()
    except:
        current = "female" # Fallback

    # 3. Determine and Save Next State
    next_anchor = "male" if current == "female" else "female"
    
    try:
        with open(STATE_FILE, "w") as f:
            f.write(next_anchor)
    except Exception as e:
        print(f"⚠️ [ANCHOR] Failed to save state: {e}")

    return next_anchor

# NTE Auto-Fish Settings Guide

This guide details the meaning and adjustment methods for each setting in NTE Auto-Fish, helping you optimize the auto-fishing bot's performance according to your game environment and needs.

All settings can be adjusted in real-time in the **Settings** tab on the left side of the GUI. Remember to click `Save Settings` at the bottom to save your changes.

---

## 1. PID Tuning
The PID controller is used to smoothly and accurately track the target safe zone in the fishing mini-game. If the cursor is jittering severely or failing to keep up, adjust these parameters:

*   **Kp (Proportional Gain):** The base response strength. **A higher value means a stronger force moving the cursor toward the target**. If the cursor lags behind a fast-moving safe zone, increase Kp. If the cursor shakes violently back and forth around the target, Kp is too high, please lower it.
*   **Ki (Integral Gain):** Used to eliminate long-term steady-state errors. Usually kept small (e.g., 0.05). If the cursor is consistently slightly off the center, slightly increase Ki.
*   **Kd (Derivative Gain):** Used to suppress oscillation, acting as a damper. If the cursor always overshoots and swings back and forth, increase Kd.
*   **Deadband (px):** When the distance between the cursor and the center of the safe zone is within this range, the bot will not send any key presses. **This effectively prevents nervous jittering caused by over-correction near the center.** Recommended value is around 5.0.
*   **Integral limit:** Prevents the integral term from accumulating too much and causing windup. The default 150 is usually fine.
*   **Adaptive damping:** Highly recommended to be **Enabled**. When severe cursor oscillation is detected, the system will automatically reduce the Kp temporarily to quickly stabilize the cursor.

## 2. Vision & Detection
This section controls how the bot identifies game elements via screen colors. You may need to tweak these when facing lighting changes (e.g., sunset/night).

*   **Safe Zone HSV:** The color range of the target safe zone on the fishing bar.
*   **Cursor HSV:** The color range of the player's cursor on the fishing bar.
*   **Bite Trigger HSV:** The color range of the float/exclamation mark used to detect if a fish bites.
    *   *Tuning Tip: Expand the HSV options, adjust the Min/Max sliders, and observe the preview swatch to match the actual in-game color as closely as possible.*
*   **Edge ignore ratio:** The ratio of the left and right edges of the fishing bar to ignore (e.g., 0.02 means ignoring the outer 2% on both sides). This prevents misidentifying the bar's borders as the cursor or safe zone.
*   **Blue pixel trigger:** The minimum number of matched pixels in the detection region required to trigger a "fish bite". If the bot pulls too early (false positive), increase this value; if it misses bites, lower it.

## 3. Timing
Defines various delays and timeouts for the bot's state machine, ensuring smooth logic and preventing softlocks.

*   **Cast animation (s):** How long to wait after casting before starting bite detection. Detecting too early might cause false triggers.
*   **Bite timeout (s):** Max time to wait for a bite before automatically recasting.
*   **Lost frame limit:** During the struggle phase, if the cursor or safe zone is lost for this many consecutive frames, the struggle is considered over (fish caught or escaped).
*   **Result wait (s):** How long to wait before closing the result screen after catching a fish. Increase if the game doesn't register the close action in time.
*   **Waiting poll (s):** How often to check the screen while waiting for a bite.
*   **Tracking poll (s):** The update interval for PID and vision tracking during the struggle. Lower is more responsive but uses more CPU.
*   **Bait error limit:** How many consecutive cast errors before popping up an error dialog (usually due to running out of bait). Reaching this limit stops the bot to prevent an infinite loop.
*   **Max struggle (s):** The maximum allowed time for a single struggle phase (default 120s). Prevents softlocks if a bug occurs.

## 4. Input & Hotkeys
Manages in-game key bindings and the bot's global hotkeys.

*   **Key Bindings:**
    *   **Cast key:** Key to cast/hook (Default: F)
    *   **Move left/right:** Keys to pull the fish during the struggle (Default: A and D)
    *   **Exit key:** Key to close UI screens (Default: Esc)
*   **Result close:** How to close the result popup. Options: "Click center" or "Press exit key".
*   **Always on top:** Keeps the GUI window on top of the game window.
*   **Debug logging:** Writes detailed PID tracking data to `fishing_data.csv`. Only recommended for troubleshooting.
*   **Monitor:** If you have multiple monitors, select the one running the game to ensure the capture region is correct.
*   **Global Hotkeys:**
    *   **Toggle:** Hotkey to pause/resume the bot (Default: F8). Recommend using this before navigating game menus.
    *   **Stop:** Hotkey to completely stop the bot (Default: F12).

## 5. Humanization
Introduces randomness and imperfect reactions to make the bot look more like a human player, reducing the risk of anti-cheat detection.

*   **Humanize input:** Master switch. Strongly recommended to leave on.
*   **Key Pulse Timing:**
    *   **Pulse hold min/max:** Random duration range for holding a key during the struggle.
    *   **Pulse gap min/max:** Random delay range between key presses.
*   **Deadband Micro-corrections:**
    *   **Deadband taps:** When the cursor is in the deadband (perfectly aligned), occasionally send very short "micro-tap" inputs to mimic human hand jitter and subconscious adjustments.
    *   **Tap chance:** Probability of triggering a deadband tap per loop.
*   **Reaction Latency:**
    *   **Reaction min/max:** Simulates human visual reaction time. The bot waits this long before pressing a key after seeing a movement.
    *   **Reaction dist:** The distribution pattern of random delays (uniform, gaussian, exponential).
*   **PID Noise:** 
    *   Overlays random noise onto the perfect PID output, making the movement path less mechanical.
*   **Timing Jitter:** 
    *   Adds random fluctuation to fixed timings like cast animation and result wait.
*   **Adaptive Focus (Dynamic Speedup):**
    *   **High-level:** Simulates real player behavior: When the fish is far away and about to escape, a player's focus increases and reactions become faster. When enabled, larger errors automatically reduce the bot's latency and increase input frequency to pull the fish back quickly.
    *   **How it works:** The bot calculates an `intensity` factor based on how far the cursor is from the center of the safe zone. The larger the distance, the higher the intensity. This intensity then dynamically scales three key humanization parameters:
        *   **Reaction Latency:** The time the bot waits before reacting is shortened.
        *   **Pulse Gap:** The random delay *between* key presses is shortened, leading to more rapid inputs.
        *   **Pulse Hold:** The duration of each key press is *lengthened*, resulting in stronger, more decisive corrections.
    *   **Tuning Parameters:**
        *   **Latency focus min:** The minimum a reaction time can be scaled down to. A value of `0.3` means at maximum intensity, the reaction time will be `30%` of its normal value (i.e., a 70% reduction).
        *   **Pulse gap focus min:** The minimum a pulse gap can be scaled down to. A value of `0.2` means at maximum intensity, the gap between keys will be `20%` of its normal duration (i.e., an 80% reduction).
        *   **Pulse hold focus max:** The maximum a key press duration can be scaled up to. A value of `1.5` means at maximum intensity, a key will be held `50%` longer than its normal duration.
    *   **Tuning Advice:** For most users, the defaults are well-balanced. If you find the bot is still too slow to react to large, sudden movements of the fishing bar, you can slightly decrease the `Latency focus min` or `Pulse gap focus min`. If the bot overcorrects aggressively, consider slightly decreasing the `Pulse hold focus max`.

## 6. System & Updates

*   **Check for Updates:** Checks GitHub for new releases. If found, a "Download Update" button appears to open the release page in your browser.

---

**Troubleshooting:**
1. If the cursor always lags behind: Check if `Kp` under `PID Tuning` is too low, or if `Reaction Latency` under `Humanization` is too high.
2. If the bot stops hooking fish during sunset/night: Warm in-game lighting reduces blue pixels. Slightly lower the `Blue pixel trigger` in `Vision & Detection`, or recalibrate the `Safe Zone` and `Cursor` HSV ranges.
3. If the detection area needs adjustment: Trigger `recalibrate` from the console or the main GUI window.

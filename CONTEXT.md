# Ankimon Code Logic Overview

## Overview: Ankimon - A Pokémon-Themed Anki Addon

This is a gamification addon that transforms the Anki flashcard review experience into a Pokémon battle and collection game.

### Core Logic Flow:

#### 1. Battle System (Main Logic)
- **Trigger**: Every time you review a flashcard in Anki, it triggers `on_review_card()` at `__init__.py:~5000+`
- **Attack Calculation**: After reviewing N cards (configurable via `cards_per_round`), your Pokémon attacks:
  ```
  Damage = calc_atk_dmg(attacker_stats, defender_stats, move_power, type_effectiveness)
  ```
- **Type Effectiveness**: Uses Pokémon battle mechanics (e.g., Water beats Fire) from `eff_chart.json`
- **HP Management**: Both your Pokémon and wild Pokémon have HP bars that decrease with damage

#### 2. Progression System
- **Experience**: Defeating wild Pokémon grants XP based on their level/base stats
- **Leveling**: XP accumulates following Pokémon growth rate formulas from `ExpPokemonAddon.csv`
- **Evolution**: When level thresholds are reached, `evolve_pokemon()` triggers animations and stat upgrades
- **Move Learning**: Pokémon learn new moves at specific levels via `learnsets.json`

#### 3. Catch Mechanics
- **Wild Encounters**: Random Pokémon spawn based on enabled generations (Gen 1-9)
- **Capture**: Player can choose to catch or defeat wild Pokémon
- **Storage**: Caught Pokémon saved to `user_files/mypokemon.json`
- **Party Management**: Switch active Pokémon, rename, release, or export teams

#### 4. Additional Features
- **Gym Battles**: Special trainer battles after milestone card reviews (100+ cards)
- **Items/Badges**: Collectible achievements that unlock during gameplay
- **Pokédex**: Full database viewer with stats, types, and descriptions
- **Audio**: Battle cries and sound effects tied to game events

### Technical Architecture:

**Main Engine**: `__init__.py` (7,982 lines)
- PyQt6-based GUI overlays on Anki's reviewer
- Hooks into Anki's card review lifecycle
- Real-time damage calculations and animations
- JSON-based save system for persistence

**Data Pipeline**:
```
User Reviews Card → Battle Logic Triggered →
Damage Calculated → HP Updated →
XP Awarded → Level/Evolution Check →
Save State to JSON
```

**Key Algorithms**:
- Damage formula considers: base stats, move power, type matchups, critical hits, status effects
- Experience curves follow official Pokémon growth rates (fast/medium/slow)
- Random encounter generation with weighted probabilities by generation

The addon essentially creates a complete RPG layer on top of Anki's spaced repetition system, rewarding study sessions with tangible game progression.

## Current Task

**Goal**: Once gym battle initiates after 100 cards and user clicks "start gym battle", the current battle against wild pokemon should end, then start battle with gym pokemon until all are defeated.

## Implementation Details

### Changes Made

Modified the `_start()` function in `__init__.py:7907-7923` to properly transition from wild pokemon battle to gym battle:

**What was changed:**
1. Added `conf["ankimon_gym_enemy_ids"] = leader.get("team", [])` - Sets the gym leader's pokemon team
2. Added `conf["ankimon_gym_enemy_index"] = 0` - Resets index to spawn the first gym pokemon
3. Added call to `new_pokemon()` after dialog closes - Immediately ends current wild battle and spawns first gym pokemon

**How it works:**
- When user clicks "Start Gym Battle" button, the following sequence occurs:
  1. Gym active flag is set to True
  2. Gym leader metadata is stored (name, type, key, index)
  3. **NEW:** Gym enemy team IDs are loaded from the leader's team data
  4. **NEW:** Gym enemy index is set to 0 (first pokemon)
  5. Dialog closes
  6. **NEW:** `new_pokemon()` is called, which:
     - Detects gym is active via `_ankimon_is_gym_active()`
     - Uses gym enemy IDs and index from config
     - Spawns the first gym leader pokemon (ending any current wild battle)

- As gym pokemon are defeated, the existing logic at `__init__.py:2393-2427` handles:
  - Incrementing the gym enemy index
  - Spawning next gym pokemon
  - Detecting when all gym pokemon are defeated
  - Ending gym battle and returning to wild encounters

**Files Modified:**
- `/home/user/anki-addons-dev/1908235722/__init__.py` - Lines 7914-7923

---

## Update 2: Persistent Gym Progress Tracking

**Goal**: Continue with remaining 7 gym battles (8 total) per every 100 cards, remembering progress when Anki is closed and reopened.

### Changes Made

#### 1. Made gym card counter persistent (Lines 7729-7741)
**Before**: Counter stored in memory (`mw._ankimon_gym_counter`) - reset on program restart
**After**: Counter stored in collection config - persists across sessions

```python
def _ankimon_gym_state():
    """Get the current gym card counter from persistent storage."""
    conf = _ankimon_get_col_conf()
    if conf is None:
        return 0
    return int(conf.get("ankimon_gym_counter", 0))

def _ankimon_set_gym_state(val: int):
    """Set the gym card counter in persistent storage."""
    conf = _ankimon_get_col_conf()
    if conf is not None:
        conf["ankimon_gym_counter"] = int(val)
        mw.col.setMod()
```

#### 2. Increment gym index after gym completion (Lines 2413-2428)
**Before**: Gym index stayed the same after completion - would repeat same gym leader
**After**: Gym index increments to next leader (0→1→2...→7), cycles back to 0 after 8th gym

```python
# Gym battle complete! Increment gym index for next gym leader
current_gym_idx = int(conf.get("ankimon_gym_index", 0))
conf["ankimon_gym_index"] = current_gym_idx + 1
# ... existing cleanup code ...
# Reset card counter for next gym
conf["ankimon_gym_counter"] = 0
mw.col.setMod()
```

#### 3. Removed redundant counter reset (Line 7848)
**Reason**: Counter already resets when reaching 100 cards (line 7967), no need to reset again when starting gym

### How It Works Now

**Gym Progression Flow:**
1. User reviews 100 cards → Counter reaches 100
2. Counter auto-resets to 0, gym popup shows for current gym leader (based on `ankimon_gym_index`)
3. User clicks "Start Gym Battle" → Gym battle begins
4. User defeats all gym pokemon → Gym index increments, counter stays at 0
5. User continues reviewing cards → Counter increments (1, 2, 3... toward next 100)
6. Process repeats for all 8 gym leaders

**Persistence:**
- `ankimon_gym_counter` - Stored in collection config, persists across Anki restarts
- `ankimon_gym_index` - Stored in collection config, tracks which gym leader is next (0-7, then cycles)
- Progress is saved automatically via `mw.col.setMod()`

**User Experience:**
- Close Anki at 50 cards → Reopen → Still at 50 cards toward next gym
- Complete Gym 3 → Close Anki → Reopen → Next gym will be Gym 4
- Complete all 8 gyms → Cycles back to Gym 1 for continued play

**Files Modified:**
- `/home/user/anki-addons-dev/1908235722/__init__.py`:
  - Lines 7729-7741 (persistent counter functions)
  - Lines 2413-2428 (gym completion with index increment)
  - Line 7848 (removed redundant counter reset)

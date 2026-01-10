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

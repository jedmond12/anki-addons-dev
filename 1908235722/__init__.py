# -*- coding: utf-8 -*-

# Ankimon
# Copyright (C) 2024 Unlucky-Life

# This program is free software: you can redistribute it and/or modify
# by the Free Software Foundation
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# Important - If you redistribute it and/or modify this addon - must give contribution in Title and Code
# aswell as ask for permission to modify / redistribute this addon or the code itself

import os, sys
from aqt.utils import *
from typing import Optional
from aqt.qt import *
import anki
import threading
from anki.hooks import addHook, wrap
from aqt.reviewer import Reviewer
from aqt import mw, editor, gui_hooks


# --- Ankimon Gym helpers (safe) ---
def _ankimon_get_col_conf():
    try:
        col = getattr(mw, "col", None)
        return getattr(col, "conf", None) if col else None
    except Exception:
        return None

def _ankimon_is_gym_active():
    conf = _ankimon_get_col_conf()
    try:
        return bool(conf and conf.get("ankimon_gym_active", False))
    except Exception:
        return False

def _ankimon_is_elite_four_active():
    conf = _ankimon_get_col_conf()
    try:
        return bool(conf and conf.get("ankimon_elite_four_active", False))
    except Exception:
        return False

def _ankimon_is_champion_active():
    conf = _ankimon_get_col_conf()
    try:
        return bool(conf and conf.get("ankimon_champion_active", False))
    except Exception:
        return False

def _ankimon_get_gym_enemy_ids():
    conf = _ankimon_get_col_conf()
    try:
        ids = conf.get("ankimon_gym_enemy_ids", []) if conf else []
        return ids if isinstance(ids, list) else []
    except Exception:
        return []

def _ankimon_get_gym_enemy_index():
    conf = _ankimon_get_col_conf()
    try:
        idx = conf.get("ankimon_gym_enemy_index", 0) if conf else 0
        return int(idx) if idx is not None else 0
    except Exception:
        return 0

def _ankimon_get_elite_four_enemy_ids():
    conf = _ankimon_get_col_conf()
    try:
        ids = conf.get("ankimon_elite_four_enemy_ids", []) if conf else []
        return ids if isinstance(ids, list) else []
    except Exception:
        return []

def _ankimon_get_elite_four_pokemon_index():
    conf = _ankimon_get_col_conf()
    try:
        idx = conf.get("ankimon_elite_four_pokemon_index", 0) if conf else 0
        return int(idx) if idx is not None else 0
    except Exception:
        return 0

def _ankimon_get_champion_enemy_ids():
    conf = _ankimon_get_col_conf()
    try:
        ids = conf.get("ankimon_champion_enemy_ids", []) if conf else []
        return ids if isinstance(ids, list) else []
    except Exception:
        return []

def _ankimon_get_champion_pokemon_index():
    conf = _ankimon_get_col_conf()
    try:
        idx = conf.get("ankimon_champion_pokemon_index", 0) if conf else 0
        return int(idx) if idx is not None else 0
    except Exception:
        return 0

from aqt.qt import QDialog, QGridLayout, QLabel, QPixmap, QPainter, QFont, Qt, QVBoxLayout, QWidget, QAction
import random
import csv
from aqt.qt import *
import requests
import json
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtWebEngineWidgets import *
#from PyQt6.QtWidgets import QAction
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QDialog, QVBoxLayout, QLabel, QWidget
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
#from PyQt6.QtCore import QUrl
import base64
from aqt import utils
from PyQt6.QtGui import QSurfaceFormat
import aqt
import pathlib
from pathlib import Path
from typing import List, Union
import shutil
import distutils.dir_util
from anki.collection import Collection
import csv
import time, wave
import platform

#from .download_pokeapi_db import create_pokeapidb
config = mw.addonManager.getConfig(__name__)
#show config .json file

# Find current directory
addon_dir = Path(__file__).parents[0]
currdirname = addon_dir

# ============================================================================
# ANKIMON LOGGING SYSTEM
# ============================================================================

import datetime
import zipfile

# Logging configuration
LOG_DIR = addon_dir / "user_files" / "logs"
LOG_FILE = LOG_DIR / "ankimon.log"
LOG_MAX_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_KEEP_COUNT = 3  # Keep last 3 rotated logs

def _ankimon_ensure_log_dir():
    """Ensure log directory exists"""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"[Ankimon] Failed to create log directory: {e}")
        return False

def _ankimon_rotate_log():
    """Rotate log file if it exceeds max size"""
    try:
        if not LOG_FILE.exists():
            return
        if LOG_FILE.stat().st_size < LOG_MAX_SIZE:
            return

        # Rotate existing logs
        for i in range(LOG_KEEP_COUNT - 1, 0, -1):
            old_log = LOG_DIR / f"ankimon.log.{i}"
            new_log = LOG_DIR / f"ankimon.log.{i + 1}"
            if old_log.exists():
                if new_log.exists():
                    new_log.unlink()
                old_log.rename(new_log)

        # Move current log to .1
        rotated = LOG_DIR / "ankimon.log.1"
        if rotated.exists():
            rotated.unlink()
        LOG_FILE.rename(rotated)
    except Exception as e:
        print(f"[Ankimon] Log rotation failed: {e}")

def _ankimon_log(severity, prefix, message):
    """
    Write log message to file and console.

    Args:
        severity: INFO, WARN, ERROR
        prefix: Component name (e.g., AnkimonValidator, AnkimonUI, AnkimonBattle)
        message: Log message
    """
    try:
        _ankimon_ensure_log_dir()
        _ankimon_rotate_log()

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{severity}] [{prefix}] {message}\n"

        # Write to file
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line)

        # Also print to console
        print(f"[Ankimon] [{prefix}] {message}")
    except Exception as e:
        print(f"[Ankimon] Logging failed: {e}")

# ============================================================================
# SAFE JSON OPERATIONS
# ============================================================================

def _ankimon_safe_load_json(file_path, default_value=None):
    """
    Safely load JSON file with corruption handling.

    Args:
        file_path: Path to JSON file
        default_value: Value to return if file missing/corrupted

    Returns:
        Loaded JSON data or default_value
    """
    try:
        if not Path(file_path).exists():
            _ankimon_log("WARN", "SafeJSON", f"File not found: {file_path}")
            return default_value

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _ankimon_log("INFO", "SafeJSON", f"Successfully loaded: {file_path}")
            return data
    except json.JSONDecodeError as e:
        # Corrupted JSON - rename and return default
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(str(file_path) + f".corrupted_{timestamp}")
        try:
            Path(file_path).rename(backup_path)
            _ankimon_log("ERROR", "SafeJSON", f"Corrupted JSON renamed to: {backup_path}")
        except Exception as rename_err:
            _ankimon_log("ERROR", "SafeJSON", f"Failed to rename corrupted file: {rename_err}")
        return default_value
    except Exception as e:
        _ankimon_log("ERROR", "SafeJSON", f"Unexpected error loading {file_path}: {e}")
        return default_value

def _ankimon_safe_save_json(file_path, data, indent=2):
    """
    Safely save JSON file with error handling.

    Args:
        file_path: Path to JSON file
        data: Data to save
        indent: JSON indentation level

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure parent directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        _ankimon_log("INFO", "SafeJSON", f"Successfully saved: {file_path}")
        return True
    except Exception as e:
        _ankimon_log("ERROR", "SafeJSON", f"Failed to save {file_path}: {e}")
        return False

# ============================================================================
# STARTUP STATE VALIDATOR
# ============================================================================

def _ankimon_validate_startup():
    """
    Validate and initialize all required directories and JSON files.
    Run once on addon load before any UI windows are created.
    """
    _ankimon_log("INFO", "AnkimonValidator", "Starting startup validation...")

    # Required directories
    required_dirs = [
        addon_dir / "user_files",
        addon_dir / "user_files" / "data_files",
        addon_dir / "user_files" / "pkmn_data",
        addon_dir / "user_files" / "sprites",
        addon_dir / "user_files" / "sprites" / "front_default",
        addon_dir / "user_files" / "sprites" / "back_default",
        addon_dir / "user_files" / "sprites" / "front_default_gif",
        addon_dir / "user_files" / "sprites" / "back_default_gif",
        addon_dir / "user_files" / "sprites" / "shiny_front_default",
        addon_dir / "user_files" / "sprites" / "shiny_back_default_gif",
        addon_dir / "user_files" / "sprites" / "items",
        addon_dir / "user_files" / "sprites" / "badges",
        addon_dir / "user_files" / "logs",
        addon_dir / "user_files" / "debug_bundles",
    ]

    # Create missing directories
    for dir_path in required_dirs:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            _ankimon_log("INFO", "AnkimonValidator", f"Directory OK: {dir_path.name}")
        except Exception as e:
            _ankimon_log("ERROR", "AnkimonValidator", f"Failed to create {dir_path}: {e}")

    # Required JSON files with safe defaults
    required_json_files = {
        addon_dir / "user_files" / "party.json": [],
        addon_dir / "user_files" / "mainpokemon.json": {},
        addon_dir / "user_files" / "mypokemon.json": [],
        addon_dir / "user_files" / "items.json": [],
        addon_dir / "user_files" / "badges.json": [],
        addon_dir / "user_files" / "progression_stats.json": {
            "total_cards_reviewed": 0,
            "total_pokemon_caught": 0,
            "total_battles_won": 0,
            "current_round": 0,
            "gym_badges": [],
            "elite_four_defeated": [],
            "champion_defeated": False
        },
        addon_dir / "user_files" / "mega_state.json": {
            "owned_mega_stones": [],
            "mega_available": False,
            "mega_active_this_battle": False,
            "legendary_catches": {}
        }
    }

    # Create missing JSON files with defaults
    for file_path, default_data in required_json_files.items():
        if not file_path.exists():
            _ankimon_log("WARN", "AnkimonValidator", f"Creating missing file: {file_path.name}")
            _ankimon_safe_save_json(file_path, default_data)
        else:
            # Validate existing JSON is loadable
            loaded = _ankimon_safe_load_json(file_path, None)
            if loaded is None:
                # Corrupted - recreate with defaults
                _ankimon_log("WARN", "AnkimonValidator", f"Recreating corrupted file: {file_path.name}")
                _ankimon_safe_save_json(file_path, default_data)

    _ankimon_log("INFO", "AnkimonValidator", "Startup validation complete!")

# Run startup validation immediately
_ankimon_validate_startup()

# ============================================================================
# BATTLE STATE LOCK SYSTEM
# ============================================================================

# Battle state tracking to prevent interruptions
_ankimon_battle_state = "idle"  # idle | wild | trainer | gym | elite4 | champion

def _ankimon_get_battle_state():
    """Get current battle state"""
    global _ankimon_battle_state
    return _ankimon_battle_state

def _ankimon_set_battle_state(state):
    """
    Set battle state.

    Args:
        state: idle | wild | trainer | gym | elite4 | champion
    """
    global _ankimon_battle_state
    valid_states = ["idle", "wild", "trainer", "gym", "elite4", "champion"]
    if state not in valid_states:
        _ankimon_log("ERROR", "AnkimonBattle", f"Invalid battle state: {state}")
        return

    old_state = _ankimon_battle_state
    _ankimon_battle_state = state
    _ankimon_log("INFO", "AnkimonBattle", f"Battle state: {old_state} -> {state}")

def _ankimon_is_battle_locked():
    """Check if important battle is in progress (gym/elite4/champion)"""
    state = _ankimon_get_battle_state()
    return state in ["gym", "elite4", "champion"]

def _ankimon_can_start_new_battle():
    """Check if new battle can be started"""
    state = _ankimon_get_battle_state()
    if state != "idle":
        _ankimon_log("WARN", "AnkimonBattle", f"Cannot start new battle - current state: {state}")
        return False
    return True

def _ankimon_is_boss_battle_pending():
    """Check if gym/elite4/champion battle is pending (queued)"""
    try:
        conf = _ankimon_get_col_conf()
        if not conf:
            return False

        is_pending = (
            conf.get("ankimon_gym_pending", False) or
            conf.get("ankimon_elite_four_pending", False) or
            conf.get("ankimon_champion_pending", False)
        )

        if is_pending:
            _ankimon_log("INFO", "AnkimonBattle", "Boss battle is pending")

        return is_pending
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonBattle", f"Error checking pending boss battle: {e}")
        return False

def _ankimon_should_suppress_post_battle_ui():
    """
    Check if post-battle UI (Defeat/Catch screen) should be suppressed.
    Returns True if currently in or pending a boss battle.
    """
    # Suppress if actively in boss battle
    if _ankimon_is_battle_locked():
        _ankimon_log("INFO", "AnkimonUI", "Suppressing post-battle UI - active boss battle")
        return True

    # Suppress if boss battle is pending
    if _ankimon_is_boss_battle_pending():
        _ankimon_log("INFO", "AnkimonUI", "Suppressing post-battle UI - pending boss battle")
        return True

    return False

def _ankimon_close_post_battle_ui(reason=""):
    """
    Force-close any lingering post-battle UI (Defeat/Catch screens).

    Args:
        reason: Reason for closing (for logging)
    """
    _ankimon_log("INFO", "AnkimonUI", f"Closing post-battle UI: {reason}")

    global test_window

    # Close external window's post-battle screen
    try:
        if test_window and hasattr(test_window, 'isVisible') and test_window.isVisible():
            # Check if we're on the post-battle screen and switch back to battle view
            if hasattr(test_window, 'display_first_encounter'):
                # This will clear the post-battle UI and show normal battle view
                test_window.display_first_encounter()
                _ankimon_log("INFO", "AnkimonUI", "Cleared post-battle screen in external window")
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonUI", f"Error closing external window post-battle UI: {e}")

    # Note: The standalone display_dead_pokemon() dialog is modal and blocks,
    # so it's less likely to cause this issue. The main problem is the
    # external window's display_pokemon_death() screen.

def _ankimon_force_refresh_enemy_display():
    """
    Force complete refresh of enemy display in both external window and reviewer.
    Clears any cached sprites/movies and re-renders from current global state.

    This is critical when enemy changes (gym pokemon spawn, etc) to prevent
    stale UI showing old pokemon sprite/name/HP.
    """
    global test_window, pkmn_window
    global name, id, hp, max_hp, level

    try:
        battle_state = _ankimon_get_battle_state()
        _ankimon_log("INFO", "AnkimonUI", f"Force refreshing enemy display - battle_state={battle_state}, enemy_id={id}, enemy_name={name}, enemy_hp={hp}/{max_hp}")

        # Refresh external window
        if test_window is not None and pkmn_window is True:
            try:
                # Force complete redraw of battle view
                test_window.display_first_encounter()

                # Force Qt to process updates immediately
                test_window.update()
                test_window.repaint()

                # Ensure window is visible and on top
                test_window.show()
                test_window.raise_()
                test_window.activateWindow()

                _ankimon_log("INFO", "AnkimonUI", "External window enemy display refreshed successfully")
            except Exception as e:
                _ankimon_log("ERROR", "AnkimonUI", f"Error refreshing external window: {e}")

        # Refresh reviewer overlay (if visible)
        try:
            from aqt import mw
            if mw and mw.reviewer and hasattr(mw.reviewer, 'web'):
                # Force reviewer to update
                class Container(object):
                    pass
                reviewer = Container()
                reviewer.web = mw.reviewer.web
                update_life_bar(reviewer, 0, 0)
                _ankimon_log("INFO", "AnkimonUI", "Reviewer overlay refreshed")
        except Exception as e:
            _ankimon_log("ERROR", "AnkimonUI", f"Error refreshing reviewer: {e}")

    except Exception as e:
        _ankimon_log("ERROR", "AnkimonUI", f"Error in _ankimon_force_refresh_enemy_display: {e}")

def _ankimon_clear_stale_enemy_sprites():
    """
    Clear any stale enemy sprites/movies from UI before displaying new enemy.
    This prevents old pokemon from persisting on screen when enemy changes.
    """
    global test_window

    try:
        _ankimon_log("INFO", "AnkimonUI", "Clearing stale enemy sprites")

        if test_window is not None:
            # The display_first_encounter() method will create fresh widgets,
            # but we should ensure any old QMovie objects are properly stopped
            # to prevent them from continuing to play

            # Note: PyQt6 will automatically clean up old widgets when new ones
            # are created in display_first_encounter(), but stopping movies
            # explicitly is good practice
            _ankimon_log("INFO", "AnkimonUI", "Stale sprites cleared - new display will be created fresh")
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonUI", f"Error clearing stale sprites: {e}")

def _ankimon_transition_to_gym(reason=""):
    """
    Atomic transition to gym battle - ensures clean UI state transition.

    This function handles the complete transition from wild/trainer battle to gym battle:
    1. Clears stale enemy sprites
    2. Activates gym and sets battle state
    3. Spawns first gym Pokemon (updates all enemy vars)
    4. Forces complete UI refresh on all surfaces

    Args:
        reason: Description of why transition is happening (for logging)
    """
    global test_window, pkmn_window, id, name, hp, max_hp

    try:
        _ankimon_log("INFO", "AnkimonBattle", f"=== Transitioning to gym battle ({reason}) ===")

        # Get gym configuration
        conf = _ankimon_get_col_conf()
        if not conf:
            _ankimon_log("ERROR", "AnkimonBattle", "Cannot transition to gym - config not available")
            return False

        leader_name = conf.get("ankimon_gym_leader_name", "Unknown Leader")
        enemy_ids = conf.get("ankimon_gym_enemy_ids") or []

        _ankimon_log("INFO", "AnkimonBattle", f"Gym transition: leader={leader_name}, team_size={len(enemy_ids)}, first_pokemon_id={enemy_ids[0] if enemy_ids else 'none'}")

        # Step 1: Clear stale enemy sprites
        _ankimon_clear_stale_enemy_sprites()

        # Step 2: Activate gym and set battle state BEFORE spawning
        # This ensures generate_random_pokemon() sees gym_active=True
        conf["ankimon_gym_active"] = True
        conf["ankimon_gym_pending"] = False
        conf["ankimon_gym_enemy_index"] = 0
        mw.col.setMod()
        _ankimon_log("INFO", "AnkimonBattle", "Gym activated: active=True, pending=False, index=0")

        # Set battle state to gym
        _ankimon_set_battle_state("gym")
        _ankimon_log("INFO", "AnkimonBattle", "Battle state set to: gym")

        # Step 3: Spawn first gym Pokemon (bypasses battle lock)
        try:
            tooltipWithColour(f"Gym Battle vs {leader_name} Starting!", "#FFD700")
        except:
            pass

        _ankimon_log("INFO", "AnkimonBattle", "Spawning first gym Pokemon...")
        if not _ankimon_spawn_special_battle_pokemon():
            _ankimon_log("ERROR", "AnkimonBattle", "Failed to spawn gym Pokemon")
            return False

        # Log the new enemy state for debugging
        _ankimon_log("INFO", "AnkimonBattle", f"Gym Pokemon spawned: id={id}, name={name}, hp={hp}/{max_hp}")

        # Step 4: Force complete refresh of ALL views (if external window enabled)
        if pkmn_window is True:
            from aqt.qt import QTimer

            # Immediate refresh
            _ankimon_force_refresh_enemy_display()
            _ankimon_log("INFO", "AnkimonUI", "Immediate refresh triggered")

            # Delayed refreshes to ensure update propagates
            def _delayed_refresh():
                try:
                    _ankimon_log("INFO", "AnkimonUI", "Delayed refresh executing")
                    _ankimon_force_refresh_enemy_display()
                except Exception as e:
                    _ankimon_log("ERROR", "AnkimonUI", f"Delayed refresh error: {e}")

            QTimer.singleShot(100, _delayed_refresh)
            QTimer.singleShot(250, _delayed_refresh)

            # Final complete refresh of all views
            def _final_refresh():
                try:
                    _ankimon_log("INFO", "AnkimonUI", "Final complete refresh executing")
                    _ankimon_refresh_all_views()
                except Exception as e:
                    _ankimon_log("ERROR", "AnkimonUI", f"Final refresh error: {e}")

            QTimer.singleShot(300, _final_refresh)

        _ankimon_log("INFO", "AnkimonBattle", "=== Gym transition complete ===")
        return True

    except Exception as e:
        _ankimon_log("ERROR", "AnkimonBattle", f"Error in gym transition: {e}")
        import traceback
        traceback.print_exc()
        return False

def _ankimon_transition_to_elite_four(reason=""):
    """
    Atomic transition to Elite Four battle - ensures clean UI state transition.

    This function handles the complete transition from wild/trainer battle to Elite Four battle:
    1. Clears stale enemy sprites
    2. Activates Elite Four and sets battle state
    3. Spawns first Elite Four Pokemon (updates all enemy vars)
    4. Forces complete UI refresh on all surfaces

    Args:
        reason: Description of why transition is happening (for logging)
    """
    global test_window, pkmn_window, id, name, hp, max_hp

    try:
        _ankimon_log("INFO", "AnkimonBattle", f"=== Transitioning to Elite Four battle ({reason}) ===")

        # Get Elite Four configuration
        conf = _ankimon_get_col_conf()
        if not conf:
            _ankimon_log("ERROR", "AnkimonBattle", "Cannot transition to Elite Four - config not available")
            return False

        member_name = conf.get("ankimon_elite_four_member_name", "Unknown Member")
        enemy_ids = conf.get("ankimon_elite_four_enemy_ids") or []

        _ankimon_log("INFO", "AnkimonBattle", f"Elite Four transition: member={member_name}, team_size={len(enemy_ids)}, first_pokemon_id={enemy_ids[0] if enemy_ids else 'none'}")

        # Step 1: Clear stale enemy sprites
        _ankimon_clear_stale_enemy_sprites()

        # Step 2: Activate Elite Four and set battle state BEFORE spawning
        conf["ankimon_elite_four_active"] = True
        conf["ankimon_elite_four_pending"] = False
        conf["ankimon_elite_four_pokemon_index"] = 0
        mw.col.setMod()
        _ankimon_log("INFO", "AnkimonBattle", "Elite Four activated: active=True, pending=False, index=0")

        # Set battle state to elite4
        _ankimon_set_battle_state("elite4")
        _ankimon_log("INFO", "AnkimonBattle", "Battle state set to: elite4")

        # Step 3: Spawn first Elite Four Pokemon (bypasses battle lock)
        try:
            tooltipWithColour(f"Elite Four {member_name} Battle Starting!", "#FFD700")
        except:
            pass

        _ankimon_log("INFO", "AnkimonBattle", "Spawning first Elite Four Pokemon...")
        if not _ankimon_spawn_special_battle_pokemon():
            _ankimon_log("ERROR", "AnkimonBattle", "Failed to spawn Elite Four Pokemon")
            return False

        # Log the new enemy state for debugging
        _ankimon_log("INFO", "AnkimonBattle", f"Elite Four Pokemon spawned: id={id}, name={name}, hp={hp}/{max_hp}")

        # Step 4: Force complete refresh of ALL views (if external window enabled)
        if pkmn_window is True:
            from aqt.qt import QTimer

            # Immediate refresh
            _ankimon_force_refresh_enemy_display()
            _ankimon_log("INFO", "AnkimonUI", "Immediate refresh triggered")

            # Delayed refreshes to ensure update propagates
            def _delayed_refresh():
                try:
                    _ankimon_log("INFO", "AnkimonUI", "Delayed refresh executing")
                    _ankimon_force_refresh_enemy_display()
                except Exception as e:
                    _ankimon_log("ERROR", "AnkimonUI", f"Delayed refresh error: {e}")

            QTimer.singleShot(100, _delayed_refresh)
            QTimer.singleShot(250, _delayed_refresh)

            # Final complete refresh of all views
            def _final_refresh():
                try:
                    _ankimon_log("INFO", "AnkimonUI", "Final complete refresh executing")
                    _ankimon_refresh_all_views()
                except Exception as e:
                    _ankimon_log("ERROR", "AnkimonUI", f"Final refresh error: {e}")

            QTimer.singleShot(300, _final_refresh)

        _ankimon_log("INFO", "AnkimonBattle", "=== Elite Four transition complete ===")
        return True

    except Exception as e:
        _ankimon_log("ERROR", "AnkimonBattle", f"Error in Elite Four transition: {e}")
        import traceback
        traceback.print_exc()
        return False

def _ankimon_transition_to_champion(reason=""):
    """
    Atomic transition to Champion battle - ensures clean UI state transition.

    This function handles the complete transition from wild/trainer battle to Champion battle:
    1. Clears stale enemy sprites
    2. Activates Champion and sets battle state
    3. Spawns first Champion Pokemon (updates all enemy vars)
    4. Forces complete UI refresh on all surfaces

    Args:
        reason: Description of why transition is happening (for logging)
    """
    global test_window, pkmn_window, id, name, hp, max_hp

    try:
        _ankimon_log("INFO", "AnkimonBattle", f"=== Transitioning to Champion battle ({reason}) ===")

        # Get Champion configuration
        conf = _ankimon_get_col_conf()
        if not conf:
            _ankimon_log("ERROR", "AnkimonBattle", "Cannot transition to Champion - config not available")
            return False

        enemy_ids = conf.get("ankimon_champion_enemy_ids") or []

        _ankimon_log("INFO", "AnkimonBattle", f"Champion transition: team_size={len(enemy_ids)}, first_pokemon_id={enemy_ids[0] if enemy_ids else 'none'}, enemy_id_before={id}, enemy_name_before={name}, enemy_hp_before={hp}")

        # Step 1: Clear stale enemy sprites
        _ankimon_log("INFO", "AnkimonBattle", "Clearing stale enemy sprites...")
        _ankimon_clear_stale_enemy_sprites()

        # Step 2: CRITICAL - Close any lingering post-battle UI
        _ankimon_log("INFO", "AnkimonBattle", "Closing post-battle UI...")
        _ankimon_close_post_battle_ui("starting Champion battle")

        # Step 3: Activate Champion and set battle state BEFORE spawning
        conf["ankimon_champion_active"] = True
        conf["ankimon_champion_pending"] = False
        conf["ankimon_champion_pokemon_index"] = 0
        mw.col.setMod()
        _ankimon_log("INFO", "AnkimonBattle", "Champion activated: active=True, pending=False, index=0")

        # Set battle state to champion
        _ankimon_set_battle_state("champion")
        _ankimon_log("INFO", "AnkimonBattle", "Battle state set to: champion")

        # Step 4: Spawn first Champion Pokemon (bypasses battle lock)
        try:
            tooltipWithColour("Champion Cynthia Battle Starting!", "#FFD700")
        except:
            pass

        _ankimon_log("INFO", "AnkimonBattle", "Spawning first Champion Pokemon...")
        if not _ankimon_spawn_special_battle_pokemon():
            _ankimon_log("ERROR", "AnkimonBattle", "Failed to spawn Champion Pokemon")
            return False

        # Log the new enemy state for debugging
        _ankimon_log("INFO", "AnkimonBattle", f"Champion Pokemon spawned: id={id}, name={name}, hp={hp}/{max_hp}")

        # Step 5: Force complete refresh of ALL views (if external window enabled)
        if pkmn_window is True:
            from aqt.qt import QTimer

            # Immediate refresh
            _ankimon_force_refresh_enemy_display()
            _ankimon_log("INFO", "AnkimonUI", "Immediate refresh triggered")

            # Delayed refreshes to ensure update propagates
            def _delayed_refresh():
                try:
                    _ankimon_log("INFO", "AnkimonUI", "Delayed refresh executing")
                    _ankimon_force_refresh_enemy_display()
                except Exception as e:
                    _ankimon_log("ERROR", "AnkimonUI", f"Delayed refresh error: {e}")

            QTimer.singleShot(100, _delayed_refresh)
            QTimer.singleShot(250, _delayed_refresh)

            # Final complete refresh of all views
            def _final_refresh():
                try:
                    _ankimon_log("INFO", "AnkimonUI", "Final complete refresh executing")
                    _ankimon_refresh_all_views()
                except Exception as e:
                    _ankimon_log("ERROR", "AnkimonUI", f"Final refresh error: {e}")

            QTimer.singleShot(400, _final_refresh)

        _ankimon_log("INFO", "AnkimonBattle", "Champion transition completed successfully")
        return True

    except Exception as e:
        _ankimon_log("ERROR", "AnkimonBattle", f"Error in Champion transition: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# ROSTER VALIDATOR (DEV TOOL)
# ============================================================================

def _ankimon_validate_rosters():
    """
    Dev tool to validate all Elite Four and Champion rosters for duplicates.
    Prints results to console and shows summary dialog.
    """
    try:
        print("\n" + "="*60)
        print("ANKIMON ROSTER VALIDATOR")
        print("="*60)

        errors = []
        warnings = []

        # Elite Four rosters
        elite_four_members = [
            {"key": "aaron", "name": "Aaron", "type": "Bug", "team": [269, 212, 416, 214, 452]},
            {"key": "bertha", "name": "Bertha", "type": "Ground", "team": [195, 185, 340, 450, 31]},
            {"key": "flint", "name": "Flint", "type": "Fire", "team": [392, 229, 78, 136, 467]},
            {"key": "lucian", "name": "Lucian", "type": "Psychic", "team": [122, 437, 178, 561, 475]}
        ]

        print("\nELITE FOUR ROSTERS:")
        print("-" * 60)
        for member in elite_four_members:
            team = member["team"]
            print(f"\n{member['name']} ({member['type']} type):")
            print(f"  Roster: {team}")
            print(f"  Count: {len(team)} Pokemon")

            # Check for duplicates
            if len(team) != len(set(team)):
                duplicates = [x for i, x in enumerate(team) if x in team[:i]]
                error_msg = f"  ⚠️  DUPLICATE IDs FOUND: {duplicates}"
                print(error_msg)
                errors.append(f"{member['name']}: Duplicate Pokemon IDs {duplicates}")
            else:
                print("  ✅ No duplicates")

            # Check for empty roster
            if not team:
                warning_msg = "  ⚠️  WARNING: Empty roster"
                print(warning_msg)
                warnings.append(f"{member['name']}: Empty roster")

        # Champion roster
        champion_team = [442, 407, 350, 445, 59, 448]  # Spiritomb, Roserade, Milotic, Garchomp, Arcanine, Lucario

        print("\n" + "-" * 60)
        print("\nCHAMPION ROSTER:")
        print("-" * 60)
        print(f"\nChampion Cynthia:")
        print(f"  Roster: {champion_team}")
        print(f"  Count: {len(champion_team)} Pokemon")

        # Check for duplicates
        if len(champion_team) != len(set(champion_team)):
            duplicates = [x for i, x in enumerate(champion_team) if x in champion_team[:i]]
            error_msg = f"  ⚠️  DUPLICATE IDs FOUND: {duplicates}"
            print(error_msg)
            errors.append(f"Champion Cynthia: Duplicate Pokemon IDs {duplicates}")
        else:
            print("  ✅ No duplicates")

        # Check for empty roster
        if not champion_team:
            warning_msg = "  ⚠️  WARNING: Empty roster"
            print(warning_msg)
            warnings.append("Champion Cynthia: Empty roster")

        # Check current battle rosters (if in config)
        print("\n" + "-" * 60)
        print("\nCURRENT BATTLE STATE:")
        print("-" * 60)
        conf = _ankimon_get_col_conf()
        if conf:
            # Elite Four active roster
            e4_ids = conf.get("ankimon_elite_four_enemy_ids", [])
            if e4_ids:
                print(f"\nElite Four (active): {e4_ids}")
                if len(e4_ids) != len(set(e4_ids)):
                    duplicates = [x for i, x in enumerate(e4_ids) if x in e4_ids[:i]]
                    error_msg = f"  ⚠️  ACTIVE BATTLE HAS DUPLICATES: {duplicates}"
                    print(error_msg)
                    errors.append(f"Elite Four (active battle): Duplicate IDs {duplicates}")
                else:
                    print("  ✅ No duplicates")

            # Champion active roster
            champ_ids = conf.get("ankimon_champion_enemy_ids", [])
            if champ_ids:
                print(f"\nChampion (active): {champ_ids}")
                if len(champ_ids) != len(set(champ_ids)):
                    duplicates = [x for i, x in enumerate(champ_ids) if x in champ_ids[:i]]
                    error_msg = f"  ⚠️  ACTIVE BATTLE HAS DUPLICATES: {duplicates}"
                    print(error_msg)
                    errors.append(f"Champion (active battle): Duplicate IDs {duplicates}")
                else:
                    print("  ✅ No duplicates")

            if not e4_ids and not champ_ids:
                print("\nNo active battles")

        print("\n" + "="*60)
        print("VALIDATION SUMMARY:")
        print("="*60)

        if errors:
            print(f"\n❌ ERRORS FOUND: {len(errors)}")
            for error in errors:
                print(f"  - {error}")
        else:
            print("\n✅ No errors found")

        if warnings:
            print(f"\n⚠️  WARNINGS: {len(warnings)}")
            for warning in warnings:
                print(f"  - {warning}")

        print("\n" + "="*60 + "\n")

        # Show summary dialog
        summary = "ROSTER VALIDATION RESULTS\n\n"
        if errors:
            summary += f"❌ {len(errors)} ERROR(S) FOUND:\n"
            for error in errors:
                summary += f"  • {error}\n"
        else:
            summary += "✅ No duplicate Pokemon found in rosters\n"

        if warnings:
            summary += f"\n⚠️  {len(warnings)} WARNING(S):\n"
            for warning in warnings:
                summary += f"  • {warning}\n"

        summary += "\nSee console for full details."

        from aqt.utils import showInfo
        showInfo(summary, title="Roster Validator")

    except Exception as e:
        error_msg = f"Error during roster validation: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        try:
            from aqt.utils import showWarning
            showWarning(error_msg)
        except:
            pass

# ============================================================================
# DEBUG BUNDLE EXPORT
# ============================================================================

def _ankimon_export_debug_bundle():
    """
    Export debug bundle with logs, config, and state files.
    Creates a ZIP file in user_files/debug_bundles/
    """
    try:
        _ankimon_log("INFO", "AnkimonDebugBundle", "Creating debug bundle...")

        # Create debug bundle directory
        bundle_dir = addon_dir / "user_files" / "debug_bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"ankimon_debug_{timestamp}.zip"
        zip_path = bundle_dir / zip_filename

        # Collect system info
        system_info = []
        system_info.append(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        system_info.append(f"Platform: {platform.system()} {platform.release()}")
        system_info.append(f"Python Version: {sys.version}")
        try:
            system_info.append(f"Anki Version: {anki.version}")
        except:
            system_info.append("Anki Version: Unknown")
        try:
            system_info.append(f"Qt Version: {QT_VERSION_STR}")
        except:
            system_info.append("Qt Version: Unknown")
        system_info.append(f"Addon Directory: {addon_dir}")

        # Files to include in bundle
        files_to_include = {
            # Logs
            "logs/ankimon.log": LOG_FILE,
            "logs/ankimon.log.1": LOG_DIR / "ankimon.log.1",
            "logs/ankimon.log.2": LOG_DIR / "ankimon.log.2",
            "logs/ankimon.log.3": LOG_DIR / "ankimon.log.3",
            # State files
            "state/party.json": addon_dir / "user_files" / "party.json",
            "state/mainpokemon.json": mainpokemon_path,
            "state/mypokemon.json": mypokemon_path,
            "state/items.json": itembag_path,
            "state/badges.json": badgebag_path,
            "state/progression_stats.json": progression_stats_path,
            "state/mega_state.json": mega_state_path,
            # Config
            "config/config.json": addon_dir / "config.json",
            "config/meta.json": addon_dir / "meta.json",
        }

        # Create ZIP file
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add system info
            zipf.writestr("system_info.txt", "\n".join(system_info))

            # Add files
            for arcname, file_path in files_to_include.items():
                try:
                    if Path(file_path).exists():
                        zipf.write(file_path, arcname)
                        _ankimon_log("INFO", "AnkimonDebugBundle", f"Added: {arcname}")
                    else:
                        _ankimon_log("WARN", "AnkimonDebugBundle", f"Skipped (not found): {arcname}")
                except Exception as e:
                    _ankimon_log("WARN", "AnkimonDebugBundle", f"Failed to add {arcname}: {e}")

        _ankimon_log("INFO", "AnkimonDebugBundle", f"Debug bundle created: {zip_path}")

        # Show success message to user
        from aqt.utils import showInfo
        msg = f"Debug bundle created successfully!\n\n"
        msg += f"Location: {zip_path}\n\n"
        msg += "This bundle contains logs, config, and state files.\n"
        msg += "Share this file when reporting issues."
        showInfo(msg)

        # Optionally open folder
        try:
            if platform.system() == "Windows":
                os.startfile(bundle_dir)
            elif platform.system() == "Darwin":  # macOS
                os.system(f'open "{bundle_dir}"')
            else:  # Linux
                os.system(f'xdg-open "{bundle_dir}"')
        except Exception as e:
            _ankimon_log("WARN", "AnkimonDebugBundle", f"Could not open folder: {e}")

        return True

    except Exception as e:
        _ankimon_log("ERROR", "AnkimonDebugBundle", f"Failed to create debug bundle: {e}")
        from aqt.utils import showWarning
        showWarning(f"Failed to create debug bundle:\n{str(e)}")
        return False

# ============================================================================
# CENTRALIZED UI REFRESH SYSTEM
# ============================================================================

# Global window references (will be set after windows are created)
_ankimon_windows = {
    "test_window": None,
    "pokecollection_win": None,
    "complete_pokedex": None,
    "item_window": None,
    "reviewer": None,
}

def _ankimon_register_window(name, window_obj):
    """Register a window for centralized refresh"""
    global _ankimon_windows
    _ankimon_windows[name] = window_obj
    _ankimon_log("INFO", "AnkimonUI", f"Registered window: {name}")

def _ankimon_refresh_all_views():
    """
    Refresh all open Ankimon windows and views.
    Safe to call anytime - handles missing/closed windows gracefully.
    """
    _ankimon_log("INFO", "AnkimonUI", "Refreshing all views...")

    global _ankimon_windows

    # Refresh test window (main battle window)
    try:
        if _ankimon_windows.get("test_window") and hasattr(_ankimon_windows["test_window"], "isVisible"):
            if _ankimon_windows["test_window"].isVisible():
                if hasattr(_ankimon_windows["test_window"], "update"):
                    _ankimon_windows["test_window"].update()
                    _ankimon_log("INFO", "AnkimonUI", "Refreshed test_window")
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonUI", f"Failed to refresh test_window: {e}")

    # Refresh Pokemon Collection window
    try:
        if _ankimon_windows.get("pokecollection_win") and hasattr(_ankimon_windows["pokecollection_win"], "isVisible"):
            if _ankimon_windows["pokecollection_win"].isVisible():
                if hasattr(_ankimon_windows["pokecollection_win"], "refresh"):
                    _ankimon_windows["pokecollection_win"].refresh()
                    _ankimon_log("INFO", "AnkimonUI", "Refreshed pokecollection_win")
                elif hasattr(_ankimon_windows["pokecollection_win"], "update"):
                    _ankimon_windows["pokecollection_win"].update()
                    _ankimon_log("INFO", "AnkimonUI", "Updated pokecollection_win")
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonUI", f"Failed to refresh pokecollection_win: {e}")

    # Refresh Pokedex window
    try:
        if _ankimon_windows.get("complete_pokedex") and hasattr(_ankimon_windows["complete_pokedex"], "isVisible"):
            if _ankimon_windows["complete_pokedex"].isVisible():
                if hasattr(_ankimon_windows["complete_pokedex"], "refresh"):
                    _ankimon_windows["complete_pokedex"].refresh()
                    _ankimon_log("INFO", "AnkimonUI", "Refreshed complete_pokedex")
                elif hasattr(_ankimon_windows["complete_pokedex"], "update"):
                    _ankimon_windows["complete_pokedex"].update()
                    _ankimon_log("INFO", "AnkimonUI", "Updated complete_pokedex")
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonUI", f"Failed to refresh complete_pokedex: {e}")

    # Refresh Item window
    try:
        if _ankimon_windows.get("item_window") and hasattr(_ankimon_windows["item_window"], "isVisible"):
            if _ankimon_windows["item_window"].isVisible():
                if hasattr(_ankimon_windows["item_window"], "refresh"):
                    _ankimon_windows["item_window"].refresh()
                    _ankimon_log("INFO", "AnkimonUI", "Refreshed item_window")
                elif hasattr(_ankimon_windows["item_window"], "update"):
                    _ankimon_windows["item_window"].update()
                    _ankimon_log("INFO", "AnkimonUI", "Updated item_window")
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonUI", f"Failed to refresh item_window: {e}")

    # Refresh reviewer UI overlay
    try:
        if mw and hasattr(mw, "reviewer") and mw.reviewer:
            if hasattr(mw.reviewer, "web"):
                # Trigger reviewer refresh
                mw.reviewer.web.eval("if (typeof refreshUI === 'function') { refreshUI(); }")
                _ankimon_log("INFO", "AnkimonUI", "Refreshed reviewer overlay")
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonUI", f"Failed to refresh reviewer: {e}")

    _ankimon_log("INFO", "AnkimonUI", "Refresh complete!")

def check_folders_exist(parent_directory, folder):
    folder_path = os.path.join(parent_directory, folder)
    if not os.path.isdir(folder_path):
       return False
    else:
       return True

def check_file_exists(folder, filename):
    file_path = os.path.join(folder, filename)
    if os.path.isfile(file_path):
        return True
    else:
        return False

#safe route for updates
user_path = addon_dir / "user_files"
user_path_data = addon_dir / "user_files" / "data_files"
user_path_sprites = addon_dir / "user_files" / "sprites"

# Assign Pokemon Image folder directory name
pkmnimgfolder = addon_dir / "user_files" / "sprites"
backdefault = addon_dir / "user_files" / "sprites" / "back_default"
frontdefault = addon_dir / "user_files" / "sprites" / "front_default"
backdefault_gif = addon_dir / "user_files" / "sprites" / "back_default_gif"
frontdefault_gif = addon_dir / "user_files" / "sprites" / "front_default_gif"

# Shiny sprite paths (actual directory structure from repository)
shiny_front_default = addon_dir / "user_files" / "sprites" / "shiny_front_default"  # Contains GIFs for enemy Pokémon
shiny_back_default_gif = addon_dir / "user_files" / "sprites" / "shiny_back_default_gif"  # Contains GIFs for player Pokémon
#Assign saved Pokemon Directory
mypokemon_path = addon_dir / "user_files" / "mypokemon.json"
mainpokemon_path = addon_dir / "user_files" / "mainpokemon.json"
battlescene_path = addon_dir / "addon_sprites" / "battle_scenes"
battlescene_path_without_dialog = addon_dir / "addon_sprites" / "battle_scenes_without_dialog"
enemy_battles_path = addon_dir / "addon_sprites" / "enemy_battles"
battle_ui_path = addon_dir / "pkmnbattlescene - UI_transp"
type_style_file = addon_dir / "addon_files" / "types.json"
next_lvl_file_path = addon_dir / "addon_files" / "ExpPokemonAddon.csv"
berries_path = addon_dir / "user_files" / "sprites" / "berries"
background_dialog_image_path  = addon_dir / "background_dialog_image.png"
pokedex_image_path = addon_dir / "addon_sprites" / "pokedex_template.jpg"
evolve_image_path = addon_dir / "addon_sprites" / "evo_temp.jpg"
learnset_path = addon_dir / "user_files" / "data_files" / "learnsets.json"
pokedex_path = addon_dir / "user_files" / "data_files" / "pokedex.json"
moves_file_path = addon_dir / "user_files" / "data_files" / "moves.json"
items_path = addon_dir / "user_files" / "sprites" / "items"
badges_path = addon_dir / "user_files" / "sprites" / "badges"
itembag_path = addon_dir / "user_files" / "items.json"
badgebag_path = addon_dir / "user_files" / "badges.json"
progression_stats_path = addon_dir / "user_files" / "progression_stats.json"
mega_state_path = addon_dir / "user_files" / "mega_state.json"
pokenames_lang_path = addon_dir / "user_files" / "data_files" / "pokemon_species_names.csv"
pokedesc_lang_path = addon_dir / "user_files" / "data_files" / "pokemon_species_flavor_text.csv"
pokeapi_db_path = user_path_data / "pokeapi_db.json"
starters_path = addon_dir / "addon_files" / "starters.json"
eff_chart_html_path = addon_dir / "addon_files" / "eff_chart_html.html"
effectiveness_chart_file_path = addon_dir / "addon_files" / "eff_chart.json"
table_gen_id_html_path = addon_dir / "addon_files" / "table_gen_id.html"
icon_path = addon_dir / "addon_sprites" / "icons" / "poke.png"
sound_list_path = addon_dir / "addon_files" / "sound_list.json"
badges_list_path = addon_dir / "addon_files" / "badges.json"
items_list_path = addon_dir / "addon_files" / "items.json"
rate_path = addon_dir / "user_files" / "rate_this.json"
csv_file_items = addon_dir / "user_files" / "data_files" / "item_names.csv"
csv_file_descriptions = addon_dir / "user_files" / "data_files" / "item_flavor_text.csv"


items_list = []
with open(items_list_path, 'r') as file:
    items_list = json.load(file)



#effect sounds paths
hurt_normal_sound_path = addon_dir / "addon_sprites" / "sounds" / "HurtNormal.mp3"
hurt_noteff_sound_path = addon_dir / "addon_sprites" / "sounds" / "HurtNotEffective.mp3"
hurt_supereff_sound_path = addon_dir / "addon_sprites" / "sounds" / "HurtSuper.mp3"
ownhplow_sound_path = addon_dir / "addon_sprites" / "sounds" / "OwnHpLow.mp3"
hpheal_sound_path = addon_dir / "addon_sprites" / "sounds" / "HpHeal.mp3"
fainted_sound_path = addon_dir / "addon_sprites" / "sounds" / "Fainted.mp3"

with open(sound_list_path, 'r') as json_file:
    sound_list = json.load(json_file)

#pokemon species id files
pokemon_species_normal_path = addon_dir / "user_files" / "pkmn_data" / "normal.json"
pokemon_species_legendary_path = addon_dir / "user_files" / "pkmn_data" / "legendary.json"
pokemon_species_ultra_path = addon_dir / "user_files" / "pkmn_data" / "ultra.json"
pokemon_species_mythical_path = addon_dir / "user_files" / "pkmn_data" / "mythical.json"
pokemon_species_baby_path = addon_dir / "user_files" / "pkmn_data" / "baby.json"

# New rarity tier paths for wild encounters
pokemon_species_common_path = addon_dir / "user_files" / "pkmn_data" / "common.json"
pokemon_species_uncommon_path = addon_dir / "user_files" / "pkmn_data" / "uncommon.json"
pokemon_species_rare_path = addon_dir / "user_files" / "pkmn_data" / "rare.json"

# Get the profile folder
profilename = mw.pm.name
#profilefolder = Path(mw.pm.profileFolder())
#mediafolder = Path(mw.col.media.dir())
font_path = addon_dir / "addon_files"

mainpkmn = 0
mainpokemon_hp = 100
#test mainpokemon
#battlescene_file = "pkmnbattlescene.png"
pokemon_encounter = 0

# check for sprites, data
sound_files = check_folders_exist(pkmnimgfolder, "sounds")
back_sprites = check_folders_exist(pkmnimgfolder, "back_default")
back_default_gif = check_folders_exist(pkmnimgfolder, "back_default_gif")
front_sprites = check_folders_exist(pkmnimgfolder, "front_default")
front_default_gif = check_folders_exist(pkmnimgfolder, "front_default_gif")
item_sprites = check_folders_exist(pkmnimgfolder, "items")
badges_sprites = check_folders_exist(pkmnimgfolder, "badges")
berries_sprites = check_folders_exist(addon_dir, "berries")
poke_api_data = check_file_exists(user_path_data, "pokeapi_db.json")
pokedex_data = check_file_exists(user_path_data, "pokedex.json")
learnsets_data = check_file_exists(user_path_data, "learnsets.json")
poke_api_data = check_file_exists(user_path_data, "pokeapi_db.json")
pokedex_data = check_file_exists(user_path_data, "pokedex.json")
moves_data = check_file_exists(user_path_data, "moves.json")

if (
    pokedex_data
    and learnsets_data
    and moves_data
    and back_sprites
    and front_sprites
    and front_default_gif
    and back_default_gif
    and item_sprites
    and badges_sprites == True
):    database_complete = True
else:
    database_complete = False

if database_complete == True:
    owned_pokemon_ids = {}

    def extract_ids_from_file():
        global owned_pokemon_ids, mypokemon_path
        filename = mypokemon_path
        try:
            with open(filename, 'r') as file:
                data = json.load(file)
                # Only count Pokemon without variants (or with variant=None) in Pokedex
                # This excludes Shadow Mewtwo from counting as regular Mewtwo
                ids = [character['id'] for character in data if not character.get('variant')]
                owned_pokemon_ids = ids
        except FileNotFoundError:
            # First-time setup - mypokemon.json doesn't exist yet
            owned_pokemon_ids = []
        except Exception:
            # Other errors - initialize as empty list
            owned_pokemon_ids = []

    extract_ids_from_file()

    def check_pokecoll_in_list(id):
        extract_ids_from_file()
        global owned_pokemon_ids
        pokeball = False
        for num in owned_pokemon_ids:
            if num == id:
                pokeball = True
                break
        return pokeball

class CheckFiles(QDialog):
    def __init__(self):
        super().__init__()
        check_files_message = "Ankimon Files:"
        if database_complete != True:
            check_files_message += " \n Resource Files incomplete. \n  Please go to Ankimon => 'Download Resources' to download the needed files"
        check_files_message += "\n Once all files have been downloaded: Restart Anki"
        # Set the window title for the dialog
        self.setWindowTitle("Ankimon Files Checker")

        # Create a QLabel instance
        self.label = QLabel(f"{check_files_message}", self)

        # Create a QVBoxLayout instance
        self.layout = QVBoxLayout()

        # Add the QLabel to the layout
        self.layout.addWidget(self.label)

        # Set the dialog's layout
        self.setLayout(self.layout)

dialog = CheckFiles()
if database_complete != True:
    dialog.show()

if mainpokemon_path.is_file():
    with open(mainpokemon_path, "r") as json_file:
        main_pokemon_data = json.load(json_file)
        if not main_pokemon_data or main_pokemon_data is None:
            mainpokemon_empty = True
        else:
            mainpokemon_empty = False
else:
    # First-time setup - mainpokemon.json doesn't exist yet
    mainpokemon_empty = True

window = None
gender = None
card_counter = -1
item_receive_value = random.randint(30, 120)
system_name = platform.system()
forced_next_pokemon_id = None  # For Pokédex force encounter feature
forced_next_pokemon_shiny = False  # Whether forced encounter should be shiny

# Shiny system globals
current_wild_is_shiny = False  # Tracks if current wild encounter is shiny
SHINY_RATE = 1 / 512  # 1 in 512 chance for shiny encounters

if system_name == "Windows" or system_name == "Linux":
    system = "win_lin"
elif system_name == "Darwin":
    # Open file explorer at the specified path in macOS
    system = "mac"
pop_up_dialog_message_on_defeat = config["pop_up_dialog_message_on_defeat"]
reviewer_text_message_box = config["reviewer_text_message_box"]
reviewer_text_message_box_time = config["reviewer_text_message_box_time"] #time in seconds for text message
reviewer_text_message_box_time = reviewer_text_message_box_time * 1000 #times 1000 for s => ms
cards_per_round = config["cards_per_round"]
reviewer_image_gif = config["reviewer_image_gif"]
sounds = config["sounds"]
battle_sounds = config["battle_sounds"]
language = config["language"]
ankimon_key = config["key_for_opening_closing_ankimon"]
show_mainpkmn_in_reviewer = config["show_mainpkmn_in_reviewer"] #0 is off, 1 normal, 2 battle mode
xp_bar_config = config["xp_bar_config"]
review_hp_bar_thickness = config["review_hp_bar_thickness"] #2 = 8px, 3# 12px, 4# 16px, 5# 20px
hp_bar_thickness = review_hp_bar_thickness * 4
hp_bar_config = config["hp_bar_config"] #2 = 8px, 3# 12px, 4# 16px, 5# 20px
xp_bar_location = config["xp_bar_location"] #1 top, 2 = bottom
ssh = config["ssh"] #for eduroam users - false ; default: true
dmg_in_reviewer = config["dmg_in_reviewer"] #default: false; true = mainpokemon is getting damaged in reviewer for false answers
animate_time = config["animate_time"] #default: true; false = animate for 0.8 seconds
view_main_front = config["view_main_front"] #default: true => -1; false = 1
gif_in_collection = config["gif_in_collection"] #default: true => -1; false = 1
sound_effects = config["sound_effects"] #default: false; true = sound_effects on

if sound_effects is True:
    from . import playsound

if view_main_front is True and reviewer_image_gif is True:
    view_main_front = -1
else:
    view_main_front = 1

if animate_time is True:
    animate_time = 0.8
else:
    animate_time = 0

if xp_bar_location == 1:
    xp_bar_location = "top"
    xp_bar_spacer = 0
elif xp_bar_location == 2:
    xp_bar_location = "bottom"
    xp_bar_spacer = 20

if xp_bar_config is False:
    xp_bar_spacer = 0

if hp_bar_config != True:
    hp_only_spacer = 15
    wild_hp_spacer = 65
else:
    hp_only_spacer = 0
    wild_hp_spacer = 0

def test_online_connectivity(url='http://www.google.com', timeout=5):
    try:
        # Attempt to get the URL
        response = requests.get(url, timeout=timeout)

        # Check if the response status code is 200 (OK)
        if response.status_code == 200:
            return True
    except requests.ConnectionError:
        # Connection error means no internet connectivity
        return False

online_connectivity = test_online_connectivity()

if ssh != False:
    # Function to check if the content of the two files is the same
    def compare_files(local_content, github_content):
        return local_content == github_content

    # Function to read the content of the local file
    def read_local_file(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return None

    # Function to write content to a local file
    def write_local_file(file_path, content):
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)

    # Function to check if the file exists on GitHub and read its content
    def read_github_file(url):
        response = requests.get(url)
            
        if response.status_code == 200:
            # File exists, parse the Markdown content
            content = response.text
            html_content = markdown.markdown(content)
            return content, html_content
        else:
            return None, None
        
if online_connectivity != False:
    if ssh != False:
        import markdown

        # Custom Dialog class
        class UpdateNotificationWindow(QDialog):
            def __init__(self, content):
                super().__init__()
                global icon_path
                self.setWindowTitle("Ankimon Notifications")
                self.setGeometry(100, 100, 600, 400)

                layout = QVBoxLayout()
                self.text_edit = QTextEdit()
                self.text_edit.setReadOnly(True)
                self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
                self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # For horizontal scrollbar, if you want it off
                self.text_edit.setHtml(content)
                layout.addWidget(self.text_edit)
                self.setWindowIcon(QIcon(str(icon_path)))

                self.setLayout(layout)

        # URL of the file on GitHub
        github_url = "https://raw.githubusercontent.com/Unlucky-Life/ankimon/main/update_txt.md"
        # Path to the local file
        local_file_path = addon_dir / "updateinfos.md"
        # Read content from GitHub
        github_content, github_html_content = read_github_file(github_url)
        # Read content from the local file
        local_content = read_local_file(local_file_path)
        # If local content exists and is the same as GitHub content, do not open dialog
        if local_content is not None and compare_files(local_content, github_content):
            pass
        else:
            # Download new content from GitHub
            if github_content is not None:
                # Write new content to the local file
                write_local_file(local_file_path, github_content)
                dialog = UpdateNotificationWindow(github_html_content)
                dialog.exec()
            else:
                showWarning("Failed to retrieve Ankimon content from GitHub.")

if ssh != False:
    ##HelpGuide
    class HelpWindow(QDialog):
        def __init__(self):
            super().__init__()
            html_content = " "
            global icon_path
            if online_connectivity != False:
                # URL of the file on GitHub
                help_github_url = "https://raw.githubusercontent.com/Unlucky-Life/ankimon/main/src/Ankimon/HelpInfos.html"
                # Path to the local file
                help_local_file_path = addon_dir / "HelpInfos.html"
                local_content = read_local_file(help_local_file_path)
                # Read content from GitHub
                github_content, github_html_content = read_github_file(help_github_url)
                if local_content is not None and compare_files(local_content, github_content):
                    html_content = github_html_content
                else: 
                    # Download new content from GitHub
                    if github_content is not None:
                        # Write new content to the local file
                        write_local_file(help_local_file_path, github_content)
                        html_content = github_html_content
            else:
                local_content = read_local_file(help_local_file_path)
                html_content = local_content

            self.setWindowTitle("Ankimon HelpGuide")
            self.setGeometry(100, 100, 600, 400)

            layout = QVBoxLayout()
            self.text_edit = QTextEdit()
            self.text_edit.setReadOnly(True)
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
            self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.text_edit.setHtml(html_content)
            layout.addWidget(self.text_edit)
            self.setWindowIcon(QIcon(str(icon_path)))
            self.setLayout(layout)
            
def open_help_window():
    if ssh != False:
        help_dialog = HelpWindow()
        help_dialog.exec()
        
try:
    from aqt.sound import av_player
    from anki.sound import SoundOrVideoTag
    legacy_play = None
    from . import audios
except (ImportError, ModuleNotFoundError):
    showWarning("Sound import error occured.")
    from anki.sound import play as legacy_play
    av_player = None


def play_effect_sound(sound_type):
    global effect_sound_timer, sound_effects, hurt_normal_sound_path, hurt_noteff_sound_path, hurt_supereff_sound_path, ownhplow_sound_path, hpheal_sound_path, fainted_sound_path
    
    if sound_effects is True:
        audio_path = None
        if sound_type == "HurtNotEffective":
            audio_path = hurt_noteff_sound_path
        elif sound_type == "HurtNormal":
            audio_path = hurt_normal_sound_path
        elif sound_type == "HurtSuper":
            audio_path = hurt_supereff_sound_path
        elif sound_type == "OwnHpLow":
            audio_path = ownhplow_sound_path
        elif sound_type == "HpHeal":
            audio_path = hpheal_sound_path
        elif sound_type == "Fainted":
            audio_path = fainted_sound_path

        if not audio_path.is_file():
            return
        else:   
            audio_path = Path(audio_path)
            #threading.Thread(target=playsound.playsound, args=(audio_path,)).start()
            audios.will_use_audio_player()
            audios.audio(audio_path)
    else:
        pass

def play_sound():
    global sounds
    if sounds is True:
        global name, addon_dir
        file_name = f"{name.lower()}.mp3"
        audio_path = addon_dir / "user_files" / "sprites" / "sounds" / file_name
        if audio_path.is_file():
            audio_path = Path(audio_path)
            audios.will_use_audio_player()
            audios.audio(audio_path)

gen_ids = {
    "gen_1": 151,
    "gen_2": 251,
    "gen_3": 386,
    "gen_4": 493,
    "gen_5": 649,
    "gen_6": 721,
    "gen_7": 809,
    "gen_8": 905,
    "gen_9": 1025
}

gen_config = []
for i in range(1,10):
    gen_config.append(config[f"gen{i}"])

def check_id_ok(id_num):
    if isinstance(id_num, int):
        pass
    elif isinstance(id_num, list):
        if len(id_num) > 0:
            id_num = id_num[0]
        else:
            return False
    # Determine the generation of the given ID
    if id_num < 898:
        generation = 0
        for gen, max_id in gen_ids.items():
            if id_num <= max_id:
                generation = int(gen.split('_')[1])
                break

        if generation == 0:
            return False  # ID does not belong to any generation

        return gen_config[generation - 1]
    else:
        return False

#count index - count 2 cards - easy = 20, good = 10, hard = 5, again = 0
# if index = 40 - 100 => normal ; multiply with damage
# if index < 40 => attack misses

def special_pokemon_names_for_min_level(name):
    if name == "flabébé":
        return "flabebe"
    elif name == "sirfetch'd":
        return "sirfetchd"
    elif name == "farfetch'd":
        return "farfetchd"
    elif name == "porygon-z":
        return "porygonz"
    elif name == "kommo-o":
        return "kommoo"
    elif name == "hakamo-o":
        return "hakamoo"
    elif name == "jangmo-o":
        return "jangmoo"
    elif name == "mr. rime":
        return "mrrime"
    elif name == "mr. mime":
        return "mrmime"
    elif name == "mime jr.":
        return "mimejr"
    elif name == "nidoran♂":
        return "nidoranm"
    elif name == "nidoran":
        return "nidoranf"
    elif name == "keldeo[e]":
        return "keldeo"
    elif name == "mew[e]":
        return "mew"
    elif name == "deoxys[e]":
        return "deoxys"
    elif name == "jirachi[e]":
        return "jirachi"
    elif name == "arceus[e]":
        return "arceus"
    elif name == "shaymin[e]":
        return "shaymin-land"
    elif name == "darkrai [e]":
        return "darkrai"
    elif name == "manaphy[e]":
        return "manaphy"
    elif name == "phione[e]":
        return "phione"
    elif name == "celebi[e]":
        return "celebi"
    elif name == "magearna[e]":
        return "magearna"
    elif name == "type: null":
        return "typenull"
    else:
        #showWarning("Error in Handling Pokémon name")
        return name

def special_pokemon_names_for_pokedex_to_poke_api_db(name):
    global pokedex_to_poke_api_db
    return pokedex_to_poke_api_db.get(name, name)

def answerCard_before(filter, reviewer, card):
	utils.answBtnAmt = reviewer.mw.col.sched.answerButtons(card)
	return filter

aqt.gui_hooks.reviewer_will_answer_card.append(answerCard_before)
# Globale Variable für die Zählung der Bewertungen
card_ratings_count = {"Again": 0, "Hard": 0, "Good": 0, "Easy": 0}

def answerCard_after(rev, card, ease):
    maxEase = utils.answBtnAmt
    aw = aqt.mw.app.activeWindow() or aqt.mw
    # Aktualisieren Sie die Zählung basierend auf der Bewertung
    global card_ratings_count
    if ease == 1:
        card_ratings_count["Again"] += 1
    elif ease == maxEase - 2:
        card_ratings_count["Hard"] += 1
    elif ease == maxEase - 1:
        card_ratings_count["Good"] += 1
    elif ease == maxEase:
        card_ratings_count["Easy"] += 1
    else:
        # default behavior for unforeseen cases
        tooltip("Error in ColorConfirmation: Couldn't interpret ease")

aqt.gui_hooks.reviewer_did_answer_card.append(answerCard_after)

def get_image_as_base64(path):
    """
    Get image as base64, with fallback to default sprite if path is invalid.
    Prevents crashes from invalid Pokemon IDs like [] or empty strings.
    """
    try:
        # Validate path - check for invalid patterns
        path_str = str(path)
        if not path_str or '[' in path_str or ']' in path_str or path_str.endswith('/.gif') or path_str.endswith('/.png'):
            _ankimon_log("WARN", "AnkimonSprite", f"Invalid sprite path detected: {path_str}, using fallback")
            # Use fallback to Pikachu (ID 25)
            import pathlib
            addon_dir = pathlib.Path(__file__).parent
            if '.gif' in path_str or 'front_default_gif' in path_str:
                fallback_path = addon_dir / "user_files" / "sprites" / "front_default_gif" / "25.gif"
            else:
                fallback_path = addon_dir / "user_files" / "sprites" / "front_default" / "25.png"
            path = str(fallback_path)

        # Check if file exists
        if not os.path.exists(path):
            _ankimon_log("WARN", "AnkimonSprite", f"Sprite file not found: {path}, using fallback")
            # Use fallback to Pikachu
            import pathlib
            addon_dir = pathlib.Path(__file__).parent
            if '.gif' in str(path):
                fallback_path = addon_dir / "user_files" / "sprites" / "front_default_gif" / "25.gif"
            else:
                fallback_path = addon_dir / "user_files" / "sprites" / "front_default" / "25.png"
            path = str(fallback_path)

        with open(path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonSprite", f"Error loading sprite {path}: {e}")
        # Return empty base64 as last resort
        return ""

if database_complete != False:
    def get_random_moves_for_pokemon(pokemon_name, level):
        """
        Get up to 4 random moves learned by a Pokémon at a specific level and lower, along with the highest level,
        excluding moves that can be learned at a higher level.

        Args:
            json_file_name (str): The name of the JSON file containing Pokémon learnset data.
            pokemon_name (str): The name of the Pokémon.
            level (int): The level at which to check for moves.

        Returns:
            list: A list of up to 4 random moves and their highest levels.
        """
        global learnset_path
        # Load the JSON file
        with open(learnset_path, 'r') as file:
            learnsets = json.load(file)

        # Normalize the Pokémon name to lowercase for consistency
        pokemon_name = pokemon_name.lower()

        # Retrieve the learnset for the specified Pokémon
        pokemon_learnset = learnsets.get(pokemon_name, {})

        # Create a dictionary to store moves and their corresponding highest levels
        moves_at_level_and_lower = {}

        # Loop through the learnset dictionary
        for move, levels in pokemon_learnset.get('learnset', {}).items():
            highest_level = float('-inf')  # Initialize with negative infinity
            eligible_moves = []  # Store moves eligible for inclusion

            for move_level in levels:
                # Check if the move_level string contains 'L'
                if 'L' in move_level:
                    # Extract the level from the move_level string
                    move_level_int = int(move_level.split('L')[1])

                    # Check if the move can be learned at the specified level or lower
                    if move_level_int <= level:
                        # Update the highest_level if a higher level is found
                        highest_level = max(highest_level, move_level_int)
                        eligible_moves.append(move)

            # Check if the eligible moves can be learned at a higher level
            if highest_level != float('-inf'):
                can_learn_at_higher_level = any(
                    int(move_level.split('L')[1]) > highest_level
                    for move_level in levels
                    if 'L' in move_level
                )
                if not can_learn_at_higher_level:
                    moves_at_level_and_lower[move] = highest_level

        attacks = []
        if moves_at_level_and_lower:
            # Convert the dictionary into a list of tuples for random selection
            moves_and_levels_list = list(moves_at_level_and_lower.items())
            random.shuffle(moves_and_levels_list)

            # Pick up to 4 random moves and append them to the attacks list
            for move, highest_level in moves_and_levels_list[:4]:
                #attacks.append(f"{move} at level: {highest_level}")
                attacks.append(f"{move}")

        return attacks
    
    def get_all_pokemon_moves(pk_name, level):
        """
        Args:
            json_file_name (str): The name of the JSON file containing Pokémon learnset data.
            pokemon_name (str): The name of the Pokémon.
            level (int): The level at which to check for moves.

        Returns:
            list: A list of up to 4 random moves and their highest levels.
        """
        global learnset_path
        # Load the JSON file
        with open(learnset_path, 'r') as file:
            learnsets = json.load(file)

        # Normalize the Pokémon name to lowercase for consistency
        pk_name = pk_name.lower()

        # Retrieve the learnset for the specified Pokémon
        pokemon_learnset = learnsets.get(pk_name, {})

        # Create a dictionary to store moves and their corresponding highest levels
        moves_at_level_and_lower = {}

        # Loop through the learnset dictionary
        for move, levels in pokemon_learnset.get('learnset', {}).items():
            highest_level = float('-inf')  # Initialize with negative infinity
            eligible_moves = []  # Store moves eligible for inclusion

            for move_level in levels:
                # Check if the move_level string contains 'L'
                if 'L' in move_level:
                    # Extract the level from the move_level string
                    move_level_int = int(move_level.split('L')[1])

                    # Check if the move can be learned at the specified level or lower
                    if move_level_int <= level:
                        # Update the highest_level if a higher level is found
                        highest_level = max(highest_level, move_level_int)
                        eligible_moves.append(move)

            # Check if the eligible moves can be learned at a higher level
            if highest_level != float('-inf'):
                can_learn_at_higher_level = any(
                    int(move_level.split('L')[1]) > highest_level
                    for move_level in levels
                    if 'L' in move_level
                )
                if not can_learn_at_higher_level:
                    moves_at_level_and_lower[move] = highest_level

        attacks = []
        if moves_at_level_and_lower:
            # Convert the dictionary into a list of tuples for random selection
            moves_and_levels_list = list(moves_at_level_and_lower.items())

            # Pick up to 4 random moves and append them to the attacks list
            for move, highest_level in moves_and_levels_list:
                attacks.append(f"{move}")

        return attacks

def pick_random_gender(pokemon_name):
    """
    Randomly pick a gender for a given Pokémon based on its gender ratios.

    Args:
        pokemon_name (str): The name of the Pokémon.
        pokedex_data (dict): Pokémon data loaded from the pokedex JSON file.

    Returns:
        str: "M" for male, "F" for female, or "Genderless" for genderless Pokémon.
    """
    global pokedex_path
    with open(pokedex_path, 'r', encoding="utf-8") as file:
        pokedex_data = json.load(file)
    pokemon_name = pokemon_name.lower()  # Normalize Pokémon name to lowercase
    pokemon = pokedex_data.get(pokemon_name)

    if pokemon:
        gender_ratio = pokemon.get("genderRatio")
        if gender_ratio:
            random_number = random.random()  # Generate a random number between 0 and 1
            if random_number < gender_ratio["M"]:
                #return "M"  # Male
                gender = "M"
                return gender
            elif random_number > gender_ratio["M"]:
                #return "F"  # Female
                gender = "F"
                return gender
        else:
            genders = pokemon.get("gender")
            if genders:
                if genders == "F":
                    #return "M"
                    gender = "F"
                elif genders == "M":
                    #return "F"
                    gender = "M"
                elif genders == "N":
                    gender = "N"
                return gender
            else:
                genders = ["M", "F"]
                #genders = ["M", "♀"]
                gender = random.choice(genders)
                return gender
                # Randomly choose between "M" and "F"
    else:
        genders = ["M", "F"]
        gender = random.choice(genders)
        return gender

if database_complete != False:
    def get_levelup_move_for_pokemon(pokemon_name, level):
        """
        Get a random move learned by a Pokémon at a specific level and lower, excluding moves that can be learned at a higher level.

        Args:
            pokemon_name (str): The name of the Pokémon.
            level (int): The level at which to check for moves.

        Returns:
            str: A random move and its highest level.
        """
        global learnset_path
        # Load the JSON file
        with open(learnset_path, 'r') as file:
            learnsets = json.load(file)

        # Normalize the Pokémon name to lowercase for consistency
        pokemon_name = pokemon_name.lower()

        # Retrieve the learnset for the specified Pokémon
        pokemon_learnset = learnsets.get(pokemon_name, {})

        # Create a dictionary to store moves and their corresponding highest levels
        moves_at_level_and_lower = {}

        # Loop through the learnset dictionary
        for move, levels in pokemon_learnset.get('learnset', {}).items():
            highest_level = float('-inf')  # Initialize with negative infinity
            eligible_moves = []  # Store moves eligible for inclusion

            for move_level in levels:
                # Check if the move_level string contains 'L'
                if 'L' in move_level:
                    # Extract the level from the move_level string
                    move_level_int = int(move_level.split('L')[1])

                    # Check if the move can be learned at the specified level or lower
                    if move_level_int <= level:
                        # Update the highest_level if a higher level is found
                        highest_level = max(highest_level, move_level_int)
                        eligible_moves.append(move)

            # Check if the move can be learned at a higher level
            can_learn_at_higher_level = any(
                'L' in move_level and int(move_level.split('L')[1]) > level
                for move_level in levels
            )

            # Add the move and its highest level to the dictionary if not learnable at a higher level
            if highest_level != float('-inf') and not can_learn_at_higher_level:
                moves_at_level_and_lower[move] = highest_level

        if moves_at_level_and_lower:
            # Filter moves with the same highest level as the input level
            eligible_moves = [
                move for move, highest_level in moves_at_level_and_lower.items()
                if highest_level == level
            ]
            #if eligible_moves:
                # Randomly select and return a move
               #random_attack = random.choice(eligible_moves)
               # return f"{random_attack} at level: {level}"
           # else:
                #return "No moves to be found."
       # else:
            #return f"{pokemon_name} does not learn any new moves at level {level} or lower."
            return eligible_moves

def split_string_by_length(input_string, max_length):
    current_length = 0
    current_line = []

    for word in input_string.split():
        word_length = len(word)  # Change this to calculate length in pixels

        if current_length + len(current_line) + word_length <= max_length:
            current_line.append(word)
            current_length += word_length
        else:
            yield ' '.join(current_line)
            current_line = [word]
            current_length = word_length

    yield ' '.join(current_line)

def split_japanese_string_by_length(input_string, max_length):
    max_length = 30
    current_length = 0
    current_line = ""

    for char in input_string:
        if current_length + 1 <= max_length:
            current_line += char
            current_length += 1
        else:
            yield current_line
            current_line = char
            current_length = 1

    if current_line:  # Ensure the last line is also yielded
        yield current_line

def resize_pixmap_img(pixmap, max_width):
    original_width = pixmap.width()
    original_height = pixmap.height()
    new_width = max_width
    new_height = (original_height * max_width) // original_width
    pixmap2 = pixmap.scaled(new_width, new_height)
    return pixmap2

def random_battle_scene(pokemon_type=None):
    """Select battle scene based on Pokemon type, or random if no type specified"""
    global battlescene_path_without_dialog

    # Type to battle scene mapping
    type_scene_map = {
        "Water": ["ocean_pkmnbattlescene.png", "beach_pkmnbattlescene.png"],
        "Fire": ["desert_pkmnbattlescene.png"],
        "Grass": ["grass_pkmnbattlescene.png"],
        "Bug": ["grass_pkmnbattlescene.png"],
        "Ice": ["ice_pkmnbattlescene.png"],
        "Ground": ["ground_pkmnbattlescene.png", "desert_pkmnbattlescene.png"],
        "Rock": ["rock_pkmnbattlescene.png", "ground_pkmnbattlescene.png"],
        "Poison": ["toxic_pkmnbattlescene.png"],
        "Psychic": ["psychic_pkmnbattlescene.png"],
        "Steel": ["metal_city_pkmnbattlescene.png", "rock_pkmnbattlescene.png"],  # metal_city when added
        "Dragon": ["rock_pkmnbattlescene.png"],
        "Dark": ["psychic_pkmnbattlescene.png"],
        "Ghost": ["psychic_pkmnbattlescene.png"],
        "Fighting": ["ground_pkmnbattlescene.png"],
        "Normal": ["grass_pkmnbattlescene.png"],
        "Flying": ["grass_pkmnbattlescene.png"],
        "Electric": ["pkmnbattlescene.png"],
        "Fairy": ["grass_pkmnbattlescene.png"],
    }

    # Get list of all available battle scenes
    available_scenes = []
    for filename in os.listdir(battlescene_path_without_dialog):
        if filename.endswith(".png"):
            available_scenes.append(filename)

    # If no type specified or type not in map, return random scene
    if not pokemon_type or pokemon_type not in type_scene_map:
        return random.choice(available_scenes) if available_scenes else "pkmnbattlescene.png"

    # Get scenes for this type
    type_scenes = type_scene_map[pokemon_type]

    # Filter to only scenes that actually exist
    existing_type_scenes = [scene for scene in type_scenes if scene in available_scenes]

    # Return random scene from type's options, or fallback to random
    if existing_type_scenes:
        return random.choice(existing_type_scenes)
    else:
        return random.choice(available_scenes) if available_scenes else "pkmnbattlescene.png"

if berries_sprites != False:
    def random_berries():
        global berries_path
        berries = {}
        for index, filename in enumerate(os.listdir(berries_path)):
            if filename.endswith(".png"):
                berries[index + 1] = filename
        # Get the corresponding file name
        berries_file = berries.get(random.randint(1, len(berries)))
        return berries_file

if item_sprites != False:
    def random_item():
        global items_path
        # Initialize an empty list to store the file names
        item_names = []
        # Iterate over each file in the directory
        for file in os.listdir(items_path):
            # Check if the file is a .png file
            if file.endswith(".png"):
                # Append the file name without the .png extension to the list
                item_names.append(file[:-4])
        item_names = [name for name in item_names if not name.endswith("-ball")]
        item_names = [name for name in item_names if not name.endswith("-repel")]
        item_names = [name for name in item_names if not name.endswith("-incense")]
        item_names = [name for name in item_names if not name.endswith("-fang")]
        item_names = [name for name in item_names if not name.endswith("dust")]
        item_names = [name for name in item_names if not name.endswith("-piece")]
        item_names = [name for name in item_names if not name.endswith("-nugget")]
        item_name = random.choice(item_names)
        # add item to item list
        try:
            with open(itembag_path, 'r') as json_file:
                itembag_list = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create empty items list if file doesn't exist
            itembag_list = []
        itembag_list.append(item_name)
        with open(itembag_path, 'w') as json_file:
            json.dump(itembag_list, json_file)
        return item_name

    def random_fossil():
        global items_path
        fossil_names = []
        # Iterate over each file in the directory
        for file in os.listdir(items_path):
            # Check if the file is a .png file
            if file.endswith("-fossil.png"):
                # Append the file name without the .png extension to the list
                fossil_names.append(file[:-4])
        fossil_name = random.choice(fossil_names)
        try:
            with open(itembag_path, 'r') as json_file:
                itembag_list = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create empty items list if file doesn't exist
            itembag_list = []
        itembag_list.append(fossil_name)
        with open(itembag_path, 'w') as json_file:
            json.dump(itembag_list, json_file, indent=2)
        return fossil_name

#def copy_directory(dir_addon: str, dir_anki: str = None)
#       if not dir_anki:
        #dir_anki = dir_addon
    #fromdir = addon_dir / dir_addon
    #todir = mediafolder / dir_anki
    #if not fromdir.is_dir():
        #return
    #if not todir.is_dir():
        #shutil.copytree(str(fromdir), str(todir))
    #else:
        #distutils.dir_util.copy_tree(str(fromdir), str(todir))

caught_pokemon = {} #pokemon not caught

def check_min_generate_level(pkmn_name):
    # Handle special variants (Shadow Mewtwo, etc.) - use base Pokemon for lookups
    lookup_name = "mewtwo" if name == "Shadow Mewtwo" else name.lower()

    evoType = search_pokedex(lookup_name, "evoType")
    evoLevel = search_pokedex(lookup_name, "evoLevel")
    if evoLevel is not None:
        return int(evoLevel)
    elif evoType is not None:
        min_level = 100
        return int(min_level)
    elif evoType and evoLevel is None:
        min_level = 1
        return int(min_level)
    else:
        min_level = 1
        return min_level

def customCloseTooltip(tooltipLabel):
	if tooltipLabel:
		try:
			tooltipLabel.deleteLater()
		except:
			# already deleted as parent window closed
			pass
		tooltipLabel = None

def tooltipWithColour(msg, color, x=0, y=20, xref=1, parent=None, width=0, height=0, centered=False):
    period = reviewer_text_message_box_time #time for pop up message
    global reviewer_text_message_box
    class CustomLabel(QLabel):
        def mousePressEvent(self, evt):
            evt.accept()
            self.hide()
    aw = parent or QApplication.activeWindow()
    if aw is None:
        return
    else:
        if reviewer_text_message_box != False:
            # Assuming closeTooltip() and customCloseTooltip() are defined elsewhere
            closeTooltip()
            x = aw.mapToGlobal(QPoint(x + round(aw.width() / 2), 0)).x()
            y = aw.mapToGlobal(QPoint(0, aw.height() - 180)).y()
            lab = CustomLabel(aw)
            lab.setFrameShape(QFrame.Shape.StyledPanel)
            lab.setLineWidth(2)
            lab.setWindowFlags(Qt.WindowType.ToolTip)
            lab.setText(msg)
            lab.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
            
            if width > 0:
                lab.setFixedWidth(width)
            if height > 0:
                lab.setFixedHeight(height)
            
            p = QPalette()
            p.setColor(QPalette.ColorRole.Window, QColor(color))
            p.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
            lab.setPalette(p)
            lab.show()
            lab.move(QPoint(x - round(lab.width() * 0.5 * xref), y))    
            QTimer.singleShot(period, lambda: lab.hide())

pokemon_species = None
# Your random Pokémon generation function using the PokeAPI
if database_complete != False:
    def generate_random_pokemon(_recursion_depth=0):
        # Prevent infinite recursion - max 5 retries
        if _recursion_depth >= 5:
            # Too many retries - check if this is a gym battle
            is_gym = _ankimon_is_gym_active()

            if is_gym:
                # CRITICAL: Never use fallback pokemon in gym battles!
                # Reset gym state and show error
                try:
                    conf = _ankimon_get_col_conf()
                    if conf:
                        leader_name = conf.get("ankimon_gym_leader_name", "Gym Leader")
                        gym_idx = int(conf.get("ankimon_gym_enemy_index", 0))
                        enemy_ids = conf.get("ankimon_gym_enemy_ids", [])

                        # Log the problematic pokemon ID for debugging
                        problem_id = enemy_ids[gym_idx] if gym_idx < len(enemy_ids) else "unknown"

                        conf["ankimon_gym_active"] = False
                        conf["ankimon_gym_pending"] = False
                        conf["ankimon_gym_enemy_ids"] = []
                        conf["ankimon_gym_enemy_index"] = 0
                        mw.col.setMod()

                        error_msg = f"Failed to generate gym pokemon (ID {problem_id}) for {leader_name}.\n\n"
                        error_msg += "This pokemon's data may be corrupted in the database.\n"
                        error_msg += "Gym battle has been reset.\n\n"
                        error_msg += "You can:\n"
                        error_msg += "1. Try the gym battle again (may fail on same pokemon)\n"
                        error_msg += "2. Use 'Reset Battle' from Ankimon menu\n"
                        error_msg += "3. Report this bug with pokemon ID " + str(problem_id)
                        showWarning(error_msg)
                except Exception as e:
                    import traceback
                    traceback.print_exc()

                # Return a basic fallback to prevent crash, but gym is now reset
                tooltipWithColour("Gym battle reset due to pokemon generation error", "#FF0000")

                # Calculate proper HP for fallback Pikachu (level 5)
                pikachu_base_hp = 35
                pikachu_iv = 20
                pikachu_level = 5
                pikachu_calculated_hp = int(((2 * pikachu_base_hp + pikachu_iv) * pikachu_level / 100) + pikachu_level + 10)

                return "pikachu", 25, pikachu_level, "static", ["Electric"], {"hp": 35, "atk": 55, "def": 40, "spa": 50, "spd": 50, "spe": 90}, [], 112, "medium-fast", pikachu_calculated_hp, pikachu_calculated_hp, {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}, {"hp": pikachu_iv, "atk": pikachu_iv, "def": pikachu_iv, "spa": pikachu_iv, "spd": pikachu_iv, "spe": pikachu_iv}, "unknown", "fighting", {"hp": 35, "atk": 55, "def": 40, "spa": 50, "spd": 50, "spe": 90}
            else:
                # Wild pokemon - fallback to Pikachu is OK
                try:
                    tooltipWithColour("Pokemon generation failed, using fallback", "#FF0000")
                except:
                    pass

                # Calculate proper HP for fallback Pikachu (level 5)
                pikachu_base_hp = 35
                pikachu_iv = 20
                pikachu_level = 5
                pikachu_calculated_hp = int(((2 * pikachu_base_hp + pikachu_iv) * pikachu_level / 100) + pikachu_level + 10)

                return "pikachu", 25, pikachu_level, "static", ["Electric"], {"hp": 35, "atk": 55, "def": 40, "spa": 50, "spd": 50, "spe": 90}, [], 112, "medium-fast", pikachu_calculated_hp, pikachu_calculated_hp, {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}, {"hp": pikachu_iv, "atk": pikachu_iv, "def": pikachu_iv, "spa": pikachu_iv, "spd": pikachu_iv, "spe": pikachu_iv}, "unknown", "fighting", {"hp": 35, "atk": 55, "def": 40, "spa": 50, "spd": 50, "spe": 90}

        # Fetch random Pokémon data from Generation
        # Load the JSON file with Pokémon data
        global addon_dir
        global pokemon_encounter
        global hp, gender, name, enemy_attacks
        global mainpokemon_level
        global pokemon_species
        global cards_per_round
        pokemon_encounter = 0
        pokemon_species = None
        #generation_file = ("pokeapi_db.json")
        # Initialize id with a default value to prevent UnboundLocalError
        id = None
        try:
            # Check for forced encounter from Pokédex
            global forced_next_pokemon_id, forced_next_pokemon_shiny, current_wild_is_shiny
            if forced_next_pokemon_id is not None and not _ankimon_is_gym_active():
                # Use the forced pokemon ID and clear it
                id = forced_next_pokemon_id
                forced_next_pokemon_id = None
                pokemon_species = None
                # Apply forced shiny status
                current_wild_is_shiny = forced_next_pokemon_shiny
                forced_next_pokemon_shiny = False
                try:
                    shiny_text = " (Shiny)" if current_wild_is_shiny else ""
                    tooltipWithColour(f"Forced encounter activated{shiny_text}!", "#00FF00")
                except:
                    pass
            # If a gym battle is active, lock the opponent to the current gym team.
            elif _ankimon_is_gym_active():
                # Gym battles are NEVER shiny
                current_wild_is_shiny = False
                _ids = _ankimon_get_gym_enemy_ids()
                _idx = _ankimon_get_gym_enemy_index()
                if _ids and len(_ids) > 0:
                    if _idx < 0:
                        _idx = 0
                    if _idx >= len(_ids):
                        _idx = len(_ids) - 1
                    try:
                        id = int(_ids[_idx])
                        pokemon_species = None
                    except (ValueError, IndexError, TypeError):
                        # If gym pokemon ID is invalid, fall back to random
                        id, pokemon_species = choose_random_pkmn_from_tier()
                else:
                    # Gym is active but no IDs - this shouldn't happen, fall back to random
                    id, pokemon_species = choose_random_pkmn_from_tier()
            # If Elite Four battle is active, lock the opponent to the current member's team
            elif _ankimon_is_elite_four_active():
                # Elite Four battles are NEVER shiny
                current_wild_is_shiny = False
                _ids = _ankimon_get_elite_four_enemy_ids()
                _idx = _ankimon_get_elite_four_pokemon_index()
                if _ids and len(_ids) > 0:
                    if _idx < 0:
                        _idx = 0
                    if _idx >= len(_ids):
                        _idx = len(_ids) - 1
                    try:
                        id = int(_ids[_idx])
                        pokemon_species = None
                    except (ValueError, IndexError, TypeError):
                        id, pokemon_species = choose_random_pkmn_from_tier()
                else:
                    id, pokemon_species = choose_random_pkmn_from_tier()
            # If Champion battle is active, lock the opponent to Champion's team
            elif _ankimon_is_champion_active():
                # Champion battles are NEVER shiny
                current_wild_is_shiny = False
                _ids = _ankimon_get_champion_enemy_ids()
                _idx = _ankimon_get_champion_pokemon_index()
                if _ids and len(_ids) > 0:
                    if _idx < 0:
                        _idx = 0
                    if _idx >= len(_ids):
                        _idx = len(_ids) - 1
                    try:
                        id = int(_ids[_idx])
                        pokemon_species = None
                    except (ValueError, IndexError, TypeError):
                        id, pokemon_species = choose_random_pkmn_from_tier()
                else:
                    id, pokemon_species = choose_random_pkmn_from_tier()
            else:
                # Wild encounter - use weighted rarity system
                id, pokemon_species = choose_random_pkmn_from_tier()

                # Roll for shiny AFTER Pokemon selection (wild encounters only)
                current_wild_is_shiny = roll_for_shiny()

                # Log shiny encounter for debugging (only if Developer Mode is active)
                try:
                    if current_wild_is_shiny and developer_menu and developer_menu.menuAction().isVisible():
                        print(f"[Wild] SHINY ENCOUNTER! id={id}")
                except:
                    pass

            # Safety check: if id is still None, use fallback
            if id is None:
                id, pokemon_species = choose_random_pkmn_from_tier()
                current_wild_is_shiny = roll_for_shiny()
            #test_ids = [417]
            #id = random.choice(test_ids)
            name = search_pokedex_by_id(id)

            if name is list:
                name = name[0]

            # CRITICAL FIX: For gym/Elite Four/Champion pokemon, skip min_level check (it causes RecursionError for some pokemon like Steelix)
            is_special_battle = _ankimon_is_gym_active() or _ankimon_is_elite_four_active() or _ankimon_is_champion_active()
            if is_special_battle:
                # Special battle pokemon: skip min_level check, always generate at appropriate level
                min_level = 0  # Bypass evolution level requirements
            else:
                # Wild pokemon: do normal min_level check
                try:
                    min_level = int(check_min_generate_level(str(name.lower())))
                except Exception as e:
                    # Log the error for debugging
                    try:
                        tooltipWithColour(f"Error checking min level for {name}: {str(e)[:50]}", "#FF0000")
                    except:
                        pass
                    # Recursive call with depth tracking
                    return generate_random_pokemon(_recursion_depth + 1)
            # Special level calculation for Gym/Elite Four/Champion battles
            if is_special_battle:
                try:
                    # Get current round for scaling
                    stats = _load_progression_stats()
                    current_round = stats["lifetime"].get("current_round", 1)

                    # Get base level based on battle type
                    conf = _ankimon_get_col_conf()
                    base_level = 10  # Fallback

                    if _ankimon_is_gym_active() and conf:
                        # Get gym leader key and Pokemon index
                        leader_key = conf.get("ankimon_gym_leader_key", "")
                        pokemon_idx = int(conf.get("ankimon_gym_enemy_index", 0))
                        base_levels = _get_gym_base_levels().get(leader_key, [])
                        base_level = base_levels[pokemon_idx] if pokemon_idx < len(base_levels) else 10 + (pokemon_idx * 5)

                    elif _ankimon_is_elite_four_active() and conf:
                        # Get Elite Four member key and Pokemon index
                        member_key = conf.get("ankimon_elite_four_member_key", "")
                        pokemon_idx = int(conf.get("ankimon_elite_four_pokemon_index", 0))
                        base_levels = _get_elite_four_base_levels().get(member_key, [])
                        base_level = base_levels[pokemon_idx] if pokemon_idx < len(base_levels) else 50 + (pokemon_idx * 2)

                    elif _ankimon_is_champion_active() and conf:
                        # Get Champion Pokemon index
                        pokemon_idx = int(conf.get("ankimon_champion_pokemon_index", 0))
                        base_levels = _get_champion_base_levels()
                        base_level = base_levels[pokemon_idx] if pokemon_idx < len(base_levels) else 58 + (pokemon_idx * 2)

                    # Apply scaling based on current round
                    level = _get_scaled_level(base_level, current_round)
                except Exception as e:
                    print(f"Error calculating scaled level: {e}")
                    level = mainpokemon_level if mainpokemon_level else 10
            else:
                # Normal wild Pokemon - use player level
                var_level = 3
                if mainpokemon_level or mainpokemon_level != None:
                    try:
                        level = random.randint((mainpokemon_level - (random.randint(0, var_level))), (mainpokemon_level + (random.randint(0, var_level))))  # Random level between 1 and 100
                        if mainpokemon_level == 100:
                            level = 100
                        if level < 0:
                            level = 1
                    except Exception as e:
                        showWarning(f"Error in generate random pokemon{e}")
                        mainpokemon_level = 5
                        level = 5
                else:
                    level = 5
                    min_level = 0

            # Only apply this safety check for non-special battles
            # For Gym/Elite Four/Champion, levels are already set correctly above
            if not is_special_battle:
                if min_level is None or not min_level or mainpokemon_level is None or not mainpokemon_level:
                    level = 5
                    min_level = 0
            if min_level < level:
                id_check = check_id_ok(id)
                if id_check:
                    pass
                else:
                    return generate_random_pokemon(_recursion_depth + 1)
                abilities = search_pokedex(name, "abilities")
                # Filter abilities to include only those with numeric keys
                # numeric_abilities = {k: v for k, v in abilities.items() if k.isdigit()}
                numeric_abilities = None
                try:
                    numeric_abilities = {k: v for k, v in abilities.items() if k.isdigit()}
                except:
                    ability = "No Ability"
                # Check if there are numeric abilities
                if numeric_abilities:
                    # Convert the filtered abilities dictionary values to a list
                    abilities_list = list(numeric_abilities.values())
                    # Select a random ability from the list
                    ability = random.choice(abilities_list)
                else:
                    # Set to "No Ability" if there are no numeric abilities
                    ability = "No Ability"
                # ability = abilities.get("0", "No ability")
                # if ability == "No ability":
                #    ability = abilities.get("H", None)
                type = search_pokedex(name, "types")
                stats = search_pokedex(name, "baseStats")
                enemy_attacks_list = get_all_pokemon_moves(name, level)
                enemy_attacks = []
                if len(enemy_attacks_list) <= 4:
                    enemy_attacks = enemy_attacks_list
                else:
                    enemy_attacks = random.sample(enemy_attacks_list, 4)
                base_experience = search_pokeapi_db_by_id(id, "base_experience")
                growth_rate = search_pokeapi_db_by_id(id, "growth_rate")
                if gender is None:
                    gender = pick_random_gender(name)
                iv = {
                    "hp": random.randint(1, 32),
                    "atk": random.randint(1, 32),
                    "def": random.randint(1, 32),
                    "spa": random.randint(1, 32),
                    "spd": random.randint(1, 32),
                    "spe": random.randint(1, 32)
                }
                ev = {
                    "hp": 0,
                    "atk": 0,
                    "def": 0,
                    "spa": 0,
                    "spd": 0,
                    "spe": 0
                }
                battle_stats = stats
                battle_status = "fighting"
                try:
                    hp_stat = int(stats['hp'])
                except Exception as e:
                    showInfo(f"Error occured: {e}")
                hp = calculate_hp(hp_stat, level, ev, iv)
                max_hp = hp
                global ev_yield
                ev_yield = search_pokeapi_db_by_id(id, "effort_values")
                return name, id, level, ability, type, stats, enemy_attacks, base_experience, growth_rate, hp, max_hp, ev, iv, gender, battle_status, battle_stats
            else:
                return generate_random_pokemon(_recursion_depth + 1)  # Return the result of the recursive call with depth tracking
        except FileNotFoundError:
            showInfo("Error", "Can't open the JSON File.")
            # Set the layout for the dialog

def kill_pokemon():
    """
    Handle defeated Pokemon based on battle_state.
    Routes to appropriate handler: wild/trainer = spawn new, gym/elite4/champion = advance boss battle.
    """
    global level, hp, name, image_url, mainpokemon_xp, mainpokemon_base_experience, mainpokemon_name, mainpokemon_level, mainpokemon_path, mainpokemon_growth_rate, mainpokemon_hp, ev_yield
    global pkmn_window, base_experience

    # Get current battle state to determine routing
    battle_state = _ankimon_get_battle_state()
    _ankimon_log("INFO", "AnkimonBattle", f"kill_pokemon() called - battle_state={battle_state}")

    name = name.capitalize()
    # CRITICAL FIX: Use defeated pokemon's base_experience, not main pokemon's
    exp = int(calc_experience(base_experience, level))
    mainpokemon_level = save_main_pokemon_progress(mainpokemon_path, mainpokemon_level, mainpokemon_name, mainpokemon_base_experience, mainpokemon_growth_rate, exp)
    _ankimon_log("INFO", "AnkimonBattle", f"Awarded {exp} XP to {mainpokemon_name}, now level {mainpokemon_level}")

    # Distribute EXP to Pokemon holding EXP Share (50% of earned EXP)
    try:
        _distribute_exp_share(exp)
    except Exception as e:
        print(f"Error distributing EXP Share: {e}")

    # Track battle wins in progression stats
    try:
        stats_data = _load_progression_stats()
        stats_data["lifetime"]["total_battles_won"] += 1
        stats_data["current_round"]["battles_won"] += 1
        stats_data["session"]["battles_won"] += 1
        stats_data["session"]["xp_gained"] += exp

        # Track specific battle types
        if is_trainer_battle:
            stats_data["lifetime"]["total_trainer_battles"] += 1

            # After defeating Champion, enemy trainer battles have a chance to drop mega stones
            try:
                # Award mega stone from trainer battles (5% drop chance, requires Key Stone)
                mega_state = _load_mega_state()
                if mega_state.get("key_stone_unlocked", False):
                    _award_random_mega_stone("trainer")
            except Exception as e:
                print(f"Error awarding mega stone from trainer: {e}")
        else:
            stats_data["lifetime"]["total_wild_battles"] += 1

        _save_progression_stats(stats_data)
    except Exception:
        pass  # Don't break gameplay if stats tracking fails

    # Reset mega battle state (battle ended)
    try:
        _reset_mega_battle_state()
    except Exception:
        pass

    # Check if gym battle is pending and start it now
    try:
        conf = _ankimon_get_col_conf()
        if conf and conf.get("ankimon_gym_pending"):
            _ankimon_log("INFO", "AnkimonBattle", "Detected queued gym battle after current battle ended")

            # Use atomic transition helper to ensure clean UI state
            if _ankimon_transition_to_gym("queued start after defeat"):
                _ankimon_log("INFO", "AnkimonBattle", "Gym transition successful")
                return
            else:
                _ankimon_log("ERROR", "AnkimonBattle", "Gym transition failed")
                # Fall through to normal flow if transition failed
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonBattle", f"Error starting queued gym battle: {e}")
        import traceback
        traceback.print_exc()

    # Check if Elite Four battle is pending and start it now
    try:
        conf = _ankimon_get_col_conf()
        if conf and conf.get("ankimon_elite_four_pending"):
            _ankimon_log("INFO", "AnkimonBattle", "Detected queued Elite Four battle after current battle ended")

            # Use atomic transition helper to ensure clean UI state
            if _ankimon_transition_to_elite_four("queued start after defeat"):
                _ankimon_log("INFO", "AnkimonBattle", "Elite Four transition successful")
                return
            else:
                _ankimon_log("ERROR", "AnkimonBattle", "Elite Four transition failed")
                # Fall through to normal flow if transition failed
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonBattle", f"Error starting queued Elite Four battle: {e}")
        import traceback
        traceback.print_exc()

    # Check if Champion battle is pending and start it now
    try:
        conf = _ankimon_get_col_conf()
        if conf and conf.get("ankimon_champion_pending"):
            _ankimon_log("INFO", "AnkimonBattle", "Detected queued Champion battle after current battle ended")

            # Use atomic transition helper to ensure clean UI state
            if _ankimon_transition_to_champion("queued start after defeat"):
                _ankimon_log("INFO", "AnkimonBattle", "Champion transition successful")
                return
            else:
                _ankimon_log("ERROR", "AnkimonBattle", "Champion transition failed")
                # Fall through to normal flow if transition failed
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonBattle", f"Error starting queued Champion battle: {e}")
        import traceback
        traceback.print_exc()

    # Route based on battle_state (Requirement D)
    battle_state = _ankimon_get_battle_state()

    # HARD GATE: For roster battles (gym/elite4/champion), DO NOT auto-advance
    # Roster advancement should ONLY happen via Next button handler
    # This prevents "skip every other pokemon" bug from double-advancement
    if battle_state in ["gym", "elite4", "champion"]:
        _ankimon_log("INFO", "AnkimonBattle", f"[HARD GATE] {battle_state} pokemon defeated - NOT auto-advancing (fainted panel controls advancement)")
        _ankimon_log("INFO", "AnkimonBattle", f"[HARD GATE] User must click Next button to advance roster (prevents double-advancement)")
        # XP already awarded above, battle stats tracked
        # Fainted panel is showing (set by enemy HP <= 0 detection)
        # Next button will call spawn_next_*() to advance roster
        return

    # Default: wild or trainer battle - spawn new wild pokemon
    _ankimon_log("INFO", "AnkimonBattle", f"Wild/trainer battle ended - spawning new pokemon (state={battle_state})")
    if pkmn_window is True:
        new_pokemon()  # Show a new random Pokémon

caught = 0

def display_dead_pokemon():
    global pokemon_hp, name, id, level, caught_pokemon, pkmnimgfolder, frontdefault, addon_dir, caught
    # Create the dialog
    w_dead_pokemon = QDialog(mw)
    w_dead_pokemon.setWindowTitle(f"Would you want to kill or catch the wild {name} ?")
    # Create a layout for the dialog
    layout2 = QVBoxLayout()
    # Display the Pokémon image
    pkmnimage_file = f"{id}.png"
    pkmnimage_path = frontdefault / pkmnimage_file
    pkmnimage_label = QLabel()
    pkmnpixmap = QPixmap()
    pkmnpixmap.load(str(pkmnimage_path))
    # Calculate the new dimensions to maintain the aspect ratio
    max_width = 200
    original_width = pkmnpixmap.width()
    original_height = pkmnpixmap.height()

    if original_width > max_width:
        new_width = max_width
        new_height = (original_height * max_width) // original_width
        pkmnpixmap = pkmnpixmap.scaled(new_width, new_height)

    # Create a painter to add text on top of the image
    painter2 = QPainter(pkmnpixmap)

    # Capitalize the first letter of the Pokémon's name
    capitalized_name = name.capitalize()
    # Create level text
    lvl = (f" Level: {level}")

    # Draw the text on top of the image
    font = QFont()
    font.setPointSize(16)  # Adjust the font size as needed
    painter2.setFont(font)
    fontlvl = QFont()
    fontlvl.setPointSize(12)
    painter2.end()

    # Create a QLabel for the capitalized name
    name_label = QLabel(capitalized_name)
    name_label.setFont(font)

    # Create a QLabel for the level
    level_label = QLabel(lvl)
    # Align to the center
    level_label.setFont(fontlvl)

    # Create buttons for catching and killing the Pokémon
    catch_button = QPushButton("Catch Pokémon")
    kill_button = QPushButton("Defeat Pokémon")
    qconnect(catch_button.clicked, catch_pokemon)
    qconnect(kill_button.clicked, kill_pokemon)

    # Set the merged image as the pixmap for the QLabel
    pkmnimage_label.setPixmap(pkmnpixmap)
    layout2.addWidget(pkmnimage_label)

    # add all widgets to the dialog window
    layout2.addWidget(name_label)
    layout2.addWidget(level_label)
    layout2.addWidget(catch_button)
    layout2.addWidget(kill_button)

    # align things needed to middle
    pkmnimage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Align to the center

    # Set the layout for the dialog
    w_dead_pokemon.setLayout(layout2)

    if w_dead_pokemon is not None:
        # Close the existing dialog if it's open
        w_dead_pokemon.accept()
    # Show the dialog
    result = w_dead_pokemon.exec()
    # Check the result to determine if the user closed the dialog
    if result == QDialog.Rejected:
        w_dead_pokemon = None  # Reset the global window reference

def get_pokemon_by_category(category_name):
    # Reload the JSON data from the file
    global all_species_path
    with open(all_species_path, 'r') as file:
        pokemon_data = json.load(file)
    # Convert the input to lowercase to match the values in our JSON data
    category_name = category_name.lower()

    # Filter the Pokémon data to only include those in the given tier
    pokemon_in_tier = [pokemon['name'] for pokemon in pokemon_data if pokemon['Tier'].lower() == category_name]
    random_pokemon_name_from_tier = f"{(random.choice(pokemon_in_tier)).lower()}"
    random_pokemon_name_from_tier = special_pokemon_names_for_min_level(random_pokemon_name_from_tier)
    return random_pokemon_name_from_tier #return random pokemon name from that category

def choose_random_pkmn_from_tier():
    """
    NEW WEIGHTED RARITY SYSTEM for wild encounters only.
    Uses fixed probabilities instead of progression-based tiers.
    Trainer/Gym/Elite Four/Champion battles are NOT affected.

    Rarity weights (wild encounters only):
    - COMMON:     75.0%
    - UNCOMMON:   20.0%
    - RARE:        4.5%
    - LEGENDARY:   0.45%
    - MYTHICAL:    0.05%
    """
    try:
        # Define weighted rarity tiers
        tiers = ["COMMON", "UNCOMMON", "RARE", "LEGENDARY", "MYTHICAL"]
        weights = [75.0, 20.0, 4.5, 0.45, 0.05]

        # Randomly select a tier based on weights
        tier = random.choices(tiers, weights=weights, k=1)[0]

        # Get a random Pokemon ID from the selected tier
        id, pokemon_species = get_pokemon_id_by_tier(tier)

        # Log encounter for debugging (only if Developer Mode is active)
        try:
            global developer_menu
            if developer_menu and developer_menu.menuAction().isVisible():
                print(f"[Wild] tier={tier} id={id}")
        except:
            pass

        return id, pokemon_species
    except Exception as e:
        showWarning(f"An error occurred with generating Pokémon: {e}\nPlease report this error.")
        # Fallback to a safe Common tier selection
        return get_pokemon_id_by_tier("COMMON")

def get_pokemon_id_by_tier(tier):
    global pokemon_species_normal_path, pokemon_species_baby_path, pokemon_species_mythical_path, pokemon_species_ultra_path, pokemon_species_legendary_path
    global pokemon_species_common_path, pokemon_species_uncommon_path, pokemon_species_rare_path
    id_species_path = None

    # Support both old and new tier naming systems
    if tier == "Normal":
        id_species_path = pokemon_species_normal_path
    elif tier == "Baby":
        id_species_path = pokemon_species_baby_path
    elif tier == "Ultra":
        id_species_path = pokemon_species_ultra_path
    elif tier == "Legendary":
        id_species_path = pokemon_species_legendary_path
    elif tier == "Mythical":
        id_species_path = pokemon_species_mythical_path
    # New rarity tiers for wild encounters
    elif tier == "COMMON":
        id_species_path = pokemon_species_common_path
    elif tier == "UNCOMMON":
        id_species_path = pokemon_species_uncommon_path
    elif tier == "RARE":
        id_species_path = pokemon_species_rare_path

    with open(id_species_path, 'r') as file:
        id_data = json.load(file)

    pokemon_species = f"{tier}"
    # Select a random Pokemon ID from those in the tier
    random_pokemon_id = random.choice(id_data)
    return random_pokemon_id, pokemon_species

def roll_for_shiny():
    """
    Roll for shiny Pokemon based on SHINY_RATE (1/512 by default).
    Returns True if shiny, False otherwise.
    """
    global SHINY_RATE
    return random.random() < SHINY_RATE

def save_caught_pokemon(nickname):
    # Create a dictionary to store the Pokémon's data
    # add all new values like hp as max_hp, evolution_data, description and growth rate
    global achievements
    global pokemon_species
    if pokemon_species != None:
        if pokemon_species == "Normal":
            check = check_for_badge(achievements,17)
            if check is False:
                achievements = receive_badge(17,achievements)
                test_window.display_badge(17)
        elif pokemon_species == "Baby":
            check = check_for_badge(achievements,18)
            if check is False:
                achievements = receive_badge(18,achievements)
                test_window.display_badge(18)
        elif pokemon_species == "Ultra":
            check = check_for_badge(achievements,8)
            if check is False:
                achievements = receive_badge(8,achievements)
                test_window.display_badge(8)
        elif pokemon_species == "Legendary":
            check = check_for_badge(achievements,9)
            if check is False:
                achievements = receive_badge(9,achievements)
                test_window.display_badge(9)
        elif pokemon_species == "Mythical":
            check = check_for_badge(achievements,10)
            if check is False:
                achievements = receive_badge(10,achievements)
                test_window.display_badge(10)

    # Handle special variants (Shadow Mewtwo, etc.) - use base Pokemon for lookups
    lookup_name = "mewtwo" if name == "Shadow Mewtwo" else name.lower()

    stats = search_pokedex(lookup_name,"baseStats")
    stats["xp"] = 0
    ev = {
      "hp": 0,
      "atk": 0,
      "def": 0,
      "spa": 0,
      "spd": 0,
      "spe": 0
    }
    evos = search_pokedex(lookup_name, "evos")
    if evos is None:
        evos = ""

    # Capture shiny status from current wild encounter
    global current_wild_is_shiny, current_wild_variant
    is_shiny = current_wild_is_shiny if current_wild_is_shiny else False

    # Capture variant (e.g., "shadow", "primal", etc.)
    variant = current_wild_variant if current_wild_variant else None

    caught_pokemon = {
        "name": name.capitalize(),
        "nickname": nickname,
        "level": level,
        "gender": gender,
        "id": search_pokedex(lookup_name,'num'),
        "ability": ability,
        "type": type,
        "stats": stats,
        "ev": ev,
        "iv": iv,
        "attacks": enemy_attacks,
        "base_experience": base_experience,
        "current_hp": calculate_hp(int(stats["hp"]),level, ev, iv),
        "growth_rate": growth_rate,
        "evos": evos,
        "is_shiny": is_shiny,
        "variant": variant
    }
    # Load existing Pokémon data if it exists
    if mypokemon_path.is_file():
        with open(mypokemon_path, "r") as json_file:
            caught_pokemon_data = json.load(json_file)
    else:
        caught_pokemon_data = []

    # Append the caught Pokémon's data to the list
    caught_pokemon_data.append(caught_pokemon)

    # Debug log for capture
    print(f"[Shiny] Captured: id={caught_pokemon['id']} is_shiny={is_shiny} name={caught_pokemon['name']}")

    # Save the caught Pokémon's data to a JSON file
    with open(str(mypokemon_path), "w") as json_file:
        json.dump(caught_pokemon_data, json_file, indent=2)

    # Track Pokemon caught in progression stats
    try:
        stats_data = _load_progression_stats()
        stats_data["lifetime"]["total_pokemon_caught"] += 1
        stats_data["current_round"]["pokemon_caught"] += 1
        stats_data["session"]["pokemon_caught"] += 1
        _save_progression_stats(stats_data)
    except Exception:
        pass  # Don't break gameplay if stats tracking fails

def find_details_move(move_name):
    global moves_file_path
    try:
        with open(moves_file_path, "r", encoding="utf-8") as json_file:
            moves_data = json.load(json_file)
            move = moves_data.get(move_name.lower())  # Use get() to access the move by name
            if move:
                return move
            else:
                showInfo(f"Move '{move_name}' not found.")
                return None
    except FileNotFoundError:
        showInfo("Moves Data File Missing!\nPlease Download Moves Data")
        return None
    except json.JSONDecodeError as e:
        showInfo(f"Error decoding JSON: {e}")
        return None
    except Exception as e:
        showWarning(f"There is an issue in find_details_move{e}")

def save_main_pokemon_progress(mainpokemon_path, mainpokemon_level, mainpokemon_name, mainpokemon_base_experience, mainpokemon_growth_rate, exp):
    global mainpokemon_current_hp, mainpokemon_ev, ev_yield, mainpokemon_evolution, mainpokemon_xp, pop_up_dialog_message_on_defeat
    experience = find_experience_for_level(mainpokemon_growth_rate, mainpokemon_level)
    if mainpokemon_level != 100:
        mainpokemon_xp += exp
    if mainpokemon_path.is_file():
        with open(mainpokemon_path, "r") as json_file:
            main_pokemon_data = json.load(json_file)
    else:
        showWarning("Missing Mainpokemon Data !")
    while int(experience) < int(mainpokemon_xp) and mainpokemon_level != 100:
        mainpokemon_level += 1
        msg = ""
        msg += f"Your {mainpokemon_name} is now level {mainpokemon_level} !"
        color = "#6A4DAC" #pokemon leveling info color for tooltip
        global achievements
        check = check_for_badge(achievements,5)
        if check is False:
            achievements = receive_badge(5,achievements)
            test_window.display_badge(5)
        try:
            tooltipWithColour(msg, color)
        except:
            pass
        if pop_up_dialog_message_on_defeat is True:
            showInfo(f"{msg}")
        mainpokemon_xp = int(mainpokemon_xp) - int(experience)
        name = f"{mainpokemon_name}"

        # Handle special variants (Shadow Mewtwo, etc.) - use base Pokemon for lookups
        lookup_name = "mewtwo" if name == "Shadow Mewtwo" else name.lower()

        # Update mainpokemon_evolution and handle evolution logic
        mainpokemon_evolution = search_pokedex(lookup_name, "evos")
        if mainpokemon_evolution:
            for pokemon in mainpokemon_evolution:
                min_level = search_pokedex(pokemon.lower(), "evoLevel")
                evo_type = search_pokedex(pokemon.lower(), "evoType")
                evo_item = search_pokedex(pokemon.lower(), "evoItem")

                # Trigger evolution if:
                # 1. Current level >= evolution level (handles over-leveled captures)
                # 2. It's a level-based evolution (no item required)
                if (min_level and mainpokemon_level >= min_level and
                    (evo_type is None or evo_type == "levelUp") and
                    (evo_item is None or evo_item == "None")):
                    msg = ""
                    msg += f"{mainpokemon_name} is about to evolve to {pokemon} at level {mainpokemon_level}"
                    if mainpokemon_level > min_level:
                        msg += f" (evolution level: {min_level})"
                    showInfo(f"{msg}")
                    color = "#6A4DAC"
                    try:
                        tooltipWithColour(msg, color)
                    except:
                        pass
                    evo_window.display_pokemon_evo(mainpokemon_name.lower())
                else:
                    for mainpkmndata in main_pokemon_data:
                        if mainpkmndata["name"] == mainpokemon_name.capitalize():
                            attacks = mainpkmndata["attacks"]
                            new_attacks = get_levelup_move_for_pokemon(mainpokemon_name.lower(),int(mainpokemon_level))
                            if new_attacks:
                                msg = ""
                                msg += f"Your {mainpokemon_name.capitalize()} can learn a new attack !"
                            for new_attack in new_attacks:
                                if len(attacks) < 4:
                                    attacks.append(new_attack)
                                    msg += f"\n Your {mainpokemon_name.capitalize()} has learned {new_attack} !"
                                    color = "#6A4DAC"
                                    tooltipWithColour(msg, color)
                                    if pop_up_dialog_message_on_defeat is True:
                                        showInfo(f"{msg}")
                                else:
                                    dialog = AttackDialog(attacks, new_attack)
                                    if dialog.exec() == QDialog.DialogCode.Accepted:
                                        selected_attack = dialog.selected_attack
                                        index_to_replace = None
                                        for index, attack in enumerate(attacks):
                                            if attack == selected_attack:
                                                index_to_replace = index
                                                pass
                                            else:
                                                pass
                                        # If the attack is found, replace it with 'new_attack'
                                        if index_to_replace is not None:
                                            attacks[index_to_replace] = new_attack
                                            showInfo(
                                                f"Replaced '{selected_attack}' with '{new_attack}'")
                                        else:
                                            showInfo(f"'{selected_attack}' not found in the list")
                                    else:
                                        # Handle the case where the user cancels the dialog
                                        showInfo(f"{new_attack} will be discarded.")
                            mainpkmndata["attacks"] = attacks
                            break
        else:
            for mainpkmndata in main_pokemon_data:
                if mainpkmndata["name"] == mainpokemon_name.capitalize():
                    attacks = mainpkmndata["attacks"]
                    new_attacks = get_levelup_move_for_pokemon(mainpokemon_name.lower(), int(mainpokemon_level))
                    if new_attacks:
                        showInfo(f"Your {mainpokemon_name.capitalize()} can now learn a new attack !")
                    for new_attack in new_attacks:
                        if len(attacks) < 4:
                            attacks.append(new_attack)
                        else:
                            dialog = AttackDialog(attacks, new_attack)
                            if dialog.exec() == QDialog.DialogCode.Accepted:
                                selected_attack = dialog.selected_attack
                                index_to_replace = None
                                for index, attack in enumerate(attacks):
                                    if attack == selected_attack:
                                        index_to_replace = index
                                        pass
                                    else:
                                        pass
                                # If the attack is found, replace it with 'new_attack'
                                if index_to_replace is not None:
                                    attacks[index_to_replace] = new_attack
                                    showInfo(
                                        f"Replaced '{selected_attack}' with '{new_attack}'")
                                else:
                                    showInfo(f"'{selected_attack}' not found in the list")
                            else:
                                # Handle the case where the user cancels the dialog
                                showInfo("No attack selected")
                    mainpkmndata["attacks"] = attacks
                    break
    else:
        msg = ""
        msg += f"Your {mainpokemon_name} has gained {exp} XP.\n {experience} exp is needed for next level \n Your pokemon currently has {mainpokemon_xp}"
        color = "#6A4DAC" #pokemon leveling info color for tooltip
        try:
            tooltipWithColour(msg, color)
        except:
            pass
        if pop_up_dialog_message_on_defeat is True:
            showInfo(f"{msg}")
    # Load existing Pokémon data if it exists

    for mainpkmndata in main_pokemon_data:
        mainpkmndata["stats"]["xp"] = int(mainpokemon_xp)
        mainpkmndata["level"] = int(mainpokemon_level)
        mainpkmndata["current_hp"] = int(mainpokemon_current_hp)
        #for stat, values in ev_yield.items():
        #for attribute, value in values.items():
        #mainpkmndata["ev"][stat][attribute] += int(value)
        mainpkmndata["ev"]["hp"] += ev_yield["hp"]
        mainpkmndata["ev"]["atk"] += ev_yield["attack"]
        mainpkmndata["ev"]["def"] += ev_yield["defense"]
        mainpkmndata["ev"]["spa"] += ev_yield["special-attack"]
        mainpkmndata["ev"]["spd"] += ev_yield["special-defense"]
        mainpkmndata["ev"]["spe"] += ev_yield["speed"]
    mypkmndata = mainpkmndata
    mainpkmndata = [mainpkmndata]
    # Save the caught Pokémon's data to a JSON file
    with open(str(mainpokemon_path), "w") as json_file:
        json.dump(mainpkmndata, json_file, indent=2)

    # Find the specified Pokémon's data in mainpokemondata
    #selected_pokemon_data = None
    #for pokemon_data in mainpkmndata:
        #if pokemon_data["name"] == mainpokemon_name:
            #selected_pokemon_data = pokemon_data

    #if selected_pokemon_data is not None:
        # Modify the selected Pokémon's data
        #selected_pokemon_data["stats"]["xp"] = mainpokemon_xp
        #selected_pokemon_data["level"] = mainpokemon_level  # Replace with the actual level
        #selected_pokemon_data["current_hp"] = mainpokemon_current_hp  # save current hp

        # Load data from the output JSON file
    with open(str(mypokemon_path), "r") as output_file:
        mypokemondata = json.load(output_file)

        # Find and replace the specified Pokémon's data in mypokemondata
        for index, pokemon_data in enumerate(mypokemondata):
            if pokemon_data["name"] == mainpokemon_name:
                mypokemondata[index] = mypkmndata
                break
        # Save the modified data to the output JSON file
        with open(str(mypokemon_path), "w") as output_file:
            json.dump(mypokemondata, output_file, indent=2)

    return mainpokemon_level

def evolve_pokemon(pkmn_name):
    global mainpokemon_path
    global addon_dir
    global achievements
    try:
        evoName = search_pokedex(pkmn_name.lower(), "evos")
        evoName = f"{evoName[0]}"
        with open(mypokemon_path, "r") as json_file:
            captured_pokemon_data = json.load(json_file)
            pokemon = None
            if captured_pokemon_data:
                for pokemon_data in captured_pokemon_data:
                    if pokemon_data['name'] == pkmn_name.capitalize():
                        pokemon = pokemon_data
                        if pokemon is not None:
                            pokemon["name"] = evoName.capitalize()
                            evoId = int(search_pokedex(evoName.lower(), "num"))
                            pokemon["id"] = evoId
                            # pokemon["ev"] = ev
                            # pokemon["iv"] = iv
                            pokemon["type"] = search_pokedex(evoName.lower(), "types")
                            pokemon["evos"] = []
                            attacks = pokemon["attacks"]
                            new_attacks = get_random_moves_for_pokemon(evoName, int(pokemon["level"]))
                            for new_attack in new_attacks:
                                if len(attacks) < 4:
                                    attacks.append(new_attack)
                                else:
                                    dialog = AttackDialog(attacks, new_attack)
                                    if dialog.exec() == QDialog.DialogCode.Accepted:
                                        selected_attack = dialog.selected_attack
                                        index_to_replace = None
                                        for index, attack in enumerate(attacks):
                                            if attack == selected_attack:
                                                index_to_replace = index
                                                pass
                                            else:
                                                pass
                                        # If the attack is found, replace it with 'new_attack'
                                        if index_to_replace is not None:
                                            attacks[index_to_replace] = new_attack
                                            showInfo(
                                                f"Replaced '{selected_attack}' with '{new_attack}'")
                                        else:
                                            showInfo(f"'{selected_attack}' not found in the list")
                                    else:
                                        # Handle the case where the user cancels the dialog
                                        showInfo("No attack selected")
                            pokemon["attacks"] = attacks
                            if search_pokedex(evoName, "evos"):
                                pokemon["evos"].append(search_pokedex(evoName.lower(), "evos"))
                            stats = search_pokedex(evoName.lower(), "baseStats")
                            pokemon["stats"] = stats
                            pokemon["stats"]["xp"] = 0
                            hp_stat = int(stats['hp'])
                            hp = calculate_hp(hp_stat, level, ev, iv)
                            pokemon["current_hp"] = int(hp)
                            #pokemon["gender"] = pick_random_gender(evoName.lower()) dont replace gender
                            pokemon["growth_rate"] = search_pokeapi_db_by_id(evoId,"growth_rate")
                            pokemon["base_experience"] = search_pokeapi_db_by_id(evoId,"base_experience")
                            #pokemon["growth_rate"] = search_pokeapi_db(evoName.lower(), "growth_rate")
                            #pokemon["base_experience"] = search_pokeapi_db(evoName.lower(), "base_experience")
                            abilities = search_pokedex(evoName.lower(), "abilities")
                            # Filter abilities to include only those with numeric keys
                            # numeric_abilities = {k: v for k, v in abilities.items() if k.isdigit()}
                            numeric_abilities = None
                            try:
                                numeric_abilities = {k: v for k, v in abilities.items() if k.isdigit()}
                            except:
                                ability = "No Ability"
                            # Check if there are numeric abilities
                            if numeric_abilities:
                                # Convert the filtered abilities dictionary values to a list
                                abilities_list = list(numeric_abilities.values())
                                # Select a random ability from the list
                                pokemon["ability"] = random.choice(abilities_list)
                            else:
                                # Set to "No Ability" if there are no numeric abilities
                                pokemon["ability"] = "No Ability"
                            # Load data from the output JSON file
                            with open(str(mypokemon_path), "r") as output_file:
                                mypokemondata = json.load(output_file)
                                # Find and replace the specified Pokémon's data in mypokemondata
                                for index, pokemon_data in enumerate(mypokemondata):
                                    if pokemon_data["name"] == pkmn_name.capitalize():
                                        mypokemondata[index] = pokemon
                                        break
                                        # Save the modified data to the output JSON file
                                with open(str(mypokemon_path), "w") as output_file:
                                    json.dump(mypokemondata, output_file, indent=2)
                            with open(str(mainpokemon_path), "r") as output_file:
                                mainpokemon_data = json.load(output_file)
                                # Find and replace the specified Pokémon's data in mypokemondata
                                for index, pokemon_data in enumerate(mainpokemon_data):
                                    if pokemon_data["name"] == pkmn_name.capitalize():
                                        mypokemondata[index] = pokemon
                                        break
                                    else:
                                        pass
                                            # Save the modified data to the output JSON file
                                with open(str(mainpokemon_path), "w") as output_file:
                                        pokemon = [pokemon]
                                        json.dump(pokemon, output_file, indent=2)
                            showInfo(f"Your {pkmn_name.capitalize()} has evolved to {evoName.capitalize()}! \n You can now close this Window.")
    except Exception as e:
        showWarning(f"{e}")
    prevo_name = pkmn_name
    evo_window.display_evo_pokemon(evoName.capitalize(), prevo_name)
    check = check_for_badge(achievements,16)
    if check is False:
        receive_badge(16,achievements)
        test_window.display_badge(16)

def cancel_evolution(pkmn_name):
    global mainpokemon_current_hp, mainpokemon_ev, ev_yield, mainpokemon_evolutions
    # Load existing Pokémon data if it exists
    if mainpokemon_path.is_file():
        with open(mainpokemon_path, "r") as json_file:
            main_pokemon_data = json.load(json_file)
            for pokemon in main_pokemon_data:
                if pokemon["name"] == pkmn_name.capitalize():
                    attacks = pokemon["attacks"]
                    new_attacks = get_random_moves_for_pokemon(pkmn_name.lower(), int(main_pokemon_data["level"]))
                    for new_attack in new_attacks:
                        if len(attacks) < 4:
                            attacks.append(new_attack)
                        else:
                            dialog = AttackDialog(attacks, new_attack)
                            if dialog.exec() == QDialog.DialogCode.Accepted:
                                selected_attack = dialog.selected_attack
                                index_to_replace = None
                                for index, attack in enumerate(attacks):
                                    if attack == selected_attack:
                                        index_to_replace = index
                                        pass
                                    else:
                                        pass
                                # If the attack is found, replace it with 'new_attack'
                                if index_to_replace is not None:
                                    attacks[index_to_replace] = new_attack
                                    showInfo(
                                        f"Replaced '{selected_attack}' with '{new_attack}'")
                                else:
                                    showInfo(f"'{selected_attack}' not found in the list")
                            else:
                                # Handle the case where the user cancels the dialog
                                showInfo("No attack selected")
                    break
            for mainpkmndata in main_pokemon_data:
                mainpkmndata["stats"]["xp"] = int(mainpokemon_xp)
                mainpkmndata["level"] = int(mainpokemon_level)
                mainpkmndata["current_hp"] = int(mainpokemon_current_hp)
                mainpkmndata["ev"]["hp"] += ev_yield["hp"]
                mainpkmndata["ev"]["atk"] += ev_yield["attack"]
                mainpkmndata["ev"]["def"] += ev_yield["defense"]
                mainpkmndata["ev"]["spa"] += ev_yield["special-attack"]
                mainpkmndata["ev"]["spd"] += ev_yield["special-defense"]
                mainpkmndata["ev"]["spe"] += ev_yield["speed"]
                mainpkmndata["attacks"] = attacks
    mypkmndata = mainpkmndata
    mainpkmndata = [mainpkmndata]
    # Save the caught Pokémon's data to a JSON file
    with open(str(mainpokemon_path), "w") as json_file:
        json.dump(mainpkmndata, json_file, indent=2)

    # Find the specified Pokémon's data in mainpokemondata
    #selected_pokemon_data = None
    #for pokemon_data in mainpkmndata:
        #if pokemon_data["name"] == mainpokemon_name:
            #selected_pokemon_data = pokemon_data

    #if selected_pokemon_data is not None:
        # Modify the selected Pokémon's data
        #selected_pokemon_data["stats"]["xp"] = mainpokemon_xp
        #selected_pokemon_data["level"] = mainpokemon_level  # Replace with the actual level
        #selected_pokemon_data["current_hp"] = mainpokemon_current_hp  # save current hp
        #selected_pokemon_data["attacks"] = attacks
        #selected_pokemon_data["ev"]["hp"] += ev_yield["hp"]
        #selected_pokemon_data["ev"]["atk"] += ev_yield["attack"]
        #selected_pokemon_data["ev"]["def"] += ev_yield["defense"]
        #selected_pokemon_data["ev"]["spa"] += ev_yield["special-attack"]
        #selected_pokemon_data["ev"]["spd"] += ev_yield["special-defense"]
        #selected_pokemon_data["ev"]["spe"] += ev_yield["speed"]

        # Load data from the output JSON file
    with open(str(mypokemon_path), "r") as output_file:
        mypokemondata = json.load(output_file)

        # Find and replace the specified Pokémon's data in mypokemondata
        for index, pokemon_data in enumerate(mypokemondata):
            if pokemon_data["name"] == pkmn_name:
                mypokemondata[index] = mypkmndata
                break
        # Save the modified data to the output JSON file
        with open(str(mypokemon_path), "w") as output_file:
            json.dump(mypokemondata, output_file, indent=2)

def calc_experience(base_experience, enemy_level):
    exp = base_experience * enemy_level / 7
    return exp

def catch_pokemon(nickname):
    # --- Special battles: you cannot catch leader/Elite Four/Champion Pokémon; prevent this action ---
    try:
        if _ankimon_is_gym_active():
            try:
                showInfo("Gym battle: you can't catch a leader's Pokémon. The battle will continue automatically.")
            except:
                pass
            return
        elif _ankimon_is_elite_four_active():
            try:
                showInfo("Elite Four battle: you can't catch an Elite Four member's Pokémon. The battle will continue automatically.")
            except:
                pass
            return
        elif _ankimon_is_champion_active():
            try:
                showInfo("Champion battle: you can't catch the Champion's Pokémon. The battle will continue automatically.")
            except Exception:
                pass
            return
    except Exception:
        pass

    global pokemon_hp, name, ability, enemy_attacks, type, stats, base_experience, level, growth_rate, gender, id, iv, pop_up_dialog_message_on_defeat
    global mypokemon_path, caught
    caught += 1
    if caught == 1:
        name = name.capitalize()
        if nickname is None or not nickname:  # Wenn None oder leer
            save_caught_pokemon(nickname)
        else:
            save_caught_pokemon(name)
        msg = f"You caught {name}!"
        if pop_up_dialog_message_on_defeat is True:
            showInfo(f"{msg}") # Display a message when the Pokémon is caught
        color = "#6A4DAC" #pokemon leveling info color for tooltip
        try:
            tooltipWithColour(msg, color)
        except:
            pass

        # Check if gym battle is pending and start it now
        try:
            conf = _ankimon_get_col_conf()
            if conf and conf.get("ankimon_gym_pending"):
                _ankimon_log("INFO", "AnkimonBattle", "Detected queued gym battle after catching pokemon")

                # Use atomic transition helper to ensure clean UI state
                if _ankimon_transition_to_gym("queued start after catch"):
                    _ankimon_log("INFO", "AnkimonBattle", "Gym transition successful after catch")
                    return
                else:
                    _ankimon_log("ERROR", "AnkimonBattle", "Gym transition failed after catch")
                    # Fall through to spawn new pokemon if transition failed
        except Exception as e:
            _ankimon_log("ERROR", "AnkimonBattle", f"Error in gym transition after catch: {e}")
            import traceback
            traceback.print_exc()

        # Check if Elite Four battle is pending and start it now
        try:
            conf = _ankimon_get_col_conf()
            if conf and conf.get("ankimon_elite_four_pending"):
                _ankimon_log("INFO", "AnkimonBattle", "Detected queued Elite Four battle after catching pokemon")

                # Use atomic transition helper to ensure clean UI state
                if _ankimon_transition_to_elite_four("queued start after catch"):
                    _ankimon_log("INFO", "AnkimonBattle", "Elite Four transition successful after catch")
                    return
                else:
                    _ankimon_log("ERROR", "AnkimonBattle", "Elite Four transition failed after catch")
                    # Fall through to spawn new pokemon if transition failed
        except Exception as e:
            _ankimon_log("ERROR", "AnkimonBattle", f"Error in Elite Four transition after catch: {e}")
            import traceback
            traceback.print_exc()

        # Check if Champion battle is pending and start it now
        try:
            conf = _ankimon_get_col_conf()
            if conf and conf.get("ankimon_champion_pending"):
                _ankimon_log("INFO", "AnkimonBattle", "Detected queued Champion battle after catching pokemon")

                # Use atomic transition helper to ensure clean UI state
                if _ankimon_transition_to_champion("queued start after catch"):
                    _ankimon_log("INFO", "AnkimonBattle", "Champion transition successful after catch")
                    return
                else:
                    _ankimon_log("ERROR", "AnkimonBattle", "Champion transition failed after catch")
                    # Fall through to spawn new pokemon if transition failed
        except Exception as e:
            _ankimon_log("ERROR", "AnkimonBattle", f"Error in Champion transition after catch: {e}")
            import traceback
            traceback.print_exc()

        # Refresh captured Pokemon collection dialog if it's open
        try:
            global pokecollection_win
            if pokecollection_win and pokecollection_win.isVisible():
                pokecollection_win.refresh_pokemon_collection()
        except Exception:
            pass

        new_pokemon()  # Show a new random Pokémon
    else:
        if pop_up_dialog_message_on_defeat is True:
            showInfo("You have already caught the pokemon. Please close this window!") # Display a message when the Pokémon is caught

def get_random_starter():
    global addon_dir, starters_path    # event if pokemon
    category = "Starter"
    try:
        # Reload the JSON data from the file
        with open(str(starters_path), 'r') as file:
            pokemon_in_tier = json.load(file)
            # Convert the input to lowercase to match the values in our JSON data
            category_name = category.lower()
            # Filter the Pokémon data to only include those in the given tier
            water_starter = []
            fire_starter = []
            grass_starter = []
            for pokemon in pokemon_in_tier:
                pokemon = (pokemon).lower()
                types = search_pokedex(pokemon, "types")
                for type in types:
                    if type == "Grass":
                        grass_starter.append(pokemon)
                    if type == "Fire":
                        fire_starter.append(pokemon)
                    if type == "Water":
                        water_starter.append(pokemon)
            random_gen = random.randint(0, 6)
            water_start = f"{water_starter[random_gen]}"
            fire_start = f"{fire_starter[random_gen]}"
            grass_start = f"{grass_starter[random_gen]}"
            return water_start, fire_start, grass_start
    except Exception as e:
        showWarning(f"Error in get_random_starter: {e}")
        return None, None, None


def calculate_max_hp_wildpokemon():
    global stats, level, ev, iv
    wild_pk_max_hp = calculate_hp(stats["hp"], level, ev, iv)
    return wild_pk_max_hp

def generate_enemy_trainer_pokemon():
    """Generate a slightly tougher enemy trainer Pokemon with random variation"""
    global mainpokemon_level

    # Get a random Pokemon first
    name, id, level, ability, type, stats, enemy_attacks, base_experience, growth_rate, hp, max_hp, ev, iv, gender, battle_status, battle_stats = generate_random_pokemon()

    # Make it slightly tougher with random variation:
    # 1. Level can be -1 to +2 relative to player (more random, less guaranteed tough)
    level_variation = random.randint(-1, 2)
    trainer_level = max(5, mainpokemon_level + level_variation)  # Never below level 5

    # 2. Slightly better IVs on average (10-20 range, vs wild pokemon's full random)
    trainer_iv = {
        "hp": random.randint(10, 20),
        "atk": random.randint(10, 20),
        "def": random.randint(10, 20),
        "spa": random.randint(10, 20),
        "spd": random.randint(10, 20),
        "spe": random.randint(10, 20)
    }

    # 3. Recalculate HP with new level and IVs
    trainer_hp = calculate_hp(stats["hp"], trainer_level, ev, trainer_iv)

    return name, id, trainer_level, ability, type, stats, enemy_attacks, base_experience, growth_rate, trainer_hp, trainer_hp, ev, trainer_iv, gender, battle_status, battle_stats

def get_random_trainer():
    """Select a random enemy trainer with their sprite and battle scene"""
    global enemy_battles_path

    # Define trainer types with their associated sprites and scenes
    trainers = {
        "Plasma Grunt": {
            "sprites": ["plasma_grunt_female.png", "plama_grunt_male.png"],
            "scene": "plasmagrunts_pkmnbattlescene.png",
            "title": "Team Plasma Grunt"
        },
        "Ghetsis": {
            "sprites": ["ghetsis.png"],
            "scene": "plasmagrunts_pkmnbattlescene.png",
            "title": "Ghetsis"
        },
        "Shadow Triad": {
            "sprites": ["shadow_triad.png"],
            "scene": "plasmagrunts_pkmnbattlescene.png",
            "title": "Shadow Triad"
        },
        "Veteran": {
            "sprites": ["veteran_m.png"],
            "scene": "pkmnbattlescene.png",
            "title": "Veteran Trainer"
        },
        "Ranger": {
            "sprites": ["pokémon_ranger_female.png", "pokémon_ranger_male.png"],
            "scene": "grass_pkmnbattlescene.png",
            "title": "Pokémon Ranger"
        },
        "Policeman": {
            "sprites": ["policeman.png"],
            "scene": "metalcity_pkmnbattlescene.png",
            "title": "Officer"
        },
        "Hooligans": {
            "sprites": ["hooligans.png"],
            "scene": "pkmnbattlescene.png",
            "title": "Street Hooligans"
        },
        "Gym Leader": {
            "sprites": ["lenora.png", "marshal.png"],
            "scene": "pkmnbattlescene.png",
            "title": "Veteran Trainer"  # Changed from "Gym Leader" to avoid confusion
        }
    }

    # Randomly select a trainer type
    trainer_type = random.choice(list(trainers.keys()))
    trainer_data = trainers[trainer_type]

    # Randomly select a sprite from that trainer's available sprites
    sprite = random.choice(trainer_data["sprites"])

    return trainer_data["title"], sprite, trainer_data["scene"]

def check_enemy_trainer_encounter():
    """Check if it's time for an enemy trainer battle and show dialog"""
    global enemy_trainer_card_counter, test_window, pkmn_window, current_trainer_name

    # Don't interrupt special battles (gym, Elite Four, Champion)
    if _ankimon_is_gym_active() or _ankimon_is_elite_four_active() or _ankimon_is_champion_active():
        # Counter still increments but don't trigger battle
        # Will trigger after special battle ends
        return False

    # Every 20 cards, trigger potential enemy trainer battle
    if enemy_trainer_card_counter >= 20:
        # Reset counter
        enemy_trainer_card_counter = 0

        # Select random trainer
        trainer_name, trainer_sprite, trainer_scene = get_random_trainer()
        current_trainer_name = trainer_name

        # Show dialog asking if user wants to engage
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Enemy Trainer Encountered!")
        msg.setText(f"A {trainer_name} challenges you to a battle!")
        msg.setInformativeText("Do you want to accept the challenge?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)

        result = msg.exec()

        if result == QMessageBox.StandardButton.Yes:
            # User accepted - start enemy trainer battle
            start_enemy_trainer_battle(trainer_name, trainer_sprite, trainer_scene)
            return True
        else:
            # User declined - show message
            tooltipWithColour(f"You declined the battle. The {trainer_name} walks away...", "#FFA500")
            return False

    return False

def start_enemy_trainer_battle(trainer_name, trainer_sprite, trainer_scene):
    """Start an enemy trainer battle with a tougher Pokemon"""
    global name, id, level, hp, max_hp, ability, type, enemy_attacks, attacks, base_experience, stats, battlescene_file, ev, iv, gender, battle_status, battle_stats
    global test_window, pkmn_window, pokemon_encounter
    global current_trainer_name, current_trainer_sprite, is_trainer_battle

    # Set trainer battle flag and info
    is_trainer_battle = True
    current_trainer_name = trainer_name
    current_trainer_sprite = trainer_sprite

    # Reset encounter counter to show trainer intro message
    pokemon_encounter = 0

    # Generate tough enemy trainer Pokemon
    name, id, level, ability, type, stats, enemy_attacks, base_experience, growth_rate, hp, max_hp, ev, iv, gender, battle_status, battle_stats = generate_enemy_trainer_pokemon()

    # Use the trainer's designated battle scene
    battlescene_file = trainer_scene

    # Recalculate max HP
    max_hp = calculate_hp(stats["hp"], level, ev, iv)

    # Display the battle
    if test_window is not None and pkmn_window is True:
        test_window.display_first_encounter()
        tooltipWithColour(f"{trainer_name} sent out {name.capitalize()} (Level {level})!", "#FF4444")

    # Update life bar
    class Container(object):
        pass
    reviewer = Container()
    reviewer.web = mw.reviewer.web
    update_life_bar(reviewer, 0, 0)

def _ankimon_validate_enemy_id(enemy_id, enemy_name="unknown"):
    """
    Validate enemy ID is valid before using for sprite paths or other operations.
    Returns (is_valid, safe_id, warning_message)
    """
    try:
        # Check if enemy_id is valid type
        if enemy_id is None:
            return (False, 25, f"Enemy ID is None (name={enemy_name})")

        # Check if it's a list/tuple (common error case)
        if isinstance(enemy_id, (list, tuple)):
            return (False, 25, f"Enemy ID is list/tuple: {enemy_id} (name={enemy_name})")

        # Try to convert to int
        try:
            id_int = int(enemy_id)
        except (ValueError, TypeError):
            return (False, 25, f"Enemy ID cannot convert to int: {enemy_id} (name={enemy_name})")

        # Check if in valid range [1..1025]
        if id_int < 1 or id_int > 1025:
            return (False, 25, f"Enemy ID out of range: {id_int} (name={enemy_name})")

        return (True, id_int, None)
    except Exception as e:
        return (False, 25, f"Exception validating enemy ID: {e}")

def _ankimon_spawn_special_battle_pokemon():
    """
    Spawn Pokemon for special battles (gym/elite4/champion) - bypasses battle lock.
    This is used during transitions to ensure the first opponent spawns correctly.
    """
    global name, id, level, hp, max_hp, ability, type, enemy_attacks, attacks, base_experience, stats, battlescene_file, ev, iv, gender, battle_status
    global is_trainer_battle, current_trainer_name, current_trainer_sprite, test_window

    try:
        battle_state = _ankimon_get_battle_state()
        _ankimon_log("INFO", "AnkimonBattle", f"Spawning special battle Pokemon (state={battle_state})")

        # Reset trainer battle flags
        is_trainer_battle = False
        current_trainer_name = None
        current_trainer_sprite = None
        gender = None

        # Generate Pokemon (will use gym/elite4/champion roster based on battle_state)
        name, id, level, ability, type, stats, enemy_attacks, base_experience, growth_rate, hp, max_hp, ev, iv, gender, battle_status, battle_stats = generate_random_pokemon()

        # Select battle scene
        primary_type = type[0] if isinstance(type, list) and len(type) > 0 else None
        battlescene_file = random_battle_scene(primary_type)
        max_hp = calculate_hp(stats["hp"], level, ev, iv)

        _ankimon_log("INFO", "AnkimonBattle", f"Special battle Pokemon spawned: id={id}, name={name}, hp={hp}/{max_hp}, level={level}")

        # Clear stale sprites
        _ankimon_clear_stale_enemy_sprites()

        # Display in external window if enabled
        if test_window is not None and hasattr(test_window, 'display_first_encounter'):
            test_window.display_first_encounter()

        return True
    except Exception as e:
        _ankimon_log("ERROR", "AnkimonBattle", f"Error spawning special battle Pokemon: {e}")
        import traceback
        traceback.print_exc()
        return False

def new_pokemon():
    global name, id, level, hp, max_hp, ability, type, enemy_attacks, attacks, base_experience, stats, battlescene_file, ev, iv, gender, battle_status
    global is_trainer_battle, current_trainer_name, current_trainer_sprite, current_wild_variant

    # BATTLE LOCK: Check if important battle is in progress
    if _ankimon_is_battle_locked():
        _ankimon_log("WARN", "AnkimonBattle", "Suppressed wild encounter - important battle in progress")
        return

    # Set battle state for wild encounter
    if not _ankimon_is_gym_active() and not _ankimon_is_elite_four_active() and not _ankimon_is_champion_active():
        _ankimon_set_battle_state("wild")

    # new pokemon - reset trainer battle flag and variant
    is_trainer_battle = False
    current_trainer_name = None
    current_trainer_sprite = None
    gender = None
    current_wild_variant = None  # Reset variant for new encounters

    # Check for legendary battles (priority order: Primal Groudon > Primal Kyogre > Mega Rayquaza)
    try:
        if _check_legendary_available('mega_rayquaza'):
            _trigger_legendary_battle('mega_rayquaza')
            return
        elif _check_legendary_available('primal_kyogre'):
            _trigger_legendary_battle('primal_kyogre')
            return
        elif _check_legendary_available('primal_groudon'):
            _trigger_legendary_battle('primal_groudon')
            return
    except Exception as e:
        print(f"Error checking legendary availability: {e}")
        pass  # Continue with normal Pokemon if legendary check fails

    name, id, level, ability, type, stats, enemy_attacks, base_experience, growth_rate, hp, max_hp, ev, iv, gender, battle_status, battle_stats = generate_random_pokemon()
    # Select battle scene based on Pokemon's primary type
    primary_type = type[0] if isinstance(type, list) and len(type) > 0 else None
    battlescene_file = random_battle_scene(primary_type)
    max_hp = calculate_hp(stats["hp"], level, ev, iv)

    # Log the enemy that was generated
    battle_state = _ankimon_get_battle_state()
    _ankimon_log("INFO", "AnkimonBattle", f"Generated pokemon: id={id}, name={name}, hp={hp}/{max_hp}, level={level}, battle_state={battle_state}")

    # CRITICAL: Clear stale sprites and force complete UI refresh
    # This ensures old pokemon don't persist when gym/elite4/champion pokemon spawn
    _ankimon_clear_stale_enemy_sprites()

    #reset mainpokemon hp
    if test_window is not None:
        # Force complete refresh of enemy display
        _ankimon_force_refresh_enemy_display()

        # Extra reinforcement for gym battles
        if _ankimon_is_gym_active() and pkmn_window is True:
            from aqt.qt import QTimer
            # Additional delayed refresh to ensure gym pokemon displays
            def _delayed_gym_refresh():
                try:
                    conf = _ankimon_get_col_conf()
                    if conf:
                        gym_idx = int(conf.get("ankimon_gym_enemy_index", 0))
                        enemy_ids = conf.get("ankimon_gym_enemy_ids") or []
                        expected_id = enemy_ids[gym_idx] if gym_idx < len(enemy_ids) else "unknown"
                        _ankimon_log("INFO", "AnkimonBattle", f"Delayed gym refresh - expected_id={expected_id}, current_displayed_id={id}")
                    _ankimon_force_refresh_enemy_display()
                except Exception as e:
                    _ankimon_log("ERROR", "AnkimonBattle", f"Error in delayed gym refresh: {e}")
            QTimer.singleShot(100, _delayed_gym_refresh)
    class Container(object):
        pass
    reviewer = Container()
    reviewer.web = mw.reviewer.web
    update_life_bar(reviewer, 0, 0)

def spawn_next_gym_pokemon():
    """Handler for Next Pokemon button - spawns the next gym pokemon"""
    global test_window, pkmn_window
    try:
        _ankimon_log("INFO", "AnkimonBattle", "=== spawn_next_gym_pokemon() called ===")

        # Set battle state to gym
        _ankimon_set_battle_state("gym")

        # Defensive: Force-close any lingering post-battle UI
        _ankimon_close_post_battle_ui("failsafe - gym pokemon spawn")

        conf = _ankimon_get_col_conf()
        if not conf:
            _ankimon_log("ERROR", "AnkimonBattle", "Config not available in spawn_next_gym_pokemon")
            tooltipWithColour("Config not available", "#FF0000")
            return

        # Get current gym state
        gym_active = conf.get("ankimon_gym_active", False)
        enemy_ids = conf.get("ankimon_gym_enemy_ids") or []
        current_idx = int(conf.get("ankimon_gym_enemy_index") or 0)
        leader_name = conf.get("ankimon_gym_leader_name", "Unknown")
        next_idx = current_idx + 1

        _ankimon_log("INFO", "AnkimonBattle", f"Gym state: active={gym_active}, current_idx={current_idx}, next_idx={next_idx}, total={len(enemy_ids)}, leader={leader_name}")

        if not gym_active:
            _ankimon_log("WARN", "AnkimonBattle", "spawn_next_gym_pokemon called but gym not active - aborting")
            return

        if not enemy_ids:
            _ankimon_log("ERROR", "AnkimonBattle", "spawn_next_gym_pokemon called but no enemy_ids - corrupted state")
            tooltipWithColour("Gym state corrupted - use Reset Battle", "#FF0000")
            return

        if next_idx < len(enemy_ids):
            _ankimon_log("INFO", "AnkimonBattle", f"Spawning next gym pokemon: index {next_idx}/{len(enemy_ids)}, ID={enemy_ids[next_idx] if next_idx < len(enemy_ids) else 'N/A'}")

            # Show tooltip BEFORE incrementing index
            try:
                tooltipWithColour(f"Leader sends out next Pokémon! ({next_idx+1}/{len(enemy_ids)})", "#00FF00")
            except:
                pass

            # Increment index BEFORE spawning (needed for generate_random_pokemon to use correct ID)
            conf["ankimon_gym_enemy_index"] = next_idx
            mw.col.setMod()
            _ankimon_log("INFO", "AnkimonBattle", f"Updated gym_enemy_index to {next_idx}")

            # Try to spawn next pokemon
            try:
                # Clear any stale UI before spawning
                _ankimon_clear_stale_enemy_sprites()

                # CRITICAL: Use special battle spawn to bypass battle lock
                _ankimon_log("INFO", "AnkimonBattle", "Spawning next gym Pokemon (bypassing lock)...")
                if not _ankimon_spawn_special_battle_pokemon():
                    raise Exception("Failed to spawn gym Pokemon")
                _ankimon_log("INFO", "AnkimonBattle", "Gym Pokemon spawn completed successfully")

                # Verify the correct gym pokemon is now loaded
                conf_verify = _ankimon_get_col_conf()
                if conf_verify:
                    current_gym_idx = int(conf_verify.get("ankimon_gym_enemy_index", 0))
                    enemy_ids_verify = conf_verify.get("ankimon_gym_enemy_ids") or []
                    expected_id = enemy_ids_verify[current_gym_idx] if current_gym_idx < len(enemy_ids_verify) else "unknown"
                    _ankimon_log("INFO", "AnkimonBattle", f"Post-spawn verification - gym_idx={current_gym_idx}, expected_id={expected_id}, displayed_id={id}")

                # Force window update with multiple retries to ensure refresh
                if test_window is not None and pkmn_window is True:
                    from aqt.qt import QTimer
                    def _update_window():
                        try:
                            _ankimon_log("INFO", "AnkimonUI", "Updating gym battle window display")
                            _ankimon_force_refresh_enemy_display()
                            _ankimon_log("INFO", "AnkimonUI", "Window update completed")
                        except Exception as e:
                            _ankimon_log("ERROR", "AnkimonUI", f"Window update error: {e}")
                            tooltipWithColour(f"Window update error: {str(e)}", "#FF0000")
                    # Call immediately and again after short delays to ensure update
                    _update_window()
                    QTimer.singleShot(100, _update_window)
                    QTimer.singleShot(250, _update_window)

                    # Central refresh after gym progression (Requirement G)
                    QTimer.singleShot(300, _ankimon_refresh_all_views)
                    _ankimon_log("INFO", "AnkimonBattle", "Scheduled central refresh after gym pokemon spawn")
                else:
                    _ankimon_log("WARN", "AnkimonBattle", f"Cannot update window: test_window={test_window is not None}, pkmn_window={pkmn_window}")
            except Exception as e:
                # CRITICAL: If spawning fails, rollback the index to prevent state corruption
                conf["ankimon_gym_enemy_index"] = current_idx
                mw.col.setMod()

                error_msg = f"Error spawning next gym pokemon: {str(e)}"
                _ankimon_log("ERROR", "AnkimonBattle", error_msg)
                tooltipWithColour(error_msg, "#FF0000")
                import traceback
                traceback.print_exc()

                # Show user-friendly message
                try:
                    showWarning(f"Failed to spawn next gym pokemon.\nUse Reset Battle from Ankimon menu to fix.\n\nError: {str(e)[:100]}")
                except:
                    pass
        else:
            # All pokemon defeated - complete the gym
            _ankimon_log("INFO", "AnkimonBattle", "All gym pokemon defeated, completing gym battle")
            complete_gym_battle()
    except Exception as e:
        error_msg = f"Error in spawn_next_gym_pokemon: {str(e)}"
        _ankimon_log("ERROR", "AnkimonBattle", error_msg)
        tooltipWithColour(error_msg, "#FF0000")
        import traceback
        traceback.print_exc()

def spawn_next_elite_four_pokemon():
    """Handler for Next Pokemon button in Elite Four battles - spawns the next Elite Four pokemon"""
    global test_window, pkmn_window
    try:
        _ankimon_log("INFO", "AnkimonBattle", "=== spawn_next_elite_four_pokemon() called ===")

        # Set battle state to elite4
        _ankimon_set_battle_state("elite4")

        # Defensive: Force-close any lingering post-battle UI
        _ankimon_close_post_battle_ui("failsafe - elite four pokemon spawn")

        conf = _ankimon_get_col_conf()
        if not conf:
            _ankimon_log("ERROR", "AnkimonBattle", "Config not available in spawn_next_elite_four_pokemon")
            tooltipWithColour("Config not available", "#FF0000")
            return

        # Get current Elite Four state
        elite_four_active = conf.get("ankimon_elite_four_active", False)
        enemy_ids = conf.get("ankimon_elite_four_enemy_ids") or []
        current_idx = int(conf.get("ankimon_elite_four_pokemon_index") or 0)
        member_name = conf.get("ankimon_elite_four_member_name", "Unknown")
        next_idx = current_idx + 1

        _ankimon_log("INFO", "AnkimonBattle", f"Elite Four state: active={elite_four_active}, current_idx={current_idx}, next_idx={next_idx}, total={len(enemy_ids)}, member={member_name}")

        if not elite_four_active:
            _ankimon_log("WARN", "AnkimonBattle", "spawn_next_elite_four_pokemon called but Elite Four not active - aborting")
            return

        if not enemy_ids:
            _ankimon_log("ERROR", "AnkimonBattle", "spawn_next_elite_four_pokemon called but no enemy_ids - corrupted state")
            tooltipWithColour("Elite Four state corrupted - use Reset Battle", "#FF0000")
            return

        if next_idx < len(enemy_ids):
            _ankimon_log("INFO", "AnkimonBattle", f"Spawning next Elite Four pokemon: index {next_idx}/{len(enemy_ids)}, ID={enemy_ids[next_idx] if next_idx < len(enemy_ids) else 'N/A'}")

            # Show tooltip BEFORE incrementing index
            try:
                tooltipWithColour(f"{member_name} sends out next Pokémon! ({next_idx+1}/{len(enemy_ids)})", "#00FF00")
            except:
                pass

            # Increment index BEFORE spawning (needed for generate_random_pokemon to use correct ID)
            conf["ankimon_elite_four_pokemon_index"] = next_idx
            mw.col.setMod()
            _ankimon_log("INFO", "AnkimonBattle", f"Updated elite_four_pokemon_index to {next_idx}")

            # Try to spawn next pokemon
            try:
                # Clear any stale UI before spawning
                _ankimon_clear_stale_enemy_sprites()

                # CRITICAL: Use special battle spawn to bypass battle lock
                _ankimon_log("INFO", "AnkimonBattle", "Spawning next Elite Four Pokemon (bypassing lock)...")
                if not _ankimon_spawn_special_battle_pokemon():
                    raise Exception("Failed to spawn Elite Four Pokemon")
                _ankimon_log("INFO", "AnkimonBattle", "Elite Four Pokemon spawn completed successfully")

                # Verify the correct Elite Four pokemon is now loaded
                conf_verify = _ankimon_get_col_conf()
                if conf_verify:
                    current_e4_idx = int(conf_verify.get("ankimon_elite_four_pokemon_index", 0))
                    enemy_ids_verify = conf_verify.get("ankimon_elite_four_enemy_ids") or []
                    expected_id = enemy_ids_verify[current_e4_idx] if current_e4_idx < len(enemy_ids_verify) else "unknown"
                    _ankimon_log("INFO", "AnkimonBattle", f"Post-spawn verification - elite_four_pokemon_index={current_e4_idx}, expected_id={expected_id}, displayed_id={id}")

                # Force window update with multiple retries to ensure refresh
                if test_window is not None and pkmn_window is True:
                    from aqt.qt import QTimer
                    def _update_window():
                        try:
                            _ankimon_log("INFO", "AnkimonUI", "Updating Elite Four battle window display")
                            _ankimon_force_refresh_enemy_display()
                            _ankimon_log("INFO", "AnkimonUI", "Window update completed")
                        except Exception as e:
                            _ankimon_log("ERROR", "AnkimonUI", f"Window update error: {e}")
                            tooltipWithColour(f"Window update error: {str(e)}", "#FF0000")
                    # Call immediately and again after short delays to ensure update
                    _update_window()
                    QTimer.singleShot(100, _update_window)
                    QTimer.singleShot(250, _update_window)

                    # Central refresh after Elite Four progression
                    QTimer.singleShot(300, _ankimon_refresh_all_views)
                    _ankimon_log("INFO", "AnkimonBattle", "Scheduled central refresh after Elite Four pokemon spawn")
                else:
                    _ankimon_log("WARN", "AnkimonBattle", f"Cannot update window: test_window={test_window is not None}, pkmn_window={pkmn_window}")
            except Exception as e:
                # CRITICAL: If spawning fails, rollback the index to prevent state corruption
                conf["ankimon_elite_four_pokemon_index"] = current_idx
                mw.col.setMod()

                error_msg = f"Error spawning next Elite Four pokemon: {str(e)}"
                _ankimon_log("ERROR", "AnkimonBattle", error_msg)
                tooltipWithColour(error_msg, "#FF0000")
                import traceback
                traceback.print_exc()

                # Show user-friendly message
                try:
                    showWarning(f"Failed to spawn next Elite Four pokemon.\nUse Reset Battle from Ankimon menu to fix.\n\nError: {str(e)[:100]}")
                except:
                    pass
        else:
            # All pokemon defeated - complete this Elite Four member
            _ankimon_log("INFO", "AnkimonBattle", "All Elite Four pokemon defeated, completing Elite Four member")
            complete_elite_four_member()
    except Exception as e:
        error_msg = f"Error in spawn_next_elite_four_pokemon: {str(e)}"
        _ankimon_log("ERROR", "AnkimonBattle", error_msg)
        tooltipWithColour(error_msg, "#FF0000")
        import traceback
        traceback.print_exc()

def complete_gym_battle():
    """Handler for completing gym battle - awards badge and spawns wild pokemon"""
    global test_window, pkmn_window, achievements
    try:
        _ankimon_log("INFO", "AnkimonBattle", "=== complete_gym_battle() called ===")

        conf = _ankimon_get_col_conf()
        if not conf:
            _ankimon_log("ERROR", "AnkimonBattle", "Config not available in complete_gym_battle")
            tooltipWithColour("Config not available", "#FF0000")
            return

        # Get current gym index before clearing
        current_gym_idx = int(conf.get("ankimon_gym_index", 0))
        gym_number = (current_gym_idx % 8) + 1
        leader_name = conf.get("ankimon_gym_leader_name", "Unknown")
        _ankimon_log("INFO", "AnkimonBattle", f"Completing gym {gym_number} vs {leader_name} (index={current_gym_idx})")

        # Clear gym state FIRST
        conf["ankimon_gym_active"] = False
        conf["ankimon_gym_enemy_ids"] = []
        conf["ankimon_gym_enemy_index"] = 0
        _ankimon_log("INFO", "AnkimonBattle", "Cleared gym state flags")

        # Reset battle state to idle
        _ankimon_set_battle_state("idle")
        conf["ankimon_gym_current_enemy_id"] = None
        conf["ankimon_gym_last_cleared_leader"] = conf.get("ankimon_gym_leader_key")
        conf["ankimon_gym_leader_key"] = None
        conf["ankimon_gym_leader_name"] = None

        # Increment gym index for next gym
        conf["ankimon_gym_index"] = current_gym_idx + 1

        # Reset card counter for next gym
        conf["ankimon_gym_counter"] = 0

        # Save config immediately
        mw.col.setMod()
        _ankimon_log("INFO", "AnkimonBattle", f"Gym index incremented to {current_gym_idx + 1}, counter reset to 0")

        # Track gym battle completion in progression stats
        try:
            stats_data = _load_progression_stats()
            stats_data["lifetime"]["total_gym_battles"] += 1
            stats_data["current_round"]["gyms_defeated"] += 1
            _save_progression_stats(stats_data)
        except Exception:
            pass  # Don't break gameplay if stats tracking fails

        # Award gym badge (badges 25-32 for gyms 0-7)
        badge_num = 25 + (current_gym_idx % 8)
        try:
            check = check_for_badge(achievements, badge_num)
            if not check:
                receive_badge(badge_num, achievements)
                if test_window is not None:
                    test_window.display_badge(badge_num)
                # Track badge earned
                try:
                    stats_data = _load_progression_stats()
                    stats_data["lifetime"]["total_badges_earned"] += 1
                    _save_progression_stats(stats_data)
                except Exception:
                    pass
        except Exception:
            pass

        # Award Mega Stone for defeating gym (10% drop chance)
        try:
            _award_random_mega_stone("gym")
        except Exception as e:
            print(f"Error awarding Mega Stone for gym: {e}")

        # Show completion message
        try:
            # Check if all 8 badges are earned (after gym 8)
            if _ankimon_all_gym_badges_earned():
                completion_msg = f"Gym {gym_number} battle complete!\n\n🏆 All 8 badges earned! Moving on to Elite Four.\n\nDefeat 150 Pokemon to challenge the first Elite Four member!"
            else:
                completion_msg = f"Gym {gym_number} battle complete! Collect 100 more cards for the next gym."
            tooltipWithColour(completion_msg, "#FFD700")
        except:
            pass

        # Spawn new wild pokemon
        try:
            _ankimon_log("INFO", "AnkimonBattle", "Spawning new wild pokemon after gym completion")
            new_pokemon()
            # Force window update with small delay to ensure refresh
            if test_window is not None and pkmn_window is True:
                from aqt.qt import QTimer
                def _update_window():
                    try:
                        test_window.display_first_encounter()
                        test_window.show()
                        test_window.raise_()
                        test_window.activateWindow()
                        test_window.update()  # Force Qt to redraw
                        test_window.repaint()  # Force immediate repaint
                    except Exception as e:
                        tooltipWithColour(f"Window update error: {str(e)}", "#FF0000")
                # Call immediately and again after short delay to ensure update
                _update_window()
                QTimer.singleShot(100, _update_window)

                # Central refresh after gym completion (Requirement G)
                QTimer.singleShot(200, _ankimon_refresh_all_views)
                _ankimon_log("INFO", "AnkimonBattle", "Scheduled central refresh after gym completion")
        except Exception as e:
            error_msg = f"Error spawning pokemon after gym: {str(e)}"
            tooltipWithColour(error_msg, "#FF0000")
            import traceback
            traceback.print_exc()
    except Exception as e:
        error_msg = f"Error in complete_gym_battle: {str(e)}"
        tooltipWithColour(error_msg, "#FF0000")
        import traceback
        traceback.print_exc()

def complete_elite_four_member():
    """Handler for completing one Elite Four member - advances to next member or completes Elite Four"""
    global test_window, pkmn_window
    try:
        conf = _ankimon_get_col_conf()
        if not conf:
            tooltipWithColour("Config not available", "#FF0000")
            return

        # Get current member info
        member_index = int(conf.get("ankimon_elite_four_index", 0))
        member_name = conf.get("ankimon_elite_four_member_name", "Elite Four")

        # Clear Elite Four state
        conf["ankimon_elite_four_active"] = False
        conf["ankimon_elite_four_enemy_ids"] = []
        conf["ankimon_elite_four_pokemon_index"] = 0

        # Reset battle state to idle
        _ankimon_set_battle_state("idle")

        # Increment member index
        conf["ankimon_elite_four_index"] = member_index + 1

        # Reset card counter for next member
        conf["ankimon_elite_four_counter"] = 0

        mw.col.setMod()

        # Track Elite Four member completion
        try:
            stats_data = _load_progression_stats()
            stats_data["lifetime"]["total_elite_four_battles"] += 1
            current_defeated = stats_data["current_round"].get("elite_four_defeated", 0)
            stats_data["current_round"]["elite_four_defeated"] = current_defeated + 1
            _save_progression_stats(stats_data)
        except Exception:
            pass

        # Award Mega Stone for defeating Elite Four member (25% drop chance)
        try:
            _award_random_mega_stone("elite4")
        except Exception as e:
            print(f"Error awarding Mega Stone for Elite Four: {e}")

        # Show completion message
        try:
            if (member_index + 1) >= 4:
                tooltipWithColour(f"Elite Four {member_name} defeated! All Elite Four members conquered!", "#FFD700")
            else:
                tooltipWithColour(f"Elite Four {member_name} defeated! Collect 150 more cards for the next member.", "#FFD700")
        except:
            pass

        # Spawn new wild pokemon
        try:
            new_pokemon()
            if test_window is not None and pkmn_window is True:
                from aqt.qt import QTimer
                def _update_window():
                    try:
                        test_window.display_first_encounter()
                        test_window.show()
                        test_window.raise_()
                        test_window.activateWindow()
                        test_window.update()
                        test_window.repaint()
                    except Exception as e:
                        tooltipWithColour(f"Window update error: {str(e)}", "#FF0000")
                _update_window()
                QTimer.singleShot(100, _update_window)
        except Exception as e:
            error_msg = f"Error spawning pokemon after Elite Four: {str(e)}"
            tooltipWithColour(error_msg, "#FF0000")
            import traceback
            traceback.print_exc()
    except Exception as e:
        error_msg = f"Error in complete_elite_four_member: {str(e)}"
        tooltipWithColour(error_msg, "#FF0000")
        import traceback
        traceback.print_exc()

def spawn_next_champion_pokemon():
    """Handler for Next Pokemon button in Champion battles - spawns the next Champion pokemon"""
    global test_window, pkmn_window
    try:
        _ankimon_log("INFO", "AnkimonBattle", "=== spawn_next_champion_pokemon() called ===")

        # Set battle state to champion
        _ankimon_set_battle_state("champion")

        # Defensive: Force-close any lingering post-battle UI
        _ankimon_close_post_battle_ui("failsafe - champion pokemon spawn")

        conf = _ankimon_get_col_conf()
        if not conf:
            _ankimon_log("ERROR", "AnkimonBattle", "Config not available in spawn_next_champion_pokemon")
            tooltipWithColour("Config not available", "#FF0000")
            return

        # Get current Champion state
        champion_active = conf.get("ankimon_champion_active", False)
        enemy_ids = conf.get("ankimon_champion_enemy_ids") or []
        current_idx = int(conf.get("ankimon_champion_pokemon_index") or 0)
        next_idx = current_idx + 1

        _ankimon_log("INFO", "AnkimonBattle", f"Champion state: active={champion_active}, current_idx={current_idx}, next_idx={next_idx}, total={len(enemy_ids)}")

        if not champion_active:
            _ankimon_log("WARN", "AnkimonBattle", "spawn_next_champion_pokemon called but Champion not active - aborting")
            return

        if not enemy_ids:
            _ankimon_log("ERROR", "AnkimonBattle", "spawn_next_champion_pokemon called but no enemy_ids - corrupted state")
            tooltipWithColour("Champion state corrupted - use Reset Battle", "#FF0000")
            return

        if next_idx < len(enemy_ids):
            _ankimon_log("INFO", "AnkimonBattle", f"Spawning next Champion pokemon: index {next_idx}/{len(enemy_ids)}, ID={enemy_ids[next_idx] if next_idx < len(enemy_ids) else 'N/A'}")

            # Show tooltip BEFORE incrementing index
            try:
                tooltipWithColour(f"Champion Cynthia sends out next Pokémon! ({next_idx+1}/{len(enemy_ids)})", "#00FF00")
            except:
                pass

            # Increment index BEFORE spawning (needed for generate_random_pokemon to use correct ID)
            conf["ankimon_champion_pokemon_index"] = next_idx
            mw.col.setMod()
            _ankimon_log("INFO", "AnkimonBattle", f"Updated champion_pokemon_index to {next_idx}")

            # Try to spawn next pokemon
            try:
                # Clear any stale UI before spawning
                _ankimon_clear_stale_enemy_sprites()

                # CRITICAL: Use special battle spawn to bypass battle lock
                _ankimon_log("INFO", "AnkimonBattle", "Spawning next Champion Pokemon (bypassing lock)...")
                if not _ankimon_spawn_special_battle_pokemon():
                    raise Exception("Failed to spawn Champion Pokemon")
                _ankimon_log("INFO", "AnkimonBattle", "Champion Pokemon spawn completed successfully")

                # Verify the correct Champion pokemon is now loaded
                conf_verify = _ankimon_get_col_conf()
                if conf_verify:
                    current_champ_idx = int(conf_verify.get("ankimon_champion_pokemon_index", 0))
                    enemy_ids_verify = conf_verify.get("ankimon_champion_enemy_ids") or []
                    expected_id = enemy_ids_verify[current_champ_idx] if current_champ_idx < len(enemy_ids_verify) else "unknown"
                    _ankimon_log("INFO", "AnkimonBattle", f"Post-spawn verification - champion_pokemon_index={current_champ_idx}, expected_id={expected_id}, displayed_id={id}")

                # Force window update with multiple retries to ensure refresh
                if test_window is not None and pkmn_window is True:
                    from aqt.qt import QTimer
                    def _update_window():
                        try:
                            _ankimon_log("INFO", "AnkimonUI", "Updating Champion battle window display")
                            _ankimon_force_refresh_enemy_display()
                            _ankimon_log("INFO", "AnkimonUI", "Window update completed")
                        except Exception as e:
                            _ankimon_log("ERROR", "AnkimonUI", f"Window update error: {e}")
                            tooltipWithColour(f"Window update error: {str(e)}", "#FF0000")
                    # Call immediately and again after short delays to ensure update
                    _update_window()
                    QTimer.singleShot(100, _update_window)
                    QTimer.singleShot(250, _update_window)

                    # Central refresh after Champion progression
                    QTimer.singleShot(300, _ankimon_refresh_all_views)
                    _ankimon_log("INFO", "AnkimonBattle", "Scheduled central refresh after Champion pokemon spawn")
                else:
                    _ankimon_log("WARN", "AnkimonBattle", f"Cannot update window: test_window={test_window is not None}, pkmn_window={pkmn_window}")
            except Exception as e:
                # CRITICAL: If spawning fails, rollback the index to prevent state corruption
                conf["ankimon_champion_pokemon_index"] = current_idx
                mw.col.setMod()

                error_msg = f"Error spawning next Champion pokemon: {str(e)}"
                _ankimon_log("ERROR", "AnkimonBattle", error_msg)
                tooltipWithColour(error_msg, "#FF0000")
                import traceback
                traceback.print_exc()

                # Show user-friendly message
                try:
                    showWarning(f"Failed to spawn next Champion pokemon.\nUse Reset Battle from Ankimon menu to fix.\n\nError: {str(e)[:100]}")
                except:
                    pass
        else:
            # All pokemon defeated - complete Champion battle
            _ankimon_log("INFO", "AnkimonBattle", "All Champion pokemon defeated, completing Champion battle")
            complete_champion_battle()
    except Exception as e:
        error_msg = f"Error in spawn_next_champion_pokemon: {str(e)}"
        _ankimon_log("ERROR", "AnkimonBattle", error_msg)
        tooltipWithColour(error_msg, "#FF0000")
        import traceback
        traceback.print_exc()

def complete_champion_battle():
    """Handler for completing Champion battle - unlocks Key Stone, triggers round progression"""
    global test_window, pkmn_window
    try:
        conf = _ankimon_get_col_conf()
        if not conf:
            tooltipWithColour("Config not available", "#FF0000")
            return

        # Clear Champion state
        conf["ankimon_champion_active"] = False
        conf["ankimon_champion_enemy_ids"] = []
        conf["ankimon_champion_pokemon_index"] = 0
        conf["ankimon_champion_counter"] = 0

        # Reset battle state to idle
        _ankimon_set_battle_state("idle")

        mw.col.setMod()

        # Track Champion battle completion and check if first time BEFORE incrementing
        try:
            stats_data = _load_progression_stats()

            # Check if first time defeating Champion (before incrementing)
            is_first_time = stats_data["lifetime"]["total_champion_battles"] == 0

            # Now increment the count
            stats_data["lifetime"]["total_champion_battles"] += 1
            stats_data["current_round"]["champion_defeated"] = True

            _save_progression_stats(stats_data)
        except Exception as e:
            print(f"Error tracking champion stats: {e}")
            is_first_time = False

        # Award Key Stone on first completion
        if is_first_time:
            try:
                mega_state = _load_mega_state()
                mega_state["key_stone_unlocked"] = True
                _save_mega_state(mega_state)

                # Add Key Stone to items bag (only if not already present)
                try:
                    with open(itembag_path, 'r') as json_file:
                        itembag_list = json.load(json_file)
                except (FileNotFoundError, json.JSONDecodeError):
                    itembag_list = []

                if "key_stone" not in itembag_list:
                    itembag_list.append("key_stone")
                    with open(itembag_path, 'w') as json_file:
                        json.dump(itembag_list, json_file)

                # Display Key Stone item popup
                try:
                    if test_window is not None:
                        test_window.rate_display_item("key_stone")
                except Exception as e:
                    print(f"Error displaying Key Stone: {e}")

                tooltipWithColour("You obtained the Key Stone! Mega Evolution is now unlocked!", "#FF00FF")
            except Exception as e:
                print(f"Error unlocking Key Stone: {e}")

        # Award Mega Stone for defeating Champion (100% drop chance, guaranteed)
        try:
            _award_random_mega_stone("champion")
        except Exception as e:
            print(f"Error awarding Mega Stone for Champion: {e}")

        # Show completion message
        try:
            tooltipWithColour("Champion Cynthia defeated! You are the new Champion!", "#FFD700")
        except:
            pass

        # Trigger round progression (will be implemented next)
        try:
            _trigger_round_progression()
        except Exception as e:
            print(f"Error triggering round progression: {e}")

        # Spawn new wild pokemon
        try:
            new_pokemon()
            if test_window is not None and pkmn_window is True:
                from aqt.qt import QTimer
                def _update_window():
                    try:
                        test_window.display_first_encounter()
                        test_window.show()
                        test_window.raise_()
                        test_window.activateWindow()
                        test_window.update()
                        test_window.repaint()
                    except Exception as e:
                        tooltipWithColour(f"Window update error: {str(e)}", "#FF0000")
                _update_window()
                QTimer.singleShot(100, _update_window)
        except Exception as e:
            error_msg = f"Error spawning pokemon after Champion: {str(e)}"
            tooltipWithColour(error_msg, "#FF0000")
            import traceback
            traceback.print_exc()
    except Exception as e:
        error_msg = f"Error in complete_champion_battle: {str(e)}"
        tooltipWithColour(error_msg, "#FF0000")
        import traceback
        traceback.print_exc()

def _trigger_round_progression():
    """Trigger new round progression - reset badges, increment round, scale difficulty"""
    try:
        stats_data = _load_progression_stats()
        current_round = stats_data["lifetime"]["current_round"]
        new_round = current_round + 1

        # Update round number
        stats_data["lifetime"]["current_round"] = new_round
        stats_data["current_round"]["round_number"] = new_round

        # Reset current round progress
        stats_data["current_round"]["cards_reviewed"] = 0
        stats_data["current_round"]["battles_won"] = 0
        stats_data["current_round"]["gyms_defeated"] = 0
        stats_data["current_round"]["elite_four_defeated"] = 0
        stats_data["current_round"]["champion_defeated"] = False
        stats_data["current_round"]["pokemon_caught"] = 0
        stats_data["current_round"]["items_obtained"] = 0
        stats_data["current_round"]["mega_evolutions_used"] = 0

        _save_progression_stats(stats_data)

        # Remove all gym badges from inventory
        try:
            global achievements
            # Refresh achievements from file
            achievements = check_badges(achievements)

            # Remove gym badges (IDs 25-32)
            for badge_id in range(25, 33):
                achievements[str(badge_id)] = False

            # Rebuild and save badge collection
            badges_collection = []
            for num in range(1, 69):
                if achievements[str(num)] is True:
                    badges_collection.append(int(num))
            save_badges(badges_collection)
        except Exception as e:
            print(f"Error removing badges: {e}")

        # Reset gym/Elite Four/Champion counters and states
        try:
            conf = _ankimon_get_col_conf()
            if conf:
                # Reset counters
                conf["ankimon_gym_index"] = 0
                conf["ankimon_gym_counter"] = 0
                conf["ankimon_elite_four_index"] = 0
                conf["ankimon_elite_four_counter"] = 0
                conf["ankimon_champion_counter"] = 0

                # Clear any pending or active battle flags
                conf["ankimon_gym_active"] = False
                conf["ankimon_gym_pending"] = False
                conf["ankimon_elite_four_active"] = False
                conf["ankimon_elite_four_pending"] = False
                conf["ankimon_champion_active"] = False
                conf["ankimon_champion_pending"] = False

                # Clear battle state variables
                conf["ankimon_gym_enemy_ids"] = []
                conf["ankimon_gym_enemy_index"] = 0
                conf["ankimon_elite_four_enemy_ids"] = []
                conf["ankimon_elite_four_pokemon_index"] = 0
                conf["ankimon_champion_enemy_ids"] = []
                conf["ankimon_champion_pokemon_index"] = 0

                mw.col.setMod()
        except Exception as e:
            print(f"Error resetting counters: {e}")

        # Show round progression message
        tooltipWithColour(f"Round {new_round} begins! Gyms will be stronger now!", "#00FFFF")

    except Exception as e:
        print(f"Error in round progression: {e}")
        import traceback
        traceback.print_exc()

def reset_battle():
    """Reset current battle and spawn a new wild pokemon. Fixes fainted pokemon display issues."""
    try:
        global test_window, pkmn_window, hp

        conf = _ankimon_get_col_conf()
        if conf is None:
            showInfo("Cannot reset battle - collection config not available.")
            return

        # Check if gym battle is active
        is_gym_active = conf.get("ankimon_gym_active", False)
        is_gym_pending = conf.get("ankimon_gym_pending", False)

        if is_gym_active or is_gym_pending:
            # Ask user if they want to reset gym battle
            reply = QMessageBox.question(
                mw,
                "Reset Gym Battle?",
                "You are currently in a gym battle. Resetting will end the gym battle.\n\nDo you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                return

            # Reset gym state
            conf["ankimon_gym_active"] = False
            conf["ankimon_gym_pending"] = False
            conf["ankimon_gym_enemy_ids"] = []
            conf["ankimon_gym_enemy_index"] = 0
            conf["ankimon_gym_current_enemy_id"] = None
            mw.col.setMod()

        # Reset battle state to idle
        _ankimon_set_battle_state("idle")

        # Reset HP to ensure we're not in fainted state
        hp = 1

        # Spawn new wild pokemon
        try:
            new_pokemon()
            # Force window update
            if test_window is not None and pkmn_window is True:
                test_window.display_first_encounter()
                test_window.show()
                test_window.raise_()
                test_window.activateWindow()
        except Exception as e:
            showWarning(f"Error spawning new pokemon: {e}")
            import traceback
            traceback.print_exc()
            return

        showInfo("Battle has been reset. A new wild pokemon has appeared!")
    except Exception as e:
        showWarning(f"Error resetting battle: {e}")
        import traceback
        traceback.print_exc()

def calc_atk_dmg(level, critical, power, stat_atk, wild_stat_def, main_type, move_type, wild_type, critRatio):
        if power is None:
            # You can choose a default power or handle it according to your requirements
            power = 0
        if critRatio == 1:
            crit_chance = 0.0417
        elif critRatio == 2:
            crit_chance = 0.125
        elif critRatio == 3:
            crit_chance = 0.5
        elif critRatio > 3:
            crit_chance = 1
        random_number = random.random()  # Generate a random number between 0 and 1
        if random_number > crit_chance:
            critical = critical * 1
        else:
            critical += 2
        # damage = (((2 * level * critical)+2)/ 5) * power * stat_atk / wild_stat_def)+2)/ 50 * stab * random
        # if move_typ is the same as the main pkmn type => damage * 1.5; else damage * 1.0
        # STAB calculation
        stab = 1.5 if move_type == main_type else 1.0
        eff = get_effectiveness(move_type)
        # random luck
        random_number = random.randint(217, 255)
        random_factor = random_number / 255
        damage = (((((2 * level * critical) + 2) / 5) * power * stat_atk / wild_stat_def) + 2) / 50 * stab * eff * random_factor
        # if main pkmn type = move type => damage * 1,5
        # if wild pokemon type x main pokemon type => 0.5 not very eff.; 1.0 eff.; 2 very eff.
        return damage

def calculate_hp(base_stat_hp, level, ev, iv):
    ev_value = ev["hp"] / 4
    iv_value = iv["hp"]
    #hp = int(((iv + 2 * (base_stat_hp + ev) + 100) * level) / 100 + 10)
    hp = int((((((base_stat_hp + iv_value) * 2 ) + ev_value) * level) / 100) + level + 10)
    return hp

def get_mainpokemon_evo(pokemon_name):
    global pokedex_path
    with open(str(pokedex_path), "r", encoding="utf-8") as json_file:
            pokedex_data = json.load(json_file)
            if pokemon_name in pokedex_data:
                pokemon_info = pokedex_data[pokemon_name]
                evolutions = pokemon_info.get("evos", [])
                return evolutions
            else:
                return []

def search_pokedex(pokemon_name,variable):
    global pokedex_path
    pokemon_name = special_pokemon_names_for_min_level(pokemon_name)
    with open(str(pokedex_path), "r", encoding="utf-8") as json_file:
            pokedex_data = json.load(json_file)
            if pokemon_name in pokedex_data:
                pokemon_info = pokedex_data[pokemon_name]
                var = pokemon_info.get(variable, None)
                return var
            else:
                return []

def search_pokedex_by_name_for_id(pokemon_name, variable):
    global pokedex_path
    pokemon_name = special_pokemon_names_for_min_level(pokemon_name)
    with open(str(pokedex_path), "r", encoding="utf-8") as json_file:
            pokedex_data = json.load(json_file)
            if pokemon_name in pokedex_data:
                pokemon_info = pokedex_data[pokemon_name]
                var = pokemon_info.get("num", None)
                return var
            else:
                return None

def search_pokedex_by_id(pokemon_id):
    global pokedex_path
    with open(str(pokedex_path), "r", encoding="utf-8") as json_file:
            pokedex_data = json.load(json_file) 
            for entry_name, attributes in pokedex_data.items():
                if attributes['num'] == pokemon_id:
                    return entry_name
    return 'Pokémon not found'

def get_pokemon_diff_lang_name(pokemon_id):
    global language
    global pokenames_lang_path
    with open(pokenames_lang_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header row if there is one
        for row in reader:
            # Assuming the CSV structure is: pokemon_species_id,local_language_id,name,genus
            species_id, lang_id, name, genus = row
            if int(species_id) == pokemon_id and int(lang_id) == language:
                return name
    return "No Translation in this language"  # Return None if no match is found

def get_pokemon_descriptions(species_id):
    global language
    global pokedesc_lang_path
    descriptions = []  # Initialize an empty list to store matching descriptions
    with open(pokedesc_lang_path, mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            if int(row['species_id']) == species_id and int(row['language_id']) == language:
                # Replace control characters for readability, if necessary
                flavor_text = row['flavor_text'].replace('\x0c', ' ')
                descriptions.append(flavor_text)  # Add the matching description to the list
    if descriptions:
        if len(descriptions) > 1:
            return random.choice(descriptions)
        else:
            return descriptions
    else:
        ["Description not found."]

def search_pokeapi_db(pkmn_name,variable):
    global addon_dir
    global pokeapi_db_path
    with open(str(pokeapi_db_path), "r", encoding="utf-8") as json_file:
            pokedex_data = json.load(json_file)
            for pokemon_data in pokedex_data:
                name = pokemon_data["name"]
                if pokemon_data["name"] == pkmn_name:
                    var = pokemon_data.get(variable, None)
                    return var
            else:
                return None

def search_pokeapi_db_by_id(pkmn_id,variable):
    global addon_dir
    global pokeapi_db_path
    with open(str(pokeapi_db_path), "r", encoding="utf-8") as json_file:
            pokedex_data = json.load(json_file)
            for pokemon_data in pokedex_data:
                if pokemon_data["id"] == pkmn_id:
                    var = pokemon_data.get(variable, None)
                    return var
            else:
                return None
            
def mainpokemon_data():
    global mainpkmn
    global mainpokemon_name, mainpokemon_id, mainpokemon_ability, mainpokemon_type, mainpokemon_stats, mainpokemon_attacks, mainpokemon_level, mainpokemon_base_experience, mainpokemon_xp, mainpokemon_hp, mainpokemon_current_hp, mainpokemon_growth_rate, mainpokemon_ev, mainpokemon_iv, mainpokemon_evolutions, mainpokemon_battle_stats, mainpokemon_gender, mainpokemon_nickname
    mainpkmn = 1
    try:
        with (open(str(mainpokemon_path), "r", encoding="utf-8") as json_file):
                main_pokemon_datalist = json.load(json_file)
                main_pokemon_data = []
                for main_pokemon_data in main_pokemon_datalist:
                    mainpokemon_name = main_pokemon_data["name"]
                    if not main_pokemon_data.get('nickname') or main_pokemon_data.get('nickname') is None:
                            mainpokemon_nickname = None
                    else:
                        mainpokemon_nickname = main_pokemon_data['nickname']
                    mainpokemon_id = main_pokemon_data["id"]
                    mainpokemon_ability = main_pokemon_data["ability"]
                    mainpokemon_type = main_pokemon_data["type"]
                    mainpokemon_stats = main_pokemon_data["stats"]
                    mainpokemon_attacks = main_pokemon_data["attacks"]
                    mainpokemon_level = main_pokemon_data["level"]
                    mainpokemon_hp_base_stat = mainpokemon_stats["hp"]
                    mainpokemon_evolutions = search_pokedex(mainpokemon_name, "evos")
                    mainpokemon_xp = mainpokemon_stats["xp"]
                    mainpokemon_ev = main_pokemon_data["ev"]
                    mainpokemon_iv = main_pokemon_data["iv"]
                    #mainpokemon_battle_stats = mainpokemon_stats
                    mainpokemon_battle_stats = {}
                    for d in [mainpokemon_stats, mainpokemon_iv, mainpokemon_ev]:
                        for key, value in d.items():
                            mainpokemon_battle_stats[key] = value
                    #mainpokemon_battle_stats += mainpokemon_iv
                    #mainpokemon_battle_stats += mainpokemon_ev
                    mainpokemon_hp = calculate_hp(mainpokemon_hp_base_stat,mainpokemon_level, mainpokemon_ev, mainpokemon_iv)
                    mainpokemon_current_hp = calculate_hp(mainpokemon_hp_base_stat,mainpokemon_level, mainpokemon_ev, mainpokemon_iv)
                    mainpokemon_base_experience = main_pokemon_data["base_experience"]
                    mainpokemon_growth_rate = main_pokemon_data["growth_rate"]
                    mainpokemon_gender = main_pokemon_data["gender"]
                    return mainpokemon_name, mainpokemon_id, mainpokemon_ability, mainpokemon_type, mainpokemon_stats, mainpokemon_attacks, mainpokemon_level, mainpokemon_base_experience, mainpokemon_xp, mainpokemon_hp, mainpokemon_current_hp, mainpokemon_growth_rate, mainpokemon_ev, mainpokemon_iv, mainpokemon_evolutions, mainpokemon_battle_stats, mainpokemon_gender, mainpokemon_nickname
    except:
            pass
#get main pokemon details:
if database_complete != False:
    try:
        mainpokemon_name, mainpokemon_id, mainpokemon_ability, mainpokemon_type, mainpokemon_stats, mainpokemon_attacks, mainpokemon_level, mainpokemon_base_experience, mainpokemon_xp, mainpokemon_hp, mainpokemon_current_hp, mainpokemon_growth_rate, mainpokemon_ev, mainpokemon_iv, mainpokemon_evolutions, mainpokemon_battle_stats, mainpokemon_gender, mainpokemon_nickname = mainpokemon_data()
        starter = True
    except Exception as e:
        starter = False
        mainpokemon_level = 5
    name, id, level, ability, type, stats, enemy_attacks, base_experience, growth_rate, hp, max_hp, ev, iv, gender, battle_status, battle_stats = generate_random_pokemon()
    # Select battle scene based on Pokemon's primary type
    primary_type = type[0] if isinstance(type, list) and len(type) > 0 else None
    battlescene_file = random_battle_scene(primary_type)

def get_effectiveness(move_type):
    global mainpokemon_type, effectiveness_chart_file_path, type
    move_type = move_type.capitalize()
    attacking_types = []
    attacking_types.append(move_type)
    defending_types = type
    attacking_types = [attacking_type.capitalize() for attacking_type in attacking_types]
    defending_types = [defending_type.capitalize() for defending_type in defending_types]
    with open(effectiveness_chart_file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
        # Find the effectiveness values for each attacking type
        effectiveness_values = []
        for attacking_type in attacking_types:
            if attacking_type in data:
                # Find the effectiveness values for each defending type
                eff_values = [data[attacking_type][defending_type] for defending_type in defending_types]
                effectiveness_values.extend(eff_values)  # Use extend to add values to the list
        if effectiveness_values:
            if len(effectiveness_values) > 1:
                # Multiply all values in the list
                eff_value = 1
                for value in effectiveness_values:
                    eff_value *= value
                effective_txt = effectiveness_text(eff_value)
                return eff_value
            else:
                effective_txt = effectiveness_text(effectiveness_values[0])
                return effectiveness_values[0]
    # If the combination is not found, return None or a default value
    return None

def effectiveness_text(effect_value):
    if effect_value == 0:
        effective_txt = "has missed."
    elif effect_value <= 0.5:
        effective_txt = "was not very effective."
    elif effect_value <= 1:
        effective_txt = "was effective."
    elif effect_value <= 1.5:
        effective_txt = "was very effective !"
    elif effect_value <= 2:
        effective_txt = "was super effective !"
    else:
        effective_txt = "was effective."
        #return None
    return effective_txt

def calc_multiply_card_rating():
    global card_ratings_count
    max_points = cards_per_round * 10
    multiply_sum = 0
    multiply_sum += (card_ratings_count['Easy'] * 20)
    multiply_sum += (card_ratings_count['Hard'] * 5)
    multiply_sum += (card_ratings_count['Good'] * 10)
    multiply_sum += (card_ratings_count['Again'] * 0)
    card_ratings_count = {"Again": 0, "Hard": 0, "Good": 0, "Easy": 0}
    multiplier = multiply_sum / max_points
    return multiplier

reviewed_cards_count = 0
general_card_count_for_battle = 0
enemy_trainer_card_counter = 0  # Counter for enemy trainer battles every 20 cards
current_trainer_name = None  # Current enemy trainer name
current_trainer_sprite = None  # Current enemy trainer sprite filename
is_trainer_battle = False  # Flag to track if current battle is vs trainer
cry_counter = 0
seconds = 0
myseconds = 0
# Hook into Anki's card review event
def on_review_card(*args):
    try:
        global reviewed_cards_count, card_ratings_count, card_counter, general_card_count_for_battle, enemy_trainer_card_counter, cry_counter, battle_sounds
        global hp, stats, type, battle_status, name, battle_stats, enemy_attacks, level
        global pokemon_encounter, mainpokemon_hp, seconds, myseconds, animate_time
        global mainpokemon_xp, mainpokemon_current_hp, mainpokemon_attacks, mainpokemon_level, mainpokemon_stats, mainpokemon_type, mainpokemon_name, mainpokemon_battle_stats, mainpokemon_ev, mainpokemon_iv
        global attack_counter
        global pkmn_window
        global achievements
        global current_trainer_name, current_trainer_sprite, is_trainer_battle
        # Increment the counter when a card is reviewed
        reviewed_cards_count += 1
        card_counter += 1
        cry_counter += 1
        enemy_trainer_card_counter += 1
        dmg = 0
        seconds = 0
        myseconds = 0
        general_card_count_for_battle += 1

        # Track card reviews in progression stats
        try:
            stats_data = _load_progression_stats()
            stats_data["lifetime"]["total_cards_reviewed"] += 1
            stats_data["current_round"]["cards_reviewed"] += 1
            stats_data["session"]["cards_reviewed"] += 1

            # Track cards in wild/enemy battles for mega stone rewards
            if pokemon_encounter > 0:  # Currently in a battle
                if not _ankimon_is_gym_active():  # Not a gym battle
                    # This is a wild or enemy trainer battle
                    cards_in_battles = stats_data.get("cards_in_wild_enemy_battles", 0)
                    cards_in_battles += 1
                    stats_data["cards_in_wild_enemy_battles"] = cards_in_battles

                    # NOTE: Mega stones now awarded from battles (gym/elite4/champion) instead of card milestones

            _save_progression_stats(stats_data)
        except Exception:
            pass  # Don't break gameplay if stats tracking fails
        if battle_sounds == True:
            if general_card_count_for_battle == 1:
                play_sound()

        # Try to trigger mega evolution at battle start (first card)
        if general_card_count_for_battle == 1 and pokemon_encounter > 0:
            try:
                if _can_mega_evolve():
                    _trigger_mega_evolution()
            except Exception as e:
                print(f"Error checking mega evolution: {e}")

        #test achievment system
        if card_counter == 100:
            check = check_for_badge(achievements,1)
            if check is False:
                achievements = receive_badge(1,achievements)
                test_window.display_badge(1)
        elif card_counter == 200:
            check = check_for_badge(achievements,2)
            if check is False:
                achievements = receive_badge(2,achievements)
                test_window.display_badge(2)
        elif card_counter == 300:
                check = check_for_badge(achievements,3)
                if check is False:
                    achievements = receive_badge(3,achievements)
                    test_window.display_badge(3)
        elif card_counter == 500:
                check = check_for_badge(achievements,4)
                if check is False:
                    receive_badge(4,achievements)
                    test_window.display_badge(4)

        # NOTE: Mega stones now awarded from battles (gym/elite4/champion) instead of card milestones

        if card_counter == item_receive_value:
            test_window.display_item()
            check = check_for_badge(achievements,6)
            if check is False:
                receive_badge(6,achievements)
                test_window.display_badge(6)

        # Check for enemy trainer battle every 10 cards
        check_enemy_trainer_encounter()

        if reviewed_cards_count >= cards_per_round:
            reviewed_cards_count = 0
            attack_counter = 0
            slp_counter = 0
            pokemon_encounter += 1
            multiplier = calc_multiply_card_rating()
            msg = ""
            msg += f"{multiplier}x Multiplier"
            #failed card = enemy attack
            if pokemon_encounter > 0 and hp > 0 and dmg_in_reviewer is True and multiplier < 1:
                msg += f" \n "
                try:
                    max_attempts = 3  # Set the maximum number of attempts
                    for _ in range(max_attempts):
                        rand_enemy_atk = random.choice(enemy_attacks)
                        enemy_move = find_details_move(rand_enemy_atk)
                        
                        if enemy_move is not None:
                            break  # Exit the loop if a valid enemy_move is found
                    msg += f"{name.capitalize()} chose {rand_enemy_atk.capitalize()} !"
                    e_move_category = enemy_move.get("category")
                    e_move_acc = enemy_move.get("accuracy")
                    if e_move_acc is True:
                        e_move_acc = 100
                    elif e_move_acc != 0:
                        e_move_acc = 100 / e_move_acc
                    if random.random() > e_move_acc:
                        msg += "\n Move has missed !"
                    else:
                        if e_move_category == "Status":
                            color = "#F7DC6F"
                            msg = effect_status_moves(rand_enemy_atk, stats, mainpokemon_stats, msg, mainpokemon_name , name)
                        elif e_move_category == "Physical" or e_move_category == "Special":
                            critRatio = enemy_move.get("critRatio", 1)
                            if e_move_category == "Physical":
                                color = "#F0B27A"
                            elif e_move_category == "Special":
                                color = "#D2B4DE"
                            if enemy_move["basePower"] == 0:
                                enemy_dmg = bP_none_moves(enemy_move)

                                # Apply mega evolution damage reduction (0.85x taken)
                                try:
                                    if _is_mega_active():
                                        enemy_dmg = int(enemy_dmg * 0.85)
                                except Exception:
                                    pass

                                mainpokemon_hp -= int(enemy_dmg)
                                if enemy_dmg == 0:
                                    msg += "\n Move has missed !"
                            else:
                                if e_move_category == "Special":
                                    def_stat = mainpokemon_stats["spd"]
                                    atk_stat = stats["spa"]
                                elif e_move_category == "Physical":
                                    def_stat = mainpokemon_stats["def"]
                                    atk_stat = stats["atk"]
                                enemy_dmg = int(calc_atk_dmg(level,(multiplier * 2),enemy_move["basePower"], atk_stat, def_stat, type, enemy_move["type"],mainpokemon_type, critRatio))

                                # Apply mega evolution damage reduction (0.85x taken)
                                try:
                                    if _is_mega_active():
                                        enemy_dmg = int(enemy_dmg * 0.85)
                                except Exception:
                                    pass

                                if enemy_dmg == 0:
                                    enemy_dmg = 1
                                mainpokemon_hp -= enemy_dmg
                                if enemy_dmg > 0:
                                    myseconds = animate_time
                                    if multiplier < 1:
                                        play_effect_sound("HurtNormal")
                                else:
                                    myseconds = 0
                                msg += f" {enemy_dmg} dmg is dealt to {mainpokemon_name.capitalize()}."
                except:
                    enemy_dmg = 0
                    rand_enemy_atk = random.choice(enemy_attacks)
                    enemy_move = find_details_move(rand_enemy_atk)
                    e_move_category = enemy_move.get("category")
                    if e_move_category == "Status":
                            color = "#F7DC6F"
                            msg = effect_status_moves(rand_enemy_atk, stats, mainpokemon_stats, msg, mainpokemon_name , name)
                    elif e_move_category == "Physical" or e_move_category == "Special":
                        if e_move_category == "Special":
                            def_stat = mainpokemon_stats["spd"]
                            atk_stat = stats["spa"]
                        elif e_move_category == "Physical":
                            def_stat = mainpokemon_stats["def"]
                            atk_stat = stats["atk"]                        
                        enemy_dmg = int(calc_atk_dmg(level,(multiplier * 2),random.randint(60, 100), atk_stat, def_stat, type, "Normal", mainpokemon_type, critRatio))

                        # Apply mega evolution damage reduction (0.85x taken)
                        try:
                            if _is_mega_active():
                                enemy_dmg = int(enemy_dmg * 0.85)
                        except Exception:
                            pass

                        if enemy_dmg == 0:
                            enemy_dmg = 1
                        mainpokemon_hp -= enemy_dmg
                    if enemy_dmg > 0:
                        myseconds = animate_time
                        if multiplier < 1:
                            play_effect_sound("HurtNormal")
                    else:
                        myseconds = 0
                    msg += f" {enemy_dmg} dmg is dealt to {mainpokemon_name.capitalize()}."
    
            # If 10 or more cards have been reviewed, show the random Pokémon
            if pokemon_encounter > 0 and hp > 0:
                dmg = 0
                random_attack = random.choice(mainpokemon_attacks)
                msg += f"\n {mainpokemon_name} has chosen {random_attack.capitalize()} !"
                move = find_details_move(random_attack)
                category = move.get("category")
                acc = move.get("accuracy")
                if battle_status != "fighting":
                    msg, acc, battle_status, stats = status_effect(battle_status, name, move, hp, slp_counter, battle_stats, msg, acc)
                if acc is True:
                    acc = 100
                if acc != 0:
                    calc_acc = 100 / acc
                else:
                    calc_acc = 0
                if battle_status == "slp":
                    calc_acc = 0
                    msg += f"{name.capitalize()} is deep asleep."
                    #slp_counter -= 1
                elif battle_status == "par":
                    msg += f"\n {name.capitalize()} is paralyzed."
                    missing_chance = 1 / 4
                    random_number = random.random()
                    if random_number < missing_chance:
                        acc = 0
                if random.random() > calc_acc:
                    msg += "\n Move has missed !"
                else:
                    if category == "Status":
                        color = "#F7DC6F"
                        msg = effect_status_moves(random_attack, mainpokemon_stats, stats, msg, name, mainpokemon_name)
                    elif category == "Physical" or category == "Special":
                        try:
                            critRatio = move.get("critRatio", 1)
                            if category == "Physical":
                                color = "#F0B27A"
                            elif category == "Special":
                                color = "#D2B4DE"
                            if move["basePower"] == 0:
                                dmg = bP_none_moves(move)

                                # Apply mega evolution damage boost (1.25x dealt)
                                try:
                                    if _is_mega_active():
                                        dmg = int(dmg * 1.25)
                                except Exception:
                                    pass

                                hp -= dmg
                                if dmg == 0:
                                    msg += "\n Move has missed !"
                                    #dmg = 1
                            else:
                                if category == "Special":
                                    def_stat = stats["spd"]
                                    atk_stat = mainpokemon_stats["spa"]
                                elif category == "Physical":
                                    def_stat = stats["def"]
                                    atk_stat = mainpokemon_stats["atk"]
                                dmg = int(calc_atk_dmg(mainpokemon_level, multiplier,move["basePower"], atk_stat, def_stat, mainpokemon_type, move["type"],type, critRatio))

                                # Apply mega evolution damage boost (1.25x dealt)
                                try:
                                    if _is_mega_active():
                                        dmg = int(dmg * 1.25)
                                except Exception:
                                    pass

                                if dmg == 0:
                                    dmg = 1
                                hp -= dmg
                                msg += f" {dmg} dmg is dealt to {name.capitalize()}."
                                move_stat = move.get("status", None)
                                secondary = move.get("secondary", None)
                                if secondary is not None:
                                    bat_status = move.get("secondary", None).get("status", None)
                                    if bat_status is not None:
                                        move_with_status(move, move_stat, secondary)
                                if move_stat is not None:
                                    move_with_status(move, move_stat, secondary)
                                if dmg == 0:
                                    msg += " \n Move has missed !"
                        except:
                            if category == "Special":
                                def_stat = stats["spd"]
                                atk_stat = mainpokemon_stats["spa"]
                            elif category == "Physical":
                                def_stat = stats["def"]
                                atk_stat = mainpokemon_stats["atk"]
                            dmg = int(calc_atk_dmg(mainpokemon_level, multiplier,random.randint(60, 100), atk_stat, def_stat, mainpokemon_type, "Normal",type, critRatio))

                            # Apply mega evolution damage boost (1.25x dealt)
                            try:
                                if _is_mega_active():
                                    dmg = int(dmg * 1.25)
                            except Exception:
                                pass

                            hp -= dmg
                        if hp <= 0:
                            hp = 0

                            # --- Gym battles: show fainted display with Next Pokemon button ---
                            try:
                                if _ankimon_is_gym_active():
                                    conf = _ankimon_get_col_conf()
                                    if conf:
                                        enemy_ids = conf.get("ankimon_gym_enemy_ids") or []

                                        # Validate gym state before proceeding
                                        if not enemy_ids or len(enemy_ids) == 0:
                                            # Gym has no pokemon - this shouldn't happen, reset gym
                                            try:
                                                tooltipWithColour("Gym state corrupted - resetting", "#FF0000")
                                            except:
                                                pass
                                            conf["ankimon_gym_active"] = False
                                            conf["ankimon_gym_enemy_ids"] = []
                                            conf["ankimon_gym_enemy_index"] = 0
                                            mw.col.setMod()
                                            try:
                                                new_pokemon()
                                            except:
                                                pass
                                            return

                                        # Show fainted display with button instead of auto-spawning
                                        try:
                                            if test_window is not None and pkmn_window is True:
                                                def _update_fainted_window():
                                                    test_window.display_gym_pokemon_fainted()
                                                    test_window.show()
                                                    test_window.raise_()
                                                    test_window.activateWindow()
                                                    test_window.update()  # Force Qt to redraw
                                                    test_window.repaint()  # Force immediate repaint
                                                # Call immediately
                                                _update_fainted_window()
                                                # Call again after short delay to ensure update
                                                from aqt.qt import QTimer
                                                QTimer.singleShot(100, _update_fainted_window)
                                        except Exception as e:
                                            try:
                                                error_msg = f"Error displaying fainted gym pokemon: {str(e)}"
                                                tooltipWithColour(error_msg, "#FF0000")
                                                import traceback
                                                traceback.print_exc()
                                            except:
                                                pass
                                        return
                            except Exception as e:
                                # If gym battle error occurs, still don't show catch/defeat dialog
                                if _ankimon_is_gym_active():
                                    try:
                                        error_msg = f"Gym battle error: {str(e)}"
                                        tooltipWithColour(error_msg, "#FF0000")
                                        import traceback
                                        traceback.print_exc()
                                    except:
                                        pass
                                    return
                                pass

                            # --- Elite Four battles: show fainted display with Next Pokemon button (GYM-STYLE FLOW) ---
                            try:
                                if _ankimon_is_elite_four_active():
                                    print("[Elite4Faint] Enemy fainted - showing fainted panel (NO auto-advance)")

                                    # Show fainted display with button instead of auto-advancing
                                    try:
                                        if test_window is not None and pkmn_window is True:
                                            def _update_fainted_window():
                                                test_window.display_elite_four_pokemon_fainted()
                                                test_window.show()
                                                test_window.raise_()
                                                test_window.activateWindow()
                                                test_window.update()
                                                test_window.repaint()
                                            # Call immediately
                                            _update_fainted_window()
                                            # Call again after short delay to ensure update
                                            from aqt.qt import QTimer
                                            QTimer.singleShot(100, _update_fainted_window)
                                    except Exception as e:
                                        try:
                                            error_msg = f"Error displaying fainted Elite Four pokemon: {str(e)}"
                                            tooltipWithColour(error_msg, "#FF0000")
                                            import traceback
                                            traceback.print_exc()
                                        except:
                                            pass
                                    return
                            except Exception as e:
                                if _ankimon_is_elite_four_active():
                                    try:
                                        error_msg = f"Elite Four battle error: {str(e)}"
                                        tooltipWithColour(error_msg, "#FF0000")
                                        import traceback
                                        traceback.print_exc()
                                    except:
                                        pass
                                    return
                                pass

                            # --- Champion battles: show fainted display with Next Pokemon button (GYM-STYLE FLOW) ---
                            try:
                                if _ankimon_is_champion_active():
                                    print("[ChampionFaint] Enemy fainted - showing fainted panel (NO auto-advance)")

                                    # Show fainted display with button instead of auto-advancing
                                    try:
                                        if test_window is not None and pkmn_window is True:
                                            def _update_fainted_window():
                                                test_window.display_champion_pokemon_fainted()
                                                test_window.show()
                                                test_window.raise_()
                                                test_window.activateWindow()
                                                test_window.update()
                                                test_window.repaint()
                                            # Call immediately
                                            _update_fainted_window()
                                            # Call again after short delay to ensure update
                                            from aqt.qt import QTimer
                                            QTimer.singleShot(100, _update_fainted_window)
                                    except Exception as window_error:
                                        try:
                                            error_msg = f"Champion fainted window error: {str(window_error)}"
                                            print(error_msg)
                                            import traceback
                                            traceback.print_exc()
                                        except:
                                            pass
                                    return
                            except Exception as e:
                                if _ankimon_is_champion_active():
                                    try:
                                        error_msg = f"Champion battle error: {str(e)}"
                                        tooltipWithColour(error_msg, "#FF0000")
                                        import traceback
                                        traceback.print_exc()
                                    except:
                                        pass
                                    return
                                pass

                            msg += f" {name.capitalize()} has fainted"
                    tooltipWithColour(msg, color)
                    if dmg > 0:
                        seconds = animate_time
                        if multiplier == 1:
                            play_effect_sound("HurtNormal")
                        elif multiplier < 1:
                            play_effect_sound("HurtNotEffective")
                        elif multiplier > 1:
                            play_effect_sound("HurtSuper")
                    else:
                        seconds = 0
            else:
                # Skip catch/defeat dialog during gym battles or when boss battle pending
                if not _ankimon_should_suppress_post_battle_ui():
                    if pkmn_window is True:
                        test_window.display_pokemon_death()
                    elif pkmn_window is False:
                        new_pokemon()
                        general_card_count_for_battle = 0
                else:
                    # Boss battle active/pending - auto-resolve and continue
                    if pkmn_window is False:
                        kill_pokemon()
                        general_card_count_for_battle = 0
            # Update window during battle (including gym battles)
            if pkmn_window is True:
                if hp > 0:
                    # Always update window when HP > 0, even during gym battles
                    test_window.display_first_encounter()
                elif hp < 1 and not _ankimon_should_suppress_post_battle_ui():
                    # Only show death dialog if NOT in boss battle (active or pending)
                    hp = 0
                    test_window.display_pokemon_death()
                    general_card_count_for_battle = 0
                elif hp < 1:
                    # Boss battle active/pending - auto-resolve
                    hp = 0
                    kill_pokemon()
                    general_card_count_for_battle = 0
            elif pkmn_window is False and not _ankimon_should_suppress_post_battle_ui():
                # Only auto-spawn new pokemon if NOT in boss battle (active or pending)
                if hp < 1:
                    hp = 0
                    kill_pokemon()
                    general_card_count_for_battle = 0
            # Reset the counter
            reviewed_cards_count = 0
        if cry_counter == 10 and battle_sounds is True:
            cry_counter = 0
            play_sound()
        if mainpokemon_hp < 1:
            msg = f"Your {mainpokemon_name} has been defeated and the wild {name} has fled!"
            play_effect_sound("Fainted")
            new_pokemon()
            mainpokemon_data()
            color = "#E12939"
            tooltipWithColour(msg, color)
    except Exception as e:
        showWarning(f"An error occured in reviewer: {e}")


def create_status_label(status_name):
    #to create status symbols
    # Define the background and outline colors for each status
    status_colors = {
        "burned": {"background": "#FF4500", "outline": "#C13500"},
        "frozen": {"background": "#ADD8E6", "outline": "#91B0C0"},
        "paralysis": {"background": "#FFFF00", "outline": "#CCCC00"},
        "poisoned": {"background": "#A020F0", "outline": "#8000C0"},
        "asleep": {"background": "#FFC0CB", "outline": "#D895A1"},
        "confusion": {"background": "#FFA500", "outline": "#CC8400"},
        "flinching": {"background": "#808080", "outline": "#666666"},
        "fainted": {"background": "#000000", "outline": "#000000", "text_color": "#FFFFFF"},
    }

    # Get the colors for the given status name
    colors = status_colors.get(status_name.lower())

    # If the status name is valid, create and style the QLabel
    if colors:
        label = QLabel(status_name.capitalize())
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"background-color: {colors['background']};"
            f"border: 2px solid {colors['outline']};"
            f"border-radius: 5px;"
            f"padding: 5px 10px;"
            f"font-weight: bold;"
            f"color: {colors.get('text_color', '#000000')};"
        )
    else:
        label = QLabel("Unknown Status")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            "padding: 5px 10px;"
        )

    return label
def create_status_html(status_name):
    global show_mainpkmn_in_reviewer, hp_bar_thickness, xp_bar_spacer
    status_colors = {
        "brn": {"background": "#FF4500", "outline": "#C13500", "name": "Burned"},
        "frz": {"background": "#ADD8E6", "outline": "#91B0C0", "name": "Frozen"},
        "par": {"background": "#FFFF00", "outline": "#CCCC00", "name": "Paralysis"},
        "psn": {"background": "#A020F0", "outline": "#8000C0", "name": "Poisoned"},
        "tox": {"background": "#A545FF", "outline": "#842BFF", "name": "Badly Poisoned"},
        "slp": {"background": "#FFC0CB", "outline": "#D895A1", "name": "Asleep"},
        "confusion": {"background": "#FFA500", "outline": "#CC8400", "name": "Confusion"},
        "flinching": {"background": "#808080", "outline": "#666666", "name": "Flinching"},
        "fainted": {"background": "#000000", "outline": "#000000", "text_color": "#FFFFFF", "name": "Fainted"},
        "fighting": {"background": "#C03028", "outline": "#7D1F1A", "name": "Fighting"},  # Example colors for Fighting
    }

    # Get the colors for the given status name
    colors = status_colors.get(status_name.lower())

    # If the status name is valid, create the HTML with inline CSS
    if colors:
        if show_mainpkmn_in_reviewer == 2:
            html = f"""
            <div id=pokestatus style="
                position: fixed;
                bottom: {140 + xp_bar_spacer + hp_bar_thickness}px; /* Adjust as needed */
                right: 1%;
                z-index: 9999;
                background-color: {colors['background']};
                border: 2px solid {colors['outline']};
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 8px;
                font-weight: bold;
                display: inline-block;
                color: {colors.get('text_color', '#000000')};
                text-transform: uppercase;
                text-align: center;
                margin: 4px;
            ">{colors['name']}</div>
            """
        elif show_mainpkmn_in_reviewer == 1:
            html = f"""
            <div id=pokestatus style="
                position: fixed;
                bottom: {40 + hp_bar_thickness + xp_bar_spacer}px; /* Adjust as needed */
                right: 15%;
                z-index: 9999;
                background-color: {colors['background']};
                border: 2px solid {colors['outline']};
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 8px;
                font-weight: bold;
                display: inline-block;
                color: {colors.get('text_color', '#000000')};
                text-transform: uppercase;
                text-align: center;
                margin: 4px;
            ">{colors['name']}</div>
            """
        elif show_mainpkmn_in_reviewer == 0:
            html = f"""
            <div id=pokestatus style="
                position: fixed;
                bottom: {40 + hp_bar_thickness}px; /* Adjust as needed */
                left: 160px;
                z-index: 9999;
                background-color: {colors['background']};
                border: 2px solid {colors['outline']};
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 8px;
                font-weight: bold;
                display: inline-block;
                color: {colors.get('text_color', '#000000')};
                text-transform: uppercase;
                text-align: center;
                margin: 4px;
            ">{colors['name']}</div>
            """
    else:
        html = "<div>Unknown Status</div>"

    return html

def get_multiplier_stats(stage):
    # Define the mapping of stage to factor
    stage_to_factor = {
        -6: 3/9, -5: 3/8, -4: 3/7, -3: 3/6, -2: 3/5, -1: 3/4,
        0: 3/3,
        1: 4/3, 2: 5/3, 3: 6/3, 4: 7/3, 5: 8/3, 6: 9/3
    }

    # Return the corresponding factor or a default value if the stage is out of range
    return stage_to_factor.get(stage, "Invalid stage")

def get_multiplier_acc_eva(stage):
    # Define the mapping of stage to factor
    stage_to_factor_new = {
        -6: 2/8, -5: 2/7, -4: 2/6, -3: 2/5, -2: 2/4, -1: 2/3,
        0: 2/2,
        1: 3/2, 2: 4/2, 3: 5/2, 4: 6/2, 5: 7/2, 6: 8/2
    }

    # Return the corresponding factor or a default value if the stage is out of range
    return stage_to_factor_new.get(stage, "Invalid stage")

def bP_none_moves(move):
    target =  move.get("target", None)
    if target == "normal":
        damage = move.get("damage")
        if damage is None:
            damage = 5
        return damage


def effect_status_moves(move_name, mainpokemon_stats, stats, msg, name, mainpokemon_name):
    global battle_status
    move = find_details_move(move_name)
    target = move.get("target")
    boosts = move.get("boosts", {})
    stat_boost_value = {
        "hp": boosts.get("hp", 0),
        "atk": boosts.get("atk", 0),
        "def": boosts.get("def", 0),
        "spa": boosts.get("spa", 0),
        "spd": boosts.get("spd", 0),
        "spe": boosts.get("spe", 0),
        "xp": mainpokemon_stats.get("xp", 0)
    }
    move_stat = move.get("status",None)
    status = move.get("secondary",None)
    if move_stat is not None:
        battle_status = move_stat
    if status is not None:
        random_number = random.random()
        chances = status["chance"] / 100
        if random_number < chances:
            battle_status = status["status"]
    if battle_status == "slp":
        slp_counter = random.randint(1, 3)
    if target == "self":
        for boost, stage in boosts.items():
            stat = get_multiplier_stats(stage)
            mainpokemon_stats[boost] = mainpokemon_stats.get(boost, 0) * stat
            msg += f" {mainpokemon_name.capitalize()}'s "
            if stage < 0:
                msg += f"{boost.capitalize()} is decreased."
            elif stage > 0:
                msg += f"{boost.capitalize()} is increased."
    elif target in ["normal", "allAdjacentFoes"]:
        for boost, stage in boosts.items():
            stat = get_multiplier_stats(stage)
            stats[boost] = stats.get(boost, 0) * stat
            msg += f" {name.capitalize()}'s "
            if stage < 0:
                msg += f"{boost.capitalize()} is decreased."
            elif stage > 0:
                msg += f"{boost.capitalize()} is increased."
    return msg

def move_with_status(move, move_stat, status):
    global battle_status
    target = move.get("target")
    bat_status = move.get("secondary", None).get("status", None)
    if target in ["normal", "allAdjacentFoes"]:
        if move_stat is not None:
            battle_status = move_stat
        if status is not None:
            random_number = random.random()
            chances = status["chance"] / 100
            if random_number < chances:
                battle_status = status["status"]
    if battle_status == "slp":
        slp_counter = random.randint(1, 3)

def status_effect(stat, name, move, hp, slp_counter, stats, msg, acc):
    # Extend the existing dictionary with the "Fighting" status
    if stat == "par":
        stats["spe"] = stats["spe"] * 0.5
        msg += f" {name.capitalize()}'s speed is reduced."
        missing_chance = 1/4
        random_number = random.random()
        if random_number < missing_chance:
            msg += (f"{name} is paralyzed! It can't move!")
            acc = 0
    elif stat == "brn":
        dmg = 1/16 * calculate_max_hp_wildpokemon()
        hp -= dmg
        msg += (f"Wild {name} was hurt by burning!")
    elif stat == "psn":
        max_hp = calculate_max_hp_wildpokemon()
        dmg = 1 / 8 * max_hp
        hp -= dmg
        msg += (f"The wild {name} was hurt by its poisoning!")
    elif stat == "tox":
        max_hp = calculate_max_hp_wildpokemon()
        dmg = ((random.randint(1,3)) / 16 * max_hp)
        hp -= dmg
        msg += (f"The wild {name} is badly poisoned and was hurt by is poisoning!")
        stat = "psn"
    elif stat == "frz":
        free_chance = 20 / 100
        if move["type"] == "fire" and move["target"] != "self":
            free_chance = 1
        random_number = random.random()
        if random_number < free_chance:
            msg += (f"Wild {name} is frozen solid!")
            acc = 0
        else:
            stat = None
            msg += (f"Wild {name} is no longer frozen!")
    elif stat == "slp":
            if slp_counter > 1:
                slp_counter -= 1
                msg += (f"Wild {name} is asleep!")
            else:
                stat = None
                msg += (f"Wild {name} is no longer asleep!")
    return msg, acc, stat, battle_stats

# Connect the hook to Anki's review event
gui_hooks.reviewer_did_answer_card.append(on_review_card)

from PyQt6 import *
from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtGui import QMovie

class MovieSplashLabel(QLabel):
    def __init__(self, gif_path, parent=None):
        super().__init__(parent)
        self.movie = QMovie(gif_path)
        self.movie.jumpToFrame(0)
        self.setMovie(self.movie)
        self.movie.frameChanged.connect(self.repaint)

    def showEvent(self, event):
        self.movie.start()

    def hideEvent(self, event):
        self.movie.stop()


class PokemonCollectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Captured Pokemon")
        self.setMinimumWidth(750)
        self.setMinimumHeight(400)
        self.layout = QVBoxLayout(self)

        # Search Filter
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search Pokémon...")
        #self.search_edit.textChanged.connect(self.filter_pokemon)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.filter_pokemon)

        # Add dropdown menu for generation filtering
        self.generation_combo = QComboBox()
        self.generation_combo.addItem("All")
        self.generation_combo.addItems(["Generation 1", "Generation 2", "Generation 3", "Generation 4", "Generation 5", "Generation 6", "Generation 7", "Generation 8"])
        self.generation_combo.currentIndexChanged.connect(self.filter_pokemon)

        # Add widgets to layout
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(self.search_button)
        filter_layout.addWidget(self.generation_combo)
        self.layout.addLayout(filter_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.container = QWidget()
        self.scroll_layout = QGridLayout(self.container)
        self.setup_ui()

    def showEvent(self, event):
        # Call refresh_pokemon_collection when the dialog is shown
        self.refresh_pokemon_collection()
    
    def refresh_pokemon_collection(self):
        # Clear previous contents
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        self.setup_ui()

    def setup_ui(self):

        try:
            with open(mypokemon_path, "r") as json_file:
                captured_pokemon_data = json.load(json_file)
                if captured_pokemon_data:
                    row, column = 0, 0
                    for pokemon_idx, pokemon in enumerate(captured_pokemon_data):
                        pokemon_container = QWidget()
                        image_label = QLabel()
                        pixmap = QPixmap()
                        pokemon_id = pokemon['id']
                        pokemon_name = pokemon['name']
                        if not pokemon.get('nickname') or pokemon.get('nickname') is None:
                            pokemon_nickname = None
                        else:
                            pokemon_nickname = pokemon['nickname']
                        pokemon_gender = pokemon['gender']
                        pokemon_level = pokemon['level']
                        pokemon_ability = pokemon['ability']
                        pokemon_type = pokemon['type']
                        pokemon_stats = pokemon['stats']
                        pokemon_hp = pokemon_stats["hp"],
                        pokemon_attacks = pokemon['attacks']
                        pokemon_base_experience = pokemon['base_experience']
                        pokemon_growth_rate = pokemon['growth_rate']
                        pokemon_ev = pokemon['ev']
                        pokemon_iv = pokemon['iv']
                        pokemon_variant = pokemon.get('variant', None)  # Get variant field
                        pokemon_description = search_pokeapi_db_by_id(pokemon_id, "description")
                        if gif_in_collection is True:
                            # Check if Pokemon is in Mega form (with hard Key Stone gate)
                            try:
                                mega_state = _load_mega_state()
                                is_mega_unlocked = mega_state and mega_state.get("key_stone_unlocked", False)
                            except (NameError, Exception):
                                is_mega_unlocked = False  # Default to locked if function not yet defined

                            # Check if Pokemon is shiny
                            is_shiny = pokemon.get('is_shiny', False)

                            # Priority: Mega > Shadow > Shiny > Normal
                            if is_mega_unlocked and pokemon.get('is_mega', False):
                                pkmn_image_path = str(user_path_sprites / "front_mega_pokemon_gif" / f"{pokemon_id}.gif")
                                # Fallback to normal if mega sprite doesn't exist
                                if not os.path.exists(pkmn_image_path):
                                    pkmn_image_path = str(user_path_sprites / "front_default_gif" / f"{pokemon_id}.gif")
                            elif pokemon_variant == "shadow" and pokemon_id == 150:
                                # Shadow Mewtwo variant
                                pkmn_image_path = str(user_path_sprites / "front_default_gif" / f"{pokemon_id}_shadow_front.gif")
                                _ankimon_log("INFO", "ShadowMewtwo", f"Collection list using Shadow Mewtwo GIF: {pkmn_image_path}")
                            elif is_shiny:
                                # Try shiny sprite
                                global shiny_front_default
                                pkmn_image_path = str(shiny_front_default / f"{pokemon_id}.gif")
                                # Fallback to normal if shiny sprite doesn't exist
                                if not os.path.exists(pkmn_image_path):
                                    pkmn_image_path = str(user_path_sprites / "front_default_gif" / f"{pokemon_id}.gif")
                            else:
                                pkmn_image_path = str(user_path_sprites / "front_default_gif" / f"{pokemon_id}.gif")
                            splash_label = MovieSplashLabel(pkmn_image_path)
                        else:
                            # PNG mode - check for shadow > shiny > normal
                            is_shiny = pokemon.get('is_shiny', False)
                            if pokemon_variant == "shadow" and pokemon_id == 150:
                                # Shadow Mewtwo variant (PNG)
                                pkmn_image_path = str(user_path_sprites / "front_default" / f"{pokemon_id}_shadow_front.png")
                                _ankimon_log("INFO", "ShadowMewtwo", f"Collection list using Shadow Mewtwo PNG: {pkmn_image_path}")
                            elif is_shiny:
                                # Try shiny PNG (if exists)
                                shiny_png_path = str(user_path_sprites / "shiny_front_default" / f"{pokemon_id}.png")
                                if os.path.exists(shiny_png_path):
                                    pkmn_image_path = shiny_png_path
                                else:
                                    pkmn_image_path = str(frontdefault / f"{pokemon_id}.png")
                            else:
                                pkmn_image_path = str(frontdefault / f"{pokemon_id}.png")
                        pixmap.load(pkmn_image_path)

                        # Calculate the new dimensions to maintain the aspect ratio
                        max_width = 300
                        max_height = 230
                        original_width = pixmap.width()
                        original_height = pixmap.height()

                        if original_width > max_width:
                            new_width = max_width
                            new_height = (original_height * max_width) // original_width
                            pixmap = pixmap.scaled(new_width, new_height)

                        painter = QPainter(pixmap)

                        if pokemon_gender == "M":
                            gender_symbol = "♂"
                        elif pokemon_gender == "F":
                            gender_symbol = "♀"
                        elif pokemon_gender == "N":
                            gender_symbol = ""
                        else:
                            gender_symbol = ""

                        if pokemon_nickname is None:
                            capitalized_name = f"{get_pokemon_diff_lang_name(int(pokemon_id)).capitalize()} {gender_symbol}"
                        else:
                            capitalized_name = f"{pokemon_nickname.capitalize()} {gender_symbol}"
                        lvl = (f" Level: {pokemon_level}")
                        type_txt = "Type: "
                        for type in pokemon_type:
                            type_txt += f" {type.capitalize()}"
                        ability_txt = (f" Ability: {pokemon_ability.capitalize()}")

                        font = QFont()
                        font.setPointSize(12)
                        painter.setFont(font)
                        fontpkmnspec = QFont()
                        fontpkmnspec.setPointSize(8)
                        painter.end()

                        # Name with shiny icon (if shiny)
                        name_container = QHBoxLayout()
                        name_container.setContentsMargins(0, 0, 0, 0)
                        name_container.setSpacing(5)

                        # Add shiny icon if Pokemon is shiny
                        is_shiny = pokemon.get('is_shiny', False)
                        if is_shiny:
                            shiny_icon_label = QLabel()
                            shiny_icon_path = addon_dir / "addon_sprites" / "icons" / "shiny-stars.png"
                            if shiny_icon_path.exists():
                                shiny_icon_pixmap = QPixmap(str(shiny_icon_path))
                                shiny_icon_scaled = shiny_icon_pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                                shiny_icon_label.setPixmap(shiny_icon_scaled)
                                name_container.addWidget(shiny_icon_label)

                        name_label = QLabel(capitalized_name)
                        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                        name_label.setFont(font)
                        name_container.addWidget(name_label)
                        name_container.addStretch()

                        # Convert QHBoxLayout to QWidget for adding to container
                        name_widget = QWidget()
                        name_widget.setLayout(name_container)

                        level_label = QLabel(lvl)
                        level_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                        level_label.setFont(fontpkmnspec)

                        type_label = QLabel(type_txt)
                        type_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                        type_label.setFont(fontpkmnspec)

                        ability_label = QLabel(ability_txt)
                        ability_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                        ability_label.setFont(fontpkmnspec)

                        # Held Item with Remove button
                        pokemon_held_item = pokemon.get('held_item', None)
                        held_item_container = QHBoxLayout()
                        if pokemon_held_item:
                            held_item_txt = f" Held Item: {pokemon_held_item.replace('_', ' ').replace('-', ' ').title()}"
                            held_item_label = QLabel(held_item_txt)
                            held_item_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                            held_item_label.setFont(fontpkmnspec)
                            held_item_container.addWidget(held_item_label)

                            # Add Remove button
                            remove_item_btn = QPushButton("Remove")
                            remove_item_btn.setFixedWidth(60)
                            remove_item_btn.setStyleSheet("font-size: 8px; padding: 2px;")
                            def _remove_held_item(*, _poke_name=pokemon_name):
                                _remove_pokemon_held_item(_poke_name)
                                self.refresh_pokemon_collection()
                            remove_item_btn.clicked.connect(_remove_held_item)
                            held_item_container.addWidget(remove_item_btn)
                        else:
                            held_item_txt = " Held Item: None"
                            held_item_label = QLabel(held_item_txt)
                            held_item_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                            held_item_label.setFont(fontpkmnspec)
                            held_item_container.addWidget(held_item_label)
                        held_item_container.addStretch()

                        image_label.setPixmap(pixmap)

                        pokemon_button = QPushButton("Show me Details")
                        pokemon_button.setIconSize(pixmap.size())
                        if len(pokemon_type) > 1:
                            pokemon_button.clicked.connect(lambda state, name=pokemon_name, level=pokemon_level, id=pokemon_id, ability=pokemon_ability, type=[pokemon_type[0], pokemon_type[1]], detail_stats=pokemon_stats, attacks=pokemon_attacks, base_experience=pokemon_base_experience, growth_rate=pokemon_growth_rate, description=pokemon_description, gender=pokemon_gender, nickname=pokemon_nickname, variant=pokemon_variant: PokemonCollectionDetails(name, level, id, ability, type, detail_stats, attacks, base_experience, growth_rate, description, gender, nickname, variant))
                        else:
                            pokemon_button.clicked.connect(lambda state, name=pokemon_name, level=pokemon_level, id=pokemon_id, ability=pokemon_ability, type=[pokemon_type[0]], detail_stats=pokemon_stats, attacks=pokemon_attacks, base_experience=pokemon_base_experience, growth_rate=pokemon_growth_rate, description=pokemon_description, gender=pokemon_gender, nickname=pokemon_nickname, variant=pokemon_variant: PokemonCollectionDetails(name, level, id, ability, type, detail_stats, attacks, base_experience, growth_rate, description, gender, nickname, variant))

                        slot_combo = QComboBox()
                        slot_combo.addItem("Assign to Slot...", -1)
                        slot_combo.addItem("Assign to Slot 1 (Active)", 0)
                        slot_combo.addItem("Assign to Slot 2", 1)
                        slot_combo.addItem("Assign to Slot 3", 2)
                        slot_combo.addItem("Assign to Slot 4", 3)
                        slot_combo.setFixedWidth(180)
                        def _on_party_choice(_idx, *, _poke_index=pokemon_idx, _combo=slot_combo, _poke_name=pokemon_name, _poke_nickname=pokemon_nickname):
                            data = _combo.currentData()
                            if data is None:
                                return
                            try:
                                slot = int(data)
                            except Exception:
                                return
                            if slot < 0 or slot > 3:
                                return
                            party = _load_party()
                            slots = party.get("slots", [None, None, None, None])
                            if not isinstance(slots, list) or len(slots) != 4:
                                slots = [None, None, None, None]
                            slots[slot] = _poke_index
                            party["slots"] = slots
                            if slot == 0:
                                party["active_slot"] = 0
                            _save_party(party)

                            # Update menu text to show new pokemon name
                            try:
                                _update_party_menu_text()
                            except Exception:
                                pass

                            # Get display name (nickname if available, otherwise regular name)
                            display_name = _poke_nickname.capitalize() if _poke_nickname else _poke_name.capitalize()

                            if slot == 0:
                                try:
                                    _set_active_from_party_slot(0)
                                except Exception:
                                    pass
                            else:
                                # Show confirmation popup for slots 2, 3, and 4
                                showInfo(f"Party Slot {slot+1} set to: {display_name}")
                            _combo.setCurrentIndex(0)
                        slot_combo.currentIndexChanged.connect(_on_party_choice)

                        container_layout = QVBoxLayout()
                        container_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
                        if gif_in_collection is True:
                            container_layout.addWidget(splash_label)
                            splash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        else:
                            container_layout.addWidget(image_label)
                            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        container_layout.addWidget(name_widget)
                        container_layout.addWidget(level_label)
                        container_layout.addWidget(type_label)
                        container_layout.addWidget(ability_label)
                        container_layout.addLayout(held_item_container)
                        container_layout.addWidget(pokemon_button)
                        container_layout.addWidget(slot_combo)
                        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        ability_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                        pokemon_container.setLayout(container_layout)
                        self.scroll_layout.addWidget(pokemon_container, row, column)
                        column += 1
                        if column >= 3:
                            column = 0
                            row += 1

                    self.container.setLayout(self.scroll_layout)
                    self.scroll_area.setWidget(self.container)
                    self.layout.addWidget(self.scroll_area)
                    self.setLayout(self.layout)
                else:
                    self.layout.addWidget(QLabel("You haven't captured any Pokémon yet."))
        except FileNotFoundError:
            self.layout.addWidget(QLabel(f"Can't open the Saving File. {mypokemon_path}"))

    def filter_pokemon(self):
        search_text = self.search_edit.text().lower()
        generation_index = self.generation_combo.currentIndex()
        # Clear previous contents
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        try:
            with open(mypokemon_path, "r") as json_file:
                captured_pokemon_data = json.load(json_file)
                if captured_pokemon_data:
                    row, column = 0, 0
                    for pokemon_idx, pokemon in enumerate(captured_pokemon_data):
                        pokemon_id = pokemon['id']
                        pokemon_name = pokemon['name'].lower()
                        pokemon_nickname = pokemon.get("nickname", None)
                        # Check if the Pokémon matches the search text and generation filter
                        if (search_text.lower() in pokemon_name.lower() or 
                            (pokemon_nickname is not None and search_text.lower() in pokemon_nickname.lower())) and \
                            0 <= generation_index <= 8 and \
                            ((generation_index == 0) or 
                            (1 <= pokemon_id <= 151 and generation_index == 1) or
                            (152 <= pokemon_id <= 251 and generation_index == 2) or
                            (252 <= pokemon_id <= 386 and generation_index == 3) or
                            (387 <= pokemon_id <= 493 and generation_index == 4) or
                            (494 <= pokemon_id <= 649 and generation_index == 5) or
                            (650 <= pokemon_id <= 721 and generation_index == 6) or
                            (722 <= pokemon_id <= 809 and generation_index == 7) or
                            (810 <= pokemon_id <= 898 and generation_index == 8)):

                            # Display the Pokémon
                            pokemon_container = QWidget()
                            image_label = QLabel()
                            pixmap = QPixmap()
                            pokemon_id = pokemon['id']
                            pokemon_name = pokemon['name']
                            if not pokemon.get('nickname') or pokemon.get('nickname') is None:
                                pokemon_nickname = None
                            else:
                                pokemon_nickname = pokemon['nickname']
                            pokemon_gender = pokemon['gender']
                            pokemon_level = pokemon['level']
                            pokemon_ability = pokemon['ability']
                            pokemon_type = pokemon['type']
                            pokemon_stats = pokemon['stats']
                            pokemon_hp = pokemon_stats["hp"],
                            pokemon_attacks = pokemon['attacks']
                            pokemon_base_experience = pokemon['base_experience']
                            pokemon_growth_rate = pokemon['growth_rate']
                            pokemon_ev = pokemon['ev']
                            pokemon_iv = pokemon['iv']
                            pokemon_variant = pokemon.get('variant', None)  # Get variant field
                            pokemon_description = search_pokeapi_db_by_id(pokemon_id, "description")
                            if gif_in_collection is True:
                                # Check if Pokemon is in Mega form (with hard Key Stone gate)
                                try:
                                    mega_state = _load_mega_state()
                                    is_mega_unlocked = mega_state and mega_state.get("key_stone_unlocked", False)
                                except (NameError, Exception):
                                    is_mega_unlocked = False  # Default to locked if function not yet defined

                                # Priority: Mega > Shadow > Normal
                                if is_mega_unlocked and pokemon.get('is_mega', False):
                                    pkmn_image_path = str(user_path_sprites / "front_mega_pokemon_gif" / f"{pokemon_id}.gif")
                                    # Fallback to normal if mega sprite doesn't exist
                                    if not os.path.exists(pkmn_image_path):
                                        pkmn_image_path = str(user_path_sprites / "front_default_gif" / f"{pokemon_id}.gif")
                                elif pokemon_variant == "shadow" and pokemon_id == 150:
                                    # Shadow Mewtwo variant
                                    pkmn_image_path = str(user_path_sprites / "front_default_gif" / f"{pokemon_id}_shadow_front.gif")
                                    _ankimon_log("INFO", "ShadowMewtwo", f"Filtered collection using Shadow Mewtwo GIF: {pkmn_image_path}")
                                else:
                                    pkmn_image_path = str(user_path_sprites / "front_default_gif" / f"{pokemon_id}.gif")
                                splash_label = MovieSplashLabel(pkmn_image_path)
                            else:
                                # PNG mode - check for shadow variant
                                if pokemon_variant == "shadow" and pokemon_id == 150:
                                    pkmn_image_path = str(user_path_sprites / "front_default" / f"{pokemon_id}_shadow_front.png")
                                    _ankimon_log("INFO", "ShadowMewtwo", f"Filtered collection using Shadow Mewtwo PNG: {pkmn_image_path}")
                                else:
                                    pkmn_image_path = str(frontdefault / f"{pokemon_id}.png")
                            pixmap.load(pkmn_image_path)

                            # Calculate the new dimensions to maintain the aspect ratio
                            max_width = 300
                            max_height = 230
                            original_width = pixmap.width()
                            original_height = pixmap.height()

                            if original_width > max_width:
                                new_width = max_width
                                new_height = (original_height * max_width) // original_width
                                pixmap = pixmap.scaled(new_width, new_height)

                            painter = QPainter(pixmap)

                            if pokemon_gender == "M":
                                gender_symbol = "♂"
                            elif pokemon_gender == "F":
                                gender_symbol = "♀"
                            elif pokemon_gender == "N":
                                gender_symbol = ""
                            else:
                                gender_symbol = ""

                            if pokemon_nickname is None:
                                capitalized_name = f"{get_pokemon_diff_lang_name(int(pokemon_id)).capitalize()} {gender_symbol}"
                            else:
                                capitalized_name = f"{pokemon_nickname.capitalize()} {gender_symbol}"
                            lvl = (f" Level: {pokemon_level}")
                            type_txt = "Type: "
                            for type in pokemon_type:
                                type_txt += f" {type.capitalize()}"
                            ability_txt = (f" Ability: {pokemon_ability.capitalize()}")

                            font = QFont()
                            font.setPointSize(12)
                            painter.setFont(font)
                            fontpkmnspec = QFont()
                            fontpkmnspec.setPointSize(8)
                            painter.end()

                            name_label = QLabel(capitalized_name)
                            name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                            name_label.setFont(font)

                            level_label = QLabel(lvl)
                            level_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                            level_label.setFont(fontpkmnspec)

                            type_label = QLabel(type_txt)
                            type_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                            type_label.setFont(fontpkmnspec)

                            ability_label = QLabel(ability_txt)
                            ability_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                            ability_label.setFont(fontpkmnspec)

                            # Held Item with Remove button
                            pokemon_held_item = pokemon.get('held_item', None)
                            held_item_container = QHBoxLayout()
                            if pokemon_held_item:
                                held_item_txt = f" Held Item: {pokemon_held_item.replace('_', ' ').replace('-', ' ').title()}"
                                held_item_label = QLabel(held_item_txt)
                                held_item_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                                held_item_label.setFont(fontpkmnspec)
                                held_item_container.addWidget(held_item_label)

                                # Add Remove button
                                remove_item_btn = QPushButton("Remove")
                                remove_item_btn.setFixedWidth(60)
                                remove_item_btn.setStyleSheet("font-size: 8px; padding: 2px;")
                                def _remove_held_item(*, _poke_name=pokemon_name):
                                    _remove_pokemon_held_item(_poke_name)
                                    self.refresh_pokemon_collection()
                                remove_item_btn.clicked.connect(_remove_held_item)
                                held_item_container.addWidget(remove_item_btn)
                            else:
                                held_item_txt = " Held Item: None"
                                held_item_label = QLabel(held_item_txt)
                                held_item_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                                held_item_label.setFont(fontpkmnspec)
                                held_item_container.addWidget(held_item_label)
                            held_item_container.addStretch()

                            image_label.setPixmap(pixmap)

                            pokemon_button = QPushButton("Show me Details")
                            pokemon_button.setIconSize(pixmap.size())
                            if len(pokemon_type) > 1:
                                pokemon_button.clicked.connect(lambda state, name=pokemon_name, level=pokemon_level, id=pokemon_id, ability=pokemon_ability, type=[pokemon_type[0], pokemon_type[1]], detail_stats=pokemon_stats, attacks=pokemon_attacks, base_experience=pokemon_base_experience, growth_rate=pokemon_growth_rate, description=pokemon_description, gender=pokemon_gender, nickname=pokemon_nickname, variant=pokemon_variant: PokemonCollectionDetails(name, level, id, ability, type, detail_stats, attacks, base_experience, growth_rate, description, gender, nickname, variant))
                            else:
                                pokemon_button.clicked.connect(lambda state, name=pokemon_name, level=pokemon_level, id=pokemon_id, ability=pokemon_ability, type=[pokemon_type[0]], detail_stats=pokemon_stats, attacks=pokemon_attacks, base_experience=pokemon_base_experience, growth_rate=pokemon_growth_rate, description=pokemon_description, gender=pokemon_gender, nickname=pokemon_nickname, variant=pokemon_variant: PokemonCollectionDetails(name, level, id, ability, type, detail_stats, attacks, base_experience, growth_rate, description, gender, nickname, variant))

                            slot_combo = QComboBox()
                            slot_combo.addItem("Assign to Slot...", -1)
                            slot_combo.addItem("Assign to Slot 1 (Active)", 0)
                            slot_combo.addItem("Assign to Slot 2", 1)
                            slot_combo.addItem("Assign to Slot 3", 2)
                            slot_combo.addItem("Assign to Slot 4", 3)
                            slot_combo.setFixedWidth(180)
                            def _on_party_choice(_idx, *, _poke_index=pokemon_idx, _combo=slot_combo, _poke_name=pokemon_name, _poke_nickname=pokemon_nickname):
                                data = _combo.currentData()
                                if data is None:
                                    return
                                try:
                                    slot = int(data)
                                except Exception:
                                    return
                                if slot < 0 or slot > 3:
                                    return
                                party = _load_party()
                                slots = party.get("slots", [None, None, None, None])
                                if not isinstance(slots, list) or len(slots) != 4:
                                    slots = [None, None, None, None]
                                slots[slot] = _poke_index
                                party["slots"] = slots
                                if slot == 0:
                                    party["active_slot"] = 0
                                _save_party(party)

                                # Update menu text to show new pokemon name
                                try:
                                    _update_party_menu_text()
                                except Exception:
                                    pass

                                # Get display name (nickname if available, otherwise regular name)
                                display_name = _poke_nickname.capitalize() if _poke_nickname else _poke_name.capitalize()

                                if slot == 0:
                                    try:
                                        _set_active_from_party_slot(0)
                                    except Exception:
                                        pass
                                else:
                                    # Show confirmation popup for slots 2, 3, and 4
                                    showInfo(f"Party Slot {slot+1} set to: {display_name}")
                                _combo.setCurrentIndex(0)
                            slot_combo.currentIndexChanged.connect(_on_party_choice)

                            container_layout = QVBoxLayout()
                            container_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
                            if gif_in_collection is True:
                                container_layout.addWidget(splash_label)
                                splash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            else:
                                container_layout.addWidget(image_label)
                                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            container_layout.addWidget(name_label)
                            container_layout.addWidget(level_label)
                            container_layout.addWidget(type_label)
                            container_layout.addWidget(ability_label)
                            container_layout.addLayout(held_item_container)
                            container_layout.addWidget(pokemon_button)
                            container_layout.addWidget(slot_combo)
                            type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            ability_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                            pokemon_container.setLayout(container_layout)
                            self.scroll_layout.addWidget(pokemon_container, row, column)
                            column += 1
                            if column >= 3:
                                column = 0
                                row += 1
                    self.container.setLayout(self.scroll_layout)
                    self.scroll_area.setWidget(self.container)
                    self.layout.addWidget(self.scroll_area)
                    self.setLayout(self.layout)                        
                else:
                    self.layout.addWidget(QLabel("You haven't captured any Pokémon yet."))
        except FileNotFoundError:
            self.layout.addWidget(QLabel(f"Can't open the Saving File. {mypokemon_path}"))


pokecollection_win = PokemonCollectionDialog()
_ankimon_register_window("pokecollection_win", pokecollection_win)

def rename_pkmn(nickname, pkmn_name):
    try:
        with open(mypokemon_path, "r") as json_file:
            captured_pokemon_data = json.load(json_file)
            pokemon = None
            if captured_pokemon_data:
                for pokemon_data in captured_pokemon_data:
                    if pokemon_data['name'] == pkmn_name:
                        pokemon = pokemon_data
                        if pokemon is not None:
                            pokemon["nickname"] = nickname
                            # Load data from the output JSON file
                            with open(str(mypokemon_path), "r") as output_file:
                                mypokemondata = json.load(output_file)
                                # Find and replace the specified Pokémon's data in mypokemondata
                                for index, pokemon_data in enumerate(mypokemondata):
                                    if pokemon_data["name"] == pkmn_name:
                                        mypokemondata[index] = pokemon
                                        break
                                        # Save the modified data to the output JSON file
                                with open(str(mypokemon_path), "w") as output_file:
                                    json.dump(mypokemondata, output_file, indent=2)
                                showInfo(f"Your {pkmn_name.capitalize()} has been renamed to {nickname}!")
                                pokecollection_win.refresh_pokemon_collection()
    except Exception as e:
        showWarning(f"An error occured: {e}")

def PokemonCollectionDetails(name, level, id, ability, type, detail_stats, attacks, base_experience, growth_rate, description, gender, nickname, variant=None):
    global frontdefault, type_style_file, language, icon_path, gif_in_collection
    # Create the dialog
    try:
        lang_name = get_pokemon_diff_lang_name(int(id)).capitalize()

        # Custom description for Shadow Mewtwo
        if variant == "shadow" and id == 150:
            description = "In the past, Anne was almost possessed by a Shadow Synergy Stone but was saved by Mewtwo, whom the Shadow Synergy Stone took control of and merged with instead."
        else:
            lang_desc = get_pokemon_descriptions(int(id))
            description = lang_desc

        wpkmn_details = QDialog(mw)
        if nickname is None:
            wpkmn_details.setWindowTitle(f"Infos to : {lang_name} ")
        else:
            wpkmn_details.setWindowTitle(f"Infos to : {nickname} ({lang_name}) ")

        wpkmn_details.setFixedWidth(500)
        wpkmn_details.setMaximumHeight(400)

        # Create a layout for the dialog
        layout = QVBoxLayout()
        typelayout = QHBoxLayout()
        attackslayout = QVBoxLayout()
        # Display the Pokémon image (check for variant first)
        pkmnimage_label = QLabel()
        pkmnpixmap = QPixmap()
        if gif_in_collection is True:
            # Check for shadow variant
            if variant == "shadow" and id == 150:
                pkmnimage_path = str(user_path_sprites / "front_default_gif" / f"{int(id)}_shadow_front.gif")
                _ankimon_log("INFO", "ShadowMewtwo", f"Collection Details using Shadow Mewtwo GIF: {pkmnimage_path}")
            else:
                pkmnimage_path = str(user_path_sprites / "front_default_gif" / f"{int(id)}.gif")
            pkmnimage_label = MovieSplashLabel(pkmnimage_path)
        else:
            # Check for shadow variant (PNG)
            if variant == "shadow" and id == 150:
                pkmnimage_path = str(user_path_sprites / "front_default" / f"{int(id)}_shadow_front.png")
                _ankimon_log("INFO", "ShadowMewtwo", f"Collection Details using Shadow Mewtwo PNG: {pkmnimage_path}")
            else:
                pkmnimage_path = str(frontdefault / f"{int(id)}.png")
            pkmnpixmap.load(str(pkmnimage_path))
            # Calculate the new dimensions to maintain the aspect ratio
            max_width = 150
            original_width = pkmnpixmap.width()
            original_height = pkmnpixmap.height()
            new_width = max_width
            new_height = (original_height * max_width) // original_width
            pkmnpixmap = pkmnpixmap.scaled(new_width, new_height)
        typeimage_file = f"{type[0]}.png"
        typeimage_path = addon_dir / "addon_sprites" / "Types" / typeimage_file
        pkmntype_label = QLabel()
        pkmntypepixmap = QPixmap()
        pkmntypepixmap.load(str(typeimage_path))
        if len(type) > 1:
            type_image_file2 = f"{type[1]}.png"
            typeimage_path2 = addon_dir / "addon_sprites" / "Types" / type_image_file2
            pkmntype_label2 = QLabel()
            pkmntypepixmap2 = QPixmap()
            pkmntypepixmap2.load(str(typeimage_path2))
        

        # Create a painter to add text on top of the image
        painter2 = QPainter(pkmnpixmap)

        #custom font
        custom_font = load_custom_font(20)

        # Capitalize the first letter of the Pokémon's name
        if nickname is None:
            capitalized_name = f"{lang_name.capitalize()}"
        else:
            capitalized_name = f"{nickname} ({lang_name.capitalize()})"
        # Create level text
        if (
            language == 11
            or language == 12
            or language == 4
            or language == 3
            or language == 2
            or language == 1
        ):
            result = list(split_string_by_length(description, 30))
        else:
            result = list(split_string_by_length(description, 55))
        description_formated = '\n'.join(result)
        description_txt = f"Description: \n {description_formated}"
        #curr_hp_txt = (f"Current Hp:{current_hp}")

        # Safe capitalize for growth_rate and ability (handle None)
        if growth_rate:
            growth_rate_txt = (f"Growth Rate: {growth_rate.capitalize()}")
        else:
            growth_rate_txt = (f"Growth Rate: Unknown")

        lvl = (f" Level: {level}")

        if ability:
            ability_txt = (f" Ability: {ability.capitalize()}")
        else:
            ability_txt = (f" Ability: Unknown")
        type_txt = (f" Type:")
        stats_list = [
            detail_stats["hp"],
            detail_stats["atk"],
            detail_stats["def"],
            detail_stats["spa"],
            detail_stats["spd"],
            detail_stats["spe"],
            detail_stats["xp"]
        ]
        stats_txt = f"Stats:\n\
            Hp: {stats_list[0]}\n\
            Attack: {stats_list[1]}\n\
            Defense: {stats_list[2]}\n\
            Special-attack: {stats_list[3]}\n\
            Special-defense: {stats_list[4]}\n\
            Speed: {stats_list[5]}\n\
            XP: {stats_list[6]}"
        attacks_txt = "Moves:"
        for attack in attacks:
            attacks_txt += f"\n{attack.capitalize()}"

        CompleteTable_layout = PokemonDetailsStats(detail_stats, growth_rate, level)

        # Properties of the text of the image
        # custom font
        namefont = load_custom_font(30)
        namefont.setUnderline(True)
        painter2.setFont(namefont)
        font = load_custom_font(20)
        painter2.end()

        # Convert gender name to symbol - this function is from Foxy-null
        if gender == "M":
            gender_symbol = "♂"
        elif gender == "F":
            gender_symbol = "♀"
        elif gender == "N":
            gender_symbol = ""
        else:
            gender_symbol = ""  # None

        # Create a QLabel for the capitalized name
        name_label = QLabel(f"{capitalized_name} - {gender_symbol}")
        name_label.setFont(namefont)
        # Create a QLabel for the level
        description_label = QLabel(description_txt)
        level_label = QLabel(lvl)
        growth_rate_label = QLabel(growth_rate_txt)
        base_exp_label = QLabel(f"Base XP: {base_experience}")
        # Align to the center
        level_label.setFont(font)
        base_exp_label.setFont(font)
        type_label= QLabel("Type:")
        type_label.setFont(font)
        # Create a QLabel for the level
        ability_label = QLabel(ability_txt)
        ability_label.setFont(font)
        attacks_label = QLabel(attacks_txt)
        attacks_label.setFont(font)
        growth_rate_label.setFont(font)
        if language == 1:
            description_font = load_custom_font(20)
        else:
            description_font = load_custom_font(15)
        description_label.setFont(description_font)
        #stats_label = QLabel(stats_txt)

        # Set the merged image as the pixmap for the QLabel
        if gif_in_collection is False:
            pkmnimage_label.setPixmap(pkmnpixmap)
        # Set the merged image as the pixmap for the QLabel
        pkmntype_label.setPixmap(pkmntypepixmap)
        if len(type) > 1:
            pkmntype_label2.setPixmap(pkmntypepixmap2)
        #Border
        #description_label.setStyleSheet("border: 0px solid #000000; padding: 0px;")
        level_label.setStyleSheet("border: 0px solid #000000; padding: 0px;")
        base_exp_label.setStyleSheet("border: 0px solid #000000; padding: 0px;")
        ability_label.setStyleSheet("border: 0px solid #000000; padding: 0px;")
        growth_rate_label.setStyleSheet("border: 0px solid #000000; padding: 0px;")
        type_label.setStyleSheet("border: 0px solid #000000; padding: 0px;")
        level_label.setFixedWidth(230)
        growth_rate_label.setFixedWidth(230)
        base_exp_label.setFixedWidth(230)
        pkmnimage_label.setFixedHeight(100)
        ability_label.setFixedWidth(230)
        attacks_label.setFixedWidth(230)
        first_layout = QHBoxLayout() #Top Image Left and Direkt Info Right
        TopR_layout_Box = QVBoxLayout() #Top Right Info Direkt Layout
        TopL_layout_Box = QVBoxLayout() #Top Left Pokemon and Direkt Info Layout
        typelayout_widget = QWidget()
        TopL_layout_Box.addWidget(level_label)
        TopL_layout_Box.addWidget(pkmnimage_label)

        TopFirstLayout = QWidget()
        TopFirstLayout.setLayout(first_layout)
        layout.addWidget(name_label)
        layout.addWidget(TopFirstLayout)
        layout.addWidget(description_label)
        #.addWidget(growth_rate_label)
        #.addWidget(base_exp_label)
        typelayout.addWidget(type_label)
        typelayout.addWidget(pkmntype_label)
        pkmntype_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pkmntype_label.setStyleSheet("border: 0px solid #000000; padding: 0px;")
        if len(type) > 1:
            typelayout.addWidget(pkmntype_label2)
            pkmntype_label2.setStyleSheet("border: 0px solid #000000; padding: 0px;")
            pkmntype_label2.setAlignment(Qt.AlignmentFlag.AlignLeft)
            pkmntype_label2.setAlignment(Qt.AlignmentFlag.AlignBottom)
        typelayout_widget.setLayout(typelayout)
        typelayout_widget.setStyleSheet("border: 0px solid #000000; padding: 0px;")
        typelayout_widget.setFixedWidth(230)
        TopL_layout_Box.addWidget(typelayout_widget)
        TopL_layout_Box.addWidget(ability_label)
        #attackslayout.addWidget(attacks_label)
        attacks_details_button = QPushButton("Attack Details") #add Details to Moves
        qconnect(attacks_details_button.clicked, lambda: attack_details_window(attacks))
        remember_attacks_details_button = QPushButton("Remember Attacks") #add Details to Moves

        # Handle Shadow Mewtwo specially for attack learning
        lookup_name = "mewtwo" if name == "Shadow Mewtwo" else name
        all_attacks = get_all_pokemon_moves(lookup_name, level)
        qconnect(remember_attacks_details_button.clicked, lambda: remember_attack_details_window(id, attacks, all_attacks))
        
        #free_pokemon_button = QPushButton("Release Pokemon") #add Details to Moves unneeded button
        attacks_label.setFixedHeight(150)
        TopR_layout_Box.addWidget(attacks_label)
        TopR_layout_Box.addWidget(attacks_details_button)
        TopR_layout_Box.addWidget(remember_attacks_details_button)
        first_layout.addLayout(TopL_layout_Box)
        first_layout.addLayout(TopR_layout_Box)
        layout.addLayout(first_layout)
        attacks_label.setStyleSheet("border: 2px solid white; padding: 5px;")
        #TopR_layout_Box.setStyleSheet("border: 2px solid white; padding: 5px;")
        statstablelayout = QWidget()
        statstablelayout.setLayout(CompleteTable_layout)
        layout.addWidget(statstablelayout)
        statstablelayout.setStyleSheet("border: 2px solid white; padding: 5px;")
        #statstablelayout.setFixedWidth(350)
        statstablelayout.setFixedHeight(200)
        free_pokemon_button = QPushButton("Release Pokemon") #add Details to Moves
        qconnect(free_pokemon_button.clicked, lambda: PokemonFree(name))
        trade_pokemon_button = QPushButton("Trade Pokemon") #add Details to Moves
        qconnect(trade_pokemon_button.clicked, lambda: PokemonTrade(name, id, level, ability, iv, ev, gender, attacks))
        layout.addWidget(trade_pokemon_button)
        layout.addWidget(free_pokemon_button)
        rename_button = QPushButton("Rename Pokemon") #add Details to Moves
        rename_input = QLineEdit()
        rename_input.setPlaceholderText("Enter a new Nickname for your Pokemon")
        qconnect(rename_button.clicked, lambda: rename_pkmn(rename_input.text(),name))
        layout.addWidget(rename_input)
        layout.addWidget(rename_button)
        #qconnect()
        #layout.addLayout(CompleteTable_layout)

        #wpkmn_details.setFixedWidth(500)
        #wpkmn_details.setMaximumHeight(600)

        # align things needed to middle
        pkmnimage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        growth_rate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        base_exp_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
        base_exp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pkmntype_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        pkmntype_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Align to the center
        ability_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        attacks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set the layout for the dialog
        wpkmn_details.setLayout(layout)

        # Show the dialog
        wpkmn_details.setWindowIcon(QIcon(str(icon_path))) # Add a Pokeball icon
        # Show the dialog
        wpkmn_details.exec()
    except Exception as e:
        showWarning(f"Error occured in Pokemon Details Button: {e}")

def attack_details_window(attacks):
    global icon_path
    window = QDialog()
    window.setWindowIcon(QIcon(str(icon_path)))
    layout = QVBoxLayout()
    # HTML content
    html_content = """
    <style>
      .pokemon-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
        margin-bottom: 20px;
      }

      .pokemon-table th, .pokemon-table td {
        padding: 8px;
        border: 1px solid #ddd; /* light grey border */
      }

      .pokemon-table th {
        background-color: #040D12;
      }

      .pokemon-table tr:nth-child(even) {background-color: #f9f9f9;}

      .pokemon-table .move-name {
        text-align: center;
        font-weight: bold;
      }

      .pokemon-table .basePower {
        font-weight: bold;
        text-align: center;
      }

      .pokemon-table .no-accuracy {
        text-align: center;
        color: yellow;
      }
    </style>
    </head>
    <body>

    <table class="pokemon-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Category</th>
          <th>Power</th>
          <th>Accuracy</th>
          <th>PP</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
    """
    # Loop through the list of attacks and add them to the HTML content
    for attack in attacks:
        move = find_details_move(attack)

        html_content += f"""
        <tr>
          <td class="move-name">{move['name']}</td>
          <td><img src="{type_icon_path(move['type'])}" alt="{move['type']}"/></td>
          <td><img src="{move_category_path(move['category'].lower())}" alt="{move['category']}"/></td>
          <td class="basePower">{move['basePower']}</td>
          <td class="no-accuracy">{move['accuracy']}</td>
          <td>{move['pp']}</td>
          <td>{move['shortDesc']}</td>
        </tr>
        """
    html_content += """
      </tbody>
    </table>

    </body>
    </html>
    """

    # Create a QLabel to display the HTML content
    label = QLabel(html_content)
    label.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Align the label's content to the top
    label.setScaledContents(True)  # Enable scaling of the pixmap

    layout.addWidget(label)
    window.setLayout(layout)
    window.exec()

def remember_attack_details_window(id, attack_set, all_attacks):
    global icon_path
    window = QDialog()
    window.setWindowIcon(QIcon(str(icon_path)))
    layout = QHBoxLayout()
    window.setWindowTitle("Remember Attacks")  # Optional: Set a window title
    # Outer layout contains everything
    outer_layout = QVBoxLayout(window)

    # Create a scroll area that will contain our main layout
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)

    # Main widget that contains the content
    content_widget = QWidget()
    layout = QHBoxLayout(content_widget)  # The main layout is now set on this widget

    # HTML content
    html_content = """
    <style>
      .pokemon-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
        margin-bottom: 20px;
      }

      .pokemon-table th, .pokemon-table td {
        padding: 8px;
        border: 1px solid #ddd; /* light grey border */
      }

      .pokemon-table th {
        background-color: #040D12;
      }

      .pokemon-table tr:nth-child(even) {background-color: #f9f9f9;}

      .pokemon-table .move-name {
        text-align: center;
        font-weight: bold;
      }

      .pokemon-table .basePower {
        font-weight: bold;
        text-align: center;
      }

      .pokemon-table .no-accuracy {
        text-align: center;
        color: yellow;
      }
    </style>
    </head>
    <body>

    <table class="pokemon-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Category</th>
          <th>Power</th>
          <th>Accuracy</th>
          <th>PP</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
    """
    # Loop through the list of attacks and add them to the HTML content
    for attack in all_attacks:
        move = find_details_move(attack)

        html_content += f"""
        <tr>
          <td class="move-name">{move['name']}</td>
          <td><img src="{type_icon_path(move['type'])}" alt="{move['type']}"/></td>
          <td><img src="{move_category_path(move['category'].lower())}" alt="{move['category']}"/></td>
          <td class="basePower">{move['basePower']}</td>
          <td class="no-accuracy">{move['accuracy']}</td>
          <td>{move['pp']}</td>
          <td>{move['shortDesc']}</td>
        </tr>
        """

    html_content += """
      </tbody>
    </table>

    </body>
    </html>
    """

    # Create a QLabel to display the HTML content
    label = QLabel(html_content)
    label.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Align the label's content to the top
    label.setScaledContents(True)  # Enable scaling of the pixmap
    attack_layout = QVBoxLayout()
    for attack in all_attacks:
        move = find_details_move(attack)
        remember_attack_button = QPushButton(f"Remember {attack}") #add Details to Moves
        remember_attack_button.clicked.connect(lambda checked, a=attack: remember_attack(id, attack_set, a))
        attack_layout.addWidget(remember_attack_button)
    attack_layout_widget = QWidget()
    attack_layout_widget.setLayout(attack_layout)
    # Add the label and button layout widget to the main layout
    layout.addWidget(label)
    layout.addWidget(attack_layout_widget)

    # Set the main widget with content as the scroll area's widget
    scroll_area.setWidget(content_widget)

    # Add the scroll area to the outer layout
    outer_layout.addWidget(scroll_area)

    window.setLayout(outer_layout)
    window.resize(1000, 400)  # Optional: Set a default size for the window
    window.exec()

def remember_attack(id, attacks, new_attack):
    global mainpokemon_path
    if mainpokemon_path.is_file():
        with open(mainpokemon_path, "r") as json_file:
            main_pokemon_data = json.load(json_file)
        for mainpkmndata in main_pokemon_data:
            if mainpkmndata["id"] == id:
                mainpokemon_name = mainpkmndata["name"]
                attacks = mainpkmndata["attacks"]
                if new_attack:
                    msg = ""
                    msg += f"Your {mainpkmndata['name'].capitalize()} can learn a new attack !"
                    if len(attacks) < 4:
                            attacks.append(new_attack)
                            msg += f"\n Your {mainpkmndata['name'].capitalize()} has learned {new_attack} !"
                            showInfo(f"{msg}")
                    else:
                            dialog = AttackDialog(attacks, new_attack)
                            if dialog.exec() == QDialog.DialogCode.Accepted:
                                selected_attack = dialog.selected_attack
                                index_to_replace = None
                                for index, attack in enumerate(attacks):
                                    if attack == selected_attack:
                                        index_to_replace = index
                                        pass
                                    else:
                                        pass
                                # If the attack is found, replace it with 'new_attack'
                                if index_to_replace is not None:
                                    attacks[index_to_replace] = new_attack
                                    showInfo(f"Replaced '{selected_attack}' with '{new_attack}'")
                                else:
                                    # Handle the case where the user cancels the dialog
                                    showInfo(f"{new_attack} will be discarded.")
                mainpkmndata["attacks"] = attacks
                mypkmndata = mainpkmndata
                mainpkmndata = [mainpkmndata]
                # Save the caught Pokémon's data to a JSON file
                with open(str(mainpokemon_path), "w") as json_file:
                    json.dump(mainpkmndata, json_file, indent=2)
                
                with open(str(mypokemon_path), "r") as output_file:
                    mypokemondata = json.load(output_file)

                # Find and replace the specified Pokémon's data in mypokemondata
                for index, pokemon_data in enumerate(mypokemondata):
                    if pokemon_data["name"] == mainpokemon_name:
                        mypokemondata[index] = mypkmndata
                        break
                # Save the modified data to the output JSON file
                with open(str(mypokemon_path), "w") as output_file:
                    json.dump(mypokemondata, output_file, indent=2)
            else:
                showInfo("Please Select this Pokemon first as Main Pokemon ! \n Only Mainpokemons can re-learn attacks!")
    else:
        showWarning("Missing Mainpokemon Data !")
    
def type_colors(type):
    type_colors = {
        "Normal": "#A8A77A",
        "Fire": "#EE8130",
        "Water": "#6390F0",
        "Electric": "#F7D02C",
        "Grass": "#7AC74C",
        "Ice": "#96D9D6",
        "Fighting": "#C22E28",
        "Poison": "#A33EA1",
        "Ground": "#E2BF65",
        "Flying": "#A98FF3",
        "Psychic": "#F95587",
        "Bug": "#A6B91A",
        "Rock": "#B6A136",
        "Ghost": "#735797",
        "Dragon": "#6F35FC",
        "Dark": "#705746",
        "Steel": "#B7B7CE",
        "Fairy": "#D685AD"
    }

    return type_colors.get(type, "Unknown")

def type_icon_path(type):
    global addon_dir
    png_file = f"{type}.png"
    icon_path = addon_dir / "addon_sprites" / "Types"
    icon_png_file_path = icon_path / png_file
    return icon_png_file_path

def move_category_path(category):
    global addon_dir
    png_file = f"{category}_move.png"
    category_path = addon_dir / "addon_sprites" / png_file
    return category_path

def MainPokemon(name, nickname, level, id, ability, type, detail_stats, attacks, hp, base_experience, growth_rate, ev, iv, gender, is_shiny=False, preserve_enemy=False, silent=False):
    # Display the Pokémon image
    global mainpkmn, addon_dir, currdirname, mainpokemon_path
    mainpkmn = 1
    # Capitalize the first letter of the Pokémon's name
    capitalized_name = name.capitalize()
    stats_list = [
        detail_stats["hp"],
        detail_stats["atk"],
        detail_stats["def"],
        detail_stats["spa"],
        detail_stats["spd"],
        detail_stats["spe"],
        detail_stats["xp"]
    ]
    # Create a dictionary to store the Pokémon's data
    main_pokemon_data = []
    main_pokemon_data = [
        {
            "name": name,
            "nickname": nickname,
            "gender": gender,
            "level": level,
            "id": id,
            "ability": ability,
            "type": type,
            "stats": detail_stats,
            "ev": ev,
            "iv": iv,
            "attacks": attacks,
            "base_experience": base_experience,
            "current_hp": calculate_hp(detail_stats["hp"],level, ev, iv),
            "growth_rate": growth_rate,
            "is_shiny": is_shiny
        }
    ]

    # Save the caught Pokémon's data to a JSON file
    with open(str(mainpokemon_path), "w") as json_file:
        json.dump(main_pokemon_data, json_file, indent=2)

    if not silent:
        showInfo(f"{capitalized_name} has been chosen as your main Pokemon !")
    if not preserve_enemy:
        new_pokemon()  # new pokemon if you change your pokemon
    mainpokemon_data()
    if pkmn_window is True:
        test_window.display_first_encounter()
	
def PokemonDetailsStats(detail_stats, growth_rate, level):
    
    
    CompleteTable_layout = QVBoxLayout()
    experience = find_experience_for_level(growth_rate, level)
    # Stat colors
    stat_colors = {
        "hp": QColor(255, 0, 0),  # Red
        "atk": QColor(255, 165, 0),  # Orange
        "def": QColor(255, 255, 0),  # Yellow
        "spa": QColor(0, 0, 255),  # Blue
        "spd": QColor(0, 128, 0),  # Green
        "spe": QColor(255, 192, 203),  # Pink
        "total": QColor(168, 168, 167),  # Beige
        "xp": QColor(58,155,220)  # lightblue
    }

    #custom font
    custom_font = load_custom_font(20)

    # Populate the table and create the stat bars
    for row, (stat, value) in enumerate(detail_stats.items()):
        stat_item2 = QLabel(stat.capitalize())
        max_width_stat_item = 200
        stat_item2.setFixedWidth(max_width_stat_item)
        if stat == "xp":
            experience = int(experience)
            xp = value
            value = int((int(value) / experience) * max_width_stat_item)
        value_item2 = QLabel(str(value))
        if stat == "xp":
            value_item2 = QLabel(str(xp))
        stat_item2.setFont(custom_font)
        value_item2.setFont(custom_font)
        # Create a bar item
        bar_item2 = QLabel()
        pixmap2 = createStatBar(stat_colors.get(stat), value)
        # Convert the QPixmap to an QIcon
        icon = QIcon(pixmap2)
        # Set the QIcon as the background for the QLabel
        bar_item2.setPixmap(icon.pixmap(200, 10))  # Adjust the size as needed
        layout_row = str(f"{row}" + "row")
        layout_row = QHBoxLayout()
        layout_row.addWidget(stat_item2)
        layout_row.addWidget(value_item2)
        layout_row.addWidget(bar_item2)
        stat_item2.setStyleSheet("border: 0px solid #000000; padding: 0px;")
        bar_item2.setStyleSheet("border: 0px solid #000000; padding: 0px;")
        value_item2.setStyleSheet("border: 0px solid #000000; padding: 0px;")
        stat_item2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar_item2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        CompleteTable_layout.addLayout(layout_row)

    return CompleteTable_layout

def PokemonTrade(name, id, level, ability, iv, ev, gender, attacks):
    global addon_dir
    global mainpokemon_path
     # Load the data from the file
    with open(mainpokemon_path, 'r') as file:
        pokemon_data = json.load(file)

    found = False
    for pokemons in pokemon_data:
        if pokemons["name"] == name:
            found = True
            break

    if not found:
        pokemon_trade = []
        pokemon_trade = [
            {
                "name": name,
                "level": level,
                "gender": gender,
                "ability": ability,
                "type": type,
                "stats": stats,
                "ev": ev,
                "iv": iv,
                "attacks": attacks,
                "base_experience": base_experience,
                "current_hp": 30,
                "growth_rate": growth_rate
            }
        ]
        # Create a main window
        window = QDialog()
        window.setWindowTitle(f"Trade Pokemon {name}")
        # Create an input field for error code
        trade_code_input = QLineEdit()
        trade_code_input.setPlaceholderText("Enter Pokemon Code you want to Trade for")

        # Create a button to save the input
        trade_button = QPushButton("Trade Pokemon")
        qconnect(trade_button.clicked, lambda: PokemonTradeIn(trade_code_input.text(), name))
        # Information label
        info = "Pokemon Infos have been Copied to your Clipboard! \nNow simply paste this text into Teambuilder in PokemonShowdown. \nNote: Fight in the [Gen 9] Anything Goes - Battle Mode"

        pokemon_ev = ','.join([f"{value}" for stat, value in ev.items()])
        pokemon_iv = ','.join([f"{value}" for stat, value in iv.items()])
        if gender == "M":
            gender = 0
        elif gender == "F":
            gender = 1
        elif gender == "N":
            gender = 2
        else:
            gender = 3 #None

        attacks_ids = []
        for attack in attacks:
            attack = attack.replace(" ", "").lower()
            move_details = find_details_move(attack)
            if move_details:
                attacks_ids.append(str(move_details["num"]))

        attacks_id_string = ','.join(attacks_ids)  # Concatenated with a delimiter

        # Concatenating details to form a single string
        info = f"{id},{level},{gender},{pokemon_ev},{pokemon_iv},{attacks_id_string}"

        Trade_Info = QLabel(f"{name} Code: {info}")

        # Create a layout and add the labels
        layout = QVBoxLayout()
        layout.addWidget(Trade_Info)
        layout.addWidget(trade_code_input)
        layout.addWidget(trade_button)
        layout.addWidget(trade_code_input)
        # Set the layout for the main window
        window.setLayout(layout)

        # Copy text to clipboard in Anki
        #mw.app.clipboard().setText(pokemon_info)
        mw.app.clipboard().setText(f"{info}")

        # Write the Id, EV, IV and Attacks ID into numbers, seperated by ,
        # Place in a QLabel and Copy to clipboard
        # let player place Number in and find additionally needed data from pokedex
        # at last append to pokemon_list
        # check remove mainpokemon
        # remove pokemon from pokemon_list

        # Show the window
        window.exec()
    else:
        showWarning("You cant trade your Main Pokemon ! \n Please pick a different Main Pokemon and then you can trade this one.")

def find_move_by_num(move_num):
    global moves_file_path
    try:
        with open(moves_file_path, 'r', encoding='utf-8') as json_file:
            moves_data = json.load(json_file)

        # Iterate through each move in the data to find the one with the matching 'num'
        for move in moves_data.values():
            if move.get('num') == move_num:
                return move  # Return the move details if found

        # If the move wasn't found, return a message indicating so
        return showInfo(f"No move found with number: {move_num}")

    except FileNotFoundError:
        return showInfo("The moves file was not found. Please check the file path.")

    except json.JSONDecodeError as e:
        return showInfo(f"Error decoding JSON: {e}")


def find_pokemon_by_id(pokemon_id):
    global pokedex_path
    try:
        # Open and load the pokedex file
        with open(pokedex_path, 'r', encoding='utf-8') as json_file:
            pokedex = json.load(json_file)

        # Search for the Pokemon by ID
        for pokemon_name, details in pokedex.items():
            if details.get('num') == pokemon_id:
                return details  # Return the details if the Pokemon is found

        # If the Pokemon wasn't found, return a message indicating so
        showInfo(f"No Pokemon found with ID: {pokemon_id}")

    except FileNotFoundError:
        showInfo("The pokedex file was not found. Please check the file path.")

    except json.JSONDecodeError as e:
        showInfo(f"Error decoding JSON: {e}")

def trade_pokemon(old_pokemon_name, pokemon_trade):
    global mypokemon_path
    try:
        # Load the current list of Pokemon
        with open(mypokemon_path, 'r') as file:
            pokemon_list = json.load(file)
    except FileNotFoundError:
        print("The Pokemon file was not found. Please check the file path.")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return

    # Find and replace the specific Pokemon's information
    for i, pokemon in enumerate(pokemon_list):
        if pokemon["name"].lower() == old_pokemon_name.lower():
            pokemon_list[i] = pokemon_trade  # Replace with new Pokemon data
            break
    else:
        showInfo(f"Pokemon named '{old_pokemon_name}' not found.")
        return

    # Write the updated data back to the file
    try:
        with open(mypokemon_path, 'w') as file:
            json.dump(pokemon_list, file, indent=2)
        showInfo(f"{old_pokemon_name} has been traded successfully!")
    except Exception as e:
        showInfo(f"An error occurred while writing to the file: {e}")

    global mainpokemon_path
    # Load the data from the file
    with open(mainpokemon_path, 'r') as file:
        pokemons = json.load(file)

    # Find and remove the Pokemon with the given name
    pokemons = [p for p in pokemons if p['name'] != old_pokemon_name]

    # Write the updated data back to the file
    with open(mainpokemon_path, 'w') as file:
        json.dump(pokemons, file, indent=4)

def PokemonTradeIn(number_code, old_pokemon_name):
    if len(number_code) > 15:
        global addon_dir
        # Split the string into a list of integers
        numbers = [int(num) for num in number_code.split(',')]

        # Extracting specific parts of the list
        pokemon_id = numbers[0]
        level = numbers[1]
        gender_id = numbers[2]
        ev_stats = {'hp': numbers[3], 'atk': numbers[4], 'def': numbers[5], 'spa': numbers[6], 'spd': numbers[7],
                    'spe': numbers[8]}
        iv_stats = {'hp': numbers[9], 'atk': numbers[10], 'def': numbers[11], 'spa': numbers[12], 'spd': numbers[13],
                    'spe': numbers[14]}
        attack_ids = numbers[15:]
        attacks = []
        for attack_id in attack_ids:
            move = find_move_by_num(int(attack_id))
            attacks.append(move['name'])
        details = find_pokemon_by_id(pokemon_id)
        name = details["name"]
        type = details["types"]
        if gender_id == 0:
            gender = "M"
        elif gender_id == 1:
            gender = "F"
        elif gender_id == 2:
            gender = "N"
        else:
            gender = None #None
        stats = details["baseStats"]
        evos = details.get("evos", "None")
        #type = search_pokedex(name, "types")
        #stats = search_pokedex(name, "baseStats")
        global pokeapi_db_path
        with open(str(pokeapi_db_path), "r") as json_file:
            pokemon_data = json.load(json_file)
            for pokemon in pokemon_data:
                if pokemon["id"] == pokemon_id:
                    growth_rate = pokemon["growth_rate"]
        # Creating a dictionary to organize the extracted information
        stats["xp"] = 0
        pokemon_trade = {
                "name": name,
                "gender": gender,
                "ability": ability,
                "level": level,
                "id": pokemon_id,
                "type": type,
                "stats": stats,
                "ev": ev_stats,
                "iv": iv_stats,
                "attacks": attacks,
                "base_experience": base_experience,
                "current_hp": calculate_hp(stats["hp"], level, ev, iv),
                "growth_rate": growth_rate,
                "evos": evos
        }
        #showInfo(f"{pokemon_trade}")

        #PokemonFree(old_pokemon_name)
        #global mypokemon_path
        #with open(mypokemon_path, 'r') as file:
        #    pokemon_list = json.load(file)

        #pokemon_list.append(pokemon_trade)
        #for pokemon in pokemon_list:
        #    if pokemon["name"] == old_pokemon_name:
        #        pokemon = pokemon_trade

        # Write the updated data back to the file
        #with open(mypokemon_path, 'w') as file:
        #    json.dump(pokemon_list, file, indent=2)
        trade_pokemon(f"{old_pokemon_name}", pokemon_trade)
        showInfo(f"You have sucessfully traded your {old_pokemon_name} for {name} ")
    else:
        showWarning("Please enter a valid Code !")


def PokemonFree(name):
    global mypokemon_path
    global mainpokemon_path

    # Confirmation dialog
    reply = QMessageBox.question(None, "Confirm Release", 
                                 f"Are you sure you want to release {name}?", 
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                 QMessageBox.StandardButton.No)

    if reply == QMessageBox.StandardButton.No:
        showInfo("Release cancelled.")
        return

    # Load the data from the file
    with open(mainpokemon_path, 'r') as file:
        pokemon_data = json.load(file)

    found = False
    for pokemons in pokemon_data:
        if pokemons["name"] == name:
            found = True
            break

    if not found:
        with open(mypokemon_path, 'r') as file:
            pokemon_list = json.load(file)

        # Find and remove the Pokemon with the given name
        pokemon_list = [p for p in pokemon_list if p['name'] != name]

        # Write the updated data back to the file
        with open(mypokemon_path, 'w') as file:
            json.dump(pokemon_list, file, indent=2)
        showInfo(f"{name.capitalize()} has been let free.")
    else:
        showWarning("You can't free your Main Pokemon!")

def createStatBar(color, value):
    pixmap = QPixmap(200, 10)
    #pixmap.fill(Qt.transparent)
    pixmap.fill(QColor(0, 0, 0, 0))  # RGBA where A (alpha) is 0 for full transparency
    painter = QPainter(pixmap)

    # Draw bar in the background
    painter.setPen(QColor(Qt.GlobalColor.black))
    # new change due to pyqt6.6.1
    painter.setBrush(QColor(0, 0, 0, 200))  # Semi-transparent black
    painter.drawRect(0, 0, 200, 10)

    # Draw the colored bar based on the value
    painter.setBrush(color)
    bar_width = int(value * 1)  # Adjust the width as needed
    painter.drawRect(0, 0, bar_width, 10)

    return pixmap

def load_custom_font(font_size):
    global font_path, language
    if language == 1:
        font_file = "pkmn_w.ttf"
        font_file_path = font_path / font_file
        font_size = (font_size * 1) / 2
        if font_file_path.exists():
            font_name = "PKMN Western"
        else:
            font_name = "Early GameBoy"
            font_file = "Early GameBoy.ttf"
            font_size = (font_size * 5) / 7
    else:
        font_name = "Early GameBoy"
        font_file = "Early GameBoy.ttf"
        font_size = (font_size * 2) / 5

    # Register the custom font with its file path
    QFontDatabase.addApplicationFont(str(font_path / font_file))
    custom_font = QFont(font_name)  # Use the font family name you specified in the font file
    custom_font.setPointSize(font_size)  # Adjust the font size as needed

    return custom_font

#test functions

def find_experience_for_level(group_growth_rate, level):
    if level > 100:
    	level = 100
    if group_growth_rate == "medium":
        group_growth_rate = "medium-fast"
    elif group_growth_rate == "slow-then-very-fast":
        group_growth_rate = "fluctuating"
    elif group_growth_rate == "fast-then-very-slow":
        group_growth_rate = "fluctuating"
    global next_lvl_file_path
    # Specify the growth rate and level you're interested in
    growth_rate = f'{group_growth_rate}'
    # Open the CSV file
    csv_file_path = str(next_lvl_file_path)  # Replace 'your_file_path.csv' with the actual path to your CSV file
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        # Create a CSV reader
        csv_reader = csv.DictReader(file, delimiter=';')

        # Get the fieldnames from the CSV file
        fieldnames = [field.strip() for field in csv_reader.fieldnames]

        # Iterate through rows and find the experience for the specified growth rate and level
        for row in csv_reader:
            if row[fieldnames[0]] == str(level):  # Use the first fieldname to access the 'Level' column
                experience = row[growth_rate]
                break

        return experience

def find_experience_for_mainpokemon():
    global next_lvl_file_path
    global mainpokemon_growth_rate
    global mainpokemon_level
    global mainpokemon_xp, pop_up_dialog_message_on_defeat
    if mainpokemon_growth_rate == "medium":
        mainpokemon_growth_rate = "medium-fast"
    level = mainpokemon_level
    # Specify the growth rate and level you're interested in
    growth_rate = f'{mainpokemon_growth_rate}'
    # Open the CSV file
    csv_file_path = str(next_lvl_file_path)  # Replace 'your_file_path.csv' with the actual path to your CSV file
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        # Create a CSV reader
        csv_reader = csv.DictReader(file, delimiter=';')

        # Get the fieldnames from the CSV file
        fieldnames = [field.strip() for field in csv_reader.fieldnames]

        # Iterate through rows and find the experience for the specified growth rate and level
        for row in csv_reader:
            if row[fieldnames[0]] == str(level):  # Use the first fieldname to access the 'Level' column
                experience = row[growth_rate]
                experience = int(experience)
                experience -= mainpokemon_xp
                #if pop_up_dialog_message_on_defeat is True:
                    #showInfo((f"Your main Pokemon {mainpokemon_name} Lvl {level} needs {experience} XP to reach the next level."))
                break

        return experience

class Downloader(QObject):
    progress_updated = pyqtSignal(int)  # Signal to update progress bar
    download_complete = pyqtSignal()  # Signal when download is complete
    downloading_badges_sprites_txt = pyqtSignal()  # Signal when download is complete
    downloading_sprites_txt = pyqtSignal()  # Signal when download is complete
    downloading_sounds_txt = pyqtSignal()  # Signal when download is complete
    downloading_item_sprites_txt = pyqtSignal()  # Signal when download is complete
    downloading_data_txt = pyqtSignal()  # Signal when download is complete
    downloading_gif_sprites_txt = pyqtSignal()

    def __init__(self, addon_dir, parent=None):
        super().__init__(parent)
        self.addon_dir = Path(addon_dir)
        self.pokedex = []
        global user_path_data, user_path_sprites, pkmnimgfolder, backdefault, frontdefault, sound_list, items_list
        self.items_destination_to = user_path_sprites / "items"
        self.badges_destination_to = user_path_sprites / "badges"
        self.sounds_destination_to = user_path_sprites / "sounds"
        self.front_dir = os.path.join(user_path_sprites, "front_default")
        self.back_dir = os.path.join(user_path_sprites, "back_default")
        self.front_gif_dir = os.path.join(user_path_sprites, "front_default_gif")
        self.back_gif_dir = os.path.join(user_path_sprites, "back_default_gif")
        self.user_path_data = user_path_data
        self.badges_base_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/badges/"
        self.item_base_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/dream-world/"
        self.sounds_base_url = "https://play.pokemonshowdown.com/audio/cries/"
        self.sound_names = sound_list
        self.item_names = items_list
        if not os.path.exists(self.items_destination_to):
            os.makedirs(self.items_destination_to)
        if not os.path.exists(self.badges_destination_to):
            os.makedirs(self.badges_destination_to)
        if not os.path.exists(self.sounds_destination_to):
            os.makedirs(self.sounds_destination_to)
        if not os.path.exists(self.front_dir):
            os.makedirs(self.front_dir)
        if not os.path.exists(self.back_dir):
            os.makedirs(self.back_dir)
        if not os.path.exists(self.user_path_data):
            os.makedirs(self.user_path_data)
        if not os.path.exists(self.back_gif_dir):
            os.makedirs(self.back_gif_dir)
        if not os.path.exists(self.front_gif_dir):
            os.makedirs(self.front_gif_dir)       

        self.urls = [
                "https://play.pokemonshowdown.com/data/learnsets.json",
                "https://play.pokemonshowdown.com/data/pokedex.json",
                "https://play.pokemonshowdown.com/data/moves.json",
                "POKEAPI"
        ]
        self.csv_url = [
                "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/item_names.csv",
                "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon_species_flavor_text.csv",
                "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon_species_names.csv",
                "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/move_flavor_text.csv",
                "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon.csv",
                "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon_stats.csv"
        ]

    def save_to_json(self, pokedex, filename):
        with open(filename, 'w') as json_file:
            json.dump(pokedex, json_file, indent=2)

    def get_pokemon_data(self,pokemon_id):
        url = f'https://pokeapi.co/api/v2/pokemon/{pokemon_id}/'
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Failed to retrieve data for Pokemon with ID {pokemon_id}")
            return None

    def get_pokemon_species_data(self,pokemon_id):
        url = f'https://pokeapi.co/api/v2/pokemon-species/{pokemon_id}/'
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Failed to retrieve species data for Pokemon with ID {pokemon_id}")
            return None

    def fetch_pokemon_data(self,url):
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Failed to fetch data from {url}")
            return None

    def create_pokedex(self,pokemon_id):
        pokemon_data = self.get_pokemon_data(pokemon_id)
        species_data = self.get_pokemon_species_data(pokemon_id)
        if pokemon_data and species_data:
            entry = {
                "name": pokemon_data["name"],
                "id": pokemon_id,
                "effort_values": {
                    stat["stat"]["name"]: stat["effort"] for stat in pokemon_data["stats"]
                },
                "base_experience": pokemon_data["base_experience"],
                "growth_rate": species_data["growth_rate"]["name"]
            }
            self.pokedex.append(entry)

    def download_pokemon_data(self):
        try:
            global user_path_sprites, pkmnimgfolder, backdefault, frontdefault, pokeapi_db_path
            num_files = len(self.urls)
            self.downloading_data_txt.emit()
            for i, url in enumerate(self.urls, start=1):
                if url != "POKEAPI":
                    response = requests.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        file_path = self.user_path_data / f"{url.split('/')[-1]}"
                        with open(file_path, 'w') as json_file:
                            json.dump(data, json_file, indent=2)
                    else:
                        print(f"Failed to download data from {url}")  # Replace with a signal if needed
                    progress = int((i / num_files) * 100)
                    self.progress_updated.emit(progress)
                else:  # Handle "POKEAPI" case
                    self.pokedex = []
                    id = 899  # Assuming you want to fetch data for 898 Pokemon
                    for pokemon_id in range(1, id):
                        self.create_pokedex(pokemon_id)
                        progress = int((pokemon_id / id) * 100)
                        self.progress_updated.emit(progress)
                    self.save_to_json(self.pokedex, pokeapi_db_path)
            num_files = len(self.csv_url)
            for i, url in enumerate(self.csv_url, start=1):
                with requests.get(url, stream=True) as r:
                    file_path = self.addon_dir / "user_files" / "data_files" / f"{url.split('/')[-1]}"
                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192): 
                            f.write(chunk)
                progress = int((i / num_files) * 100)
                self.progress_updated.emit(progress)
            total_downloaded = 0
            self.id_to = 898
            self.downloading_sprites_txt.emit()
            for pokemon_id in range(1, self.id_to + 1):
                    for sprite_type in ["front_default", "back_default"]:
                        if sprite_type == "front_default":
                            base_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
                            response = requests.get(base_url)
                            if response.status_code == 200:
                                save_dir = self.front_dir
                                with open(os.path.join(save_dir, f"{pokemon_id}.png"), "wb") as f:
                                    f.write(response.content)
                        elif sprite_type == "back_default":
                            base_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/back/{pokemon_id}.png"
                            response = requests.get(base_url)
                            if response.status_code == 200:
                                save_dir = self.back_dir
                                with open(os.path.join(save_dir, f"{pokemon_id}.png"), "wb") as f:
                                    f.write(response.content)
                        total_downloaded += 1
                        progress = int((pokemon_id / self.id_to) * 100)
                        self.progress_updated.emit(progress)
            self.downloading_item_sprites_txt.emit()
            item_files = 336
            i = 0
            for item_name in self.item_names:
                i += 1
                item_url = self.item_base_url + item_name
                response = requests.get(item_url)
                if response.status_code == 200:
                    with open(os.path.join(self.items_destination_to, item_name), 'wb') as file:
                        file.write(response.content)
                progress = int((i / item_files) * 100)
                self.progress_updated.emit(progress)
            # Emit the download_complete signal at the end of the download process
            max_badges = 68
            self.downloading_badges_sprites_txt.emit()
            for badge_num in range(1,68):
                badge_file = f"{badge_num}.png"
                badge_url = self.badges_base_url + badge_file
                response = requests.get(badge_url)
                if response.status_code == 200:
                    with open(os.path.join(self.badges_destination_to, badge_file), 'wb') as file:
                        file.write(response.content)
                progress = int((badge_num / max_badges) * 100)
                self.progress_updated.emit(progress)
            self.downloading_sounds_txt.emit()
            num_sound_files = len(self.sound_names)
            i = 0
            for sound in self.sound_names:
                i += 1
                sounds_url = self.sounds_base_url + sound
                response = requests.get(sounds_url)
                if response.status_code == 200:
                    with open(os.path.join(self.sounds_destination_to, sound), 'wb') as file:
                        file.write(response.content)
                progress = int((i / num_sound_files) * 100)
                self.progress_updated.emit(progress)
            self.downloading_gif_sprites_txt.emit()
            base_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/"
            total_downloaded = 0
            self.id_to = 898
            for pokemon_id in range(1, self.id_to + 1):
                for sprite_type in ["front_showdown", "back_showdown"]:
                    front_sprite_url = f"{base_url}other/showdown/{pokemon_id}.gif"
                    response = requests.get(front_sprite_url)
                    if response.status_code == 200:
                        with open(os.path.join(self.front_gif_dir, f"{pokemon_id}.gif"), 'wb') as file:
                            file.write(response.content)
                    # Download back sprite
                    back_sprite_url = f"{base_url}other/showdown/back/{pokemon_id}.gif"
                    response = requests.get(back_sprite_url)
                    if response.status_code == 200:
                        with open(os.path.join(self.back_gif_dir, f"{pokemon_id}.gif"), 'wb') as file:
                            file.write(response.content)
                    progress = int((pokemon_id / self.id_to) * 100)
                    self.progress_updated.emit(progress)
            self.download_complete.emit()
        except Exception as e:
            showWarning(f"An error occurred: {e}")  # Replace with a signal if needed

class LoadingDialog(QDialog):
    def __init__(self, addon_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloading Resources")
        self.label = QLabel("Downloading... \nThis may take several minutes.", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        self.setLayout(layout)
        self.start_download(addon_dir)

    def start_download(self, addon_dir):
        self.thread = QThread()
        self.downloader = Downloader(addon_dir)
        self.downloader.moveToThread(self.thread)
        self.thread.started.connect(self.downloader.download_pokemon_data)
        self.downloader.progress_updated.connect(self.progress.setValue)
        self.downloader.downloading_data_txt.connect(self.downloading_data_txt)
        self.downloader.downloading_sprites_txt.connect(self.downloading_sprite_txt)
        self.downloader.downloading_item_sprites_txt.connect(self.downloading_item_sprites_txt)
        self.downloader.downloading_badges_sprites_txt.connect(self.downloading_badges_sprites_txt)
        self.downloader.downloading_sounds_txt.connect(self.downloading_sounds_txt)
        self.downloader.downloading_gif_sprites_txt.connect(self.downloading_gif_sprites_txt)
        self.downloader.progress_updated.connect(self.progress.setValue)
        self.downloader.download_complete.connect(self.on_download_complete)
        self.downloader.download_complete.connect(self.thread.quit)
        self.downloader.download_complete.connect(self.downloader.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_download_complete(self):
        self.label.setText("Download complete! You can now close this window.")
    
    def downloading_data_txt(self):
        self.label.setText("Now Downloading Data Files")

    def downloading_sprite_txt(self):
        self.label.setText("Now Downloading Sprite Files")

    def downloading_sounds_txt(self):
        self.label.setText("Now Downloading Sound Files")
        
    def downloading_item_sprites_txt(self):
        self.label.setText("Now Downloading Item Sprites...")

    def downloading_badges_sprites_txt(self):
        self.label.setText("Now Downloading Badges...")
        
    def downloading_gif_sprites_txt(self):
        self.label.setText("Now Downloading Gif Sprites...")

def show_agreement_and_download_database():
    # Show the agreement dialog
    dialog = AgreementDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        #pyqt6.6.1 difference
        # User agreed, proceed with download
        pokeapi_db_downloader()

def pokeapi_db_downloader():
    global addon_dir
    dlg = LoadingDialog(addon_dir)
    dlg.exec()

class AgreementDialog(QDialog):
    def __init__(self):
        super().__init__()

        # Setup the dialog layout
        layout = QVBoxLayout()
        # Add a label with the warning message
        title = QLabel("""Please agree to the terms before downloading the information:""")
        subtitle = QLabel("""Terms and Conditions Clause""")
        terms = QLabel("""§1 Disclaimer of Liability
(1) The user acknowledges that the use of the downloaded files is at their own risk. \n The provider assumes no liability for any damages, direct or indirect,\n that may arise from the download or use of such files.
(2) The provider is not responsible for the content of the downloaded files or \n for the legal consequences that may result from the use of the files. \n Each user is obligated to inform themselves about the legality of the use \n before using the files and to use the files only in a manner that does not cause any legal violations.

§2 Copyright Infringements
(1) The user agrees to respect copyright and other protective rights of third parties. \n It is prohibited for the user to download, reproduce, distribute, or make publicly available any copyrighted works \n without the required permission of the rights holder.
(2) In the event of a violation of copyright provisions, the user bears full responsibility and the resulting consequences. \n The provider reserves the right to take appropriate legal action \n in the event of becoming aware of any rights violations and to block access to the services.
                       
Check out https://pokeapi.co/docs/v2#fairuse and https://github.com/smogon/pokemon-showdown for more information.
                       """)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(terms)
         # Ensure the terms QLabel is readable and scrolls if necessary
        terms.setWordWrap(True)
        terms.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Add a checkbox for the user to agree to the terms
        self.checkbox = QCheckBox("I agree to the above named terms.")
        layout.addWidget(self.checkbox)

        # Add a button to proceed
        proceed_button = QPushButton("Proceed")
        proceed_button.clicked.connect(self.on_proceed_clicked)
        layout.addWidget(proceed_button)

        self.setLayout(layout)

    def on_proceed_clicked(self):
        if self.checkbox.isChecked():
            self.accept()  # Close the dialog and return success
        else:
            QMessageBox.warning(self, "Agreement Required", "You must agree to the terms to proceed.")

life_bar_injected = False

def animate_pokemon():
    seconds = 2
    from aqt import mw
    reviewer = mw.reviewer
    reviewer.web = mw.reviewer.web
    reviewer.web.eval(f'document.getElementById("PokeImage").style="animation: shake {seconds}s ease;"')
    if show_mainpkmn_in_reviewer is True:
        reviewer.web.eval(f'document.getElementById("MyPokeImage").style="animation: shake {myseconds}s ease;"')
   
if database_complete != False and mainpokemon_empty is False:
    def reviewer_reset_life_bar_inject():
        global life_bar_injected
        life_bar_injected = False
    def inject_life_bar(web_content, context):
        global life_bar_injected, hp, name, level, id, battle_status, show_mainpkmn_in_reviewer, mainpokemon_xp, icon_path
        global frontdefault, backdefault, addon_dir, user_path_sprites, mainpokemon_id, mainpokemon_name, mainpokemon_level, mainpokemon_hp, mainpokemon_stats, mainpokemon_ev, mainpokemon_iv, mainpokemon_growth_rate
        global hp_bar_thickness, xp_bar_config, xp_bar_location, hp_bar_config, xp_bar_spacer, hp_only_spacer, wild_hp_spacer, seconds, myseconds, view_main_front

        experience_for_next_lvl = find_experience_for_level(mainpokemon_growth_rate, mainpokemon_level)

        # Handle special variants (Shadow Mewtwo, etc.) - use base Pokemon for lookups
        lookup_name = "mewtwo" if name == "Shadow Mewtwo" else name.lower()

        if reviewer_image_gif == False:
            # For Shadow Mewtwo, use the id directly since it's already set
            if name == "Shadow Mewtwo":
                pokemon_imagefile = f'{id}_shadow_front.png'
            else:
                pokemon_imagefile = f'{search_pokedex(lookup_name, "num")}.png' #use for png files
            pokemon_image_file = os.path.join(frontdefault, pokemon_imagefile) #use for png files
            if show_mainpkmn_in_reviewer > 0:
                main_pkmn_imagefile = f'{mainpokemon_id}.png' #use for png files
                main_pkmn_imagefile_path = os.path.join(backdefault, main_pkmn_imagefile) #use for png files
        else:
            # Check for shadow variant
            global current_wild_variant
            if current_wild_variant == "shadow" and id == 150:
                pokemon_imagefile = f'{id}_shadow_front.gif'
                _ankimon_log("INFO", "ShadowMewtwo", f"Using Shadow Mewtwo sprite: {pokemon_imagefile}")
            else:
                pokemon_imagefile = f'{search_pokedex(lookup_name, "num")}.gif'
            pokemon_image_file = os.path.join((user_path_sprites / "front_default_gif"), pokemon_imagefile)

            # Fallback to PNG if GIF doesn't exist
            if not os.path.exists(pokemon_image_file):
                pokemon_imagefile_png = pokemon_imagefile.replace('.gif', '.png')
                pokemon_image_file_fallback = os.path.join((user_path_sprites / "front_default"), pokemon_imagefile_png)
                if os.path.exists(pokemon_image_file_fallback):
                    _ankimon_log("INFO", "SpriteLoad", f"GIF not found, using PNG fallback: {pokemon_imagefile_png}")
                    pokemon_image_file = pokemon_image_file_fallback
            if show_mainpkmn_in_reviewer > 0:
                main_pkmn_imagefile = f'{mainpokemon_id}.gif'

                # Check if Pokemon is in Mega form (uses hard Key Stone gate)
                is_mega_active = _is_mega_active()

                # Choose sprite directory based on Mega state
                if view_main_front == -1:
                    if is_mega_active:
                        gif_type = "front_mega_pokemon_gif"
                    else:
                        gif_type = "front_default_gif"
                else:
                    if is_mega_active:
                        gif_type = "back_mega_pokemon_gif"
                    else:
                        gif_type = "back_default_gif"

                main_pkmn_imagefile_path = os.path.join((user_path_sprites / f"{gif_type}"), main_pkmn_imagefile)

                # Fallback to normal sprite if mega sprite doesn't exist
                if is_mega_active and not os.path.exists(main_pkmn_imagefile_path):
                    if view_main_front == -1:
                        gif_type = "front_default_gif"
                    else:
                        gif_type = "back_default_gif"
                    main_pkmn_imagefile_path = os.path.join((user_path_sprites / f"{gif_type}"), main_pkmn_imagefile)
        if show_mainpkmn_in_reviewer > 0:
            mainpkmn_max_hp = calculate_hp(mainpokemon_stats["hp"], mainpokemon_level, mainpokemon_ev, mainpokemon_iv)
            mainpkmn_hp_percent = int((mainpokemon_hp / mainpkmn_max_hp) * 50)
            max_hp = calculate_max_hp_wildpokemon()
            pokemon_hp_percent = int((hp / max_hp) * 50)
        else:    
            max_hp = calculate_max_hp_wildpokemon()
            pokemon_hp_percent = int((hp / max_hp) * 100)
        is_reviewer = mw.state == "review"
        # Inject CSS and the life bar only if not injected before and in the reviewer
        # Use lookup_name for Shadow Mewtwo compatibility
        pokeball = check_pokecoll_in_list(search_pokedex(lookup_name, "num"))
        if not life_bar_injected and is_reviewer:
            css = """
            """
            if show_mainpkmn_in_reviewer == 0:
                css += f"""
                #life-bar {{
                width: {pokemon_hp_percent}%; /* Replace with the actual percentage */
                height: {hp_bar_thickness}px;
                background: linear-gradient(to right, 
                                            rgba(114, 230, 96, 0.7), /* Green with transparency */
                                            rgba(114, 230, 96, 0.7) 100%, /* Continue green to the percentage point */
                                            rgba(54, 54, 56, 0.7) 100%, /* Transition to dark background */
                                            rgba(54, 54, 56, 0.7)); /* Dark background with transparency */
                position: fixed;
                bottom: {10 + xp_bar_spacer}px;
                left: 0px;
                z-index: 9999;
                border-radius: 5px; /* Shorthand for all corners rounded */
                box-shadow: 0 0 10px rgba(0, 255, 0, 0.8), /* Green glow effect */
                            0 0 30px rgba(54, 54, 56, 1);  /* Dark glow effect */
                }}
                #hp-display {{
                position: fixed;
                bottom: {40 + xp_bar_spacer}px;
                right: 10px;
                z-index: 9999;
                color: white;
                font-size: 16px;
                font-weight: bold; /* Make the text bold */
                background-color: rgb(54,54,56,0.7); 
                text-align: right;
                }}
                #name-display {{
                position: fixed;
                bottom: {40 + xp_bar_spacer}px;
                left: 10px;
                z-index: 9999;
                color: white;
                font-size: 16px;
                background-color: rgb(54,54,56, 0.7);
                text-align: left;
                }}
                #PokeImage {{
                    position: fixed;
                    bottom: {30 + xp_bar_spacer + hp_bar_thickness}px; /* Adjust as needed */
                    left: 3px;
                    z-index: 9999;
                    width: 100px; /* Adjust as needed */
                    height: 100px; /* Adjust as needed */
                    background-size: cover; /* Cover the div area with the image */
                }}
                """
                css += f"""
                    #PokeIcon {{
                    position: fixed;
                    bottom: {85 + xp_bar_spacer}px; /* Adjust as needed */
                    left: 90px;
                    z-index: 9999;
                    width: 25px; /* Adjust as needed */
                    height: 25px; /* Adjust as needed */
                    }}
                    """
            elif show_mainpkmn_in_reviewer == 2:
                css += f"""
                #life-bar {{
                width: {pokemon_hp_percent}%; /* Replace with the actual percentage */
                height: {hp_bar_thickness}px;
                background: linear-gradient(to right, 
                                            rgba(114, 230, 96, 0.7), /* Green with transparency */
                                            rgba(114, 230, 96, 0.7) 100%, /* Continue green to the percentage point */
                                            rgba(54, 54, 56, 0.7) 100%, /* Transition to dark background */
                                            rgba(54, 54, 56, 0.7)); /* Dark background with transparency */
                position: fixed;
                bottom: {130 + xp_bar_spacer}px;
                right: 0px;
                z-index: 9999;
                border-radius: 5px; /* Shorthand for all corners rounded */
                box-shadow: 0 0 10px rgba(0, 255, 0, 0.8), /* Green glow effect */
                            0 0 30px rgba(54, 54, 56, 1);  /* Dark glow effect */
                }}
                #mylife-bar {{
                width: {mainpkmn_hp_percent}%; /* Replace with the actual percentage */
                height: {hp_bar_thickness}px;
                background: linear-gradient(to right, 
                                            rgba(114, 230, 96, 0.7), /* Green with transparency */
                                            rgba(114, 230, 96, 0.7) 100%, /* Continue green to the percentage point */
                                            rgba(54, 54, 56, 0.7) 100%, /* Transition to dark background */
                                            rgba(54, 54, 56, 0.7)); /* Dark background with transparency */
                position: fixed;
                bottom: {25 + xp_bar_spacer}px;
                left: 0px;
                z-index: 9999;
                border-radius: 5px; /* Shorthand for all corners rounded */
                box-shadow: 0 0 10px rgba(0, 255, 0, 0.8), /* Green glow effect */
                            0 0 30px rgba(54, 54, 56, 1);  /* Dark glow effect */
                }}
                #myhp-display {{
                position: fixed;
                bottom: {25 + xp_bar_spacer + hp_bar_thickness}px;
                right: {40 + hp_only_spacer}%;
                z-index: 9999;
                color: white;
                font-size: 16px;
                font-weight: bold; /* Make the text bold */
                background-color: rgb(54,54,56,0.7); 
                text-align: right;
                }}
                #myname-display {{
                position: fixed;
                bottom: {25 + xp_bar_spacer + hp_bar_thickness}px;
                left: 10px;
                z-index: 9999;
                color: white;
                font-size: 16px;
                background-color: rgb(54,54,56, 0.7);
                text-align: left;
                }}
                #MyPokeImage {{
                    position: fixed;
                    bottom: {50 + xp_bar_spacer + hp_bar_thickness}px; /* Adjust as needed */
                    left: 15px;
                    z-index: 9999;
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: bottom;
                    transform: scaleX({view_main_front});
                }}
                #hp-display {{
                position: fixed;
                bottom: {160 - wild_hp_spacer + xp_bar_spacer}px;
                left: {50 + hp_only_spacer}%;
                z-index: 9999;
                color: white;
                font-size: 16px;
                font-weight: bold; /* Make the text bold */
                background-color: rgb(54,54,56,0.7); 
                text-align: right;
                }}
                #name-display {{
                position: fixed;
                bottom: {20 + xp_bar_spacer}px;
                right: 10px;
                z-index: 9999;
                color: white;
                font-size: 16px;
                background-color: rgb(54,54,56, 0.7);
                text-align: right;
                }}
                #PokeImage {{
                    position: fixed;
                    bottom: {30 + xp_bar_spacer}px; /* Adjust as needed */
                    right: 3px;
                    z-index: 9999;
                    width: 100px; /* Adjust as needed */
                    height: 100px; /* Adjust as needed */
                    background-size: cover; /* Cover the div area with the image */
                }}"""
                css += f"""
                    #PokeIcon {{
                        position: fixed;
                        bottom: {8 + xp_bar_spacer}px; /* Adjust as needed */
                        right: 20%;
                        z-index: 9999;
                        width: 25px; /* Adjust as needed */
                        height: 25px; /* Adjust as needed */
                        background-size: cover; /* Cover the div area with the image */
                    }}
                    """
            elif show_mainpkmn_in_reviewer == 1:
                css += f"""
                #life-bar {{
                width: {pokemon_hp_percent}%; /* Replace with the actual percentage */
                height: {hp_bar_thickness}px;
                background: linear-gradient(to right, 
                                            rgba(114, 230, 96, 0.7), /* Green with transparency */
                                            rgba(114, 230, 96, 0.7) 100%, /* Continue green to the percentage point */
                                            rgba(54, 54, 56, 0.7) 100%, /* Transition to dark background */
                                            rgba(54, 54, 56, 0.7)); /* Dark background with transparency */
                position: fixed;
                bottom: {10 + xp_bar_spacer}px;
                right: 0px;
                z-index: 9999;
                border-radius: 5px; /* Shorthand for all corners rounded */
                box-shadow: 0 0 10px rgba(0, 255, 0, 0.8), /* Green glow effect */
                            0 0 30px rgba(54, 54, 56, 1);  /* Dark glow effect */
                }}
                #mylife-bar {{
                width: {mainpkmn_hp_percent}%; /* Replace with the actual percentage */
                height: {hp_bar_thickness}px;
                background: linear-gradient(to right, 
                                            rgba(114, 230, 96, 0.7), /* Green with transparency */
                                            rgba(114, 230, 96, 0.7) 100%, /* Continue green to the percentage point */
                                            rgba(54, 54, 56, 0.7) 100%, /* Transition to dark background */
                                            rgba(54, 54, 56, 0.7)); /* Dark background with transparency */
                position: fixed;
                bottom: {10 + xp_bar_spacer}px;
                left: 0px;
                z-index: 9999;
                border-radius: 5px; /* Shorthand for all corners rounded */
                box-shadow: 0 0 10px rgba(0, 255, 0, 0.8), /* Green glow effect */
                            0 0 30px rgba(54, 54, 56, 1);  /* Dark glow effect */
                }}
                #myhp-display {{
                position: fixed;
                bottom: {15 + xp_bar_spacer + hp_bar_thickness}px;
                right: {55}%;
                z-index: 9999;
                color: white;
                font-size: 16px;
                font-weight: bold; /* Make the text bold */
                background-color: rgb(54,54,56,0.7); 
                text-align: right;
                }}
                #myname-display {{
                position: fixed;
                bottom: {15 + xp_bar_spacer + hp_bar_thickness}px;
                left: 10px;
                z-index: 9999;
                color: white;
                font-size: 16px;
                background-color: rgb(54,54,56, 0.7);
                text-align: left;
                }}
                #MyPokeImage {{
                    position: fixed;
                    bottom: {50 + xp_bar_spacer + hp_bar_thickness}px; /* Adjust as needed */
                    left: 3px;
                    z-index: 9999;
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: bottom;
                    transform: scaleX({view_main_front});
                }}
                #hp-display {{
                position: fixed;
                bottom: {15 + xp_bar_spacer + hp_bar_thickness}px;
                left: {55}%;
                z-index: 9999;
                color: white;
                font-size: 16px;
                font-weight: bold; /* Make the text bold */
                background-color: rgb(54,54,56,0.7); 
                text-align: right;
                }}
                #name-display {{
                position: fixed;
                bottom: {15 + xp_bar_spacer + hp_bar_thickness}px;
                right: 10px;
                z-index: 9999;
                color: white;
                font-size: 16px;
                background-color: rgb(54,54,56, 0.7);
                text-align: right;
                }}
                #PokeImage {{
                    position: fixed;
                    bottom: {30 + xp_bar_spacer + hp_bar_thickness}px; /* Adjust as needed */
                    right: 3px;
                    z-index: 9999;
                    width: 100px; /* Adjust as needed */
                    height: 100px; /* Adjust as needed */
                    background-size: cover; /* Cover the div area with the image */
                }}"""
                css += f"""
                    #PokeIcon {{
                        position: fixed;
                        bottom: {8 + xp_bar_spacer + hp_bar_thickness}px; /* Adjust as needed */
                        right: 20%;
                        z-index: 9999;
                        width: 25px; /* Adjust as needed */
                        height: 25px; /* Adjust as needed */
                        background-size: cover; /* Cover the div area with the image */
                    }}
                    """

            if xp_bar_config is True:
                css += f"""
                #xp-bar {{
                width: {int((mainpokemon_xp / int(experience_for_next_lvl)) * 100)}%; /* Replace with the actual percentage */
                height: 10px;
                background: linear-gradient(to right, 
                                            rgba(0, 191, 255, 0.7), /* Light Blue with transparency */
                                            rgba(0, 191, 255, 0.7) 100%, /* Continue light blue to the percentage point */
                                            rgba(25, 25, 112, 0.7) 100%, /* Transition to dark blue background */
                                            rgba(25, 25, 112, 0.7)); /* Dark blue background with transparency */
                position: fixed;
                {xp_bar_location}: 0px;
                left: 0px;
                z-index: 9999;
                border-radius: 5px; /* Shorthand for all corners rounded */
                box-shadow: 0 0 10px rgba(0, 191, 255, 0.8), /* Light blue glow effect */
                            0 0 30px rgba(25, 25, 112, 1);  /* Dark blue glow effect */
                }}
                #next_lvl_text {{
                position: fixed;
                {xp_bar_location}: 13px;
                right: 15px;
                z-index: 9999;
                color: white;
                font-size: 10px;
                background-color: rgb(54,54,56, 0.7);
                text-align: right;
                }}
                #xp_text {{
                position: fixed;
                {xp_bar_location}: 13px;
                left: 15px;
                z-index: 9999;
                color: white;
                font-size: 10px;
                background-color: rgb(54,54,56, 0.7);
                text-align: right;
                }}
                """
            css += f"""
            @keyframes shake {{
                0% {{ transform: translateX(0) rotateZ(0); filter: drop-shadow(0 0 10px rgba(255, 0, 0, 0.5)); }}
                10% {{ transform: translateX(-10%) rotateZ(-5deg); }}
                20% {{ transform: translateX(10%) rotateZ(5deg); }}
                30% {{ transform: translateX(-10%) rotateZ(-5deg); }}
                40% {{ transform: translateX(10%) rotateZ(5deg); }}
                50% {{ transform: translateX(-10%) rotateZ(-5deg); }}
                60% {{ transform: translateX(10%) rotateZ(5deg); }}
                70% {{ transform: translateX(-10%) rotateZ(-5deg); }}
                80% {{ transform: translateX(10%) rotateZ(5deg); }}
                90% {{ transform: translateX(-10%) rotateZ(-5deg); }}
                100% {{ transform: translateX(100vw); filter: drop-shadow(0 0 10px rgba(255, 0, 0, 0.5)); }}
            }}
            """

            # background-image: url('{pokemon_image_file}'); Change to your image path */
            # Inject the CSS into the head of the HTML content
            web_content.head += f"<style>{css}</style>"
            # Inject a div element at the end of the body for the life bar
            if hp_bar_config is True:
                web_content.body += f'<div id="life-bar"></div>'
            if xp_bar_config is True:
                web_content.body += f'<div id="xp-bar"></div>'
                web_content.body += f'<div id="next_lvl_text">Next Level</div>'
                web_content.body += f'<div id="xp_text">XP</div>'
            # Inject a div element for the text display
            web_content.body += f'<div id="name-display">{name.capitalize()} LvL: {level}</div>'
            if hp > 0:
                web_content.body += f'{create_status_html(f"{battle_status}")}'
            else:
                web_content.body += f'{create_status_html(f"fainted")}'

            web_content.body += f'<div id="hp-display">HP: {hp}/{max_hp}</div>'
            # Inject a div element at the end of the body for the life bar
            image_base64 = get_image_as_base64(pokemon_image_file)
            web_content.body += f'<div id="PokeImage"><img src="data:image/png;base64,{image_base64}" alt="PokeImage style="animation: shake 0s ease;"></div>'
            if show_mainpkmn_in_reviewer > 0:
                image_base64_mypkmn = get_image_as_base64(main_pkmn_imagefile_path)
                web_content.body += f'<div id="MyPokeImage"><img src="data:image/png;base64,{image_base64_mypkmn}" alt="MyPokeImage" style="animation: shake 0s ease;"></div>'
                web_content.body += f'<div id="myname-display">{mainpokemon_name.capitalize()} LvL: {mainpokemon_level}</div>'
                web_content.body += f'<div id="myhp-display">HP: {mainpokemon_hp}/{mainpkmn_max_hp}</div>'
                # Inject a div element at the end of the body for the life bar
                if hp_bar_config is True:
                    web_content.body += f'<div id="mylife-bar"></div>'
            # Set the flag to True to indicate that the life bar has been injected
            if pokeball == True:
                icon_base_64 = get_image_as_base64(icon_path)
                web_content.body += f'<div id="PokeIcon"><img src="data:image/png;base64,{icon_base_64}" alt="PokeIcon"></div>'
            else:
                web_content.body += f'<div id="PokeIcon"></div>' 
            life_bar_injected = True
        return web_content

    def update_life_bar(reviewer, card, ease):
        global hp, name, id, frontdefault, battle_status, user_path_sprites, show_mainpkmn_in_reviewer, mainpokemon_hp, mainpokemon_id, mainpokemon_name, mainpokemon_level, mainpokemon_stats, mainpokemon_ev, mainpokemon_iv, mainpokemon_xp, xp_bar_config
        global mainpokemon_level, icon_path, empty_icon_path, seconds, myseconds, view_main_front, pokeball

        # Handle special variants (Shadow Mewtwo, etc.) - use base Pokemon for lookups
        lookup_name = "mewtwo" if name == "Shadow Mewtwo" else name.lower()

        # Validate enemy ID before building sprite paths
        enemy_num = search_pokedex(lookup_name, "num")
        is_valid, safe_id, warning = _ankimon_validate_enemy_id(enemy_num, name)
        if not is_valid:
            _ankimon_log("WARN", "AnkimonSprite", f"Invalid enemy ID in update_life_bar: {warning}, using fallback ID {safe_id}")
            enemy_num = safe_id

        pokeball = check_pokecoll_in_list(enemy_num)
        if reviewer_image_gif == False:
            pokemon_imagefile = f'{enemy_num}.png' #use for png files
            pokemon_image_file = os.path.join(frontdefault, pokemon_imagefile) #use for png files
            if show_mainpkmn_in_reviewer > 0:
                main_pkmn_imagefile = f'{mainpokemon_id}.png' #use for png files
                main_pkmn_imagefile_path = os.path.join(backdefault, main_pkmn_imagefile) #use for png files
        else:
            # Enemy Pokémon sprite (wild encounter)
            # Check for shadow variant first
            global current_wild_is_shiny, shiny_front_default, current_wild_variant
            if current_wild_variant == "shadow" and enemy_num == 150:
                pokemon_imagefile = f'{enemy_num}_shadow_front.gif'
                pokemon_image_file = os.path.join((user_path_sprites / "front_default_gif"), pokemon_imagefile)
                _ankimon_log("INFO", "ShadowMewtwo", f"Reviewer overlay using Shadow Mewtwo sprite: {pokemon_imagefile}")
            else:
                pokemon_imagefile = f'{enemy_num}.gif'

                # Check if this is a shiny encounter
                if current_wild_is_shiny:
                    # Try shiny sprite first
                    shiny_sprite_path = shiny_front_default / pokemon_imagefile
                    if shiny_sprite_path.exists():
                        pokemon_image_file = str(shiny_sprite_path)
                        # Debug log
                        try:
                            if developer_menu and developer_menu.menuAction().isVisible():
                                print(f"[Shiny] Reviewer enemy sprite: id={search_pokedex(lookup_name, 'num')} is_shiny=True path={pokemon_image_file}")
                        except:
                            pass
                    else:
                        # Fallback to normal sprite
                        pokemon_image_file = os.path.join((user_path_sprites / "front_default_gif"), pokemon_imagefile)
                else:
                    pokemon_image_file = os.path.join((user_path_sprites / "front_default_gif"), pokemon_imagefile)

            if show_mainpkmn_in_reviewer > 0:
                main_pkmn_imagefile = f'{mainpokemon_id}.gif'

                # Check if Pokemon is in Mega form (uses hard Key Stone gate)
                is_mega_active = _is_mega_active()

                # Check if player Pokemon is shiny
                player_is_shiny = False
                try:
                    if mainpokemon_path.is_file():
                        with open(mainpokemon_path, 'r') as file:
                            mainpkmn_data = json.load(file)
                            if isinstance(mainpkmn_data, list) and len(mainpkmn_data) > 0:
                                player_is_shiny = mainpkmn_data[0].get('is_shiny', False)
                except:
                    pass

                # Choose sprite directory based on Mega state and shiny status
                # Priority: Mega > Shiny > Normal
                if view_main_front == -1:
                    if is_mega_active:
                        gif_type = "front_mega_pokemon_gif"
                    elif player_is_shiny:
                        # Shiny front sprite (not commonly used but supported)
                        gif_type = "shiny_front_default"
                    else:
                        gif_type = "front_default_gif"
                else:
                    if is_mega_active:
                        gif_type = "back_mega_pokemon_gif"
                    elif player_is_shiny:
                        global shiny_back_default_gif
                        gif_type = "shiny_back_default_gif"
                    else:
                        gif_type = "back_default_gif"

                main_pkmn_imagefile_path = os.path.join((user_path_sprites / f"{gif_type}"), main_pkmn_imagefile)

                # Fallback to normal sprite if mega/shiny sprite doesn't exist
                if (is_mega_active or player_is_shiny) and not os.path.exists(main_pkmn_imagefile_path):
                    if view_main_front == -1:
                        gif_type = "front_default_gif"
                    else:
                        gif_type = "back_default_gif"
                    main_pkmn_imagefile_path = os.path.join((user_path_sprites / f"{gif_type}"), main_pkmn_imagefile)

                # Debug log for sprite selection
                if is_mega_active:
                    print(f"[Sprite] reviewer player id={mainpokemon_id} shiny={player_is_shiny} mega=True -> {gif_type}")
                elif player_is_shiny:
                    print(f"[Sprite] reviewer player id={mainpokemon_id} shiny=True mega=False -> {gif_type}")
                else:
                    print(f"[Sprite] reviewer player id={mainpokemon_id} shiny=False mega=False -> {gif_type}")
        if show_mainpkmn_in_reviewer > 0:
            mainpkmn_max_hp = calculate_hp(mainpokemon_stats["hp"], mainpokemon_level, mainpokemon_ev, mainpokemon_iv)
            mainpkmn_hp_percent = int((mainpokemon_hp / mainpkmn_max_hp) * 50)
            max_hp = calculate_max_hp_wildpokemon()
            pokemon_hp_percent = int((hp / max_hp) * 50)
            image_base64_mainpkmn = get_image_as_base64(main_pkmn_imagefile_path)
        else:    
            max_hp = calculate_max_hp_wildpokemon()
            pokemon_hp_percent = int((hp / max_hp) * 100)
        image_base64 = get_image_as_base64(pokemon_image_file)
        # Determine the color based on the percentage
        if hp < int(0.25 * max_hp):
            hp_color = "rgba(255, 0, 0, 0.7)"  # Red
        elif hp < int(0.5 * max_hp):
            hp_color = "rgba(255, 140, 0, 0.7)"  # Dark Orange
        elif hp < int(0.75 * max_hp):
            hp_color = "rgba(255, 255, 0, 0.7)"  # Yellow
        else:
            hp_color = "rgba(114, 230, 96, 0.7)"  # Green

        if show_mainpkmn_in_reviewer > 0:
            if mainpokemon_hp < int(0.25 * mainpkmn_max_hp):
                myhp_color = "rgba(255, 0, 0, 0.7)"  # Red
            elif mainpokemon_hp < int(0.5 * mainpkmn_max_hp):
                myhp_color = "rgba(255, 140, 0, 0.7)"  # Dark Orange
            elif mainpokemon_hp < int(0.75 * mainpkmn_max_hp):
                myhp_color = "rgba(255, 255, 0, 0.7)"  # Yellow
            else:
                myhp_color = "rgba(114, 230, 96, 0.7)"  # Green
        # Extract RGB values from the hex color code
        #hex_color = hp_color.lstrip('#')
        #rgb_values = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        status_html = ""
        if hp < 1:
            status_html = create_status_html('fainted')
        elif hp > 0:
            status_html = create_status_html(f"{battle_status}")

        # Refresh the reviewer content to apply the updated life bar
        reviewer.web.eval('document.getElementById("life-bar").style.width = "' + str(pokemon_hp_percent) + '%";')
        reviewer.web.eval('document.getElementById("life-bar").style.background = "linear-gradient(to right, ' + str(hp_color) + ', ' + str(hp_color) + ' ' + '100' + '%, ' + 'rgba(54, 54, 56, 0.7)' + '100' + '%, ' + 'rgba(54, 54, 56, 0.7)' + ')";')
        reviewer.web.eval('document.getElementById("life-bar").style.boxShadow = "0 0 10px ' + hp_color + ', 0 0 30px rgba(54, 54, 56, 1)";');
        if xp_bar_config is True:
            experience_for_next_lvl = find_experience_for_level(mainpokemon_growth_rate, mainpokemon_level)
            xp_bar_percent = int((mainpokemon_xp / int(experience_for_next_lvl)) * 100)
            reviewer.web.eval('document.getElementById("xp-bar").style.width = "' + str(xp_bar_percent) + '%";')
        name_display_text = f"{name.capitalize()} Lvl: {level}"
        hp_display_text = f"HP: {hp}/{max_hp}"
        reviewer.web.eval('document.getElementById("name-display").innerText = "' + name_display_text + '";')
        reviewer.web.eval('document.getElementById("hp-display").innerText = "' + hp_display_text + '";')
        new_html_content = f'<img src="data:image/png;base64,{image_base64}" alt="PokeImage" style="animation: shake {seconds}s ease;">'
        reviewer.web.eval(f'document.getElementById("PokeImage").innerHTML = `{new_html_content}`;')
        if pokeball == True:
            image_icon_path = get_image_as_base64(icon_path)
            pokeicon_html = f'<img src="data:image/png;base64,{image_icon_path}" alt="PokeIcon">'
        else:
            pokeicon_html = ''
        reviewer.web.eval(f'document.getElementById("PokeIcon").innerHTML = `{pokeicon_html}`;')
        reviewer.web.eval(f'document.getElementById("pokestatus").innerHTML = `{status_html}`;')
        if show_mainpkmn_in_reviewer > 0:
            new_html_content_mainpkmn = f'<img src="data:image/png;base64,{image_base64_mainpkmn}" alt="MyPokeImage" style="animation: shake {myseconds}s ease;">'
            main_name_display_text = f"{mainpokemon_name.capitalize()} Lvl: {mainpokemon_level}"
            main_hp_display_text = f"HP: {mainpokemon_hp}/{mainpkmn_max_hp}"
            reviewer.web.eval('document.getElementById("mylife-bar").style.width = "' + str(mainpkmn_hp_percent) + '%";')
            reviewer.web.eval('document.getElementById("mylife-bar").style.background = "linear-gradient(to right, ' + str(myhp_color) + ', ' + str(myhp_color) + ' ' + '100' + '%, ' + 'rgba(54, 54, 56, 0.7)' + '100' + '%, ' + 'rgba(54, 54, 56, 0.7)' + ')";')
            reviewer.web.eval('document.getElementById("mylife-bar").style.boxShadow = "0 0 10px ' + myhp_color + ', 0 0 30px rgba(54, 54, 56, 1)";');
            reviewer.web.eval(f'document.getElementById("MyPokeImage").innerHTML = `{new_html_content_mainpkmn}`;')
            reviewer.web.eval('document.getElementById("myname-display").innerText = "' + main_name_display_text + '";')
            reviewer.web.eval('document.getElementById("myhp-display").innerText = "' + main_hp_display_text + '";')

    # Register the functions for the hooks
    gui_hooks.reviewer_will_end.append(reviewer_reset_life_bar_inject)
    gui_hooks.webview_will_set_content.append(inject_life_bar)
    gui_hooks.reviewer_did_answer_card.append(update_life_bar)

def choose_pokemon(starter_name):
    global mypokemon_path, addon_dir, mainpokemon_path
    # Create a dictionary to store the Pokémon's data
    # add all new values like hp as max_hp, evolution_data, description and growth rate
    name = search_pokedex(starter_name, "name")
    id = search_pokedex(starter_name, "num")
    stats = search_pokedex(starter_name, "baseStats")
    abilities = search_pokedex(starter_name, "abilities")
    evos = search_pokedex(starter_name, "evos")
    gender = pick_random_gender(name.lower())
    numeric_abilities = {k: v for k, v in abilities.items() if k.isdigit()}
    # Check if there are numeric abilities
    if numeric_abilities:
        # Convert the filtered abilities dictionary values to a list
        abilities_list = list(numeric_abilities.values())
        # Select a random ability from the list
        ability = random.choice(abilities_list)
    else:
        # Set to "No Ability" if there are no numeric abilities
        ability = "No Ability"
    type = search_pokedex(starter_name, "types")
    name = search_pokedex(starter_name, "name")
    global pokeapi_db_path
    generation_file = "pokeapi_db.json"
    growth_rate = search_pokeapi_db_by_id(id, "growth_rate")
    base_experience = search_pokeapi_db_by_id(id, "base_experience")
    description= search_pokeapi_db_by_id(id, "description")
    level = 5
    attacks = get_random_moves_for_pokemon(starter_name, level)
    stats["xp"] = 0
    ev = {
        "hp": 0,
        "atk": 0,
        "def": 0,
        "spa": 0,
        "spd": 0,
        "spe": 0
    }
    caught_pokemon = {
        "name": name,
        "gender": gender,
        "level": level,
        "id": id,
        "ability": ability,
        "type": type,
        "stats": stats,
        "ev": ev,
        "iv": iv,
        "attacks": attacks,
        "base_experience": base_experience,
        "current_hp": calculate_hp(int(stats["hp"]), level, ev, iv),
        "growth_rate": growth_rate,
        "evos": evos
    }
    # Load existing Pokémon data if it exists
    if mypokemon_path.is_file():
        with open(mypokemon_path, "r") as json_file:
            caught_pokemon_data = json.load(json_file)
    else:
        caught_pokemon_data = []

    # Append the caught Pokémon's data to the list
    caught_pokemon_data.append(caught_pokemon)
    # Save the caught Pokémon's data to a JSON file
    with open(str(mainpokemon_path), "w") as json_file:
        json.dump(caught_pokemon_data, json_file, indent=2)
    mainpokemon_name, mainpokemon_id, mainpokemon_ability, mainpokemon_type, mainpokemon_stats, mainpokemon_attacks, mainpokemon_level, mainpokemon_base_experience, mainpokemon_xp, mainpokemon_hp, mainpokemon_current_hp, mainpokemon_growth_rate, mainpokemon_ev, mainpokemon_iv, mainpokemon_evolutions, mainpokemon_battle_stats, mainpokemon_gender, mainpokemon_nickname = mainpokemon_data()

    # Save the caught Pokémon's data to a JSON file
    with open(str(mypokemon_path), "w") as json_file:
        json.dump(caught_pokemon_data, json_file, indent=2)

    showInfo(f"{name.capitalize()} has been chosen as Starter Pokemon !")

    starter_window.display_chosen_starter_pokemon(starter_name)

def save_outside_pokemon(pokemon_name, pokemon_id):
    global mypokemon_path, addon_dir, mainpokemon_path
    # Create a dictionary to store the Pokémon's data
    # add all new values like hp as max_hp, evolution_data, description and growth rate
    name = search_pokedex_by_id(pokemon_id)
    id = pokemon_id
    stats = search_pokedex(name, "baseStats")
    abilities = search_pokedex(name, "abilities")
    evos = search_pokedex(name, "evos")
    gender = pick_random_gender(name.lower())
    numeric_abilities = {k: v for k, v in abilities.items() if k.isdigit()}
    # Check if there are numeric abilities
    if numeric_abilities:
        # Convert the filtered abilities dictionary values to a list
        abilities_list = list(numeric_abilities.values())
        # Select a random ability from the list
        ability = random.choice(abilities_list)
    else:
        # Set to "No Ability" if there are no numeric abilities
        ability = "No Ability"
    type = search_pokedex(name, "types")
    name = search_pokedex(name, "name")
    global pokeapi_db_path
    generation_file = "pokeapi_db.json"
    growth_rate = search_pokeapi_db_by_id(id, "growth_rate")
    base_experience = search_pokeapi_db_by_id(id, "base_experience")
    description= search_pokeapi_db_by_id(id, "description")
    level = 5
    attacks = get_random_moves_for_pokemon(name, level)
    stats["xp"] = 0
    ev = {
        "hp": 0,
        "atk": 0,
        "def": 0,
        "spa": 0,
        "spd": 0,
        "spe": 0
    }
    caught_pokemon = {
        "name": name,
        "gender": gender,
        "level": level,
        "id": id,
        "ability": ability,
        "type": type,
        "stats": stats,
        "ev": ev,
        "iv": iv,
        "attacks": attacks,
        "base_experience": base_experience,
        "current_hp": calculate_hp(int(stats["hp"]), level, ev, iv),
        "growth_rate": growth_rate,
        "evos": evos
    }
    # Load existing Pokémon data if it exists
    if mypokemon_path.is_file():
        with open(mypokemon_path, "r") as json_file:
            caught_pokemon_data = json.load(json_file)
    else:
        caught_pokemon_data = []

    # Append the caught Pokémon's data to the list
    caught_pokemon_data.append(caught_pokemon)
    # Save the caught Pokémon's data to a JSON file
    with open(str(mypokemon_path), "w") as json_file:
        json.dump(caught_pokemon_data, json_file, indent=2)

def export_to_pkmn_showdown():
    global mainpokemon_level, mainpokemon_type, mainpokemon_name, mainpokemon_stats, mainpokemon_attacks, mainpokemon_ability, mainpokemon_iv, mainpokemon_ev, mainpokemon_gender
    # Create a main window
    window = QDialog(mw)
    window.setWindowTitle("Export Pokemon to Pkmn Showdown")
    for stat, value in mainpokemon_ev.items():
        if value == 0:
            mainpokemon_ev[stat] += 1
    # Format the Pokemon info
    #pokemon_info = f"{mainpokemon_name}\nAbility: {mainpokemon_ability}\nLevel: {mainpokemon_level}\nType: {mainpokemon_type}\nEVs: {mainpokemon_stats['hp']} HP / {mainpokemon_stats['attack']} Atk / {mainpokemon_stats['defense']} Def / {mainpokemon_stats['special-attack']} SpA / {mainpokemon_stats['special-defense']} SpD / {mainpokemon_stats['speed']} Spe\n IVs: {mainpokemon_iv["hp"]} HP / {mainpokemon_iv["attack"]} Atk / {mainpokemon_iv["defense"]} Def / {mainpokemon_iv["special-attack"]} SpA / {mainpokemon_iv["special-defense"]} SpD / {mainpokemon_iv["speed"]} Spe \n- {mainpokemon_attacks[0]}\n- {mainpokemon_attacks[1]}\n- {mainpokemon_attacks[2]}\n- {mainpokemon_attacks[3]}"
    pokemon_info = "{} ({})\nAbility: {}\nLevel: {}\nType: {}\nEVs: {} HP / {} Atk / {} Def / {} SpA / {} SpD / {} Spe\n IVs: {} HP / {} Atk / {} Def / {} SpA / {} SpD / {} Spe ".format(
        mainpokemon_name,
        mainpokemon_gender,
        mainpokemon_ability,
        mainpokemon_level,
        mainpokemon_type,
        mainpokemon_ev["hp"],
        mainpokemon_ev["atk"],
        mainpokemon_ev["def"],
        mainpokemon_ev["spa"],
        mainpokemon_ev["spd"],
        mainpokemon_ev["spe"],
        mainpokemon_iv["hp"],
        mainpokemon_iv["atk"],
        mainpokemon_iv["def"],
        mainpokemon_iv["spa"],
        mainpokemon_iv["spd"],
        mainpokemon_iv["spe"]
    )
    for attack in mainpokemon_attacks:
        pokemon_info += f"\n- {attack}"
    # Information label
    info = "Pokemon Infos have been Copied to your Clipboard! \nNow simply paste this text into Teambuilder in PokemonShowdown. \nNote: Fight in the [Gen 9] Anything Goes - Battle Mode"
    info += f"\n Your Pokemon is considered Tier: {search_pokedex(mainpokemon_name.lower(), 'tier')} in PokemonShowdown"
    # Create labels to display the text
    label = QLabel(pokemon_info)
    info_label = QLabel(info)

    # Align labels
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Align center
    info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Align center

    # Create a layout and add the labels
    layout = QVBoxLayout()
    layout.addWidget(info_label)
    layout.addWidget(label)

    # Set the layout for the main window
    window.setLayout(layout)

    # Copy text to clipboard in Anki
    mw.app.clipboard().setText(pokemon_info)

    # Show the window
    window.show()

def save_error_code(error_code):
    error_fix_msg = ""
    try:
        # Find the position of the phrase "can't be transferred from Gen"
        index = error_code.find("can't be transferred from Gen")

        # Extract the substring starting from this position
        relevant_text = error_code[index:]

        # Find the first number in the extracted text (assuming it's the generation number)
        generation_number = int(''.join(filter(str.isdigit, relevant_text)))

        # Show the generation number
        error_fix_msg += (f"\n Please use Gen {str(generation_number)[0]} or lower")

        index = error_code.find("can't be transferred from Gen")

        # Extract the substring starting from this position
        relevant_text = error_code[index:]

        # Find the first number in the extracted text (assuming it's the generation number)
        generation_number = int(''.join(filter(str.isdigit, relevant_text)))

        error_fix_msg += (f"\n Please use Gen {str(generation_number)[0]} or lower")

    except Exception as e:
        showInfo(f"An error occurred: {e}")

    showInfo(f"{error_fix_msg}")

def export_all_pkmn_showdown():
    # Create a main window
    export_window = QDialog()
    #export_window.setWindowTitle("Export Pokemon to Pkmn Showdown")

    # Information label
    info = "Pokemon Infos have been Copied to your Clipboard! \nNow simply paste this text into Teambuilder in PokemonShowdown. \nNote: Fight in the [Gen 7] Anything Goes - Battle Mode"
    info_label = QLabel(info)

    # Get all pokemon data
    global mypokemon_path
    pokemon_info_complete_text = ""
    try:
        with (open(mypokemon_path, "r") as json_file):
            captured_pokemon_data = json.load(json_file)

            # Check if there are any captured Pokémon
            if captured_pokemon_data:
                # Counter for tracking the column position
                column = 0
                row = 0
                for pokemon in captured_pokemon_data:
                    pokemon_name = pokemon['name']
                    pokemon_level = pokemon['level']
                    pokemon_ability = pokemon['ability']
                    pokemon_type = pokemon['type']
                    pokemon_type_text = pokemon_type[0].capitalize()
                    if len(pokemon_type) > 1:
                        pokemon_type_text = ""
                        pokemon_type_text += f"{pokemon_type[0].capitalize()}"
                        pokemon_type_text += f" {pokemon_type[1].capitalize()}"
                    pokemon_stats = pokemon['stats']
                    pokemon_hp = pokemon_stats["hp"]
                    pokemon_attacks = pokemon['attacks']
                    pokemon_ev = pokemon['ev']
                    pokemon_iv = pokemon['iv']

                    pokemon_info = "\n{} \nAbility: {}\nLevel: {}\nType: {}\nEVs: {} HP / {} Atk / {} Def / {} SpA / {} SpD / {} Spe\n IVs: {} HP / {} Atk / {} Def / {} SpA / {} SpD / {} Spe \n".format(
                        pokemon_name,
                        pokemon_ability.capitalize(),
                        pokemon_level,
                        pokemon_type_text,
                        pokemon_stats["hp"],
                        pokemon_stats["atk"],
                        pokemon_stats["def"],
                        pokemon_stats["spa"],
                        pokemon_stats["spd"],
                        pokemon_stats["spe"],
                        pokemon_iv["hp"],
                        pokemon_iv["atk"],
                        pokemon_iv["def"],
                        pokemon_iv["spa"],
                        pokemon_iv["spd"],
                        pokemon_iv["spe"]
                    )
                    for attack in pokemon_attacks:
                        pokemon_info += f"- {attack}\n"
                    pokemon_info_complete_text += pokemon_info

                    # Create labels to display the text
                    #label = QLabel(pokemon_info_complete_text)
                    # Align labels
                    #label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Align center
                    info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Align center

                    # Create an input field for error code
                    error_code_input = QLineEdit()
                    error_code_input.setPlaceholderText("Enter Error Code")

                    # Create a button to save the input
                    save_button = QPushButton("Fix Pokemon Export Code")

                    # Create a layout and add the labels, input field, and button
                    layout = QVBoxLayout()
                    layout.addWidget(info_label)
                    #layout.addWidget(label)
                    layout.addWidget(error_code_input)
                    layout.addWidget(save_button)

                    # Copy text to clipboard in Anki
                    mw.app.clipboard().setText(pokemon_info_complete_text)

        save_button.clicked.connect(lambda: save_error_code(error_code_input.text()))

        # Set the layout for the main window
        export_window.setLayout(layout)

        export_window.exec()
    except Exception as e:
        showInfo(f"An error occurred: {e}")

def calc_exp_gain(base_experience, w_pkmn_level):
    exp = int((base_experience * w_pkmn_level) / 7)
    return exp

# Define the function to open the Pokémon Showdown Team Builder
def open_team_builder():
    # Specify the URL of the Pokémon Showdown Team Builder
    team_builder_url = "https://play.pokemonshowdown.com/teambuilder"

    # Open the Team Builder in the default web browser
    QDesktopServices.openUrl(QUrl(team_builder_url))

def rate_addon_url():
    # Specify the URL of the Pokémon Showdown Team Builder
    rating_url = "https://ankiweb.net/shared/review/1908235722"

    # Open the Team Builder in the default web browser
    QDesktopServices.openUrl(QUrl(rating_url))

#def no_hp():
    #if main_window is not None:
        #main_window.death_window()
test = 1
video = False
pkmn_window = False #if fighting window open
first_start = False

# Helper function for bottom-anchored sprite positioning
def bottom_anchor_pos(ground_x, ground_y, sprite_w, sprite_h, anchor="center"):
    """
    Calculate draw position for bottom-anchored sprites.

    Args:
        ground_x: X coordinate of the ground point (baseline)
        ground_y: Y coordinate of the ground point (baseline)
        sprite_w: Width of the sprite
        sprite_h: Height of the sprite
        anchor: "center" means x is center of sprite, otherwise left-aligned

    Returns:
        Tuple of (draw_x, draw_y) for top-left corner of sprite
    """
    if anchor == "center":
        draw_x = int(ground_x - sprite_w / 2)
    else:
        draw_x = int(ground_x)
    draw_y = int(ground_y - sprite_h)   # bottom anchored to ground
    return draw_x, draw_y


class PokemonPlacementTool(QDialog):
    """Visual tool for positioning Pokemon sprites and getting exact coordinates"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pokémon Placement Tool")
        self.setFixedSize(800, 600)

        # Sprite positioning data
        self.player_x = 96
        self.player_y = 184
        self.player_size = 80
        self.enemy_x = 420
        self.enemy_y = 112
        self.enemy_size = 80

        # Fainted text positioning data (load from config)
        conf = _ankimon_get_col_conf()
        self.fainted_x = int(conf.get("ankimon_fainted_text_x", 270)) if conf else 270
        self.fainted_y = int(conf.get("ankimon_fainted_text_y", 100)) if conf else 100

        # Separate positions for each text element
        self.leader_name_x = int(conf.get("ankimon_gym_leader_name_x", 270)) if conf else 270
        self.leader_name_y = int(conf.get("ankimon_gym_leader_name_y", 150)) if conf else 150
        self.remaining_text_x = int(conf.get("ankimon_gym_remaining_text_x", 270)) if conf else 270
        self.remaining_text_y = int(conf.get("ankimon_gym_remaining_text_y", 180)) if conf else 180
        self.complete_text_x = int(conf.get("ankimon_gym_complete_text_x", 270)) if conf else 270
        self.complete_text_y = int(conf.get("ankimon_gym_complete_text_y", 150)) if conf else 150

        # Dragging state
        self.dragging_player = False
        self.dragging_enemy = False
        self.dragging_fainted = False
        self.dragging_leader_name = False
        self.dragging_remaining_text = False
        self.dragging_complete_text = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Get current player Pokemon for display
        try:
            self.player_pokemon_id = mw.col.get_config("mainpokemon")
            if not self.player_pokemon_id:
                self.player_pokemon_id = 6  # Charizard as fallback
        except:
            self.player_pokemon_id = 6  # Charizard as fallback
        self.enemy_pokemon_id = 25  # Pikachu as default example

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Mode selector tabs
        self.tab_widget = QTabWidget()

        # Tab 1: Sprite positioning
        sprite_tab = QWidget()
        sprite_layout = QVBoxLayout()
        sprite_tab.setLayout(sprite_layout)

        info_label = QLabel("Drag sprites to position them. Use +/- to adjust size.\nCoordinates shown below are for copying.")
        info_label.setWordWrap(True)
        sprite_layout.addWidget(info_label)

        # Battle scene display
        self.scene_label = QLabel()
        self.scene_label.setFixedSize(555, 258)
        self.scene_label.setStyleSheet("border: 2px solid black;")
        self.scene_label.mousePressEvent = self.mouse_press
        self.scene_label.mouseMoveEvent = self.mouse_move
        self.scene_label.mouseReleaseEvent = self.mouse_release
        sprite_layout.addWidget(self.scene_label)

        # Control buttons
        controls_layout = QHBoxLayout()

        # Player controls
        player_group = QLabel("PLAYER:")
        controls_layout.addWidget(player_group)

        player_minus_btn = QPushButton("-")
        player_minus_btn.clicked.connect(lambda: self.adjust_size("player", -10))
        controls_layout.addWidget(player_minus_btn)

        player_plus_btn = QPushButton("+")
        player_plus_btn.clicked.connect(lambda: self.adjust_size("player", 10))
        controls_layout.addWidget(player_plus_btn)

        controls_layout.addStretch()

        # Enemy controls
        enemy_group = QLabel("ENEMY:")
        controls_layout.addWidget(enemy_group)

        enemy_minus_btn = QPushButton("-")
        enemy_minus_btn.clicked.connect(lambda: self.adjust_size("enemy", -10))
        controls_layout.addWidget(enemy_minus_btn)

        enemy_plus_btn = QPushButton("+")
        enemy_plus_btn.clicked.connect(lambda: self.adjust_size("enemy", 10))
        controls_layout.addWidget(enemy_plus_btn)

        sprite_layout.addLayout(controls_layout)

        # Coordinates display
        self.coords_text = QTextEdit()
        self.coords_text.setReadOnly(True)
        self.coords_text.setMaximumHeight(150)
        sprite_layout.addWidget(self.coords_text)

        self.tab_widget.addTab(sprite_tab, "Battle Sprites")

        # Tab 2: Fainted text positioning
        fainted_tab = QWidget()
        fainted_layout = QVBoxLayout()
        fainted_tab.setLayout(fainted_layout)

        fainted_info = QLabel("Drag each text element independently (click near any text to drag it):\n• RED 'FAINTED!' • BLUE Leader Name • GREEN Remaining Count • PURPLE Complete Message\nClick 'Save Position' to apply to all gym battles.")
        fainted_info.setWordWrap(True)
        fainted_layout.addWidget(fainted_info)

        # Fainted screen preview
        self.fainted_scene_label = QLabel()
        self.fainted_scene_label.setFixedSize(555, 258)
        self.fainted_scene_label.setStyleSheet("border: 2px solid black;")
        self.fainted_scene_label.mousePressEvent = self.fainted_mouse_press
        self.fainted_scene_label.mouseMoveEvent = self.fainted_mouse_move
        self.fainted_scene_label.mouseReleaseEvent = self.fainted_mouse_release
        fainted_layout.addWidget(self.fainted_scene_label)

        # Fainted text controls
        fainted_controls = QHBoxLayout()
        fainted_controls.addWidget(QLabel("Position:"))

        reset_fainted_btn = QPushButton("Reset to Default")
        reset_fainted_btn.clicked.connect(self.reset_fainted_position)
        fainted_controls.addWidget(reset_fainted_btn)

        fainted_controls.addStretch()

        save_fainted_btn = QPushButton("✓ Save Position")
        save_fainted_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px 15px;")
        save_fainted_btn.clicked.connect(self.save_fainted_position)
        fainted_controls.addWidget(save_fainted_btn)

        fainted_layout.addLayout(fainted_controls)

        # Fainted coordinates display
        self.fainted_coords_text = QTextEdit()
        self.fainted_coords_text.setReadOnly(True)
        self.fainted_coords_text.setMaximumHeight(100)
        fainted_layout.addWidget(self.fainted_coords_text)

        self.tab_widget.addTab(fainted_tab, "Fainted Text")

        # Add tabs to main layout
        layout.addWidget(self.tab_widget)

        # Close button (outside tabs)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

        # Connect tab change signal to update the appropriate scene
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        self.update_scene()

    def adjust_size(self, sprite_type, delta):
        """Adjust sprite size"""
        if sprite_type == "player":
            self.player_size = max(20, min(200, self.player_size + delta))
        else:
            self.enemy_size = max(20, min(200, self.enemy_size + delta))
        self.update_scene()

    def mouse_press(self, event):
        """Handle mouse press to start dragging"""
        x, y = event.pos().x(), event.pos().y()

        # Check if clicking on player sprite
        player_draw_x = self.player_x - self.player_size // 2
        player_draw_y = self.player_y - self.player_size
        if (player_draw_x <= x <= player_draw_x + self.player_size and
            player_draw_y <= y <= player_draw_y + self.player_size):
            self.dragging_player = True
            self.drag_offset_x = x - self.player_x
            self.drag_offset_y = y - self.player_y
            return

        # Check if clicking on enemy sprite
        enemy_draw_x = self.enemy_x - self.enemy_size // 2
        enemy_draw_y = self.enemy_y - self.enemy_size
        if (enemy_draw_x <= x <= enemy_draw_x + self.enemy_size and
            enemy_draw_y <= y <= enemy_draw_y + self.enemy_size):
            self.dragging_enemy = True
            self.drag_offset_x = x - self.enemy_x
            self.drag_offset_y = y - self.enemy_y

    def mouse_move(self, event):
        """Handle mouse move for dragging"""
        if not (self.dragging_player or self.dragging_enemy):
            return

        x = event.pos().x() - self.drag_offset_x
        y = event.pos().y() - self.drag_offset_y

        # Keep within bounds
        x = max(0, min(555, x))
        y = max(0, min(258, y))

        if self.dragging_player:
            self.player_x = x
            self.player_y = y
        elif self.dragging_enemy:
            self.enemy_x = x
            self.enemy_y = y

        self.update_scene()

    def mouse_release(self, event):
        """Handle mouse release to stop dragging"""
        self.dragging_player = False
        self.dragging_enemy = False

    def update_scene(self):
        """Redraw the battle scene with current positions"""
        global addon_dir

        # Create canvas
        canvas = QPixmap(555, 258)
        canvas.fill(QColor(200, 200, 200))
        painter = QPainter(canvas)

        # Draw battle background if available
        bg_path = addon_dir / "user_files" / "addon_sprites" / "background_battle.png"
        if bg_path.exists():
            bg = QPixmap(str(bg_path))
            painter.drawPixmap(0, 0, bg)

        # Draw grid lines for reference
        painter.setPen(QPen(QColor(100, 100, 100, 100), 1, Qt.PenStyle.DashLine))
        for i in range(0, 555, 50):
            painter.drawLine(i, 0, i, 258)
        for i in range(0, 258, 50):
            painter.drawLine(0, i, 555, i)

        # Draw sprites
        sprite_folder = addon_dir / "user_files" / "sprites"
        frontdefault = sprite_folder / "front_default"
        backdefault = sprite_folder / "back_default"

        # Draw enemy Pokemon (front sprite)
        enemy_path = frontdefault / f"{self.enemy_pokemon_id}.png"
        if enemy_path.exists():
            enemy_pixmap = QPixmap(str(enemy_path))
            enemy_pixmap = enemy_pixmap.scaled(
                self.enemy_size, self.enemy_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            enemy_draw_x = self.enemy_x - enemy_pixmap.width() // 2
            enemy_draw_y = self.enemy_y - enemy_pixmap.height()
            painter.drawPixmap(enemy_draw_x, enemy_draw_y, enemy_pixmap)

            # Draw crosshair at ground point
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawLine(self.enemy_x - 10, self.enemy_y, self.enemy_x + 10, self.enemy_y)
            painter.drawLine(self.enemy_x, self.enemy_y - 10, self.enemy_x, self.enemy_y + 10)

        # Draw player Pokemon (back sprite)
        player_path = backdefault / f"{self.player_pokemon_id}.png"
        if player_path.exists():
            player_pixmap = QPixmap(str(player_path))
            player_pixmap = player_pixmap.scaled(
                self.player_size, self.player_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            player_draw_x = self.player_x - player_pixmap.width() // 2
            player_draw_y = self.player_y - player_pixmap.height()
            painter.drawPixmap(player_draw_x, player_draw_y, player_pixmap)

            # Draw crosshair at ground point
            painter.setPen(QPen(QColor(0, 0, 255), 2))
            painter.drawLine(self.player_x - 10, self.player_y, self.player_x + 10, self.player_y)
            painter.drawLine(self.player_x, self.player_y - 10, self.player_x, self.player_y + 10)

        painter.end()
        self.scene_label.setPixmap(canvas)

        # Update coordinates display
        coords_info = f"""CURRENT POSITIONING DATA (copy this info):

PLAYER Pokemon (blue crosshair):
  Ground Point: ({self.player_x}, {self.player_y})
  Size: {self.player_size}px

ENEMY Pokemon (red crosshair):
  Ground Point: ({self.enemy_x}, {self.enemy_y})
  Size: {self.enemy_size}px

CODE TO USE:
  # Player ground point
  PLAYER_GROUND_X, PLAYER_GROUND_Y = {self.player_x}, {self.player_y}

  # Enemy ground point
  ENEMY_GROUND_X, ENEMY_GROUND_Y = {self.enemy_x}, {self.enemy_y}

  # Sizes (if dynamic sizing based on Pokemon)
  player_size = {self.player_size}
  enemy_size = {self.enemy_size}
"""
        self.coords_text.setText(coords_info)

    def on_tab_changed(self, index):
        """Handle tab change to update the appropriate scene"""
        if index == 0:
            self.update_scene()
        elif index == 1:
            self.update_fainted_scene()

    def fainted_mouse_press(self, event):
        """Handle mouse press for fainted text dragging - supports dragging each element separately"""
        x, y = event.pos().x(), event.pos().y()

        # Check which text element is being clicked (priority: fainted > leader > remaining > complete)
        if abs(x - self.fainted_x) < 100 and abs(y - self.fainted_y) < 25:
            self.dragging_fainted = True
            self.drag_offset_x = x - self.fainted_x
            self.drag_offset_y = y - self.fainted_y
        elif abs(x - self.leader_name_x) < 100 and abs(y - self.leader_name_y) < 25:
            self.dragging_leader_name = True
            self.drag_offset_x = x - self.leader_name_x
            self.drag_offset_y = y - self.leader_name_y
        elif abs(x - self.remaining_text_x) < 100 and abs(y - self.remaining_text_y) < 25:
            self.dragging_remaining_text = True
            self.drag_offset_x = x - self.remaining_text_x
            self.drag_offset_y = y - self.remaining_text_y
        elif abs(x - self.complete_text_x) < 100 and abs(y - self.complete_text_y) < 25:
            self.dragging_complete_text = True
            self.drag_offset_x = x - self.complete_text_x
            self.drag_offset_y = y - self.complete_text_y

    def fainted_mouse_move(self, event):
        """Handle mouse move for fainted text dragging"""
        if not (self.dragging_fainted or self.dragging_leader_name or self.dragging_remaining_text or self.dragging_complete_text):
            return

        x = event.pos().x() - self.drag_offset_x
        y = event.pos().y() - self.drag_offset_y

        # Keep within bounds
        x = max(50, min(505, x))
        y = max(30, min(228, y))

        if self.dragging_fainted:
            self.fainted_x = x
            self.fainted_y = y
        elif self.dragging_leader_name:
            self.leader_name_x = x
            self.leader_name_y = y
        elif self.dragging_remaining_text:
            self.remaining_text_x = x
            self.remaining_text_y = y
        elif self.dragging_complete_text:
            self.complete_text_x = x
            self.complete_text_y = y

        self.update_fainted_scene()

    def fainted_mouse_release(self, event):
        """Handle mouse release for fainted text dragging"""
        self.dragging_fainted = False
        self.dragging_leader_name = False
        self.dragging_remaining_text = False
        self.dragging_complete_text = False

    def reset_fainted_position(self):
        """Reset all fainted text elements to default positions"""
        self.fainted_x = 270
        self.fainted_y = 100
        self.leader_name_x = 270
        self.leader_name_y = 150
        self.remaining_text_x = 270
        self.remaining_text_y = 180
        self.complete_text_x = 270
        self.complete_text_y = 150
        self.update_fainted_scene()
        tooltipWithColour("All text positions reset to default", "#888888")

    def save_fainted_position(self):
        """Save all fainted text positions to config"""
        try:
            conf = _ankimon_get_col_conf()
            if conf:
                # Save all text element positions
                conf["ankimon_fainted_text_x"] = self.fainted_x
                conf["ankimon_fainted_text_y"] = self.fainted_y
                conf["ankimon_gym_leader_name_x"] = self.leader_name_x
                conf["ankimon_gym_leader_name_y"] = self.leader_name_y
                conf["ankimon_gym_remaining_text_x"] = self.remaining_text_x
                conf["ankimon_gym_remaining_text_y"] = self.remaining_text_y
                conf["ankimon_gym_complete_text_x"] = self.complete_text_x
                conf["ankimon_gym_complete_text_y"] = self.complete_text_y
                mw.col.setMod()
                tooltipWithColour("All text positions saved!", "#00FF00")
                print(f"[PlacementTool] Saved text positions:")
                print(f"  FAINTED: ({self.fainted_x}, {self.fainted_y})")
                print(f"  Leader Name: ({self.leader_name_x}, {self.leader_name_y})")
                print(f"  Remaining: ({self.remaining_text_x}, {self.remaining_text_y})")
                print(f"  Complete: ({self.complete_text_x}, {self.complete_text_y})")
            else:
                tooltipWithColour("Failed to save: Config not available", "#FF0000")
        except Exception as e:
            tooltipWithColour(f"Error saving position: {e}", "#FF0000")
            print(f"[PlacementTool] Error saving fainted position: {e}")

    def update_fainted_scene(self):
        """Redraw the fainted screen preview with current text position"""
        global addon_dir

        # Create canvas matching the pokedex background size
        canvas = QPixmap(555, 258)
        canvas.fill(QColor(255, 255, 255))
        painter = QPainter(canvas)

        # Draw pokedex background if available
        pokedex_bg_path = addon_dir / "addon_sprites" / "mypokemon" / "pokeball_icon.png"
        if pokedex_bg_path.exists():
            bg = QPixmap(str(pokedex_bg_path))
            bg = bg.scaled(555, 258, Qt.AspectRatioMode.KeepAspectRatio)
            painter.drawPixmap(0, 0, bg)
        else:
            # Fallback: draw a simple background
            painter.fillRect(0, 0, 555, 258, QColor(240, 240, 240))

        # Draw a sample Pokemon sprite (Pikachu for example)
        sprite_folder = addon_dir / "user_files" / "sprites" / "front_default"
        pikachu_path = sprite_folder / "25.png"
        if pikachu_path.exists():
            pokemon_pixmap = QPixmap(str(pikachu_path))
            pokemon_pixmap = pokemon_pixmap.scaled(230, 230, Qt.AspectRatioMode.KeepAspectRatio)
            painter.drawPixmap(15, 15, pokemon_pixmap)

        # Draw the "FAINTED!" text at current position
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 0, 0))
        painter.drawText(self.fainted_x, self.fainted_y, "FAINTED!")

        # Draw crosshair at FAINTED text position (red)
        painter.setPen(QPen(QColor(255, 0, 0, 150), 2))
        painter.drawLine(self.fainted_x - 15, self.fainted_y, self.fainted_x + 15, self.fainted_y)
        painter.drawLine(self.fainted_x, self.fainted_y - 15, self.fainted_x, self.fainted_y + 15)

        # Draw leader name text with independent position (blue crosshair)
        font.setPointSize(16)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(self.leader_name_x, self.leader_name_y, "Maylene")

        # Draw crosshair for leader name (blue)
        painter.setPen(QPen(QColor(0, 0, 255, 150), 2))
        painter.drawLine(self.leader_name_x - 15, self.leader_name_y, self.leader_name_x + 15, self.leader_name_y)
        painter.drawLine(self.leader_name_x, self.leader_name_y - 15, self.leader_name_x, self.leader_name_y + 15)

        # Draw remaining text with independent position (green crosshair)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(self.remaining_text_x, self.remaining_text_y, "1 Pokémon left")

        # Draw crosshair for remaining text (green)
        painter.setPen(QPen(QColor(0, 255, 0, 150), 2))
        painter.drawLine(self.remaining_text_x - 15, self.remaining_text_y, self.remaining_text_x + 15, self.remaining_text_y)
        painter.drawLine(self.remaining_text_x, self.remaining_text_y - 15, self.remaining_text_x, self.remaining_text_y + 15)

        # Draw complete text with independent position (purple crosshair) - overlayed but not visible unless testing
        painter.setPen(QColor(0, 0, 0, 100))  # Semi-transparent
        painter.drawText(self.complete_text_x, self.complete_text_y, "Gym Complete!")

        # Draw crosshair for complete text (purple)
        painter.setPen(QPen(QColor(128, 0, 128, 100), 2))
        painter.drawLine(self.complete_text_x - 15, self.complete_text_y, self.complete_text_x + 15, self.complete_text_y)
        painter.drawLine(self.complete_text_x, self.complete_text_y - 15, self.complete_text_x, self.complete_text_y + 15)

        painter.end()
        self.fainted_scene_label.setPixmap(canvas)

        # Update coordinates display
        coords_info = f"""INDEPENDENT TEXT POSITIONS (drag each separately):

FAINTED!: ({self.fainted_x}, {self.fainted_y}) [RED crosshair]
Leader Name: ({self.leader_name_x}, {self.leader_name_y}) [BLUE crosshair]
Remaining: ({self.remaining_text_x}, {self.remaining_text_y}) [GREEN crosshair]
Complete: ({self.complete_text_x}, {self.complete_text_y}) [PURPLE crosshair]

Click "Save Position" to apply to all gym battles.
Each text element can be positioned independently!
"""
        self.fainted_coords_text.setText(coords_info)


# Global instance
_placement_tool = None

def show_placement_tool():
    """Show the Pokemon Placement Tool"""
    global _placement_tool
    if _placement_tool is None:
        _placement_tool = PokemonPlacementTool()
    _placement_tool.show()
    _placement_tool.raise_()
    _placement_tool.activateWindow()

def show_progression_stats():
    """Show the Progression Stats window"""
    try:
        stats = _load_progression_stats()

        # Create dialog
        dlg = QDialog(mw)
        dlg.setWindowTitle("Progression Stats")
        dlg.setMinimumWidth(500)
        dlg.setMinimumHeight(600)

        layout = QVBoxLayout()
        dlg.setLayout(layout)

        # Title
        title = QLabel("PROGRESSION STATS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #FFD700; padding: 10px;")
        layout.addWidget(title)

        # Create scroll area for stats
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_content.setLayout(scroll_layout)

        # Lifetime Stats Section
        lifetime_label = QLabel("LIFETIME STATS")
        lifetime_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #00FFFF; padding: 5px;")
        scroll_layout.addWidget(lifetime_label)

        lifetime = stats.get("lifetime", {})
        lifetime_stats = [
            ("Total Cards Reviewed", lifetime.get("total_cards_reviewed", 0)),
            ("Total Battles Won", lifetime.get("total_battles_won", 0)),
            ("├─ Wild Battles", lifetime.get("total_wild_battles", 0)),
            ("├─ Trainer Battles", lifetime.get("total_trainer_battles", 0)),
            ("├─ Gym Battles", lifetime.get("total_gym_battles", 0)),
            ("├─ Elite Four Battles", lifetime.get("total_elite_four_battles", 0)),
            ("└─ Champion Battles", lifetime.get("total_champion_battles", 0)),
            ("Pokemon Caught", lifetime.get("total_pokemon_caught", 0)),
            ("Pokemon Evolved", lifetime.get("total_pokemon_evolved", 0)),
            ("Badges Earned", lifetime.get("total_badges_earned", 0)),
            ("Mega Evolutions", lifetime.get("total_mega_evolutions", 0)),
            ("Current Round", lifetime.get("current_round", 1)),
            ("Highest Level Reached", lifetime.get("highest_level_reached", 1)),
            ("Legendary Encounters", lifetime.get("legendary_encounters", 0)),
            ("Primal Battles Won", lifetime.get("primal_battles_won", 0)),
        ]

        for stat_name, stat_value in lifetime_stats:
            stat_label = QLabel(f"{stat_name}: {stat_value:,}")
            if stat_name.startswith("├") or stat_name.startswith("└"):
                stat_label.setStyleSheet("padding-left: 20px; font-size: 11px;")
            else:
                stat_label.setStyleSheet("font-size: 12px; padding: 2px;")
            scroll_layout.addWidget(stat_label)

        # Current Round Section
        scroll_layout.addSpacing(15)
        current_round_label = QLabel(f"CURRENT ROUND (Round {stats['lifetime'].get('current_round', 1)})")
        current_round_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF6B6B; padding: 5px;")
        scroll_layout.addWidget(current_round_label)

        current = stats.get("current_round", {})
        current_stats = [
            ("Cards Reviewed", current.get("cards_reviewed", 0)),
            ("Battles Won", current.get("battles_won", 0)),
            ("Gyms Defeated", f"{current.get('gyms_defeated', 0)}/8"),
            ("Elite Four Defeated", f"{current.get('elite_four_defeated', 0)}/4"),
            ("Champion Defeated", "✓" if current.get("champion_defeated", False) else "✗"),
            ("Pokemon Caught", current.get("pokemon_caught", 0)),
            ("Mega Evolutions Used", current.get("mega_evolutions_used", 0)),
        ]

        for stat_name, stat_value in current_stats:
            stat_label = QLabel(f"{stat_name}: {stat_value}")
            stat_label.setStyleSheet("font-size: 12px; padding: 2px;")
            scroll_layout.addWidget(stat_label)

        # Session Stats Section
        scroll_layout.addSpacing(15)
        session_label = QLabel("⚡ THIS SESSION")
        session_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #90EE90; padding: 5px;")
        scroll_layout.addWidget(session_label)

        session = stats.get("session", {})
        session_stats = [
            ("Cards Reviewed", session.get("cards_reviewed", 0)),
            ("Battles Won", session.get("battles_won", 0)),
            ("XP Gained", session.get("xp_gained", 0)),
            ("Pokemon Caught", session.get("pokemon_caught", 0)),
        ]

        for stat_name, stat_value in session_stats:
            stat_label = QLabel(f"{stat_name}: {stat_value:,}")
            stat_label.setStyleSheet("font-size: 12px; padding: 2px;")
            scroll_layout.addWidget(stat_label)

        # Legendary Captures Section
        scroll_layout.addSpacing(15)
        legendary_label = QLabel("LEGENDARY CAPTURES")
        legendary_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFD700; padding: 5px;")
        scroll_layout.addWidget(legendary_label)

        legendary = stats.get("legendary_captures", {})
        legendary_stats = [
            ("Primal Groudon", "✓ Captured" if legendary.get("primal_groudon_captured", False) else f"✗ ({stats['lifetime'].get('total_cards_reviewed', 0)}/5000 cards)"),
            ("Primal Kyogre", "✓ Captured" if legendary.get("primal_kyogre_captured", False) else f"✗ ({stats['lifetime'].get('total_cards_reviewed', 0)}/6000 cards)"),
            ("Mega Rayquaza", "✓ Captured" if legendary.get("mega_rayquaza_captured", False) else f"✗ ({stats['lifetime'].get('total_cards_reviewed', 0)}/7000 cards)"),
        ]

        for stat_name, stat_value in legendary_stats:
            stat_label = QLabel(f"{stat_name}: {stat_value}")
            stat_label.setStyleSheet("font-size: 12px; padding: 2px;")
            scroll_layout.addWidget(stat_label)

        # Counter Info Section
        scroll_layout.addSpacing(15)
        counter_label = QLabel("📍 CURRENT PROGRESS")
        counter_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFA500; padding: 5px;")
        scroll_layout.addWidget(counter_label)

        # Get current counters
        try:
            conf = _ankimon_get_col_conf()
            if conf:
                gym_counter = conf.get("ankimon_gym_counter", 0)
                elite_counter = conf.get("ankimon_elite_four_counter", 0)
                champion_counter = conf.get("ankimon_champion_counter", 0)

                # Determine current objective
                if not _ankimon_all_gym_badges_earned():
                    objective = f"Next Gym: {gym_counter}/100 cards"
                elif not _ankimon_all_elite_four_defeated():
                    member_idx = conf.get("ankimon_elite_four_index", 0) % 4
                    members = ["Aaron", "Bertha", "Flint", "Lucian"]
                    objective = f"Elite Four {members[member_idx]}: {elite_counter}/150 cards"
                else:
                    objective = f"Champion: {champion_counter}/200 cards"

                objective_label = QLabel(objective)
                objective_label.setStyleSheet("font-size: 13px; font-weight: bold; padding: 2px; color: #00FF00;")
                scroll_layout.addWidget(objective_label)
        except Exception:
            pass

        # Mega Evolution Section
        scroll_layout.addSpacing(15)
        mega_label = QLabel("⚡ MEGA EVOLUTION")
        mega_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF00FF; padding: 5px;")
        scroll_layout.addWidget(mega_label)

        try:
            mega_state = _load_mega_state()
            key_stone = "✓ Unlocked" if mega_state.get("key_stone_unlocked", False) else "✗ Locked (Defeat Champion first)"
            stones_count = len([v for v in mega_state.get("mega_stones", {}).values() if v > 0])

            mega_stats = [
                ("Key Stone", key_stone),
                ("Mega Stones Owned", stones_count),
            ]

            for stat_name, stat_value in mega_stats:
                stat_label = QLabel(f"{stat_name}: {stat_value}")
                stat_label.setStyleSheet("font-size: 12px; padding: 2px;")
                scroll_layout.addWidget(stat_label)
        except Exception:
            pass

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Button layout
        button_layout = QHBoxLayout()

        # Reset Progression button (only show if Developer Mode is enabled)
        try:
            global developer_menu
            if developer_menu and developer_menu.menuAction().isVisible():
                reset_btn = QPushButton("🔄 Reset Progression")
                reset_btn.setStyleSheet("background-color: #D32F2F; color: white; font-weight: bold;")
                def reset_and_close():
                    _reset_progression()
                    dlg.close()
                reset_btn.clicked.connect(reset_and_close)
                button_layout.addWidget(reset_btn)
        except Exception:
            pass

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        dlg.exec()

    except Exception as e:
        showWarning(f"Error displaying progression stats: {e}")
        import traceback
        traceback.print_exc()


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        #self.update()
    def init_ui(self):
        global test
        global addon_dir, icon_path
        layout = QVBoxLayout()

        # Add button bar at the top
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        # Load icons from icons/ folder
        try:
            icons_path_dir = addon_dir / "addon_sprites" / "icons"
            pokedex_icon = QIcon(str(icons_path_dir / "pokedex.gif"))  # Changed from "smaller pokedex.gif" to larger version
            pokeball_icon = QIcon(str(icons_path_dir / "poke.png"))
        except Exception as e:
            print(f"Could not load button icons: {e}")
            pokedex_icon = QIcon()
            pokeball_icon = QIcon()

        # Pokedex button (with icon)
        pokedex_btn = QPushButton(pokedex_icon, "Pokédex")
        pokedex_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a9fd4;
                color: white;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a8fc4;
            }
        """)
        pokedex_btn.clicked.connect(lambda: complete_pokedex.show_complete_pokedex())
        button_layout.addWidget(pokedex_btn)

        # Party dropdown button with menu
        from PyQt6.QtWidgets import QMenu
        party_btn = QPushButton("Party ▼")
        party_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a9fd4;
                color: white;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a8fc4;
            }
            QPushButton::menu-indicator {
                width: 0px;
            }
        """)
        self.party_menu = QMenu()

        # Update party menu dynamically when it's about to be shown
        def update_party_menu():
            self.party_menu.clear()
            try:
                party = _load_party()
                slots = party.get("slots", [0, 1, 2, 3])
                my_list = _load_mypokemon_list()

                for i in range(4):
                    try:
                        idx = int(slots[i])
                        if 0 <= idx < len(my_list):
                            pkmn = my_list[idx]
                            pkmn_name = pkmn.get("name", "Empty")
                            nickname = pkmn.get("nickname", "")
                            if nickname:
                                label = f"Slot {i+1} ({nickname})"
                            else:
                                label = f"Slot {i+1} ({pkmn_name})"
                        else:
                            label = f"Slot {i+1} (Empty)"
                    except Exception:
                        label = f"Slot {i+1} (Empty)"
                    self.party_menu.addAction(label, lambda slot=i: _set_active_from_party_slot(slot))
            except Exception:
                # Fallback if party loading fails
                self.party_menu.addAction("Slot 1", lambda: _set_active_from_party_slot(0))
                self.party_menu.addAction("Slot 2", lambda: _set_active_from_party_slot(1))
                self.party_menu.addAction("Slot 3", lambda: _set_active_from_party_slot(2))
                self.party_menu.addAction("Slot 4", lambda: _set_active_from_party_slot(3))

        # Connect the menu's aboutToShow signal to refresh the party list
        self.party_menu.aboutToShow.connect(update_party_menu)

        party_btn.setMenu(self.party_menu)
        button_layout.addWidget(party_btn)

        # Pokemon Collection button (with icon)
        collection_btn = QPushButton(pokeball_icon, "Pokémon Collection")
        collection_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a9fd4;
                color: white;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a8fc4;
            }
        """)
        collection_btn.clicked.connect(lambda: pokecollection_win.show())
        button_layout.addWidget(collection_btn)

        # Progression Stats button
        progression_btn = QPushButton("Progression")
        progression_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #8b49a6;
            }
        """)
        progression_btn.clicked.connect(show_progression_stats)
        button_layout.addWidget(progression_btn)

        # Itembag button
        itembag_btn = QPushButton(" Itembag")

        # Set icon for the button
        try:
            icon_path = str(addon_dir / "addon_sprites" / "icons" / "poke.png")
            itembag_btn.setIcon(QIcon(icon_path))
        except Exception as e:
            print(f"[UI] Failed to load itembag icon: {e}")

        itembag_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B4513;
                color: white;
                border-radius: 5px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #A0522D;
            }
        """)
        itembag_btn.clicked.connect(lambda: item_window.show_window())
        button_layout.addWidget(itembag_btn)

        layout.addLayout(button_layout)

        # Add progress label for gym/Elite Four/Champion counter
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("""
            QLabel {
                background-color: rgba(74, 144, 226, 0.9);
                color: white;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
                margin: 5px;
            }
        """)
        self.progress_label.setVisible(False)  # Hidden by default
        layout.addWidget(self.progress_label)

        # Create a content widget to hold the battle/logo display
        # This will be what gets cleared and updated, not the buttons
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_widget.setLayout(self.content_layout)
        layout.addWidget(self.content_widget)

        # Add initial logo
        image_file = f"ankimon_logo.png"
        image_path = str(addon_dir) + "/" + image_file
        image_label = QLabel()
        pixmap = QPixmap()
        pixmap.load(str(image_path))
        if pixmap.isNull():
            showWarning("Failed to load image")
        else:
            image_label.setPixmap(pixmap)
        scaled_pixmap = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio)
        image_label.setPixmap(scaled_pixmap)
        self.content_layout.addWidget(image_label)

        first_start = True
        self.setLayout(layout)
        # Set window
        self.setWindowTitle('Ankimon Window')
        self.setWindowIcon(QIcon(str(icon_path))) # Add a Pokeball icon
        # Ensure window is resizable (remove any fixed size constraints)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        # Display the Pokémon image

    def open_dynamic_window(self):
        # Create and show the dynamic window
        try:
            global pkmn_window
            if pkmn_window == False:
                self.display_first_encounter()
                pkmn_window = True
            self.show()
        except Exception as e:
            showWarning(f"Following Error occured when opening window: {e}")

    def display_first_start_up(self):
        global first_start, pkmn_window
        if first_start == False:
            from aqt import mw
            # Get the geometry of the main screen
            main_screen_geometry = mw.geometry()
            # Calculate the position to center the ItemWindow on the main screen
            x = main_screen_geometry.center().x() - self.width() / 2
            y = main_screen_geometry.center().y() - self.height() / 2
            self.setGeometry(x, y, 256, 256 )
            self.move(x,y)
            self.show()
            first_start = True
        global pkmn_window
        pkmn_window = True

    def pokemon_display_first_encounter(self):
        # Create a widget-based battle display with animated GIFs
        global pokemon_encounter
        global hp, name, id, stats, level, max_hp, base_experience, ev, iv, gender
        global caught_pokemon, message_box_text
        global pkmnimgfolder, backdefault, frontdefault_gif, backdefault_gif, addon_dir
        global caught
        global mainpkmn, mainpokemon_path
        global mainpokemon_id, mainpokemon_name, mainpokemon_level, mainpokemon_ability, mainpokemon_type, mainpokemon_xp, mainpokemon_stats, mainpokemon_attacks, mainpokemon_base_experience, mainpokemon_ev, mainpokemon_iv, mainpokemon_hp, mainpokemon_current_hp, mainpokemon_growth_rate
        global battlescene_path, battlescene_path_without_dialog, battlescene_file, battle_ui_path
        global attack_counter, merged_pixmap, window
        global is_trainer_battle, current_trainer_name, current_trainer_sprite, enemy_battles_path
        attack_counter = 0
        caught = 0

        # Safety check: if name is None or empty, this shouldn't happen
        if not name:
            _ankimon_log("ERROR", "AnkimonBattle", "pokemon_display_first_encounter called with empty name!")
            # Fallback: generate a new Pokemon
            new_pokemon()
            # Recursively call this function with the new Pokemon data
            return self.pokemon_display_first_encounter()

        # Special handling for Shadow Mewtwo (and other variants)
        if name == "Shadow Mewtwo":
            # Use base Mewtwo for Pokedex lookups but keep display name
            display_name = "Shadow Mewtwo"
            lookup_name = "mewtwo"
            # id is already set globally to 150
        else:
            display_name = name.capitalize() if name else "Unknown"
            lookup_name = name.lower() if name else "pikachu"
            id = int(search_pokedex(lookup_name, "num"))

        lang_name = get_pokemon_diff_lang_name(int(id))
        name = display_name
        max_hp = calculate_hp(stats["hp"], level, ev, iv)
        mainpkmn_max_hp = calculate_hp(mainpokemon_stats["hp"], mainpokemon_level, mainpokemon_ev, mainpokemon_iv)

        # Set message based on whether it's a trainer battle or wild encounter
        if is_trainer_battle and current_trainer_name:
            message_box_text = (f"{current_trainer_name} wants to battle!")
        else:
            message_box_text = (f"A wild {lang_name.capitalize()} appeared !")

        # Always use battle scene without dialog box for consistent positioning
        bckgimage_path = battlescene_path_without_dialog / battlescene_file

        # Create a container widget
        container = QWidget()
        # Set minimum size but allow expansion - removed setFixedSize for resizability
        container.setMinimumSize(556, 300)

        # Create background label
        background_label = QLabel(container)
        background_label.setGeometry(0, 0, 556, 300)
        pixmap_bckg = QPixmap()
        pixmap_bckg.load(str(bckgimage_path))
        background_label.setPixmap(pixmap_bckg)

        # Load and overlay UI elements on background
        ui_path = battle_ui_path
        pixmap_ui = QPixmap()
        pixmap_ui.load(str(ui_path))

        # Create merged background with UI
        merged_bg = QPixmap(pixmap_bckg.size())
        merged_bg.fill(QColor(0, 0, 0, 0))
        painter = QPainter(merged_bg)
        painter.drawPixmap(0, 0, pixmap_bckg)

        # Draw HP bars
        def draw_hp_bar(x, y, h, w, hp, max_hp):
            pokemon_hp_percent = (hp / max_hp) * 100
            hp_bar_value = (w * (hp / max_hp))
            if pokemon_hp_percent < 25:
                hp_color = QColor(255, 0, 0)
            elif pokemon_hp_percent < 50:
                hp_color = QColor(255, 140, 0)
            elif pokemon_hp_percent < 75:
                hp_color = QColor(255, 255, 0)
            else:
                hp_color = QColor(110, 218, 163)
            painter.setBrush(hp_color)
            painter.drawRect(x, y, hp_bar_value, h)

        draw_hp_bar(118, 76, 8, 116, hp, max_hp)
        draw_hp_bar(401, 208, 8, 116, mainpokemon_hp, mainpkmn_max_hp)

        painter.drawPixmap(0, 0, pixmap_ui)

        # Draw XP bar
        experience = find_experience_for_level(mainpokemon_growth_rate, mainpokemon_level)
        experience = int(experience)
        mainpokemon_xp_value = int((mainpokemon_xp / experience) * 148)
        painter.setBrush(QColor(58, 155, 220))
        painter.drawRect(366, 246, mainpokemon_xp_value, 5)

        # Draw text
        lvl = (f"{level}")
        mainlvl = (f"{mainpokemon_level}")
        if gender == "M":
            gender_symbol = "♂"
        elif gender == "F":
            gender_symbol = "♀"
        else:
            gender_symbol = ""

        custom_font = load_custom_font(26)
        msg_font = load_custom_font(32)
        mainpokemon_lang_name = get_pokemon_diff_lang_name(int(mainpokemon_id))

        painter.setFont(custom_font)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(36,67,f"{lang_name} {gender_symbol}")
        painter.drawText(208,67,lvl)
        painter.drawText(328,199,mainpokemon_lang_name)
        painter.drawText(490,199,mainlvl)
        painter.drawText(487,238,f"{mainpkmn_max_hp}")
        painter.drawText(442,238,f"{mainpokemon_hp}")

        # Battle message
        painter.setFont(msg_font)
        painter.setPen(QColor(240, 240, 208))
        painter.drawText(40, 320, message_box_text)
        painter.end()

        background_label.setPixmap(merged_bg)

        # Get Pokemon sizes from pokedex for proper scaling
        def get_pokemon_size(pkmn_id):
            """Get Pokemon height in meters from pokedex, return scale factor"""
            try:
                # First get pokemon name from ID
                pkmn_name = search_pokedex_by_id(pkmn_id)
                if pkmn_name and pkmn_name != 'Pokémon not found':
                    # Then get height using the name
                    height = search_pokedex(pkmn_name.lower(), "heightm")
                    if height and isinstance(height, (int, float)):
                        # Base size 60px for 1.0m Pokemon, scale proportionally
                        # Cap at max 120px to prevent covering UI elements (status bars)
                        # Min 30px for tiny Pokemon
                        size = max(30, min(120, int(60 * height)))
                        return size
                return 80  # Default size if lookup fails
            except Exception:
                return 80  # Default size

        wild_size = get_pokemon_size(id)
        player_size = get_pokemon_size(mainpokemon_id)

        # Ground baseline coordinates for bottom-anchored positioning
        # These coordinates represent where Pokemon "feet" touch the ground
        ENEMY_GROUND_X, ENEMY_GROUND_Y = 390, 166  # Enemy Pokemon ground baseline
        PLAYER_GROUND_X, PLAYER_GROUND_Y = 134, 249  # Player Pokemon ground baseline

        # Wild Pokemon animated sprite (with shiny support)
        wild_pkmn_label = QLabel(container)
        wild_pkmn_label.setStyleSheet("background: transparent;")
        wild_pkmn_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Check if this is a shiny encounter
        global current_wild_is_shiny, shiny_front_default
        sprite_loaded = False

        if current_wild_is_shiny:
            # Try shiny GIF (shiny_front_default contains GIF files)
            wild_gif_path = shiny_front_default / f"{id}.gif"
            if wild_gif_path.exists():
                wild_movie = QMovie(str(wild_gif_path))
                wild_movie.setScaledSize(QSize(wild_size, wild_size))
                wild_pkmn_label.setMovie(wild_movie)
                wild_movie.start()
                sprite_loaded = True
                # Log successful shiny sprite load
                try:
                    if developer_menu and developer_menu.menuAction().isVisible():
                        print(f"[Shiny] Loaded shiny sprite: {wild_gif_path}")
                except:
                    pass

        # Fallback to normal sprites ONLY if shiny sprite doesn't exist
        if not sprite_loaded:
            # Check for shadow variant
            global current_wild_variant
            if current_wild_variant == "shadow" and id == 150:
                wild_gif_path = frontdefault_gif / f"{id}_shadow_front.gif"
                _ankimon_log("INFO", "ShadowMewtwo", f"Loading Shadow Mewtwo sprite: {wild_gif_path}")
            else:
                wild_gif_path = frontdefault_gif / f"{id}.gif"

            if wild_gif_path.exists():
                wild_movie = QMovie(str(wild_gif_path))
                wild_movie.setScaledSize(QSize(wild_size, wild_size))
                wild_pkmn_label.setMovie(wild_movie)
                wild_movie.start()
                _ankimon_log("INFO", "SpriteLoad", f"Loaded GIF sprite: {wild_gif_path}")
            else:
                # Fallback to PNG
                if current_wild_variant == "shadow" and id == 150:
                    wild_pixmap_path = frontdefault / f"{id}_shadow_front.png"
                    _ankimon_log("INFO", "ShadowMewtwo", f"GIF not found, using PNG: {wild_pixmap_path}")
                else:
                    wild_pixmap_path = frontdefault / f"{id}.png"

                wild_pixmap = QPixmap(str(wild_pixmap_path))
                wild_pixmap = wild_pixmap.scaled(wild_size, wild_size, Qt.AspectRatioMode.KeepAspectRatio)
                wild_pkmn_label.setPixmap(wild_pixmap)

        # Calculate bottom-anchored position for enemy Pokemon
        enemy_draw_x, enemy_draw_y = bottom_anchor_pos(ENEMY_GROUND_X, ENEMY_GROUND_Y, wild_size, wild_size, anchor="center")
        wild_pkmn_label.setGeometry(enemy_draw_x, enemy_draw_y, wild_size, wild_size)

        # Display shiny icon if this is a shiny encounter
        if current_wild_is_shiny:
            shiny_icon_label = QLabel(container)
            shiny_icon_label.setStyleSheet("background: transparent;")
            shiny_icon_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            shiny_icon_path = addon_dir / "addon_sprites" / "icons" / "shiny-stars.png"
            if shiny_icon_path.exists():
                shiny_icon_pixmap = QPixmap(str(shiny_icon_path))
                # Scale to small icon size (20x20)
                shiny_icon_scaled = shiny_icon_pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                shiny_icon_label.setPixmap(shiny_icon_scaled)
                # Position next to wild Pokemon name (left side of name box)
                shiny_icon_label.setGeometry(15, 50, 20, 20)

        # Player Pokemon animated sprite
        player_pkmn_label = QLabel(container)
        player_pkmn_label.setStyleSheet("background: transparent;")
        player_pkmn_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Store reference for transition animations
        self.player_sprite_label = player_pkmn_label
        self.player_sprite_size = None  # Will be set below

        # Check if player Pokemon is Mega (load from mypokemon.json)
        # Check if Pokemon is in Mega form (uses hard Key Stone gate)
        player_is_mega = _is_mega_active()

        # Check if player Pokemon is shiny
        player_is_shiny = False
        try:
            if mainpokemon_path.is_file():
                with open(mainpokemon_path, 'r') as file:
                    mainpkmn_data = json.load(file)
                    if isinstance(mainpkmn_data, list) and len(mainpkmn_data) > 0:
                        player_is_shiny = mainpkmn_data[0].get('is_shiny', False)
        except:
            pass

        # Check if player's active Pokemon is Shadow variant
        player_is_shadow_variant = False
        try:
            my_list = _load_mypokemon_list()
            party = _load_party()
            active_slot = party.get("active_slot", 0)
            slots = party.get("slots", [0, 1, 2, 3])
            if 0 <= active_slot < len(slots):
                party_index = slots[active_slot]
                if 0 <= party_index < len(my_list):
                    active_pokemon = my_list[party_index]
                    if active_pokemon.get("id") == 150 and active_pokemon.get("variant") == "shadow":
                        player_is_shadow_variant = True
                        _ankimon_log("INFO", "ShadowMewtwo", "Player's active Pokemon is Shadow Mewtwo")
        except Exception as e:
            pass

        # Priority: Mega > Shadow > Shiny > Normal
        # Use mega sprite if Pokemon is in Mega form
        if player_is_mega:
            player_gif_path = user_path_sprites / "back_mega_pokemon_gif" / f"{mainpokemon_id}.gif"
            if not player_gif_path.exists():
                player_gif_path = backdefault_gif / f"{mainpokemon_id}.gif"
            print(f"[Sprite] player id={mainpokemon_id} shiny={player_is_shiny} mega=True -> {player_gif_path.name}")
        # Use shadow sprite if Pokemon is Shadow variant
        elif player_is_shadow_variant:
            player_gif_path = backdefault_gif / f"{mainpokemon_id}_shadow_back.gif"
            if not player_gif_path.exists():
                player_gif_path = backdefault_gif / f"{mainpokemon_id}.gif"
                print(f"[Sprite] player id={mainpokemon_id} shadow=True -> back_default_gif (shadow sprite not found)")
            else:
                print(f"[Sprite] player id={mainpokemon_id} shadow=True -> shadow_back_default_gif")
                _ankimon_log("INFO", "ShadowMewtwo", f"Using Shadow Mewtwo back sprite: {player_gif_path}")
        # Use shiny sprite if Pokemon is shiny (and not mega or shadow)
        elif player_is_shiny:
            global shiny_back_default_gif
            player_gif_path = shiny_back_default_gif / f"{mainpokemon_id}.gif"
            # Fallback to normal if shiny sprite doesn't exist
            if not player_gif_path.exists():
                player_gif_path = backdefault_gif / f"{mainpokemon_id}.gif"
                print(f"[Sprite] player id={mainpokemon_id} shiny=True mega=False -> back_default_gif (shiny sprite not found)")
            else:
                print(f"[Sprite] player id={mainpokemon_id} shiny=True mega=False -> shiny_back_default_gif")
        # Normal sprite
        else:
            player_gif_path = backdefault_gif / f"{mainpokemon_id}.gif"
            print(f"[Sprite] player id={mainpokemon_id} shiny=False mega=False -> back_default_gif")

        # Store current sprite path and size for transition
        self.player_sprite_path = player_gif_path
        self.player_sprite_size = player_size

        if player_gif_path.exists():
            player_movie = QMovie(str(player_gif_path))
            player_movie.setScaledSize(QSize(player_size, player_size))
            player_pkmn_label.setMovie(player_movie)
            player_movie.start()
        else:
            # Fallback to PNG
            player_pixmap = QPixmap(str(backdefault / f"{mainpokemon_id}.png"))
            player_pixmap = player_pixmap.scaled(player_size, player_size, Qt.AspectRatioMode.KeepAspectRatio)
            player_pkmn_label.setPixmap(player_pixmap)

        # Calculate bottom-anchored position for player Pokemon
        player_draw_x, player_draw_y = bottom_anchor_pos(PLAYER_GROUND_X, PLAYER_GROUND_Y, player_size, player_size, anchor="center")
        player_pkmn_label.setGeometry(player_draw_x, player_draw_y, player_size, player_size)

        # Display held item icon if main Pokemon has one
        try:
            with open(mainpokemon_path, 'r') as file:
                mainpkmn_data = json.load(file)
                if isinstance(mainpkmn_data, list) and len(mainpkmn_data) > 0:
                    held_item = mainpkmn_data[0].get('held_item')
                    if held_item:
                        # Display held item icon in bottom left corner
                        held_item_label = QLabel(container)
                        held_item_label.setStyleSheet("background: transparent;")
                        held_item_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

                        # Try to load the item sprite
                        item_sprite_path = items_path / f"{held_item}.png"
                        if not item_sprite_path.exists():
                            # Try without the prefix format
                            item_sprite_path = items_path / f"{held_item}"

                        if item_sprite_path.exists():
                            held_item_pixmap = QPixmap(str(item_sprite_path))
                            # Scale to small icon size (30x30)
                            held_item_scaled = held_item_pixmap.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            held_item_label.setPixmap(held_item_scaled)
                            # Position in bottom left corner (near player Pokemon status box)
                            held_item_label.setGeometry(320, 265, 30, 30)
        except Exception as e:
            print(f"Error displaying held item: {e}")

        # Display trainer sprite for any trainer battle (enemy, Elite Four, Champion)
        trainer_sprite_path = None

        # Check for enemy trainer battle
        if is_trainer_battle and current_trainer_sprite:
            trainer_sprite_path = enemy_battles_path / current_trainer_sprite

        # Check for Elite Four battle
        elif _ankimon_is_elite_four_active():
            try:
                conf = _ankimon_get_col_conf()
                if conf:
                    member_key = conf.get("ankimon_elite_four_member_key")
                    if member_key:
                        elite_sprite_dir = addon_dir / "addon_sprites" / "elite_four_champion_sprite" / "elite_four_gif"
                        trainer_sprite_path = elite_sprite_dir / f"{member_key}.gif"
            except Exception:
                pass

        # Check for Champion battle
        elif _ankimon_is_champion_active():
            try:
                elite_sprite_dir = addon_dir / "addon_sprites" / "elite_four_champion_sprite" / "elite_four_gif"
                trainer_sprite_path = elite_sprite_dir / "cynthia.gif"
            except Exception:
                pass

        # Display the trainer sprite if we have a valid path
        if trainer_sprite_path and trainer_sprite_path.exists():
            trainer_label = QLabel(container)
            trainer_label.setStyleSheet("background: transparent;")
            trainer_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

            # Use QMovie for animated GIF instead of QPixmap
            trainer_movie = QMovie(str(trainer_sprite_path))
            trainer_movie.setScaledSize(QSize(80, 80))  # Scale to 80px
            trainer_label.setMovie(trainer_movie)
            trainer_movie.start()

            # Position trainer sprite on the left side of the wild Pokemon area
            trainer_x = 260  # Left of wild Pokemon
            trainer_y = 40   # Aligned with top of battle area
            trainer_label.setGeometry(trainer_x, trainer_y, 80, 80)

        # Add popup message for first encounter
        if pokemon_encounter == 0:
            popup_label = QLabel(container)
            popup_label.setText(message_box_text)
            popup_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            popup_label.setStyleSheet("""
                QLabel {
                    background-color: rgb(0, 0, 0);
                    color: #f0f0d0;
                    font-size: 18px;
                    font-weight: bold;
                    border-radius: 10px;
                    padding: 15px;
                }
            """)
            popup_label.setGeometry(100, 230, 356, 60)

            # Fade out animation
            from PyQt6.QtCore import QTimer, QPropertyAnimation
            opacity_effect = QGraphicsOpacityEffect(popup_label)
            popup_label.setGraphicsEffect(opacity_effect)

            fade = QPropertyAnimation(opacity_effect, b"opacity")
            fade.setDuration(2000)  # 2 seconds
            fade.setStartValue(1.0)
            fade.setEndValue(0.0)

            # Start fade after 1 second delay
            QTimer.singleShot(1000, fade.start)
            QTimer.singleShot(3000, popup_label.hide)

        return container

    def pokemon_display_battle(self):
        global pokemon_encounter, id
        pokemon_encounter += 1
        if pokemon_encounter == 1:
            bckgimage_path = battlescene_path / battlescene_file
        elif pokemon_encounter > 1:
            bckgimage_path = battlescene_path_without_dialog / battlescene_file
        ui_path = battle_ui_path
        pixmap_ui = QPixmap()
        pixmap_ui.load(str(ui_path))

        # Load the background image
        pixmap_bckg = QPixmap()
        pixmap_bckg.load(str(bckgimage_path))

        # Display the Pokémon image
        pkmnimage_file = f"{id}.png"
        pkmnimage_path = frontdefault / pkmnimage_file
        image_label = QLabel()
        pixmap = QPixmap()
        pixmap.load(str(pkmnimage_path))

        # Display the Main Pokémon image
        pkmnimage_file2 = f"{mainpokemon_id}.png"
        pkmnimage_path2 = backdefault / pkmnimage_file2
        pixmap2 = QPixmap()
        pixmap2.load(str(pkmnimage_path2))

        # Calculate the new dimensions to maintain the aspect ratio
        max_width = 150
        # Guard: missing/invalid sprite can yield width==0 and crash scaling
        if pixmap.isNull() or pixmap.width() <= 0 or pixmap.height() <= 0:
            pixmap = QPixmap(max_width, max_width)
            pixmap.fill(QColor(0, 0, 0, 0))
        else:
            original_width = max(1, pixmap.width())
            original_height = pixmap.height()
            new_width = max_width
            new_height = (original_height * max_width) // original_width
            pixmap = pixmap.scaled(new_width, new_height)

        # Calculate the new dimensions to maintain the aspect ratio
        max_width = 150
        # Guard: missing/invalid sprite can yield width==0 and crash scaling
        if pixmap2.isNull() or pixmap2.width() <= 0 or pixmap2.height() <= 0:
            pixmap2 = QPixmap(max_width, max_width)
            pixmap2.fill(QColor(0, 0, 0, 0))
        else:
            original_width2 = max(1, pixmap2.width())
            original_height2 = pixmap2.height()
            new_width2 = max_width
            new_height2 = (original_height2 * max_width) // original_width2
            pixmap2 = pixmap2.scaled(new_width2, new_height2)

        # Merge the background image and the Pokémon image
        merged_pixmap = QPixmap(pixmap_bckg.size())
        #merged_pixmap.fill(Qt.transparent)
        merged_pixmap.fill(QColor(0, 0, 0, 0))  # RGBA where A (alpha) is 0 for full transparency
        # merge both images together
        painter = QPainter(merged_pixmap)
        # draw background to a specific pixel
        painter.drawPixmap(0, 0, pixmap_bckg)

        def draw_hp_bar(x, y, h, w, hp, max_hp):
            pokemon_hp_percent = (hp / max_hp) * 100
            hp_bar_value = (w * (hp / max_hp))
            # Draw the HP bar
            if pokemon_hp_percent < 25:
                hp_color = QColor(255, 0, 0)  # Red
            elif pokemon_hp_percent < 50:
                hp_color = QColor(255, 140, 0)  # Orange
            elif pokemon_hp_percent < 75:
                hp_color = QColor(255, 255, 0)  # Yellow
            else:
                hp_color = QColor(110, 218, 163)  # Green
            painter.setBrush(hp_color)
            painter.drawRect(x, y, hp_bar_value, h)

        draw_hp_bar(118, 76, 8, 116, hp, max_hp)  # enemy pokemon hp_bar
        draw_hp_bar(401, 208, 8, 116, mainpokemon_current_hp, mainpokemon_hp)  # main pokemon hp_bar

        painter.drawPixmap(0, 0, pixmap_ui)

        # Ground baseline coordinates for bottom-anchored positioning
        # These coordinates represent where Pokemon "feet" touch the ground
        ENEMY_GROUND_X, ENEMY_GROUND_Y = 390, 166  # Enemy Pokemon ground baseline
        PLAYER_GROUND_X, PLAYER_GROUND_Y = 134, 249  # Player Pokemon ground baseline

        # Calculate bottom-anchored positions for sprites
        enemy_draw_x, enemy_draw_y = bottom_anchor_pos(ENEMY_GROUND_X, ENEMY_GROUND_Y, new_width, new_height, anchor="center")
        player_draw_x, player_draw_y = bottom_anchor_pos(PLAYER_GROUND_X, PLAYER_GROUND_Y, new_width2, new_height2, anchor="center")

        # Draw pokemon sprites with bottom-anchored positioning
        painter.drawPixmap(enemy_draw_x, enemy_draw_y, pixmap)
        painter.drawPixmap(player_draw_x, player_draw_y, pixmap2)

        experience = find_experience_for_level(mainpokemon_growth_rate, mainpokemon_level)
        experience = int(experience)
        mainxp_bar_width = 5
        mainpokemon_xp_value = int((mainpokemon_xp / experience) * 148)
        # Paint XP Bar
        painter.setBrush(QColor(58, 155, 220))
        painter.drawRect(366, 246, mainpokemon_xp_value, mainxp_bar_width)

        # create level text
        lvl = (f"{level}")
        mainlvl = (f"{mainpokemon_level}")

        # custom font
        custom_font = load_custom_font(28)
        msg_font = load_custom_font(32)

        painter.setFont(custom_font)
        painter.setPen(QColor(0, 0, 0))
        lang_name = get_pokemon_diff_lang_name(int(id))
        painter.drawText(36,67,lang_name)
        painter.drawText(208,67,lvl)
        mainpokemon_lang_name = get_pokemon_diff_lang_name(int(mainpokemon_id))
        painter.drawText(328,199,mainpokemon_lang_name)
        painter.drawText(490,199,mainlvl)
        painter.drawText(487,238,f"{mainpokemon_hp}")
        painter.drawText(442,238,f"{mainpokemon_current_hp}")

        # Battle message
        painter.setFont(msg_font)
        painter.setPen(QColor(240, 240, 208))
        painter.drawText(40, 320, message_box_text)
        painter.end()
        # Set the merged image as the pixmap for the QLabel
        image_label.setPixmap(merged_pixmap)
        return image_label

    def pokemon_display_item(self, item):
        global pokemon_encounter, user_path_sprites
        global addon_dir
        global frontdefault

        # SAFETY: Handle None item
        if not item:
            item = "unknown-item"
            print("[Item Display] WARNING: Item is None, using placeholder")

        bckgimage_path =  addon_dir / "addon_sprites" / "starter_screen" / "bg.png"

        # Try loading from addon_sprites/items/ first (official location)
        item_path = addon_dir / "addon_sprites" / "items" / f"{item}.png"
        if not item_path.exists():
            # Fallback to user_files/sprites/items/
            item_path = user_path_sprites / "items" / f"{item}.png"

        # Load the background image
        pixmap_bckg = QPixmap()
        pixmap_bckg.load(str(bckgimage_path))

        # Display the Pokémon image
        item_label = QLabel()
        item_pixmap = QPixmap()

        # SAFETY: Check if item file exists before loading
        if item_path.exists():
            item_pixmap.load(str(item_path))
        else:
            print(f"[Item Display] WARNING: Item sprite not found: {item_path}")
            # Create a placeholder pixmap (50x50 gray square)
            item_pixmap = QPixmap(50, 50)
            item_pixmap.fill(QColor(128, 128, 128))

        def resize_pixmap_img(pixmap):
            max_width = 100
            original_width = pixmap.width()
            original_height = pixmap.height()

            if original_width == 0:
                return pixmap  # Avoid division by zero

            new_width = max_width
            new_height = (original_height * max_width) // original_width
            pixmap2 = pixmap.scaled(new_width, new_height)
            return pixmap2

        item_pixmap = resize_pixmap_img(item_pixmap)

        # Merge the background image and the Pokémon image
        merged_pixmap = QPixmap(pixmap_bckg.size())
        merged_pixmap.fill(QColor(0, 0, 0, 0))  # RGBA where A (alpha) is 0 for full transparency
        #merged_pixmap.fill(Qt.transparent)
        # merge both images together
        painter = QPainter(merged_pixmap)
        # draw background to a specific pixel
        painter.drawPixmap(0, 0, pixmap_bckg)
        #item = str(item)
        if item.endswith("-up") or item.endswith("-max") or item.endswith("protein") or item.endswith("zinc") or item.endswith("carbos") or item.endswith("calcium") or item.endswith("repel") or item.endswith("statue"):
            painter.drawPixmap(200,50,item_pixmap)
        elif item.endswith("soda-pop"):
            painter.drawPixmap(200,30,item_pixmap)
        elif item.endswith("-heal") or item.endswith("awakening") or item.endswith("ether") or item.endswith("leftovers"):
            painter.drawPixmap(200,50,item_pixmap)
        elif item.endswith("-berry") or item.endswith("potion"):
            painter.drawPixmap(200,80,item_pixmap)
        else:
            painter.drawPixmap(200,90,item_pixmap)

        # custom font
        custom_font = load_custom_font(26)
        item_display_name = item.replace("-", " ").replace("_", " ").capitalize()
        message_box_text = f"You have received a item: {item_display_name} !"
        # Draw the text on top of the image
        # Adjust the font size as needed
        painter.setFont(custom_font)
        painter.setPen(QColor(255,255,255))  # Text color
        painter.drawText(50, 290, message_box_text)
        custom_font = load_custom_font(20)
        painter.setFont(custom_font)
        #painter.drawText(10, 330, "You can look this up in your item bag.")
        painter.end()
        # Set the merged image as the pixmap for the QLabel
        image_label = QLabel()
        image_label.setPixmap(merged_pixmap)

        return image_label

    def pokemon_display_badge(self, badge_number):
        try:
            global pokemon_encounter, addon_dir, badges_path, badges
            bckgimage_path = addon_dir / "addon_sprites" / "starter_screen" / "bg.png"
            badge_path = addon_dir / "user_files" / "sprites" / "badges" / f"{badge_number}.png"

            # Load the background image
            pixmap_bckg = QPixmap()
            pixmap_bckg.load(str(bckgimage_path))

            # Display the Pokémon image
            item_pixmap = QPixmap()
            item_pixmap.load(str(badge_path))

            def resize_pixmap_img(pixmap):
                max_width = 100
                original_width = pixmap.width()
                original_height = pixmap.height()

                if original_width == 0:
                    return pixmap  # Avoid division by zero

                new_width = max_width
                new_height = (original_height * max_width) // original_width
                pixmap2 = pixmap.scaled(new_width, new_height)
                return pixmap2

            item_pixmap = resize_pixmap_img(item_pixmap)

            # Merge the background image and the Pokémon image
            merged_pixmap = QPixmap(pixmap_bckg.size())
            merged_pixmap.fill(QColor(0, 0, 0, 0))  # RGBA where A (alpha) is 0 for full transparency
            #merged_pixmap.fill(Qt.transparent)
            # merge both images together
            painter = QPainter(merged_pixmap)
            # draw background to a specific pixel
            painter.drawPixmap(0, 0, pixmap_bckg)
            #item = str(item)
            painter.drawPixmap(200,90,item_pixmap)

            # custom font
            custom_font = load_custom_font(20)
            message_box_text = f"You have received a badge for:"
            message_box_text2 = f"{badges[str(badge_number)]}!"
            # Draw the text on top of the image
            # Adjust the font size as needed
            painter.setFont(custom_font)
            painter.setPen(QColor(255,255,255))  # Text color
            painter.drawText(120, 270, message_box_text)
            painter.drawText(140, 290, message_box_text2)
            custom_font = load_custom_font(20)
            painter.setFont(custom_font)
            #painter.drawText(10, 330, "You can look this up in your item bag.")
            painter.end()
            # Set the merged image as the pixmap for the QLabel
            image_label = QLabel()
            image_label.setPixmap(merged_pixmap)

            return image_label
        except Exception as e:
            showWarning(f"An error occured in badges window {e}")

    def pokemon_display_dead_pokemon(self):
        global pokemon_hp, name, id, level, type, caught_pokemon, pkmnimgfolder, frontdefault, addon_dir, caught, pokedex_image_path
        # Create the dialog
        lang_name = get_pokemon_diff_lang_name(int(id))
        window_title = (f"Would you want let the  wild {lang_name} free or catch the wild {lang_name} ?")

        # Handle special variants (Shadow Mewtwo, etc.) - use base Pokemon for lookups
        lookup_name = "mewtwo" if name == "Shadow Mewtwo" else name.lower()

        # Display the Pokémon image
        pkmnimage_file = f"{int(search_pokedex(lookup_name,'num'))}.png"
        pkmnimage_path = frontdefault / pkmnimage_file
        pkmnimage_label = QLabel()
        pkmnpixmap = QPixmap()
        pkmnpixmap.load(str(pkmnimage_path))
        pkmnpixmap_bckg = QPixmap()
        pkmnpixmap_bckg.load(str(pokedex_image_path))
        # Calculate the new dimensions to maintain the aspect ratio
        pkmnpixmap = pkmnpixmap.scaled(230, 230)

        # Create a painter to add text on top of the image
        painter2 = QPainter(pkmnpixmap_bckg)
        painter2.drawPixmap(15,15,pkmnpixmap)
        # Capitalize the first letter of the Pokémon's name
        capitalized_name = lang_name.capitalize()
        # Create level text
        lvl = (f" Level: {level}")

        # Draw the text on top of the image
        font = QFont()
        font.setPointSize(20)  # Adjust the font size as needed
        painter2.setFont(font)
        painter2.drawText(270,107,f"{lang_name}")
        font.setPointSize(17)  # Adjust the font size as needed
        painter2.setFont(font)
        painter2.drawText(315,192,f"{lvl}")
        painter2.drawText(322,225,f"Type: {type[0].capitalize()}")
        painter2.setFont(font)
        fontlvl = QFont()
        fontlvl.setPointSize(12)
        painter2.end()

        # Create a QLabel for the capitalized name
        name_label = QLabel(capitalized_name)
        name_label.setFont(font)

        # Create a QLabel for the level
        level_label = QLabel(lvl)
        # Align to the center
        level_label.setFont(fontlvl)

        nickname_input = QLineEdit()
        nickname_input.setPlaceholderText("Choose Nickname")
        nickname_input.setStyleSheet("background-color: rgb(44,44,44);")
        nickname_input.setFixedSize(120, 30)  # Adjust the size as needed

        # Create buttons for catching and killing the Pokémon
        catch_button = QPushButton("Catch Pokémon")
        catch_button.setFixedSize(175, 30)  # Adjust the size as needed
        catch_button.setFont(QFont("Arial", 12))  # Adjust the font size and style as needed
        catch_button.setStyleSheet("background-color: rgb(44,44,44);")
        #catch_button.setFixedWidth(150)
        qconnect(catch_button.clicked, lambda: catch_pokemon(nickname_input.text()))

        kill_button = QPushButton("Defeat Pokémon")
        kill_button.setFixedSize(175, 30)  # Adjust the size as needed
        kill_button.setFont(QFont("Arial", 12))  # Adjust the font size and style as needed
        kill_button.setStyleSheet("background-color: rgb(44,44,44);")
        #kill_button.setFixedWidth(150)
        qconnect(kill_button.clicked, kill_pokemon)
        # Set the merged image as the pixmap for the QLabel
        pkmnimage_label.setPixmap(pkmnpixmap_bckg)


        # align things needed to middle
        pkmnimage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        return pkmnimage_label, kill_button, catch_button, nickname_input

    def update_progress_label(self):
        """Update the progress label with current gym/Elite Four/Champion progress"""
        try:
            conf = _ankimon_get_col_conf()
            if not conf:
                self.progress_label.setVisible(False)
                return

            # Determine current objective and progress
            if not _ankimon_all_gym_badges_earned():
                # Working on gyms
                gym_counter = conf.get("ankimon_gym_counter", 0)
                gym_index = conf.get("ankimon_gym_index", 0) % 8
                gym_names = ["Roark", "Gardenia", "Maylene", "Crasher Wake", "Fantina", "Byron", "Candice", "Volkner"]
                gym_name = gym_names[gym_index]
                gym_target = _ankimon_get_battle_interval_gym()
                pct = int((gym_counter / gym_target) * 100)
                self.progress_label.setText(f"Next Gym ({gym_name}): {gym_counter}/{gym_target} cards ({pct}%)")
                self.progress_label.setVisible(True)
            elif not _ankimon_all_elite_four_defeated():
                # Working on Elite Four
                elite_counter = conf.get("ankimon_elite_four_counter", 0)
                member_idx = conf.get("ankimon_elite_four_index", 0) % 4
                members = ["Aaron", "Bertha", "Flint", "Lucian"]
                member_name = members[member_idx]
                elite_target = _ankimon_get_battle_interval_elite_four()
                pct = int((elite_counter / elite_target) * 100)
                self.progress_label.setText(f"Elite Four ({member_name}): {elite_counter}/{elite_target} cards ({pct}%)")
                self.progress_label.setVisible(True)
            else:
                # Working on Champion
                champion_counter = conf.get("ankimon_champion_counter", 0)
                champion_target = _ankimon_get_battle_interval_champion()
                pct = int((champion_counter / champion_target) * 100)
                self.progress_label.setText(f"Champion (Cynthia): {champion_counter}/{champion_target} cards ({pct}%)")
                self.progress_label.setVisible(True)
        except Exception as e:
            print(f"Error updating progress label: {e}")
            self.progress_label.setVisible(False)

    def display_first_encounter(self):
        # pokemon encounter image
        # Update progress label
        self.update_progress_label()

        # Clear only the content area, not the button bar
        self.clear_layout(self.content_layout)
        battle_widget = self.pokemon_display_first_encounter()
        #battle_widget.setScaledContents(True) #scalable ankimon window
        self.content_layout.addWidget(battle_widget)
        self.setStyleSheet("background-color: rgb(44,44,44);")
        # Allow window to be resizable - removed setMaximumWidth/Height constraints

    def rate_display_item(self, item):
        Receive_Window = QDialog(mw)
        layout = QHBoxLayout()
        item_name = item
        item_widget = self.pokemon_display_item(item_name)
        layout.addWidget(item_widget)
        Receive_Window.setStyleSheet("background-color: rgb(44,44,44);")
        Receive_Window.setMaximumWidth(512)
        Receive_Window.setMaximumHeight(320)
        Receive_Window.setLayout(layout)
        Receive_Window.show()
    
    def display_item(self):
        Receive_Window = QDialog(mw)
        layout = QHBoxLayout()
        item_name = random_item()
        item_widget = self.pokemon_display_item(item_name)
        layout.addWidget(item_widget)
        Receive_Window.setStyleSheet("background-color: rgb(44,44,44);")
        Receive_Window.setMaximumWidth(512)
        Receive_Window.setMaximumHeight(320)
        Receive_Window.setLayout(layout)
        Receive_Window.show()

    def display_badge(self, badge_num):
        Receive_Window = QDialog(mw)
        Receive_Window.setWindowTitle("You have received a Badge!")
        layout = QHBoxLayout()
        badge_widget = self.pokemon_display_badge(badge_num)
        layout.addWidget(badge_widget)
        Receive_Window.setStyleSheet("background-color: rgb(44,44,44);")
        Receive_Window.setMaximumWidth(512)
        Receive_Window.setMaximumHeight(320)
        Receive_Window.setLayout(layout)
        Receive_Window.show()

    def display_pokemon_death(self):
        # Prevent this from showing during gym battles or when boss battle is pending
        if _ankimon_should_suppress_post_battle_ui():
            _ankimon_log("INFO", "AnkimonUI", "Post-battle UI suppressed - boss battle active/pending")
            # Auto-resolve: award EXP and continue to next step
            kill_pokemon()
            return

        # Check if this is a legendary Pokemon or Shadow Mewtwo - auto-capture instead of showing dialog
        global name, current_wild_variant, id
        try:
            legendary_names = ['Groudon-Primal', 'Kyogre-Primal', 'Rayquaza-Mega']

            # Check for Shadow Mewtwo
            if name == "Shadow Mewtwo" or (current_wild_variant == "shadow" and id == 150):
                _ankimon_log("INFO", "ShadowMewtwo", "Shadow Mewtwo defeated, auto-capturing")

                # Auto-capture Shadow Mewtwo using save_caught_pokemon directly
                try:
                    save_caught_pokemon("Shadow Mewtwo")
                    _ankimon_log("INFO", "ShadowMewtwo", "Shadow Mewtwo successfully saved to collection")
                except Exception as e:
                    _ankimon_log("ERROR", "ShadowMewtwo", f"Error saving Shadow Mewtwo: {e}")

                # Reset ALL shadow state before spawning new Pokemon
                current_wild_variant = None

                tooltipWithColour("Shadow Mewtwo has been captured!", "#8B008B")

                # Spawn new Pokemon after capture (this will update name, id, etc.)
                new_pokemon()

                # Log the new Pokemon for debugging
                _ankimon_log("INFO", "ShadowMewtwo", f"After capture, spawned new Pokemon: name={name}, id={id}")

                # Display should now show the new Pokemon (not Shadow Mewtwo)
                self.display_first_encounter()
                return

            # Check for other legendaries
            if name in legendary_names:
                # Determine legendary type
                legendary_type = None
                if name == 'Groudon-Primal':
                    legendary_type = 'primal_groudon'
                elif name == 'Kyogre-Primal':
                    legendary_type = 'primal_kyogre'
                elif name == 'Rayquaza-Mega':
                    legendary_type = 'mega_rayquaza'

                if legendary_type:
                    _complete_legendary_capture(legendary_type)
                    # Spawn new Pokemon after legendary capture
                    new_pokemon()
                    self.display_first_encounter()
                    return
        except Exception as e:
            print(f"Error handling legendary capture: {e}")
            pass

        # pokemon encounter image
        # Clear only the content area, not the button bar
        self.clear_layout(self.content_layout)
        pkmnimage_label, kill_button, catch_button, nickname_input = self.pokemon_display_dead_pokemon()
        self.content_layout.addWidget(pkmnimage_label)
        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_layout.addWidget(kill_button)
        button_layout.addWidget(catch_button)
        button_layout.addWidget(nickname_input)
        button_widget.setLayout(button_layout)
        self.content_layout.addWidget(button_widget)
        self.setStyleSheet("background-color: rgb(177,147,209);")
        self.setMaximumWidth(500)
        self.setMaximumHeight(350)  # Increased to accommodate buttons

    def display_gym_pokemon_fainted(self):
        """Display fainted gym pokemon with Next Pokemon button"""
        # Clear only the content area, not the button bar
        self.clear_layout(self.content_layout)

        # Get gym battle info
        conf = _ankimon_get_col_conf()
        if not conf:
            return

        enemy_ids = conf.get("ankimon_gym_enemy_ids") or []
        current_idx = int(conf.get("ankimon_gym_enemy_index") or 0)
        gym_leader_name = conf.get("ankimon_gym_leader_name") or "Gym Leader"

        # Calculate how many pokemon are left
        remaining = len(enemy_ids) - (current_idx + 1)

        # Create display widget
        global name, id, frontdefault, pokedex_image_path

        # Display the fainted Pokémon image
        pkmnimage_file = f"{id}.png"
        pkmnimage_path = frontdefault / pkmnimage_file
        pkmnimage_label = QLabel()
        pkmnpixmap = QPixmap()
        pkmnpixmap.load(str(pkmnimage_path))
        pkmnpixmap_bckg = QPixmap()
        pkmnpixmap_bckg.load(str(pokedex_image_path))
        pkmnpixmap = pkmnpixmap.scaled(230, 230)

        # Create a painter to add text on top of the image
        painter = QPainter(pkmnpixmap_bckg)
        painter.drawPixmap(15, 15, pkmnpixmap)

        # Draw fainted text (load position from config, defaults to 270, 100)
        conf = _ankimon_get_col_conf()
        fainted_x = int(conf.get("ankimon_fainted_text_x", 270)) if conf else 270
        fainted_y = int(conf.get("ankimon_fainted_text_y", 100)) if conf else 100

        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 0, 0))  # Red color for "FAINTED"
        painter.drawText(fainted_x, fainted_y, "FAINTED!")

        # Draw remaining pokemon count or complete message (each with independent positioning)
        font.setPointSize(16)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))  # Black color
        if remaining > 0:
            # Gym leader name position (independent)
            leader_x = int(conf.get("ankimon_gym_leader_name_x", 270)) if conf else 270
            leader_y = int(conf.get("ankimon_gym_leader_name_y", 150)) if conf else 150
            painter.drawText(leader_x, leader_y, f"{gym_leader_name}")

            # Remaining text position (independent)
            remaining_x = int(conf.get("ankimon_gym_remaining_text_x", 270)) if conf else 270
            remaining_y = int(conf.get("ankimon_gym_remaining_text_y", 180)) if conf else 180
            painter.drawText(remaining_x, remaining_y, f"{remaining} Pokémon left")
        else:
            # Complete text position (independent)
            complete_x = int(conf.get("ankimon_gym_complete_text_x", 270)) if conf else 270
            complete_y = int(conf.get("ankimon_gym_complete_text_y", 150)) if conf else 150
            painter.drawText(complete_x, complete_y, "Gym Complete!")

        painter.end()
        pkmnimage_label.setPixmap(pkmnpixmap_bckg)
        pkmnimage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(pkmnimage_label)

        # Create button widget
        button_widget = QWidget()
        button_layout = QHBoxLayout()

        if remaining > 0:
            # Next Pokemon button
            next_button = QPushButton("▶ Next Pokémon")
            next_button.setFixedSize(200, 40)
            next_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            next_button.setStyleSheet("""
                QPushButton {
                    background-color: rgb(76, 175, 80);
                    color: white;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: rgb(56, 142, 60);
                }
            """)
            qconnect(next_button.clicked, lambda: spawn_next_gym_pokemon())
            button_layout.addWidget(next_button)
        else:
            # Gym Complete button
            complete_button = QPushButton("Gym Complete!")
            complete_button.setFixedSize(200, 40)
            complete_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            complete_button.setStyleSheet("""
                QPushButton {
                    background-color: rgb(255, 215, 0);
                    color: black;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: rgb(218, 165, 32);
                }
            """)
            qconnect(complete_button.clicked, lambda: complete_gym_battle())
            button_layout.addWidget(complete_button)

        button_widget.setLayout(button_layout)
        self.content_layout.addWidget(button_widget)

        self.setStyleSheet("background-color: rgb(177,147,209);")
        self.setMaximumWidth(500)
        self.setMaximumHeight(400)  # Increased to accommodate buttons

    def display_elite_four_pokemon_fainted(self):
        """Display fainted Elite Four pokemon with Next Pokemon button - mirrors gym flow"""
        # Clear only the content area, not the button bar
        self.clear_layout(self.content_layout)

        # Get Elite Four battle info
        conf = _ankimon_get_col_conf()
        if not conf:
            return

        enemy_ids = conf.get("ankimon_elite_four_enemy_ids") or []
        current_idx = int(conf.get("ankimon_elite_four_pokemon_index") or 0)
        member_name = conf.get("ankimon_elite_four_member_name") or "Elite Four Member"

        # Calculate how many pokemon are left
        remaining = len(enemy_ids) - (current_idx + 1)

        # Create display widget
        global name, id, frontdefault, pokedex_image_path

        # Display the fainted Pokémon image
        pkmnimage_file = f"{id}.png"
        pkmnimage_path = frontdefault / pkmnimage_file
        pkmnimage_label = QLabel()
        pkmnpixmap = QPixmap()
        pkmnpixmap.load(str(pkmnimage_path))
        pkmnpixmap_bckg = QPixmap()
        pkmnpixmap_bckg.load(str(pokedex_image_path))
        pkmnpixmap = pkmnpixmap.scaled(230, 230)

        # Create a painter to add text on top of the image
        painter = QPainter(pkmnpixmap_bckg)
        painter.drawPixmap(15, 15, pkmnpixmap)

        # Draw fainted text (load position from config)
        fainted_x = int(conf.get("ankimon_fainted_text_x", 270)) if conf else 270
        fainted_y = int(conf.get("ankimon_fainted_text_y", 100)) if conf else 100

        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 0, 0))
        painter.drawText(fainted_x, fainted_y, "FAINTED!")

        # Draw remaining pokemon count or complete message
        font.setPointSize(16)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))
        if remaining > 0:
            # Elite Four member name position
            leader_x = int(conf.get("ankimon_gym_leader_name_x", 270)) if conf else 270
            leader_y = int(conf.get("ankimon_gym_leader_name_y", 150)) if conf else 150
            painter.drawText(leader_x, leader_y, f"{member_name}")

            # Remaining text position
            remaining_x = int(conf.get("ankimon_gym_remaining_text_x", 270)) if conf else 270
            remaining_y = int(conf.get("ankimon_gym_remaining_text_y", 180)) if conf else 180
            painter.drawText(remaining_x, remaining_y, f"{remaining} Pokémon left")
        else:
            # Complete text position
            complete_x = int(conf.get("ankimon_gym_complete_text_x", 270)) if conf else 270
            complete_y = int(conf.get("ankimon_gym_complete_text_y", 150)) if conf else 150
            painter.drawText(complete_x, complete_y, f"{member_name} defeated!")

        painter.end()
        pkmnimage_label.setPixmap(pkmnpixmap_bckg)
        pkmnimage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(pkmnimage_label)

        # Create button widget
        button_widget = QWidget()
        button_layout = QHBoxLayout()

        if remaining > 0:
            # Next Pokemon button
            next_button = QPushButton("▶ Next Pokémon")
            next_button.setFixedSize(200, 40)
            next_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            next_button.setStyleSheet("""
                QPushButton {
                    background-color: rgb(76, 175, 80);
                    color: white;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: rgb(56, 142, 60);
                }
            """)
            qconnect(next_button.clicked, lambda: spawn_next_elite_four_pokemon())
            button_layout.addWidget(next_button)
        else:
            # Elite Four Member Complete button
            complete_button = QPushButton(f"{member_name} Complete!")
            complete_button.setFixedSize(250, 40)
            complete_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            complete_button.setStyleSheet("""
                QPushButton {
                    background-color: rgb(255, 215, 0);
                    color: black;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: rgb(218, 165, 32);
                }
            """)
            qconnect(complete_button.clicked, lambda: complete_elite_four_member())
            button_layout.addWidget(complete_button)

        button_widget.setLayout(button_layout)
        self.content_layout.addWidget(button_widget)

        self.setStyleSheet("background-color: rgb(177,147,209);")
        self.setMaximumWidth(500)
        self.setMaximumHeight(400)

    def display_champion_pokemon_fainted(self):
        """Display fainted Champion pokemon with Next Pokemon button - mirrors gym flow"""
        # Clear only the content area, not the button bar
        self.clear_layout(self.content_layout)

        # Get Champion battle info
        conf = _ankimon_get_col_conf()
        if not conf:
            return

        enemy_ids = conf.get("ankimon_champion_enemy_ids") or []
        current_idx = int(conf.get("ankimon_champion_pokemon_index") or 0)

        # Calculate how many pokemon are left
        remaining = len(enemy_ids) - (current_idx + 1)

        # Create display widget
        global name, id, frontdefault, pokedex_image_path

        # Display the fainted Pokémon image
        pkmnimage_file = f"{id}.png"
        pkmnimage_path = frontdefault / pkmnimage_file
        pkmnimage_label = QLabel()
        pkmnpixmap = QPixmap()
        pkmnpixmap.load(str(pkmnimage_path))
        pkmnpixmap_bckg = QPixmap()
        pkmnpixmap_bckg.load(str(pokedex_image_path))
        pkmnpixmap = pkmnpixmap.scaled(230, 230)

        # Create a painter to add text on top of the image
        painter = QPainter(pkmnpixmap_bckg)
        painter.drawPixmap(15, 15, pkmnpixmap)

        # Draw fainted text (load position from config)
        fainted_x = int(conf.get("ankimon_fainted_text_x", 270)) if conf else 270
        fainted_y = int(conf.get("ankimon_fainted_text_y", 100)) if conf else 100

        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 0, 0))
        painter.drawText(fainted_x, fainted_y, "FAINTED!")

        # Draw remaining pokemon count or complete message
        font.setPointSize(16)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))
        if remaining > 0:
            # Champion name position
            leader_x = int(conf.get("ankimon_gym_leader_name_x", 270)) if conf else 270
            leader_y = int(conf.get("ankimon_gym_leader_name_y", 150)) if conf else 150
            painter.drawText(leader_x, leader_y, "Champion Cynthia")

            # Remaining text position
            remaining_x = int(conf.get("ankimon_gym_remaining_text_x", 270)) if conf else 270
            remaining_y = int(conf.get("ankimon_gym_remaining_text_y", 180)) if conf else 180
            painter.drawText(remaining_x, remaining_y, f"{remaining} Pokémon left")
        else:
            # Complete text position
            complete_x = int(conf.get("ankimon_gym_complete_text_x", 270)) if conf else 270
            complete_y = int(conf.get("ankimon_gym_complete_text_y", 150)) if conf else 150
            painter.drawText(complete_x, complete_y, "Champion defeated!")

        painter.end()
        pkmnimage_label.setPixmap(pkmnpixmap_bckg)
        pkmnimage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(pkmnimage_label)

        # Create button widget
        button_widget = QWidget()
        button_layout = QHBoxLayout()

        if remaining > 0:
            # Next Pokemon button
            next_button = QPushButton("▶ Next Pokémon")
            next_button.setFixedSize(200, 40)
            next_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            next_button.setStyleSheet("""
                QPushButton {
                    background-color: rgb(76, 175, 80);
                    color: white;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: rgb(56, 142, 60);
                }
            """)
            qconnect(next_button.clicked, lambda: spawn_next_champion_pokemon())
            button_layout.addWidget(next_button)
        else:
            # Champion Complete button
            complete_button = QPushButton("Champion Defeated!")
            complete_button.setFixedSize(250, 40)
            complete_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            complete_button.setStyleSheet("""
                QPushButton {
                    background-color: rgb(255, 215, 0);
                    color: black;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: rgb(218, 165, 32);
                }
            """)
            qconnect(complete_button.clicked, lambda: complete_champion_battle())
            button_layout.addWidget(complete_button)

        button_widget.setLayout(button_layout)
        self.content_layout.addWidget(button_widget)

        self.setStyleSheet("background-color: rgb(177,147,209);")
        self.setMaximumWidth(500)
        self.setMaximumHeight(400)

    def keyPressEvent(self, event):
        global test, pokemon_encounter, pokedex_image_path, system, ankimon_key
        open_window_key = getattr(Qt.Key, 'Key_' + ankimon_key.upper())
        if system == "mac":
            if event.key() == open_window_key and event.modifiers() == Qt.KeyboardModifier.MetaModifier:
                self.close()
        else:
            if event.key() == open_window_key and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.close()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def closeEvent(self,event):
        global pkmn_window
        pkmn_window = False

# Create an instance of the MainWindow
test_window = TestWindow()
_ankimon_register_window("test_window", test_window)

#Test window
def rate_this_addon():
    global rate_this, rate_path, itembag_path
    # Load rate data
    with open(rate_path, 'r') as file:
        rate_data = json.load(file)
        rate_this = rate_data.get("rate_this", False)
    
    # Check if rating is needed
    if not rate_this:
        rate_window = QDialog()
        rate_window.setWindowTitle("Please Rate this Addon!")
        
        layout = QVBoxLayout(rate_window)
        
        text_label = QLabel("""Thanks for using Ankimon! 
                            \nI would like Ankimon to be known even more in the community, 
                            \nand a rating would be amazing. Letting others know what you think of the addon.
                            \nThis takes less than a minute.

                            \nIf you do not want to rate this addon. Feel free to press: I dont want to rate this addon.
                            """)
        layout.addWidget(text_label)
        
        # Rate button
        rate_button = QPushButton("Rate Now")
        dont_show_button = QPushButton("I dont want to rate this addon.")

        def support_button_click():
            support_url = "https://ko-fi.com/unlucky99"
            QDesktopServices.openUrl(QUrl(support_url))
        
        def thankyou_message():
            thankyou_window = QDialog()
            thankyou_window.setWindowTitle("Thank you !") 
            thx_layout = QVBoxLayout(thankyou_window)
            thx_label = QLabel("""
            Thank you for Rating this Addon !
                               
            Please exit this window!
            """)
            thx_layout.addWidget(thx_label)
            # Support button
            support_button = QPushButton("Support the Author")
            support_button.clicked.connect(support_button_click)
            thx_layout.addWidget(support_button)
            thankyou_window.setModal(True)
            thankyou_window.exec()
        
        def dont_show_this_button():
            rate_window.close()
            rate_data["rate_this"] = True
            # Save the updated data back to the file
            with open(rate_path, 'w') as file:
                json.dump(rate_data, file, indent=4)
            showInfo("""This Pop Up wont turn up on startup anymore.
            If you decide to rate this addon later on.
            You can go to Ankimon => Rate This.
            Anyway, have fun playing !
            """)

        def rate_this_button():
            rate_window.close()
            rate_url = "https://ankiweb.net/shared/review/1908235722"
            QDesktopServices.openUrl(QUrl(rate_url))
            thankyou_message()
            rate_data["rate_this"] = True
            # Save the updated data back to the file
            with open(rate_path, 'w') as file:
                json.dump(rate_data, file, indent=4)
                test_window.rate_display_item("potion")
                # add item to item list
                try:
                    with open(itembag_path, 'r') as json_file:
                        itembag_list = json.load(json_file)
                except (FileNotFoundError, json.JSONDecodeError):
                    # Create empty items list if file doesn't exist
                    itembag_list = []
                itembag_list.append("potion")
                with open(itembag_path, 'w') as json_file:
                    json.dump(itembag_list, json_file)
        rate_button.clicked.connect(rate_this_button)
        layout.addWidget(rate_button)

        dont_show_button.clicked.connect(dont_show_this_button)
        layout.addWidget(dont_show_button)
        
        # Support button
        support_button = QPushButton("Support the Author")
        support_button.clicked.connect(support_button_click)
        layout.addWidget(support_button)
        
        # Make the dialog modal to wait for user interaction
        rate_window.setModal(True)
        
        # Execute the dialog
        rate_window.exec()


if database_complete is True:
    try:
        with open(badgebag_path, 'r') as json_file:
            badge_list = json.load(json_file)
            if len(badge_list) > 2:
                rate_this_addon()
    except FileNotFoundError:
        # First-time setup - badges.json doesn't exist yet
        pass
    except Exception:
        # Other errors - skip rating check
        pass

#Badges needed for achievements:
with open(badges_list_path, 'r') as json_file:
    badges = json.load(json_file)

achievements = {str(i): False for i in range(1, 69)}

def check_badges(achievements):
        try:
            with open(badgebag_path, 'r') as json_file:
                badge_list = json.load(json_file)
                for badge_num in badge_list:
                    achievements[str(badge_num)] = True
        except FileNotFoundError:
            # First-time setup - badges.json doesn't exist yet
            pass
        except Exception:
            # Other errors - skip badge check
            pass
        return achievements

def check_for_badge(achievements, rec_badge_num):
        achievements = check_badges(achievements)
        if achievements[str(rec_badge_num)] is False:
            got_badge = False
        else:
            got_badge = True
        return got_badge
        
def save_badges(badges_collection):
        with open(badgebag_path, 'w') as json_file:
            json.dump(badges_collection, json_file)

achievements = check_badges(achievements)

def receive_badge(badge_num,achievements):
    achievements = check_badges(achievements)
    #for badges in badge_list:
    achievements[str(badge_num)] = True
    badges_collection = []
    for num in range(1,69):
        if achievements[str(num)] is True:
            badges_collection.append(int(num))
    save_badges(badges_collection)
    return achievements


class StarterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        #self.update()

    def init_ui(self):
        global test
        basic_layout = QVBoxLayout()
        # Set window
        self.setWindowTitle('Choose a Starter')
        self.setLayout(basic_layout)
        self.starter = False

    def open_dynamic_window(self):
        self.show()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
    def keyPressEvent(self, event):
        global test, pokemon_encounter, pokedex_image_path
        # Close the main window when the spacebar is pressed
        if event.key() == Qt.Key.Key_G:  # Updated to Key_G for PyQt 6
            # First encounter image
            if not self.starter:
                self.display_starter_pokemon()
            # If self.starter is True, simply pass (do nothing)
            else:
                pass

    def display_starter_pokemon(self):
        self.setMaximumWidth(512)
        self.setMaximumHeight(320)
        self.clear_layout(self.layout())
        layout = self.layout()
        water_start, fire_start, grass_start = get_random_starter()
        starter_label = self.pokemon_display_starter(water_start, fire_start, grass_start)
        self.water_starter_button, self.fire_starter_button, self.grass_start_button = self.pokemon_display_starter_buttons(water_start, fire_start, grass_start)
        layout.addWidget(starter_label)
        button_widget = QWidget()
        layout_buttons = QHBoxLayout()
        layout_buttons.addWidget(self.water_starter_button)
        layout_buttons.addWidget(self.fire_starter_button)
        layout_buttons.addWidget(self.grass_start_button)
        button_widget.setLayout(layout_buttons)
        layout.addWidget(button_widget)
        self.setStyleSheet("background-color: rgb(14,14,14);")
        self.setLayout(layout)
        self.show()
        
    def display_chosen_starter_pokemon(self, starter_name):
        self.clear_layout(self.layout())
        layout = self.layout()
        starter_label = self.pokemon_display_chosen_starter(starter_name)
        layout.addWidget(starter_label)
        self.setStyleSheet("background-color: rgb(14,14,14);")
        self.setLayout(layout)
        self.setMaximumWidth(512)
        self.setMaximumHeight(340)
        self.show()
        self.starter = True
        showInfo("You have chosen your Starter Pokemon ! \n You can now close this window ! \n Please restart your Anki to restart your Pokemon Journey!")
        global achievments
        check = check_for_badge(achievements,7)
        if check is False:
            receive_badge(7,achievements)
            test_window.display_badge(7)
    
    def display_fossil_pokemon(self, fossil_id, fossil_name):
        self.clear_layout(self.layout())
        layout = self.layout()
        fossil_label = self.pokemon_display_fossil_pokemon(fossil_id, fossil_name)
        layout.addWidget(fossil_label)
        self.setStyleSheet("background-color: rgb(14,14,14);")
        self.setLayout(layout)
        self.setMaximumWidth(512)
        self.setMaximumHeight(340)
        self.show()
        self.starter = True
        showInfo("You have received your Fossil Pokemon ! \n You can now close this window !")
        global achievments
        check = check_for_badge(achievements,19)
        if check is False:
            receive_badge(19,achievements)
            test_window.display_badge(19)

    def pokemon_display_starter_buttons(self, water_start, fire_start, grass_start):
        # Create buttons for catching and killing the Pokémon
        water_starter_button = QPushButton(f"{(water_start).capitalize()}")
        water_starter_button.setFont(QFont("Arial",12))  # Adjust the font size and style as needed
        water_starter_button.setStyleSheet("background-color: rgb(44,44,44);")
        #qconnect(water_starter_button.clicked, choose_pokemon)
        qconnect(water_starter_button.clicked, lambda: choose_pokemon(water_start))

        fire_starter_button = QPushButton(f"{(fire_start).capitalize()}")
        fire_starter_button.setFont(QFont("Arial", 12))  # Adjust the font size and style as needed
        fire_starter_button.setStyleSheet("background-color: rgb(44,44,44);")
        #qconnect(fire_starter_button.clicked, choose_pokemon)
        qconnect(fire_starter_button.clicked, lambda: choose_pokemon(fire_start))
        # Set the merged image as the pixmap for the QLabel

        grass_start_button = QPushButton(f"{(grass_start).capitalize()}")
        grass_start_button.setFont(QFont("Arial", 12))  # Adjust the font size and style as needed
        grass_start_button.setStyleSheet("background-color: rgb(44,44,44);")
        #qconnect(grass_start_button.clicked, choose_pokemon)
        qconnect(grass_start_button.clicked, lambda: choose_pokemon(grass_start))
        # Set the merged image as the pixmap for the QLabel

        return water_starter_button, fire_starter_button, grass_start_button

    def pokemon_display_starter(self, water_start, fire_start, grass_start):
        global pokemon_encounter
        global addon_dir
        global frontdefault
        bckgimage_path = addon_dir / "addon_sprites" / "starter_screen" / "bckg.png"
        water_id = int(search_pokedex(water_start, "num"))
        grass_id = int(search_pokedex(grass_start, "num"))
        fire_id = int(search_pokedex(fire_start, "num"))

        # Load the background image
        pixmap_bckg = QPixmap()
        pixmap_bckg.load(str(bckgimage_path))

        # Display the Pokémon image
        water_path = frontdefault / f"{water_id}.png"
        water_label = QLabel()
        water_pixmap = QPixmap()
        water_pixmap.load(str(water_path))

        # Display the Pokémon image
        fire_path = frontdefault / f"{fire_id}.png"
        fire_label = QLabel()
        fire_pixmap = QPixmap()
        fire_pixmap.load(str(fire_path))

        # Display the Pokémon image
        grass_path = frontdefault / f"{grass_id}.png"
        grass_label = QLabel()
        grass_pixmap = QPixmap()
        grass_pixmap.load(str(grass_path))

        def resize_pixmap_img(pixmap):
            max_width = 150
            original_width = pixmap.width()
            original_height = pixmap.height()
            new_width = max_width
            new_height = (original_height * max_width) // original_width
            pixmap2 = pixmap.scaled(new_width, new_height)
            return pixmap2

        water_pixmap = resize_pixmap_img(water_pixmap)
        fire_pixmap = resize_pixmap_img(fire_pixmap)
        grass_pixmap = resize_pixmap_img(grass_pixmap)

        # Merge the background image and the Pokémon image
        merged_pixmap = QPixmap(pixmap_bckg.size())
        merged_pixmap.fill(QColor(0, 0, 0, 0))  # RGBA where A (alpha) is 0 for full transparency
        #merged_pixmap.fill(Qt.transparent)
        # merge both images together
        painter = QPainter(merged_pixmap)
        # draw background to a specific pixel
        painter.drawPixmap(0, 0, pixmap_bckg)

        painter.drawPixmap(57,-5,water_pixmap)
        painter.drawPixmap(182,-5,fire_pixmap)
        painter.drawPixmap(311,-3,grass_pixmap)

        # custom font
        custom_font = load_custom_font(28)
        message_box_text = "Choose your Starter Pokemon"
        # Draw the text on top of the image
        # Adjust the font size as needed
        painter.setFont(custom_font)
        painter.setPen(QColor(255,255,255))  # Text color
        painter.drawText(110, 310, message_box_text)
        custom_font = load_custom_font(20)
        painter.setFont(custom_font)
        painter.drawText(10, 330, "Press G to change Generation")
        painter.end()
        # Set the merged image as the pixmap for the QLabel
        starter_label = QLabel()
        starter_label.setPixmap(merged_pixmap)

        return starter_label

    def pokemon_display_chosen_starter(self, starter_name):
        global pokemon_encounter
        global addon_dir
        global frontdefault
        bckgimage_path = addon_dir / "addon_sprites" / "starter_screen" / "bg.png"
        id = int(search_pokedex(starter_name, "num"))

        # Load the background image
        pixmap_bckg = QPixmap()
        pixmap_bckg.load(str(bckgimage_path))

        # Display the Pokémon image
        image_path = frontdefault / f"{id}.png"
        image_label = QLabel()
        image_pixmap = QPixmap()
        image_pixmap.load(str(image_path))
        image_pixmap = resize_pixmap_img(image_pixmap, 250)

        # Merge the background image and the Pokémon image
        merged_pixmap = QPixmap(pixmap_bckg.size())
        #merged_pixmap.fill(Qt.transparent)
        merged_pixmap.fill(QColor(0, 0, 0, 0))  # RGBA where A (alpha) is 0 for full transparency
        # merge both images together
        painter = QPainter(merged_pixmap)
        # draw background to a specific pixel
        painter.drawPixmap(0, 0, pixmap_bckg)
        painter.drawPixmap(125,10,image_pixmap)

        # custom font
        custom_font = load_custom_font(32)
        message_box_text = f"{(starter_name).capitalize()} was chosen as Starter !"
        # Draw the text on top of the image
        # Adjust the font size as needed
        painter.setFont(custom_font)
        painter.setPen(QColor(255,255,255))  # Text color
        painter.drawText(40, 290, message_box_text)
        painter.end()
        # Set the merged image as the pixmap for the QLabel
        starter_label = QLabel()
        starter_label.setPixmap(merged_pixmap)

        return starter_label
    
    def pokemon_display_fossil_pokemon(self, fossil_id, fossil_name):
        global pokemon_encounter
        global addon_dir
        global frontdefault
        bckgimage_path = addon_dir / "addon_sprites" / "starter_screen" / "bg.png"
        id = fossil_id

        # Load the background image
        pixmap_bckg = QPixmap()
        pixmap_bckg.load(str(bckgimage_path))

        # Display the Pokémon image
        image_path = frontdefault / f"{id}.png"
        image_label = QLabel()
        image_pixmap = QPixmap()
        image_pixmap.load(str(image_path))
        image_pixmap = resize_pixmap_img(image_pixmap, 250)

        # Merge the background image and the Pokémon image
        merged_pixmap = QPixmap(pixmap_bckg.size())
        #merged_pixmap.fill(Qt.transparent)
        merged_pixmap.fill(QColor(0, 0, 0, 0))  # RGBA where A (alpha) is 0 for full transparency
        # merge both images together
        painter = QPainter(merged_pixmap)
        # draw background to a specific pixel
        painter.drawPixmap(0, 0, pixmap_bckg)
        painter.drawPixmap(125,10,image_pixmap)

        # custom font
        custom_font = load_custom_font(32)
        message_box_text = f"{(fossil_name).capitalize()} was brought to life !"
        # Draw the text on top of the image
        # Adjust the font size as needed
        painter.setFont(custom_font)
        painter.setPen(QColor(255,255,255))  # Text color
        painter.drawText(40, 290, message_box_text)
        painter.end()
        # Set the merged image as the pixmap for the QLabel
        fossil_label = QLabel()
        fossil_label.setPixmap(merged_pixmap)

        return fossil_label

class EvoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        #self.open_dynamic_window()
        #self.display_evo_pokemon(name, prevo_name)
    def init_ui(self):
        basic_layout = QVBoxLayout()
        # Set window
        self.setWindowTitle('Your Pokemon is about to Evolve')
        self.setLayout(basic_layout)
    def open_dynamic_window(self):
        self.show()

    def display_evo_pokemon(self, pkmn_name, prevo_name):
        self.clear_layout(self.layout())
        layout = self.layout()
        pkmn_label = self.pokemon_display_evo(pkmn_name, prevo_name)
        layout.addWidget(pkmn_label)
        self.setStyleSheet("background-color: rgb(14,14,14);")
        self.setLayout(layout)
        self.setMaximumWidth(500)
        self.setMaximumHeight(300)
        self.show()

    def pokemon_display_evo(self, pkmn_name, prevo_name):
        global addon_dir, frontdefault
        bckgimage_path = addon_dir / "addon_sprites" / "starter_screen" / "bg.png"
        id = int(search_pokedex(pkmn_name.lower(), "num"))

        # Load the background image
        pixmap_bckg = QPixmap()
        pixmap_bckg.load(str(bckgimage_path))

        # Display the Pokémon image
        image_path = frontdefault / f"{id}.png"
        image_label = QLabel()
        image_pixmap = QPixmap()
        image_pixmap.load(str(image_path))
        image_pixmap = resize_pixmap_img(image_pixmap, 250)

        # Merge the background image and the Pokémon image
        merged_pixmap = QPixmap(pixmap_bckg.size())
        merged_pixmap.fill(QColor(0, 0, 0, 0))  # RGBA where A (alpha) is 0 for full transparency
        #merged_pixmap.fill(Qt.transparent)
        # merge both images together
        painter = QPainter(merged_pixmap)
        # draw background to a specific pixel
        painter.drawPixmap(0, 0, pixmap_bckg)
        painter.drawPixmap(125,10,image_pixmap)

        # custom font
        custom_font = load_custom_font(20)
        message_box_text = f"{(prevo_name).capitalize()} has evolved to {(pkmn_name).capitalize()} !"
        # Draw the text on top of the image
        # Adjust the font size as needed
        painter.setFont(custom_font)
        painter.setPen(QColor(255,255,255))  # Text color
        painter.drawText(40, 290, message_box_text)
        painter.end()
        # Set the merged image as the pixmap for the QLabel
        pkmn_label = QLabel()
        pkmn_label.setPixmap(merged_pixmap)

        return pkmn_label

    def display_pokemon_evo(self, pkmn_name):
        self.setMaximumWidth(600)
        self.setMaximumHeight(530)
        self.clear_layout(self.layout())
        layout = self.layout()
        pokemon_images, evolve_button, dont_evolve_button = self.pokemon_display_evo_pokemon(pkmn_name)
        layout.addWidget(pokemon_images)
        layout.addWidget(evolve_button)
        layout.addWidget(dont_evolve_button)
        self.setStyleSheet("background-color: rgb(44,44,44);")
        self.setLayout(layout)
        self.show()

    def pokemon_display_evo_pokemon(self, pkmn_name):
        global pokemon_hp, name, id, level, caught_pokemon, pkmnimgfolder, frontdefault, addon_dir, caught, evolve_image_path
        global mainpokemon_name, mainpokemon_id
        layout_pokemon = QHBoxLayout()
        # Update mainpokemon_evolution and handle evolution logic
        pokemon_evos = search_pokedex(pkmn_name.lower(), "evos")
        pkmn_id = int(search_pokedex(pkmn_name.lower(), "num"))
        try:
            if len(pokemon_evos) > 1:
                pokemon_evo = random.choice(pokemon_evos)
                pokemon_evo_id = int((search_pokedex(pokemon_evo.lower(), "num")))
            else:
                pokemon_evo = pokemon_evos[0]
                pokemon_evo_id = int((search_pokedex(pokemon_evo.lower(), "num")))
        except (IndexError, ValueError, TypeError) as e:
            showInfo(f"Error finding evolution details: {e}")
        window_title = (f"{pkmn_name.capitalize()} is evolving to {pokemon_evo.capitalize()} ?")
        # Display the Pokémon image
        pkmnimage_path = frontdefault / f"{pkmn_id}.png"
        #pkmnimage_path2 = addon_dir / frontdefault / f"{mainpokemon_prevo_id}.png"
        pkmnimage_path2 = frontdefault / f"{(pokemon_evo_id)}.png"
        #pkmnimage_label = QLabel()
        #pkmnimage_label2 = QLabel()
        pkmnpixmap = QPixmap()
        pkmnpixmap.load(str(pkmnimage_path))
        pkmnpixmap2 = QPixmap()
        pkmnpixmap2.load(str(pkmnimage_path2))
        pixmap_bckg = QPixmap()
        pixmap_bckg.load(str(evolve_image_path))
        # Calculate the new dimensions to maintain the aspect ratio
        max_width = 200
        original_width = pkmnpixmap.width()
        original_height = pkmnpixmap.height()

        if original_width > max_width:
            new_width = max_width
            new_height = (original_height * max_width) // original_width
            pkmnpixmap = pkmnpixmap.scaled(new_width, new_height)


        # Calculate the new dimensions to maintain the aspect ratio
        max_width = 200
        original_width = pkmnpixmap.width()
        original_height = pkmnpixmap.height()

        if original_width > max_width:
            new_width = max_width
            new_height = (original_height * max_width) // original_width
            pkmnpixmap2 = pkmnpixmap2.scaled(new_width, new_height)

        # Merge the background image and the Pokémon image
        merged_pixmap = QPixmap(pixmap_bckg.size())
        merged_pixmap.fill(QColor(0, 0, 0, 0))  # RGBA where A (alpha) is 0 for full transparency
        #merged_pixmap.fill(Qt.transparent)
        # merge both images together
        painter = QPainter(merged_pixmap)
        painter.drawPixmap(0,0,pixmap_bckg)
        painter.drawPixmap(255,70,pkmnpixmap)
        painter.drawPixmap(255,285,pkmnpixmap2)
        # Draw the text on top of the image
        font = QFont()
        font.setPointSize(12)  # Adjust the font size as needed
        painter.setFont(font)
        #fontlvl = QFont()
        #fontlvl.setPointSize(12)
        # Create a QPen object for the font color
        pen = QPen()
        pen.setColor(QColor(255, 255, 255))
        painter.setPen(pen)
        painter.drawText(150,35,f"{pkmn_name.capitalize()} is evolving to {pokemon_evo.capitalize()}")
        painter.drawText(95,430,"Please Choose to Evolve Your Pokemon or Cancel Evolution")
        # Capitalize the first letter of the Pokémon's name
        #name_label = QLabel(capitalized_name)
        painter.end()
        # Capitalize the first letter of the Pokémon's name

        # Create buttons for catching and killing the Pokémon
        evolve_button = QPushButton("Evolve Pokémon")
        dont_evolve_button = QPushButton("Cancel Evolution")
        qconnect(evolve_button.clicked, lambda: evolve_pokemon(pkmn_name))
        qconnect(dont_evolve_button.clicked, lambda: cancel_evolution(pkmn_name))

        # Set the merged image as the pixmap for the QLabel
        evo_image_label = QLabel()
        evo_image_label.setPixmap(merged_pixmap)

        return evo_image_label, evolve_button, dont_evolve_button

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

# Create an instance of the MainWindow
starter_window = StarterWindow()

evo_window = EvoWindow()
# Erstellen einer Klasse, die von QObject erbt und die eventFilter Methode überschreibt
class MyEventFilter(QObject):
    def eventFilter(self, obj, event):
        if obj is mw and event.type() == QEvent.Type.KeyPress:
            global system, ankimon_key
            open_window_key = getattr(Qt.Key, 'Key_' + ankimon_key.upper())
            if system == "mac":
                if event.key() == open_window_key and event.modifiers() == Qt.KeyboardModifier.MetaModifier:
                    if test_window.isVisible():
                        test_window.close()  # Testfenster schließen, wenn Shift gedrückt wird
                    else:
                        if first_start == False:
                            test_window.display_first_start_up()
                        else:
                            test_window.open_dynamic_window()
            else:
                if event.key() == open_window_key and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    if test_window.isVisible():
                        test_window.close()  # Testfenster schließen, wenn Shift gedrückt wird
                    else:
                        if first_start == False:
                            test_window.display_first_start_up()
                        else:
                            test_window.open_dynamic_window()
        return False  # Andere Event-Handler nicht blockieren

# Erstellen und Installieren des Event Filters
event_filter = MyEventFilter()
mw.installEventFilter(event_filter)

class TableWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Pokémon Type Effectiveness Table")
        global addon_dir
        global eff_chart_html_path

        # Create a label and set HTML content
        label = QLabel()
        html_content = self.read_html_file(f"{eff_chart_html_path}")  # Replace with the path to your HTML file
        label.setText(html_content)  # 'html_table' contains the HTML table string
        label.setWordWrap(True)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)
    def read_html_file(self, file_path):
        """Reads an HTML file and returns its content as a string."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    def show_eff_chart(self):
        self.show()

class Pokedex_Widget(QWidget):
    def __init__(self):
        super().__init__()
        self.read_poke_coll()
        self.initUI()

    def read_poke_coll(self):
        global mypokemon_path
        try:
            with (open(mypokemon_path, "r") as json_file):
                self.captured_pokemon_data = json.load(json_file)
        except FileNotFoundError:
            # First-time setup or no pokemon captured yet
            self.captured_pokemon_data = []
        except Exception:
            # Other errors - initialize as empty list
            self.captured_pokemon_data = []

    def initUI(self):
        self.setWindowTitle("Pokédex")
        global addon_dir

        # Create a label and set HTML content
        label = QLabel()
        pokedex_html_template = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pokédex</title>
        <style>
        .pokedex-table { width: 100%; border-collapse: collapse; }
        .pokedex-table th, .pokedex-table td { border: 1px solid #ddd; text-align: left; padding: 8px; }
        .pokedex-table tr:nth-child(even) { background-color: #f2f2f2; }
        .pokedex-table th { padding-top: 12px; padding-bottom: 12px; background-color: #4CAF50; color: white; }
        .pokemon-image { height: 50px; width: 50px; }
        .pokemon-gray { filter: grayscale(100%); }
        </style>
        </head>
        <body>
        <table class="pokedex-table">
        <tr>
            <th>No.</th>
            <th>Name</th>
            <th>Image</th>
        </tr>
        <!-- Table Rows Will Go Here -->
        </table>
        </body>
        </html>
        '''
        # Extract the IDs of the Pokémon listed in the JSON file
        self.available_pokedex_ids = {pokemon['id'] for pokemon in self.captured_pokemon_data}

        # Now we generate the HTML rows for each Pokémon in the range 1-898, graying out those not in the JSON file
        table_rows = [self.generate_table_row(i, i not in self.available_pokedex_ids) for i in range(1, 899)]

        # Combine the HTML template with the generated rows
        html_content = pokedex_html_template.replace('<!-- Table Rows Will Go Here -->', ''.join(table_rows))

        #html_content = self.read_html_file(f"{pokedex_html_path}")  # Replace with the path to your HTML file
        label.setText(html_content)  # 'html_table' contains the HTML table string
        label.setWordWrap(True)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)

    # Helper function to generate table rows
    def generate_table_row(self, pokedex_number, is_gray):
        name = f"Pokemon #{pokedex_number}" # Placeholder, actual name should be fetched from a database or API
        image_class = "pokemon-gray" if is_gray else ""
        return f'''
        <tr>
            <td>{pokedex_number}</td>
            <td>{name}</td>
            <td><img src="{pokedex_number}.png" alt="{name}" class="pokemon-image {image_class}" /></td>
        </tr>
        '''

    def read_html_file(self, file_path):
        """Reads an HTML file and returns its content as a string."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
        
    def show_pokedex(self):
        self.read_poke_coll()
        self.show()

class CompletePokedex(QWidget):
    """Complete Pokédex showing all pokemon with force encounter feature"""
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Complete Pokédex")
        global icon_path, pokedex_path, frontdefault
        self.setWindowIcon(QIcon(str(icon_path)))

        # Dark mode theme
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
        """)

        # Main layout
        main_layout = QVBoxLayout()

        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #e0e0e0; font-size: 14px; font-weight: bold;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter Pokémon name or ID...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                color: #e0e0e0;
                background-color: #2d2d2d;
                border: 2px solid #4a4a4a;
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #5a9fd4;
            }
        """)
        self.search_input.textChanged.connect(self.filter_pokemon)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        # Scroll area for pokemon list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.pokemon_layout = QVBoxLayout()
        scroll_widget.setLayout(self.pokemon_layout)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)
        self.setMinimumSize(800, 600)

        # Initialize lazy loading state
        self.all_pokemon = []
        self.caught_pokemon_ids = set()
        self.render_batch_size = 25  # Render 25 pokemon at a time
        self.render_index = 0
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self.render_next_batch)
        self.grid_layout = None
        self.current_row = 0
        self.current_col = 0
        self.max_cols = 3

        # Load all pokemon
        self.load_all_pokemon()

    def load_all_pokemon(self):
        """Load all pokemon from pokedex.json and caught pokemon from mypokemon.json"""
        try:
            # Load caught Pokemon IDs
            global mypokemon_path
            self.caught_pokemon_ids = set()
            try:
                with open(mypokemon_path, 'r') as file:
                    caught_pokemon = json.load(file)
                    if isinstance(caught_pokemon, list):
                        for pkmn in caught_pokemon:
                            if isinstance(pkmn, dict) and 'id' in pkmn:
                                self.caught_pokemon_ids.add(pkmn['id'])
            except (FileNotFoundError, json.JSONDecodeError):
                # No caught Pokemon yet or invalid file
                pass

            # Load all Pokemon from Pokedex
            with open(pokedex_path, 'r') as file:
                pokedex_dict = json.load(file)
            # Convert dict to list of pokemon objects
            # Filter to unique Pokemon IDs only (no duplicate forms)
            self.all_pokemon = []
            seen_ids = set()
            for pkmn_name, pkmn_data in pokedex_dict.items():
                if isinstance(pkmn_data, dict):
                    # Ensure num and name are in the data
                    if 'num' not in pkmn_data:
                        pkmn_data['num'] = 0
                    if 'name' not in pkmn_data:
                        pkmn_data['name'] = pkmn_name

                    # Only add if we haven't seen this Pokemon ID before
                    pkmn_id = pkmn_data['num']
                    if pkmn_id not in seen_ids and pkmn_id > 0:
                        seen_ids.add(pkmn_id)
                        self.all_pokemon.append(pkmn_data)
            # Sort by pokemon number
            self.all_pokemon.sort(key=lambda x: x.get('num', 0))

            # Start lazy loading instead of rendering all at once
            _ankimon_log("INFO", "AnkimonPokedex", f"Loaded {len(self.all_pokemon)} pokemon, starting lazy render...")
            self.start_lazy_display(self.all_pokemon)
        except Exception as e:
            error_label = QLabel(f"Error loading Pokédex: {str(e)}")
            error_label.setStyleSheet("color: #ff6b6b; font-size: 14px;")
            self.pokemon_layout.addWidget(error_label)
            _ankimon_log("ERROR", "AnkimonPokedex", f"Failed to load pokedex: {e}")

    def start_lazy_display(self, pokemon_list):
        """Start lazy loading display of pokemon"""
        # Stop any existing timer
        if self.render_timer.isActive():
            self.render_timer.stop()

        # Clear existing layout
        while self.pokemon_layout.count():
            item = self.pokemon_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

        # Create new grid layout
        self.grid_layout = QGridLayout()
        self.current_row = 0
        self.current_col = 0
        self.render_index = 0
        self.pokemon_to_display = pokemon_list

        # Show loading message initially
        loading_label = QLabel(f"Loading {len(pokemon_list)} Pokémon...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet("color: #5a9fd4; font-size: 16px; padding: 20px;")
        self.pokemon_layout.addWidget(loading_label)

        # Start rendering batches
        self.render_timer.start(1)  # 1ms intervals for fast rendering

    def render_next_batch(self):
        """Render next batch of pokemon"""
        if self.render_index >= len(self.pokemon_to_display):
            # Done rendering
            self.render_timer.stop()
            # Remove loading message if present
            if self.pokemon_layout.count() > 0:
                item = self.pokemon_layout.itemAt(0)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, QLabel) and "Loading" in widget.text():
                        widget.deleteLater()
            # Add grid to layout
            self.pokemon_layout.addLayout(self.grid_layout)
            _ankimon_log("INFO", "AnkimonPokedex", f"Finished rendering {len(self.pokemon_to_display)} pokemon")
            return

        # Render batch
        batch_end = min(self.render_index + self.render_batch_size, len(self.pokemon_to_display))
        for i in range(self.render_index, batch_end):
            pokemon = self.pokemon_to_display[i]
            card_widget = self.render_pokemon_card(pokemon)
            if card_widget:
                self.grid_layout.addWidget(card_widget, self.current_row, self.current_col)
                self.current_col += 1
                if self.current_col >= self.max_cols:
                    self.current_col = 0
                    self.current_row += 1

        self.render_index = batch_end
        _ankimon_log("INFO", "AnkimonPokedex", f"Rendered batch: {self.render_index}/{len(self.pokemon_to_display)}")

    def render_pokemon_card(self, pokemon):
        """Render a single pokemon card widget"""
        try:
            pkmn_id = pokemon.get('num')
            pkmn_name = pokemon.get('name', 'Unknown')

            if not pkmn_id or not pkmn_name:
                return None

            # Check if caught
            is_caught = pkmn_id in self.caught_pokemon_ids

            # Pokemon card widget with dark theme
            card_widget = QWidget()
            border_color = "#4CAF50" if is_caught else "#4a4a4a"
            card_widget.setStyleSheet(f"""
                QWidget {{
                    border: 2px solid {border_color};
                    border-radius: 8px;
                    padding: 10px;
                    background-color: #2d2d2d;
                }}
            """)
            card_layout = QVBoxLayout()

            # Caught indicator
            if is_caught:
                caught_label = QLabel("🔴 CAUGHT")
                caught_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                caught_label.setStyleSheet("""
                    color: #4CAF50;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 3px;
                    background-color: #1e4620;
                    border-radius: 4px;
                """)
                card_layout.addWidget(caught_label)

            # Pokemon image (lazy load - don't load until visible)
            img_label = QLabel()
            img_path = frontdefault / f"{pkmn_id}.png"
            if img_path.exists():
                try:
                    pixmap = QPixmap(str(img_path))
                    pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio)
                    img_label.setPixmap(pixmap)
                except:
                    img_label.setText("IMG")
                    img_label.setStyleSheet("color: #888;")
            else:
                img_label.setText("No Image")
                img_label.setStyleSheet("color: #888;")
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(img_label)

            # Pokemon name and ID
            info_label = QLabel(f"#{pkmn_id:03d} - {pkmn_name.capitalize()}")
            info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info_label.setStyleSheet("color: #e0e0e0; font-size: 14px; font-weight: bold;")
            card_layout.addWidget(info_label)

            # Type badges (keep this as it's quick)
            types = pokemon.get('types', [])
            if types:
                type_container = QHBoxLayout()
                type_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
                type_colors = {
                    'normal': '#A8A878', 'fire': '#F08030', 'water': '#6890F0',
                    'electric': '#F8D030', 'grass': '#78C850', 'ice': '#98D8D8',
                    'fighting': '#C03028', 'poison': '#A040A0', 'ground': '#E0C068',
                    'flying': '#A890F0', 'psychic': '#F85888', 'bug': '#A8B820',
                    'rock': '#B8A038', 'ghost': '#705898', 'dragon': '#7038F8',
                    'dark': '#705848', 'steel': '#B8B8D0', 'fairy': '#EE99AC'
                }
                for ptype in types[:2]:  # Limit to 2 types for performance
                    type_badge = QLabel(ptype.upper())
                    bg_color = type_colors.get(ptype.lower(), '#68A090')
                    type_badge.setStyleSheet(f"""
                        background-color: {bg_color};
                        color: white;
                        font-size: 10px;
                        font-weight: bold;
                        padding: 3px 8px;
                        border-radius: 10px;
                    """)
                    type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    type_container.addWidget(type_badge)
                card_layout.addLayout(type_container)

            # Add force encounter button (Developer Mode feature)
            if config and config.get("developer_mode_enabled", False):
                force_button = QPushButton("Force Encounter")
                force_button.setStyleSheet("""
                    QPushButton {
                        background-color: #5a9fd4;
                        color: white;
                        border-radius: 5px;
                        padding: 5px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #4a8fc4;
                    }
                """)
                force_button.clicked.connect(lambda checked, pid=pkmn_id: self.force_encounter(pid))
                card_layout.addWidget(force_button)

            card_widget.setLayout(card_layout)
            return card_widget

        except Exception as e:
            _ankimon_log("ERROR", "AnkimonPokedex", f"Failed to render card for {pokemon.get('name', '?')}: {e}")
            return None

    def clear_layout(self, layout):
        """Recursively clear a layout and all its children"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def display_pokemon(self, pokemon_list):
        """Display pokemon in a grid with detailed info"""
        # Clear existing layout - remove both widgets AND layouts
        while self.pokemon_layout.count():
            item = self.pokemon_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Clear the layout and its children
                self.clear_layout(item.layout())

        # Create grid layout for pokemon entries
        grid_layout = QGridLayout()
        row = 0
        col = 0
        max_cols = 3

        for pokemon in pokemon_list:
            try:
                pkmn_id = pokemon.get('num')
                pkmn_name = pokemon.get('name', 'Unknown')

                if not pkmn_id or not pkmn_name:
                    continue

                # Check if caught
                is_caught = pkmn_id in self.caught_pokemon_ids

                # Pokemon card widget with dark theme
                card_widget = QWidget()
                border_color = "#4CAF50" if is_caught else "#4a4a4a"
                card_widget.setStyleSheet(f"""
                    QWidget {{
                        border: 2px solid {border_color};
                        border-radius: 8px;
                        padding: 10px;
                        background-color: #2d2d2d;
                    }}
                """)
                card_layout = QVBoxLayout()

                # Caught indicator (Pokéball icon)
                if is_caught:
                    caught_label = QLabel("🔴 CAUGHT")
                    caught_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    caught_label.setStyleSheet("""
                        color: #4CAF50;
                        font-weight: bold;
                        font-size: 11px;
                        padding: 3px;
                        background-color: #1e4620;
                        border-radius: 4px;
                    """)
                    card_layout.addWidget(caught_label)

                # Pokemon image
                img_label = QLabel()
                img_path = frontdefault / f"{pkmn_id}.png"
                if img_path.exists():
                    pixmap = QPixmap(str(img_path))
                    pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio)
                    img_label.setPixmap(pixmap)
                else:
                    img_label.setText("No Image")
                    img_label.setStyleSheet("color: #888;")
                img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                card_layout.addWidget(img_label)

                # Pokemon name and ID
                info_label = QLabel(f"#{pkmn_id:03d} - {pkmn_name.capitalize()}")
                info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                info_label.setStyleSheet("color: #e0e0e0; font-size: 14px; font-weight: bold;")
                card_layout.addWidget(info_label)

                # Type badges
                types = pokemon.get('types', [])
                if types:
                    type_container = QHBoxLayout()
                    type_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    type_colors = {
                        'normal': '#A8A878', 'fire': '#F08030', 'water': '#6890F0',
                        'electric': '#F8D030', 'grass': '#78C850', 'ice': '#98D8D8',
                        'fighting': '#C03028', 'poison': '#A040A0', 'ground': '#E0C068',
                        'flying': '#A890F0', 'psychic': '#F85888', 'bug': '#A8B820',
                        'rock': '#B8A038', 'ghost': '#705898', 'dragon': '#7038F8',
                        'dark': '#705848', 'steel': '#B8B8D0', 'fairy': '#EE99AC'
                    }
                    for ptype in types:
                        type_badge = QLabel(ptype.upper())
                        bg_color = type_colors.get(ptype.lower(), '#68A090')
                        type_badge.setStyleSheet(f"""
                            background-color: {bg_color};
                            color: white;
                            font-size: 10px;
                            font-weight: bold;
                            padding: 3px 8px;
                            border-radius: 10px;
                        """)
                        type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        type_container.addWidget(type_badge)
                    card_layout.addLayout(type_container)

                # Base Stats
                base_stats = pokemon.get('baseStats', {})
                if base_stats:
                    stats_label = QLabel(f"HP: {base_stats.get('hp', '?')} | ATK: {base_stats.get('atk', '?')} | DEF: {base_stats.get('def', '?')}")
                    stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    stats_label.setStyleSheet("color: #b0b0b0; font-size: 11px;")
                    card_layout.addWidget(stats_label)

                # Abilities
                abilities = pokemon.get('abilities', {})
                if abilities:
                    ability_text = " / ".join([v for k, v in abilities.items() if k in ['0', '1', 'H']][:2])
                    ability_label = QLabel(f"{ability_text}")
                    ability_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    ability_label.setStyleSheet("color: #ffd700; font-size: 10px;")
                    ability_label.setWordWrap(True)
                    card_layout.addWidget(ability_label)

                # Height and Weight
                height = pokemon.get('heightm')
                weight = pokemon.get('weightkg')
                if height and weight:
                    hw_label = QLabel(f"{height}m | {weight}kg")
                    hw_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    hw_label.setStyleSheet("color: #90c090; font-size: 10px;")
                    card_layout.addWidget(hw_label)

                # Force Encounter button (only visible when Developer Mode is ON)
                encounter_btn = QPushButton("Force Encounter")
                encounter_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #5a9fd4;
                        color: white;
                        border-radius: 5px;
                        padding: 8px;
                        font-weight: bold;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #4a8fc4;
                    }
                    QPushButton:pressed {
                        background-color: #3a7fb4;
                    }
                """)
                encounter_btn.clicked.connect(lambda checked, pid=pkmn_id, pname=pkmn_name: self.force_encounter(pid, pname))

                # Check if Developer Mode is active
                try:
                    global developer_menu
                    if developer_menu and developer_menu.menuAction().isVisible():
                        encounter_btn.setVisible(True)
                    else:
                        encounter_btn.setVisible(False)
                except:
                    encounter_btn.setVisible(False)

                card_layout.addWidget(encounter_btn)

                card_widget.setLayout(card_layout)
                grid_layout.addWidget(card_widget, row, col)

                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

            except Exception as e:
                continue

        self.pokemon_layout.addLayout(grid_layout)

    def filter_pokemon(self):
        """Filter pokemon based on search text"""
        search_text = self.search_input.text().lower()

        if not search_text:
            # Show all pokemon with lazy loading
            self.start_lazy_display(self.all_pokemon)
            return

        # Filter pokemon by name or ID
        filtered = []
        for pokemon in self.all_pokemon:
            pkmn_name = pokemon.get('name', '').lower()
            pkmn_id = str(pokemon.get('num', ''))

            if search_text in pkmn_name or search_text in pkmn_id:
                filtered.append(pokemon)

        # Display filtered results with lazy loading
        self.start_lazy_display(filtered)

    def force_encounter(self, pokemon_id, pokemon_name):
        """Set the next wild encounter to be this specific pokemon with Normal/Shiny choice"""
        global forced_next_pokemon_id, forced_next_pokemon_shiny

        # Show dialog to choose Normal or Shiny
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Force Encounter: {pokemon_name.capitalize()}")
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton {
                background-color: #5a9fd4;
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 12px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #4a8fc4;
            }
            QPushButton:pressed {
                background-color: #3a7fb4;
            }
        """)

        layout = QVBoxLayout()

        # Question label
        question_label = QLabel(f"Choose encounter type for {pokemon_name.capitalize()}:")
        question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(question_label)

        # Button layout
        button_layout = QHBoxLayout()

        # Normal button
        normal_btn = QPushButton("Normal")
        normal_btn.clicked.connect(lambda: self._set_forced_encounter(pokemon_id, pokemon_name, False, dialog))
        button_layout.addWidget(normal_btn)

        # Shiny button
        shiny_btn = QPushButton("✨ Shiny")
        shiny_btn.clicked.connect(lambda: self._set_forced_encounter(pokemon_id, pokemon_name, True, dialog))
        button_layout.addWidget(shiny_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def _set_forced_encounter(self, pokemon_id, pokemon_name, is_shiny, dialog):
        """Helper method to set forced encounter and close dialog"""
        global forced_next_pokemon_id, forced_next_pokemon_shiny

        # Ensure pokemon_id is an integer
        try:
            forced_next_pokemon_id = int(pokemon_id)
        except (ValueError, TypeError):
            forced_next_pokemon_id = pokemon_id

        forced_next_pokemon_shiny = is_shiny

        # Debug log
        print(f"[Shiny] Force encounter set is_shiny={is_shiny} for id={forced_next_pokemon_id}")

        # Show confirmation tooltip
        shiny_text = " ✨ SHINY" if is_shiny else ""
        tooltipWithColour(f"Force Encounter set: {pokemon_name.capitalize()}{shiny_text} (#{forced_next_pokemon_id})\nAnswer a card to trigger!", "#00FF00")

        # Close dialog
        dialog.accept()

        # Keep Pokédex open for easier testing/iteration

    def show_complete_pokedex(self):
        self.load_all_pokemon()
        self.show()

class IDTableWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Pokémon - Generations and ID")
        global table_gen_id_html_path
        # Create a label and set HTML content
        label = QLabel()
        html_content = self.read_html_file(f"{table_gen_id_html_path}")  # Replace with the path to your HTML file
        label.setText(html_content)  # 'html_table' contains the HTML table string
        label.setWordWrap(True)
        label.setStyleSheet("background-color: rgb(44,44,44);")
        # Layout
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)

    def read_html_file(self, file_path):
        """Reads an HTML file and returns its content as a string."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def show_gen_chart(self):
        self.show()

if database_complete!= False:
    if mypokemon_path.is_file() is False:
        starter_window.display_starter_pokemon()
    else:
        with open(mypokemon_path, 'r') as file:
            pokemon_list = json.load(file)
            if not pokemon_list :
                starter_window.display_starter_pokemon()

eff_chart = TableWidget()
pokedex = Pokedex_Widget()
complete_pokedex = CompletePokedex()
_ankimon_register_window("complete_pokedex", complete_pokedex)
gen_id_chart = IDTableWidget()

class License(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("AnkiMon License")
        global addon_dir

        # Create a label and set HTML content
        label = QLabel()
        html_content = self.read_html_file(f"{addon_dir}/license.html")  # Replace with the path to your HTML file
        # Create a QScrollArea to enable scrolling
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Create a layout for the scroll area using QGridLayout
        scroll_layout = QGridLayout()

        # Create a widget to hold the layout
        container = QWidget()

        label.setText(html_content)  # 'html_table' contains the HTML table string
        label.setWordWrap(True)

        # Layout
        #layout = QVBoxLayout()
        scroll_layout.addWidget(label)
        # Set the widget for the scroll area
        scroll_area.setWidget(container)

        # Set the layout for the container
        container.setLayout(scroll_layout)

        # Set the widget for the scroll area
        scroll_area.setWidget(container)

        # Add the scroll area to the dialog
        window_layout = QVBoxLayout()
        window_layout.addWidget(scroll_area)
        self.setLayout(window_layout)
    def read_html_file(self, file_path):
        """Reads an HTML file and returns its content as a string."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    def show_window(self):
        self.show()

license = License()

class Credits(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("AnkiMon License")
        global addon_dir

        # Create a label and set HTML content
        label = QLabel()
        html_content = self.read_html_file(f"{addon_dir}/credits.html")  # Replace with the path to your HTML file
        # Create a QScrollArea to enable scrolling
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Create a layout for the scroll area using QGridLayout
        scroll_layout = QGridLayout()

        # Create a widget to hold the layout
        container = QWidget()

        label.setText(html_content)  # 'html_table' contains the HTML table string
        label.setWordWrap(True)

        # Layout
        #layout = QVBoxLayout()
        scroll_layout.addWidget(label)
        # Set the widget for the scroll area
        scroll_area.setWidget(container)

        # Set the layout for the container
        container.setLayout(scroll_layout)

        # Set the widget for the scroll area
        scroll_area.setWidget(container)

        # Add the scroll area to the dialog
        window_layout = QVBoxLayout()
        window_layout.addWidget(scroll_area)
        self.setLayout(window_layout)
    def read_html_file(self, file_path):
        """Reads an HTML file and returns its content as a string."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    def show_window(self):
        self.show()

credits = Credits()

class ItemWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.read_item_file()
        self.initUI()

    def initUI(self):
        global icon_path
        self.hp_heal_items = {
            'potion': 20,
            'sweet-heart': 20,
            'berry-juice': 20,
            'fresh-water': 30,
            'soda-pop': 50,
            'super-potion': 60,
            'energy-powder': 60,
            'lemonade': 70,
            'moomoo-milk': 100,
            'hyper-potion': 120,
            'energy-root': 120,
            'full-restore': 1000,
            'max-potion': 1000
        }
        self.fossil_pokemon = {
            "helix-fossil": 138,
            "dome-fossil": 140,
            "old-amber": 142,
            "root-fossil": 345,
            "claw-fossil": 347,
            "skull-fossil": 408,
            "armor-fossil": 410,
            "cover-fossil": 564,
            "plume-fossil": 566
            }
        
        self.evolution_items = {

        }
        
        self.tm_hm_list = {

        }

        self.setWindowIcon(QIcon(str(icon_path))) # Add a Pokeball icon
        self.setWindowTitle("Itembag")
        self.layout = QVBoxLayout()  # Main layout is now a QVBoxLayout

        # Search Filter
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search Items...")
        self.search_edit.returnPressed.connect(self.filter_items)
        #self.search_edit.textChanged.connect(self.filter_pokemon)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.filter_items)

        # Add dropdown menu for generation filtering
        self.category = QComboBox()
        self.category.addItem("All")
        self.category.addItems(["Fossils", "TMs and HMs", "Heal", "Evolution Items"])
        self.category.currentIndexChanged.connect(self.filter_items)

        # Add widgets to layout
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(self.search_button)
        filter_layout.addWidget(self.category)
        self.layout.addLayout(filter_layout)

        # Create the scroll area and its properties
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)

        # Create a widget and layout for content inside the scroll area
        self.contentWidget = QWidget()
        self.contentLayout = QGridLayout()  # The layout for items
        self.contentWidget.setLayout(self.contentLayout)

        # Add the content widget to the scroll area
        self.scrollArea.setWidget(self.contentWidget)

        # Add the scroll area to the main layout
        self.layout.addWidget(self.scrollArea)
        self.setLayout(self.layout)
        self.resize(600, 500)

    def renewWidgets(self):
        self.read_item_file()
        # Clear the existing widgets from the content layout
        for i in reversed(range(self.contentLayout.count())):
            widget = self.contentLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        row, col = 0, 0
        max_items_per_row = 3

        if not self.itembag_list:  # Simplified check
            empty_label = QLabel("You don't own any items yet.")
            self.contentLayout.addWidget(empty_label, 1, 1)
        else:
            for item_name in self.itembag_list:
                item_widget = self.ItemLabel(item_name)
                self.contentLayout.addWidget(item_widget, row, col)
                col += 1
                if col >= max_items_per_row:
                    row += 1
                    col = 0
    
    def filter_items(self):
        self.read_item_file()
        search_text = self.search_edit.text().lower()
        category_index = self.category.currentIndex()
        # Clear the existing widgets from the content layout
        for i in reversed(range(self.contentLayout.count())):
            widget = self.contentLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        row, col = 0, 0
        max_items_per_row = 3

        if not self.itembag_list:  # Simplified check
            empty_label = QLabel("Empty Search")
            self.contentLayout.addWidget(empty_label, 1, 1)
        else:
            # Filter items based on category index
            if category_index == 1:  # Heal items
                filtered_items = [item_name for item_name in self.itembag_list if item_name in self.fossil_pokemon and search_text in item_name.lower()]
            elif category_index == 2:  # Heal items
                filtered_items = [item_name for item_name in self.itembag_list if item_name in self.tm_hm_list and search_text in item_name.lower()]
            elif category_index == 3:
                filtered_items = [item_name for item_name in self.itembag_list if item_name in self.hp_heal_items and search_text in item_name.lower()]
            elif category_index == 4:
                filtered_items = [item_name for item_name in self.itembag_list if item_name in self.evolution_items and search_text in item_name.lower()]
            else:
                filtered_items = [item_name for item_name in self.itembag_list if search_text in item_name.lower()]

            for item_name in filtered_items:
                item_widget = self.ItemLabel(item_name)
                self.contentLayout.addWidget(item_widget, row, col)
                col += 1
                if col >= max_items_per_row:
                    row += 1
                    col = 0

    def ItemLabel(self, item_name):
        item_file_path = items_path / f"{item_name}.png"
        item_frame = QVBoxLayout() #itemframe
        info_item_button = QPushButton("More Info")
        info_item_button.clicked.connect(lambda: self.more_info_button_act(item_name))
        item_name_for_label = item_name.replace("-", " ").replace("_", " ")   # Remove hyphens and underscores
        item_name_label = QLabel(f"{item_name_for_label.capitalize()}") #itemname
        item_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        item_picture_pixmap = QPixmap(str(item_file_path))
        item_picture_label = QLabel()
        item_picture_label.setPixmap(item_picture_pixmap)
        item_picture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        item_frame.addWidget(item_picture_label)
        item_frame.addWidget(item_name_label)
        item_name = item_name.lower()
        if item_name == "shadow-synergy-stone":
            # Special handling for Shadow Synergy Stone
            use_item_button = QPushButton("Challenge Shadow Mewtwo")
            use_item_button.setStyleSheet("""
                QPushButton {
                    background-color: #8B008B;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #9932CC;
                }
            """)
            use_item_button.clicked.connect(lambda: self.Use_Shadow_Synergy_Stone())
        elif item_name in self.hp_heal_items :
            use_item_button = QPushButton("Heal Mainpokemon")
            global mainpokemon_name
            hp_heal = self.hp_heal_items[item_name]
            use_item_button.clicked.connect(lambda: self.Check_Heal_Item(mainpokemon_name, hp_heal, item_name))
        elif item_name in self.fossil_pokemon:
            fossil_id = self.fossil_pokemon[item_name]
            fossil_pokemon_name = search_pokedex_by_id(fossil_id)
            use_item_button = QPushButton(f"Evolve Fossil to {fossil_pokemon_name.capitalize()}")
            use_item_button.clicked.connect(lambda: self.Evolve_Fossil(item_name, fossil_id, fossil_pokemon_name))
        else:
            # Create comboBox FIRST (before referencing it in lambda)
            comboBox = QComboBox()
            comboBox.addItem("Select Pokemon...", None)  # Default/placeholder
            self.PokemonList(comboBox)
            item_frame.addWidget(comboBox)

            # Determine button text based on item type
            is_exp_share = 'exp' in item_name and 'share' in item_name
            # Check if item is a mega stone (all mega stones end with "ite")
            is_mega_stone = item_name.lower().endswith('ite')

            if is_exp_share:
                button_text = "Assign EXP Share"
            elif is_mega_stone:
                button_text = "Assign Mega Stone"
            else:
                button_text = "Use Item"

            use_item_button = QPushButton(button_text)

            # Connect button with proper closure
            def _assign_item(*, _combo=comboBox, _item=item_name):
                selected_pokemon = _combo.currentText()
                if selected_pokemon == "Select Pokemon..." or not selected_pokemon:
                    showInfo("Please select a Pokemon first!")
                    return
                self.Check_Evo_Item(selected_pokemon, _item)
                # Refresh the ItemBag after assignment
                self.renewWidgets()

            use_item_button.clicked.connect(_assign_item)
        item_frame.addWidget(use_item_button)
        item_frame.addWidget(info_item_button)
        item_frame_widget = QWidget()
        item_frame_widget.setLayout(item_frame)

        return item_frame_widget

    def PokemonList(self, comboBox):
        try:
            with open(mypokemon_path, "r") as json_file:
                captured_pokemon_data = json.load(json_file)
                if captured_pokemon_data:
                    for pokemon in captured_pokemon_data:
                        pokemon_name = pokemon['name']
                        comboBox.addItem(f"{pokemon_name}")
        except:
            pass
    
    def Evolve_Fossil(self, item_name, fossil_id, fossil_poke_name):
        starter_window.display_fossil_pokemon(fossil_id, fossil_poke_name)
        save_outside_pokemon(fossil_poke_name, fossil_id)
        self.delete_item(item_name)


    def delete_item(self, item_name):
        self.read_item_file()
        if item_name in self.itembag_list:
            self.itembag_list.remove(item_name)
        self.write_item_file()
        self.renewWidgets()

    def Check_Heal_Item(self, pkmn_name, heal_points, item_name):
        global achievments
        check = check_for_badge(achievements,20)
        if check is False:
            receive_badge(20,achievements)
            test_window.display_badge(20)
        global mainpokemon_hp, mainpokemon_stats, mainpokemon_level, mainpokemon_ev, mainpokemon_iv
        mainpkmn_max_hp = calculate_hp(mainpokemon_stats["hp"], mainpokemon_level, mainpokemon_ev, mainpokemon_iv)
        if item_name == "fullrestore" or "maxpotion":
            heal_points = mainpkmn_max_hp
        mainpokemon_hp += heal_points
        if mainpokemon_hp > (mainpkmn_max_hp + 1):
            mainpokemon_hp = mainpkmn_max_hp
        self.delete_item(item_name)
        play_effect_sound("HpHeal")
        showInfo(f"{pkmn_name} was healed for {heal_points}")

    def Use_Shadow_Synergy_Stone(self):
        """Trigger Shadow Mewtwo encounter when stone is used"""
        global test_window, pkmn_window
        try:
            _ankimon_log("INFO", "ShadowMewtwo", "Shadow Synergy Stone used from item bag")

            # Close item bag
            self.close()

            # Open battle window if not already open
            if not pkmn_window:
                test_window.show()

            # Trigger the encounter
            success = _trigger_shadow_mewtwo_encounter()

            if success:
                # Battle started successfully
                _ankimon_log("INFO", "ShadowMewtwo", "Shadow Mewtwo encounter started from item bag")
            else:
                # Encounter failed or was cancelled
                _ankimon_log("INFO", "ShadowMewtwo", "Shadow Mewtwo encounter cancelled or failed")

        except Exception as e:
            _ankimon_log("ERROR", "ShadowMewtwo", f"Error using Shadow Synergy Stone: {e}")
            import traceback
            traceback.print_exc()
            showWarning(f"Error triggering Shadow Mewtwo encounter: {e}")

    def Check_Evo_Item(self, pkmn_name, item_name):
        try:
            # Debug logging
            print(f"[ItemBag] Check_Evo_Item called: pkmn_name={pkmn_name}, item_name={item_name}")

            # Check if it's EXP Share (held item, not evolution item)
            if "exp" in item_name.lower() and "share" in item_name.lower():
                # Check if another Pokemon already holds this item
                conflict_pokemon = self.check_item_holder(item_name)
                if conflict_pokemon and conflict_pokemon.lower() != pkmn_name.lower():
                    # Prompt to move item
                    from aqt.utils import askUser
                    move_item = askUser(f"EXP Share is currently held by {conflict_pokemon}.\nMove it to {pkmn_name.capitalize()}?")
                    if not move_item:
                        return
                    # Remove from previous holder
                    self.remove_held_item_from(conflict_pokemon)

                # Assign EXP Share to Pokemon
                self.assign_held_item(pkmn_name, item_name)
                self.delete_item(item_name)
                showInfo(f"{pkmn_name.capitalize()} is now holding EXP Share!\n{pkmn_name.capitalize()} will gain EXP when other Pokémon battle.")
                return

            # Check if it's a mega stone (clean names like "Ampharosite")
            if item_name.lower().endswith('ite'):
                try:
                    # Check if Mega Evolution is unlocked
                    mega_state = _load_mega_state()
                    if not mega_state.get("key_stone_unlocked", False):
                        showWarning("Mega Evolution is locked.\n\nDefeat the Champion to unlock the Key Stone and enable Mega Evolution!")
                        print("[Mega ItemBag] BLOCKED: Mega Evolution not unlocked yet")
                        return

                    # Stone name is just the item name
                    stone_name = item_name
                    print(f"[Mega ItemBag] Equipping mega stone: {stone_name} to {pkmn_name}")

                    # Get Pokemon ID and check if it matches the stone
                    pokemon_id = search_pokedex(pkmn_name.lower(), "num")
                    if pokemon_id is None:
                        showWarning(f"Item equip failed: Could not find Pokemon ID for {pkmn_name}")
                        print(f"[Mega ItemBag] ERROR: pokemon_id is None for {pkmn_name}")
                        return

                    expected_stone = _get_mega_stone_name(pokemon_id)
                    if expected_stone is None:
                        showWarning(f"Item equip failed: Could not determine mega stone for {pkmn_name}")
                        print(f"[Mega ItemBag] ERROR: expected_stone is None for pokemon_id {pokemon_id}")
                        return

                    # DEBUG: Show what we're comparing
                    print(f"[Mega ItemBag] VALIDATION CHECK:")
                    print(f"  - Pokemon: {pkmn_name} (ID: {pokemon_id})")
                    print(f"  - Stone from UI: '{stone_name}'")
                    print(f"  - Expected stone: '{expected_stone}'")
                    print(f"  - Lowercase match: '{stone_name.lower()}' == '{expected_stone.lower()}' = {stone_name.lower() == expected_stone.lower()}")

                    # CRITICAL FIX: Case-insensitive comparison
                    if stone_name.lower() == expected_stone.lower():
                        # Check if another Pokemon already holds this stone
                        conflict_pokemon = self.check_item_holder(item_name)
                        if conflict_pokemon and conflict_pokemon.lower() != pkmn_name.lower():
                            from aqt.utils import askUser
                            move_item = askUser(f"{expected_stone} is currently held by {conflict_pokemon}.\nMove it to {pkmn_name.capitalize()}?")
                            if not move_item:
                                return
                            self.remove_held_item_from(conflict_pokemon)

                        # Assign mega stone to Pokemon
                        self.assign_held_item(pkmn_name, item_name)
                        self.delete_item(item_name)
                        print(f"[Mega ItemBag] SUCCESS: Equipped {stone_name} to {pkmn_name}")
                        showInfo(f"{expected_stone} has been given to {pkmn_name.capitalize()}!\n{pkmn_name.capitalize()} can now Mega Evolve in battle!")
                    else:
                        print(f"[Mega ItemBag] REJECTION: Stone mismatch")
                        print(f"  - '{stone_name}' != '{expected_stone}'")
                        showInfo(f"{pkmn_name.capitalize()} cannot use {stone_name}.\nThis stone is for a different Pokemon.")
                    return
                except Exception as e:
                    error_msg = f"Item equip failed: {str(e)}"
                    showWarning(error_msg)
                    print(f"[Mega ItemBag] ERROR during mega stone equip: {e}")
                    import traceback
                    traceback.print_exc()
                    return

            # Handle evolution items
            evoName = search_pokedex(pkmn_name.lower(), "evos")
            evoName = f"{evoName[0]}"
            evoItem = search_pokedex(evoName.lower(), "evoItem")
            item_name_clean = item_name.replace("-", " ")  # Remove hyphens from item_name
            evoItem = str(evoItem).lower()
            if evoItem == item_name_clean:  # Corrected this line to assign the item_name to evoItem
                # Perform your action when the item matches the Pokémon's evolution item
                showInfo("Pokemon Evolution is fitting !")
                evo_window.display_pokemon_evo(pkmn_name)
            else:
                showInfo("This Pokemon does not need this item.")
        except Exception as e:
            showWarning(f"{e}")
    
    def check_item_holder(self, item_name):
        """Check if any Pokemon is currently holding this item"""
        try:
            global mypokemon_path
            with open(mypokemon_path, 'r') as file:
                pokemon_list = json.load(file)

            for pokemon in pokemon_list:
                if pokemon.get('held_item', '') == item_name:
                    return pokemon.get('name', 'Unknown')
            return None
        except Exception:
            return None

    def remove_held_item_from(self, pkmn_name):
        """Remove held item from a specific Pokemon"""
        try:
            global mypokemon_path
            with open(mypokemon_path, 'r') as file:
                pokemon_list = json.load(file)

            for pokemon in pokemon_list:
                if pokemon['name'].lower() == pkmn_name.lower():
                    pokemon['held_item'] = None
                    break

            with open(mypokemon_path, 'w') as file:
                json.dump(pokemon_list, file, indent=2)

        except Exception as e:
            print(f"Error removing held item: {e}")

    def assign_held_item(self, pkmn_name, item_name):
        """Assign a held item to a Pokemon and trigger Mega if it's a mega stone"""
        try:
            global mypokemon_path, pokecollection_win
            print(f"[ItemBag] assign_held_item called: pkmn_name={pkmn_name}, item_name={item_name}")

            with open(mypokemon_path, 'r') as file:
                pokemon_list = json.load(file)

            # Find the Pokemon and assign the item
            pokemon_found = False
            pokemon_obj = None
            for pokemon in pokemon_list:
                if pokemon['name'].lower() == pkmn_name.lower():
                    old_item = pokemon.get('held_item', 'None')
                    pokemon['held_item'] = item_name
                    pokemon_obj = pokemon
                    pokemon_found = True
                    print(f"[ItemBag] Updated {pkmn_name}: held_item changed from {old_item} to {item_name}")

                    # Check if this is a mega stone - if so, trigger instant mega evolution
                    if item_name and item_name.lower().endswith('ite'):
                        pokemon_id = pokemon.get('id')
                        if pokemon_id and pokemon_id in _get_mega_capable_pokemon_ids():
                            # Instant Mega Evolution (like dev toggle)
                            pokemon['is_mega'] = True
                            print(f"[Mega] {pkmn_name} instantly transformed into Mega form!")

                            # Play transition animation
                            try:
                                _play_mega_transition_animation(pkmn_name, pokemon_id)
                            except Exception as e:
                                print(f"[Mega] Transition animation failed: {e}")

                            # Show detailed popup (same as Dev Mode)
                            tooltipWithColour(f"⚡ {pkmn_name} is now MEGA!", "#FF00FF")
                            showInfo(f"✓ {pkmn_name} transformed to Mega form!\n\nStats boosted:\n• Outgoing damage: +25%\n• Incoming damage: -15%")
                        else:
                            pokemon['is_mega'] = False
                    break

            if not pokemon_found:
                print(f"[ItemBag] WARNING: Pokemon '{pkmn_name}' not found in collection!")
                return

            # Save the updated Pokemon data
            with open(mypokemon_path, 'w') as file:
                json.dump(pokemon_list, file, indent=2)
            print(f"[ItemBag] Pokemon data saved to {mypokemon_path}")

            # Refresh Pokemon collection dialog and itembag if they're open
            if pokemon_found:
                try:
                    global test_window, item_window
                    if pokecollection_win and pokecollection_win.isVisible():
                        pokecollection_win.refresh_pokemon_collection()
                        print(f"[ItemBag] Refreshed Pokemon collection dialog")
                    # Refresh itembag window if open
                    if item_window and item_window.isVisible():
                        item_window.renewWidgets()
                        print(f"[ItemBag] Refreshed itembag window after equip")
                    # Refresh external Ankimon window if open
                    if test_window and test_window.isVisible():
                        test_window.display_first_encounter()
                        print(f"[ItemBag] Refreshed external Ankimon window")
                except Exception as e:
                    print(f"[ItemBag] Window refresh error: {e}")

        except Exception as e:
            print(f"Error assigning held item: {e}")
            import traceback
            traceback.print_exc()

    def write_item_file(self):
        with open(itembag_path, 'w') as json_file:
            json.dump(self.itembag_list, json_file)

    def read_item_file(self):
        # Read the list from the JSON file
        try:
            with open(itembag_path, 'r') as json_file:
                self.itembag_list = json.load(json_file)
        except FileNotFoundError:
            # First-time setup - items.json doesn't exist yet
            self.itembag_list = []
        except Exception:
            # Other errors - initialize as empty list
            self.itembag_list = []

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def showEvent(self, event):
        # This method is called when the window is shown or displayed
        self.renewWidgets()

    def show_window(self):
        from aqt import mw
        # Get the geometry of the main screen
        main_screen_geometry = mw.geometry()
        
        # Calculate the position to center the ItemWindow on the main screen
        x = main_screen_geometry.center().x() - self.width() / 2
        y = main_screen_geometry.center().y() - self.height() / 2
        
        # Move the ItemWindow to the calculated position
        self.move(x, y)
        
        self.show()

    def more_info_button_act(self, item_name):
        description = get_id_and_description_by_item_name(item_name)
        showInfo(f"{description}")
    
def read_csv_file(csv_file):
    item_id_mapping = {}
    with open(csv_file, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            item_id_mapping[row['name'].lower()] = int(row['item_id'])
    return item_id_mapping

def capitalize_each_word(item_name):
    # Replace hyphens with spaces and capitalize each word
    return ' '.join(word.capitalize() for word in item_name.replace("-", " ").split())

def read_descriptions_csv(csv_file):
    descriptions = {}
    with open(csv_file, newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header row
        for row in reader:
            item_id = int(row[0])
            version_group_id = int(row[1])
            language_id = int(row[2])
            description = row[3].strip('"')
            key = (item_id, version_group_id, language_id)
            descriptions[key] = description
    return descriptions

def get_id_and_description_by_item_name(item_name):
    global csv_file_descriptions, csv_file_items
    item_name = capitalize_each_word(item_name)
    item_id_mapping = read_csv_file(csv_file_items)
    item_id = item_id_mapping.get(item_name.lower())
    if item_id is None:
        return None, None
    else:
        descriptions = read_descriptions_csv(csv_file_descriptions)
        key = (item_id, 11, 9)  # Assuming version_group_id 11 and language_id 9
        description = descriptions.get(key, None)
        return description
    
item_window = ItemWindow()
_ankimon_register_window("item_window", item_window)

class AttackDialog(QDialog):
    def __init__(self, attacks, new_attack):
        super().__init__()
        self.attacks = attacks
        self.new_attack = new_attack
        self.selected_attack = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f"Select which Attack to Replace with {self.new_attack}")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Select which Attack to Replace with {self.new_attack}"))
        for attack in self.attacks:
            button = QPushButton(attack)
            button.clicked.connect(self.attackSelected)
            layout.addWidget(button)
        reject_button = QPushButton("Reject Attack")
        reject_button.clicked.connect(self.attackNoneSelected)
        layout.addWidget(reject_button)
        self.setLayout(layout)

    def attackSelected(self):
        sender = self.sender()
        self.selected_attack = sender.text()
        self.accept()

    def attackNoneSelected(self):
        sender = self.sender()
        self.selected_attack = sender.text()
        self.reject()


class AchievementWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.read_item_file()
        self.initUI()

    def initUI(self):
        global addon_dir, icon_path
        self.setWindowIcon(QIcon(str(icon_path)))
        self.setWindowTitle("Achievements")
        self.layout = QVBoxLayout()  # Main layout is now a QVBoxLayout

        # Create the scroll area and its properties
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)

        # Create a widget and layout for content inside the scroll area
        self.contentWidget = QWidget()
        self.contentLayout = QGridLayout()  # The layout for items
        self.contentWidget.setLayout(self.contentLayout)

        # Add the content widget to the scroll area
        self.scrollArea.setWidget(self.contentWidget)

        # Add the scroll area to the main layout
        self.layout.addWidget(self.scrollArea)
        self.setLayout(self.layout)

    def renewWidgets(self):
        self.read_item_file()
        # Clear the existing widgets from the layout
        for i in reversed(range(self.contentLayout.count())):
            widget = self.contentLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        row, col = 0, 0
        max_items_per_row = 4
        if self.badge_list is None or not self.badge_list:  # Wenn None oder leer
            empty_label = QLabel("You dont own any badges yet.")
            self.contentLayout.addWidget(empty_label, 1, 1)
        else:
            for badge_num in self.badge_list:
                item_widget = self.BadgesLabel(badge_num)
                self.contentLayout.addWidget(item_widget, row, col)
                col += 1
                if col >= max_items_per_row:
                    row += 1
                    col = 0
        self.resize(700, 400)

    def BadgesLabel(self, badge_num):
        badge_path = badges_path / f"{str(badge_num)}.png"
        frame = QVBoxLayout() #itemframe
        achievement_description = f"{(badges[str(badge_num)])}"
        badges_name_label = QLabel(f"{achievement_description}")
        badges_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if badge_num < 15:
            border_width = 93  # Example width
            border_height = 93  # Example height
            border_color = QColor('black')
            border_pixmap = QPixmap(border_width, border_height)
            border_pixmap.fill(border_color)
            desired_width = 89  # Example width
            desired_height = 89  # Example height
            background_color = QColor('white')
            background_pixmap = QPixmap(desired_width, desired_height)
            background_pixmap.fill(background_color)
            picture_pixmap = QPixmap(str(badge_path))
            painter = QPainter(border_pixmap)
            painter.drawPixmap(2, 2, background_pixmap)
            painter.drawPixmap(5,5, picture_pixmap)
            painter.end()  # Finish drawing
            picture_label = QLabel()
            picture_label.setPixmap(border_pixmap)
        else:
            picture_pixmap = QPixmap(str(badge_path))
            # Scale the QPixmap to fit within a maximum size while maintaining the aspect ratio
            max_width, max_height = 100, 100  # Example maximum sizes
            scaled_pixmap = picture_pixmap.scaled(max_width, max_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            picture_label = QLabel()
            picture_label.setPixmap(scaled_pixmap)
        picture_label.setStyleSheet("border: 2px solid #3498db; border-radius: 5px; padding: 5px;")
        picture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame.addWidget(picture_label)
        frame.addWidget(badges_name_label)
        frame_widget = QWidget()
        frame_widget.setLayout(frame)

        return frame_widget

    def read_item_file(self):
        # Read the list from the JSON file
        try:
            with open(badgebag_path, 'r') as json_file:
                self.badge_list = json.load(json_file)
        except FileNotFoundError:
            # First-time setup - badges.json doesn't exist yet
            self.badge_list = []
        except Exception:
            # Other errors - initialize as empty list
            self.badge_list = []

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def showEvent(self, event):
        # This method is called when the window is shown or displayed
        self.renewWidgets()

    def show_window(self):
        from aqt import mw
        # Get the geometry of the main screen
        main_screen_geometry = mw.geometry()
        
        # Calculate the position to center the ItemWindow on the main screen
        x = main_screen_geometry.center().x() - self.width() / 2
        y = main_screen_geometry.center().y() - self.height() / 2
        
        # Move the ItemWindow to the calculated position
        self.move(x, y)
        
        self.show()

def report_bug():
    # Specify the URL of the Pokémon Showdown Team Builder
    bug_url = "https://github.com/Unlucky-Life/ankimon/issues"

    # Open the Team Builder in the default web browser
    QDesktopServices.openUrl(QUrl(bug_url))

achievement_bag = AchievementWindow()

#buttonlayout
mw.pokemenu = QMenu('&Ankimon', mw)
# and add it to the tools menu
mw.form.menubar.addMenu(mw.pokemenu)


# ---------------- PARTY SYSTEM (4 slots) ----------------
# This section adds a lightweight party backend + manual switching without adding fragile UI.
# Party state lives in user_files/party.json:
#   {"active_slot": 0, "slots": [0,1,2,3]}
# Each slot stores an index into mypokemon.json.

_party_shortcuts = []
_party_slot_actions = []  # Store references to slot menu actions for updating text

def _party_path():
    try:
        return os.path.join(str(currdirname), "user_files", "party.json")
    except Exception:
        return os.path.join(os.path.dirname(__file__), "user_files", "party.json")

def _load_party():
    path = _party_path()
    default_party = {"active_slot": 0, "slots": [0, 1, 2, 3]}
    try:
        with open(path, "r", encoding="utf-8") as f:
            party = json.load(f) or {}
    except Exception:
        party = {}
    # normalize
    if not isinstance(party, dict):
        party = {}
    party.setdefault("active_slot", default_party["active_slot"])
    party.setdefault("slots", default_party["slots"])
    # ensure 4 slots
    slots = party.get("slots", default_party["slots"])
    if not isinstance(slots, list):
        slots = default_party["slots"]
    slots = (slots + default_party["slots"])[:4]
    party["slots"] = slots
    # clamp active_slot
    try:
        a = int(party.get("active_slot", 0))
    except Exception:
        a = 0
    party["active_slot"] = max(0, min(3, a))
    return party

def _save_party(party: dict):
    path = _party_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(party, f, indent=2)

def _remove_pokemon_held_item(pkmn_name):
    """Remove held item from a specific Pokemon, revert Mega form, and return item to inventory"""
    try:
        global mypokemon_path, itembag_path
        with open(mypokemon_path, 'r') as file:
            pokemon_list = json.load(file)

        item_removed = None
        was_mega = False
        for pokemon in pokemon_list:
            if pokemon['name'].lower() == pkmn_name.lower():
                item_removed = pokemon.get('held_item')
                pokemon['held_item'] = None

                # If this was a mega stone, revert mega form
                if item_removed and item_removed.lower().endswith('ite'):
                    if pokemon.get('is_mega', False):
                        pokemon['is_mega'] = False
                        was_mega = True
                        print(f"[Mega] {pkmn_name} reverted from Mega form!")
                        tooltipWithColour(f"{pkmn_name} reverted to normal form", "#888888")
                break

        # Save updated Pokemon data
        with open(mypokemon_path, 'w') as file:
            json.dump(pokemon_list, file, indent=2)

        if item_removed:
            # Return item to inventory (EXP Share is reusable!)
            try:
                # Load current inventory
                if os.path.exists(itembag_path):
                    with open(itembag_path, 'r') as file:
                        itembag_list = json.load(file)
                else:
                    itembag_list = []

                # Add item back to inventory
                itembag_list.append(item_removed)

                # Save updated inventory
                with open(itembag_path, 'w') as file:
                    json.dump(itembag_list, file)

                item_display = item_removed.replace('_', ' ').replace('-', ' ').title()
                showInfo(f"{item_display} returned to inventory")
                print(f"[ItemBag] {item_removed} returned to inventory from {pkmn_name}")
            except Exception as e:
                print(f"Error returning item to inventory: {e}")
                item_display = item_removed.replace('_', ' ').replace('-', ' ').title()
                showInfo(f"Removed {item_display} from {pkmn_name.capitalize()}")

            # Refresh itembag window if open
            try:
                global item_window
                if item_window and item_window.isVisible():
                    item_window.renewWidgets()
                    print(f"[ItemBag] Refreshed itembag window after unequip")
            except Exception as e:
                print(f"[ItemBag] Error refreshing itembag: {e}")
        else:
            showInfo(f"{pkmn_name.capitalize()} was not holding any item")

    except Exception as e:
        print(f"Error removing held item: {e}")
        showWarning(f"Failed to remove held item from {pkmn_name}")

def _distribute_exp_share(exp_earned):
    """Distribute 50% of earned EXP to party Pokemon holding EXP Share (party-only, not entire collection)"""
    global mypokemon_path, mainpokemon_name
    try:
        # Calculate shared EXP (50% of earned EXP)
        shared_exp = int(exp_earned * 0.5)

        if shared_exp <= 0:
            return

        # Load party data to get the 4 active party members
        party = _load_party()
        party_slots = party.get("slots", [None, None, None, None])
        active_slot = party.get("active_slot", 0)

        # Load all caught Pokemon
        if not mypokemon_path.is_file():
            return

        with open(mypokemon_path, 'r') as file:
            pokemon_list = json.load(file)

        if not isinstance(pokemon_list, list):
            return

        # Find Pokemon holding EXP Share (ONLY in party, excluding the active Pokemon)
        exp_share_recipients = []
        for slot_idx, pokemon_idx in enumerate(party_slots):
            # Skip if not a valid party slot
            if pokemon_idx is None:
                continue

            # Skip the active slot (the one currently battling)
            if slot_idx == active_slot:
                continue

            # Get the Pokemon from the list
            if pokemon_idx < 0 or pokemon_idx >= len(pokemon_list):
                continue

            pokemon = pokemon_list[pokemon_idx]
            if not isinstance(pokemon, dict):
                continue

            # Check if holding EXP Share
            held_item = pokemon.get('held_item', '')
            if held_item and ('exp' in held_item.lower() and 'share' in held_item.lower()):
                exp_share_recipients.append((pokemon_idx, pokemon))

        if not exp_share_recipients:
            return

        # Distribute EXP to each recipient
        pokemon_leveled_up = []
        for idx, pokemon in exp_share_recipients:
            pkmn_name = pokemon.get('name', 'Unknown')
            original_level = pokemon.get('level', 1)
            pkmn_level = original_level
            pkmn_growth_rate = pokemon.get('growth_rate', 'medium')
            pkmn_xp = pokemon.get('stats', {}).get('xp', 0)

            # Add EXP
            if pkmn_level < 100:
                new_xp = pkmn_xp + shared_exp
                pokemon['stats']['xp'] = new_xp

                # Check for level-up
                while pkmn_level < 100:
                    try:
                        exp_needed = find_experience_for_level(pkmn_growth_rate, pkmn_level)
                        # CRITICAL FIX: CSV reader returns strings, must convert to int
                        exp_needed = int(exp_needed) if exp_needed else 0
                    except (ValueError, TypeError, AttributeError):
                        # Malformed XP value - skip level-up check to prevent crash
                        print(f"[EXP Share] Invalid exp_needed for {pkmn_name} level {pkmn_level}")
                        break

                    if new_xp >= exp_needed:
                        pkmn_level += 1
                        new_xp -= exp_needed
                        pokemon['level'] = pkmn_level
                        pokemon['stats']['xp'] = new_xp

                        # Check for level-based evolution (for over-leveled captures)
                        try:
                            evos = search_pokedex(pkmn_name.lower(), "evos")
                            if evos and isinstance(evos, list):
                                for evo_name in evos:
                                    evo_level = search_pokedex(evo_name.lower(), "evoLevel")
                                    evo_type = search_pokedex(evo_name.lower(), "evoType")
                                    # Only trigger evolution if:
                                    # 1. It's a level-based evolution (evoType is None or "levelUp")
                                    # 2. Current level is >= evolution level
                                    # 3. No item is required
                                    evo_item = search_pokedex(evo_name.lower(), "evoItem")
                                    if (evo_level and pkmn_level >= evo_level and
                                        (evo_type is None or evo_type == "levelUp") and
                                        (evo_item is None or evo_item == "None")):
                                        # Mark Pokemon for evolution notification
                                        # (Full evolution handling would require UI interaction)
                                        tooltipWithColour(f"{pkmn_name} can evolve to {evo_name}! (Level {pkmn_level} >= {evo_level})", "#FF00FF")
                                        break
                        except Exception:
                            pass

                        # Learn new moves at this level
                        try:
                            new_moves = get_levelup_move_for_pokemon(pkmn_name.lower(), pkmn_level)
                            if new_moves:
                                attacks = pokemon.get('attacks', [])
                                for move in new_moves:
                                    if len(attacks) < 4 and move not in attacks:
                                        attacks.append(move)
                                pokemon['attacks'] = attacks
                        except Exception:
                            pass
                    else:
                        break

                # Update the pokemon in the list
                pokemon_list[idx] = pokemon

                # Track for notification
                if pkmn_level > original_level:
                    pokemon_leveled_up.append((pkmn_name, pkmn_level))

        # Save updated Pokemon data
        with open(mypokemon_path, 'w') as file:
            json.dump(pokemon_list, file, indent=2)

        # Show notification for EXP Share recipients
        if exp_share_recipients:
            recipient_count = len(exp_share_recipients)
            if pokemon_leveled_up:
                level_up_msgs = [f"{name} reached level {lvl}!" for name, lvl in pokemon_leveled_up]
                msg = f"EXP Share: {shared_exp} EXP distributed to {recipient_count} Pokemon\n" + "\n".join(level_up_msgs)
            else:
                msg = f"EXP Share: {shared_exp} EXP distributed to {recipient_count} Pokemon"
            tooltipWithColour(msg, "#FFD700")

    except Exception as e:
        print(f"Error in _distribute_exp_share: {e}")
        import traceback
        traceback.print_exc()

def _load_progression_stats():
    """Load progression stats from JSON file with defaults"""
    default_stats = {
        "lifetime": {
            "total_cards_reviewed": 0,
            "total_battles_won": 0,
            "total_wild_battles": 0,
            "total_trainer_battles": 0,
            "total_gym_battles": 0,
            "total_elite_four_battles": 0,
            "total_champion_battles": 0,
            "total_pokemon_caught": 0,
            "total_pokemon_evolved": 0,
            "total_badges_earned": 0,
            "total_items_used": 0,
            "total_mega_evolutions": 0,
            "current_round": 1,
            "highest_level_reached": 1,
            "legendary_encounters": 0,
            "primal_battles_won": 0
        },
        "current_round": {
            "round_number": 1,
            "cards_reviewed": 0,
            "battles_won": 0,
            "gyms_defeated": 0,
            "elite_four_defeated": 0,
            "champion_defeated": False,
            "pokemon_caught": 0,
            "items_obtained": 0,
            "mega_evolutions_used": 0
        },
        "session": {
            "cards_reviewed": 0,
            "battles_won": 0,
            "xp_gained": 0,
            "pokemon_caught": 0
        },
        "legendary_captures": {
            "primal_groudon_captured": False,
            "primal_kyogre_captured": False,
            "mega_rayquaza_captured": False,
            "primal_groudon_battles": 0,
            "primal_kyogre_battles": 0,
            "mega_rayquaza_battles": 0
        },
        "cards_in_wild_enemy_battles": 0
    }

    try:
        with open(str(progression_stats_path), "r", encoding="utf-8") as f:
            stats = json.load(f) or {}
    except FileNotFoundError:
        # First time - create file with defaults
        stats = default_stats
        _save_progression_stats(stats)
        return stats
    except Exception:
        stats = {}

    # Ensure all sections exist with defaults
    if not isinstance(stats, dict):
        stats = default_stats
    else:
        # Merge with defaults to ensure all fields exist
        for section in default_stats:
            if section not in stats:
                stats[section] = default_stats[section]
            elif isinstance(default_stats[section], dict):
                for key in default_stats[section]:
                    if key not in stats[section]:
                        stats[section][key] = default_stats[section][key]

    return stats

def _save_progression_stats(stats: dict):
    """Save progression stats to JSON file"""
    try:
        os.makedirs(os.path.dirname(str(progression_stats_path)), exist_ok=True)
        with open(str(progression_stats_path), "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        print(f"Error saving progression stats: {e}")

def _load_mega_state():
    """Load mega evolution state from JSON file with defaults"""
    default_state = {
        "key_stone_unlocked": False,
        "mega_active": False,
        "mega_used_this_battle": False,
        "mega_stones": {}  # {dex_id: count}
    }

    try:
        with open(str(mega_state_path), "r", encoding="utf-8") as f:
            state = json.load(f) or {}
    except FileNotFoundError:
        # First time - create file with defaults
        state = default_state
        _save_mega_state(state)
        return state
    except Exception:
        state = {}

    # Ensure all fields exist with defaults
    if not isinstance(state, dict):
        state = default_state
    else:
        for key in default_state:
            if key not in state:
                state[key] = default_state[key]

    return state

def _save_mega_state(state: dict):
    """Save mega evolution state to JSON file"""
    try:
        os.makedirs(os.path.dirname(str(mega_state_path)), exist_ok=True)
        with open(str(mega_state_path), "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error saving mega state: {e}")

def _check_legendary_available(legendary_type):
    """Check if a legendary battle is available based on card count

    Args:
        legendary_type: 'primal_groudon', 'primal_kyogre', or 'mega_rayquaza'

    Returns:
        bool: True if legendary battle can be triggered
    """
    global card_counter
    stats = _load_progression_stats()

    thresholds = {
        'primal_groudon': 5000,
        'primal_kyogre': 6000,
        'mega_rayquaza': 7000
    }

    if legendary_type not in thresholds:
        return False

    # Check if card threshold is met
    if card_counter < thresholds[legendary_type]:
        return False

    # Check if already captured this round
    captured_key = f"{legendary_type}_captured"
    if not stats["legendary_captures"][captured_key]:
        # First time - always available once threshold is met
        return True

    # Already captured - check if re-battle is available this round
    battles_key = f"{legendary_type}_battles"
    current_round = stats["current_round"]["round_number"]

    # Allow one re-battle per round after initial capture
    # We track battles per round in a separate structure
    return stats["legendary_captures"].get(battles_key, 0) < current_round

def _trigger_legendary_battle(legendary_type):
    """Trigger a special legendary battle

    Args:
        legendary_type: 'primal_groudon', 'primal_kyogre', or 'mega_rayquaza'
    """
    global name, id, level, hp, max_hp, ability, type, enemy_attacks, base_experience, stats, ev, iv, gender, battle_status, growth_rate, pokemon_species

    # Legendary Pokemon definitions
    legendary_data = {
        'primal_groudon': {
            'name': 'Groudon-Primal',
            'id': 383,  # Groudon Pokedex ID
            'level': 70,
            'pokemon_species': 'Legendary'
        },
        'primal_kyogre': {
            'name': 'Kyogre-Primal',
            'id': 382,  # Kyogre Pokedex ID
            'level': 70,
            'pokemon_species': 'Legendary'
        },
        'mega_rayquaza': {
            'name': 'Rayquaza-Mega',
            'id': 384,  # Rayquaza Pokedex ID
            'level': 75,
            'pokemon_species': 'Legendary'
        }
    }

    if legendary_type not in legendary_data:
        return

    data = legendary_data[legendary_type]

    # Set up the legendary Pokemon for battle
    name = data['name']
    id = data['id']
    level = data['level']
    pokemon_species = data['pokemon_species']

    # Get Pokemon data from pokedex
    try:
        ability = search_pokedex(name.split('-')[0].lower(), "abilities")
        if ability and isinstance(ability, dict):
            ability = list(ability.values())[0] if ability else "Unknown"
        type = search_pokedex(name.split('-')[0].lower(), "types")
        base_experience = search_pokedex(name.split('-')[0].lower(), "baseExp")
        stats = search_pokedex(name.split('-')[0].lower(), "baseStats")
        growth_rate = search_pokedex(name.split('-')[0].lower(), "growth_rate")

        # Generate high-level stats
        ev = {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}
        iv = {
            "hp": random.randint(20, 31),
            "atk": random.randint(20, 31),
            "def": random.randint(20, 31),
            "spa": random.randint(20, 31),
            "spd": random.randint(20, 31),
            "spe": random.randint(20, 31)
        }

        max_hp = calculate_hp(stats["hp"], level, ev, iv)
        hp = max_hp

        # Generate powerful moveset
        enemy_attacks = generate_attacks(id, level)

        # Set gender and battle status
        gender = random.choice(["male", "female", "genderless"])
        battle_status = None

        # Show legendary encounter message
        tooltipWithColour(f"A Legendary {name} appears!", "#FFD700")

        # Update battle window if active
        global test_window, pkmn_window
        if pkmn_window is True and test_window is not None:
            test_window.display_first_encounter()

    except Exception as e:
        print(f"Error triggering legendary battle: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# SHADOW MEWTWO ENCOUNTER SYSTEM
# ============================================================================

def _has_shadow_synergy_stone():
    """Check if player has Shadow Synergy Stone in their bag"""
    try:
        with open(itembag_path, 'r') as json_file:
            itembag_list = json.load(json_file)
            return "shadow-synergy-stone" in itembag_list
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    except Exception as e:
        _ankimon_log("ERROR", "ShadowMewtwo", f"Error checking for Shadow Synergy Stone: {e}")
        return False

def _consume_shadow_synergy_stone():
    """Remove Shadow Synergy Stone from player's bag"""
    try:
        with open(itembag_path, 'r') as json_file:
            itembag_list = json.load(json_file)

        if "shadow-synergy-stone" in itembag_list:
            itembag_list.remove("shadow-synergy-stone")
            with open(itembag_path, 'w') as json_file:
                json.dump(itembag_list, json_file, indent=2)
            _ankimon_log("INFO", "ShadowMewtwo", "Shadow Synergy Stone consumed")
            return True
        return False
    except Exception as e:
        _ankimon_log("ERROR", "ShadowMewtwo", f"Error consuming Shadow Synergy Stone: {e}")
        return False

def _check_shadow_mewtwo_captured():
    """Check if Shadow Mewtwo has already been captured"""
    try:
        if not mypokemon_path.is_file():
            return False

        with open(mypokemon_path, 'r') as json_file:
            pokemon_list = json.load(json_file)
            for pokemon in pokemon_list:
                if pokemon.get("id") == 150 and pokemon.get("variant") == "shadow":
                    return True
        return False
    except Exception as e:
        _ankimon_log("ERROR", "ShadowMewtwo", f"Error checking Shadow Mewtwo capture status: {e}")
        return False

class ShadowMewtwoPopup(QDialog):
    """Popup dialog for Shadow Mewtwo encounter approval"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shadow Encounter")
        self.setModal(True)
        self.result_accepted = False

        # Set fixed size
        self.setFixedSize(500, 600)

        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Title
        title_label = QLabel("A Shadow presence approaches…")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #BB86FC; padding: 10px;")  # Purple for dark mode
        layout.addWidget(title_label)

        # Shadow Mewtwo popup image
        try:
            popup_image_path = addon_dir / "user_files" / "sprites" / "shadow_mewtwo_project" / "shadow_mewtwo_popup.png"
            if popup_image_path.exists():
                pixmap = QPixmap(str(popup_image_path))
                # Scale to fit dialog
                scaled_pixmap = pixmap.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                image_label = QLabel()
                image_label.setPixmap(scaled_pixmap)
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(image_label)
            else:
                _ankimon_log("WARN", "ShadowMewtwo", f"Popup image not found: {popup_image_path}")
        except Exception as e:
            _ankimon_log("ERROR", "ShadowMewtwo", f"Error loading popup image: {e}")

        # Description text
        desc_label = QLabel("Use Shadow Synergy Stone to challenge Shadow Mewtwo?")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setFont(QFont("Arial", 14))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("padding: 15px; color: #E0E0E0;")  # Light gray text for dark mode
        layout.addWidget(desc_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)

        # Start Battle button
        start_button = QPushButton("Start Battle")
        start_button.setFixedSize(150, 50)
        start_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #BB86FC;
                color: #000000;
                border-radius: 8px;
                padding: 10px;
                border: 2px solid #BB86FC;
            }
            QPushButton:hover {
                background-color: #CF6BDD;
                border: 2px solid #CF6BDD;
            }
        """)
        qconnect(start_button.clicked, self.accept_battle)
        button_layout.addWidget(start_button)

        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setFixedSize(150, 50)
        cancel_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                color: #E0E0E0;
                border-radius: 8px;
                padding: 10px;
                border: 2px solid #555555;
            }
            QPushButton:hover {
                background-color: #505050;
                border: 2px solid #777777;
            }
        """)
        qconnect(cancel_button.clicked, self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        # Dark mode styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
            }
        """)

    def accept_battle(self):
        """User accepted the battle"""
        self.result_accepted = True
        self.accept()

def _trigger_shadow_mewtwo_encounter():
    """Trigger Shadow Mewtwo special encounter with popup approval"""
    global test_window, pkmn_window

    try:
        _ankimon_log("INFO", "ShadowMewtwo", "Shadow Mewtwo encounter triggered")

        # Check if already captured
        if _check_shadow_mewtwo_captured():
            tooltipWithColour("Shadow Mewtwo has already been captured!", "#FFA500")
            _ankimon_log("INFO", "ShadowMewtwo", "Shadow Mewtwo already captured, encounter cancelled")
            return False

        # Check if player has the stone
        if not _has_shadow_synergy_stone():
            tooltipWithColour("You need the Shadow Synergy Stone to trigger this encounter!", "#FF0000")
            _ankimon_log("WARN", "ShadowMewtwo", "Player missing Shadow Synergy Stone")
            return False

        # Show popup approval dialog
        popup = ShadowMewtwoPopup(mw)
        popup.exec()

        if not popup.result_accepted:
            _ankimon_log("INFO", "ShadowMewtwo", "Player cancelled Shadow Mewtwo encounter")
            tooltipWithColour("Shadow Mewtwo encounter cancelled", "#888888")
            return False

        # Player accepted - consume the stone and start battle
        _ankimon_log("INFO", "ShadowMewtwo", "Player accepted Shadow Mewtwo encounter, consuming stone")
        _consume_shadow_synergy_stone()

        # Set battle state to wild (Shadow Mewtwo is catchable)
        _ankimon_set_battle_state("wild")

        # Set up Shadow Mewtwo battle
        _spawn_shadow_mewtwo()

        tooltipWithColour("Shadow Mewtwo battle begins!", "#8B008B")
        return True

    except Exception as e:
        _ankimon_log("ERROR", "ShadowMewtwo", f"Error triggering Shadow Mewtwo encounter: {e}")
        import traceback
        traceback.print_exc()
        return False

def _spawn_shadow_mewtwo():
    """Spawn Shadow Mewtwo for battle"""
    global name, id, level, hp, max_hp, ability, type, enemy_attacks, base_experience, stats, ev, iv, gender, battle_status, growth_rate, pokemon_species
    global test_window, pkmn_window, battlescene_file, current_wild_variant

    try:
        _ankimon_log("INFO", "ShadowMewtwo", "Spawning Shadow Mewtwo for battle")

        # Set Pokemon data
        name = "Shadow Mewtwo"
        id = 150  # Mewtwo ID
        level = 70
        pokemon_species = "Legendary"

        # Mark as shadow variant globally
        current_wild_variant = "shadow"

        # Get Pokemon data from pokedex (using base Mewtwo)
        ability = search_pokedex("mewtwo", "abilities")
        if ability and isinstance(ability, dict):
            ability = list(ability.values())[0] if ability else "Unknown"
        type = search_pokedex("mewtwo", "types")
        base_experience = search_pokedex("mewtwo", "baseExp")
        stats = search_pokedex("mewtwo", "baseStats")
        growth_rate = search_pokedex("mewtwo", "growth_rate")

        # Generate high-level stats
        ev = {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}
        iv = {
            "hp": random.randint(25, 31),
            "atk": random.randint(25, 31),
            "def": random.randint(25, 31),
            "spa": random.randint(25, 31),
            "spd": random.randint(25, 31),
            "spe": random.randint(25, 31)
        }

        max_hp = calculate_hp(stats["hp"], level, ev, iv)
        hp = max_hp

        # Shadow Mewtwo custom moveset
        enemy_attacks = ["psywave", "psystrike", "flamethrower", "shadowball"]
        _ankimon_log("INFO", "ShadowMewtwo", f"Shadow Mewtwo moveset: {enemy_attacks}")

        # Set gender and battle status
        gender = "genderless"
        battle_status = None

        # Select battle scene
        battlescene_file = random_battle_scene("Psychic")

        _ankimon_log("INFO", "ShadowMewtwo", f"Shadow Mewtwo spawned: hp={hp}/{max_hp}, level={level}")

        # Clear stale sprites
        _ankimon_clear_stale_enemy_sprites()

        # Update battle window if active
        if pkmn_window is True and test_window is not None:
            test_window.display_first_encounter()

        return True

    except Exception as e:
        _ankimon_log("ERROR", "ShadowMewtwo", f"Error spawning Shadow Mewtwo: {e}")
        import traceback
        traceback.print_exc()
        return False

# Global variable to track current wild Pokemon variant
current_wild_variant = None

def _get_mega_capable_pokemon_ids():
    """Return list of Pokemon IDs that can mega evolve"""
    # Complete list of Pokemon that can mega evolve (by National Dex ID)
    return [
        3,    # Venusaur
        6,    # Charizard (X and Y)
        9,    # Blastoise
        15,   # Beedrill
        18,   # Pidgeot
        65,   # Alakazam
        80,   # Slowbro
        94,   # Gengar
        115,  # Kangaskhan
        127,  # Pinsir
        130,  # Gyarados
        142,  # Aerodactyl
        150,  # Mewtwo (X and Y)
        181,  # Ampharos
        208,  # Steelix
        212,  # Scizor
        214,  # Heracross
        229,  # Houndoom
        248,  # Tyranitar
        254,  # Sceptile
        257,  # Blaziken
        260,  # Swampert
        282,  # Gardevoir
        302,  # Sableye
        303,  # Mawile
        306,  # Aggron
        308,  # Medicham
        310,  # Manectric
        319,  # Sharpedo
        323,  # Camerupt
        334,  # Altaria
        354,  # Banette
        359,  # Absol
        362,  # Glalie
        373,  # Salamence
        376,  # Metagross
        380,  # Latias
        381,  # Latios
        384,  # Rayquaza
        428,  # Lopunny
        445,  # Garchomp
        448,  # Lucario
        460,  # Abomasnow
        475,  # Gallade
        531,  # Audino
        719   # Diancie
    ]

def _get_owned_mega_capable_pokemon():
    """Return list of owned Pokemon IDs that can mega evolve"""
    try:
        mega_capable_ids = _get_mega_capable_pokemon_ids()
        pokemon_list = _load_mypokemon_list()
        owned_ids = [p.get("id") for p in pokemon_list if "id" in p]
        return [id for id in owned_ids if id in mega_capable_ids]
    except Exception as e:
        print(f"Error getting owned mega-capable Pokemon: {e}")
        return []

def _get_mega_stone_name(pokemon_id):
    """Get the name of the mega stone for a Pokemon ID"""
    stone_names = {
        3: "Venusaurite",
        6: "Charizardite",  # Note: Simplified (normally X or Y)
        9: "Blastoisinite",
        15: "Beedrillite",
        18: "Pidgeotite",
        65: "Alakazite",
        80: "Slowbronite",
        94: "Gengarite",
        115: "Kangaskhanite",
        127: "Pinsirite",
        130: "Gyaradosite",
        142: "Aerodactylite",
        150: "Mewtwonite",  # Note: Simplified (normally X or Y)
        181: "Ampharosite",
        208: "Steelixite",
        212: "Scizorite",
        214: "Heracronite",
        229: "Houndoominite",
        248: "Tyranitarite",
        254: "Sceptilite",
        257: "Blazikenite",
        260: "Swampertite",
        282: "Gardevoirite",
        302: "Sablenite",
        303: "Mawilite",
        306: "Aggronite",
        308: "Medichamite",
        310: "Manectite",
        319: "Sharpedonite",
        323: "Cameruptite",
        334: "Altarianite",
        354: "Banettite",
        359: "Absolite",
        362: "Glalitite",
        373: "Salamencite",
        376: "Metagrossite",
        380: "Latiasite",
        381: "Latiosite",
        384: "Rayquazite",
        428: "Lopunnite",
        445: "Garchompite",
        448: "Lucarionite",
        460: "Abomasite",
        475: "Galladite",
        531: "Audinite",
        719: "Diancite"
    }
    return stone_names.get(pokemon_id, f"Mega Stone #{pokemon_id}")

def _award_random_mega_stone(battle_type="wild"):
    """
    Award a random mega stone for an owned Pokemon that can mega evolve.

    Rules:
    - Only 1 stone per Pokemon species (no duplicates)
    - Drop chances: wild=0%, trainer=5%, gym=10%, elite4=25%, champion=100%
    - Exhaustion: stops awarding when all eligible stones collected

    Args:
        battle_type: Type of battle (wild, trainer, gym, elite4, champion)

    Returns:
        True if stone awarded, False otherwise
    """
    try:
        # Drop chance by battle type
        drop_chances = {
            "wild": 0.0,
            "trainer": 0.05,
            "gym": 0.10,
            "elite4": 0.25,
            "champion": 1.0
        }

        drop_chance = drop_chances.get(battle_type, 0.0)

        # Roll for drop (champion always drops)
        if random.random() > drop_chance:
            return False

        # Get all owned mega-capable Pokemon
        eligible_ids = _get_owned_mega_capable_pokemon()

        if not eligible_ids:
            # No eligible Pokemon owned
            return False

        # Load mega state to check which stones already owned
        mega_state = _load_mega_state()
        if "mega_stones" not in mega_state:
            mega_state["mega_stones"] = {}

        # Filter out Pokemon that already have stones (1 per type rule)
        unowned_ids = [id for id in eligible_ids if str(id) not in mega_state["mega_stones"]]

        if not unowned_ids:
            # All eligible stones already collected (exhaustion rule)
            return False

        # Choose a random eligible Pokemon that doesn't have a stone yet
        chosen_id = random.choice(unowned_ids)
        stone_name = _get_mega_stone_name(chosen_id)

        # Add mega stone to inventory (set to 1, not increment)
        mega_state["mega_stones"][str(chosen_id)] = 1
        _save_mega_state(mega_state)

        # Add mega stone to items bag so it appears in UI
        try:
            with open(itembag_path, 'r') as json_file:
                itembag_list = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            itembag_list = []

        # Use clean stone name (e.g., "Ampharosite")
        item_name = stone_name
        itembag_list.append(item_name)

        with open(itembag_path, 'w') as json_file:
            json.dump(itembag_list, json_file)

        # Get Pokemon name and display the item
        pokemon_name = search_pokedex_by_id(chosen_id)

        # Show item popup like other items
        try:
            if test_window is not None:
                test_window.rate_display_item(item_name)
        except Exception as e:
            print(f"Error displaying mega stone: {e}")

        tooltipWithColour(f"Received {stone_name} for {pokemon_name}!", "#FFD700")
        print(f"[MegaStone] Awarded {stone_name} (#{chosen_id}) from {battle_type} battle")
        return True
    except Exception as e:
        print(f"Error awarding mega stone: {e}")
        import traceback
        traceback.print_exc()
        return False

def _can_mega_evolve():
    """Check if the active party Pokemon can mega evolve"""
    try:
        print("[Mega] Checking if can mega evolve...")

        # Check if key stone is unlocked
        mega_state = _load_mega_state()
        if mega_state is None:
            print("[Mega] FAIL: mega_state is None")
            return False

        if not mega_state.get("key_stone_unlocked", False):
            print("[Mega] FAIL: Key stone not unlocked")
            return False

        # Check if already mega evolved this battle
        if mega_state.get("mega_used_this_battle", False):
            print("[Mega] FAIL: Already mega evolved this battle")
            return False

        # Get active Pokemon from party
        party = _load_party()
        if party is None:
            print("[Mega] FAIL: party is None")
            return False

        active_slot = party.get("active_slot", 0)
        party_slots = party.get("slots", [None, None, None, None])

        if active_slot >= len(party_slots):
            print(f"[Mega] FAIL: active_slot {active_slot} >= party_slots length {len(party_slots)}")
            return False

        active_pokemon_index = party_slots[active_slot]
        if active_pokemon_index is None:
            print(f"[Mega] FAIL: No Pokemon in active slot {active_slot}")
            return False

        # Load Pokemon list
        pokemon_list = _load_mypokemon_list()
        if pokemon_list is None:
            print("[Mega] FAIL: pokemon_list is None")
            return False

        if active_pokemon_index >= len(pokemon_list):
            print(f"[Mega] FAIL: active_pokemon_index {active_pokemon_index} >= pokemon_list length {len(pokemon_list)}")
            return False

        active_pokemon = pokemon_list[active_pokemon_index]
        if active_pokemon is None:
            print("[Mega] FAIL: active_pokemon is None")
            return False

        pokemon_id = active_pokemon.get("id")
        pokemon_name = active_pokemon.get("name", "Unknown")

        print(f"[Mega] Active Pokemon: {pokemon_name} (ID: {pokemon_id})")

        # Check if Pokemon can mega evolve
        if pokemon_id not in _get_mega_capable_pokemon_ids():
            print(f"[Mega] FAIL: {pokemon_name} (ID: {pokemon_id}) cannot mega evolve")
            return False

        # Check if player owns the corresponding mega stone (not tied to held item)
        expected_stone_name = _get_mega_stone_name(pokemon_id)

        # Check if the mega stone is in the player's inventory
        if "mega_stones" not in mega_state:
            print(f"[Mega] FAIL: No mega stones owned yet")
            return False

        if str(pokemon_id) not in mega_state["mega_stones"]:
            print(f"[Mega] FAIL: {expected_stone_name} not owned")
            print(f"[Mega]   Need to obtain {expected_stone_name} for {pokemon_name}")
            return False

        print(f"[Mega] SUCCESS: {pokemon_name} can mega evolve with owned {expected_stone_name}!")
        return True
    except Exception as e:
        print(f"[Mega] ERROR checking mega evolution: {e}")
        import traceback
        traceback.print_exc()
        return False

def _trigger_mega_evolution():
    """Trigger mega evolution for active party Pokemon"""
    try:
        print("[Mega] Triggering mega evolution...")

        # Get active Pokemon
        party = _load_party()
        if party is None:
            print("[Mega] ERROR: party is None")
            tooltipWithColour("Mega Evolution failed: Could not load party", "#FF0000")
            return False

        active_slot = party.get("active_slot", 0)
        party_slots = party.get("slots", [None, None, None, None])

        if active_slot >= len(party_slots):
            print(f"[Mega] ERROR: active_slot {active_slot} out of range")
            tooltipWithColour("Mega Evolution failed: Invalid party slot", "#FF0000")
            return False

        active_pokemon_index = party_slots[active_slot]
        if active_pokemon_index is None:
            print(f"[Mega] ERROR: No Pokemon in slot {active_slot}")
            tooltipWithColour("Mega Evolution failed: No Pokemon in active slot", "#FF0000")
            return False

        pokemon_list = _load_mypokemon_list()
        if pokemon_list is None or active_pokemon_index >= len(pokemon_list):
            print("[Mega] ERROR: Invalid pokemon_list or index")
            tooltipWithColour("Mega Evolution failed: Could not load Pokemon", "#FF0000")
            return False

        active_pokemon = pokemon_list[active_pokemon_index]
        pokemon_id = active_pokemon.get("id")
        pokemon_name = active_pokemon.get("name", "Unknown")

        print(f"[Mega] Mega evolving {pokemon_name} (ID: {pokemon_id})")

        # Update mega state
        mega_state = _load_mega_state()
        if mega_state is None:
            print("[Mega] ERROR: mega_state is None")
            tooltipWithColour("Mega Evolution failed: Could not load mega state", "#FF0000")
            return False

        # Mark mega as active and used this battle
        mega_state["mega_active"] = True
        mega_state["mega_used_this_battle"] = True

        _save_mega_state(mega_state)

        # Set is_mega flag on the Pokemon
        active_pokemon['is_mega'] = True
        try:
            global mypokemon_path
            with open(mypokemon_path, 'w') as file:
                json.dump(pokemon_list, file, indent=2)
            print(f"[Mega] Set is_mega=True for {pokemon_name}")
        except Exception as e:
            print(f"[Mega] ERROR saving is_mega flag: {e}")

        # Track mega evolution usage
        try:
            stats_data = _load_progression_stats()
            if stats_data:
                stats_data["lifetime"]["total_mega_evolutions"] += 1
                stats_data["current_round"]["mega_evolutions_used"] += 1
                _save_progression_stats(stats_data)
        except Exception as e:
            print(f"[Mega] Warning: Could not update stats: {e}")
            pass

        # Play transition animation
        try:
            _play_mega_transition_animation(pokemon_name, pokemon_id)
        except Exception as e:
            print(f"[Mega] Transition animation failed: {e}")

        # Refresh external window if open
        try:
            global test_window
            if test_window and test_window.isVisible():
                test_window.display_first_encounter()
        except Exception as e:
            print(f"[Mega] Window refresh failed: {e}")

        # Show mega evolution message (same as Dev Mode)
        tooltipWithColour(f"⚡ {pokemon_name} is now MEGA!", "#FF00FF")
        showInfo(f"✓ {pokemon_name} transformed to Mega form!\n\nStats boosted:\n• Outgoing damage: +25%\n• Incoming damage: -15%")
        print(f"[Mega] SUCCESS: {pokemon_name} mega evolved!")

        return True
    except Exception as e:
        print(f"[Mega] ERROR triggering mega evolution: {e}")
        import traceback
        traceback.print_exc()
        tooltipWithColour(f"Mega Evolution failed: {str(e)}", "#FF0000")
        return False

def _reset_mega_battle_state():
    """Reset mega evolution state at end of battle and revert Pokemon to normal form"""
    try:
        print("[Mega] Resetting battle state and reverting Mega form")
        mega_state = _load_mega_state()
        mega_state["mega_active"] = False
        mega_state["mega_used_this_battle"] = False
        _save_mega_state(mega_state)

        # Revert is_mega flag on active Pokemon
        try:
            party = _load_party()
            if party and isinstance(party, dict):
                active_slot = party.get("active_slot", 0)
                party_slots = party.get("slots", [0, 1, 2, 3])

                if active_slot < len(party_slots):
                    active_pokemon_index = party_slots[active_slot]

                    if active_pokemon_index is not None:
                        pokemon_list = _load_mypokemon_list()

                        if pokemon_list and isinstance(pokemon_list, list) and active_pokemon_index < len(pokemon_list):
                            active_pokemon = pokemon_list[active_pokemon_index]

                            if active_pokemon and isinstance(active_pokemon, dict):
                                if active_pokemon.get('is_mega', False):
                                    active_pokemon['is_mega'] = False
                                    pokemon_name = active_pokemon.get('name', 'Unknown')

                                    global mypokemon_path
                                    with open(mypokemon_path, 'w') as file:
                                        json.dump(pokemon_list, file, indent=2)

                                    print(f"[Mega] Reverted {pokemon_name} to normal form")
        except Exception as e:
            print(f"[Mega] Error reverting is_mega: {e}")

    except Exception as e:
        print(f"Error resetting mega state: {e}")

def _is_mega_active():
    """Check if active Pokemon is in Mega form - CRASH-PROOF with hard Key Stone gate"""
    try:
        # HARD GATE: Check if Mega Evolution is unlocked first
        mega_state = _load_mega_state()
        if not mega_state or not mega_state.get("key_stone_unlocked", False):
            return False  # Mega is LOCKED - no mega functionality allowed

        # Load party safely
        party = _load_party()
        if not party or not isinstance(party, dict):
            return False

        active_slot = party.get("active_slot", 0)
        party_slots = party.get("slots", [0, 1, 2, 3])

        if not isinstance(party_slots, list) or active_slot >= len(party_slots):
            return False

        active_pokemon_index = party_slots[active_slot]
        if active_pokemon_index is None:
            return False

        # Load Pokemon list safely
        pokemon_list = _load_mypokemon_list()
        if not pokemon_list or not isinstance(pokemon_list, list):
            return False

        if active_pokemon_index >= len(pokemon_list):
            return False

        active_pokemon = pokemon_list[active_pokemon_index]
        if not active_pokemon or not isinstance(active_pokemon, dict):
            return False

        # Check is_mega flag
        return active_pokemon.get('is_mega', False)
    except Exception as e:
        print(f"[Mega] Error checking is_mega_active: {e}")
        return False

def _complete_legendary_capture(legendary_type):
    """Handle completion of legendary capture - guaranteed capture

    Args:
        legendary_type: 'primal_groudon', 'primal_kyogre', or 'mega_rayquaza'
    """
    stats = _load_progression_stats()

    # Mark as captured if first time
    captured_key = f"{legendary_type}_captured"
    is_first_capture = not stats["legendary_captures"][captured_key]

    if is_first_capture:
        stats["legendary_captures"][captured_key] = True
        stats["lifetime"]["legendary_encounters"] += 1

    # Increment battle count for this legendary
    battles_key = f"{legendary_type}_battles"
    stats["legendary_captures"][battles_key] = stats["legendary_captures"].get(battles_key, 0) + 1
    stats["lifetime"]["primal_battles_won"] += 1

    _save_progression_stats(stats)

    # Force capture the legendary
    global name
    if is_first_capture:
        save_caught_pokemon(name)
        tooltipWithColour(f"{name} was captured!", "#FFD700")
    else:
        # Re-battle - award mega stone instead (guaranteed drop for legendary re-battles)
        if _award_random_mega_stone("champion"):
            tooltipWithColour(f"{name} defeated! You received a Mega Stone!", "#FFD700")
        else:
            tooltipWithColour(f"{name} defeated!", "#FFD700")

def _load_mypokemon_list():
    """Load Pokemon list with comprehensive error handling"""
    global mypokemon_path
    try:
        with open(str(mypokemon_path), "r", encoding="utf-8") as f:
            data = json.load(f) or []
        if not isinstance(data, list):
            print(f"[Pokemon List] WARNING: Data is not a list, returning empty list")
            return []
        return data
    except FileNotFoundError:
        print(f"[Pokemon List] WARNING: File not found: {mypokemon_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"[Pokemon List] ERROR: Invalid JSON in {mypokemon_path}: {e}")
        return []
    except Exception as e:
        print(f"[Pokemon List] ERROR loading Pokemon list: {e}")
        import traceback
        traceback.print_exc()
        return []

def _is_fainted(pkmn: dict) -> bool:
    try:
        return int(pkmn.get("current_hp", 1)) <= 0
    except Exception:
        return False

def _set_active_from_party_slot(slot_index: int):
    """Sets main pokemon to the pokemon referenced by party slot (0-3)."""
    try:
        slot_index = int(slot_index)
    except Exception:
        slot_index = 0
    slot_index = max(0, min(3, slot_index))

    party = _load_party()
    slots = party.get("slots", [0, 1, 2, 3])
    try:
        my_index = int(slots[slot_index])
    except Exception:
        showInfo(f"Party slot {slot_index+1} is not set to a valid Pokémon index.")
        return

    my_list = _load_mypokemon_list()
    if my_index < 0 or my_index >= len(my_list):
        showInfo(f"Party slot {slot_index+1} points to index {my_index}, but you only have {len(my_list)} Pokémon.")
        return

    p = my_list[my_index]
    if _is_fainted(p):
        showInfo(f"{p.get('name','This Pokémon')} is fainted. Heal it before switching into it.")
        return

    # Use empty nickname if missing
    nickname = p.get("nickname", "") if isinstance(p.get("nickname",""), str) else ""
    # MainPokemon expects stats dict that includes xp
    stats = p.get("stats", {}) or {}
    if "xp" not in stats:
        stats["xp"] = 0

    try:
        MainPokemon(
            p.get("name","Unknown"),
            nickname,
            int(p.get("level", 1)),
            int(p.get("id", 0)),
            p.get("ability",""),
            p.get("type", []),
            stats,
            p.get("attacks", []),
            int(stats.get("hp", 1)),
            int(p.get("base_experience", 0)),
            p.get("growth_rate", "medium"),
            p.get("ev", {}) or {},
            p.get("iv", {}) or {},
            p.get("gender", "N"),
            is_shiny=p.get("is_shiny", False),
            preserve_enemy=True,
            silent=True,
        )
    except Exception as e:
        showInfo(f"Could not switch party slot {slot_index+1} to main Pokémon. Error: {e}")
        return

    party["active_slot"] = slot_index
    _save_party(party)
    # Changed from "Active Party Slot set to X:" to "Go! (name)"
    pokemon_display_name = nickname if nickname and nickname.strip() else p.get('name','Unknown')
    showInfo(f"Go! {pokemon_display_name.capitalize()}!")

def _cycle_party(direction: int = 1):
    party = _load_party()
    start = int(party.get("active_slot", 0))
    direction = 1 if direction >= 0 else -1
    for step in range(1, 5):
        nxt = (start + direction * step) % 4
        # try switch; if fainted or invalid, keep cycling
        before = party.get("active_slot", start)
        _set_active_from_party_slot(nxt)
        # reload to see if it actually changed
        party2 = _load_party()
        if int(party2.get("active_slot", start)) == nxt:
            return
    showInfo("Could not switch: no valid non-fainted Pokémon found in party slots.")

def _update_party_menu_text():
    """Update the party slot menu items to show pokemon names."""
    global _party_slot_actions
    if not _party_slot_actions or len(_party_slot_actions) != 4:
        return

    try:
        party = _load_party()
        slots = party.get("slots", [None, None, None, None])
        mypokemon_data = _load_mypokemon_list()

        for i in range(4):
            slot_idx = slots[i] if i < len(slots) else None
            pokemon_name = ""

            if slot_idx is not None and isinstance(mypokemon_data, list) and 0 <= slot_idx < len(mypokemon_data):
                pokemon = mypokemon_data[slot_idx]
                if isinstance(pokemon, dict):
                    # Use nickname if available, otherwise use regular name
                    nickname = pokemon.get('nickname')
                    name = pokemon.get('name', 'Unknown')
                    pokemon_name = f" ({nickname.capitalize()})" if nickname else f" ({name.capitalize()})"

            # Update menu text
            _party_slot_actions[i].setText(f"Party: Use Slot {i+1}{pokemon_name}")
    except Exception:
        # If anything fails, just keep the default text
        pass

def _register_party_actions():
    """Adds hotkeys to switch active party slot (no menu items - those were removed per request)."""
    try:
        # Hotkeys only (global while Anki is focused)
        # Menu items removed - party switching now only via hotkeys or Pokemon Collection UI
        global _party_shortcuts
        def _mk(seq, fn):
            sc = QShortcut(QKeySequence(seq), mw)
            sc.activated.connect(fn)
            _party_shortcuts.append(sc)

        _mk("Ctrl+Shift+1", lambda: _set_active_from_party_slot(0))
        _mk("Ctrl+Shift+2", lambda: _set_active_from_party_slot(1))
        _mk("Ctrl+Shift+3", lambda: _set_active_from_party_slot(2))
        _mk("Ctrl+Shift+4", lambda: _set_active_from_party_slot(3))
        _mk("Ctrl+Shift+Right", lambda: _cycle_party(1))
        _mk("Ctrl+Shift+Left", lambda: _cycle_party(-1))
    except Exception as e:
        # Don't crash the addon if shortcuts fail
        try:
            showInfo(f"Party hotkeys could not be registered: {e}")
        except Exception:
            pass

# Register party actions once the Ankimon menu exists.
try:
    _register_party_actions()
except Exception:
    pass
# ---------------------------------------------------------

# DEVELOPER MODE: RESET PROGRESSION
def _reset_progression():
    """Reset progression stats and counters for a clean start"""
    try:
        from aqt.qt import QMessageBox

        # Show confirmation dialog
        reply = QMessageBox.question(
            mw,
            "Reset Progression",
            "Reset progression stats?\n\n"
            "This will reset:\n"
            "• Gym progression (badges, rounds)\n"
            "• Elite Four progression\n"
            "• Champion progression\n"
            "• Cards-until-next-boss counters\n"
            "• Resume battle states\n\n"
            "This will NOT delete:\n"
            "• Your Pokémon collection\n"
            "• Party\n"
            "• Items\n"
            "• Settings/config",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            print("[ResetProgression] User cancelled reset")
            return

        print("[ResetProgression] Starting progression reset...")

        # Get collection config
        conf = _ankimon_get_col_conf()
        if not conf:
            showWarning("Could not access collection config")
            return

        # Reset gym progression
        conf["ankimon_gym_counter"] = 0
        if "ankimon_gym_badges" in conf:
            conf["ankimon_gym_badges"] = []

        # Reset Elite Four progression
        conf["ankimon_elite_four_index"] = 0
        conf["ankimon_elite_four_counter"] = 0
        conf["ankimon_elite_four_active"] = False

        # Reset Champion progression
        conf["ankimon_champion_counter"] = 0
        conf["ankimon_champion_active"] = False

        # Reset progression stats JSON
        stats = _load_progression_stats()

        # Reset current round stats (but keep lifetime stats intact)
        stats["current_round"] = {
            "round_number": 1,
            "cards_reviewed": 0,
            "battles_won": 0,
            "gyms_defeated": 0,
            "elite_four_defeated": 0,
            "champion_defeated": False,
            "pokemon_caught": 0,
            "items_obtained": 0,
            "mega_evolutions_used": 0
        }

        # Reset lifetime current round counter to 1
        if "lifetime" in stats:
            stats["lifetime"]["current_round"] = 1

        # Save updated stats
        _save_progression_stats(stats)

        # Save collection config
        if hasattr(mw, 'col') and mw.col:
            mw.col.set_config_bool("ankimon_elite_four_active", False)
            mw.col.set_config_bool("ankimon_champion_active", False)

        print("[ResetProgression] ✓ Reset complete")
        print(f"[ResetProgression] - Gym counter: {conf.get('ankimon_gym_counter', 0)}")
        print(f"[ResetProgression] - Elite Four index: {conf.get('ankimon_elite_four_index', 0)}")
        print(f"[ResetProgression] - Elite Four counter: {conf.get('ankimon_elite_four_counter', 0)}")
        print(f"[ResetProgression] - Champion counter: {conf.get('ankimon_champion_counter', 0)}")
        print(f"[ResetProgression] - Current round stats reset")

        # Force refresh UI
        try:
            global test_window
            if test_window and test_window.isVisible():
                test_window.display_first_encounter()
                print("[ResetProgression] - Refreshed test window")
        except Exception as e:
            print(f"[ResetProgression] Warning: Could not refresh test window: {e}")

        showInfo(
            "✓ Progression reset complete!\n\n"
            "Your journey starts fresh:\n"
            "• All gym/Elite Four/Champion progress cleared\n"
            "• Pokémon and items preserved\n\n"
            "Review 100 cards to challenge the first gym!"
        )

    except Exception as e:
        print(f"[ResetProgression] ERROR: {e}")
        import traceback
        traceback.print_exc()
        showWarning(f"Reset progression failed: {e}")

# DEVELOPER MODE: MEGA TOGGLE (NO CRASHES GUARANTEED)
def _dev_toggle_mega_for_active():
    """Toggle Mega form for active Pokemon - CRASH-PROOF"""
    try:
        print("[DevMega] Toggle Mega called")

        # Load party safely
        party = _load_party()
        if not party or not isinstance(party, dict):
            showInfo("Failed to load party data")
            return

        active_slot = party.get("active_slot", 0)
        party_slots = party.get("slots", [0, 1, 2, 3])

        if not isinstance(party_slots, list) or active_slot >= len(party_slots):
            showInfo(f"Invalid party slot: {active_slot}")
            return

        active_pokemon_index = party_slots[active_slot]
        if active_pokemon_index is None:
            showInfo("No Pokemon in active slot")
            return

        # Load Pokemon list safely
        pokemon_list = _load_mypokemon_list()
        if not pokemon_list or not isinstance(pokemon_list, list):
            showInfo("Failed to load Pokemon list")
            return

        if active_pokemon_index >= len(pokemon_list):
            showInfo(f"Invalid Pokemon index: {active_pokemon_index}")
            return

        active_pokemon = pokemon_list[active_pokemon_index]
        if not active_pokemon or not isinstance(active_pokemon, dict):
            showInfo("Invalid Pokemon data")
            return

        # Get Pokemon info
        pokemon_name = active_pokemon.get('name', 'Unknown')
        pokemon_id = active_pokemon.get('id', 0)
        current_mega_state = active_pokemon.get('is_mega', False)

        # Toggle Mega
        new_mega_state = not current_mega_state
        active_pokemon['is_mega'] = new_mega_state

        # Save safely
        try:
            global mypokemon_path
            with open(mypokemon_path, 'w') as file:
                json.dump(pokemon_list, file, indent=2)
            print(f"[DevMega] Saved {pokemon_name} is_mega={new_mega_state}")
        except Exception as e:
            showInfo(f"Failed to save: {e}")
            return

        # Play transition animation if turning ON mega
        if new_mega_state:
            try:
                _play_mega_transition_animation(pokemon_name, pokemon_id)
            except Exception as e:
                print(f"[DevMega] Transition animation failed: {e}")

        # Show result
        if new_mega_state:
            tooltipWithColour(f"⚡ {pokemon_name} is now MEGA! (ID: {pokemon_id})", "#FF00FF")
            showInfo(f"✓ {pokemon_name} transformed to Mega form!\n\nStats boosted:\n• Outgoing damage: +25%\n• Incoming damage: -15%")
        else:
            tooltipWithColour(f"{pokemon_name} reverted to normal form", "#888888")
            showInfo(f"✓ {pokemon_name} reverted to normal form")

        # Refresh all windows immediately
        try:
            global pokecollection_win, test_window
            # Refresh collection window if open
            if pokecollection_win and pokecollection_win.isVisible():
                pokecollection_win.refresh_pokemon_collection()
            # Refresh external Ankimon window if open
            if test_window and test_window.isVisible():
                test_window.display_first_encounter()
        except Exception as e:
            print(f"[DevMega] Window refresh failed: {e}")

    except Exception as e:
        print(f"[DevMega] ERROR: {e}")
        import traceback
        traceback.print_exc()
        showInfo(f"Mega toggle failed: {e}")

def _play_mega_transition_animation(pokemon_name, pokemon_id):
    """Play Mega Evolution transition animation IN-PLACE in the external window"""
    try:
        global test_window, user_path_sprites, backdefault_gif
        if not test_window or not test_window.isVisible():
            print(f"[DevMega] Test window not visible, skipping transition")
            return

        # Check if sprite label exists
        if not hasattr(test_window, 'player_sprite_label') or test_window.player_sprite_label is None:
            print(f"[DevMega] Player sprite label not found, skipping transition")
            return

        # Check if transition GIF exists
        transition_path = user_path_sprites / "mega_evolve_transition" / "mega_evolve_transition.gif"
        if not transition_path.exists():
            print(f"[DevMega] Transition GIF not found at {transition_path}, skipping")
            return

        from PyQt6.QtGui import QMovie
        from PyQt6.QtCore import QTimer, QSize

        # Get the sprite label
        sprite_label = test_window.player_sprite_label
        sprite_size = test_window.player_sprite_size if hasattr(test_window, 'player_sprite_size') else 80

        print(f"[DevMega] Playing transition animation in-place for {pokemon_name}")

        # Create and play transition movie
        transition_movie = QMovie(str(transition_path))
        transition_movie.setScaledSize(QSize(sprite_size, sprite_size))
        sprite_label.setMovie(transition_movie)
        transition_movie.start()

        # After 2 seconds, swap to Mega sprite
        def switch_to_mega_sprite():
            try:
                # Load Mega sprite
                mega_sprite_path = user_path_sprites / "back_mega_pokemon_gif" / f"{pokemon_id}.gif"
                if not mega_sprite_path.exists():
                    # Fallback to normal sprite
                    mega_sprite_path = backdefault_gif / f"{pokemon_id}.gif"

                if mega_sprite_path.exists():
                    mega_movie = QMovie(str(mega_sprite_path))
                    mega_movie.setScaledSize(QSize(sprite_size, sprite_size))
                    sprite_label.setMovie(mega_movie)
                    mega_movie.start()
                    print(f"[DevMega] Switched to Mega sprite: {mega_sprite_path}")
                else:
                    print(f"[DevMega] Mega sprite not found: {mega_sprite_path}")
            except Exception as e:
                print(f"[DevMega] Error switching to Mega sprite: {e}")

        # Schedule sprite swap after transition
        QTimer.singleShot(2000, switch_to_mega_sprite)

    except Exception as e:
        print(f"[DevMega] Animation error: {e}")
        import traceback
        traceback.print_exc()

# ==========================================================================
# MEGA SYSTEM: FRESH RESTART, PURGE, SEED, AND SELF-TEST
# ==========================================================================

def _fresh_mega_restart():
    """Complete fresh restart: unequip all stones, remove from inventory, reset unlock"""
    try:
        from aqt.utils import askUser

        # Confirm with user
        confirm = askUser(
            "FRESH MEGA RESTART\n\n"
            "This will:\n"
            "• Unequip ALL Mega Stones from all Pokémon\n"
            "• Remove ALL Mega Stones from Itembag\n"
            "• Remove Key Stone from Itembag\n"
            "• Lock Mega Evolution (reset to pre-Champion state)\n"
            "• Force all Pokémon to normal forms\n\n"
            "This action cannot be undone.\n\n"
            "Continue?"
        )

        if not confirm:
            print("[Fresh Restart] Cancelled by user")
            return False

        print("[Fresh Restart] Starting complete Mega system reset...")

        # 1. Unequip all Mega Stones and force is_mega = False for ALL Pokemon
        global mypokemon_path
        try:
            with open(mypokemon_path, 'r') as f:
                pokemon_list = json.load(f)

            modified_count = 0
            for pokemon in pokemon_list:
                # Remove held item if it's a mega stone
                held_item = pokemon.get('held_item', '')
                if held_item and (held_item.lower().endswith('ite') or held_item == 'key_stone'):
                    pokemon['held_item'] = None
                    modified_count += 1

                # Force is_mega = False
                if pokemon.get('is_mega', False):
                    pokemon['is_mega'] = False
                    modified_count += 1

            # Save updated Pokemon list
            with open(mypokemon_path, 'w') as f:
                json.dump(pokemon_list, f, indent=2)

            print(f"[Fresh Restart] Unequipped stones and reset Mega state for {modified_count} changes")
        except Exception as e:
            print(f"[Fresh Restart] Error modifying Pokemon: {e}")

        # 2. Remove ALL mega stones and Key Stone from Itembag
        global itembag_path
        try:
            with open(itembag_path, 'r') as f:
                itembag_list = json.load(f)

            original_count = len(itembag_list)
            # Remove all items ending in 'ite' (mega stones) and 'key_stone'
            itembag_list = [item for item in itembag_list if not (item.lower().endswith('ite') or item == 'key_stone')]
            removed_count = original_count - len(itembag_list)

            # Save cleaned inventory
            with open(itembag_path, 'w') as f:
                json.dump(itembag_list, f, indent=2)

            print(f"[Fresh Restart] Removed {removed_count} items from Itembag")
        except Exception as e:
            print(f"[Fresh Restart] Error cleaning Itembag: {e}")

        # 3. Reset mega_state.json - lock Mega Evolution
        try:
            mega_state = {
                "key_stone_unlocked": False,
                "mega_active": False,
                "mega_used_this_battle": False,
                "mega_stones": {}
            }
            _save_mega_state(mega_state)
            print("[Fresh Restart] Reset mega_state.json - Mega Evolution LOCKED")
        except Exception as e:
            print(f"[Fresh Restart] Error resetting mega_state: {e}")

        # 4. Refresh all windows
        try:
            global pokecollection_win, test_window
            if pokecollection_win and pokecollection_win.isVisible():
                pokecollection_win.refresh_pokemon_collection()
            if test_window and test_window.isVisible():
                test_window.display_first_encounter()
        except Exception as e:
            print(f"[Fresh Restart] Error refreshing windows: {e}")

        showInfo(
            "✓ Fresh Mega Restart Complete!\n\n"
            "• All Mega Stones unequipped\n"
            "• All Mega Stones removed from Itembag\n"
            "• Key Stone removed\n"
            "• Mega Evolution LOCKED\n"
            "• All Pokémon reverted to normal forms\n\n"
            "Mega system reset to pre-Champion state."
        )

        print("[Fresh Restart] SUCCESS - Complete reset finished")
        return True

    except Exception as e:
        error_msg = f"Fresh restart failed: {e}"
        showWarning(error_msg)
        print(f"[Fresh Restart] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def _purge_all_mega_stones():
    """Remove ALL mega stones from inventory and mega_state, keep Key Stone"""
    try:
        print("[Mega Purge] Starting mega stone purge...")
        purge_count = 0

        # 1. Purge from items.json (itembag)
        try:
            with open(itembag_path, 'r') as f:
                itembag_list = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            itembag_list = []

        # Remove all items ending with 'ite' (mega stones) but keep 'key_stone'
        original_count = len(itembag_list)
        itembag_list = [item for item in itembag_list if not (item.lower().endswith('ite') and item != 'key_stone')]
        purge_count += (original_count - len(itembag_list))

        with open(itembag_path, 'w') as f:
            json.dump(itembag_list, f, indent=2)
        print(f"[Mega Purge] Removed {purge_count} mega stones from itembag")

        # 2. Clear mega_stones from mega_state.json but keep key_stone_unlocked
        mega_state = _load_mega_state()
        stones_cleared = len(mega_state.get("mega_stones", {}))
        mega_state["mega_stones"] = {}
        _save_mega_state(mega_state)
        print(f"[Mega Purge] Cleared {stones_cleared} stone entries from mega_state")

        # 3. Remove mega stones from any Pokemon held_item slots
        try:
            global mypokemon_path
            with open(mypokemon_path, 'r') as f:
                pokemon_list = json.load(f)

            unequipped_count = 0
            for pokemon in pokemon_list:
                held_item = pokemon.get('held_item')
                if held_item and held_item.lower().endswith('ite') and held_item != 'key_stone':
                    pokemon['held_item'] = None
                    pokemon['is_mega'] = False
                    unequipped_count += 1

            if unequipped_count > 0:
                with open(mypokemon_path, 'w') as f:
                    json.dump(pokemon_list, f, indent=2)
                print(f"[Mega Purge] Unequipped {unequipped_count} mega stones from Pokemon")
        except Exception as e:
            print(f"[Mega Purge] Error clearing held items: {e}")

        total_purged = purge_count + stones_cleared + unequipped_count
        msg = f"Mega Stone Purge Complete!\n\n✓ Removed {purge_count} stones from inventory\n✓ Cleared {stones_cleared} stone entries from state\n✓ Unequipped {unequipped_count} stones from Pokemon\n\nTotal purged: {total_purged}"
        showInfo(msg)
        print(f"[Mega Purge] {msg}")
        return True

    except Exception as e:
        error_msg = f"Purge failed: {e}"
        showWarning(error_msg)
        print(f"[Mega Purge] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def _seed_specific_mega_stones():
    """Add exactly 3 mega stones: Scizorite, Ampharosite, Cameruptite"""
    try:
        print("[Mega Seed] Seeding specific mega stones...")

        # Define the 3 stones to seed
        stones_to_seed = [
            {"dex": 212, "name": "Scizorite"},
            {"dex": 181, "name": "Ampharosite"},
            {"dex": 323, "name": "Cameruptite"}
        ]

        # Load current inventory
        try:
            with open(itembag_path, 'r') as f:
                itembag_list = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            itembag_list = []

        # Load mega state
        mega_state = _load_mega_state()
        if "mega_stones" not in mega_state or not isinstance(mega_state["mega_stones"], dict):
            mega_state["mega_stones"] = {}

        seeded_stones = []
        for stone in stones_to_seed:
            # Add to inventory
            itembag_list.append(stone["name"])

            # Add to mega_state
            mega_state["mega_stones"][str(stone["dex"])] = mega_state["mega_stones"].get(str(stone["dex"]), 0) + 1

            seeded_stones.append(stone["name"])
            print(f"[Mega Seed] Added {stone['name']} (dex {stone['dex']})")

        # Save inventory
        with open(itembag_path, 'w') as f:
            json.dump(itembag_list, f, indent=2)

        # Save mega state
        _save_mega_state(mega_state)

        msg = f"Mega Stones Seeded!\n\nAdded to inventory:\n✓ Scizorite (Scizor)\n✓ Ampharosite (Ampharos)\n✓ Cameruptite (Camerupt)\n\nReady for testing!"
        showInfo(msg)
        print(f"[Mega Seed] Success: {', '.join(seeded_stones)}")
        return True

    except Exception as e:
        error_msg = f"Seed failed: {e}"
        showWarning(error_msg)
        print(f"[Mega Seed] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def _mega_system_self_test():
    """Comprehensive self-test of the entire Mega system"""
    try:
        print("\n" + "="*80)
        print("[MEGA SYSTEM SELF-TEST]")
        print("="*80)

        test_results = []
        errors = []

        # Test data
        test_pokemon = [
            {"dex": 181, "name": "ampharos", "stone": "Ampharosite"},
            {"dex": 212, "name": "scizor", "stone": "Scizorite"},
            {"dex": 323, "name": "camerupt", "stone": "Cameruptite"}
        ]

        global mypokemon_path

        # ===== TEST 1: Verify Pokemon exist =====
        print("\n[Test 1] Verifying Pokemon in collection...")
        try:
            with open(mypokemon_path, 'r') as f:
                pokemon_list = json.load(f)

            for test_pkmn in test_pokemon:
                found = any(p.get('id') == test_pkmn['dex'] or p.get('name', '').lower() == test_pkmn['name'].lower() for p in pokemon_list)
                if found:
                    test_results.append(f"✓ {test_pkmn['name'].capitalize()} found in collection")
                    print(f"  ✓ {test_pkmn['name'].capitalize()} exists")
                else:
                    errors.append(f"✗ {test_pkmn['name'].capitalize()} NOT found in collection")
                    print(f"  ✗ {test_pkmn['name'].capitalize()} NOT FOUND")
        except Exception as e:
            errors.append(f"✗ Failed to load Pokemon: {e}")
            print(f"  ✗ ERROR: {e}")

        # ===== TEST 2: Verify stones in inventory =====
        print("\n[Test 2] Verifying stones in inventory...")
        try:
            with open(itembag_path, 'r') as f:
                itembag_list = json.load(f)

            for test_pkmn in test_pokemon:
                if test_pkmn['stone'] in itembag_list:
                    test_results.append(f"✓ {test_pkmn['stone']} in inventory")
                    print(f"  ✓ {test_pkmn['stone']} found")
                else:
                    errors.append(f"✗ {test_pkmn['stone']} NOT in inventory")
                    print(f"  ✗ {test_pkmn['stone']} MISSING")
        except Exception as e:
            errors.append(f"✗ Failed to load inventory: {e}")
            print(f"  ✗ ERROR: {e}")

        # ===== TEST 3: Equip stones (simulate) =====
        print("\n[Test 3] Testing stone equip logic...")
        for test_pkmn in test_pokemon:
            try:
                # Find the Pokemon
                with open(mypokemon_path, 'r') as f:
                    pokemon_list = json.load(f)

                pokemon_found = None
                pokemon_idx = None
                for idx, p in enumerate(pokemon_list):
                    if p.get('id') == test_pkmn['dex'] or p.get('name', '').lower() == test_pkmn['name'].lower():
                        pokemon_found = p
                        pokemon_idx = idx
                        break

                if not pokemon_found:
                    errors.append(f"✗ Equip test: {test_pkmn['name']} not found")
                    print(f"  ✗ {test_pkmn['name']} not found for equip test")
                    continue

                # Simulate equipping the stone
                old_item = pokemon_found.get('held_item')
                pokemon_found['held_item'] = test_pkmn['stone']
                pokemon_list[pokemon_idx] = pokemon_found

                # Save temporarily
                with open(mypokemon_path, 'w') as f:
                    json.dump(pokemon_list, f, indent=2)

                # Verify it stuck
                with open(mypokemon_path, 'r') as f:
                    verify_list = json.load(f)
                verify_pkmn = verify_list[pokemon_idx]

                if verify_pkmn.get('held_item') == test_pkmn['stone']:
                    test_results.append(f"✓ {test_pkmn['name']} equipped {test_pkmn['stone']}")
                    print(f"  ✓ Equipped {test_pkmn['stone']} to {test_pkmn['name']}")
                else:
                    errors.append(f"✗ {test_pkmn['stone']} equip failed for {test_pkmn['name']}")
                    print(f"  ✗ Equip FAILED for {test_pkmn['name']}")

            except Exception as e:
                errors.append(f"✗ Equip test error for {test_pkmn['name']}: {e}")
                print(f"  ✗ ERROR equipping to {test_pkmn['name']}: {e}")

        # ===== TEST 4: Mega activation logic =====
        print("\n[Test 4] Testing Mega activation...")
        for test_pkmn in test_pokemon:
            try:
                with open(mypokemon_path, 'r') as f:
                    pokemon_list = json.load(f)

                pokemon_found = None
                pokemon_idx = None
                for idx, p in enumerate(pokemon_list):
                    if p.get('id') == test_pkmn['dex'] or p.get('name', '').lower() == test_pkmn['name'].lower():
                        pokemon_found = p
                        pokemon_idx = idx
                        break

                if not pokemon_found:
                    continue

                # Set is_mega = True
                pokemon_found['is_mega'] = True
                pokemon_list[pokemon_idx] = pokemon_found

                with open(mypokemon_path, 'w') as f:
                    json.dump(pokemon_list, f, indent=2)

                # Verify
                with open(mypokemon_path, 'r') as f:
                    verify_list = json.load(f)
                verify_pkmn = verify_list[pokemon_idx]

                if verify_pkmn.get('is_mega') == True:
                    test_results.append(f"✓ {test_pkmn['name']} mega flag set")
                    print(f"  ✓ Mega activated for {test_pkmn['name']}")
                else:
                    errors.append(f"✗ Mega flag failed for {test_pkmn['name']}")
                    print(f"  ✗ Mega activation FAILED for {test_pkmn['name']}")

            except Exception as e:
                errors.append(f"✗ Mega activation error for {test_pkmn['name']}: {e}")
                print(f"  ✗ ERROR: {e}")

        # ===== TEST 5: Sprite path resolution =====
        print("\n[Test 5] Testing sprite paths...")
        for test_pkmn in test_pokemon:
            try:
                global user_path_sprites
                mega_sprite_front = user_path_sprites / "front_mega_pokemon_gif" / f"{test_pkmn['dex']}.gif"
                mega_sprite_back = user_path_sprites / "back_mega_pokemon_gif" / f"{test_pkmn['dex']}.gif"
                normal_sprite_front = user_path_sprites / "front_default_gif" / f"{test_pkmn['dex']}.gif"
                normal_sprite_back = user_path_sprites / "back_default_gif" / f"{test_pkmn['dex']}.gif"

                has_mega_front = mega_sprite_front.exists()
                has_mega_back = mega_sprite_back.exists()
                has_normal_front = normal_sprite_front.exists()
                has_normal_back = normal_sprite_back.exists()

                if has_mega_front or has_mega_back or (has_normal_front and has_normal_back):
                    sprite_info = []
                    if has_mega_front:
                        sprite_info.append("mega front")
                    if has_mega_back:
                        sprite_info.append("mega back")
                    if not (has_mega_front or has_mega_back):
                        sprite_info.append("fallback normal")

                    test_results.append(f"✓ {test_pkmn['name']} sprites OK ({', '.join(sprite_info)})")
                    print(f"  ✓ Sprites found for {test_pkmn['name']}: {', '.join(sprite_info)}")
                else:
                    errors.append(f"✗ No sprites found for {test_pkmn['name']}")
                    print(f"  ✗ NO SPRITES for {test_pkmn['name']}")

            except Exception as e:
                errors.append(f"✗ Sprite check error for {test_pkmn['name']}: {e}")
                print(f"  ✗ ERROR: {e}")

        # ===== TEST 6: Unequip and revert =====
        print("\n[Test 6] Testing unequip/revert...")
        for test_pkmn in test_pokemon:
            try:
                with open(mypokemon_path, 'r') as f:
                    pokemon_list = json.load(f)

                pokemon_found = None
                pokemon_idx = None
                for idx, p in enumerate(pokemon_list):
                    if p.get('id') == test_pkmn['dex'] or p.get('name', '').lower() == test_pkmn['name'].lower():
                        pokemon_found = p
                        pokemon_idx = idx
                        break

                if not pokemon_found:
                    continue

                # Unequip and revert
                pokemon_found['held_item'] = None
                pokemon_found['is_mega'] = False
                pokemon_list[pokemon_idx] = pokemon_found

                with open(mypokemon_path, 'w') as f:
                    json.dump(pokemon_list, f, indent=2)

                # Verify
                with open(mypokemon_path, 'r') as f:
                    verify_list = json.load(f)
                verify_pkmn = verify_list[pokemon_idx]

                if verify_pkmn.get('held_item') is None and verify_pkmn.get('is_mega') == False:
                    test_results.append(f"✓ {test_pkmn['name']} unequipped/reverted")
                    print(f"  ✓ Unequipped {test_pkmn['name']}")
                else:
                    errors.append(f"✗ Unequip failed for {test_pkmn['name']}")
                    print(f"  ✗ Unequip FAILED for {test_pkmn['name']}")

            except Exception as e:
                errors.append(f"✗ Unequip error for {test_pkmn['name']}: {e}")
                print(f"  ✗ ERROR: {e}")

        # ===== FINAL RESULTS =====
        print("\n" + "="*80)
        print("[SELF-TEST RESULTS]")
        print("="*80)

        if not errors:
            result_msg = "✅ ALL TESTS PASSED!\n\n"
            result_msg += f"Passed: {len(test_results)}\n"
            result_msg += f"Failed: 0\n\n"
            result_msg += "Summary:\n" + "\n".join(test_results)
            print(result_msg)
            showInfo(result_msg)
            return True
        else:
            result_msg = "⚠️ TESTS COMPLETED WITH ERRORS\n\n"
            result_msg += f"Passed: {len(test_results)}\n"
            result_msg += f"Failed: {len(errors)}\n\n"
            result_msg += "Errors:\n" + "\n".join(errors[:10])  # Show first 10 errors
            if len(errors) > 10:
                result_msg += f"\n... and {len(errors) - 10} more errors"
            print(result_msg)
            showWarning(result_msg)
            return False

    except Exception as e:
        error_msg = f"Self-test crashed: {e}"
        showWarning(error_msg)
        print(f"[Mega Self-Test] CRASH: {e}")
        import traceback
        traceback.print_exc()
        return False

# ---------------------------------------------------------

if database_complete != False:
    # Load icons from icons/ folder
    try:
        icons_path_dir = addon_dir / "addon_sprites" / "icons"
        gameboy_icon = QIcon(str(icons_path_dir / "game-boy.png"))
        pokedex_icon = QIcon(str(icons_path_dir / "pokedex.gif"))  # Changed from "smaller pokedex.gif" to larger version
        pokeball_icon = QIcon(str(icons_path_dir / "poke.png"))
    except Exception as e:
        print(f"Could not load menu icons: {e}")
        gameboy_icon = QIcon()
        pokedex_icon = QIcon()
        pokeball_icon = QIcon()

    # REORGANIZED MENU STRUCTURE per request
    # 1. Open Ankimon Window (with game-boy icon)
    test_action10 = QAction(gameboy_icon, "Open Ankimon Window", mw)
    qconnect(test_action10.triggered, test_window.open_dynamic_window)
    mw.pokemenu.addAction(test_action10)

    # 2. Pokédex (with Pokédex icon - explicitly sized)
    complete_pokedex_action = QAction(pokedex_icon, "Pokédex", mw)
    qconnect(complete_pokedex_action.triggered, complete_pokedex.show_complete_pokedex)
    mw.pokemenu.addAction(complete_pokedex_action)
    # Set explicit icon size for Pokédex in menu
    try:
        from PyQt6.QtCore import QSize
        mw.pokemenu.setIconSize(QSize(24, 24))  # Larger icon size
    except Exception:
        pass

    # 3. Show Pokémon Collection (with Pokéball icon)
    pokecol_action = QAction(pokeball_icon, "Show Pokémon Collection", mw)
    qconnect(pokecol_action.triggered, pokecollection_win.show)
    mw.pokemenu.addAction(pokecol_action)

    # Define toggle_developer_mode function (used by menu item and F6 hotkey)
    def toggle_developer_mode():
        """Toggle Developer Mode menu visibility"""
        print("[DevMode] activated")  # Debug: shortcut fired
        showInfo("Developer Mode toggled")  # Immediate visual confirmation

        current_visible = developer_menu.menuAction().isVisible()
        developer_menu.menuAction().setVisible(not current_visible)
        if not current_visible:
            tooltipWithColour("Developer Mode: Enabled", "#00FF00")
            print("[DevMode] toggled: True")
        else:
            tooltipWithColour("Developer Mode: Hidden", "#888888")
            print("[DevMode] toggled: False")

        # Refresh Pokédex if it's open to update Force Encounter button visibility
        try:
            global complete_pokedex
            if complete_pokedex and complete_pokedex.isVisible():
                # Reload pokemon display to refresh button visibility
                complete_pokedex.display_pokemon(complete_pokedex.all_pokemon)
                print("[DevMode] Pokédex refreshed")
        except Exception as e:
            print(f"[DevMode] Error refreshing Pokédex: {e}")

    # 4. Developer Mode submenu (hidden by default, toggle with Option+Shift+9 hotkey)
    developer_menu = QMenu("Developer Mode", mw)
    mw.pokemenu.addMenu(developer_menu)
    developer_menu.menuAction().setVisible(False)  # Hidden by default

    # Developer Mode: Validate Rosters
    validate_rosters_action = QAction("🔍 Validate Rosters", mw)
    qconnect(validate_rosters_action.triggered, _ankimon_validate_rosters)
    developer_menu.addAction(validate_rosters_action)

    # Developer Mode: Export Debug Bundle
    export_debug_action = QAction("📦 Export Debug Bundle", mw)
    qconnect(export_debug_action.triggered, _ankimon_export_debug_bundle)
    developer_menu.addAction(export_debug_action)

    # Developer Mode: Reset Battle
    reset_battle_action = QAction("🔄 Reset Battle", mw)
    qconnect(reset_battle_action.triggered, reset_battle)
    developer_menu.addAction(reset_battle_action)

    # Developer Mode: Pokémon Placement Tool
    placement_tool_action = QAction("Pokémon Placement Tool", mw)
    qconnect(placement_tool_action.triggered, show_placement_tool)
    developer_menu.addAction(placement_tool_action)

    # Developer Mode: Reset Progression
    reset_progression_action = QAction("🔄 Reset Progression", mw)
    qconnect(reset_progression_action.triggered, _reset_progression)
    developer_menu.addAction(reset_progression_action)

    # Developer Mode: Ankimon Configure Menu
    try:
        configure_action = QAction("Ankimon Configure Menu", mw)
        def open_config():
            try:
                # Try modern Anki 24.11 API
                mw.addonManager.showConfigWindow("1908235722")
            except AttributeError:
                try:
                    # Fallback: open addons dialog
                    from aqt.addons import AddonsDialog
                    dialog = AddonsDialog(mw.addonManager)
                    dialog.exec()
                except Exception as e2:
                    showInfo(f"Please open config via: Tools → Add-ons → Ankimon → Config\n(Error: {e2})")
        qconnect(configure_action.triggered, open_config)
        developer_menu.addAction(configure_action)
    except Exception as e:
        print(f"Could not add config menu item: {e}")

    # Add separator before mega evolution tools
    developer_menu.addSeparator()

    # Developer Mode: Fresh Mega Restart
    try:
        fresh_restart_action = QAction("🔥 Fresh Mega Restart", mw)
        qconnect(fresh_restart_action.triggered, _fresh_mega_restart)
        developer_menu.addAction(fresh_restart_action)
        print("[DevMenu] Added: Fresh Mega Restart")
    except Exception as e:
        print(f"[DevMenu] ERROR: Could not add fresh restart: {e}")
        import traceback
        traceback.print_exc()

    # Add separator before Shadow Mewtwo controls
    developer_menu.addSeparator()

    # Developer Mode: Give Shadow Synergy Stone
    def dev_give_shadow_stone():
        """Give Shadow Synergy Stone to player"""
        try:
            with open(itembag_path, 'r') as json_file:
                itembag_list = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            itembag_list = []

        if "shadow-synergy-stone" not in itembag_list:
            itembag_list.append("shadow-synergy-stone")
            with open(itembag_path, 'w') as json_file:
                json.dump(itembag_list, json_file, indent=2)
            tooltipWithColour("Shadow Synergy Stone added to bag!", "#8B008B")
            _ankimon_log("INFO", "ShadowMewtwo", "Dev mode: Shadow Synergy Stone given")
        else:
            tooltipWithColour("You already have the Shadow Synergy Stone!", "#FFA500")

    give_shadow_stone_action = QAction("🌑 Give Shadow Synergy Stone", mw)
    qconnect(give_shadow_stone_action.triggered, dev_give_shadow_stone)
    developer_menu.addAction(give_shadow_stone_action)

    # Developer Mode: Trigger Shadow Mewtwo Encounter
    def dev_trigger_shadow_mewtwo():
        """Directly trigger Shadow Mewtwo encounter"""
        global test_window, pkmn_window
        try:
            if not _has_shadow_synergy_stone():
                tooltipWithColour("You need Shadow Synergy Stone! Giving you one...", "#FFA500")
                dev_give_shadow_stone()

            # Open battle window if not open
            if not pkmn_window:
                test_window.show()

            # Trigger encounter
            _trigger_shadow_mewtwo_encounter()
        except Exception as e:
            _ankimon_log("ERROR", "ShadowMewtwo", f"Dev mode trigger error: {e}")
            import traceback
            traceback.print_exc()

    trigger_shadow_mewtwo_action = QAction("👻 Trigger Shadow Mewtwo Encounter", mw)
    qconnect(trigger_shadow_mewtwo_action.triggered, dev_trigger_shadow_mewtwo)
    developer_menu.addAction(trigger_shadow_mewtwo_action)

    # Developer Mode: Reset Shadow Mewtwo (remove from captured)
    def dev_reset_shadow_mewtwo():
        """Remove Shadow Mewtwo from captured Pokemon"""
        try:
            if not mypokemon_path.is_file():
                tooltipWithColour("No captured Pokemon to reset!", "#888888")
                return

            with open(mypokemon_path, 'r') as json_file:
                pokemon_list = json.load(json_file)

            original_count = len(pokemon_list)
            pokemon_list = [p for p in pokemon_list if not (p.get("id") == 150 and p.get("variant") == "shadow")]
            removed_count = original_count - len(pokemon_list)

            if removed_count > 0:
                with open(mypokemon_path, 'w') as json_file:
                    json.dump(pokemon_list, json_file, indent=2)
                tooltipWithColour(f"Shadow Mewtwo removed from captured Pokemon! ({removed_count} removed)", "#8B008B")
                _ankimon_log("INFO", "ShadowMewtwo", f"Dev mode: Shadow Mewtwo reset ({removed_count} removed)")
            else:
                tooltipWithColour("Shadow Mewtwo not found in captured Pokemon!", "#888888")

        except Exception as e:
            _ankimon_log("ERROR", "ShadowMewtwo", f"Dev mode reset error: {e}")
            import traceback
            traceback.print_exc()

    reset_shadow_mewtwo_action = QAction("🔄 Reset Shadow Mewtwo Capture", mw)
    qconnect(reset_shadow_mewtwo_action.triggered, dev_reset_shadow_mewtwo)
    developer_menu.addAction(reset_shadow_mewtwo_action)

    # Add separator before Mega controls
    developer_menu.addSeparator()

    # Developer Mode: Toggle Mega for Active Pokemon
    try:
        toggle_mega_action = QAction("⚡ Toggle Mega for Active Pokémon", mw)
        qconnect(toggle_mega_action.triggered, _dev_toggle_mega_for_active)
        developer_menu.addAction(toggle_mega_action)
        print("[DevMenu] Added: Toggle Mega for Active Pokémon")
    except Exception as e:
        print(f"[DevMenu] ERROR: Could not add developer mega toggle: {e}")
        import traceback
        traceback.print_exc()

    # Developer Mode: Purge All Mega Stones
    try:
        purge_stones_action = QAction("🧹 Purge All Mega Stones", mw)
        qconnect(purge_stones_action.triggered, _purge_all_mega_stones)
        developer_menu.addAction(purge_stones_action)
        print("[DevMenu] Added: Purge All Mega Stones")
    except Exception as e:
        print(f"[DevMenu] ERROR: Could not add purge stones action: {e}")
        import traceback
        traceback.print_exc()

    # Developer Mode: Seed 3 Specific Mega Stones
    try:
        seed_stones_action = QAction("🌱 Seed 3 Test Mega Stones", mw)
        qconnect(seed_stones_action.triggered, _seed_specific_mega_stones)
        developer_menu.addAction(seed_stones_action)
        print("[DevMenu] Added: Seed 3 Test Mega Stones")
    except Exception as e:
        print(f"[DevMenu] ERROR: Could not add seed stones action: {e}")
        import traceback
        traceback.print_exc()

    # Developer Mode: Run Mega System Self-Test
    try:
        self_test_action = QAction("🔬 Run Mega System Self-Test", mw)
        qconnect(self_test_action.triggered, _mega_system_self_test)
        developer_menu.addAction(self_test_action)
        print("[DevMenu] Added: Run Mega System Self-Test")
    except Exception as e:
        print(f"[DevMenu] ERROR: Could not add self-test action: {e}")
        import traceback
        traceback.print_exc()

    # Confirmation log
    print("[DevMenu] Developer Mode actions added: purge/seed/self-test")

    # Developer Mode: Fast Battle Testing Toggle
    developer_menu.addSeparator()
    try:
        def toggle_fast_battle_testing():
            """Toggle fast battle testing (10-card intervals instead of 100/150/200)"""
            conf = _ankimon_get_col_conf()
            if not conf:
                tooltipWithColour("Failed to load configuration", "#FF0000")
                return

            current = conf.get("ankimon_fast_battle_testing", False)
            new_value = not current
            conf["ankimon_fast_battle_testing"] = new_value
            mw.col.setMod()  # Save config changes

            # Update checkbox state
            fast_testing_action.setChecked(new_value)

            if new_value:
                tooltipWithColour("Fast Battle Testing: ON (10-card intervals)", "#00FF00")
                print("[DevMode] Fast battle testing enabled: gym/elite/champion every 10 cards")
            else:
                tooltipWithColour("Fast Battle Testing: OFF (normal intervals)", "#888888")
                print("[DevMode] Fast battle testing disabled: normal intervals restored")

            # Refresh battle window if open
            global test_window
            if test_window is not None and hasattr(test_window, 'update_progress_label'):
                try:
                    test_window.update_progress_label()
                except:
                    pass

        fast_testing_action = QAction("⚡ Fast Battle Testing (10-card)", mw)
        fast_testing_action.setCheckable(True)

        # Set initial state from config
        conf = _ankimon_get_col_conf()
        if conf and conf.get("ankimon_fast_battle_testing", False):
            fast_testing_action.setChecked(True)

        qconnect(fast_testing_action.triggered, toggle_fast_battle_testing)
        developer_menu.addAction(fast_testing_action)
        print("[DevMenu] Added: Fast Battle Testing (10-card)")
    except Exception as e:
        print(f"[DevMenu] ERROR: Could not add fast battle testing toggle: {e}")
        import traceback
        traceback.print_exc()

    # Add keyboard shortcut to toggle Developer Mode visibility
    from PyQt6.QtGui import QKeySequence, QShortcut
    from PyQt6.QtCore import Qt

    # Option+Shift+9 (Alt+Shift+9) - macOS hotkey
    shortcut_dev_mode = QShortcut(QKeySequence("Alt+Shift+9"), mw)
    shortcut_dev_mode.setContext(Qt.ShortcutContext.ApplicationShortcut)  # Works across all windows
    qconnect(shortcut_dev_mode.activated, toggle_developer_mode)

    # Store in mw to prevent garbage collection
    mw._ankimon_dev_mode_shortcut = shortcut_dev_mode

    print("[DevMode] Hotkey registered: Option+Shift+9 (Alt+Shift+9)")
    print("[DevMode] Shortcut context: ApplicationShortcut (works in Deck Browser, Reviewer, Browser)")
    print("[DevMode] Menu item: 'Toggle Developer Mode' is always visible in Ankimon menu")

    # 5. Separator
    mw.pokemenu.addSeparator()

    # 6. Itembag
    test_action15 = QAction("Itembag", mw)
    test_action15.triggered.connect(item_window.show_window)
    mw.pokemenu.addAction(test_action15)

    # 7. Achievements
    achievement_bag_action = QAction("Achievements", mw)
    achievement_bag_action.triggered.connect(achievement_bag.show_window)
    mw.pokemenu.addAction(achievement_bag_action)

    test_action8 = QAction("Open Pokemon Showdown Teambuilder", mw)
    qconnect(test_action8.triggered, open_team_builder)
    mw.pokemenu.addAction(test_action8)

    test_action6 = QAction("Export Main Pokemon to PkmnShowdown", mw)
    qconnect(test_action6.triggered, export_to_pkmn_showdown)
    mw.pokemenu.addAction(test_action6)

    test_action7 = QAction("Export All Pokemon to PkmnShowdown", mw)
    qconnect(test_action7.triggered, export_all_pkmn_showdown)
    mw.pokemenu.addAction(test_action7)

test_action11 = QAction("Check Effectiveness Chart", mw)
test_action11.triggered.connect(eff_chart.show_eff_chart)
mw.pokemenu.addAction(test_action11)

test_action12 = QAction("Check Generations and Pokemon Chart", mw)
test_action12.triggered.connect(gen_id_chart.show_gen_chart)
mw.pokemenu.addAction(test_action12)

test_action3 = QAction("Download Resources", mw)
qconnect(test_action3.triggered, show_agreement_and_download_database)
mw.pokemenu.addAction(test_action3)

test_action14 = QAction("Credits", mw)
test_action14.triggered.connect(credits.show_window)
mw.pokemenu.addAction(test_action14)

test_action13 = QAction("About and License", mw)
test_action13.triggered.connect(license.show_window)
mw.pokemenu.addAction(test_action13)

help_action = QAction("Open Help Guide", mw)
help_action.triggered.connect(open_help_window)
mw.pokemenu.addAction(help_action)

test_action16 = QAction("Report Bug", mw)
test_action16.triggered.connect(report_bug)
mw.pokemenu.addAction(test_action16)

rate_action = QAction("Rate This", mw)
rate_action.triggered.connect(rate_addon_url)
mw.pokemenu.addAction(rate_action)

    #https://goo.gl/uhAxsg
    #https://www.reddit.com/r/PokemonROMhacks/comments/9xgl7j/pokemon_sound_effects_collection_over_3200_sfx/
    #https://archive.org/details/pokemon-dp-sound-library-disc-2_202205

"""
Future Code Notes

       mw_x = mw.x()
        mw_y = mw.y()
        width = mw.width()
        height = mw.height()
        akw_height = self.height()
        akw_width = self.width()

        amw_center = True
        if amw_center is True:
            if height > akw_height:
                y = int(mw_y + ((height/2) - (akw_height/2)))
            else:
                y = int(mw_y + ((akw_height/2) - (height/2)))
        amw_left = True
        amw_right = False
        if amw_right is True:
            x = int(mw_x + width)
        elif amw_left is True:
            x = int(mw_x-(akw_width))"""


# ================== GYM COUNTER OVERLAY (SAFE) ==================
# Adds an on-screen gym counter and triggers at 100 cards.
# Designed for Anki 24.11 hook signatures.

from aqt import mw
from aqt.qt import QMessageBox
from aqt import gui_hooks
import json

# Battle interval targets - can be overridden by dev mode
ANKIMON_GYM_TARGET = 100
ANKIMON_ELITE_FOUR_TARGET = 150
ANKIMON_CHAMPION_TARGET = 200

# Dev mode: Fast battle testing (10-card intervals)
ANKIMON_FAST_TESTING_INTERVAL = 10

def _ankimon_get_battle_interval_gym():
    """Get gym battle interval (100 normal, 10 if fast testing enabled)"""
    conf = _ankimon_get_col_conf()
    if conf and conf.get("ankimon_fast_battle_testing", False):
        return ANKIMON_FAST_TESTING_INTERVAL
    return ANKIMON_GYM_TARGET

def _ankimon_get_battle_interval_elite_four():
    """Get Elite Four battle interval (150 normal, 10 if fast testing enabled)"""
    conf = _ankimon_get_col_conf()
    if conf and conf.get("ankimon_fast_battle_testing", False):
        return ANKIMON_FAST_TESTING_INTERVAL
    return ANKIMON_ELITE_FOUR_TARGET

def _ankimon_get_battle_interval_champion():
    """Get Champion battle interval (200 normal, 10 if fast testing enabled)"""
    conf = _ankimon_get_col_conf()
    if conf and conf.get("ankimon_fast_battle_testing", False):
        return ANKIMON_FAST_TESTING_INTERVAL
    return ANKIMON_CHAMPION_TARGET

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

def _ankimon_elite_four_state():
    """Get the current Elite Four card counter from persistent storage."""
    conf = _ankimon_get_col_conf()
    if conf is None:
        return 0
    return int(conf.get("ankimon_elite_four_counter", 0))

def _ankimon_set_elite_four_state(val: int):
    """Set the Elite Four card counter in persistent storage."""
    conf = _ankimon_get_col_conf()
    if conf is not None:
        conf["ankimon_elite_four_counter"] = int(val)
        mw.col.setMod()

def _ankimon_champion_state():
    """Get the current Champion card counter from persistent storage."""
    conf = _ankimon_get_col_conf()
    if conf is None:
        return 0
    return int(conf.get("ankimon_champion_counter", 0))

def _ankimon_set_champion_state(val: int):
    """Set the Champion card counter in persistent storage."""
    conf = _ankimon_get_col_conf()
    if conf is not None:
        conf["ankimon_champion_counter"] = int(val)
        mw.col.setMod()

def _ankimon_all_gym_badges_earned():
    """Check if all 8 gym badges have been earned"""
    try:
        global achievements
        # Gym badges are IDs 25-32
        for badge_id in range(25, 33):
            if not check_for_badge(achievements, badge_id):
                return False
        return True
    except Exception:
        return False

def _ankimon_all_elite_four_defeated():
    """Check if all 4 Elite Four members have been defeated this round"""
    try:
        stats = _load_progression_stats()
        # Check if all 4 members defeated in current round
        return stats["current_round"].get("elite_four_defeated", 0) >= 4
    except Exception:
        return False

def _get_scaled_level(base_level, current_round):
    """Calculate scaled Pokemon level based on current round

    Args:
        base_level: Base level from original game (e.g., 12 for Roark's Geodude)
        current_round: Current progression round (1, 2, 3, etc.)

    Returns:
        Scaled level for this round
    """
    if current_round <= 1:
        return base_level

    # Scaling formula: add 20-25 levels per round
    level_increase = (current_round - 1) * 22  # 22 levels per round average
    scaled_level = base_level + level_increase

    # Cap at level 100
    return min(scaled_level, 100)

def _get_gym_base_levels():
    """Get base levels for gym leaders (Round 1 canonical levels)"""
    return {
        "roark": [12, 12, 14],  # Geodude, Onix, Cranidos
        "gardenia": [19, 19, 22],  # Cherubi, Turtwig, Roserade
        "maylene": [27, 27, 30],  # Meditite, Machoke, Lucario
        "crasher_wake": [27, 29, 33],  # Gyarados, Quagsire, Floatzel
        "fantina": [32, 34, 36],  # Duskull, Haunter, Mismagius
        "byron": [36, 36, 39],  # Magneton, Steelix, Bastiodon
        "candice": [38, 38, 40, 42],  # Snover, Sneasel, Medicham, Abomasnow
        "volkner": [46, 46, 48, 50]  # Raichu, Ambipom, Octillery, Luxray (note: actual Volkner has different team)
    }

def _get_elite_four_base_levels():
    """Get base levels for Elite Four members (Round 1 canonical levels)"""
    return {
        "aaron": [49, 49, 51, 53, 53],  # Dustox, Beautifly, Vespiquen, Heracross, Drapion
        "bertha": [50, 52, 52, 53, 55],  # Whiscash, Sudowoodo, Golem, Hippowdon, Rhyperior
        "flint": [52, 53, 53, 55, 57],  # Houndoom, Flareon, Rapidash, Infernape, Magmortar
        "lucian": [53, 53, 54, 55, 59]  # Mr. Mime, Espeon, Bronzong, Alakazam, Gallade
    }

def _get_champion_base_levels():
    """Get base levels for Champion Cynthia (Round 1 canonical levels)"""
    return [58, 58, 58, 60, 60, 62]  # Spiritomb, Roserade, Togekiss, Lucario, Milotic, Garchomp

def _ankimon_gym_overlay_html(count: int) -> str:
    gym_target = _ankimon_get_battle_interval_gym()
    pct = int((count / gym_target) * 100)
    if pct < 0:
        pct = 0
    if pct > 100:
        pct = 100
    return f"""
    <div id="ankimon-gym-counter" style="
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 9999;
        background: rgba(0,0,0,0.55);
        color: #fff;
        padding: 8px 10px;
        border-radius: 10px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial;
        font-size: 12px;
        line-height: 1.2;
        min-width: 160px;
        ">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
        <div>Gym</div>
        <div style="opacity:0.95;">{count}/{gym_target}</div>
      </div>
      <div style="margin-top:6px; height:6px; background: rgba(255,255,255,0.25); border-radius: 999px; overflow:hidden;">
        <div style="height:100%; width:{pct}%; background: rgba(255,255,255,0.9);"></div>
      </div>
    </div>
    """

def _ankimon_render_gym_overlay(reviewer=None):
    try:
        if reviewer is None:
            reviewer = mw.reviewer
        if reviewer is None or reviewer.web is None:
            return
        count = _ankimon_gym_state()
        html = _ankimon_gym_overlay_html(count)
        js = """
        (function(){
          var el = document.getElementById('ankimon-gym-counter');
          if (el) { el.remove(); }
          var tmp = document.createElement('div');
          tmp.innerHTML = %s;
          document.body.appendChild(tmp.firstElementChild);
        })();
        """ % (json.dumps(html))
        reviewer.web.eval(js)
    except Exception:
        pass


def _ankimon_show_gym_leader_dialog(leader: dict):
    """Step 1 UI: show leader sprite GIF + Start/Later."""
    try:
        dlg = QDialog(mw)
        dlg.setWindowTitle(f"Gym Battle: {leader.get('name','Gym')}")
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)

        title = QLabel(f"{leader.get('name','Gym')} Gym ({leader.get('type','')})")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: 700; font-size: 14px;")
        layout.addWidget(title)

        # Get current round for level scaling
        try:
            stats = _load_progression_stats()
            current_round = stats["lifetime"].get("current_round", 1)
        except:
            current_round = 1

        # Display Pokemon team with names and levels
        team_ids = leader.get("team", [])
        base_levels = _get_gym_base_levels().get(leader.get("key", ""), [])

        team_info = QLabel("Opponent Team:")
        team_info.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(team_info)

        for i, pokemon_id in enumerate(team_ids):
            try:
                pokemon_name = search_pokedex_by_id(pokemon_id)
                base_level = base_levels[i] if i < len(base_levels) else 10 + (i * 5)
                scaled_level = _get_scaled_level(base_level, current_round)

                # Mark the ace (last Pokemon) with a star
                ace_marker = " (ACE)" if i == len(team_ids) - 1 else ""
                pokemon_label = QLabel(f"  • {pokemon_name} (Lv. {scaled_level}){ace_marker}")
                pokemon_label.setStyleSheet("font-size: 11px; padding: 2px;")
                layout.addWidget(pokemon_label)
            except:
                pass

        layout.addSpacing(10)

        gif_label = QLabel()
        gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        gif_name = leader.get("gif")
        gif_path = os.path.join(addon_dir, "addon_sprites", "gym_leaders", gif_name) if gif_name else ""
        if gif_name and os.path.exists(gif_path):
            movie = QMovie(gif_path)
            gif_label.setMovie(movie)
            movie.start()
        else:
            gif_label.setText(f"(Missing gym leader GIF for {leader.get('name','Gym')})\nPlace it in addon_sprites/gym_leaders/")
        layout.addWidget(gif_label)

        # Show round info if not Round 1
        if current_round > 1:
            round_info = QLabel(f"Round {current_round} - Pokemon levels scaled up!")
            round_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            round_info.setStyleSheet("color: #FF6B6B; font-weight: bold; font-size: 11px; padding: 5px;")
            layout.addWidget(round_info)

        btn_row = QHBoxLayout()
        start_btn = QPushButton("Start Gym Battle")
        later_btn = QPushButton("Later")
        btn_row.addWidget(start_btn)
        btn_row.addWidget(later_btn)
        layout.addLayout(btn_row)

        def _start():
            conf = _ankimon_get_col_conf()
            if conf is None:
                QMessageBox.information(mw, "Gym", "Collection not ready yet.")
                dlg.accept()
                return
            conf["ankimon_gym_active"] = True
            conf["ankimon_gym_enemy_ids"] = leader.get("team", [])
            conf["ankimon_gym_enemy_index"] = 0
            conf["ankimon_gym_leader_key"] = leader.get("key")
            # Note: counter already reset when reaching 100, no need to reset again
            mw.col.setMod()

            # CRITICAL: Set battle state to gym BEFORE opening window
            _ankimon_set_battle_state("gym")
            _ankimon_log("INFO", "AnkimonBattle", f"Starting gym battle vs {leader.get('name', 'Gym Leader')}")

            dlg.accept()
            try:
                open_test_window()
            except Exception:
                pass

        start_btn.clicked.connect(_start)
        later_btn.clicked.connect(lambda: dlg.reject())

        dlg.exec()
    except Exception as e:
        try:
            QMessageBox.information(mw, "Gym", f"Could not open gym leader dialog: {e}")
        except Exception:
            pass

def reset_gym_progress():
    """Reset all gym battle progress to fix stuck states."""
    try:
        conf = _ankimon_get_col_conf()
        if conf is None:
            showInfo("Cannot reset gym progress - collection config not available.")
            return

        # Reset all gym-related config
        conf["ankimon_gym_active"] = False
        conf["ankimon_gym_pending"] = False
        conf["ankimon_gym_enemy_ids"] = []
        conf["ankimon_gym_enemy_index"] = 0
        conf["ankimon_gym_leader_key"] = None
        conf["ankimon_gym_leader_name"] = None
        conf["ankimon_gym_leader_type"] = None
        conf["ankimon_gym_counter"] = 0
        conf["ankimon_gym_index"] = 0
        conf["ankimon_gym_current_enemy_id"] = None
        conf["ankimon_gym_last_cleared_leader"] = None

        mw.col.setMod()

        # Force spawn new wild pokemon to clear any stuck state
        try:
            new_pokemon()
        except Exception:
            pass

        showInfo("Gym progress has been reset. You can now start fresh with gym battles.")
    except Exception as e:
        showWarning(f"Error resetting gym progress: {e}")

def _ankimon_gym_ready_popup():
    """Prompt when gym is ready; lets user start a gym run (leader intro only for now)."""
    try:
        # Persistent state in collection config
        conf = getattr(mw, "col", None) and getattr(mw.col, "conf", None)
        if conf is None:
            QMessageBox.information(mw, "Gym Battle Ready!", "Gym Battle Ready! You reached 100 reviewed cards.")
            return

        # Leaders in DP order
        leaders = [
            {"key": "roark", "name": "Roark", "type": "Rock", "gif": "roark.gif", "team": [74, 95, 408]},
            {"key": "gardenia", "name": "Gardenia", "type": "Grass", "gif": "gardenia.gif", "team": [420, 387, 407]},
            {"key": "maylene", "name": "Maylene", "type": "Fighting", "gif": "maylene.gif", "team": [307, 67, 448]},
            {"key": "crasher_wake", "name": "Crasher Wake", "type": "Water", "gif": "crasher_wake.gif", "team": [130, 195, 419]},
            {"key": "fantina", "name": "Fantina", "type": "Ghost", "gif": "fantina.gif", "team": [426, 94, 429]},
            {"key": "byron", "name": "Byron", "type": "Steel", "gif": "byron.gif", "team": [436, 208, 411]},
            {"key": "candice", "name": "Candice", "type": "Ice", "gif": "candice.gif", "team": [459, 215, 308, 460]},
            {"key": "volkner", "name": "Volkner", "type": "Electric", "gif": "volkner.gif", "team": [26, 424, 224, 405]},
        ]
        idx =  int(conf.get("ankimon_gym_index", 0)) % len(leaders)
        leader = leaders[idx]

        # Dialog
        dlg = QDialog(mw)
        dlg.setWindowTitle("Gym Battle: %s" % leader["name"])
        outer = QVBoxLayout(dlg)

        title = QLabel(" %s Gym (%s)" % (leader["name"], leader["type"]))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(title)

        # Leader GIF (optional)
        gif_path = os.path.join(os.path.dirname(__file__), "addon_sprites", "gym_leaders", "%s.gif" % leader["key"])
        if os.path.exists(gif_path):
            gif_label = QLabel()
            gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            movie = QMovie(gif_path)
            movie.start()
            gif_label.setMovie(movie)
            outer.addWidget(gif_label)
            # keep refs alive
            dlg._ankimon_movie = movie
            dlg._ankimon_gif_label = gif_label
        else:
            msg = QLabel("(Missing gym leader GIF for %s) Place it in addon_sprites/gym_leaders/" % leader["name"])
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            outer.addWidget(msg)

        btn_row = QHBoxLayout()
        start_btn = QPushButton("Start Gym Battle")
        later_btn = QPushButton("Later")
        btn_row.addWidget(start_btn)
        btn_row.addWidget(later_btn)
        outer.addLayout(btn_row)

        def _start():
            # Set pending gym battle flag instead of starting immediately
            conf["ankimon_gym_pending"] = True
            conf["ankimon_gym_leader_key"] = leader["key"]
            conf["ankimon_gym_leader_name"] = leader["name"]
            conf["ankimon_gym_leader_type"] = leader["type"]
            conf["ankimon_gym_index"] = idx
            # Set gym enemy team for when battle actually starts
            conf["ankimon_gym_enemy_ids"] = leader.get("team", [])
            mw.col.setMod()
            _ankimon_log("INFO", "AnkimonBattle", f"Gym battle queued: {leader['name']} - will start after current battle")
            dlg.accept()
            # Show message that gym will start after current match
            try:
                tooltipWithColour("Gym battle will begin after current match", "#FFD700")
            except Exception:
                pass

        def _later():
            dlg.reject()

        start_btn.clicked.connect(_start)
        later_btn.clicked.connect(_later)

        dlg.exec()

        # If user started gym, open Ankimon window to show overlay immediately
        if conf.get("ankimon_gym_active"):
            try:
                # try common entrypoints; ignore if not present
                if "open_ankimon_window" in globals():
                    open_ankimon_window()
                elif "open_test_window" in globals():
                    open_test_window()
            except Exception:
                pass

    except Exception:
        try:
            QMessageBox.information(mw, "Gym Battle Ready!", "Gym Battle Ready! You reached 100 reviewed cards.")
        except Exception:
            pass
def _ankimon_elite_four_ready_popup():
    """Prompt when Elite Four battle is ready"""
    try:
        # Elite Four members (Sinnoh)
        members = [
            {"key": "aaron", "name": "Aaron", "type": "Bug", "team": [269, 212, 416, 214, 452]},  # Dustox, Scizor, Vespiquen, Heracross, Drapion
            {"key": "bertha", "name": "Bertha", "type": "Ground", "team": [195, 185, 340, 450, 31]},  # Quagsire, Sudowoodo, Whiscash, Hippowdon, Nidoqueen
            {"key": "flint", "name": "Flint", "type": "Fire", "team": [392, 229, 78, 136, 467]},  # Infernape, Houndoom, Rapidash, Flareon, Magmortar
            {"key": "lucian", "name": "Lucian", "type": "Psychic", "team": [122, 437, 178, 561, 475]}  # Mr. Mime, Bronzong, Xatu, Sigilyph, Gallade
        ]

        conf = _ankimon_get_col_conf()
        if conf is None:
            QMessageBox.information(mw, "Elite Four Ready!", "Elite Four Battle Ready!")
            return

        # Determine which member is next (0-3)
        member_index = int(conf.get("ankimon_elite_four_index", 0)) % 4
        member = members[member_index]

        # Create dialog
        dlg = QDialog(mw)
        dlg.setWindowTitle(f"Elite Four - {member['name']}")
        dlg.setMinimumWidth(400)
        outer = QVBoxLayout()
        dlg.setLayout(outer)

        # Title
        title = QLabel(f"Elite Four {member['name']} ({member['type']} Type)")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        outer.addWidget(title)

        # Elite Four member GIF sprite
        gif_path = os.path.join(os.path.dirname(__file__), "addon_sprites", "elite_four_champion_gif", f"{member['key']}.gif")
        if os.path.exists(gif_path):
            gif_label = QLabel()
            gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            movie = QMovie(gif_path)
            movie.start()
            gif_label.setMovie(movie)
            outer.addWidget(gif_label)
            # keep refs alive
            dlg._ankimon_movie = movie
            dlg._ankimon_gif_label = gif_label
        else:
            # Fallback message if GIF not found
            msg = QLabel(f"(GIF sprite for {member['name']} not found)\nPlace {member['key']}.gif in addon_sprites/elite_four_champion_gif/")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("color: #888888; font-size: 10px; padding: 5px;")
            outer.addWidget(msg)

        # Get current round for level scaling
        try:
            stats = _load_progression_stats()
            current_round = stats["lifetime"].get("current_round", 1)
        except:
            current_round = 1

        # Display Pokemon team with names and levels
        team_ids = member.get("team", [])
        base_levels = _get_elite_four_base_levels().get(member.get("key", ""), [])

        team_info = QLabel("Opponent Team:")
        team_info.setStyleSheet("font-weight: bold; font-size: 13px; padding: 5px;")
        team_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(team_info)

        for i, pokemon_id in enumerate(team_ids):
            try:
                pokemon_name = search_pokedex_by_id(pokemon_id)
                base_level = base_levels[i] if i < len(base_levels) else 50 + (i * 2)
                scaled_level = _get_scaled_level(base_level, current_round)

                # Mark the ace (last Pokemon) with a star
                ace_marker = " (ACE)" if i == len(team_ids) - 1 else ""
                pokemon_label = QLabel(f"  • {pokemon_name} (Lv. {scaled_level}){ace_marker}")
                pokemon_label.setStyleSheet("font-size: 12px; padding: 2px;")
                outer.addWidget(pokemon_label)
            except:
                pass

        # Show round info if not Round 1
        if current_round > 1:
            round_info = QLabel(f"Round {current_round} - Elite Four leveled up!")
            round_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            round_info.setStyleSheet("color: #FF6B6B; font-weight: bold; font-size: 12px; padding: 10px;")
            outer.addWidget(round_info)

        outer.addSpacing(10)

        # Buttons
        btn_row = QHBoxLayout()
        start_btn = QPushButton("Start Elite Four Battle")
        later_btn = QPushButton("Later")
        btn_row.addWidget(start_btn)
        btn_row.addWidget(later_btn)
        outer.addLayout(btn_row)

        def _start():
            conf["ankimon_elite_four_pending"] = True
            conf["ankimon_elite_four_member_key"] = member["key"]
            conf["ankimon_elite_four_member_name"] = member["name"]
            conf["ankimon_elite_four_member_type"] = member["type"]
            conf["ankimon_elite_four_index"] = member_index

            # Validate roster for duplicates
            team = member.get("team", [])
            if len(team) != len(set(team)):
                duplicates = [x for i, x in enumerate(team) if x in team[:i]]
                _ankimon_log("ERROR", "AnkimonBattle", f"Elite Four {member['name']} roster contains duplicates: {duplicates}")
                print(f"[ROSTER ERROR] {member['name']} has duplicate Pokemon IDs: {duplicates}")
                print(f"[ROSTER ERROR] Full roster: {team}")
                # Remove duplicates while preserving order
                seen = set()
                team = [x for x in team if not (x in seen or seen.add(x))]
                _ankimon_log("WARN", "AnkimonBattle", f"Removed duplicates, new roster: {team}")
                print(f"[ROSTER FIX] Deduplicated roster: {team}")

            conf["ankimon_elite_four_enemy_ids"] = team
            mw.col.setMod()
            _ankimon_log("INFO", "AnkimonBattle", f"Elite Four battle queued: {member['name']} - will start after current battle")
            dlg.accept()
            try:
                tooltipWithColour("Elite Four battle will begin after current match", "#FFD700")
            except Exception:
                pass

        def _later():
            dlg.reject()

        start_btn.clicked.connect(_start)
        later_btn.clicked.connect(_later)
        dlg.exec()

    except Exception as e:
        print(f"Error in Elite Four popup: {e}")
        try:
            QMessageBox.information(mw, "Elite Four Ready!", "Elite Four Battle Ready!")
        except Exception:
            pass

def _ankimon_champion_ready_popup():
    """Prompt when Champion battle is ready"""
    try:
        conf = _ankimon_get_col_conf()
        if conf is None:
            QMessageBox.information(mw, "Champion Ready!", "Champion Battle Ready!")
            return

        # Champion Cynthia team
        champion_team = [442, 407, 350, 445, 59, 448]  # Spiritomb, Roserade, Milotic, Garchomp, Arcanine, Lucario

        # Create dialog
        dlg = QDialog(mw)
        dlg.setWindowTitle("Champion Cynthia")
        dlg.setMinimumWidth(400)
        outer = QVBoxLayout()
        dlg.setLayout(outer)

        # Title
        title = QLabel("Champion Cynthia")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        outer.addWidget(title)

        # Champion GIF sprite
        gif_path = os.path.join(os.path.dirname(__file__), "addon_sprites", "elite_four_champion_gif", "cynthia.gif")
        if os.path.exists(gif_path):
            gif_label = QLabel()
            gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            movie = QMovie(gif_path)
            movie.start()
            gif_label.setMovie(movie)
            outer.addWidget(gif_label)
            # keep refs alive
            dlg._ankimon_movie = movie
            dlg._ankimon_gif_label = gif_label
        else:
            # Fallback message if GIF not found
            msg = QLabel("(GIF sprite for Champion Cynthia not found)\nPlace cynthia.gif in addon_sprites/elite_four_champion_gif/")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("color: #888888; font-size: 10px; padding: 5px;")
            outer.addWidget(msg)

        # Get current round for level scaling
        try:
            stats = _load_progression_stats()
            current_round = stats["lifetime"].get("current_round", 1)
        except:
            current_round = 1

        # Display Pokemon team with names and levels
        base_levels = _get_champion_base_levels()

        team_info = QLabel("Champion's Team:")
        team_info.setStyleSheet("font-weight: bold; font-size: 13px; padding: 5px;")
        team_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(team_info)

        for i, pokemon_id in enumerate(champion_team):
            try:
                pokemon_name = search_pokedex_by_id(pokemon_id)
                base_level = base_levels[i] if i < len(base_levels) else 58 + (i * 2)
                scaled_level = _get_scaled_level(base_level, current_round)

                # Mark the ace (Garchomp) with a star
                ace_marker = " (ACE)" if i == len(champion_team) - 1 else ""
                pokemon_label = QLabel(f"  • {pokemon_name} (Lv. {scaled_level}){ace_marker}")
                pokemon_label.setStyleSheet("font-size: 12px; padding: 2px;")
                outer.addWidget(pokemon_label)
            except:
                pass

        warning = QLabel("This is the final challenge!")
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning.setStyleSheet("color: #FF6B6B; font-weight: bold; font-size: 14px; padding: 10px;")
        outer.addWidget(warning)

        # Show round info if not Round 1
        if current_round > 1:
            round_info = QLabel(f"Round {current_round} - Champion at peak strength!")
            round_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            round_info.setStyleSheet("color: #FFD700; font-weight: bold; font-size: 12px; padding: 5px;")
            outer.addWidget(round_info)

        outer.addSpacing(10)

        # Buttons
        btn_row = QHBoxLayout()
        start_btn = QPushButton("Challenge Champion")
        later_btn = QPushButton("Later")
        btn_row.addWidget(start_btn)
        btn_row.addWidget(later_btn)
        outer.addLayout(btn_row)

        def _start():
            conf["ankimon_champion_pending"] = True

            # Validate Champion roster for duplicates
            team = champion_team[:]  # Make a copy
            if len(team) != len(set(team)):
                duplicates = [x for i, x in enumerate(team) if x in team[:i]]
                _ankimon_log("ERROR", "AnkimonBattle", f"Champion Cynthia roster contains duplicates: {duplicates}")
                print(f"[ROSTER ERROR] Champion has duplicate Pokemon IDs: {duplicates}")
                print(f"[ROSTER ERROR] Full roster: {team}")
                # Remove duplicates while preserving order
                seen = set()
                team = [x for x in team if not (x in seen or seen.add(x))]
                _ankimon_log("WARN", "AnkimonBattle", f"Removed duplicates, new roster: {team}")
                print(f"[ROSTER FIX] Deduplicated roster: {team}")

            conf["ankimon_champion_enemy_ids"] = team
            mw.col.setMod()
            _ankimon_log("INFO", "AnkimonBattle", "Champion battle queued: Cynthia - will start after current battle")
            dlg.accept()
            try:
                tooltipWithColour("Champion battle will begin after current match", "#FFD700")
            except Exception:
                pass

        def _later():
            dlg.reject()

        start_btn.clicked.connect(_start)
        later_btn.clicked.connect(_later)
        dlg.exec()

    except Exception as e:
        print(f"Error in Champion popup: {e}")
        try:
            QMessageBox.information(mw, "Champion Ready!", "Champion Battle Ready!")
        except Exception:
            pass

def _ankimon_gym_on_answer(*args):
    try:
        # Only increment gym counter if all gyms haven't been completed yet
        if not _ankimon_all_gym_badges_earned():
            c = _ankimon_gym_state() + 1
            gym_target = _ankimon_get_battle_interval_gym()
            if c >= gym_target:
                _ankimon_set_gym_state(0)
                _ankimon_gym_ready_popup()
            else:
                _ankimon_set_gym_state(c)
        # After all gyms, check Elite Four
        elif _ankimon_all_gym_badges_earned() and not _ankimon_all_elite_four_defeated():
            e = _ankimon_elite_four_state() + 1
            elite_target = _ankimon_get_battle_interval_elite_four()
            if e >= elite_target:
                _ankimon_set_elite_four_state(0)
                _ankimon_elite_four_ready_popup()
            else:
                _ankimon_set_elite_four_state(e)
        # After Elite Four, check Champion
        elif _ankimon_all_elite_four_defeated():
            ch = _ankimon_champion_state() + 1
            champion_target = _ankimon_get_battle_interval_champion()
            if ch >= champion_target:
                _ankimon_set_champion_state(0)
                _ankimon_champion_ready_popup()
            else:
                _ankimon_set_champion_state(ch)
    except Exception:
        pass
    # Overlay removed - progress now shown in Ankimon window
    # _ankimon_render_gym_overlay(mw.reviewer)

def _ankimon_gym_on_question(*args):
    # Overlay removed - progress now shown in Ankimon window
    # _ankimon_render_gym_overlay(mw.reviewer)
    pass

def _ankimon_check_incomplete_gym():
    """Check for incomplete gym battles on startup and prompt user to continue"""
    try:
        conf = _ankimon_get_col_conf()
        if not conf:
            return

        # Check if there's an active or pending gym battle
        gym_active = conf.get("ankimon_gym_active", False)
        gym_pending = conf.get("ankimon_gym_pending", False)

        if gym_active or gym_pending:
            leader_name = conf.get("ankimon_gym_leader_name", "Gym Leader")
            enemy_ids = conf.get("ankimon_gym_enemy_ids") or []
            current_idx = int(conf.get("ankimon_gym_enemy_index") or 0)

            if not enemy_ids:
                # Corrupted state, reset
                conf["ankimon_gym_active"] = False
                conf["ankimon_gym_pending"] = False
                mw.col.setMod()
                return

            remaining = len(enemy_ids) - current_idx
            if remaining <= 0:
                # Gym was completed but state not cleared, reset
                conf["ankimon_gym_active"] = False
                conf["ankimon_gym_pending"] = False
                mw.col.setMod()
                return

            # Ask user if they want to continue the gym battle
            msg = f"You have an incomplete gym battle against {leader_name}.\n"
            msg += f"{remaining} Pokémon remaining.\n\n"
            msg += "Would you like to continue the gym battle?"

            reply = QMessageBox.question(
                mw,
                "Continue Gym Battle?",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Continue the gym battle
                _ankimon_log("INFO", "AnkimonBattle", f"User chose to resume gym battle vs {leader_name} ({remaining} pokemon remaining)")

                if gym_pending:
                    # Was pending, activate it now
                    conf["ankimon_gym_active"] = True
                    conf["ankimon_gym_pending"] = False
                    mw.col.setMod()

                # CRITICAL: Fully initialize gym battle state
                try:
                    # 1. Set battle state to gym
                    _ankimon_set_battle_state("gym")
                    _ankimon_log("INFO", "AnkimonBattle", f"Set battle state to gym, index={current_idx}, remaining={remaining}")

                    # 2. Force-close any lingering post-battle UI
                    _ankimon_close_post_battle_ui("gym resume initialization")

                    # 2.5. Clear any stale sprites from before restart
                    _ankimon_clear_stale_enemy_sprites()

                    # 3. Spawn the current gym pokemon (at current_idx)
                    global pkmn_window, test_window
                    if pkmn_window is True:
                        # Spawn current gym pokemon
                        new_pokemon()
                        _ankimon_log("INFO", "AnkimonBattle", "Spawned current gym pokemon after resume")

                        # 4. Force complete UI refresh to show gym pokemon (not stale pre-resume state)
                        if test_window is not None:
                            from aqt.qt import QTimer
                            # Immediate refresh
                            _ankimon_force_refresh_enemy_display()
                            _ankimon_log("INFO", "AnkimonUI", "Immediate refresh after resume")

                            # Delayed refreshes to ensure display updates
                            QTimer.singleShot(100, _ankimon_force_refresh_enemy_display)
                            QTimer.singleShot(250, _ankimon_force_refresh_enemy_display)

                        # 5. Refresh all views
                        QTimer.singleShot(300, _ankimon_refresh_all_views)

                    try:
                        tooltipWithColour(f"Gym Battle vs {leader_name} - {remaining} Pokémon left", "#FFD700")
                    except:
                        pass
                except Exception as e:
                    _ankimon_log("ERROR", "AnkimonBattle", f"Failed to initialize resumed gym battle: {e}")
                    import traceback
                    traceback.print_exc()
                    try:
                        tooltipWithColour("Error resuming gym battle - please restart", "#FF0000")
                    except:
                        pass
            else:
                # User chose not to continue, reset gym state
                conf["ankimon_gym_active"] = False
                conf["ankimon_gym_pending"] = False
                conf["ankimon_gym_enemy_ids"] = []
                conf["ankimon_gym_enemy_index"] = 0
                conf["ankimon_gym_current_enemy_id"] = None
                conf["ankimon_gym_leader_key"] = None
                conf["ankimon_gym_leader_name"] = None
                mw.col.setMod()
                try:
                    tooltipWithColour("Gym battle cancelled", "#FF0000")
                except:
                    pass
    except Exception as e:
        # Silently fail if something goes wrong
        import traceback
        traceback.print_exc()

def _ankimon_scrub_hook(hook):
    try:
        internal = getattr(hook, "_hooks", None)
        if internal is None:
            return
        new_list = []
        for fn in list(internal):
            base_fn = getattr(fn, "func", fn)
            name = getattr(base_fn, "__name__", "")
            if name == "_ankimon_gym_on_answer":
                continue
            new_list.append(fn)
        hook._hooks[:] = new_list
    except Exception:
        pass

try:
    _ankimon_scrub_hook(gui_hooks.reviewer_did_answer_card)
    gui_hooks.reviewer_did_answer_card.append(_ankimon_gym_on_answer)
except Exception:
    pass

try:
    gui_hooks.reviewer_did_show_question.append(_ankimon_gym_on_question)
except Exception:
    pass

# Check for incomplete gym battles on startup
try:
    from aqt import gui_hooks
    def _delayed_gym_check():
        # Use QTimer to delay check until UI is fully loaded
        from aqt.qt import QTimer
        QTimer.singleShot(1000, _ankimon_check_incomplete_gym)
    gui_hooks.profile_did_open.append(_delayed_gym_check)
except Exception:
    pass

# ================= END GYM COUNTER OVERLAY (SAFE) =================
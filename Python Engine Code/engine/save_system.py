from datetime import datetime
from typing import Dict, Any
from .ui import UIEvent

class SaveSystemManager:
    
    def __init__(self):
        self.memory_saves = {}
    
    # Save game state to memory
    def handle_save_request(self, payload: Dict[str, Any], game_state) -> Dict[str, Any]:
        try:
            slot = payload.get("slot", 0)
            save_name = payload.get("name", f"Save {slot}")
            
            # Create save data with media state
            save_data = self._create_save_data(game_state, slot, save_name)
            
            # Save to memory
            self.memory_saves[slot] = save_data
            
            return {
                "type": "SAVE_SUCCESS",
                "payload": {
                    "slot": slot,
                    "name": save_name,
                    "message": f"✓ {save_name} saved successfully"
                }
            }
            
        except Exception as e:
            return {
                "type": "SAVE_ERROR",
                "payload": {
                    "message": f"Save failed: {str(e)}"
                }
            }
    
    # Load game state from memory
    def handle_load_request(self, payload: Dict[str, Any], game_state) -> Dict[str, Any]:
        try:
            slot = payload.get("slot", 0)
            
            # Get save from memory
            if slot not in self.memory_saves:
                return {
                    "type": "LOAD_ERROR",
                    "payload": {
                        "message": f"No save data in slot {slot}"
                    }
                }
            
            save_data = self.memory_saves[slot]
            save_name = save_data.get("save_name", f"Save {slot}")
            
            # Jump to save state
            self._jump_to_save_state(game_state, save_data)
            
            # Restore media state
            self._restore_media_state(game_state, save_data)
            
            return {
                "type": "LOAD_SUCCESS",
                "payload": {
                    "slot": slot,
                    "name": save_name,
                    "message": f"✓ {save_name} loaded successfully"
                }
            }
            
        except Exception as e:
            return {
                "type": "LOAD_ERROR",
                "payload": {
                    "message": f"Load failed: {str(e)}"
                }
            }
    
    # Create save data structure
    def _create_save_data(self, game_state, slot: int, save_name: str) -> Dict[str, Any]:
        # Save index-1 so load will re-execute current command
        save_index = max(0, game_state.index - 1)
        
        # Capture current media state
        media_state = self._capture_media_state(game_state)
        
        return {
            "save_time": datetime.now().isoformat(),
            "save_name": save_name,
            "slot": slot,
            "game_state": {
                "vars": game_state.vars.copy(),
                "current_scene": game_state.current_scene,
                "current_index": save_index,
                "call_stack": [stack.copy() for stack in game_state.call_stack],
                "labels": game_state.labels.copy()
            },
            "media_state": media_state,
            "metadata": {
                "engine_version": "1.4",
                "save_type": "jump_based_save_with_media",
                "original_index": game_state.index,
                "has_media_state": True
            }
        }
    
    # Capture current media state
    def _capture_media_state(self, game_state) -> Dict[str, Any]:
        media_state = {
            "images": {
            "current": getattr(game_state, 'current_image', None)
            },
            "audio": {
                "current_bgm": getattr(game_state, 'current_bgm', None),
                "bgm_loop": getattr(game_state, 'bgm_loop', True)
            }
        }
        
        # Filter out None values to reduce save size
        media_state["images"] = {k: v for k, v in media_state["images"].items() if v is not None}
        if not media_state["audio"]["current_bgm"]:
            media_state["audio"] = {}
        
        return media_state
    
    # Restore media state from save data
    def _restore_media_state(self, game_state, save_data: Dict[str, Any]):
        media_state = save_data.get("media_state", {})
        
        if not media_state:
            return
        
        # Restore images
        images = media_state.get("images", {})
        if images:
            self._restore_images(game_state, images)
        
        # Restore audio
        audio = media_state.get("audio", {})
        if audio:
            self._restore_audio(game_state, audio)
    
    def _restore_images(self, game_state, images: Dict[str, Any]):
        # Hide all images first
        game_state.ui.emit(UIEvent("HIDE_IMAGE", {}))
        
        # Restore background image if exists
        current_image = images.get("current")
        if current_image:
            game_state.ui.emit(UIEvent("SHOW_IMAGE", {
            "path": current_image
        }))
            game_state.current_image = current_image
    
    def _restore_audio(self, game_state, audio: Dict[str, Any]):
        # Stop current audio
        game_state.ui.emit(UIEvent("STOP_BGM", {}))
        game_state.ui.emit(UIEvent("STOP_VOICE", {}))
        
        # Restore background music
        current_bgm = audio.get("current_bgm")
        if current_bgm:
            game_state.ui.emit(UIEvent("PLAY_BGM", {
                "path": current_bgm,
                "loop": audio.get("bgm_loop", True)
            }))
            
            # Update game state tracking
            game_state.current_bgm = current_bgm
            game_state.bgm_loop = audio.get("bgm_loop", True)
    
    def _jump_to_save_state(self, game_state, save_data: Dict[str, Any]):
        saved_state = save_data.get("game_state", {})
        
        # Restore variables
        game_state.vars = saved_state.get("vars", {}).copy()
        
        # Restore call stack
        game_state.call_stack = [stack.copy() for stack in saved_state.get("call_stack", [])]
        
        # Check if scene switch is needed
        target_scene = saved_state.get("current_scene", "main")
        target_index = saved_state.get("current_index", 0)
        target_labels = saved_state.get("labels", {})
        
        if target_scene != game_state.current_scene:
            # Switch to target scene
            self._switch_to_scene(game_state, target_scene, target_index)
        else:
            # Jump within current scene
            game_state.index = target_index
            game_state.labels = target_labels
    
    def _switch_to_scene(self, game_state, target_scene: str, target_index: int):
        try:
            from parser import parse_script
            from commands import LabelCommand
            
            script_file = f"{target_scene}.txt"
            with open(script_file, "r", encoding="utf-8") as f:
                script_text = f.read()
            
            # Update scene state
            game_state.cmds = parse_script(script_text)
            game_state.current_scene = target_scene
            game_state.index = target_index
            game_state.labels = {cmd.name: i for i, cmd in enumerate(game_state.cmds) 
                               if isinstance(cmd, LabelCommand)}
            
        except Exception as e:
            raise Exception(f"Scene switch failed: {e}")
    
    def get_save_list(self) -> Dict[int, Dict[str, Any]]:
        save_list = {}
        for slot, save_data in self.memory_saves.items():
            save_list[slot] = {
                "slot": slot,
                "name": save_data.get("save_name", f"Save {slot}"),
                "time": save_data.get("save_time", ""),
                "scene": save_data.get("game_state", {}).get("current_scene", "unknown"),
                "has_media": save_data.get("metadata", {}).get("has_media_state", False)
            }
        return save_list
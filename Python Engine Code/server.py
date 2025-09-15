import asyncio
import json
import websockets
import threading
import queue
from typing import Any, Dict, List

from engine.ui import UiPort, UIEvent
from engine.core import run
from parser import parse_script

#Interrupt exception for breaking choice waits
class LoadInterruptException(Exception):
    pass

# WebSocket UI port for Godot client
class WsUiPort(UiPort):
    
    def __init__(self):
        self.send_queue = queue.Queue()
        self.recv_queue = queue.Queue()
        self.running = True
        self.game_state = None

    # Send event
    def emit(self, ev: UIEvent) -> None:
        self.send_queue.put({"type": ev.type, "payload": ev.payload})

    # "Wait for NEXT message
    def wait_next(self) -> None:
        self._wait_for_message_type("NEXT")

    # Wait for choice selection and load interrupt
    def wait_choice(self, valid_ids: List[str]) -> str:
        try:
            while True:
                data = self._wait_for_message_type("CHOICE_SELECTED")
                if data:
                    choice_id = data.get("payload", {}).get("id")
                    if choice_id in valid_ids:
                        return choice_id
        except LoadInterruptException:
            raise

    #   Wait for text input
    def wait_text_input(self, prompt: str) -> Any:
        data = self._wait_for_message_type("INPUT_REPLY")
        if data:
            input_value = data.get("payload", {}).get("value", "")
            
            # Try to convert to number
            try:
                if '.' not in str(input_value):
                    return int(input_value)
                else:
                    return float(input_value)
            except (ValueError, TypeError):
                return str(input_value)

    # Wait for specific message type and handling save/load inline
    def _wait_for_message_type(self, message_type: str) -> Dict[str, Any]:
        while self.running:
            try:
                data = self.recv_queue.get(timeout=0.1)
                received_type = data.get("type", "")
                
                if received_type == message_type:
                    return data
                elif received_type in ["SAVE_REQUEST", "LOAD_REQUEST"]:
                    # Handle save/load directly in main thread
                    self._handle_save_load_message_sync(data)
                    
                    # If load during choice wait, interrupt
                    if received_type == "LOAD_REQUEST" and message_type == "CHOICE_SELECTED":
                        raise LoadInterruptException("Choice wait interrupted by load")
                    
                    continue
                else:
                    continue
            except queue.Empty:
                continue
        return {}

    # Synchronously handle save/load messages
    def _handle_save_load_message_sync(self, data: Dict[str, Any]):
        msg_type = data.get("type")
        
        try:
            if not self.game_state:
                self.emit(UIEvent("SAVE_ERROR", {"message": "Game state unavailable"}))
                return
            
            from engine.handlers import handle_save_request, handle_load_request
            
            payload = data.get("payload", {})
            
            if msg_type == "SAVE_REQUEST":
                handle_save_request(payload, self.game_state)
            elif msg_type == "LOAD_REQUEST":
                handle_load_request(payload, self.game_state)
                
        except Exception as e:
            self.emit(UIEvent("SAVE_ERROR", {"message": f"Save/load error: {str(e)}"}))

    # Set current game state for save system
    def set_game_state(self, game_state):
        self.game_state = game_state

# WebSocket server 
async def serve(script_path: str, scene_name: str, host="127.0.0.1", port=8765):
    
    async def handle_client(websocket):
        # Create UI port
        ui_port = WsUiPort()
        
        # Start game engine thread
        def run_engine():
            try:
                with open(script_path, "r", encoding="utf-8") as f:
                    cmd_list = parse_script(f.read())
                
                from engine.core import run
                run(cmd_list, initial_scene=scene_name, ui=ui_port)
            except Exception as e:
                ui_port.emit(UIEvent("ERROR", {"message": str(e)}))
        
        engine_thread = threading.Thread(target=run_engine, daemon=True)
        engine_thread.start()
        
        # Send message
        async def sender():
            while True:
                try:
                    data = ui_port.send_queue.get_nowait()
                    message = json.dumps(data, ensure_ascii=False)
                    await websocket.send(message)
                except queue.Empty:
                    await asyncio.sleep(0.01)
                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception:
                    break

        # Receive messages
        async def receiver():
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        ui_port.recv_queue.put(data)
                    except json.JSONDecodeError:
                        pass
            except websockets.exceptions.ConnectionClosed:
                pass
        
        try:
            await asyncio.gather(sender(), receiver(), return_exceptions=True)
        finally:
            ui_port.running = False

    async with websockets.serve(handle_client, host, port, max_size=10*1024*1024):
        print(f"Server running on ws://{host}:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    import sys
    main_scene = sys.argv[1] if len(sys.argv) > 1 else "main.txt"
    scene_name = main_scene[:-4] if main_scene.endswith(".txt") else main_scene
    if not main_scene.endswith(".txt"):
        main_scene += ".txt"
    
    try:
        asyncio.run(serve(main_scene, scene_name))
    except KeyboardInterrupt:
        print("\nServer stopped")
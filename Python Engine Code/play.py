"""
Legacy CLI Launcher (currently deprecated)
This file was used during early development to run the game engine in command-line interface mode for quick testing and debugging. 
It has been replaced by the WebSocket server (server.py) + Godot frontend architecture.
"""
from parser import parse_script
from engine.core import run

def main():
    import sys
    
    # Parse command line arguments
    main_scene = "main.txt"
    scene_name = "main"
    
    if len(sys.argv) > 1:
        main_scene = sys.argv[1]
        if not main_scene.endswith('.txt'):
            scene_name = main_scene
            main_scene += '.txt'
        else:
            scene_name = main_scene[:-4]
    
    try:
        # Load and parse script
        with open(main_scene, "r", encoding="utf-8") as f:
            script_text = f.read()
        
        print(f"Starting game: {main_scene}")
        
        cmd_list = parse_script(script_text)
        run(cmd_list, scene_name)
        
    except FileNotFoundError:
        print(f"Error: Scene file '{main_scene}' not found")
        print("Usage: python play.py [scene_file]")
    except Exception as e:
        print(f"Error starting game: {e}")

if __name__ == "__main__":
    main()
from .state import GameState
from .handlers import (
    handle_say, handle_setvar, handle_jump, handle_label,
    handle_choose, handle_roll, handle_input, handle_scene, handle_return,
    handle_show_image, handle_hide_image, handle_play_bgm, 
    handle_stop_bgm, handle_play_sfx, handle_play_voice, handle_stop_voice
)
from .ui import UiPort, UIEvent
from typing import Optional
from commands import (
    SayCommand, SetVarCommand, LabelCommand, JumpCommand, ChooseCommand,
    RollCommand, InputCommand, SceneCommand, ReturnCommand,
    ShowImageCommand, HideImageCommand, PlayBGMCommand, StopBGMCommand,
    PlaySFXCommand, PlayVoiceCommand, StopVoiceCommand
)

# Command handler mapping
HANDLERS = {
    SayCommand:       handle_say,
    SetVarCommand:    handle_setvar,
    LabelCommand:     handle_label,
    JumpCommand:      handle_jump,
    ChooseCommand:    handle_choose,
    RollCommand:      handle_roll,
    InputCommand:     handle_input,
    SceneCommand:     handle_scene,
    ReturnCommand:    handle_return,
    ShowImageCommand: handle_show_image,
    HideImageCommand: handle_hide_image,
    PlayBGMCommand:   handle_play_bgm,
    StopBGMCommand:   handle_stop_bgm,
    PlaySFXCommand:   handle_play_sfx,
    PlayVoiceCommand: handle_play_voice,
    StopVoiceCommand: handle_stop_voice,
}

# Main game execution loop
def run(cmd_list, initial_scene="main", ui: Optional[UiPort] = None):
    if ui is None:
        raise RuntimeError("No UiPort provided. Use WebSocket server.")
    
    # Initialize game state
    st = GameState(cmds=cmd_list)
    st.current_scene = initial_scene
    st.labels = {cmd.name: i for i, cmd in enumerate(cmd_list) 
                 if isinstance(cmd, LabelCommand)}
    st.ui = ui
    
    _init_media_state(st)
    
    # Setup save system integration
    if hasattr(ui, 'set_game_state'):
        ui.set_game_state(st)
    
    st.ui.emit(UIEvent("INIT", {"title": initial_scene}))

    # Main execution loop
    while st.index < len(st.cmds):
        cmd = st.cmds[st.index]
        st.index += 1

        handler = HANDLERS.get(type(cmd))
        if handler:
            try:
                handler(cmd, st)
            except Exception as e:
                st.ui.emit(UIEvent("INFO", {"text": f"Error: {e}"}))
        
        # Auto-return from scene calls when finished
        if st.index >= len(st.cmds) and st.call_stack:
            _return_to_caller(st)

    st.ui.emit(UIEvent("END", {"text": "Game finished!"}))

# Return from scene call stack   
def _return_to_caller(st: GameState):
    
    if not st.call_stack:
        return
    
    caller_state = st.call_stack.pop()
    st.cmds = caller_state['cmds']
    st.index = caller_state['index']
    st.labels = caller_state['labels']
    st.current_scene = caller_state.get('scene_name', st.current_scene)
    st.ui.emit(UIEvent("INFO", {"text": "[Scene returned]"}))

# Initialize media state tracking attributes
def _init_media_state(st: GameState):
    st.current_image = None  
    st.current_bgm = None        
    st.bgm_loop = True           
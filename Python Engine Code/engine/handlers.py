import ast
import operator as op
import re
import random
from typing import Any, Dict, List
from commands import (
    ChooseCommand, Option, SetVarCommand, LabelCommand,
    SayCommand, JumpCommand, RollCommand, InputCommand,
    SceneCommand, ReturnCommand,
    ShowImageCommand, HideImageCommand, PlayBGMCommand, 
    StopBGMCommand, PlaySFXCommand, PlayVoiceCommand, StopVoiceCommand
)
from .state import GameState
from .ui import UIEvent
from .save_system import SaveSystemManager 

# Safe expression evaluation system
_BIN_OPERATORS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.Mod: op.mod, ast.Pow: op.pow
}

_CMP_OPERATORS = {
    ast.Gt: op.gt, ast.GtE: op.ge, ast.Lt: op.lt,
    ast.LtE: op.le, ast.Eq: op.eq, ast.NotEq: op.ne
}

_DICE_PATTERN = re.compile(r'(\d*)d(\d+)')

# Safe evaluation function for expressions
# Supports basic math, comparisons, and variable references
def safe_eval(expr: str, vars_dict: Dict[str, Any]) -> Any:
    if expr is None:
        return None
    
    # Clean expression
    expr = str(expr).replace("{", "").replace("}", "").strip()
    
    try:
        node = ast.parse(expr, mode="eval").body
        return _eval_node(node, vars_dict)
    except Exception:
        return 0

# Recursive evaluation of AST nodes
# Handle numbers, variable references, binary operations, comparisons, and boolean operations
def _eval_node(node, vars_dict: Dict[str, Any]) -> Any:
    if isinstance(node, (ast.Constant, ast.Constant)):
        return node.n if hasattr(node, "n") else node.value
    
    elif isinstance(node, ast.Name):
        return vars_dict.get(node.id, 0)
    
    elif isinstance(node, ast.BinOp):
        if type(node.op) in _BIN_OPERATORS:
            left = _eval_node(node.left, vars_dict)
            right = _eval_node(node.right, vars_dict)
            return _BIN_OPERATORS[type(node.op)](left, right)
    
    elif isinstance(node, ast.Compare):
        left = _eval_node(node.left, vars_dict)
        right = _eval_node(node.comparators[0], vars_dict)
        if type(node.ops[0]) in _CMP_OPERATORS:
            return _CMP_OPERATORS[type(node.ops[0])](left, right)
    
    elif isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_eval_node(v, vars_dict) for v in node.values)
        elif isinstance(node.op, ast.Or):
            return any(_eval_node(v, vars_dict) for v in node.values)
    
    raise ValueError(f"Unsupported expression node type: {type(node)}")

# Roll dice expression handler
def _roll_dice(match: re.Match) -> str:
    count = int(match.group(1) or 1)
    sides = int(match.group(2))
    total = sum(random.randint(1, sides) for _ in range(count))
    return str(total)

# Basic command handlers
# Handle Say, SetVar, Input, Label, Jump, Choose, Roll, Scene, Return commands
def handle_say(cmd: SayCommand, st: GameState):
    # Replace variable references in text
    text = re.sub(r"\{(\w+)\}", lambda m: str(st.vars.get(m.group(1), f"{{{m.group(1)}}}")), cmd.text)
    
    st.ui.emit(UIEvent("SHOW_TEXT", {
        "text": text, 
        "speaker": cmd.speaker
    }))
    st.ui.wait_next()

def handle_setvar(cmd: SetVarCommand, st: GameState):
    value = safe_eval(cmd.value, st.vars)
    st.vars[cmd.name] = value

def handle_input(cmd: InputCommand, st: GameState):
    prompt = cmd.prompt or f"Enter {cmd.var_name}: "
    
    st.ui.emit(UIEvent("INPUT_REQUEST", {
        "prompt": prompt, 
        "var": cmd.var_name
    }))
    
    value = st.ui.wait_text_input(prompt)
    st.vars[cmd.var_name] = value

def handle_label(cmd: LabelCommand, st: GameState):
    st.ui.emit(UIEvent("INFO", {"text": f"[Label: {cmd.name}]"}))

def handle_jump(cmd: JumpCommand, st: GameState):
    if cmd.target in st.labels:
        st.index = st.labels[cmd.target]
    else:
        st.ui.emit(UIEvent("INFO", {"text": f"Error: Label {cmd.target} not found"}))

def handle_choose(cmd: ChooseCommand, st: GameState):
    # Check global conditions
    if cmd.global_when and not safe_eval(cmd.global_when, st.vars):
        return
    
    if cmd.global_enable and not safe_eval(cmd.global_enable, st.vars):
        return

    # Filter valid options
    candidates: List[Option] = []
    for opt in cmd.options:
        if opt.when and not safe_eval(opt.when, st.vars):
            continue
        candidates.append(opt)
    
    if not candidates:
        st.ui.emit(UIEvent("INFO", {"text": "[No available choices]"}))
        st.ui.wait_next()
        return

    # Build choice list
    items = []
    valid_ids = []
    for opt in candidates:
        enabled = True
        if opt.enable and not safe_eval(opt.enable, st.vars):
            enabled = False
        
        items.append({
            "id": opt.target, 
            "text": opt.text, 
            "enabled": enabled
        })
        valid_ids.append(opt.target)

    st.ui.emit(UIEvent("CHOICES", {"items": items}))
    
    # Wait for user choice
    while True:
        chosen = st.ui.wait_choice(valid_ids)
        chosen_opt = next((o for o in candidates if o.target == chosen), None)
        
        if chosen_opt and (not chosen_opt.enable or safe_eval(chosen_opt.enable, st.vars)):
            st.index = st.labels[chosen]
            return
        else:
            st.ui.emit(UIEvent("INFO", {"text": "That option is currently unavailable"}))

def handle_roll(cmd: RollCommand, st: GameState):
    # Process dice expressions
    expr_with_dice = _DICE_PATTERN.sub(_roll_dice, cmd.expr)
    
    # Calculate final result
    result = safe_eval(expr_with_dice, st.vars)
    
    # Save result to variable
    target_var = cmd.to or "rollResult"
    st.vars[target_var] = result
    
    st.ui.emit(UIEvent("ROLL_RESULT", {
        "expr": cmd.expr, 
        "to": target_var, 
        "value": result
    }))

def handle_scene(cmd: SceneCommand, st: GameState):
    from parser import parse_script
    from commands import LabelCommand
    
    script_file = f"{cmd.name}.txt"
    
    try:
        with open(script_file, "r", encoding="utf-8") as f:
            script_text = f.read()
        
        new_cmds = parse_script(script_text)
        
        if cmd.mode == "call":
            # Call scene: save current state to call stack
            st.call_stack.append({
                'cmds': st.cmds,
                'index': st.index,
                'labels': st.labels,
                'scene_name': st.current_scene,
            })
            st.ui.emit(UIEvent("INFO", {"text": f"[Calling scene: {cmd.name}]"}))
        else:
            # Change scene: direct replacement
            st.ui.emit(UIEvent("INFO", {"text": f"[Changed to scene: {cmd.name}]"}))

        # Update scene state
        st.cmds = new_cmds
        st.index = 0
        st.current_scene = cmd.name
        st.labels = {c.name: i for i, c in enumerate(new_cmds) if isinstance(c, LabelCommand)}
        
        # Initialize media state for new scene
        _init_media_state(st)
        
        st.ui.emit(UIEvent("SCENE_CHANGED", {"name": cmd.name, "mode": cmd.mode}))
        
    except FileNotFoundError:
        error_msg = f"Error: Scene file '{script_file}' not found"
        st.ui.emit(UIEvent("INFO", {"text": error_msg}))
    except Exception as e:
        error_msg = f"Error loading scene '{cmd.name}': {e}"
        st.ui.emit(UIEvent("INFO", {"text": error_msg}))

def handle_return(cmd: ReturnCommand, st: GameState):
    if not st.call_stack:
        st.ui.emit(UIEvent("INFO", {"text": "Warning: No scene to return to"}))
        return
    
    # Restore state from call stack
    caller_state = st.call_stack.pop()
    st.cmds = caller_state['cmds']
    st.index = caller_state['index']
    st.labels = caller_state['labels']
    st.current_scene = caller_state.get('scene_name', st.current_scene)
    
    st.ui.emit(UIEvent("INFO", {"text": "[Returned to previous scene]"}))

# Media command handlers
# Handle image display, background music, sound effects, and voice commands
def handle_show_image(cmd: ShowImageCommand, st: GameState):
    st.ui.emit(UIEvent("SHOW_IMAGE", {
        "path": cmd.path,
    }))
    
    # Track image state
    st.current_image = cmd.path

def handle_hide_image(cmd: HideImageCommand, st: GameState):
    st.ui.emit(UIEvent("HIDE_IMAGE", {}))
    
    # Clear state tracking
    st.current_image = None

def handle_play_bgm(cmd: PlayBGMCommand, st: GameState):
    if hasattr(st, 'current_bgm') and st.current_bgm is not None:
        st.ui.emit(UIEvent("STOP_BGM", {}))
    
    st.ui.emit(UIEvent("PLAY_BGM", {
        "path": cmd.path,
        "loop": cmd.loop
    }))
    
    # Track BGM state
    st.current_bgm = cmd.path
    st.bgm_loop = cmd.loop

def handle_stop_bgm(cmd: StopBGMCommand, st: GameState):
    st.ui.emit(UIEvent("STOP_BGM", {}))
    st.current_bgm = None

def handle_play_sfx(cmd: PlaySFXCommand, st: GameState):
    st.ui.emit(UIEvent("PLAY_SFX", {"path": cmd.path}))

def handle_play_voice(cmd: PlayVoiceCommand, st: GameState):
    st.ui.emit(UIEvent("PLAY_VOICE", {"path": cmd.path}))

def handle_stop_voice(cmd: StopVoiceCommand, st: GameState):
    st.ui.emit(UIEvent("STOP_VOICE", {}))

# Initialize media state for game state
def _init_media_state(st: GameState):
    if not hasattr(st, 'current_image'):
        st.current_image = None
    if not hasattr(st, 'current_bgm'):
        st.current_bgm = None
    if not hasattr(st, 'bgm_loop'):
        st.bgm_loop = True

# Save system handlers
_save_manager = SaveSystemManager()

def handle_save_request(payload: Dict[str, Any], st: GameState):
    _init_media_state(st)
    result = _save_manager.handle_save_request(payload, st)
    st.ui.emit(UIEvent(result["type"], result["payload"]))

def handle_load_request(payload: Dict[str, Any], st: GameState):
    _init_media_state(st)
    result = _save_manager.handle_load_request(payload, st)
    st.ui.emit(UIEvent(result["type"], result["payload"]))
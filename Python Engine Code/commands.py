from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class Option:
    text: str
    target: str
    when: Optional[str] = None
    enable: Optional[str] = None

# Basic narrative commands
@dataclass
class SayCommand:
    text: str
    speaker: str = None
    voice: str = None

@dataclass
class SetVarCommand:
    name: str
    value: Any
    global_var: bool = False

@dataclass
class InputCommand:
    var_name: str
    prompt: str = ""

@dataclass
class RollCommand:
    expr: str
    to: str = None

@dataclass
class ChooseCommand:
    options: List[Option]
    global_when: Optional[str] = None
    global_enable: Optional[str] = None

# Flow control commands
@dataclass
class LabelCommand:
    name: str

@dataclass
class JumpCommand:
    target: str

@dataclass
class SceneCommand:
    name: str
    mode: str  

@dataclass
class ReturnCommand:
    pass

# Media commands
@dataclass
class ShowImageCommand:
    path: str

@dataclass
class HideImageCommand:
    pass

@dataclass
class PlayBGMCommand:
    path: str
    loop: bool = True

@dataclass
class StopBGMCommand:
    pass

@dataclass
class PlaySFXCommand:
    path: str

@dataclass
class PlayVoiceCommand:
    path: str

@dataclass
class StopVoiceCommand:
    pass
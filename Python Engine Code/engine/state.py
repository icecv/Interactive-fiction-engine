from dataclasses import dataclass, field
from typing import Any, List, Dict

# Main game state container
@dataclass
class GameState:
    # Command execution
    cmds: List[Any] = field(default_factory=list)
    index: int = 0

    # Game variables and labels
    vars: Dict[str, Any] = field(default_factory=dict)
    labels: Dict[str, int] = field(default_factory=dict)

    # Scene management
    current_scene: str = "main"
    call_stack: List[Dict[str, Any]] = field(default_factory=list)

    # UI interface
    ui: Any = None

    # Initialize collections
    def __post_init__(self):
        if self.vars is None:
            self.vars = {}
        if self.labels is None:
            self.labels = {}
        if self.call_stack is None:
            self.call_stack = []
from dataclasses import dataclass
from typing import Any, Dict, List

# UI event container
@dataclass
class UIEvent:
    type: str
    payload: Dict[str, Any]

# Abstract UI port interface
class UiPort:
    
    # Send event to UI client
    def emit(self, ev: UIEvent) -> None:
        raise NotImplementedError

    # Wait for continue signal
    def wait_next(self) -> None:
        raise NotImplementedError

    # Wait for user choice selection 
    def wait_choice(self, valid_ids: List[str]) -> str:
        raise NotImplementedError

    # Wait for text input from user
    def wait_text_input(self, prompt: str) -> Any:
        raise NotImplementedError
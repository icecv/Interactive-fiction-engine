from lark import Lark, Transformer, Token
from commands import (
    SayCommand, SetVarCommand, RollCommand, ChooseCommand, 
    Option, LabelCommand, JumpCommand, InputCommand, SceneCommand, ReturnCommand,
    ShowImageCommand, HideImageCommand, PlayBGMCommand, StopBGMCommand, 
    PlaySFXCommand, PlayVoiceCommand, StopVoiceCommand
)

# Load DSL grammar
_parser = Lark.open('grammar.lark', parser='lalr', propagate_positions=True)

# Transform AST to Command objects
class DSLTransformer(Transformer):
    
    def value(self, items):
        return items[0]
    
    def statement(self, items):
        return items[0]

    def STRING(self, tok: Token):
        return tok.value.strip('"')

    def IDENT(self, tok: Token):
        return tok.value

    def INT(self, tok: Token):
        return int(tok.value)

    def BOOLEAN(self, tok: Token):
        return tok.value.lower() == "true"

    # Basic commands
    def say_stmt(self, items):
        text = items[0]
        params = {k: v for k, v in items[1:] if isinstance((k, v), tuple)}
        return SayCommand(text=text, speaker=params.get("speaker"))

    def setvar_stmt(self, items):
        name, expr = items
        return SetVarCommand(name=name, value=expr)
    
    def input_stmt(self, items):
        var_name = items[0]
        params = {k: v for k, v in items[1:] if isinstance((k, v), tuple)}
        return InputCommand(var_name=var_name, prompt=params.get("prompt", ""))

    def roll_stmt(self, items):
        expr = items[0]
        to_var = items[1] if len(items) > 1 else None
        return RollCommand(expr=expr, to=to_var)

    def label_stmt(self, items):
        return LabelCommand(name=items[0])

    def jump_stmt(self, items):
        return JumpCommand(target=items[0])

    # Choice handling
    def option(self, items):
        text, target = items[:2]
        params = {k: v for k, v in items[2:] if isinstance((k, v), tuple)}
        return Option(
            text=text, 
            target=target,
            when=params.get("when"), 
            enable=params.get("enable")
        )
    
    def choose_stmt(self, items):
        options = []
        global_params = {}
        
        for item in items:
            if isinstance(item, Option):
                options.append(item)
            elif isinstance(item, tuple):
                key, val = item
                if key in ["when", "enable"]:
                    global_params[key] = val

        return ChooseCommand(
            options=options,
            global_when=global_params.get("when"),
            global_enable=global_params.get("enable")
        )

    # Scene commands
    def changescene_stmt(self, items):
        return SceneCommand(name=items[0], mode="change")
    
    def callscene_stmt(self, items):
        return SceneCommand(name=items[0], mode="call")

    def return_stmt(self, items):
        return ReturnCommand()

    # Media commands
    def showimage_stmt(self, items):
        path = items[0]
        return ShowImageCommand(path=path)

    def hideimage_stmt(self, items):
        return HideImageCommand()

    def playbgm_stmt(self, items):
        path = items[0]
        params = {k: v for k, v in items[1:] if isinstance((k, v), tuple)}
        return PlayBGMCommand(
            path=path,
            loop=params.get("loop", True)
        )

    def stopbgm_stmt(self, items):
        return StopBGMCommand()

    def playsfx_stmt(self, items):
        path = items[0]
        return PlaySFXCommand(path=path)

    def playvoice_stmt(self, items):
        path = items[0]
        return PlayVoiceCommand(path=path)

    def stopvoice_stmt(self, items):
        return StopVoiceCommand()

    # Parameter handling
    def param(self, items):
        key = items[0]
        if len(items) == 2:
            value_str = str(items[1]).strip()
            
            # Type conversion
            if value_str.lower() == "true":
                value = True
            elif value_str.lower() == "false":
                value = False
            else:
                try:
                    value = float(value_str) if '.' in value_str else int(value_str)
                except ValueError:
                    value = value_str
            
            return (key, value)
        else:
            return (key, True)

    start = list

# Parse script text and return list of command objects
def parse_script(script_text: str):
    try:
        tree = _parser.parse(script_text)
        commands = DSLTransformer().transform(tree)
        return commands
    except Exception as e:
        print(f"Parse error: {e}")
        import traceback
        traceback.print_exc()
        return []
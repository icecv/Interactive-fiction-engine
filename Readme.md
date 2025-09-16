Game Creation Process

1. Writing the Script: Modify main.txt to create the main scene file.
2. Adding Resources: Place images and audio files in the corresponding directories under assets/.
3. Multiple Scenes: Create additional .txt files and switch between them using the scene command.
4. Running: Launch FictionGame.exe to play.

This engine has built-in sample story scripts

Script Syntax

Basic Commands
# Dialogue
say "Hello, world!"
say "Welcome to the game!"
speaker="Narration"

# Variable Operations
setvar health 100
setvar playerName "Player"
setvar score {health + 10}

# User Input
input playerName prompt="Please enter your name:"

# Branch Selection
choose
"Go north" -> northPath when="{hasKey}"
"Go south" -> southPath
"Rest" -> rest enable="{health > 50}"

# Jumps and Labels
label startGame
jump startGame

# Scene Management
scene "forest" # Switch scenes
call "inventory" # Call a scene
return # Return

# Dice System
roll "1d20+{strength}" to attackRoll
Multimedia Commands
# Image
showimage "backgrounds/forest.jpg"
hideimage

# Audio
playbgm "music/theme.ogg" loop=true
playsfx "sounds/door.wav"
playvoice "voice/line1.ogg"
stopbgm
stopvoice
Conditional expressions
Supports mathematical operations and comparisons:
{health + 10} # Arithmetic
{level >= 5 and hasWeapon} # Logical
{playerName} # Variable reference
Using variables in text:
say "You have {health} points."
say "Welcome, {playerName}!"
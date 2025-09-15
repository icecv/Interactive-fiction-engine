# GameManager.gd - Minimally Simplified Production Version
extends Node

# WebSocket connection
var socket: WebSocketPeer
var is_connected = false
var engine_process: int = -1

# External paths
var exe_dir: String
var main_script_path: String
var engine_path: String
var assets_path: String

# UI references
var text_label: RichTextLabel
var choice_container: VBoxContainer  
var input_container: HBoxContainer
var input_field: LineEdit
var input_button: Button
var next_button: Button
var save_button: Button
var save_menu: Control
var waiting_for_input: bool = false

# Save data management
var save_data = {}

func _ready():
	_setup_external_paths()
	_get_ui_nodes()
	_fix_mouse_filters()
	_connect_signals()
	_setup_save_menu()
	
	await _start_python_engine()
	await _init_websocket()

func _setup_external_paths():
	exe_dir = OS.get_executable_path().get_base_dir()
	main_script_path = exe_dir.path_join("main.txt")
	assets_path = exe_dir.path_join("assets")
	engine_path = exe_dir.path_join("GameEngine.exe")

func _get_ui_nodes():
	var main_node = get_parent()
	var ui_node = main_node.get_node("UI")
	var game_ui = ui_node.get_node("GameUI")
	
	text_label = game_ui.get_node("TextDisplay")
	choice_container = game_ui.get_node("ChoiceContainer")
	input_container = game_ui.get_node("InputContainer")
	next_button = game_ui.get_node("NextButton")
	input_field = input_container.get_node("InputField")
	input_button = input_container.get_node("SubmitButton")
	save_button = ui_node.get_node("GlobalControls/SaveButton")
	save_menu = ui_node.get_node("SaveMenu")

func _fix_mouse_filters():
	var ui_node = get_parent().get_node("UI")
	
	# Background layers ignore mouse
	ui_node.get_node("BackgroundLayer").mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui_node.get_node("BackgroundLayer/BackgroundImage").mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui_node.get_node("CharacterLayer").mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui_node.get_node("GlobalControls").mouse_filter = Control.MOUSE_FILTER_IGNORE
	
	# Interactive elements receive mouse
	ui_node.get_node("GameUI").mouse_filter = Control.MOUSE_FILTER_PASS
	next_button.mouse_filter = Control.MOUSE_FILTER_PASS
	input_button.mouse_filter = Control.MOUSE_FILTER_PASS
	save_button.mouse_filter = Control.MOUSE_FILTER_PASS
	choice_container.mouse_filter = Control.MOUSE_FILTER_PASS
	
	# Text display ignores mouse
	text_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	
	# Save menu initially ignores mouse
	save_menu.mouse_filter = Control.MOUSE_FILTER_IGNORE
	save_menu.get_node("SaveMenuBG").mouse_filter = Control.MOUSE_FILTER_IGNORE

func _connect_signals():
	next_button.pressed.connect(_on_next_pressed)
	save_button.pressed.connect(_on_save_pressed)
	input_button.pressed.connect(_on_input_submitted)
	input_field.text_submitted.connect(_on_input_submitted)  # Unified input handler

func _setup_save_menu():
	var save_confirm = save_menu.get_node("SavePanel/SavePanelContent/SaveTabs/Save Game/SaveSlotContainer/SaveConfirmButton")
	var load_confirm = save_menu.get_node("SavePanel/SavePanelContent/SaveTabs/Load Game/LoadSlotContainer/LoadButtonContainer/LoadConfirmButton")
	var quick_save = save_menu.get_node("SavePanel/SavePanelContent/SaveMenuButtons/QuickSaveButton")
	var quick_load = save_menu.get_node("SavePanel/SavePanelContent/SaveMenuButtons/QuickLoadButton")
	var return_game = save_menu.get_node("SavePanel/SavePanelContent/SaveMenuButtons/ReturnToGameButton")
	
	save_confirm.pressed.connect(_on_save_confirm)
	load_confirm.pressed.connect(_on_load_confirm)
	quick_save.pressed.connect(_on_quick_save)
	quick_load.pressed.connect(_on_quick_load)
	return_game.pressed.connect(_on_return_game)
	
	_initialize_save_lists()

func _start_python_engine():
	text_label.text = "Starting game engine..."
	
	if not FileAccess.file_exists(engine_path):
		text_label.text = "Error: GameEngine.exe not found"
		return
	
	if not FileAccess.file_exists(main_script_path):
		text_label.text = "Error: main.txt not found"
		return
	
	await _start_with_batch()

func _start_with_batch():
	var batch_path = exe_dir.path_join("start.bat")
	var batch_file = FileAccess.open(batch_path, FileAccess.WRITE)
	
	if not batch_file:
		text_label.text = "Failed to create startup script"
		return
	
	batch_file.store_string("@echo off\ncd /d \"" + exe_dir + "\"\n\"GameEngine.exe\" \"main.txt\"\n")
	batch_file.close()
	
	engine_process = OS.create_process(batch_path, [])
	
	if engine_process > 0:
		text_label.text = "Engine starting..."
		await _wait_for_engine_ready()
	else:
		text_label.text = "Failed to start engine"

func _wait_for_engine_ready():
	for i in range(5):
		await get_tree().create_timer(1.0).timeout
		text_label.text = "Engine initializing..."
		
		var test_socket = WebSocketPeer.new()
		test_socket.connect_to_url("ws://localhost:8765")
		await get_tree().create_timer(0.3).timeout
		
		if test_socket.get_ready_state() == WebSocketPeer.STATE_OPEN:
			test_socket.close()
			return
		
		test_socket.close()

func _init_websocket():
	socket = WebSocketPeer.new()
	text_label.text = "Connecting to game server..."
	
	socket.connect_to_url("ws://localhost:8765")
	
	# Simplified connection without showing attempt count
	while true:
		await get_tree().create_timer(0.5).timeout
		
		var state = socket.get_ready_state()
		
		if state == WebSocketPeer.STATE_OPEN:
			is_connected = true
			text_label.text = "Connected! Game ready."
			return
		elif state == WebSocketPeer.STATE_CLOSED:
			break
	
	text_label.text = "Connection failed. Try manual start:\n1. Open cmd in game folder\n2. Run: GameEngine.exe main.txt\n3. Restart this game"

func _initialize_save_lists():
	var save_list = save_menu.get_node("SavePanel/SavePanelContent/SaveTabs/Save Game/SaveSlotContainer/SaveSlotList")
	var load_list = save_menu.get_node("SavePanel/SavePanelContent/SaveTabs/Load Game/LoadSlotContainer/LoadSlotList")
	
	save_list.clear()
	load_list.clear()
	
	for i in range(10):
		var slot_text = "Slot " + str(i + 1)
		
		if i in save_data:
			var save_info = save_data[i]
			var save_name = save_info.get("name", "Unnamed Save")
			var save_time = save_info.get("time", "")
			slot_text += " - " + save_name
			if save_time:
				slot_text += " (" + _format_time(save_time) + ")"
		else:
			slot_text += " (Empty)"
		
		save_list.add_item(slot_text)
		load_list.add_item(slot_text)

func _format_time(iso_time: String) -> String:
	if iso_time.is_empty():
		return ""
	
	var parts = iso_time.split("T")
	if parts.size() >= 2:
		var date = parts[0]
		var time = parts[1].split(".")[0]
		return date + " " + time
	return iso_time

func _process(_delta):
	if socket == null:
		return
	
	socket.poll()
	var state = socket.get_ready_state()
	
	if state == WebSocketPeer.STATE_OPEN:
		if not is_connected:
			is_connected = true
			text_label.text = "Connected! Game starting..."
		
		while socket.get_available_packet_count():
			var packet = socket.get_packet()
			var message = packet.get_string_from_utf8()
			_handle_message(message)
	
	elif state == WebSocketPeer.STATE_CLOSED:
		if is_connected:
			is_connected = false
			text_label.text = "Connection to server lost"

func _send_message(data: Dictionary):
	if socket != null and is_connected:
		socket.send_text(JSON.stringify(data))

func _handle_message(message: String):
	var json = JSON.new()
	json.parse(message)
	var data = json.data
	var msg_type = data.get("type", "")
	var payload = data.get("payload", {})
	
	match msg_type:
		"SHOW_TEXT":
			_show_text(payload)
		"CHOICES":
			_show_choices(payload)
		"INPUT_REQUEST":
			_show_input(payload)
		"ROLL_RESULT":
			_show_roll_result(payload)
		"INFO":
			_show_info(payload)
		"SAVE_SUCCESS":
			_handle_save_success(payload)
		"LOAD_SUCCESS":
			_handle_load_success(payload)
		"SAVE_ERROR", "LOAD_ERROR":
			_handle_save_error(payload)
		"SHOW_IMAGE":
			_handle_show_image(payload)
		"HIDE_IMAGE":
			_handle_hide_image(payload)
		"PLAY_BGM":
			_handle_play_bgm(payload)
		"STOP_BGM":
			_handle_stop_bgm(payload)
		"PLAY_SFX":
			_handle_play_sfx(payload)
		"PLAY_VOICE":
			_handle_play_voice(payload)
		"STOP_VOICE":
			_handle_stop_voice(payload)

func _show_text(payload: Dictionary):
	var text = payload.get("text", "")
	var speaker = payload.get("speaker", "")
	
	var display_text = ""
	if speaker:
		display_text = "[b]" + speaker + ":[/b] " + text
	else:
		display_text = text
	
	text_label.text = display_text
	
	_reset_ui()
	next_button.visible = true

func _show_choices(payload: Dictionary):
	var items = payload.get("items", [])
	_reset_ui()
	_clear_choices()
	
	for i in range(items.size()):
		var item = items[i]
		var button = Button.new()
		button.text = str(i + 1) + ". " + item.get("text", "")
		button.disabled = not item.get("enabled", true)
		button.mouse_filter = Control.MOUSE_FILTER_PASS
		button.custom_minimum_size = Vector2(400, 50)
		
		var choice_id = item.get("id", "")
		button.pressed.connect(_on_choice_selected.bind(choice_id))
		choice_container.add_child(button)
	
	choice_container.visible = true

func _show_input(payload: Dictionary):
	var prompt = payload.get("prompt", "Please enter:")
	text_label.text = prompt
	input_field.text = ""
	_reset_ui()
	input_container.visible = true
	input_field.grab_focus()
	waiting_for_input = true

func _show_roll_result(payload: Dictionary):
	var expr = payload.get("expr", "")
	var value = payload.get("value", 0)
	text_label.text = "🎲 " + expr + " = " + str(value)
	_reset_ui()
	next_button.visible = true

func _show_info(payload: Dictionary):
	var info_text = payload.get("text", "")
	text_label.text = "[color=gray]" + info_text + "[/color]"
	_reset_ui()
	next_button.visible = true

func _reset_ui():
	next_button.visible = false
	choice_container.visible = false
	input_container.visible = false
	waiting_for_input = false

func _clear_choices():
	for child in choice_container.get_children():
		child.queue_free()

func _handle_show_image(payload: Dictionary):
	var path = payload.get("path", "")
	var ui_node = get_parent().get_node("UI")
	var image_node = ui_node.get_node("BackgroundLayer/BackgroundImage")
	
	if image_node:
		var texture = _load_external_resource(path, "image")
		if texture:
			image_node.texture = texture
			image_node.modulate = Color(1, 1, 1, 1)
			image_node.visible = true
			image_node.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED

func _handle_hide_image(payload: Dictionary):
	var ui_node = get_parent().get_node("UI")
	var image_node = ui_node.get_node("BackgroundLayer/BackgroundImage")
	
	if image_node:
		image_node.visible = false

func _handle_play_bgm(payload: Dictionary):
	var path = payload.get("path", "")
	var loop = payload.get("loop", true)
	
	var bgm_player = get_parent().get_node("AudioManager/BGMPlayer")
	if not bgm_player:
		return
	
	if bgm_player.playing:
		bgm_player.stop()
	
	var audio_stream = _load_external_resource(path, "audio")
	if not audio_stream:
		return
	
	bgm_player.stream = audio_stream
	if audio_stream.has_method("set_loop"):
		audio_stream.set_loop(loop)
	elif "loop" in audio_stream:
		audio_stream.loop = loop
	
	bgm_player.play()

func _handle_stop_bgm(payload: Dictionary):
	var bgm_player = get_parent().get_node("AudioManager/BGMPlayer")
	if bgm_player and bgm_player.playing:
		bgm_player.stop()

func _handle_play_sfx(payload: Dictionary):
	var path = payload.get("path", "")
	
	var sfx_player = get_parent().get_node("AudioManager/SFXPlayer")
	if sfx_player:
		var audio_stream = _load_external_resource(path, "audio")
		if audio_stream:
			sfx_player.stream = audio_stream
			sfx_player.play()

func _handle_play_voice(payload: Dictionary):
	var path = payload.get("path", "")
	
	var voice_player = get_parent().get_node("AudioManager/VoicePlayer")
	if voice_player:
		var audio_stream = _load_external_resource(path, "audio")
		if audio_stream:
			voice_player.stream = audio_stream
			voice_player.play()

func _handle_stop_voice(payload: Dictionary):
	var voice_player = get_parent().get_node("AudioManager/VoicePlayer")
	if voice_player and voice_player.playing:
		voice_player.stop()

# Unified resource loading function
func _load_external_resource(script_path: String, resource_type: String):
	var paths = _get_resource_paths(script_path, resource_type)
	
	for path in paths:
		if FileAccess.file_exists(path):
			if resource_type == "image":
				return _load_image_from_path(path)
			elif resource_type == "audio":
				return _load_audio_from_path(path)
	
	return null

func _get_resource_paths(script_path: String, resource_type: String) -> Array:
	var paths = []
	var subfolder = "images" if resource_type == "image" else "audio"
	
	paths.append(assets_path.path_join(script_path))
	paths.append(assets_path.path_join(subfolder).path_join(script_path.get_file()))
	
	# Handle "image/" prefix correction for images
	if resource_type == "image" and script_path.begins_with("image/"):
		var corrected = script_path.replace("image/", "images/")
		paths.append(assets_path.path_join(corrected))
	
	return paths

func _load_image_from_path(path: String) -> Texture2D:
	var image = Image.new()
	var error = image.load(path)
	if error == OK:
		var texture = ImageTexture.new()
		texture.set_image(image)
		return texture
	return null

func _load_audio_from_path(path: String) -> AudioStream:
	var extension = path.get_extension().to_lower()
	var file = FileAccess.open(path, FileAccess.READ)
	if not file:
		return null
	
	var bytes = file.get_buffer(file.get_length())
	file.close()
	
	var audio_stream: AudioStream = null
	
	match extension:
		"ogg":
			audio_stream = AudioStreamOggVorbis.new()
			audio_stream.packet_sequence = OggPacketSequence.new()
			audio_stream.packet_sequence.packet_data = bytes
		"wav":
			audio_stream = AudioStreamWAV.new()
			audio_stream.data = bytes
		"mp3":
			audio_stream = AudioStreamMP3.new()
			audio_stream.data = bytes
	
	return audio_stream

# Signal handlers
func _on_next_pressed():
	_send_message({"type": "NEXT"})

func _on_choice_selected(choice_id: String):
	_send_message({"type": "CHOICE_SELECTED", "payload": {"id": choice_id}})

func _on_input_submitted():
	if waiting_for_input:
		var text = input_field.text.strip_edges()
		_send_message({"type": "INPUT_REPLY", "payload": {"value": text}})

# Save system - keeping original logic
func _on_save_pressed():
	_initialize_save_lists()  # Direct call instead of _update_save_lists()
	save_menu.visible = true
	save_menu.mouse_filter = Control.MOUSE_FILTER_STOP
	save_menu.get_node("SaveMenuBG").mouse_filter = Control.MOUSE_FILTER_STOP

func _on_return_game():
	save_menu.visible = false
	save_menu.mouse_filter = Control.MOUSE_FILTER_IGNORE
	save_menu.get_node("SaveMenuBG").mouse_filter = Control.MOUSE_FILTER_IGNORE

func _on_save_confirm():
	var save_list = save_menu.get_node("SavePanel/SavePanelContent/SaveTabs/Save Game/SaveSlotContainer/SaveSlotList")
	var name_input = save_menu.get_node("SavePanel/SavePanelContent/SaveTabs/Save Game/SaveSlotContainer/SaveNameContainer/SaveNameInput")
	
	var selected = save_list.get_selected_items()
	var slot = selected[0] if selected.size() > 0 else 0
	var save_name = name_input.text.strip_edges()
	if save_name.is_empty():
		save_name = "Save" + str(slot + 1)
	
	_send_message({
		"type": "SAVE_REQUEST", 
		"payload": {
			"slot": slot, 
			"name": save_name
		}
	})

func _on_load_confirm():
	var load_list = save_menu.get_node("SavePanel/SavePanelContent/SaveTabs/Load Game/LoadSlotContainer/LoadSlotList")
	var selected = load_list.get_selected_items()
	if selected.size() > 0:
		var slot = selected[0]
		
		if slot in save_data:
			var save_info = save_data[slot]
			var save_name = save_info.get("name", "Save" + str(slot + 1))
			_show_load_confirmation(slot, save_name)
		else:
			_show_message("No save in this slot", "red")

# Keep original confirmation dialog logic - create new each time
func _show_load_confirmation(slot: int, save_name: String):
	var dialog = AcceptDialog.new()
	dialog.title = "Confirm Load"
	dialog.dialog_text = "Load save '" + save_name + "'?\n\nCurrent progress will be lost."
	dialog.add_cancel_button("Cancel")
	
	dialog.size = Vector2(400, 200)
	dialog.position = (get_viewport().size - dialog.size) / 2
	
	dialog.confirmed.connect(_on_load_confirmed.bind(slot, save_name))
	dialog.canceled.connect(_on_load_canceled)
	
	get_parent().add_child(dialog)
	dialog.popup_centered()

func _on_load_confirmed(slot: int, save_name: String):
	_on_return_game()
	_send_message({"type": "LOAD_REQUEST", "payload": {"slot": slot}})
	_show_message("Loading save...", "blue")

func _on_load_canceled():
	pass

func _on_quick_save():
	_send_message({
		"type": "SAVE_REQUEST", 
		"payload": {
			"slot": 0, 
			"name": "Quick Save"
		}
	})

func _on_quick_load():
	if 0 in save_data:
		var save_info = save_data[0]
		var save_name = save_info.get("name", "Quick Save")
		_show_load_confirmation(0, save_name)
	else:
		_show_message("No quick save", "red")

func _handle_save_success(payload: Dictionary):
	var slot_raw = payload.get("slot", 0)
	var slot = int(slot_raw)
	var save_name = payload.get("name", "Save")
	var message = payload.get("message", "✓ " + save_name + " saved successfully")
	
	save_data[slot] = {
		"name": save_name,
		"time": Time.get_datetime_string_from_system(),
		"exists": true
	}
	
	_initialize_save_lists()
	_show_message(message, "green")
	_on_return_game()

func _handle_load_success(payload: Dictionary):
	var save_name = payload.get("name", "Save")
	var message = payload.get("message", "✓ " + save_name + " loaded successfully")
	
	_show_message(message, "green", true)
	_send_message({"type": "NEXT"})

func _handle_save_error(payload: Dictionary):
	var error_msg = payload.get("message", "Operation failed")
	_show_message("✗ " + error_msg, "red")
	_on_return_game()

# Unified message display function
func _show_message(message: String, color: String = "green", brief: bool = false):
	if brief:
		# Brief success message in corner
		var success_label = Label.new()
		success_label.text = message
		success_label.add_theme_color_override("font_color", Color.GREEN)
		success_label.position = Vector2(get_viewport().size.x - 200, 10)
		get_parent().add_child(success_label)
		
		var timer = Timer.new()
		add_child(timer)
		timer.wait_time = 1.0
		timer.one_shot = true
		timer.timeout.connect(func():
			success_label.queue_free()
			timer.queue_free()
		)
		timer.start()
	else:
		# Temporary message in main text
		var current_text = text_label.text
		text_label.text = current_text + "\n[color=" + color + "]" + message + "[/color]"
		
		var timer = Timer.new()
		add_child(timer)
		timer.wait_time = 2.0
		timer.one_shot = true
		timer.timeout.connect(func():
			text_label.text = current_text
			timer.queue_free()
		)
		timer.start()

func _exit_tree():
	if socket:
		socket.close()
	
	if engine_process > 0:
		OS.kill(engine_process)

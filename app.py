"""Flask application for AI-powered Live2D avatar with Twitch integration.

This module provides a web server that manages a Live2D avatar, processes AI responses
through Ollama, and handles Twitch chat interactions with WebSocket communication.
"""

# Monkey patching for eventlet compatibility - MUST be done before other imports
import eventlet
eventlet.monkey_patch(all=True)

# Suppress eventlet warnings about already-imported modules
import warnings
warnings.filterwarnings('ignore', message='.*RLock.*greened.*')

import os
import re
import logging
import subprocess
import time
import datetime
import base64
import bleach
from flask import Flask, render_template, send_from_directory, abort, request, jsonify
from flask_socketio import SocketIO
from dotenv import load_dotenv, find_dotenv
import ollama
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
import fitz  # PyMuPDF
import google.generativeai as genai
from utils.rag_handler import RAGHandler
from utils.computer_control import ComputerController, COMPUTER_CONTROL_FUNCTIONS
from utils.file_manager import FileManager, setup_file_manager_routes

# Load default .env file
dotenv_path = find_dotenv()
if not dotenv_path:
    dotenv_path = find_dotenv('.env.example')
load_dotenv(dotenv_path, encoding='utf-8')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'supersecret')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting for Gemini API
gemini_last_call_time = 0
GEMINI_MIN_DELAY = 4.0  # Minimum 4 seconds between requests (15 requests/min = 4s interval)

# Configuration class
class Config:
    """Manages environment variables and application settings."""
    socketio_cors_allowed: str  # explicitly declare the attribute

    def __init__(self):
        self.fields = [
            'PERSONA_NAME', 'PERSONA_ROLE', 'PRE_PROMPT', 'AVATAR_MODEL', 'BACKGROUND_IMAGE',
            'CHANNEL_NAME', 'TWITCH_TOKEN', 'TWITCH_CLIENT_ID', 'EXTRA_DELAY_LISTENER', 'NB_SPAM_MESSAGE',
            'OLLAMA_MODEL', 'BOT_NAME_FOLLOW_SUB', 'KEY_WORD_FOLLOW', 'KEY_WORD_SUB',
            'DELIMITER_NAME', 'DELIMITER_NAME_END', 'SOCKETIO_IP', 'SOCKETIO_IP_PORT',
            'SOCKETIO_CORS_ALLOWED', 'API_URL', 'API_URL_PORT', 'FIXED_LANGUAGE', 'VOICE_GENDER',
            'WAKE_WORD', 'WAKE_WORD_ENABLED', 'CELEBRATE_FOLLOW', 'CELEBRATE_SUB',
            'CELEBRATE_FOLLOW_MESSAGE', 'CELEBRATE_SUB_MESSAGE', 'CELEBRATE_SOUND',
            'SPEECH_BUBBLE_ENABLED', 'ASK_RAG', 'AI_PROVIDER', 'GEMINI_API_KEY', 'GEMINI_MODEL',
            'ENABLE_COMPUTER_CONTROL'
        ]
        self.load()

        if not self.socketio_cors_allowed:
            self.socketio_cors_allowed = '*'  # set default if not provided

    def load(self):
        """Load configuration from environment variables."""
        for field in self.fields:
            setattr(self, field.lower(), os.getenv(field))

    def update(self, **kwargs):
        """Update configuration settings with provided values and save changes."""
        for key, value in kwargs.items():
            if key.upper() in self.fields:
                setattr(self, key.lower(), value)
        self.save()

    def save(self):
        """Persist current configuration to the environment file."""
        env_file_path = find_dotenv()
        if not env_file_path:
            # If no .env file exists, create one in the project root
            env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

        with open(env_file_path, 'w', encoding='utf-8') as f:  # changed encoding to utf-8
            for field in self.fields:
                value = getattr(self, field.lower())
                if value is not None:
                    f.write(f'{field}="{value}"\n')

    def to_dict(self):
        """Return the configuration settings as a dictionary."""
        return {field: getattr(self, field.lower()) for field in self.fields}

config = Config()

# SocketIO setup
socketio = SocketIO(app, cors_allowed_origins=config.socketio_cors_allowed, async_mode='eventlet')

listener_process = None

# Initialize global RAG handler
rag_handler = RAGHandler()

# Initialize Computer Controller
computer_controller = ComputerController(require_confirmation=True)

# Initialize FileManager
file_manager = FileManager(app.root_path, socketio, rag_handler)

# Setup file manager routes
setup_file_manager_routes(socketio, file_manager)

# Route handlers
@app.route('/')
def home():
    """Render the avatar homepage."""
    return render_template('avatar.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files from the static directory."""
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

@app.route('/models/<path:filename>')
def serve_model_files(filename):
    """Serve model files if they exist, otherwise abort with 404."""
    models_dir = os.path.join(app.root_path, 'models')
    if os.path.isfile(os.path.join(models_dir, filename)):
        return send_from_directory(models_dir, filename)
    return abort(404)

@app.route('/download/document/<category>/<filename>')
def download_document(category, filename):
    """Serve document files for download based on category."""
    from werkzeug.utils import secure_filename
    safe_filename = secure_filename(filename)
    
    logger.info(f"Download request - Category: {category}, Filename: {filename}, Safe: {safe_filename}")
    
    if category == 'rag':
        directory = os.path.join(app.root_path, 'static', 'doc')
    elif category == 'llm':
        directory = os.path.join(app.root_path, 'output')
    else:
        logger.error(f"Invalid category: {category}")
        return abort(404)
    
    file_path = os.path.join(directory, safe_filename)
    logger.info(f"Looking for file at: {file_path}")
    logger.info(f"File exists: {os.path.isfile(file_path)}")
    
    if os.path.isfile(file_path):
        return send_from_directory(directory, safe_filename, as_attachment=True)
    
    logger.error(f"File not found: {file_path}")
    return abort(404)

# New route to render the callback page that extracts the token from URL hash
@app.route('/auth/twitch/callback')
def twitch_callback():
    return render_template('twitch_callback.html')

# New route to receive the access token via POST, update config, and notify UI
@app.route('/auth/twitch/store_token', methods=['POST'])
def store_twitch_token():
    data = request.get_json()
    access_token = data.get('access_token')
    if not access_token:
        return jsonify({'status': 'error', 'message': 'No access token provided'}), 400
    # Update configuration with the new token
    config.update(TWITCH_TOKEN=access_token)
    # Emit the updated token to the UI
    socketio.emit('update_twitch_token', {'twitchToken': access_token})
    return jsonify({'status': 'success', 'twitchToken': access_token})

# New API endpoint to list JSON files for a model
@app.route('/api/models/<modelName>')
def get_model_files(modelName):
    models_dir = os.path.join(app.root_path, 'models', modelName)
    if not os.path.isdir(models_dir):
        return jsonify({"files": []})
    files = [f for f in os.listdir(models_dir) if f.endswith('.json')]
    return jsonify({"files": files})

@app.route('/api/ask_ai', methods=['POST'])
def api_ask_ai():
    data = request.get_json()
    response, status_code = process_ai_request(data)
    if status_code == 200:
        socketio.emit('ai_response', {
            'text': response['message'],
            'fixedLanguage': response['language']
        })

        return jsonify({
            'status': 'success',
            'text': response['message'],
            'fixedLanguage': response['language']
        }), 200
    else:
        # Emit error to frontend via socketio
        socketio.emit('ai_error', {
            'message': response.get('message', 'Error')
        })
        return jsonify({
            'status': 'error',
            'message': response.get('message', 'Error')
        }), status_code

# Helper functions
def get_directory_contents(directory):
    """Return a list of subdirectory names in the given directory."""
    try:
        return [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]
    except OSError as e:
        logger.error("Error accessing directory %s: %s", directory, e)
        return []

def get_file_contents(directory):
    """Return a list of file names in the given directory."""
    try:
        return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    except OSError as e:
        logger.error("Error accessing directory %s: %s", directory, e)
        return []

def get_avatar_models():
    """Return a dict containing available avatar models."""
    return {'models': get_directory_contents(os.path.join(app.root_path, 'models'))}

def get_background_images():
    """Return a dict containing available background images."""
    return {'images': get_file_contents(os.path.join(app.root_path, 'static', 'images', 'background'))}

def get_ollama_models():
    """Return a dict containing available Ollama models."""
    # Check if using Gemini provider
    try:
        ai_provider = getattr(config, 'ai_provider', 'ollama') or 'ollama'
        if ai_provider.lower() == 'gemini':
            return {'models': []}
    except:
        pass  # If config not loaded yet, proceed with Ollama check

    try:
        response = ollama.list()
        return {'models': [model['model'] for model in response['models']]}
    except Exception as e:
        # Only log as warning since this is expected when using Gemini or Ollama isn't running
        logger.debug("Ollama not available: %s", e)
        return {'models': []}

def get_celebration_sounds():
    """Get list of available celebration sound files."""
    sounds_dir = os.path.join(app.root_path, 'static', 'mp3')
    try:
        return {'sounds': [f for f in os.listdir(sounds_dir) if f.endswith('.mp3')]}
    except OSError as e:
        logger.error("Error accessing sounds directory: %s", e)
        return {'sounds': []}

def call_ai_model(messages, screenshot_file_path=None):
    """
    Call the appropriate AI model based on configuration.
    Returns tuple: (response_text, model_name, api_call_time)
    """
    global gemini_last_call_time
    ai_provider = getattr(config, 'ai_provider', 'ollama') or 'ollama'
    start_time = time.time()

    if ai_provider.lower() == 'gemini':
        # Rate limiting for Gemini API
        time_since_last_call = time.time() - gemini_last_call_time
        if time_since_last_call < GEMINI_MIN_DELAY:
            wait_time = GEMINI_MIN_DELAY - time_since_last_call
            logger.info("Rate limiting: waiting %.2f seconds before Gemini API call", wait_time)
            time.sleep(wait_time)

        # Use Gemini API
        gemini_api_key = getattr(config, 'gemini_api_key', None)
        gemini_model = getattr(config, 'gemini_model', 'gemini-1.5-flash')

        if not gemini_api_key:
            raise ValueError("Gemini API key not configured. Please add your API key in settings.")

        try:
            genai.configure(api_key=gemini_api_key)

            # Check if computer control is enabled
            enable_computer_control_value = getattr(config, 'enable_computer_control', 'False')
            # Handle both string and boolean values
            if isinstance(enable_computer_control_value, bool):
                enable_computer_control = enable_computer_control_value
            else:
                enable_computer_control = str(enable_computer_control_value).lower() == 'true'

            # Check if the model supports function calling
            # Gemini 2.0 Flash Lite doesn't support function calling well
            supports_function_calling = 'lite' not in gemini_model.lower()

            if enable_computer_control and not supports_function_calling:
                logger.warning(f"Model {gemini_model} may not support function calling. Consider using gemini-2.0-flash-exp or gemini-1.5-flash for computer control.")

            # Initialize model with or without tools
            if enable_computer_control and supports_function_calling:
                # Convert function definitions to Gemini format
                from google.generativeai.types import FunctionDeclaration, Tool

                function_declarations = []
                for func in COMPUTER_CONTROL_FUNCTIONS:
                    function_declarations.append(
                        FunctionDeclaration(
                            name=func["name"],
                            description=func["description"],
                            parameters=func["parameters"]
                        )
                    )

                tools = [Tool(function_declarations=function_declarations)]

                # Configure model with automatic function calling
                tool_config = {'function_calling_config': {'mode': 'AUTO'}}
                model = genai.GenerativeModel(
                    gemini_model,
                    tools=tools,
                    tool_config=tool_config
                )
                logger.info("Initialized model with computer control tools")
            else:
                model = genai.GenerativeModel(gemini_model)

            # Convert messages to Gemini format
            # Combine system message with first user message
            gemini_messages = []
            system_content = ""

            for msg in messages:
                if msg['role'] == 'system':
                    system_content = msg['content']
                elif msg['role'] == 'user':
                    content = msg['content']
                    if system_content:
                        content = f"{system_content}\n\n{content}"
                        system_content = ""
                    gemini_messages.append({'role': 'user', 'parts': [content]})
                elif msg['role'] == 'assistant':
                    gemini_messages.append({'role': 'model', 'parts': [msg['content']]})

            # Handle screenshot for Gemini
            if screenshot_file_path:
                # Load the image into memory (don't keep file handle open)
                import PIL.Image
                image = PIL.Image.open(screenshot_file_path)
                # Convert to RGB if necessary (Gemini needs RGB)
                if image.mode not in ('RGB', 'RGBA'):
                    image = image.convert('RGB')
                # Add image to the last user message
                if gemini_messages and gemini_messages[-1]['role'] == 'user':
                    gemini_messages[-1]['parts'].append(image)

            # Generate response
            chat = model.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
            response = chat.send_message(gemini_messages[-1]['parts'] if gemini_messages else "Hello")

            # Debug: Log response structure
            logger.info(f"Response candidates: {len(response.candidates)}")
            if response.candidates:
                logger.info(f"Response parts: {len(response.candidates[0].content.parts)}")
                for i, part in enumerate(response.candidates[0].content.parts):
                    logger.info(f"Part {i}: has function_call = {hasattr(part, 'function_call')}")
                    if hasattr(part, 'function_call'):
                        fc = part.function_call
                        logger.info(f"Part {i} function_call: name={fc.name if fc and hasattr(fc, 'name') else 'None'}")

            # Handle function calling if enabled and supported - Loop to handle multiple function calls
            max_function_calls = 10  # Prevent infinite loops
            function_call_count = 0

            while (enable_computer_control and supports_function_calling and
                   response.candidates[0].content.parts and
                   function_call_count < max_function_calls):

                # Check all parts for function calls (parallel function calling)
                function_calls_found = []
                for part in response.candidates[0].content.parts:
                    if (hasattr(part, 'function_call') and part.function_call and
                        hasattr(part.function_call, 'name') and part.function_call.name):
                        function_calls_found.append(part.function_call)

                # If no function calls, break the loop
                if not function_calls_found:
                    logger.info(f"No more function calls found after {function_call_count} executions")
                    break

                logger.info(f"Found {len(function_calls_found)} function call(s) to execute")

                # Execute all function calls
                function_responses = []
                for function_call in function_calls_found:
                    function_name = function_call.name
                    function_args = dict(function_call.args)

                    logger.info(f"Function call {function_call_count + 1}: {function_name} with args: {function_args}")

                    # Execute the function
                    result = computer_controller.execute_action(function_name, function_args)
                    logger.info(f"Function execution result: {result}")

                    # Create function response
                    function_response = genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=function_name,
                            response={'result': result}
                        )
                    )
                    function_responses.append(function_response)
                    function_call_count += 1

                # Send all function responses back to model
                response = chat.send_message(function_responses)

                # Log response carefully - check if it has text
                try:
                    response_preview = response.text if hasattr(response, 'text') and response.text else 'Checking for more function calls...'
                    logger.info(f"Response after function call(s): {response_preview}")
                except Exception:
                    logger.info("Response after function call(s): Contains function calls or no text yet")

            if function_call_count > 0:
                logger.info(f"Total function calls executed: {function_call_count}")

            # Update last call time for rate limiting
            gemini_last_call_time = time.time()

            api_time = time.time() - start_time

            # Get final text response - handle case where response only has function calls
            try:
                final_text = response.text
            except Exception as e:
                logger.warning(f"Could not extract text from response: {e}")
                # If there's no text (only function calls), provide a default response
                final_text = "Task completed!"

            return final_text, gemini_model, api_time

        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg or 'Resource exhausted' in error_msg:
                raise ValueError("Gemini API rate limit exceeded. Please wait a moment before trying again. Free tier has limited requests per minute.")
            elif 'API_KEY' in error_msg or 'invalid' in error_msg.lower():
                raise ValueError("Invalid Gemini API key. Please check your API key in settings.")
            else:
                raise ValueError(f"Gemini API error: {error_msg}")

    else:
        # Use Ollama (default)
        ollama_model = config.ollama_model

        # Add screenshot to user message if provided
        if screenshot_file_path:
            for msg in messages:
                if msg['role'] == 'user' and 'images' not in msg:
                    msg['images'] = [screenshot_file_path]
                    break

        response = ollama.chat(
            model=ollama_model,
            messages=messages
        )

        api_time = time.time() - start_time
        return response['message']['content'], ollama_model, api_time

def process_ai_request(data):
    """Process an AI request based on the input data and return a response."""
    start_time = time.time()
    username = data.get('username', 'Gaëtan')
    text = data.get('text', '').strip()
    source = data.get('source', 'twitch')
    fixed_language = data.get('fixedLanguage')

    # Process screenshot if provided
    screenshot = data.get('screenshot')
    screenshot_file_path = None
    if screenshot:
        try:
            if screenshot.startswith("data:image"):
                header, encoded = screenshot.split(',', 1)
                image_data = base64.b64decode(encoded)
                filename = f"ask_ai_{int(time.time())}.png"
                screenshot_file_path = os.path.join(app.root_path, "static", "screenshots", filename)
                os.makedirs(os.path.dirname(screenshot_file_path), exist_ok=True)
                with open(screenshot_file_path, "wb") as f:
                    f.write(image_data)
            else:
                screenshot_file_path = screenshot
        except Exception as e:
            print("Error processing screenshot:", e)
            screenshot_file_path = None

    if not text:
        return {'status': 'error', 'message': 'No text provided'}, 400

    # Write discussion file and build conversation history
    discussion_file_path = os.path.join(app.root_path, 'static', 'discution', f"{username.lower()}.txt")
    os.makedirs(os.path.dirname(discussion_file_path), exist_ok=True)
    with open(discussion_file_path, 'a', encoding='utf-8') as disc_file:
        disc_file.write(f"({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}) {username} - {text}\n")
    sanitized_input = bleach.clean(text)

    # Build proper conversation history with alternating roles
    conversation_history = []
    if os.path.exists(discussion_file_path):
        with open(discussion_file_path, 'r', encoding='utf-8') as conv_file:
            lines = conv_file.read().splitlines()

            # Parse conversation history properly
            recent_exchanges = []
            for line in lines[-10:]:  # Reduced to last 10 lines for more focused context
                if ' - ' in line:
                    # Extract timestamp, user, and message
                    parts = line.split(' - ', 1)
                    if len(parts) == 2:
                        timestamp_user = parts[0].strip('()')
                        message = parts[1].strip()

                        # Extract username from timestamp
                        if ' ' in timestamp_user:
                            msg_user = timestamp_user.split(' ', 1)[1] if ' ' in timestamp_user else username
                            recent_exchanges.append({
                                'user': msg_user,
                                'message': message
                            })

            # Build alternating conversation (skip duplicates)
            last_message = None
            for exchange in recent_exchanges:
                msg = exchange['message']
                # Skip if it's the same as last message (duplicate)
                if msg == last_message:
                    continue
                last_message = msg

                # Determine if this is from the user or the bot
                if exchange['user'].lower() == username.lower():
                    conversation_history.append({"role": "user", "content": msg})
                else:
                    conversation_history.append({"role": "assistant", "content": msg})

    # Detect language
    if source == 'microphone' and fixed_language:
        detected_language = fixed_language
    else:
        try:
            detected_language = detect(sanitized_input)
        except LangDetectException:
            detected_language = 'en'

    # Get relevant documents from RAG handler
    retrieved_docs = rag_handler.get_relevant_documents(sanitized_input) if config.ask_rag else []

    # Check if computer control is enabled
    enable_computer_control_value = getattr(config, 'enable_computer_control', 'False')
    if isinstance(enable_computer_control_value, bool):
        computer_control_enabled = enable_computer_control_value
    else:
        computer_control_enabled = str(enable_computer_control_value).lower() == 'true'

    # Build enhanced system message with better personality
    system_message = f"""You are {config.persona_name}, {config.persona_role}

Your personality:
- Warm, friendly, and naturally conversational
- Use casual language and contractions (I'm, you're, etc.)
- Show genuine interest in what users say
- Express personality through your words, NOT with emojis or emoticons
- Keep responses short and punchy (1-3 sentences max)
- Match the user's energy and tone

Language: Respond ONLY in {detected_language}

Key guidelines:
- Be yourself - don't sound like a formal assistant
- DON'T greet again if you already greeted the user in previous messages
- If continuing a conversation, just answer the question directly without "Salut" or greetings
- Only greet if this is the first message in the conversation
- Reference previous messages when relevant
- Stay appropriate for Twitch (no hate speech, etc.)"""

    # Add computer control instructions if enabled
    if computer_control_enabled:
        system_message += """

COMPUTER CONTROL CAPABILITIES:
You have the ability to control the computer to help users. When a user asks you to:
- Open applications (notepad, calculator, chrome, etc.) → Use open_application function
- Open websites ONLY to view them → Use open_website function
- Search Google (just to open a search page) → Use search_web function
- Get content/information FROM a website → Use scrape_webpage function (DON'T open first, just scrape!)
- Extract links from a webpage → Use extract_links function
- Create files → Use create_file function (just use filename like "jobs.txt" - it will be saved automatically!)
- List directory contents → Use list_directory function

FILE CREATION: When creating files, just use a simple filename like "jobs.txt" or "results.txt".
The file will be automatically saved in the project's output folder. No need for full paths!

CRITICAL DISTINCTION:
- open_website = Opens website in browser for USER to see (doesn't give you the content!)
- scrape_webpage = Gets the actual content from a website that YOU can read and use
- extract_links = Gets links from a webpage

IMPORTANT: When asked to "get jobs from LinkedIn" or similar:
→ DON'T open_website first! Just scrape_webpage directly!
→ scrape_webpage can access websites without opening them in a browser

When users ask to "find", "get", "search for", or "look for" information ON a specific website:
→ Use scrape_webpage or extract_links (NOT open_website! NOT search_web!)

When users ask to just "Google something" or "search the web":
→ Use search_web

IMPORTANT: When a user asks you to do something that requires computer control, YOU MUST use the appropriate function. Don't just say you'll do it - actually call the function to execute the action!

MULTI-STEP TASKS: When a user asks you to do multiple things (like "go to X and do Y"), you should:
1. Execute ALL the functions needed to complete the task
2. Don't stop after the first function - keep going!
3. For "open website and scrape it" → First open_website, then IMMEDIATELY scrape_webpage
4. For "scrape and save to file" → First scrape_webpage, then IMMEDIATELY create_file
5. Complete the ENTIRE task before giving a final response

Example:
User: "open chrome"
You: [Call open_application with application_name="chrome"] then respond "Opening Chrome for you!"

User: "Google python tutorials"
You: [Call search_web with query="python tutorials"] then respond "Opening Google search!"

User: "what's on the homepage of example.com?"
You: [Call scrape_webpage with url="example.com"] then respond with the content found

User: "find CTO job links on linkedin.com/jobs"
You: [Call extract_links with url="linkedin.com/jobs/search/?keywords=cto" and filter_text="cto"] then list the jobs found

User: "find the top 5 CTO jobs on LinkedIn in Belgium"
You: [Call scrape_webpage with url="linkedin.com/jobs/search/?keywords=cto&location=Belgium"] to get job listings, then tell user what you found

User: "go to linkedin and find IT director jobs in Belgium, save to notepad"
You: [Call scrape_webpage with url="linkedin.com/jobs/search/?keywords=it+director&location=Belgium"] then [Call create_file with file_path and content] then respond "Done! Saved jobs to notepad."

For complex tasks, chain multiple functions in the SAME response:
1. Don't say "I'll do X" - just DO X by calling the functions
2. Call multiple functions in sequence to complete the full task
3. Only respond with text after ALL functions are called
4. Example flow: scrape_webpage → create_file → respond "All done!"

Always use the functions when the user requests an action."""

    system_message += f"""

CRITICAL for text-to-speech:
- NEVER use emojis, emoticons, or symbols
- NEVER use parentheses with alternatives like "Prêt(e)" or "heureux(se)"
- Always choose one gender form and stick with it (prefer neutral or masculine form)
- Write ONLY words that can be spoken naturally and fluently
- Avoid special characters, abbreviations, or formatting
- Write complete, speakable sentences

Additional instructions: {config.pre_prompt}"""

    # Build user message content
    if config.ask_rag and retrieved_docs:
        user_message_content = f"Context from memory: {retrieved_docs}\n\nCurrent message: {sanitized_input}"
    else:
        user_message_content = sanitized_input

    user_message = {"role": "user", "content": user_message_content}
    if screenshot_file_path:
        user_message["images"] = [screenshot_file_path]

    # Build messages: include conversation history for context
    messages = [{"role": "system", "content": system_message.strip()}]

    # Include conversation history (reduced if there's a screenshot to save context window)
    if conversation_history:
        if screenshot_file_path:
            # With screenshot, only include last 3 exchanges to save context
            messages.extend(conversation_history[-6:])
        else:
            # Without screenshot, include more history
            messages.extend(conversation_history)

    messages.append(user_message)

    try:
        print(f"messages: {messages}")
        api_start_time = time.time()

        # Call AI model (Ollama or Gemini based on config)
        response_text, model_name, api_time = call_ai_model(messages, screenshot_file_path)

        print(f"response: {response_text}")
        # Clean response but preserve natural formatting
        cleaned_response = re.sub(
            r'<think>.*?</think>',
            '',
            response_text,
            flags=re.DOTALL
        ).strip()
        # Only normalize excessive whitespace (3+ spaces/newlines)
        cleaned_response = re.sub(r'\s{3,}', ' ', cleaned_response)

        # Remove all emojis and emoticons
        # This regex matches all emoji characters
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            u"\U0001FA00-\U0001FA6F"  # Chess Symbols
            u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            u"\U00002600-\U000026FF"  # Miscellaneous Symbols
            "]+",
            flags=re.UNICODE
        )
        cleaned_response = emoji_pattern.sub('', cleaned_response).strip()

        # Remove gender alternatives in parentheses like "Prêt(e)" -> "Prêt"
        # Matches patterns like (e), (s), (es), (se), etc.
        cleaned_response = re.sub(r'\([eséESÉ]+\)', '', cleaned_response)

        # Remove markdown formatting (asterisks for bold/italic)
        cleaned_response = cleaned_response.replace('**', '')  # Remove bold markers
        cleaned_response = cleaned_response.replace('*', '')   # Remove italic/bullet markers

        # Remove special quotes and apostrophes (backticks, smart quotes, etc.)
        # Replace with standard equivalents for TTS
        cleaned_response = cleaned_response.replace('`', "'")  # backtick to apostrophe
        cleaned_response = cleaned_response.replace('"', '"')  # smart double quote opening
        cleaned_response = cleaned_response.replace('"', '"')  # smart double quote closing
        cleaned_response = cleaned_response.replace(''', "'")  # smart single quote opening
        cleaned_response = cleaned_response.replace(''', "'")  # smart single quote closing
        cleaned_response = cleaned_response.replace('«', '"')  # French quotes
        cleaned_response = cleaned_response.replace('»', '"')  # French quotes

        # Clean up any double spaces created by removals
        cleaned_response = re.sub(r'\s+', ' ', cleaned_response).strip()

        try:
            response_language = detect(cleaned_response)
        except LangDetectException:
            response_language = detected_language
        total_time = time.time() - start_time
        print("AI Processing Times:")
        print(f"  - Model call: {model_name}")
        print(f"  - API call: {api_time:.2f} seconds")
        print(f"  - Total processing: {total_time:.2f} seconds")
        return {
            'status': 'success',
            'message': cleaned_response,
            'language': response_language
        }, 200
    except Exception as e:
        total_time = time.time() - start_time
        logger.error("AI processing error (%0.2f seconds): %s", total_time, e)
        return {'status': 'error', 'message': f'AI service error: {e}'}, 500

def emit_celebration_event(event_type, username):
    """Emit celebration events to the frontend based on event type."""
    message = ""
    # Convert string 'true'/'false' to boolean or handle direct boolean values
    celebrate_follow = str(config.celebrate_follow).lower() == 'true'
    celebrate_sub = str(config.celebrate_sub).lower() == 'true'

    if event_type == 'follow' and celebrate_follow:
        message = f"New FOLLOW: {username}"
    elif event_type == 'sub' and celebrate_sub:
        message = f"NEW SUB: {username}"

    if message:
        socketio.emit('fireworks', {'message': message})

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle new client connection."""
    logger.info("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected")

@socketio.on('speak')
def handle_speak(data):
    """Process speak event data and emit the text to be spoken."""
    text = data.get('text', '').strip()
    if text:
        try:
            # Detect language of the text to speak
            detected_language = detect(text)
        except LangDetectException:
            detected_language = 'en'

        print(f"detected_language: {detected_language}")

        socketio.emit('speak_text', {
            'text': text,
            'fixedLanguage': detected_language  # Use detected language instead of passed language
        })

@socketio.on('ask_ai')
def handle_ask_ai(data):
    """Handle AI request from client and emit AI response."""
    response, status_code = process_ai_request(data)
    if status_code == 200:
        socketio.emit('ai_response', {
            'text': response['message'],
            'fixedLanguage': response['language']
        })
    else:
        # Emit error to frontend
        socketio.emit('ai_error', {
            'message': response.get('message', 'Unknown error occurred')
        })

@socketio.on('save_config')
def handle_save_config(data):
    """Handle saving configuration settings."""
    try:
        config.update(**data)
        socketio.emit('update_twitch_config', {k: v for k, v in data.items() if k in [
            'EXTRA_DELAY_LISTENER', 'NB_SPAM_MESSAGE', 'BOT_NAME_FOLLOW_SUB',
            'KEY_WORD_FOLLOW', 'KEY_WORD_SUB', 'DELIMITER_NAME', 'DELIMITER_NAME_END',
            'CHANNEL_NAME'
        ]})
        socketio.emit('save_config_response', {'status': 'success', 'config': config.to_dict()})
    # Example: catch IO errors explicitly
    except (IOError, OSError) as e:
        logger.error("Error saving configuration: %s", e)
        socketio.emit('save_config_response', {'status': 'error', 'message': str(e)})

@socketio.on('get_init_cfg')
def handle_get_init_cfg():
    """Emit initial configuration and resource lists to the client."""
    try:
        socketio.emit('init_cfg', {
            'status': 'success',
            'data': {
                'config': config.to_dict(),
                'avatarList': get_avatar_models().get('models', []),
                'backgroundList': get_background_images().get('images', []),
                'ollamaModelList': get_ollama_models().get('models', []),
                'soundsList': get_celebration_sounds().get('sounds', [])
            }
        })
    except (AttributeError, KeyError, TypeError) as e:
        logger.error("Error getting initial configuration: %s", e)
        socketio.emit('init_cfg', {'status': 'error', 'message': str(e)})

@socketio.on('get_listener_status')
def handle_get_listener_status():
    """Emit the current status of the listener process."""
    status = 'running' if listener_process and listener_process.poll() is None else 'stopped'
    socketio.emit('listener_status', {'status': status})

@socketio.on('get_conversation_history')
def handle_get_conversation_history(data):
    """Retrieve and emit conversation history for a specific user."""
    username = data.get('username', 'Gaëtan').lower()
    discussion_file_path = os.path.join(app.root_path, 'static', 'discution', f"{username}.txt")

    history = []
    if os.path.exists(discussion_file_path):
        try:
            with open(discussion_file_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()

            for line in lines:
                if ' - ' in line:
                    parts = line.split(' - ', 1)
                    if len(parts) == 2:
                        timestamp_user = parts[0].strip('()')
                        message = parts[1].strip()

                        # Extract timestamp and user
                        if ' ' in timestamp_user:
                            timestamp, user = timestamp_user.split(' ', 1)
                            history.append({
                                'timestamp': timestamp,
                                'user': user,
                                'message': message,
                                'role': 'user' if user.lower() == username else 'assistant'
                            })
        except Exception as e:
            logger.error("Error reading conversation history: %s", e)

    socketio.emit('conversation_history', {
        'status': 'success',
        'history': history,
        'username': username
    })

@socketio.on('clear_conversation_history')
def handle_clear_conversation_history(data):
    """Clear conversation history for a specific user."""
    username = data.get('username', 'Gaëtan').lower()
    discussion_file_path = os.path.join(app.root_path, 'static', 'discution', f"{username}.txt")

    try:
        if os.path.exists(discussion_file_path):
            os.remove(discussion_file_path)
        socketio.emit('conversation_history_cleared', {
            'status': 'success',
            'username': username
        })
    except Exception as e:
        logger.error("Error clearing conversation history: %s", e)
        socketio.emit('conversation_history_cleared', {
            'status': 'error',
            'message': str(e)
        })

def get_python_executable():
    """Get the appropriate Python executable path."""
    venv_python = os.path.join(app.root_path, 'venv', 'Scripts', 'python.exe')
    if os.path.exists(venv_python):
        logger.info("Using venv Python: %s", venv_python)
        return venv_python

    # Try system Python paths
    system_paths = ['python', 'python3', 'py']
    for cmd in system_paths:
        try:
            subprocess.run([cmd, '--version'], capture_output=True, check=True)
            logger.info("Using system Python: %s", cmd)
            return cmd
        except (subprocess.SubprocessError, FileNotFoundError):
            continue

    logger.error("No Python executable found")
    raise RuntimeError("No Python executable found in venv or system path")

def load_pdf(pdf_path):
    """Load text content from a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        texts = [page.get_text("text") for page in doc]
        return texts
    # Catch file related errors explicitly
    except (OSError, RuntimeError) as e:
        logger.error("Error loading PDF %s: %s", pdf_path, e)
        return []

def load_documents_from_directory(directory):
    """Load text content from all documents in a directory."""
    documents = []
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if filename.endswith('.pdf'):
            documents.extend(load_pdf(file_path))
        # Add more file type handlers here if needed
    return documents

@socketio.on('start_listener')
def handle_start_listener():
    """Start the listener process for Twitch chat."""
    global listener_process
    if not listener_process:
        try:
            listener_dir = os.path.join(app.root_path, 'listener')
            python_exec = get_python_executable()

            listener_process = subprocess.Popen(
                [python_exec, 'twitch_listener.py'],
                cwd=listener_dir
            )
            logger.info("Started listener process with Python: %s", python_exec)
            socketio.emit('listener_update', {'status': 'success', 'action': 'start'})
        except (subprocess.SubprocessError, OSError) as e:
            logger.error("Error starting listener: %s", e)
            socketio.emit('listener_update', {
                'status': 'error',
                'action': 'start',
                'message': 'Failed to start listener: %s' % str(e)
            })
    else:
        socketio.emit('listener_update', {
            'status': 'error',
            'action': 'start',
            'message': 'Listener already running'
        })

@socketio.on('stop_listener')
def handle_stop_listener():
    """Stop the listener process if it is running."""
    global listener_process
    if listener_process:
        listener_process.terminate()
        listener_process = None
        socketio.emit('listener_update', {'status': 'success', 'action': 'stop'})
    else:
        socketio.emit('listener_update', {'status': 'error', 'action': 'stop', 'message': 'Listener not running'})

@socketio.on('trigger_event')
def handle_trigger_event(data):
    """Handle WebSocket events for triggering celebrations."""
    event_type = data.get('event_type', '').strip()
    username = data.get('username', '').strip()
    if event_type and username:
        emit_celebration_event(event_type, username)
        socketio.emit('event_response', {
            'status': 'success',
            'message': f'{event_type} event triggered for {username}'
        })
    else:
        socketio.emit('event_response', {
            'status': 'error',
            'message': 'Invalid event data'
        })

@socketio.on('trigger_ai_request')
def handle_trigger_ai_request(data):
    """Process AI requests from Twitch and emit speech response."""
    try:
        response, status_code = process_ai_request({
            'text': data.get('message', '').strip(),
            'username': data.get('username', '').strip(),
            'source': 'twitch'
        })
        if status_code == 200:
            socketio.emit('speak_text', {
                'text': response['message'],
                'fixedLanguage': response['language']
            })
    # Catch any errors from process_ai_request
    except Exception as e:
        logger.error("AI request error: %s", e)
        socketio.emit('ai_response_error', {'message': str(e)})

@socketio.on('display_question')
def handle_display_question(data):
    """Forward question display events to connected clients."""
    socketio.emit('display_question', data)

# Main entry point
if __name__ == '__main__':
    try:
        # Initialize RAG system with documents from the static/doc/ directory
        documents_dir = os.path.join(app.root_path, 'static', 'doc')
        rag_handler.initialize(documents_dir)

        logger.info("Starting server at %s:%s", config.api_url, config.api_url_port)
        socketio.run(app, host=config.socketio_ip, port=int(config.socketio_ip_port))
    # Catch server startup errors explicitly
    except (OSError, RuntimeError) as e:
        logger.error("Error starting server: %s", e)
[project]
# Whether to enable telemetry (default: true). No personal data is collected.
enable_telemetry = true

# List of environment variables to be provided by each user to use the app.
user_env = []

# Duration (in seconds) during which the session is saved when the connection is lost
session_timeout = 3600

# Enable third parties caching (e.g LangChain cache)
cache = false

# Authorized origins
allow_origins = ["https://www.naturalhealthgroup.com.au"]

# Follow symlink for asset mount (see https://github.com/Chainlit/chainlit/issues/317)
# follow_symlink = false

[features]
# Show the prompt playground
prompt_playground = false

# Process and display HTML in messages. This can be a security risk (see https://github.com/Chainlit/chainlit/issues/441)
unsafe_allow_html = false

# Process and display mathematical expressions. This can clash with custom CSS.
latex = false

# Automatically tag threads the user participates in. Defaults to true.
auto_tag_thread = true

# Authorize users to upload files with messages
multi_modal = true

# Allows user to use speech to text
[features.speech_to_text]
enabled = false
# See all languages here https://github.com/JamesBrill/react-speech-kit#language-support
# language = "en-US"

[UI]
# Name of the app and chatbot.
name = "Zoe - Natural Health Assistant"

# Show the readme while the thread is empty.
show_readme_as_default = false

# Description of the app and chatbot. This is used for HTML tags.
description = "Your personal natural health assistant from Natural Health Group Australia"

# Large size content are by default collapsed for a cleaner ui
default_collapse_content = true

# The default value for the expand messages settings.
default_expand_messages = false

# Hide the chain of thought details from the user in the UI.
hide_cot = true

# Link to your github repo. This will add a github button in the UI's header.
# github = ""

# Specify a CSS file that can be used to customize the user interface.
# The CSS file can be served from the ./public directory
custom_css = "/public/copilot-styles.css"

# Specify a Javascript file that can be used to customize the user interface.
# The Javascript file can be served from the ./public directory
custom_js = "/public/copilot-integration.js"

# Override default MUI light theme. (Check theme.py)
[UI.theme]
primary_color = "#2E8B57"
background_color = "#FAFAFA"
paper_color = "#FFFFFF"

[UI.theme.light]
background = "#FAFAFA"
paper = "#FFFFFF"

[UI.theme.dark]
background = "#1E1E1E"
paper = "#2D2D2D"

# Copilot configuration
[copilot]
# Copilot is a feature that allows you to embed Chainlit into any website.
# To use this feature, you need to set the following configuration:

# Origins allowed to embed the copilot. Can be a string or a list of strings.
allowed_origins = ["https://www.naturalhealthgroup.com.au"]

# Name of the copilot. Used to identify the copilot in the logs.
name = "Zoe: Natural Health Group Assistant"

# Description of the copilot.
description = "Get instant help with natural health questions and product recommendations"

# The copilot will be served at https://your-chainlit-app.com/copilot
# You can then embed it in your website with the following code:
# <chainlit-copilot></chainlit-copilot>

# Default collapsed state of the copilot
collapsed = true

# Default expanded state of the copilot
expanded = false

# Theme for the copilot
theme = "light"

# Button configuration
[copilot.button]
# Image URL for the button
image_url = "/public/logo_light.png"

# Alt text for the button image
alt = "Chat with Zoe"

# Style for the button
style = "position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px; border-radius: 50%; background-color: #2E8B57; border: none; cursor: pointer; box-shadow: 0 4px 12px rgba(46, 139, 87, 0.3); transition: all 0.3s ease;"

# Hover style for the button
hover_style = "transform: scale(1.1); box-shadow: 0 6px 20px rgba(46, 139, 87, 0.4);"
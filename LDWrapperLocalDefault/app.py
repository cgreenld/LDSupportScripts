from flask import Flask, render_template, jsonify, redirect, url_for
import os
import ldclient
from ldclient.config import Config
from ldclient import Context
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
#app.config['SECRET_KEY'] = os.urandom(24)

# Initialize LaunchDarkly client
ldclient.set_config(Config("sdk-454cfea4-bd3b-4de9-a817-4d87fdc2485a"))
client = ldclient.get()

context = Context.builder("context-key-123abc").name("Sandy").build()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ld-info')
def ld_info():
    return render_template('ld_info.html')

# Pass flag state and SDK key to all templates
@app.context_processor
def inject_flag_state():
    return {
        'is_ai_config_enabled': ldclient.get().variation("ai-config-enabled", context, False),
        'ld_client_id': os.getenv('LD_CLIENT_SDK_KEY', 'client-side-sdk-key-here')
    }

if __name__ == '__main__':
    app.run(debug=True) 
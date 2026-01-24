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
ldclient.set_config(Config(""))
client = ldclient.get()

context = Context.builder("context-key-123abc").name("Sandy").build()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/audience')
def audience():
    return render_template('audience.html')

@app.route('/ld-info')
def ld_info():
    return render_template('ld_info.html')

@app.route('/ai-config')
def ai_config():
    # Check if AI Config feature is enabled
    is_ai_config_enabled = ldclient.get().variation("ai-config-enabled", context, False)
    
    if not is_ai_config_enabled:
        return redirect(url_for('index'))
    
    return render_template('ai_config.html')

# Pass flag state and SDK key to all templates
@app.context_processor
def inject_flag_state():
    return {
        'is_ai_config_enabled': ldclient.get().variation("ai-config-enabled", context, False),
        'ld_client_id': os.getenv('LD_CLIENT_SDK_KEY', 'client-side-sdk-key-here')
    }

if __name__ == '__main__':
    app.run(debug=True) 

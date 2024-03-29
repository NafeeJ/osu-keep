import flask
from flask import session
import requests
import comment
from authlib.integrations.flask_client import OAuth

# import environment variables from .env
import dotenv
dotenv.load_dotenv()

import os
if (os.path.exists("./osu-keep-b226a1b1acf3.json")):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]= "./osu-keep-b226a1b1acf3.json"

app = flask.Flask(__name__)
app.secret_key = os.getenv("APP-SECRET-KEY")

# OAuth data
API_URL = 'https://osu.ppy.sh/api/v2'
TOKEN_URL = 'https://osu.ppy.sh/oauth/token'
CLIENT_ID = os.getenv("OSU-CLIENT-ID")
CLIENT_SECRET = os.getenv("OSU-CLIENT-SECRET")
AUTH_URI = 'https://osu.ppy.sh/oauth/authorize'
SCOPE = 'identify'

oauth = OAuth(app)
oauth.register(
    name = 'osu',
    client_id= CLIENT_ID,
    client_secret= CLIENT_SECRET,
    access_token_url = TOKEN_URL, 
    access_token_params=None,
    authorize_url=AUTH_URI,
    authorize_params=None,
    api_base_url=API_URL
)

def get_token():
   data = {
      'client_id': CLIENT_ID,
      'client_secret': CLIENT_SECRET,
      'grant_type': 'client_credentials',
      'scope': 'public'
   }

   response = requests.post(TOKEN_URL, data=data)

   return response.json().get('access_token')

HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f"Bearer {get_token()}"
}

def logged_in():
    return 'token' in session

@app.route('/')
@app.route('/index.html')
def root():
    return flask.render_template('index.html', login=logged_in())

@app.route('/aboutus.html')
def about_page():
    return flask.render_template('aboutus.html', login=logged_in())

@app.route('/login')
def login():
    if 'token' in session:
        return flask.redirect('/logout')

    redirect_uri = flask.url_for('authorize', _external=True)
    return oauth.osu.authorize_redirect(redirect_uri)

@app.route("/authorize", methods=["GET"])
def authorize():
    osu = oauth.create_client('osu')
    token = osu.authorize_access_token()['access_token']
    session['token'] = token
    session['username'] = get_self(token)['username']
    return flask.redirect('/')

@app.route('/logout')
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return flask.redirect('/')

def get_self(token):
    """
    Gets logged in user data
    """
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f"Bearer {token}"
    }

    response = requests.get(f'{API_URL}/me/', headers=headers)
    return response.json()

def get_user(user_key):
    """
    Returns a User object which extends UserCompact from a user key which can be a username or user ID
    """
    params = {
        'key': {user_key}
    }
    
    response = requests.get(f'{API_URL}/users/{user_key}', params=params, headers=HEADERS)
    return response.json()

@app.route('/get-comments', methods=['GET'])
def get_comments(user_id=None):
    """
    Gets comments list and returns it as JSON
    """
    if not user_id:
        user_id = flask.request.headers.get('user-id')
    return flask.jsonify(comment.get_comments_list(user_id))

@app.route('/create-comment', methods=['POST'])
def handle_create_comment():
    """
    Creates a comment from the given POST request and returns a comment list
    """
    body = flask.request.get_json(silent=True)
    comment_message = body['message']
    user_id = body['userID']

    # Creates a comment by currently logged in user, of a message, on a user's profile
    comment.create_comment(session['username'], comment_message, user_id)
    return get_comments(user_id)

@app.route('/get-scores', methods=['GET'])
def get_scores():
    """
    Requests user scores from osu API using given User ID in request header and returns best 100 scores by pp
    """
    user_id = flask.request.headers.get('user-id')
    params = {
        'limit': 100
    }

    response = requests.get(f'{API_URL}/users/{user_id}/scores/best', params=params, headers=HEADERS)
    user_scores = response.json() # this is not actually a json its just a python list
    return flask.jsonify(user_scores)

@app.route('/get-recent', methods=['GET'])
def get_recent():
    """
    Requests user scores from osu API using given User ID in request header and returns best 100 scores by pp
    """
    user_id = flask.request.headers.get('user-id')
    params = {
        'include_fails': 1,
        'limit': 100
    }

    response = requests.get(f'{API_URL}/users/{user_id}/scores/recent', params=params, headers=HEADERS)
    user_scores = response.json() # this is not actually a json its just a python list
    return flask.jsonify(user_scores)
    
@app.route('/get-profile')
def get_profile():
    """
    Render profile page from given username or user ID
    """
    user_key = flask.request.args['user']    
    user = get_user(user_key)

    try:
        user_id = user['id']
        username = user['username']
        return flask.render_template('profile.html', user_id=user_id, username=username, login=logged_in())
    except:
        return flask.render_template('index.html', login=logged_in())
    
    

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
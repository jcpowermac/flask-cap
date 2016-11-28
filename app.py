#!/usr/bin/env python

from docker import Client
from flask import Flask, render_template, request, session, url_for, redirect, \
    Response, abort
from flask_login import LoginManager, UserMixin, \
                                login_required, login_user, logout_user

from flask_socketio import SocketIO

import psutil
import capng
import json
import sys



DEBUG = True
SECRET_KEY = 'development key'

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKCAP_SETTINGS', silent=True)

async_mode = None

socketio = SocketIO(app, async_mode=async_mode)


# flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


pids = []

# silly user model
class User(UserMixin):

    def __init__(self, id):
        self.id = id
        self.name = "user" + str(id)
        self.password = "password"

    def __repr__(self):
        return "%d/%s/%s" % (self.id, self.name, self.password)


# create some users with ids 1 to 20
users = [User(id) for id in range(1, 21)]


def capabilities(pid):
    permitted = None

    capng.capng_setpid(pid)
    capng.capng_clear(capng.CAPNG_SELECT_BOTH)
    capng.capng_get_caps_process()
    caps = capng.capng_have_capabilities(capng.CAPNG_SELECT_CAPS)

    if caps > capng.CAPNG_NONE:
        if caps == capng.CAPNG_PARTIAL:
            permitted = capng.capng_print_caps_text(capng.CAPNG_PRINT_BUFFER, capng.CAPNG_PERMITTED)
            if capng.capng_have_capabilities(capng.CAPNG_SELECT_BOUNDS) == capng.CAPNG_FULL:
                permitted += "+"
        else:
            permitted = "full"
    return permitted


@app.route('/', methods=['GET', 'POST'])
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = "Error"
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        if password == 'password':
            id = username.split('user')[1]
            user = User(id)
            login_user(user)
            return redirect(url_for('docker'))

    return render_template('login.html', error=error)


@app.route('/docker', methods=['GET', 'POST'])
def docker():
    if request.method == "POST":
        total = 0
        current = 0
        layerids = []
        cli = Client(base_url='unix://var/run/docker.sock', version='auto')
        image = request.form["dockerimage"]
        dockerrun = request.form["dockerrun"]

        for line in cli.pull(image, tag="latest", stream=True):
            pull = json.loads(line)

            if 'id' in pull and 'progressDetail' in pull:
                id = pull['id']
                progressDetail = pull['progressDetail']
                # print(json.dumps(pull, indent=4))
                # sys.stdout.flush()
                if 'total' in progressDetail and 'current' in progressDetail:
                    if id in layerids:
                        current += pull['progressDetail']['current']
                    else:
                        layerids.append(id)
                        total += pull['progressDetail']['total']

                    # print current / total
                    # sys.stdout.flush()
                    value = current / total
                    style = "width: %d %%;" % value
                    socketio.emit('aria-valuenow', {'style': style, 'value': value }, namespace='')

                #socketio.emit('dockerpull', {'data': json.dumps(pull)}, namespace='')
        container = cli.create_container(image=image)
        container_id = container['Id']
        cli.start(container_id)
        socketio.sleep(10)
        pids = cli.top(container_id)
        print pids
        return redirect(url_for('results'))
    return render_template('docker.html', async_mode=socketio.async_mode)


@app.route('/results')
def results():
    results = []
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=['ppid', 'pid', 'name', 'username', 'uids', 'gids'])
        except psutil.NoSuchProcess:
            pass
        else:
            capstext = capabilities(pinfo["pid"])
            if capstext is not None:
                pinfo["capabilities"] = capstext
                results.append(pinfo)

    return render_template('results.html', results=results)


# somewhere to logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return Response('<p>Logged out</p>')


# handle login failed
@app.errorhandler(401)
def page_not_found(e):
    return Response('<p>Login failed</p>')


# callback to reload the user object
@login_manager.user_loader
def load_user(userid):
    return User(userid)


if __name__ == '__main__':
    socketio.run(app, debug=True)

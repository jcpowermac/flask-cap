#!/usr/bin/env python

from flask import Flask, render_template, request, session, url_for, redirect, \
    Response, abort
from flask_login import LoginManager, UserMixin, \
                                login_required, login_user, logout_user
import psutil
import capng

DEBUG = True
SECRET_KEY = 'development key'

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKCAP_SETTINGS', silent=True)

# flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


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
            return redirect(url_for('results'))

    return render_template('login.html', error=error)

@app.route('/results')
@login_required
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
    app.run()

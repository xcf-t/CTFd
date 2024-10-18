from flask import redirect, render_template, request, session, url_for
from werkzeug.exceptions import Forbidden
from CTFd.plugins import bypass_csrf_protection
from CTFd.models import UserFieldEntries, Users, UserFields, db
from CTFd.utils import get_app_config, get_config
from CTFd.utils.logging import log
from CTFd.utils.security.auth import login_user, logout_user
from CTFd.utils.helpers import error_for
from urllib.parse import urlencode
from os import urandom
import jwt

def load(app):
    #print(app.view_functions)

    @bypass_csrf_protection
    @app.route('/moodle/start', methods=['POST'])
    def auth_start():
        print(request.form)
        print(session)

        login_hint = request.form.get("login_hint")
        message_hint = request.form.get("lti_message_hint")

        if str(login_hint) == "0":
            course_url = get_app_config("MOODLE_COURSE_URL") or get_config("moodle_course_url")
            return redirect(course_url)

        nonce = urandom(14).hex()
        session['lti_state'] = urandom(14).hex()

        client_id = get_app_config("MOODLE_CLIENT_ID") or get_config("moodle_client_id")
        auth_url = get_app_config("MOODLE_AUTH_URL") or get_config("moodle_auth_url") or "https://moodle.ruhr-uni-bochum.de/mod/lti/auth.php"
        
        if client_id is None:
            abort(500, "Invalid client id")

        params = {
            "client_id": client_id,
            "login_hint": login_hint,
            "lti_message_hint": message_hint,
            "nonce": nonce,
            "scope": "openid",
            "response_mode": "form_post",
            "response_type": "id_token",
            "redirect_uri": "http://localhost/moodle/callback",
            "state": session['lti_state']
        }

        return redirect(f"{auth_url}?{urlencode(params)}")


    @bypass_csrf_protection
    @app.route('/moodle/callback', methods=['POST'])
    def auth_redirect():
        id_token = request.form.get("id_token")
        state = request.form.get("state")

        print(id_token)

        # TODO: Fix security issue :)
        #if session["lti_state"] != state:
        #    log("logins", "[{date}] {ip} - OAuth State validation mismatch")
        #    error_for(endpoint="auth.login", message="OAuth State validation mismatch.")
        #    return redirect(url_for("auth.login"))

        if not id_token:
            log("logins", "[{date}] {ip} - Received redirect without id token")
            error_for(
                endpoint="auth.login", message="Received redirect without id token."
            )
            return redirect(url_for("auth.login"))

        client_id = get_app_config("MOODLE_CLIENT_ID") or get_config("moodle_client_id")

        if client_id is None:
            abort(500, "Invalid client id")

        PUBKEY="""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvD0PY+b3EC/oNlgKAf+t
RUErmVq1d/3rqYzFdWS2LC3lryFUIKuzHQJgmnmvJ50n7U/uD7jmUZy9+nDHU/pJ
LjdyEnllGw8Qi69uArW/F8eiPEfmdVuS3wsMgf6O36oRkLBXld/hmEgiQIppR5Jm
fZ+hPJASs88XY+YRFy4tPFA20LhmQyyRPY4ukyAtU/dxSxKjdttafaDXBimQrZaB
VcuU0SuOm4jsTRg4dVjAeDpPnzjSzUJ4vZ+2mge9t4S9lNCp0P1DBJjxIQBaEeQk
pVXT/QPMXQMJukj9s8xlx0P4sAUCjfdWzSNyLKyMYo4d4Tcfn9iB0F5M6RZzGtK5
bwIDAQAB
-----END PUBLIC KEY-----"""

        decoded = jwt.decode(id_token, PUBKEY, leeway=60, audience=client_id, algorithms=["RS256"])

        print(decoded)

        matr_nr = decoded["https://purl.imsglobal.org/spec/lti/claim/lis"]["person_sourcedid"]
        username = decoded["name"]

        if not username or not matr_nr:
            abort(400, description=f"Missing username or matrikelnummer")

        oauth_id=matr_nr
        if oauth_id.startswith("108"):
            oauth_id = oauth_id[3:]

        user = Users.query.filter_by(oauth_id=oauth_id).first()

        if user is None:
            # Respect the user count limit
            num_users_limit = int(get_config("num_users", default=0))
            num_users = Users.query.filter_by(banned=False, hidden=False).count()
            if num_users_limit and num_users >= num_users_limit:
                abort(
                    403,
                    description=f"Reached the maximum number of users ({num_users_limit}).",
                )

            field = UserFields.query.filter_by(name="Machine").first()
            if field is None:
                abort(500, description=f"Machine access is currently not configured!")
        
            # Create new user
            user = Users(
                name=username,
                oauth_id=int(oauth_id),
                verified=False,
            )

            entry = UserFieldEntries(
                type="user", value=None, user_id=user.id, field_id=field.id
            )

            db.session.add(user)
            db.session.add(entry)
            db.session.commit()

        login_user(user)

        return redirect("/")

    def auth_start():
        start_url = get_app_config("MOODLE_START_URL") or get_config("moodle_start_url")

        if start_url is None:
            abort(500, "Invalid client id")

        return redirect(start_url)

    standard_login = app.view_functions["auth.login"]
    app.view_functions["auth.login"] = auth_start


    @app.route('/admin-login', methods=['GET', 'POST'])
    def admin_auth():
        return standard_login()
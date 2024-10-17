from flask import redirect, render_template, request, session, url_for
from werkzeug.exceptions import Forbidden
from CTFd.plugins import bypass_csrf_protection
from CTFd.models import UserFieldEntries, Users, UserFields, db
from CTFd.utils import get_app_config, get_config
from CTFd.utils.security.auth import login_user, logout_user
from urllib.parse import urlencode
from os import urandom
import jwt

def load(app):
    @bypass_csrf_protection
    @app.route('/moodle/start', methods=['POST'])
    def auth_start():
        print(request.form)
        print(session)

        login_hint = request.form.get("login_hint")
        message_hint = request.form.get("lti_message_hint")

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
            "redirect_uri": "http://localhost:8000/moodle/callback",
            "state": session['lti_state']
        }

        return redirect(f"{auth_url}?{urlencode(params)}")


    @bypass_csrf_protection
    @app.route('/moodle/callback', methods=['POST'])
    def auth_redirect():
        id_token = request.form.get("id_token")
        state = request.form.get("state")

        print(session)

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

        print(id_token)

        PUBKEY="""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxGDidz93ahyiAT3P/as5
oIMqj0+oCVuVv8Cfixra0AvDtrIJmQKf316P8gB9McIB1W8Q3LykgAW6AUJkwIjK
9LVRKVIW4jAnMjzdahxuP0jexmUX9ySEW6NkhInBKT/iFdX+o7+IIZdbrEYPEJYY
oqUVJPmFAgVhTHRaiV7DSL4wXUr6iFgC/UInOUY8sHsFPV1HOQKp7ioRPd50p6np
fx6lLN5JsF7TMa5zYRC2lOeKhk+LJTmTmfsM9vMAVDxsWV+t2GEKBYLRodf1Esvj
sk7UM7TWalQJFiLvTC5AzDOlixQTAsPod0jNy9PBc2MNvC7Y3crCTCrldjmgDeps
AwIDAQAB
-----END PUBLIC KEY-----
"""

        decoded = jwt.decode(id_token, PUBKEY, audience=client_id, algorithms=["RS256"])

        print(decoded)

        matr_nr = decoded["https://purl.imsglobal.org/spec/lti/claim/lis"]["person_sourcedid"]

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
                name=matr_nr,
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
from flask import render_template, request, abort, Response, Blueprint
from CTFd.models import UserFields, UserFieldEntries, Fields, db
from CTFd.plugins import register_user_page_menu_bar, bypass_csrf_protection
from CTFd.utils.user import get_current_user
from CTFd.utils.decorators import authed_only
from CTFd.cache import cache

ssh_key_field_cache = None
machine_field_cache = None

def init_fields():
    global ssh_key_field_cache, machine_field_cache
    ssh_key_field = Fields.query.filter_by(name="SSH-Key").first()
    machine_field = Fields.query.filter_by(name="Machine").first()

    if ssh_key_field is None or machine_field is None:
        abort(500, "Machine field or SSH-Key field not present")

    ssh_key_field_cache = ssh_key_field.id
    machine_field_cache = machine_field.id

def get_ssh_key_field_id():
    global ssh_key_field_cache
    if ssh_key_field_cache is None:
        init_fields()
    return ssh_key_field_cache

def get_machine_field_id():
    global machine_field_cache
    if machine_field_cache is None:
        init_fields()
    return machine_field_cache

@cache.memoize(timeout=60)
def get_user_machine(user_id: str):
    field_id = get_machine_field_id()

    print(field_id)
    print(user_id)

    entry = UserFieldEntries.query.filter_by(field_id=field_id, user_id=user_id).first()

    if entry is None:
        return None
    return entry.value

service_ports = {
    "vscode": 80,
    "terminal": 7681
}


def load(app):
    remote = Blueprint('remote', __name__, template_folder='templates', url_prefix="/remote")

    register_user_page_menu_bar("Editor", "/remote/vscode")
    register_user_page_menu_bar("Terminal", "/remote/terminal")

    @remote.route("/vscode", methods=['GET'])
    @authed_only
    def remote_vscode():
        return render_template("vscode.html")

    @remote.route("/desktop", methods=['GET'])
    @authed_only
    def remote_desktop():
        return render_template("desktop.html")

    @remote.route("/terminal", methods=['GET'])
    @authed_only
    def remote_terminal():
        return render_template("terminal.html")

    @app.route("/api/v1/forward/<service>/", websocket=True)
    @app.route("/api/v1/forward/<service>/", methods=["GET"], defaults={'service_path': ''})
    @app.route("/api/v1/forward/<service>/<path:service_path>", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"])
    @authed_only
    @bypass_csrf_protection
    def remote_forward(service: str, service_path: str):
        if service not in service_ports:
            abort(404)

        prefix = f"/api/v1/forward/{service}"
        path = request.full_path
        
        if not path.startswith(prefix):
            abort(403)
        path = path[len(prefix):]
        if path.startswith("/"):
            path = path[1:]


        user = get_current_user()
        machine = get_user_machine(user.id)
        port = service_ports[service]

        print(f"http://{machine}:{port}/{path}")

        # TODO: fancy error message
        if machine is None:
            abort(400)


        response = Response()
        response.headers["X-Accel-Redirect"] = "@forward"
        response.headers["redirect_uri"] = f"http://{machine}:{port}/{path}"
        return response

    print(app.url_map)
    print(app.view_functions["api.users_user_private"])

    ### Hook user update to catch ssh key changes
    user_update_original = app.view_functions["api.users_user_private"]
    def user_update_hook():
        global ssh_key_field_cache, machine_field_cache
        if request.method != "PATCH":
            return user_update_original()

        if ssh_key_field_cache is None or machine_field_cache is None:
            ssh_key_field = Fields.query.filter_by(name="SSH-Key").first()
            machine_field = Fields.query.filter_by(name="Machine").first()

            if ssh_key_field is None or machine_field is None:
                abort(500, "Machine field or SSH-Key field not present")

            ssh_key_field_cache = ssh_key_field.id
            machine_field_cache = machine_field.id

        result = user_update_original()
        
        if result.status_code == 200:
            # TODO: simplify this
            user = get_current_user()
            entries = UserFieldEntries.query.filter_by(user_id=user.id).all()
            target_machine = None
            target_ssh_key = None

            for field in entries:
                if field.field_id == ssh_key_field_cache:
                    target_ssh_key = field.value
                if field.field_id == machine_field_cache:
                    target_machine = field.value

            if target_machine is None or target_ssh_key is None:
                return result
            
            print(f"Machine: {target_machine}")
            print(f"SSH-Key: {target_ssh_key}")

            # TODO: Verify ssh key and prevent shell injection [A-Za-z0-9=/@ ]

            #client = SSHClient()
            #client.load_system_host_keys()
            #client.connect(target_machine)
            #stdin, stdout, stderr = client.exec_command(f"echo /usr/bin/setup_ssh_key.sh '{target_ssh_key}'")

            # TODO: Deploy here

        return result

    app.view_functions["api.users_user_private"] = user_update_hook


    app.register_blueprint(remote)
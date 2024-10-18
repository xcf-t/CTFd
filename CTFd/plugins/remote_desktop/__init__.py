from flask import render_template, request, abort, Response, Blueprint
from CTFd.plugins import register_user_page_menu_bar, bypass_csrf_protection
from CTFd.utils.decorators import authed_only

def load(app):
    remote = Blueprint('remote', __name__, template_folder='templates', url_prefix="/remote")

    register_user_page_menu_bar("Desktop", "/remote/desktop")
    register_user_page_menu_bar("Editor", "/remote/vscode")

    @remote.route("/vscode", methods=['GET'])
    @authed_only
    def remote_vscode():
        return render_template("vscode.html")

    @remote.route("/desktop", methods=['GET'])
    @authed_only
    def remote_desktop():
        return render_template("desktop.html")

    @remote.route("/vscode-forward", methods=["GET"])
    @remote.route("/vscode-forward/", websocket=True)
    @remote.route("/vscode-forward/<path:service_path>", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"])
    @authed_only
    @bypass_csrf_protection
    def remote_forward(service_path=""):
        prefix = "/remote/vscode-forward"
        path = request.full_path
        print(path)
        if not path.startswith(prefix):
            abort(403)
        path = path[len(prefix):]
        if path.startswith("/"):
            path = path[1:]

        response = Response()
        response.headers["X-Accel-Redirect"] = "@forward"
        response.headers["redirect_uri"] = f"http://whoami/{path}"
        return response



    app.register_blueprint(remote)
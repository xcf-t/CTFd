from flask import Blueprint

from CTFd.models import Challenges, Solves, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.plugins.migrations import upgrade
from CTFd.utils.user import authed, get_current_user
import json

class TutorialChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "tutorial"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )

    def __init__(self, *args, **kwargs):
        super(TutorialChallenge, self).__init__(**kwargs)


class TutorialValueChallenge(BaseChallenge):
    id = "tutorial"  # Unique identifier used to register challenges
    name = "tutorial"  # Name of a challenge type
    templates = (
        {  # Handlebars templates used for each aspect of challenge editing & viewing
            "create": "/plugins/tutorial_challenges/assets/create.html",
            "update": "/plugins/tutorial_challenges/assets/update.html",
            "view": "/plugins/tutorial_challenges/assets/view.html",
        }
    )
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/tutorial_challenges/assets/create.js",
        "update": "/plugins/tutorial_challenges/assets/update.js",
        "view": "/plugins/tutorial_challenges/assets/view.js",
    }
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = "/plugins/tutorial_challenges/assets/"
    # Blueprint used to access the static_folder directory.
    blueprint = Blueprint(
        "tutorial_challenges",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = TutorialChallenge

    @classmethod
    def read(cls, challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.

        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """
        return super().read(challenge)

    @classmethod
    def update(cls, challenge, request):
        """
        This method is used to update the information associated with a challenge. This should be kept strictly to the
        Challenges table and any child tables.

        :param challenge:
        :param request:
        :return:
        """
        return super().update(challenge, request)

    @classmethod
    def solve(cls, user, team, challenge, request):
        super().solve(user, team, challenge, request)


def load(app):
    upgrade(plugin_name="tutorial_challenges")
    CHALLENGE_CLASSES["tutorial"] = TutorialValueChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/tutorial_challenges/assets/"
    )

    #print(app.view_functions)

    """
    standard_attempt = app.view_functions["api.challenges_challenge_attempt"]

    def challenge_attempt_wrapper():
        result = standard_attempt()
        if json.loads(result.get_data(True))["data"]["status"] == "already_solved":
            if not request.is_json:
                request_data = request.form
            else:
                request_data = request.get_json()

            challenge_id = request_data.get("challenge_id")

            challenge = Challenges.query.filter_by(id=challenge_id).first_or_404()

            if challenge.type != "tutorial":
                return result


            user = get_current_user()

            solve = Solves.query.filter_by(
                account_id=user.account_id, challenge_id=challenge_id
            ).first()

            db.session.delete(solve)
            
            return {
                "success": True,
                "data": {"status": "correct", "message": "Marked as unsolved!"},
            }
        return result

    app.view_functions["api.challenges_challenge_attempt"] = challenge_attempt_wrapper
    """
CTFd._internal.challenge.data = undefined;

// TODO: Remove in CTFd v4.0
CTFd._internal.challenge.renderer = null;

CTFd._internal.challenge.preRender = function() {};

// TODO: Remove in CTFd v4.0
CTFd._internal.challenge.render = null;

function fixButton() {
  if (!document.querySelector("div[class='row submit-row'] > div[class*='key-submit']"))
    return requestAnimationFrame(fixButton);

  document.querySelector("div[class='row submit-row'] > div[class*='key-submit']").classList.remove("col-sm-4");
  document.querySelector("div[class='row submit-row'] > div[class*='key-submit']").classList.remove("mt-3");
  document.querySelector("div[class='row submit-row'] > div[class*='key-submit']").classList.remove("mt-sm-0");
  document.querySelector("div[class='row submit-row'] > div[class='col-12 col-sm-8']").style.display='none';
}

CTFd._internal.challenge.postRender = function() {
  requestAnimationFrame(fixButton)
};

CTFd._internal.challenge.submit = function(preview) {
  var challenge_id = parseInt(CTFd.lib.$("#challenge-id").val());
  var submission = CTFd.lib.$("#challenge-input").val();

  var body = {
    challenge_id: challenge_id,
    submission: submission
  };
  var params = {};
  if (preview) {
    params["preview"] = true;
  }

  return CTFd.api.post_challenge_attempt(params, body).then(function(response) {
    if (response.status === 429) {
      // User was ratelimited but process response
      return response;
    }
    if (response.status === 403) {
      // User is not logged in or CTF is paused.
      return response;
    }
    return response;
  });
};

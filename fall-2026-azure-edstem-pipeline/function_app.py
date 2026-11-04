import azure.functions as func
import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

app = func.FunctionApp()


EDSTEM_API_BASE_URL = "https://us.edstem.org/api/courses"


@app.route(route="edstem/threads", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def get_edstem_threads(req: func.HttpRequest) -> func.HttpResponse:
    """Fetch a course's threads from EdStem.

    The API token is intentionally read only from application settings, never
    from the incoming request. The course ID can be sent as ``?course_id=...``
    (for example, from an ADF pipeline parameter), or configured through the
    ``EDSTEM_COURSE_ID`` application setting.
    """
    token = os.environ.get("EDSTEM_API_TOKEN")
    if not token:
        logging.error("EDSTEM_API_TOKEN application setting is not configured.")
        return func.HttpResponse(
            json.dumps({"error": "EdStem API token is not configured."}),
            status_code=500,
            mimetype="application/json",
        )

    course_id = req.params.get("course_id") or os.environ.get("EDSTEM_COURSE_ID")
    if not course_id or not course_id.isdecimal():
        return func.HttpResponse(
            json.dumps(
                {
                    "error": (
                        "A numeric course_id query parameter or "
                        "EDSTEM_COURSE_ID application setting is required."
                    )
                }
            ),
            status_code=400,
            mimetype="application/json",
        )

    edstem_request = Request(
        f"{EDSTEM_API_BASE_URL}/{course_id}/threads",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(edstem_request, timeout=30) as edstem_response:
            response_body = edstem_response.read()
            return func.HttpResponse(
                response_body,
                status_code=edstem_response.status,
                mimetype="application/json",
            )
    except HTTPError as error:
        # EdStem's status is useful to ADF, but its detailed body may contain
        # information that should not be relayed through this integration.
        logging.warning("EdStem returned HTTP %s.", error.code)
        return func.HttpResponse(
            json.dumps({"error": "EdStem request failed.", "status": error.code}),
            status_code=error.code,
            mimetype="application/json",
        )
    except URLError as error:
        logging.exception("Could not reach EdStem: %s", error.reason)
        return func.HttpResponse(
            json.dumps({"error": "Could not reach EdStem."}),
            status_code=502,
            mimetype="application/json",
        )

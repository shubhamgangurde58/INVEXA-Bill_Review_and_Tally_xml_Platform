from flask import jsonify


# Build every success reply in one shape so the React side can always read
# response.data.status and response.data.data without special cases.
def success(data=None, status_code=200):
    body = {"status": "success", "data": data}
    return jsonify(body), status_code


# Build every error reply in one shape. Keep the message generic, because
# detailed messages (like "email not found") help attackers guess accounts.
def error(message, status_code=400):
    body = {"status": "error", "message": message}
    return jsonify(body), status_code


# Turn a service result into the standard reply. Services return either
# (data, None) or (None, (message, status_code)), so routes stay tiny.
def respond(result, problem, success_status=200):
    if problem is not None:
        return error(problem[0], problem[1])
    return success(result, success_status)

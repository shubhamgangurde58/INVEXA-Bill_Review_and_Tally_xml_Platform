import json
import os
import secrets
import sys
import urllib.error
import urllib.request

from config import Config
from extensions import db

BASE_URL = "http://127.0.0.1:5000"
results = []


# Send one HTTP request to the running server and return (status, json).
# urllib raises an error for 4xx replies, so we catch it and read the body
# anyway, because the 4xx replies are exactly what we want to check.
def call(method, path, body=None, token=None):
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    if token is not None:
        headers["Authorization"] = "Bearer " + token

    request = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as reply:
            return reply.status, json.loads(reply.read().decode("utf-8"))
    except urllib.error.HTTPError as problem:
        return problem.code, json.loads(problem.read().decode("utf-8"))


# Record and print one PASS or FAIL line.
def check(name, condition, detail=""):
    results.append(condition)
    if condition:
        print("PASS  " + name)
    else:
        print("FAIL  " + name + "   -> " + str(detail))


# Run the checks against the live server and the demo data from seed_demo.py.
# Login is limited to 5 tries per 15 minutes, and this script uses 4, so
# restart the server before running it a second time.
def main():
    password = os.getenv("DEMO_PASSWORD", "")
    if len(password) < 8:
        print("DEMO_PASSWORD is missing in .env")
        sys.exit(1)

    firm = db.firms.find_one({"name": "Kulkarni and Associates"})
    if firm is None:
        print("Run seed_demo.py first.")
        sys.exit(1)

    status, body = call("GET", "/api/health")
    check("server is up", status == 200, body)

    status, body = call("POST", "/api/auth/login",
                        {"email": "ca.kulkarni@demo.invexa.test", "password": password, "role": "ca"})
    check("demo CA can log in", status == 200 and body["data"]["user"]["role"] == "ca", body)
    token = body["data"]["token"] if status == 200 else ""

    status, body = call("GET", "/api/auth/me", token=token)
    check("me returns the CA and firm name", status == 200 and body["data"]["firm_name"] == "Kulkarni and Associates", body)

    status, body = call("GET", "/api/auth/me")
    check("me without a token is refused (401)", status == 401, body)

    status, wrong = call("POST", "/api/auth/login",
                         {"email": "ca.kulkarni@demo.invexa.test", "password": "Wrong#Pass1", "role": "ca"})
    status2, unknown = call("POST", "/api/auth/login",
                            {"email": "nobody@demo.invexa.test", "password": "Wrong#Pass1", "role": "ca"})
    check("wrong password and unknown email give the same message", status == 401 and wrong == unknown, (wrong, unknown))

    status, body = call("POST", "/api/auth/signup-ca", {
        "firm_name": "Test Firm", "name": "Test CA", "email": "weak@demo.invexa.test",
        "membership_number": "111111", "password": "weak"})
    check("weak password is rejected", status == 400, body)

    status, body = call("POST", "/api/auth/login", {"email": {"$ne": ""}, "password": {"$ne": ""}, "role": "ca"})
    check("NoSQL injection attempt is blocked", status == 400, body)

    client_form = {
        "invite_code": firm["invite_code"], "business_name": "Smoke Test Store", "owner_name": "Smoke Tester",
        "email": "smoke." + secrets.token_hex(4) + "@demo.invexa.test", "mobile": "9999900000",
        "password": password,
    }
    status, body = call("POST", "/api/auth/signup-client", {**client_form, "invite_code": "NOPE-00000"})
    check("wrong invite code is refused", status == 400, body)

    status, body = call("GET", "/api/auth/invite-lookup?code=" + firm["invite_code"])
    check("invite lookup shows the firm name", status == 200 and body["data"]["firm_name"] == firm["name"], body)

    status, body = call("POST", "/api/auth/signup-client", client_form)
    check("new client signs up as pending", status == 201 and body["data"]["user"]["status"] == "pending", body)

    status, body = call("POST", "/api/auth/login",
                        {"email": client_form["email"], "password": password, "role": "client"})
    check("pending client can log in", status == 200 and body["data"]["user"]["status"] == "pending", body)

    passed = sum(1 for result in results if result)
    print("")
    print(str(passed) + " / " + str(len(results)) + " checks passed")
    print("Check the server console for the [DEV ONLY] verify-email link of the new client.")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()

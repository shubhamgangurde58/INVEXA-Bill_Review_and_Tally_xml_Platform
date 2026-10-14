import base64
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

from config import Config
from extensions import db

BASE_URL = "http://127.0.0.1:5000"
results = []

# A real 1x1 PNG picture, so the upload passes the "file content must match
# its type" check without needing any image library.
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


# Send one request and return (status, headers, raw_bytes). 4xx and 5xx
# replies are returned too instead of raising, because we want to check them.
def send(method, path, body=None, token=None, content_type="application/json"):
    headers = {}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(BASE_URL + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as reply:
            return reply.status, reply.headers, reply.read()
    except urllib.error.HTTPError as problem:
        return problem.code, problem.headers, problem.read()


# Send a JSON request and return (status, parsed_json).
def call(method, path, body=None, token=None):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    status, _, raw = send(method, path, data, token)
    return status, json.loads(raw.decode("utf-8"))


# Upload a file as multipart/form-data and return (status, parsed_json).
def upload(path, token, file_bytes, file_name="smoke.png", mime="image/png"):
    boundary = uuid.uuid4().hex
    head = ("--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\""
            + file_name + "\"\r\nContent-Type: " + mime + "\r\n\r\n").encode("utf-8")
    body = head + file_bytes + ("\r\n--" + boundary + "--\r\n").encode("utf-8")
    status, _, raw = send("POST", path, body, token, "multipart/form-data; boundary=" + boundary)
    return status, json.loads(raw.decode("utf-8"))


# Record and print one PASS or FAIL line.
def check(name, condition, detail=""):
    results.append(bool(condition))
    if condition:
        print("PASS  " + name)
    else:
        print("FAIL  " + name + "   -> " + str(detail)[:300])


# Log in and return the token (or "" on failure).
def login(email, password, role):
    status, body = call("POST", "/api/auth/login", {"email": email, "password": password, "role": role})
    if status != 200:
        return ""
    return body["data"]["token"]


# Run the Phase 4 checks against the live server and the demo data.
# Needs seed_demo.py to have run. It approves the pending demo client,
# uploads one bill as that client, then checks the CA can see and download
# it and that the other firm cannot. It uses 3 of the 5 allowed logins, so
# restart the server before running it again. Run seed_demo.py afterwards to
# reset the demo data.
def main():
    password = os.getenv("DEMO_PASSWORD", "")
    firm = db.firms.find_one({"name": "Kulkarni and Associates"})
    if firm is None or len(password) < 8:
        print("Run seed_demo.py first and set DEMO_PASSWORD in .env")
        sys.exit(1)

    ca_token = login("ca.kulkarni@demo.invexa.test", password, "ca")
    check("Kulkarni CA logs in", ca_token != "")

    status, body = call("GET", "/api/firm/get-profile", token=ca_token)
    check("firm profile shows the invite code", status == 200 and body["data"]["invite_code"] == firm["invite_code"], body)

    status, body = call("GET", "/api/firm/list-join-requests", token=ca_token)
    pending = [row for row in body["data"]["clients"] if row["email"] == "client4.kulkarni@demo.invexa.test"]
    check("join requests list loads", status == 200, body)

    if len(pending) == 1:
        status, body = call("POST", "/api/firm/approve-client/" + pending[0]["id"], token=ca_token)
        check("CA approves the pending client", status == 200 and body["data"]["status"] == "active", body)

    client_token = login("client4.kulkarni@demo.invexa.test", password, "client")
    check("approved client logs in", client_token != "")

    status, body = call("GET", "/api/firm/get-profile", token=client_token)
    check("client cannot open the firm profile (403)", status == 403, body)

    status, body = upload("/api/client/upload-invoice", client_token, TINY_PNG)
    check("client uploads a bill", status == 201 and body["data"]["status"] == "uploaded", body)
    invoice_id = body["data"]["id"] if status == 201 else ""

    status, body = upload("/api/client/upload-invoice", client_token, b"not an image", "fake.png")
    check("fake PNG is refused", status == 400, body)

    status, body = call("GET", "/api/client/list-my-invoices", token=client_token)
    check("client sees the bill in their list", status == 200 and any(row["id"] == invoice_id for row in body["data"]["invoices"]), body)

    status, body = call("GET", "/api/invoice/list-firm-invoices?status=uploaded", token=ca_token)
    check("CA sees the bill in the firm list", status == 200 and any(row["id"] == invoice_id for row in body["data"]["invoices"]), body)

    status, body = call("GET", "/api/invoice/get-by-id/" + invoice_id, token=ca_token)
    check("CA opens the bill detail", status == 200 and body["data"]["id"] == invoice_id, body)

    status, headers, raw = send("GET", "/api/invoice/get-file/" + invoice_id + "?token=" + ca_token)
    check("CA downloads the file (same bytes, image/png)", status == 200 and raw == TINY_PNG and headers.get_content_type() == "image/png", status)

    other_token = login("ca.mehta@demo.invexa.test", password, "ca")
    status, body = call("GET", "/api/invoice/get-by-id/" + invoice_id, token=other_token)
    check("the OTHER firm's CA cannot open it (404)", status == 404, body)
    status, _, _ = send("GET", "/api/invoice/get-file/" + invoice_id, token=other_token)
    check("the OTHER firm's CA cannot download it (404)", status == 404, status)
    status, body = call("GET", "/api/invoice/list-firm-invoices", token=other_token)
    check("the OTHER firm's list does not contain it", status == 200 and all(row["id"] != invoice_id for row in body["data"]["invoices"]), body)

    status, body = call("POST", "/api/firm/regenerate-invite-code", token=ca_token)
    check("CA regenerates the invite code", status == 200 and body["data"]["invite_code"] != firm["invite_code"], body)
    status, body = call("GET", "/api/auth/invite-lookup?code=" + firm["invite_code"])
    check("the old invite code no longer works", status == 404, body)

    passed = sum(1 for result in results if result)
    print("")
    print(str(passed) + " / " + str(len(results)) + " checks passed")
    print("Run python seed_demo.py to reset the demo data.")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()

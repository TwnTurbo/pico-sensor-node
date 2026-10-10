import urequests as requests
import json, time
import secrets

_token = None
_token_time = 0

def _sign_in():
    global _token, _token_time
    url = ("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key="
           + secrets.FB_API_KEY)
    body = json.dumps({"email": secrets.FB_EMAIL,
                       "password": secrets.FB_PASSWORD,
                       "returnSecureToken": True})
    r = requests.post(url, data=body, headers={"Content-Type": "application/json"})
    data = r.json()
    r.close()
    if "idToken" not in data:
        raise Exception("Firebase sign-in failed: " + str(data.get("error", data)))
    _token = data["idToken"]
    _token_time = time.time()
    print("Firebase signed in")

def _get_token() -> str:
    if _token is None or time.time() - _token_time > 50 * 60:
        _sign_in()
    assert _token is not None
    return _token

def send(device, t, h, l):
    reading = json.dumps({"t": t, "h": h, "l": l,
                          "ts": {".sv": "timestamp"}})  # Firebase fills in the time
    base = secrets.FB_DB_URL + "/devices/" + device
    auth = "?auth=" + _get_token()

    r = requests.post(base + "/readings.json" + auth, data=reading)  # add to history
    ok = r.status_code == 200
    r.close()

    r = requests.put(base + "/latest.json" + auth, data=reading)     # overwrite latest
    r.close()
    return ok
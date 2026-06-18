import requests
try:
    res = requests.post("http://127.0.0.1:8000/api/route/1")
    print("Status Code:", res.status_code)
    print("Response Body:", res.text)
except Exception as e:
    print(e)

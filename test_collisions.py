import requests

for i in range(30):
    response = requests.post(
        "http://127.0.0.1:8000/shorten",
        params={"long_url": "https://google.com"}
    )
    print(i, response.json())
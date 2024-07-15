# Copyright IBM Corp. 2023
from fastapi.testclient import TestClient

from context import main
from dotenv import load_dotenv
import os

load_dotenv()

client = TestClient(main.app)


def test_hello_post():

    response = client.post(
        "/hello"
    )
    print(response)

    print(response.json())

def test_hello_get():

    response = client.get(
        "/hello"
    )

    print(response)

    print(response.json())


test_hello_post()
test_hello_get()
# Copyright IBM Corp. 2024
from fastapi import APIRouter
from typing import Annotated
from fastapi import Depends


app = APIRouter(
    prefix="",
    tags=["hello"],
    responses={404 : {"description": "Not Found"}},
)

# Flight Plan API Methods
@app.post("/hello")
def hello():
     return "hello python post"

@app.get("/hello")
def hello():
     return "hello python get"
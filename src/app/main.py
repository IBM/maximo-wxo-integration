# Copyright IBM Corp. 2024
from typing import Annotated, Union
from fastapi import Depends,FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
import urllib
import json
import http.client
import requests
from random import randint, randrange
from datetime import date
import os
from routers import hello

maximo_server = os.environ['MAXIMO_SERVER_ENV']

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "fakehashedsecret",
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": True,
    },
}

# API intitialisation
app = FastAPI()

def fake_hash_password(password: str):
    return "fakehashed" + password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User(BaseModel):
    username: str
    email: Union[str, None] = None
    full_name: Union[str, None] = None
    disabled: Union[bool, None] = None

class UserInDB(User):
    hashed_password: str

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def fake_decode_token(token):
    # This doesn't provide any security at all
    # Check the next version
    user = get_user(fake_users_db, token)
    return user

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = fake_decode_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    user = UserInDB(**user_dict)
    hashed_password = fake_hash_password(form_data.password)
    if not hashed_password == user.hashed_password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    return {"access_token": user.username, "token_type": "bearer"}


@app.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user


async def print_request(request):
    print(f'request header       : {dict(request.headers.items())}' )
    print(f'request query params : {dict(request.query_params.items())}')  
    try : 
        print(f'request json         : {await request.json()}')
    except Exception as err:
        # could not parse json
        print(f'request body         : {await request.body()}')

@app.get("/get_unhealthy_assets")
async def get_unhealthy_assets(
    current_user: Annotated[User, Depends(get_current_active_user)],    
    x_access_token
):
    
    print("Value="+x_access_token)

    s = requests.Session()

    who_am_i_query = "/maximo/oslc/whoami"
    url = "https://" + maximo_server + who_am_i_query

    headers = {
        'content-type': "application/json",
        'accept': "application/json",
        'x-access-token': x_access_token
    }

    print(url)
    r = s.get(url,headers=headers)
    print("------")
    print(r.text)
    print("------")
    print(r.status_code)


    query = "/maximo/api/os/mxapiasset?oslc.select=assetuid,assetnum,siteid,estendoflife,age,assettype,assettype_description,siteid,description,location,age,ahscore.value,ahmethodology.msg,ahscore_criticality.value,ahscore_criticality.msgvalue,ahscore_effectiveage.value,ahscore_effectiveage.msgvalue,ahscore_risk.value,ahscore_risk.msgvalue,ahscore_eol.value,ahscore_eol.msgvalue&oslc.pageSize=20&oslc.where=(ahscore_risk.value%3E70%20and%20ahscore_risk.value%3C=100%20and%20ahscore_criticality.value%3E60%20and%20ahscore_criticality.value%3C=100)&savedQuery=AHALLASSETS&oslc.orderBy%3D%2Bassetnum&searchAttributes=assetnum,assettype,location&collectioncount=1&ignorecollectionref=1&relativeuri=1&addschema=1&ctx=timerangestart=2024-01-01,timerangeend=20241-01-01&lean=1&internalvalues=1"
    query = query.replace(" ", "%20")

    url = "https://" + maximo_server + query

    headers = {
        'content-type': "application/json",
        'accept': "application/json"
    }

    print(url)
    r = s.get(url,headers=headers)
    print("------")
    print(r.text)
    print("------")
    print(r.status_code)

    json_unhealthy_assets = json.loads(r.text)

    member = json_unhealthy_assets['member']

    assets = ""
    jsonAssets = {"assets":[]}
    jsonAssetString = ""
    jsonAssetUIDString = ""
    #assets = assets + "<table border='1'><tr><th width='40%'>Asset</th><th width='30%'>Asset Number</th><th width='30%'>Age</th></tr>"
    for asset in member:
        assets= assets + "Asset: <a href='https://" + maximo_server + "/maximo/oslc/graphite/manage-shell/index.html?event=loadapp&value=asset&uniqueid=" + str(asset['assetuid']) + "'>" + str(asset['assetnum']) + "</a><br/>Description: " + asset['description'] + "<br/>Asset Number: " + asset['assetnum'] + "<br/>Risk Score: " + str(asset['ahscore_risk']['value']) + "<br/>Criticality Score: " + str(asset['ahscore_criticality']['value']) + "<br/><br/>"
        jsonAsset = {"assetnum" : asset['assetnum'],"description" : asset['description'],"risk_score": asset['ahscore_risk']['value'],"risk_criticality": asset['ahscore_criticality']['value']}
        jsonAssets["assets"].append(jsonAsset)
        if jsonAssetString == "":
            jsonAssetString = str(asset['assetnum'])
        else:
            jsonAssetString = jsonAssetString + "," + str(asset['assetnum'])
        if jsonAssetUIDString == "":
            jsonAssetUIDString = str(asset['assetuid'])
        else:
            jsonAssetUIDString = jsonAssetUIDString + "," + str(asset['assetuid'])

    #assets = assets + "</table>"

    print({"displayResult" : assets, "jsonResult": str(jsonAssets), "jsonResultAssetString": jsonAssetString, "jsonResultAssetUIDString": jsonAssetUIDString})

    return  {"displayResult" : assets, "jsonResult": str(jsonAssets), "jsonResultAssetString": jsonAssetString, "jsonResultAssetUIDString": jsonAssetUIDString}


@app.get("/create_work_order")
async def create_work_order(
    current_user: Annotated[User, Depends(get_current_active_user)],
    asset_number,
    description
):
    
    conn = http.client.HTTPSConnection(maximo_server)

    payload = '{"description":"' + description + '","siteid":"BEDFORD","assetnum":"'+str(asset_number)+'"}'
    print(payload)

    headers = {
        'transactionid': randint(10000,30000),
        'content-type': "application/json",
        'apikey': maximo_apikey,
        'accept': "application/json",
        'properties' : "wonum,siteid"
        }

    conn.request("POST", "/maximo/api/os/mxapiwo?lean=1", payload, headers)

    res = conn.getresponse()
    data = res.read()

    json_work_orders = json.loads(data)

    print(json_work_orders)

    wonum = json_work_orders['wonum']
    siteid = json_work_orders['siteid']    


    resp = "The following work order has been created<br/><br/>Work Order Number : <a target='_blank' href='http://" + maximo_server + "/maximo/ui/maximo.jsp?event=loadapp&value=wotrack&additionalevent=useqbe&additionaleventvalue=wonum=" + str(wonum) + "'>" + str(wonum) + "</a><br/>Description : " + str(description)

    return {"result" : resp }


async def get_work_orders_for_asset(asset_number):

    conn = http.client.HTTPSConnection(maximo_server)

    payload = ''

    headers = {
        'content-type': "*.*",
        'apikey': maximo_apikey,
        'accept': "application/json"
        }

    query='/maximo/api/os/mxapiwo?lean=1&oslc.where=(assetnum="' + str(asset_number)+'")&oslc.select=assetnum,description,wonum'

    conn.request("GET", query, headers=headers)

    res = conn.getresponse()
    data = res.read()

    json_work_orders = json.loads(data)

    member = json_work_orders['member']

    json_work_orders = {"work_orders":[]}
    if member:
        for work_order in member:
            try:
                json_work_order = {"wonum" : work_order['wonum'],"description" : work_order['description'],"assetnum": work_order['assetnum']}
            except KeyError:
                json_work_order = {"wonum" : work_order['wonum'],"description" : "","assetnum": work_order['assetnum']}
            json_work_orders["work_orders"].append(json_work_order)

    return json_work_orders


@app.get("/check_asset_for_work_orders")
async def check_asset_for_work_orders(
    current_user: Annotated[User, Depends(get_current_active_user)],
    asset_number
):
    json_work_orders = get_work_orders_for_asset(asset_number)

    work_orders = json_work_orders['work_orders']

    work_orders_display = ""
    if work_orders:
        work_orders_display = work_orders_display + "<table border='1'><tr><th>WoNum</th><th>Description</th><th>AssetNo</th></tr>"
        for work_order in work_orders:
            work_orders_display = work_orders_display + "<tr><td>" + work_order['wonum'] + "</td><td>" + work_order['description'] + "</td><td>" + work_order['assetnum'] + "</td></tr>"        
        work_orders_display = work_orders_display + "</table>"

    result = { "displayResult" : work_orders_display, "jsonResult" : str(json_work_orders)}

    return result


@app.get("/check_multiple_assets_for_work_orders")
async def check_multiple_assets_for_work_orders(
    current_user: Annotated[User, Depends(get_current_active_user)],
    comma_separated_asset_list,
    comma_separated_asset_uid_list
):

    assetNumbers = comma_separated_asset_list.split(",")
    assetUIDNumbers = comma_separated_asset_uid_list.split(",")
    print(assetNumbers)
    print(assetUIDNumbers)
    work_orders_display = ""
    assets_no_work_orders = []
    for assetIndex, asset in enumerate(assetNumbers):
        print(asset)
        json_work_orders = await get_work_orders_for_asset(asset)    
        if json_work_orders:
            work_orders = json_work_orders['work_orders']

            if work_orders:
                work_orders_display = work_orders_display + "<b>Work Orders for Asset <a target='_blank' href='https://" + maximo_server + "/maximo/oslc/graphite/manage-shell/index.html?event=loadapp&value=asset&uniqueid=" + assetUIDNumbers[assetIndex]+ "'>" + asset + "</a></b><br/>"
                work_orders_display = work_orders_display + "<ul>"                
                for work_order in work_orders:

                    work_orders_display = work_orders_display + "<li><b>Work Order Number:</b> <a target='_blank' href='http://" + maximo_server + "/maximo/ui/maximo.jsp?event=loadapp&value=wotrack&additionalevent=useqbe&additionaleventvalue=wonum=" + work_order['wonum'] + "'>" + work_order['wonum'] + "</a><br/><b>Description:</b> " + work_order['description'] + "</li>"

                work_orders_display = work_orders_display + "</ul>"
            else:
                work_orders_display = work_orders_display + "<table border='1'><tr><td><b>Work Orders for Asset <a target='_blank' href='https://" + maximo_server + "/maximo/oslc/graphite/manage-shell/index.html?event=loadapp&value=asset&uniqueid=" + assetUIDNumbers[assetIndex]+ "'>" + asset + "</a></b></td></tr><tr><td>"
                work_orders_display = work_orders_display + "<tr><td>There are no work orders for this asset.</td></tr><tr><td><br/></td></tr></table>"
                assets_no_work_orders.append(asset)
        else:
            work_orders_display = "There are no work orders for any of the assets."

    assets_no_work_orders_string = ""
    if assets_no_work_orders:
        for asset in assets_no_work_orders:
            if assets_no_work_orders_string == "":
                assets_no_work_orders_string = str(asset)
            else:
                assets_no_work_orders_string = assets_no_work_orders_string + "," + str(asset)

    result = { "displayResult" : work_orders_display, "jsonResult" : "","assetsNoWorkOrdersString": assets_no_work_orders_string}

    return result


# Root
@app.get("/")
def hello_world(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return "Hello World"

@app.get("/items/")
async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}

app.include_router(hello.app)

desc = """
A wrapper written using Python FastAPI framework to access the Maximo APIs.
"""

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="FastAPI Wrapper for Maximo API",
        version="1.0.0",
        description=desc,
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
import os
from bottle import route, run, request, post, get

@post("/shutdown")
def shutdown():
    os.system("shutdown")

@post("/launch/<id>")
def launch(id):
    if isinstance(id, (int, float)):
        os.system(f"qemu start {id}")

        return {
            "statusCode" : 200
        }
    
    return {
        "statusCode" : 400 # TODO: Por validar
    }

#TODO: parse
@get("/list")
def list_instances():
    os.system("qm list > output.txt")
    with open("output.txt", "r") as file:
        l = file.readlines()

    return l

run(host="0.0.0.0", debug=True)
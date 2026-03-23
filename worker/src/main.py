import flask
import json
import hashlib
import os
import sqlite3

from modules.worker import RunJob

app = flask.Flask("tiny-cluster worker agent")
workers = {}

def password(pwd):
    hash = hashlib.sha512(pwd.encode())
    pwd = hash.hexdigest()

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "password")) as f:
        original = f.read()
    
    return original.startswith(pwd)

@app.route("/submit", methods=["POST"])
def action_submit():
    j_data = flask.request.get_json()
    
    if not password(j_data["password"]):
        return flask.Response("ERROR: password does not be matched", 400)

    job = RunJob(j_data)
    
    index = 1
    while job.get_name() in workers.keys(): index += 1
    
    if index != 1:
        job.set_name("%s-%d" % (job.get_name(), index))

    job.start()

    workers.update({job.get_name(): job})

    return "the submission has been successfully"

@app.route("/job_list", methods=["POST"])
def action_list():
    j_data = flask.request.get_json()
    
    if not password(j_data["password"]):
        return flask.Response("ERROR: password does not be matched", 400)

    response = {}

    for key in workers.keys():
        response.update({key: workers[key].is_alive()})
    
    return flask.jsonify(response)

@app.route("/stop", methods=["POST"])
def action_stop():
    j_data = flask.request.get_json()
    
    if not password(j_data["password"]):
        return flask.Response("ERROR: password does not be matched", 400)
    
    name = None
    
    if j_data["name"] in workers.keys():
        name = j_data["name"]
    else:
        for key in sorted(workers.keys(), reverse=True):
            if j_data["name"] in key:
                name = key
                break
    
    if name is None:
        return flask.Response("no such as job name: %s" % j_data["name"], 404)

    if not workers[name].is_alive():
        return flask.Response("%s has been stopped." % name, 404)
    
    workers[name].terminate()

    return "%s will be stopped." % name

@app.route("/logs", methods=["POST"])
def action_logs():
    j_data = flask.request.get_json()
    
    if not password(j_data["password"]):
        return flask.Response("ERROR: password does not be matched", 400)
    
    name = None
    
    if j_data["name"] in workers.keys():
        name = j_data["name"]
    else:
        for key in sorted(workers.keys(), reverse=True):
            if j_data["name"] in key:
                name = key
                break

    if name is None:
        return flask.Response("no such as job name: %s" % j_data["name"], 404)
    
    if not os.path.isfile(name + ".sqlite3"):
        return flask.Response("no such as log file of job: %s" % name, 404)
    
    conn = sqlite3.connect(name + ".sqlite3")
    cursor = conn.cursor()

    if j_data["tail"] == 0:
        cursor.execute("SELECT message FROM logs WHERE type IN ('STDOUT', 'STDERR')")
        return flask.jsonify(cursor.fetchall())
    else:
        cursor.execute("SELECT message FROM logs WHERE type IN ('STDOUT', 'STDERR') AND id IN (SELECT id FROM logs ORDER BY id DESC LIMIT ?) ORDER BY id ASC", (j_data["tail"],))
        return flask.jsonify(cursor.fetchall())
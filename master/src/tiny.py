import sys
import os
import requests
import urllib3
import getpass
import yaml
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from modules.argsparser import parser, args_checker

def args_parse(args):
    args_list, args_dict = parser(args)
    args_check_list = [
        "-h", "--h",
        "-n", "--name",
        "-p", "--port",
        "-t", "--tail",
    ]

    flag, invalid = args_checker(args_dict, args_check_list)

    if not flag:
        print("invalid option: %s" % invalid)
    
    return args_list, args_dict

def read_help():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "help.yaml"), "r") as f:
        data = yaml.safe_load(f)
    
    return data

def show_help(args_list, args_dict, help_data):
    if not args_list or "-h" in args_dict.keys() or "--help" in args_dict.keys():
        print(help_data["default"])
        return False
    
    if args_list[0] not in ("submit", "list", "logs", "stop", "venv"):
        print(help_data["default"])
        return False
    
    if args_list[0] == "submit" and (len(args_list) != 3 or "-h" in args_dict.keys() or "--help" in args_dict.keys()):
        print(help_data["submit"])
        return False
    
    if args_list[0] == "list" and (len(args_list) != 2 or "-h" in args_dict.keys() or "--help" in args_dict.keys()):
        print(help_data["list"])
        return False
    
    if args_list[0] == "logs" and (len(args_list) != 3 or "-h" in args_dict.keys() or "--help" in args_dict.keys()):
        print(help_data["logs"])
        return False
    
    if args_list[0] == "stop" and (len(args_list) != 3 or "-h" in args_dict.keys() or "--help" in args_dict.keys()):
        print(help_data["stop"])
        return False
    
    if args_list[0] == "venv" and (len(args_list) != 3 or "-h" in args_dict.keys() or "--help" in args_dict.keys()):
        print(help_data["venv"])
        return False
    
    return True

def submit_job(worker, job, port, password):
    j_data = yaml.safe_load(open(job, "r"))
    j_data.update({"password": password})
    response = requests.post(
        "https://%s:%s/submit" % (worker, port),
        json=j_data,
        verify=False,
    )

    return response.text

def job_list(worker, port, password):
    j_data = {"password": password}
    response = requests.post(
        "https://%s:%s/job_list" % (worker, port),
        json=j_data,
        verify=False,
    )

    if response.status_code != 200:
        return response.text
    
    response = response.json()

    form = [
        "=" * 100,
        "%-80s%s" % ("task name", "status"),
        "-" * 100,
    ]

    for key in response.keys():
        form.append("%-80s%s" % (key, "alive" if response[key] else "stopped"))
    
    form.append("-" * 100)
    
    return "\n".join(form)

def stop_job(worker, job, port, password):
    j_data = {"name": job, "password": password}
    response = requests.post(
        "https://%s:%s/stop" % (worker, port),
        json=j_data,
        verify=False,
    )

    return response.text

def view_logs(worker, job, port, password, tail):
    j_data = {"name": job, "password": password, "tail": int(tail)}
    response = requests.post(
        "https://%s:%s/logs" % (worker, port),
        json=j_data,
        verify=False,
    )

    if response.status_code != 200:
        return response.text

    response_list = []
    for res in response.json():
        response_list.append(base64.b64decode(res[0].encode("UTF-8")))
    
    return response_list

def main(*args):
    args_list, args_dict = args_parse(args)
    help_data = read_help()

    ret = show_help(args_list, args_dict, help_data)

    if not ret:
        return 0
    
    password = getpass.getpass("Enter the password for %s: " % args_list[1])

    ret = ""
    port = 8900

    if "--port" in args_dict.keys():
        port = args_dict["--port"]
    elif "-p" in args_dict.keys():
        port = args_dict["-p"]
    
    if args_list[0] == "submit":
        _, worker, job = args_list
        
        ret = submit_job(worker, job, port, password)
    
    elif args_list[0] == "list":
        _, worker = args_list

        ret = job_list(worker, port, password)
    
    elif args_list[0] == "stop":
        _, worker, job = args_list
        
        ret = stop_job(worker, job, port, password)
    
    elif args_list[0] == "logs":
        _, worker, job = args_list
        tail = 0
        if "-t" in args_dict.keys():
            tail = args_dict["-t"]
        elif "--tail" in args_dict.keys():
            tail = args_dict["--tail"]
        
        ret = view_logs(worker, job, port, password, tail)

        if type(ret) is not str:
            for chunk in ret:
                sys.stdout.buffer.write(chunk)

            ret = ""

    print(ret)

if __name__ == "__main__":
    ret = main(*sys.argv)
    sys.exit(ret)
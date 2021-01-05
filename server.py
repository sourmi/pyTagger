import json
import os
import subprocess
import sys
import urllib
import uuid

from flask import Flask, request, Response, send_from_directory, redirect
from flask_restful import Api, Resource

app = Flask(__name__)


class ExifData:

    @staticmethod
    def get_data(filen_name):
        try:
            s = subprocess.check_output(
                ["exiftool"
                    , "-s"  # Short output format
                    , "-json"
                    , "-ImageDescription"
                    , "-UserComment"
                    , "-DateTimeOriginal"
                    , "-Rating"
                    , "-Artist"
                    , "-Copyright"
                    , filen_name])
            j = json.loads(s)
            return j[0]
        except subprocess.CalledProcessError as error:
            print(f"error get data {error.returncode} {error.output}")
        return {}

    @staticmethod
    def set_data(file_name, data):
        try:
            args = [
                "exiftool",
                "-overwrite_original",  # change original file no backup-copy
                "-P"  # preserve Filetime
            ]
            for key, value in data.items():
                arg = f"-{key}={value}"
                args.append(arg)
            args.append(file_name)
            print(args)
            subprocess.check_output(args)
        except subprocess.CalledProcessError as error:
            print(f"error get data {error.returncode} {error.output}")
        return {}


class Images(Resource):

    @staticmethod
    def get(name):
        filename = root_path + name
        print(f"Images.get: {filename}")

        if not check_path_traversal(filename):
            return "Bad user!", 403

        if not os.path.exists(filename):
            return f"Image {name} not found", 404
        if os.path.isfile(filename):
            basename = os.path.basename(filename)
            dirname = os.path.dirname(filename) + "/"
            return send_from_directory(dirname, basename)
        else:
            files = os.listdir(filename)
            return {'images': [i for i in files]}, 200

        
class Exif(Resource):

    @staticmethod
    def get(name):
        filename = root_path + name
        if not check_path_traversal(filename):
            return "Bad user!", 403
        json_exif = get_exif_for_file(name)
        if not json_exif:
            return f"Image {name} not found", 404
        return json_exif, 200

    @staticmethod
    def put(name):
        filename = root_path + name
        if not check_path_traversal(filename):
            return "Bad user!", 403
        if not os.path.exists(filename):
            return f"Image {name} not found", 404
        content = request.json
        ExifData.set_data(filename, content)
        return "OK", 200


class Html(Resource):

    def get(self, name=""):
        filename = root_path + name
        if not check_path_traversal(filename):
            return "Bad user!", 403
        print(f"GET {name}:{str(os.path.isdir(filename))}")
        if os.path.isdir(filename):
            return Response(list_files(name), mimetype='text/html')
        if not os.path.exists(filename):
            print(f"Image {name} not found", 404)
            return f"Image {name} not found", 404
        index_html = get_index_html(name)
        return Response(index_html, mimetype='text/html')

    def post(self, name):
        filename = root_path + name
        if not check_path_traversal(filename):
            return "Bad user!", 403
        data = request.json
        print("POST {name}"+ str(data))
        for key, value in data.items():
            #print("> "+key+"=["+ value +"]")
            print(f"> {key}=[{value}]")
        # Exif speichern
        filename = root_path + name
        ExifData.set_data(filename, data)
        next_file = str(get_next_file(name))
        ret = urllib.parse.quote(next_file, '')
        return Response(ret, mimetype='text/html')


class Navigation(Resource):

    @staticmethod
    def get(direction, file_name=""):
        if direction == "next":
            next_file = get_next_file(file_name)
            return redirect("/html/" + next_file, code=303)
        if direction == "prev":
            prev = get_prev_file(file_name)
            return redirect("/html/" + prev, code=303)
        if direction == "up":
            up = os.path.dirname(file_name)
            return redirect("/html/" + up, code=303)


def get_nonce():
    global script_nonce
    script_nonce = uuid.uuid4()
    return str(script_nonce)


def get_index_html(name):
    filename = root_path + name
    result_json = ExifData.get_data(filename)
    index_html = get_index()
    index_html = index_html.replace("{ImageDescription}", result_json.get("ImageDescription", ""))
    index_html = index_html.replace("{UserComment}"     , result_json.get("UserComment", ""))
    index_html = index_html.replace("{DateTimeOriginal}", result_json.get("DateTimeOriginal", ""))
    index_html = index_html.replace("{Rating}"          , str(result_json.get("Rating", "")))
    index_html = index_html.replace("{ImagePath}"       , os.path.split(name)[0])
    index_html = index_html.replace("{SourceFile}"      , os.path.split(name)[1])
    index_html = index_html.replace("{StaticText}"      , "")
    index_html = index_html.replace("{TagJsonData}", json.dumps(tag_data_json, indent=4))
    
    # insert nonce for CSP
    index_html = index_html.replace("{script-nonce}", get_nonce())
    return index_html


def get_exif_for_file(file_name):
    name = file_name
    full_name = root_path + name
    if not os.path.exists(full_name):
        return None
    result_json = ExifData.get_data(full_name)
    result_json["SourceFile"] = name
    return result_json


def get_next_file(input_file):
    return get_next_file_by_distance(input_file, 1)


def get_prev_file(input_file):
    return get_next_file_by_distance(input_file, -1)


def get_next_file_by_distance(input_file, distance):
    file_name = root_path + input_file
    base_name = os.path.basename(file_name)
    dir_name  = os.path.dirname(file_name) + "/"
    file_list = sorted(os.listdir(dir_name))
    next_index = file_list.index(base_name)
    next_index = next_index + distance
    if next_index < 0:
        next_index = 0
    if next_index >= len(file_list):
        next_index = len(file_list)-1
    next_file = file_list[next_index]
    next_file = file_name.replace(base_name, next_file)
    next_file = next_file.replace(root_path, "")
    return next_file


def list_files(relative_path):
    absolute_path = os.path.normpath(root_path + "/" + relative_path)
    if not check_path_traversal(absolute_path):
        return "Bad user!", 403
    html = f"<a href='/html'>home</a> || \n" \
           f"<a href='/shutdown'>shutdown server</a>\n" \
           f"<br><br>\n"\
           f"<a href='/nav/up/{relative_path}'>..</a><br>\n"
    file_list = sorted(os.listdir(absolute_path))
    for file in file_list:
        html += f"<a href='/html/{relative_path}/{file}'>{relative_path}/{file}</a><br>\n"
    html += f"<script type='text/javascript' nonce='{get_nonce()}'>\n"\
            "for(var i = 0, l=document.links.length; i<l; i++)"\
            "{ document.links[i].href += window.location.hash; }\n</script>"
    return html_page(html)


def check_path_traversal(path_to_check):
    absolute_filename = os.path.realpath(path_to_check)
    absolute_root_path = os.path.realpath(root_path)
    if os.path.commonprefix((absolute_filename, absolute_root_path)) != absolute_root_path:
        #raise PermissionError
        return False
    return True


def get_index():
    file = open("./image.html", "r") 
    index_html = file.read()
    return index_html


def load_tag_data(json_file):
    print('loading tags from ' + json_file)
    with open(json_file) as json_file:
        data = json.load(json_file)
    return data


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def html_page(message):
    return f"<!Doctype html>\n<html>\n<head>"\
           f"<meta charset='UTF-8'><title>MyTager</title></head>"\
           f"\n<body>\n{message}\n</body></html>"


@app.route('/del/<path:file_name>')
def delete(file_name):
    print(f"DELETE:  {file_name}")
    full_name = root_path + file_name
    if not check_path_traversal(full_name):
        return "Bad user!", 403
    if not os.path.exists(full_name):
        return f"Image {full_name} not found", 404
    #os.remove(full_name)
    print("##### would delete: " + full_name)
    next_file = get_next_file(file_name)
    if next_file == file_name:
        return redirect("/", code=303)
    else:
        return redirect("/html/" + next_file, code=303)


@app.route('/')
def index():
    html = list_files("")
    return html


@app.route('/styles.css')
def styles():
    print("STYLES")
    return send_from_directory(".", "styles.css")


@app.route('/favicon.ico')
def favicon():
    print("FAVICON")
    return send_from_directory(".", "favicon.ico")


@app.route('/shutdown', methods=['GET'])
def shutdown():
    shutdown_server()
    return html_page("Server shutting down...")


@app.after_request
def add_security_header(response):
    global script_nonce, content_security_policy
    content_security_policy = "default-src 'self'; img-src 'self'; script-src 'strict-dynamic' 'nonce-" + str(script_nonce) + "'; style-src 'self';"
    response.headers['Content-Security-Policy'] = content_security_policy
    response.headers['X-Frame-Options'] = "deny"
    response.headers['X-Content-Type-Options'] = "nosniff"
    return response


script_nonce = "initialValue"  # nonce for CSP inline JavaScript
tag_data_json = load_tag_data('tags.json')

path = ""
if len(sys.argv) > 1:
    path = sys.argv[1]
if not os.path.exists(path):
    path = os.getcwd() + "/"
print('working path: ', str(path))
root_path = path


api = Api(app)
api.add_resource(Images    , "/images/<path:name>")
api.add_resource(Exif      , "/exif/<path:name>")
api.add_resource(Html      , "/html/", "/html/<path:name>")
api.add_resource(Navigation, "/nav/<string:direction>/", "/nav/<string:direction>/<path:file_name>")

#app.run(debug=True)
if __name__ == '__main__':
    app.run(port='5000')

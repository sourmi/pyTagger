from flask import Flask, request, Response, send_from_directory, redirect
from flask_restful import Api, Resource
import os, subprocess, json, urllib, sys, uuid

app = Flask(__name__)


class ExifData:

    @staticmethod
    def getData(filename):
        try:
            s = subprocess.check_output(["exiftool"
                , "-s" # Short output format
                , "-json"
                , "-ImageDescription"
                , "-UserComment"
                , "-DateTimeOriginal"
                , "-Rating"
                , "-Artist"
                , "-Copyright"
                , filename])
            j = json.loads(s)
            return j[0]
        except:
            print("error get data") 
        return {}

    @staticmethod
    def setData(filename, data):
        try:
            args = ["exiftool"
                , "-overwrite_original" # change original file no backup-copy
                , "-P" # preserve Filetime
            ]
            for key, value in data.iteritems():
                arg = "-"+key +"="+ value
                args.append(arg)
            args.append(filename)
            print(args)
            s = subprocess.check_output(args)
        except:
            print("error set data") 
        return {}


class Images(Resource):

    def get(self, name):
        filename = rootPath+name
        print("Images.get: " + filename)

        if not checkPathtraversal(filename):
            return "Bad user!", 403

        if not os.path.exists(filename):
            return "Image "+ name +" not found", 404
        if os.path.isfile(filename):
            basename = os.path.basename(filename)
            dirname  = os.path.dirname(filename) +"/"
            return send_from_directory(dirname, basename)
        else:
            files = os.listdir(filename)
            return {'images': [i for i in files]}, 200

        
class Exif(Resource):

    def get(self, name):
        filename = rootPath+name
        if not checkPathtraversal(filename):
            return "Bad user!", 403
        json = getExifForFile(name)
        if not json:
            return "Image "+ name +" not found", 404
        return json, 200

    def put(self, name):
        filename = rootPath+name
        if not checkPathtraversal(filename):
            return "Bad user!", 403
        if not os.path.exists(filename):
            return "Image "+ name +" not found", 404
        content = request.json
        ExifData.setData(filename, content)
        return "OK", 200


class Html(Resource):

    def get(self, name=""):
        filename = rootPath+name
        if not checkPathtraversal(filename):
            return "Bad user!", 403
        print("GET " + name +":"+str(os.path.isdir(filename)))
        if os.path.isdir(filename):
            return Response(listFiles(name), mimetype='text/html')
        if not os.path.exists(filename):
            print("Image "+ name +" not found", 404)
            return "Image "+ name +" not found", 404
        indexHtml = getIndexHtml(name)
        return Response(indexHtml, mimetype='text/html')


    def post(self,name):
        filename = rootPath+name
        if not checkPathtraversal(filename):
            return "Bad user!", 403
        print("POST "+ name)
        data = request.json
        for key, value in data.iteritems():
            print("> "+key +"=["+ value +"]")
        # Exif speichern
        filename = rootPath+name
        ExifData.setData(filename,data)

        nextFile = str(getNextFile(name))
        ret = urllib.quote(nextFile,'');
        return Response(ret,mimetype='text/html')


class Navigation(Resource):

    def get(self, direction, fileName=""):
        if direction =="next":
            next = getNextFile(fileName)
            return redirect("/html/"+next, code=303)
        if direction =="prev":
            prev = getPrevFile(fileName)
            return redirect("/html/"+prev, code=303)
        if direction =="up":
            up = os.path.dirname(fileName)
            return redirect("/html/"+up, code=303)


def getNonce():
    global scriptNonce
    scriptNonce = uuid.uuid4()
    return str(scriptNonce)


def getIndexHtml(name):
    filename = rootPath+name
    resultJson = ExifData.getData(filename)
    indexHtml = getIndex()
    indexHtml = indexHtml.replace("{ImageDescription}", resultJson.get("ImageDescription",""))
    indexHtml = indexHtml.replace("{UserComment}"     , resultJson.get("UserComment",""))
    indexHtml = indexHtml.replace("{DateTimeOriginal}", resultJson.get("DateTimeOriginal",""))
    indexHtml = indexHtml.replace("{Rating}"          , str(resultJson.get("Rating","")))
    indexHtml = indexHtml.replace("{ImagePath}"       , os.path.split(name)[0])
    indexHtml = indexHtml.replace("{SourceFile}"      , os.path.split(name)[1]) #name)
    indexHtml = indexHtml.replace("{StaticText}"      , "")
    indexHtml = indexHtml.replace("{TagJsonData}"     , json.dumps(TagDataJson, indent=4))
    
    # insert nonce for CSP
    indexHtml = indexHtml.replace("{script-nonce}"    , getNonce())
    return indexHtml


def getExifForFile(fileName):
    name = fileName
    fullName = rootPath+name
    if not os.path.exists(fullName):
        return None
    resultJson = ExifData.getData(fullName)
    resultJson["SourceFile"] = name
    return resultJson


def getNextFile(inputFile):
    return getNextFileByDistance(inputFile,  1)

def getPrevFile(inputFile):
    return getNextFileByDistance(inputFile, -1)

def getNextFileByDistance(inputFile, distance):
    filename = rootPath + inputFile
    basename = os.path.basename(filename)
    dirname  = os.path.dirname(filename) +"/"
    fileList = sorted(os.listdir(dirname))
    nextIndex = fileList.index(basename)
    nextIndex = nextIndex + distance
    if nextIndex < 0:
        nextIndex = 0;
    if nextIndex >= len(fileList):
        nextIndex = len(fileList)-1
    next = fileList[nextIndex];
    next = filename.replace(basename, next);
    next = next.replace(rootPath, "");
    return next

def listFiles(relativePath):
    absolutePath = os.path.normpath(rootPath +"/"+ relativePath)
    if not checkPathtraversal(absolutePath):
        return "Bad user!", 403
    html = ""
    html += "<a href='/html'>home</a> || \n"
    html += "<a href='/shutdown'>shutdown server</a>\n"
    html += "<br><br>\n"
    html += "<a href='/nav/up/"+ relativePath +"'>..</a><br>\n"
    fileList = sorted(os.listdir(absolutePath))
    for file in fileList:
        html += "<a href='/html/"+ relativePath +"/"+ file +"'>"+ relativePath +"/"+ file +"</a><br>\n"
    html += "<script type='text/javascript' nonce='"+getNonce()+"'>\n"
    html +=" for(var i = 0, l=document.links.length; i<l; i++) { document.links[i].href += window.location.hash; }\n</script>"
    return htmlPage(html)

def checkPathtraversal(path):
    absoluteFilename = os.path.realpath(path)
    absoluterootPath = os.path.realpath(rootPath)
    if os.path.commonprefix((absoluteFilename,absoluterootPath)) != absoluterootPath: 
        #raise PermissionError
        return False
    return True


def getIndex():
    file = open("./image.html", "r") 
    indexHtml = file.read()
    return indexHtml


def loadTagData(jsonFile):
    print('loading tags from '+ jsonFile)
    with open(jsonFile) as json_file:
        data = json.load(json_file)
    return data


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def htmlPage(message):
    return "<!Doctype html>\n<html>\n<head><meta charset='UTF-8'><title>MyTager</title></head>\n<body>\n"+ message +"\n</body></html>"


@app.route('/del/<path:fileName>')
def delelte(fileName):
    print("DELETE:  "+ fileName)
    fullName = rootPath + fileName
    if not checkPathtraversal(fullName):
        return "Bad user!", 403
    if not os.path.exists(fullName):
        return "Image "+ fullName +" not found", 404
    #os.remove(fullName) 
    print("##### would delete: "+ fullName)
    next = getNextFile(fileName)
    if (next==fileName):
        return redirect("/", code=303)
    else:
        return redirect("/html/"+next, code=303)

@app.route('/')
def index():
    html = listFiles("")
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
    return htmlPage("Server shutting down...")

@app.after_request
def add_security_header(response):
    global scriptNonce
    response.headers['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; script-src 'nonce-"+ str(scriptNonce) +"'; style-src 'self'"
    response.headers['X-Frame-Options'] = "deny"
    response.headers['X-Content-Type-Options'] = "nosniff"
    return response


scriptNonce = "initialValue" # nonce for CSP inline JavaScript
TagDataJson = loadTagData('tags.json')

path = ""
if len(sys.argv)>1:
    path = sys.argv[1];
if not os.path.exists(path):
    path = os.getcwd() +"/"
print('working path: ', str(path))
rootPath = path


api = Api(app)
api.add_resource(Images    , "/images/<path:name>")
api.add_resource(Exif      , "/exif/<path:name>")
api.add_resource(Html      , "/html/", "/html/<path:name>" )
api.add_resource(Navigation, "/nav/<string:direction>/", "/nav/<string:direction>/<path:fileName>")

#app.run(debug=True)
if __name__ == '__main__':
     app.run(port='5000')

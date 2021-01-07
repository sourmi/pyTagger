import os
import tempfile
import pytest
import base64
from enum import Enum

import server


def setup_module(session):
    print("###### START")


def teardown_module(session):
    print("###### END")


status_200 = "200 OK"
status_403 = "403 FORBIDDEN"
status_404 = "404 NOT FOUND"

mimetype_json = "application/json"
mimetype_css = "text/css"
mimetype_ico = "image/vnd.microsoft.icon"
mimetype_jpg = "image/jpeg"
mimetype_gif = "image/gif"


@pytest.fixture
def client():
    db_fd, server.app.config['DATABASE'] = tempfile.mkstemp()
    server.app.config['TESTING'] = True

    with server.app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(server.app.config['DATABASE'])

#assert b'html, body*' in rv.data
#rv = client.get('/html/testpics/01/2020-01-01__16-42-28__IMG_3130.JPG')
#rv = client.get('/html/foo')
#rv = client.get('/images/foo')
#rv = client.get('/exif/foo')
#rv = client.get('/nav/foo')

#    rv = client.get('/del/test/test.jpeg')
#    assert status_200 in rv.status

#create_jpeg("test/test.jpeg")
#create_gif("test/test.gif")


def assert_response(response, status, mimetype):
    assert response.status == status
    assert response.mimetype == mimetype


def test_path_traversal(client):
    rv = client.get("/images/test/")
    print("\n###\n### JSON3: " + str(rv.data)) #base64.b64encode(rv.data)))
    print("s: "+ rv.status +" m: "+ rv.mimetype)
    assert rv.status == status_200
    pattern = [
        "%2e%2e%2f", "%2e%2e/", "..%2f", "%2e%2e%5c", "%2e%2e\\",
        "..%5c", "%252e%252e%255c", "..%255c",
        "..%c0%af", "..%c1%9c",
        "/../../../../../../"
    ]
    assert status_200 == check_path_traversal(client, '/html/')
    for p in pattern:
        status = check_path_traversal(client, '/html/'+ p)
        assert status != status_200

    assert status_403 == check_path_traversal(client, '/html/../')

    assert status_200 == check_path_traversal(client, '/images/test/')
    assert status_200 == check_path_traversal(client, '/images/test/test.jpeg')
    assert status_200 == check_path_traversal(client, '/images/test/test.gif')

    assert status_403 == check_path_traversal(client, '/images/../../')
    assert status_403 == check_path_traversal(client, '/images/test/../../../')


def check_path_traversal(client, path):
    rv = client.get(path)
    print(f"### CPT({path}): {rv.status}, {rv.mimetype}" + str(rv.data)) #base64.b64encode(rv.data)))
    return rv.status


def test_put_exif(client):
    #rv = client.get('/html/test/test.jpeg')
    rv = client.put('/exif/test/test.jpeg', json={
        'UserComment': "", 'ImageDescription': "", 'Rating': "", 'StaticText': ""})
    assert rv.status == status_200

    rv = client.get('/exif/test/test.jpeg')
    assert rv.status == status_200
    assert rv.mimetype == mimetype_json
    json_data = rv.get_json()
    assert json_data["SourceFile"] == "test/test.jpeg"
    assert 'UserComment' not in json_data
    assert 'ImageDescription' not in json_data
    assert 'Rating' not in json_data
    assert 'StaticText' not in json_data

    rv = client.put('/exif/test/test.jpeg', json={
        'UserComment': "uc", 'ImageDescription': "id", 'Rating': "1", 'StaticText': "st"})
    assert rv.status == status_200

    rv = client.get('/exif/test/test.jpeg')
    assert rv.status == status_200
    json_data = rv.get_json()
    assert json_data["SourceFile"] == "test/test.jpeg"
    assert json_data["UserComment"] == "uc"
    assert json_data["ImageDescription"] == "id"
    assert json_data["Rating"] == 1
    #assert json_data["StaticText"] in None # kein Exif-Tag

#exiftool -overwrite_original -P -UserComment=,,st,uc,
# -ImageDescription=id -Rating=1 -StaticText=st ./pics/pyTagger/test/test.jpeg


def create_gif(name):
    gif_base64 = "R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="
    new_file = open(name, "wb")
    new_file.write(base64.b64decode(gif_base64))
    new_file.close()


def create_jpeg(name):
    jpeg_base64 = "/9j/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDREND"\
                  "g8QEBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k="
    new_file = open(name, "wb")
    new_file.write(base64.b64decode(jpeg_base64))
    new_file.close()


def test_security_headers(client):
    rv = client.get('/')
    assert rv.status == status_200
    assert "text/htm" in rv.mimetype
    assert_security_headers(rv)
    assert_security_headers(client.get('/html/'))
    assert_security_headers(client.get('/images/'))
    assert_security_headers(client.get('/exif/'))
    assert_security_headers(client.get('/nav/'))


def assert_security_headers(rv):
    assert 'X-Frame-Options' in rv.headers
    assert rv.headers['X-Frame-Options'] == "deny"
    assert 'X-Content-Type-Options' in rv.headers
    assert rv.headers['X-Content-Type-Options'] == "nosniff"
    assert 'Content-Security-Policy' in rv.headers
    assert "nonce" in rv.headers['Content-Security-Policy']


def test_favicon_present(client):
    rv = client.get('/favicon.ico')
    assert rv.date is not None
    assert rv.status == status_200
    assert rv.mimetype == mimetype_ico


def test_style_present(client):
    rv = client.get('/styles.css')
    assert rv.date is not None
    assert rv.status == status_200
    assert rv.mimetype == mimetype_css


def print_response(rv):
    #response=None, status=None, headers=None, mimetype=None, content_type=None, direct_passthrough=False
    print("##" + str(type(rv.response)))
    print("##" + str(type(rv.headers)))
    print("##" + str(rv.status))
    print("##" + str(rv.mimetype))
    print("##" + str(rv.content_type))

# Copyright 2013, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

import nose
import numpy
import numpy.testing
import requests
import slycat.web.client
import shutil
import subprocess
import sys
import time

server_process = None
connection = None

def require_valid_project(project):
  nose.tools.assert_is_instance(project, dict)
  nose.tools.assert_in("type", project)
  nose.tools.assert_equal(project["type"], "project")
  nose.tools.assert_in("name", project)
  nose.tools.assert_is_instance(project["name"], basestring)
  nose.tools.assert_in("description", project)
  nose.tools.assert_is_instance(project["description"], basestring)
  nose.tools.assert_in("creator", project)
  nose.tools.assert_is_instance(project["creator"], basestring)
  nose.tools.assert_in("created", project)
  nose.tools.assert_is_instance(project["created"], basestring)
  nose.tools.assert_in("acl", project)
  nose.tools.assert_is_instance(project["acl"], dict)
  nose.tools.assert_in("administrators", project["acl"])
  nose.tools.assert_is_instance(project["acl"]["administrators"], list)
  nose.tools.assert_in("readers", project["acl"])
  nose.tools.assert_is_instance(project["acl"]["readers"], list)
  nose.tools.assert_in("writers", project["acl"])
  nose.tools.assert_is_instance(project["acl"]["writers"], list)
  return project

def require_valid_model(model):
  nose.tools.assert_is_instance(model, dict)
  nose.tools.assert_in("type", model)
  nose.tools.assert_equal(model["type"], "model")
  nose.tools.assert_in("name", model)
  nose.tools.assert_is_instance(model["name"], basestring)
  nose.tools.assert_in("description", model)
  nose.tools.assert_is_instance(model["description"], basestring)
  nose.tools.assert_in("creator", model)
  nose.tools.assert_is_instance(model["creator"], basestring)
  nose.tools.assert_in("created", model)
  nose.tools.assert_is_instance(model["created"], basestring)
  nose.tools.assert_in("marking", model)
  nose.tools.assert_is_instance(model["marking"], basestring)
  nose.tools.assert_in("model-type", model)
  nose.tools.assert_is_instance(model["model-type"], basestring)
  nose.tools.assert_in("project", model)
  nose.tools.assert_is_instance(model["project"], basestring)
  nose.tools.assert_in("worker", model)
  nose.tools.assert_is_instance(model["worker"], basestring)
  return model

def setup():
  shutil.rmtree("test-data-store", ignore_errors=True)
  subprocess.check_call(["python", "slycat-couchdb-setup.py", "--database=slycat-test", "--delete"])

  global server_process, connection
  server_process = subprocess.Popen(["python", "slycat-web-server.py", "--config=test-config.ini"])
  time.sleep(2.0)
  connection = slycat.web.client.connection(host="https://localhost:8093", proxies={"http":"", "https":""}, verify=False, auth=("slycat", "slycat"), log=slycat.web.client.dev_null())

def teardown():
  global server_process
  server_process.terminate()
  server_process.wait()

def test_projects():
  projects = connection.get_projects()
  nose.tools.assert_equal(projects, [])

  pid1 = connection.create_project("foo")
  pid2 = connection.create_project("bar")
  projects = connection.get_projects()
  nose.tools.assert_is_instance(projects, list)
  nose.tools.assert_equal(len(projects), 2)
  for project in projects:
    require_valid_project(project)

  connection.delete_project(pid2)
  connection.delete_project(pid1)
  projects = connection.get_projects()
  nose.tools.assert_equal(projects, [])

def test_project():
  pid = connection.create_project("test-project", "My test project.")

  project = require_valid_project(connection.get_project(pid))
  nose.tools.assert_equal(project["name"], "test-project")
  nose.tools.assert_equal(project["description"], "My test project.")
  nose.tools.assert_equal(project["creator"], "slycat")
  nose.tools.assert_equal(project["acl"], {'administrators': [{'user': 'slycat'}], 'writers': [], 'readers': []})

  connection.put_project(pid, {"name":"modified-project", "description":"My modified project.", "acl":{"administrators":[{"user":"slycat"}], "writers":[{"user":"foo"}], "readers":[{"user":"bar"}]}})
  project = require_valid_project(connection.get_project(pid))
  nose.tools.assert_equal(project["name"], "modified-project")
  nose.tools.assert_equal(project["description"], "My modified project.")
  nose.tools.assert_equal(project["acl"], {'administrators': [{'user': 'slycat'}], 'writers': [{"user":"foo"}], 'readers': [{"user":"bar"}]})

  connection.delete_project(pid)
  with nose.tools.assert_raises(requests.HTTPError):
    project = connection.get_project(pid)

def test_bookmarks():
  pid = connection.create_project("test-project")

  bookmark = {"foo":"bar", "baz":[1, 2, 3]}
  bid = connection.create_bookmark(pid, bookmark)
  nose.tools.assert_equal(connection.get_bookmark(bid), bookmark)

  bid2 = connection.create_bookmark(pid, bookmark)
  nose.tools.assert_equal(bid, bid2)

  connection.delete_project(pid)

def test_models():
  pid = connection.create_project("test-project")

  wid = connection.create_model_worker(pid, "generic", "test-model")
  mid1 = connection.finish_model(wid)
  connection.join_worker(wid)

  wid = connection.create_model_worker(pid, "generic", "test-model-2")
  mid2 = connection.finish_model(wid)
  connection.join_worker(wid)

  models = connection.get_project_models(pid)
  nose.tools.assert_is_instance(models, list)
  nose.tools.assert_equal(len(models), 2)
  for model in models:
    require_valid_model(model)

  connection.delete_model(mid2)
  connection.delete_model(mid1)
  models = connection.get_project_models(pid)
  nose.tools.assert_equal(models, [])

  connection.delete_project(pid)

def test_model_parameters():
  pid = connection.create_project("test-project")
  wid = connection.create_model_worker(pid, "generic", "test-model")
  connection.set_parameter(wid, "foo", "bar")
  connection.set_parameter(wid, "baz", [1, 2, 3])
  connection.set_parameter(wid, "blah", {"cat":"dog"})
  mid = connection.finish_model(wid)
  connection.join_worker(wid)

  model = connection.get_model(mid)
  nose.tools.assert_in("artifact:foo", model)
  nose.tools.assert_equal(model["artifact:foo"], "bar")
  nose.tools.assert_in("artifact:baz", model)
  nose.tools.assert_equal(model["artifact:baz"], [1, 2, 3])
  nose.tools.assert_in("artifact:blah", model)
  nose.tools.assert_equal(model["artifact:blah"], {"cat":"dog"})
  nose.tools.assert_in("input-artifacts", model)
  nose.tools.assert_equal(set(model["input-artifacts"]), set(["foo", "baz", "blah"]))
  nose.tools.assert_in("artifact-types", model)
  nose.tools.assert_equal(model["artifact-types"], {"foo":"json", "baz":"json", "blah":"json"})

  with nose.tools.assert_raises(requests.HTTPError):
    connection.set_parameter(wid, "biff", 2.5)

  connection.delete_model(mid)
  connection.delete_project(pid)

def test_model_table():
  column_types = ["int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64", "float32", "float64", "string"]
  column_names = column_types
  row_count = 10
  columns = [numpy.arange(row_count).astype(type) for type in column_types]

  attributes = zip(column_names, column_types)
  dimensions = [("row", "int64", 0, row_count)]

  pid = connection.create_project("test-project")
  wid = connection.create_model_worker(pid, "generic", "test-model")
  connection.start_array_set(wid, "test-table")
  connection.create_array(wid, "test-table", 0, attributes, dimensions)
  for index, data in enumerate(columns):
    connection.store_array_attribute(wid, "test-table", 0, index, data)
  connection.finish_array_set(wid, "test-table")
  mid = connection.finish_model(wid)
  connection.join_worker(wid)

  with nose.tools.assert_raises(requests.HTTPError):
    connection.start_array_set(wid, "test-table-2")

  metadata = connection.get_table_metadata(mid, "test-table", 0)
  nose.tools.assert_equal(metadata["row-count"], 10)
  nose.tools.assert_equal(metadata["column-count"], 11)
  nose.tools.assert_equal(metadata["column-names"], column_names)
  nose.tools.assert_equal(metadata["column-types"], column_types)
  nose.tools.assert_equal(metadata["column-min"], [0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, "0"])
  nose.tools.assert_equal(metadata["column-max"], [9, 9, 9, 9, 9, 9, 9, 9, 9.0, 9.0, "9"])

  for index, column in enumerate(columns):
    chunk = connection.get_table_chunk(mid, "test-table", 0, range(10), [index])
    nose.tools.assert_equal(chunk["column-names"][0], column_names[index])
    numpy.testing.assert_array_equal(chunk["data"][0], column)

  connection.delete_model(mid)
  connection.delete_project(pid)


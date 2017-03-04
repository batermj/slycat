/*
Copyright 2013, Sandia Corporation. Under the terms of Contract
DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
rights in this software.
*/

define("slycat-coordinator", ["slycat-server-root", "URI", "jquery", "lodash"], function(server_root, URI, $, lodash)
{
  var module = {};

  module.create = function(pid, mid)
  {
    var coordinator = {};

    var state = {}; // JSON object representing the state of the model UI

    return coordinator;
  }

  return module;
});

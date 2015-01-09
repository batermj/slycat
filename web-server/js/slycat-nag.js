/*
Copyright 2013, Sandia Corporation. Under the terms of Contract
DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
rights in this software.
*/

define("slycat-nag", [], function()
{
  var nag = false;

  // We need EventSource for our live project and model feeds.
  if(!window.EventSource)
    nag = true;

  if(nag)
  {
    alert("Your browser is missing features required by Slycat. We suggest switching to a current version of Firefox, Chrome, or Safari.");
  }
});
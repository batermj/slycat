/*
Copyright 2013, Sandia Corporation. Under the terms of Contract
DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
rights in this software.
*/

define("slycat-model-controls", ["slycat-server-root", "slycat-web-client", "slycat-markings", "knockout"], function(server_root, client, markings, ko)
{
  ko.components.register("slycat-model-controls",
  {
    viewModel: function(params)
    {
      var component = this;
      component.name = params.name;
      component.description = params.description;
      component.marking = params.marking;
      component.markings = markings.allowed;

      // This is a tad awkward, but a default marking may-or-may-not be available yet.
      if(component.marking() === null)
      {
        component.marking(markings.preselected());
        markings.preselected.subscribe(function()
        {
          component.marking(markings.preselected());
        });
      }
    },
    template: { require: "text!" + server_root + "templates/slycat-model-controls.html" }
  });
});


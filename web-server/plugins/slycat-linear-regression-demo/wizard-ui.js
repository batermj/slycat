define(["slycat-server-root", "slycat-web-client", "slycat-dialog", "knockout", "knockout-mapping"], function(server_root, client, dialog, ko, mapping)
{
  function constructor(params)
  {
    var component = {};
    component.tab = ko.observable(0);
    component.project = params.projects()[0];
    component.model = mapping.fromJS({_id: null, name: "New Linear Regression Demo Model", description: "This model demonstrates plotting with d3.js", marking: null});
    component.browser = mapping.fromJS({selection: []});
    component.parser = ko.observable(null);
    component.attributes = mapping.fromJS([]);
    component.x_column = ko.observable(null);
    component.y_column = ko.observable(null);

    component.cancel = function()
    {
      if(component.model._id())
        client.delete_model({ mid: component.model._id() });
    }
    component.create_model = function()
    {
      client.post_project_models(
      {
        pid: component.project._id(),
        type: "linear-regression-demo",
        name: component.model.name(),
        description: component.model.description(),
        marking: component.model.marking(),
        success: function(mid)
        {
          component.model._id(mid);
          component.tab(1);
        },
        error: dialog.ajax_error("Error creating model.")
      });
    }
    component.upload_table = function()
    {
      $('.local-browser-continue').toggleClass("disabled", true);
      client.post_model_files(
      {
        mid: component.model._id(),
        files: component.browser.selection(),
        input: true,
        aids: ["data-table"],
        parser: component.parser(),
        success: function()
        {
          client.get_model_table_metadata(
          {
            mid: component.model._id(),
            aid: "data-table",
            success: function(metadata)
            {
              var attributes = [];
              for(var i = 0; i != metadata["column-names"].length; ++i)
              {
                var name = metadata["column-names"][i];
                var type = metadata["column-types"][i];

                attributes.push({name: name, type: type})

                if(type != "string" && component.x_column() === null)
                  component.x_column(i);
                else if(type != "string" && component.y_column() === null)
                  component.y_column(i);
              }
              mapping.fromJS(attributes, component.attributes);
              component.tab(2);
              $('.local-browser-continue').toggleClass("disabled", false);
            }
          });
        },
        error: function(){
          dialog.ajax_error("Did you choose the correct file and filetype?  There was a problem parsing the file: ")();
          $('.local-browser-continue').toggleClass("disabled", false);
        },
      });
    }
    component.go_to_model = function() {
      location = server_root + 'models/' + component.model._id();
    }
    component.finish = function()
    {
      client.put_model_parameter(
      {
        mid: component.model._id(),
        aid: "x-column",
        value: component.x_column(),
        input: true,
        success: function()
        {
          client.put_model_parameter(
          {
            mid: component.model._id(),
            aid: "y-column",
            value: component.y_column(),
            input: true,
            success: function()
            {
              client.post_model_finish(
              {
                mid: component.model._id(),
                success: function()
                {
                  component.tab(3);
                }
              });
            }
          });
        }
      });
    }

    return component;
  }

  return {
    viewModel: constructor,
    template: { require: "text!" + server_root + "resources/wizards/linear-regression-demo/ui.html" },
    };
});

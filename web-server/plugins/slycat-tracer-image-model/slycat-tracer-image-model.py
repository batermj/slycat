def register_slycat_plugin(context):
  """Called during startup when the plugin is loaded."""
  import datetime
  import os
  import slycat.web.server

  def finish(database, model):
    """Called to finish the model.  This function must return immediately, so any real work would be done in a separate thread."""
    slycat.web.server.update_model(database, model, state="finished", result="succeeded", finished=datetime.datetime.utcnow().isoformat(), progress=1.0, message="")

  def html(database, model):
    """Add the HTML representation of the model to the context object."""
    import json
    import pystache

    context = dict()
    context["formatted-model"] = json.dumps(model, indent=2, sort_keys=True)
    context["_id"] = model["_id"];
    context["name"] = model["name"];
    context["full-project"] = database.get("project", model["project"]);
    return pystache.render(open(os.path.join(os.path.dirname(__file__), "ui.html"), "r").read(), context)

  # Register our new model type
  context.register_model("tracer-image", finish, html)

  # Register JS
  javascripts = [
    # This JS is loaded by header (global bundle defined in get_model in handlers.py)
    # "js/jquery-2.1.1.min.js",
    # "js/jquery-migrate-1.2.1.js",
    # "js/jquery.json-2.4.min.js",
    # "js/jquery-ui-1.10.4.custom.min.js",
    # "js/jquery.knob.js",
    # "js/jquery.qtip.min.js",
    # "js/knockout-3.2.0.js",
    # "js/knockout.mapping.js",
    # "js/slycat-browser.js",
    # "js/slycat-navbar.js",
    # "js/slycat-model.js",
    # End JS loaded by header
    "jquery.layout-latest.min.js",
    "jquery.ba-bbq.min.js",
    "d3.min.js",
    "bookmarker.js",
    "chunker.js",
    "color-switcher.js",
    "jquery.mousewheel.js",
    "jquery.scrollintoview.min.js",
    "jquery.event.drag-2.2.js",
    "slick.core.js",
    "slick.grid.js",
    "slick.rowselectionmodel.js",
    "slick.headerbuttons.js",
    "slick.autotooltips.js",
    "slick.slycateditors.js",
    "popcorn-complete.js",
    "modernizr.custom.01940.js",
    "tracer-image-scatterplots.js",
    "tracer-image-table.js",
    "layout.js",
    "model.js",
    "scatterplot.js",
    "plot-control.js",
    "table.js",
    "movie.js",
    "grid.js",
    "login.js",
    "init.js",
    "load.js",
    "selector-brush.js"
  ]
  context.register_model_bundle("tracer-image", "text/javascript", [
    os.path.join(os.path.join(os.path.dirname(__file__), "js"), js) for js in javascripts
    ])


  # Register CSS
  stylesheets = [
    # This CSS is loaded by header
    # "css/smoothness/jquery-ui-1.10.4.custom.min.css",
    # "css/jquery.qtip.min.css",
    # "css/namespaced-bootstrap.css",
    # "css/slycat.css",
    # End CSS loaded by header
    "slick.grid.css",
    "slick-default-theme.css",
    "slick.headerbuttons.css",
    "slick-slycat-theme.css",
    "model-tracer-image.css",
  ]
  context.register_model_bundle("tracer-image", "text/css", [
    os.path.join(os.path.join(os.path.dirname(__file__), "css"), css) for css in stylesheets
    ])

  # Register images and other resources
  images = [
   # TODO track down images
  ]
  for image in images:
    context.register_model_resource("tracer-image", image, os.path.join(os.path.join(os.path.dirname(__file__), "img"), image))

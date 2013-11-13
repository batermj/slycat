# Copyright 2013, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

"""
Generate a set of timeseries, upload them to Slycat Web Server, and compute a Timeseries Model.

This script computes a Slycat Timeseries Model using a collection of timeseries
generated by summing sine waves with random coefficients.  Use this script as a
starting-point for writing uploading your own data to a Timeseries Model.

A Slycat Timeseries Model requires the following artifacts, which you will have
to provide in your own scripts:

   inputs                     An M x N table containing M input observations with N features each.
   output-0 ... output-(S-1)  One or more timeseries sets, each containing all M timeseries for each of one-or-more output variables.
   output-count               The number of timeseries sets S in the model
   cluster-bin-count          The number of bins for downsampling each timeseries.
   cluster-bin-type           The algorithm used for downsampling.  Currently "naive" is the only allowed value.
   cluster-type               The algorithm used for clustering.  Allowed values are "single", "complete", "average", and "weighted".

Note that for V output variables, you could upload a single timeseries set
containing V variables, or V timeseries sets each containing 1 variable, or
something in-between.

This script uses the latter approach to minimize its memory footprint: we
create a timeseries set with one variable for each of our outputs, allowing us
to generate a single timeseries at a time.
"""

import numpy
import slycat.web.client
import sys

parser = slycat.web.client.option_parser()
parser.add_option("--cluster-bin-count", type="int", default=500, help="Cluster bin count.  Default: %default")
parser.add_option("--cluster-bin-type", default="naive", help="Cluster bin type.  Default: %default")
parser.add_option("--cluster-type", default="average", help="Clustering type.  Default: %default")
parser.add_option("--input-variable-prefix", default="a", help="Input variable prefix.  Default: %default")
parser.add_option("--marking", default="", help="Marking type.  Default: %default")
parser.add_option("--model-name", default="Demo Timeseries Model", help="New model name.  Default: %default")
parser.add_option("--output-variable-count", type="int", default=2, help="Number of output variables in each timeseries.  Default: %default")
parser.add_option("--output-variable-prefix", default="b", help="Output variable prefix.  Default: %default")
parser.add_option("--project-name", default="Demo Timeseries Project", help="New project name.  Default: %default")
parser.add_option("--seed", type="int", default=12345, help="Random seed.  Default: %default")
#parser.add_option("--sample-bundling", type="int", default=10000, help="Maximum number of timeseries samples to send in a single request.  Default: %default")
parser.add_option("--timeseries-count", type="int", default=10, help="Number of timeseries.  Default: %default")
parser.add_option("--timeseries-samples", type="int", default=15000, help="Number of samples in each timeseries.  Default: %default")
parser.add_option("--timeseries-waves", type="int", default=4, help="Number of random sine waves to sum for each timeseries.  Default: %default")
options, arguments = parser.parse_args()

numpy.random.seed(options.seed)

# Generate a set of random coefficients that we'll use later to synthesize our timeseries.
inputs = numpy.hstack([numpy.sort(numpy.random.random((options.timeseries_count, options.timeseries_waves)) * 8 + 1) for output_variable in range(options.output_variable_count)])

# Setup a connection to the Slycat Web Server.
connection = slycat.web.client.connect(options)

# Create a new project to contain our model.
pid = connection.create_project(options.project_name)

# Create the new, empty model.
wid = connection.create_model_worker(pid, "timeseries", options.model_name, options.marking)

# Upload our coefficients as the "inputs" artifact.
input_attributes = [("%s%s" % (options.input_variable_prefix, attribute), "float64") for attribute in range(inputs.shape[1])]
input_dimensions = [("row", "int64", 0, inputs.shape[0])]

connection.start_array_set(wid, "inputs")
connection.create_array(wid, "inputs", 0, input_attributes, input_dimensions)
for attribute, data in enumerate(inputs.T):
  connection.store_array_attribute(wid, "inputs", 0, attribute, data)
connection.finish_array_set(wid, "inputs")

# Upload a collection of timeseries as the "outputs" artifact.
connection.start_array_set(wid, "outputs")

# For each timeseries ...
for timeseries in range(options.timeseries_count):
  sys.stderr.write("Generating timeseries {}.\n".format(timeseries))
  timeseries_attributes = [("time", "float64")] + [("%s%s" % (options.output_variable_prefix, attribute), "float64") for attribute in range(options.output_variable_count)]
  timeseries_dimensions = [("row", "int64", 0, options.timeseries_samples)]
  connection.create_array(wid, "outputs", timeseries, timeseries_attributes, timeseries_dimensions)

  times = numpy.linspace(0, 2 * numpy.pi, options.timeseries_samples)
  connection.store_array_attribute(wid, "outputs", timeseries, 0, times)

  for variable in range(options.output_variable_count):
    coefficients = inputs[timeseries, variable * options.timeseries_waves : (variable+1) * options.timeseries_waves]
    values = numpy.zeros((options.timeseries_samples))
    for k in coefficients:
      values += numpy.sin(times * k) / k
    connection.store_array_attribute(wid, "outputs", timeseries, variable + 1, values)

connection.finish_array_set(wid, "outputs")

# Store the remaining parameters ...
connection.set_parameter(wid, "cluster-bin-count", options.cluster_bin_count)
connection.set_parameter(wid, "cluster-bin-type", options.cluster_bin_type)
connection.set_parameter(wid, "cluster-type", options.cluster_type)

# Signal that we're done uploading artifacts to the model.  This lets Slycat Web Server know that it can start computation.
mid = connection.finish_model(wid)

# Wait for the model to finish computing, then delete the worker.
#connection.join_worker(wid)
#connection.delete_worker(wid)

# Give the user a URL where they can access their new model.
sys.stderr.write("Your new model is located at %s/models/%s\n" % (options.host, mid))

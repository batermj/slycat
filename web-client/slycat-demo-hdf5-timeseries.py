# Copyright 2013, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

"""Synthesizes hdf5 timeseries data suitable for upload as a Slycat Timeseries Model.

This generates a collection of timeseries by summing sine waves with random
coefficients.  Use this script as a starting-point for converting your own data
to hdf5 data suitable for upload to Slycat using the
slycat-hdf5-to-timeseries.py script.

hdf5 timeseries data must be stored in a directory containing the following
files, which you will have to provide in your own scripts:

   inputs.hdf5                A single 1D array containing M input observations with N features (array attributes).
   timeseries-N.hdf5          A set of M 1D arrays, each containing one time variable and V output variables (array attributes).
"""

import argparse
import numpy
import os
import shutil
import slycat.data.hdf5

parser = argparse.ArgumentParser()
parser.add_argument("--force", action="store_true", help="Overwrite existing data.")
parser.add_argument("--input-variable-prefix", default="X", help="Input variable prefix.  Default: %(default)s")
parser.add_argument("--output-variable-count", type=int, default=2, help="Number of output variables in each timeseries.  Default: %(default)s")
parser.add_argument("--output-variable-prefix", default="Y", help="Output variable prefix.  Default: %(default)s")
parser.add_argument("--seed", type=int, default=12345, help="Random seed.  Default: %(default)s")
parser.add_argument("--timeseries-count", type=int, default=10, help="Number of timeseries.  Default: %(default)s")
parser.add_argument("--timeseries-samples", type=int, default=15000, help="Number of samples in each timeseries.  Default: %(default)s")
parser.add_argument("--timeseries-waves", type=int, default=4, help="Number of random sine waves to sum for each timeseries.  Default: %(default)s")
parser.add_argument("output_directory", help="Destination directory that will contain the generated .hdf5 files.")
arguments = parser.parse_args()

if arguments.force:
  shutil.rmtree(arguments.output_directory, ignore_errors=True)
if os.path.exists(arguments.output_directory):
  raise Exception("Destination directory %s already exists.  Use --force to overwrite." % arguments.output_directory)
os.makedirs(arguments.output_directory)

# Generate a set of random coefficients that we'll use later to synthesize our timeseries.
numpy.random.seed(arguments.seed)
inputs = numpy.hstack([numpy.sort(numpy.random.random((arguments.timeseries_count, arguments.timeseries_waves)) * 8 + 1) for output_variable in range(arguments.output_variable_count)])
input_attributes = [("%s%s" % (arguments.input_variable_prefix, attribute), "float64") for attribute in range(inputs.shape[1])]
input_dimensions = [("row", "int64", 0, inputs.shape[0])]

with slycat.data.hdf5.start_array_set(os.path.join(arguments.output_directory, "inputs.hdf5")) as file:
  slycat.data.hdf5.start_array(file, 0, input_attributes, input_dimensions)
  for attribute, data in enumerate(inputs.T):
    slycat.data.hdf5.store_array_attribute(file, 0, attribute, [(0, inputs.shape[0])], data)

# Upload a collection of timeseries as "outputs".
for timeseries in range(arguments.timeseries_count):
  print "Generating timeseries %s" % timeseries
  with slycat.data.hdf5.start_array_set(os.path.join(arguments.output_directory, "timeseries-%s.hdf5" % timeseries)) as file:
    timeseries_attributes = [("time", "float64")] + [("%s%s" % (arguments.output_variable_prefix, attribute), "float64") for attribute in range(arguments.output_variable_count)]
    timeseries_dimensions = [("row", "int64", 0, arguments.timeseries_samples)]
    slycat.data.hdf5.start_array(file, timeseries, timeseries_attributes, timeseries_dimensions)

    times = numpy.linspace(0, 2 * numpy.pi, arguments.timeseries_samples)
    slycat.data.hdf5.store_array_attribute(file, timeseries, 0, [(0, times.shape[0])], times)

    for variable in range(arguments.output_variable_count):
      print "  Generating variable %s" % variable
      coefficients = inputs[timeseries, variable * arguments.timeseries_waves : (variable+1) * arguments.timeseries_waves]
      values = numpy.zeros((arguments.timeseries_samples))
      for k in coefficients:
        values += numpy.sin(times * k) / k
      slycat.data.hdf5.store_array_attribute(file, timeseries, variable + 1, [(0, values.shape[0])], values)


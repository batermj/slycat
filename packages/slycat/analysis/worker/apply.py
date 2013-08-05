# Copyright 2013, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
from __future__ import division

import ast
import numpy

from slycat.analysis.worker.api import log, array, array_iterator
from slycat.analysis.worker.expression import evaluator

class apply_array(array):
  def __init__(self, worker_index, source, attribute_expressions):
    array.__init__(self, worker_index)
    self.source = source
    self.attribute_expressions = attribute_expressions
  def dimensions(self):
    return self.source.dimensions()
  def attributes(self):
    return self.source.attributes() + [attribute for attribute, expression in self.attribute_expressions]
  def iterator(self):
    return self.pyro_register(apply_array_iterator(self))

class symbol_lookup:
  """Helper class that looks-up expression symbols, returning array attributes / dimensions."""
  def __init__(self, iterator, attributes, dimensions):
    self.iterator = iterator
    self.attributes = attributes
    self.dimensions = dimensions
    self.attribute_map = {attribute["name"]:index for index, attribute in enumerate(attributes)}
    self.dimension_map = {dimension["name"]:index for index, dimension in enumerate(dimensions)}
  def __contains__(self, key):
    return key in self.attribute_map or key in self.dimension_map
  def __getitem__(self, key):
    try:
      if key in self.attribute_map:
        return self.iterator.values(self.attribute_map[key])
      if key in self.dimension_map:
        dimension = self.dimension_map[key]
        offset = self.iterator.coordinates()[dimension]
        shape = tuple(self.iterator.shape())
        slices = [slice(end) for end in shape]
        return offset + numpy.mgrid[slices][dimension]
    except Exception as e:
      log.error("symbol_lookup exception: %s", e)

class apply_array_iterator(array_iterator):
  def __init__(self, owner):
    array_iterator.__init__(self, owner)
    self.iterator = owner.source.iterator()
    self.source_attributes = owner.source.attributes()
    self.symbol_lookup = symbol_lookup(self.iterator, self.source_attributes, owner.source.dimensions())
  def __del__(self):
    self.iterator.release()
  def next(self):
    self.iterator.next()
  def coordinates(self):
    return self.iterator.coordinates()
  def shape(self):
    return self.iterator.shape()
  def values(self, attribute):
    if attribute < len(self.source_attributes):
      return self.iterator.values(attribute)

    attribute, expression = self.owner.attribute_expressions[attribute - len(self.source_attributes)]
    #log.debug("Evaluating %s." % ast.dump(expression))
    result = evaluator(self.symbol_lookup).evaluate(expression)
    if isinstance(result, int) or isinstance(result, float):
      temp = numpy.empty(self.iterator.shape())
      temp.fill(result)
      result = temp
    return result.astype(attribute["type"])


# Copyright 2013, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

import time

class Timer(object):
  def __init__(self, clock):
    self._clock = clock
    self.reset()

  def reset(self):
    self._start = self._clock()

  def elapsed(self):
    return self._clock() - self._start

  def interval(self):
    start = self._start
    self._start = self._clock()
    return self._start - start

def processor():
  return Timer(time.clock)

def wallclock():
  return Timer(time.time)

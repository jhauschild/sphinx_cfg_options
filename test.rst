Test Parameters
===============

We first define a ``prm:collection`` called DMRG:

.. prm:collection:: DMRG
   :module: mylib
   :class: A
   :parent: mylib.A

   :param x: Decribe parameter `x` with text.
   :param y: Describe parameter `y` with text.
   :collect TEBD:

Given that we have that, we can define parameters
within that collection with a ``prm:definition``:


.. prm:definition:: DMRG

   :param a: Describe parameter `a` with text.
   :type a: None
   :param mylib.B b: Describe parameter `b` with text.


And here's another test: the TEBD collection.
It should include the parameters from DMRG

.. prm:collection:: TEBD

   :param tebd1: Describe par tebd1. Could contain a ref to :class:`mylib.A` or :prm:entry:`DMRG.b`.
   :param x: `x` parameter of tebd, different form :prm:entry:`DMRG.x`.

See, there you go. You can also link to the collection :prm:coll:`DMRG`, 
and individual parameters like :prm:entry:`DMRG.a` or :prm:entry:`DMRG.b`, or :prm:entry:`DMRG.first` and
:prm:entry:`DMRG.second`.


We can also have a todolist here:

.. todolist ::

There's nothing in?

Test Parameters
===============

The recipe contains `tomato` and `cilantro`.

.. prm:collection:: DMRG
   :module: mylib
   :class: A
   :include: TEBD




.. prm:definition:: DMRG
   :module: mylib
   :class: A

   :param a: Describe parameter `a` with text.
   :type a: None
   :param mylib.B b: Describe parameter `b` with text.


And here's another test.

.. prm:collection:: TEBD

  Some description.


See, there you go. You can also link to the collection :prm:coll:`DMRG`, 
and individual parameters like :prm:entry:`DMRG.a` or :prm:entry:`DMRG.b`

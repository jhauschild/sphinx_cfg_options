Test Parameters
===============

The recipe contains `tomato` and `cilantro`.

.. prm:collection:: DMRG
  :contains: N_max x asdf

  Some text.


.. prm:definition:: DMRG
   :module: mylib
   :class: A
   
   :param a: Describe parameter `a` with text.
   :type a: int
   :param b: Descripbe parameter `b` with text.
   :type b: mylib.B


And here's another test.

.. prm:collection:: TEBD
  :contains: dt x N_steps

  Some description.



See, there you go. You can also link to :prm:coll:`DMRG`

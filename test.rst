Config Parameters
=================

Motivation
----------
During coding, I often define a (nested) dictionary `config` which collects all the necessary parameters 
for setting up a simulation (or equivalently: creating a complicated object), i.e., I have something like a
`setup(config)` function, which sets up the whole thing, and the `config` dictionary contains all the parameters 
required to run the simulation/create the complicated object.
The `config` then gets passed on to other functions/classes, which can read out config values and take appropriate
actions.
The motivation for this extension is that I want to document the entries of the `config` dictionary 
*close to the code using them*, not in the documentation of the `setup` function.
However, inside the `setup` function, we need to collect all the possible values of the `config` to give the user an idea
of what he options he can choose. That's what this extension does.


Example
-------

Consider a factory producing vehicles. 
It can define the following config with a `.. cfg:collection:: Vehicle` directive:

.. cfg:collection:: Vehicle

   :param max_speed: Maximum speed of the vehicle.
   :type max_speed: float

In the function that sets up the engine, we notice that we need another
parameter: the type of the fuel. So we add a ``.. cfg:definition:: Vehicle``
directive to document another parameter for all vehicles.

.. cfg:definition:: Vehicle

   :param str fuel: Type of the used fuel, can be 'gasoline' or 'electric'.


Now we want to setup a factory for cars.
The car factory can use the vehicle factory, so the `config` of the car factory
should include the `config` of the vehicle factory.
This is indicated by a ``:include Vehicle:`` in the body of the collection:

.. cfg:collection:: Car

   :include Vehicle:
   :param int doors: Number of doors.

You can also link to the collections with :cfg:coll:`Vehicle` and :cfg:coll:`Car`,
and to individual parameters like :cfg:entry:`Vehicle.max_speed` or :cfg:entry:`Car.max_speed`, 
:cfg:entry:`Model.second`.

Even one step further, we can have a collection which just includes other collections. Note that the include is recursive by
default. In case of duplicate parameter keys, all are shown.

.. cfg:collection:: BMW

   :include Car:
   :param int doors: The doors.


Now we've covered everything. As a final remark: you can include a collection of the same name at multiple positions in
the documentation. (And you don't have to set the ``:include Car:`` again in that case)

.. cfg:collection:: BMW



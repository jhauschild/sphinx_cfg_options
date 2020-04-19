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
It can define the following config with a `.. cfg:config:: Vehicle` directive:

.. cfg:config:: Vehicle

   .. cfg:option:: max_speed
      :type: float

      Maximum speed of the vehicle.

In the function that sets up the engine, we notice that we need another
parameter: the type of the fuel. So we add a ``.. cfg:definition:: Vehicle``
directive to document another parameter for all vehicles.


.. cfg:option:: fuel
    :type: string
    :default: "gasoline"

    Type of the used fuel, can be 'gasoline' or 'diesel'.

Now we want to setup a factory for cars.
The car factory can use the vehicle factory, so the `config` of the car factory
should include the `config` of the vehicle factory.
This is indicated by the option ``:include: Vehicle`` in the body of the config:

.. cfg:config:: Car
   :include: Vehicle


You can also link to the configs with :cfg:config:`Vehicle` and :cfg:config:`Car`,
and to individual parameters like :cfg:option:`Vehicle.fuel` or :cfg:option:`Car.fuel`;
they latter two point to the same definition in this case.

Of course, a new config can also define it's own parameters in addition to using the `include`.
Also, note that the include is recursive, as shown in the following example.
In case of duplicated parameter keys, all definitions are listed.

.. cfg:config:: ElectricCar
   :include: Car

   .. cfg:option:: fuel
      
      Additional choice ``"battery"`` on top of what :cfg:option:`Vehicle.fuel` defines.

   .. cfg:option:: hybrid
      :type: bool
      :default: False
      
      Wheter the car has both an internal combustion engine and an electric motor, or not.

As you might have expected, the references :cfg:option:`Vehicle.fuel` and :cfg:option:`ElectricCar.fuel` now
point to the two different definitions.

One last hint: you can include a config of the same name at multiple positions in the documentation.
However, all but one should have `:noindex:` set, and only the one not having `:noindex:` can define the includes.

.. cfg:config:: ElectricCar
    :noindex:


Config Options, a Sphinx extension
==================================

.. image:: https://readthedocs.org/projects/sphinx-cfg-options/badge/?version=latest
    :target: https://sphinx-cfg-options.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

This is the `README.rst` file of the repo.
I recommend to compare the raw text on `github <https://github.com/jhauschild/sphinx_cfg_options>`_ 
with the `built documentation <https://sphinx-cfg-options.readthedocs.io/en/latest/README.html>`_.

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

What this is
------------
This (more precisely, the file `ext/sphinx_cfg_options.py`) is an extension for `Sphinx <https://www.sphinx-doc.org>`_.
It adds the domain `cfg` with directives ``.. cfg:config:: config_name`` to document a config (= a bunch of options)
and ``.. cfg:option:: option_name`` (= an entry of a config). The roles ``:cfg:config:`` and ``:cfg:option:`` 
allow references to these definitions from anywhere in the documentation.
Moreover, the options of a given `config` are collected and summarized at the beginning of the config description.
Further, there are two indices provided, which list all the options and configs at a single place and enhance search
results:

* :ref:`cfg-config-index`
* :ref:`cfg-option-index`


Example usage
-------------

Consider a factory producing vehicles. 
It can define the following config with a ``.. cfg:config:: Vehicle`` directive.

.. cfg:config:: Vehicle

   max_speed : float = 220.
      Maximum speed of the vehicle in km/h.

      This description might go over multiple lines and gets fully parse.

      .. note ::

          The table above only shows the first line.

In the function that sets up the engine, we notice that we need another
parameter: the type of the fuel. 
If we want to define only a single option value, we can use the
``.. cfg:option::`` directive:

.. cfg:option:: fuel
    :config: Vehicle
    :type: str
    :default: "gasoline"

    Type of the used fuel, ``"gasoline"`` or ``"diesel"``.


Now we want to setup a factory for cars.
The car factory can use the vehicle factory, so the `config` of the car factory
should include the `config` of the vehicle factory.
This is indicated by the option ``:include: Vehicle`` in the body of the config:

.. cfg:config:: Car
   :include: Vehicle


You can also link to the configs with :cfg:config:`Vehicle` and :cfg:config:`Car`,
and to individual parameters like :cfg:option:`Vehicle.fuel` or :cfg:option:`Car.fuel`;
the latter two point to the same definition in this case.

Of course, a new config can also define it's own parameters in addition to using the `include`.
Also, note that the include is recursive, as shown in the following example.
In case of duplicated parameter keys, all definitions are listed.

.. cfg:config:: ElectricCar
   :include: Car

   fuel :
      Additional choice ``"battery"`` on top of what :cfg:option:`Vehicle.fuel` defines.
   hybrid : bool = False
      Whether the car has both an internal combustion engine and an electric motor, or not.

As you might have expected, the references :cfg:option:`Vehicle.fuel` and :cfg:option:`ElectricCar.fuel` now
point to the two different definitions.

.. tip ::
    You can include a config of the same name at multiple positions in the documentation, and you don't need to 
    repeat all the options again. If you want to specify what the `:cfg:config:` role points to, you can 
    use the `:master:` option in one of the ``.. cfg:config`` directives, as demonstrated in the following.

.. cfg:config:: ElectricCar
    :master:

Installation
------------
You need Sphinx version >=3.0.
Put the `ext/sphinx_cfg_options.py` somewhere where it can be imported as python module during the sphinx build.
(This can be acchieved by updating ``sys.path`` inside the `conf.py`, take a look at the example provided in this repo).

.. cfg:config:: conf.py options
    
    cfg_options_recursive_includes = True
         If config A includes B and B includes C, this option sets whether A automatically includes C.
    cfg_options_parse_numpydoc_style_options = True
        Allows to disable the parsing of the ``.. cfg:config::`` content.
        If disabled, you need to use the ``.. cfg:option::`` for all context.
    cfg_options_summary : "table", "list", or None = "table"
        Choose how to format the summary at the g
    cfg_options_table_add_header = True
        Include the header "option default summary" in the option tables in the beginnning of a config.



Limitations
-----------
- Right now, the "summary" of an option to be included into the summary table of a config does not get parsed.
- Parsing of the `optionname : type = value` line is probably not very stable.

License
-------
MIT license, feel free to reuse the extension in your own projects.

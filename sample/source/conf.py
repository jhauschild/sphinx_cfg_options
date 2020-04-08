# -*- coding: utf-8 -*-
extensions = ['sphinx.ext.coverage',
              'sphinx.ext.viewcode',
              'sphinxparameters']

source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'parameter-test'
copyright = u'2020, Johannes Hauschild'
author = 'Johannes Hauschild'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

language = None

exclude_patterns = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


html_theme = 'alabaster'

html_static_path = ['_static']

# This is required for the alabaster theme
# refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'relations.html',  # needs 'show_related': True theme option to display
        'searchbox.html',
        'donate.html',
    ]
}

# Output file base name for HTML help builder.
htmlhelp_basename = 'parameter-testdoc'

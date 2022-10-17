# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.abspath('./ext'))

extensions = ['sphinx.ext.coverage',
              'sphinx.ext.viewcode',
              'sphinx.ext.autodoc',
              'sphinx.ext.napoleon',
              'sphinx.ext.todo',
              'sphinx_cfg_options']

source_suffix = '.rst'

todo_include_todos = True

needs_sphinx = '3.0'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Sphinx Config Options'
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

language = 'en'

exclude_patterns = []

autodoc_default_options = {'inherited-members': True}

# ----- Options for the the extension -------

#cfg_options_recursive_includes = True
#cfg_options_parse_numpydoc_style_options = True
cfg_options_parse_comma_sep_names = True
#cfg_options_table_summary = "table"  # "table", "list" or None
#cfg_options_table_add_header = True
# cfg_options_default_in_summary_table = True
# cfg_options_unique = True

# ----- Output options ----------------------

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

#  html_theme = 'alabaster'
html_theme = 'sphinx_rtd_theme'

html_static_path = ['_static']

html_css_files = ['custom.css']  # to highlight targets


# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from unittest.mock import MagicMock

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../src'))

# Mock modules that may not be available during documentation build
class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

MOCK_MODULES = [
    'sotodlib', 'sotodlib.core', 'sotodlib.core.Context',
    'radical', 'radical.utils', 'radical.pilot',
    'slurmise', 
    'networkx',
]
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'SO Campaign Manager'
copyright = '2024, Simons Observatory'
author = 'Giannis Paraskevakos'
release = '0.0.3'
version = '0.0.3'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.githubpages',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# Try to use Read the Docs theme, fallback to alabaster
try:
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_options = {
        'navigation_depth': 4,
        'collapse_navigation': False,
        'sticky_navigation': True,
        'includehidden': True,
        'titles_only': False,
        'display_version': True,
    }
except ImportError:
    html_theme = 'alabaster'
    html_theme_options = {
        'description': 'Workflow orchestration for SO mapmaking campaigns',
        'github_user': 'simonsobs',
        'github_repo': 'so_campaign_manager',
        'github_button': True,
        'github_banner': True,
        'show_related': True,
        'show_powered_by': True,
    }

html_static_path = ['_static']

# Custom footer
html_context = {
    'display_github': True,
    'github_user': 'simonsobs',
    'github_repo': 'so_campaign_manager',
    'github_version': 'main',
    'conf_py_path': '/docs/',
}

# Custom CSS (if needed)
html_css_files = [
    'custom.css',
]

# Footer text
html_show_sphinx = True
html_show_copyright = True

# Logo and favicon (optional - add if files exist)
# html_logo = '_static/logo.png'
# html_favicon = '_static/favicon.ico'

# -- Extension configuration -------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Configure to exclude private members from main documentation
def skip_private(app, what, name, obj, skip, options):
    """Skip private members (starting with _) except in complete API reference."""
    # Get the current document being processed
    docname = getattr(app.env, 'docname', '')
    
    # Skip private members in main API documentation, but not in complete reference
    if name.startswith('_') and name != '__init__' and 'api_complete' not in docname:
        return True
    return skip

def add_custom_footer(app, pagename, templatename, context, doctree):
    """Add custom footer noting documentation was created by Claude Code."""
    context['custom_footer'] = """
    <div style="margin-top: 2em; padding-top: 1em; border-top: 1px solid #ccc; font-size: 0.9em; color: #666;">
        <p>
            This documentation was created with assistance from
            <a href="https://claude.ai/code" target="_blank">Claude Code</a>,
            an AI coding assistant by Anthropic.
        </p>
    </div>
    """

def setup(app):
    app.connect('autodoc-skip-member', skip_private)
    app.connect('html-page-context', add_custom_footer)

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pydantic': ('https://docs.pydantic.dev/latest/', None),
}

# Autosummary
autosummary_generate = True
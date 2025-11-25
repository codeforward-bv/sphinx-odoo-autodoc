import os
import sys
from sphinx.application import Sphinx
from . import VERSION


try:
    import odoo
    from odoo import fields
    ODOO_AVAILABLE = True
except ImportError:
    ODOO_AVAILABLE = False


def setup(app: Sphinx) -> dict:
    """
    Setup function used by Sphinx, when loading willdooit-odoo-autodoc as a Sphinx extension,

    :param app: Sphinx instance.
    :type app: Sphinx
    :return: Dictionary to report extension details back to Sphinx.
    :rtype: dict
    """
    app.add_config_value('odoo_root_path', '', True)
    app.add_config_value('odoo_addons_path', [], True)
    app.add_config_value('odoo_config_path', '', True)
    app.connect('builder-inited', load_modules)
    app.connect('autodoc-process-docstring', filter_odoo_docstrings)
    app.connect('autodoc-skip-member', skip_odoo_fields)

    return {'version': VERSION}


def load_modules(app: Sphinx) -> None:
    """
    Parse config values and initialise Odoo modules.

    :param app: Sphinx instance.
    :type app: Sphinx
    """
    odoo_config_args = []

    if app.env.config.odoo_config_path:
        odoo_config_args.append('-c')
        odoo_config_args.append(app.env.config.odoo_config_path)

    addons_path = ','.join(app.env.config.odoo_addons_path)
    if not addons_path:
        addons_path = os.environ.get('ODOO_ADDONS_PATH', '')

    if addons_path:
        odoo_config_args.append('--addons-path')
        odoo_config_args.append(addons_path)

    if app.env.config.odoo_root_path:
        sys.path.append(app.env.config.odoo_root_path)

    # Initialise Odoo sys path overrides
    odoo.tools.config._parse_config(odoo_config_args)
    odoo.modules.initialize_sys_path()


def skip_odoo_fields(app, what, name, obj, skip, options):
    """
    Skip default Odoo fields to reduce noise in documentation.
    """
    # List of fields to exclude
    EXCLUDED_FIELDS = {
        'write_date',
        'write_uid',
        'create_uid',
        'create_date',
        'display_name',
        '__last_update'
    }
    
    if name in EXCLUDED_FIELDS:
        return True
    
    return skip


def filter_odoo_docstrings(app, what, name, obj, options, lines):
    """Filter out unwanted parameters from Odoo field docstrings and inject type info."""

    if isinstance(obj, fields.Field):
        # If the docstring is inherited from the class (generic Odoo docstring), clear it.
        # We check if the lines (which Sphinx extracted) match the generic class docstring.
        # This preserves custom docstrings defined in the source code.
        generic_doc = type(obj).__doc__
        if generic_doc:
            # Normalize whitespace for comparison
            generic_doc_normalized = " ".join(generic_doc.split())
            lines_normalized = " ".join(" ".join(lines).split())
            
            if generic_doc_normalized == lines_normalized:
                lines[:] = []

        # Inject Field Type and Comodel info
        field_type = obj.type
        header_lines = [f"**Type**: {field_type}"]

        if field_type in ('many2one', 'one2many', 'many2many'):
            comodel = obj.comodel_name
            if comodel:
                header_lines.append(f"**Comodel**: ``{comodel}``")

        # Inject Help Text
        if obj.help:
            header_lines.append("")
            header_lines.append(f"**Help**: {obj.help}")

        header_lines.append("") # Blank line separator

        # Prepend to lines
        lines[0:0] = header_lines

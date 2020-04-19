# TODO: config values, e.g. 'recursive'?
# TODO: use python domain?


# TODO: allow includes in definitions as well;
# use `ConfigEntry` with additional `typ` in domain.data['def'] for *all* definitions
# TODO: don't use fields, instead define a separate `CfgOption` directive

# TODO: def id could be defined through context!
# TODO: use numpydoc-style definitions of parameters

# TODO: should we switch to defining entries as separate directives,
# instead of hacking the fields to contain anchors?
# That's how it should work, really...


from collections import namedtuple

import docutils
from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives
import sphinx
from sphinx.domains import Domain, Index, ObjType
from sphinx.domains.python import PyTypedField
from sphinx.domains.std import StandardDomain
from sphinx.errors import NoUri
from sphinx.util.docfields import Field, TypedField, GroupedField
from sphinx.roles import XRefRole
from sphinx.directives import ObjectDescription
from sphinx.util.nodes import make_id, make_refnode
from sphinx.util.docutils import new_document
from sphinx import addnodes
from sphinx.util.docutils import SphinxDirective

from sphinx.util import logging

logger = logging.getLogger(__name__)

# ConfigEntry is used in CfgDomain.data['config']
ConfigEntry = namedtuple('ConfigEntry', "fullname, dispname, typ, docname, anchor, includes")

# OptionEntry is used in CfgDomain.data['config2options']
OptionEntry = namedtuple('OptionEntry', "fullname, dispname, config, docname, anchor, context")

# ObjectsEntry is returned by Domain.get_objects()
ObjectsEntry = namedtuple('ObjectsEntry', "name, dispname, typ, docname, anchor, prio")

# IndexEntry is retured by Index.generate()
IndexEntry = namedtuple('IndexEntry', "name, subtype, docname, anchor, extra, qualifier, descr")


class cfgconfig(nodes.General, nodes.Element):
    """A node to be replaced by a list of options for a given `config`.

    The replacement happens in :meth:`ConfigNodeProcessor.process`."""
    def __init__(self, config, can_collapse=True):
        super().__init__('')
        self.config = config
        self.can_collapse = can_collapse


class ConfigField(GroupedField):
    """Field collecting all the `fieldarg` given in a `cfgconfig` node."""
    def make_field(self, types, domain, items, env=None):
        assert env is not None   # don't expect this to happen

        fieldname = nodes.field_name('', self.label)
        entries = [fieldarg for (fieldarg, content) in items]
        config = entries[0]  # ensured by CfgConfig.before_content().
        config_entry = env.domaindata['cfg']['config'].get(config, None)
        if config_entry is not None:
            config_includes = config_entry.includes
            for incl in entries:
                if incl not in config_includes:
                    config_includes.append(incl)
        bodynode = cfgconfig(config, self.can_collapse)
        fieldbody = nodes.field_body('', bodynode)
        return nodes.field('', fieldname, fieldbody)


class IndexedTypedField(PyTypedField):
    def make_xref(self, rolename, domain, target,
                  innernode=addnodes.literal_emphasis,
                  contnode=None, env=None):
        if rolename == 'py-class':
            return super().make_xref("class", "py", target, innernode, contnode, env)
        return Field.make_xref(self, rolename, domain, target, innernode, contnode, env)

    def make_field(self, types, domain, items, env=None):
        """Like TypedField.make_field(), but also call `self.add_entry_target_and_index`."""
        assert env is not None   # don't expect this to happen

        entries = []

        for fieldarg, content in items:
            par = nodes.paragraph()
            par.extend(self.make_xrefs(self.rolename, domain, fieldarg,
                                       addnodes.literal_strong, env=env))
            if fieldarg in types:
                par += nodes.Text(' (')
                # NOTE: using .pop() here to prevent a single type node to be
                # inserted twice into the doctree, which leads to
                # inconsistencies later when references are resolved
                fieldtype = types.pop(fieldarg)
                if len(fieldtype) == 1 and isinstance(fieldtype[0], nodes.Text):
                    typename = fieldtype[0].astext()
                    par.extend(self.make_xrefs(self.typerolename, domain, typename,
                                               addnodes.literal_emphasis, env=env))
                else:
                    par += fieldtype
                par += nodes.Text(')')
            par += nodes.Text(' -- ')
            par += content
            self.add_entry_target_and_index(fieldarg, par, env)  # <--- this is new!
            entries.append(par)

        fieldname = nodes.field_name('', self.label)
        if len(items) == 1 and self.can_collapse:
            bodynode = entries[0]
        else:
            bodynode = self.list_type()
            for entry in entries:
                bodynode += nodes.list_item('', entry)
        fieldbody = nodes.field_body('', bodynode)
        return nodes.field('', fieldname, fieldbody)

    def add_entry_target_and_index(self, fieldname, content, env, noindex=False):
        config = env.ref_context['cfg:config']
        context = env.ref_context.get('cfg:context', None)
        assert config is not None
        name = "%s.%s" % (config, fieldname)
        anchor = "cfg-option-%d" % env.new_serialno('cfg-option')
        content['ids'].append(anchor)
        content['ids'].append("cfg-%s" % name)

        option_entry = OptionEntry(fullname=name,
                                  dispname=fieldname,
                                  config=config,
                                  docname=env.docname,
                                  anchor=anchor,
                                  context=context,
                                  )
        config_entries = env.domaindata['cfg']['config2options'].setdefault(config, [])
        config_entries.append(option_entry)


class CfgDefinition(ObjectDescription):

    required_arguments = 1

    option_spec = {
        'noindex': directives.flag,
        'nolist': directives.flag,  # TODO use this
        'context': directives.unchanged,
    }

    doc_field_types = [
        IndexedTypedField('definition', label='Definitions',
                      names=('param', 'param', 'parameter', 'arg', 'argument', 'keyword', 'kwarg', 'kwparam'),
                      rolename='',  # HACK
                      typerolename='py-class', typenames=('paramtype', 'type'),
                      can_collapse=True),
        ConfigField('config', label='Options',
                      names=('incl', 'include'),
                      can_collapse=True)
    ]

    def handle_signature(self, sig, signode):
        # TODO: use below; might want to use PyXRefMixin for that?
        # modname = self.options.get('module', self.env.ref_context.get('py:module'))
        # clsname = self.options.get('cls', self.env.ref_context.get('py:class'))
        # fullname = (modname + '.' if modname else '') + sig
        signode += addnodes.desc_annotation('Config ', 'Config ')
        signame = nodes.Text(sig)
        if 'noindex' in self.options:
            signame = addnodes.pending_xref(sig, signame,
                                            refdomain='cfg', reftype='config', reftarget=sig)
        signode += addnodes.desc_name(sig, '', signame)

        name = sig  # TODO make name a tuple `(fullname, dispname)` as for PyObject?
        return name

    def add_target_and_index(self, name, sig, signode):
        node_id = make_id(self.env, self.state.document, 'cfg-config', name)
        signode['ids'].append(node_id)
        self.state.document.note_explicit_target(signode)
        if 'noindex' not in self.options:
            obj_entry = ObjectsEntry(name, sig, 'config', self.env.docname, node_id, 0)
            self.env.domaindata['cfg']['def'].append(obj_entry)
            config_entry = ConfigEntry(fullname=name,
                                   dispname=name,
                                   typ="config",
                                   docname=obj_entry.docname,
                                   anchor=obj_entry.anchor,
                                   includes=[name],
                                   )
            other = self.env.domaindata['cfg']['config'].get(name, None)
            if other:
                logger.warning('duplicate object description of config %s, '
                               'other instance in %s, use :noindex: for one of them',
                               name, other.docname, location=signode)
            # TODO: warn about duplicates
            self.env.domaindata['cfg']['config'][name] = config_entry

            # TODO: rewrite this
            obj_entry = ObjectsEntry(name, sig, 'def', self.env.docname, node_id, 2)
            self.env.domaindata['cfg']['def'].append(obj_entry)

    def before_content(self):
        # save context
        if self.names:
            name = self.names[-1]  # what was returned by `handle_sig`
            self.env.ref_context['cfg:config'] = name
        if 'context' in self.options:
            self.env.ref_context['cfg:context'] = context = self.options['context']

        # HACK: insert `:include <name>:` line before content
        self.content.insert(0, ":include " + name + ":", (self.state.document, ), offset=0)
        super().before_content()

    # def after_content(self):
    #     if 'cfg:config' in self.env.ref_context:
    #         del self.env.ref_context['cfg:config']
    #     super().after_content()

    def run(self):
        context_name = self.env.temp_data.get('object', None)
        if isinstance(context_name, tuple):
            context_name = context_name[0]
        self.env.ref_context['cfg:context'] = context_name
        res = super().run()
        return res


class CfgOption(ObjectDescription):
    option_spec = {
        'noindex': directives.flag,
        'context': directives.unchanged,
        'config': directives.unchanged,
        'type': directives.unchanged,
        'value': directives.unchanged,
    }

    def handle_signature(self, sig, signode):
        name = sig  # TODO make name a tuple `(fullname, dispname)` as for PyObject?
        # TODO: use below; might want to use PyXRefMixin for that?
        config = self.options.get('config', self.env.ref_context.get('cfg:config', None))
        if config is None:
            logger.warning("config option with unknown config")
            config = "UNKNOWN"
        fullname = config + '.' + name
        signode += addnodes.desc_annotation('option ', 'option ')
        signode += addnodes.pending_xref(sig, addnodes.desc_addname(config, config),
                                         refdomain='cfg', reftype='config', reftarget=config)
        signode += addnodes.desc_addname('', '.')

        signode += addnodes.desc_name(sig, '', nodes.Text(sig))

        typ = self.options.get('type')
        if typ:
            signode += addnodes.desc_annotation(typ, ': ' + typ)

        value = self.options.get('value')
        if value:
            signode += addnodes.desc_annotation(value, ' = ' + value)

        return fullname, config


    def add_target_and_index(self, name_config, sig, signode):
        fullname, config = name_config
        context = self.options.get('config', self.env.ref_context.get('cfg:config', None))
        node_id = make_id(self.env, self.state.document, 'cfg-opt', fullname)
        signode['ids'].append(node_id)
        self.state.document.note_explicit_target(signode)
        if 'noindex' not in self.options:
            option_entry = OptionEntry(fullname=fullname,
                                       dispname=fullname[len(config) + 1:],
                                       config=config,
                                       docname=self.env.docname,
                                       anchor=node_id,
                                       context=context,
                                       )
            config_entries = self.env.domaindata['cfg']['config2options'].setdefault(config, [])
            config_entries.append(option_entry)


class CfgCurrentConfig(SphinxDirective):
    """
    This directive is just to tell Sphinx that we're documenting
    stuff in module foo, but links to module foo won't lead here.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}  # type: Dict

    def run(self):
        # TODO: python context?
        configname = self.arguments[0].strip()
        if configname == 'None':
            self.env.ref_context.pop('cfg:config', None)
        else:
            self.env.ref_context['cfg:config'] = configname
        return []


class ConfigNodeProcessor:
    def __init__(self, app, doctree, docname):
        self.env = app.builder.env
        self.builder = app.builder
        self.domain = app.env.get_domain('cfg')
        self.docname = docname

        self.process(doctree)

    def process(self, doctree):
        for node in doctree.traverse(cfgconfig):
            config = node.config # TODO: include more configs
            options = self.domain.configs.get(config, [])

            new_content = [self.create_option_reference(o, config) for o in options]
            if len(new_content) > 1 or not node.can_collapse:
                listnode = nodes.bullet_list()
                for entry in new_content:
                    listnode += nodes.list_item('', entry)
                new_content = listnode
            node.replace_self(new_content)


    def create_option_reference(self, option, config):

        # TODO: include link to definition and name category if different

        par = nodes.paragraph()
        # OptionEntry = namedtuple('OptionEntry', "name, dispname, config, docname, anchor, context")
        innernode = addnodes.literal_strong(option.dispname, option.dispname)
        par += self.make_refnode(option.docname, option.anchor, innernode)
        if option.config != config:
            par += nodes.Text(' (from ')
            par += self._make_config_xref(option.config)
            par += nodes.Text(')')
        if option.context is not None:
            par += nodes.Text(" in ")
            par += addnodes.literal_emphasis(option.context, option.context)
        return par

    def make_refnode(self, docname, anchor, innernode):
        try:
            refnode = make_refnode(self.builder, self.docname, docname, anchor, innernode)
        except NoUri:  # ignore if no URI can be determined, e.g. for LaTeX output
            refnode = innernode
        return refnode

    def _make_config_xref(self, config):
        node = nodes.Text(config, config)
        match = [(obj_entry.docname, obj_entry.anchor)
                 for obj_entry in self.domain.get_objects()
                 if obj_entry.name == config and obj_entry.typ == 'config']
        if len(match) > 0:
            docname, anchor = match[0]
            node = self.make_refnode(docname, anchor, node)
        return node


# TODO: which indices do we need?
class CfgOptionIndex(Index):
    name = 'option'
    localname = 'Config Option Index'
    shortname = 'Config Option'

    def generate(self, docnames=None):
        content = {}
        for config, options in self.domain.data['config2options'].items():
            for option_entry in options:
                ind_entry = IndexEntry(name=option_entry.dispname,
                                       subtype=0,
                                       docname=option_entry.docname,
                                       anchor=option_entry.anchor,
                                       extra=config,
                                       qualifier='',
                                       descr='')
                content.setdefault(config, []).append(ind_entry)
        content = [(k, content[k]) for k in sorted(content.keys())]
        return (content, True)


class CfgConfigIndex(Index):
    name = 'config'
    localname = 'Config Index'
    shortname = 'Config Index'

    def generate(self, docnames=None):
        content = {}
        items = self.domain.get_objects()
        items = [entry for entry in items if entry.typ != "option"]
        items = sorted(items, key=lambda item: item[1])
        for name, dispname, typ, docname, anchor, prio in items:
            lis = content.setdefault(dispname[0].upper(), [])
            lis.append((
                dispname, 0, docname,
                anchor,
                docname, '', typ
            ))
        re = [(k, v) for k, v in sorted(content.items())]
        return (re, True)


class CfgDomain(Domain):
    name = 'cfg'
    label = 'Parameter Configs'

    obj_types = {
        'config':  ObjType('config', 'config'),
        'option':  ObjType('option', 'option'),
        'def':  ObjType('definiton', 'def'),
    }

    roles = {
        'config': XRefRole(),
        'option': XRefRole(),
        'def': XRefRole(),
    }

    directives = {
        'config': CfgDefinition,
        'currentconfig': CfgCurrentConfig,
        'myoption': CfgOption,
    }

    indices = {
        CfgConfigIndex,
        CfgOptionIndex,
    }

    initial_data = {
        'config': {}, # config_name -> ConfigEntry
        'def': [],  # ObjectsEntry
        'config2options': {}, # config_name -> List[OptionEntry]
    }

    def clear_doc(self, docname):
        config_data = self.data['config']
        for name, config_entry in list(config_data.items()):
            if config_entry.docname == docname:
                del config_data[name]
        self.data['def'] = [entry for entry in self.data['def'] if entry.docname != docname]
        for config_name, entries_list in self.data['config2options'].items():
            filered_entries = [entry for entry in entries_list if entry.docname != docname]
            self.data['config2options'][config_name] = filered_entries

    # TODO: needed?
    # def get_full_qualified_name(self, node):
    #     """Return full qualified name for a given node"""
    #     return "{}.{}.{}".format('cfg',
    #                              type(node).__name__,
    #                              node.arguments[0])

    def get_objects(self):
        for config_entry in self.data['config'].values():
            yield ObjectsEntry(config_entry.fullname,
                               config_entry.dispname,
                               'config',
                               config_entry.docname,
                               config_entry.anchor,
                               prio=1)
        for param_list in self.data['config2options'].values():
            for option_entry in param_list:
                yield ObjectsEntry(option_entry.fullname,
                                   option_entry.dispname,
                                   'config',
                                   option_entry.docname,
                                   option_entry.anchor,
                                   prio=1)
        for obj_entry in self.data['def']:
            yield obj_entry


    def resolve_xref(self, env, fromdocname, builder, typ,
                     target, node, contnode):
        if not target:
            return None
        if typ == "config":
            config = self.data['config'].get(target, None)
            if config is None:
                return None
            return make_refnode(builder, fromdocname, config.docname, config.anchor, contnode,
                                config.dispname)
        elif typ == "option":
            config2options = self.data['config2options']
            split = target.split('.')
            if len(split) < 2:
                return None
            for i in range(1, len(split)):
                config, entry_name = '.'.join(split[:i]), '.'.join(split[i:])
                for option_entry in self.configs.get(config, []):
                    if option_entry.dispname == entry_name:  # match!
                        return make_refnode(builder,
                                            fromdocname,
                                            option_entry.docname,
                                            option_entry.anchor,
                                            contnode,
                                            option_entry.dispname)
            return None
        return None


    @property
    def configs(self):
        """dict config_name -> List[OptionEntry], recursively with `includes`."""
        configs = getattr(self, '_configs', None)
        if configs is None:
            self._configs = configs = self._get_configs_with_includes()
        return configs

    @property
    def includes(self):
        """dict config_name -> List[config_name], recursively."""
        includes = getattr(self, '_includes', None)
        if includes is None:
            self._includes = includes = {}
            for config in self.data['config'].keys():
                if config not in includes:  # _get_recursive_includes might have inserted it already
                    includes[config] = self._get_recursive_includes(config)
        return includes

    def _get_configs_with_includes(self):
        # build recursive configs from "flat" configs in self.data
        res = {}
        config2options = self.data['config2options']
        config_names = set(self.data['config'].keys()).union(set(config2options.keys()))
        for config in config_names:
            includes = self.includes.get(config, [config])
            prio = dict((c_incl, i) for i, c_incl in enumerate(includes))
            options = []
            for config_incl in includes:
                options.extend(config2options.get(config_incl, []))
            res[config] = sorted(options, key=lambda e: (e.dispname.lower(), prio[e.config]))
        return res

    def _get_recursive_includes(self, config):
        recursive = True # TODO: option to disable recursive includes
        config_entry = self.data['config'].get(config, None)
        if config_entry is None:
            logger.warning("asked to include unknown config %s", config)
            return []

        # TODO: rewrite this to make recursive use of the method itself.
        # order should be given in the same way as methods are resolved for classes!
        config2incl = {config: entry.includes for config, entry in self.data['config'].items()}
        includes = config2incl.get(config, [config])[:]
        assert includes[0] == config
        if recursive:
            check_recursive = includes[1:]
            checked = set([config])
            while len(check_recursive) > 0:
                check = check_recursive.pop(0)
                checked.add(check)
                for incl in config2incl.get(check, [])[1:]:
                    if incl in includes:
                        continue
                    includes.append(incl)
                    check_recursive.append(incl)
        return includes


def setup(app):
    app.add_domain(CfgDomain)

    app.add_node(cfgconfig)
    app.connect('doctree-resolved', ConfigNodeProcessor)

    StandardDomain.initial_data['labels']['cfg-config-index'] =\
        ('cfg-config', '', 'Config Definiton Index')
    StandardDomain.initial_data['labels']['cfg-option-index'] =\
        ('cfg-option', '', 'Config Options Index')

    return {'version': '0.1'}

# TODO: further config values

# TODO: add event before parsing the content
# TODO: can we avoid requiring a newline after the directive header?

import re
from collections import namedtuple

import docutils
from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
import sphinx
from sphinx.domains import Domain, Index, ObjType
from sphinx.domains.std import StandardDomain
from sphinx.errors import NoUri
from sphinx.roles import XRefRole
from sphinx.directives import ObjectDescription
from sphinx.util.nodes import make_id, make_refnode
from sphinx.util.docutils import new_document
from sphinx import addnodes
from sphinx.util.docutils import SphinxDirective

from sphinx.util import logging

logger = logging.getLogger(__name__)

# ConfigEntry is used in CfgDomain.data['config']
ConfigEntry = namedtuple('ConfigEntry', "fullname, dispname, docname, anchor, master, includes")

# OptionEntry is used in CfgDomain.data['config2options']
OptionEntry = namedtuple('OptionEntry', "fullname, dispname, config, docname, anchor, context")

# ObjectsEntry is returned by Domain.get_objects()
ObjectsEntry = namedtuple('ObjectsEntry', "name, dispname, typ, docname, anchor, prio")

# IndexEntry is retured by Index.generate()
IndexEntry = namedtuple('IndexEntry', "name, subtype, docname, anchor, extra, qualifier, descr")


class cfgconfig(nodes.General, nodes.Element):
    """A node to be replaced by a list of options for a given `config`.

    The replacement happens in :meth:`ConfigNodeProcessor.process`."""
    def __init__(self, config):
        super().__init__('')
        self.config = config


class CfgConfig(ObjectDescription):

    objtype = "config"
    required_arguments = 1
    optional_arguments = 0

    option_spec = {
        'noindex': directives.flag,
        'nolist': directives.flag,
        'noparse': directives.flag,
        'master': directives.flag,
        'context': directives.unchanged,
        'include': directives.unchanged,
    }

    def handle_signature(self, sig, signode):
        fullname = sig
        signode += addnodes.desc_annotation('config ', 'config ')
        signame = nodes.Text(sig)
        if 'master' not in self.options:
            signame = addnodes.pending_xref(sig, signame,
                                            refdomain='cfg', reftype='config', reftarget=fullname)
        signode += addnodes.desc_name(sig, '', signame)
        return fullname

    def add_target_and_index(self, fullname, sig, signode):
        node_id = make_id(self.env, self.state.document, 'cfg-config', fullname)
        signode['ids'].append(node_id)
        self.state.document.note_explicit_target(signode)

        includes = [fullname]  # a config always includes itself
        for incl in self.options.get('include', "").split(','):
            incl = incl.strip()
            if incl and incl not in includes:
                includes.append(incl)
        master = 'master' in self.options
        config_entry = ConfigEntry(fullname=fullname,
                                   dispname=sig,
                                   docname=self.env.docname,
                                   anchor=node_id,
                                   master=master,
                                   includes=includes,
                                   )
        self.env.domaindata['cfg']['config'].append(config_entry)

    def before_content(self):
        if self.config.cfg_parse_numpydoc_style_options and 'noparse' not in self.options:
            self.parse_numpydoc_style_options()
        # save context
        if self.names:
            self.env.ref_context['cfg:config'] = self.names[-1]
            self.env.ref_context['cfg:in-config'] = True
        if 'context' in self.options:
            self.env.ref_context['cfg:context'] = context = self.options['context']
        super().before_content()

    def transform_content(self, contentnode):
        if 'nolist' not in self.options:
            contentnode.insert(0, cfgconfig(self.names[-1]))
        super().transform_content(contentnode)

    def after_content(self):
        if 'cfg:config' in self.env.ref_context:
            del self.env.ref_context['cfg:config']
            del self.env.ref_context['cfg:in-config']
        super().after_content()


    def run(self):
        context_name = self.env.temp_data.get('object', None)
        if isinstance(context_name, tuple):
            context_name = context_name[0]
        self.env.ref_context['cfg:context'] = context_name
        return super().run()

    def parse_numpydoc_style_options(self):
        option_header_re = re.compile("([\w.]*)\s*(?::\s*([^=]*))?(?:=\s*(\S*)\s*)?$")
        self.app.emit('cfg-parse_config', self)
        self.content.disconnect()  # avoid screwing up the parsing of the parent
        N = len(self.content)
        # i = index in the lines
        indents = [_get_indent(line) for line in self.content]
        field_begin = [i for i, indent in enumerate(indents) if indent == 0]
        for field_beg, field_end in reversed(list(zip(field_begin, field_begin[1:] + [N]))):
            field_beg_line = self.content[field_beg]
            next_indent = "    "  # default indent, if no non-empty lines follow
            for j in range(field_beg + 1, field_end):
                if indents[j] > 0:
                    next_indent = self.content[j][:indents[j]]
                    break
            m = option_header_re.match(field_beg_line)
            if m is None:
                source, line = self.content.info(field_beg)
                location = "{0!s}:{1!s}".format(source, line)
                logger.warning("can't parse config option header-line " + repr(field_beg_line),
                               location=location)
                continue
            name, typ, default = m.groups()
            replace = [".. cfg:option :: " + name]
            if typ is not None and typ.strip():
                replace.append(next_indent + ":type: " + typ)
            if default:
                replace.append(next_indent + ":default: " + default)
            replace.append(next_indent)
            field_beg_view = self.content[field_beg:field_beg+1]
            field_beg_view *= len(replace)
            field_beg_view.data[:] = replace
            self.content.insert(field_end, StringList([next_indent], items=[self.content.info(field_end-1)]))
            self.content[field_beg:field_beg+1] = field_beg_view


def _get_indent(line):
    for i, c in enumerate(line):
        if not c.isspace():
            return i
    return -1

def _parse_inline(state, line, info):
    source = StringList([line], items=[info])
    node = nodes.paragraph()
    state.nested_parse(source, 0, node)
    par = node[0]
    assert isinstance(node, nodes.paragraph)
    par = node[0]
    assert isinstance(node, nodes.paragraph)
    return par.children


class CfgOption(ObjectDescription):

    objtype = "option"
    option_spec = {
        'noindex': directives.flag,
        'context': directives.unchanged,
        'config': directives.unchanged,
        'type': directives.unchanged,
        'default': directives.unchanged,
    }

    def handle_signature(self, sig, signode):
        name = sig
        config = self.options.get('config', self.env.ref_context.get('cfg:config', ""))
        if not config:
            logger.warning("config option with unknown config", location=signode)
            config = "UNKNOWN"
        fullname = config + '.' + name

        signode += addnodes.desc_annotation('option ', 'option ')
        if not self.env.ref_context.get('cfg:in-config', False):
            signode += addnodes.pending_xref(sig, addnodes.desc_addname(config, config),
                                            refdomain='cfg', reftype='config', reftarget=config)
            signode += addnodes.desc_addname('', '.')

        signode += addnodes.desc_name(sig, '', nodes.Text(sig))

        typ = self.options.get('type')
        if typ:
            type_node = addnodes.desc_annotation(': ', ': ')
            info = self.content.parent.info(1)  # might be off my +- a few lines...
            type_node.extend(_parse_inline(self.state, typ, info))
            signode += type_node

        defaultvalue = self.options.get('default')
        if defaultvalue:
            val_node = addnodes.desc_annotation(' = ', ' = ')
            info = self.content.parent.info(1)  # might be off my +- a few lines...
            val_node.extend(_parse_inline(self.state, defaultvalue, info))
            signode += val_node

        return fullname, config


    def add_target_and_index(self, name_config, sig, signode):
        fullname, config = name_config
        context = self.options.get('context',
                                   self.env.ref_context.get('cfg:context', None))
        node_id = make_id(self.env, self.state.document, 'cfg-option', fullname)
        signode['ids'].append(node_id)
        self.state.document.note_explicit_target(signode)
        if 'noindex' not in self.options:
            option_entry = OptionEntry(fullname=fullname,
                                       dispname=sig,
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
    options from the given config, but links to config won't lead here.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
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
            config = node.config
            options = self.domain.config_options[config]

            new_content = [self.create_option_reference(o, config) for o in options]
            if len(new_content) > 1:
                listnode = nodes.bullet_list()
                for entry in new_content:
                    listnode += nodes.list_item('', entry)
                new_content = listnode
            node.replace_self(new_content)


    def create_option_reference(self, option, config):
        par = nodes.paragraph()
        # OptionEntry = namedtuple('OptionEntry', "name, dispname, config, docname, anchor, context")
        innernode = addnodes.literal_strong(option.dispname, option.dispname)
        par += self.make_refnode(option.docname, option.anchor, innernode)
        if option.config != config:
            par += nodes.Text(" (from ")
            par += self._make_config_xref(option.config)
            par += nodes.Text(")")
        if option.context is not None:
            par += nodes.Text(" defined in ")
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
        res = [(k, v) for k, v in sorted(content.items())]
        return (res, True)


class CfgDomain(Domain):
    name = 'cfg'
    label = 'Parameter Configs'

    obj_types = {
        'config':  ObjType('config', 'config'),
        'option':  ObjType('option', 'option'),
    }

    roles = {
        'config': XRefRole(),
        'option': XRefRole(),
    }

    directives = {
        'config': CfgConfig,
        'currentconfig': CfgCurrentConfig,
        'option': CfgOption,
    }

    indices = {
        CfgConfigIndex,
        CfgOptionIndex,
    }

    initial_data = {
        'config': [],  # ConfigEntry
        'config2options': {}, # config_name -> List[OptionEntry]
    }

    def clear_doc(self, docname):
        self.data['config'] = [entry for entry in self.data['config']
                               if entry.docname != docname]
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
        for config_entry in self.data['config']:
            yield ObjectsEntry(config_entry.fullname,
                               config_entry.dispname,
                               'config',
                               config_entry.docname,
                               config_entry.anchor,
                               prio=0 if config_entry.master else 1)
        for param_list in self.data['config2options'].values():
            for option_entry in param_list:
                yield ObjectsEntry(option_entry.fullname,
                                   option_entry.dispname,
                                   'config',
                                   option_entry.docname,
                                   option_entry.anchor,
                                   prio=1)

    def resolve_xref(self, env, fromdocname, builder, typ,
                     target, node, contnode):
        if not target:
            return None
        if typ == "config":
            config = self.master_configs.get(target, None)
            if config is None:
                return None
            return make_refnode(builder, fromdocname, config.docname, config.anchor, contnode,
                                config.dispname)
        elif typ == "option":
            config_options = self.config_options
            split = target.split('.')
            if len(split) < 2:
                return None
            for i in range(1, len(split)):
                config, entry_name = '.'.join(split[:i]), '.'.join(split[i:])
                for option_entry in config_options.get(config, []):
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
    def master_configs(self):
        """dict config_name -> ConfigEntry, with recursive `includes`."""
        if not hasattr(self, '_master_configs'):
            self._build_master_configs()
        return self._master_configs

    @property
    def config_options(self):
        """dict config_name -> List[OptionEntry], taking into account recursive `includes`."""
        if not hasattr(self, '_config_options'):
            self._build_config_options()
        return self._config_options

    def _build_master_configs(self):
        """build recursive configs from "flat" configs in self.data"""
        self._master_configs = master_configs = {}
        data_config = self.data['config']
        # collect master configs
        for config_entry in data_config:
            if config_entry.master:
                other = master_configs.get(config_entry.fullname, None)
                if other:
                    logger.warning("two 'cfg:config' objects %s with ':master:' "
                                   "in documents %s and %s",
                                   config_entry.fullname,
                                   config_entry.docname,
                                   other.docname)
                master_configs[config_entry.fullname] = config_entry
            # if no master is given: master = first defined entry; set in next loop
        # collect the includes from other entries in `data_config`
        for config_entry in data_config:
            master = master_configs.setdefault(config_entry.fullname, config_entry)
            for incl in config_entry.includes:
                if incl not in master.includes:
                    master.includes.append(incl)

        # collect configs implicitly defined by options only

        # check validity of `include` names

        # make includes recursive
        if self.env.config.cfg_recursive_includes:
            handled_recursive = set([])
            for config in master_configs.keys():
                self._set_recursive_include(config, handled_recursive)
        return master_configs

    def _build_config_options(self):
        self._config_options = config_options = {}
        data_config2options = self.data['config2options']
        config_names = set(self.master_configs.keys()).union(set(data_config2options.keys()))
        for config in config_names:
            includes = [config]
            master_config = self.master_configs.get(config, None)
            if master_config:
                includes = master_config.includes
            prio = dict((incl, i) for i, incl in enumerate(includes))

            options = []
            for config_incl in includes:
                options.extend(data_config2options.get(config_incl, []))


            def sort_priority(option_entry):
                return (option_entry.dispname.lower(), prio[option_entry.config])

            config_options[config] = sorted(options, key=sort_priority)


    def _set_recursive_include(self, config, handled_recursive):
        includes = self.master_configs[config].includes
        if config in handled_recursive:
            return includes
        handled_recursive.add(config) # before doing it: safeguard for cyclic includes
        new_includes = [config]
        for sub in includes:
            if sub not in new_includes:
                new_includes.append(sub)
            subincludes = self._set_recursive_include(sub, handled_recursive)
            for subincl in subincludes:
                if subincl not in new_includes:
                    new_includes.append(subincl)
        includes[:] = new_includes
        return new_includes



def setup(app):
    app.add_event('cfg-parse_config')
    app.add_config_value('cfg_recursive_includes', True, 'html')
    app.add_config_value('cfg_parse_numpydoc_style_options', True, 'html')

    app.add_domain(CfgDomain)

    app.add_node(cfgconfig)
    app.connect('doctree-resolved', ConfigNodeProcessor)

    StandardDomain.initial_data['labels']['cfg-config-index'] =\
        ('cfg-config', '', 'Config Index')
    StandardDomain.initial_data['labels']['cfg-option-index'] =\
        ('cfg-option', '', 'Config-Options Index')

    return {'version': '0.1'}

# TODO: config values, e.g. 'recursive'?
# TODO: use python domain?
# TODO: allow/use recursive includes
# TODO: allow/use reference for includes
# TODO: rename role :cfg:entry: -> :cfg:option:?

# TODO: def id could be defined through context!
# TODO: use numpydoc-style definitions of parameters

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


# CollEntry is used in CfgDomain.data['coll']
CollEntry = namedtuple('CollEntry', "fullname, dispname, docname, anchor, includes")
# ParamEntry is used in CfgDomain.data['entry2coll']
ParamEntry = namedtuple('ParamEntry', "fullname, dispname, collection, docname, anchor, context")

# ObjectsEntry is returned by Domain.get_objects()
ObjectsEntry = namedtuple('ObjectsEntry', "name, dispname, typ, docname, anchor, prio")
# IndexEntry is retured by Index.generate()
IndexEntry = namedtuple('IndexEntry', "name, subtype, docname, anchor, extra, qualifier, descr")


class cfgcollection(nodes.General, nodes.Element):
    """A node to be replaced by a list of entries for a given `collection`.

    The replacement happens in :meth:`CollectionNodeProcessor.process`."""
    def __init__(self, collection, can_collapse=True):
        super().__init__('')
        self.collection = collection
        self.can_collapse = can_collapse


class CollectionField(GroupedField):
    """Field collecting all the `fieldarg` given in a `cfgcollection` node."""
    def make_field(self, types, domain, items, env=None):
        """Like TypedField.make_field(), but also call `self.add_entry_target_and_index`."""
        assert env is not None   # don't expect this to happen

        fieldname = nodes.field_name('', self.label)
        entries = [fieldarg for (fieldarg, content) in items]
        collection = entries[0]  # ensured by CfgCollection.before_content().
        coll_includes = env.domaindata['cfg']['coll'][collection].includes
        for incl in entries:
            if incl not in coll_includes:
                coll_includes.append(incl)
        bodynode = cfgcollection(collection, self.can_collapse)
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
        collection = env.ref_context['cfg:coll']
        context = env.ref_context.get('cfg:def-context', None)
        assert collection is not None
        name = "%s.%s" % (collection, fieldname)
        anchor = "cfg-entry-%d" % env.new_serialno('cfg-entry')
        content['ids'].append(anchor)
        content['ids'].append("cfg-%s" % name)

        param_entry = ParamEntry(fullname=name,
                                 dispname=fieldname,
                                 collection=collection,
                                 docname=env.docname,
                                 anchor=anchor,
                                 context=context,
                                 )
        coll_entries = env.domaindata['cfg']['coll2entries'].setdefault(collection, [])
        coll_entries.append(param_entry)


class CfgDefinition(ObjectDescription):
    """A custom node that describes a parameter."""

    required_arguments = 1

    option_spec = {
        'noindex': directives.flag,
        'context': directives.unchanged,
    }

    doc_field_types = [
        IndexedTypedField('definition', label='Definitions',
                      names=('param', 'param', 'parameter', 'arg', 'argument', 'keyword', 'kwarg', 'kwparam'),
                      rolename='',  # HACK
                      typerolename='py-class', typenames=('paramtype', 'type'),
                      can_collapse=True),
    ]

    def handle_signature(self, sig, signode):
        # TODO: use below; might want to use PyXRefMixin for that?
        # modname = self.options.get('module', self.env.ref_context.get('py:module'))
        # clsname = self.options.get('cls', self.env.ref_context.get('py:class'))
        # fullname = (modname + '.' if modname else '') + sig
        signode += addnodes.desc_annotation('Config ', 'Config ')
        signame = addnodes.pending_xref(sig, nodes.Text(sig),
                                        refdomain='cfg', reftype='coll', reftarget=sig)
        anchor = "cfg-entry-%d" % self.env.new_serialno('entry')
        signode += addnodes.desc_name(sig, '', signame)

        name = sig  # TODO make name a tuple `(fullname, dispname)` as for PyObject?
        return name

    def add_target_and_index(self, name, sig, signode):

        anchor = "cfg-def-%d" % self.env.new_serialno('cfg-def')
        signode['ids'].append(anchor)
        self.state.document.note_explicit_target(signode)
        if 'noindex' not in self.options:
            obj_entry = ObjectsEntry(name, sig, 'def', self.env.docname, anchor, 2)
            self.env.domaindata['cfg']['def'].append(obj_entry)

    def before_content(self):
        # save context
        if self.names:
            name = self.names[-1]  # what was returned by `handle_sig`
            self.env.ref_context['cfg:coll'] = name
        if 'context' in self.options:
            self.env.ref_context['cfg:def-context'] = context = self.options['context']
        super().before_content()

    def after_content(self):
        if 'cfg:coll' in self.env.ref_context:
            del self.env.ref_context['cfg:coll']
        super().after_content()

    def run(self):
        context_name = self.env.temp_data.get('object', None)
        if isinstance(context_name, tuple):
            context_name = context_name[0]
        self.env.ref_context['cfg:def-context'] = context_name
        res = super().run()
        return res


class CfgCollection(CfgDefinition):

    has_content = 1
    required_arguments = 1

    # option_spec = CfgDefinition.option_spec
    # option_spec.update({
    #     'include': directives.unchanged,
    # })
    doc_field_types = CfgDefinition.doc_field_types[:]
    doc_field_types.append(
        CollectionField('collection', label='Options',
                      names=('incl', 'include'),
                      can_collapse=True)
    )

    def handle_signature(self, sig, signode):
        # TODO: use below; might want to use PyXRefMixin for that?
        # modname = self.options.get('module', self.env.ref_context.get('py:module'))
        # clsname = self.options.get('cls', self.env.ref_context.get('py:class'))
        # fullname = (modname + '.' if modname else '') + sig
        signode += addnodes.desc_annotation('Config ', 'Config ')
        signode += addnodes.desc_name(sig, sig)

        name = sig  # TODO make name a tuple `(fullname, dispname)` as for PyObject?
        return name

    def before_content(self):
        name = self.names[0]
        # HACK: insert `:include <name>:` line before content
        self.content.insert(0, ":include " + name + ":", (self.state.document, ), offset=0)
        super().before_content()

    def add_target_and_index(self, name, sig, signode):
        node_id = make_id(self.env, self.state.document, 'cfg-coll', name)
        signode['ids'].append(node_id)
        self.state.document.note_explicit_target(signode)
        if 'noindex' not in self.options:
            obj_entry = ObjectsEntry(name, sig, 'coll', self.env.docname, node_id, 0)
            self.env.domaindata['cfg']['def'].append(obj_entry)
            coll_entry = CollEntry(fullname=name,
                                   dispname=name,
                                   docname=obj_entry.docname,
                                   anchor=obj_entry.anchor,
                                   includes=[],  # filled in CollectionField.make_field
                                   )
            # TODO: warn about duplicates
            self.env.domaindata['cfg']['coll'][name] = coll_entry


class CollectionNodeProcessor:
    def __init__(self, app, doctree, docname):
        self.env = app.builder.env
        self.builder = app.builder
        self.domain = app.env.get_domain('cfg')
        self.docname = docname

        self.process(doctree)

    def process(self, doctree):
        coll2entries = self.env.domaindata['cfg']['coll2entries']

        for node in doctree.traverse(cfgcollection):
            collection = node.collection # TODO: include more collections
            includes = self.domain.get_includes(collection)
            prio = dict((coll, i) for i, coll in enumerate(includes))
            entries = []
            for include in includes:
                for entry in coll2entries.get(include, []):
                    entries.append(entry)
            entries = sorted(entries, key=lambda e: (e.dispname.lower(), prio[entry.collection]))

            new_content = [self.create_entry_reference(entry, collection) for entry in entries]
            if len(new_content) > 1 or not node.can_collapse:
                listnode = nodes.bullet_list()
                for entry in new_content:
                    listnode += nodes.list_item('', entry)
                new_content = listnode
            node.replace_self(new_content)


    def create_entry_reference(self, entry, collection):

        # TODO: include link to definition and name category if different

        par = nodes.paragraph()
        # ParamEntry = namedtuple('ParamEntry', "name, dispname, collection, docname, anchor, context")
        innernode = addnodes.literal_strong(entry.dispname, entry.dispname)
        par += self.make_refnode(entry.docname, entry.anchor, innernode)
        if entry.collection != collection:
            par += nodes.Text(' (from ')
            par += self._make_collection_xref(entry.collection)  # TODO crossref!
            par += nodes.Text(')')
        if entry.context is not None:
            par += nodes.Text(" in ")
            par += addnodes.literal_emphasis(entry.context, entry.context)  # TODO: crossref
        return par

    def make_refnode(self, docname, anchor, innernode):
        try:
            refnode = make_refnode(self.builder, self.docname, docname, anchor, innernode)
        except NoUri:  # ignore if no URI can be determined, e.g. for LaTeX output
            refnode = innernode
        return refnode

    def _make_collection_xref(self, collection):
        node = nodes.Text(collection, collection)
        match = [(obj_entry.docname, obj_entry.anchor)
                 for obj_entry in self.domain.get_objects()
                 if obj_entry.name == collection and obj_entry.typ == 'coll']
        if len(match) > 0:
            docname, anchor = match[0]
            node = self.make_refnode(docname, anchor, node)
        return node




class CfgDomain(Domain):
    name = 'cfg'
    label = 'Parameter Collections'

    obj_types = {
        'coll':  ObjType('collection', 'coll'),
        'entry':  ObjType('entry', 'entry'),
        'def':  ObjType('definiton', 'def'),
    }

    roles = {
        'coll': XRefRole(),
        'entry': XRefRole(),
        'def': XRefRole(),
    }

    directives = {
        'definition': CfgDefinition,
        'collection': CfgCollection,
    }

    indices = {
        # CfgCollectionIndex,  # TODO
        # CfgEntryIndex
    }

    initial_data = {
        'coll': {}, # coll_name -> CollEntry
        'def': [],  # ObjectsEntry, includes 'def' and 'coll'
        'coll2entries': {}, # coll_name -> List[ParamEntry]
    }

    def clear_doc(self, docname):
        # bug/limiation: in general, we should clear `coll2includes` as well...
        coll_data = self.data['coll']
        for name, coll_entry in list(coll_data.items()):
            if coll_entry.docname == docname:
                del coll_data[name]
        self.data['def'] = [entry for entry in self.data['def'] if entry.docname != docname]
        for coll_name, entries_list in self.data['coll2entries'].items():
            filered_entries = [entry for entry in entries_list if entry.docname != docname]
            self.data['coll2entries'][coll_name] = filered_entries

    # TODO: needed?
    # def get_full_qualified_name(self, node):
    #     """Return full qualified name for a given node"""
    #     return "{}.{}.{}".format('cfg',
    #                              type(node).__name__,
    #                              node.arguments[0])

    def get_objects(self):
        for coll_entry in self.data['coll'].values():
            yield ObjectsEntry(coll_entry.fullname,
                               coll_entry.dispname,
                               'coll',
                               coll_entry.docname,
                               coll_entry.anchor,
                               prio=1)
        for param_list in self.data['coll2entries'].values():
            for param_entry in param_list:
                yield ObjectsEntry(param_entry.fullname,
                                   param_entry.dispname,
                                   'coll',
                                   param_entry.docname,
                                   param_entry.anchor,
                                   prio=1)
        for obj_entry in self.data['def']:
            yield obj_entry


    def resolve_xref(self, env, fromdocname, builder, typ,
                     target, node, contnode):
        if not target:
            return None
        if typ == "coll":
            coll = self.data['coll'].get(target, None)
            if coll is None:
                return None
            return make_refnode(builder, fromdocname, coll.docname, coll.anchor, contnode,
                                coll.dispname)
        elif typ == "entry":
            coll2entries = self.data['coll2entries']
            split = target.split('.')
            if len(split) < 2:
                return None
            for i in range(1, len(split)):
                coll, entry_name = '.'.join(split[:i]), '.'.join(split[i:])
                # TODO: match parameter from included collections
                for param_entry in coll2entries.get(coll, []):
                    if param_entry.dispname == entry_name:  # match!
                        return make_refnode(builder,
                                            fromdocname,
                                            param_entry.docname,
                                            param_entry.anchor,
                                            contnode,
                                            param_entry.dispname)
            return None
        return None


    def get_includes(self, collection, recursive=True):
        # TODO: option for recursive
        coll2incl = {coll: entry.includes for coll, entry in self.data['coll'].items()}
        includes = coll2incl.get(collection, [collection])[:]
        assert includes[0] == collection
        if recursive:
            check_recursive = includes[1:]
            checked = set([collection])
            while len(check_recursive) > 0:
                check = check_recursive.pop(0)
                checked.add(check)
                for incl in coll2incl.get(check, [])[1:]:
                    if incl in includes:
                        continue
                    includes.append(incl)
                    check_recursive.append(incl)
        return includes


# TODO: which indices do we need?
class CfgEntryIndex(Index):
    name = 'entry'
    localname = 'Parameters Index'
    shortname = 'Parameters'

    def generate(self, docnames=None):
        content = {}
        for obj in self.domain.get_objects():
            if obj.typ != "entry":
                continue
            collection = obj.name.rsplit('.', 1)[0] # TODO: note the best way: not unique?
            ind_entry = IndexEntry(name=obj.dispname,
                                   subtype=0,
                                   docname=obj.docname,
                                   anchor=obj.anchor,
                                   extra=collection,
                                   qualifier='',
                                   descr='')
            content.setdefault(collection, []).append(ind_entry)
        content = [(k, content[k]) for k in sorted(content.keys())]
        return (content, True)


class CfgCollectionIndex(Index):
    name = 'coll'
    localname = 'Parameter Collections Index'
    shortname = 'Parameter Index'

    def generate(self, docnames=None):
        content = {}
        items = self.domain.get_objects()
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


def setup(app):
    app.add_domain(CfgDomain)

    app.add_node(cfgcollection)
    app.connect('doctree-resolved', CollectionNodeProcessor)

    # StandardDomain.initial_data['labels']['cfg-coll-index'] =\
    #     ('cfg-coll', '', 'Parameter Collection Index')
    # StandardDomain.initial_data['labels']['cfg-entry-index'] =\
    #     ('cfg-entry', '', 'Parameters Index')

    return {'version': '0.1'}

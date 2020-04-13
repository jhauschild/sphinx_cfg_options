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


ParamEntry = namedtuple('ParamEntry', "name, dispname, collection, docname, anchor, parent")
ObjectsEntry = namedtuple('ObjectsEntry', "name, dispname, typ, docname, anchor, prio")
IndexEntry = namedtuple('IndexEntry', "name, subtype, docname, anchor, extra, qualifier, descr")


class prmcollection(nodes.General, nodes.Element):
    """A node to be replaced by a list of entries for a given `collection`.

    The replacement happens in :meth:`CollectionNodeProcessor.process`."""
    def __init__(self, collections, can_collapse=True):
        super().__init__('')
        self.collections = collections
        self.can_collapse = can_collapse


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
        collection = env.ref_context['prm:def']
        parent = env.ref_context.get('prm:def-parent', None)
        assert collection is not None
        name = "%s.%s" % (collection, fieldname)
        anchor = "prm-entry-%d" % env.new_serialno('prm-entry')
        content['ids'].append(anchor)
        content['ids'].append("prm-%s" % name)

        param_entry = ParamEntry(name=name,
                                 dispname=fieldname,
                                 collection=collection,
                                 docname=env.docname,
                                 anchor=anchor,
                                 parent=parent,
                                 )
        coll_entries = env.domaindata['prm']['coll2entries'].setdefault(collection, [])
        coll_entries.append(param_entry)
        obj_entry = ObjectsEntry(name=name,
                                 dispname=fieldname,
                                 typ="entry",
                                 docname=env.docname,
                                 anchor=anchor,
                                 prio=0)
        env.domaindata['prm']['objects'].append(obj_entry)



class CollectionField(GroupedField):
    def make_field(self, types, domain, items, env=None):
        """Like TypedField.make_field(), but also call `self.add_entry_target_and_index`."""
        assert env is not None   # don't expect this to happen

        fieldname = nodes.field_name('', self.label)
        entries = []
        for fieldarg, content in items:
            entries.append(fieldarg)
        bodynode = prmcollection(entries, self.can_collapse)
        fieldbody = nodes.field_body('', bodynode)
        return nodes.field('', fieldname, fieldbody)


class PrmDefinition(ObjectDescription):
    """A custom node that describes a parameter."""

    required_arguments = 1

    option_spec = {
        'noindex': directives.flag,
        'parent': directives.unchanged,
        'module': directives.unchanged,  # TODO: use those in handle_signature
        'class': directives.unchanged,
    }

    doc_field_types = [
        IndexedTypedField('definition', label='Definitions',
                      names=('param', 'param', 'parameter', 'arg', 'argument', 'keyword', 'kwarg', 'kwparam'),
                      rolename='make-entry-target',  # HACK
                      typerolename='py-class', typenames=('paramtype', 'type'),
                      can_collapse=True),
    ]


    def handle_signature(self, sig, signode):
        # TODO: use below; might want to use PyXRefMixin for that?
        # modname = self.options.get('module', self.env.ref_context.get('py:module'))
        # clsname = self.options.get('cls', self.env.ref_context.get('py:class'))
        # fullname = (modname + '.' if modname else '') + sig
        signode += addnodes.desc_annotation('Parameters ', 'Parameters ')
        signame = addnodes.pending_xref(sig, nodes.Text(sig),
                                        refdomain='prm', reftype='coll', reftarget=sig)
        anchor = "prm-entry-%d" % self.env.new_serialno('entry')
        signode += addnodes.desc_name(sig, '', signame)

        name = sig  # TODO make name a tuple `(fullname, dispname)` as for PyObject?
        return name

    def add_target_and_index(self, name, sig, signode):

        anchor = "prm-def-%d" % self.env.new_serialno('prm-def')
        signode['ids'].append(anchor)
        self.state.document.note_explicit_target(signode)
        if 'noindex' not in self.options:
            obj_entry = ObjectsEntry(name, sig, 'def', self.env.docname, anchor, 0)
            self.env.domaindata['prm']['objects'].append(obj_entry)

    def before_content(self):
        # save context
        if self.names:
            name = self.names[-1]  # what was returned from `handle_sig
            self.env.ref_context['prm:def'] = name
        if 'parent' in self.options:
            self.env.ref_context['prm:def-parent'] =  parent = self.options['parent']
        super().before_content()

    def after_content(self):
        if 'prm:def' in self.env.ref_context:
            del self.env.ref_context['prm:def']
        super().after_content()

    def run(self):
        parent_name = self.env.temp_data.get('object', None)
        if isinstance(parent_name, tuple):
            parent_name = parent_name[0]
        self.env.ref_context['prm:def-parent'] = parent_name
        res = super().run()
        return res


class PrmCollection(PrmDefinition):

    has_content = 1
    required_arguments = 1

    # option_spec = PrmDefinition.option_spec
    # option_spec.update({
    #     'include': directives.unchanged,
    # })
    doc_field_types = PrmDefinition.doc_field_types[:]
    doc_field_types.append(
        CollectionField('collection', label='Collection',
                      names=('collect', 'coll'),
                      can_collapse=True)
    )

    def handle_signature(self, sig, signode):
        # TODO: use below; might want to use PyXRefMixin for that?
        # modname = self.options.get('module', self.env.ref_context.get('py:module'))
        # clsname = self.options.get('cls', self.env.ref_context.get('py:class'))
        # fullname = (modname + '.' if modname else '') + sig
        signode += addnodes.desc_annotation('Parameters ', 'Parameters ')
        signode += addnodes.desc_name(sig, sig)

        name = sig  # TODO make name a tuple `(fullname, dispname)` as for PyObject?
        return name
    def before_content(self):
        name = self.names[0]
        # HACK: insert `:collect <name>:` line before content
        self.content.insert(0, ":collect " + name + ":", (self.state.document, ), offset=0)
        super().before_content()

    def add_target_and_index(self, name, sig, signode):
        node_id = make_id(self.env, self.state.document, 'prm-coll', name)
        signode['ids'].append(node_id)
        self.state.document.note_explicit_target(signode)
        if 'noindex' not in self.options:
            obj_entry = ObjectsEntry(name, sig, 'coll', self.env.docname, node_id, 0)
            self.env.domaindata['prm']['objects'].append(obj_entry)


class CollectionNodeProcessor:
    def __init__(self, app, doctree, docname):
        self.env = app.builder.env
        self.builder = app.builder
        self.domain = app.env.get_domain('prm')
        self.docname = docname

        self.process(doctree)

    def process(self, doctree):
        coll2entries = self.env.domaindata['prm']['coll2entries']

        for node in doctree.traverse(prmcollection):
            collections = node.collections # TODO: include more collections
            collection = collections[0]
            prio = dict((coll, i) for i, coll in enumerate(collections))
            entries = []
            for include in collections:
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
        # ParamEntry = namedtuple('ParamEntry', "name, dispname, collection, docname, anchor, parent")
        innernode = addnodes.literal_strong(entry.dispname, entry.dispname)
        try:
            refnode = make_refnode(self.builder, self.docname, entry.docname, entry.anchor, innernode)
        except NoUri:
            # ignore if no URI can be determined, e.g. for LaTeX output
            refnode = innernode
        par += refnode
        if entry.parent is not None:
            par += nodes.Text(" in ")
            par += addnodes.literal_emphasis(entry.parent, entry.parent)  # TODO: crossref
        if entry.collection != collection:
            par += nodes.Text(' (from ')
            par += nodes.Text(entry.collection)  # TODO crossref!
            par += nodes.Text(')')
        return par



class PrmEntryIndex(Index):
    name = 'entry'
    localname = 'Parameters Index'
    shortname = 'Parameters'

    def generate(self, docnames=None):
        content = {}
        for obj in self.domain.get_objects():
            if obj.typ != "entry":
                continue
            collection = obj.name.rsplit('.', 1)[0]
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


class PrmCollectionIndex(Index):
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


class PrmDomain(Domain):
    name = 'prm'
    label = 'Parameter collections'

    roles = {
        'coll': XRefRole(),
        'entry': XRefRole(),
        'def': XRefRole(),
    }

    directives = {
        'definition': PrmDefinition,
        'collection': PrmCollection,
    }

    indices = {
        PrmCollectionIndex,
        PrmEntryIndex
    }

    initial_data = {
        'objects': [],  # list of ObjectsEntry tuples
        'coll2entries': {},  # collectionname -> ParamEntry tuples
    }

    obj_types = {
        'collection':  ObjType('collection', 'coll'),
        'entry':  ObjType('entry', 'entry'),
        'definition':  ObjType('definiton', 'def'),
    }


    def get_full_qualified_name(self, node):
        """Return full qualified name for a given node"""
        return "{}.{}.{}".format('prm',
                                 type(node).__name__,
                                 node.arguments[0])

    def get_objects(self):
        for obj in self.data['objects']:
            yield(obj)

    def resolve_xref(self, env, fromdocname, builder, typ,
                     target, node, contnode):

        match = [(docname, anchor)
                 for name, dispname, typ_, docname, anchor, prio
                 in self.get_objects() if name == target and typ_ == typ]

        if len(match) > 0:
            todocname = match[0][0]
            targ = match[0][1]

            return make_refnode(builder, fromdocname, todocname, targ, contnode, targ)
        else:
            # found nothing
            return None


def setup(app):
    app.add_domain(PrmDomain)

    app.add_node(prmcollection)
    app.connect('doctree-resolved', CollectionNodeProcessor)

    StandardDomain.initial_data['labels']['prm-coll-index'] =\
        ('prm-coll', '', 'Parameter Collection Index')
    StandardDomain.initial_data['labels']['prm-entry-index'] =\
        ('prm-entry', '', 'Parameters Index')

    return {'version': '0.1'}

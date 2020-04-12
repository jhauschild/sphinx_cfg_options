from collections import namedtuple

import docutils
from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives, Directive
import sphinx
from sphinx.domains import Domain, Index, ObjType
from sphinx.domains.python import PyTypedField
from sphinx.domains.std import StandardDomain
from sphinx.util.docfields import Field, TypedField
from sphinx.roles import XRefRole
from sphinx.directives import ObjectDescription
from sphinx.util.nodes import make_id, make_refnode
from sphinx import addnodes


ParamEntry = namedtuple('ParamEntry', "name, dispname, docname, anchor, contentnode")
ObjectsEntry = namedtuple('ObjectsEntry', "name, dispname, typ, docname, anchor, prio")
IndexEntry = namedtuple('IndexEntry', "name, subtype, docname, anchor, extra, qualifier, descr")



class IndexedTypedField(PyTypedField):
    def make_xref(self, rolename, domain, target,
                  innernode=addnodes.literal_emphasis,
                  contnode=None, env=None):
        if rolename == 'py-class':
            return super().make_xref("class", "py", target, innernode, contnode, env)
        if rolename == 'entry':
            pass # TODO need context to update target: include Parent class!
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
        assert collection is not None
        id_name = "%s.%s" % (collection, fieldname)

        param_entry = ParamEntry(name=id_name,
                                 dispname=fieldname,
                                 docname=env.docname,
                                 anchor=id_name,
                                 contentnode=content.copy())
        coll_entries = env.domaindata['prm']['coll2entries'].setdefault(collection, [])
        coll_entries.append(param_entry)
        obj_entry = ObjectsEntry(name=id_name,
                                 dispname=fieldname,
                                 typ="entry",
                                 docname=env.docname,
                                 anchor=id_name,
                                 prio=0)
        env.domaindata['prm']['objects'].append(obj_entry)

        content['ids'].append(id_name)  # after copying the content!


class PrmDefinition(ObjectDescription):
    """A custom node that describes a parameter."""

    required_arguments = 1

    option_spec = {
        'noindex': directives.flag,
        'module': directives.unchanged,  # TODO: use those
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
        signode += addnodes.desc_name(text=sig)
        signode += addnodes.desc_type(text='Parameters definition')
        # TODO: use self.env.ref_context['py:class'] and self.env.ref_context['py:module']
        # update `sig` for a full, unique name.
        name = sig
        return name  # TODO: returns `name_cls` used for `add_target_and_index`; Py uses fullname, name?

    def add_target_and_index(self, name, sig, signode):
        modname = self.options.get('module', self.env.ref_context.get('py:module'))
        fullname = (modname + '.' if modname else '') + name
        node_id = make_id(self.env, self.state.document, '', fullname)

        signode['ids'].append(node_id)
        if 'noindex' not in self.options:
            obj_entry = ObjectsEntry(fullname, sig, 'def', self.env.docname, node_id, 0)
            self.env.domaindata['prm']['objects'].append(obj_entry)

    def before_content(self):
        # save context for make_xref
        if self.names:
            name = self.names[-1]  # what was returned from `handle_sig
            self.env.ref_context['prm:def'] = name

    def after_content(self):
        if 'prm:def' in self.env.ref_context:
            del self.env.ref_context['prm:def']



class PrmCollection(Directive):
    """A custom node that describes a parameter."""

    has_content = 1
    required_arguments = 1

    option_spec = PrmDefinition.option_spec
    option_spec.update({
        'include': directives.unchanged,
    })
    # TODO : for each `include` entry, make a Node to be replaced afterwards.


    # def handle_signature(self, sig, signode):
    #     # TODO: use self.env.ref_context['py:class'] and self.env.ref_context['py:module']
    #     # update `sig` for a full, unique name.
    #     signode += addnodes.desc_name(text=sig)
    #     signode += addnodes.desc_type(text='Parameter collection')
    #     return sig

    # def add_target_and_index(self, name_cls, sig, signode):
    #     signode['ids'].append('prm' + '-' + sig)
    #     if 'noindex' not in self.options:
    #         name = "{}.{}.{}".format('prm', type(self).__name__, sig)
    #         imap = self.env.domaindata['prm']['obj2entry']
    #         imap[name] = list(self.options.get('include').split(' '))
    #         objs = self.env.domaindata['prm']['objects']
    #         objs.append((name,
    #                      sig,
    #                      'Parameter',
    #                      self.env.docname,
    #                      'prm' + '-' + sig,
    #                      0))

    def run(self):
        return []


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
                 in self.get_objects() if dispname == target]

        if len(match) > 0:
            todocname = match[0][0]
            targ = match[0][1]

            return make_refnode(builder, fromdocname, todocname, targ, contnode, targ)
        else:
            # found nothing
            return None


def setup(app):
    app.add_domain(PrmDomain)

    StandardDomain.initial_data['labels']['prm-coll-index'] =\
        ('prm-coll', '', 'Parameter Collection Index')
    StandardDomain.initial_data['labels']['prm-entry-index'] =\
        ('prm-entry', '', 'Parameters Index')

    return {'version': '0.1'}

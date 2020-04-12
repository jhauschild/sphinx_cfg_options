import docutils
from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives
import sphinx
from sphinx.domains import Domain, Index, ObjType
from sphinx.domains.python import PyTypedField
from sphinx.domains.std import StandardDomain
from sphinx.util.docfields import Field, TypedField
from sphinx.roles import XRefRole
from sphinx.directives import ObjectDescription
from sphinx.util.nodes import make_id, make_refnode
from sphinx import addnodes



class PrmTypedField(PyTypedField):
    def make_xref(self, rolename, domain, target,
                  innernode=addnodes.literal_emphasis,
                  contnode=None, env=None):
        if rolename == 'py-class':
            return super().make_xref("class", "py", target, innernode, contnode, env)
        if rolename == 'entry-lookup':
            pass # TODO need context to update target: include Parent class!

        elif rolename == 'make-entry-target':
            # TODO: instead of making a cross-ref to another entry, define a target node!
            pass

        return Field.make_xref(self, rolename, domain, target, innernode, contnode, env)


class PrmDefinition(ObjectDescription):
    """A custom node that describes a parameter."""

    required_arguments = 1

    option_spec = {
        'noindex': directives.flag,
        'module': directives.unchanged,
        'class': directives.unchanged,
    }

    doc_field_types = [
        PrmTypedField('definitions', label='Used here',
                   names=('param', 'parameter', 'arg', 'argument', 'keyword', 'kwarg', 'kwparam'),
                   rolename='entry',
                   typerolename='py-class', typenames=('paramtype', 'type'),
                   can_collapse=True),
    ]


    def handle_signature(self, sig, signode):
        # TODO: use self.env.ref_context['py:class'] and self.env.ref_context['py:module']
        # update `sig` for a full, unique name.
        signode += addnodes.desc_name(text=sig)
        signode += addnodes.desc_type(text='Parameters instance')
        return sig  # TODO: returns `name_cls` used for `add_target_and_index`; Py uses fullname, name?

    def add_target_and_index(self, name_cls, sig, signode):
        modname = self.options.get('module', self.env.ref_context.get('py:module'))
        fullname = (modname + '.' if modname else '') + name_cls
        node_id = make_id(self.env, self.state.document, '', fullname)

        signode['ids'].append(node_id)  # this is the index text!
        if 'noindex' not in self.options:
            name = "{}".format('prm', type(self).__name__, sig)
            # imap = self.env.domaindata['prm']['obj2entry']
            # imap[name] = list(self.options.get('contains').split(' '))
            objs = self.env.domaindata['prm']['objects']
            objs.append((name,
                         sig,
                         'definition',
                         self.env.docname,
                         node_id,
                         0))


class PrmCollection(ObjectDescription):
    """A custom node that describes a parameter."""

    required_arguments = 1

    option_spec = {
        'noindex': directives.flag,
        'contains': directives.unchanged
    }


    def handle_signature(self, sig, signode):
        # TODO: use self.env.ref_context['py:class'] and self.env.ref_context['py:module']
        # update `sig` for a full, unique name.
        signode += addnodes.desc_name(text=sig)
        signode += addnodes.desc_type(text='Parameter collection')
        return sig

    def add_target_and_index(self, name_cls, sig, signode):
        signode['ids'].append('prm' + '-' + sig)
        if 'noindex' not in self.options:
            name = "{}.{}.{}".format('prm', type(self).__name__, sig)
            imap = self.env.domaindata['prm']['obj2entry']
            imap[name] = list(self.options.get('contains').split(' '))
            objs = self.env.domaindata['prm']['objects']
            objs.append((name,
                         sig,
                         'Parameter',
                         self.env.docname,
                         'prm' + '-' + sig,
                         0))



class PrmEntryIndex(Index):
    """A custom directive that creates an entry matrix."""

    name = 'entr'
    localname = 'Parameters Index'
    shortname = 'Parameters'

    def generate(self, docnames=None):
        content = {}

        objs = {name: (dispname, typ, docname, anchor)
                for name, dispname, typ, docname, anchor, prio
                in self.domain.get_objects()}

        imap = {}
        ingr = self.domain.data['obj2entry']
        for name, ingr in ingr.items():
            for ig in ingr:
                imap.setdefault(ig,[])
                imap[ig].append(name)

        for ingredient in imap.keys():
            lis = content.setdefault(ingredient, [])
            objlis = imap[ingredient]
            for objname in objlis:
                dispname, typ, docname, anchor = objs[objname]
                lis.append((
                    dispname, 0, docname,
                    anchor,
                    docname, '', typ
                ))
        re = [(k, v) for k, v in sorted(content.items())]

        return (re, True)


class PrmCollectionIndex(Index):
    name = 'coll'
    localname = 'Parameter Collection Index'
    shortname = 'Parameter Collections'

    def generate(self, docnames=None):
        content = {}
        items = ((name, dispname, typ, docname, anchor)
                 for name, dispname, typ, docname, anchor, prio
                 in self.domain.get_objects())
        items = sorted(items, key=lambda item: item[0])
        for name, dispname, typ, docname, anchor in items:
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
        'param': XRefRole(),
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
        'objects': [],  # object list
        'obj2entry': {},  # name -> object
    }

    obj_types = {
        'collection':  ObjType('collection', 'coll'),
        'entry':  ObjType('parameter', 'param'),
        'definition':  ObjType('definiton'),
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
                 for name, sig, typ_, docname, anchor, prio
                 in self.get_objects() if sig == target]

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
    StandardDomain.initial_data['labels']['prm-entr-index'] =\
        ('prm-entr', '', 'Parameters Index')

    return {'version': '0.1'}

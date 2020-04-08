import docutils
from docutils import nodes
import sphinx
from docutils.parsers import rst
from docutils.parsers.rst import directives
from sphinx.domains import Domain, Index
from sphinx.domains.std import StandardDomain
from sphinx.roles import XRefRole
from sphinx.directives import ObjectDescription
from sphinx.util.nodes import make_refnode
from sphinx import addnodes


class CollectionNode(ObjectDescription):
    """A custom node that describes a parameter."""

    required_arguments = 1

    option_spec = {
        'noindex': directives.flag,
        'contains': directives.unchanged_required
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


class EntryIndex(Index):
    """A custom directive that creates an entry matrix."""

    name = 'entr'
    localname = 'Parameters Index'
    shortname = 'Parameters'

    def __init__(self, *args, **kwargs):
        super(EntryIndex, self).__init__(*args, **kwargs)

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


class CollectionIndex(Index):
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
            lis = content.setdefault(name[0].upper(), [])
            lis.append((
                dispname, 0, docname,
                anchor,
                docname, '', typ
            ))
        re = [(k, v) for k, v in sorted(content.items())]
        return (re, True)


class ParametersDomain(Domain):
    name = 'prm'
    label = 'Parameter collections'

    roles = {
        'coll': XRefRole(),
    }

    directives = {
        'collection': CollectionNode,
    }

    indices = {
        CollectionIndex,
        EntryIndex
    }

    initial_data = {
        'objects': [],  # object list
        'obj2entry': {},  # name -> object
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
                 for name, sig, typ, docname, anchor, prio
                 in self.get_objects() if sig == target]

        if len(match) > 0:
            todocname = match[0][0]
            targ = match[0][1]

            return make_refnode(builder,fromdocname,todocname,
                                targ, contnode, targ)
        else:
            print("Awww, found nothing")
            return None


def setup(app):
    app.add_domain(ParametersDomain)

    StandardDomain.initial_data['labels']['prm-coll-index'] =\
        ('prm-coll', '', 'Parameter Collection Index')
    StandardDomain.initial_data['labels']['prm-entr-index'] =\
        ('prm-entr', '', 'Parameters Index')

    return {'version': '0.1'}

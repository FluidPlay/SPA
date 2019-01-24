from collections import OrderedDict
from typing import List

from six import string_types
from sqlalchemy import asc, desc, inspect, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.orm import (
    RelationshipProperty, joinedload, subqueryload, aliased, contains_eager, scoped_session, sessionmaker)
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql import operators, extract
from sqlalchemy_utils import force_auto_coercion, force_instant_defaults

from conf import settings

JOINED = 'joined'
SUBQUERY = 'subquery'

RELATION_SPLITTER = '___'
OPERATOR_SPLITTER = '__'

DESC_PREFIX = '-'


class classproperty(object):
    """
    @property for @classmethod
    taken from http://stackoverflow.com/a/13624858
    """

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


def _parse_path_and_make_aliases(entity, entity_path, attrs, aliases):
    """
    :type entity: InspectionMixin
    :type entity_path: str
    :type attrs: list
    :type aliases: OrderedDict

    Sample values:

    attrs: ['product__subject_ids', 'user_id', '-group_id',
            'user__name', 'product__name', 'product__grade_from__order']
    relations: {'product': ['subject_ids', 'name'], 'user': ['name']}

    """
    relations = {}
    # take only attributes that have magic RELATION_SPLITTER
    for attr in attrs:
        # from attr (say, 'product__grade__order')  take
        # relationship name ('product') and nested attribute ('grade__order')
        if RELATION_SPLITTER in attr:
            relation_name, nested_attr = attr.split(RELATION_SPLITTER, 1)
            if relation_name in relations:
                relations[relation_name].append(nested_attr)
            else:
                relations[relation_name] = [nested_attr]

    for relation_name, nested_attrs in relations.items():
        path = entity_path + RELATION_SPLITTER + relation_name \
            if entity_path else relation_name
        if relation_name not in entity.relations:
            raise KeyError(f"Incorrect path `{path}`: {entity} doesnt have "
                           f"`{relation_name}` relationship")
        relationship = getattr(entity, relation_name)
        alias = aliased(relationship.property.argument())
        aliases[path] = alias, relationship
        _parse_path_and_make_aliases(alias, path, nested_attrs, aliases)


def eager_expr(schema):
    """
    :type schema: dict
    """
    flat_schema = _flatten_schema(schema)
    return _eager_expr_from_flat_schema(flat_schema)


def _flatten_schema(schema):
    """
    :type schema: dict
    """

    def _flatten(schema, parent_path, result):
        """
        :type schema: dict
        """
        for path, value in schema.items():
            # for supporting schemas like Product.user: {...},
            # we transform, say, Product.user to 'user' string
            if isinstance(path, InstrumentedAttribute):
                path = path.key

            if isinstance(value, tuple):
                join_method, inner_schema = value[0], value[1]
            elif isinstance(value, dict):
                join_method, inner_schema = JOINED, value
            else:
                join_method, inner_schema = value, None

            full_path = parent_path + '.' + path if parent_path else path
            result[full_path] = join_method

            if inner_schema:
                _flatten(inner_schema, full_path, result)

    result = {}
    _flatten(schema, '', result)
    return result


def _eager_expr_from_flat_schema(flat_schema):
    """
    :type flat_schema: dict
    """
    result = []
    for path, join_method in flat_schema.items():
        if join_method == JOINED:
            result.append(joinedload(path))
        elif join_method == SUBQUERY:
            result.append(subqueryload(path))
        else:
            raise ValueError(f'Bad join method `{join_method}` in `{path}`')
    return result


class BaseModel(object):
    __abstract__ = True

    __repr_attrs__: List[str] = []
    __repr_max_length__ = 15

    _operators = {
        'isnull': lambda c, v: (c is None) if v else (c is not None),
        'exact': operators.eq,

        'gt': operators.gt,  # greater than , >
        'ge': operators.ge,  # greater than or equal, >=
        'lt': operators.lt,  # lower than, <
        'le': operators.le,  # lower than or equal, <=

        'in': operators.in_op,
        'between': lambda c, v: c.between(v[0], v[1]),

        'like': operators.like_op,
        'ilike': operators.ilike_op,
        'startswith': operators.startswith_op,
        'istartswith': lambda c, v: c.ilike(v + '%'),
        'endswith': operators.endswith_op,
        'iendswith': lambda c, v: c.ilike('%' + v),

        'year': lambda c, v: extract('year', c) == v,
        'month': lambda c, v: extract('month', c) == v,
        'day': lambda c, v: extract('day', c) == v
    }

    @classproperty
    def filterable_attributes(cls):
        return (cls.relations + cls.columns +
                cls.hybrid_properties + cls.hybrid_methods)

    @classproperty
    def sortable_attributes(cls):
        return cls.columns + cls.hybrid_properties

    @classmethod
    def filter_expr(cls_or_alias, **filters):
        """
        forms expressions like [Product.age_from = 5,
                                Product.subject_ids.in_([1,2])]
        from filters like {'age_from': 5, 'subject_ids__in': [1,2]}

        Example 1:
            db.query(Product).filter(
                *Product.filter_expr(age_from = 5, subject_ids__in=[1, 2]))

        Example 2:
            filters = {'age_from': 5, 'subject_ids__in': [1,2]}
            db.query(Product).filter(*Product.filter_expr(**filters))


        ### About alias ###:
        If we will use alias:
            alias = aliased(Product) # table name will be product_1
        we can't just write query like
            db.query(alias).filter(*Product.filter_expr(age_from=5))
        because it will be compiled to
            SELECT * FROM product_1 WHERE product.age_from=5
        which is wrong: we select from 'product_1' but filter on 'product'
        such filter will not work

        We need to obtain
            SELECT * FROM product_1 WHERE product_1.age_from=5
        For such case, we can call filter_expr ON ALIAS:
            alias = aliased(Product)
            db.query(alias).filter(*alias.filter_expr(age_from=5))

        Alias realization details:
          * we allow to call this method
            either ON ALIAS (say, alias.filter_expr())
            or on class (Product.filter_expr())
          * when method is called on alias, we need to generate SQL using
            aliased table (say, product_1), but we also need to have a real
            class to call methods on (say, Product.relations)
          * so, we have 'mapper' that holds table name
            and 'cls' that holds real class

            when we call this method ON ALIAS, we will have:
                mapper = <product_1 table>
                cls = <Product>
            when we call this method ON CLASS, we will simply have:
                mapper = <Product> (or we could write <Product>.__mapper__.
                                    It doesn't matter because when we call
                                    <Product>.getattr, SA will magically
                                    call <Product>.__mapper__.getattr())
                cls = <Product>
        """
        if isinstance(cls_or_alias, AliasedClass):
            mapper, cls = cls_or_alias, inspect(cls_or_alias).mapper.class_
        else:
            mapper = cls = cls_or_alias

        expressions = []
        valid_attributes = cls.filterable_attributes
        for attr, value in filters.items():
            # if attribute is filtered by method, call this method
            if attr in cls.hybrid_methods:
                method = getattr(cls, attr)
                expressions.append(method(value, mapper=mapper))
            # else just add simple condition (== for scalars or IN for lists)
            else:
                # determine attrbitute name and operator
                # if they are explicitly set (say, id___between), take them
                if OPERATOR_SPLITTER in attr:
                    attr_name, op_name = attr.rsplit(OPERATOR_SPLITTER, 1)
                    if op_name not in cls._operators:
                        raise KeyError(f'Expression `{attr}` has incorrect '
                                       f'operator `{op_name}`')
                    op = cls._operators[op_name]
                # assume equality operator for other cases (say, id=1)
                else:
                    attr_name, op = attr, operators.eq

                if attr_name not in valid_attributes:
                    raise KeyError(f'Expression `{attr}` '
                                   f'has incorrect attribute `{attr_name}`')

                column = getattr(mapper, attr_name)
                expressions.append(op(column, value))

        return expressions

    @classmethod
    def order_expr(cls_or_alias, *columns):
        """
        Forms expressions like [desc(User.first_name), asc(User.phone)]
          from list like ['-first_name', 'phone']

        Example for 1 column:
          db.query(User).order_by(*User.order_expr('-first_name'))
          # will compile to ORDER BY user.first_name DESC

        Example for multiple columns:
          columns = ['-first_name', 'phone']
          db.query(User).order_by(*User.order_expr(*columns))
          # will compile to ORDER BY user.first_name DESC, user.phone ASC

        About cls_or_alias, mapper, cls: read in filter_expr method description
        """
        if isinstance(cls_or_alias, AliasedClass):
            mapper, cls = cls_or_alias, inspect(cls_or_alias).mapper.class_
        else:
            mapper = cls = cls_or_alias

        expressions = []
        for attr in columns:
            fn, attr = (desc, attr[1:]) if attr.startswith(DESC_PREFIX) \
                else (asc, attr)
            if attr not in cls.sortable_attributes:
                raise KeyError(f'Cant order {cls} by {attr}')

            expr = fn(getattr(mapper, attr))
            expressions.append(expr)
        return expressions

    @classmethod
    def smart_query(cls, filters=None, sort_attrs=None, schema=None):
        """
        Does magic Django-ish joins like post___user___name__startswith='Bob'
         (see https://goo.gl/jAgCyM)
        Does filtering, sorting and eager loading at the same time.
        And if, say, filters and sorting need the same joinm it will be done
         only one. That's why all stuff is combined in single method

        :param filters: dict
        :param sort_attrs: List[basestring]
        :param schema: dict
        """
        if not filters:
            filters = {}
        if not sort_attrs:
            sort_attrs = []
        if not schema:
            schema = {}

        root_entity = cls
        attrs = list(filters.keys()) + \
                list(map(lambda s: s.lstrip(DESC_PREFIX), sort_attrs))
        aliases = OrderedDict({})
        _parse_path_and_make_aliases(root_entity, '', attrs, aliases)

        query = cls.query
        loaded_paths = []
        for path, al in aliases.items():
            relationship_path = path.replace(RELATION_SPLITTER, '.')
            query = query.outerjoin(al[0], al[1]) \
                .options(contains_eager(relationship_path, alias=al[0]))
            loaded_paths.append(relationship_path)

        for attr, value in filters.items():
            if RELATION_SPLITTER in attr:
                parts = attr.rsplit(RELATION_SPLITTER, 1)
                entity, attr_name = aliases[parts[0]][0], parts[1]
            else:
                entity, attr_name = root_entity, attr
            try:
                query = query.filter(*entity.filter_expr(**{attr_name: value}))
            except KeyError as e:
                raise KeyError(f"Incorrect filter path `{attr}`: {e}")

        for attr in sort_attrs:
            if RELATION_SPLITTER in attr:
                prefix = ''
                if attr.startswith(DESC_PREFIX):
                    prefix = DESC_PREFIX
                    attr = attr.lstrip(DESC_PREFIX)
                parts = attr.rsplit(RELATION_SPLITTER, 1)
                entity, attr_name = aliases[parts[0]][0], prefix + parts[1]
            else:
                entity, attr_name = root_entity, attr
            try:
                query = query.order_by(*entity.order_expr(attr_name))
            except KeyError as e:
                raise KeyError(f"Incorrect order path `{attr}`: {e}")

        if schema:
            flat_schema = _flatten_schema(schema)
            not_loaded_part = {path: v for path, v in flat_schema.items()
                               if path not in loaded_paths}
            query = query.options(*_eager_expr_from_flat_schema(
                not_loaded_part))

        return query

    @classmethod
    def where(cls, **filters):
        """
        Shortcut for smart_query() method
        Example 1:
          Product.where(subject_ids__in=[1,2], grade_from_id=2).all()

        Example 2:
          filters = {'subject_ids__in': [1,2], 'grade_from_id': 2}
          Product.where(**filters).all()

        Example 3 (with joins):
          Post.where(public=True, user___name__startswith='Bi').all()
        """
        return cls.smart_query(filters)

    @classmethod
    def sort(cls, *columns):
        """
        Shortcut for smart_query() method
        Example 1:
            User.sort('first_name','-user_id')
        This is equal to
            db.query(User).order_by(*User.order_expr('first_name','-user_id'))

        Example 2:
            columns = ['first_name','-user_id']
            User.sort(*columns)
        This is equal to
            columns = ['first_name','-user_id']
            db.query(User).order_by(*User.order_expr(*columns))

        Exanple 3 (with joins):
            Post.sort('comments___rating', 'user___name').all()
        """
        return cls.smart_query({}, columns)

    @classmethod
    def with_(cls, schema):
        """
        Query class and eager load schema at once.
        :type schema: dict

        Example:
            schema = {
                'user': JOINED, # joinedload user
                'comments': (SUBQUERY, {  # load comments in separate query
                    'user': JOINED  # but, in this separate query, join user
                })
            }
            # the same schema using class properties:
            schema = {
                Post.user: JOINED,
                Post.comments: (SUBQUERY, {
                    Comment.user: JOINED
                })
            }
            User.with_(schema).first()
        """
        return cls.query.options(*eager_expr(schema or {}))

    @classmethod
    def with_joined(cls, *paths):
        """
        Eagerload for simple cases where we need to just
         joined load some relations
        In strings syntax, you can split relations with dot
         due to this SQLAlchemy feature: https://goo.gl/yM2DLX

        :type paths: *List[str] | *List[InstrumentedAttribute]

        Example 1:
            Comment.with_joined('user', 'post', 'post.comments').first()

        Example 2:
            Comment.with_joined(Comment.user, Comment.post).first()
        """
        options = [joinedload(path) for path in paths]
        return cls.query.options(*options)

    @classmethod
    def with_subquery(cls, *paths):
        """
        Eagerload for simple cases where we need to just
         joined load some relations
        In strings syntax, you can split relations with dot
         (it's SQLAlchemy feature)

        :type paths: *List[str] | *List[InstrumentedAttribute]

        Example 1:
            User.with_subquery('posts', 'posts.comments').all()

        Example 2:
            User.with_subquery(User.posts, User.comments).all()
        """
        options = [subqueryload(path) for path in paths]
        return cls.query.options(*options)

    @property
    def _id_str(self):
        ids = inspect(self).identity
        if ids:
            return '-'.join([str(x) for x in ids]) if len(ids) > 1 \
                else str(ids[0])
        else:
            return 'None'

    @property
    def _repr_attrs_str(self):
        max_length = self.__repr_max_length__

        values = []
        single = len(self.__repr_attrs__) == 1
        for key in self.__repr_attrs__:
            if not hasattr(self, key):
                raise KeyError(f"{self.__class__} has incorrect attribute "
                               f"'{key}' in __repr__attrs__")
            value = getattr(self, key)
            wrap_in_quote = isinstance(value, string_types)

            value = str(value)
            if len(value) > max_length:
                value = value[:max_length] + '...'

            if wrap_in_quote:
                value = f"'{value}'"
            values.append(value if single else f"{key}:{value}")

        return ' '.join(values)

    def __repr__(self):
        # get id like '#123'
        id_str = ('#' + self._id_str) if self._id_str else ''
        # join class name, id and repr_attrs
        repr_attr = ' ' + self._repr_attrs_str if self._repr_attrs_str else ''
        return f"<{self.__class__.__name__} {id_str}{repr_attr}>"

    def fill(self, **kwargs):
        for name in kwargs.keys():
            if name in self.settable_attributes:
                setattr(self, name, kwargs[name])
            else:
                raise KeyError(f"Attribute '{name}' doesn't exist")

        return self

    def save(self):
        """Saves the updated model to the current entity db.
        """
        session.add(self)
        session.flush()
        return self

    @classmethod
    def create(cls, **kwargs):
        """Create and persist a new record for the model
        :param kwargs: attributes for the record
        :return: the new model instance
        """
        return cls().fill(**kwargs).save()

    def update(self, **kwargs):
        """Same as :meth:`fill` method but persists changes to database.
        """
        return self.fill(**kwargs).save()

    def delete(self):
        """Removes the model from the current entity session and mark for deletion.
        """
        session.delete(self)
        session.flush()

    @classmethod
    def destroy(cls, *ids):
        """Delete the records with the given ids
        :type ids: list
        :param ids: primary key ids of records
        """
        for pk in ids:
            cls.find(pk).delete()
        session.flush()

    @classmethod
    def all(cls):
        return cls.query.all()

    @classmethod
    def first(cls):
        return cls.query.first()

    @classmethod
    def find(cls, id_):
        """Find record by the id
        :param id_: the primary key
        """
        return cls.query.get(id_)

    @classproperty
    def columns(cls):
        return inspect(cls).columns.keys()

    @classproperty
    def relations(cls):
        """Return a `list` of relationship names or the given model
        """
        return [c.key for c in cls.__mapper__.iterate_properties
                if isinstance(c, RelationshipProperty)]

    @classproperty
    def settable_attributes(cls):
        return cls.columns + cls.hybrid_properties + cls.settable_relations

    @classproperty
    def settable_relations(cls):
        """Return a `list` of relationship names or the given model
        """
        return [r for r in cls.relations
                if getattr(cls, r).property.viewonly is False]

    @classproperty
    def hybrid_properties(cls):
        items = inspect(cls).all_orm_descriptors
        return [item.__name__ for item in items
                if type(item) == hybrid_property]

    @classproperty
    def hybrid_methods_full(cls):
        items = inspect(cls).all_orm_descriptors
        return {item.func.__name__: item
                for item in items if type(item) == hybrid_method}

    @classproperty
    def hybrid_methods(cls):
        return list(cls.hybrid_methods_full.keys())


force_auto_coercion()
force_instant_defaults()
engine = create_engine(settings.DATABASE_URL, encoding="utf-8", echo=False, pool_pre_ping=True)
session = scoped_session(sessionmaker(bind=engine))
Model = declarative_base(cls=BaseModel)
Model.query = session.query_property()
metadata = Model.metadata

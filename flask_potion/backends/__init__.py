from __future__ import division
import datetime
from math import ceil

import six
from werkzeug.utils import cached_property
from flask_potion.filters import filters_for_fields, FILTER_NAMES, FILTERS_BY_TYPE
from flask_potion.exceptions import ItemNotFound
from flask_potion import fields


class Manager(object):
    """

    .. attribute:: supported_comparators

        A tuple of names filter comparators supported by this manager.

    :param flask_potion.resource.Resource resource: resource class
    :param model: model read from ``Meta.model`` or ``None``
    """
    filter_names = FILTER_NAMES
    filters_by_type = FILTERS_BY_TYPE
    supported_comparators = ()

    def __init__(self, resource, model):
        self.resource = resource
        self.model = model

        self._init_key_converters(resource, resource.meta)

    def _create_filter(self, filter_class, name, field, attribute):
        return filter_class(name,
                            field=field,
                            attribute=field.attribute or attribute)

    @cached_property
    def filters(self):
        fields = self.resource.schema.fields
        filters = filters_for_fields(self.resource.schema.fields,
                                     self.resource.meta.filters,
                                     filter_names=self.filter_names,
                                     filters_by_type=self.filters_by_type)
        return {
            field_name: {
                name: self._create_filter(filter, name, fields[field_name], field_name)
                for name, filter in field_filters.items()
                }
            for field_name, field_filters in filters.items()
        }

    def _init_key_converters(self, resource, meta):
        if 'natural_key' in meta:
            from flask_potion.natural_keys import PropertyKey, PropertiesKey
            if isinstance(meta.natural_key, str):
                meta['key_converters'] += (PropertyKey(meta.natural_key),)
            elif isinstance(meta.natural_key, (list, tuple)):
                meta['key_converters'] += (PropertiesKey(*meta.natural_key),)

        if 'key_converters' in meta:
            meta.key_converters = [k.bind(resource) for k in meta['key_converters']]
            meta.key_converters_by_type = {}
            for nk in meta.key_converters:
                if nk.matcher_type() in meta.key_converters_by_type:
                    raise RuntimeError(
                        'Multiple keys of type {} defined for {}'.format(nk.matcher_type(), meta.name))
                meta.key_converters_by_type[nk.matcher_type()] = nk

    @staticmethod
    def _get_field_from_python_type(python_type):
        try:
            return {
                str: fields.String,
                six.text_type: fields.String,
                int: fields.Integer,
                float: fields.Number,
                bool: fields.Boolean,
                list: fields.Array,
                dict: fields.Object,
                datetime.date: fields.Date,
                datetime.datetime: fields.DateTime
            }[python_type]
        except KeyError:
            raise RuntimeError('No appropriate field class for "{}" type found'.format(python_type))

    def is_sortable_field(self, field):
        return isinstance(field, (fields.String,
                                  fields.Boolean,
                                  fields.Number,
                                  fields.Integer,
                                  fields.Date,
                                  fields.DateTime))

    def get_field_comparators(self, field):
        pass

    def relation_instances(self, item, attribute, target_resource, page=None, per_page=None):
        """

        :param item:
        :param attribute:
        :param target_resource:
        :param page:
        :param per_page:
        :return:
        """
        raise NotImplementedError()

    def relation_add(self, item, attribute, target_resource, target_item):
        """

        :param item:
        :param attribute:
        :param target_resource:
        :param target_item:
        :return:
        """
        raise NotImplementedError()

    def relation_remove(self, item, attribute, target_resource, target_item):
        """

        :param item:
        :param attribute:
        :param target_resource:
        :param target_item:
        :return:
        """
        raise NotImplementedError()

    def paginated_instances(self, page, per_page, where=None, sort=None):
        """

        :param page:
        :param per_page:
        :param where:
        :param sort:
        :return: a :class:`Pagination` object or similar
        """
        pass

    def instances(self, where=None, sort=None):
        """

        :param where:
        :param sort:
        :return:
        """
        pass

    def first(self, where=None, sort=None):
        """

        :param where:
        :param sort:
        :return:
        :raises exceptions.ItemNotFound:
        """
        try:
            return self.instances(where, sort)[0]
        except IndexError:
            raise ItemNotFound(self.resource, where=where)

    def create(self, properties, commit=True):
        """

        :param properties:
        :param commit:
        :return:
        """
        pass

    def read(self, id):
        """

        :param id:
        :return:
        """
        pass

    def update(self, item, changes, commit=True):
        """

        :param item:
        :param changes:
        :param commit:
        :return:
        """
        pass

    def delete(self, item):
        """

        :param item:
        :return:
        """
        pass

    def delete_by_id(self, id):
        """

        :param id:
        :return:
        """
        return self.delete(self.read(id))

    def commit(self):
        pass

    def begin(self):

        pass


class Pagination(object):
    """
    A pagination class for list-like instances.

    :param items:
    :param page:
    :param per_page:
    :param total:
    """

    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total

    @property
    def pages(self):
        return max(1, int(ceil(self.total / self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @classmethod
    def from_list(cls, items, page, per_page):
        start = per_page * (page - 1)
        return Pagination(items[start:start + per_page], page, per_page, len(items))
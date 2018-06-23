from stig.client.filters.torrent import (SingleTorrentFilter, TorrentFilter)
from stig.client.base import TorrentBase
import unittest


def get_names(torrents, *ids):
    return tuple(t['name'] for t in torrents)


class MockTorrent(TorrentBase):
    mock_id = 1
    def __init__(self, dct, **kwargs):
        dct.update(kwargs)
        if 'id' not in dct:
            type(self).mock_id += 1
            dct['id'] = type(self).mock_id
        if 'name' not in dct:
            kwargs['name'] = 'MockTorrent #' + str(type(self).mock_id)
        self._dct = dct

    def __getitem__(self, item):
        return self._dct[item]


class TestSingleTorrentFilter(unittest.TestCase):
    def test_parser(self):
        self.assertEqual(str(SingleTorrentFilter()), 'all')
        self.assertEqual(str(SingleTorrentFilter('*')), 'all')
        self.assertEqual(str(SingleTorrentFilter('idle')), 'idle')
        self.assertEqual(str(SingleTorrentFilter('!idle')), '!idle')
        self.assertEqual(str(SingleTorrentFilter('foo')), '~foo')
        self.assertEqual(str(SingleTorrentFilter('~foo')), '~foo')
        self.assertEqual(str(SingleTorrentFilter('=foo')), '=foo')
        self.assertEqual(str(SingleTorrentFilter('!=foo')), '!=foo')
        self.assertEqual(str(SingleTorrentFilter('name= foo')), "=' foo'")
        self.assertEqual(str(SingleTorrentFilter('name!=foo ')), "!='foo '")
        self.assertEqual(str(SingleTorrentFilter('%downloaded>17.2')), '%downloaded>17.2%')

        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('=')
        self.assertEqual(str(cm.exception), "Missing value: = ...")
        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('%downloaded!>')
        self.assertEqual(str(cm.exception), "Missing value: %downloaded!> ...")
        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('name! =foo')
        self.assertEqual(str(cm.exception), "Malformed filter expression: 'name! =foo'")

    def test_parsing_spaces(self):
        self.assertEqual(str(SingleTorrentFilter(' idle ')), 'idle')
        self.assertEqual(str(SingleTorrentFilter('   %downloaded   ')), '%downloaded')
        self.assertEqual(str(SingleTorrentFilter(' name = foo')), '=foo')
        self.assertEqual(str(SingleTorrentFilter(' name != foo  ')), '!=foo')
        self.assertEqual(str(SingleTorrentFilter(' name= foo, bar and baz  ')), "=' foo, bar and baz  '")

        self.assertEqual(str(SingleTorrentFilter(' =   foo, bar and baz ')), '=foo, bar and baz')
        self.assertEqual(str(SingleTorrentFilter('=   foo, bar and baz ')), "='   foo, bar and baz '")

    def test_unknown_filter(self):
        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('foo=bar')
        self.assertEqual(str(cm.exception), "Invalid filter name: 'foo'")
        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('foo!~bar')
        self.assertEqual(str(cm.exception), "Invalid filter name: 'foo'")

    def test_aliases(self):
        tlist = (MockTorrent({'name': 'foo', 'rate-down': 0}),
                 MockTorrent({'name': 'bar', 'rate-down': 500e3}))
        result1 = tuple(SingleTorrentFilter('rate-down>100k').apply(tlist, key='name'))
        result2 = tuple(SingleTorrentFilter('rdn>100k').apply(tlist, key='name'))
        self.assertEqual(result1, result2)

    def test_no_filter(self):
        tlist = (MockTorrent({'name': 'foo'}),
                 MockTorrent({'name': 'bar'}),
                 MockTorrent({'name': 'baz'}))
        result = tuple(SingleTorrentFilter().apply(tlist, key='name'))
        self.assertEqual(result, ('foo', 'bar', 'baz'))

    def test_invalid_operator(self):
        tlist = (MockTorrent({'name': 'foo', '%downloaded': 100}),)
        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('%downloaded~0').apply(tlist)
        self.assertEqual(str(cm.exception), "Invalid operator for filter '%downloaded': ~")

    def test_invalid_value(self):
        tlist = (MockTorrent({'name': 'foo', 'rate-down': 100e3}),)
        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('rate-down>foo').apply(tlist)
        self.assertEqual(str(cm.exception), "Invalid value for filter 'rate-down': 'foo'")

    def test_equality(self):
        self.assertEqual(SingleTorrentFilter('name=foo'),
                         SingleTorrentFilter('name=foo'))
        self.assertNotEqual(SingleTorrentFilter('name=foo'),
                            SingleTorrentFilter('name=Foo'))
        self.assertEqual(SingleTorrentFilter('complete'),
                         SingleTorrentFilter('complete'))
        self.assertNotEqual(SingleTorrentFilter('complete'),
                            SingleTorrentFilter('!complete'))
        self.assertEqual(SingleTorrentFilter('!private'),
                         SingleTorrentFilter('!private'))
        self.assertNotEqual(SingleTorrentFilter('private'),
                            SingleTorrentFilter('!private'))
        self.assertEqual(SingleTorrentFilter('path=/some/path/to/torrents/'),
                         SingleTorrentFilter('path=/some/path/to/torrents'))

    def test_equals_operator(self):
        tlist = (MockTorrent({'name': 'foo'}),
                 MockTorrent({'name': 'bar'}),
                 MockTorrent({'name': 'baz'}))
        result = tuple(SingleTorrentFilter('name=foo').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))
        result = tuple(SingleTorrentFilter('name=bar').apply(tlist, key='name'))
        self.assertEqual(result, ('bar',))
        result = tuple(SingleTorrentFilter('name=baz').apply(tlist, key='name'))
        self.assertEqual(result, ('baz',))

    def test_contains_operator(self):
        tlist = (MockTorrent({'name': 'foo'}),
                 MockTorrent({'name': 'bar'}),
                 MockTorrent({'name': 'baz'}))
        result = tuple(SingleTorrentFilter('name~oo').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))
        result = tuple(SingleTorrentFilter('name~b').apply(tlist, key='name'))
        self.assertEqual(result, ('bar', 'baz'))

    def test_inverter(self):
        tlist = (MockTorrent({'name': 'foo', 'rate-down': 0}),
                 MockTorrent({'name': 'bar', 'rate-down': 500e3}))
        result = tuple(SingleTorrentFilter('downloading').apply(tlist, key='name'))
        self.assertEqual(result, ('bar',))
        result = tuple(SingleTorrentFilter('!downloading').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))
        result = tuple(SingleTorrentFilter('name~oo').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))
        result = tuple(SingleTorrentFilter('name!~oo').apply(tlist, key='name'))
        self.assertEqual(result, ('bar',))
        result = tuple(SingleTorrentFilter('!name~oo').apply(tlist, key='name'))
        self.assertEqual(result, ('bar',))
        result = tuple(SingleTorrentFilter('!name!~foo').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))

    def test_larger_operator_with_numbers(self):
        tlist = (MockTorrent({'name': 'foo', 'rate-down': 0}),
                 MockTorrent({'name': 'bar', 'rate-down': 500e3}),
                 MockTorrent({'name': 'baz', 'rate-down': 1000e3}))
        result = tuple(SingleTorrentFilter('rate-down>=0').apply(tlist, key='name'))
        self.assertEqual(result, ('foo', 'bar', 'baz'))
        result = tuple(SingleTorrentFilter('rate-down>0').apply(tlist, key='name'))
        self.assertEqual(result, ('bar', 'baz'))
        result = tuple(SingleTorrentFilter('rate-down>=500k').apply(tlist, key='name'))
        self.assertEqual(result, ('bar', 'baz'))
        result = tuple(SingleTorrentFilter('rate-down>500k').apply(tlist, key='name'))
        self.assertEqual(result, ('baz',))
        result = tuple(SingleTorrentFilter('rate-down>=1M').apply(tlist, key='name'))
        self.assertEqual(result, ('baz',))
        result = tuple(SingleTorrentFilter('rate-down>1M').apply(tlist, key='name'))
        self.assertEqual(result, ())

    def test_smaller_operator_with_numbers(self):
        tlist = (MockTorrent({'name': 'foo', 'rate-down': 0}),
                 MockTorrent({'name': 'bar', 'rate-down': 500e3}),
                 MockTorrent({'name': 'baz', 'rate-down': 1000e3}))
        result = tuple(SingleTorrentFilter('rate-down<0').apply(tlist, key='name'))
        self.assertEqual(result, ())
        result = tuple(SingleTorrentFilter('rate-down<=0').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))
        result = tuple(SingleTorrentFilter('rate-down<500k').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))
        result = tuple(SingleTorrentFilter('rate-down<=500k').apply(tlist, key='name'))
        self.assertEqual(result, ('foo', 'bar'))
        result = tuple(SingleTorrentFilter('rate-down<1M').apply(tlist, key='name'))
        self.assertEqual(result, ('foo', 'bar'))
        result = tuple(SingleTorrentFilter('rate-down<=1M').apply(tlist, key='name'))
        self.assertEqual(result, ('foo', 'bar', 'baz'))

    def test_larger_operator_with_strings(self):
        tlist = (MockTorrent({'name': 'x'}),
                 MockTorrent({'name': 'xx'}),
                 MockTorrent({'name': 'xxx'}))
        result = SingleTorrentFilter('name>2').apply(tlist, key='name')
        self.assertEqual(set(result), {'xxx'})
        result = SingleTorrentFilter('name>=2').apply(tlist, key='name')
        self.assertEqual(set(result), {'xx', 'xxx'})
        result = tuple(SingleTorrentFilter('name>yy').apply(tlist, key='name'))
        self.assertEqual(result, ('xxx',))
        result = SingleTorrentFilter('name>=yy').apply(tlist, key='name')
        self.assertEqual(set(result), {'xx', 'xxx'})

    def test_smaller_operator_with_strings(self):
        tlist = (MockTorrent({'name': 'x'}),
                 MockTorrent({'name': 'xx'}),
                 MockTorrent({'name': 'xxx'}))
        result = tuple(SingleTorrentFilter('name<2').apply(tlist, key='name'))
        self.assertEqual(result, ('x',))
        result = tuple(SingleTorrentFilter('name<=2').apply(tlist, key='name'))
        self.assertEqual(result, ('x', 'xx'))
        result = tuple(SingleTorrentFilter('name<yy').apply(tlist, key='name'))
        self.assertEqual(result, ('x',))
        result = tuple(SingleTorrentFilter('name<=yy').apply(tlist, key='name'))
        self.assertEqual(result, ('x', 'xx'))

    def test_boolean_evaluation_without_value(self):
        tlist = (MockTorrent({'name': 'foo', 'rate-down': 0}),
                 MockTorrent({'name': 'bar', 'rate-down': 100}))
        result = tuple(SingleTorrentFilter('rate-down').apply(tlist, key='name'))
        self.assertEqual(result, ('bar',))
        result = tuple(SingleTorrentFilter('!rate-down').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))

    def test_default_filter(self):
        tlist = (MockTorrent({'name': 'foo'}),
                 MockTorrent({'name': 'bar'}),
                 MockTorrent({'name': ''}))
        result = tuple(SingleTorrentFilter('=foo').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))
        result = tuple(SingleTorrentFilter('!=foo').apply(tlist, key='name'))
        self.assertEqual(result, ('bar', ''))
        result = tuple(SingleTorrentFilter('~f').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))
        result = tuple(SingleTorrentFilter('!~f').apply(tlist, key='name'))
        self.assertEqual(result, ('bar', ''))
        result = tuple(SingleTorrentFilter('!').apply(tlist, key='name'))
        self.assertEqual(result, ('',))

    def test_percent_downloaded_filter(self):
        tlist = (MockTorrent({'name': 'foo', '%downloaded': 99.3}),
                 MockTorrent({'name': 'bar', '%downloaded': 100}),
                 MockTorrent({'name': 'baz', '%downloaded': 0}))
        result = tuple(SingleTorrentFilter('complete').apply(tlist, key='name'))
        self.assertEqual(result, ('bar',))
        result = tuple(SingleTorrentFilter('!complete').apply(tlist, key='name'))
        self.assertEqual(result, ('foo', 'baz'))
        result = tuple(SingleTorrentFilter('%downloaded=99.3').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))
        result = tuple(SingleTorrentFilter('%downloaded<99.3').apply(tlist, key='name'))
        self.assertEqual(result, ('baz',))
        result = tuple(SingleTorrentFilter('%downloaded>99.3').apply(tlist, key='name'))
        self.assertEqual(result, ('bar',))

    def test_status_filter(self):
        from stig.client.ttypes import Status
        tlist = (MockTorrent({'name': 'foo', 'status': (Status.STOPPED, Status.IDLE),
                              'rate-down': 0, 'rate-up': 0, 'peers-connected': 0}),
                 MockTorrent({'name': 'bar', 'status': (Status.DOWNLOAD, Status.CONNECTED),
                              'rate-down': 100e3, 'rate-up': 0, 'peers-connected': 1}),
                 MockTorrent({'name': 'baz', 'status': (Status.UPLOAD, Status.CONNECTED),
                              'rate-down': 0, 'rate-up': 100e3, 'peers-connected': 2}))
        result = tuple(SingleTorrentFilter('stopped').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))
        result = tuple(SingleTorrentFilter('downloading').apply(tlist, key='name'))
        self.assertEqual(result, ('bar',))
        result = tuple(SingleTorrentFilter('uploading').apply(tlist, key='name'))
        self.assertEqual(result, ('baz',))
        result = tuple(SingleTorrentFilter('active').apply(tlist, key='name'))
        self.assertEqual(result, ('bar', 'baz'))

    def test_private_filter(self):
        tlist = (MockTorrent({'name': 'foo', 'private': True}),
                 MockTorrent({'name': 'bar', 'private': False}))
        for f in ('!public', 'private'):
            result = tuple(SingleTorrentFilter(f).apply(tlist, key='name'))
            self.assertEqual(result, ('foo',))
        for f in ('public', '!private'):
            result = tuple(SingleTorrentFilter(f).apply(tlist, key='name'))
            self.assertEqual(result, ('bar',))

    def test_path_filter(self):
        tlist = (MockTorrent({'name': 'foo', 'path': '/x/y/z/foo.asdf'}),
                 MockTorrent({'name': 'bar', 'path': '/x/z/y/bar.asdf'}))
        result = tuple(SingleTorrentFilter('path~asdf').apply(tlist, key='name'))
        self.assertEqual(result, ('foo', 'bar',))
        result = tuple(SingleTorrentFilter('path~foo').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))
        result = tuple(SingleTorrentFilter('path~/x').apply(tlist, key='name'))
        self.assertEqual(result, ('foo', 'bar'))
        result = tuple(SingleTorrentFilter('path~y/z').apply(tlist, key='name'))
        self.assertEqual(result, ('foo',))

    def test_eta_filter_larger_smaller(self):
        class MockTimespan(int):
            def __new__(cls, seconds, is_known):
                obj = super().__new__(cls, seconds)
                obj.is_known = is_known
                return obj

        tlist = (MockTorrent({'name': 'foo', 'timespan-eta': MockTimespan((60*60),   is_known=True)}),
                 MockTorrent({'name': 'bar', 'timespan-eta': MockTimespan((60*60)+1, is_known=True)}))
        result = tuple(SingleTorrentFilter('eta>1h').apply(tlist, key='name'))
        self.assertEqual(result, ('bar',))
        result = tuple(SingleTorrentFilter('eta>=1h').apply(tlist, key='name'))
        self.assertEqual(result, ('foo', 'bar'))

    # def test_date_filter(self):
    #     tids = SingleTorrentFilter('completed>2002-01-01').apply(self.tlist, key='id')
    #     self.assertEqual(set(tids), {3, 4})


class TestTorrentFilter(unittest.TestCase):
    def test_parser(self):
        for s in ('&', '|', '&idle', '|idle'):
            with self.assertRaisesRegex(ValueError, "can't start with operator"):
                TorrentFilter(s)
        for s in ('idle&', 'idle|'):
            with self.assertRaisesRegex(ValueError, "can't end with operator"):
                TorrentFilter(s)
        for s in ('idle||private', 'idle&&private', 'idle&|private', 'idle|&private',
                  'idle||private&name~foo|name~bar', 'name~foo|name~bar&idle|&private|name~baz'):
            with self.assertRaisesRegex(ValueError, "Consecutive operators: 'idle[&|]{2}private'"):
                TorrentFilter(s)
        TorrentFilter()

    def test_sequence_argument(self):
        f1 = TorrentFilter(['foo', 'bar'])
        f2 = TorrentFilter('foo|bar')
        self.assertEqual(f1, f2)

    def test_no_filters(self):
        tlist = (MockTorrent({'name': 'foo'}),
                 MockTorrent({'name': 'bar'}))
        result = tuple(TorrentFilter().apply(tlist))
        self.assertEqual(get_names(result), ('foo', 'bar'))

    def test_any_allfilter_means_no_filters(self):
        self.assertEqual(str(TorrentFilter('name~f|all&public')), 'all')

    def test_AND_operator(self):
        tlist = (MockTorrent({'name': 'foo', 'private': True, 'rate-up': 123, '%downloaded': 50}),
                 MockTorrent({'name': 'zoo', 'private': False, 'rate-up': 0, '%downloaded': 60}),
                 MockTorrent({'name': 'bar', 'private': False, 'rate-up': 456, '%downloaded': 100}),
                 MockTorrent({'name': 'baz', 'private': True, 'rate-up': 0, '%downloaded': 0}))
        result = tuple(TorrentFilter('~b&public').apply(tlist))
        self.assertEqual(get_names(result), ('bar',))
        result = tuple(TorrentFilter('~b&!public').apply(tlist))
        self.assertEqual(get_names(result), ('baz',))
        result = tuple(TorrentFilter('rate-up>100&!complete&~oo').apply(tlist))
        self.assertEqual(get_names(result), ('foo',))
        result = tuple(TorrentFilter('rate-up>400&!private&complete&name~ar').apply(tlist))
        self.assertEqual(get_names(result), ('bar',))

    def test_OR_operator(self):
        tlist = (MockTorrent({'name': 'foo', 'private': True, 'rate-up': 123, '%downloaded': 50}),
                 MockTorrent({'name': 'zoo', 'private': False, 'rate-up': 0, '%downloaded': 60}),
                 MockTorrent({'name': 'bar', 'private': False, 'rate-up': 456, '%downloaded': 100}),
                 MockTorrent({'name': 'baz', 'private': True, 'rate-up': 0, '%downloaded': 0}))
        result = tuple(TorrentFilter('~f|public').apply(tlist))
        self.assertEqual(get_names(result), ('foo', 'zoo', 'bar'))
        result = tuple(TorrentFilter('~bar|rate-up|%downloaded=0').apply(tlist))
        self.assertEqual(get_names(result), ('foo', 'bar', 'baz'))
        result = tuple(TorrentFilter('%downloaded<50|%downloaded>=60').apply(tlist))
        self.assertEqual(get_names(result), ('zoo', 'bar', 'baz'))
        result = tuple(TorrentFilter('%downloaded<=50|private|!rate-up').apply(tlist))
        self.assertEqual(get_names(result), ('foo', 'zoo', 'baz'))

    def test_AND_OR_operator_combinations(self):
        tlist = (MockTorrent({'name': 'foo', 'private': True, 'rate-up': 123, '%downloaded': 50}),
                 MockTorrent({'name': 'zoo', 'private': False, 'rate-up': 0, '%downloaded': 60}),
                 MockTorrent({'name': 'bar', 'private': False, 'rate-up': 456, '%downloaded': 100}),
                 MockTorrent({'name': 'baz', 'private': True, 'rate-up': 0, '%downloaded': 0}))
        result = tuple(TorrentFilter('!private&complete|name=foo').apply(tlist))
        self.assertEqual(get_names(result), ('foo', 'bar'))
        result = tuple(TorrentFilter('~oo|incomplete&private').apply(tlist))
        self.assertEqual(get_names(result), ('foo', 'zoo', 'baz'))
        result = tuple(TorrentFilter('~oo&rate-up|complete&uploading|private&!uploading&name=baz').apply(tlist))
        self.assertEqual(get_names(result), ('foo', 'bar', 'baz'))

    def test_escaping_operators(self):
        tlist = (MockTorrent({'name': 'foo&bar'}),
                 MockTorrent({'name': 'foo||bar'}),
                 MockTorrent({'name': 'foo && bar'}),
                 MockTorrent({'name': 'foo | bar'}))
        result = tuple(TorrentFilter('~\&').apply(tlist))
        self.assertEqual(get_names(result), ('foo&bar', 'foo && bar'))
        result = tuple(TorrentFilter('~\&\&').apply(tlist))
        self.assertEqual(get_names(result), ('foo && bar',))
        result = tuple(TorrentFilter('~\|').apply(tlist))
        self.assertEqual(get_names(result), ('foo||bar', 'foo | bar'))
        result = tuple(TorrentFilter('!~\|').apply(tlist))
        self.assertEqual(get_names(result), ('foo&bar', 'foo && bar'))
        result = tuple(TorrentFilter('!~\|\|').apply(tlist))
        self.assertEqual(get_names(result), ('foo&bar', 'foo && bar', 'foo | bar'))
        result = tuple(TorrentFilter('~\|\||\&\&').apply(tlist))
        self.assertEqual(get_names(result), ('foo||bar', 'foo && bar'))
        result = tuple(TorrentFilter('!~\|\|&!\&\&').apply(tlist))
        self.assertEqual(get_names(result), ('foo&bar', 'foo | bar'))

    def test_equality(self):
        self.assertEqual(TorrentFilter('idle&private'),
                         TorrentFilter('idle&private'))
        self.assertEqual(TorrentFilter('idle&private'),
                         TorrentFilter('private&idle'))
        self.assertEqual(TorrentFilter('idle|private'),
                         TorrentFilter('private|idle'))
        self.assertNotEqual(TorrentFilter('idle|private'),
                            TorrentFilter('idle&private'))
        self.assertEqual(TorrentFilter('idle|private&stopped'),
                         TorrentFilter('stopped&private|idle'))
        self.assertNotEqual(TorrentFilter('idle|private&stopped'),
                            TorrentFilter('private|idle&stopped'))
        self.assertEqual(TorrentFilter('idle|private&stopped|name~foo'),
                         TorrentFilter('stopped&private|name~foo|idle'))
        self.assertNotEqual(TorrentFilter('idle|private&stopped|name~foo'),
                            TorrentFilter('stopped&private|idle'))
        self.assertEqual(TorrentFilter('idle&active|private&stopped|name~foo'),
                         TorrentFilter('stopped&private|name~foo|idle&active'))
        self.assertNotEqual(TorrentFilter('idle&active|private&stopped|name~foo'),
                            TorrentFilter('stopped&private|name~foo|idle'))

    def test_multiple_implied_name_filters(self):
        self.assertEqual(str(TorrentFilter('foo|bar')), '~foo|~bar')

    def test_combining_filters(self):
        f1 = TorrentFilter('name=foo')
        f2 = TorrentFilter('active')
        f3 = f1+f2
        self.assertEqual(f3, TorrentFilter('name=foo|active'))

        f1 = TorrentFilter('name~foo&private|path~other')
        f2 = TorrentFilter('active&private|public&!complete')
        f3 = f1+f2
        self.assertEqual(str(f3), ('~foo&private|path~other|'
                                   'active&private|public&!complete'))

        f1 = TorrentFilter('public&active')
        f2 = TorrentFilter('active&public')
        self.assertEqual(str(f1+f2), 'public&active')
        f3 = TorrentFilter('complete')
        self.assertEqual(str(f1+f2+f3), 'public&active|complete')
        self.assertEqual(str(f3+f2+f1), 'complete|active&public')

    def test_combining_any_filter_with_all_is_all(self):
        f = TorrentFilter('active') + TorrentFilter('all')
        self.assertEqual(f, TorrentFilter('all'))

        f = TorrentFilter('active') + TorrentFilter('private')
        self.assertEqual(f, TorrentFilter('active|private'))

    def test_needed_keys(self):
        f1 = TorrentFilter('public')
        self.assertEqual(set(f1.needed_keys), set(['private']))
        f2 = TorrentFilter('complete')
        self.assertEqual(set((f1+f2).needed_keys), set(['private', '%downloaded']))
        f3 = TorrentFilter('!private|active')
        self.assertEqual(set((f1+f2+f3).needed_keys),
                         set(['private', '%downloaded', 'peers-connected', 'status']))

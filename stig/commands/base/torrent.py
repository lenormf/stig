# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details
# http://www.gnu.org/licenses/gpl-3.0.txt

"""Base classes for torrent commands"""

from ...logging import make_logger
log = make_logger(__name__)

import asyncio

from .. import (InitCommand, ExpectedResource)


class AddTorrentsCmdbase(metaclass=InitCommand):
    name = 'add'
    aliases = ('download','get')
    provides = set()
    category = 'torrent'
    description = 'Download torrents'
    usage = ('add <TORRENT> <TORRENT> <TORRENT> ... [<OPTIONS>]',)
    examples = ('add 72d7a3179da3de7a76b98f3782c31843e3f818ee',
                'add --stopped http://example.org/something.torrent')
    argspecs = (
        { 'names': ('TORRENT',), 'nargs': '+',
          'description': 'Link or path to torrent file, magnet link or hash' },
        { 'names': ('--stopped','-s'), 'action': 'store_true',
          'description': 'Do not start downloading the added torrent' },
    )

    srvapi = ExpectedResource
    cmdutils = ExpectedResource  # Needed by make_request

    async def run(self, TORRENT, stopped):
        success = True
        force_torrentlist_update = False
        for source in TORRENT:
            response = await self.make_request(self.srvapi.torrent.add(source, stopped=stopped))
            success = success and response.success
            force_torrentlist_update = force_torrentlist_update or success

        # Update torrentlist AFTER all 'add' requests
        if success and force_torrentlist_update and hasattr(self, 'update_torrentlist'):
            self.update_torrentlist()
        return success


class ListTorrentsCmdbase(metaclass=InitCommand):
    name = 'list'
    aliases = ('ls',)
    provides = set()
    category = 'torrent'
    description = 'List torrents'
    usage = ('list [<OPTIONS>]',
             'list [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('ls active',
                'ls !active',
                'ls seeds<10',
                'ls active&tracker~example.org',
                'ls active|idle&tracker~example')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filter`)'},

        { 'names': ('--sort', '-s'),
          'default_description': "current value of 'tlist.sort' setting",
          'description': ('Comma-separated list of sort orders '
                          "(see 'sort' command for available sort orders)") },

        { 'names': ('--columns', '-c'),
          'default_description': "current value of 'tlist.columns' setting",
          'description': ('Comma-separated list of column names '
                          "(see 'help tlist.columns' for available columns)") },
    )
    more_sections = {
        'SCRIPTING': (
            ("If invoked as a command line argument and the output does not "
             "go to a TTY (i.e. the terminal size can't be determined), "
             "the output is optimized for scripting.  Numbers are "
             "unformatted, columns are separated by '|' and headers are "
             "not printed."),
            "",
            ("To enforce human-readable, formatted output, set the environment"
             "variables COLUMNS and LINES."),
            "",
            "\t$ \tCOLUMNS=80 LINES=24 {APPNAME} ls | less -R"
        ),
    }


    cmdutils = ExpectedResource
    cfg = ExpectedResource

    async def run(self, FILTER, sort, columns):
        sort = self.cfg['tlist.sort'].value if sort is None else sort
        columns = self.cfg['tlist.columns'].value if columns is None else columns
        try:
            filters = self.cmdutils.parseargs_tfilter(TORRENT_FILTER)
            sort = self.cmdutils.parseargs_sort(sort)
            columns = self.cmdutils.parseargs_tcolumns(columns)
        except ValueError as e:
            log.error(e)
            return False
        else:
            log.debug('Listing %s torrents sorted by %s', filters, sort)
            if asyncio.iscoroutinefunction(self.make_tlist):
                return await self.make_tlist(filters, sort, columns)
            else:
                return self.make_tlist(filters, sort, columns)


class ListFilesCmdbase(metaclass=InitCommand):
    name = 'filelist'
    aliases = ('fls', 'lsf')
    provides = set()
    category = 'torrent'
    description = 'List torrent files'
    usage = ('filelist [<OPTIONS>]',
             'filelist [<OPTIONS>] [<TORRENT FILTER>] [<FILE FILTER>]')
    examples = ('filelist',
                "filelist 'A.Torrent.with.Files'")
    argspecs = (
        make_filter_argspec(default_to_focused_torrent=True),
        { 'names': ('--columns', '-c'),
          'default_description': "current value of 'flist.columns' setting",
          'description': ('Comma-separated list of column names '
                          "(see 'help flist.columns' for available columns)") },
    )

    cmdutils = ExpectedResource
    cfg = ExpectedResource

    async def run(self, FILTER, columns):
        columns = self.cfg['flist.columns'].value if columns is None else columns
        try:
            columns = self.cmdutils.parseargs_fcolumns(columns)
        except ValueError as e:
            log.error(e)
            return False

        filters = self.select_torrents(FILTER)
        if filters is None:  # Bad filter expression
            return False
        else:
            log.debug('Listing files of %s torrents', filters)
            if asyncio.iscoroutinefunction(self.make_flist):
                return await self.make_flist(filters, columns)
            else:
                return self.make_flist(filters, columns)


class RemoveTorrentsCmdbase(metaclass=InitCommand):
    name = 'remove'
    aliases = ('rm', 'delete')
    provides = set()
    category = 'torrent'
    description = 'Remove torrents'
    usage = ('remove [<OPTIONS>]',
             'remove [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('remove',
                'remove "some torrent" another\ torrent and_this_torrent',
                'remove -d "unwanted torrent"')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},

        { 'names': ('--delete-files','-d'), 'action': 'store_true',
          'description': 'Delete any downloaded files' },
    )

    srvapi = ExpectedResource
    cmdutils = ExpectedResource  # Needed by make_request

    async def run(self, TORRENT_FILTER, delete_files):
        filters = self.select_torrents(TORRENT_FILTER)
        if filters is None:  # Bad filter expression
            return False
        else:
            response = await self.make_request(
                self.srvapi.torrent.remove(filters, delete=delete_files),
                update_torrentlist=True)
            return response.success


# Argument definitions that are shared between commands
ARGSPEC_TOGGLE = {
    'names': ('--toggle','-t'), 'action': 'store_true',
    'description': ('Start TORRENT if stopped and vice versa')
}

class StartTorrentsCmdbase(metaclass=InitCommand):
    name = 'start'
    aliases = ()
    provides = set()
    category = 'torrent'
    description = 'Start downloading torrents'
    usage = ('start [<OPTIONS>]',
             'start [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('start',
                "start 'night of the living dead' Metropolis",
                'start ubuntu --force')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},
        { 'names': ('--force','-f'), 'action': 'store_true',
          'description': 'Ignore download queue' },
        ARGSPEC_TOGGLE,
    )

    srvapi = ExpectedResource
    cmdutils = ExpectedResource  # Needed by make_request

    async def run(self, TORRENT_FILTER, toggle, force):
        filters = self.select_torrents(TORRENT_FILTER)
        if filters is None:  # Bad filter expression
            return False
        elif toggle:
            response = await self.make_request(self.srvapi.torrent.toggle_stopped(filters, force=force),
                                               update_torrentlist=True)
        else:
            response = await self.make_request(self.srvapi.torrent.start(filters, force=force),
                                               update_torrentlist=True)
        return response.success


class StopTorrentsCmdbase(metaclass=InitCommand):
    name = 'stop'
    aliases = ('pause',)
    provides = set()
    category = 'torrent'
    description = 'Stop downloading torrents'
    usage = ('stop [<OPTIONS>]',
             'stop [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('stop',
                'stop "night of the living dead" idle',
                'stop --toggle ubuntu')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},
        ARGSPEC_TOGGLE,
    )

    srvapi = ExpectedResource
    cmdutils = ExpectedResource  # Needed by make_request

    async def run(self, TORRENT_FILTER, toggle):
        filters = self.select_torrents(TORRENT_FILTER)
        if filters is None:  # Bad filter expression
            return False
        elif toggle:
            response = await self.make_request(self.srvapi.torrent.toggle_stopped(filters),
                                               update_torrentlist=True)
        else:
            response = await self.make_request(self.srvapi.torrent.stop(filters),
                                               update_torrentlist=True)
        return response.success


class VerifyTorrentsCmdbase(metaclass=InitCommand):
    name = 'verify'
    aliases = ('check',)
    provides = set()
    category = 'torrent'
    description = 'Verify downloaded torrent data'
    usage = ('verify [<OPTIONS>]',
             'verify [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('verify',
                'verify debian')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},
    )

    srvapi = ExpectedResource
    cmdutils = ExpectedResource  # Needed by make_request

    async def run(self, TORRENT_FILTER):
        filters = self.select_torrents(TORRENT_FILTER)
        if filters is None:  # Bad filter expression
            return False
        else:
            response = await self.make_request(self.srvapi.torrent.verify(filters),
                                               update_torrentlist=False)
            return response.success

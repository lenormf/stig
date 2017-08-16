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

"""Commands that work exclusively in the TUI"""

from ...logging import make_logger
log = make_logger(__name__)

from .. import (InitCommand, ExpectedResource)
from ._common import make_tab_title_widget

import shlex


# Import tui module only on demand
def _get_KEYMAP_CONTEXTS():
    from ...tui.main import KEYMAP_CONTEXTS
    return sorted(KEYMAP_CONTEXTS)


class BindCmd(metaclass=InitCommand):
    name = 'bind'
    provides = {'tui'}
    category = 'tui'
    description = 'Bind keys to commands or other keys'
    usage = ('bind [<OPTIONS>] <KEY> <ACTION>',)
    examples = ('bind --context tabs alt-[ tab --focus left',
                'bind --context tabs alt-] tab --focus right',
                'bind --context torrent alt-! start --force',
                'bind ctrl-a tab ls active',
                "bind 'd .' delete",
                "bind 'd !' delete --delete-files",
                'bind u <up>',
                'bind d <down>')
    argspecs = (
        { 'names': ('--context','-c'),
          'description': 'Where KEY is grabbed (see CONTEXTS section)' },
        { 'names': ('KEY',),
          'description': 'One or more keys or key combinations (see KEYS section)' },
        { 'names': ('ACTION',), 'nargs': 'REMAINDER',
          'description': ("Any command or '<KEY>' (including the brackets) "
                          'to translate one key to another') },
    )

    def __create_CONTEXTS_section():
        lines = [
            ('Keys are mapped in contexts.  With no context given, the default '
             'context is used.  The default context only gets the key if no '
             'other context wants it.  The same key can be mapped to different '
             'actions in different contexts.'),
            '',
            'Available contexts are: ' + \
              ', '.join('%s' % context for context in _get_KEYMAP_CONTEXTS()),
            '',
            'EXAMPLE',
            '\tbind --context torrent ctrl-t start',
            '\tbind --context tabs ctrl-t tab',
            '\tbind ctrl-t <left>',
            '',
            ('\tWhen focusing a torrent, <ctrl-t> starts the focused torrent.  '
             'If focus is not on a torrent but still on a tab (e.g. when reading '
             'documentation) a new tab is opened.  Otherwise (e.g. focus is on the '
             'command prompt), <ctrl-t> does the same as <left>.'),
        ]
        return lines

    more_sections = {
        'CONTEXTS': __create_CONTEXTS_section,
        'KEYS': (
            'Single-character keys are specified as themselves (e.g. h, X, 5, !, þ, ¥, etc).',
            '',
            ('Special key names are enter, space, tab, backspace, insert, delete, home, end, '
             'up, down, left, right, pgup, pgdn and f1-12.'),
            '',
            ("The modifiers 'ctrl', 'alt' and 'shift' are separated with '-' from the key "
             "(e.g. alt-i, shift-delete, ctrl-a).  shift-x is identical to X."),
            '',
            ("Chained keys are sparated by single spaces (' ') or pluses ('+') and must be "
             "given as a single argument."),
        )
    }

    tui = ExpectedResource

    def run(self, context, KEY, ACTION):
        keymap = self.tui.keymap

        key = KEY
        if len(ACTION) == 1 and ACTION[0][0] == '<' and ACTION[0][-1] == '>':
            # ACTION is another key (e.g. 'j' -> 'down')
            action = keymap.mkkey(ACTION[0])
        else:
            action = ' '.join(shlex.quote(x) for x in ACTION)

        if context is not None and context not in _get_KEYMAP_CONTEXTS():
            log.error('Invalid context: {!r}'.format(context))
            return False
        try:
            keymap.bind(key, action, context=context)
        except ValueError as e:
            log.error(e)
            return False
        else:
            return True


class UnbindCmd(metaclass=InitCommand):
    name = 'unbind'
    provides = {'tui'}
    category = 'tui'
    description = 'Unbind keys so pressing them has no effect'
    usage = ('unbind [<OPTIONS>] <KEY> <KEY> <KEY> ...',)
    examples = ('unbind --context main ctrl-l',
                'unbind q')
    argspecs = (
        { 'names': ('--context','-c'),
          'description': 'Where KEY is grabbed (see "bind" command)' },
        { 'names': ('--all','-a'), 'action': 'store_true',
          'description': 'Remove all existing keybindings, including defaults' },
        { 'names': ('KEY',), 'nargs': 'REMAINDER',
          'description': 'Keys or key combinations (see "bind" command)' },
    )

    tui = ExpectedResource

    def run(self, context, all, KEY):
        keymap = self.tui.keymap

        if all:
            keymap.clear()

        if context is not None and context not in _get_KEYMAP_CONTEXTS():
            log.error('Invalid context: {!r}'.format(context))
            return False

        success = True
        for key in KEY:
            try:
                keymap.unbind(key, context=context)
            except ValueError as e:
                log.error(e)
                success = False
            else:
                success = success and True
        return success


class MarkCmd(metaclass=InitCommand):
    name = 'mark'
    provides = {'tui'}
    category = 'tui'
    description = 'Select torrents or files for an action'
    usage = ('mark [<OPTIONS>]',)
    argspecs = (
        { 'names': ('--focus-next','-n'), 'action': 'store_true',
          'description': 'Move focus forward after marking or toggling' },
        { 'names': ('--toggle','-t'), 'action': 'store_true',
          'description': 'Mark if unmarked, unmark if marked' },
        { 'names': ('--all','-a'), 'action': 'store_true',
          'description': 'Mark or toggle all items' },
    )
    more_sections = {
        'NOTES': (('The column "marked" must be in the "columns.*" settings. Otherwise '
                   'marked list items are indistinguishable from unmarked ones.'),
                  '',
                  ('The character that is displayed in the "marked" column is '
                   'specified by the settings "tui.marked.on" and "tui.marked.off".')),
    }

    tui = ExpectedResource

    def run(self, focus_next, toggle, all):
        widget = self.tui.tabs.focus
        if not hasattr(widget, 'mark'):
            log.error('Nothing to mark here.')
            return False
        else:
            widget.mark(toggle=toggle, all=all)
            if focus_next:
                widget.focus_position += 1
            return True


class UnmarkCmd(metaclass=InitCommand):
    name = 'unmark'
    provides = {'tui'}
    category = 'tui'
    description = 'Deselect torrents or files for an action'
    usage = ('unmark [<OPTIONS>]',)
    argspecs = (
        { 'names': ('--focus-next','-n'), 'action': 'store_true',
          'description': 'Move focus forward after unmarking or toggling' },
        { 'names': ('--toggle','-t'), 'action': 'store_true',
          'description': 'Mark if unmarked, unmark if marked' },
        { 'names': ('--all','-a'), 'action': 'store_true',
          'description': 'Unmark or toggle all items' },
    )
    more_sections = MarkCmd.more_sections

    tui = ExpectedResource

    def run(self, focus_next, toggle, all):
        widget = self.tui.tabs.focus
        if not hasattr(widget, 'unmark'):
            log.error('Nothing to unmark here.')
            return False
        else:
            widget.unmark(toggle=toggle, all=all)
            if focus_next:
                widget.focus_position += 1
            return True


class QuitCmd(metaclass=InitCommand):
    name = 'quit'
    provides = {'tui'}
    category = 'tui'
    description = 'Terminate the TUI'

    def run(self):
        import urwid
        raise urwid.ExitMainLoop()


class TabCmd(metaclass=InitCommand):
    name = 'tab'
    provides = {'tui'}
    category = 'tui'
    description = 'Open, close and focus tabs'
    usage = ('tab [<OPTIONS>] [<COMMAND>]',)
    examples = ('tab',
                'tab ls active',
                'tab -b ls active',
                'tab -f active',
                'tab -f 3 ls active',
                'tab -c')
    argspecs = (
        { 'names': ('--background', '-b'), 'default': False, 'action': 'store_true',
          'description': 'Opens tab in background, instead of focusing it' },
        { 'names': ('--close', '-c'), 'nargs': '?', 'const': None, 'default': False,
          'description': 'Close tab at index or with partial title CLOSE' },
        { 'names': ('--close-all', '-ca'), 'default': False, 'action': 'store_true',
          'description': 'Close all tabs' },
        { 'names': ('--focus', '-f'),
          'description': ('Focus tab; FOCUS can be an index (first tab is 1), '
                          'part of a tab title, "left" or "right"') },
        { 'names': ('--title', '-t'),
          'description': 'Manually set tab title instead of generating one' },
        { 'names': ('COMMAND',), 'nargs': 'REMAINDER',
          'description': ('Command to run in new tab') },
    )

    tui = ExpectedResource
    cmdmgr = ExpectedResource

    async def run(self, close, close_all, focus, background, title, COMMAND):
        # Get indexes before adding/removing tabs, which changes indexes on
        # subsequent operations
        if focus is not None:
            i_focus = self.get_tab_index(focus)
            log.debug('Focusing tab %r at index %r', focus, i_focus)
            if i_focus is None:
                return False
        if close is not False:
            i_close = self.get_tab_index(close)
            log.debug('Closing tab %r at index %r', close, i_close)
            if i_close is None:
                return False

        tabs = self.tui.tabs
        old_index = tabs.focus_position

        # Apply close/focus operations
        if focus is not None:
            tabs.focus_position = i_focus
        if close_all is not False:
            tabs.clear()
        elif close is not False:
            tabs.remove(i_close)

        # User may specify a custom title for new tab
        cmdargs = {'title': title} if title else {}

        # Find out which torrent is focused in current tab so we can provide it
        # to the command running in a new tab.
        focused_content = tabs.focus
        if focused_content is not None:
            for attr in ('focused_torrent_id', 'focused_id'):
                torrent_id = getattr(tabs.focus, attr)
                if torrent_id is not None:
                    cmdargs['torrent_id'] = torrent_id
                    break

        if close is False and close_all is False and focus is None:
            titlew = make_tab_title_widget(title or 'Empty tab',
                                           attr_unfocused='tabs.unfocused',
                                           attr_focused='tabs.focused')
            tabs.insert(titlew, position='right')
            log.debug('Inserted new tab at position %d: %r', tabs.focus_position, titlew.base_widget.text)

        if COMMAND:
            cmd = ' '.join(shlex.quote(arg) for arg in COMMAND)
            log.debug('Running command in tab %d with args %s: %r',
                      tabs.focus_position,
                      ', '.join('%s=%r' % (k,v) for k,v in cmdargs.items()),
                      cmd)

            cmd = await self.cmdmgr.run_async(cmd, **cmdargs)
            retval = cmd
        else:
            retval = True

        if background:
            tabs.focus_position = old_index

        return retval

    def get_tab_index(self, pos):
        tabs = self.tui.tabs

        if pos is None:
            return tabs.focus_position

        def find_index(pos):
            i = pos-1 if pos > 0 else pos
            try:
                return tabs.get_index(i)
            except IndexError as e:
                log.error('No tab at position: {}'.format(pos))

        def find_title(string):
            for i,title in enumerate(tabs.titles):
                if string in title.original_widget.text:
                    return i
            log.error('No tab found: {!r}'.format(string))

        tabcount = len(tabs)
        curpos = tabs.focus_position
        curpos = 1 if curpos is None else curpos

        try:
            return find_index(int(pos))
        except ValueError:
            if pos == 'left':
                if tabcount > 1:
                    return tabs.get_index(max(0, curpos-1))
            elif pos == 'right':
                if tabcount > 1:
                    return tabs.get_index(min(tabcount-1, curpos+1))
            else:
                return find_title(pos)


class TUICmd(metaclass=InitCommand):
    name = 'tui'
    provides = {'tui'}
    category = 'tui'
    description = 'Show or hide parts of the text user interface'
    usage = ('tui <ACTION> <ELEMENT> <ELEMENT> ...',)
    examples = ('tui toggle log',
                'tui hide topbar.help')
    argspecs = (
        { 'names': ('ACTION',), 'choices': ('show', 'hide', 'toggle'),
          'description': '"show", "hide" or "toggle"' },
        { 'names': ('ELEMENT',), 'nargs': '+',
          'description': ('Name of TUI elements; '
                          'see ELEMENT NAMES section for a list') },
    )

    # Lazily load the element names from tui (HelpManager supports sequences
    # of lines or a callable that returns them)
    def __create_element_names():
        from ...tui.main import widgets
        return ('Available TUI element names are: ' + \
                ', '.join(str(e) for e in sorted(widgets.names_recursive)),)
    more_sections = { 'ELEMENT NAMES': __create_element_names }

    tui = ExpectedResource

    def run(self, ACTION, ELEMENT):
        widgets = self.tui.widgets
        widget = None
        success = False
        for element in ELEMENT:
            # Resolve path
            path = element.split('.')
            target_name = path.pop(-1)
            current_path = []
            widget = widgets
            try:
                for widgetname in path:
                    current_path.append(widgetname)
                    widget = getattr(widget, widgetname)
            except AttributeError as e:
                log.error('Unknown TUI element: %r', '.'.join(current_path))

            if widget is not None:
                action = getattr(widget, ACTION)
                log.debug('%sing %s in %s', ACTION.capitalize(), target_name, widget)
                try:
                    action(target_name)
                    success = True
                except ValueError as e:
                    log.error(e)
        return success


class SortCmd(metaclass=InitCommand):
    name = 'sort'
    aliases = ()
    provides = {'tui'}
    category = 'tui'
    description = "Sort lists of torrents/peers/trackers/etc"
    usage = ('sort [<OPTIONS>] [<ORDER> <ORDER> <ORDER> ...]',)
    examples = ('sort tracker status !rate-down',
                'sort --add eta')
    argspecs = (
        {'names': ('ORDER',), 'nargs': '*',
         'description': 'How to sort list items (see SORT ORDERS section)'},

        {'names': ('--add', '-a'), 'action': 'store_true',
         'description': 'Append ORDERs to current list of sort orders instead of replacing it'},

        {'names': ('--reset', '-r'), 'action': 'store_true',
         'description': 'Go back to sort order that was used when list was created'},

        {'names': ('--none', '-n'), 'action': 'store_true',
         'description': 'Remove all sort orders from the list'},
    )

    def _list_sort_orders(title, sortercls):
        return (title,) + \
            tuple('\t{}\t - \t{}'.format(', '.join((sname,) + s.aliases), s.description)
                  for sname,s in sorted(sortercls.SORTSPECS.items()))

    from ...client.sorters.tsorter import TorrentSorter
    from ...client.sorters.psorter import TorrentPeerSorter
    from ...client.sorters.trksorter import TorrentTrackerSorter
    more_sections = {
        'SORT ORDERS': _list_sort_orders('TORRENT LISTS', TorrentSorter) + \
                       ('',) + \
                       _list_sort_orders('PEER LISTS', TorrentPeerSorter) + \
                       ('',) + \
                       _list_sort_orders('TRACKER LISTS', TorrentTrackerSorter)
    }

    tui = ExpectedResource

    async def run(self, add, reset, none, ORDER):
        current_tab = self.tui.tabs.focus

        if reset:
            current_tab.sort = 'RESET'

        if none:
            current_tab.sort = None

        if ORDER:
            # Find appropriate sorter class for focused list
            from ...tui.views.torrentlist import TorrentListWidget
            from ...tui.views.peerlist import PeerListWidget
            from ...tui.views.trackerlist import TrackerListWidget
            if isinstance(current_tab, TorrentListWidget):
                sortcls = self.TorrentSorter
            elif isinstance(current_tab, PeerListWidget):
                sortcls = self.TorrentPeerSorter
            elif isinstance(current_tab, TrackerListWidget):
                sortcls = self.TorrentTrackerSorter
            else:
                log.error('Current tab does not contain a torrent, peer or tracker list.')
                return False

            try:
                new_sort = sortcls(ORDER)
            except ValueError as e:
                log.error(e)
                return False

            if add and current_tab.sort is not None:
                current_tab.sort += new_sort
            else:
                current_tab.sort = new_sort
            return True

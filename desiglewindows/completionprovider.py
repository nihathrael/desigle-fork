#    DeSiGLE
#    Origninal Copyright (C) 2008 Derek Anderson
#    Changes Copyright (C) 2010 Greg McWhirter
#    Changes Copyright (C) 2010 Thomas Kinnen
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import gobject
import gtk
import gtksourceview2 as gtksourceview
import os

from latex_tags import AUTOCOMPLETE

class CompletionProvider(gobject.GObject, gtksourceview.CompletionProvider):
    def __init__(self, name):
        gobject.GObject.__init__(self)
        self.name = name

    def do_get_name(self):
        return self.name

    def do_get_proposals(self):
        ret = []
        for item in sorted(AUTOCOMPLETE):
            ret.append(gtksourceview.CompletionItem(item, item))
        return ret

    def do_get_activation(self):
        return gtksourceview.COMPLETION_ACTIVATION_INTERACTIVE

    def do_match(self, context):
        textiter = context.get_iter()
        found = textiter.backward_search("\\", gtk.TEXT_SEARCH_TEXT_ONLY)
        if found is not None:
            return " " not in textiter.get_text(found[1])
        return False

    def do_populate(self, context):
        textiter = context.get_iter()
        found = textiter.backward_search("\\", gtk.TEXT_SEARCH_TEXT_ONLY)
        proposals = []
        if found is not None:
            text = "\\" + textiter.get_text(found[1])
            if not " " in text and not os.linesep in text:
                for proposal in self.do_get_proposals():
                    if proposal.get_label().startswith(text):
                        proposals.append(proposal)
        context.add_proposals(self, proposals, True)

    def do_activate_proposal(self, proposal, iterator):
        text = proposal.get_text()
        start = iterator.backward_search("\\", gtk.TEXT_SEARCH_TEXT_ONLY)[0]
        buffer = iterator.get_buffer()
        # Handle replacing
        buffer.begin_user_action()
        buffer.delete(start, iterator)
        buffer.insert(start, text, -1)

        # get new iter, the old one has been modified
        new_iter = buffer.get_iter_at_mark(buffer.get_insert())
        # calculate cursor moving for smart cursor placement
        if os.linesep in text:
            # used in snippets like:
            # \begin{table}\n\end{table}
            linesep_pos = text.index(os.linesep)
            new_iter.backward_cursor_positions(len(text)-linesep_pos)
        elif text.endswith("{}"):
            #stuff like \subsection{}
            new_iter.backward_cursor_position()

        buffer.place_cursor(new_iter)
        buffer.end_user_action()
        return True



gobject.type_register(CompletionProvider)
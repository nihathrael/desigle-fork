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
        for item in AUTOCOMPLETE:
            ret.append(gtksourceview.CompletionItem(item, item[1:]))
            # TODO Find out how to make the insertation go over the first
            # character, we remove the first character now for the time being
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

gobject.type_register(CompletionProvider)
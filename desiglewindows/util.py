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

import gtksourceview2 as gtksourceview

def pango_escape(s):
    return s.replace('&','&amp;').replace('>','&gt;').replace('<','&lt;')

def get_language_for_mime_type(mime):
    lang_manager = gtksourceview.language_manager_get_default()
    lang_ids = lang_manager.get_language_ids()
    for i in lang_ids:
        lang = lang_manager.get_language(i)
        for m in lang.get_mime_types():
            if m == mime:
                return lang
    return None

######################################################################
##### remove all source marks
def remove_all_marks(buffer):
    begin, end = buffer.get_bounds()
    marks = buffer.remove_source_marks(begin, end)
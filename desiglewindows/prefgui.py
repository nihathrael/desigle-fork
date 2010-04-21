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

import gtk
import config

from latex_tags import *

class PrefGUI:

    config = config.GConfConfig('/apps/desigle')

    def __init__(self):
        self.ui = gtk.glade.XML(RUN_FROM_DIR + 'desigle.glade')
        self.main_window = self.ui.get_widget('desigle_prefs')
        self.main_window.show_all()
        self.main_window.connect("delete-event", lambda x,y: self.main_window.destroy() )
        self.ui.get_widget('button_close').connect('clicked', lambda x: self.main_window.destroy() )

        # blank document
        textview_default_blank_document = self.ui.get_widget('textview_default_blank_document')
        textview_default_blank_document.get_buffer().set_text( self.config.get_string( 'default_blank_document', default=BLANK_DOCUMENT ) )
        textview_default_blank_document.get_buffer().connect('changed', self.save_default_blank_document  )
        self.ui.get_widget('toolbutton_revert_to_default').connect( 'clicked', lambda x: self.ui.get_widget('textview_default_blank_document').get_buffer().set_text( BLANK_DOCUMENT ) )

        # pdf preview
        pref_auto_add_doc_tags_in_preview = self.ui.get_widget('pref_auto_add_doc_tags_in_preview')
        pref_auto_add_doc_tags_in_preview.set_active( self.config.get_bool( 'pref_auto_add_doc_tags_in_preview') )
        pref_auto_add_doc_tags_in_preview.connect('toggled', lambda x: self.config.set_bool( 'pref_auto_add_doc_tags_in_preview', pref_auto_add_doc_tags_in_preview.get_active()) )
        pref_keep_preview_on_parent = self.ui.get_widget('pref_keep_preview_on_parent')
        pref_keep_preview_on_parent.set_active( self.config.get_bool( 'pref_keep_preview_on_parent') )
        pref_keep_preview_on_parent.connect('toggled', lambda x: self.config.set_bool( 'pref_keep_preview_on_parent', pref_keep_preview_on_parent.get_active()) )
        pref_default_doc_class = self.ui.get_widget('pref_default_doc_class')
        pref_default_doc_class.set_text( self.config.get_string( 'default_doc_class', default='article' ) )
        pref_default_doc_class.connect('changed', lambda x: self.config.set_string( 'default_doc_class', pref_default_doc_class.get_text()) )
        self.ui.get_widget('reset_pref_default_doc_class').connect( 'clicked', lambda x: self.ui.get_widget('pref_default_doc_class').set_text( 'article' ) )

    def save_default_blank_document(self, buffer):
        default_blank_document = buffer.get_text( buffer.get_start_iter(), buffer.get_end_iter() )
        self.config.set_string( 'default_blank_document', default_blank_document )

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

import gtkspell
import gtk
import os

import config

from datetime import datetime
from latex_tags import *

class TexDocument:
    main_gui = None
    fq_filename = None
    changed_time = None
    changed = False
    undo_stack = []
    redo_stack = []
    record_operations = True
    editor = None
    error_line_offset = 0
    undo_or_redo_in_progress = False

    def __init__(self, main_gui, filename=None):
        self.main_gui = main_gui
        self.ui = main_gui.ui
        self.config = main_gui.config
        self.notebook = self.ui.get_widget('notebook_editor')
        if filename:
            self.fq_filename = filename

        self.init_editor()
        self.init_tags()
        self.init_label()

        self.notebook.set_current_page(self.notebook.get_n_pages()-1)

        text_buffer = self.editor.get_buffer()
        if self.fq_filename:
            f = open( self.fq_filename )
            self.record_operations = False
            text_buffer.set_text( f.read() )
            self.record_operations = True
            f.close()
            self.ui.get_widget('menu_save').set_sensitive(False)
            self.ui.get_widget('toolbutton_save').set_sensitive(False)
        else:
            text_buffer = self.editor.get_buffer()
            text_buffer.set_text( self.config.get_string( 'default_blank_document', default=BLANK_DOCUMENT ) )
            self.ui.get_widget('menu_save').set_sensitive(True)
            self.ui.get_widget('toolbutton_save').set_sensitive(True)

        self.changed = False
        self.retag( text_buffer )
        text_buffer.place_cursor( text_buffer.get_start_iter() )


    def init_label(self):
        hbox = gtk.HBox()
        if self.fq_filename:
            self.notebook_label = gtk.Label( pango_escape(os.path.basename(self.fq_filename)) )
        else:
            self.notebook_label = gtk.Label('untitled')
        hbox.add( self.notebook_label )
        close_button = gtk.Button()
        close_button.connect('clicked', self.close)
        close_button.set_focus_on_click(False)
        close_button_image = gtk.Image()
        close_button_image.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
        close_button.set_image(close_button_image)
        close_button.set_relief(gtk.RELIEF_NONE)
        style = close_button.get_style().copy()
        settings = gtk.Widget.get_settings (close_button);
        (w,h) = gtk.icon_size_lookup_for_settings(settings,gtk.ICON_SIZE_MENU);
        gtk.Widget.set_size_request (close_button, w + 4, h + 4);
        hbox.add( close_button )
        hbox.show_all()
        self.notebook.set_tab_label( self.scrolled_window, hbox )


    def close(self, x=None):
        if self.changed:

            dialog = gtk.MessageDialog( type=gtk.MESSAGE_WARNING )
            if self.fq_filename:
                dialog.set_markup('<b>Save changes to document "%s" before closing?</b>\n\nIf you don\'t save, changes will be lost.' % ( pango_escape(os.path.basename(self.fq_filename)) ))
                dialog.add_button('_Save', 1)
            else:
                dialog.set_markup('<b>Save untitled document before closing?</b>\n\nIf you don\'t save, changes will be lost.')
                dialog.add_button('_Save as', 1)
            dialog.add_button('Close _without saving', 2)
            dialog.add_button('_Cancel', 3)
            dialog.show_all()
            response = dialog.run()
            dialog.destroy()
            if response==1:
                if self.fq_filename:
                    self.save()
                else:
                    if not self.save_as():
                        return True
            elif response==2:
                pass
            elif response==3:
                return True

        page_num = self.main_gui.tex_docs.index(self)
        self.notebook.remove_page(page_num)
        self.main_gui.tex_docs.remove(self)
        if not len(self.main_gui.tex_docs):
            self.main_gui.new()


    def init_editor(self):
        self.scrolled_window = gtk.ScrolledWindow()
        self.editor = gtk.TextView()
        self.editor.set_wrap_mode(gtk.WRAP_WORD)
        self.scrolled_window.add(self.editor)
        self.notebook.append_page(self.scrolled_window)
        self.scrolled_window.show_all()

        pangoFont = pango.FontDescription('monospace')
        self.editor.modify_font(pangoFont)
        spell = gtkspell.Spell(self.editor)
        spell.set_language("en_US")
        self.editor.get_buffer().connect('changed', self.editor_text_change_event )
        self.editor.get_buffer().connect('mark-set', self.editor_mark_set_event )
        self.editor.get_buffer().connect('insert-text', self.editor_insert_text_event )
        self.editor.get_buffer().connect('delete-range', self.editor_delete_range_event )

    def init_tags(self):
        tag_table = self.editor.get_buffer().get_tag_table()
        for tag_name, tag_attr in LATEX_TAGS:
            warn_tag = gtk.TextTag(tag_name)
            for k,v in tag_attr['properties'].iteritems():
                warn_tag.set_property(k,v)
            tag_table.add(warn_tag)

    def editor_text_change_event(self, buffer):
        self.changed_time = datetime.now()
        self.ui.get_widget('menu_undo').set_sensitive( len(self.undo_stack)>0 )
        if not self.undo_or_redo_in_progress:
            for action in self.redo_stack:
                action[1].delete_mark(action[2])
            self.redo_stack = []
        self.undo_or_redo_in_progress = False
        self.ui.get_widget('menu_redo').set_sensitive( len(self.redo_stack) > 0)
        self.changed = True
        self.ui.get_widget('menu_save').set_sensitive(True)
        self.ui.get_widget('toolbutton_save').set_sensitive(True)

    def editor_insert_text_event(self, buffer, start, text, length):
        if not self.record_operations: return
        start_mark = buffer.create_mark(None, start, True)
        self.undo_stack.append( ('insert_text', buffer, start_mark, text, length) )
        self.prune_undo_stack()


    def editor_delete_range_event(self, buffer, start, end):
        if not self.record_operations: return
        start_mark = buffer.create_mark(None, start, False)
        text = buffer.get_text( start, end )
        self.undo_stack.append( ('delete_range', buffer, start_mark, text) )
        self.prune_undo_stack()

    def editor_mark_set_event(self, buffer, x, y):
        iter=buffer.get_iter_at_mark(buffer.get_insert())
        self.ui.get_widget('label_row_col').set_text( 'line:%i/%i col:%i/%i' % ( iter.get_line()+1, buffer.get_line_count(), iter.get_line_offset(), iter.get_chars_in_line() ) )

    def find_forward(self, search_text=None):
        if search_text==None:
            search_text = self.ui.get_widget('entry_find').get_text()
        search_text = search_text.lower()
        buffer = self.editor.get_buffer()
        editor_text = buffer.get_text( buffer.get_start_iter(), buffer.get_end_iter() )
        editor_text = editor_text.lower()
        editor_offset = buffer.get_iter_at_mark( buffer.get_insert() ).get_offset()
        found_offset = editor_text.find(search_text, editor_offset+1)
        if found_offset<0:
            found_offset = editor_text.find(search_text)
        if found_offset>=0:
            found_iter = buffer.get_iter_at_offset(found_offset)
            buffer.place_cursor( found_iter )
            self.editor.scroll_to_iter( found_iter, 0.0 )
            buffer.remove_tag_by_name('search_highlight', buffer.get_start_iter(), buffer.get_end_iter())
            buffer.apply_tag_by_name( 'search_highlight', found_iter, buffer.get_iter_at_offset(found_offset+len(search_text)) )


    def find_backward(self, search_text=None):
        if search_text==None:
            search_text = self.ui.get_widget('entry_find').get_text()
        search_text = search_text.lower()
        buffer = self.editor.get_buffer()
        editor_text = buffer.get_text( buffer.get_start_iter(), buffer.get_end_iter() )
        editor_text = editor_text.lower()
        editor_offset = buffer.get_iter_at_mark( buffer.get_insert() ).get_offset()
        found_offset = editor_text.rfind(search_text, 0, editor_offset)
        if found_offset<0:
            found_offset = editor_text.rfind(search_text)
        if found_offset>=0:
            found_iter = buffer.get_iter_at_offset(found_offset)
            buffer.place_cursor( found_iter )
            self.editor.scroll_to_iter( found_iter, 0.0 )
            buffer.remove_tag_by_name('search_highlight', buffer.get_start_iter(), buffer.get_end_iter())
            buffer.apply_tag_by_name( 'search_highlight', found_iter, buffer.get_iter_at_offset(found_offset+len(search_text)) )


    def prune_undo_stack(self):
        while len(self.undo_stack)>512:
            action = self.undo_stack.pop(0)
            action[1].delete_mark(action[2])


    def retag( self, buffer=None, start=None, end=None ):
        if not buffer: buffer = self.editor.get_buffer()
        if not start: start = buffer.get_start_iter()
        if not end: end = buffer.get_end_iter()

        # tag syntax highlighting
        for tag_name, tag_attr in LATEX_TAGS:
            #buffer.remove_tag_by_name(tag_name, start, end)
            buffer.remove_tag_by_name(tag_name, buffer.get_start_iter(), buffer.get_end_iter())
            p = tag_attr['regex']
            #line = start.get_text(end)
            line = buffer.get_text( buffer.get_start_iter(), buffer.get_end_iter() )
            for match in p.finditer(line):
                st = buffer.get_iter_at_offset( start.get_offset()+ match.span()[0] )
                et = buffer.get_iter_at_offset( start.get_offset()+ match.span()[1] )
                buffer.apply_tag_by_name( tag_name, st, et )
        # tag errors
        for file, line_number, error in self.main_gui.errors:
            tmp = line_number-1
            st = buffer.get_iter_at_line(tmp)
            while st.get_chars_in_line()<=1:
                tmp +=1
                st = buffer.get_iter_at_line(tmp)
            et = buffer.get_iter_at_line(tmp+1)
            buffer.apply_tag_by_name( 'latex_error', st, et )
            #print line_number, st.get_offset(), et.get_offset(), error

    def get_actual_screen_coords_of_text_cursor(self):
        text_buffer = self.editor.get_buffer()
        here = text_buffer.get_iter_at_mark( text_buffer.get_insert() )
        here_location = self.editor.get_iter_location(here)
        x,y = here_location.x, here_location.y
        visible_rect = self.editor.get_visible_rect()
        x,y = x-visible_rect.x,y-visible_rect.y
        x,y = self.editor.translate_coordinates(self.main_gui.main_window, x,y)
        main_window_position = self.main_gui.main_window.get_position()
        x,y = main_window_position[0]+x, main_window_position[1]+y+12
        return x,y

    def save_as(self):
        os.chdir(config.CURRENT_DIR)
        dialog = gtk.FileChooserDialog(title='Save TEX file...', parent=None, action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK), backend=None)
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            CURRENT_DIR = dialog.get_current_folder()
            self.fq_filename = dialog.get_filename()
            self.notebook_label.set_text( pango_escape(os.path.basename(self.fq_filename)) )
            self.save()
            dialog.destroy()
            return True
        else:
            dialog.destroy()
        return False

    def save(self):
        if not self.fq_filename:
            return self.save_as()
        text_buffer = self.editor.get_buffer()
        tex = text_buffer.get_text( text_buffer.get_start_iter(), text_buffer.get_end_iter() )
        ftex = open( self.fq_filename, 'w' )
        ftex.write( tex )
        ftex.close()
        self.changed = False
        self.ui.get_widget('menu_save').set_sensitive(False)
        self.ui.get_widget('toolbutton_save').set_sensitive(False)
        self.save_pdf()

    def save_pdf(self):
        o_filename = self.fq_filename
        if o_filename.endswith('.tex'):
            o_filename = o_filename[:-4]
        o_filename = o_filename +'.pdf'

        if os.path.isfile(self.main_gui.pdf_file):
            #child_stdin, child_stdout = os.popen2( 'cp "%s" "%s"' % (self.main_gui.pdf_file, o_filename) )
            cmd_string = 'cp "%s" "%s"' % (self.main_gui.pdf_file, o_filename)
            p = subprocess.Popen(cmd_string, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
            (child_stdin, child_stdout) = (p.stdin, p.stdout)
            child_stdin.close()
            output = child_stdout.read()
            child_stdout.close()

    def start_undo_or_redo(self, typ, stack_item):
        if typ == 'undo':
            self.redo_stack.append(stack_item)
        elif typ == 'redo':
            self.undo_stack.append(stack_item)
        self.undo_or_redo_in_progress = True

    def set_record_operations(self, record_operations):
        self.record_operations = record_operations

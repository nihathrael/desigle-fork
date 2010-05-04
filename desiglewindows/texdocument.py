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
import subprocess
import gtksourceview2 as gtksourceview
import gio

import config

from datetime import datetime
from latex_tags import *
from util import pango_escape, get_language_for_mime_type, remove_all_marks
from completionprovider import CompletionProvider

class TexDocument:
    main_gui = None
    fq_filename = None
    changed_time = None
    changed = False
    editor = None
    error_line_offset = 0

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

        if self.fq_filename:
            self.open_file(self.fq_filename)
            self.ui.get_widget('menu_save').set_sensitive(False)
            self.ui.get_widget('toolbutton_save').set_sensitive(False)
        else:
            self.open_file("%s/../default.tex" % os.path.dirname(__file__))
            self.ui.get_widget('menu_save').set_sensitive(True)
            self.ui.get_widget('toolbutton_save').set_sensitive(True)
        self.changed = False

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

    def remove_current_line(self):
        buffer = self.text_buffer
        iter = buffer.get_iter_at_mark(buffer.get_insert())
        line = iter.get_line()
        iter_start = buffer.get_iter_at_line(line)
        iter_end = buffer.get_iter_at_line(line+1)
        buffer.delete(iter_start, iter_end)

    def retag( self, buffer=None, start=None, end=None ):
        if not buffer: buffer = self.editor.get_buffer()
        if not start: start = buffer.get_start_iter()
        if not end: end = buffer.get_end_iter()

        buffer.remove_tag_by_name("latex_error", start, end)

        # tag errors
        for file, line_number, error in self.main_gui.errors:
            tmp = line_number-1
            st = buffer.get_iter_at_line(tmp)
            while st.get_chars_in_line()<=1:
                tmp +=1
                st = buffer.get_iter_at_line(tmp)
            et = buffer.get_iter_at_line(tmp+1)
            buffer.apply_tag_by_name( 'latex_error', st, et )

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

    def init_editor(self):
        self.text_buffer = gtksourceview.Buffer()
        self.scrolled_window = gtk.ScrolledWindow()
        self.editor = gtksourceview.View(self.text_buffer)
        self.editor.set_wrap_mode(gtk.WRAP_WORD)
        self.editor.set_indent_width(4)
        completion = self.editor.get_completion()
        completion.add_provider(CompletionProvider("LaTeX Provider"))
        self.scrolled_window.add(self.editor)
        self.notebook.append_page(self.scrolled_window)
        self.scrolled_window.show_all()

        pangoFont = pango.FontDescription('monospace')
        self.editor.modify_font(pangoFont)
        spell = gtkspell.Spell(self.editor)
        spell.set_language("en_US")
        self.text_buffer.connect('changed', self.update_cursor_position, self.editor)
        self.text_buffer.connect('mark-set', self.editor_mark_set_event)

    def init_tags(self):
        tag_table = self.editor.get_buffer().get_tag_table()
        for tag_name, tag_attr in LATEX_TAGS:
            warn_tag = gtk.TextTag(tag_name)
            for k,v in tag_attr['properties'].iteritems():
                warn_tag.set_property(k,v)
            tag_table.add(warn_tag)

    def editor_text_change_event(self, buffer):
        self.changed_time = datetime.now()
        self.undo_or_redo_in_progress = False
        self.ui.get_widget('menu_redo').set_sensitive( self.text_buffer.can_redo())
        self.changed = True
        self.ui.get_widget('menu_save').set_sensitive(True)
        self.ui.get_widget('toolbutton_save').set_sensitive(True)
        self.ui.get_widget('menu_undo').set_sensitive( self.text_buffer.can_undo() )

    def editor_mark_set_event(self, buffer, x, y):
        iter=buffer.get_iter_at_mark(buffer.get_insert())
        self.ui.get_widget('label_row_col').set_text( 'line:%i/%i col:%i/%i' % ( iter.get_line()+1, buffer.get_line_count(), iter.get_line_offset(), iter.get_chars_in_line() ) )

    def find_forward(self, search_text=None):
        if search_text==None:
            search_text = self.ui.get_widget('entry_find').get_text()
        search_text = search_text.lower()
        editor_text = self.text_buffer.get_text( self.text_buffer.get_start_iter(), self.text_buffer.get_end_iter() )
        editor_text = editor_text.lower()
        editor_offset = self.text_buffer.get_iter_at_mark( self.text_buffer.get_insert() ).get_offset()
        found_offset = editor_text.find(search_text, editor_offset+1)
        if found_offset<0:
            found_offset = editor_text.find(search_text)
        if found_offset>=0:
            found_iter = self.text_buffer.get_iter_at_offset(found_offset)
            self.text_buffer.place_cursor( found_iter )
            self.editor.scroll_to_iter( found_iter, 0.0 )
            self.text_buffer.remove_tag_by_name('search_highlight', self.text_buffer.get_start_iter(), self.text_buffer.get_end_iter())
            self.text_buffer.apply_tag_by_name( 'search_highlight', found_iter, self.text_buffer.get_iter_at_offset(found_offset+len(search_text)) )


    def find_backward(self, search_text=None):
        if search_text==None:
            search_text = self.ui.get_widget('entry_find').get_text()
        search_text = search_text.lower()
        editor_text =self.text_buffer.get_text(self.text_buffer.get_start_iter(), self.text_buffer.get_end_iter() )
        editor_text = editor_text.lower()
        editor_offset = self.text_buffer.get_iter_at_mark( self.text_buffer.get_insert() ).get_offset()
        found_offset = editor_text.rfind(search_text, 0, editor_offset)
        if found_offset<0:
            found_offset = editor_text.rfind(search_text)
        if found_offset>=0:
            found_iter = self.text_buffer.get_iter_at_offset(found_offset)
            self.text_buffer.place_cursor( found_iter )
            self.editor.scroll_to_iter( found_iter, 0.0 )
            self.text_buffer.remove_tag_by_name('search_highlight', self.text_buffer.get_start_iter(), self.text_buffer.get_end_iter())
            self.text_buffer.apply_tag_by_name( 'search_highlight', found_iter, self.text_buffer.get_iter_at_offset(found_offset+len(search_text)) )

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


    def open_file(self, filename):
        #get the new language for the file mimetype

        if os.path.isabs(filename):
            path = filename
        else:
            path = os.path.abspath(filename)
        f = gio.File(path)

        path = f.get_path()

        info = f.query_info("*")

        mime_type = info.get_content_type()
        language = None

        if mime_type:
            language = get_language_for_mime_type(mime_type)
            if not language:
                print 'No language found for mime type "%s"' % mime_type
        else:
            print 'Couldn\'t get mime type for file "%s"' % filename

        self.text_buffer.set_language(language)
        self.text_buffer.set_highlight_syntax(True)
        remove_all_marks(self.text_buffer)
        self.load_file(path) # TODO: check return
        return True

    def load_file(self, path):
        self.text_buffer.begin_not_undoable_action()
        try:
            txt = open(path).read()
        except:
            return False
        self.text_buffer.set_text(txt)
        self.text_buffer.set_data('filename', path)
        self.text_buffer.end_not_undoable_action()

        self.text_buffer.set_modified(False)
        self.text_buffer.place_cursor(self.text_buffer.get_start_iter())
        return True


    def update_cursor_position(self, buffer, view):
        tabwidth = view.get_tab_width()
        pos_label = self.ui.get_widget('label_row_col')
        iter = buffer.get_iter_at_mark(buffer.get_insert())
        nchars = iter.get_offset()
        row = iter.get_line() + 1
        start = iter
        start.set_line_offset(0)
        col = 0
        while not start.equal(iter):
            if start.get_char == '\t':
                col += (tabwidth - (col % tabwidth))
            else:
                col += 1
                start = start.forward_char()
        pos_label.set_text('char: %d, line: %d, column: %d' % (nchars, row, col))
        self.mark_editor_changed()

    def mark_editor_changed(self):
        self.ui.get_widget('menu_save').set_sensitive(True)
        self.ui.get_widget('toolbutton_save').set_sensitive(True)
        self.ui.get_widget('menu_redo').set_sensitive( self.text_buffer.can_redo())
        self.ui.get_widget('menu_undo').set_sensitive( self.text_buffer.can_undo())
        self.changed_time = datetime.now()
        self.changed = True

#!/usr/bin/env python

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

import sys, os, traceback
import glib

from desiglewindows import MainGUI


# GUI imports
try:
    import pygtk
    pygtk.require("2.0")
    import gobject
    import gtkspell
    import gtk
    import gtk.glade
    import gnome
    import gnome.ui
    import pango
    import gconf
    gobject.threads_init()
    gtk.gdk.threads_init()
except:
    traceback.print_exc()
    print 'could not import required GTK libraries.  try running:'
    print '\tfor ubuntu: sudo apt-get install python python-glade2 python-gnome2 python-gconf python-gnome2-extras'
    print '\tfor debian: sudo apt-get install python python-glade2 python-gnome2 python-gnome2-extras'
    print '\tfor redhat: yum install pygtk2 gnome-python2-gconf pygtk2-libglade python-gnome2-extras'
    sys.exit()

try:
    import poppler
except:
    traceback.print_exc()
    print 'could not import python-poppler [https://code.launchpad.net/~poppler-python/poppler-python/].  try running (from "%s"):' % RUN_FROM_DIR
    print "\tsudo apt-get install build-essential libpoppler2 libpoppler-dev libpoppler-glib2 libpoppler-glib-dev python-cairo-dev bzr gnome-common python-dev python-gnome2-dev python-gtk2-dev python-gobject-dev python-pyorbit-dev"
    print '\tbzr branch http://bazaar.launchpad.net/~poppler-python/poppler-python/poppler-0.6-experimental'
    print '\tcd poppler-0.6-experimental'
    print '\t./autogen.sh'
    print '\t./configure'
    print '\tmake'
    print '\tsudo make install'
    sys.exit()

if __name__ == "__main__":

    global main_gui
    main_gui = MainGUI()

    if len(sys.argv)>1 and sys.argv[1] and os.path.isfile( sys.argv[1] ):
        main_gui.open_file(sys.argv[1])
    else:
        main_gui.new()

    gtk.main()




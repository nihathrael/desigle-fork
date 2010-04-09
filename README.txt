=============================================
 DeSiGLE - Derek's Simple Gnome LaTeX Editor
=============================================

Dependencies
------------

You will need all the typical gnome/python bindings.  If you're using a recent
version of Ubuntu, this line will install them all:

    sudo apt-get install python python-glade2 python-gnome2 python-gconf python-gnome2-extras
    
And (obviously) the LaTeX utilities:

    sudo apt-get install texlive-latex-base texlive-base-bin texlive-latex-extra

You will also need pypoppler (for the PDF integration), which can be installed
with the following set of commands (again assuming Ubuntu):

    sudo apt-get install build-essential libpoppler2 libpoppler-dev libpoppler-glib2 libpoppler-glib-dev python-cairo-dev bzr gnome-common python-dev python-gnome2-dev python-gtk2-dev python-gobject-dev python-pyorbit-dev
    bzr branch http://bazaar.launchpad.net/~poppler-python/poppler-python/poppler-0.6-experimental
    cd poppler-0.6-experimental
    ./autogen.sh
    ./configure
    make
    sudo make install


Usage
-----

Like most editors, run it like this:

    python desigle.py [filename]
    

Feedback
--------
Please report bugs to the website, and join the listserv:

    http://code.google.com/p/desigle/
    http://groups.google.com/group/desigle-discuss
    

Thanks!
Derek Anderson


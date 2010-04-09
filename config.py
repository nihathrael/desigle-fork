import pickle

try:
    import gconf
except:
    traceback.print_exc()
    print 'could not import required GTK libraries.  try running:'
    print '\tfor ubuntu: sudo apt-get install python-gconf'
    sys.exit()


class GConfConfig:
    
    BASE_KEY = None
    
    def get_string(self, key, default=None):
        x = self.client.get_string(self.BASE_KEY +'/'+ key)
        if x:
            return x
        else:
            return default

    def set_string(self, key, value):
        self.client.set_string(self.BASE_KEY +'/'+ key,value)
        
    def get_list(self, key, default=[]):
        x = self.client.get_string(self.BASE_KEY +'/'+ key)
        if x:
            return pickle.loads(x)
        else:
            return default
    
    def set_list(self, key, values):
        self.client.set_string( self.BASE_KEY +'/'+ key, pickle.dumps(values) ) 
    
    def get_bool(self, key):
        return self.client.get_bool(self.BASE_KEY +'/'+ key)
    
    def set_bool(self, key, value):
        self.client.set_bool(self.BASE_KEY +'/'+ key,value)

    def get_int(self, key, default=0):
        x = self.client.get_int(self.BASE_KEY +'/'+ key)
        if x!=None:
            return x
        else:
            return default
    
    def set_int(self, key, value):
        self.client.set_int(self.BASE_KEY +'/'+ key, value)

    def __init__(self, base_key):
        self.BASE_KEY = base_key
        self.client = gconf.client_get_default()
        self.client.add_dir (self.BASE_KEY, gconf.CLIENT_PRELOAD_NONE)

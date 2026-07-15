import uno
import time
import sys
from unohelper import Base

try:
    local_ctx = uno.getComponentContext()
    resolver = local_ctx.ServiceManager.createInstanceWithContext(
        'com.sun.star.bridge.UnoUrlResolver', local_ctx)
    ctx = resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
except Exception as e:
    print('ERROR connecting to UNO:', e)
    sys.exit(1)

smgr = ctx.ServiceManager
print('connected to UNO')

services = [
    'com.sun.star.frame.Desktop',
    'com.sun.star.script.provider.MasterScriptProviderFactory',
    'com.sun.star.script.provider.ScriptProviderFactory',
    'com.sun.star.task.JobExecutor',
]
for name in services:
    try:
        obj = smgr.createInstanceWithContext(name, ctx)
        print(name, 'OK', type(obj), obj)
    except Exception as e:
        print(name, 'ERR', e)

try:
    desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
    print('desktop OK', desktop)
    try:
        current = desktop.getCurrentComponent()
        print('current component', current)
        if current is not None:
            print('has getSupportedServiceNames', hasattr(current, 'getSupportedServiceNames'))
            if hasattr(current, 'getSupportedServiceNames'):
                print('supported services:')
                for s in current.getSupportedServiceNames():
                    print('  ', s)
            print('has getScriptProvider', hasattr(current, 'getScriptProvider'))
            if hasattr(current, 'getScriptProvider'):
                sp = current.getScriptProvider()
                print('script provider', sp)
    except Exception as e:
        print('desktop getCurrentComponent failed:', e)
except Exception as e:
    print('desktop ERR', e)

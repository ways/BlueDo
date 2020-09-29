#!/usr/bin/env python3

import sys
try:
    from . import bluedoapp
except ImportError:
    import bluedoapp

def main(args=None):
    app = bluedoapp.BlueDo()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main(args=sys.argv))

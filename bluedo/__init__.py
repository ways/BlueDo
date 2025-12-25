import sys

__version__ = "2.5.0"
__name__ = 'bluedo'

try:
    from . import bluedoapp
except ImportError:
    import bluedoapp

def main(args=None):
    app = bluedoapp.BlueDo()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main(args=sys.argv))

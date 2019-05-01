import argparse


class SmartFormatter(argparse.HelpFormatter):

    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


def get_cli_parameters(args):
    parser = argparse.ArgumentParser()

    parser.add_argument("--config", help="config file",
                        dest="config_filename",
                        action="store", default=None)

    parser.add_argument("--debug", help="If debug enabled - exit when error occurs. ",
                        dest="debug",
                        default=False,
                        action="store_true")

    parser.add_argument("--noauth", help="If debug enabled - exit when error occurs. ",
                        dest="noauth",
                        default=False,
                        action="store_true")

    parser.add_argument("--exchange", help="Seth the exchange_id. Ignore config file. ",
                        dest='exchange_id',
                        action="store", default=None)

    parser.add_argument("--balance", help="Staring test balance. if no value set - 1 by default",
                        dest="test_balance",
                        type=float,
                        action="store", const=1, nargs="?")

    subparsers = parser.add_subparsers(help="Offline mode")
    subparsers.required = False
    offline = subparsers.add_parser("offline", help="Set the working  mode. offline -h for help")
    # online = subparsers.add_parser("online", help="Set the online mode")
    offline.set_defaults(offline=True)

    offline.add_argument("--tickers", "-t",
                         help="path to csv tickers file",
                         dest="offline_tickers_file",
                         default=None,
                         action="store")

    offline.add_argument("--order_books","-ob",
                         help="path to csv order books file",
                         dest="offline_order_books_file",
                         default=None,
                         action="store")

    offline.add_argument("--markets", "-m",
                         help="path to markets json file",
                         dest="offline_markets_file",
                         default=None,
                         action="store")

    return parser.parse_args(args)

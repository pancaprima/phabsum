import requests, datetime, time, sys, phabsum
from .phab import Phab
from optparse import OptionParser

version = phabsum.__version__

def parse_options():
    """
    Handle command-line options with optparse.OptionParser.

    Return list of arguments, largely for use in `parse_arguments`.
    """

    # Initialize
    parser = OptionParser(usage="phabsum [options]")

    parser.add_option(
        '--purl',
        dest='phabricator_url',
        default=None,
        help="Set URL of your phabricator. i.e.: https://secure.phabricator.com/"
    )

    parser.add_option(
        '--ptoken',
        dest='phabricator_api_token',
        default=None,
        help="Set Conduit API token to your phabricator."
    )

    parser.add_option(
        '--ptag',
        dest='phabricator_tag',
        default=None,
        help="Set name of the project tag that you want to summary for today. i.e.: dexter_squad"
    )

    parser.add_option(
        '--gurl',
        dest='google_sheet_url',
        default=None,
        help="Set URL of google sheet to store the summary"
    )

    parser.add_option(
        '--gcred',
        dest='google_sheet_api_credential',
        default=None,
        help="Set path to json credential file of Google Sheet API"
    )

    parser.add_option(
        '--shook',
        dest='slack_webhook',
        default=None,
        help="Set incoming webhook URL of slack"
    )

    # Finalize
    # Return three-tuple of parser + the output from parse_args (opt obj, args)
    opts, args = parser.parse_args()
    return parser, opts, args

def main():
    print("Phabsum made by Prima (pancaprima8@gmail.com), version %s" % (version))
    parser, options, arguments = parse_options()
    args_verif = True
    if options.phabricator_url is None :
        args_verif = False
        print("Please specify URL of your phabricator by passing --purl. i.e.: --purl https://secure.phabricator.com/")
    
    if options.phabricator_tag is None :
        args_verif = False
        print("Please specify the workboard/project name that you want to summarize by passing --ptag. i.e.: --ptag dexter_squad")
        
    if options.phabricator_api_token is None :
        args_verif = False
        print('Please specify Conduit API Token of your phabricator by passing --ptoken. i.e.: --ptoken api-s4bokfdgdfjgerog')

    if args_verif is False :
        sys.exit(0)
    
    if options.google_sheet_api_credential is None:
        print("You don't pass json credential file of Google Sheet. Ignoring to record summary to Google Sheet.")
    
    if options.google_sheet_url is None:
        print("You don't pass URL of your google sheet. Ignoring to record summary to Google Sheet.")

    if options.slack_webhook is None:
        print("You don't pass slack incoming webhook URL. Ignoring to report it to slack.")
    
    today = datetime.date.today()
    phab = Phab(options.phabricator_url, options.phabricator_api_token, options.google_sheet_api_credential, options.google_sheet_url, options.slack_webhook)
    phab.compile(options.phabricator_tag, today)

if __name__ == '__main__':
    main()